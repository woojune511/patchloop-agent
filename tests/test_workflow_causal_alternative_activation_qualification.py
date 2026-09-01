from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_causal_alternative_activation_qualification import (
    PREDECESSOR_CONTENT_HASH,
    PREDECESSOR_FILE_SHA256,
    PREDECESSOR_PATH,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_workflow_causal_alternative_activation_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_causal_activation_qualification_binds_generic_v17_runtime() -> None:
    value = build_workflow_causal_alternative_activation_qualification(ROOT)
    scenarios = value["scenarios"]

    assert value["status"] == "offline-qualified"
    assert scenarios["runtime_identity"] == {
        "runtime_policy_version": "lean-harness-v17",
        "tool_schema_version": "v21",
        "context_policy_version": "phase-evidence-v27",
        "request_evidence_schema": "lean-harness-request-evidence-v17",
        "activation_policy_version": "gateway-owned-causal-baseline-reset-v1",
    }
    assert scenarios["restore_trigger"]["active_at_restored_baseline"] is True
    assert scenarios["restore_trigger"]["semantic_state_round_trip_exact"] is True
    assert scenarios["restore_trigger"]["epoch_event_count_after_restore"] == 0
    assert scenarios["restore_trigger"]["trigger_cleared_after_mutation"] is True
    assert scenarios["restore_trigger"]["failure_events_deleted"] is False
    assert scenarios["bounded_workflow"] == {
        "initial_allowed_tools": ["search_files", "read_file"],
        "after_read_allowed_tools": ["search_files"],
        "after_read_search_target": "revise-work-plan",
        "after_plan_allowed_tools": ["apply_structured_edit"],
        "third_plan_dispatch_blocked": True,
        "initial_plus_corrective_mutation_limit": "1+3",
        "correction_limit_changed": False,
        "review_correction_limit_changed": False,
    }
    assert scenarios["generic_plan_surface"]["exception_specific_key_present"] is False
    assert scenarios["generic_plan_surface"]["task_specific_field_names"] == []
    assert "causal_path" in scenarios["generic_plan_surface"]["causal_mechanism_keys"]
    assert "mutation_site_rationale" in scenarios["generic_plan_surface"]["causal_mechanism_keys"]
    assert scenarios["durable_binding"]["round_trip_exact"] is True
    assert scenarios["durable_binding"]["tampered_binding_rejected"] is True
    assert tuple(item["path"] for item in value["source_files"]) == SOURCE_FILES


def test_causal_activation_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_causal_alternative_activation_qualification(ROOT)
    second = build_workflow_causal_alternative_activation_qualification(ROOT)

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
    assert first["rapid_candidate_created"] is False
    assert first["paid_execution_authorized"] is False
    assert first["quality_improvement_established"] is False
    assert first["generalization_established"] is False


def test_causal_activation_predecessor_is_exact() -> None:
    value = build_workflow_causal_alternative_activation_qualification(ROOT)

    assert value["immutable_predecessor"] == {
        "path": PREDECESSOR_PATH.as_posix(),
        "bytes": 5_415,
        "file_sha256": PREDECESSOR_FILE_SHA256,
        "content_hash": PREDECESSOR_CONTENT_HASH,
    }


def test_causal_activation_qualification_artifact_is_immutable_predecessor() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    stored = json.loads(raw)

    assert raw == qualification_bytes(stored)
    assert len(raw) == 5_235
    assert sha256_bytes(raw) == (
        "sha256:72576cdcf05a9337bcee415d3200bfe76f04fd8b13b3231b02140fb6b2cd448e"
    )
    assert stored["content_hash"] == (
        "sha256:45f469b256c50b7259b7c1df6a59e3b4fe8f598f67733ef93a96733b72191f85"
    )
