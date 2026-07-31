from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from patchloop.contracts import Budget, EventType, ModelConfig, RunManifest
from patchloop.evals.budget import (
    calculate_budget_pressure,
    derive_experiment_budget_pressure,
)
from patchloop.state import StateStore


def _manifest(run_id: str = "run_budget_pressure") -> RunManifest:
    return RunManifest(
        run_id=run_id,
        task_id="budget-pressure-task",
        task_version=1,
        base_commit="a" * 40,
        public_spec_hash="sha256:" + "b" * 64,
        model=ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            max_output_tokens=25_000,
        ),
        budget=Budget(
            max_model_calls=40,
            max_tool_calls=100,
            max_total_tokens=480_000,
            wall_clock_timeout_seconds=1_800,
        ),
        created_at=datetime.now(UTC),
    )


def _event(
    sequence: int,
    event_type: EventType,
    payload: dict,
    *,
    run_id: str = "run_budget_pressure",
) -> dict:
    return {
        "run_id": run_id,
        "sequence": sequence,
        "type": event_type.value,
        "payload": payload,
    }


def _result(run_id: str = "run_budget_pressure") -> dict:
    return {
        "run_id": run_id,
        "usage": {
            "input_tokens": 386_012,
            "output_tokens": 52_471,
            "model_calls": 21,
            "tool_calls": 43,
            "wall_clock_ms": 581_487,
        },
    }


def test_budget_pressure_reconstructs_hf_total_token_block() -> None:
    events = [
        _event(
            1,
            EventType.MODEL_CALLED,
            {
                "requested_input_tokens": 280_000,
                "input_tokens": 280_000,
                "output_tokens": 7_226,
            },
        ),
        _event(
            2,
            EventType.CONTEXT_BUILT,
            {
                "investigation_tail_block_reasons": ["token_tail_reserved"],
                "investigation_tail_remaining_tokens": 192_774,
                "investigation_tail_reserved_tokens": 201_560,
                "investigation_tail_projected_next_input_tokens": 35_312,
                "investigation_tail_projected_model_turns": 5,
            },
        ),
        _event(
            3,
            EventType.TOOL_ADMISSION_BLOCKED,
            {
                "tool": "search_files",
                "reason_codes": ["token_tail_reserved"],
                "tail_policy": {
                    "projection_stage": "post_generation",
                    "token_projection": {
                        "total_tokens_used": 343_178,
                        "remaining_tokens": 136_822,
                        "reserved_tokens": 166_248,
                        "projected_next_input_tokens": 35_312,
                        "projected_model_turns": 4,
                    },
                },
            },
        ),
        _event(
            4,
            EventType.MODEL_CALLED,
            {
                "requested_input_tokens": 140_000,
                "input_tokens": 106_012,
                "output_tokens": 45_245,
            },
        ),
        _event(
            5,
            EventType.CONTEXT_BUILT,
            {
                "investigation_tail_block_reasons": ["token_tail_reserved"],
                "investigation_tail_remaining_tokens": 41_517,
                "investigation_tail_reserved_tokens": 220_255,
                "investigation_tail_projected_next_input_tokens": 39_051,
                "investigation_tail_projected_model_turns": 5,
            },
        ),
        _event(
            6,
            EventType.MODEL_GENERATION_BLOCKED,
            {
                "reason_code": "exact_request_budget_exceeded",
                "requested_input_tokens": 21_688,
                "remaining_tokens": 41_517,
                "max_output_tokens": 25_000,
            },
        ),
    ]

    diagnostic = calculate_budget_pressure(
        _manifest(),
        events,
        _result(),
    )

    assert diagnostic["schema_version"] == "budget-pressure-v1"
    assert diagnostic["binding_dimension"] == "total_tokens"
    assert diagnostic["binding_reason"] == "exact_request_budget_exceeded"
    assert diagnostic["headroom"] == {
        "model_calls": 19,
        "tool_calls": 57,
        "total_tokens": 41_517,
        "wall_clock_ms": 1_218_513,
    }
    assert diagnostic["blocked_tool_count"] == 1
    assert diagnostic["blocked_tool_counts_by_reason"] == {"token_tail_reserved": 1}
    assert diagnostic["token_tail"]["first"]["sequence"] == 2
    assert (
        diagnostic["token_tail"]["first"][
            "minimum_total_budget_to_keep_exploration_open_same_prefix"
        ]
        == 488_787
    )
    assert diagnostic["token_tail"]["maximum"]["sequence"] == 5
    assert diagnostic["token_tail"]["maximum"]["additional_tokens_to_reopen"] == 178_739
    assert (
        diagnostic["token_tail"]["maximum"][
            "minimum_total_budget_to_keep_exploration_open_same_prefix"
        ]
        == 658_739
    )
    assert diagnostic["exact_request"] == {
        "blocked": True,
        "sequence": 6,
        "requested_input_tokens": 21_688,
        "max_output_tokens": 25_000,
        "required_tokens": 46_688,
        "remaining_tokens": 41_517,
        "deficit_tokens": 5_171,
        "minimum_total_budget_same_prefix": 485_171,
        "observed_prefix_minimum_total_budget": 485_171,
    }
    assert diagnostic["counterfactual_same_prefix_only"] is True


