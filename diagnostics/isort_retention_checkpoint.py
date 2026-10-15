"""Frozen I3 data retention seam; no default runtime policy changes."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics import isort_table_checkpoint as baseline
from diagnostics import observation_exposure as exposure
from diagnostics.decision_sampler import require
from diagnostics.uptake_checkpoint import read_bound as read_bound
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import history_metadata, validate_model_input
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json, sha256_bytes

DESIGN = Path("C:/pt/isortretainplan01/design-packet.json")
DESIGN_HASH = "sha256:d43f3e998691a1b73c288217ee3480262dfa3a7f36eb409f91a774f6f11e5ee4"
FIELD = baseline.FIELD
HISTORICAL_FIELD = "historical_operator_public_observation"
accepted_edits = baseline.accepted_edits
compare_first_request = baseline.compare_first_request
verify_feedback = baseline.verify_feedback


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
    ):
        require(plan[key] == prior[key], "non-treatment design changed")
    require(plan["row"] == "I3" and plan["repeat"] == 1, "frozen row changed")
    expected = expected_first_request(plan)
    require(expected == baseline.expected_first_request(prior), "first preview changed")
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


def retain_observation(items, feedback, seed):
    """Change only the latest operator field; never rewrite native/history items."""
    result = copy.deepcopy(items)
    view = json.loads(result[-1]["content"])
    require(view["kind"] == "harness_current_state", "missing current public state")
    state = view["state"]
    require(FIELD not in state and HISTORICAL_FIELD not in state, "operator packet already present")
    require(
        not seed["truncated"]
        and sha256_bytes(seed["patch"].encode())
        == seed["patch_hash"]
        == feedback["observed_on_current_diff_hash"],
        "observed diff identity changed",
    )
    current = state["current_diff"]
    if current["patch_hash"] == seed["patch_hash"]:
        require(current == seed, "same-diff source bytes changed")
        field, value = FIELD, feedback
    else:
        field = HISTORICAL_FIELD
        value = {"observed_candidate_diff": seed, "observation": feedback}
    state[field] = copy.deepcopy(value)
    result[-1]["content"] = canonical_json(view)
    validate_model_input(
        result,
        history_metadata(result, context_policy="segmented-v1"),
        context_policy="segmented-v1",
    )
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
    branch.row, branch.provider_free = {"cell": "I3"}, provider_free
    branch.journal.append(
        "isort_retention_checkpoint_restored",
        {
            "row": "I3",
            "cut_sequence": cut_sequence,
            "synthetic_transport": provider_free,
            "operator_feedback": branch.store.put_json(feedback).model_dump(mode="json"),
            "candidate_hash": feedback["observed_on_current_diff_hash"],
            "active_elapsed_ms": base_ms + int((clock() - started) * 1000),
            "new_seed_executions": 0,
        },
    )
    return branch
