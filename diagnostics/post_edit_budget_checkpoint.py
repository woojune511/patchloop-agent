"""Unhinted first-post-edit continuation; fresh funds, unchanged solving state."""
from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import yaml

from diagnostics.cleanup_information_checkpoint import ForkStore, restore_candidate  # noqa: F401
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from diagnostics.segmented_input_audit import verify_turn
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, PublicTask
from patchloop.dev import runner
from patchloop.dev.cost import usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "post-edit-budget-checkpoint-v1"
IMPLEMENTATION = (
    "diagnostics/post_edit_budget_checkpoint.py",
    "diagnostics/post_edit_budget_continuation.py",
    "diagnostics/checkpoint_continuation.py",
    "diagnostics/checkpoint_comparison.py",
    "diagnostics/cleanup_information_checkpoint.py",
    "diagnostics/declaration_checkpoint.py",
    "diagnostics/segmented_input_audit.py",
    ".agent/post-edit-budget-continuation.md",
)


def load(source: Source):
    path = source.root / "runs" / f"{source.run_id}.jsonl"
    for p, digest in ((path, source.journal_hash),
                      (path.with_suffix(".envelope.json"), source.envelope_hash),
                      (source.public_path, source.public_hash)):
        require(p.is_file() and sha256_bytes(p.read_bytes()) == digest, "source identity changed")
    journal = DevJournal(source.root, source.run_id)
    events, envelope = journal.events(), journal.load_envelope()
    require(envelope.runtime_hash == runtime_content_hash(), "source runtime changed")
    require(envelope.provider == "openai" and envelope.context_policy == "segmented-v1"
            and envelope.completion_cost_policy == "per-call-v1",
            "OpenAI segmented per-call checkpoint required")
    public = PublicTask.model_validate(yaml.safe_load(
        source.public_path.read_text(encoding="utf-8")))
    require(public.split == "dev-train" and public.task_id == envelope.task_id
            and public.task_version == envelope.task_version, "public task identity changed")
    accepted = next(e for e in events if e["event_type"] == "action_finished"
                    and e["payload"]["result"]["tool"] == "replace_text"
                    and e["payload"]["result"]["error_code"] is None)
    mutation = next(e["payload"] for e in events if e["event_type"] == "action_started"
                    and e["payload"]["action_id"] == accepted["payload"]["action_id"])
    result = accepted["payload"]["result"]
    require(result["input_hash"] == mutation["input_hash"]
            and result["output"]["mutation"]["diff_hash"]
            == mutation["mutation_expected_worktree_diff_hash"], "mutation binding changed")
    start = next(e for e in events if e["event_type"] == "turn_started"
                 and e["sequence"] > accepted["sequence"])
    cutoff = max(e["sequence"] for e in events if e["event_type"] == "tool_batch_finished"
                 and e["sequence"] < start["sequence"])
    cutoff = max([cutoff] + [e["sequence"] for e in events
                            if e["event_type"] == "context_segment_started"
                            and cutoff < e["sequence"] < start["sequence"]])
    prefix = [e for e in events if e["sequence"] <= cutoff]
    mutations = [e for e in prefix if e["event_type"] == "action_started"
                 and e["payload"]["tool"] == "replace_text"]
    require(len(mutations) == 1, "exactly one historical mutation required")
    require(not any(e["event_type"] == "action_started" and e["sequence"] > accepted["sequence"]
                    for e in prefix), "checkpoint is not immediately after edit")
    view = SimpleNamespace(events=lambda: prefix)
    require(DevJournal.unresolved_provider_call(view) is None
            and DevJournal.unresolved_input_count(view) is None, "uncertain source calls")
    usage = [e["payload"] for e in prefix if e["event_type"] == "provider_call_finished"]
    require(usage and all(type(u.get("cost_nanos")) is int and u["cost_nanos"] >= 0
                         and not u.get("error_code") for u in usage), "uncertain source billing")
    store = ForkStore(source.root, prefix)
    runner._validate_recorded_continuations(prefix, store)
    boundary = start["payload"]["prepared_input"]
    bundle = json.loads(store.read_bytes(Artifact.model_validate(boundary["artifact"])))
    request = bundle["request"]
    require(sha256_json(request) == boundary["request_hash"], "prepared input changed")
    verified = verify_turn(start, events, store, actual_input=request["input"])
    require(request["model"] == envelope.model
            and request["reasoning"] == {"effort": envelope.reasoning_effort}
            and request["max_output_tokens"] == envelope.max_output_tokens,
            "checkpoint model settings changed")
    state = json.loads(request["input"][-1]["content"])["state"]
    context = json.loads(store.read_bytes(Artifact.model_validate(
        start["payload"]["context_artifact"])))
    require(context["public_task"] == public.model_dump(mode="json"), "public source mismatch")
    require(state["current_diff"]["patch_hash"] == mutation["mutation_expected_worktree_diff_hash"],
            "candidate differs from checkpoint")
    spent = envelope.cost_start_nanos + sum(u["cost_nanos"] for u in usage)
    require(state["remaining_budget"]["cost"]["settled_usage"] == spent,
            "historical settled cost changed")
    return SimpleNamespace(request=request, store=store, source=source, mutation=mutation, receipt={
        "source_turn_id": start["payload"]["turn_id"],
        "source_mutation_action_id": mutation["action_id"],
        "source_prefix_hash": prefix[-1]["event_hash"], "cutoff_sequence": cutoff,
        "source_projection": verified, "historical_cost_nanos_before_boundary": spent,
        "remaining_budget": state["remaining_budget"],
        "candidate_diff_hash": mutation["mutation_expected_worktree_diff_hash"],
    })


