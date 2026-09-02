from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path

import pytest

import patchloop.dev.runner as runner
from patchloop.agent.model import ModelTurn
from patchloop.agent.model import RequestedTool as ProviderRequestedTool
from patchloop.dev.contracts import DevLimits, DevModelTurn, DevRunRequest, RequestedTool
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError, ResumeContractMismatch
from patchloop.repository import WorkspaceManager as RealWorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.task_loader import load_task_package


def test_latest_tool_result_is_not_evicted_by_working_set(gateway_factory, smoke_package) -> None:
    gateway, journal, _ = gateway_factory()
    for index in range(12):
        gateway.spans[f"span_ffffffffffff{index:04d}"] = {
            "span_id": f"span_ffffffffffff{index:04d}",
            "path": "mini_data_utils/csvlite.py",
            "start_line": 1,
            "end_line": 1,
            "content": f"old-{index}",
            "file_hash": "sha256:" + "0" * 64,
            "last_observed_seq": index + 1,
        }
    latest = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="latest-read",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 13,
            },
        )
    )
    context = json.loads(
        runner._build_context(  # noqa: SLF001 - direct context contract test
            package=smoke_package,
            gateway=gateway,
            journal=journal,
            correction=None,
            latest_tool_results=[latest],
            counters=runner._RunCounters(),  # noqa: SLF001
            elapsed_seconds=0,
            limits=DevRunRequest(
                provider="mock",
                task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
                model="mock-dev",
            ).limits,
        )
    )
    projected = context["latest_tool_results"][0]["output"]["spans"]
    assert projected[0]["span_id"] == latest.output["spans"][0]["span_id"]
    assert len(context["source_spans"]) == 8


def test_mock_end_to_end_isolated_evaluator_and_public_context(tmp_path, monkeypatch) -> None:
    contexts: list[str] = []

    class CapturingMock(MockDevAdapter):
        def next_turn(self, context, tools):
            contexts.append(context)
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "MockDevAdapter", CapturingMock)
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    result = runner.run_dev(request)
    run = result["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["evaluator"] == {"status": "PASS", "failure_class": None}
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert run["accepted_mutations"] == 1
    assert all("hidden-multiline-csv" not in context for context in contexts)
    assert all("reference_patch" not in context for context in contexts)
    context_keys = {
        "public_task",
        "current_diff",
        "latest_tool_results",
        "source_spans",
        "recent_checks",
        "last_successful_mutation",
        "recent_attempt_result_next_question",
        "workflow_gate",
        "remaining_budget",
    }
    assert all(set(json.loads(context)) == context_keys for context in contexts)
    projected = [
        json.loads(context)["current_diff"]
        for context in contexts
        if json.loads(context)["current_diff"]["patch"]
    ]
    assert projected
    assert all(item["truncated"] is False for item in projected)

    journal_path = tmp_path / "runs" / f"{run['run_id']}.jsonl"
    rows = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    assert all(row["schema_version"] == "dev-run-v1" for row in rows)
    assert all(row["official"] is False for row in rows)
    assert all(row["event_type"] != "state_changed" for row in rows)
    assert [json.loads(context)["workflow_gate"] for context in contexts] == [
        "needs_mutation",
        "needs_mutation",
        "needs_visible_checks",
        "ready_to_submit",
    ]
    assert len([row for row in rows if row["event_type"] == "turn_decision_recorded"]) == 4
    assert len([row for row in rows if row["event_type"] == "tool_batch_finished"]) == 4
    terminal = next(row for row in rows if row["event_type"] == "terminal")
    assert terminal["payload"]["milestones"]["submission"]["patch_hash"].startswith("sha256:")
    turns = [row for row in rows if row["event_type"] == "turn_started"]
    assert len(turns) == 4
    assert all(row["payload"]["context_hash"].startswith("sha256:") for row in turns)
    assert any(
        result["output"].get("spans")
        for context in contexts[1:]
        for result in json.loads(context)["latest_tool_results"]
    )
    evaluator = next(row for row in rows if row["event_type"] == "evaluator_finished")
    assert evaluator["payload"]["agent_context_reinjected"] is False
    envelope_path = tmp_path / "runs" / f"{run['run_id']}.envelope.json"
    assert json.loads(envelope_path.read_text(encoding="utf-8"))["schema_version"] == (
        "dev-run-envelope-v1"
    )
    workspace_roots = [path for path in (tmp_path / "workspaces").iterdir() if path.is_dir()]
    assert len(workspace_roots) == 2


def test_unexpected_tool_gateway_failure_writes_terminal(tmp_path, monkeypatch) -> None:
    class ExplodingGateway(runner.DevToolGateway):
        def execute_batch(self, calls):
            del calls
            raise RuntimeError("simulated gateway crash")

    monkeypatch.setattr(runner, "DevToolGateway", ExplodingGateway)
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    result = runner.run_dev(request)
    run = result["runs"][0]
    assert run["terminal"] == "TASK_FAILED"

    journal_path = tmp_path / "runs" / f"{run['run_id']}.jsonl"
    rows = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    terminal = [row for row in rows if row["event_type"] == "terminal"]
    assert len(terminal) == 1
    assert terminal[0]["payload"]["message"] == "tool gateway failed: RuntimeError"


def test_invalid_tool_batch_gets_one_correction_then_stops(tmp_path, monkeypatch) -> None:
    class InvalidBatchMock:
        calls = 0

        def __init__(self, task_id) -> None:
            del task_id

        def next_turn(self, context, tools):
            del context, tools
            self.calls += 1
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="read_file",
                        action_id=f"bad-read-{self.calls}",
                        arguments={"path": "mini_data_utils/csvlite.py"},
                    ),
                    RequestedTool(
                        name="run_check",
                        action_id=f"bad-check-{self.calls}",
                        arguments={"check_id": "existing-unit-tests"},
                    ),
                ]
            )

    monkeypatch.setattr(runner, "MockDevAdapter", InvalidBatchMock)
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    result = runner.run_dev(request)
    run = result["runs"][0]
    assert run["terminal"] == "PROTOCOL_VIOLATION"
    assert run["call_counts"] == {"model": 2, "input_count": 0, "tool": 0}

    journal_path = tmp_path / "runs" / f"{run['run_id']}.jsonl"
    rows = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    assert len([row for row in rows if row["event_type"] == "protocol_correction"]) == 1


