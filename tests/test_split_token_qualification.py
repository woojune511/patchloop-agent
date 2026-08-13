from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from patchloop.agent.investigation import tail_policy
from patchloop.contracts import Budget, EventType, RunEvent
from patchloop.evals.policy_replay import (
    PolicyReplayError,
    _safe_projection_payload,
)
from patchloop.evals.qualification import (
    _cumulative_split_generation_block_payload_valid,
    _tool_admission_call_budget_binding_valid,
)
from patchloop.task_loader import load_task_package

_START = datetime(2026, 8, 14, tzinfo=UTC)


def _event(
    sequence: int,
    event_type: EventType,
    payload: dict[str, object],
    *,
    actor: str = "agent",
) -> RunEvent:
    return RunEvent(
        event_id=f"evt_split_{sequence}",
        run_id="run_split_qualification",
        sequence=sequence,
        type=event_type,
        timestamp=_START + timedelta(seconds=sequence),
        actor=actor,
        payload=payload,
    )


def _budget() -> Budget:
    return Budget(
        max_model_calls=180,
        max_tool_calls=300,
        max_total_tokens=140,
        wall_clock_timeout_seconds=3_600,
        token_budget_schema_version="cumulative-split-v1",
        max_cumulative_input_tokens=100,
        max_cumulative_output_tokens=50,
    )


def _blocked_payload() -> dict[str, object]:
    return {
        "schema_version": "model-generation-block-v4",
        "token_budget_schema_version": "cumulative-split-v1",
        "reason_code": "exact_request_budget_exceeded",
        "error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
        "generation_started": False,
        "request_artifact_id": "artifact-request",
        "request_artifact_path": "requests/request.json",
        "request_artifact_hash": "sha256:" + "a" * 64,
        "request_body_hash": "sha256:" + "b" * 64,
        "requested_input_tokens": 40,
        "max_output_tokens": 15,
        "input_token_count_calls": 1,
        "retry_context_present": False,
        "retry_candidate_content_hash": None,
        "binding_dimension": "input_tokens",
        "exceeded_dimensions": ["input_tokens", "total_tokens"],
        "input_tokens_used": 70,
        "output_tokens_used": 20,
        "total_tokens_used": 90,
        "max_cumulative_input_tokens": 100,
        "max_cumulative_output_tokens": 50,
        "max_total_tokens": 140,
        "remaining_input_tokens": 30,
        "remaining_output_tokens": 30,
        "remaining_total_tokens": 50,
    }


def _admission_payload() -> dict[str, object]:
    task = load_task_package(Path("tasks/dev-validation/moto-query-scanned-count")).public
    events = [
        *[
            _event(
                index,
                EventType.MODEL_CALLED,
                {
                    "requested_input_tokens": 1,
                    "input_tokens": 1,
                    "output_tokens": 1,
                },
            )
            for index in range(1, 8)
        ],
        *[_event(index, EventType.TOOL_CALLED, {}) for index in range(8, 19)],
    ]
    calculated_tail_policy = tail_policy(
        task,
        None,
        context_policy_version="phase-evidence-v6",
        events=events,
        budget=_budget(),
        max_output_tokens=15,
        projection_stage="post_generation",
    )
    reason_codes = calculated_tail_policy["block_reasons"]
    return {
        "schema_version": "tool-admission-blocked-v2",
        "policy_version": "investigation-policy-v2",
        "reason_codes": reason_codes,
        "model_calls_used": 7,
        "max_model_calls": 180,
        "tool_calls_used": 11,
        "max_tool_calls": 300,
        "error_details": {
            "schema_version": "tool-admission-blocked-v2",
            "policy_version": "investigation-policy-v2",
            "reason_codes": reason_codes,
            "remaining_model_calls": 173,
            "remaining_tool_calls": 289,
            "tail_policy": calculated_tail_policy,
        },
    }


def test_bounded_tool_admission_projection_accepts_exact_producer_counters() -> None:
    assert _tool_admission_call_budget_binding_valid(
        _admission_payload(),
        budget=_budget(),
        bounded=True,
    )


