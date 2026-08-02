from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from patchloop.agent.model import (
    MOCK_TASK_SCRIPTS,
    OpenAIResponsesAdapter,
    RequestedTool,
)
from patchloop.agent.runner import AgentRunner
from patchloop.contracts import (
    Budget,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
)
from patchloop.evals.qualification import (
    _v11_coverage_rejection_recovery_evidence,
)
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package
from tests.test_coverage_rejection_v11 import (
    _tampered_events,
    _wrong_target_review,
)
from tests.test_coverage_review_v10 import (
    TASK,
    _review_arguments,
    _smoke_v2_contract,
)

LIVE_BUDGET = Budget(
    max_model_calls=60,
    max_tool_calls=100,
    max_total_tokens=1_200_000,
    wall_clock_timeout_seconds=1_800,
)


def _live_experiment(run_label: str) -> ExperimentRunContext:
    return ExperimentRunContext(
        experiment_id=(
            "dev-no-memory-coverage-rejection-v11-pilot-20260802-r1"
        ),
        purpose=(
            ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT
        ),
        suite_hash="sha256:" + ("a" * 64),
        execution_hash="sha256:" + ("b" * 64),
        schedule_seed=20260723,
        schedule_order=1,
        schedule_row_id="sha256:" + ("c" * 64),
        repetition=1,
    )


def _live_manifest(package, contract, *, run_label: str):
    return build_manifest(
        package,
        run_id=f"run_d072_{run_label}",
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        sandbox_backend="local",
        budget=LIVE_BUDGET,
        max_output_tokens=25_000,
        experiment_context=_live_experiment(run_label),
        coverage_rejection_live_pilot=True,
        public_review_contract=contract,
    )


def _evidence(runner, manifest, package, events):
    return _v11_coverage_rejection_recovery_evidence(
        root=runner.root,
        manifest=manifest,
        package=package,
        events=events,
        context_events=[
            event
            for event in events
            if event.type == EventType.CONTEXT_BUILT
        ],
        worker_claims=runner.state.list_worker_claims(manifest.run_id),
    )


def _fake_openai_response(
    *,
    input_tokens: int,
    tool_call: RequestedTool,
    response_id: str,
):
    return SimpleNamespace(
        id=response_id,
        model="gpt-5.4-mini-2026-03-17",
        service_tier="default",
        system_fingerprint="d072-test-fingerprint",
        status="completed",
        truncation="disabled",
        incomplete_details=None,
        output=[
            SimpleNamespace(
                type="function_call",
                name=tool_call.name,
                call_id=tool_call.action_id,
                arguments=json.dumps(tool_call.arguments),
            )
        ],
        output_text="",
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=1,
            total_tokens=input_tokens + 1,
            input_tokens_details=SimpleNamespace(
                cached_tokens=0,
                cache_write_tokens=0,
            ),
            output_tokens_details=SimpleNamespace(reasoning_tokens=0),
        ),
    )


class _ScriptedResponses:
    """In-memory Responses API double; it never reads credentials or network."""

    def __init__(self, steps, *, label: str) -> None:
        self.steps = list(steps)
        self.label = label
        self.count_requests: list[dict] = []
        self.create_requests: list[dict] = []
        self.input_tokens = SimpleNamespace(count=self.count)

    def count(self, **request):
        self.count_requests.append(request)
        return SimpleNamespace(input_tokens=1_000)

    def create(self, **request):
        index = len(self.create_requests)
        if index >= len(self.steps):
            raise AssertionError("scripted provider received an extra generation")
        self.create_requests.append(request)
        context = request["input"][1]["content"]
        step = self.steps[index]
        tool_call = step(context) if callable(step) else step
        return _fake_openai_response(
            input_tokens=1_000,
            tool_call=tool_call,
            response_id=f"resp_d072_{self.label}_{index + 1}",
        )


def test_generic_v11_without_rejection_remains_strict() -> None:
    package = load_task_package(TASK.parent)
    contract = _smoke_v2_contract(package)
    manifest = build_manifest(
        package,
        run_id="run_d072_offline_strict",
        coverage_rejection_validation=True,
        public_review_contract=contract,
    )

    passed, details = _v11_coverage_rejection_recovery_evidence(
        root=TASK.parent,
        manifest=manifest,
        package=package,
        events=[],
        context_events=[],
        worker_claims=[],
    )

    assert passed is False
    assert details["live_pilot"] is False
    assert details["exercise_required"] is True
    assert details["restart_required"] is True
    assert details["exercise_status"] == "failed"
    assert details["rejection_count"] == 0


