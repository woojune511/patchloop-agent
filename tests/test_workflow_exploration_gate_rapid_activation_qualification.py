from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent import workflow_exploration_gate_rapid_activation_qualification as qual
from patchloop.errors import ContractError
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]


def _stored() -> dict[str, object]:
    raw = (REPOSITORY / qual.QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)
    assert isinstance(value, dict)
    return value


def test_consumed_activation_qualification_is_an_exact_byte_audit() -> None:
    stored = _stored()
    raw = (REPOSITORY / qual.QUALIFICATION_PATH).read_bytes()

    assert raw == qual.qualification_bytes(stored)
    assert len(raw) == 15_102
    assert sha256_bytes(raw) == (
        "sha256:46b11d3e56a6e3f9a3284ef297a2833bb5b16915b42460d3bda43b132a614b64"
    )
    assert stored["content_hash"] == (
        "sha256:bb9ec29fa5e5a5dc655e440b335b56a2d36638fc8efb3c49e1017da41d677944"
    )
    assert stored["verifier_descriptor_hash"] == live_verifier_registry().descriptor_hash_for(
        experiment_id=qual.EXPERIMENT_ID,
        plan_schema=qual.PLAN_SCHEMA,
        plan_kind=qual.PLAN_KIND,
    )


def test_consumed_activation_rejects_current_source_reuse() -> None:
    with pytest.raises(ContractError, match="source changes differ"):
        qual.build_workflow_exploration_gate_rapid_activation_qualification(REPOSITORY)
    with pytest.raises(ContractError, match="source changes differ"):
        qual.load_workflow_exploration_gate_rapid_activation_qualification(REPOSITORY)


def test_activation_allows_only_the_r15_manifest_contract_change() -> None:
    value = _stored()

    assert value["v19_source_transition"]["qualified_behavior_unchanged"] is True
    assert value["three_check_source_transition"]["qualified_behavior_unchanged"] is True
    assert value["v19_source_transition"]["observed_changed_paths"] == [
        "patchloop/contracts.py",
        "tests/test_workflow_exploration_gate_activation_qualification.py",
    ]
    assert value["three_check_source_transition"]["observed_changed_paths"] == [
        "patchloop/contracts.py",
        "tests/test_three_visible_check_runtime_compatibility_qualification.py",
    ]
    assert value["source_preservation"] == {
        "qualified_behavior_unchanged": True,
        "permitted_admission_source_changes": [
            "patchloop/contracts.py",
            "tests/test_workflow_exploration_gate_activation_qualification.py",
            "tests/test_three_visible_check_runtime_compatibility_qualification.py",
        ],
        "consumed_r14_builder_unchanged": True,
        "lean_v18_behavior_modified": False,
        "anyio_v4_modified": False,
        "anyio_v5_visible_check_order": [
            "public-interrupt-runner-lifecycle",
            "public-ordinary-failure-preservation",
            "upstream-pytest-plugin-regression",
        ],
    }


def test_activation_qualification_makes_no_external_claim_or_call() -> None:
    value = _stored()
    boundary = value["evidence_boundary"]

    assert boundary["provider_calls"] == 0
    assert boundary["docker_calls"] == 0
    assert boundary["task_calls"] == 0
    assert boundary["evaluator_calls"] == 0
    assert boundary["visible_check_calls"] == 0
    assert boundary["network_calls"] == 0
    assert boundary["workspace_mutations"] == 0
    assert boundary["added_model_cost_usd"] == "0"
    assert value["rapid_candidate_created_by_qualification"] is False
    assert value["runtime_activation_authorized"] is False
    assert value["paid_execution_authorized"] is False
    assert value["quality_improvement_established"] is False
    assert value["generalization_established"] is False
