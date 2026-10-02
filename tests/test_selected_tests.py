from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
from dataclasses import replace

import pytest
import yaml
from pydantic import ValidationError
from test_dev_tools import mutation_call, read_calls

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import PublicTask, PublicTestSuite
from patchloop.dev import runner, segments, working_plan
from patchloop.dev.contracts import (
    DevLimits,
    DevModelTurn,
    DevRunRequest,
    PublicTurnDecision,
    RequestedTool,
)
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.state import DevJournal
from patchloop.dev.test_selection import recent_tests
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas, validate_tool_batch
from patchloop.dev.verification_observations import verification_observation
from patchloop.errors import ActionConflict, ContractError
from patchloop.runtime import repository_root
from patchloop.sandbox.runner import LocalSandbox, SandboxResult
from patchloop.task_loader import load_public_task

TARGET = "tests/test_csvlite.py::ParseRowsTests::test_parses_rows"


def suite(**updates):
    return PublicTestSuite.model_validate({
        "id": "public-pytest", "test_roots": ["tests"],
        "environment": {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", **(
            {"SYSTEMROOT": os.environ["SYSTEMROOT"]} if os.name == "nt" else {}
        )},
        "command": ["python", "-m", "pytest", "-q"], **updates,
    })


def enable(gateway):
    gateway.public_task = gateway.public_task.model_copy(deep=True)
    gateway.public_task.test_suites = [suite()]
    return gateway


def call(action_id="selected-tests", targets=None, **arguments):
    return RequestedTool(
        name="run_tests", action_id=action_id,
        arguments={"suite_id": "public-pytest", "targets": targets or [TARGET], **arguments},
        turn_decision=PublicTurnDecision(mode="verify", basis="Check a public caller."),
    )


class RecordingSandbox:
    supports_execution_deadline = True

    def __init__(self, **updates):
        self.calls = []
        self.result = SandboxResult(
            command=[], exit_code=0, stdout="1 passed", stderr="", duration_ms=1,
            timed_out=False, truncated=False, original_output_bytes=8,
        )
        self.result = replace(self.result, **updates)

    def run_check(self, workspace, check, **kwargs):
        self.calls.append((workspace, check, kwargs))
        return replace(self.result, command=check.command)


def test_suite_is_explicit_and_legacy_public_serialization_is_unchanged(smoke_package):
    original = smoke_package.public.model_dump(mode="json")
    assert "test_suites" not in original
    configured = PublicTask.model_validate({**original, "test_suites": [suite().model_dump()]})
    assert configured.model_dump(exclude={"test_suites"}) == original
    with pytest.raises(ValidationError, match="unique"):
        PublicTask.model_validate({**original, "test_suites": [suite(), suite()]})
    with pytest.raises(ValidationError, match="exit zero"):
        suite(expected_exit_codes=[0, 5])
    for root in (".patchloop-hidden", ".git", "tests/../hidden", "C:/tests"):
        with pytest.raises((ValidationError, ContractError)):
            suite(test_roots=[root])


def test_registered_suite_reuses_existing_sqlfluff_environment_and_public_runner():
    from patchloop.runtime import repository_root

    public = load_public_task(repository_root() / "tasks/dev-train" /
                              "swebench-lite-dev-sqlfluff-sqlfluff-1625/public.yaml")
    required = public.visible_checks[0]
    optional = public.test_suites[0]
    assert optional.command == required.command[:4] + required.command[5:]
    assert optional.environment == required.environment
    assert optional.timeout_seconds == required.timeout_seconds
    assert optional.test_roots == ["test"]


def test_schema_and_batch_admission_only_offer_registered_selections():
    assert "run_tests" not in {s["name"] for s in dev_tool_schemas(finish_enabled=False)}
    selected, = dev_tool_schemas(
        finish_enabled=False, test_suite_ids=["public-pytest"], allowed_tools={"run_tests"},
    )
    properties = selected["parameters"]["properties"]
    assert properties["suite_id"]["enum"] == ["public-pytest"]
    assert properties["targets"]["maxItems"] == 8
    assert properties["targets"]["items"]["maxLength"] == 500
    assert validate_tool_batch([call()], allowed_tools={"run_tests"}) == "single_action"
    with pytest.raises(ContractError):
        validate_tool_batch([call(), read_calls()[0]])
    with pytest.raises(ContractError):
        validate_tool_batch([call()], allowed_tools={"run_check"})


