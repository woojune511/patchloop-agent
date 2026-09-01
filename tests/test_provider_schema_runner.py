from __future__ import annotations

import copy
import json
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest

from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V27,
    LeanHarnessRequestEvidenceV27,
    build_lean_harness_calibration_manifest,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.model import ModelTurn, RequestedTool
from patchloop.agent.provider_count_accounting import project_input_token_count_attempts
from patchloop.agent.provider_schema_adapter import StrictOpenAIResponsesAdapter
from patchloop.agent.provider_schema_admission import validate_provider_tool_schemas
from patchloop.agent.runner import AgentRunner
from patchloop.contracts import EventType, MemoryCondition, ModelConfig
from patchloop.sandbox.runner import LocalSandbox, SandboxResult
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json
from tests.test_workflow_r21_reliability_runner import (
    _AnchoredReadAdapter,
    _InvalidInitialPlanOnceAdapter,
    _V26Adapter,
)
from tests.test_workflow_self_directed_exploration_runner import TASK_PATH
from tests.test_workflow_successor_v2_runner import TARGET_PATH


@pytest.fixture(autouse=True)
def no_live_provider_or_container(monkeypatch):
    from patchloop.sandbox import DockerSandbox
    from patchloop.verifier import EvaluationEngine

    def forbidden(*_args, **_kwargs):
        raise AssertionError("V27 tests require fake provider/check/evaluator boundaries")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(DockerSandbox, "available", staticmethod(lambda: False))
    for name in ("image_identity", "run_check", "run_probe"):
        monkeypatch.setattr(DockerSandbox, name, forbidden)
    monkeypatch.setattr(EvaluationEngine, "__init__", forbidden)


def _manifest(run_id: str):
    return build_lean_harness_calibration_manifest(
        load_task_package(Path(TASK_PATH).parent),
        run_id=run_id,
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V27,
    )


def _wire(turn):
    for call in turn.tool_calls:
        if call.name == "read_file":
            for field in ("path", "start_line", "end_line", "search_anchor"):
                call.arguments.setdefault(field, None)
    return turn


class _V27Adapter(_V26Adapter):
    def next_turn(self, context, tools):
        validate_provider_tool_schemas({"tools": tools})
        return _wire(super().next_turn(context, tools))


class _AnchoredV27Adapter(_AnchoredReadAdapter):
    def next_turn(self, context, tools):
        validate_provider_tool_schemas({"tools": tools})
        return _wire(super().next_turn(context, tools))


def _mock_boundaries(runner, monkeypatch):
    """Synthetic results only: no test subprocess or private evaluator is invoked."""

    def check(_self, _workspace, registered):
        return SandboxResult(
            command=registered.command,
            exit_code=0,
            stdout="synthetic public check pass",
            stderr="",
            duration_ms=0,
            timed_out=False,
            truncated=False,
            original_output_bytes=27,
        )

    monkeypatch.setattr(LocalSandbox, "run_check", check)
    monkeypatch.setattr(
        runner,
        "_evaluate",
        lambda *_args, **_kwargs: {
            "mock_submission_boundary_reached": True,
            "official": False,
        },
    )


def _requests(runner, run_id):
    requests = []
    for event in runner.state.list_events(run_id):
        if event.type != EventType.MODEL_CALLED:
            continue
        payload = json.loads(Path(event.payload["request_artifact_path"]).read_bytes())
        evidence = validate_persisted_lean_harness_request(payload)
        assert isinstance(evidence, LeanHarnessRequestEvidenceV27)
        requests.append(evidence)
    return requests


@pytest.mark.parametrize("anchored", [False, True])
def test_v27_mocked_runner_submits_through_strict_dynamic_surfaces(tmp_path, monkeypatch, anchored):
    manifest = _manifest("run_v27_strict_surface")
    runner = AgentRunner(tmp_path / "s")
    _mock_boundaries(runner, monkeypatch)
    adapter = (_AnchoredV27Adapter if anchored else _V27Adapter)(prefix="strict")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    assert result.get("mock_submission_boundary_reached") is True, result.get("terminal_error")
    requests = _requests(runner, manifest.run_id)
    assert requests and all(r.tool_schema_version == "v28" for r in requests)
    assert all(
        r.provider_tool_schema_admission["provider_authority_granted"] is False for r in requests
    )
    names = {name for r in requests for name in r.phase_tool_surface.selected_tool_names}
    assert {
        "record_work_plan",
        "apply_structured_edit",
        "run_check",
        "get_diff",
        "finish_task",
    } <= names
    events = runner.state.list_events(manifest.run_id)
    assert any(e.type == EventType.SUBMISSION_ACCEPTED for e in events)
    assert not any(e.type == EventType.INPUT_TOKEN_COUNT_STARTED for e in events)
    if anchored:
        assert any(e.payload.get("anchored_read_resolution") for e in events)


