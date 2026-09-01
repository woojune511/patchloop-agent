from __future__ import annotations

import copy

import pytest

from patchloop.agent.workflow_causal_plan_projection_activation import (
    project_activated_causal_plan_request,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    _arguments,
    _catalog,
    _task,
)
from patchloop.agent.workflow_plan_gate_liveness_successor import (
    EligiblePlanEvidenceCatalogV3,
    bind_recovered_plan_gate_pin,
    normalize_pinned_exploration_plan,
    project_pinned_evidence_catalog,
    project_pinned_exploration_plan_request,
    project_pinned_plan_gate_decision,
    project_plan_gate_readiness_snapshot,
)
from patchloop.agent.workflow_semantic_progress_successor import (
    WORKFLOW_POLICY_V15,
    WorkflowDecisionV3,
)
from patchloop.agent.workflow_successor_v2 import EligiblePlanEvidenceCatalogV2
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_json


def _catalog_v2(*, keep_source: bool = True) -> EligiblePlanEvidenceCatalogV2:
    source = _catalog(include_failed_check=False)
    items = (
        source.items
        if keep_source
        else tuple(item for item in source.items if item.kind != "source_read")
    )
    body = {
        **source.model_dump(mode="python", exclude={"schema_version", "content_hash", "items"}),
        "schema_version": "eligible-plan-evidence-catalog-v2",
        "items": tuple(item.model_dump(mode="python") for item in items),
        "required_trigger_status": "not_required",
        "required_trigger_event_sequence": None,
        "required_trigger_evidence_id": None,
        "model_visible_pinned_event_sequences": (),
        "unavailable_reason": None,
    }
    return EligiblePlanEvidenceCatalogV2.model_validate({**body, "content_hash": sha256_json(body)})


def _decision(
    *,
    target: str = "pre-mutation-exploration",
    allowed: tuple[str, ...] = ("search_files", "read_file", "record_work_plan"),
    recovery_used: bool = False,
    terminal_reason: str | None = None,
) -> WorkflowDecisionV3:
    body = {
        "schema_version": "lean-workflow-decision-v3",
        "runtime_policy_version": "lean-harness-v15",
        "policy_version": WORKFLOW_POLICY_V15,
        "target": target,
        "current_diff_hash": _catalog_v2().worktree_diff_hash,
        "expected_check_id": None,
        "allowed_tool_names": allowed,
        "information_actions_in_episode": 0,
        "fresh_current_read": False,
        "corrective_mutations_for_check": 0,
        "review_corrections_used": 0,
        "pre_mutation_actions_used": 4,
        "active_plan_hash": None,
        "plan_gate_id": "sha256:" + "4" * 64,
        "plan_admission_recovery_used": recovery_used,
        "plan_admission_recovery_remaining": 0 if recovery_used else 1,
        "required_trigger_evidence_id": None,
        "revision_trigger": None,
        "terminal_reason": terminal_reason,
        "configured_max_output_tokens": 12_288,
        "effective_max_output_tokens": 1 if target == "terminal" else 4_096,
        "reasoning_effort": "low",
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "provider_calls_authorized": False,
        "semantic_progress_state_hash": None,
        "semantic_reset_required": False,
        "required_prior_hypothesis_disposition": None,
    }
    return WorkflowDecisionV3.model_validate({**body, "content_hash": sha256_json(body)})


def _arguments_with_single_unknown() -> dict:
    arguments = _arguments()
    question = arguments.pop("unknowns")[0]
    arguments["exploration_state"] = {
        "boundary_coverage": {
            "ownership_boundary_span_ids": ["cspan:10:0"],
            "execution_boundary_span_ids": ["cspan:11:0"],
            "mutation_boundary_span_ids": ["cspan:10:0"],
        },
        "invariants": [
            {
                "subject": "Public lifecycle ownership",
                "claim": "Two current-source ranges jointly own the transition.",
                "evidence_source_span_ids": ["cspan:10:0", "cspan:11:0"],
            }
        ],
        "preservation_obligations": [
            {
                "public_requirement": "Preserve the later visible lifecycle step.",
                "expected_behavior": "Visible checks remain ordered after the edit.",
                "evidence_source_span_ids": ["cspan:11:0"],
            }
        ],
        "unknown_dispositions": [
            {
                "question": question,
                "disposition": "non_blocking",
                "explanation": "The bounded transition does not depend on this question.",
                "evidence_source_span_ids": ["cspan:11:0"],
            }
        ],
        "open_blocking_unknowns": [],
    }
    return arguments


def _request():
    catalog = project_pinned_evidence_catalog(base=_catalog_v2(), pin=None)
    base = project_activated_causal_plan_request(
        task=_task(),
        catalog=catalog,
        trigger="initial",
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
    )
    return project_pinned_exploration_plan_request(base)


