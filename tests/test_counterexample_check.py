"""Frozen public check semantics and recovery; no Docker, provider, or target execution."""
from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from test_counterexample_packet import receipt, rows, saved  # noqa: F401

from diagnostics import counterexample_check as checks
from diagnostics import counterexample_packet as packet_api
from patchloop.contracts import RegisteredCheck
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import DevTerminal, DevToolResult
from patchloop.dev.runner import _batch_execution_abort
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_json


@pytest.fixture
def harness(saved, tmp_path, monkeypatch):  # noqa: F811
    packet = packet_api.build_packet(saved["root"])
    current = SimpleNamespace(patch_hash=packet["candidate_diff_hash"])
    monkeypatch.setattr(checks.WorkspaceManager, "diff_summary", lambda *a, **kw: current)

    class Probe:
        def __init__(self):
            self.calls, self.preflights = [], []
            self.receipt = receipt(rows(True), packet["program_hash"])
            self.error = None

        def preflight(self, *, deadline):
            self.preflights.append(deadline)
            return {key: packet["environment"][key] for key in ("image_digest", "profile_hash")}

        def run_probe(self, workspace, question, source, **kwargs):
            self.calls.append((workspace, question, source, kwargs))
            if self.error:
                raise self.error
            return copy.deepcopy(self.receipt)

    class Delegate:
        backend, official = "local", False
        supports_execution_deadline = True
        supports_public_execution = True

        def run_check(self, workspace, check, **kwargs):
            return (workspace, check, kwargs)

    journal = DevJournal(tmp_path / "audit", "run_dev_check")
    probe, delegate = Probe(), Delegate()
    sandbox = checks.CheckSandbox(delegate, probe, journal, packet)
    identity = {"run_id": journal.run_id, "action_id": "public-check-one"}
    return SimpleNamespace(packet=packet, current=current, journal=journal, sandbox=sandbox,
                           probe=probe, delegate=delegate, identity=identity, workspace=tmp_path)


def execute(harness):
    return harness.sandbox.run_check(
        harness.workspace, harness.sandbox.entry.check,
        deadline=ExecutionDeadline.from_remaining(100), execution_identity=harness.identity)


def test_registration_binds_program_cases_environment_and_failure(harness):
    entry = harness.sandbox.entry
    assert len(entry.binding["mandatory_cases"]) == 11
    assert entry.binding["preexisting_excluded"] == ["namespace_root_empty"]
    assert entry.check.command == ["python", "-c", harness.packet["program_text"]]
    assert entry.binding["environment"] == harness.packet["environment"]
    assert entry.binding["source_provenance"] == harness.packet["evidence_files"]
    assert entry.binding["packet_hash"] == sha256_json(harness.packet)
    assert entry.observation["passed"] is False
    assert all(entry.observation[flag] is False for flag in
               ("timed_out", "truncated", "deadline_exhausted", "cleanup_failed"))
    assert harness.journal.events() == [] and harness.probe.calls == []


@pytest.mark.parametrize("repaired", [False, True])
def test_exit_zero_is_assessed_by_cases_and_complete_receipt_is_reused(harness, repaired):
    harness.probe.receipt = receipt(rows(not repaired), harness.packet["program_hash"])
    outcome = execute(harness)
    assert outcome.exit_code == (0 if repaired else 1)
    assert outcome.passed is repaired
    assert '"mandatory":false' in outcome.stdout  # The shared discrepancy is not a new obligation.
    assert len(harness.probe.calls) == 1
    details = json.loads(outcome.stdout.removeprefix(checks.PREFIX))["failed_case_details"]
    if not repaired:
        assert len(details) == 3
        assert details[0]["actual"]["status"] == "found"
        assert details[0]["expected"] == {"status": "ImportError"}
    assert harness.probe.calls[0][2] == harness.packet["program_text"]
    assert harness.probe.calls[0][3]["execution_identity"] == harness.identity
    assert harness.probe.calls[0][3]["deadline"] is harness.probe.preflights[0]
    assert harness.probe.preflights[0].remaining_seconds() <= checks.TIMEOUT_SECONDS
    rebuilt = checks.CheckSandbox(harness.delegate, harness.probe, harness.journal, harness.packet)
    harness.sandbox = rebuilt
    replay = execute(harness)
    assert replay == outcome and len(harness.probe.calls) == 1