def test_bounded_tool_admission_accepts_exact_same_turn_barrier_shape() -> None:
    payload = {
        "schema_version": "tool-admission-blocked-v3",
        "policy_version": "turn-mutation-barrier-v1",
        "reason_codes": ["prior_apply_patch_same_turn"],
        "source_call_index": 1,
        "blocked_call_index": 2,
        "error_details": {
            "schema_version": "tool-admission-blocked-v3",
            "policy_version": "turn-mutation-barrier-v1",
            "reason_codes": ["prior_apply_patch_same_turn"],
        },
    }

    assert _tool_admission_call_budget_binding_valid(
        payload,
        budget=_budget(),
        bounded=True,
    )
    payload["blocked_call_index"] = 1
    assert not _tool_admission_call_budget_binding_valid(
        payload,
        budget=_budget(),
        bounded=True,
    )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("max_model_calls",), None),
        (("error_details", "remaining_model_calls"), 172),
        (("error_details", "tail_policy", "remaining_budget", "tool_calls"), 288),
        (("error_details", "tail_policy", "projection_stage"), "pre_generation"),
        (
            (
                "error_details",
                "tail_policy",
                "remaining_budget",
                "model_calls_after_next_generation",
            ),
            172,
        ),
    ],
)
def test_bounded_tool_admission_projection_rejects_legacy_or_mismatched_counters(
    path: tuple[str, ...],
    value: object,
) -> None:
    payload = _admission_payload()
    selected: Any = payload
    for part in path[:-1]:
        selected = selected[part]
    selected[path[-1]] = value

    assert not _tool_admission_call_budget_binding_valid(
        payload,
        budget=_budget(),
        bounded=True,
    )


def _events(payload: dict[str, object]) -> tuple[list[RunEvent], RunEvent]:
    called = _event(
        1,
        EventType.MODEL_CALLED,
        {
            "input_tokens": 70,
            "output_tokens": 20,
            "duration_ms": 10,
        },
    )
    blocked = _event(
        2,
        EventType.MODEL_GENERATION_BLOCKED,
        payload,
        actor="budget-guard",
    )
    return [called, blocked], blocked


def test_split_generation_block_recomputes_each_cumulative_dimension() -> None:
    payload = _blocked_payload()
    events, blocked = _events(payload)

    assert _cumulative_split_generation_block_payload_valid(
        manifest=SimpleNamespace(budget=_budget()),
        events=events,
        blocked_event=blocked,
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("input_tokens_used", 69),
        ("remaining_output_tokens", 29),
        ("exceeded_dimensions", ["total_tokens", "input_tokens"]),
        ("binding_dimension", "total_tokens"),
        ("token_budget_schema_version", "legacy-total-only"),
    ],
)
def test_split_generation_block_rejects_tampered_projection(
    field: str,
    replacement: object,
) -> None:
    payload = _blocked_payload()
    payload[field] = replacement
    events, blocked = _events(payload)

    assert not _cumulative_split_generation_block_payload_valid(
        manifest=SimpleNamespace(budget=_budget()),
        events=events,
        blocked_event=blocked,
    )


def test_policy_replay_projects_validated_split_dimensions() -> None:
    blocked = _events(_blocked_payload())[1]

    projection = _safe_projection_payload(blocked, apply_call_worktrees={})

    assert projection["schema_version"] == "model-generation-block-v4"
    assert projection["binding_dimension"] == "input_tokens"
    assert projection["exceeded_dimensions"] == ["input_tokens", "total_tokens"]
    assert projection["remaining_input_tokens"] == 30
    assert projection["remaining_output_tokens"] == 30
    assert projection["remaining_total_tokens"] == 50


def test_policy_replay_rejects_inconsistent_split_arithmetic() -> None:
    payload = _blocked_payload()
    payload["remaining_total_tokens"] = 49
    blocked = _events(payload)[1]

    with pytest.raises(
        PolicyReplayError,
        match="remaining_total_tokens is inconsistent",
    ):
        _safe_projection_payload(blocked, apply_call_worktrees={})


def test_policy_replay_preserves_legacy_generation_block_projection() -> None:
    blocked = _event(
        1,
        EventType.MODEL_GENERATION_BLOCKED,
        {
            "schema_version": "model-generation-block-v1",
            "reason_code": "exact_request_budget_exceeded",
            "error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
            "generation_started": False,
            "requested_input_tokens": 40,
            "max_output_tokens": 15,
            "remaining_tokens": 50,
        },
        actor="budget-guard",
    )

    assert _safe_projection_payload(blocked, apply_call_worktrees={}) == {
        "error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
        "reason_code": "exact_request_budget_exceeded",
        "generation_started": False,
        "requested_input_tokens": 40,
        "max_output_tokens": 15,
        "remaining_tokens": 50,
    }
