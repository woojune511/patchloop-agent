"""Freshly funded continuation of an immutable, already executed probe boundary."""
from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics import checkpoint_comparison as live
from diagnostics import checkpoint_continuation as continuation
from diagnostics import expectation_review_continuation as guidance
from diagnostics.cleanup_information_checkpoint import ForkStore, restore_candidate
from diagnostics.closure_policy_sampler import REMOVED
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import disjoint
from diagnostics.post_edit_budget_checkpoint import project as fund
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import native_compaction, runner, segments
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import history_metadata
from patchloop.dev.cost import DevCostLedger, pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

RUN_ID = "run_dev_33068b6e257f423a"
TASK = "tasks/dev-train/original-toqito-1538/public.yaml"
EXTENSION = Path("C:/pt/analyses/time-extension-checkpoint-20260928-v1/packet.json")
IMPLEMENTATION = (
    "diagnostics/probe_boundary_collector.py", "diagnostics/checkpoint_continuation.py",
    "diagnostics/checkpoint_comparison.py", "diagnostics/expectation_review_continuation.py",
    "diagnostics/cleanup_information_checkpoint.py", "diagnostics/declaration_checkpoint.py",
    "diagnostics/post_edit_budget_checkpoint.py", ".agent/selected-probe-continuation.md",
    "diagnostics/closure_policy_sampler.py",
)


def load(root):
    journal = DevJournal(root, RUN_ID)
    events, envelope = journal.events(), journal.load_envelope()
    receipt = json.loads((root / "prepared-boundary.json").read_bytes())
    require(envelope.runtime_hash == runtime_content_hash(), "runtime changed")
    require(journal.terminal() is None and journal.unresolved_provider_call() is None
            and journal.unresolved_input_count() is None, "boundary is not settled and open")
    boundary = next(e["payload"] for e in reversed(events)
                    if e["event_type"] == "model_input_prepared")
    require(boundary == receipt["boundary"], "prepared boundary changed")
    reader = ForkStore(root, events)
    bundle = json.loads(reader.read_bytes(Artifact.model_validate(boundary["artifact"])))
    require(sha256_json(bundle["request"]) == receipt["next_request_hash"],
            "request identity changed")
    audits = [e["payload"]["audit"] for e in events
              if e["event_type"] == "diagnostic_prepared_delivery_verified"]
    require(len(audits) == 1, "unique delivery audit required")
    audit = json.loads(reader.read_bytes(Artifact.model_validate(audits[0])))
    require(audit["input_verified"]["verified"] and audit["error_visible"]
            and audit["input_verified"]["input_hash"] == bundle["turn"]["model_input_hash"],
            "delivery audit does not bind this input")
    runner._validate_recorded_continuations(events, reader)
    return SimpleNamespace(journal=journal, events=events, envelope=envelope,
                           bundle=bundle, reader=reader, receipt=receipt)


def controls(source_root, env_file, result_root, new_cap_usd):
    source = load(source_root)
    cap = usd_to_nanos(new_cap_usd)
    require(cap > 0, "positive cap required")
    require(sha256_bytes(str(env_file.resolve()).encode())
            == source.envelope.credential_file_path_hash, "credential path changed")
    disjoint(result_root.resolve(), (repository_root(), source_root.resolve(), EXTENSION.parent))
    task_dir, package = runner._resolve_task_file(repository_root() / TASK)
    require(package.public.split == "dev-train"
            and package.public_spec_hash == source.envelope.public_spec_hash
            and package.task_content_hash == source.envelope.task_content_hash,
            "task package changed")
    selected = fund(source.bundle["request"], cap)
    return {"schema": "selected-probe-funded-v1", "official": False,
            "paid_execution_authorized": False, "repeat": 1,
            "source_root": str(source_root.resolve()),
            "source_journal_hash": sha256_bytes(source.journal.path.read_bytes()),
            "source_envelope_hash": sha256_json(source.envelope.model_dump(mode="json")),
            "source_receipt_hash": sha256_json(source.receipt),
            "packet": str(EXTENSION), "packet_hash": sha256_bytes(EXTENSION.read_bytes()),
            "task": str((repository_root() / TASK).resolve()),
            "model": source.envelope.model, "reasoning_effort": source.envelope.reasoning_effort,
            "max_output_tokens": source.envelope.max_output_tokens,
            "env_file": str(env_file.resolve()), "result_root": str(result_root.resolve()),
            "new_cap_nanos": cap, "first_request_hash": sha256_json(selected),
            "remaining_budget": json.loads(selected["input"][-1]["content"])["state"][
                "remaining_budget"], "sdk_retries": 0, "automatic_resume": False,
            "runtime_hash": source.envelope.runtime_hash,
            "implementation": {p: sha256_bytes((repository_root() / p).read_bytes())
                               for p in IMPLEMENTATION}}


