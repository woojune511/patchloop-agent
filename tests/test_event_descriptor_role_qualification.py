from __future__ import annotations

import copy
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.agent.event_descriptor_role_qualification import (
    QUALIFICATION_PATH,
    EventDescriptorRoleQualification,
    build_event_descriptor_role_qualification,
    load_event_descriptor_role_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _rehash(body: dict) -> dict:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_qualification_replays_the_production_gateway_composition() -> None:
    qualification = build_event_descriptor_role_qualification(REPOSITORY)
    scenarios = {item.scenario_id: item.observed for item in qualification.scenarios}

    assert scenarios["legacy-composition-rejected"] == {
        "error": "recent-event artifact binding differs"
    }
    assert scenarios["production-role-distinct-inputs-preserved"] == {
        "mutation_status": "succeeded",
        "blocked_status": "rejected",
        "preserved_descriptor_count": 2,
        "preserved_roles": [
            {
                "event_type": "ToolCalled",
                "tool": "apply_structured_edit",
                "binding_field": "patch_artifact",
            },
            {
                "event_type": "ToolAdmissionBlocked",
                "tool": "run_check",
                "binding_field": "result_artifact",
            },
        ],
    }
    assert scenarios["redundant-admission-result-compacted"] == {
        "removed_descriptor_count": 1,
        "removed_fields": ["result_artifact"],
    }
    assert scenarios["production-context-exact-roundtrip"]["exact_roundtrip"] is True
    assert scenarios["alternate-binding-tamper-rejected"] == {
        "error": "recent-event alternate artifact binding differs"
    }
    assert scenarios["v16-persisted-next-request"]["schema_version"] == (
        "lean-harness-request-evidence-v6"
    )


def test_qualification_is_deterministic_canonical_and_external_authority_closed() -> None:
    first = build_event_descriptor_role_qualification(REPOSITORY)
    second = build_event_descriptor_role_qualification(REPOSITORY)
    consumed = load_event_descriptor_role_qualification(REPOSITORY)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert qualification_bytes(consumed) == (REPOSITORY / QUALIFICATION_PATH).read_bytes()
    current = first.model_dump(mode="json")
    historical = consumed.model_dump(mode="json")
    current_sources = {item["path"]: item for item in current.pop("source_files")}
    historical_sources = {item["path"]: item for item in historical.pop("source_files")}
    current.pop("content_hash")
    historical.pop("content_hash")
    assert current == historical
    assert [
        path for path in current_sources if current_sources[path] != historical_sources[path]
    ] == [
        "patchloop/agent/lean_runtime.py",
        "patchloop/agent/tools.py",
        "patchloop/agent/runner.py",
        "patchloop/contracts.py",
    ]
    assert first.official is False
    assert first.provider_calls == first.docker_calls == first.evaluator_calls == 0
    assert first.added_cost_usd == "0"
    assert first.runtime_activation_authorized is False
    assert first.paid_execution_authorized is False
    assert first.r6_retry_authorized is False
    assert first.quality_improvement_established is False
    assert first.task_repository_mutated is False
    assert first.hidden_or_private_data_read is False


def test_rehashed_authority_or_typed_role_drift_fails_closed() -> None:
    qualification = build_event_descriptor_role_qualification(REPOSITORY)
    authority = qualification.model_dump(mode="python")
    authority["paid_execution_authorized"] = True
    _rehash(authority)
    with pytest.raises(ValidationError):
        EventDescriptorRoleQualification.model_validate(authority)

    role = qualification.model_dump(mode="python")
    scenarios = copy.deepcopy(list(role["scenarios"]))
    scenarios[1]["observed"]["preserved_roles"][0]["binding_field"] = "result_artifact"
    scenarios[1]["observation_hash"] = sha256_json(scenarios[1]["observed"])
    role["scenarios"] = tuple(scenarios)
    role["scenario_set_hash"] = sha256_json(scenarios)
    _rehash(role)
    with pytest.raises(ValidationError, match="preserved roles differ"):
        EventDescriptorRoleQualification.model_validate(role)