def test_readiness_forces_initial_plan_and_survives_catalog_shrink() -> None:
    current = _catalog_v2()
    decision = _decision()
    readiness = project_plan_gate_readiness_snapshot(
        task=_task(),
        decision=decision,
        catalog=current,
    )
    assert readiness is not None
    forced = project_pinned_plan_gate_decision(
        decision=decision,
        readiness=readiness,
        pin=None,
    )
    assert forced.allowed_tool_names == ("record_work_plan",)

    pin = bind_recovered_plan_gate_pin(
        snapshot=readiness,
        source_model_event_sequence=20,
        source_request_artifact_hash="sha256:" + "a" * 64,
        source_request_body_hash="sha256:" + "b" * 64,
    )
    shrunk = project_pinned_evidence_catalog(base=_catalog_v2(keep_source=False), pin=pin)
    assert isinstance(shrunk, EligiblePlanEvidenceCatalogV3)
    assert {item.evidence_id for item in shrunk.items}.issuperset({"pev:10", "pev:11"})
    recovered_readiness = project_plan_gate_readiness_snapshot(
        task=_task(),
        decision=decision,
        catalog=shrunk,
    )
    assert recovered_readiness is not None
    assert project_pinned_plan_gate_decision(
        decision=decision,
        readiness=recovered_readiness,
        pin=pin,
    ).allowed_tool_names == ("record_work_plan",)


def test_first_rejection_forces_retry_but_repeated_terminal_remains_terminal() -> None:
    readiness = project_plan_gate_readiness_snapshot(
        task=_task(), decision=_decision(), catalog=_catalog_v2()
    )
    assert readiness is not None
    pin = bind_recovered_plan_gate_pin(
        snapshot=readiness,
        source_model_event_sequence=20,
        source_request_artifact_hash="sha256:" + "a" * 64,
        source_request_body_hash="sha256:" + "b" * 64,
    )
    retry = _decision(recovery_used=True)
    assert project_pinned_plan_gate_decision(
        decision=retry,
        readiness=None,
        pin=pin,
    ).allowed_tool_names == ("record_work_plan",)

    repeated = _decision(
        target="terminal",
        allowed=(),
        recovery_used=True,
        terminal_reason="work_plan_admission_repeated",
    )
    assert (
        project_pinned_plan_gate_decision(
            decision=repeated,
            readiness=None,
            pin=pin,
        )
        == repeated
    )


def test_pin_is_current_diff_and_gate_bound() -> None:
    readiness = project_plan_gate_readiness_snapshot(
        task=_task(), decision=_decision(), catalog=_catalog_v2()
    )
    assert readiness is not None
    pin = bind_recovered_plan_gate_pin(
        snapshot=readiness,
        source_model_event_sequence=20,
        source_request_artifact_hash="sha256:" + "a" * 64,
        source_request_body_hash="sha256:" + "b" * 64,
    )
    stale_base = _catalog_v2().model_copy(update={"worktree_diff_hash": "sha256:" + "f" * 64})
    with pytest.raises(RecoveryError, match="stale or foreign"):
        project_pinned_evidence_catalog(base=stale_base, pin=pin)

    wrong_gate = _decision().model_copy(update={"plan_gate_id": "sha256:" + "9" * 64})
    with pytest.raises(RecoveryError, match="current decision"):
        project_pinned_plan_gate_decision(decision=wrong_gate, readiness=None, pin=pin)


def test_unknown_is_represented_once_and_gateway_derives_recorded_unknowns() -> None:
    request = _request()
    assert "unknowns" not in request.parameters["properties"]
    assert "unknowns" not in request.parameters["required"]
    catalog = project_pinned_evidence_catalog(base=_catalog_v2(), pin=None)
    arguments = _arguments_with_single_unknown()

    projected, _ = normalize_pinned_exploration_plan(
        task=_task(),
        catalog=catalog,
        request_projection=request,
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
        history=(),
        raw_arguments=arguments,
    )
    assert projected.unknowns == (
        arguments["exploration_state"]["unknown_dispositions"][0]["question"],
    )

    duplicated = copy.deepcopy(arguments)
    duplicated["unknowns"] = ["duplicate"]
    with pytest.raises(ContractError) as exc_info:
        normalize_pinned_exploration_plan(
            task=_task(),
            catalog=catalog,
            request_projection=request,
            trigger="initial",
            revision_index=0,
            parent_plan_hash=None,
            trigger_check_id=None,
            trigger_event_sequence=None,
            cross_reset_trigger=None,
            history=(),
            raw_arguments=duplicated,
        )
    assert exc_info.value.details["reason_codes"] == ["plan_gate_unknown_text_duplicated"]


def test_projection_is_deterministic_and_tampering_fails_closed() -> None:
    first = _request()
    second = _request()
    assert first == second

    parameters = copy.deepcopy(first.parameters)
    parameters["properties"]["unknowns"] = {"type": "array"}
    tampered = first.model_copy(update={"parameters": parameters})
    with pytest.raises(RecoveryError, match="request projection differs"):
        normalize_pinned_exploration_plan(
            task=_task(),
            catalog=project_pinned_evidence_catalog(base=_catalog_v2(), pin=None),
            request_projection=tampered,
            trigger="initial",
            revision_index=0,
            parent_plan_hash=None,
            trigger_check_id=None,
            trigger_event_sequence=None,
            cross_reset_trigger=None,
            history=(),
            raw_arguments=_arguments_with_single_unknown(),
        )