def test_live_rejects_non_dev_train_before_credential_or_provider(tmp_path) -> None:
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=not-used\n", encoding="utf-8")
    request = DevRunRequest(
        provider="openai",
        task=(
            repository_root()
            / "tasks"
            / "dev-validation"
            / "babel-strict-grouped-decimal-trailing-zeroes-v2"
            / "public.yaml"
        ),
        model="gpt-5.4-mini-2026-03-17",
        env_file=env_file,
        max_cost_usd=Decimal("0.01"),
        state_root=tmp_path / "state",
    )
    with pytest.raises(ContractError, match="dev-train"):
        runner.run_dev(request)


def test_live_missing_local_image_stops_before_provider(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=test-only-sentinel\n", encoding="utf-8")
    monkeypatch.setattr(runner.DockerSandbox, "available", staticmethod(lambda: True))
    monkeypatch.setattr(runner.DockerSandbox, "image_identity", lambda self: None)
    request = DevRunRequest(
        provider="openai",
        task=(
            repository_root()
            / "tasks"
            / "dev-train"
            / "anyio-interrupt-runner-cleanup"
            / "public.yaml"
        ),
        model="gpt-5.4-mini-2026-03-17",
        env_file=env_file,
        max_cost_usd=Decimal("0.01"),
        state_root=tmp_path / "state",
    )
    result = runner.run_dev(request)
    assert result["runs"][0]["terminal"] == "PREFLIGHT_FAILED"
    assert result["runs"][0]["call_counts"]["model"] == 0


class _SnapshotWorkspaceManager:
    smoke = load_task_package(repository_root() / "tasks" / "smoke" / "csv-quoted-newline")
    diff_summary = staticmethod(RealWorkspaceManager.diff_summary)

    def __init__(self, fixture_root, workspace_root) -> None:
        self.delegate = RealWorkspaceManager(fixture_root, workspace_root)

    def create(self, run_id, repository_url, expected_revision=None):
        del repository_url, expected_revision
        return self.delegate.create(
            run_id,
            self.smoke.public.repository.url,
            self.smoke.public.repository.base_commit,
        )

    def validate_managed_workspace(self, workspace):
        return self.delegate.validate_managed_workspace(workspace)


def _live_request(tmp_path: Path, *, repeat: int = 3, cap: str = "0.01") -> DevRunRequest:
    tmp_path.mkdir(parents=True, exist_ok=True)
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=test-only-sentinel\n", encoding="utf-8")
    return DevRunRequest(
        provider="openai",
        task=(
            repository_root()
            / "tasks"
            / "dev-train"
            / "anyio-interrupt-runner-cleanup"
            / "public.yaml"
        ),
        model="gpt-5.4-mini-2026-03-17",
        env_file=env_file,
        max_cost_usd=Decimal(cap),
        repeat=repeat,
        state_root=tmp_path / "state",
    )


def _patch_live_boundaries(monkeypatch) -> None:
    monkeypatch.setattr(runner, "_live_sandbox_preflight", lambda package: LocalSandbox())
    monkeypatch.setattr(runner, "WorkspaceManager", _SnapshotWorkspaceManager)


class _SimulatedCrash(BaseException):
    pass


def _enveloped_run_id(state_root: Path) -> str:
    envelopes = list((state_root / "runs").glob("run_dev_*.envelope.json"))
    assert len(envelopes) == 1
    return envelopes[0].name.removesuffix(".envelope.json")


def _crash_journal_once(
    monkeypatch,
    *,
    event_type: str,
    when: str,
    predicate=lambda payload: True,
) -> None:
    original = DevJournal.append
    fired = False

    def append(self, current_type, payload=None):
        nonlocal fired
        matches = not fired and current_type == event_type and predicate(payload or {})
        if matches and when == "before":
            fired = True
            raise _SimulatedCrash(current_type)
        result = original(self, current_type, payload)
        if matches and when == "after":
            fired = True
            raise _SimulatedCrash(current_type)
        return result

    monkeypatch.setattr(DevJournal, "append", append)


@pytest.mark.parametrize(
    "crash_case",
    [
        "decision_recorded",
        "mutation_before_result",
        "check_result_recorded",
        "batch_before_finished",
    ],
)
def test_mock_resume_replays_durable_work_without_duplicate_mutation(
    tmp_path,
    monkeypatch,
    crash_case,
) -> None:
    if crash_case == "decision_recorded":
        _crash_journal_once(
            monkeypatch,
            event_type="turn_decision_recorded",
            when="after",
        )
    elif crash_case == "mutation_before_result":
        _crash_journal_once(
            monkeypatch,
            event_type="action_finished",
            when="before",
            predicate=lambda payload: payload.get("result", {}).get("tool") == "apply_patch",
        )
    elif crash_case == "check_result_recorded":
        _crash_journal_once(
            monkeypatch,
            event_type="action_finished",
            when="after",
            predicate=lambda payload: payload.get("result", {}).get("tool") == "run_check",
        )
    else:
        _crash_journal_once(
            monkeypatch,
            event_type="tool_batch_finished",
            when="before",
            predicate=lambda payload: "mock-visible-check" in payload.get("action_ids", []),
        )

    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)

    run_id = _enveloped_run_id(tmp_path)
    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    run = resumed["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert run["accepted_mutations"] == 1

    journal = DevJournal(tmp_path, run_id)
    action_results = [
        row["payload"]["result"]
        for row in journal.events()
        if row["event_type"] == "action_finished"
    ]
    mutation_results = [row for row in action_results if row["tool"] == "apply_patch"]
    assert len(mutation_results) == 1
    assert len([row for row in journal.events() if row["event_type"] == "run_resumed"]) == 1


def test_resume_contract_and_workspace_mismatch_do_not_change_journal(
    tmp_path,
    monkeypatch,
) -> None:
    _crash_journal_once(
        monkeypatch,
        event_type="turn_decision_recorded",
        when="after",
    )
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(tmp_path)
    journal = DevJournal(tmp_path, run_id)
    before = journal.path.read_bytes()

    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(
            request.model_copy(
                update={"resume_run_id": run_id, "model": "different-mock-model"}
            )
        )
    assert journal.path.read_bytes() == before

    workspace = tmp_path / "workspaces" / run_id / "repo"
    target = workspace / "mini_data_utils" / "csvlite.py"
    target.write_text(target.read_text(encoding="utf-8") + "\n# external drift\n", encoding="utf-8")
    with pytest.raises(ResumeContractMismatch, match="workspace diff"):
        runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    assert journal.path.read_bytes() == before


def test_runtime_mismatch_and_pre_envelope_run_fail_before_journal_change(
    tmp_path,
    monkeypatch,
) -> None:
    _crash_journal_once(
        monkeypatch,
        event_type="turn_decision_recorded",
        when="after",
    )
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(tmp_path)
    journal = DevJournal(tmp_path, run_id)
    before = journal.path.read_bytes()
    monkeypatch.setattr(runner, "_runtime_hash", lambda: "sha256:" + "f" * 64)
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    assert journal.path.read_bytes() == before

    old = DevJournal(tmp_path, "run_dev_oldformat0001")
    old.append("run_started", {"runtime": "dev-head"})
    old_before = old.path.read_bytes()
    with pytest.raises(RecoveryError, match="predates resumable envelopes"):
        runner.run_dev(
            request.model_copy(update={"resume_run_id": "run_dev_oldformat0001"})
        )
    assert old.path.read_bytes() == old_before


def test_terminal_resume_is_read_only_and_does_not_reenter_model(tmp_path, monkeypatch) -> None:
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    first = runner.run_dev(request)
    run_id = first["runs"][0]["run_id"]
    journal = DevJournal(tmp_path, run_id)
    before = journal.path.read_bytes()

    class ForbiddenAdapter:
        def __init__(self, task_id):
            del task_id
            raise AssertionError("terminal resume must not initialize the model")

    monkeypatch.setattr(runner, "MockDevAdapter", ForbiddenAdapter)
    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    assert resumed["runs"][0] == first["runs"][0]
    assert journal.path.read_bytes() == before


def test_provider_response_resume_does_not_repeat_provider_call(tmp_path, monkeypatch) -> None:
    calls = {"execute": 0}

    class OneReadAdapter:
        def __init__(self, config, *, api_key) -> None:
            del config, api_key

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 100

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request
            assert timeout_seconds > 0
            calls["execute"] += 1
            return ModelTurn(
                tool_calls=[
                    ProviderRequestedTool(
                        name="read_file",
                        action_id="provider-read-once",
                        arguments={
                            "path": "mini_data_utils/csvlite.py",
                            "start_line": 1,
                            "end_line": 20,
                        },
                    )
                ],
                requested_input_tokens=requested_input_tokens,
                input_tokens=requested_input_tokens,
                output_tokens=1,
                response_id="response-once",
                response_model="mocked-provider",
                response_status="completed",
            )

    _patch_live_boundaries(monkeypatch)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", OneReadAdapter)
    _crash_journal_once(
        monkeypatch,
        event_type="provider_call_finished",
        when="after",
    )
    request = _live_request(tmp_path, repeat=1, cap="0.10").model_copy(
        update={"limits": DevLimits(max_model_calls=1)}
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)

    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    run = resumed["runs"][0]
    assert run["terminal"] == "LIMIT_REACHED"
    assert run["call_counts"] == {"model": 1, "input_count": 1, "tool": 1}
    assert run["cost_nanos"] > 0
    assert calls["execute"] == 1


def test_unfinished_provider_dispatch_becomes_one_unknown_terminal(tmp_path, monkeypatch) -> None:
    calls = {"adapter": 0, "preflight": 0, "execute": 0}

    class NeverExecutedAdapter:
        def __init__(self, config, *, api_key) -> None:
            del config, api_key
            calls["adapter"] += 1

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 100

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request, requested_input_tokens, timeout_seconds
            calls["execute"] += 1
            raise AssertionError("crash occurs before dispatch")

    def preflight(package):
        del package
        calls["preflight"] += 1
        return LocalSandbox()

    monkeypatch.setattr(runner, "_live_sandbox_preflight", preflight)
    monkeypatch.setattr(runner, "WorkspaceManager", _SnapshotWorkspaceManager)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", NeverExecutedAdapter)
    _crash_journal_once(
        monkeypatch,
        event_type="provider_call_started",
        when="after",
    )
    request = _live_request(tmp_path, repeat=1, cap="0.10").model_copy(
        update={"limits": DevLimits(max_model_calls=1)}
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)

    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    assert resumed["runs"][0]["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert resumed["runs"][0]["call_counts"] == {
        "model": 1,
        "input_count": 1,
        "tool": 0,
    }
    assert calls == {"adapter": 1, "preflight": 1, "execute": 0}
    journal = DevJournal(request.state_root, run_id)
    assert len([row for row in journal.events() if row["event_type"] == "terminal"]) == 1


def test_provider_timeout_stops_remaining_repetitions(tmp_path, monkeypatch) -> None:
    calls = {"create": 0}
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    class TimeoutAdapter:
        def __init__(self, config, *, api_key) -> None:
            del config
            assert api_key == "test-only-sentinel"
            assert "OPENAI_API_KEY" not in os.environ

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 100

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request, requested_input_tokens
            assert timeout_seconds > 0
            calls["create"] += 1
            raise TimeoutError("ambiguous provider timeout")

    _patch_live_boundaries(monkeypatch)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", TimeoutAdapter)
    result = runner.run_dev(_live_request(tmp_path))
    assert result["completed_repetitions"] == 1
    assert result["runs"][0]["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert calls["create"] == 1


def test_count_timeout_and_cost_cap_stop_without_generation(tmp_path, monkeypatch) -> None:
    class CountTimeoutAdapter:
        execute_calls = 0

        def __init__(self, config, *, api_key) -> None:
            del config, api_key

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            raise TimeoutError("count timeout")

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request, requested_input_tokens, timeout_seconds
            self.execute_calls += 1

    _patch_live_boundaries(monkeypatch)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", CountTimeoutAdapter)
    timed_out = runner.run_dev(_live_request(tmp_path / "count"))
    assert timed_out["completed_repetitions"] == 1
    assert timed_out["runs"][0]["terminal"] == "COUNT_TIMEOUT_OR_UNKNOWN"

    class TooExpensiveAdapter(CountTimeoutAdapter):
        create_calls = 0

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 1_000_000

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request, requested_input_tokens, timeout_seconds
            self.create_calls += 1
            raise AssertionError("generation must not be dispatched")

    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", TooExpensiveAdapter)
    capped = runner.run_dev(_live_request(tmp_path / "cap", cap="0.0001"))
    assert capped["runs"][0]["terminal"] == "COST_CAP_REACHED"
