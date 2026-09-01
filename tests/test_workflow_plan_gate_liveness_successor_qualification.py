from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_plan_gate_liveness_successor_qualification import (
    IMMUTABLE_PREDECESSORS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_workflow_plan_gate_liveness_successor_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_plan_gate_liveness_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_plan_gate_liveness_successor_qualification(ROOT)
    second = build_workflow_plan_gate_liveness_successor_qualification(ROOT)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
    assert first["runtime_surface_activated"] is True
    assert first["rapid_candidate_created"] is False
    assert first["paid_execution_authorized"] is False
    assert first["quality_improvement_established"] is False
    assert all(
        first["evidence_boundary"][key] == 0
        for key in (
            "provider_calls",
            "docker_calls",
            "evaluator_calls",
            "visible_check_calls",
            "workspace_runtime_mutations",
        )
    )


def test_plan_gate_liveness_qualification_covers_force_retry_and_unknown() -> None:
    scenarios = build_workflow_plan_gate_liveness_successor_qualification(ROOT)["scenarios"]

    assert scenarios["runtime_identity"] == {
        "runtime_policy_version": "lean-harness-v21",
        "tool_schema_version": "v25",
        "context_policy_version": "phase-evidence-v31",
        "request_evidence_schema": "lean-harness-request-evidence-v21",
        "plan_gate_liveness_policy_version": "pinned-plan-gate-liveness-v1",
    }
    constructible = scenarios["constructible_initial_plan"]
    assert constructible["distinct_source_coverage_keys"] >= 2
    assert constructible["forced_target"] == "record-work-plan"
    assert constructible["forced_tools"] == ["record_work_plan"]
    retry = scenarios["one_recovered_retry"]
    assert retry["recovered_catalog_status"] == "pinned"
    assert retry["retry_tools"] == ["record_work_plan"]
    assert retry["repeated_terminal_preserved"] is True
    assert retry["repeated_terminal_reason"] == "work_plan_admission_repeated"
    canonical = scenarios["canonical_unknown"]
    assert canonical["top_level_unknown_schema_present"] is False
    assert canonical["recorded_unknowns"] == canonical["unknown_disposition_questions"]
    assert canonical["duplicate_rejection"] == "plan_gate_unknown_text_duplicated"
    assert all(
        "stale" in value or "decision" in value for value in scenarios["fail_closed"].values()
    )


def test_plan_gate_liveness_qualification_binds_sources_and_predecessors() -> None:
    value = build_workflow_plan_gate_liveness_successor_qualification(ROOT)

    assert [item["path"] for item in value["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in value["immutable_predecessors"]] == list(
        IMMUTABLE_PREDECESSORS
    )
    for item in value["immutable_predecessors"]:
        assert {
            key: item[key] for key in IMMUTABLE_PREDECESSORS[item["path"]]
        } == IMMUTABLE_PREDECESSORS[item["path"]]


def test_stored_plan_gate_liveness_qualification_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == qualification_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
