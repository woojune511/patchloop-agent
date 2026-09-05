from __future__ import annotations

import json
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest

import patchloop.dev.runner as runner
from patchloop.agent.model import (
    EncryptedReasoningContinuationItem,
    FunctionCallContinuationRef,
    ModelTurn,
    ModelTurnError,
)
from patchloop.agent.model import RequestedTool as ProviderTool
from patchloop.contracts import TaskEnvironment
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev.contracts import DevModelTurn, DevRunRequest, PublicTurnDecision, RequestedTool
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ResumeContractMismatch
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.sandbox.runner import SandboxCleanupError, SandboxResult


class SimulatedCrash(BaseException):
    pass


def _request(root: Path) -> DevRunRequest:
    return DevRunRequest(
        provider="mock", task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        model="mock-dev", state_root=root,
    )


def _mutation(action_id="mutation") -> RequestedTool:
    item = MOCK_MUTATIONS["csv-quoted-newline"]
    return RequestedTool(
        name="replace_text", action_id=action_id,
        arguments={
            "path": item.path, "old_text": item.old_text, "new_text": item.new_text,
            "occurrence": 1, "hypothesis": item.hypothesis,
            "expected_behavior": item.expected_behavior, "causal_revision": None,
        },
        turn_decision=PublicTurnDecision(mode="mutate", basis="Use the exact observed source."),
    )


def _read(gateway, path, action_id="read"):
    return gateway.execute(RequestedTool(
        name="read_file", action_id=action_id,
        arguments={"path": path, "start_line": 1, "end_line": 80},
        turn_decision=PublicTurnDecision(
            mode="inspect", basis="Read the public source", evidence_goal="Acquire exact anchor",
        ),
    ))


def _restart(gateway, journal):
    return DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task,
        sandbox=gateway.sandbox, journal=journal, limits=gateway.limits,
    )


@pytest.mark.parametrize("boundary", ["before_admission", "after_admission", "after_write"])
def test_run_resume_mutation_crash_has_one_admission_and_one_write(
    tmp_path, monkeypatch, boundary,
) -> None:
    append = DevJournal.append
    replace = WorkspaceManager.atomic_replace_source
    crashed = False
    writes = 0

    def intercept_append(self, event_type, payload=None):
        nonlocal crashed
        matches = event_type == "action_started" and (payload or {}).get("tool") == "replace_text"
        if matches and not crashed and boundary == "before_admission":
            crashed = True
            raise SimulatedCrash()
        result = append(self, event_type, payload)
        if matches and not crashed and boundary == "after_admission":
            crashed = True
            raise SimulatedCrash()
        return result

    def intercept_replace(workspace, path, content):
        nonlocal crashed, writes
        replace(workspace, path, content)
        writes += 1
        if not crashed and boundary == "after_write":
            crashed = True
            raise SimulatedCrash()

    monkeypatch.setattr(DevJournal, "append", intercept_append)
    monkeypatch.setattr(WorkspaceManager, "atomic_replace_source", staticmethod(intercept_replace))
    request = _request(tmp_path)
    with pytest.raises(SimulatedCrash):
        runner.run_dev(request)
    run_id = next((tmp_path / "runs").glob("*.jsonl")).stem
    result = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert result["accepted_mutations"] == writes == 1
    rows = DevJournal(tmp_path, run_id).events()
    admissions = [r for r in rows if r["event_type"] == "action_started"
                  and r["payload"].get("tool") == "replace_text"]
    assert len(admissions) == 1
    assert admissions[0]["payload"]["mutation_expected_worktree_diff_hash"].startswith("sha256:")


