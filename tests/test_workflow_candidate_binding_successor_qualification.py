from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_candidate_binding_successor_qualification import (
    IMMUTABLE_PREDECESSORS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_workflow_candidate_binding_successor_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_candidate_binding_qualification_captures_r12_mechanical_delta() -> None:
    value = build_workflow_candidate_binding_successor_qualification(ROOT)
    scenarios = value["scenarios"]

    assert value["successor_runtime"] == "lean-harness-v16"
    assert value["tool_schema_version"] == "v20"
    assert value["context_policy_version"] == "phase-evidence-v26"
    assert scenarios["r12_shaped_legacy_rejection"]["legacy_reason_codes"] == [
        "plan_schema_invalid"
    ]
    normalized = scenarios["v16_normalization"]
    assert normalized["recorded_candidate_files"] == [
        {
            "path": "src/anyio/pytest_plugin.py",
            "read_evidence_id": "pev:17",
        }
    ]
    assert normalized["retained_foundation_evidence_ids"] == ["pev:12", "pev:17"]
    assert normalized["reversed_request_exact"] is True
    assert scenarios["fail_closed"]["mismatched_path_reason_codes"] == [
        "candidate_read_binding_invalid"
    ]
    assert scenarios["credential_safe_entry"]["rehearsal_env_file_read"] is False
    assert scenarios["credential_safe_entry"]["execute_dispatches"] == 0
    assert tuple(item["path"] for item in value["source_files"]) == SOURCE_FILES
    assert tuple(item["path"] for item in value["immutable_predecessors"]) == tuple(
        IMMUTABLE_PREDECESSORS
    )


def test_candidate_binding_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_candidate_binding_successor_qualification(ROOT)
    second = build_workflow_candidate_binding_successor_qualification(ROOT)

    assert first == second
    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["evidence_boundary"] == {
        "public_only": True,
        "task_fixture_files_read": False,
        "private_task_spec_read": False,
        "hidden_evaluator_content_read": False,
        "reference_patch_read": False,
        "reasoning_text_read": False,
        "repository_env_file_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "added_cost_usd": "0",
    }
    assert first["runtime_activation_authorized"] is False
    assert first["paid_execution_authorized"] is False
    assert first["rapid_candidate_created"] is False
    assert first["quality_improvement_established"] is False


def test_candidate_binding_qualification_predecessors_are_exact() -> None:
    value = build_workflow_candidate_binding_successor_qualification(ROOT)
    observed = {item["path"]: item for item in value["immutable_predecessors"]}
    for path, expected in IMMUTABLE_PREDECESSORS.items():
        assert {key: observed[path][key] for key in expected} == expected


def test_candidate_binding_qualification_artifact_is_canonical() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    stored = json.loads(raw)

    assert raw == qualification_bytes(stored)
    assert len(raw) == 5_218
    assert sha256_bytes(raw) == (
        "sha256:55038c7be91138c1863e59f37169276974960255978c87ad94b1b574acf0a2d1"
    )
    assert stored["content_hash"] == (
        "sha256:9e973d1b7976148861af71399d5cfe6e43d436eaff713f3ed171dbb94fc88b4c"
    )
