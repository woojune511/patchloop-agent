from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.workflow_causal_plan_projection_activation_qualification import (
    IMMUTABLE_PREDECESSORS,
    QUALIFICATION_PATH,
    build_workflow_causal_plan_projection_activation_qualification,
    qualification_bytes,
)
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_projection_activation_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_causal_plan_projection_activation_qualification(ROOT)
    second = build_workflow_causal_plan_projection_activation_qualification(ROOT)

    assert first == second
    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
    assert first["runtime_activation_authorized"] is True
    assert first["rapid_candidate_created"] is False
    assert first["paid_execution_authorized"] is False
    assert first["quality_improvement_established"] is False
    assert first["evidence_boundary"] == {
        "public_synthetic_source_only": True,
        "task_fixture_files_read": False,
        "private_task_spec_read": False,
        "hidden_evaluator_content_read": False,
        "reference_patch_read": False,
        "reasoning_text_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "workspace_mutations": 0,
        "added_cost_usd": "0",
    }


def test_projection_activation_qualification_covers_runtime_and_fail_closed_limits() -> None:
    value = build_workflow_causal_plan_projection_activation_qualification(ROOT)
    scenarios = value["scenarios"]

    assert scenarios["runtime_identity"] == {
        "runtime_policy_version": "lean-harness-v18",
        "tool_schema_version": "v22",
        "context_policy_version": "phase-evidence-v28",
        "request_evidence_schema": "lean-harness-request-evidence-v18",
        "activation_policy_version": "gateway-owned-causal-plan-projection-v1",
    }
    assert scenarios["dynamic_model_surface"]["runtime_surface_activated"] is True
    assert scenarios["dynamic_model_surface"]["forbidden_server_fields_absent"] is True
    assert scenarios["dynamic_model_surface"]["stale_span_rejection"] == (
        "causal_source_span_ineligible"
    )
    assert (
        scenarios["dynamic_model_surface"]["tampered_projection_rejected_before_normalization"]
        is True
    )
    assert scenarios["cross_reset_evidence_boundary"] == {
        "stale_check_observation_only": True,
        "observation_evidence": None,
        "current_foundation_ids": ["pev:21"],
        "candidate_read_id": "pev:21",
        "exhausted_current_boundary_rejection": "causal_boundary_already_exhausted",
        "same_span_boundary_and_mutation_accepted": True,
    }
    assert scenarios["durable_v2_binding"]["round_trip_exact"] is True
    assert scenarios["durable_v2_binding"]["stale_check_observation_only"] is True
    assert scenarios["preserved_limits"]["after_read_search_target"] == ("revise-work-plan")
    assert scenarios["preserved_limits"]["first_rejection_consumes_recovery"] is True
    assert scenarios["preserved_limits"]["third_plan_dispatch_blocked"] is True


def test_projection_activation_qualification_preserves_predecessors() -> None:
    value = build_workflow_causal_plan_projection_activation_qualification(ROOT)

    assert {item["path"] for item in value["immutable_predecessors"]} == set(IMMUTABLE_PREDECESSORS)
    assert value["preservation_boundary"] == {
        "lean_v17_behavior_modified": False,
        "r13_retry_allowed": False,
        "source_projection_requalified": False,
        "activation_is_opt_in": True,
    }


def test_stored_projection_activation_qualification_is_immutable_predecessor() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    stored = json.loads(raw)

    assert len(raw) == 5_438
    assert sha256_bytes(raw) == (
        "sha256:7f4b75a80c8085cdcf3beca1f9693077f97596ba719f3bdece5c9d5553cefa8b"
    )
    assert stored["content_hash"] == (
        "sha256:359b3bc8b2067bcd9b42f3c8dbbc5d8894d04a0611948c44a1d83d2995979754"
    )
    assert raw == qualification_bytes(stored)


def test_projection_activation_predecessor_drift_fails_closed(tmp_path: Path) -> None:
    relative = next(iter(IMMUTABLE_PREDECESSORS))
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_text("{}", encoding="utf-8")

    with pytest.raises(ContractError):
        build_workflow_causal_plan_projection_activation_qualification(tmp_path)
