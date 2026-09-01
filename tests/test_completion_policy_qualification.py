from __future__ import annotations

import copy
import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.agent.completion_policy_qualification import (
    QUALIFICATION_PATH,
    CompletionPolicyQualification,
    build_completion_policy_qualification,
    load_completion_policy_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _rehash(body: dict) -> dict:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_qualification_covers_state_sequence_shared_retry_and_edit_correction() -> None:
    qualification = build_completion_policy_qualification(REPOSITORY)
    scenarios = {item.scenario_id: item.observed for item in qualification.scenarios}

    assert scenarios["post-mutation-exploration-forces-visible-check"] == {
        "reserve_mode": "exploration",
        "completion_target": "visible-check",
        "selected_tool_names": ("run_check",),
        "completion_lane_active": True,
    }
    assert scenarios["failed-check-forces-correction"]["selected_tool_names"] == ("apply_patch",)
    assert scenarios["passing-check-forces-diff-review"]["selected_tool_names"] == ("get_diff",)
    assert scenarios["presented-diff-forces-submission"]["selected_tool_names"] == ("finish_task",)
    assert scenarios["checkpoint-safe-actionless-retry"]["mode"] == "retry-actionless"
    assert scenarios["checkpoint-safe-reasoning-incomplete-retry"]["mode"] == (
        "retry-reasoning-incomplete"
    )
    assert scenarios["shared-retry-disables-second-reserve"]["mode"] == ("primary-direct-low")
    assert scenarios["raw-edit-bounded-current-source"]["worktree_unchanged"] is True
    assert scenarios["structured-edit-bounded-current-source"]["exact_occurrence_counts"] == [0]
    assert scenarios["v6-consumed-scenario-set-preserved"]["equal"] is True


def test_qualification_is_deterministic_zero_call_and_runtime_closed() -> None:
    first = build_completion_policy_qualification(REPOSITORY)
    second = build_completion_policy_qualification(REPOSITORY)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first.official is False
    assert first.provider_calls == 0
    assert first.docker_calls == 0
    assert first.evaluator_calls == 0
    assert first.added_cost_usd == "0"
    assert first.runtime_activation_authorized is False
    assert first.paid_execution_authorized is False
    assert first.quality_improvement_established is False
    assert first.cumulative_budget_limits_changed is False
    assert first.task_or_evaluator_contract_changed is False
    assert first.task_repository_mutated is False
    assert first.hidden_or_private_data_read is False
    assert first.reference_patch_read is False
    assert first.reasoning_text_read is False


def test_rehashed_authority_or_scenario_drift_fails_closed() -> None:
    qualification = build_completion_policy_qualification(REPOSITORY)
    authority = qualification.model_dump(mode="python")
    authority["paid_execution_authorized"] = True
    _rehash(authority)
    with pytest.raises(ValidationError):
        CompletionPolicyQualification.model_validate(authority)

    scenario = qualification.model_dump(mode="python")
    scenarios = copy.deepcopy(list(scenario["scenarios"]))
    scenarios[0]["observed"]["completion_target"] = "phase-policy"
    scenarios[0]["observation_hash"] = sha256_json(scenarios[0]["observed"])
    scenario["scenarios"] = tuple(scenarios)
    scenario["scenario_set_hash"] = sha256_json(scenarios)
    _rehash(scenario)
    changed = CompletionPolicyQualification.model_validate(scenario)
    assert changed.content_hash != qualification.content_hash


def test_qualification_artifact_is_canonical_and_only_successor_contract_drifted() -> None:
    current = build_completion_policy_qualification(REPOSITORY)
    path = REPOSITORY / QUALIFICATION_PATH

    assert path.is_file()
    consumed = load_completion_policy_qualification(REPOSITORY)
    assert path.read_bytes() == qualification_bytes(consumed)

    current_payload = current.model_dump(mode="json")
    consumed_payload = consumed.model_dump(mode="json")
    current_sources = {row["path"]: row for row in current_payload.pop("source_files")}
    consumed_sources = {row["path"]: row for row in consumed_payload.pop("source_files")}
    current_payload.pop("content_hash")
    consumed_payload.pop("content_hash")

    assert current_payload == consumed_payload
    assert current_sources.keys() == consumed_sources.keys()
    assert [
        path
        for path in current_sources
        if current_sources[path] != consumed_sources[path]
    ] == [
        "patchloop/agent/lean_runtime.py",
        "patchloop/agent/tools.py",
        "patchloop/agent/runner.py",
        "patchloop/contracts.py",
    ]


def test_builder_source_has_no_provider_docker_or_evaluator_dispatch() -> None:
    source = inspect.getsource(build_completion_policy_qualification)

    assert "OpenAIResponses" not in source
    assert "DockerSandbox" not in source
    assert "EvaluationEngine" not in source