def restore(plan, output):
    """Copy immutable evidence and replay accepted edits, never historical tools."""
    source = load(Path(plan["source_root"]))
    require(sha256_bytes(source.journal.path.read_bytes()) == plan["source_journal_hash"],
            "source journal changed")
    disjoint(output.resolve(), (repository_root(), Path(plan["source_root"]).resolve()))
    output.mkdir()
    store = ArtifactStore(output / "artifacts")
    # Sampler provenance has external artifact links, not runtime continuation data.
    # Preserve those journal bytes without treating links as locally owned CAS.
    provenance = {"diagnostic_saved_response_replay", "diagnostic_probe_boundary_captured"}
    runtime_events = [e for e in source.events if e["event_type"] not in provenance]
    references, pending = {}, list(continuation._artifacts(runtime_events))
    while pending:
        ref = pending.pop()
        key = sha256_json(ref.model_dump(mode="json"))
        if key in references:
            continue
        raw = source.reader.read_bytes(ref)
        copied = store.put_bytes(raw, ref.media_type)
        references[key] = (ref.model_dump(mode="json"), copied.model_dump(mode="json"))
        if ref.media_type.startswith("application/json"):
            pending.extend(continuation._artifacts(json.loads(raw)))
    journal = DevJournal(output, RUN_ID)
    with journal.path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("".join(canonical_json(e) + "\n" for e in source.events))
    envelope = source.envelope
    journal.write_envelope(envelope)
    journal.append("diagnostic_checkpoint_fork", {
        "official": False, "artifact_references": references,
        "source_journal_hash": plan["source_journal_hash"],
        "active_elapsed_ms": source.journal.latest_active_elapsed_ms(),
        "historical_execution_is_not_new_execution": True})
    task_dir, package = runner._resolve_task_file(Path(plan["task"]))
    manager = WorkspaceManager(repository_root() / "fixtures/repositories", output / "workspaces",
                               prepared_source=Path(envelope.prepared_source_path),
                               prepared_source_hash=envelope.prepared_source_hash)
    workspace = manager.create(RUN_ID, package.public.repository.url,
                               package.public.repository.base_commit,
                               deadline=ExecutionDeadline.from_remaining(120))
    accepted = {e["payload"]["action_id"] for e in source.events
                if e["event_type"] == "action_finished"
                and e["payload"]["result"]["tool"] == "replace_text"
                and e["payload"]["result"]["error_code"] is None}
    for event in source.events:
        if event["event_type"] == "action_started" and event["payload"]["action_id"] in accepted:
            restore_candidate(workspace, event["payload"])
    runner._validate_resumed_workspace(workspace, journal)
    selected = fund(source.bundle["request"], plan["new_cap_nanos"])
    require(sha256_json(selected) == plan["first_request_hash"], "funded input changed")
    cost = json.loads(selected["input"][-1]["content"])["state"]["remaining_budget"]["cost"]
    extra = sum(e["payload"]["extra_seconds"] for e in source.events
                if e["event_type"] == "diagnostic_time_extended")
    request = DevRunRequest(
        provider="openai", task=Path(plan["task"]), env_file=output / "NO_CREDENTIAL_FILE",
        state_root=output, resume_run_id=RUN_ID,
        max_cost_usd=Decimal(cost["invocation_cap"]) / 10**9,
        limits=envelope.limits.model_copy(update={
            "wall_time_seconds": envelope.limits.wall_time_seconds + extra}),
        prepared_source=manager.prepared_source,
        prepared_probe_dependencies=Path(envelope.prepared_probe_dependencies_path),
        enable_probes=True,
        **{k: getattr(envelope, k) for k in (
            "model", "reasoning_effort", "max_output_tokens", "repair_recheck",
            "repair_inspection_policy", "planning_policy", "probe_policy", "context_policy",
            "segment_boundary_policy", "completion_cost_policy")})
    pricing = pricing_for_model(envelope.model)
    ledger = DevCostLedger(request.max_cost_usd, pricing)
    ledger.restore_settled_usage(
        journal.provider_usage(), base_spent_nanos=envelope.cost_start_nanos)
    require(ledger.spent_nanos == cost["settled_usage"]
            and ledger.remaining_nanos == plan["new_cap_nanos"], "funding mismatch")
    journal.append("diagnostic_budget_allocated", {
        "historical_spent_nanos": ledger.spent_nanos, "new_cap_nanos": plan["new_cap_nanos"],
        "effective_cap_nanos": ledger.cap_nanos, "original_unused_allocation_reopened": False})
    bundle = copy.deepcopy(source.bundle)
    bundle["request"] = selected
    turn = bundle["turn"]
    turn["model_input_artifact"] = native_compaction.put_json(store, selected["input"])
    turn["model_input_hash"] = turn["model_input_artifact"]["content_hash"]
    turn["native_history"] = history_metadata(selected["input"], context_policy="segmented-v1")
    turn["context_request_sizes"] = segments.request_sizes(selected)
    canonical = json.loads(source.reader.read_bytes(
        Artifact.model_validate(turn["context_artifact"])))
    canonical["remaining_budget"]["cost"] = cost
    turn["context_artifact"] = native_compaction.put_json(store, canonical)
    turn["context_hash"] = turn["context_artifact"]["content_hash"]
    journal.append("model_input_prepared", {
        "boundary_id": turn["turn_id"], "cursor": native_compaction.cursor(journal),
        "artifact": native_compaction.put_json(store, bundle),
        "request_hash": sha256_json(selected)})
    return SimpleNamespace(
        root=output, store=store, journal=journal, references=references,
        envelope=envelope, request=request, package=package, task_dir=task_dir,
        ledger=ledger, pricing=pricing, packet=json.loads(EXTENSION.read_bytes()),
        selected=selected, original=selected, source_request=source.bundle["request"],
        inherited_events=len(source.events), initial_spent_nanos=ledger.spent_nanos)


