from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V24,
    LeanHarnessRequestEvidenceV24,
    build_lean_harness_calibration_manifest,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.runner import AgentRunner
from patchloop.agent.workflow_successor import PROTOCOL_RECOVERY_POLICY
from patchloop.contracts import EventType, MemoryCondition
from patchloop.errors import ContractError
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json
from tests.test_workflow_self_directed_exploration_runner import (
    TASK_PATH,
    _CaptureFirstRequestAdapter,
    _CrashAfterCoverageAdapter,
    _SelfDirectedWorkflowAdapter,
)


def _manifest(run_id: str):
    package = load_task_package("tasks/smoke/config-falsy-override")
    return build_lean_harness_calibration_manifest(
        package,
        run_id=run_id,
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V24,
    )


def _request_payloads(runner: AgentRunner, run_id: str) -> list[dict]:
    values: list[dict] = []
    for event in runner.state.list_events(run_id):
        if event.type != EventType.MODEL_CALLED:
            continue
        values.append(
            json.loads(Path(event.payload["request_artifact_path"]).read_text(encoding="utf-8"))
        )
    return values


def _request_evidence(runner: AgentRunner, run_id: str) -> list[LeanHarnessRequestEvidenceV24]:
    values: list[LeanHarnessRequestEvidenceV24] = []
    for payload in _request_payloads(runner, run_id):
        raw = payload.get("lean_harness_request")
        if not isinstance(raw, dict) or raw.get("schema_version") != (
            "lean-harness-request-evidence-v24"
        ):
            continue
        evidence = validate_persisted_lean_harness_request(payload)
        assert isinstance(evidence, LeanHarnessRequestEvidenceV24)
        values.append(evidence)
    return values


def _context(evidence: LeanHarnessRequestEvidenceV24) -> dict:
    value = json.loads(evidence.request_body["context"])
    assert isinstance(value, dict)
    return value


def _request_bytes(evidence: LeanHarnessRequestEvidenceV24) -> int:
    return len(canonical_json(evidence.request_body).encode("utf-8"))


def test_v24_zero_to_limit_has_exact_surface_and_bounded_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v24_zero_to_limit")
    runner = AgentRunner(tmp_path / "v24-zero-to-limit")
    adapter = _SelfDirectedWorkflowAdapter(prefix="v24-exhaust", exhaust=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    requests = _request_evidence(runner, manifest.run_id)
    context_events = [
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.CONTEXT_BUILT
    ]

    assert result["terminal_error"]["code"] == "SELF_DIRECTED_EXPLORATION_EXHAUSTED"
    assert len(requests) == 11
    assert requests[0].workflow_decision.allowed_tool_names == (
        "search_files",
        "read_file",
    )
    assert requests[1].workflow_decision.allowed_tool_names == (
        "search_files",
        "read_file",
        "record_work_plan",
    )
    assert all(
        "run_check" not in item.workflow_decision.allowed_tool_names
        for item in requests
        if item.self_directed_exploration_state is not None
        and item.self_directed_exploration_state.active_plan_hash is None
    )
    assert all(
        item.exact_pre_plan_surface_projection.durable_state_changed is False for item in requests
    )
    assert all(
        item.bounded_investigation_request_context.model_facing_projection_only is True
        and item.bounded_investigation_request_context.durable_event_changed is False
        and item.bounded_investigation_request_context.durable_ledger_changed is False
        for item in requests
    )
    assert any(
        item.bounded_investigation_request_context.reference_event_count > 0
        for item in requests[2:]
    )
    assert all(
        projection.projected_payload_bytes < projection.source_payload_bytes
        for item in requests
        for projection in item.bounded_investigation_request_context.event_projections
        if projection.disposition == "reference"
    )
    assert all(
        item.bounded_investigation_request_context.projected_context_bytes
        <= item.bounded_investigation_request_context.source_context_bytes
        for item in requests
    )
    assert len(context_events) == len(requests)
    assert all(
        request.bounded_investigation_request_context.source_investigation_ledger_hash
        == json.loads(Path(event.payload["artifact_path"]).read_text(encoding="utf-8"))[
            "context_build"
        ]["investigation_ledger"]["content_hash"]
        for request, event in zip(requests, context_events, strict=True)
    )

    sizes = [_request_bytes(item) for item in requests]
    source_available_size = sizes[1]
    assert max(sizes) <= 90_000
    assert max(sizes) / source_available_size <= 1.25, sizes
    for item in requests:
        context = _context(item)
        ledger = context["investigation_ledger"]
        projection = item.bounded_investigation_request_context
        assert ledger["searches"] == []
        assert len(ledger["recent_details"]) <= 3
        assert len(ledger["tail_policy"]["token_projection"]["observations"]) <= 3
        assert ledger["source_ledger_content_hash"] == (projection.source_investigation_ledger_hash)
        if projection.source_read_body_count:
            assert projection.retained_usable_source_body_count >= 1
    assert not any(
        event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "run_check"
        for event in runner.state.list_events(manifest.run_id)
    )


def test_v24_plan_and_completion_keep_post_mutation_check_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v24_success")
    runner = AgentRunner(tmp_path / "v24-success")
    adapter = _SelfDirectedWorkflowAdapter(prefix="v24-success")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    requests = _request_evidence(runner, manifest.run_id)

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert any(event.type == EventType.PLAN_RECORDED for event in events)
    assert any(event.type == EventType.PATCH_APPLIED for event in events)
    assert any(
        event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "run_check"
        for event in events
    )
    assert any(
        item.self_directed_exploration_state is None
        and "run_check" in item.workflow_decision.allowed_tool_names
        for item in requests
    )


def test_v24_invalid_intent_uses_shared_recovery_without_second_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v24_invalid_intent")
    runner = AgentRunner(tmp_path / "v24-invalid-intent")
    adapter = _SelfDirectedWorkflowAdapter(prefix="v24-invalid", invalid_intent=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    blocked = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == PROTOCOL_RECOVERY_POLICY
    ]

    assert result["terminal_error"]["code"] == "MODEL_ACTION_CONTRACT_REPEATED"
    assert len(blocked) == 1
    assert (
        sum(
            event.type == EventType.TOOL_CALLED and event.payload.get("tool") == "read_file"
            for event in events
        )
        == 1
    )


def test_v24_restart_recovers_identical_projected_context_and_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v24_restart")
    runner = AgentRunner(tmp_path / "v24-restart")
    first = _CrashAfterCoverageAdapter(prefix="v24-restart-first")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    assert first.captured_state is not None

    second = _CaptureFirstRequestAdapter(prefix="v24-restart-second")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert second.first_state == first.captured_state
    assert second.first_tool_names == first.captured_tool_names


def test_v24_persisted_projection_tamper_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("run_v24_tamper")
    runner = AgentRunner(tmp_path / "v24-tamper")
    adapter = _SelfDirectedWorkflowAdapter(prefix="v24-tamper", exhaust=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    runner.start(TASK_PATH, model="mock", manifest=manifest)
    payload = _request_payloads(runner, manifest.run_id)[1]
    tampered = json.loads(canonical_json(payload))
    context = json.loads(tampered["lean_harness_request"]["request_body"]["context"])
    context["investigation_ledger"]["source_ledger_content_hash"] = "sha256:" + "0" * 64
    tampered["lean_harness_request"]["request_body"]["context"] = canonical_json(context)

    with pytest.raises(ContractError):
        validate_persisted_lean_harness_request(tampered)