class _HTTPRejection(Exception):
    status_code = 400
    code = "invalid_function_parameters"


class _FakeProvider:
    """Only observes the public request; cannot inspect runner state or hidden events."""

    def __init__(self, *, fail_count=False, crash_count=False):
        self.max_retries = 0
        self.responses = self
        self.input_tokens = SimpleNamespace(count=self.count)
        self.count_calls = self.create_calls = 0
        self.fail_count = fail_count
        self.crash_count = crash_count
        self.policy = _V27Adapter(prefix="fake-provider")

    def count(self, **kwargs):
        self.count_calls += 1
        if self.crash_count:
            raise SystemExit(87)
        if self.fail_count:
            raise _HTTPRejection("private fixture sentinel must never be persisted")
        validate_provider_tool_schemas(kwargs)
        return SimpleNamespace(input_tokens=100)

    def create(self, **kwargs):
        self.create_calls += 1
        context = kwargs["input"][1]["content"]
        turn = self.policy.next_turn(context, kwargs["tools"])
        return SimpleNamespace(
            id=f"resp_fake_{self.create_calls}",
            model=kwargs["model"],
            service_tier="default",
            status="completed",
            truncation="disabled",
            incomplete_details=None,
            system_fingerprint=None,
            output_text=turn.text,
            output=[
                SimpleNamespace(
                    type="function_call",
                    name=call.name,
                    call_id=call.action_id,
                    arguments=canonical_json(call.arguments),
                )
                for call in turn.tool_calls
            ],
            usage=SimpleNamespace(
                input_tokens=100,
                output_tokens=10,
                total_tokens=110,
                input_tokens_details=None,
                output_tokens_details=None,
            ),
        )


def _provider_adapter(client, *, corrupt_schema=False):
    class Adapter(StrictOpenAIResponsesAdapter):
        def request_payload(self, *args, **kwargs):
            request = copy.deepcopy(super().request_payload(*args, **kwargs))
            if corrupt_schema:
                for tool in request["tools"]:
                    if tool["name"] == "read_file":
                        tool["parameters"]["required"] = []
            return request

    return Adapter(
        ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            transport_max_retries=0,
            max_output_tokens=25_000,
        ),
        client=client,
    )


@pytest.mark.parametrize("corrupt", [False, True])
def test_real_shaped_rejection_has_no_generation_and_honest_count_usage(
    tmp_path, monkeypatch, corrupt
):
    manifest = _manifest("run_v27_rejection")
    runner = AgentRunner(tmp_path / "r")
    client = _FakeProvider(fail_count=True)
    adapter = _provider_adapter(client, corrupt_schema=corrupt)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    assert result["outcome_kind"] == "infrastructure_error", result
    assert result["terminal_error"]["code"] == (
        "PROVIDER_TOOL_SCHEMA_INVALID" if corrupt else "PROVIDER_INPUT_TOKEN_COUNT_FAILED"
    ), result
    assert client.create_calls == 0
    assert client.count_calls == (0 if corrupt else 1)
    assert result["usage"]["input_token_count_calls"] == client.count_calls
    assert result["usage"]["model_calls"] == result["usage"]["tool_calls"] == 0
    assert result["usage"]["model_cost_usd"] == 0
    events = runner.state.list_events(manifest.run_id)
    assert "private fixture sentinel" not in canonical_json(
        [e.model_dump(mode="json") for e in events]
    )
    summary = project_input_token_count_attempts(manifest.run_id, events)
    assert summary["failed"] == client.count_calls
    assert summary["http_request_total"] is None


