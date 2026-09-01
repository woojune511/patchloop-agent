from __future__ import annotations

import hashlib
from pathlib import Path

from patchloop.agent.workflow_successor_v2_qualification import (
    IMMUTABLE_PREDECESSOR_FILES,
    QUALIFICATION_PATH,
    SCENARIO_IDS,
    SOURCE_FILES,
    WorkflowSuccessorV2Qualification,
    build_workflow_successor_v2_qualification,
    qualification_bytes,
)

ROOT = Path(__file__).resolve().parents[1]


def test_workflow_successor_v2_qualification_binds_all_offline_gates() -> None:
    qualification = build_workflow_successor_v2_qualification(ROOT)

    assert qualification.runtime_versions == ("lean-harness-v11", "lean-harness-v12")
    assert qualification.tool_schema_versions == ("v15", "v16")
    assert qualification.context_policy_versions == (
        "phase-evidence-v21",
        "phase-evidence-v22",
    )
    assert tuple(item.scenario_id for item in qualification.scenarios) == SCENARIO_IDS
    assert tuple(item.path for item in qualification.source_files) == SOURCE_FILES
    assert tuple(item.path for item in qualification.immutable_predecessors) == (
        IMMUTABLE_PREDECESSOR_FILES
    )
    observed = {item.scenario_id: item.observed for item in qualification.scenarios}
    assert observed["v11-r10-failed-plan-one-shot"]["status"] == "targeted_check_failed"
    assert observed["v11-second-admission-terminal"]["terminal_reason"] == (
        "work_plan_admission_repeated"
    )
    assert observed["v12-failed-check-requires-revision"]["mutation_available"] is False
    assert observed["v12-review-correction-requires-revision"]["direct_mutation_available"] is False
    assert observed["v12-tampered-chain-fails-closed"]["tampered_chain_rejected"] is True


def test_workflow_successor_v2_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_successor_v2_qualification(ROOT)
    second = build_workflow_successor_v2_qualification(ROOT)

    assert first == second
    assert qualification_bytes(first) == qualification_bytes(second)
    assert first.provider_calls == 0
    assert first.docker_calls == 0
    assert first.evaluator_calls == 0
    assert first.visible_check_calls == 0
    assert first.added_cost_usd == "0"
    assert first.hidden_or_private_data_read is False
    assert first.reference_patch_read is False
    assert first.reasoning_text_read is False
    assert first.runtime_activation_authorized is False
    assert first.paid_execution_authorized is False
    assert first.quality_improvement_established is False


def test_workflow_successor_v2_qualification_artifact_is_preserved() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    stored = WorkflowSuccessorV2Qualification.model_validate_json(raw)

    assert stored.runtime_versions == ("lean-harness-v11", "lean-harness-v12")
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == (
        "sha256:68c66708a2615fb93bfa8eb86fb829692721e5ee90b49bff060c74c8ff45aed0"
    )
