"""Exact OpenSandbox prefix and frozen plan-instruction treatment; no live calls."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics import observation_exposure as exposure
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source
from diagnostics.isort_uptake_checkpoint import accepted_edits
from diagnostics.uptake_checkpoint import read_bound
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json, sha256_json

DESIGN = Path("C:/pt/hostplan01/design-packet.json")
DESIGN_HASH = "sha256:1506043c2cdb6a58225e077b7f7177c4b849c3cc5e0d5a7534aa19e085a5d48a"


def load_design():
    packet = json.loads(read_bound({"path": str(DESIGN), "content_hash": DESIGN_HASH}))
    plan = json.loads(read_bound(packet["plan"]))
    for ref in packet.values():
        if isinstance(ref, dict) and "content_hash" in ref:
            read_bound(ref)
    bindings = json.loads(read_bound(plan["bindings"]))["files"]
    for ref in bindings:
        read_bound(ref)
    by_path = {str(Path(r["path"]).resolve()): r for r in bindings}
    seed = plan["source"]
    root = Path(seed["root"])
    journal = root / "runs" / f"{seed['run_id']}.jsonl"
    public = Path(plan["task_path"])
    source = Source(
        root,
        seed["run_id"],
        by_path[str(journal)]["content_hash"],
        by_path[str(journal.with_suffix(".envelope.json"))]["content_hash"],
        public,
        by_path[str(public)]["content_hash"],
    )
    require(plan["runtime_hash"] == runner._runtime_hash(), "frozen runtime changed")
    treatment = json.loads(read_bound(plan["treatment"]))
    systems = {a: read_bound(r).decode() for a, r in treatment["system_prompts"].items()}
    require(systems["A"].count(treatment["before"]) == 1, "ambiguous treatment anchor")
    require(
        systems["A"].replace(treatment["before"], treatment["after"]) == systems["B"],
        "non-treatment system text changed",
    )
    plan = {**plan, "systems": systems}
    return plan, source


def normalize_clock(request):
    """Only the displayed *current* remaining seconds may differ across branches."""
    result = copy.deepcopy(request)
    view = json.loads(result["input"][-1]["content"])
    require(view["kind"] == "harness_current_state", "missing latest state")
    view["state"]["remaining_budget"]["active_wall_time_seconds"] = "<actual remaining seconds>"
    result["input"][-1]["content"] = canonical_json(view)
    return result


def untreated(request, systems):
    result = copy.deepcopy(request)
    require(result["input"][0]["role"] == "system", "missing system message")
    require(result["input"][0]["content"] in systems.values(), "unfrozen system prompt")
    result["input"][0]["content"] = systems["A"]
    return result


def first_parity(left, right, systems):
    a, b = (normalize_clock(untreated(r, systems)) for r in (left, right))
    require(a == b, "A/B first requests differ beyond treatment and actual remaining seconds")
    return {
        "status": "PASS",
        "normalized_request_hash": sha256_json(a),
        "normalized_fields": ["latest.remaining_budget.active_wall_time_seconds"],
    }


def restore_branch(
    plan,
    source,
    output,
    arm,
    *,
    provider_free=True,
    credential_file=None,
    started=None,
    clock=monotonic,
    deadline=None,
):
    require(arm in {"A", "B"}, "fixed A/B arm required")
    started = clock() if started is None else started
    seed = plan["source"]
    bundle = json.loads(read_bound(seed["original_prepared"]))
    historical = DevJournal(source.root, source.run_id)
    old, events = historical.load_envelope(), historical.events()
    prefix = [e for e in events if e["sequence"] < seed["cut_prepared_sequence"]]
    require(prefix[-1]["event_hash"] == seed["prefix_head"], "checkpoint prefix changed")
    counters = runner._restore_counters(SimpleNamespace(events=lambda: prefix))
    require(
        (counters.model_calls, counters.tool_actions, accepted_edits(prefix))
        == (
            seed["prefix_counts"]["model"],
            seed["prefix_counts"]["tools"],
            seed["prefix_counts"]["edits"],
        ),
        "checkpoint usage changed",
    )
    require(
        bundle["turn"]["active_elapsed_ms"] == seed["base_active_elapsed_ms"],
        "inherited time changed",
    )
    solver_end = min(
        started + plan["caps"]["solver_seconds_per_row"],
        started + old.limits.wall_time_seconds - seed["base_active_elapsed_ms"] / 1000,
        deadline.expires_at if deadline else float("inf"),
    )
    row_end = min(started + 2400, deadline.expires_at if deadline else float("inf"))
    ExecutionDeadline(solver_end, clock).check()
    limits = old.limits.model_copy(update=plan["common_configuration"]["limits_totals_per_row"])

    def request(**kwargs):
        return DevRunRequest(
            **{
                **kwargs,
                "agent_policy": old.agent_policy,
                "limits": limits,
                "evaluation_reserve_seconds": 0,
            }
        )

    class PreparationDeadline:
        @staticmethod
        def from_remaining(seconds):
            return ExecutionDeadline(min(clock() + seconds, solver_end), clock)

    with (
        patch.object(exposure, "DevRunRequest", request),
        patch.object(exposure, "ExecutionDeadline", PreparationDeadline),
    ):
        branch = exposure._fork(
            source,
            seed["cut_prepared_sequence"],
            output,
            arm,
            new_cap_usd=Decimal("5.50"),
            mode="offline-scripted-only" if provider_free else "funded-observation",
            env_file=output / "NO_CREDENTIAL_FILE" if provider_free else credential_file,
            preserve_parent_configuration=True,
        )
    require(
        branch.envelope.probe_image_digest == old.probe_image_digest
        and branch.envelope.probe_dependencies == old.probe_dependencies,
        "inherited image/dependencies changed",
    )
    require(
        branch.initial_spent_nanos == int(Decimal(seed["prefix_settled_usd"]) * 10**9),
        "historical funds changed",
    )
    branch.plan, branch.selected = plan, bundle["request"]
    branch.solver_deadline = ExecutionDeadline(solver_end, clock)
    branch.row_deadline = ExecutionDeadline(row_end, clock)
    branch.started, branch.clock = started, clock
    branch.parent_actions, branch.parent_edits = counters.tool_actions, 0
    branch.row, branch.provider_free = {"cell": "O1-" + arm}, provider_free
    branch.deliveries, branch.dispatched = {}, []
    branch.solver_deadline.check()
    branch.journal.append(
        "host_plan_checkpoint_restored",
        {
            "row": branch.row["cell"],
            "prefix_head": seed["prefix_head"],
            "synthetic": provider_free,
            "seed_executions": 0,
            "historical_spent_nanos": branch.initial_spent_nanos,
            "solver_seconds_including_restoration": 1697,
            "whole_row_seconds": 2400,
        },
    )
    return branch


def verify_first(branch, request):
    def native(request):
        return [
            i
            for i in request["input"]
            if i.get("type") in {"reasoning", "function_call", "function_call_output"}
        ]

    require(native(request) == native(branch.selected), "historical native continuation changed")
    require(
        request["input"][1:3] == branch.selected["input"][1:3],
        "immutable initial task/state changed",
    )
    actual = reconstruct_state(request["input"], context_policy="segmented-v1")
    saved = reconstruct_state(branch.selected["input"], context_policy="segmented-v1")
    require(actual["working_plan"] == saved["working_plan"], "initial plan changed")
    require(actual["current_diff"] == saved["current_diff"], "initial candidate changed")
    require(
        actual["current_diff"]["patch_hash"] == branch.plan["source"]["empty_diff_hash"],
        "checkpoint candidate is not empty",
    )
    branch.first_request = copy.deepcopy(request)
