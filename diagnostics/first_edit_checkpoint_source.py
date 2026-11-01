"""Load a frozen public input before the closed run's unsuccessful first-edit call.

No provider, target code, probe, replay or budget change is performed here. Opaque
parent-history artifacts and events after the selected cutoff are never projected.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes, sha256_json

SOURCE_JOURNAL = Path("C:/pt/dependency-source-run-v1/R1/runs/run_dev_feedbacksourcemodel.jsonl")
SOURCE_JOURNAL_HASH = "sha256:097cb3c208b9a8f39ad011fbeccf823dc9752bc30bae2ced04e4f4503664acf4"
SOURCE_REQUEST_HASH = "sha256:727dcf9429de510ea20c90996a0827fb937236d6bcfac37540ecd1cc0cc04c9b"
CUTOFF_SEQUENCE = 120
CUTOFF_CALL_ID = "call-count-14-0-0-segment-3"
HELPER_SEQUENCE = 113
SEED_HASH = "sha256:93b024b3f11ef89311d9cbf5a06a56328b14f7b7d7687746e6d24a8b9fb8e3e5"
SPAN_FIELDS = ("path", "start_line", "end_line", "content", "file_hash")
HANDOFF_KIND = "diagnostic_repair_cycle_handoff_v1"
ARCHIVE_KIND = "harness_historical_public_evidence_v1"


def require(condition, message):
    if not condition:
        raise ContractError(message)


def _event(events, sequence, event_type):
    selected = [event for event in events if event.get("sequence") == sequence]
    require(len(selected) == 1 and selected[0].get("event_type") == event_type,
            f"checkpoint requires one {event_type} at sequence {sequence}")
    return selected[0]


def extract_checkpoint(events, request, *, cutoff_sequence=CUTOFF_SEQUENCE,
                       call_id=CUTOFF_CALL_ID, helper_sequence=HELPER_SEQUENCE,
                       seed_hash=SEED_HASH):
    """Pure projection; callers validate journal bytes/hash chain before extraction."""
    require(helper_sequence < cutoff_sequence, "checkpoint helper must precede cutoff")
    cutoff = _event(events, cutoff_sequence, "provider_call_started")
    require(cutoff["payload"].get("call_id") == call_id, "checkpoint cutoff call changed")
    require(sha256_json(request) == cutoff["payload"].get("request_hash"),
            "checkpoint request differs from the selected provider call")
    messages = request.get("input")
    require(isinstance(messages, list) and len(messages) == 5,
            "checkpoint requires exactly five public role messages")
    roles = ["system", "user", "developer", "developer", "developer"]
    require(all(isinstance(item, dict) and set(item) == {"role", "content"}
                and item["role"] == role and isinstance(item["content"], str)
                for item, role in zip(messages, roles, strict=True)),
            "checkpoint input contains non-public or opaque items")
    try:
        user, handoff, archive = (json.loads(messages[index]["content"]) for index in (1, 2, 3))
    except (ValueError, TypeError) as exc:
        raise ContractError("checkpoint public bodies are not JSON") from exc
    require(isinstance(user, dict) and isinstance(handoff, dict) and isinstance(archive, dict),
            "checkpoint public bodies must be objects")
    require(handoff.get("kind") == HANDOFF_KIND and archive.get("kind") == ARCHIVE_KIND,
            "checkpoint public handoff/archive kind changed")
    state = handoff.get("state", {})
    require(state.get("protocol_correction") is None, "checkpoint includes an active correction")
    require(user.get("initial_source_diff_hash") == seed_hash
            and state.get("current_diff", {}).get("diff_hash") == seed_hash,
            "checkpoint seed diff changed")
    patch = state["current_diff"].get("patch")
    require(isinstance(patch, str) and sha256_bytes(patch.encode("utf-8")) == seed_hash,
            "checkpoint seed patch bytes changed")
    for original in (user.get("current_original_recheck"),
                     state.get("current_original_recheck")):
        require(isinstance(original, dict) and original.get("candidate_diff_hash") == seed_hash,
                "checkpoint original observation belongs to another seed")

    helper = _event(events, helper_sequence, "action_finished")
    result = helper["payload"].get("result", {})
    action_id = helper["payload"].get("action_id")
    output = result.get("output", {})
    require(result.get("tool") == "run_probe" and result.get("status") == "succeeded"
            and result.get("action_id") == action_id
            and result.get("workspace_diff_hash") == seed_hash
            and output.get("workspace_diff_hash") == seed_hash,
            "checkpoint helper result does not match the unchanged seed")
    require(output.get("status") == "passed" and output.get("exit_code") == 0
            and output.get("probe_stage") == "execution_returned"
            and output.get("verification_scope") == "helper_or_unbound_diagnostic"
            and all(output.get(key) is False
                    for key in ("truncated", "timed_out", "cleanup_failed"))
            and isinstance(output.get("stdout"), str) and output["stdout"]
            and output.get("captured_output_bytes") == output.get("observed_output_bytes"),
            "checkpoint requires a completed untruncated public helper observation")
    exchanges = archive.get("referenced_public_exchanges", [])
    require(len(exchanges) == 2 and not archive.get("observations") and not archive.get("sources"),
            "checkpoint archive must contain only the latest helper exchange")
    call, returned = exchanges
    require(call.get("type") == "function_call" and call.get("name") == "run_probe"
            and call.get("call_id") == action_id and returned.get("call_id") == action_id
            and returned.get("type") == "function_call_output",
            "checkpoint archive helper identity changed")
    try:
        archived_result = json.loads(returned["output"])
        arguments = json.loads(call["arguments"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("checkpoint helper exchange is malformed") from exc
    require(archived_result == result, "checkpoint helper output differs from the journal")
    program = arguments.get("python_source")
    require(isinstance(program, str)
            and sha256_bytes(program.encode("utf-8")) == output.get("source_hash")
            and arguments.get("question") == output.get("question"),
            "checkpoint helper program differs from its public execution")
    require(state.get("latest_batch_action_ids") == [action_id],
            "checkpoint latest public batch is not the selected helper")
    require(not any(event["event_type"] == "action_finished"
                    for event in events if helper_sequence < event["sequence"] < cutoff_sequence),
            "checkpoint selected helper is not the latest completed action")

    spans, seen = [], set()
    for span in [*user.get("initial_source", []), *state.get("current_sources", [])]:
        require(isinstance(span, dict) and all(key in span for key in SPAN_FIELDS),
                "checkpoint workspace source span is incomplete")
        public = {key: copy.deepcopy(span[key]) for key in SPAN_FIELDS}
        identity = sha256_json(public)
        if identity not in seen:
            seen.add(identity)
            spans.append(public)
    require(bool(spans), "checkpoint has no observed workspace source")
    return SimpleNamespace(
        bodies=copy.deepcopy([user, handoff, archive]), workspace_spans=spans, bindings=[],
        provenance={"schema": "frozen-public-first-edit-checkpoint-v1",
                    "cutoff_sequence": cutoff_sequence, "cutoff_call_id": call_id,
                    "cutoff_event_hash": cutoff.get("event_hash"),
                    "request_hash": sha256_json(request), "seed_diff_hash": seed_hash,
                    "helper_sequence": helper_sequence, "helper_action_id": action_id,
                    "helper_event_hash": helper.get("event_hash"),
                    "helper_result_hash": sha256_json(result)},
    )


def _read_bound(path, expected_hash, expected_bytes=None):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "checkpoint source file is unavailable")
    raw = path.read_bytes()
    require(sha256_bytes(raw) == expected_hash
            and (expected_bytes is None or len(raw) == expected_bytes),
            "checkpoint source file hash/size changed")
    return raw, {"path": str(path.resolve()), "hash": expected_hash, "bytes": len(raw)}


def _artifact(root, reference):
    digest = reference["content_hash"]
    require(isinstance(digest, str) and digest.startswith("sha256:") and len(digest) == 71,
            "checkpoint artifact has no SHA-256 identity")
    hex_digest = digest[7:]
    expected = root / "artifacts" / "objects" / "sha256" / hex_digest[:2] / hex_digest[2:]
    require(Path(reference["path"]).resolve() == expected.resolve(),
            "checkpoint artifact path differs from its canonical identity")
    return _read_bound(expected, digest, reference["size_bytes"])


def load_checkpoint():
    """Read only the sealed journal, selected request and its public source artifacts."""
    _, journal_binding = _read_bound(SOURCE_JOURNAL, SOURCE_JOURNAL_HASH)
    root = SOURCE_JOURNAL.parent.parent
    journal = DevJournal(root, SOURCE_JOURNAL.stem)
    events = journal.events()
    # Check again after hash-chain loading to bind exactly the same immutable bytes.
    _read_bound(SOURCE_JOURNAL, SOURCE_JOURNAL_HASH)
    cutoff = _event(events, CUTOFF_SEQUENCE, "provider_call_started")
    reference = cutoff["payload"]["request"]
    require(reference["content_hash"] == SOURCE_REQUEST_HASH,
            "checkpoint selected request artifact changed")
    raw, request_binding = _artifact(root, reference)
    checkpoint = extract_checkpoint(
        events, json.loads(raw), cutoff_sequence=CUTOFF_SEQUENCE, call_id=CUTOFF_CALL_ID,
        helper_sequence=HELPER_SEQUENCE, seed_hash=SEED_HASH,
    )
    state = checkpoint.bodies[1]["state"]
    committed = [event for event in events if event["sequence"] < CUTOFF_SEQUENCE
                 and event["event_type"] == "repair_context_committed"]
    require(bool(committed) and committed[-1]["payload"].get("state_hash") == sha256_json(state),
            "checkpoint handoff differs from its committed public state")
    checkpoint.bindings = [journal_binding, request_binding]
    for name in ("current_diff", "current_sources", "dependency_sources"):
        reference = committed[-1]["payload"]["artifacts"][name]
        require(reference["content_hash"] == state["binding"][name],
                "checkpoint public artifact binding changed")
        raw, binding = _artifact(root, reference)
        expected = state["current_diff"]["patch"] if name == "current_diff" else state[name]
        actual = raw.decode("utf-8") if name == "current_diff" else json.loads(raw)
        require(actual == expected, "checkpoint public artifact differs from projected state")
        checkpoint.bindings.append(binding)
    checkpoint.provenance.update({"source_journal": journal_binding,
                                  "source_request": request_binding})
    return checkpoint
