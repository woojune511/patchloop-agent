from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_causal_alternative_successor_qualification import (
    IMMUTABLE_PREDECESSORS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_workflow_causal_alternative_successor_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_causal_alternative_qualification_captures_generic_gate() -> None:
    value = build_workflow_causal_alternative_successor_qualification(ROOT)
    scenarios = value["scenarios"]

    assert value["status"] == "offline-qualified"
    assert value["runtime_version"] is None
    assert value["tool_schema_version"] is None
    assert value["context_policy_version"] is None
    assert scenarios["generic_schema"]["exception_specific_key_present"] is False
    assert "mutation_site_rationale" in scenarios["generic_schema"]["model_facing_keys"]
    assert scenarios["same_family_relabel"]["reason_codes"] == ["causal_boundary_already_exhausted"]
    assert scenarios["same_family_relabel"]["mutation_admitted"] is False
    assert scenarios["non_exhausted_alternative"]["alternative_boundary_is_non_exhausted"] is True
    assert scenarios["mutation_baseline_restore"]["restore_action_ids"] == [
        "mutation-2",
        "mutation-1",
    ]
    assert scenarios["admission_recovery"]["terminal_reason"] == (
        "causal_alternative_admission_repeated"
    )
    assert scenarios["restart_and_limits"]["initial_plus_corrective_mutation_limit"] == ("1+3")
    assert tuple(item["path"] for item in value["source_files"]) == SOURCE_FILES
    assert tuple(item["path"] for item in value["immutable_predecessors"]) == tuple(
        IMMUTABLE_PREDECESSORS
    )


def test_causal_alternative_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_causal_alternative_successor_qualification(ROOT)
    second = build_workflow_causal_alternative_successor_qualification(ROOT)

    assert first == second
    assert qualification_bytes(first) == qualification_bytes(second)
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
    assert first["runtime_activation_authorized"] is False
    assert first["paid_execution_authorized"] is False
    assert first["rapid_candidate_created"] is False
    assert first["quality_improvement_established"] is False
    assert first["semantic_distinctness_established"] is False


def test_causal_alternative_qualification_predecessors_are_exact() -> None:
    value = build_workflow_causal_alternative_successor_qualification(ROOT)
    observed = {item["path"]: item for item in value["immutable_predecessors"]}
    for path, expected in IMMUTABLE_PREDECESSORS.items():
        assert {key: observed[path][key] for key in expected} == expected


def test_causal_alternative_qualification_artifact_is_canonical() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    stored = json.loads(raw)

    assert raw == qualification_bytes(stored)
    assert sha256_bytes(raw).startswith("sha256:")
    assert raw == qualification_bytes(
        build_workflow_causal_alternative_successor_qualification(ROOT)
    )