def test_pending_candidate_rejects_drift_in_another_modified_file(
    gateway_factory, monkeypatch,
) -> None:
    gateway, journal, workspace = gateway_factory()
    gateway.public_task = gateway.public_task.model_copy(update={
        "constraints": gateway.public_task.constraints.model_copy(update={"max_changed_files": 2})
    })
    _read(gateway, "mini_data_utils/csvlite.py")
    assert gateway.execute(_mutation()).status == "succeeded"
    _read(gateway, "mini_data_utils/__init__.py", "read-second")
    second = _mutation("second-mutation").model_copy(update={"arguments": {
        **_mutation().arguments, "path": "mini_data_utils/__init__.py",
        "old_text": "Small data utilities", "new_text": "Tiny data utilities",
    }})
    original = WorkspaceManager.atomic_replace_source

    def crash_after_write(*args):
        original(*args)
        raise SimulatedCrash()

    monkeypatch.setattr(WorkspaceManager, "atomic_replace_source", staticmethod(crash_after_write))
    with pytest.raises(SimulatedCrash):
        gateway.execute(second)
    first = workspace / "mini_data_utils/csvlite.py"
    first.write_bytes(first.read_bytes().replace(b"import csv", b"import csv  # drift"))
    before = journal.path.read_bytes()
    with pytest.raises(ResumeContractMismatch, match="baseline and admitted candidate"):
        runner._validate_resumed_workspace(workspace, journal)
    assert journal.path.read_bytes() == before


def test_pending_scope_candidate_rolls_back_and_records_baseline_hash(
    gateway_factory, monkeypatch,
) -> None:
    gateway, journal, workspace = gateway_factory()
    gateway.public_task = gateway.public_task.model_copy(update={
        "constraints": gateway.public_task.constraints.model_copy(update={"max_diff_lines": 1})
    })
    _read(gateway, "mini_data_utils/csvlite.py")
    baseline = gateway.current_diff_hash
    before = (workspace / "mini_data_utils/csvlite.py").read_bytes()
    original = WorkspaceManager.atomic_replace_source
    crashed = False

    def crash_once(*args):
        nonlocal crashed
        original(*args)
        if not crashed:
            crashed = True
            raise SimulatedCrash()

    monkeypatch.setattr(WorkspaceManager, "atomic_replace_source", staticmethod(crash_once))
    with pytest.raises(SimulatedCrash):
        gateway.execute(_mutation())
    candidate = gateway.current_diff_hash
    runner._validate_resumed_workspace(workspace, journal)
    resumed = _restart(gateway, journal)
    result = resumed.execute(_mutation())
    assert result.status == "failed"
    assert result.output["mutation_failure"]["class"] == "scope_violation"
    assert result.output["mutation_failure"]["candidate"]["diff_hash"] == candidate
    assert result.output["mutation_failure"]["baseline"]["diff_hash"] == baseline
    assert result.workspace_diff_hash == baseline
    assert resumed.current_diff_hash == baseline
    assert (workspace / "mini_data_utils/csvlite.py").read_bytes() == before
    assert _restart(resumed, journal).last_failed_mutation == resumed.last_failed_mutation


def test_pending_scope_rollback_restores_crlf_after_empty_candidate(
    gateway_factory, monkeypatch,
) -> None:
    gateway, journal, workspace = gateway_factory()
    path = "mini_data_utils/csvlite.py"
    target = workspace / path
    old_text = target.read_text(encoding="utf-8")
    preimage = old_text.replace("\n", "\r\n").encode()
    target.write_bytes(preimage)
    for arguments in (
        ["config", "core.autocrlf", "false"], ["add", "--", path],
        ["-c", "user.name=Audit", "-c", "user.email=audit@example.invalid",
         "commit", "-qm", "CRLF audit baseline"],
    ):
        subprocess.run(["git", *arguments], cwd=workspace, check=True, capture_output=True)
    gateway.public_task = gateway.public_task.model_copy(update={
        "constraints": gateway.public_task.constraints.model_copy(update={"max_diff_lines": 1})
    })
    _read(gateway, path)
    call = _mutation().model_copy(update={"arguments": {
        **_mutation().arguments, "old_text": old_text, "new_text": "",
    }})
    original = WorkspaceManager.atomic_replace_source
    crashed = False

    def crash_once(*args):
        nonlocal crashed
        original(*args)
        if not crashed:
            crashed = True
            raise SimulatedCrash()

    monkeypatch.setattr(WorkspaceManager, "atomic_replace_source", staticmethod(crash_once))
    with pytest.raises(SimulatedCrash):
        gateway.execute(call)
    assert target.read_bytes() == b""
    result = _restart(gateway, journal).execute(call)
    assert result.output["mutation_failure"]["class"] == "scope_violation"
    assert result.output["mutation_failure"]["rolled_back"] is True
    assert target.read_bytes() == preimage


