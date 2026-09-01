from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.three_visible_check_runtime_compatibility_qualification import (
    EXPECTED_CHECK_ORDER,
    IMMUTABLE_PREDECESSORS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_three_visible_check_runtime_compatibility_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_three_check_qualification_is_deterministic_and_zero_call() -> None:
    first = build_three_visible_check_runtime_compatibility_qualification(ROOT)
    second = build_three_visible_check_runtime_compatibility_qualification(ROOT)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-source-qualified"
    assert first["runtime_source_compatible"] is True
    assert first["runtime_source_modified"] is False
    assert first["rapid_candidate_created"] is False
    assert first["paid_execution_authorized"] is False
    assert first["quality_improvement_established"] is False
    assert all(
        first["evidence_boundary"][key] == 0
        for key in (
            "provider_calls",
            "docker_calls",
            "evaluator_calls",
            "visible_check_calls",
            "network_calls",
            "workspace_mutations",
        )
    )


def test_three_check_plan_and_completion_surfaces_preserve_exact_order() -> None:
    value = build_three_visible_check_runtime_compatibility_qualification(ROOT)
    scenarios = value["scenarios"]
    expected = list(EXPECTED_CHECK_ORDER)

    assert scenarios["public_task_projection"]["visible_check_order"] == expected
    assert scenarios["plan_projection"]["task_spec_check_order"] == expected
    assert scenarios["plan_projection"]["projected_plan_check_order"] == expected
    assert scenarios["plan_projection"]["durable_plan_check_order"] == expected
    assert scenarios["plan_projection"]["dynamic_initial_check_enum"] == [expected[0]]
    assert scenarios["plan_projection"]["server_owned_check_order"] is True
    assert scenarios["plan_projection"]["model_authors_check_order"] is False

    states = scenarios["completion_projection"]["ordered_states"]
    assert [item["phase"] for item in states] == [
        "IMPLEMENT",
        "VERIFY",
        "VERIFY",
        "VERIFY",
    ]
    assert [item["run_check_enum"] for item in states] == [
        [expected[0]],
        [expected[1]],
        [expected[2]],
        None,
    ]
    assert states[-1]["target"] == "diff-review"
    assert states[-1]["selected_tools"] == ["get_diff"]
    assert scenarios["tail_reserve"] == {
        "tool_calls": 10,
        "model_calls": 3,
        "feedback_model_calls": 1,
    }


def test_middle_failure_blocks_upstream_and_correction_restarts_at_first_check() -> None:
    value = build_three_visible_check_runtime_compatibility_qualification(ROOT)
    completion = value["scenarios"]["completion_projection"]
    failed = completion["middle_check_failure"]
    corrected = completion["post_correction_invalidation"]

    assert failed["completed_checks"] == [EXPECTED_CHECK_ORDER[0]]
    assert failed["pending_checks"] == list(EXPECTED_CHECK_ORDER[1:])
    assert failed["target"] == "correction-investigation"
    assert failed["selected_tools"] == ["search_files", "read_file"]
    assert failed["upstream_exposed"] is False
    assert failed["trigger_kind"] == "visible_check_result"
    assert failed["trigger_check_index"] == 1
    assert failed["trigger_check_id"] == EXPECTED_CHECK_ORDER[1]

    assert corrected["completed_checks"] == []
    assert corrected["pending_checks"] == list(EXPECTED_CHECK_ORDER)
    assert corrected["target"] == "visible-check"
    assert corrected["run_check_enum"] == [EXPECTED_CHECK_ORDER[0]]


def test_runner_phase_path_accepts_multiple_passes_and_returns_on_failure() -> None:
    value = build_three_visible_check_runtime_compatibility_qualification(ROOT)
    phase = value["scenarios"]["phase_projection"]

    assert phase == {
        "after_first_pass": "VERIFY",
        "after_second_pass": "VERIFY",
        "after_third_pass": "VERIFY",
        "after_middle_failure": "IMPLEMENT",
        "recorded_transitions": [
            ["IMPLEMENT", "VERIFY"],
            ["VERIFY", "IMPLEMENT"],
        ],
        "workspace_accessed": False,
    }


def test_three_check_stored_qualification_remains_an_immutable_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert [item["path"] for item in value["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in value["immutable_predecessors"]] == list(
        IMMUTABLE_PREDECESSORS
    )
    assert raw == qualification_bytes(value)
    assert len(raw) == 7_395
    assert sha256_bytes(raw) == (
        "sha256:74c1acdf905b417ae9d8d094228d1fd79eda7c95a8f0c354e91a4ffed9a4fef9"
    )