def test_count_crash_recovers_unknown_without_another_sdk_attempt(tmp_path, monkeypatch):
    manifest = _manifest("run_v27_count_crash")
    runner = AgentRunner(tmp_path / "c")
    client = _FakeProvider(crash_count=True)
    adapter = _provider_adapter(client)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    with pytest.raises(SystemExit, match="87"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    before = project_input_token_count_attempts(
        manifest.run_id, runner.state.list_events(manifest.run_id)
    )
    assert before["outcome_unknown"] == 1
    result = runner.resume(manifest.run_id)
    after = project_input_token_count_attempts(
        manifest.run_id, runner.state.list_events(manifest.run_id)
    )
    assert result["terminal_error"]["code"] == "PROVIDER_INPUT_TOKEN_COUNT_OUTCOME_UNKNOWN", result
    assert before == after
    assert client.count_calls == 1 and client.create_calls == 0
    assert result["usage"]["input_token_count_calls"] == 1


def test_fake_provider_full_runner_counts_are_durable_not_doubled(tmp_path, monkeypatch):
    manifest = _manifest("run_v27_count_success")
    runner = AgentRunner(tmp_path / "p")
    _mock_boundaries(runner, monkeypatch)
    client = _FakeProvider()
    adapter = _provider_adapter(client)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    assert result.get("mock_submission_boundary_reached") is True, result.get("terminal_error")
    events = runner.state.list_events(manifest.run_id)
    summary = project_input_token_count_attempts(manifest.run_id, events)
    assert summary["logical_attempts"] == summary["completed"] == client.count_calls
    assert summary["failed"] == summary["outcome_unknown"] == 0
    assert runner._usage(manifest.run_id).input_token_count_calls == client.count_calls
    assert client.create_calls == runner._usage(manifest.run_id).model_calls
    assert all(r.provider_tool_schema_admission for r in _requests(runner, manifest.run_id))
    first_count = next(e.sequence for e in events if e.type == EventType.INPUT_TOKEN_COUNT_STARTED)
    first_context = next(e.sequence for e in events if e.type == EventType.CONTEXT_BUILT)
    assert first_count < first_context


@pytest.mark.parametrize("review", [False, True])
def test_strict_dynamic_revision_correction_and_review(tmp_path, monkeypatch, review):
    manifest = _manifest("run_v27_revision")
    runner = AgentRunner(tmp_path / "v")
    _mock_boundaries(runner, monkeypatch)
    check_calls = []

    def check(_self, _workspace, registered):
        check_calls.append(registered.id)
        failed = not review and len(check_calls) == 1
        return SandboxResult(
            command=registered.command,
            exit_code=1 if failed else 0,
            stdout="synthetic falsy override mismatch" if failed else "synthetic pass",
            stderr="",
            duration_ms=0,
            timed_out=False,
            truncated=False,
            original_output_bytes=32,
        )

    monkeypatch.setattr(LocalSandbox, "run_check", check)
    adapter = _V27Adapter(prefix="revise", fail_first_mutation=not review, review_correction=review)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    assert result.get("mock_submission_boundary_reached") is True, result.get("terminal_error")
    requests = _requests(runner, manifest.run_id)
    assert any("revise_work_plan" in r.phase_tool_surface.selected_tool_names for r in requests)
    events = runner.state.list_events(manifest.run_id)
    plans = [e for e in events if e.type == EventType.PLAN_RECORDED]
    assert len(plans) == 2
    mutations = [e for e in events if e.type == EventType.PATCH_APPLIED]
    assert len(mutations) == 2
    assert len(check_calls) >= 2 and check_calls[0] == check_calls[1]
    assert any(e.type == EventType.SUBMISSION_ACCEPTED for e in events)


class _IntentAnchorAdapter(_V27Adapter):
    def __init__(self):
        super().__init__(prefix="intent-anchor")
        self.stage = 0

    def next_turn(self, context, tools):
        parsed = json.loads(context)
        workflow = parsed["workflow"]
        state = workflow.get("self_directed_exploration_state")
        if state and state["source_spans"] and self.stage < 2:
            self.stage += 1
            if self.stage == 1:
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "search_files",
                            self._action_id("bound-search"),
                            {
                                "query": "result[key] = value or result.get(key)",
                                "path_glob": TARGET_PATH,
                                "investigation_intent": self._intent(workflow),
                            },
                        )
                    ]
                )
            seq = next(
                e["sequence"]
                for e in reversed(parsed["recent_events"])
                if e.get("type") == "ToolSucceeded" and e["payload"].get("tool") == "search_files"
            )
            return _wire(
                ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "read_file",
                            self._action_id("bound-read"),
                            {
                                "search_anchor": {
                                    "search_event_sequence": seq,
                                    "match_index": 0,
                                    "before_lines": 1,
                                    "after_lines": 1,
                                },
                                "investigation_intent": self._intent(workflow),
                            },
                        )
                    ]
                )
            )
        return super().next_turn(context, tools)


def test_nullable_anchor_with_investigation_intent_is_admitted(tmp_path, monkeypatch):
    manifest = _manifest("run_v27_anchor_intent")
    runner = AgentRunner(tmp_path / "i")
    _mock_boundaries(runner, monkeypatch)
    adapter = _IntentAnchorAdapter()
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    assert result.get("mock_submission_boundary_reached") is True, result.get("terminal_error")
    assert adapter.stage == 2
    calls = [
        e for e in runner.state.list_events(manifest.run_id) if e.type == EventType.TOOL_CALLED
    ]
    assert any(
        e.payload.get("anchored_read_resolution") and e.payload.get("investigation_intent")
        for e in calls
    )