@pytest.mark.parametrize("boundary", ["correction", "next_turn_started"])
@pytest.mark.parametrize("invalid_shape", ["reasoning_only", "mixed_batch"])
def test_provider_correction_survives_crash_without_repeating_dispatch(
    tmp_path, monkeypatch, boundary, invalid_shape,
) -> None:
    inputs = []
    executions = 0
    counted = 0
    stop_arguments = {
        "reason_code": "insufficient_public_evidence", "summary": "End synthetic run",
        "evidence_span_ids": [],
        "turn_decision": {"mode": "stop", "basis": "End", "evidence_goal": None},
    }

    class FakeProvider:
        def __init__(self, config, *, api_key):
            assert api_key == "unused"

        def request_payload(self, context, schemas, *, system_prompt):
            return {"input": context, "tools": schemas, "max_output_tokens": 25000}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            nonlocal counted
            counted += 1
            return 20

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            nonlocal executions
            executions += 1
            inputs.append(request["input"])
            stop = ProviderTool("stop_task", f"stop-{executions}", stop_arguments)
            if executions > 1:
                return ModelTurn(tool_calls=[stop], input_tokens=20, output_tokens=5)
            reasoning = EncryptedReasoningContinuationItem("rs-audit", "cipher-audit")
            if invalid_shape == "reasoning_only":
                return ModelTurn(
                    input_tokens=20, output_tokens=5, response_status="incomplete",
                    response_incomplete_reason="max_output_tokens",
                    error=ModelTurnError("incomplete_response", "max_output_tokens"),
                    output_item_types=("reasoning",), provider_continuation=(reasoning,),
                )
            read = ProviderTool("read_file", "read-invalid", {
                "path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 10,
                "turn_decision": {"mode": "inspect", "basis": "Read", "evidence_goal": "Source"},
            })
            return ModelTurn(
                tool_calls=[read, stop], input_tokens=20, output_tokens=5,
                output_item_types=("reasoning", "function_call", "function_call"),
                provider_continuation=(reasoning, FunctionCallContinuationRef(read.action_id),
                                       FunctionCallContinuationRef(stop.action_id)),
            )

    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", FakeProvider)
    monkeypatch.setattr(runner, "_live_task_is_admitted", lambda *args: None)
    monkeypatch.setattr(runner, "_live_source_preflight", lambda *args: None)
    monkeypatch.setattr(runner, "_live_sandbox_preflight", lambda *args: LocalSandbox())
    monkeypatch.setattr(runner, "load_exact_openai_api_key", lambda path: "unused")
    task_dir, package = runner._resolve_task_file(_request(tmp_path).task)
    package = package.model_copy(update={"environment": TaskEnvironment(
        evaluator_image="audit/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64,
    )})
    monkeypatch.setattr(runner, "_resolve_task_file", lambda task: (task_dir, package))
    append = DevJournal.append
    seen_correction = crashed = False

    def crash_append(self, event_type, payload=None):
        nonlocal seen_correction, crashed
        result = append(self, event_type, payload)
        if event_type == "protocol_correction":
            seen_correction = True
        if not crashed and seen_correction and (
            (boundary == "correction" and event_type == "protocol_correction")
            or (boundary == "next_turn_started" and event_type == "turn_started")
        ):
            crashed = True
            raise SimulatedCrash()
        return result

    monkeypatch.setattr(DevJournal, "append", crash_append)
    request = _request(tmp_path).model_copy(update={
        "provider": "openai", "model": "gpt-5.4-mini-2026-03-17",
        "env_file": tmp_path / "credential.env", "max_cost_usd": Decimal("1.20"),
    })
    with pytest.raises(SimulatedCrash):
        runner.run_dev(request)
    run_id = next((tmp_path / "runs").glob("*.jsonl")).stem
    result = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED"
    assert executions == counted == 2
    assert result["accepted_mutations"] == 0
    context = json.loads(inputs[-1][-1]["content"])
    cards = context["recent_attempt_result_next_question"]
    assert any(card["attempt"] == "protocol" for card in cards)
    expected_code = (
        "incomplete_response" if invalid_shape == "reasoning_only" else "INVALID_TOOL_BATCH"
    )
    assert any(card["result"] == expected_code for card in cards)
    if invalid_shape == "reasoning_only":
        assert "max_output_tokens" in json.dumps(cards)
    assert sum(item.get("type") == "reasoning" for item in inputs[-1]) == 1
    journal = DevJournal(tmp_path, run_id)
    assert len([r for r in journal.events() if r["event_type"] == "provider_call_started"]) == 2
    before = journal.path.read_bytes()
    assert runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0] == result
    assert executions == 2 and journal.path.read_bytes() == before


