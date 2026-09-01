from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V22,
    LeanHarnessRequestEvidenceV22,
    build_lean_harness_calibration_manifest,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.runner import AgentRunner
from patchloop.agent.workflow_successor_v2 import WORK_PLAN_ADMISSION_POLICY
from patchloop.contracts import EventType, MemoryCondition
from patchloop.errors import ContractError
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_json
from tests.test_workflow_successor_v2_runner import (
    TASK_PATH,
    _CrashBeforePinnedRetryAdapter,
    _PinnedPlanGateWorkflowAdapter,
)


def _manifest(run_id: str):
    package = load_task_package("tasks/smoke/config-falsy-override")
    return build_lean_harness_calibration_manifest(
        package,
        run_id=run_id,
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V22,
    )


def _model_requests(runner: AgentRunner, run_id: str) -> list[tuple[object, dict, dict]]:
    requests: list[tuple[object, dict, dict]] = []
    for event in runner.state.list_events(run_id):
        if event.type != EventType.MODEL_CALLED:
            continue
        payload = json.loads(
            Path(event.payload["request_artifact_path"]).read_text(encoding="utf-8")
        )
        evidence = payload.get("lean_harness_request")
        if isinstance(evidence, dict) and evidence.get("schema_version") == (
            "lean-harness-request-evidence-v22"
        ):
            validated = validate_persisted_lean_harness_request(payload)
            assert isinstance(validated, LeanHarnessRequestEvidenceV22)
            requests.append((event, evidence, payload))
    return requests


def _plan_requests(runner: AgentRunner, run_id: str) -> list[tuple[object, dict, dict]]:
    return [
        item
        for item in _model_requests(runner, run_id)
        if item[1]["workflow_decision"]["allowed_tool_names"] == ["record_work_plan"]
    ]


def test_v22_success_path_preserves_v21_plan_gate_behavior(tmp_path, monkeypatch) -> None:
    manifest = _manifest("run_v22_bounded_feedback_success")
    runner = AgentRunner(tmp_path / "v22-success")
    adapter = _PinnedPlanGateWorkflowAdapter(prefix="v22-success")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    requests = _model_requests(runner, manifest.run_id)
    plans = _plan_requests(runner, manifest.run_id)

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert len(plans) == 1
    assert all(
        request[1]["plan_admission_feedback_projection"]["projected_event_count"] == 0
        for request in requests
    )
    assert sum(event.type == EventType.PLAN_RECORDED for event in events) == 1
    assert all(
        event.payload.get("plan_hash") for event in events if event.type == EventType.PATCH_APPLIED
    )


def test_v22_bounds_retry_feedback_without_changing_durable_failure(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _manifest("run_v22_bounded_feedback_retry")
    runner = AgentRunner(tmp_path / "v22-retry")
    adapter = _PinnedPlanGateWorkflowAdapter(
        prefix="v22-retry",
        invalid_closure=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plans = _plan_requests(runner, manifest.run_id)
    failures = [
        event
        for event in events
        if event.type == EventType.TOOL_FAILED and event.payload.get("tool") == "record_work_plan"
    ]
    blocked = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == WORK_PLAN_ADMISSION_POLICY
    ]

    assert result["terminal_error"]["code"] == "WORK_PLAN_ADMISSION_REPEATED"
    assert len(plans) == len(failures) == len(blocked) == 2
    first_projection = plans[0][1]["plan_admission_feedback_projection"]
    retry_projection = plans[1][1]["plan_admission_feedback_projection"]
    assert first_projection["projected_event_count"] == 0
    assert retry_projection["projected_event_count"] == 1
    assert retry_projection["context_bytes_saved"] > 30_000
    assert plans[1][1]["requested_input_tokens"] < 90_000
    assert plans[1][1]["requested_input_tokens"] < 0.8 * 110_000
    assert retry_projection["event_projections"][0]["projected_error_details_bytes"] <= 4_096

    durable_details = failures[0].payload["error_details"]
    assert isinstance(durable_details["eligible_plan_evidence_catalog"], dict)
    assert isinstance(durable_details["activated_exploration_plan_request"], dict)
    assert isinstance(durable_details["causal_plan_request_projection"], dict)
    assert (
        durable_details["activated_exploration_plan_request_hash"]
        == durable_details["activated_exploration_plan_request"]["content_hash"]
    )
    artifact = json.loads(Path(failures[0].payload["artifact_path"]).read_text(encoding="utf-8"))
    assert artifact["error_details"] == durable_details
    assert not any(
        event.type == EventType.MODEL_CALLED and event.sequence > blocked[-1].sequence
        for event in events
    )


def test_v22_restart_recovers_pin_and_bounded_feedback_once(tmp_path, monkeypatch) -> None:
    manifest = _manifest("run_v22_bounded_feedback_restart")
    runner = AgentRunner(tmp_path / "v22-restart")
    first = _CrashBeforePinnedRetryAdapter(prefix="v22-restart-first")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    before = runner.state.list_events(manifest.run_id)
    assert sum(event.type == EventType.TOOL_ADMISSION_BLOCKED for event in before) == 1
    assert sum(event.type == EventType.PLAN_RECORDED for event in before) == 0

    second = _PinnedPlanGateWorkflowAdapter(prefix="v22-restart-second")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    after = runner.state.list_events(manifest.run_id)
    plans = _plan_requests(runner, manifest.run_id)

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert sum(event.type == EventType.PLAN_RECORDED for event in after) == 1
    assert [item[1]["plan_gate_readiness_source"] for item in plans] == [
        "current_request",
        "recovered_pin",
    ]
    assert plans[1][1]["plan_admission_feedback_projection"]["projected_event_count"] == 1
    assert (
        plans[1][1]["recovered_plan_gate_pin"]["source_model_event_sequence"]
        == plans[0][0].sequence
    )


def test_v22_persisted_projection_tamper_fails_closed(tmp_path, monkeypatch) -> None:
    manifest = _manifest("run_v22_bounded_feedback_tamper")
    runner = AgentRunner(tmp_path / "v22-tamper")
    adapter = _PinnedPlanGateWorkflowAdapter(
        prefix="v22-tamper",
        invalid_closure=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    runner.start(TASK_PATH, model="mock", manifest=manifest)
    retry_payload = _plan_requests(runner, manifest.run_id)[1][2]

    tampered = copy.deepcopy(retry_payload)
    evidence = tampered["lean_harness_request"]
    projection = evidence["plan_admission_feedback_projection"]
    projection["event_projections"][0]["source_event_hash"] = sha256_json("tampered")
    projection_body = {key: value for key, value in projection.items() if key != "content_hash"}
    projection["content_hash"] = sha256_json(projection_body)
    evidence["plan_admission_feedback_projection_hash"] = projection["content_hash"]
    evidence_body = {key: value for key, value in evidence.items() if key != "content_hash"}
    evidence["content_hash"] = sha256_json(evidence_body)

    with pytest.raises(ContractError, match="persisted request evidence is invalid"):
        validate_persisted_lean_harness_request(tampered)