@pytest.mark.parametrize("arguments", [
    {"suite_id": "unknown"}, {"command": ["whoami"]}, {"targets": []},
    {"targets": [TARGET] * 9}, {"targets": [TARGET, TARGET]},
    {"targets": ["-k"]}, {"targets": ["../test.py"]},
    {"targets": ["tests/../../test.py"]}, {"targets": ["/tmp/test.py"]},
    {"targets": ["C:/test.py"]}, {"targets": ["tests"]},
    {"targets": ["mini_data_utils/csvlite.py"]},
    {"targets": ["tests_extra/test_csvlite.py"]},
    {"targets": [".patchloop-hidden/test_private.py"]},
    {"targets": ["tests/test_csvlite.py\n--collect-only"]},
    {"targets": ["tests/test_csvlite.py::"]},
    {"targets": ["tests/untracked.py"]}, {"targets": ["tests/" + "x" * 500]},
])
def test_invalid_selection_never_dispatches(gateway_factory, arguments):
    backend = RecordingSandbox()
    gateway, _, workspace = gateway_factory(sandbox=backend)
    enable(gateway)
    (workspace / "tests/untracked.py").write_text("def test_untracked(): pass\n")
    request = call().model_copy(update={"arguments": {**call().arguments, **arguments}})
    result = gateway.execute(request)
    assert result.status == "failed"
    assert not backend.calls


def test_symlink_target_is_rejected_before_resolution(gateway_factory):
    backend = RecordingSandbox()
    gateway, _, workspace = gateway_factory(sandbox=backend)
    enable(gateway)
    link = workspace / "tests/test_link.py"
    try:
        link.symlink_to(workspace / "tests/test_csvlite.py")
    except OSError:
        pytest.skip("symlink creation unavailable")
    subprocess.run(["git", "add", "tests/test_link.py"], cwd=workspace, check=True)
    result = gateway.execute(call(targets=["tests/test_link.py"]))
    assert result.status == "failed" and "symlink" in result.message
    assert not backend.calls


@pytest.mark.parametrize("updates,status", [
    ({}, "PASS"), ({"exit_code": 1}, "FAIL"), ({"exit_code": 2}, "ERROR"),
    ({"exit_code": 5}, "ERROR"), ({"timed_out": True}, "ERROR"),
    ({"cleanup_failed": True}, "ERROR"), ({"deadline_exhausted": True}, "ERROR"),
])
def test_execution_receipt_distinguishes_failure_from_incomplete_run(
    gateway_factory, updates, status,
):
    backend = RecordingSandbox(**updates)
    gateway, _, _ = gateway_factory(sandbox=backend)
    enable(gateway)
    result = gateway.execute(call())
    assert result.status == "succeeded"
    assert result.output["test_status"] == status
    assert result.output["passed"] == (status == "PASS")
    assert result.output["counts_toward_completion"] is False
    assert backend.calls[0][1].command == ["python", "-m", "pytest", "-q", "--", TARGET]
    assert backend.calls[0][2]["execution_identity"]["action_id"] == call().action_id
    assert gateway.checks_by_diff == {}
    assert gateway.remaining_visible_check_ids() == ["existing-unit-tests"]
    observation = verification_observation(result.model_dump(mode="json"))
    assert (observation is None) == (status == "PASS")
    if observation:
        assert observation["origin"] == "selected_public_tests"
    terminal, _ = runner._batch_execution_abort([result])
    assert (terminal is not None) == bool(
        updates.get("cleanup_failed") or updates.get("deadline_exhausted"))