def test_deadline_after_model_response_starts_no_tool(tmp_path, monkeypatch) -> None:
    clock = [0.0]
    monkeypatch.setattr(runner, "monotonic", lambda: clock[0])

    class LateAdapter:
        def __init__(self, task_id):
            pass

        def next_turn(self, context, schemas):
            clock[0] = 1800
            return DevModelTurn(tool_calls=[RequestedTool(
                name="run_check", action_id="too-late",
                arguments={"check_id": "existing-unit-tests"},
                turn_decision=PublicTurnDecision(mode="verify", basis="Observe baseline"),
            )])

    monkeypatch.setattr(runner, "MockDevAdapter", LateAdapter)
    result = runner.run_dev(_request(tmp_path))["runs"][0]
    assert result["terminal"] == "LIMIT_REACHED"
    rows = DevJournal(tmp_path, result["run_id"]).events()
    assert not [r for r in rows if r["event_type"] == "action_started"]


def test_expired_pending_read_does_not_repeat_filesystem_execution(
    gateway_factory, monkeypatch,
) -> None:
    gateway, journal, _ = gateway_factory()
    append = DevJournal.append
    crashed = False

    def crash_after_read_start(self, event_type, payload=None):
        nonlocal crashed
        result = append(self, event_type, payload)
        if not crashed and event_type == "action_started":
            crashed = True
            raise SimulatedCrash()
        return result

    monkeypatch.setattr(DevJournal, "append", crash_after_read_start)
    with pytest.raises(SimulatedCrash):
        _read(gateway, "mini_data_utils/csvlite.py")
    resumed = _restart(gateway, journal)
    resumed.deadline = ExecutionDeadline.from_remaining(0)

    def forbidden_execution(*args):
        raise AssertionError("expired pending read performed filesystem work")

    monkeypatch.setattr(resumed, "_perform", forbidden_execution)
    before = journal.path.read_bytes()
    with pytest.raises(ExecutionDeadlineExceeded):
        _read(resumed, "mini_data_utils/csvlite.py")
    assert journal.path.read_bytes() == before


def test_deadline_after_submission_keeps_manifest_and_evaluator_provenance(
    tmp_path, monkeypatch,
) -> None:
    clock = [0.0]
    monkeypatch.setattr(runner, "monotonic", lambda: clock[0])
    append = DevJournal.append

    def expire_after_manifest(self, event_type, payload=None):
        result = append(self, event_type, payload)
        if event_type == "manifest_recorded":
            clock[0] = 1800
        return result

    monkeypatch.setattr(DevJournal, "append", expire_after_manifest)
    result = runner.run_dev(_request(tmp_path))["runs"][0]
    assert result["terminal"] == "LIMIT_REACHED"
    root = tmp_path / "artifacts" / "runs" / result["run_id"]
    assert (root / "manifest.json").is_file()
    assert (root / "terminal-provenance.json").is_file()
    provenance = json.loads((root / "provenance.json").read_text())
    assert provenance["deadline_exhausted"] is True
    assert provenance["completed_check_results"] == []
    terminal = DevJournal(tmp_path, result["run_id"]).terminal()
    assert terminal["payload"]["milestones"]["submission"] is not None


