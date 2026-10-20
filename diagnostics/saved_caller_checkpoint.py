"""Task-neutral, unchanged-base checkpoint with frozen public operator observations."""
from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

from diagnostics import caller_information
from diagnostics.caller_uptake import read_ref
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, SourceStore, disjoint
from diagnostics.segmented_input_audit import verify_turn
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "saved-caller-checkpoint-v1"
JOURNAL = "run_dev_savedcallerpreparation"


def load(source, turn_id):
    journal = DevJournal(source.root, source.run_id)
    for path, digest in ((journal.path, source.journal_hash),
                         (journal.envelope_path, source.envelope_hash),
                         (source.public_path, source.public_hash)):
        require(sha256_bytes(path.read_bytes()) == digest, "source identity changed")
    events, envelope = journal.events(), journal.load_envelope()
    require(envelope.runtime_hash == runtime_content_hash(), "source runtime changed")
    require(envelope.provider == "openai" and envelope.context_policy == "segmented-v1",
            "OpenAI segmented checkpoint required")
    public = load_public_task(source.public_path)
    require(public.split == "dev-train" and public.task_id == envelope.task_id,
            "public task identity changed")
    starts = [e for e in events if e["event_type"] == "turn_started"
              and e["payload"]["turn_id"] == turn_id]
    require(len(starts) == 1, "unique selected checkpoint required")
    start = starts[0]
    counts = [e for e in events if e["event_type"] == "input_count_started"
              and e["payload"]["turn_id"] == turn_id]
    require(len(counts) == 1, "unique target count required")
    count_start = counts[0]["sequence"]
    cutoff = max(e["sequence"] for e in events if e["sequence"] < count_start
                 and e["event_type"] in {"tool_batch_finished", "context_segment_prepared",
                                         "context_segment_started"})
    prefix = events[:cutoff]
    view = SimpleNamespace(events=lambda: prefix)
    require(DevJournal.unresolved_provider_call(view) is None
            and DevJournal.unresolved_input_count(view) is None,
            "uncertain inherited provider/count")
    require(not any(e["event_type"] == "action_started"
                    and e["payload"]["tool"] == "replace_text" for e in prefix),
            "unchanged-base checkpoint required")
    usage = [e["payload"] for e in prefix if e["event_type"] == "provider_call_finished"]
    require(usage and all(type(p.get("cost_nanos")) is int and p["cost_nanos"] >= 0
                         and not p.get("error_code") for p in usage),
            "uncertain inherited billing")
    store = SourceStore(source.root)
    runner._validate_recorded_continuations(prefix, store)
    bundle = json.loads(store.read_bytes(Artifact.model_validate(
        start["payload"]["prepared_input"]["artifact"])))
    request = bundle["request"]
    verified = verify_turn(start, events, store, actual_input=request["input"])
    require(verified["verified"], "source input projection mismatch")
    selected_counts = [e for e in events if e["event_type"] == "input_count_finished"
                       and e["payload"].get("count_id") == start["payload"]["selected_count_id"]]
    dispatches = [e for e in events if e["event_type"] == "provider_call_started"
                  and e["payload"]["turn_id"] == turn_id]
    require(len(selected_counts) == len(dispatches) == 1, "count/dispatch identity missing")
    counted, dispatch = selected_counts[0], dispatches[0]
    digest = sha256_json(request)
    require(count_start < counted["sequence"] < start["sequence"] < dispatch["sequence"]
            and digest == counted["payload"]["request_hash"]
            == dispatch["payload"]["request_hash"]
            == start["payload"]["counted_request_hash"]
            == start["payload"]["prepared_input"]["request_hash"]
            and counted["payload"]["input_tokens"] == dispatch["payload"]["input_tokens"],
            "counted/dispatched checkpoint changed")
    state = json.loads(request["input"][-1]["content"])["state"]
    context = json.loads(store.read_bytes(Artifact.model_validate(
        start["payload"]["context_artifact"])))
    require(context["public_task"] == public.model_dump(mode="json")
            and not state["current_diff"]["patch"]
            and not state["current_diff"]["untracked_files"], "public base state changed")
    require(request["model"] == envelope.model
            and request["reasoning"] == {"effort": envelope.reasoning_effort}
            and request["max_output_tokens"] == envelope.max_output_tokens,
            "model settings changed")
    return SimpleNamespace(request=request, store=store, mutation=None, envelope=envelope,
        receipt={"source_turn_id": turn_id, "cutoff_sequence": cutoff,
                 "source_prefix_hash": prefix[-1]["event_hash"],
                 "active_elapsed_ms": start["payload"]["active_elapsed_ms"],
                 "remaining_budget": state["remaining_budget"],
                 "historical_input_tokens": counted["payload"]["input_tokens"],
                 "source_projection": verified})


