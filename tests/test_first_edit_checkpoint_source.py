"""Frozen checkpoint extraction uses public observations, never replay or later turns."""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

import pytest

from diagnostics import first_edit_checkpoint_source as source
from patchloop.artifacts import ArtifactStore
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_json


@pytest.fixture
def public_checkpoint():
    patch = "synthetic unchanged seed patch\n"
    seed = sha256_bytes(patch.encode())
    program = "raise RuntimeError('MUST_NOT_EXECUTE')\n"
    question = "Does the public helper distinguish the inputs?"
    span = {"path": "project/source.py", "start_line": 1, "end_line": 2,
            "content": "def target():\n    return 1\n", "file_hash": sha256_bytes(b"source")}
    partial = {**span, "start_line": 2, "content": "    return 1\n"}
    result = {
        "tool": "run_probe", "status": "succeeded", "action_id": "helper-1",
        "workspace_diff_hash": seed,
        "output": {"status": "passed", "exit_code": 0, "probe_stage": "execution_returned",
                   "verification_scope": "helper_or_unbound_diagnostic",
                   "truncated": False, "timed_out": False, "cleanup_failed": False,
                   "stdout": "actual complete public observation\n", "stderr": "",
                   "captured_output_bytes": 35, "observed_output_bytes": 35,
                   "source_hash": sha256_bytes(program.encode()), "question": question,
                   "workspace_diff_hash": seed},
    }
    user = {"initial_source": [span], "initial_source_diff_hash": seed,
            "public_feedback": {"status": "failed"}, "registered_dependency_sources": [],
            "current_original_recheck": {"candidate_diff_hash": seed, "status": "failed"}}
    state = {
        "current_diff": {"patch": patch, "diff_hash": seed},
        "current_original_recheck": {"candidate_diff_hash": seed, "status": "failed"},
        "current_sources": [{**span, "span_id": "old", "last_observed_seq": 5}, partial],
        "dependency_sources": [{"path": "caller/public.py", "content": "PUBLIC = True\n"}],
        "action_outcomes": [{"action_id": "helper-1", "status": "succeeded"}],
        "latest_batch_action_ids": ["helper-1"], "protocol_correction": None,
        "counters": {"normal_calls": 14, "model_limit": 15}, "binding": {},
    }
    handoff = {"kind": source.HANDOFF_KIND, "instructions": "quoted public state", "state": state}
    archive = {
        "kind": source.ARCHIVE_KIND, "observations": [], "sources": [],
        "referenced_public_exchanges": [
            {"type": "function_call", "name": "run_probe", "call_id": "helper-1",
             "arguments": canonical_json({"question": question, "python_source": program,
                                          "memory_update": None})},
            {"type": "function_call_output", "call_id": "helper-1",
             "output": canonical_json(result)},
        ],
    }
    request = {"input": [
        {"role": "system", "content": "old system contract"},
        {"role": "user", "content": canonical_json(user)},
        {"role": "developer", "content": canonical_json(handoff)},
        {"role": "developer", "content": canonical_json(archive)},
        {"role": "developer", "content": "OLD_BUDGET_DO_NOT_RETAIN"},
    ]}
    events = [
        {"sequence": 1, "event_type": "action_finished", "event_hash": "helper-event",
         "payload": {"action_id": "helper-1", "result": result}},
        {"sequence": 3, "event_type": "provider_call_started", "event_hash": "cutoff-event",
         "payload": {"call_id": "selected-call", "request_hash": sha256_json(request)}},
        {"sequence": 4, "event_type": "action_finished",
         "payload": {"result": {"message": "LATER_FAILURE_DO_NOT_RETAIN"}}},
    ]
    return SimpleNamespace(events=events, request=request, seed=seed)


def extract(case):
    return source.extract_checkpoint(
        case.events, case.request, cutoff_sequence=3, helper_sequence=1,
        call_id="selected-call", seed_hash=case.seed,
    )


def change_body(case, index, change):
    body = json.loads(case.request["input"][index]["content"])
    change(body)
    case.request["input"][index]["content"] = canonical_json(body)
    case.events[1]["payload"]["request_hash"] = sha256_json(case.request)


