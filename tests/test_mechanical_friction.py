from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from patchloop.agent.mechanical_friction import (
    COMPLETION_RESPONSE_RECOVERY_OUTPUT_RESERVE,
    INCOMPLETE_RECOVERY_OUTPUT_RESERVE,
    CompletionResponseRecovery,
    ReasoningIncompleteRecovery,
    project_completion_response_recovery,
    project_reasoning_incomplete_recovery,
    project_registered_check_outcome,
)
from patchloop.agent.structured_edit import (
    FreshStructuredEditArguments,
    FreshStructuredFileEdit,
    FreshStructuredReplacement,
    project_fresh_atomic_structured_edit,
)
from patchloop.contracts import Budget, EventType, RunEvent, TaskConstraints, Usage
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes, sha256_json


def _budget() -> Budget:
    return Budget(
        max_model_calls=240,
        max_tool_calls=400,
        max_total_tokens=1_100_000,
        wall_clock_timeout_seconds=3_600,
        token_budget_schema_version="cumulative-split-v1",
        max_cumulative_input_tokens=1_000_000,
        max_cumulative_output_tokens=100_000,
    )


def _fresh_args(expected: str, replacement: str) -> FreshStructuredEditArguments:
    return FreshStructuredEditArguments(
        files=(
            FreshStructuredFileEdit(
                path="src/example.py",
                replacements=(
                    FreshStructuredReplacement(
                        expected_text=expected,
                        replacement_text=replacement,
                    ),
                ),
            ),
        ),
    )


def _event(sequence: int, payload: dict[str, object]) -> RunEvent:
    return RunEvent(
        event_id=f"event-{sequence}",
        run_id="run-mechanical-friction",
        sequence=sequence,
        type=EventType.MODEL_CALLED,
        timestamp=datetime(2026, 8, 23, tzinfo=UTC),
        actor="model-adapter",
        payload=payload,
    )


def test_fresh_structured_edit_uses_current_preimage_not_stale_model_hash() -> None:
    current = b"before current target after\n"
    projection = project_fresh_atomic_structured_edit(
        action_id="fresh-edit",
        arguments=_fresh_args("current target", "fixed target"),
        source_worktree_diff_hash="sha256:" + "1" * 64,
        preimages={"src/example.py": current},
        constraints=TaskConstraints(allowed_paths=["src/**"]),
    )

    assert projection.refreshed_file_hashes == {"src/example.py": sha256_bytes(current)}
    assert projection.model_supplied_preimage_hashes is False
    assert projection.model_supplied_byte_offsets is False
    assert projection.atomic_projection.files[0].postimage_text == ("before fixed target after\n")


def test_fresh_structured_edit_preserves_crlf_and_rejects_ambiguous_text() -> None:
    projection = project_fresh_atomic_structured_edit(
        action_id="fresh-crlf",
        arguments=_fresh_args("alpha\ntarget", "alpha\nfixed"),
        source_worktree_diff_hash="sha256:" + "2" * 64,
        preimages={"src/example.py": b"alpha\r\ntarget\r\n"},
        constraints=TaskConstraints(allowed_paths=["src/**"]),
    )
    assert projection.atomic_projection.files[0].postimage_text == "alpha\r\nfixed\r\n"

    with pytest.raises(ValueError, match="ambiguous"):
        project_fresh_atomic_structured_edit(
            action_id="fresh-ambiguous",
            arguments=_fresh_args("target", "fixed"),
            source_worktree_diff_hash="sha256:" + "3" * 64,
            preimages={"src/example.py": b"target target\n"},
            constraints=TaskConstraints(allowed_paths=["src/**"]),
        )


def test_check_invocation_success_is_distinct_from_behavior_failure() -> None:
    outcome = project_registered_check_outcome(
        check_id="public-check",
        exit_code=1,
        passed=False,
        timed_out=False,
        truncated=False,
        stdout="",
        stderr="expected cleanup before cancellation",
        worktree_diff_hash="sha256:" + "4" * 64,
    )

    assert outcome.invocation_status == "completed"
    assert outcome.behavior_status == "failed"
    assert outcome.correction_required is True
    assert outcome.failure_summary == "expected cleanup before cancellation"