@pytest.mark.parametrize(
    ("reason", "dimension"),
    [
        ("model_call_budget_exhausted", "model_calls"),
        ("tool_call_budget_exhausted", "tool_calls"),
        ("wall_clock_budget_exhausted", "wall_clock"),
        ("token_budget_exhausted", "total_tokens"),
    ],
)
def test_budget_pressure_classifies_counter_guard(
    reason: str,
    dimension: str,
) -> None:
    diagnostic = calculate_budget_pressure(
        _manifest(),
        [_event(1, EventType.MODEL_GENERATION_BLOCKED, {"reason_code": reason})],
        _result(),
    )

    assert diagnostic["binding_dimension"] == dimension
    assert diagnostic["binding_reason"] == reason
    assert diagnostic["exact_request"]["blocked"] is False


def test_budget_pressure_uses_terminal_result_when_block_event_is_absent() -> None:
    result = _result()
    result["terminal_error"] = {
        "details": {
            "reason_code": "exact_request_budget_exceeded",
            "requested_input_tokens": 21_688,
            "remaining_tokens": 41_517,
            "max_output_tokens": 25_000,
        }
    }

    diagnostic = calculate_budget_pressure(_manifest(), [], result)

    assert diagnostic["binding_dimension"] == "total_tokens"
    assert diagnostic["exact_request"]["sequence"] is None
    assert diagnostic["exact_request"]["deficit_tokens"] == 5_171
    assert diagnostic["exact_request"]["minimum_total_budget_same_prefix"] == 485_171


def test_experiment_derivation_is_read_only(tmp_path) -> None:
    state = StateStore(tmp_path / "state.sqlite3")
    manifest = _manifest("run_budget_read_only")
    state.create_run(manifest)
    state.append_event(
        manifest.run_id,
        EventType.MODEL_CALLED,
        actor="test-model",
        payload={
            "requested_input_tokens": 1_000,
            "input_tokens": 1_000,
            "output_tokens": 100,
        },
    )
    state.append_event(
        manifest.run_id,
        EventType.MODEL_GENERATION_BLOCKED,
        actor="budget-guard",
        payload={
            "reason_code": "exact_request_budget_exceeded",
            "requested_input_tokens": 20_000,
            "remaining_tokens": 10_000,
            "max_output_tokens": 25_000,
        },
    )
    result_path = tmp_path / "experiment.json"
    result_payload = {
        "experiment_id": "budget-read-only",
        "execution_hash": "sha256:" + "c" * 64,
        "runs": [
            {
                "order": 1,
                "task_id": manifest.task_id,
                "run_id": manifest.run_id,
                "result": {
                    "run_id": manifest.run_id,
                    "usage": {
                        "input_tokens": 1_000,
                        "output_tokens": 100,
                        "model_calls": 1,
                        "tool_calls": 0,
                        "wall_clock_ms": 50,
                    },
                },
            }
        ],
    }
    original_bytes = json.dumps(result_payload).encode("utf-8")
    result_path.write_bytes(original_bytes)
    sequence_before = state.last_sequence(manifest.run_id)

    derived = derive_experiment_budget_pressure(result_path, state)

    assert derived["schema_version"] == "experiment-budget-pressure-v1"
    assert derived["run_count"] == 1
    diagnostic = derived["runs"][0]["diagnostic"]
    assert diagnostic["binding_dimension"] == "total_tokens"
    assert diagnostic["exact_request"]["deficit_tokens"] == 35_000
    assert diagnostic["exact_request"]["minimum_total_budget_same_prefix"] == 515_000
    assert result_path.read_bytes() == original_bytes
    assert state.last_sequence(manifest.run_id) == sequence_before