def restore_candidate(_workspace, mutation):
    require(mutation is None, "base checkpoint cannot restore a mutation")


def program_variant(template, instruction):
    if instruction == "Use the template exactly.":
        return template
    match = re.fullmatch(r"Replace the single line (.+) with (.+)\.", instruction)
    require(match is not None, "unsupported program variant")
    before, after = match.groups()
    require(template.splitlines().count(before) == 1, "variant anchor is not unique")
    return "".join(after + line[len(before):] if line.rstrip("\r\n") == before else line
                   for line in template.splitlines(keepends=True))


def checked_spec(descriptor):
    spec = json.loads(read_ref(descriptor))
    require(spec["schema"] == "caller-evidence-checkpoint-spec-v1"
            and spec["paid_authorized"] is False and spec["official"] is False,
            "unapproved specification required")
    source_data = spec["source"]
    public = repository_root() / spec["task"]
    source = Source(Path(source_data["root"]), source_data["run_id"],
                    source_data["journal"]["hash"], source_data["envelope"]["hash"],
                    public, sha256_bytes(public.read_bytes()))
    loaded = load(source, source_data["turn_id"])
    require(loaded.receipt["cutoff_sequence"] == source_data["cutoff_sequence"]
            and loaded.receipt["source_prefix_hash"] == source_data["cutoff_event_hash"]
            and loaded.receipt["active_elapsed_ms"] == source_data["active_elapsed_ms"]
            and loaded.receipt["remaining_budget"] == spec["remaining_budget"]
            and spec["runtime_hash"] == loaded.envelope.runtime_hash,
            "specification checkpoint changed")
    observation = json.loads(read_ref(spec["observation"]))
    envelope = loaded.envelope
    require(observation["origin"] == "operator"
            and observation["kind"] == "saved_public_probe_observation"
            and observation["base_commit"] == load_public_task(public).repository.base_commit
            and observation["diff_hash"] == sha256_bytes(b"")
            and observation["probe_image_digest"] == envelope.probe_image_digest
            and observation["probe_profile_hash"] == envelope.probe_profile_hash
            and observation["dependencies"] == envelope.probe_dependencies.model_dump(mode="json"),
            "observation base/environment changed")
    require(len(observation["program_template"]) <= 8000
            and len(observation["program_template"].encode()) <= 32000
            and len(canonical_json(observation)) <= 24000, "observation exceeds frozen bounds")
    rows = observation["observations"]
    prefix = DevJournal(source.root, source.run_id).events()[:loaded.receipt["cutoff_sequence"]]
    require(any(e["event_type"] == "action_finished" and e["payload"]["result"].get(
        "output", {}).get("snapshot_hash") == observation["snapshot_hash"] for e in prefix),
        "observation snapshot is not the checkpoint base")
    require(len(rows) == len(spec["public_provenance"]) == 2, "two public observations required")
    journals = {}
    for row, bound in zip(rows, spec["public_provenance"], strict=True):
        receipt = json.loads(read_ref(bound["receipt"]))
        # The specification stored text-mode LF templates; raw CRLF files and
        # their execution hashes remain bound separately, without other rewriting.
        program = read_ref(bound["program"]).decode().replace("\r\n", "\n")
        root = Path(bound["receipt"]["path"]).parent
        if root not in journals:
            records = list((root / "runs").glob("*.jsonl"))
            require(len(records) == 1, "unique observation journal required")
            journals[root] = DevJournal(root, records[0].stem).events()
        require(any(e["event_type"] == "calibration_probe_finished"
                    and e["payload"].get("receipt") == bound["receipt"]
                    for e in journals[root]), "receipt lacks completed journal provenance")
        require(row["variant"] == bound["mode"]
                and program_variant(observation["program_template"],
                    observation["program_variants"][row["variant"]]) == program
                and receipt["source_hash"] == bound["program"]["hash"]
                and receipt["snapshot_hash"] == observation["snapshot_hash"]
                and receipt["image_digest"] == envelope.probe_image_digest
                and receipt["profile_hash"] == envelope.probe_profile_hash
                and receipt["execution_policy"]["dependencies"] == observation["dependencies"]
                and receipt["status"] == "passed" and receipt["exit_code"] == 0
                and receipt["setup_checks"]["status"] == "passed"
                and all(c["matched"] for c in receipt["setup_checks"]["checks"])
                and not any(receipt[k] for k in
                            ("timed_out", "truncated", "cleanup_failed", "deadline_exhausted")),
                "public program/receipt changed")
        expected = {"variant": bound["mode"], "present": row["present"],
                    "execution_status": receipt["status"],
                    "execution_exit_code": receipt["exit_code"],
                    **{k: receipt[k] for k in ("source_hash", "timed_out", "truncated",
                         "cleanup_failed", "deadline_exhausted", "setup_checks",
                         "stdout", "stderr")}}
        require(row == expected, "observation is not raw receipt data")
    require(sum(len((r["stdout"] + r["stderr"]).encode()) for r in rows) <= 12000,
            "combined public output exceeds bound")
    pair = {"A": loaded.request, "B": caller_information.project(loaded.request, observation)}
    for arm, request in pair.items():
        require(json.loads(read_ref(spec["first_request_examples"][arm])) == request
                and sha256_json(request) == spec["canonical_request_hashes"][arm]
                and len(canonical_json(request).encode()) <= 1048576,
                "frozen first request changed")
    require(spec["order"] == [f"{a}{n}" for n in range(1, 7)
                              for a in ("AB" if n % 2 else "BA")], "roster changed")
    remaining = loaded.receipt["remaining_budget"]["cost"]
    funds = spec["funding"]
    require(funds["historical_debit_per_branch_nanos"] == remaining["settled_usage"]
            and funds["new_row_cap_nanos"] == remaining["remaining"] > 0
            and funds["logical_row_cap_nanos"] == envelope.max_cost_nanos
            == remaining["settled_usage"] + remaining["remaining"]
            and funds["new_arm_cap_nanos"] == 6 * remaining["remaining"]
            and funds["new_invocation_cap_nanos"] == 12 * remaining["remaining"],
            "inherited allocation changed")
    return spec, source, loaded, observation