def test_finalization_reserves_one_retry_then_rebuilds_it_at_low_effort() -> None:
    primary = project_reasoning_incomplete_recovery(
        phase_mode="finalization",
        events=(),
        usage=Usage(input_tokens=900_000, output_tokens=60_000),
        budget=_budget(),
        requested_input_tokens=5_000,
        configured_max_output_tokens=25_000,
    )
    assert primary.mode == "primary-reserved"
    assert primary.effective_max_output_tokens == 25_000
    assert primary.reserved_retry_output_tokens == INCOMPLETE_RECOVERY_OUTPUT_RESERVE
    assert primary.reasoning_effort == "medium"

    incomplete = _event(
        1,
        {
            "response_error_code": "incomplete_response",
            "response_incomplete_reason": "max_output_tokens",
            "output_tokens": 25_000,
            "reasoning_output_tokens": 25_000,
            "lean_incomplete_recovery_mode": primary.mode,
            "lean_reserved_retry_output_tokens": (primary.reserved_retry_output_tokens),
            "response_text_present": False,
            "response_tool_call_count": 0,
        },
    )
    retry = project_reasoning_incomplete_recovery(
        phase_mode="finalization",
        events=(incomplete,),
        usage=Usage(input_tokens=905_000, output_tokens=85_000, model_calls=1),
        budget=_budget(),
        requested_input_tokens=5_000,
        configured_max_output_tokens=25_000,
    )
    assert retry.mode == "retry"
    assert retry.effective_max_output_tokens == INCOMPLETE_RECOVERY_OUTPUT_RESERVE
    assert retry.reasoning_effort == "low"
    assert retry.retry_available_after_response is False
    assert retry.source_event_sequence == 1


def test_retry_is_run_global_and_partial_incomplete_fails_closed() -> None:
    consumed_retry = _event(
        1,
        {
            "lean_incomplete_recovery_mode": "retry",
            "response_text_present": False,
            "response_tool_call_count": 1,
        },
    )
    after_retry = project_reasoning_incomplete_recovery(
        phase_mode="finalization",
        events=(consumed_retry,),
        usage=Usage(input_tokens=900_000, output_tokens=60_000, model_calls=1),
        budget=_budget(),
        requested_input_tokens=5_000,
        configured_max_output_tokens=25_000,
    )
    assert after_retry.mode == "primary-direct-low"
    assert after_retry.retry_already_consumed is True
    assert after_retry.reserved_retry_output_tokens == 0

    partial_incomplete = _event(
        2,
        {
            "response_error_code": "incomplete_response",
            "response_incomplete_reason": "max_output_tokens",
            "output_tokens": 25_000,
            "reasoning_output_tokens": 24_999,
            "lean_incomplete_recovery_mode": "primary-reserved",
            "lean_reserved_retry_output_tokens": 2_048,
            "response_text_present": True,
            "response_tool_call_count": 0,
        },
    )
    with pytest.raises(ContractError, match="not eligible"):
        project_reasoning_incomplete_recovery(
            phase_mode="finalization",
            events=(partial_incomplete,),
            usage=Usage(input_tokens=905_000, output_tokens=85_000, model_calls=1),
            budget=_budget(),
            requested_input_tokens=5_000,
            configured_max_output_tokens=25_000,
        )


def test_tight_final_budget_uses_low_effort_without_inventing_retry_capacity() -> None:
    projection = project_reasoning_incomplete_recovery(
        phase_mode="finalization",
        events=(),
        usage=Usage(input_tokens=990_000, output_tokens=98_284),
        budget=_budget(),
        requested_input_tokens=5_000,
        configured_max_output_tokens=25_000,
    )
    assert projection.mode == "primary-direct-low"
    assert projection.effective_max_output_tokens == 1_716
    assert projection.reserved_retry_output_tokens == 0
    assert projection.reasoning_effort == "low"


def test_post_mutation_completion_lane_reserves_one_shared_retry() -> None:
    primary = project_completion_response_recovery(
        phase_mode="exploration",
        completion_lane_active=True,
        events=(),
        usage=Usage(input_tokens=200_000, output_tokens=10_000, model_calls=5),
        budget=_budget(),
        requested_input_tokens=5_000,
        configured_max_output_tokens=25_000,
    )

    assert primary.mode == "primary-reserved"
    assert primary.completion_lane_active is True
    assert primary.action_only_required is True
    assert primary.reserved_retry_output_tokens == (COMPLETION_RESPONSE_RECOVERY_OUTPUT_RESERVE)
    assert primary.effective_max_output_tokens == 22_952


