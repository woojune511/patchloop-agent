from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_required_trigger_successor_qualification import (
    IMMUTABLE_PREDECESSOR_FILES,
    QUALIFICATION_PATH,
    build_workflow_required_trigger_successor_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_required_trigger_successor_qualification_binds_the_single_fix() -> None:
    value = build_workflow_required_trigger_successor_qualification(ROOT)
    scenarios = value["scenarios"]
    assert value["successor_runtime"] == "lean-harness-v14"
    assert value["tool_schema_version"] == "v18"
    assert value["context_policy_version"] == "phase-evidence-v24"
    assert value["scope"] == ("single-r11-v12-required-failed-check-trigger-eviction-class")
    assert scenarios["v13_evicted_trigger_reproduction"] == {
        "information_actions": 3,
        "required_trigger_evidence_id": None,
        "allowed_tool_names": ["read_file"],
    }
    pinned = scenarios["v14_pinned_trigger"]
    assert pinned["required_trigger_status"] == "pinned"
    assert pinned["pinned_event_sequences"] == [4]
    assert 4 not in pinned["recent_event_sequences"]
    assert pinned["required_trigger_evidence_id"] == "pev:4"
    assert pinned["target"] == "revise-work-plan"
    assert pinned["allowed_tool_names"] == ["revise_work_plan"]
    unavailable = scenarios["v14_unavailable_trigger"]
    assert unavailable == {
        "required_trigger_status": "unavailable",
        "unavailable_reason": "artifact_binding_invalid",
        "target": "terminal",
        "terminal_reason": "required_workflow_evidence_unavailable",
        "allowed_tool_names": [],
    }


def test_required_trigger_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_required_trigger_successor_qualification(ROOT)
    second = build_workflow_required_trigger_successor_qualification(ROOT)
    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["evidence_boundary"] == {
        "public_only": True,
        "private_task_spec_read": False,
        "hidden_evaluator_content_read": False,
        "reference_patch_read": False,
        "reasoning_text_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "added_cost_usd": "0",
    }
    assert first["runtime_activation_authorized"] is False
    assert first["paid_execution_authorized"] is False
    assert first["quality_improvement_established"] is False


def test_required_trigger_qualification_preserves_predecessor_identities() -> None:
    value = build_workflow_required_trigger_successor_qualification(ROOT)
    identities = {item["path"]: item for item in value["immutable_predecessors"]}
    assert tuple(identities) == IMMUTABLE_PREDECESSOR_FILES
    assert identities[IMMUTABLE_PREDECESSOR_FILES[0]]["file_sha256"] == (
        "sha256:ffbff31ad0d885277bec8961341658a567687d8b9d536ad8104b6d818ba3616d"
    )
    assert identities[IMMUTABLE_PREDECESSOR_FILES[1]]["file_sha256"] == (
        "sha256:66fed2b61499f5d58b4812228591b45cba75390c6ddbe8f9bfe4612191734424"
    )
    assert identities[IMMUTABLE_PREDECESSOR_FILES[2]]["file_sha256"] == (
        "sha256:622744647a01e246170cc1d95d1c4e75c76297dc4d5b71023d15dc2493ef3e05"
    )


def test_required_trigger_qualification_artifact_is_immutable_predecessor() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    stored = json.loads(raw)

    assert len(raw) == 5_879
    assert sha256_bytes(raw) == (
        "sha256:fd3fa74c69fd78253c7d2bec11f6cbd47e28d4043fb007e567298c9002f094a4"
    )
    assert stored["content_hash"] == (
        "sha256:f5dec52a2a41a2a3c54fd283c23f9043bccf6e3f60a37b14b7d2bb639d1f95a1"
    )
    assert raw == qualification_bytes(stored)