def test_projection_preserves_exact_public_results_and_unique_spans(public_checkpoint):
    case = public_checkpoint
    checkpoint = extract(case)
    assert len(checkpoint.bodies) == 3 and len(checkpoint.workspace_spans) == 2
    assert all(set(span) == set(source.SPAN_FIELDS) for span in checkpoint.workspace_spans)
    assert checkpoint.workspace_spans[0]["start_line"] == 1
    assert checkpoint.workspace_spans[1]["start_line"] == 2
    assert checkpoint.bodies[1]["state"]["counters"]["normal_calls"] == 14
    archive_result = json.loads(checkpoint.bodies[2]["referenced_public_exchanges"][1]["output"])
    assert archive_result == case.events[0]["payload"]["result"]
    assert checkpoint.provenance["helper_result_hash"] == sha256_json(archive_result)
    serialized = canonical_json(checkpoint.bodies)
    assert "OLD_BUDGET_DO_NOT_RETAIN" not in serialized
    assert "LATER_FAILURE_DO_NOT_RETAIN" not in serialized
    assert "old system contract" not in serialized
    checkpoint.bodies[0]["initial_source"].clear()
    assert json.loads(case.request["input"][1]["content"])["initial_source"]


def test_projection_does_not_execute_the_saved_helper(public_checkpoint, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("checkpoint loading must not dispatch execution")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    checkpoint = extract(public_checkpoint)
    assert "MUST_NOT_EXECUTE" in canonical_json(checkpoint.bodies)


def test_request_tampering_is_rejected(public_checkpoint):
    public_checkpoint.request["input"][1]["content"] += " "
    with pytest.raises(ContractError, match="differs from the selected provider call"):
        extract(public_checkpoint)


@pytest.mark.parametrize("change", [
    lambda messages: messages.append({"type": "reasoning", "encrypted_content": "opaque"}),
    lambda messages: messages[2].update({"type": "reasoning", "encrypted_content": "opaque"}),
    lambda messages: messages[3].update({"role": "assistant"}),
])
def test_nonpublic_or_opaque_input_is_rejected(public_checkpoint, change):
    change(public_checkpoint.request["input"])
    public_checkpoint.events[1]["payload"]["request_hash"] = sha256_json(public_checkpoint.request)
    with pytest.raises(ContractError, match="five public|non-public or opaque"):
        extract(public_checkpoint)


def test_late_cutoff_and_late_helper_are_rejected(public_checkpoint):
    case = public_checkpoint
    case.events[1]["payload"]["call_id"] = "later-failed-call"
    with pytest.raises(ContractError, match="cutoff call changed"):
        extract(case)
    with pytest.raises(ContractError, match="must precede cutoff"):
        source.extract_checkpoint(case.events, case.request, cutoff_sequence=3, helper_sequence=4)


def test_missing_or_superseded_helper_is_rejected(public_checkpoint):
    case = public_checkpoint
    case.events.pop(0)
    with pytest.raises(ContractError, match="action_finished at sequence 1"):
        extract(case)


def test_later_completed_action_before_cutoff_rejects_old_helper(public_checkpoint):
    public_checkpoint.events.append({"sequence": 2, "event_type": "action_finished", "payload": {}})
    with pytest.raises(ContractError, match="not the latest completed action"):
        extract(public_checkpoint)


@pytest.mark.parametrize("index,field", [(1, "initial_source_diff_hash"), (2, "diff_hash")])
def test_stale_seed_is_rejected(public_checkpoint, index, field):
    def change(body):
        target = body if index == 1 else body["state"]["current_diff"]
        target[field] = sha256_bytes(b"another seed")

    change_body(public_checkpoint, index, change)
    with pytest.raises(ContractError, match="seed diff changed"):
        extract(public_checkpoint)


@pytest.mark.parametrize("flag,value", [
    ("truncated", True), ("timed_out", True), ("cleanup_failed", True), ("status", "failed"),
])
def test_incomplete_helper_result_is_rejected(public_checkpoint, flag, value):
    public_checkpoint.events[0]["payload"]["result"]["output"][flag] = value
    with pytest.raises(ContractError, match="completed untruncated"):
        extract(public_checkpoint)


def test_missing_or_changed_archived_helper_is_rejected(public_checkpoint):
    case = public_checkpoint
    change_body(case, 3, lambda body: body["referenced_public_exchanges"].pop())
    with pytest.raises(ContractError, match="only the latest helper exchange"):
        extract(case)


def test_archived_helper_output_must_equal_journal_result(public_checkpoint):
    def change(body):
        result = json.loads(body["referenced_public_exchanges"][1]["output"])
        result["output"]["stdout"] = "fabricated observation"
        body["referenced_public_exchanges"][1]["output"] = canonical_json(result)

    change_body(public_checkpoint, 3, change)
    with pytest.raises(ContractError, match="output differs from the journal"):
        extract(public_checkpoint)


@pytest.fixture
def sealed_checkpoint(public_checkpoint, tmp_path, monkeypatch):
    case = public_checkpoint
    journal = DevJournal(tmp_path, "run_dev_syntheticcheckpoint")
    store = ArtifactStore(tmp_path / "artifacts")
    handoff = json.loads(case.request["input"][2]["content"])
    state = handoff["state"]
    artifacts = {
        "current_diff": store.put_text(state["current_diff"]["patch"]).model_dump(mode="json"),
        "current_sources": store.put_json(state["current_sources"]).model_dump(mode="json"),
        "dependency_sources": store.put_json(state["dependency_sources"]).model_dump(mode="json"),
    }
    state["binding"] = {name: artifact["content_hash"] for name, artifact in artifacts.items()}
    # These hashes are provenance only. Neither artifact exists or may be read.
    state["binding"].update({"parent_history": sha256_bytes(b"opaque history"),
                             "parent_request": sha256_bytes(b"opaque request")})
    case.request["input"][2]["content"] = canonical_json(handoff)
    request_artifact = store.put_json(case.request).model_dump(mode="json")
    journal.append("action_finished", case.events[0]["payload"])
    journal.append("repair_context_committed", {"state_hash": sha256_json(state),
                                                "artifacts": artifacts})
    journal.append("provider_call_started", {"call_id": "selected-call",
                                             "request_hash": sha256_json(case.request),
                                             "request": request_artifact})
    journal.append("after_cutoff_failure", {"message": "LATE_EVENT_NEVER_PROJECTED"})
    for name, value in {
        "SOURCE_JOURNAL": journal.path,
        "SOURCE_JOURNAL_HASH": sha256_bytes(journal.path.read_bytes()),
        "SOURCE_REQUEST_HASH": request_artifact["content_hash"], "CUTOFF_SEQUENCE": 3,
        "CUTOFF_CALL_ID": "selected-call", "HELPER_SEQUENCE": 1, "SEED_HASH": case.seed,
    }.items():
        monkeypatch.setattr(source, name, value)
    return SimpleNamespace(journal=journal, artifacts=artifacts, request=request_artifact)


def test_loader_checks_chain_and_reads_only_bound_public_artifacts(sealed_checkpoint, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("loader must not append events or execute commands")

    monkeypatch.setattr(DevJournal, "append", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    checkpoint = source.load_checkpoint()
    assert len(checkpoint.bindings) == 5
    assert all(set(binding) == {"path", "hash", "bytes"} for binding in checkpoint.bindings)
    assert checkpoint.provenance["source_journal"]["path"] == str(sealed_checkpoint.journal.path)
    assert "LATE_EVENT_NEVER_PROJECTED" not in canonical_json(checkpoint.bodies)


@pytest.mark.parametrize("selected", ["journal", "request", "current_sources"])
def test_loader_rejects_changed_bound_file(sealed_checkpoint, selected):
    from pathlib import Path

    path = (sealed_checkpoint.journal.path if selected == "journal" else Path(
        sealed_checkpoint.request["path"] if selected == "request"
        else sealed_checkpoint.artifacts[selected]["path"]))
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ContractError, match="hash/size changed"):
        source.load_checkpoint()


def test_loader_rejects_invalid_journal_chain_even_with_matching_raw_hash(
    sealed_checkpoint, monkeypatch,
):
    path = sealed_checkpoint.journal.path
    events = [json.loads(line) for line in path.read_text().splitlines()]
    events[0]["payload"]["unexpected"] = "tampered without rehashing"
    path.write_text("".join(canonical_json(event) + "\n" for event in events), encoding="utf-8")
    monkeypatch.setattr(source, "SOURCE_JOURNAL_HASH", sha256_bytes(path.read_bytes()))
    with pytest.raises(RecoveryError, match="hash chain is invalid"):
        source.load_checkpoint()
