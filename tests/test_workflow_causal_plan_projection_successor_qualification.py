from __future__ import annotations

from pathlib import Path

import pytest

from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    IMMUTABLE_PREDECESSORS,
    QUALIFICATION_PATH,
    build_workflow_causal_plan_projection_successor_qualification,
    load_workflow_causal_plan_projection_successor_qualification,
    qualification_bytes,
)
from patchloop.errors import ContractError

ROOT = Path(__file__).resolve().parents[1]


def test_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_causal_plan_projection_successor_qualification(ROOT)
    second = build_workflow_causal_plan_projection_successor_qualification(ROOT)

    assert first == second
    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
    assert first["runtime_surface_activated"] is False
    assert first["rapid_candidate_created"] is False
    assert first["quality_improvement_established"] is False
    assert first["runtime_behavior_established"] is False
    assert first["evidence_boundary"]["provider_calls"] == 0
    assert first["evidence_boundary"]["docker_calls"] == 0
    assert first["evidence_boundary"]["evaluator_calls"] == 0
    assert first["evidence_boundary"]["visible_check_calls"] == 0


def test_qualification_covers_r13_admission_shapes_and_exact_binding() -> None:
    value = build_workflow_causal_plan_projection_successor_qualification(ROOT)
    scenarios = value["scenarios"]

    assert scenarios["server_owned_structure"]["forbidden_fields_absent"] is True
    assert scenarios["server_owned_structure"]["roles"] == [
        "causal_boundary",
        "intermediate",
        "mutation_site",
    ]
    assert scenarios["server_owned_structure"]["final_relationship_to_next"] is None
    assert scenarios["server_owned_structure"]["old_shape_rejection"] == (
        "causal_plan_input_shape_invalid"
    )
    assert scenarios["finite_public_source_spans"]["foreign_span_rejection"] == (
        "causal_source_span_ineligible"
    )
    assert scenarios["repeated_location"]["boundary_equals_mutation"] is True
    assert scenarios["server_owned_observation"]["initial_status"] == "static_source"
    assert scenarios["server_owned_observation"]["revision_status"] == ("visible_check_failed")
    assert (
        scenarios["server_owned_plan_bindings"]["candidate_outside_mechanism_rejection"]
        == "causal_candidate_not_in_mechanism"
    )


def test_qualification_binds_consumed_r13_and_preserves_runtime_limit_boundary() -> None:
    value = build_workflow_causal_plan_projection_successor_qualification(ROOT)

    assert value["r13_binding"]["r13_retry_allowed"] is False
    assert value["r13_binding"]["coding_quality_inferred"] is False
    assert value["r13_binding"]["v17_rows"] == 3
    assert value["r13_binding"]["v17_evaluator_reached"] == 0
    assert value["preserved_runtime_limits"]["existing_one_retry_fail_closed"] is True
    assert value["preserved_runtime_limits"]["third_plan_dispatch_blocked"] is True
    assert (
        value["preserved_runtime_limits"]["activation_required_to_claim_runtime_preservation"]
        is True
    )
    assert {item["path"] for item in value["immutable_predecessors"]} == set(IMMUTABLE_PREDECESSORS)


def test_stored_qualification_matches_current_source() -> None:
    stored = load_workflow_causal_plan_projection_successor_qualification(ROOT)
    expected = build_workflow_causal_plan_projection_successor_qualification(ROOT)

    assert stored == expected
    assert (ROOT / QUALIFICATION_PATH).read_bytes() == qualification_bytes(stored)


def test_predecessor_drift_fails_closed(tmp_path: Path) -> None:
    relative = next(iter(IMMUTABLE_PREDECESSORS))
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_text("{}", encoding="utf-8")

    with pytest.raises(ContractError):
        build_workflow_causal_plan_projection_successor_qualification(tmp_path)