def test_real_pytest_file_node_and_missing_node(gateway_factory):
    gateway, _, _ = gateway_factory(sandbox=LocalSandbox())
    enable(gateway)
    for action, target, status, expected in (
        ("file", "tests/test_csvlite.py", "PASS", "2 passed"),
        ("node", TARGET, "PASS", "1 passed"),
        ("missing", "tests/test_csvlite.py::test_absent", "ERROR", "not found"),
    ):
        result = gateway.execute(call(action, [target]))
        assert result.status == "succeeded", result.message
        assert result.output["test_status"] == status
        assert expected in result.output["stdout"] + result.output["stderr"]
    assert not gateway.visible_checks_pass()


def test_result_recovery_identity_and_historical_currency(gateway_factory):
    backend = RecordingSandbox(exit_code=1, stdout="FAILED public caller")
    gateway, journal, workspace = gateway_factory(sandbox=backend)
    enable(gateway)
    result = gateway.execute(call())
    original = journal.path.read_bytes()
    assert gateway.execute(call()).replayed
    assert journal.path.read_bytes() == original
    restored = DevToolGateway(
        workspace=workspace, public_task=gateway.public_task, sandbox=backend,
        journal=journal, limits=DevLimits(),
    )
    assert restored.execute(call()).replayed
    assert len(backend.calls) == 1
    with pytest.raises(ActionConflict):
        restored.execute(call(targets=["tests/test_csvlite.py"]))
    current = recent_tests(journal.events(), gateway.current_diff_hash)
    assert current[0]["evidence_currency"] == "current"
    for request in read_calls():
        gateway.execute(request)
    gateway.execute(mutation_call(gateway))
    rows = recent_tests(journal.events(), gateway.current_diff_hash)
    assert rows[0]["evidence_currency"] == "historical"
    assert rows[0]["diff_hash"] == result.workspace_diff_hash
    view = compact_model_state({"recent_tests": rows}, history=[])
    assert view["recent_tests"] == rows
    assert not gateway.checks_by_diff
    assert "run_tests" in segments.MAJOR_TOOLS
    plan = working_plan.project(journal.events(), diff_hash=gateway.current_diff_hash, gate="test")
    assert "test_result" in plan["review_request"]["reasons"]


@pytest.mark.parametrize("resource", ["model_calls", "tool_actions"])
def test_optional_tests_preserve_completion_budget(gateway_factory, resource):
    gateway, _, _ = gateway_factory(sandbox=RecordingSandbox())
    assert "run_tests" not in runner._tool_policy(
        gateway, runner._RunCounters(), DevLimits()).allowed_tools
    enable(gateway)
    limits = DevLimits()
    protected = runner._tool_policy(
        gateway, runner._RunCounters(), limits).completion_budget_calls
    cap = limits.max_model_calls if resource == "model_calls" else limits.max_tool_actions
    for remaining, expected in ((protected + 1, True), (protected, False), (1, False)):
        counters = runner._RunCounters(**{resource: cap - remaining})
        policy = runner._tool_policy(gateway, counters, limits)
        assert ("run_tests" in policy.allowed_tools) is expected


def test_selected_pass_cannot_replace_required_check_and_failure_does_not_erase_it(gateway_factory):
    backend = RecordingSandbox()
    gateway, _, _ = gateway_factory(sandbox=backend)
    enable(gateway)
    for request in read_calls():
        gateway.execute(request)
    gateway.execute(mutation_call(gateway))
    gateway.execute(call())
    assert not gateway.ready_to_submit()
    gateway.execute(RequestedTool(
        name="run_check", action_id="required", arguments={"check_id": "existing-unit-tests"},
    ))
    assert gateway.ready_to_submit()
    required = copy.deepcopy(gateway.checks_by_diff)
    backend.result = replace(backend.result, exit_code=1)
    failed = gateway.execute(call("selected-failure"))
    assert failed.output["test_status"] == "FAIL"
    assert gateway.checks_by_diff == required
    assert gateway.ready_to_submit()
    counters = runner._RunCounters()
    runner._update_inspection_counters(counters, [failed], gateway)
    assert not counters.failed_check_pending


