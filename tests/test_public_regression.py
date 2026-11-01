"""Public checks run through a real gateway and a nonexecuting synthetic sandbox."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

from diagnostics import public_regression as regression
from patchloop.contracts import Artifact, RegisteredCheck
from patchloop.deadline import ExecutionDeadline
from patchloop.errors import ContractError
from patchloop.sandbox import SandboxResult


class SyntheticSandbox:
    official = False
    backend = "synthetic"
    supports_execution_deadline = True

    def __init__(self):
        self.calls = []
        self.changes = {}

    def run_check(self, workspace, check, *, deadline, execution_identity):
        self.calls.append((check.id, deadline, execution_identity))
        stdout = ("observed diagnostic line\n" * 390
                  + "FAILED tests/test_paths.py::test_raw - AssertionError: raw path\n")
        values = dict(command=check.command, exit_code=1 if check.id == "check-one" else 0,
            stdout=stdout if check.id == "check-one" else "all passed\n",
            stderr="public warning line\n" * 150, duration_ms=1, timed_out=False,
            truncated=False, original_output_bytes=len(stdout),
            execution_policy={"cleanup_status": "confirmed"},
            public_execution={"operator_metadata": "NOT_PUBLIC_FEEDBACK"})
        values.update(self.changes)
        return SandboxResult(**values)


@pytest.fixture
def checker(gateway_factory, tmp_path):
    sandbox = SyntheticSandbox()
    model, _, workspace = gateway_factory(sandbox=sandbox)
    public = model.public_task.model_copy(deep=True, update={"visible_checks": [
        RegisteredCheck(id="check-one", command=["unused-one"], timeout_seconds=10,
                        infrastructure_exit_codes=[2]),
        RegisteredCheck(id="check-two", command=["unused-two"], timeout_seconds=20),
    ]})
    model.public_task = public
    model.deadline = ExecutionDeadline.from_remaining(600)
    loaded = SimpleNamespace(public=public)
    controller = regression.PublicRegressionRecheck(loaded, model, tmp_path / "regression")
    return SimpleNamespace(controller=controller, model=model, loaded=loaded,
                           workspace=workspace, sandbox=sandbox)


def test_all_public_checks_report_failure_with_bounded_tails_and_full_receipts(checker):
    check, model, sandbox = checker.controller, checker.model, checker.sandbox
    assert check.current_receipts() is None and check.needed_seconds() == 40
    feedback = check.check()
    assert feedback["schema"] == "public-regression-feedback-v1"
    assert feedback["status"] == "failed" and feedback["task_acceptance"] == "NOT_ASSESSED"
    assert feedback["candidate_diff_hash"] == model.current_diff_hash
    assert [row[0] for row in sandbox.calls] == ["check-one", "check-two"]
    assert all(row[1] is model.deadline for row in sandbox.calls)
    assert not any(event["event_type"] == "action_started" for event in model.journal.events())
    failed, passed = feedback["checks"]
    assert failed["passed"] is False and failed["exit_code"] == 1 and passed["passed"] is True
    assert failed["exception_type"] == "AssertionError"
    assert "test_raw" in failed["failure_summary"]["lines"][0]
    assert failed["public_check_failure"]["failure_summary"] == failed["failure_summary"]
    assert "public_location" in failed["public_check_failure"]
    assert len(failed["stdout_tail"]) <= 8000 and len(failed["stderr_tail"]) <= 2000
    assert failed["stdout_omitted"] and failed["stderr_omitted"]
    assert failed["output_truncated"] is False
    assert "NOT_PUBLIC_FEEDBACK" not in json.dumps(feedback)
    receipts = check.current_receipts()
    assert len(receipts) == 2 and check.host_actions == 2
    for raw, reference in zip(receipts, feedback["receipts"], strict=True):
        assert json.loads(check.store.read_bytes(Artifact.model_validate(reference))) == raw
    assert len(receipts[0]["output"]["stdout"]) > len(failed["stdout_tail"])
    assert check.needed_seconds() == 0 and check.needed_seconds(for_new_diff=True) == 40


def test_settled_same_diff_and_controller_recovery_never_rerun(checker):
    check = checker.controller
    first = check.check()
    raw = check.current_receipts()
    recovered = regression.PublicRegressionRecheck(checker.loaded, checker.model, check.root)
    again = recovered.check()
    assert again["receipts_reused"] is True and recovered.current_receipts() == raw
    assert [row["content_hash"] for row in first["receipts"]] == [
        row["content_hash"] for row in again["receipts"]]
    assert recovered.host_actions == 2 and len(checker.sandbox.calls) == 2
    assert all(row["replayed"] is False for row in recovered.current_receipts())


@pytest.mark.parametrize("exit_code", [0, 1])
@pytest.mark.parametrize("gateway_clips", [False, True])
def test_settled_truncated_output_preserves_verdict_and_reuses_receipt(
    checker, exit_code, gateway_clips,
):
    check = checker.controller
    diagnostic = "FAILED tests/test_paths.py::test_raw - AssertionError: raw path\n"
    stdout = "verbose diagnostic line\n" * 800 + diagnostic if gateway_clips else diagnostic
    stderr = "public warning line\n" * 800 if gateway_clips else "warning\n"
    checker.sandbox.changes = {"exit_code": exit_code, "stdout": stdout, "stderr": stderr,
                               "truncated": not gateway_clips}
    feedback = check.check()
    assert feedback["status"] == ("passed" if exit_code == 0 else "failed")
    raw = check.current_receipts()
    for item, receipt in zip(feedback["checks"], raw, strict=True):
        assert item["passed"] is (exit_code == 0) and item["exit_code"] == exit_code
        assert item["output_truncated"] is True and receipt["output"]["truncated"] is True
        assert item["stdout_omitted"] is gateway_clips
        assert item["stderr_omitted"] is gateway_clips
        assert (len(receipt["output"]["stdout"]) < len(stdout)) is gateway_clips
        assert (len(receipt["output"]["stderr"]) < len(stderr)) is gateway_clips
        if exit_code == 1:
            assert item["exception_type"] == "AssertionError"
            assert item["public_check_failure"] is not None
    recovered = regression.PublicRegressionRecheck(checker.loaded, checker.model, check.root)
    again = recovered.check()
    assert again["receipts_reused"] and again["checks"] == feedback["checks"]
    assert recovered.current_receipts() == raw and recovered.needed_seconds() == 0
    assert recovered.host_actions == len(checker.sandbox.calls) == 2


def test_two_unique_diffs_exhaust_quota_but_old_completed_diff_remains_reusable(checker):
    check = checker.controller
    path = checker.workspace / "mini_data_utils/csvlite.py"
    original = path.read_bytes()
    first_diff = checker.model.current_diff_hash
    check.check()
    path.write_bytes(original + b"\n# second candidate\n")
    assert check.current_receipts() is None and check.needed_seconds() == 40
    checker.sandbox.changes = {"exit_code": 0, "stdout": "passed\n"}
    assert check.check()["status"] == "passed" and check.host_actions == 4
    path.write_bytes(original + b"\n# third candidate\n")
    with pytest.raises(ContractError, match="pass allowance exhausted"):
        check.check()
    assert len(checker.sandbox.calls) == 4
    path.write_bytes(original)
    assert checker.model.current_diff_hash == first_diff
    assert check.check()["receipts_reused"] and check.host_actions == 4


@pytest.mark.parametrize("changes", [
    {"timed_out": True}, {"cleanup_failed": True},
    {"deadline_exhausted": True}, {"exit_code": None}, {"exit_code": 2},
    {"execution_policy": {"cleanup_status": "unconfirmed"}},
])
def test_incomplete_or_uncertain_execution_stops_all_checks_and_cannot_be_retried(checker, changes):
    check = checker.controller
    checker.sandbox.changes = changes
    with pytest.raises(ContractError):
        check.check()
    assert check.host_actions == len(checker.sandbox.calls) == 1
    recovered = regression.PublicRegressionRecheck(checker.loaded, checker.model, check.root)
    with pytest.raises(ContractError):
        recovered.check()
    assert len(checker.sandbox.calls) == 1
    path = checker.workspace / "mini_data_utils/csvlite.py"
    path.write_bytes(path.read_bytes() + b"\n# uncertainty cannot be bypassed by an edit\n")
    with pytest.raises(ContractError):
        recovered.current_receipts()


def test_unfinished_action_is_never_automatically_dispatched(checker):
    check = checker.controller
    diff = checker.model.current_diff_hash
    call = check._call(diff, "check-one")
    check.journal.append("action_started", {"action_id": call.action_id, "tool": call.name,
        "arguments": call.arguments, "input_hash": check._input_hash(call),
        "baseline_diff_hash": diff})
    recovered = regression.PublicRegressionRecheck(checker.loaded, checker.model, check.root)
    for operation in (recovered.check, recovered.current_receipts, recovered.needed_seconds):
        with pytest.raises(ContractError, match="unfinished action"):
            operation()
    assert recovered.host_actions == 1 and checker.sandbox.calls == []


def test_completed_partial_pass_runs_only_checks_never_started(checker):
    check = checker.controller
    diff = checker.model.current_diff_hash
    check._gateway().execute(check._call(diff, "check-one"))
    assert check.current_receipts() is None and check.needed_seconds() == 25
    recovered = regression.PublicRegressionRecheck(checker.loaded, checker.model, check.root)
    assert recovered.check()["status"] == "failed"
    assert [row[0] for row in checker.sandbox.calls] == ["check-one", "check-two"]
    assert recovered.host_actions == 2


@pytest.mark.parametrize("changed", ["task", "environment", "quota"])
def test_recovery_binds_public_check_configuration_environment_and_quota(checker, changed):
    check = checker.controller
    if changed == "task":
        checker.loaded.public.visible_checks[0].timeout_seconds += 1
    elif changed == "environment":
        checker.loaded.environment = SimpleNamespace(model_dump=lambda **kwargs: {"image": "new"})
    with pytest.raises(ContractError, match="binding changed"):
        regression.PublicRegressionRecheck(checker.loaded, checker.model, check.root,
                                           max_passes=1 if changed == "quota" else 2)
    if changed != "quota":
        with pytest.raises(ContractError, match="configuration changed"):
            check.needed_seconds()
    assert checker.sandbox.calls == []


@pytest.mark.parametrize("field", ["workspace_diff_hash", "input_hash", "output_diff_hash"])
def test_stale_or_conflicting_durable_receipt_is_not_reused(checker, field):
    check = checker.controller
    check.check()
    raw = copy.deepcopy(check.current_receipts()[0])
    if field == "output_diff_hash":
        raw["output"]["diff_hash"] = "stale"
    else:
        raw[field] = "stale"
    check.journal.append("action_finished", {"action_id": raw["action_id"],
        "input_hash": raw["input_hash"], "result": raw})
    with pytest.raises(ContractError):
        check.current_receipts()
    assert len(checker.sandbox.calls) == 2
