from __future__ import annotations

from pathlib import Path

from patchloop.evals.rapid_required_trigger_diagnosis import (
    build_rapid_required_trigger_diagnosis,
    diagnosis_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".patchloop/state.sqlite3"


def _build() -> dict:
    return build_rapid_required_trigger_diagnosis(
        repository_root=ROOT,
        state_path=STATE,
    )


def test_required_trigger_diagnosis_is_deterministic_and_public_only() -> None:
    first = _build()
    second = _build()
    assert diagnosis_bytes(first) == diagnosis_bytes(second)
    assert first["evidence_boundary"] == {
        "public_tool_metadata_only": True,
        "private_task_spec_read": False,
        "hidden_evaluator_content_read": False,
        "reference_patch_read": False,
        "reasoning_text_read": False,
        "llm_response_text_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "state_mutations": 0,
        "added_cost_nanos": 0,
    }


def test_required_trigger_diagnosis_separates_limit_from_eviction() -> None:
    value = _build()
    control = value["configured_limit_control"]
    eviction = value["eviction_failure"]
    assert control["failed_check_sequences"] == [52, 80, 113, 146]
    assert control["initial_plus_corrective_mutations"] == "1+3"
    assert control["correction_limit_bypassed"] is False
    assert eviction["trigger_event_sequence"] == 101
    assert eviction["last_request_with_trigger"]["catalog_has_trigger"] is True
    assert eviction["first_request_without_trigger"] == {
        **eviction["first_request_without_trigger"],
        "information_actions_in_episode": 3,
        "fresh_current_read": True,
        "allowed_tool_names": ["read_file"],
        "required_trigger_evidence_id": None,
        "catalog_has_trigger": False,
        "recent_context_has_trigger": False,
    }
    assert eviction["post_eviction_request_count"] > 1
    assert eviction["revision_recorded_after_trigger"] is False
    assert eviction["mutation_applied_after_trigger"] is False
    assert value["diagnosis"]["increase_correction_limit_supported"] is False
