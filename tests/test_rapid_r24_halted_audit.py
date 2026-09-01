from __future__ import annotations

import socket
from pathlib import Path

import pytest

from patchloop.errors import ContractError
from patchloop.evals.rapid_r24_halted_audit import (
    AUDIT_PATH,
    BUNDLE_PATH,
    EXECUTION_HASH,
    audit_bytes,
    build_rapid_r24_halted_audit,
    load_rapid_r24_halted_audit,
)
from patchloop.evals.rapid_workflow_diagnosis import _load_bundle

ROOT = Path(__file__).resolve().parents[1]


def test_r24_halted_audit_is_deterministic_public_and_exact(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("R24 audit must not access the network")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    first = build_rapid_r24_halted_audit(ROOT)
    second = build_rapid_r24_halted_audit(ROOT)
    assert first == second
    assert (ROOT / AUDIT_PATH).read_bytes() == audit_bytes(first)
    assert load_rapid_r24_halted_audit(ROOT) == first
    assert first["execution_hash"] == EXECUTION_HASH
    assert first["evidence_boundary"]["raw_reasoning_read"] is False
    assert first["evidence_boundary"]["hidden_evaluator_content_read"] is False
    assert first["evidence_boundary"]["network_calls_added_by_audit"] == 0


def test_r24_halted_audit_preserves_rows_cost_and_incomplete_comparison() -> None:
    audit = load_rapid_r24_halted_audit(ROOT)
    observed = audit["execution_observation"]
    assert observed["started_rows"] == observed["terminal_rows"] == 3
    assert observed["not_started_rows"] == 3
    assert observed["model_cost_nanos"] == 927_549_000
    assert observed["recorded_model_calls"] == 42
    assert observed["recorded_input_token_count_calls"] == 43
    assert observed["recorded_tool_calls"] == 41
    assert observed["evaluator_reached_rows"] == 0
    assert [row["status"] for row in audit["rows"]] == [
        "failed",
        "failed",
        "failed",
        "not_started",
        "not_started",
        "not_started",
    ]
    assert audit["disposition"]["same_candidate_retry_authorized"] is False
    assert audit["disposition"]["remaining_rows_authorized_to_resume"] is False
    assert audit["disposition"]["v27_promoted"] is False


def test_r24_plan_friction_names_exact_cross_field_mismatch() -> None:
    audit = load_rapid_r24_halted_audit(ROOT)
    diagnosis = audit["failure_diagnosis"]["v27_lifecycle_plan_admission"]
    assert diagnosis["rejected_plan_attempts"] == 3
    assert diagnosis["affected_started_rows"] == 2
    assert diagnosis["all_owner_state_sets_mismatched"] is True
    assert diagnosis["all_transition_sets_escape_owners"] is True
    assert diagnosis["feedback_component_mismatch_projection_present"] is False
    row_2 = audit["rows"][1]
    assert [attempt["accepted"] for attempt in row_2["plan_attempts"]] == [
        True,
        False,
        False,
    ]
    assert row_2["visible_check_results"][0]["check_id"] == ("public-interrupt-runner-lifecycle")
    assert "PUBLIC_CASE:anyio:test-resumed" in row_2["visible_check_results"][0]["failure_summary"]


def test_r24_timeout_is_settled_but_not_continuation_eligible() -> None:
    audit = load_rapid_r24_halted_audit(ROOT)
    timeout = audit["failure_diagnosis"]["row_3_provider_timeout_and_halt"]
    assert timeout["terminal_error"]["type"] == "APITimeoutError"
    assert timeout["input_token_count_finished"] == 12
    assert timeout["contexts_built"] == 12
    assert timeout["model_events_recorded"] == 11
    assert timeout["last_count_and_context_have_no_model_event"] is True
    assert timeout["driver_atomic_terminal_recorded"] is True
    assert timeout["continuation_atomic_check_requires_allowlisted_code"] is False
    assert timeout["artifact_triad_failure_is_policy_mismatch_not_missing_files"] is True


def test_complete_batch_diagnoser_still_rejects_r24_halted_bundle() -> None:
    with pytest.raises(ContractError, match="lacks one batch completion"):
        _load_bundle(ROOT / BUNDLE_PATH)
