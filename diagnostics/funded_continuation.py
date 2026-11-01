"""Separately funded continuation rows with immutable parents and shared admission.

The caller freezes a manifest and obtains a new invocation-wide authorization.
An outer fresh request reserves only NEW funds; a saved row restores its settled
public checkpoint under a new envelope. Historical UNKNOWN usage stays historical.
"""
from __future__ import annotations

import json
from pathlib import Path
from time import monotonic
from types import SimpleNamespace

from diagnostics import observation_comparison as live
from diagnostics import observation_exposure as exposure
from diagnostics import parallel_dev_batch as parallel
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source
from patchloop.artifacts import ArtifactStore
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.cost import DevCostLedger, pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.util import sha256_bytes


def saved_checkpoint(state_root: Path, run_id: str, public_path: Path):
    """Select the latest decision boundary without importing later model answers."""
    journal = DevJournal(state_root, run_id)
    events, envelope = journal.events(), journal.load_envelope()
    require(envelope.split == "dev-train" and envelope.provider == "openai",
            "OpenAI dev-train parent required")
    require(envelope.cost_start_nanos == 0, "only original batch parents are supported")
    terminal = journal.terminal()
    require(terminal is None or terminal["payload"]["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN",
            "only interrupted, unevaluated parents may continue")
    endpoints = {"solver_finished", "evaluator_started", "evaluator_finished"}
    require(not any(e["event_type"] in endpoints for e in events),
            "submitted or evaluated parents cannot continue")
    cuts = [e for e in events if e["event_type"] == "model_input_prepared"]
    require(bool(cuts), "no prepared decision boundary")
    cut = cuts[-1]
    prefix = [e for e in events if e["sequence"] < cut["sequence"]]
    tail = [e for e in events if e["sequence"] >= cut["sequence"]]
    view = SimpleNamespace(events=lambda: prefix)
    require(DevJournal.unresolved_provider_call(view) is None
            and DevJournal.unresolved_input_count(view) is None,
            "checkpoint prefix has uncertain usage")
    require(not any(e["event_type"] in {"action_started", "tool_batch_started",
                                       "provider_call_finished"} for e in tail),
            "checkpoint would discard executed actions or a received decision")
    require(journal.unresolved_input_count() is None, "parent count remains uncertain")
    pending = journal.unresolved_provider_call()
    starts = [e["payload"] for e in tail if e["event_type"] == "provider_call_started"]
    require(len(starts) <= 1, "multiple excluded generation attempts")
    if starts:
        require(pending is not None and pending["call_id"] == starts[0]["call_id"]
                and terminal is not None, "excluded generation is not the recorded uncertainty")
        require(type(starts[0].get("reserved_cost_nanos")) is int
                and starts[0]["reserved_cost_nanos"] > 0, "missing uncertain cost reservation")
    else:
        require(pending is None and terminal is None, "unexpected parent interruption")
    return {
        "source": Source(
            state_root.resolve(), run_id, sha256_bytes(journal.path.read_bytes()),
            sha256_bytes(journal.envelope_path.read_bytes()), public_path.resolve(),
            sha256_bytes(public_path.read_bytes()),
        ).record(),
        "cut_sequence": cut["sequence"],
        "parent_active_elapsed_ms": journal.latest_active_elapsed_ms(),
        "inherited_settled_cost_nanos": sum(
            e["payload"]["cost_nanos"] for e in prefix
            if e["event_type"] == "provider_call_finished"
        ),
        "excluded_model_calls": len(starts),
        "parent_billing_known": pending is None,
        "excluded_generation": ({
            key: starts[0][key] for key in ("call_id", "request_hash", "reserved_cost_nanos")
        } if starts else None),
        "historical_unknown_resolved": False,
        "fresh_solve": False,
    }


def validate_saved_row(row):
    """Bind every inherited resource and uncertainty fact to unchanged parent bytes."""
    saved = row["checkpoint"]
    source = Source.from_record(saved["source"])
    require(saved_checkpoint(source.root, source.run_id, source.public_path) == saved,
            "parent checkpoint changed")
    request = DevRunRequest.model_validate(row["request"])
    old = DevJournal(source.root, source.run_id).load_envelope()
    require(request.task.resolve() == source.public_path.resolve(), "task changed")
    for key in (
        "model", "reasoning_effort", "max_output_tokens", "rate_limit_policy",
        "repair_recheck", "repair_inspection_policy", "planning_policy", "probe_policy",
        "context_policy", "segment_boundary_policy", "completion_cost_policy",
        "retained_source_chars", "evaluation_reserve_seconds", "probe_recheck",
        "max_correction_output_tokens", "reproduction_acquisition", "history_search_policy",
        "agent_policy", "verification_policy",
    ):
        require(getattr(request, key) == getattr(old, key), f"continuation {key} changed")
    require(sha256_bytes(str(request.env_file.resolve()).encode()) == old.credential_file_path_hash,
            "credential path changed")
    require(request.limits.wall_time_seconds == 3600 > old.limits.wall_time_seconds,
            "this continuation panel requires a 3600-second cumulative limit")
    require(request.limits.model_dump(exclude={"wall_time_seconds"})
            == old.limits.model_dump(exclude={"wall_time_seconds"}),
            "only time and new funds may increase")
    require(request.max_cost_usd is not None and request.max_cost_usd > 0,
            "new positive row allocation required")
    return request


def restore_row(row, output: Path, *, offline=False):
    request = validate_saved_row(row)
    saved = row["checkpoint"]
    return exposure._fork(
        Source.from_record(saved["source"]), saved["cut_sequence"], output, "B",
        new_cap_usd=request.max_cost_usd,
        mode="offline-scripted-only" if offline else "funded-observation",
        env_file=output / "NO_CREDENTIAL_FILE" if offline else request.env_file,
        preserve_parent_configuration=True,
        total_wall_time_seconds=request.limits.wall_time_seconds,
    )


def initialize_worker(stop, admission):
    parallel.initialize_worker(stop, admission)
    # Every newly generated event in a branch uses the same process-shared lock.
    exposure.DevJournal = parallel.CoordinatedJournal
    live.OpenAIResponsesAdapter = parallel.CoordinatedAdapter


def new_accounting(snapshot, inherited_cost):
    """Subtract verified settled history; never turn unknown new usage into zero."""
    value = dict(snapshot)
    total = value.get("cost_nanos")
    require(total is None or total >= inherited_cost, "inherited accounting regressed")
    value["historical_settled_cost_nanos"] = inherited_cost
    value["known_new_cost_nanos"] = None if total is None else total - inherited_cost
    value["cost_nanos"] = value["known_new_cost_nanos"]
    return value


def solve_row(serialized, *, manifest_hash):
    """Execute one new allocation; the manifest is frozen by the outer launcher."""
    request = DevRunRequest.model_validate(serialized)
    raw = (request.state_root.parent / "manifest.json").read_bytes()
    require(sha256_bytes(raw) == manifest_hash, "approved continuation manifest changed")
    plan = json.loads(raw)
    row = next(r for r in plan["rows"] if r["request"] == serialized)
    if row["kind"] == "fresh":
        return parallel.solve_row(serialized)
    require(row["kind"] == "continuation", "unknown row kind")
    started = monotonic()
    branch, outcome, error = None, None, None
    try:
        if parallel._STOP.is_set():
            raise parallel.BatchStopped("batch stopped before checkpoint restoration")
        require(not request.state_root.exists(), "continuation output already used")
        branch = restore_row(row, request.state_root)
        group = DevCostLedger(request.max_cost_usd, pricing_for_model(request.model))
        operator = DevJournal(request.state_root / "operator", "run_dev_fundedcontinuation")
        outcome = live.run_branch(
            branch, group, operator, ArtifactStore(request.state_root / "operator/artifacts"),
            str(row["task_index"]), row["first_request_hash"],
        )
        if outcome["stop_remaining"]:
            parallel.stop_workers()
    except BaseException as exc:
        parallel.stop_workers()
        error = type(exc).__name__
    snapshot = parallel.recover_usage(request.state_root)
    usage = new_accounting(snapshot, row["checkpoint"]["inherited_settled_cost_nanos"]
                           if snapshot.get("runs") else 0)
    ok = (outcome is not None and not outcome["stop_remaining"]
          and usage["billing_known"] and usage["counting_known"]
          and outcome["new_cost_nanos"] == usage["cost_nanos"]
          and 0 <= usage["cost_nanos"] <= usd_to_nanos(request.max_cost_usd))
    if not ok:
        parallel.stop_workers()
    result = None if outcome is None else {
        "runs": [outcome["result"]],
        "cost_nanos": usage["cost_nanos"] if usage["billing_known"] else None,
        "known_new_cost_nanos": usage["known_new_cost_nanos"],
        "stop_remaining": not ok, "historical_funds_reopened": False,
    }
    return {"result": result, "error_type": error, "accounting": usage, "ok": bool(ok),
            "elapsed_seconds": round(monotonic() - started, 3)}