def test_exact_live_v11_without_rejection_is_integrity_pass_and_inconclusive(
    tmp_path,
    monkeypatch,
) -> None:
    package = load_task_package(TASK.parent)
    contract = _smoke_v2_contract(package)
    manifest = _live_manifest(package, contract, run_label="no_rejection")
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    monkeypatch.setattr(
        AgentRunner,
        "_require_live_authorization",
        staticmethod(lambda *_args, **_kwargs: None),
    )
    script = MOCK_TASK_SCRIPTS[package.public.task_id]
    responses = _ScriptedResponses(
        [
            RequestedTool(
                "read_file",
                "d072-no-rejection-read",
                {
                    "path": script.target_path,
                    "start_line": 1,
                    "end_line": 200,
                },
            ),
            RequestedTool(
                "apply_patch",
                "d072-no-rejection-patch",
                {"patch": script.patch},
            ),
            RequestedTool(
                "run_check",
                "d072-no-rejection-check",
                {"check_id": "existing-unit-tests"},
            ),
            RequestedTool(
                "read_file",
                "d072-no-rejection-fresh-anchor",
                {
                    "path": "mini_data_utils/csvlite.py",
                    "start_line": 1,
                    "end_line": 50,
                },
            ),
            RequestedTool(
                "get_diff",
                "d072-no-rejection-diff",
                {},
            ),
            lambda context: RequestedTool(
                "review_task",
                "d072-no-rejection-review",
                _review_arguments(
                    context,
                    contract,
                    complete=True,
                ),
            ),
            RequestedTool(
                "finish_task",
                "d072-no-rejection-finish",
                {},
            ),
        ],
        label="no_rejection",
    )
    adapter = OpenAIResponsesAdapter(
        manifest.model,
        client=SimpleNamespace(responses=responses),
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args, **_kwargs: adapter,
    )

    result = runner.start(TASK, model="openai", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    passed, details = _evidence(runner, manifest, package, events)

    assert result["scope_compliant_success"] is True
    assert len(responses.create_requests) == 7
    assert passed is True
    assert details["live_pilot"] is True
    assert details["exercise_required"] is False
    assert details["restart_required"] is False
    assert details["exercise_status"] == "inconclusive"
    assert details["exercise_reason"] == "rejection_not_observed"
    assert details["rejection_count"] == 0


def test_exact_live_v11_rejection_requires_structured_restart_recovery(
    tmp_path,
    monkeypatch,
) -> None:
    package = load_task_package(TASK.parent)
    contract = _smoke_v2_contract(package)
    manifest = _live_manifest(package, contract, run_label="recovery")
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    monkeypatch.setattr(
        AgentRunner,
        "_require_live_authorization",
        staticmethod(lambda *_args, **_kwargs: None),
    )

    script = MOCK_TASK_SCRIPTS[package.public.task_id]
    rejecting_responses = _ScriptedResponses(
        [
            RequestedTool(
                "read_file",
                "d072-live-read",
                {
                    "path": script.target_path,
                    "start_line": 1,
                    "end_line": 200,
                },
            ),
            RequestedTool(
                "apply_patch",
                "d072-live-patch",
                {"patch": script.patch},
            ),
            RequestedTool(
                "run_check",
                "d072-live-check",
                {"check_id": "existing-unit-tests"},
            ),
            RequestedTool(
                "get_diff",
                "d072-live-source-diff",
                {},
            ),
            lambda context: RequestedTool(
                "review_task",
                "d072-live-wrong-target-review",
                _wrong_target_review(context, contract),
            ),
        ],
        label="rejecting",
    )
    rejecting_adapter = OpenAIResponsesAdapter(
        manifest.model,
        client=SimpleNamespace(responses=rejecting_responses),
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args, **_kwargs: rejecting_adapter,
    )
    original_phase_after_tool = runner._phase_after_tool

    def crash_after_rejection(
        run_id,
        phase,
        tool,
        result,
        task,
        workspace,
    ):
        if (
            tool == "review_task"
            and result.status == "rejected"
            and result.error_code == "COVERAGE_CITATION_REJECTED"
        ):
            raise SystemExit(72)
        return original_phase_after_tool(
            run_id,
            phase,
            tool,
            result,
            task,
            workspace,
        )

    monkeypatch.setattr(
        runner,
        "_phase_after_tool",
        crash_after_rejection,
    )
    with pytest.raises(SystemExit, match="72"):
        runner.start(TASK, model="openai", manifest=manifest)

    source_events = runner.state.list_events(manifest.run_id)
    failure = next(
        event
        for event in source_events
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code")
        == "COVERAGE_CITATION_REJECTED"
    )

    recovery_responses = _ScriptedResponses(
        [
            RequestedTool(
                "read_file",
                "d072-live-fresh-anchor",
                {
                    "path": "mini_data_utils/csvlite.py",
                    "start_line": 1,
                    "end_line": 50,
                },
            ),
            RequestedTool(
                "get_diff",
                "d072-live-refreshed-diff",
                {},
            ),
            lambda context: RequestedTool(
                "review_task",
                "d072-live-recovered-review",
                _review_arguments(
                    context,
                    contract,
                    complete=True,
                ),
            ),
            RequestedTool(
                "finish_task",
                "d072-live-recovered-finish",
                {},
            ),
        ],
        label="recovery",
    )
    recovery_adapter = OpenAIResponsesAdapter(
        manifest.model,
        client=SimpleNamespace(responses=recovery_responses),
    )
    resumed = AgentRunner(runner.root)
    monkeypatch.setattr(
        resumed,
        "_model_adapter",
        lambda *_args, **_kwargs: recovery_adapter,
    )
    result = resumed.resume(manifest.run_id)
    events = resumed.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    assert len(recovery_responses.create_requests) == 4
    passed, details = _evidence(resumed, manifest, package, events)
    assert passed is True, details
    assert details["live_pilot"] is True
    assert details["exercise_required"] is True
    assert details["restart_required"] is False
    assert details["exercise_status"] == "passed"
    assert details["exercise_reason"] is None
    assert details["verified_rejection_sequences"] == [failure.sequence]
    assert details["restart_observed"] is True
    assert details["designated_restart_rejection_sequence"] == (
        failure.sequence
    )

    tampered = _tampered_events(
        events,
        failure.sequence,
        field="error_details",
    )
    tampered_passed, tampered_details = _evidence(
        resumed,
        manifest,
        package,
        tampered,
    )
    assert tampered_passed is False
    assert tampered_details["exercise_status"] == "failed"
    assert tampered_details["failed_rejection_sequences"] == [
        failure.sequence
    ]
