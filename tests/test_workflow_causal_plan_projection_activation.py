from __future__ import annotations

import copy
from datetime import UTC, datetime

import pytest

from patchloop.agent.workflow_causal_alternative_activation import (
    CrossResetFailureTrigger,
)
from patchloop.agent.workflow_causal_plan_projection_activation import (
    CausalMechanismHistoryEntryV2,
    build_causal_work_plan_binding_v2,
    normalize_activated_causal_plan,
    project_activated_causal_plan_request,
    project_causal_mechanism_history_v2,
    standard_plan_from_projected_causal_plan,
)
from patchloop.agent.workflow_causal_plan_projection_successor import (
    normalize_causal_plan_request,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    EMPTY_DIFF,
    HANDLER_PATH,
    RUN_ID,
    RUNTIME_PATH,
    _arguments,
    _catalog,
    _read,
    _support,
    _task,
)
from patchloop.agent.workflow_successor_v2 import EligiblePlanEvidenceCatalogV2
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_json


def _catalog_v2() -> EligiblePlanEvidenceCatalogV2:
    task = _task()
    items = (
        _read(20, RUNTIME_PATH, ((20, 57), (90, 118))),
        _read(21, HANDLER_PATH, ((120, 170),)),
        _support(24),
    )
    body = {
        "schema_version": "eligible-plan-evidence-catalog-v2",
        "run_id": RUN_ID,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": sha256_json(task.model_dump(mode="json")),
        "worktree_diff_hash": EMPTY_DIFF,
        "model_visible_context_hash": "sha256:" + "d" * 64,
        "model_visible_recent_event_sequences": tuple(
            item.canonical_event_sequence for item in items
        ),
        "items": tuple(item.model_dump(mode="python") for item in items),
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
        "required_trigger_status": "not_required",
        "required_trigger_event_sequence": None,
        "required_trigger_evidence_id": None,
        "model_visible_pinned_event_sequences": (),
        "unavailable_reason": None,
    }
    return EligiblePlanEvidenceCatalogV2.model_validate({**body, "content_hash": sha256_json(body)})


def _initial_history() -> tuple[CausalMechanismHistoryEntryV2, ...]:
    plan = normalize_causal_plan_request(
        task=_task(),
        catalog=_catalog(include_failed_check=False),
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
        raw_arguments=_arguments(),
    )
    return (
        CausalMechanismHistoryEntryV2(
            revision_index=0,
            plan_hash=sha256_json({"standard_plan": 0}),
            parent_plan_hash=None,
            trigger="initial",
            mechanism=plan.causal_mechanism,
            projected_plan_hash=plan.content_hash,
        ),
    )


