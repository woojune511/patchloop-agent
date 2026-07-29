from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from patchloop.agent.model import (
    MOCK_TASK_SCRIPTS,
    ModelTurn,
    ModelTurnError,
    OpenAIResponsesAdapter,
    RequestedTool,
)
from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
from patchloop.agent.tools import ToolGateway
from patchloop.contracts import (
    Artifact,
    Budget,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    FaultSpec,
    Phase,
    RunOutcomeKind,
    RunResult,
    RunStatus,
    VerdictState,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.evals.faults import clone_with_fault
from patchloop.evals.qualification import (
    _request_runtime_contract_valid,
    qualify_run,
)
from patchloop.runtime import build_manifest
from patchloop.sandbox import LocalSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_text, utc_now
from patchloop.verifier import EvaluationEngine

TASK = "tasks/smoke/csv-quoted-newline/public.yaml"
SMOKE_TASKS = {
    "csv-quoted-newline": TASK,
    "config-falsy-override": "tasks/smoke/config-falsy-override/public.yaml",
    "path-prefix-boundary": "tasks/smoke/path-prefix-boundary/public.yaml",
}
SMOKE_REPLAYS = {task_id: f"replays/smoke/{task_id}.jsonl" for task_id in SMOKE_TASKS}


def test_manifest_and_runtime_contract_versions_preserve_v2_compatibility() -> None:
    package = load_task_package(Path(TASK).parent)
    current = build_manifest(package, run_id="run_current_context_contract")
    legacy_v2 = current.model_copy(update={"context_policy_version": "phase-evidence-v2"})
    replay = build_manifest(
        package,
        run_id="run_replay_context_contract",
        provider="replay",
        model_id="replay:replays/smoke/csv-quoted-newline.jsonl",
        replay_hash="sha256:" + ("a" * 64),
    )

    assert current.tool_schema_version == "v2"
    assert current.context_policy_version == "phase-evidence-v3"
    assert AgentRunner._runtime_contract(current) == AgentRunner._runtime_contract(legacy_v2)
    assert replay.tool_schema_version == "v1"
    assert replay.context_policy_version == "v1"


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("model", "gpt-wrong"),
        ("truncation", "auto"),
        ("store", True),
        ("reasoning", {"effort": "low"}),
        ("service_tier", "priority"),
        ("tools", []),
    ],
)
def test_no_generation_request_must_match_the_full_runtime_contract(
    field: str,
    replacement: object,
) -> None:
    package = load_task_package(Path(TASK).parent)
    manifest = build_manifest(
        package,
        run_id=f"run_request_contract_{field}",
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
    )
    system_prompt, tools = AgentRunner._runtime_contract(manifest)
    adapter = OpenAIResponsesAdapter(
        manifest.model,
        client=SimpleNamespace(),
    )
    request = adapter.request_payload(
        "{}",
        tools,
        system_prompt=system_prompt,
    )

    assert _request_runtime_contract_valid(request, manifest) is True

    tampered = json.loads(json.dumps(request))
    tampered[field] = replacement
    assert _request_runtime_contract_valid(tampered, manifest) is False


def _write_approved_execution_plan(root: Path, execution_hash: str) -> None:
    path = root / "experiments" / "plans" / f"{execution_hash.removeprefix('sha256:')}.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "experiment-execution-plan-v1",
                "ready": True,
                "blockers": [],
                "execution_hash": execution_hash,
                "approval": {
                    "invocation_approve_live_cost": True,
                    "invocation_approved_execution_hash": execution_hash,
                    "matches_execution_hash": True,
                },
            }
        ),
        encoding="utf-8",
    )


def _fake_openai_response(
    *,
    input_tokens: int,
    model_id: str,
    output_text: str = "",
    tool_call: RequestedTool | None = None,
    response_id: str,
) -> SimpleNamespace:
    output = []
    if tool_call is not None:
        output.append(
            SimpleNamespace(
                type="function_call",
                name=tool_call.name,
                call_id=tool_call.action_id,
                arguments=json.dumps(tool_call.arguments),
            )
        )
    output_tokens = 1
    return SimpleNamespace(
        id=response_id,
        model=model_id,
        service_tier="default",
        system_fingerprint="test-fingerprint",
        status="completed",
        truncation="disabled",
        incomplete_details=None,
        output=output,
        output_text=output_text,
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            input_tokens_details=SimpleNamespace(
                cached_tokens=0,
                cache_write_tokens=0,
            ),
            output_tokens_details=SimpleNamespace(reasoning_tokens=0),
        ),
    )


class _RejectedPatchResponses:
    def __init__(
        self,
        *,
        patch: str,
        model_id: str,
        input_token_counts: list[int],
        allow_second_create: bool,
    ) -> None:
        self.patch = patch
        self.model_id = model_id
        self.input_token_counts = input_token_counts
        self.allow_second_create = allow_second_create
        self.count_requests: list[dict[str, Any]] = []
        self.create_requests: list[dict[str, Any]] = []
        self.input_tokens = SimpleNamespace(count=self.count)

    def count(self, **request):
        index = len(self.count_requests)
        self.count_requests.append(request)
        return SimpleNamespace(input_tokens=self.input_token_counts[index])

    def create(self, **request):
        index = len(self.create_requests)
        if index == 1 and not self.allow_second_create:
            raise AssertionError("second generation must not start after exact budget rejection")
        self.create_requests.append(request)
        if index == 0:
            return _fake_openai_response(
                input_tokens=self.input_token_counts[0],
                model_id=self.model_id,
                tool_call=RequestedTool(
                    "apply_patch",
                    "rejected-live-patch",
                    {"patch": self.patch},
                ),
                response_id="resp_rejected_patch",
            )
        return _fake_openai_response(
            input_tokens=self.input_token_counts[1],
            model_id=self.model_id,
            output_text="cannot continue",
            response_id="resp_after_rejection",
        )


class _GenericBudgetBlockResponses:
    def __init__(
        self,
        *,
        model_id: str,
        input_token_counts: list[int],
    ) -> None:
        self.model_id = model_id
        self.input_token_counts = input_token_counts
        self.count_requests: list[dict[str, Any]] = []
        self.create_requests: list[dict[str, Any]] = []
        self.input_tokens = SimpleNamespace(count=self.count)

    def count(self, **request):
        index = len(self.count_requests)
        self.count_requests.append(request)
        return SimpleNamespace(input_tokens=self.input_token_counts[index])

    def create(self, **request):
        if self.create_requests:
            raise AssertionError(
                "second generation must not start after exact budget rejection"
            )
        self.create_requests.append(request)
        return _fake_openai_response(
            input_tokens=self.input_token_counts[0],
            model_id=self.model_id,
            tool_call=RequestedTool(
                "search_files",
                "generic-budget-search",
                {"query": "parse", "path_glob": "**/*.py"},
            ),
            response_id="resp_before_generic_budget_block",
        )


def _assert_public_trace_boundary(runner: AgentRunner, run_id: str, task_path: str) -> None:
    package = load_task_package(Path(task_path).parent)
    hidden_check_ids = {check.id for check in package.private.hidden_checks}
    contexts: list[str] = []
    for event in runner.state.list_events(run_id):
        if event.type != EventType.CONTEXT_BUILT:
            continue
        context = Path(event.payload["artifact_path"]).read_text(encoding="utf-8")
        contexts.append(context)
        assert "reference.patch" not in context
        assert all(check_id not in context for check_id in hidden_check_ids)
    assert contexts
    assert package.private.reference_patch.sha256 not in contexts[0]