def test_actionless_and_reasoning_incomplete_share_one_retry_slot() -> None:
    actionless = _event(
        1,
        {
            "response_error_code": None,
            "response_text_present": True,
            "response_tool_call_count": 0,
            "lean_response_done": False,
            "lean_completion_recovery_mode": "primary-reserved",
            "lean_reserved_completion_retry_output_tokens": 2_048,
        },
    )
    actionless_retry = project_completion_response_recovery(
        phase_mode="exploration",
        completion_lane_active=True,
        events=(actionless,),
        usage=Usage(input_tokens=205_000, output_tokens=15_000, model_calls=6),
        budget=_budget(),
        requested_input_tokens=5_000,
        configured_max_output_tokens=25_000,
    )
    assert actionless_retry.mode == "retry-actionless"
    assert actionless_retry.source_response_kind == "actionless"
    assert actionless_retry.effective_max_output_tokens == 2_048
    assert actionless_retry.reasoning_effort == "low"

    consumed = _event(
        2,
        {
            "response_error_code": None,
            "response_tool_call_count": 1,
            "lean_response_done": False,
            "lean_completion_recovery_mode": "retry-actionless",
        },
    )
    after_shared_retry = project_completion_response_recovery(
        phase_mode="finalization",
        completion_lane_active=True,
        events=(actionless, consumed),
        usage=Usage(input_tokens=210_000, output_tokens=16_000, model_calls=7),
        budget=_budget(),
        requested_input_tokens=5_000,
        configured_max_output_tokens=25_000,
    )
    assert after_shared_retry.mode == "primary-direct-low"
    assert after_shared_retry.retry_already_consumed is True
    assert after_shared_retry.reserved_retry_output_tokens == 0

    incomplete = _event(
        3,
        {
            "response_error_code": "incomplete_response",
            "response_incomplete_reason": "max_output_tokens",
            "output_tokens": 22_952,
            "reasoning_output_tokens": 22_952,
            "response_text_present": False,
            "response_tool_call_count": 0,
            "lean_response_done": False,
            "lean_completion_recovery_mode": "primary-reserved",
            "lean_reserved_completion_retry_output_tokens": 2_048,
        },
    )
    reasoning_retry = project_completion_response_recovery(
        phase_mode="finalization",
        completion_lane_active=True,
        events=(incomplete,),
        usage=Usage(input_tokens=205_000, output_tokens=32_952, model_calls=6),
        budget=_budget(),
        requested_input_tokens=5_000,
        configured_max_output_tokens=25_000,
    )
    assert reasoning_retry.mode == "retry-reasoning-incomplete"
    assert reasoning_retry.source_response_kind == "reasoning-only-incomplete"


def test_completion_recovery_fails_before_unfundable_redispatch() -> None:
    with pytest.raises(ContractError, match="another model call"):
        project_completion_response_recovery(
            phase_mode="finalization",
            completion_lane_active=True,
            events=(),
            usage=Usage(model_calls=240),
            budget=_budget(),
            requested_input_tokens=1_000,
            configured_max_output_tokens=25_000,
        )

    with pytest.raises(ContractError, match="positive response"):
        project_completion_response_recovery(
            phase_mode="finalization",
            completion_lane_active=True,
            events=(),
            usage=Usage(input_tokens=999_000, output_tokens=100_000),
            budget=_budget(),
            requested_input_tokens=1_000,
            configured_max_output_tokens=25_000,
        )


def test_rehashed_mechanical_contracts_fail_closed() -> None:
    outcome = project_registered_check_outcome(
        check_id="public-check",
        exit_code=0,
        passed=True,
        timed_out=False,
        truncated=False,
        stdout="ok",
        stderr="",
        worktree_diff_hash="sha256:" + "5" * 64,
    )
    body = outcome.model_dump(mode="python")
    body["behavior_status"] = "failed"
    body["correction_required"] = True
    body["failure_summary"] = "tampered"
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError, match="behavior status"):
        type(outcome).model_validate(body)

    recovery = project_reasoning_incomplete_recovery(
        phase_mode="exploration",
        events=(),
        usage=Usage(),
        budget=_budget(),
        requested_input_tokens=1_000,
        configured_max_output_tokens=25_000,
    )
    recovery_body = recovery.model_dump(mode="python")
    recovery_body["provider_calls_authorized"] = True
    recovery_body["content_hash"] = sha256_json(
        {key: value for key, value in recovery_body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError):
        ReasoningIncompleteRecovery.model_validate(recovery_body)

    completion = project_completion_response_recovery(
        phase_mode="exploration",
        completion_lane_active=False,
        events=(),
        usage=Usage(),
        budget=_budget(),
        requested_input_tokens=1_000,
        configured_max_output_tokens=25_000,
    )
    completion_body = completion.model_dump(mode="python")
    completion_body["provider_calls_authorized"] = True
    completion_body["content_hash"] = sha256_json(
        {key: value for key, value in completion_body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError):
        CompletionResponseRecovery.model_validate(completion_body)
