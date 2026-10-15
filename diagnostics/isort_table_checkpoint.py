"""Frozen I2 table delivery and first-request parity, with no target execution."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics import isort_uptake_checkpoint as baseline
from diagnostics import observation_exposure as exposure
from diagnostics.decision_sampler import require
from diagnostics.uptake_checkpoint import read_bound as read_bound
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json, sha256_json

DESIGN = Path("C:/pt/isorttableplan01/design-packet.json")
DESIGN_HASH = "sha256:50822a29c1c4235d1bbe56532691afe1bdf7cc95b84a59ee519dbde1f90c4da1"
FIELD = baseline.FIELD
accepted_edits = baseline.accepted_edits
COLUMNS = [
    "case_id",
    "expectation_basis",
    "expected_position",
    "base_observed_position",
    "current_observed_position",
    "base_position_preserved",
    "current_position_preserved",
]


def comparison_table(feedback):
    """Reproduce cells from the saved public observations, never from private results."""
    snapshots = feedback["snapshots"]
    require([s["label"] for s in snapshots] == ["base", "submitted"], "both receipts required")
    decoded = []
    for snapshot in snapshots:
        rows = [json.loads(line) for line in snapshot["receipt"]["stdout"].splitlines()]
        cases = [r for r in rows if r.get("stage") == "case_result"]
        require(
            [r["case_id"] for r in cases] == [c["case_id"] for c in feedback["cases"]],
            "diagnostic case order/coverage changed",
        )
        decoded.append(cases)
    require(
        [c["case_id"] for c in feedback["cases"]]
        == ["type_opening", "type_item", "plain_opening", "plain_item"],
        "four cases required",
    )
    table_rows = []
    for case, before, after in zip(feedback["cases"], *decoded, strict=True):
        for row in (before, after):
            require(
                row["input"] == case["input"]
                and row["expected_position"] == case["position"]
                and len(row["comments"]) == 1
                and row["comment_preserved"] is True
                and row["import_ast_preserved"] is True,
                "table source differs",
            )
            require(
                row["position_preserved"] is (row["comments"][0]["position"] == case["position"]),
                "position flag differs from saved location",
            )
        table_rows.append(
            [
                case["case_id"],
                case["expectation_basis"],
                case["position"],
                before["comments"][0]["position"],
                after["comments"][0]["position"],
                before["position_preserved"],
                after["position_preserved"],
            ]
        )
    return {"columns": COLUMNS, "rows": table_rows}


def load_design(path=DESIGN):
    packet = json.loads(read_bound({"path": str(path), "content_hash": DESIGN_HASH}))
    plan = json.loads(read_bound(packet["plan"]))
    original_plan, source, original = baseline.load_design()
    for key in (
        "limits_and_criteria",
        "static_parity",
        "bindings",
        "cap_application",
        "grading",
        "terminal_public_oracle",
        "original_feedback",
    ):
        read_bound(plan[key])
    bindings = json.loads(read_bound(plan["bindings"]))
    read_bound(bindings["nested_original_bindings"])
    for name, digest in bindings["input_hashes"].items():
        read_bound({"path": name, "content_hash": digest})
    require(runner._runtime_hash() == plan["runtime_hash"], "frozen runtime changed")
    for key in (
        "model",
        "reasoning_effort",
        "service_tier",
        "credential_file",
        "caps",
        "inheritance",
        "grading",
        "terminal_public_oracle",
    ):
        require(plan[key] == original_plan[key], "non-treatment design changed")
    feedback = json.loads(read_bound(plan["feedback"]))
    raw = copy.deepcopy(feedback)
    table = raw.pop("case_comparison")
    require(raw == original and table == comparison_table(original), "table-only treatment changed")
    expected_first_request(plan)  # Binds the actual saved I1 request and frozen static transform.
    return plan, source, feedback


def expected_first_request(plan):
    parity = json.loads(read_bound(plan["static_parity"]))
    request = json.loads(read_bound(parity["baseline_prepared_artifact"]))["request"]
    require(sha256_json(request) == parity["baseline_request_hash"], "saved I1 request changed")
    view = json.loads(request["input"][-1]["content"])
    require(
        view["state"][FIELD] == json.loads(read_bound(plan["original_feedback"])),
        "saved I1 operator packet changed",
    )
    view["state"][FIELD] = json.loads(read_bound(plan["feedback"]))
    request["input"][-1]["content"] = canonical_json(view)
    require(sha256_json(request) == parity["static_table_request_hash"], "static transform changed")
    return request


def verify_feedback(feedback, branch):
    baseline.verify_feedback(feedback, branch)
    require(feedback["case_comparison"] == comparison_table(feedback), "table cells changed")


def compare_first_request(request, expected):
    """Only the public active-time integer is normalized, never an actual deadline."""
    actual, reference = copy.deepcopy(request), copy.deepcopy(expected)
    av, rv = (json.loads(r["input"][-1]["content"]) for r in (actual, reference))
    times = [v["state"]["remaining_budget"]["active_wall_time_seconds"] for v in (av, rv)]
    require(all(type(t) is int and t >= 0 for t in times), "invalid public active time")
    av["state"]["remaining_budget"]["active_wall_time_seconds"] = times[1]
    actual["input"][-1]["content"] = canonical_json(av)
    require(actual == reference, "non-treatment first-input parity changed")
    return {
        "status": "PASS",
        "actual_active_seconds": times[0],
        "reference_active_seconds": times[1],
        "difference_seconds": times[0] - times[1],
        "request_hash": sha256_json(request),
        "reference_hash": sha256_json(expected),
        "normalized_request_hash": sha256_json(actual),
        "only_normalized": (
            "/request/input/13/content/state/remaining_budget/active_wall_time_seconds"
        ),
    }


def restore_branch(
    source,
    cut_sequence,
    feedback,
    output,
    *,
    provider_free=True,
    credential_file=None,
    started=None,
    clock=monotonic,
    deadline=None,
    expected_request=None,
):
    if expected_request is None:
        plan, _, _ = load_design()
        expected_request = expected_first_request(plan)
    started = clock() if started is None else started
    parent = DevJournal(source.root, source.run_id)
    events, old = parent.events(), parent.load_envelope()
    cut = next(e for e in events if e["sequence"] == cut_sequence)
    bundle = json.loads(
        ArtifactStore(source.root / "artifacts").read_bytes(
            Artifact.model_validate(cut["payload"]["artifact"])
        )
    )
    prefix = [e for e in events if e["sequence"] < cut_sequence]
    counters = runner._restore_counters(SimpleNamespace(events=lambda: prefix))
    base_ms, edits = bundle["turn"]["active_elapsed_ms"], accepted_edits(prefix)
    solver_end = started + min(281, old.limits.wall_time_seconds - base_ms / 1000)
    require(clock() < solver_end, "inherited solver time exhausted before restoration")
    limits = old.limits.model_copy(
        update={
            "max_model_calls": min(old.limits.max_model_calls, counters.model_calls + 6),
            "max_tool_actions": min(old.limits.max_tool_actions, counters.tool_actions + 18),
            "max_accepted_mutations": min(old.limits.max_accepted_mutations, edits + 2),
            "max_protocol_recoveries": 0,
        }
    )

    def request(**kwargs):
        return DevRunRequest(
            **{
                **kwargs,
                "agent_policy": old.agent_policy,
                "limits": limits,
                # Terminal assessment has separate 30/330s phase limits inside 720s.
                # Subtracting a 330s reserve from 281s would prevent all solver work.
                "evaluation_reserve_seconds": 0,
            }
        )

    class PreparationDeadline:
        @staticmethod
        def from_remaining(seconds):
            return ExecutionDeadline(
                min(clock() + seconds, solver_end, deadline.expires_at if deadline else solver_end),
                clock,
            )

    with (
        patch.object(exposure, "DevRunRequest", request),
        patch.object(exposure, "ExecutionDeadline", PreparationDeadline),
    ):
        branch = exposure._fork(
            source,
            cut_sequence,
            output,
            "B",
            new_cap_usd=Decimal("3.50"),
            mode="offline-scripted-only" if provider_free else "funded-observation",
            env_file=output / "NO_CREDENTIAL_FILE" if provider_free else credential_file,
            preserve_parent_configuration=True,
        )
    require(
        branch.envelope.probe_image_digest == old.probe_image_digest
        and branch.envelope.probe_dependencies == old.probe_dependencies,
        "inherited image/dependencies changed",
    )
    branch.solver_deadline = ExecutionDeadline(solver_end, clock)
    branch.solver_deadline.check()
    verify_feedback(feedback, branch)  # Current profile is bound by the new operator receipts.
    branch.feedback, branch.selected = feedback, bundle["request"]
    branch.expected_first_request = expected_request
    branch.parent_actions, branch.parent_edits = counters.tool_actions, edits
    branch.row, branch.provider_free = {"cell": "I2"}, provider_free
    branch.journal.append(
        "isort_table_checkpoint_restored",
        {
            "row": "I2",
            "cut_sequence": cut_sequence,
            "synthetic_transport": provider_free,
            "operator_feedback": branch.store.put_json(feedback).model_dump(mode="json"),
            "candidate_hash": feedback["observed_on_current_diff_hash"],
            "active_elapsed_ms": base_ms + int((clock() - started) * 1000),
            "new_seed_executions": 0,
        },
    )
    return branch