@pytest.mark.parametrize(("task_id", "task_path"), SMOKE_TASKS.items())
def test_offline_mock_agent_creates_complete_trace(
    tmp_path, monkeypatch, task_id: str, task_path: str
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(task_path, model="mock")
    events = runner.state.list_events(result["run_id"])
    assert result["scope_compliant_success"] is True
    assert result["official"] is False
    assert runner.state.get_manifest(result["run_id"]).task_id == task_id
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert sum(event.type == EventType.MODEL_CALLED for event in events) == 5
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 5
    assert any(event.type == EventType.PATCH_APPLIED for event in events)
    assert any(event.type == EventType.REVIEW_RECORDED for event in events)
    assert any(event.type == EventType.SUBMISSION_ATTEMPTED for event in events)
    assert any(event.type == EventType.SUBMISSION_ACCEPTED for event in events)
    assert any(event.type == EventType.RUN_COMPLETED for event in events)
    accepted = next(event for event in events if event.type == EventType.SUBMISSION_ACCEPTED)
    submitted_artifact = Artifact.model_validate(accepted.payload["submitted_patch_artifact"])
    assert result["submitted_patch_artifact_id"] == (submitted_artifact.artifact_id)
    assert (
        sha256_bytes(Path(submitted_artifact.path).read_bytes())
        == (accepted.payload["worktree_diff_hash"])
    )
    workspace = tmp_path / "runtime" / "workspaces" / result["run_id"] / "repo"
    assert not (workspace / ".patchloop-hidden").exists()
    result_path = tmp_path / "runtime" / "artifacts" / "runs" / result["run_id"] / "result.json"
    persisted = json.loads(result_path.read_text(encoding="utf-8"))
    assert persisted["usage"] == result["usage"]
    _assert_public_trace_boundary(runner, result["run_id"], task_path)


@pytest.mark.parametrize(
    ("task_id", "task_path", "replay_path"),
    [(task_id, task_path, SMOKE_REPLAYS[task_id]) for task_id, task_path in SMOKE_TASKS.items()],
)
def test_offline_replay_agent_creates_hashed_complete_trace(
    tmp_path,
    monkeypatch,
    task_id: str,
    task_path: str,
    replay_path: str,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(task_path, model=f"replay:{replay_path}")
    manifest = runner.state.get_manifest(result["run_id"])
    events = runner.state.list_events(result["run_id"])

    assert result["scope_compliant_success"] is True
    assert result["official"] is False
    assert manifest.task_id == task_id
    assert manifest.model.provider == "replay"
    assert manifest.model.model_id == f"replay:{replay_path}"
    assert manifest.model.replay_hash == sha256_bytes(Path(replay_path).read_bytes())
    assert sum(event.type == EventType.MODEL_CALLED for event in events) == 5
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 4
    receipt = json.loads(
        (
            tmp_path
            / "runtime"
            / "artifacts"
            / "runs"
            / result["run_id"]
            / "evaluation-receipt.json"
        ).read_text(encoding="utf-8")
    )
    assert receipt["submitted_patch_artifact_id"] == result["submitted_patch_artifact_id"]
    qualification = qualify_run(
        result["run_id"],
        task_dir=Path(task_path).parent,
        root=tmp_path / "runtime",
    )
    verifier_evidence = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "verifier_evidence_artifacts"
    )
    assert verifier_evidence["passed"] is True
    _assert_public_trace_boundary(runner, result["run_id"], task_path)
    persisted_result = json.loads(
        (tmp_path / "runtime" / "artifacts" / "runs" / result["run_id"] / "result.json").read_text(
            encoding="utf-8"
        )
    )
    verifier_artifact = persisted_result["verifier_results"][0]["details"]["evidence_artifacts"][0]
    Path(verifier_artifact["path"]).write_bytes(b"tampered")
    with pytest.raises(
        ContractError,
        match="legacy trace qualification source evidence changed",
    ):
        qualify_run(
            result["run_id"],
            task_dir=Path(task_path).parent,
            root=tmp_path / "runtime",
        )


def test_replay_path_must_be_repository_relative(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    with pytest.raises(ContractError, match="safe relative path"):
        runner.start(TASK, model="replay:../outside.jsonl")


def test_agent_failure_persists_run_id_usage_cost_and_terminal_artifacts(
    tmp_path,
    monkeypatch,
) -> None:
    class InvalidTurnAdapter:
        def next_turn(self, context, tools):
            del context, tools
            return ModelTurn(
                text="not done and no tool",
                input_tokens=1_000,
                cached_input_tokens=200,
                cache_write_input_tokens=100,
                output_tokens=100,
                response_id="resp_failure",
                response_model="gpt-5.6-terra",
                response_service_tier="default",
            )

    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    execution_hash = "sha256:" + ("e" * 64)
    manifest = build_manifest(
        package,
        run_id="run_live_agent_failure",
        provider="openai",
        model_id="gpt-5.6-terra",
        input_price_per_million_usd=2.5,
        cached_input_price_per_million_usd=0.25,
        cache_write_input_price_per_million_usd=3.125,
        output_price_per_million_usd=15.0,
        experiment_context=ExperimentRunContext(
            experiment_id="live-attempt-persistence-test",
            purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
            suite_hash="sha256:" + ("a" * 64),
            execution_hash=execution_hash,
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + ("b" * 64),
            repetition=1,
        ),
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_: InvalidTurnAdapter())
    _write_approved_execution_plan(tmp_path / "runtime", execution_hash)

    result = runner.start(
        TASK,
        model="openai",
        manifest=manifest,
        live_authorization=issue_live_execution_authorization(
            execution_hash,
            root=tmp_path / "runtime",
        ),
    )

    assert result["run_id"] == manifest.run_id
    assert result["outcome_kind"] == RunOutcomeKind.AGENT_FAILURE.value
    assert result["evaluation_status"] == "not_run"
    assert result["usage"]["input_tokens"] == 1_000
    assert result["usage"]["cached_input_tokens"] == 200
    assert result["usage"]["cache_write_input_tokens"] == 100
    assert result["usage"]["model_cost_usd"] == pytest.approx(0.0036125)
    events = runner.state.list_events(manifest.run_id)
    assert events[-1].type == EventType.RUN_FAILED
    assert sum(event.type == EventType.RUN_FAILED for event in events) == 1
    result_path = tmp_path / "runtime" / "artifacts" / "runs" / manifest.run_id / "result.json"
    assert json.loads(result_path.read_text(encoding="utf-8"))["run_id"] == manifest.run_id


def test_live_runner_refuses_generation_that_cannot_fit_remaining_token_budget(
    tmp_path,
    monkeypatch,
) -> None:
    class CountingOnlyResponses:
        def __init__(self) -> None:
            self.input_tokens = SimpleNamespace(count=self.count)
            self.create_called = False

        @staticmethod
        def count(**_kwargs):
            return SimpleNamespace(input_tokens=10)

        def create(self, **_kwargs):
            self.create_called = True
            raise AssertionError("generation must not start past the strict token budget")

    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    execution_hash = "sha256:" + ("d" * 64)
    manifest = build_manifest(
        package,
        run_id="run_strict_live_token_budget",
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=4_105),
        experiment_context=ExperimentRunContext(
            experiment_id="strict-live-token-budget-test",
            purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
            suite_hash="sha256:" + ("a" * 64),
            execution_hash=execution_hash,
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + ("b" * 64),
            repetition=1,
        ),
    )
    responses = CountingOnlyResponses()
    adapter = OpenAIResponsesAdapter(
        manifest.model,
        client=SimpleNamespace(responses=responses),
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_: adapter)
    _write_approved_execution_plan(tmp_path / "runtime", execution_hash)

    result = runner.start(
        TASK,
        model="openai",
        manifest=manifest,
        live_authorization=issue_live_execution_authorization(
            execution_hash,
            root=tmp_path / "runtime",
        ),
    )

    assert result["outcome_kind"] == RunOutcomeKind.AGENT_FAILURE.value
    assert result["usage"]["model_calls"] == 0
    assert result["terminal_error"]["message"].startswith("remaining token budget cannot fund")
    assert responses.create_called is False
    events = runner.state.list_events(manifest.run_id)
    blocked = next(
        event
        for event in events
        if event.type == EventType.MODEL_GENERATION_BLOCKED
    )
    assert blocked.payload["schema_version"] == "model-generation-block-v1"
    qualification = qualify_run(
        manifest.run_id,
        task_dir=Path(TASK).parent,
        root=tmp_path / "runtime",
    )
    prompt_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "prompt_token_integrity"
    )
    terminal_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "terminal_result_integrity"
    )
    assert prompt_check["passed"] is True
    assert prompt_check["details"]["model_event_count"] == 0
    assert prompt_check["details"]["declared"] is True
    assert prompt_check["details"]["terminal_generation_block_kind"] == "generic"
    assert terminal_check["passed"] is True


def test_live_v3_retry_request_contains_exact_rejected_patch_context(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    execution_hash = "sha256:" + ("7" * 64)
    patch = "*** Begin Patch\n*** Update File: mini_data_utils/csvlite.py\n*** End Patch"
    manifest = build_manifest(
        package,
        run_id="run_live_v3_rejected_patch_context",
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=20_000),
        experiment_context=ExperimentRunContext(
            experiment_id="live-v3-rejected-patch-context-test",
            purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
            suite_hash="sha256:" + ("a" * 64),
            execution_hash=execution_hash,
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + ("b" * 64),
            repetition=1,
        ),
    )
    responses = _RejectedPatchResponses(
        patch=patch,
        model_id=manifest.model.model_id,
        input_token_counts=[100, 200],
        allow_second_create=True,
    )
    adapter = OpenAIResponsesAdapter(
        manifest.model,
        client=SimpleNamespace(responses=responses),
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_: adapter)
    _write_approved_execution_plan(tmp_path / "runtime", execution_hash)

    result = runner.start(
        TASK,
        model="openai",
        manifest=manifest,
        live_authorization=issue_live_execution_authorization(
            execution_hash,
            root=tmp_path / "runtime",
        ),
    )

    events = runner.state.list_events(manifest.run_id)
    patch_call = next(
        event
        for event in events
        if event.type == EventType.TOOL_CALLED and event.payload.get("tool") == "apply_patch"
    )
    patch_failure = next(
        event
        for event in events
        if event.type == EventType.TOOL_FAILED and event.correlation_id == patch_call.correlation_id
    )
    second_context = json.loads(
        next(
            item["content"]
            for item in responses.create_requests[1]["input"]
            if item["role"] == "user"
        )
    )
    retry = second_context["rejected_mutation_retry"]
    candidate_artifact = Artifact.model_validate(patch_call.payload["patch_artifact"])

    assert result["outcome_kind"] == RunOutcomeKind.AGENT_FAILURE.value
    assert result["usage"]["model_calls"] == 2
    assert len(responses.count_requests) == 2
    assert len(responses.create_requests) == 2
    assert retry["action_id"] == "rejected-live-patch"
    assert retry["source_call_sequence"] == patch_call.sequence
    assert retry["source_failure_sequence"] == patch_failure.sequence
    assert retry["candidate"] == {
        "patch": patch,
        "content_hash": sha256_text(patch),
        "size_bytes": len(patch.encode("utf-8")),
        "input_hash": patch_call.payload["input_hash"],
    }
    assert retry["candidate"]["content_hash"] == candidate_artifact.content_hash
    assert retry["rejection"] == {
        "status": "rejected",
        "error_code": patch_failure.payload["error_code"],
        "error_message": patch_failure.payload["error_message"],
        "error_details": patch_failure.payload["error_details"],
    }
    context_events = [event for event in events if event.type == EventType.CONTEXT_BUILT]
    request_evidence = json.loads(
        Path(context_events[-1].payload["artifact_path"]).read_text(encoding="utf-8")
    )
    assert request_evidence["context_build"]["rejected_mutation_retry"]["included"] is True
    assert request_evidence["context_build"]["rejected_mutation_retry"]["truncated"] is False


def _run_live_v3_retry_budget_block(
    tmp_path,
    monkeypatch,
    *,
    run_id: str,
):
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    execution_hash = "sha256:" + ("8" * 64)
    patch = "*** Begin Patch\n*** Update File: mini_data_utils/csvlite.py\n*** End Patch"
    manifest = build_manifest(
        package,
        run_id=run_id,
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=5_000),
        experiment_context=ExperimentRunContext(
            experiment_id="live-v3-rejected-patch-budget-test",
            purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
            suite_hash="sha256:" + ("a" * 64),
            execution_hash=execution_hash,
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + ("b" * 64),
            repetition=1,
        ),
    )
    responses = _RejectedPatchResponses(
        patch=patch,
        model_id=manifest.model.model_id,
        input_token_counts=[100, 1_000],
        allow_second_create=False,
    )
    adapter = OpenAIResponsesAdapter(
        manifest.model,
        client=SimpleNamespace(responses=responses),
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_: adapter)
    _write_approved_execution_plan(tmp_path / "runtime", execution_hash)

    result = runner.start(
        TASK,
        model="openai",
        manifest=manifest,
        live_authorization=issue_live_execution_authorization(
            execution_hash,
            root=tmp_path / "runtime",
        ),
    )
    return runner, result, manifest, responses, patch