@pytest.mark.parametrize("field,value", [
    ("timed_out", True), ("truncated", True), ("cleanup_failed", True),
    ("deadline_exhausted", True), ("source_hash", "different"),
    ("image_digest", "different"), ("profile_hash", "different"),
    ("exit_code", 1), ("stdout", "missing report"),
])
def test_invalid_observation_is_infrastructure_failure_not_semantic_pass(harness, field, value):
    harness.probe.receipt[field] = value
    with pytest.raises(RecoveryError, match="incomplete or invalid"):
        execute(harness)
    # A durable returned receipt is parsed again without dispatching again.
    with pytest.raises(RecoveryError, match="incomplete or invalid"):
        execute(harness)
    assert len(harness.probe.calls) == 1


def test_incomplete_matrix_and_dependency_drift_do_not_clear_the_obligation(harness):
    harness.probe.receipt = receipt(rows(False)[:-1], harness.packet["program_hash"])
    with pytest.raises(RecoveryError, match="incomplete or invalid"):
        execute(harness)
    assert len(harness.probe.calls) == 1
    other = copy.deepcopy(harness.packet)
    other["environment"]["dependencies"] = {"changed": True}
    with pytest.raises(RecoveryError, match="recovery identity changed"):
        checks.CheckSandbox(harness.delegate, harness.probe, harness.journal, other).run_check(
            harness.workspace, harness.sandbox.entry.check, execution_identity=harness.identity)


def test_unsettled_execution_stops_without_retry(harness):
    harness.probe.error = RuntimeError("uncertain transport")
    with pytest.raises(RecoveryError, match="did not settle") as error:
        execute(harness)
    assert error.value.details["execution_uncertain"]
    failure = DevToolResult(action_id="failed-check", input_hash="bound", tool="run_check",
                            status="failed", error_code=error.value.code,
                            output=error.value.details)
    assert _batch_execution_abort([failure])[0] == DevTerminal.TASK_FAILED
    with pytest.raises(RecoveryError, match="unsettled"):
        execute(harness)
    assert len(harness.probe.calls) == 1


def test_changed_program_or_mutable_binding_rejected_before_dispatch(harness):
    packet = copy.deepcopy(harness.packet)
    packet["program_text"] += "# changed"
    with pytest.raises(ContractError, match="program changed"):
        checks.required_check(packet)
    harness.sandbox.entry.binding["timeout_seconds"] += 1
    with pytest.raises(RecoveryError, match="binding changed"):
        execute(harness)
    assert harness.probe.calls == []


def test_other_registered_checks_keep_their_original_backend(harness):
    check = RegisteredCheck(id="base-check", command=["python", "-c", "pass"])
    value = harness.sandbox.run_check(harness.workspace, check,
                                     execution_identity=harness.identity)
    assert value[1] == check and value[2]["execution_identity"] == harness.identity
    assert harness.probe.calls == []
    harness.sandbox.delegate = SimpleNamespace(run_check=lambda workspace, check: "legacy")
    assert harness.sandbox.run_check(harness.workspace, check) == "legacy"


def test_current_summary_needs_durable_registration_or_current_check_result(harness):
    entry = harness.sandbox.entry
    current = harness.current.patch_hash
    assert checks.summary(harness.journal, harness.packet, current)["status"] == "NOT_RUN"
    harness.journal.append("public_check_imported", {"observation_id": entry.observation_id,
        "output": {**entry.observation, "binding_hash": entry.binding_hash}})
    assert checks.summary(harness.journal, harness.packet, current)["status"] == "FAIL"
    changed = "sha256:" + "2" * 64
    assert checks.summary(harness.journal, harness.packet, changed)["status"] == "NOT_RUN"
    harness.probe.receipt = receipt(rows(False), harness.packet["program_hash"])
    outcome = execute(harness)
    harness.journal.append("action_finished", {"result": {
        "tool": "run_check", "action_id": "registered-check", "input_hash": "exact-input",
        "status": "succeeded", "output": {"check_id": checks.CHECK_ID, "diff_hash": changed,
                                           "passed": True, "stdout": outcome.stdout}}})
    report = checks.summary(harness.journal, harness.packet, changed)
    assert report["status"] == "PASS" and report["source"] == "registered_check"
    assert report["preexisting"]["status"] == "FAIL"
    assert report["additional_final_executions"] == 0
    harness.journal.append("action_started", {"action_id": "failed-check", "tool": "run_check",
        "arguments": {"check_id": checks.CHECK_ID}})
    harness.journal.append("action_finished", {"result": {
        "tool": "run_check", "action_id": "failed-check", "input_hash": "bound",
        "status": "failed", "workspace_diff_hash": changed,
        "output": {"execution_uncertain": True}}})
    assert checks.summary(harness.journal, harness.packet, changed)["status"] == "INCOMPLETE"