def observation(packet):
    return checked_spec(packet["specification"])[3]


def implementation_hashes():
    return {p: sha256_bytes((repository_root() / p).read_bytes()) for p in (
        "diagnostics/saved_caller_checkpoint.py", "diagnostics/caller_information.py",
        "diagnostics/checkpoint_continuation.py")}


def prepare(specification, output):
    spec, source, loaded, supplement = checked_spec(specification)
    disjoint(output.resolve(), (repository_root(), source.root,
                                Path(specification["path"]).parent, source.public_path.parent))
    output.mkdir()
    store = ArtifactStore(output / "artifacts")
    pair = {"A": loaded.request, "B": caller_information.project(loaded.request, supplement)}
    packet = {"schema": SCHEMA, "official": False, "paid_execution_authorized": False,
              "specification": specification, "source": source.record(),
              "checkpoint": loaded.receipt, "runtime_hash": runtime_content_hash(),
              "implementation_hashes": implementation_hashes(), "order": spec["order"],
              "pair": {a + "_request_hash": sha256_json(r) for a, r in pair.items()},
              "requests": {a: store.put_json(r).model_dump(mode="json") for a, r in pair.items()},
              "supplement_hash": sha256_json(supplement)}
    path = output / "packet.json"
    path.write_text(canonical_json(packet) + "\n", encoding="utf-8")
    digest = sha256_bytes(path.read_bytes())
    DevJournal(output, JOURNAL).append("diagnostic_input_pair_prepared", {"packet_hash": digest})
    return {"packet": str(path), "packet_hash": digest}


def validate(path, digest):
    require(sha256_bytes(path.read_bytes()) == digest, "packet identity changed")
    packet = json.loads(path.read_bytes())
    spec, source, loaded, supplement = checked_spec(packet["specification"])
    require(packet["schema"] == SCHEMA and packet["paid_execution_authorized"] is False
            and packet["source"] == source.record() and packet["checkpoint"] == loaded.receipt
            and packet["runtime_hash"] == runtime_content_hash()
            and packet["implementation_hashes"] == implementation_hashes()
            and packet["order"] == spec["order"]
            and packet["supplement_hash"] == sha256_json(supplement), "checkpoint changed")
    store = SourceStore(path.parent)
    for arm, expected in (("A", loaded.request),
                          ("B", caller_information.project(loaded.request, supplement))):
        actual = json.loads(store.read_bytes(Artifact.model_validate(packet["requests"][arm])))
        require(actual == expected and sha256_json(actual) == packet["pair"][arm + "_request_hash"],
                "input pair changed")
    events = DevJournal(path.parent, JOURNAL).events()
    require(len(events) == 1 and events[0]["payload"]["packet_hash"] == digest,
            "preparation binding changed")
    return {"verified": True, "model_calls": 0, "input_counts": 0}