def _run_live_v3_generic_budget_block(
    tmp_path,
    monkeypatch,
    *,
    run_id: str,
):
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    execution_hash = "sha256:" + ("9" * 64)
    manifest = build_manifest(
        package,
        run_id=run_id,
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        budget=Budget(max_total_tokens=5_000),
        experiment_context=ExperimentRunContext(
            experiment_id="live-v3-generic-budget-test",
            purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
            suite_hash="sha256:" + ("a" * 64),
            execution_hash=execution_hash,
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + ("b" * 64),
            repetition=1,
        ),
    )
    responses = _GenericBudgetBlockResponses(
        model_id=manifest.model.model_id,
        input_token_counts=[100, 1_000],
    )
    adapter = OpenAIResponsesAdapter(
        manifest.model,
        client=SimpleNamespace(responses=responses),
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_: adapter)
    _write_approved_execution_plan(tmp_path / "runtime", execution_hash)

    result = runner.start(
        TASK,
        model="openai",
        manifest=manifest,
        live_authorization=issue_live_execution_authorization(
            execution_hash,
            root=tmp_path / "runtime",
        ),
    )
    return runner, result, manifest, responses


def test_live_v3_retry_request_budget_block_precedes_second_generation(
    tmp_path,
    monkeypatch,
) -> None:
    runner, result, manifest, responses, patch = (
        _run_live_v3_retry_budget_block(
            tmp_path,
            monkeypatch,
            run_id="run_live_v3_rejected_patch_budget",
        )
    )

    events = runner.state.list_events(manifest.run_id)
    blocked_events = [event for event in events if event.type == EventType.MODEL_GENERATION_BLOCKED]
    assert len(blocked_events) == 1
    blocked = blocked_events[0]
    expected_payload = {
        "schema_version": "model-generation-block-v1",
        "reason_code": "exact_request_budget_exceeded",
        "error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
        "generation_started": False,
        "request_artifact_id": blocked.payload["request_artifact_id"],
        "request_artifact_path": blocked.payload["request_artifact_path"],
        "request_body_hash": blocked.payload["request_body_hash"],
        "requested_input_tokens": 1_000,
        "remaining_tokens": 4_899,
        "max_output_tokens": 4_096,
        "input_token_count_calls": 1,
        "retry_context_present": True,
        "retry_candidate_content_hash": sha256_text(patch),
    }

    assert blocked.payload == expected_payload
    assert len(responses.count_requests) == 2
    assert len(responses.create_requests) == 1
    assert result["outcome_kind"] == RunOutcomeKind.AGENT_FAILURE.value
    assert result["usage"]["model_calls"] == 1
    assert result["usage"]["input_token_count_calls"] == 2
    assert result["terminal_error"]["type"] == "ModelGenerationBudgetError"
    assert result["terminal_error"]["code"] == "MODEL_GENERATION_BUDGET_EXCEEDED"
    assert result["terminal_error"]["details"] == expected_payload
    assert sum(event.type == EventType.MODEL_CALLED for event in events) == 1
    request_evidence = json.loads(
        Path(blocked.payload["request_artifact_path"]).read_text(encoding="utf-8")
    )
    second_context = json.loads(
        next(
            item["content"]
            for item in request_evidence["request_body"]["input"]
            if item["role"] == "user"
        )
    )
    assert second_context["rejected_mutation_retry"]["candidate"]["patch"] == patch
    assert request_evidence["context_build"]["rejected_mutation_retry"]["included"] is True
    assert blocked.sequence < next(
        event.sequence for event in events if event.type == EventType.RUN_FAILED
    )
    qualification = qualify_run(
        manifest.run_id,
        task_dir=Path(TASK).parent,
        root=tmp_path / "runtime",
    )
    retry_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "rejected_patch_retry_context"
    )
    prompt_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "prompt_token_integrity"
    )
    terminal_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "terminal_result_integrity"
    )
    assert retry_check["passed"] is True
    assert retry_check["details"]["model_generation_blocked_count"] == 1
    assert prompt_check["passed"] is True
    assert prompt_check["details"]["terminal_generation_block_valid"] is True
    assert (
        prompt_check["details"]["terminal_generation_block_kind"]
        == "rejected_patch_retry"
    )
    assert terminal_check["passed"] is True
    assert terminal_check["details"]["model_generation_block_binding_required"] is True
    assert terminal_check["details"]["model_generation_block_binding_valid"] is True


def test_unversioned_retry_budget_block_remains_read_compatible(
    tmp_path,
    monkeypatch,
) -> None:
    runner, _, manifest, _, _ = _run_live_v3_retry_budget_block(
        tmp_path,
        monkeypatch,
        run_id="run_live_v3_legacy_retry_budget",
    )
    database = tmp_path / "runtime" / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT sequence, event_json FROM events "
            "WHERE run_id = ? ORDER BY sequence",
            (manifest.run_id,),
        ).fetchall()
        for sequence, event_json in rows:
            event = json.loads(event_json)
            if event["type"] == EventType.MODEL_GENERATION_BLOCKED.value:
                event["payload"].pop("schema_version")
            elif event["type"] == EventType.RUN_FAILED.value:
                event["payload"]["error_details"].pop("schema_version")
            else:
                continue
            connection.execute(
                "UPDATE events SET event_json = ? "
                "WHERE run_id = ? AND sequence = ?",
                (json.dumps(event), manifest.run_id, sequence),
            )

        result_json = connection.execute(
            "SELECT result_json FROM runs WHERE run_id = ?",
            (manifest.run_id,),
        ).fetchone()[0]
        persisted_result = json.loads(result_json)
        persisted_result["terminal_error"]["details"].pop("schema_version")
        connection.execute(
            "UPDATE runs SET result_json = ? WHERE run_id = ?",
            (json.dumps(persisted_result), manifest.run_id),
        )

    result_path = (
        tmp_path
        / "runtime"
        / "artifacts"
        / "runs"
        / manifest.run_id
        / "result.json"
    )
    result_path.write_text(
        json.dumps(persisted_result, indent=2),
        encoding="utf-8",
    )

    qualification = qualify_run(
        manifest.run_id,
        task_dir=Path(TASK).parent,
        root=tmp_path / "runtime",
    )
    checks = {
        check["check_id"]: check
        for check in qualification["checks"]
    }
    assert checks["rejected_patch_retry_context"]["passed"] is True
    assert checks["prompt_token_integrity"]["passed"] is True
    assert checks["terminal_result_integrity"]["passed"] is True


def test_retry_budget_block_requires_a_verified_rejected_patch_source(
    tmp_path,
    monkeypatch,
) -> None:
    runner, _, manifest, _, _ = _run_live_v3_retry_budget_block(
        tmp_path,
        monkeypatch,
        run_id="run_live_v3_retry_without_source",
    )
    database = tmp_path / "runtime" / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT sequence, event_json FROM events "
            "WHERE run_id = ? ORDER BY sequence",
            (manifest.run_id,),
        ).fetchall()
        sequence, event_json = next(
            (sequence, event_json)
            for sequence, event_json in rows
            if json.loads(event_json)["type"] == EventType.TOOL_FAILED.value
        )
        event = json.loads(event_json)
        event["payload"]["tool"] = "read_file"
        connection.execute(
            "UPDATE events SET event_json = ? "
            "WHERE run_id = ? AND sequence = ?",
            (json.dumps(event), manifest.run_id, sequence),
        )

    qualification = qualify_run(
        manifest.run_id,
        task_dir=Path(TASK).parent,
        root=tmp_path / "runtime",
    )
    checks = {
        check["check_id"]: check
        for check in qualification["checks"]
    }
    assert checks["rejected_patch_retry_context"]["details"][
        "retry_episode_count"
    ] == 0
    assert checks["prompt_token_integrity"]["passed"] is False
    assert checks["terminal_result_integrity"]["passed"] is False
    assert qualification["qualified"] is False


def test_live_v3_generic_request_budget_block_validates_prompt_and_terminal(
    tmp_path,
    monkeypatch,
) -> None:
    runner, result, manifest, responses = _run_live_v3_generic_budget_block(
        tmp_path,
        monkeypatch,
        run_id="run_live_v3_generic_budget",
    )

    events = runner.state.list_events(manifest.run_id)
    blocked = next(
        event
        for event in events
        if event.type == EventType.MODEL_GENERATION_BLOCKED
    )
    assert blocked.payload == {
        "schema_version": "model-generation-block-v1",
        "reason_code": "exact_request_budget_exceeded",
        "error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
        "generation_started": False,
        "request_artifact_id": blocked.payload["request_artifact_id"],
        "request_artifact_path": blocked.payload["request_artifact_path"],
        "request_body_hash": blocked.payload["request_body_hash"],
        "requested_input_tokens": 1_000,
        "remaining_tokens": 4_899,
        "max_output_tokens": 4_096,
        "input_token_count_calls": 1,
        "retry_context_present": False,
        "retry_candidate_content_hash": None,
    }
    assert len(responses.count_requests) == 2
    assert len(responses.create_requests) == 1
    assert result["usage"]["model_calls"] == 1
    assert result["usage"]["input_token_count_calls"] == 2
    assert result["terminal_error"]["details"] == blocked.payload

    request_evidence = json.loads(
        Path(blocked.payload["request_artifact_path"]).read_text(
            encoding="utf-8"
        )
    )
    rendered_context = json.loads(
        next(
            item["content"]
            for item in request_evidence["request_body"]["input"]
            if item["role"] == "user"
        )
    )
    assert rendered_context["rejected_mutation_retry"] is None
    assert (
        request_evidence["context_build"]["rejected_mutation_retry"]["included"]
        is False
    )

    qualification = qualify_run(
        manifest.run_id,
        task_dir=Path(TASK).parent,
        root=tmp_path / "runtime",
    )
    retry_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "rejected_patch_retry_context"
    )
    prompt_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "prompt_token_integrity"
    )
    terminal_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "terminal_result_integrity"
    )
    assert retry_check["passed"] is True
    assert retry_check["details"]["retry_episode_count"] == 0
    assert retry_check["details"]["model_generation_blocked_count"] == 0
    assert prompt_check["passed"] is True
    assert prompt_check["details"]["terminal_generation_block_valid"] is True
    assert prompt_check["details"]["terminal_generation_block_kind"] == "generic"
    assert terminal_check["passed"] is True
    assert terminal_check["details"]["model_generation_block_binding_required"] is True
    assert terminal_check["details"]["model_generation_block_binding_valid"] is True