def test_bad_nullable_read_consumes_shared_retry_without_tool_dispatch(tmp_path, monkeypatch):
    class InvalidAdapter:
        def next_turn(self, context, tools):
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "read_file",
                        "invalid",
                        {"path": None, "start_line": None, "end_line": None, "search_anchor": None},
                    )
                ]
            )

    manifest = _manifest("run_v27_invalid_read")
    runner = AgentRunner(tmp_path / "b")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: InvalidAdapter())
    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    assert result["terminal_error"]["code"] == "MODEL_ACTION_CONTRACT_REPEATED", result
    assert result["usage"]["model_calls"] == 2
    assert result["usage"]["tool_calls"] == 0


@pytest.mark.parametrize("crash_point", ["after_intent", "before_finish"])
def test_count_receipt_crash_never_reissues_uncertain_attempt(tmp_path, monkeypatch, crash_point):
    manifest = _manifest("run_v27_receipt_crash")
    runner = AgentRunner(tmp_path / "f")
    client = _FakeProvider()
    adapter = _provider_adapter(client)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    append = runner.state.append_event

    def crash(run_id, kind, **kwargs):
        if crash_point == "before_finish" and kind == EventType.INPUT_TOKEN_COUNT_FINISHED:
            raise SystemExit(88)
        event = append(run_id, kind, **kwargs)
        if crash_point == "after_intent" and kind == EventType.INPUT_TOKEN_COUNT_STARTED:
            raise SystemExit(88)
        return event

    monkeypatch.setattr(runner.state, "append_event", crash)
    with pytest.raises(SystemExit, match="88"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    count_calls = client.count_calls
    assert count_calls == (0 if crash_point == "after_intent" else 1)
    monkeypatch.setattr(runner.state, "append_event", append)
    result = runner.resume(manifest.run_id)
    assert result["terminal_error"]["code"] == "PROVIDER_INPUT_TOKEN_COUNT_OUTCOME_UNKNOWN", result
    assert client.count_calls == count_calls and client.create_calls == 0
    assert result["usage"]["input_token_count_calls"] == 1


def test_strict_plan_feedback_retry_preserves_dynamic_schema_contract(tmp_path, monkeypatch):
    class Adapter(_InvalidInitialPlanOnceAdapter):
        def next_turn(self, context, tools):
            validate_provider_tool_schemas({"tools": tools})
            return _wire(super().next_turn(context, tools))

    manifest = _manifest("run_v27_plan_retry")
    runner = AgentRunner(tmp_path / "pr")
    _mock_boundaries(runner, monkeypatch)
    adapter = Adapter(prefix="plan-retry")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    assert result.get("mock_submission_boundary_reached") is True, result.get("terminal_error")
    assert adapter.plan_attempts == 2
    assert any(
        r.plan_admission_feedback_projection.rejection_count
        for r in _requests(runner, manifest.run_id)
    )


def test_nullable_anchored_read_provenance_and_surface_survive_restart(tmp_path, monkeypatch):
    class PauseAfterRead(_AnchoredV27Adapter):
        captured = None

        def next_turn(self, context, tools):
            state = json.loads(context)["workflow"].get("self_directed_exploration_state")
            if state and state["source_spans"]:
                self.captured = (state, copy.deepcopy(tools))
                raise SystemExit(86)
            return super().next_turn(context, tools)

    class CaptureFirstRequest(_V27Adapter):
        captured = None

        def next_turn(self, context, tools):
            if self.captured is None:
                self.captured = (
                    json.loads(context)["workflow"]["self_directed_exploration_state"],
                    copy.deepcopy(tools),
                )
            return super().next_turn(context, tools)

    manifest = _manifest("run_v27_anchor_restart")
    root = tmp_path / "ar"
    runner = AgentRunner(root)
    _mock_boundaries(runner, monkeypatch)
    first = PauseAfterRead(prefix="anchor-first")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)
    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    before = runner.state.list_events(manifest.run_id)
    read_calls = [
        e
        for e in before
        if e.type == EventType.TOOL_CALLED and e.payload.get("tool") == "read_file"
    ]
    assert len(read_calls) == 1 and read_calls[0].payload["anchored_read_resolution"]
    restarted = AgentRunner(root)
    _mock_boundaries(restarted, monkeypatch)
    second = CaptureFirstRequest(prefix="anchor-second")
    monkeypatch.setattr(restarted, "_model_adapter", lambda *_args, **_kwargs: second)
    result = restarted.resume(manifest.run_id)
    assert result.get("mock_submission_boundary_reached") is True, result.get("terminal_error")
    assert first.captured == second.captured
    after = restarted.state.list_events(manifest.run_id)
    assert [e for e in after if e.sequence <= before[-1].sequence] == before
    assert (
        sum(
            e.type == EventType.TOOL_CALLED and e.correlation_id == read_calls[0].correlation_id
            for e in after
        )
        == 1
    )
