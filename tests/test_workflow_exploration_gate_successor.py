from __future__ import annotations

import copy

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
from patchloop.agent.workflow_exploration_gate_successor import (
    ExplorationGatedCausalPlanRequest,
    ExplorationWorkPlanBinding,
    build_exploration_work_plan_binding,
    normalize_exploration_gated_causal_plan,
    project_exploration_gated_causal_plan_request,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_json


def _base_request():
    return project_activated_causal_plan_request(
        task=_task(),
        catalog=_catalog(include_failed_check=False),
        trigger="initial",
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
    )


def _exploration_state() -> dict:
    unknown = _arguments()["unknowns"][0]
    return {
        "boundary_coverage": {
            "ownership_boundary_span_ids": ["cspan:10:0"],
            "execution_boundary_span_ids": ["cspan:11:0"],
            "mutation_boundary_span_ids": ["cspan:10:0"],
        },
        "invariants": [
            {
                "subject": "Public lifecycle ownership",
                "claim": "The entry boundary and handler jointly own the transition.",
                "evidence_source_span_ids": ["cspan:10:0", "cspan:11:0"],
            }
        ],
        "preservation_obligations": [
            {
                "public_requirement": "Preserve the later visible lifecycle step.",
                "expected_behavior": "The targeted and upstream checks still pass in order.",
                "evidence_source_span_ids": ["cspan:11:0"],
            }
        ],
        "unknown_dispositions": [
            {
                "question": unknown,
                "disposition": "non_blocking",
                "explanation": (
                    "The question concerns later evidence and does not change this bounded "
                    "current-diff transition."
                ),
                "evidence_source_span_ids": ["cspan:11:0"],
            }
        ],
        "open_blocking_unknowns": [],
    }


def _arguments_with_exploration() -> dict:
    arguments = _arguments()
    arguments["exploration_state"] = _exploration_state()
    return arguments


def _normalize(arguments: dict | None = None):
    request = project_exploration_gated_causal_plan_request(_base_request())
    return normalize_exploration_gated_causal_plan(
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
        raw_arguments=_arguments_with_exploration() if arguments is None else arguments,
    )


def test_dynamic_request_uses_exact_cspan_enum_and_disallows_open_blockers() -> None:
    request = project_exploration_gated_causal_plan_request(_base_request())
    state = request.parameters["properties"]["exploration_state"]
    coverage = state["properties"]["boundary_coverage"]["properties"]

    assert coverage["ownership_boundary_span_ids"]["items"]["enum"] == [
        "cspan:10:0",
        "cspan:10:1",
        "cspan:11:0",
    ]
    assert state["properties"]["open_blocking_unknowns"]["maxItems"] == 0
    assert request.runtime_surface_activated is False
    assert request.parameter_schema_hash == sha256_json(request.parameters)


def test_valid_closure_is_deterministic_and_preserves_exact_public_spans() -> None:
    first_plan, first_receipt = _normalize()
    second_plan, second_receipt = _normalize()

    assert first_plan == second_plan
    assert first_receipt == second_receipt
    assert first_receipt.declared_unknowns_closed is True
    assert len(first_receipt.selected_source_coverage_keys) >= 2
    assert {item.source_span_id for item in first_receipt.selected_source_spans} == {
        "cspan:10:0",
        "cspan:11:0",
    }


def test_one_broad_source_span_cannot_launder_every_boundary() -> None:
    arguments = _arguments_with_exploration()
    arguments["candidate_source_span_ids"] = ["cspan:10:0"]
    arguments["causal_mechanism"] = {
        "summary": "One source range appears to own the complete transition.",
        "causal_boundary": {
            "source_span_id": "cspan:10:0",
            "symbol": "entry",
            "observation": "The range receives the transition.",
            "relationship_to_next": "The same range commits it.",
        },
        "intermediate_steps": [],
        "mutation_site": {
            "source_span_id": "cspan:10:0",
            "symbol": "mutation",
            "observation": "The range commits the transition.",
        },
        "mutation_site_rationale": "The single range appears sufficient.",
        "expected_observable_effect": "The public transition changes.",
        "falsification_condition": "The same public failure remains.",
    }
    coverage = arguments["exploration_state"]["boundary_coverage"]
    coverage["ownership_boundary_span_ids"] = ["cspan:10:0"]
    coverage["execution_boundary_span_ids"] = ["cspan:10:0"]
    coverage["mutation_boundary_span_ids"] = ["cspan:10:0"]
    arguments["exploration_state"]["invariants"][0]["evidence_source_span_ids"] = ["cspan:10:0"]
    arguments["exploration_state"]["preservation_obligations"][0]["evidence_source_span_ids"] = [
        "cspan:10:0"
    ]
    arguments["exploration_state"]["unknown_dispositions"][0]["evidence_source_span_ids"] = [
        "cspan:10:0"
    ]

    with pytest.raises(ContractError) as exc_info:
        _normalize(arguments)

    assert exc_info.value.details["reason_codes"] == ["exploration_boundary_coverage_insufficient"]


def test_declared_unknown_requires_one_evidence_bound_disposition() -> None:
    arguments = _arguments_with_exploration()
    arguments["exploration_state"]["unknown_dispositions"] = []

    with pytest.raises(ContractError) as exc_info:
        _normalize(arguments)

    assert exc_info.value.details["reason_codes"] == ["exploration_unknown_disposition_mismatch"]


def test_open_blocking_unknown_rejects_before_mutation_authority() -> None:
    arguments = _arguments_with_exploration()
    arguments["exploration_state"]["open_blocking_unknowns"] = [
        "Which public source range owns cleanup?"
    ]

    with pytest.raises(ContractError) as exc_info:
        _normalize(arguments)

    assert exc_info.value.details["reason_codes"] == ["exploration_blocking_unknowns_open"]


def test_boundary_and_mutation_must_bind_the_recorded_mechanism() -> None:
    outside = _arguments_with_exploration()
    outside["exploration_state"]["boundary_coverage"]["ownership_boundary_span_ids"] = [
        "cspan:10:1"
    ]
    with pytest.raises(ContractError) as outside_error:
        _normalize(outside)
    assert outside_error.value.details["reason_codes"] == ["exploration_boundary_outside_mechanism"]

    unbound = _arguments_with_exploration()
    unbound["exploration_state"]["boundary_coverage"]["mutation_boundary_span_ids"] = ["cspan:11:0"]
    with pytest.raises(ContractError) as mutation_error:
        _normalize(unbound)
    assert mutation_error.value.details["reason_codes"] == ["exploration_mutation_boundary_unbound"]


def test_foreign_span_and_tampered_request_fail_closed() -> None:
    arguments = _arguments_with_exploration()
    arguments["exploration_state"]["invariants"][0]["evidence_source_span_ids"] = ["cspan:99:0"]
    with pytest.raises(ContractError) as foreign_error:
        _normalize(arguments)
    assert foreign_error.value.details["reason_codes"] == ["exploration_source_span_ineligible"]

    request = project_exploration_gated_causal_plan_request(_base_request())
    tampered_parameters = copy.deepcopy(request.parameters)
    tampered_parameters["properties"]["exploration_state"]["properties"]["open_blocking_unknowns"][
        "maxItems"
    ] = 1
    tampered = request.model_copy(update={"parameters": tampered_parameters})
    with pytest.raises(RecoveryError, match="request differs"):
        normalize_exploration_gated_causal_plan(
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
            raw_arguments=_arguments_with_exploration(),
        )


def test_closure_binds_the_ordinary_active_plan_and_round_trips() -> None:
    projected, receipt = _normalize()
    plan = standard_plan_from_projected_causal_plan(
        task=_task(), catalog=_catalog(include_failed_check=False), projected=projected
    )
    binding = build_exploration_work_plan_binding(
        plan=plan,
        plan_event_sequence=30,
        projected=projected,
        receipt=receipt,
    )

    assert binding.plan_hash == plan.content_hash
    assert binding.receipt_hash == receipt.content_hash
    assert ExplorationGatedCausalPlanRequest.model_validate(
        project_exploration_gated_causal_plan_request(_base_request()).model_dump(mode="python")
    ) == project_exploration_gated_causal_plan_request(_base_request())
    assert ExplorationWorkPlanBinding.model_validate(binding.model_dump(mode="python")) == binding