def prepare(source_root, env_file, result_root, output, new_cap_usd):
    plan = controls(source_root, env_file, result_root, new_cap_usd)
    disjoint(output.resolve(), (repository_root(), source_root.resolve(), result_root.resolve()))
    runner._require_tracked_clean_paths(repository_root(), list(IMPLEMENTATION))
    output.mkdir()
    raw = (canonical_json(plan) + "\n").encode()
    (output / "manifest.json").write_bytes(raw)
    preflight = live.check_environment(EXTENSION, plan["packet_hash"], env_file)
    (output / "preflight.json").write_text(canonical_json(preflight), encoding="utf-8")
    return {"manifest_hash": sha256_bytes(raw), "plan": plan, "preflight": preflight}


@contextmanager
def inputs(branch):
    """Validate the exact inherited B2 overlay when the runner revisits its parent."""
    with continuation.inherited_reads(branch):
        parent = next(e["payload"] for e in reversed(branch.journal.events())
                      if e["event_type"] == "turn_started")
        old = json.loads(branch.store.read_bytes(Artifact.model_validate(
            parent["model_input_artifact"])))
    restored = branch.source_request["input"][0]
    require(old[0]["content"] == restored["content"].replace(REMOVED, "", 1),
            "inherited system overlay changed")
    original = segments.validate_input_binding

    def validate(items, binding, store):
        if items == old:
            items = copy.deepcopy(items)
            items[0] = copy.deepcopy(restored)
        return original(items, binding, store)

    with guidance.inputs(branch), patch.object(segments, "validate_input_binding", validate):
        yield


def collect(manifest_path, approved_hash, approved_cap_usd):
    raw = manifest_path.read_bytes()
    require(sha256_bytes(raw) == approved_hash, "approved manifest hash differs")
    plan = json.loads(raw)
    source, env, root = map(Path, (plan["source_root"], plan["env_file"], plan["result_root"]))
    require(plan == controls(source, env, root, approved_cap_usd), "manifest controls changed")
    runner._require_tracked_clean_paths(repository_root(), list(IMPLEMENTATION))
    root.mkdir()  # Single use, including failed preflight or uncertain transport.
    journal, store = DevJournal(root, "run_dev_probefollowup"), ArtifactStore(root / "artifacts")
    ledger = DevCostLedger(approved_cap_usd, pricing_for_model(plan["model"]))
    with journal.execution_lock():
        journal.append("continuation_authorized", {"manifest_hash": approved_hash, "plan": plan})
        preflight = live.check_environment(EXTENSION, plan["packet_hash"], env)
        journal.append("environment_checked", preflight)
        row, branch = {"status": "NOT_RUN", "billing_known": True}, None
        if preflight["status"] == "READY":
            try:
                branch = restore(plan, root / "B2")
                branch.request = branch.request.model_copy(update={"env_file": env})
                with inputs(branch):
                    row = live.run_branch(branch, ledger, journal, store, "B2")
            except Exception as exc:
                known = branch is None or runner._provider_usage_failure(branch.journal) is None
                row = {"status": "COLLECTOR_FAILED", "error_type": type(exc).__name__,
                       "billing_known": known, "stop_remaining": True}
        receipt = {"official": False, "manifest_hash": approved_hash, "row": row,
                   "preflight_status": preflight["status"],
                   "new_cost_nanos": ledger.spent_nanos if row["billing_known"] else None,
                   "recorded_new_cost_nanos": ledger.spent_nanos,
                   "source_billing_remains_unknown": True, "historical_allocations_reopened": False,
                   "fresh_solve": False, "efficacy_claim": "NOT_ESTABLISHED"}
        journal.append("continuation_finished", receipt)
        (root / "result.json").write_text(canonical_json(receipt), encoding="utf-8")
    return receipt