def test_public_context_exposes_suite_and_current_results(gateway_factory, smoke_package):
    gateway, _, _ = gateway_factory(sandbox=RecordingSandbox())
    enable(gateway)
    result = gateway.execute(call())
    package = smoke_package.model_copy(update={"public": gateway.public_task})
    payload = json.loads(runner._build_context(
        package=package, gateway=gateway, journal=gateway.journal, correction=None,
        latest_tool_results=[result], counters=runner._RunCounters(),
        elapsed_seconds=0, limits=DevLimits(),
    ))
    assert payload["public_task"]["test_suites"][0]["test_roots"] == ["tests"]
    assert payload["recent_tests"][0]["targets"] == [TARGET]
    assert payload["recent_tests"][0]["counts_toward_completion"] is False


def test_pending_selection_reuses_identity_and_rejects_workspace_drift(gateway_factory):
    class Interrupted(RecordingSandbox):
        def run_check(self, workspace, check, **kwargs):
            result = super().run_check(workspace, check, **kwargs)
            if len(self.calls) == 1:
                raise KeyboardInterrupt
            return result

    for change in (False, True):
        backend = Interrupted()
        gateway, journal, workspace = gateway_factory(sandbox=backend)
        enable(gateway)
        with pytest.raises(KeyboardInterrupt):
            gateway.execute(call())
        if change:
            source = workspace / "mini_data_utils/csvlite.py"
            source.write_text(source.read_text() + "\n# changed after admission\n")
        result = gateway.execute(call())
        if change:
            assert result.status == "failed" and result.error_code == "RECOVERY_ERROR"
            assert len(backend.calls) == 1
        else:
            assert result.status == "succeeded"
            identities = [item[2]["execution_identity"] for item in backend.calls]
            assert identities[0] == identities[1]
            assert sum(e["event_type"] == "action_started" for e in journal.events()) == 1


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_selected_test_receipt_reaches_model_and_mock_evaluation(tmp_path, monkeypatch, policy):
    task = tmp_path / "task"
    shutil.copytree(repository_root() / "tasks/smoke/csv-quoted-newline", task)
    public = yaml.safe_load((task / "public.yaml").read_text())
    public["test_suites"] = [suite().model_dump()]
    (task / "public.yaml").write_text(yaml.safe_dump(public), encoding="utf-8")
    selections = []

    class TestsThenMock(MockDevAdapter):
        def next_turn(self, context, tools):
            if not selections:
                tool = next(t for t in tools if t["name"] == "run_tests")
                assert tool["parameters"]["properties"]["suite_id"]["enum"] == ["public-pytest"]
                selections.append(TARGET)
                return DevModelTurn(tool_calls=[call()])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "MockDevAdapter", TestsThenMock)
    request = DevRunRequest(
        provider="mock", model="mock-dev", task=task / "public.yaml",
        context_policy=policy, state_root=tmp_path / "state",
    )
    run = runner.run_dev(request)["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["evaluator"]["safety_state"] == "NOT_RUN"
    journal = DevJournal(request.state_root, run["run_id"])
    store = ArtifactStore(request.state_root / "artifacts")
    delivered, currencies = [], set()
    for event in journal.events():
        if event["event_type"] != "turn_started":
            continue
        items = runner._load_active_model_input(event["payload"], store, context_policy=policy)
        state = reconstruct_state(items, context_policy=policy)
        for row in state.get("recent_tests", []):
            assert row["targets"] == [TARGET] and row["counts_toward_completion"] is False
            currencies.add(row["evidence_currency"])
        delivered.extend(json.loads(item["output"]) for item in items
                         if item.get("type") == "function_call_output"
                         and item["call_id"] == call().action_id)
    assert delivered and currencies == {"current", "historical"}
    assert all(r["output"]["test_status"] == "PASS" for r in delivered)
    before = journal.path.read_bytes()
    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run["run_id"]}))
    assert resumed["runs"][0] == run
    assert journal.path.read_bytes() == before and len(selections) == 1