@pytest.mark.parametrize(
    ("event_type", "field", "replacement", "failed_check_id"),
    [
        (
            EventType.MODEL_GENERATION_BLOCKED,
            "remaining_tokens",
            1,
            "prompt_token_integrity",
        ),
        (
            EventType.MODEL_GENERATION_BLOCKED,
            "retry_context_present",
            True,
            "prompt_token_integrity",
        ),
        (
            EventType.MODEL_GENERATION_BLOCKED,
            "request_body_hash",
            "sha256:" + ("f" * 64),
            "prompt_token_integrity",
        ),
        (
            EventType.RUN_FAILED,
            "error_code",
            "CONTRACT_ERROR",
            "terminal_result_integrity",
        ),
    ],
)
def test_v3_generic_budget_block_qualification_rejects_tampering(
    tmp_path,
    monkeypatch,
    event_type,
    field,
    replacement,
    failed_check_id,
) -> None:
    runner, _, manifest, _ = _run_live_v3_generic_budget_block(
        tmp_path,
        monkeypatch,
        run_id=f"run_live_v3_generic_tamper_{field}",
    )
    database = tmp_path / "runtime" / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT sequence, event_json FROM events "
            "WHERE run_id = ? ORDER BY sequence",
            (manifest.run_id,),
        ).fetchall()
        sequence, event_json = next(
            (sequence, event_json)
            for sequence, event_json in rows
            if json.loads(event_json)["type"] == event_type.value
        )
        event = json.loads(event_json)
        event["payload"][field] = replacement
        connection.execute(
            "UPDATE events SET event_json = ? "
            "WHERE run_id = ? AND sequence = ?",
            (json.dumps(event), manifest.run_id, sequence),
        )

    qualification = qualify_run(
        manifest.run_id,
        task_dir=Path(TASK).parent,
        root=tmp_path / "runtime",
    )
    failed_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == failed_check_id
    )
    assert failed_check["passed"] is False


@pytest.mark.parametrize(
    ("event_type", "field", "replacement", "failed_check_id"),
    [
        (
            EventType.MODEL_GENERATION_BLOCKED,
            "remaining_tokens",
            1,
            "rejected_patch_retry_context",
        ),
        (
            EventType.RUN_FAILED,
            "error_code",
            "CONTRACT_ERROR",
            "terminal_result_integrity",
        ),
    ],
)
def test_v3_budget_block_qualification_rejects_tampered_binding(
    tmp_path,
    monkeypatch,
    event_type,
    field,
    replacement,
    failed_check_id,
) -> None:
    runner, _, manifest, _, _ = _run_live_v3_retry_budget_block(
        tmp_path,
        monkeypatch,
        run_id=f"run_live_v3_budget_tamper_{field}",
    )
    database = tmp_path / "runtime" / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT sequence, event_json FROM events "
            "WHERE run_id = ? ORDER BY sequence",
            (manifest.run_id,),
        ).fetchall()
        sequence, event_json = next(
            (sequence, event_json)
            for sequence, event_json in rows
            if json.loads(event_json)["type"] == event_type.value
        )
        event = json.loads(event_json)
        event["payload"][field] = replacement
        connection.execute(
            "UPDATE events SET event_json = ? "
            "WHERE run_id = ? AND sequence = ?",
            (json.dumps(event), manifest.run_id, sequence),
        )

    qualification = qualify_run(
        manifest.run_id,
        task_dir=Path(TASK).parent,
        root=tmp_path / "runtime",
    )
    failed_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == failed_check_id
    )
    assert failed_check["passed"] is False
    assert qualification["qualified"] is False


def test_agent_runner_rejects_live_model_without_campaign_capability(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    manifest = build_manifest(
        package,
        run_id="run_unapproved_live",
        provider="openai",
        model_id="gpt-5.6-terra",
    )
    runner = AgentRunner(tmp_path / "runtime")

    with pytest.raises(ContractError, match="approved experiment execution capability"):
        runner.start(TASK, model="openai", manifest=manifest)

    assert runner.state.has_run(manifest.run_id) is False


def test_live_capability_requires_persisted_approved_plan(tmp_path) -> None:
    with pytest.raises(ContractError, match="persisted approved execution plan"):
        issue_live_execution_authorization(
            "sha256:" + ("a" * 64),
            root=tmp_path / "runtime",
        )


def test_live_capability_rejects_execution_plan_drift(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    root = tmp_path / "runtime"
    execution_hash = "sha256:" + ("c" * 64)
    _write_approved_execution_plan(root, execution_hash)
    authorization = issue_live_execution_authorization(execution_hash, root=root)
    Path(authorization.plan_path).write_text(
        Path(authorization.plan_path).read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    package = load_task_package(Path(TASK).parent)
    manifest = build_manifest(
        package,
        run_id="run_live_plan_drift",
        provider="openai",
        model_id="gpt-5.6-terra",
        experiment_context=ExperimentRunContext(
            experiment_id="live-plan-drift-test",
            purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
            suite_hash="sha256:" + ("a" * 64),
            execution_hash=execution_hash,
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + ("b" * 64),
            repetition=1,
        ),
    )
    runner = AgentRunner(root)

    with pytest.raises(ContractError, match="approved experiment execution capability"):
        runner.start(
            TASK,
            model="openai",
            manifest=manifest,
            live_authorization=authorization,
        )

    assert runner.state.has_run(manifest.run_id) is False


def test_agent_runner_rejects_model_selector_manifest_mismatch(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    manifest = build_manifest(
        package,
        run_id="run_model_binding_mismatch",
        provider="mock",
        model_id="mock-v1",
    )
    runner = AgentRunner(tmp_path / "runtime")

    with pytest.raises(ContractError, match="does not match"):
        runner.start(TASK, model="openai", manifest=manifest)

    assert runner.state.has_run(manifest.run_id) is False


def test_agent_runner_rejects_task_package_manifest_mismatch(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    manifest = build_manifest(
        package,
        run_id="run_task_binding_mismatch",
        provider="mock",
        model_id="mock-v1",
    ).model_copy(update={"public_spec_hash": "sha256:" + ("f" * 64)})
    runner = AgentRunner(tmp_path / "runtime")

    with pytest.raises(ContractError, match="immutable run manifest"):
        runner.start(TASK, model="mock", manifest=manifest)

    assert runner.state.has_run(manifest.run_id) is False


def test_agent_runner_uses_one_validated_task_snapshot_before_model_turn(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    original_package = load_task_package(Path(TASK).parent)
    replacement = original_package.model_copy(update={"private_spec_hash": "sha256:" + ("f" * 64)})
    loads = []

    def changing_loader(_task_dir):
        loads.append(len(loads) + 1)
        return original_package if len(loads) == 1 else replacement

    class StopAtModelTurn:
        @staticmethod
        def next_turn(_context, _tools):
            assert loads == [1]
            raise SystemExit("stop at model boundary")

    manifest = build_manifest(
        original_package,
        run_id="run_task_snapshot_probe",
        provider="mock",
        model_id="mock-v1",
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr("patchloop.agent.runner.load_task_package", changing_loader)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: StopAtModelTurn())

    with pytest.raises(SystemExit, match="stop at model boundary"):
        runner.start(TASK, model="mock", manifest=manifest)

    assert loads == [1]


def test_startup_failure_persists_terminal_infrastructure_attempt(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    manifest = build_manifest(
        package,
        run_id="run_startup_infrastructure_failure",
        provider="mock",
        model_id="mock-v1",
    )
    runner = AgentRunner(tmp_path / "runtime")

    def fail_workspace(*_args, **_kwargs):
        raise OSError("synthetic workspace failure")

    monkeypatch.setattr(runner.workspaces, "create", fail_workspace)
    with pytest.raises(OSError, match="synthetic workspace failure"):
        runner.start(TASK, model="mock", manifest=manifest)

    row = next(row for row in runner.state.list_runs() if row["run_id"] == manifest.run_id)
    assert row["status"] == "failed"
    assert row["result"]["outcome_kind"] == "infrastructure_error"
    assert runner.state.list_events(manifest.run_id)[-1].type == EventType.RUN_FAILED
    assert (tmp_path / "runtime" / "artifacts" / "runs" / manifest.run_id / "result.json").is_file()


def test_billed_model_parse_error_preserves_usage_and_cost(
    tmp_path,
    monkeypatch,
) -> None:
    class BilledMalformedTurnAdapter:
        @staticmethod
        def next_turn(_context, _tools):
            return ModelTurn(
                input_tokens=1_000,
                cached_input_tokens=200,
                cache_write_input_tokens=100,
                output_tokens=100,
                response_id="resp_malformed",
                error=ModelTurnError(
                    code="invalid_tool_arguments_json",
                    message="provider function-call arguments were not valid JSON",
                ),
            )

    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    manifest = build_manifest(
        package,
        run_id="run_billed_parse_error",
        provider="mock",
        model_id="mock-v1",
        input_price_per_million_usd=2.5,
        cached_input_price_per_million_usd=0.25,
        cache_write_input_price_per_million_usd=3.125,
        output_price_per_million_usd=15.0,
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args: BilledMalformedTurnAdapter(),
    )

    result = runner.start(TASK, model="mock", manifest=manifest)

    assert result["outcome_kind"] == "agent_failure"
    assert result["terminal_error"]["message"].endswith("invalid_tool_arguments_json")
    assert result["usage"]["input_tokens"] == 1_000
    assert result["usage"]["model_cost_usd"] == pytest.approx(0.0036125)
    model_event = next(
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.MODEL_CALLED
    )
    assert model_event.payload["response_error_code"] == ("invalid_tool_arguments_json")


def test_submission_gate_recovers_from_early_and_stale_review_attempts(
    tmp_path,
    monkeypatch,
) -> None:
    class RecoveringSubmissionAdapter:
        def __init__(self) -> None:
            script = MOCK_TASK_SCRIPTS["csv-quoted-newline"]
            self.turns = [
                RequestedTool("apply_patch", "recover-patch", {"patch": script.patch}),
                RequestedTool("get_diff", "recover-early-diff", {}),
                RequestedTool("finish_task", "recover-early-finish", {}),
                RequestedTool(
                    "run_check",
                    "recover-check",
                    {"check_id": "existing-unit-tests"},
                ),
                RequestedTool("finish_task", "recover-stale-finish", {}),
                RequestedTool("get_diff", "recover-final-diff", {}),
                RequestedTool("finish_task", "recover-final-finish", {}),
            ]
            self.offset = 0

        def next_turn(self, _context, _tools):
            call = self.turns[self.offset]
            self.offset += 1
            return ModelTurn(tool_calls=[call])

    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args: RecoveringSubmissionAdapter(),
    )

    result = runner.start(TASK, model="mock")
    events = runner.state.list_events(result["run_id"])

    assert result["scope_compliant_success"] is True
    assert result["usage"]["tool_calls"] == 7
    assert sum(event.type == EventType.SUBMISSION_REJECTED for event in events) == 2
    assert sum(event.type == EventType.SUBMISSION_ACCEPTED for event in events) == 1
    review = next(event for event in events if event.type == EventType.REVIEW_RECORDED)
    accepted = next(event for event in events if event.type == EventType.SUBMISSION_ACCEPTED)
    accepted_attempt = next(
        event
        for event in events
        if event.type == EventType.SUBMISSION_ATTEMPTED
        and event.correlation_id == accepted.correlation_id
    )
    assert review.sequence < accepted_attempt.sequence < accepted.sequence
    assert review.payload["worktree_diff_hash"] == accepted.payload["worktree_diff_hash"]


def test_submission_gate_rejects_noop_after_passing_checks_and_diff_review(
    tmp_path,
    monkeypatch,
) -> None:
    class NoopSubmissionAdapter:
        def __init__(self) -> None:
            self.turns = [
                RequestedTool(
                    "run_check",
                    "noop-check",
                    {"check_id": "existing-unit-tests"},
                ),
                RequestedTool("get_diff", "noop-diff", {}),
                RequestedTool("finish_task", "noop-finish-1", {}),
                RequestedTool("finish_task", "noop-finish-2", {}),
                RequestedTool("finish_task", "noop-finish-3", {}),
            ]
            self.offset = 0

        def next_turn(self, _context, _tools):
            call = self.turns[self.offset]
            self.offset += 1
            return ModelTurn(tool_calls=[call])

    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args: NoopSubmissionAdapter(),
    )

    result = runner.start(TASK, model="mock")
    events = runner.state.list_events(result["run_id"])
    rejections = [event for event in events if event.type == EventType.SUBMISSION_REJECTED]

    assert result["outcome_kind"] == RunOutcomeKind.AGENT_FAILURE.value
    assert len(rejections) == 3
    assert all(
        "successful_mutation_current_diff" in event.payload["missing_evidence"]
        for event in rejections
    )
    assert not any(event.type == EventType.SUBMISSION_ACCEPTED for event in events)


def test_later_patch_invalidates_prior_passing_check(
    tmp_path,
    monkeypatch,
) -> None:
    class StaleCheckAdapter:
        def __init__(self) -> None:
            script = MOCK_TASK_SCRIPTS["csv-quoted-newline"]
            second_patch = (
                "diff --git a/mini_data_utils/csvlite.py "
                "b/mini_data_utils/csvlite.py\n"
                "--- a/mini_data_utils/csvlite.py\n"
                "+++ b/mini_data_utils/csvlite.py\n"
                "@@ -1,4 +1,4 @@\n"
                '-"""A deliberately small CSV reader with one audited defect."""\n'
                '+"""A deliberately small CSV reader with one repaired defect."""\n'
                " \n"
                " import csv\n"
                " import io\n"
            )
            self.turns = [
                RequestedTool("apply_patch", "stale-first-patch", {"patch": script.patch}),
                RequestedTool(
                    "run_check",
                    "stale-first-check",
                    {"check_id": "existing-unit-tests"},
                ),
                RequestedTool(
                    "apply_patch",
                    "stale-second-patch",
                    {"patch": second_patch},
                ),
                RequestedTool("get_diff", "stale-early-diff", {}),
                RequestedTool("finish_task", "stale-early-finish", {}),
                RequestedTool(
                    "run_check",
                    "stale-second-check",
                    {"check_id": "existing-unit-tests"},
                ),
                RequestedTool("get_diff", "stale-final-diff", {}),
                RequestedTool("finish_task", "stale-final-finish", {}),
            ]
            self.offset = 0

        def next_turn(self, _context, _tools):
            call = self.turns[self.offset]
            self.offset += 1
            return ModelTurn(tool_calls=[call])

    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args: StaleCheckAdapter(),
    )

    result = runner.start(TASK, model="mock")
    events = runner.state.list_events(result["run_id"])

    assert result["scope_compliant_success"] is True
    check_events = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "run_check"
    ]
    assert len(check_events) == 2
    assert (
        check_events[0].payload["worktree_diff_hash"]
        != check_events[1].payload["worktree_diff_hash"]
    )
    rejected = next(event for event in events if event.type == EventType.SUBMISSION_REJECTED)
    assert "visible_checks_current_diff" in rejected.payload["missing_evidence"]
    checkpoint = runner.state.latest_checkpoint(result["run_id"])
    assert checkpoint is not None
    assert checkpoint.completed_checks == ["existing-unit-tests"]
    assert checkpoint.pending_checks == []


def test_rejected_patch_does_not_advance_phase_and_exposes_stage(
    tmp_path,
    monkeypatch,
) -> None:
    class InvalidPatchAdapter:
        def __init__(self) -> None:
            self.offset = 0

        def next_turn(self, _context, _tools):
            self.offset += 1
            if self.offset == 1:
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "apply_patch",
                            "invalid-envelope",
                            {"patch": "*** Begin Patch\n*** End Patch"},
                        )
                    ]
                )
            return ModelTurn(text="cannot continue")

    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args: InvalidPatchAdapter(),
    )

    result = runner.start(TASK, model="mock")
    events = runner.state.list_events(result["run_id"])

    assert result["outcome_kind"] == RunOutcomeKind.AGENT_FAILURE.value
    checkpoint = runner.state.latest_checkpoint(result["run_id"])
    assert checkpoint is not None
    assert checkpoint.phase == Phase.REPRODUCE
    failed_patch = next(
        event
        for event in events
        if event.type == EventType.TOOL_FAILED and event.payload.get("tool") == "apply_patch"
    )
    assert failed_patch.payload["error_details"]["stage"] == "format"
    assert not any(
        event.type == EventType.PHASE_CHANGED and event.payload.get("to") in {"PLAN", "IMPLEMENT"}
        for event in events
    )


