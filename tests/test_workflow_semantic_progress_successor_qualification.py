from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_semantic_progress_successor_qualification import (
    IMMUTABLE_PREDECESSORS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_workflow_semantic_progress_successor_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_semantic_progress_qualification_binds_generic_bounded_reset() -> None:
    value = build_workflow_semantic_progress_successor_qualification(ROOT)
    scenarios = value["scenarios"]

    assert value["successor_runtime"] == "lean-harness-v15"
    assert value["tool_schema_version"] == "v19"
    assert value["context_policy_version"] == "phase-evidence-v25"
    assert scenarios["second_same_signature_distinct_diff"]["semantic_reset_required"] is True
    assert scenarios["second_same_signature_distinct_diff"]["failed_diff_count"] == 2
    assert scenarios["bounded_reset_sequence"] == {
        "after_search_allowed": ["read_file"],
        "after_search_and_read_target": "revise-work-plan",
        "after_search_and_read_allowed": ["revise_work_plan"],
        "required_disposition_enum": ["rejected"],
    }
    assert scenarios["server_revision_admission"]["invalid_reason_codes"] == [
        "semantic_no_progress_requires_rejected_hypothesis"
    ]
    assert scenarios["bounded_exhaustion"]["terminal_reason"] == (
        "semantic_no_progress_evidence_exhausted"
    )
    assert scenarios["recovery_and_fail_closed"] == {
        "state_round_trip_exact": True,
        "state_hash_round_trip_exact": True,
        "missing_failure_summary_failed_closed": True,
    }
    assert tuple(item["path"] for item in value["source_files"]) == SOURCE_FILES
    assert tuple(item["path"] for item in value["immutable_predecessors"]) == tuple(
        IMMUTABLE_PREDECESSORS
    )


def test_semantic_progress_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_semantic_progress_successor_qualification(ROOT)
    second = build_workflow_semantic_progress_successor_qualification(ROOT)

    assert first == second
    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["evidence_boundary"] == {
        "public_only": True,
        "task_fixture_files_read": False,
        "private_task_spec_read": False,
        "hidden_evaluator_content_read": False,
        "reference_patch_read": False,
        "reasoning_text_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "state_mutations": 0,
        "added_cost_usd": "0",
    }
    assert first["runtime_activation_authorized"] is False
    assert first["paid_execution_authorized"] is False
    assert first["rapid_candidate_created"] is False
    assert first["quality_improvement_established"] is False


def test_semantic_progress_qualification_predecessors_are_exact() -> None:
    value = build_workflow_semantic_progress_successor_qualification(ROOT)
    observed = {item["path"]: item for item in value["immutable_predecessors"]}
    for path, expected in IMMUTABLE_PREDECESSORS.items():
        assert {key: observed[path][key] for key in expected} == expected


def test_semantic_progress_qualification_artifact_is_immutable_predecessor() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    stored = json.loads(raw)

    assert len(raw) == 6_703
    assert sha256_bytes(raw) == (
        "sha256:c13b4e6cf4c80b4eaa9c9d1016ab5e3bbdae881341c6a751a611266bb33fe7f0"
    )
    assert stored["content_hash"] == (
        "sha256:d3e578271060144513c2e49978a6e5fc2acf38888a180729bfb93c5b801e8ca1"
    )
    assert raw == qualification_bytes(stored)
