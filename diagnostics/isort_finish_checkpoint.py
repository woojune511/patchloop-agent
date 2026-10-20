"""I4 removes only the latest ready-state finish advice; I3 retention stays fixed."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics import isort_retention_checkpoint as baseline
from diagnostics import observation_exposure as exposure
from diagnostics.decision_sampler import require
from diagnostics.uptake_checkpoint import read_bound as read_bound
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json

DESIGN = Path("C:/pt/isortfinishplan01/design-packet.json")
DESIGN_HASH = "sha256:9bab428334bcbec950e1013f754950f5ea1b01f92c3aa174d1660e42175f8250"
FIELD = baseline.FIELD
HISTORICAL_FIELD = baseline.HISTORICAL_FIELD
accepted_edits = baseline.accepted_edits
compare_first_request = baseline.compare_first_request
verify_feedback = baseline.verify_feedback
retain_observation = baseline.retain_observation

INTRO = (
    "All required visible checks pass on the current diff; submission is eligible, "
    "not proof of untested behavior. "
)
MESSAGE_PREFIXES = (
    {
        "before": INTRO + "Use run_probe if a concrete remaining public uncertainty could "
        "change the edit; otherwise use finish_task to submit. No extra experiment is required.",
        "after": INTRO + "Use run_probe if a concrete remaining public uncertainty could "
        "change the edit. No extra experiment is required.",
    },
    {
        "before": INTRO + "Use finish_task to submit; keep any remaining uncertainty explicit.",
        "after": INTRO + "Keep any remaining uncertainty explicit.",
    },
)


def load_design(path=DESIGN):
    packet = json.loads(read_bound({"path": str(path), "content_hash": DESIGN_HASH}))
    plan = json.loads(read_bound(packet["plan"]))
    prior, source, feedback = baseline.load_design()
    for key in (
        "limits_and_criteria",
        "retention_policy",
        "static_parity",
        "bindings",
        "observed_candidate_diff",
        "historical_observation",
        "treatment_policy",
    ):
        read_bound(plan[key])
    for ref in json.loads(read_bound(plan["bindings"]))["files"]:
        read_bound(ref)
    for key in (
        "caps",
        "inheritance",
        "feedback",
        "grading",
        "cap_application",
        "terminal_public_oracle",
        "model",
        "reasoning_effort",
        "service_tier",
        "cost_basis",
        "credential_file",
        "task_path",
        "runtime_hash",
        "retention_policy",
        "observed_candidate_diff",
        "historical_observation",
    ):
        require(plan[key] == prior[key], "non-treatment design changed")
    require(plan["row"] == "I4" and plan["repeat"] == 1, "frozen row changed")
    policy = json.loads(read_bound(plan["treatment_policy"]))
    require(policy["message_prefixes"] == list(MESSAGE_PREFIXES), "advice literals changed")
    require(
        policy["next_action"] == {"before": {"tool": "finish_task"}, "after": None},
        "next action treatment changed",
    )
    expected = expected_first_request(plan)
    original = baseline.expected_first_request(prior)
    old_guidance = json.loads(original["input"][-1]["content"])["state"]["completion_guidance"]
    require(
        all(old_guidance[k] == v for k, v in policy["first_input_required"].items()),
        "first input no longer has the frozen ready recommendation",
    )
    require(
        expected == {**original, "input": remove_finish_advice(original["input"])},
        "first preview changed",
    )
    seed = json.loads(read_bound(plan["observed_candidate_diff"]))
    require(
        seed == json.loads(expected["input"][-1]["content"])["state"]["current_diff"],
        "observed patch binding changed",
    )
    require(
        json.loads(read_bound(plan["historical_observation"]))
        == {"observed_candidate_diff": seed, "observation": feedback},
        "historical packet changed",
    )
    return plan, source, feedback


def expected_first_request(plan):
    parity = json.loads(read_bound(plan["static_parity"]))
    return json.loads(read_bound(parity["first_request_preview"]))["request"]


def remove_finish_advice(items):
    """Subtract the two frozen advice fields; preserve eligibility and all other bytes."""
    result = copy.deepcopy(items)
    view = json.loads(result[-1]["content"])
    require(view["kind"] == "harness_current_state", "missing current public state")
    guidance = view["state"]["completion_guidance"]
    if guidance["stage"] != "ready_to_submit":
        return result
    require(guidance["next_action"] == {"tool": "finish_task"}, "unknown ready next action")
    matches = [p for p in MESSAGE_PREFIXES if guidance["message"].startswith(p["before"])]
    require(len(matches) == 1, "unknown ready message form")
    prefix = matches[0]
    guidance["message"] = prefix["after"] + guidance["message"][len(prefix["before"]) :]
    guidance["next_action"] = None
    result[-1]["content"] = canonical_json(view)
    return result


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
    branch.observed_candidate_diff = copy.deepcopy(
        json.loads(expected_request["input"][-1]["content"])["state"]["current_diff"]
    )
    branch.delivery_assemblies = {}
    branch.parent_actions, branch.parent_edits = counters.tool_actions, edits
    branch.row, branch.provider_free = {"cell": "I4"}, provider_free
    branch.journal.append(
        "isort_finish_checkpoint_restored",
        {
            "row": "I4",
            "cut_sequence": cut_sequence,
            "synthetic_transport": provider_free,
            "operator_feedback": branch.store.put_json(feedback).model_dump(mode="json"),
            "candidate_hash": feedback["observed_on_current_diff_hash"],
            "active_elapsed_ms": base_ms + int((clock() - started) * 1000),
            "new_seed_executions": 0,
        },
    )
    return branch