def test_three_submission_rejections_are_terminal_and_classified(
    tmp_path,
    monkeypatch,
) -> None:
    class PrematureSubmissionAdapter:
        def __init__(self) -> None:
            self.offset = 0

        def next_turn(self, _context, _tools):
            self.offset += 1
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "finish_task",
                        f"premature-finish-{self.offset}",
                        {},
                    )
                ]
            )

    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args: PrematureSubmissionAdapter(),
    )

    result = runner.start(TASK, model="mock")
    events = runner.state.list_events(result["run_id"])

    assert result["outcome_kind"] == RunOutcomeKind.AGENT_FAILURE.value
    assert result["terminal_error"]["type"] == "SubmissionProtocolError"
    assert sum(event.type == EventType.SUBMISSION_REJECTED for event in events) == 3
    failure_files = list((tmp_path / "runtime" / "failures").rglob("*.json"))
    assert len(failure_files) == 1
    failure = json.loads(failure_files[0].read_text(encoding="utf-8"))
    assert failure["primary_cause"] == "premature-stop"
    assert failure["recoverability"] == "terminal"


def test_evaluator_error_keeps_accepted_agent_submission(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)

    def fail_evaluator(*_args, **_kwargs):
        raise RuntimeError("synthetic evaluator outage")

    monkeypatch.setattr(
        "patchloop.agent.runner.EvaluationEngine.evaluate",
        fail_evaluator,
    )
    runner = AgentRunner(tmp_path / "runtime")

    result = runner.start(TASK, model="mock")
    events = runner.state.list_events(result["run_id"])

    assert result["outcome_kind"] == RunOutcomeKind.INFRASTRUCTURE_ERROR.value
    assert result["agent_submission_status"] == "completed"
    assert result["evaluation_status"] == "not_run"
    assert any(event.type == EventType.SUBMISSION_ACCEPTED for event in events)
    assert events[-1].type == EventType.RUN_FAILED


def test_fault_clone_preserves_replay_adapter_identity(monkeypatch) -> None:
    package = load_task_package(Path(TASK).parent)
    replay_model = f"replay:{SMOKE_REPLAYS['csv-quoted-newline']}"
    baseline = build_manifest(
        package,
        run_id="run_replay_fault_baseline",
        provider="replay",
        model_id=replay_model,
        replay_hash=sha256_bytes(Path(SMOKE_REPLAYS["csv-quoted-newline"]).read_bytes()),
    )
    captured = {}

    class FakeRunner:
        state = type(
            "FakeState",
            (),
            {"get_manifest": staticmethod(lambda _run_id: baseline)},
        )()

        @staticmethod
        def _find_task(_manifest):
            return Path(TASK).parent

        @staticmethod
        def start(_task, *, model, manifest, **_kwargs):
            captured["model"] = model
            captured["manifest"] = manifest
            return {"status": "suspended"}

    monkeypatch.setattr("patchloop.evals.faults.AgentRunner", FakeRunner)

    clone_with_fault(baseline.run_id, "worker-restart")

    assert captured["model"] == replay_model
    assert captured["manifest"].model.provider == "replay"


