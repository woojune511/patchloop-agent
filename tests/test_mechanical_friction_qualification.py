from __future__ import annotations

import copy
import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.agent.mechanical_friction_qualification import (
    QUALIFICATION_PATH,
    MechanicalFrictionQualification,
    build_mechanical_friction_qualification,
    load_mechanical_friction_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _rehash(body: dict) -> dict:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_qualification_replays_all_r5_mechanical_failure_successors() -> None:
    qualification = build_mechanical_friction_qualification(REPOSITORY)
    scenarios = {item.scenario_id: item for item in qualification.scenarios}

    assert qualification.runtime_policy_version == "lean-harness-v5"
    assert qualification.tool_schema_version == "v10"
    assert qualification.context_policy_version == "phase-evidence-v15"
    assert scenarios["fresh-current-preimage"].observed["model_supplied_preimage_hashes"] is False
    assert scenarios["typed-failed-visible-check"].observed == {
        "invocation_status": "completed",
        "behavior_status": "failed",
        "correction_required": True,
        "failure_summary_hash": scenarios["typed-failed-visible-check"].observed[
            "failure_summary_hash"
        ],
    }
    assert scenarios["primary-output-reserve"].observed["mode"] == ("primary-reserved")
    assert scenarios["reasoning-only-low-effort-retry"].observed["reasoning_effort"] == "low"
    assert scenarios["tight-budget-direct-low"].observed["effective_max_output_tokens"] == 1_716


def test_qualification_has_zero_external_authority_and_no_quality_claim() -> None:
    qualification = build_mechanical_friction_qualification(REPOSITORY)

    assert qualification.official is False
    assert qualification.provider_calls == 0
    assert qualification.docker_calls == 0
    assert qualification.evaluator_calls == 0
    assert qualification.added_cost_usd == "0"
    assert qualification.runtime_activation_authorized is False
    assert qualification.paid_execution_authorized is False
    assert qualification.quality_improvement_established is False
    assert qualification.task_or_evaluator_contract_changed is False
    assert qualification.hidden_or_private_data_read is False


def test_rehashed_authority_or_scenario_drift_fails_closed() -> None:
    qualification = build_mechanical_friction_qualification(REPOSITORY)
    authority = qualification.model_dump(mode="python")
    authority["paid_execution_authorized"] = True
    _rehash(authority)
    with pytest.raises(ValidationError):
        MechanicalFrictionQualification.model_validate(authority)

    scenario = qualification.model_dump(mode="python")
    scenarios = copy.deepcopy(list(scenario["scenarios"]))
    scenarios[0]["observed"]["model_supplied_preimage_hashes"] = True
    scenarios[0]["observation_hash"] = sha256_json(scenarios[0]["observed"])
    scenario["scenarios"] = tuple(scenarios)
    scenario["scenario_set_hash"] = sha256_json(scenarios)
    _rehash(scenario)
    changed = MechanicalFrictionQualification.model_validate(scenario)
    assert changed.content_hash != qualification.content_hash


def test_consumed_artifact_is_canonical_and_successor_source_drift_is_explicit() -> None:
    current = build_mechanical_friction_qualification(REPOSITORY)
    path = REPOSITORY / QUALIFICATION_PATH

    assert path.is_file()
    consumed = load_mechanical_friction_qualification(REPOSITORY)
    assert path.read_bytes() == qualification_bytes(consumed)
    assert current.scenario_set_hash == consumed.scenario_set_hash
    assert current.runtime_policy_version == consumed.runtime_policy_version
    assert current.tool_schema_version == consumed.tool_schema_version
    assert current.context_policy_version == consumed.context_policy_version
    changed = [
        current_binding.path
        for consumed_binding, current_binding in zip(
            consumed.source_files,
            current.source_files,
            strict=True,
        )
        if consumed_binding != current_binding
    ]
    assert changed == [
        "patchloop/agent/mechanical_friction.py",
        "patchloop/agent/lean_runtime.py",
        "patchloop/agent/tools.py",
        "patchloop/agent/runner.py",
        "patchloop/contracts.py",
    ]
    assert current.content_hash != consumed.content_hash


def test_builder_source_has_no_provider_docker_evaluator_or_task_loader() -> None:
    source = inspect.getsource(build_mechanical_friction_qualification)

    assert "OpenAIResponses" not in source
    assert "DockerSandbox" not in source
    assert "load_task" not in source
    assert "EvaluationEngine" not in source