def test_gateway_cleanup_failure_stops_all_repetitions(tmp_path, monkeypatch) -> None:
    calls = 0

    class CheckAdapter:
        def __init__(self, task_id):
            pass

        def next_turn(self, context, schemas):
            nonlocal calls
            calls += 1
            return DevModelTurn(tool_calls=[RequestedTool(
                name="run_check", action_id="cleanup-failure-check",
                arguments={"check_id": "existing-unit-tests"},
                turn_decision=PublicTurnDecision(mode="verify", basis="Observe baseline"),
            )])

    class UncertainCleanupSandbox:
        backend = "local"

        def run_check(self, workspace, check):
            return SandboxResult(
                command=check.command, exit_code=0, stdout="", stderr="", duration_ms=1,
                timed_out=False, truncated=False, original_output_bytes=0, cleanup_failed=True,
            )

    monkeypatch.setattr(runner, "MockDevAdapter", CheckAdapter)
    monkeypatch.setattr(runner, "LocalSandbox", UncertainCleanupSandbox)
    result = runner.run_dev(_request(tmp_path).model_copy(update={"repeat": 2}))
    assert result["completed_repetitions"] == calls == 1
    assert result["runs"][0]["terminal"] == "TASK_FAILED"
    rows = DevJournal(tmp_path, result["runs"][0]["run_id"]).events()
    check = next(r["payload"]["result"] for r in rows if r["event_type"] == "action_finished")
    assert check["output"]["passed"] is False
    assert "public_check_failure" not in check["output"]


def test_evaluator_cleanup_failure_stops_all_repetitions(tmp_path, monkeypatch) -> None:
    evaluations = 0

    def failed_cleanup(self, task_dir, patch_path, manifest, **kwargs):
        nonlocal evaluations
        evaluations += 1
        assert kwargs["deadline"] is not None
        raise SandboxCleanupError("synthetic owned container cleanup uncertainty")

    monkeypatch.setattr(runner.EvaluationEngine, "evaluate", failed_cleanup)
    result = runner.run_dev(_request(tmp_path).model_copy(update={"repeat": 2}))
    assert result["completed_repetitions"] == evaluations == 1
    assert result["runs"][0]["terminal"] == "EVALUATOR_ERROR"
    assert result["runs"][0]["call_counts"]["model"] == 4


@pytest.mark.parametrize("expires_after", ["request_construction", "input_count"])
def test_expired_provider_admission_does_not_record_undispatched_calls(
    tmp_path, monkeypatch, expires_after,
) -> None:
    clock = [0.0]
    counted = 0
    task_dir, package = runner._resolve_task_file(_request(tmp_path).task)
    package = package.model_copy(update={"environment": TaskEnvironment(
        evaluator_image="audit/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64,
    )})

    class FakeProvider:
        def __init__(self, *args, **kwargs):
            pass

        def request_payload(self, context, schemas, **kwargs):
            if expires_after == "request_construction":
                clock[0] = 1800
            return {"input": context, "tools": schemas}

        def count_input_tokens_v2(self, request, **kwargs):
            nonlocal counted
            counted += 1
            clock[0] = 1800
            return 20

        def execute_request(self, *args, **kwargs):
            raise AssertionError("expired admission must not dispatch a provider call")

    monkeypatch.setattr(runner, "monotonic", lambda: clock[0])
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", FakeProvider)
    monkeypatch.setattr(runner, "_live_task_is_admitted", lambda *args: None)
    monkeypatch.setattr(runner, "_live_source_preflight", lambda *args: None)
    monkeypatch.setattr(runner, "_live_sandbox_preflight", lambda *args: LocalSandbox())
    monkeypatch.setattr(runner, "load_exact_openai_api_key", lambda path: "unused")
    monkeypatch.setattr(runner, "_resolve_task_file", lambda task: (task_dir, package))
    request = _request(tmp_path).model_copy(update={
        "provider": "openai", "model": "gpt-5.4-mini-2026-03-17",
        "env_file": tmp_path / "credential.env", "max_cost_usd": Decimal("1.20"),
    })
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "LIMIT_REACHED"
    expected_counts = int(expires_after == "input_count")
    assert counted == expected_counts
    assert result["call_counts"] == {"model": 0, "input_count": expected_counts, "tool": 0}
    journal = DevJournal(tmp_path, result["run_id"])
    rows = journal.events()
    assert journal.unresolved_provider_call() is None
    assert not [r for r in rows if r["event_type"] == "provider_call_started"]
    assert len([r for r in rows if r["event_type"] == "input_count_started"]) == expected_counts
    assert len([r for r in rows if r["event_type"] == "input_count_finished"]) == expected_counts