def test_worker_restart_resumes_without_duplicate_patch(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_recovery_test",
        sandbox_backend="local",
        fault=FaultSpec(type="worker-kill-after-patch"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    suspended = runner.start(TASK, model="mock", manifest=manifest)
    assert suspended["status"] == "suspended"
    resumed = runner.resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)
    assert resumed["scope_compliant_success"] is True
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 1


def test_worker_restart_reuses_completed_evaluation_before_terminal_commit(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_evaluation_receipt_recovery",
        sandbox_backend="local",
    )
    runtime = tmp_path / "runtime"
    runner = AgentRunner(runtime)
    real_finalize = runner.state.finalize_run

    def stop_before_terminal_commit(*_args, **_kwargs):
        raise SystemExit("synthetic process death before terminal commit")

    monkeypatch.setattr(
        runner.state,
        "finalize_run",
        stop_before_terminal_commit,
    )
    with pytest.raises(
        SystemExit,
        match="synthetic process death",
    ):
        runner.start(TASK, model="mock", manifest=manifest)

    receipt_path = runtime / "artifacts" / "runs" / manifest.run_id / "evaluation-receipt.json"
    assert receipt_path.is_file()
    persisted_before = (receipt_path.parent / "result.json").read_bytes()
    evaluator_workspaces = sorted((runtime / "workspaces").glob("eval_*"))
    assert len(evaluator_workspaces) == 1
    assert runner.state.get_run_status(manifest.run_id) == RunStatus.RUNNING

    monkeypatch.setattr(runner.state, "finalize_run", real_finalize)
    fresh_runner = AgentRunner(runtime)

    def unavailable_model_adapter(*_args, **_kwargs):
        raise AssertionError("evaluation-only recovery must not construct a model adapter")

    monkeypatch.setattr(
        fresh_runner,
        "_model_adapter",
        unavailable_model_adapter,
    )
    resumed = fresh_runner.resume(manifest.run_id)

    assert resumed["scope_compliant_success"] is True
    assert (receipt_path.parent / "result.json").read_bytes() == persisted_before
    assert sorted((runtime / "workspaces").glob("eval_*")) == evaluator_workspaces
    events = runner.state.list_events(manifest.run_id)
    assert sum(event.type == EventType.RUN_COMPLETED for event in events) == 1
    assert sum(event.type == EventType.FAILURE_TAGGED for event in events) == 0


def test_worker_restart_reuses_failed_evaluation_and_failure_record(
    tmp_path,
    monkeypatch,
) -> None:
    from patchloop.evals.failures import classify_failure as real_classify

    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_failed_eval_receipt",
        sandbox_backend="local",
    )
    runtime = tmp_path / "runtime"
    real_evaluate = EvaluationEngine.evaluate

    def evaluate_as_task_failure(self, *args, **kwargs):
        result = real_evaluate(self, *args, **kwargs)
        result.scope_compliant_success = False
        result.verdicts.hidden_tests = VerdictState.FAIL
        result.outcome_kind = RunOutcomeKind.TASK_FAILURE
        run_dir = self.artifact_store.root / "runs" / result.run_id
        self.artifact_store.write_text_atomic(
            run_dir / "result.json",
            result.model_dump_json(indent=2),
        )
        return result

    def stop_after_failure_record(*args, **kwargs):
        record = real_classify(*args, **kwargs)
        assert record is not None
        raise SystemExit("synthetic process death after failure classification")

    monkeypatch.setattr(
        EvaluationEngine,
        "evaluate",
        evaluate_as_task_failure,
    )
    monkeypatch.setattr(
        "patchloop.agent.runner.classify_failure",
        stop_after_failure_record,
    )
    runner = AgentRunner(runtime)
    with pytest.raises(
        SystemExit,
        match="after failure classification",
    ):
        runner.start(TASK, model="mock", manifest=manifest)

    receipt_path = runtime / "artifacts" / "runs" / manifest.run_id / "evaluation-receipt.json"
    result_path = receipt_path.parent / "result.json"
    result_before = result_path.read_bytes()
    failure_files = list((runtime / "failures").rglob("*.json"))
    assert len(failure_files) == 1
    evaluator_workspaces = sorted((runtime / "workspaces").glob("eval_*"))
    assert len(evaluator_workspaces) == 1

    monkeypatch.setattr(
        "patchloop.agent.runner.classify_failure",
        real_classify,
    )
    resumed = AgentRunner(runtime).resume(manifest.run_id)

    assert resumed["scope_compliant_success"] is False
    assert resumed["verdicts"]["hidden_tests"] == VerdictState.FAIL.value
    assert result_path.read_bytes() == result_before
    assert sorted((runtime / "workspaces").glob("eval_*")) == evaluator_workspaces
    events = runner.state.list_events(manifest.run_id)
    assert sum(event.type == EventType.FAILURE_TAGGED for event in events) == 1
    assert sum(event.type == EventType.RUN_COMPLETED for event in events) == 1
    assert len(list((runtime / "failures").rglob("*.json"))) == 1


@pytest.mark.parametrize(
    "tamper_target",
    ["verifier-cas", "provenance"],
)
def test_evaluation_receipt_rejects_tampered_evidence(
    tmp_path,
    monkeypatch,
    tamper_target,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(TASK, model="mock")
    manifest = runner.state.get_manifest(result["run_id"])
    accepted = next(
        event
        for event in runner.state.list_events(result["run_id"])
        if event.type == EventType.SUBMISSION_ACCEPTED
    )
    submitted_patch = Artifact.model_validate(accepted.payload["submitted_patch_artifact"])
    persisted = RunResult.model_validate_json(
        (runner.artifacts.root / "runs" / result["run_id"] / "result.json").read_text(
            encoding="utf-8"
        )
    )
    if tamper_target == "verifier-cas":
        raw_evidence = next(
            verifier.details["evidence_artifacts"][0]
            for verifier in persisted.verifier_results
            if verifier.evidence_artifact_ids
        )
        verifier_artifact = Artifact.model_validate(raw_evidence)
        Path(verifier_artifact.path).write_bytes(b"tampered verifier evidence")
        error_match = "verifier evidence artifact"
    else:
        provenance_path = runner.artifacts.root / "runs" / result["run_id"] / "provenance.json"
        provenance_path.write_bytes(provenance_path.read_bytes() + b"\n")
        error_match = "file hash"
    workspace = runner.root / "workspaces" / result["run_id"] / "repo"
    expected_patch_hash = runner.workspaces.diff_summary(workspace).patch_hash

    with pytest.raises(
        RecoveryError,
        match=error_match,
    ):
        runner._load_completed_evaluation(
            manifest,
            expected_patch_hash=expected_patch_hash,
            submitted_patch_artifact=submitted_patch,
            expected_official=False,
        )


def test_created_run_can_be_resumed_without_a_prior_worker_claim(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_created_resume",
        sandbox_backend="local",
    )
    runner = AgentRunner(tmp_path / "runtime")
    runner.state.create_run(manifest)

    result = runner.resume(manifest.run_id)

    assert result["scope_compliant_success"] is True
    claims = runner.state.list_worker_claims(manifest.run_id)
    assert len(claims) == 1
    assert claims[0]["prior_status"] == RunStatus.CREATED.value


def test_resume_recovers_run_started_before_first_checkpoint(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_started_prefix_recovery",
        sandbox_backend="local",
    )
    runner = AgentRunner(tmp_path / "runtime")
    original_transition = runner._transition

    def crash_before_transition(*_args, **_kwargs):
        raise SystemExit(86)

    monkeypatch.setattr(runner, "_transition", crash_before_transition)
    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK, model="mock", manifest=manifest)
    monkeypatch.setattr(runner, "_transition", original_transition)

    result = AgentRunner(runner.root).resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    assert sum(event.type == EventType.RUN_STARTED for event in events) == 1
    assert (
        sum(
            event.type == EventType.PHASE_CHANGED
            and event.payload == {"from": Phase.INTAKE.value, "to": Phase.REPRODUCE.value}
            for event in events
        )
        == 1
    )


def test_resume_recovers_phase_change_before_first_checkpoint(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_phase_prefix_recovery",
        sandbox_backend="local",
    )
    runner = AgentRunner(tmp_path / "runtime")
    original_checkpoint = runner._checkpoint

    def crash_before_checkpoint(*_args, **_kwargs):
        raise SystemExit(86)

    monkeypatch.setattr(runner, "_checkpoint", crash_before_checkpoint)
    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK, model="mock", manifest=manifest)
    monkeypatch.setattr(runner, "_checkpoint", original_checkpoint)

    result = AgentRunner(runner.root).resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    assert (
        sum(
            event.type == EventType.PHASE_CHANGED
            and event.payload == {"from": Phase.INTAKE.value, "to": Phase.REPRODUCE.value}
            for event in events
        )
        == 1
    )


@pytest.mark.parametrize(
    ("tool_name", "expected_transition"),
    [
        (
            "run_check",
            {
                "from": Phase.IMPLEMENT.value,
                "to": Phase.VERIFY.value,
            },
        ),
        (
            "get_diff",
            {
                "from": Phase.VERIFY.value,
                "to": Phase.REVIEW.value,
            },
        ),
    ],
)
def test_resume_replays_missing_tool_phase_suffix_once(
    tmp_path,
    monkeypatch,
    tool_name,
    expected_transition,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id=f"run_phase_suffix_{tool_name}",
        sandbox_backend="local",
    )
    runner = AgentRunner(tmp_path / "runtime")
    original_phase_after_tool = runner._phase_after_tool
    crashed = False

    def crash_after_outcome(
        run_id,
        phase,
        observed_tool,
        result,
        task,
        workspace,
    ):
        nonlocal crashed
        if observed_tool == tool_name and not crashed:
            crashed = True
            raise SystemExit(86)
        return original_phase_after_tool(
            run_id,
            phase,
            observed_tool,
            result,
            task,
            workspace,
        )

    monkeypatch.setattr(
        runner,
        "_phase_after_tool",
        crash_after_outcome,
    )
    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK, model="mock", manifest=manifest)

    result = AgentRunner(runner.root).resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    assert (
        sum(
            event.type == EventType.TOOL_CALLED and event.payload.get("tool") == tool_name
            for event in events
        )
        == 1
    )
    assert (
        sum(
            event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == tool_name
            for event in events
        )
        == 1
    )
    assert (
        sum(
            event.type == EventType.PHASE_CHANGED and event.payload == expected_transition
            for event in events
        )
        == 1
    )


def test_resume_completes_get_diff_from_orphan_tool_call(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_get_diff_call_recovery",
        sandbox_backend="local",
    )
    runner = AgentRunner(tmp_path / "runtime")
    original_dispatch = ToolGateway._dispatch
    crashed = False

    def crash_after_get_diff_call(self, name, arguments):
        nonlocal crashed
        if name == "get_diff" and not crashed:
            crashed = True
            raise SystemExit(86)
        return original_dispatch(self, name, arguments)

    monkeypatch.setattr(
        ToolGateway,
        "_dispatch",
        crash_after_get_diff_call,
    )
    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK, model="mock", manifest=manifest)

    result = AgentRunner(runner.root).resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    assert (
        sum(
            event.type == EventType.TOOL_CALLED and event.payload.get("tool") == "get_diff"
            for event in events
        )
        == 1
    )
    assert (
        sum(
            event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "get_diff"
            for event in events
        )
        == 1
    )


