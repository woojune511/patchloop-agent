"""Prepare a saved post-probe input pair. No provider or tool execution entry point."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, SourceStore, disjoint
from diagnostics.segmented_input_audit import verify_turn
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, PublicTask
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

POLICY = "current-mutation-advice-off-v1"
ORIGINAL = (
    "The current candidate needs a repair. Use replace_text for a supported edit; "
    "available anchor evidence does not establish a correct solution. "
    "Submission waits for a scoped patch and its required visible checks."
)
FACTUAL = (
    "The current candidate needs a repair. "
    "Available anchor evidence does not establish a correct solution. "
    "Submission waits for a scoped patch and its required visible checks."
)


def project(request):
    """Change the final current-state message only; retain opaque history exactly."""
    result = copy.deepcopy(request)
    item = result["input"][-1]
    require(item.get("role") == "developer", "final current-state message required")
    view = json.loads(item["content"])
    require(view.get("kind") == "harness_current_state"
            and canonical_json(view) == item["content"], "canonical current state required")
    state = view["state"]
    guidance = state["completion_guidance"]
    require(state["workflow_gate"] == "needs_mutation"
            and guidance["stage"] == "needs_mutation"
            and guidance["submission_ready"] is False
            and guidance["next_action"] == {"tool": "replace_text"}
            and guidance["message"] == ORIGINAL, "unsupported mutation guidance")
    require(not state["current_diff"]["patch"]
            and not state["current_diff"]["untracked_files"], "pre-edit checkpoint required")
    require("replace_text" in {tool["name"] for tool in request["tools"]},
            "mutation tool must remain available")
    guidance.update(next_action=None, message=FACTUAL)
    item["content"] = canonical_json(view)
    return result


def verify_pair(a, b):
    require(b == project(a), "pair differs beyond the two guidance fields")
    return {
        "verified": True, "policy": POLICY,
        "changed_fields": ["completion_guidance.next_action", "completion_guidance.message"],
        "A_request_hash": sha256_json(a), "B_request_hash": sha256_json(b),
        "preserved_history_hash": sha256_json(a["input"][:-1]),
        "preserved_settings_and_tools_hash": sha256_json(
            {key: value for key, value in a.items() if key != "input"}),
        "current_message_only": True, "prior_exposure_removed": False,
    }


def load(source: Source):
    """Select the first completed probe's next input before any mutation.

    Read only public records and native encrypted continuation artifacts. Future
    dispatch metadata binds A's identity, but future decisions never enter the pair.
    """
    path = source.root / "runs" / f"{source.run_id}.jsonl"
    for p, digest in ((path, source.journal_hash),
                      (path.with_suffix(".envelope.json"), source.envelope_hash),
                      (source.public_path, source.public_hash)):
        require(p.is_file() and sha256_bytes(p.read_bytes()) == digest, "source identity changed")
    journal = DevJournal(source.root, source.run_id)
    events, envelope = journal.events(), journal.load_envelope()
    require(envelope.runtime_hash == runtime_content_hash(), "source runtime changed")
    require(envelope.provider == "openai" and envelope.context_policy == "segmented-v1",
            "OpenAI segmented checkpoint required")
    public = PublicTask.model_validate(yaml.safe_load(
        source.public_path.read_text(encoding="utf-8")))
    require(public.split == "dev-train" and public.task_id == envelope.task_id
            and public.task_version == envelope.task_version, "public task identity changed")
    probes = [e for e in events if e["event_type"] == "action_started"
              and e["payload"].get("tool") == "run_probe"]
    require(bool(probes), "first probe absent")
    probe = probes[0]
    starts = [e for e in events if e["event_type"] == "turn_started"
              and e["sequence"] > probe["sequence"]]
    require(bool(starts), "post-probe input absent")
    start = starts[0]
    prefix = [e for e in events if e["sequence"] < start["sequence"]]
    actions = [e["payload"] for e in prefix if e["event_type"] == "action_started"]
    require(all(a["tool"] in {"search_files", "read_file", "run_probe"} for a in actions),
            "checkpoint is not initial read/search/probe work")
    finished = [e for e in prefix if e["event_type"] == "action_finished"
                and e["payload"]["action_id"] == probe["payload"]["action_id"]]
    batches = [e for e in prefix if e["event_type"] == "tool_batch_finished"]
    require(len(finished) == 1 and finished[0]["payload"]["result"]["status"] == "succeeded"
            and bool(batches)
            and batches[-1]["payload"]["action_ids"] == [probe["payload"]["action_id"]],
            "one completed first probe batch required")
    output = finished[0]["payload"]["result"]["output"]
    require(output["status"] == "passed" and not output["timed_out"]
            and not output["cleanup_failed"], "first probe execution did not complete cleanly")
    prefix_view = SimpleNamespace(events=lambda: prefix)
    require(DevJournal.unresolved_provider_call(prefix_view) is None
            and DevJournal.unresolved_input_count(prefix_view) is None,
            "uncertain source dispatch or count")
    usage = [e["payload"] for e in prefix if e["event_type"] == "provider_call_finished"]
    require(bool(usage) and all(type(u.get("cost_nanos")) is int and u["cost_nanos"] >= 0
                               and not u.get("error_code") for u in usage),
            "uncertain source billing")
    store = SourceStore(source.root)
    runner._validate_recorded_continuations(prefix, store)
    boundary = start["payload"]["prepared_input"]
    request = json.loads(store.read_bytes(Artifact.model_validate(boundary["artifact"])))[
        "request"]
    verified = verify_turn(start, events, store, actual_input=request["input"])
    counts = [e for e in prefix if e["event_type"] == "input_count_finished"
              and e["payload"].get("count_id") == start["payload"]["selected_count_id"]]
    dispatches = [e for e in events if e["event_type"] == "provider_call_started"
                  and e["payload"]["turn_id"] == start["payload"]["turn_id"]]
    require(len(counts) == len(dispatches) == 1, "unique count/dispatch binding required")
    count, dispatch = counts[0], dispatches[0]
    require(count["sequence"] < start["sequence"] < dispatch["sequence"]
            and sha256_json(request) == boundary["request_hash"]
            == count["payload"]["request_hash"] == dispatch["payload"]["request_hash"]
            == start["payload"]["counted_request_hash"]
            and count["payload"]["input_tokens"] == dispatch["payload"]["input_tokens"],
            "counted/dispatched checkpoint identity changed")
    require(request["model"] == envelope.model
            and request["reasoning"] == {"effort": envelope.reasoning_effort}
            and request["max_output_tokens"] == 25_000, "checkpoint model settings changed")
    state = json.loads(request["input"][-1]["content"])["state"]
    # Public task resides in the immutable seed in segmented inputs.
    context = json.loads(store.read_bytes(Artifact.model_validate(
        start["payload"]["context_artifact"])))
    require(context["public_task"] == public.model_dump(mode="json"), "public source mismatch")
    verify_pair(request, project(request))
    return SimpleNamespace(request=request, store=store, source=source, receipt={
        "source_turn_id": start["payload"]["turn_id"],
        "source_probe_action_id": probe["payload"]["action_id"],
        "source_prefix_hash": prefix[-1]["event_hash"],
        "source_projection": verified, "historical_input_tokens": count["payload"]["input_tokens"],
        "historical_cost_nanos_before_boundary": sum(u["cost_nanos"] for u in usage),
        "remaining_budget": state["remaining_budget"],
    })


def implementation_hashes():
    names = ("mutation_advice_checkpoint.py", "declaration_checkpoint.py",
             "decision_sampler.py", "segmented_input_audit.py")
    identities = {name: sha256_bytes(Path(__file__).with_name(name).read_bytes()) for name in names}
    contract = repository_root() / ".agent/mutation-advice-checkpoint.md"
    identities["contract"] = sha256_bytes(contract.read_bytes())
    return identities


def prepare(source, output):
    output = output.resolve()
    disjoint(output, (repository_root(), source.root, source.public_path.parent))
    loaded = load(source)
    a, b = loaded.request, project(loaded.request)
    receipt = verify_pair(a, b)
    output.mkdir()
    store = ArtifactStore(output / "artifacts")
    packet = {
        "schema": "mutation-advice-checkpoint-v1", "official": False,
        "status": "PREPARED_NOT_EXECUTABLE", "paid_execution_authorized": False,
        "runtime_hash": runtime_content_hash(), "implementation_hashes": implementation_hashes(),
        "source": source.record(), "checkpoint": loaded.receipt, "pair": receipt,
        "requests": {arm: store.put_json(req).model_dump(mode="json")
                     for arm, req in (("A", a), ("B", b))},
        "inherited_artifacts": loaded.store.reads,
        "model_calls": 0, "input_counts": 0, "tool_executions": 0,
        "acceptance": "NOT_RUN", "safety": "NOT_RUN", "efficacy": "NOT_RUN",
    }
    packet_bytes = (canonical_json(packet) + "\n").encode()
    with (output / "packet.json").open("xb") as stream:
        stream.write(packet_bytes)
    digest = sha256_bytes(packet_bytes)
    journal = DevJournal(output, "run_dev_mutationadvicepreparation")
    journal.append("diagnostic_input_pair_prepared", {
        "packet_hash": digest, "pair": receipt, "official": False, "live_execution": False})
    return {"packet": str(output / "packet.json"), "packet_hash": digest,
            "status": packet["status"], "pair": receipt}


def validate(path, digest):
    require(sha256_bytes(path.read_bytes()) == digest, "packet identity changed")
    packet = json.loads(path.read_bytes())
    require(packet["schema"] == "mutation-advice-checkpoint-v1"
            and packet["status"] == "PREPARED_NOT_EXECUTABLE"
            and packet["paid_execution_authorized"] is False, "offline packet required")
    require(packet["runtime_hash"] == runtime_content_hash()
            and packet["implementation_hashes"] == implementation_hashes(),
            "implementation changed")
    loaded = load(Source.from_record(packet["source"]))
    store = SourceStore(path.parent)
    pair = {arm: json.loads(store.read_bytes(Artifact.model_validate(value)))
            for arm, value in packet["requests"].items()}
    require(set(pair) == {"A", "B"} and pair["A"] == loaded.request, "baseline input changed")
    receipt = verify_pair(pair["A"], pair["B"])
    require(receipt == packet["pair"] and loaded.receipt == packet["checkpoint"]
            and loaded.store.reads == packet["inherited_artifacts"], "source receipt changed")
    events = DevJournal(path.parent, "run_dev_mutationadvicepreparation").events()
    require(len(events) == 1 and events[0]["payload"]["packet_hash"] == digest,
            "preparation journal mismatch")
    return {"verified": True, "packet_hash": digest, "pair": receipt,
            "inherited_artifact_count": len(loaded.store.reads), "model_calls": 0,
            "input_counts": 0, "tool_executions": 0, "efficacy": "NOT_RUN"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--source", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("validate")
    check.add_argument("--packet", type=Path, required=True)
    check.add_argument("--packet-hash", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(Source.from_record(json.loads(args.source.read_bytes())), args.output)
    else:
        result = validate(args.packet, args.packet_hash)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
