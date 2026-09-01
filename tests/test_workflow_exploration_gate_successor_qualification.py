from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.workflow_exploration_gate_successor_qualification import (
    IMMUTABLE_PUBLIC_INPUTS,
    QUALIFICATION_PATH,
    build_workflow_exploration_gate_successor_qualification,
    load_workflow_exploration_gate_successor_qualification,
    qualification_bytes,
)
from patchloop.errors import ContractError

ROOT = Path(__file__).resolve().parents[1]


def test_qualification_is_deterministic_zero_call_and_unactivated() -> None:
    first = build_workflow_exploration_gate_successor_qualification(ROOT)
    second = build_workflow_exploration_gate_successor_qualification(ROOT)

    assert first == second
    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
    assert first["runtime_surface_activated"] is False
    assert first["runtime_activation_authorized"] is False
    assert first["rapid_candidate_created"] is False
    assert first["paid_execution_authorized"] is False
    assert first["evidence_boundary"] == {
        "public_synthetic_source_only": True,
        "r14_public_diagnosis_identity_and_aggregate_only": True,
        "private_task_spec_read": False,
        "hidden_evaluator_content_read": False,
        "reference_patch_read": False,
        "reasoning_text_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "workspace_task_mutations": 0,
        "added_cost_usd": "0",
    }


def test_scenarios_cover_closure_rejections_and_binding() -> None:
    value = build_workflow_exploration_gate_successor_qualification(ROOT)
    scenarios = value["scenarios"]

    assert scenarios["dynamic_request"]["open_blocking_unknowns_max_items"] == 0
    assert scenarios["valid_closure"]["same_input_same_plan"] is True
    assert scenarios["valid_closure"]["same_input_same_receipt"] is True
    assert scenarios["valid_closure"]["distinct_source_coverage_keys"] >= 2
    assert scenarios["typed_rejections"] == {
        "one_range_for_all_boundaries": "exploration_boundary_coverage_insufficient",
        "missing_unknown_disposition": "exploration_unknown_disposition_mismatch",
        "open_blocking_unknown": "exploration_blocking_unknowns_open",
        "unbound_mutation_boundary": "exploration_mutation_boundary_unbound",
        "tampered_request_failed_closed": True,
    }


def test_public_predecessors_and_r14_limits_are_exact() -> None:
    value = build_workflow_exploration_gate_successor_qualification(ROOT)

    assert len(value["immutable_public_inputs"]) == len(IMMUTABLE_PUBLIC_INPUTS)
    assert value["r14_public_binding"] == {
        "execution_hash": (
            "sha256:f077496605d0776d7d2f2e677391cc2ae9135550077486126258429917986c1b"
        ),
        "official": False,
        "v18_rows": 3,
        "first_mutation_read_calls_in_order": [3, 3, 1],
        "first_mutation_check_calls_in_order": [0, 0, 0],
        "submissions": 2,
        "successes": 0,
        "raw_plan_payloads_replayed": False,
        "coding_quality_inferred": False,
        "r14_retry_allowed": False,
    }
    assert value["contract_limits"]["does_not_detect_omitted_unstated_unknowns"] is True
    assert value["contract_limits"]["does_not_prove_semantic_correctness"] is True


def test_stored_qualification_matches_sources_when_materialized() -> None:
    if not (ROOT / QUALIFICATION_PATH).is_file():
        pytest.skip("qualification is not materialized yet")
    assert load_workflow_exploration_gate_successor_qualification(ROOT) == (
        build_workflow_exploration_gate_successor_qualification(ROOT)
    )


def test_tampered_content_or_predecessor_fails_closed(tmp_path: Path) -> None:
    value = build_workflow_exploration_gate_successor_qualification(ROOT)
    tampered = json.loads(qualification_bytes(value))
    tampered["status"] = "activated"
    with pytest.raises(ContractError, match="hash differs"):
        qualification_bytes(tampered)

    relative = next(iter(IMMUTABLE_PUBLIC_INPUTS))
    source = ROOT / relative
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes() + b"\n")
    for other in tuple(IMMUTABLE_PUBLIC_INPUTS)[1:]:
        other_target = tmp_path / other
        other_target.parent.mkdir(parents=True, exist_ok=True)
        other_target.write_bytes((ROOT / other).read_bytes())
    for source_file in value["source_files"]:
        selected = source_file["path"]
        selected_target = tmp_path / selected
        selected_target.parent.mkdir(parents=True, exist_ok=True)
        selected_target.write_bytes((ROOT / selected).read_bytes())
    with pytest.raises(ContractError):
        build_workflow_exploration_gate_successor_qualification(tmp_path)