def test_resume_does_not_promote_orphan_read_over_external_staged_change(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_orphan_read_external_change",
        sandbox_backend="local",
    )
    runner = AgentRunner(tmp_path / "runtime")
    original_dispatch = ToolGateway._dispatch
    crashed = False

    def crash_after_get_diff_call(self, name, arguments):
        nonlocal crashed
        if name == "get_diff" and not crashed:
            crashed = True
            raise SystemExit(86)
        return original_dispatch(self, name, arguments)

    monkeypatch.setattr(
        ToolGateway,
        "_dispatch",
        crash_after_get_diff_call,
    )
    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK, model="mock", manifest=manifest)

    checkpoints_before = runner.state.list_checkpoints(manifest.run_id)
    workspace = runner.root / "workspaces" / manifest.run_id / "repo"
    readme = workspace / "README.md"
    changed = readme.read_bytes() + b"\nexternal staged change\n"
    readme.write_bytes(changed)
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=workspace,
        check=True,
        capture_output=True,
    )

    with pytest.raises(RecoveryError, match="diff hash"):
        AgentRunner(runner.root).resume(manifest.run_id)

    assert readme.read_bytes() == changed
    checkpoints_after = runner.state.list_checkpoints(manifest.run_id)
    assert [item.checkpoint_id for item in checkpoints_after] == [
        item.checkpoint_id for item in checkpoints_before
    ]


def test_resume_does_not_promote_completed_read_over_external_change(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_completed_read_external_change",
        sandbox_backend="local",
    )
    runner = AgentRunner(tmp_path / "runtime")
    original_phase_after_tool = runner._phase_after_tool
    crashed = False

    def crash_after_get_diff_outcome(
        run_id,
        phase,
        tool_name,
        result,
        task,
        workspace,
    ):
        nonlocal crashed
        if tool_name == "get_diff" and not crashed:
            crashed = True
            raise SystemExit(86)
        return original_phase_after_tool(
            run_id,
            phase,
            tool_name,
            result,
            task,
            workspace,
        )

    monkeypatch.setattr(
        runner,
        "_phase_after_tool",
        crash_after_get_diff_outcome,
    )
    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK, model="mock", manifest=manifest)

    checkpoints_before = runner.state.list_checkpoints(manifest.run_id)
    workspace = runner.root / "workspaces" / manifest.run_id / "repo"
    readme = workspace / "README.md"
    changed = readme.read_bytes() + b"\nexternal tracked change\n"
    readme.write_bytes(changed)

    with pytest.raises(RecoveryError, match="diff hash"):
        AgentRunner(runner.root).resume(manifest.run_id)

    assert readme.read_bytes() == changed
    checkpoints_after = runner.state.list_checkpoints(manifest.run_id)
    assert [item.checkpoint_id for item in checkpoints_after] == [
        item.checkpoint_id for item in checkpoints_before
    ]


@pytest.mark.parametrize(
    "crash_point",
    ["before-run-started", "after-run-started"],
)
def test_pre_checkpoint_resume_rejects_different_clean_base(
    tmp_path,
    monkeypatch,
    crash_point,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id=f"run_wrong_base_{crash_point.replace('-', '_')}",
        sandbox_backend="local",
    )
    runner = AgentRunner(tmp_path / "runtime")

    def crash(*_args, **_kwargs):
        raise SystemExit(86)

    if crash_point == "before-run-started":
        monkeypatch.setattr(runner, "_execute", crash)
    else:
        monkeypatch.setattr(runner, "_transition", crash)
    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK, model="mock", manifest=manifest)

    workspace = runner.root / "workspaces" / manifest.run_id / "repo"
    readme = workspace / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\nwrong clean base\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=workspace,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-qm", "different clean base"],
        cwd=workspace,
        check=True,
        capture_output=True,
    )

    with pytest.raises(ContractError, match="immutable base revision"):
        AgentRunner(runner.root).resume(manifest.run_id)

    assert runner.state.get_run_status(manifest.run_id) == RunStatus.FAILED
    assert runner.state.list_checkpoints(manifest.run_id) == []
    assert not [
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.MODEL_CALLED
    ]


def test_fatal_interrupted_patch_does_not_promote_unknown_checkpoint(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_unknown_patch_recovery",
        sandbox_backend="local",
    )
    runner = AgentRunner(tmp_path / "runtime")
    original_finalize = ToolGateway._finalize_applied_patch

    def crash_after_mutation(*_args, **_kwargs):
        raise SystemExit(86)

    monkeypatch.setattr(
        ToolGateway,
        "_finalize_applied_patch",
        crash_after_mutation,
    )
    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK, model="mock", manifest=manifest)
    monkeypatch.setattr(
        ToolGateway,
        "_finalize_applied_patch",
        original_finalize,
    )
    checkpoints_before = runner.state.list_checkpoints(manifest.run_id)
    target = (
        runner.root / "workspaces" / manifest.run_id / "repo" / "mini_data_utils" / "csvlite.py"
    )
    unknown = target.read_text(encoding="utf-8").replace(
        'newline=""',
        "newline=None",
    )
    target.write_text(unknown, encoding="utf-8")

    with pytest.raises(RecoveryError, match="unknown state"):
        AgentRunner(runner.root).resume(manifest.run_id)

    checkpoints_after = runner.state.list_checkpoints(manifest.run_id)
    assert [item.checkpoint_id for item in checkpoints_after] == [
        item.checkpoint_id for item in checkpoints_before
    ]
    assert target.read_text(encoding="utf-8") == unknown
    assert runner.state.get_run_status(manifest.run_id) == RunStatus.FAILED
    events = runner.state.list_events(manifest.run_id)
    assert (
        sum(
            event.type == EventType.TOOL_FAILED
            and event.payload.get("tool") == "apply_patch"
            and event.payload.get("error_details", {}).get("fatal") is True
            for event in events
        )
        == 1
    )
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 0