def project(request, new_cap_nanos):
    require(type(new_cap_nanos) is int and new_cap_nanos > 0, "positive new cap required")
    selected = copy.deepcopy(request)
    view = json.loads(selected["input"][-1]["content"])
    cost = view["state"]["remaining_budget"]["cost"]
    cost["invocation_cap"] = cost["settled_usage"] + new_cap_nanos
    cost["remaining"] = new_cap_nanos
    selected["input"][-1]["content"] = canonical_json(view)
    return selected


def observation(packet):
    return None


def implementation_hashes():
    return {p: sha256_bytes((repository_root() / p).read_bytes()) for p in IMPLEMENTATION}


def prepare(source, output: Path, new_cap_usd: Decimal):
    disjoint(output.resolve(), (repository_root(), source.root, source.public_path.parent))
    loaded = load(source)
    cap = usd_to_nanos(new_cap_usd)
    selected = project(loaded.request, cap)
    packet = {"schema": SCHEMA, "official": False, "paid_execution_authorized": False,
              "source": source.record(), "checkpoint": loaded.receipt, "new_cap_nanos": cap,
              "runtime_hash": runtime_content_hash(),
              "implementation_hashes": implementation_hashes(),
              "original_request_hash": sha256_json(loaded.request),
              "selected_request_hash": sha256_json(selected)}
    output.mkdir()
    store = ArtifactStore(output / "artifacts")
    packet["request"] = store.put_json(selected).model_dump(mode="json")
    raw = (canonical_json(packet) + "\n").encode()
    (output / "packet.json").write_bytes(raw)
    digest = sha256_bytes(raw)
    DevJournal(output, "run_dev_posteditpreparation").append(
        "diagnostic_checkpoint_prepared", {"packet_hash": digest, "model_calls": 0})
    return {"packet": str(output / "packet.json"), "packet_hash": digest}


def validate(path, digest):
    require(sha256_bytes(path.read_bytes()) == digest, "packet identity changed")
    packet = json.loads(path.read_bytes())
    require(packet["schema"] == SCHEMA and packet["paid_execution_authorized"] is False
            and packet["runtime_hash"] == runtime_content_hash()
            and packet["implementation_hashes"] == implementation_hashes(),
            "checkpoint implementation changed")
    loaded = load(Source.from_record(packet["source"]))
    selected = project(loaded.request, packet["new_cap_nanos"])
    require(loaded.receipt == packet["checkpoint"]
            and sha256_json(loaded.request) == packet["original_request_hash"]
            and sha256_json(selected) == packet["selected_request_hash"], "checkpoint changed")
    actual = json.loads(ArtifactStore(path.parent / "artifacts").read_bytes(
        Artifact.model_validate(packet["request"])))
    require(actual == selected, "selected input changed")
    events = DevJournal(path.parent, "run_dev_posteditpreparation").events()
    require(len(events) == 1 and events[0]["payload"]["packet_hash"] == digest,
            "preparation binding changed")
    return {"verified": True, "model_calls": 0}
