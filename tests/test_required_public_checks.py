"""Known public failures remain obligations through edit, recovery and completion."""
from __future__ import annotations

import copy

import pytest
from test_dev_tools import mutation_call, read_calls

from patchloop.contracts import RegisteredCheck
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import completion_context, diagnosis_context, repair_context
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.required_checks import RequiredPublicCheck
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError, RecoveryError
from patchloop.sandbox.runner import SandboxResult
from patchloop.util import sha256_json


class PublicSandbox:
    official = False

    def __init__(self):
        self.passed = True
        self.calls = []

    def run_check(self, workspace, check):
        self.calls.append(check.id)
        return SandboxResult(command=check.command, exit_code=0 if self.passed else 1,
                             stdout="public mismatch" if not self.passed else "all pass",
                             stderr="", duration_ms=1, timed_out=False, truncated=False,
                             original_output_bytes=15)


def supplemental(diff_hash, *, observation=True):
    check = RegisteredCheck(id="public-counterexample", command=["public-counterexample"],
                            timeout_seconds=35)
    measured = {
        "check_id": check.id, "diff_hash": diff_hash, "passed": False,
        "stdout": "confirmed public mismatch", "stderr": "", "exit_code": 1,
        "timed_out": False, "truncated": False, "deadline_exhausted": False,
        "cleanup_failed": False,
    } if observation else None
    return RequiredPublicCheck(check=check, binding={
        "program_hash": "sealed-program", "receipt_hash": "sealed-public-receipt",
        "expectation_hash": "sealed-public-expectation", "environment": "prepared-env",
    }, observation=measured)


def reopen(gateway, entries):
    return DevToolGateway(workspace=gateway.workspace, public_task=gateway.public_task,
                          sandbox=gateway.sandbox, journal=gateway.journal,
                          limits=gateway.limits, supplemental_checks=entries,
                          deadline=gateway.deadline)


def check(gateway, check_id, action):
    return gateway.execute(RequestedTool(name="run_check", action_id=action,
                                        arguments={"check_id": check_id}))


def finish(gateway, action):
    return gateway.execute(RequestedTool(name="finish_task", action_id=action,
                                        arguments={"assessment": "public evidence reviewed"}))


def test_failure_edit_recheck_and_recovery_require_same_current_check(gateway_factory):
    sandbox = PublicSandbox()
    gateway, journal, _ = gateway_factory(sandbox=sandbox)
    original_task_hash = sha256_json(gateway.public_task.model_dump(mode="json"))
    gateway.execute_batch(read_calls())
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    assert check(gateway, "existing-unit-tests", "initial-check").output["passed"]
    entry = supplemental(gateway.current_diff_hash)
    before_calls = len(sandbox.calls)
    gateway = reopen(gateway, (entry,))
    assert len(sandbox.calls) == before_calls  # Import is not an execution.
    assert len([e for e in journal.events() if e["event_type"] == "public_check_imported"]) == 1
    assert gateway.visible_check_status()[-1]["status"] == "FAIL"
    assert not gateway.ready_to_submit()
    assert finish(gateway, "reject-known-failure").status == "failed"
    assert sha256_json(gateway.public_task.model_dump(mode="json")) == original_task_hash

    # A new candidate invalidates all old PASS/FAIL receipts; editing is not proof.
    read = read_calls()[1].model_copy(update={"action_id": "current-source"})
    assert gateway.execute(read).status == "succeeded"
    mutation = mutation_call(gateway, action_id="second-edit")
    text = MOCK_MUTATIONS["csv-quoted-newline"].new_text
    mutation.arguments.update(old_text=text, new_text=text + "\n")
    assert gateway.execute(mutation).status == "succeeded"
    assert {row["status"] for row in gateway.visible_check_status()} == {"NOT_RUN"}
    assert finish(gateway, "reject-unmeasured-edit").status == "failed"
    assert check(gateway, "existing-unit-tests", "new-public-tests").output["passed"]
    assert finish(gateway, "reject-unrelated-pass").status == "failed"
    sandbox.passed = False
    assert not check(gateway, entry.check.id, "still-fails").output["passed"]
    assert finish(gateway, "reject-new-failure").status == "failed"
    sandbox.passed = True
    assert check(gateway, entry.check.id, "now-passes").output["passed"]

    gateway = reopen(gateway, (entry,))
    assert gateway.visible_checks_pass()
    before_calls = len(sandbox.calls)
    assert check(gateway, entry.check.id, "now-passes").replayed
    assert len(sandbox.calls) == before_calls
    gateway._working_open_question = "Maybe an unrelated edge case remains?"
    assert finish(gateway, "verified-finish").status == "succeeded"
    assert len([e for e in journal.events() if e["event_type"] == "public_check_imported"]) == 1
    with pytest.raises(RecoveryError, match="registered public checks"):
        reopen(gateway, ())
    changed = copy.deepcopy(entry)
    changed.binding["expectation_hash"] = "changed"
    with pytest.raises(RecoveryError, match="registered public checks"):
        reopen(gateway, (changed,))
    gateway.deadline = ExecutionDeadline.from_remaining(0)
    restored = reopen(gateway, (entry,))
    assert check(restored, entry.check.id, "now-passes").replayed
    assert len(sandbox.calls) == before_calls


@pytest.mark.parametrize("change", ["pass", "incomplete", "wrong_diff", "collision"])
def test_import_rejects_unbound_or_incomplete_observations(gateway_factory, change):
    gateway, _, _ = gateway_factory()
    entry = supplemental(gateway.current_diff_hash)
    if change == "pass":
        entry.observation["passed"] = True
    elif change == "incomplete":
        entry.observation["truncated"] = True
    elif change == "wrong_diff":
        entry.observation["diff_hash"] = "unrelated"
    else:
        entry.check.id = "existing-unit-tests"
    with pytest.raises(ContractError):
        reopen(gateway, (entry,))


def test_registration_without_measurement_stays_pending_and_notes_are_advisory(gateway_factory):
    gateway, _, _ = gateway_factory()
    entry = supplemental(gateway.current_diff_hash, observation=False)
    gateway = reopen(gateway, (entry,))
    assert gateway.visible_check_status()[-1]["status"] == "NOT_RUN"
    assert not gateway.visible_checks_pass()
    assert not [e for e in gateway.journal.events() if e["event_type"] == "public_check_imported"]
    # Only the explicit host registry controls checks, never speculative working notes.
    gateway._working_open_question = "Maybe an unrelated edge case remains?"
    assert [row.check.id for row in gateway.supplemental_checks] == [entry.check.id]


def test_required_definitions_survive_every_model_view():
    entry = supplemental("measured")
    definitions = [{"check": entry.check.model_dump(mode="json"),
                    "binding_hash": entry.binding_hash}]
    state = {"supplemental_required_checks": definitions}
    assert compact_model_state(state, [])["supplemental_required_checks"] == definitions
    assert repair_context.project(state)["supplemental_required_checks"] == definitions
    assert diagnosis_context.project(state)["supplemental_required_checks"] == definitions
    assert completion_context.project(state)["supplemental_required_checks"] == definitions