def test_resume_rejects_replaced_workspace_root_before_patch_recovery(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_replaced_workspace_root",
        sandbox_backend="local",
    )
    runner = AgentRunner(tmp_path / "runtime")
    original_apply_postimages = ToolGateway._apply_patch_postimages

    def crash_before_postimage_write(*_args, **_kwargs):
        raise SystemExit(86)

    monkeypatch.setattr(
        ToolGateway,
        "_apply_patch_postimages",
        crash_before_postimage_write,
    )
    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK, model="mock", manifest=manifest)
    monkeypatch.setattr(
        ToolGateway,
        "_apply_patch_postimages",
        original_apply_postimages,
    )

    workspace = runner.root / "workspaces" / manifest.run_id / "repo"
    external = tmp_path / "external-identical-workspace"
    backup = workspace.with_name("repo.backup")
    shutil.copytree(workspace, external)
    workspace.rename(backup)
    external_target = external / "mini_data_utils" / "csvlite.py"
    external_before = external_target.read_bytes()
    linked = False
    try:
        if os.name == "nt":
            linked_result = subprocess.run(
                [
                    "cmd",
                    "/c",
                    "mklink",
                    "/J",
                    str(workspace),
                    str(external),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if linked_result.returncode != 0:
                pytest.skip(
                    f"Windows junction creation is unavailable: {linked_result.stderr.strip()}"
                )
        else:
            workspace.symlink_to(
                external,
                target_is_directory=True,
            )
        linked = True

        with pytest.raises(
            ContractError,
            match="symlink or junction",
        ):
            AgentRunner(runner.root).resume(manifest.run_id)

        assert external_target.read_bytes() == external_before
        assert not any(
            event.type == EventType.PATCH_APPLIED
            for event in runner.state.list_events(manifest.run_id)
        )
    finally:
        if linked:
            if workspace.is_symlink():
                workspace.unlink()
            else:
                workspace.rmdir()
        if backup.exists():
            backup.rename(workspace)


def test_malformed_prepared_mode_is_fatal_without_checkpoint_promotion(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_malformed_mode_recovery",
        sandbox_backend="local",
    )
    runner = AgentRunner(tmp_path / "runtime")
    original_put_json = runner.artifacts.put_json
    original_finalize = ToolGateway._finalize_applied_patch

    def persist_malformed_mode(value):
        if isinstance(value, dict) and value.get("schema_version") == "patch-mutation-intent-v1":
            value = json.loads(json.dumps(value))
            value["files"][0]["mode"] = "not-an-int"
        return original_put_json(value)

    def crash_after_mutation(*_args, **_kwargs):
        raise SystemExit(86)

    monkeypatch.setattr(
        runner.artifacts,
        "put_json",
        persist_malformed_mode,
    )
    monkeypatch.setattr(
        ToolGateway,
        "_finalize_applied_patch",
        crash_after_mutation,
    )
    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK, model="mock", manifest=manifest)
    monkeypatch.setattr(
        ToolGateway,
        "_finalize_applied_patch",
        original_finalize,
    )
    checkpoints_before = runner.state.list_checkpoints(manifest.run_id)

    with pytest.raises(RecoveryError, match="file image evidence"):
        AgentRunner(runner.root).resume(manifest.run_id)

    checkpoints_after = runner.state.list_checkpoints(manifest.run_id)
    assert [item.checkpoint_id for item in checkpoints_after] == [
        item.checkpoint_id for item in checkpoints_before
    ]
    assert runner.state.get_run_status(manifest.run_id) == RunStatus.FAILED


def test_replay_worker_restart_preserves_source_identity(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    replay_path = SMOKE_REPLAYS["config-falsy-override"]
    replay_hash = sha256_bytes(Path(replay_path).read_bytes())
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_manifest(
        package,
        run_id="run_replay_recovery",
        provider="replay",
        model_id=f"replay:{replay_path}",
        replay_hash=replay_hash,
        sandbox_backend="local",
        fault=FaultSpec(type="worker-kill-after-patch"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    suspended = runner.start(
        SMOKE_TASKS["config-falsy-override"],
        model=f"replay:{replay_path}",
        manifest=manifest,
    )
    assert suspended["status"] == "suspended"

    resumed = runner.resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)
    assert resumed["scope_compliant_success"] is True
    assert runner.state.get_manifest(manifest.run_id).model.replay_hash == replay_hash
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 1


def test_resume_rejects_checkpoint_worktree_mismatch(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_corrupt_checkpoint",
        sandbox_backend="local",
        fault=FaultSpec(type="worker-kill-after-patch"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    runner.start(TASK, model="mock", manifest=manifest)
    checkpoint = runner.state.latest_checkpoint(manifest.run_id)
    assert checkpoint is not None
    corrupt = checkpoint.model_copy(
        update={
            "checkpoint_id": f"ckpt_{uuid.uuid4().hex}",
            "through_sequence": runner.state.last_sequence(manifest.run_id),
            "worktree_diff_hash": "sha256:corrupt",
            "created_at": utc_now(),
        }
    )
    runner.state.save_checkpoint(corrupt)
    with pytest.raises(RecoveryError, match="diff hash"):
        runner.resume(manifest.run_id)


def test_resume_rejects_untracked_workspace_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_untracked_recovery",
        sandbox_backend="local",
        fault=FaultSpec(type="worker-kill-after-patch"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    suspended = runner.start(TASK, model="mock", manifest=manifest)
    assert suspended["status"] == "suspended"
    workspace = runner.root / "workspaces" / manifest.run_id / "repo"
    (workspace / "untracked-agent-state.txt").write_text(
        "must not survive recovery",
        encoding="utf-8",
    )

    with pytest.raises(RecoveryError, match="untracked files during recovery"):
        runner.resume(manifest.run_id)


def test_checkpoint_rejects_untracked_workspace_state(tmp_path) -> None:
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_untracked_checkpoint",
        sandbox_backend="local",
    )
    runner = AgentRunner(tmp_path / "runtime")
    runner.state.create_run(manifest)
    workspace = runner.workspaces.create(
        manifest.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    (workspace / "untracked-agent-state.txt").write_text(
        "must not enter a checkpoint",
        encoding="utf-8",
    )

    with pytest.raises(RecoveryError, match="untracked files at checkpoint"):
        runner._checkpoint(manifest, workspace, Phase.INTAKE)


def test_run_check_untracked_output_fails_as_infrastructure_error(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    real_run_check = LocalSandbox.run_check

    def run_check_and_leave_untracked(self, workspace, check):
        result = real_run_check(self, workspace, check)
        (workspace / "untracked-check-output.txt").write_text(
            "must not enter a checkpoint",
            encoding="utf-8",
        )
        return result

    monkeypatch.setattr(LocalSandbox, "run_check", run_check_and_leave_untracked)
    runner = AgentRunner(tmp_path / "runtime")

    result = runner.start(TASK, model="mock")

    assert result["outcome_kind"] == RunOutcomeKind.INFRASTRUCTURE_ERROR.value
    assert result["terminal_error"]["type"] == "RecoveryError"
    assert "untracked files at checkpoint" in result["terminal_error"]["message"]
    assert result["evaluation_status"] == "not_run"


def test_run_check_staged_tracked_mutation_closes_tool_evidence_and_usage(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    real_run_check = LocalSandbox.run_check

    def run_check_and_mutate_tracked_file(self, workspace, check):
        result = real_run_check(self, workspace, check)
        target = workspace / "mini_data_utils" / "csvlite.py"
        target.write_text(
            target.read_text(encoding="utf-8") + "\n# check mutation\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", "mini_data_utils/csvlite.py"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )
        return result

    monkeypatch.setattr(
        LocalSandbox,
        "run_check",
        run_check_and_mutate_tracked_file,
    )
    runner = AgentRunner(tmp_path / "runtime")

    result = runner.start(TASK, model="mock")
    events = runner.state.list_events(result["run_id"])
    failed_checks = [
        event
        for event in events
        if event.type == EventType.TOOL_FAILED and event.payload.get("tool") == "run_check"
    ]

    assert result["outcome_kind"] == RunOutcomeKind.INFRASTRUCTURE_ERROR.value
    assert result["terminal_error"]["type"] == "RecoveryError"
    assert len(failed_checks) == 1
    assert failed_checks[0].payload["error_code"] == "RECOVERY_ERROR"
    assert Path(failed_checks[0].payload["artifact_path"]).is_file()
    assert result["usage"]["tool_calls"] == sum(
        event.type == EventType.TOOL_CALLED for event in events
    )


def test_timeout_fault_is_recorded_without_repeating_command(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_timeout_fault",
        sandbox_backend="local",
        fault=FaultSpec(type="test-timeout"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(TASK, model="mock", manifest=manifest)
    assert result["outcome_kind"] == RunOutcomeKind.AGENT_FAILURE.value
    assert "visible check" in result["terminal_error"]["message"]
    events = runner.state.list_events(manifest.run_id)
    timed_out_checks = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("timed_out") is True
    ]
    assert len(timed_out_checks) == 1
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 3
    assert events[-1].type == EventType.RUN_FAILED


def test_controlled_rejection_full_agent_loop_rehydrates_exact_candidate(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    script = MOCK_TASK_SCRIPTS[package.public.task_id]
    manifest = build_manifest(
        package,
        run_id="run_controlled_rejection_agent_e2e",
        sandbox_backend="local",
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
    )

    class ControlledRetryAdapter:
        def __init__(self) -> None:
            self.turn = 0
            self.contexts: list[str] = []

        def next_turn(self, context, tools):
            del tools
            self.contexts.append(context)
            calls = [
                RequestedTool(
                    "read_file",
                    "controlled-read",
                    {
                        "path": script.target_path,
                        "start_line": 1,
                        "end_line": 200,
                    },
                ),
                RequestedTool(
                    "apply_patch",
                    "controlled-candidate",
                    {"patch": script.patch},
                ),
                RequestedTool(
                    "apply_patch",
                    "controlled-retry",
                    {"patch": script.patch},
                ),
                RequestedTool(
                    "run_check",
                    "controlled-check",
                    {"check_id": "existing-unit-tests"},
                ),
                RequestedTool(
                    "get_diff",
                    "controlled-review",
                    {},
                ),
                RequestedTool(
                    "finish_task",
                    "controlled-finish",
                    {},
                ),
            ]
            call = calls[self.turn]
            self.turn += 1
            return ModelTurn(tool_calls=[call])

    adapter = ControlledRetryAdapter()
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args, **_kwargs: adapter,
    )

    result = runner.start(TASK, model="mock", manifest=manifest)

    assert result["outcome_kind"] == RunOutcomeKind.RESOLVED.value
    retry_context = json.loads(adapter.contexts[2])[
        "rejected_mutation_retry"
    ]
    assert retry_context["candidate"]["patch"] == script.patch
    assert (
        retry_context["candidate"]["content_hash"]
        == sha256_bytes(script.patch.encode("utf-8"))
    )
    assert (
        retry_context["rejection"]["error_code"]
        == "CONTROLLED_DIAGNOSTIC_REJECTION"
    )
    assert (
        retry_context["rejection"]["error_details"]["worktree_mutated"]
        is False
    )
    assert (
        json.loads(adapter.contexts[3])["rejected_mutation_retry"]
        is None
    )
    events = runner.state.list_events(manifest.run_id)
    assert sum(
        event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code")
        == "CONTROLLED_DIAGNOSTIC_REJECTION"
        for event in events
    ) == 1
    assert sum(
        event.type == EventType.PATCH_APPLIED for event in events
    ) == 1


def test_resume_reuses_durable_controlled_rejection_before_checkpoint(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    script = MOCK_TASK_SCRIPTS[package.public.task_id]
    manifest = build_manifest(
        package,
        run_id="run_controlled_rejection_checkpoint_recovery",
        sandbox_backend="local",
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
    )
    runner = AgentRunner(tmp_path / "runtime")
    original_phase_after_tool = runner._phase_after_tool
    crashed = False

    def crash_after_controlled_result(
        run_id,
        phase,
        tool,
        result,
        task,
        workspace,
    ):
        nonlocal crashed
        if (
            tool == "apply_patch"
            and result.error_code == "CONTROLLED_DIAGNOSTIC_REJECTION"
            and not crashed
        ):
            crashed = True
            raise SystemExit(87)
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
        crash_after_controlled_result,
    )
    with pytest.raises(SystemExit, match="87"):
        runner.start(TASK, model="mock", manifest=manifest)

    events_before = runner.state.list_events(manifest.run_id)
    controlled_call = next(
        event
        for event in events_before
        if event.type == EventType.TOOL_CALLED
        and event.payload.get("tool") == "apply_patch"
    )
    controlled_failure = next(
        event
        for event in events_before
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code")
        == "CONTROLLED_DIAGNOSTIC_REJECTION"
    )
    checkpoint_before = runner.state.latest_checkpoint(manifest.run_id)
    assert checkpoint_before is not None
    assert checkpoint_before.through_sequence < controlled_call.sequence
    assert controlled_call.sequence < controlled_failure.sequence
    prior_before = runner.state.get_action_result(
        manifest.run_id,
        str(controlled_call.correlation_id),
        str(controlled_call.payload["input_hash"]),
    )
    assert prior_before is not None
    assert prior_before.error_code == "CONTROLLED_DIAGNOSTIC_REJECTION"

    class ResumeAdapter:
        def __init__(self) -> None:
            self.turn = 0

        def next_turn(self, context, tools):
            del context, tools
            calls = [
                RequestedTool(
                    "apply_patch",
                    "controlled-recovery-retry",
                    {"patch": script.patch},
                ),
                RequestedTool(
                    "run_check",
                    "controlled-recovery-check",
                    {"check_id": "existing-unit-tests"},
                ),
                RequestedTool(
                    "get_diff",
                    "controlled-recovery-review",
                    {},
                ),
                RequestedTool(
                    "finish_task",
                    "controlled-recovery-finish",
                    {},
                ),
            ]
            call = calls[self.turn]
            self.turn += 1
            return ModelTurn(tool_calls=[call])

    resumed_runner = AgentRunner(runner.root)
    adapter = ResumeAdapter()
    monkeypatch.setattr(
        resumed_runner,
        "_model_adapter",
        lambda *_args, **_kwargs: adapter,
    )

    def reject_recomputation(*_args, **_kwargs):
        raise AssertionError("durable controlled rejection must be reused")

    monkeypatch.setattr(
        ToolGateway,
        "_controlled_rejection",
        reject_recomputation,
    )
    result = resumed_runner.resume(manifest.run_id)

    assert result["outcome_kind"] == RunOutcomeKind.RESOLVED.value
    events = runner.state.list_events(manifest.run_id)
    assert sum(
        event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code")
        == "CONTROLLED_DIAGNOSTIC_REJECTION"
        for event in events
    ) == 1
    assert not any(
        event.type == EventType.PATCH_APPLIED
        and event.correlation_id == controlled_call.correlation_id
        for event in events
    )
    assert sum(
        event.type == EventType.PATCH_APPLIED
        and event.correlation_id == "controlled-recovery-retry"
        for event in events
    ) == 1
    prior_after = runner.state.get_action_result(
        manifest.run_id,
        str(controlled_call.correlation_id),
        str(controlled_call.payload["input_hash"]),
    )
    assert prior_after == prior_before