def _trigger() -> CrossResetFailureTrigger:
    body = {
        "schema_version": "cross-reset-public-failure-trigger-v1",
        "policy_version": "gateway-owned-causal-baseline-reset-v1",
        "run_id": RUN_ID,
        "check_id": "targeted",
        "failure_signature": "same bounded public failure",
        "failure_signature_hash": sha256_json("same bounded public failure"),
        "failure_event_sequences": (31, 41),
        "failed_diff_hashes": (
            sha256_json({"diff": 1}),
            sha256_json({"diff": 2}),
        ),
        "source_semantic_progress_state_hash": sha256_json({"state": 1}),
        "mutation_baseline_projection_hash": sha256_json({"baseline": 1}),
        "mutation_baseline_restore_receipt_hash": sha256_json({"receipt": 1}),
        "restored_baseline_diff_hash": EMPTY_DIFF,
        "restored_event_sequence": 50,
        "public_check_output_only": True,
        "stale_check_authorizes_mutation": False,
        "current_source_read_required": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return CrossResetFailureTrigger.model_validate({**body, "content_hash": sha256_json(body)})


def _cross_reset_arguments(span_id: str) -> dict:
    arguments = _arguments()
    arguments["prior_hypothesis_disposition"] = "rejected"
    arguments["supporting_evidence_ids"] = []
    arguments["candidate_source_span_ids"] = [span_id]
    arguments["causal_mechanism"] = {
        "summary": "One current public source span owns the alternative transition.",
        "causal_boundary": {
            "source_span_id": span_id,
            "symbol": "alternative_boundary",
            "observation": "This current source span receives the public transition.",
            "relationship_to_next": "The same span commits the visible transition.",
        },
        "intermediate_steps": [],
        "mutation_site": {
            "source_span_id": span_id,
            "symbol": "alternative_mutation",
            "observation": "This current source span commits the visible transition.",
        },
        "mutation_site_rationale": "The evidence-bound assignment is the minimal edit site.",
        "expected_observable_effect": "The targeted check observes the corrected transition.",
        "falsification_condition": "The same public failure remains after the edit.",
    }
    return arguments


def test_cross_reset_uses_current_source_and_keeps_stale_check_observational() -> None:
    catalog = _catalog_v2()
    trigger = _trigger()
    projection = project_activated_causal_plan_request(
        task=_task(),
        catalog=catalog,
        trigger="check_failure",
        trigger_check_id="targeted",
        trigger_event_sequence=41,
        cross_reset_trigger=trigger,
    )
    history = _initial_history()
    plan = normalize_activated_causal_plan(
        task=_task(),
        catalog=catalog,
        request_projection=projection,
        trigger="check_failure",
        revision_index=1,
        parent_plan_hash=history[-1].plan_hash,
        trigger_check_id="targeted",
        trigger_event_sequence=41,
        cross_reset_trigger=trigger,
        history=history,
        raw_arguments=_cross_reset_arguments("cspan:21:0"),
    )

    assert projection.stale_check_observation_only is True
    assert plan.observation_status == "visible_check_failed"
    assert plan.observation_evidence is None
    assert [item.evidence_id for item in plan.foundation_evidence] == ["pev:21"]
    assert plan.candidate_files[0].read_evidence_id == "pev:21"
    assert plan.trigger_event_sequence == 41


def test_cross_reset_rejects_exhausted_current_boundary_and_stale_span_id() -> None:
    catalog = _catalog_v2()
    trigger = _trigger()
    history = _initial_history()
    projection = project_activated_causal_plan_request(
        task=_task(),
        catalog=catalog,
        trigger="check_failure",
        trigger_check_id="targeted",
        trigger_event_sequence=41,
        cross_reset_trigger=trigger,
    )
    common = {
        "task": _task(),
        "catalog": catalog,
        "request_projection": projection,
        "trigger": "check_failure",
        "revision_index": 1,
        "parent_plan_hash": history[-1].plan_hash,
        "trigger_check_id": "targeted",
        "trigger_event_sequence": 41,
        "cross_reset_trigger": trigger,
        "history": history,
    }

    with pytest.raises(ContractError, match="exhausted public boundary") as exhausted:
        normalize_activated_causal_plan(
            **common,
            raw_arguments=_cross_reset_arguments("cspan:20:0"),
        )
    assert exhausted.value.details["reason_codes"] == ["causal_boundary_already_exhausted"]

    with pytest.raises(ContractError, match="outside the current request") as stale:
        normalize_activated_causal_plan(
            **common,
            raw_arguments=_cross_reset_arguments("cspan:10:0"),
        )
    assert stale.value.details["reason_codes"] == ["causal_source_span_ineligible"]


def test_projection_tamper_fails_closed_and_v2_history_round_trips() -> None:
    catalog = _catalog_v2()
    trigger = _trigger()
    history = _initial_history()
    projection = project_activated_causal_plan_request(
        task=_task(),
        catalog=catalog,
        trigger="check_failure",
        trigger_check_id="targeted",
        trigger_event_sequence=41,
        cross_reset_trigger=trigger,
    )
    tampered = projection.model_copy(
        update={"parameter_schema_hash": sha256_json({"tampered": True})}
    )
    with pytest.raises(RecoveryError, match="request projection differs"):
        normalize_activated_causal_plan(
            task=_task(),
            catalog=catalog,
            request_projection=tampered,
            trigger="check_failure",
            revision_index=1,
            parent_plan_hash=history[-1].plan_hash,
            trigger_check_id="targeted",
            trigger_event_sequence=41,
            cross_reset_trigger=trigger,
            history=history,
            raw_arguments=_cross_reset_arguments("cspan:21:0"),
        )

    projected = normalize_activated_causal_plan(
        task=_task(),
        catalog=catalog,
        request_projection=projection,
        trigger="check_failure",
        revision_index=1,
        parent_plan_hash=history[-1].plan_hash,
        trigger_check_id="targeted",
        trigger_event_sequence=41,
        cross_reset_trigger=trigger,
        history=history,
        raw_arguments=_cross_reset_arguments("cspan:21:0"),
    )
    standard = standard_plan_from_projected_causal_plan(
        task=_task(), catalog=catalog, projected=projected
    )
    binding = build_causal_work_plan_binding_v2(
        plan=standard,
        plan_event_sequence=60,
        projected=projected,
        request_projection=projection,
        cross_reset_trigger_hash=trigger.content_hash,
    )
    plan_event = RunEvent(
        event_id="evt_plan",
        run_id=RUN_ID,
        sequence=60,
        type=EventType.PLAN_RECORDED,
        timestamp=datetime(2026, 8, 26, tzinfo=UTC),
        actor="workflow-state-machine",
        correlation_id=None,
        payload={
            "plan_hash": standard.content_hash,
            "revision_index": 1,
            "parent_plan_hash": history[-1].plan_hash,
            "trigger": "check_failure",
        },
    )
    binding_event = RunEvent(
        event_id="evt_binding",
        run_id=RUN_ID,
        sequence=61,
        type=EventType.CAUSAL_MECHANISM_RECORDED,
        timestamp=datetime(2026, 8, 26, tzinfo=UTC),
        actor="workflow-state-machine",
        correlation_id=None,
        payload={
            "schema_version": "causal-mechanism-recorded-v2",
            "binding_hash": binding.content_hash,
            "binding": binding.model_dump(mode="json"),
        },
    )

    recovered = project_causal_mechanism_history_v2(
        run_id=RUN_ID, events=(plan_event, binding_event)
    )
    assert recovered[0].plan_hash == standard.content_hash
    tampered_event = binding_event.model_copy(deep=True)
    tampered_payload = copy.deepcopy(tampered_event.payload)
    tampered_payload["binding"]["plan_event_sequence"] = 59
    tampered_event = tampered_event.model_copy(update={"payload": tampered_payload})
    with pytest.raises(RecoveryError, match="binding event is invalid"):
        project_causal_mechanism_history_v2(run_id=RUN_ID, events=(plan_event, tampered_event))
