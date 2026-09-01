from __future__ import annotations

import inspect
from pathlib import Path

from patchloop.agent.completion_loop_successor_qualification import (
    QUALIFICATION_PATH,
    build_ordered_correction_qualification,
    load_ordered_correction_qualification,
    qualification_bytes,
)

REPOSITORY = Path(__file__).resolve().parents[1]


def test_ordered_correction_qualification_covers_the_exact_state_sequence() -> None:
    qualification = build_ordered_correction_qualification(REPOSITORY)
    scenarios = {item.scenario_id: item.observed for item in qualification.scenarios}

    first = scenarios["post-mutation-binds-first-public-check"]
    assert first["selected_tool_names"] == ["run_check"]
    assert first["bound_check_enum"] == ["public-interrupt-runner-lifecycle"]
    assert first["effective_max_output_tokens"] == 2_048
    assert first["parallel_tool_calls"] is False

    failed = scenarios["failed-check-requires-current-source-read"]
    assert failed["selected_tool_names"] == ["read_file"]
    assert failed["fresh_read_required"] is True

    fresh = scenarios["fresh-read-exposes-one-structured-correction"]
    assert fresh["selected_tool_names"] == ["apply_structured_edit"]
    assert fresh["effective_max_output_tokens"] == 8_192

    rejected = scenarios["edit-rejection-invalidates-prior-read"]
    assert rejected["selected_tool_names"] == ["read_file"]
    assert rejected["latest_edit_failure_sequence"] == 4

    upstream = scenarios["passing-targeted-check-binds-upstream-check"]
    assert upstream["preserve_check_ids"] == ["public-interrupt-runner-lifecycle"]
    assert upstream["bound_check_enum"] == ["upstream-pytest-plugin-regression"]

    assert scenarios["all-public-checks-pass-before-diff-review"][
        "selected_tool_names"
    ] == ["get_diff"]
    assert scenarios["presented-diff-review-binds-submission"][
        "selected_tool_names"
    ] == ["finish_task"]


def test_context_terminal_and_request_evidence_are_bound() -> None:
    qualification = build_ordered_correction_qualification(REPOSITORY)
    scenarios = {item.scenario_id: item.observed for item in qualification.scenarios}

    correction = scenarios["latest-public-edit-correction-appears-once"]
    assert correction["source_full_correction_occurrences"] == 3
    assert correction["projected_full_correction_occurrences"] == 1
    assert correction["raw_trace_mutated"] is False

    terminal = scenarios["explicit-provider-incomplete-precedes-accounting-mismatch"]
    assert terminal["primary_error_code"] == "incomplete_response"
    assert terminal["accounting_mismatch_preserved"] is True

    request = scenarios["v8-request-binds-task-surface-and-small-ceiling"]
    assert request["request_evidence_schema"] == "lean-harness-request-evidence-v8"
    assert request["runtime_policy_version"] == "lean-harness-v8"
    assert request["request_tool_names"] == ["run_check"]
    assert request["max_output_tokens"] == 2_048
    assert request["parallel_tool_calls"] is False
    assert request["one_tool_call_per_response"] is True


def test_qualification_is_deterministic_zero_call_and_live_closed() -> None:
    first = build_ordered_correction_qualification(REPOSITORY)
    second = build_ordered_correction_qualification(REPOSITORY)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first.schema_version == "lean-harness-ordered-correction-qualification-v2"
    assert first.previous_ordered_qualification.path.endswith(
        "lean-harness-ordered-correction-public-qualification-20260824-v1.json"
    )
    assert first.official is False
    assert first.provider_calls == 0
    assert first.docker_calls == 0
    assert first.evaluator_calls == 0
    assert first.visible_check_calls == 0
    assert first.added_cost_usd == "0"
    assert first.runtime_activation_authorized is False
    assert first.paid_execution_authorized is False
    assert first.quality_improvement_established is False
    assert first.hidden_or_private_data_read is False
    assert first.reference_patch_read is False
    assert first.reasoning_text_read is False


def test_qualification_artifact_is_canonical_and_builder_has_no_dispatch() -> None:
    current = build_ordered_correction_qualification(REPOSITORY)
    stored = load_ordered_correction_qualification(REPOSITORY)
    path = REPOSITORY / QUALIFICATION_PATH

    assert path.read_bytes() == qualification_bytes(current)
    assert stored == current

    source = inspect.getsource(build_ordered_correction_qualification)
    assert "OpenAIResponsesAdapter" not in source
    assert "DockerSandbox" not in source
    assert "EvaluationEngine" not in source
