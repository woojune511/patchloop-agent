from __future__ import annotations

import inspect
from pathlib import Path

from patchloop.agent.workflow_successor_qualification import (
    QUALIFICATION_PATH,
    WorkflowSuccessorQualification,
    build_workflow_successor_qualification,
    qualification_bytes,
)
from patchloop.agent.workflow_successor_v2_qualification import (
    QUALIFICATION_PATH as SUCCESSOR_V2_QUALIFICATION_PATH,
)
from patchloop.agent.workflow_successor_v2_qualification import (
    WorkflowSuccessorV2Qualification,
)
from patchloop.agent.workflow_successor_v2_qualification import (
    qualification_bytes as successor_v2_qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_workflow_successor_qualification_binds_v9_and_v10_gates() -> None:
    qualification = build_workflow_successor_qualification(ROOT)
    scenarios = {item.scenario_id: item.observed for item in qualification.scenarios}

    assert scenarios["v9-first-visible-check-bound"]["expected_check_id"] == (
        "public-interrupt-runner-lifecycle"
    )
    assert scenarios["v9-third-investigation-forces-read"]["allowed_tool_names"] == ["read_file"]
    assert scenarios["v9-third-investigation-then-edit"]["allowed_tool_names"] == [
        "apply_structured_edit"
    ]
    assert scenarios["v9-edit-rejection-requires-reread"]["allowed_tool_names"] == ["read_file"]
    assert scenarios["v9-correction-attempt-limit"]["terminal_reason"] == (
        "correction_attempt_limit"
    )
    assert scenarios["v9-shared-recovery-reconstructed"]["shared_recovery_remaining"] == 0

    assert scenarios["v10-mutation-hidden-before-plan"]["mutation_available"] is False
    assert scenarios["v10-static-plan-validated"]["reproduction_status"] == ("static_evidence")
    assert scenarios["v10-stale-evidence-rejected"]["rejected"] is True
    assert (
        scenarios["v10-plan-propagates-through-mutation"]["plan_hash"]
        == scenarios["v10-static-plan-validated"]["plan_hash"]
    )
    assert scenarios["v9-request-assembled"]["tool_schema_version"] == "v13"
    assert scenarios["v10-request-assembled"]["tool_schema_version"] == "v14"


def test_workflow_successor_qualification_is_deterministic_zero_call_and_closed() -> None:
    first = build_workflow_successor_qualification(ROOT)
    second = build_workflow_successor_qualification(ROOT)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first.official is False
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


def test_consumed_workflow_qualification_is_bound_as_immutable_predecessor() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    stored = WorkflowSuccessorQualification.model_validate_json(raw)
    successor_raw = (ROOT / SUCCESSOR_V2_QUALIFICATION_PATH).read_bytes()
    successor = WorkflowSuccessorV2Qualification.model_validate_json(successor_raw)
    binding = next(
        item
        for item in successor.immutable_predecessors
        if item.path == QUALIFICATION_PATH.as_posix()
    )

    assert qualification_bytes(stored) == raw
    assert len(successor_raw) == 10_604
    assert sha256_bytes(successor_raw) == (
        "sha256:68c66708a2615fb93bfa8eb86fb829692721e5ee90b49bff060c74c8ff45aed0"
    )
    assert successor.content_hash == (
        "sha256:25f65f814818e96e38f258c66d79d7a7d045b6111473f53fb0e1ff4bb891f4f5"
    )
    assert successor_v2_qualification_bytes(successor) == successor_raw
    assert binding.bytes == len(raw)
    assert binding.file_sha256 == sha256_bytes(raw)
    source = inspect.getsource(build_workflow_successor_qualification)
    assert "OpenAIResponsesAdapter" not in source
    assert "DockerSandbox" not in source
    assert "EvaluationEngine" not in source
