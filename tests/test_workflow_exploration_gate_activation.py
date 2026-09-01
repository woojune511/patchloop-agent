from __future__ import annotations

import copy
from datetime import UTC, datetime

import pytest

from patchloop.agent.workflow_causal_plan_projection_activation import (
    project_activated_causal_plan_request,
    standard_plan_from_projected_causal_plan,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    _arguments,
    _catalog,
    _task,
)
from patchloop.agent.workflow_exploration_gate_activation import (
    ActivatedExplorationPlanRequest,
    exploration_binding_for_hash,
    exploration_closure_event_payload,
    normalize_activated_exploration_plan,
    project_activated_exploration_plan_request,
)
from patchloop.agent.workflow_exploration_gate_successor import (
    build_exploration_work_plan_binding,
)
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import RecoveryError


def _request() -> ActivatedExplorationPlanRequest:
    base = project_activated_causal_plan_request(
        task=_task(),
        catalog=_catalog(include_failed_check=False),
        trigger="initial",
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
    )
    return project_activated_exploration_plan_request(base)


def _arguments_with_closure() -> dict:
    arguments = _arguments()
    unknown = arguments["unknowns"][0]
    arguments["exploration_state"] = {
        "boundary_coverage": {
            "ownership_boundary_span_ids": ["cspan:10:0"],
            "execution_boundary_span_ids": ["cspan:11:0"],
            "mutation_boundary_span_ids": ["cspan:10:0"],
        },
        "invariants": [
            {
                "subject": "Public transition ownership",
                "claim": "The two current-source ranges jointly own the transition.",
                "evidence_source_span_ids": ["cspan:10:0", "cspan:11:0"],
            }
        ],
        "preservation_obligations": [
            {
                "public_requirement": "Preserve the later public lifecycle step.",
                "expected_behavior": "Visible checks remain ordered after the edit.",
                "evidence_source_span_ids": ["cspan:11:0"],
            }
        ],
        "unknown_dispositions": [
            {
                "question": unknown,
                "disposition": "non_blocking",
                "explanation": "The bounded source transition does not depend on it.",
                "evidence_source_span_ids": ["cspan:11:0"],
            }
        ],
        "open_blocking_unknowns": [],
    }
    return arguments


def _event(sequence: int, event_type: EventType, payload: dict) -> RunEvent:
    return RunEvent(
        event_id=f"evt_exploration_activation_{sequence}",
        run_id="run_causal_plan_projection_qualification",
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 27, tzinfo=UTC),
        actor="test",
        payload=payload,
    )


def test_activation_preserves_source_schema_and_changes_only_runtime_authority() -> None:
    first = _request()
    second = _request()

    assert first == second
    assert first.runtime_surface_activated is True
    assert first.source_request.runtime_surface_activated is False
    assert first.parameters == first.source_request.parameters
    assert first.base_request_hash == first.source_request.base_request.content_hash


def test_activation_normalizes_exact_public_closure_deterministically() -> None:
    request = _request()
    first = normalize_activated_exploration_plan(
        task=_task(),
        catalog=_catalog(include_failed_check=False),
        request_projection=request,
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
        history=(),
        raw_arguments=_arguments_with_closure(),
    )
    second = normalize_activated_exploration_plan(
        task=_task(),
        catalog=_catalog(include_failed_check=False),
        request_projection=request,
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
        history=(),
        raw_arguments=_arguments_with_closure(),
    )

    assert first == second
    assert len(first[1].selected_source_coverage_keys) >= 2


def test_activation_request_tampering_fails_before_plan_admission() -> None:
    request = _request()
    parameters = copy.deepcopy(request.parameters)
    parameters["properties"]["exploration_state"]["properties"]["open_blocking_unknowns"][
        "maxItems"
    ] = 1
    tampered = request.model_copy(update={"parameters": parameters})

    with pytest.raises(RecoveryError, match="request projection differs"):
        normalize_activated_exploration_plan(
            task=_task(),
            catalog=_catalog(include_failed_check=False),
            request_projection=tampered,
            trigger="initial",
            revision_index=0,
            parent_plan_hash=None,
            trigger_check_id=None,
            trigger_event_sequence=None,
            cross_reset_trigger=None,
            history=(),
            raw_arguments=_arguments_with_closure(),
        )


def test_durable_closure_binding_round_trips_and_tampering_fails_closed() -> None:
    request = _request()
    projected, receipt = normalize_activated_exploration_plan(
        task=_task(),
        catalog=_catalog(include_failed_check=False),
        request_projection=request,
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
        history=(),
        raw_arguments=_arguments_with_closure(),
    )
    plan = standard_plan_from_projected_causal_plan(
        task=_task(), catalog=_catalog(include_failed_check=False), projected=projected
    )
    binding = build_exploration_work_plan_binding(
        plan=plan,
        plan_event_sequence=30,
        projected=projected,
        receipt=receipt,
    )
    plan_event = _event(
        30,
        EventType.PLAN_RECORDED,
        {
            "plan_hash": plan.content_hash,
            "revision_index": plan.revision_index,
            "parent_plan_hash": plan.parent_plan_hash,
            "trigger": plan.trigger,
            "exploration_closure_receipt_hash": receipt.content_hash,
            "activated_exploration_request_hash": request.content_hash,
        },
    )
    payload = exploration_closure_event_payload(
        binding=binding,
        request_projection=request,
    )
    closure_event = _event(31, EventType.EXPLORATION_CLOSURE_RECORDED, payload)

    assert (
        exploration_binding_for_hash(
            run_id=plan.run_id,
            plan_hash=plan.content_hash,
            events=(plan_event, closure_event),
        )
        == binding
    )

    tampered_payload = dict(payload)
    tampered_payload["activated_request_hash"] = "sha256:" + "0" * 64
    with pytest.raises(RecoveryError, match="event binding differs"):
        exploration_binding_for_hash(
            run_id=plan.run_id,
            plan_hash=plan.content_hash,
            events=(
                plan_event,
                _event(31, EventType.EXPLORATION_CLOSURE_RECORDED, tampered_payload),
            ),
        )
