"""Registered public additions share normal repair, recovery, and completion budgets."""

from dataclasses import asdict
from decimal import Decimal
from types import SimpleNamespace

import pytest
from native_history_support import input_context
from test_dev_completion_resources import Gateway, counters
from test_dev_completion_v27 import _batch, _check
from test_dev_feedback_integration_v18 import _input
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read
from test_finish_reproduction_budget import snapshot

from patchloop.contracts import RegisteredCheck
from patchloop.dev import check_review, runner
from patchloop.dev.contracts import DevLimits
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.repair_recheck import RepairRecheck, latest_repair_check
from patchloop.dev.required_checks import RequiredPublicCheck
from patchloop.dev.tools import DevToolGateway
from patchloop.sandbox.runner import SandboxResult
from patchloop.util import sha256_json


def failed_output(check_id="public-matrix", diff_hash="candidate"):
    return {
        "check_id": check_id, "diff_hash": diff_hash, "passed": False,
        "failure_signature": sha256_json("public failure"), "exit_code": 0,
        "stdout": "PUBLIC_COUNTEREXAMPLE: expected ImportError, observed namespace",
        "stderr": "", "timed_out": False, "truncated": False,
        "deadline_exhausted": False, "cleanup_failed": False,
        "origin": "imported_public_observation",
    }


class PublicSandbox:
    backend = "local"
    supports_execution_deadline = True

    def __init__(self, fail=False):
        self.fail, self.calls = fail, []

    def run_check(self, workspace, check, **kwargs):
        self.calls.append(check.id)
        failed = self.fail and check.id == "public-matrix"
        return SandboxResult(command=check.command, exit_code=int(failed),
            stdout="CURRENT_PUBLIC_MATRIX: " + ("FAIL" if failed else "PASS"), stderr="",
            duration_ms=1, timed_out=False, truncated=False, original_output_bytes=32)


def registered_gateway(tmp_path, fail=False):
    initial = _gateway(tmp_path)
    initial.sandbox = PublicSandbox(fail)
    initial.public_task.visible_checks = [RegisteredCheck(
        id="regression", command=["python", "-c", "pass"], timeout_seconds=10)]
    _read(initial)
    _batch(initial, _mutation("first"), tmp_path)
    _batch(initial, _check("regression", "prior-pass"), tmp_path)
    entry = RequiredPublicCheck(
        check=RegisteredCheck(id="public-matrix", command=["python", "-c", "pass"],
                              timeout_seconds=30),
        binding={"program_hash": sha256_json("public fixture")},
        observation=failed_output(diff_hash=initial.current_diff_hash),
    )
    gateway = DevToolGateway(workspace=initial.workspace, public_task=initial.public_task,
        sandbox=initial.sandbox, journal=initial.journal, limits=initial.limits,
        supplemental_checks=(entry,))
    return gateway, entry


@pytest.mark.parametrize("fail", [False, True])
def test_imported_failure_drives_one_real_recheck_and_next_model_feedback(tmp_path, fail):
    gateway, entry = registered_gateway(tmp_path, fail)
    imported = next(e for e in gateway.journal.events()
                    if e["event_type"] == "public_check_imported")
    observation_id = imported["payload"]["observation_id"]
    before = runner._restore_counters(gateway.journal)
    rows = runner._recent_checks(gateway)
    row = next(row for row in rows if row["check_id"] == entry.check.id)
    assert row["origin"] == "imported_public_observation"
    assert row["action_id"] == row["observation_id"] == observation_id
    assert not row["counts_toward_completion"]
    assert gateway.sandbox.calls == ["regression"]
    _read(gateway, "current-source")
    repair = _batch(gateway, _mutation("repair", "editable = 1", "editable = 2"), tmp_path)
    result = runner._run_repair_recheck(
        journal=gateway.journal, gateway=gateway, latest_results=[repair], counters=before,
        active_elapsed_ms=lambda: 50,
    )
    assert result == (None, None)
    assert gateway.sandbox.calls == ["regression", "public-matrix"]
    assert before.tool_actions == 1 and before.model_calls == 0
    selected = next(e["payload"] for e in gateway.journal.events()
                    if e["event_type"] == "repair_recheck_finished")
    assert selected["previous_check_action_id"] == observation_id
    assert selected["previous_check_origin"] == "imported_public_observation"
    raw = runner._build_context(package=SimpleNamespace(public=SimpleNamespace(
        model_dump=lambda **kw: {"task_id": "public-note-feedback"})),
        gateway=gateway, journal=gateway.journal, correction=None, latest_tool_results=[repair],
        counters=before, elapsed_seconds=0, limits=gateway.limits, repair_recheck=True)
    view = input_context(_input(gateway, [repair], tmp_path, context=raw))
    assert view["supplemental_required_checks"][0]["check"]["id"] == "public-matrix"
    fresh = next(row for row in view["recent_checks"] if row["action_id"] == selected["action_id"])
    assert fresh["passed"] is not fail and "CURRENT_PUBLIC_MATRIX" in fresh["stdout"]
    assert view["repair_recheck"]["last_result"]["previous_check_origin"] == (
        "imported_public_observation")
    assert gateway.visible_check_status()[0]["status"] == "NOT_RUN"  # Old PASS was invalidated.
    assert not gateway.ready_to_submit()
    saved = gateway.journal.path.read_bytes()
    restored = DevToolGateway(workspace=gateway.workspace, public_task=gateway.public_task,
        sandbox=gateway.sandbox, journal=gateway.journal, limits=gateway.limits,
        supplemental_checks=(entry,))
    restored_counts = runner._restore_counters(gateway.journal)
    assert runner._run_repair_recheck(journal=gateway.journal, gateway=restored,
        latest_results=[repair], counters=restored_counts,
        active_elapsed_ms=lambda: 99) == (None, None)
    assert gateway.journal.path.read_bytes() == saved
    assert gateway.sandbox.calls == ["regression", "public-matrix"]


def budget_gateway():
    gateway = Gateway(statuses=("PASS", "FAIL"), initial=False, mutations=2)
    base, extra = (RegisteredCheck(id=f"check-{i}", command=["python", "-c", "pass"],
                                  timeout_seconds=seconds) for i, seconds in ((0, 10), (1, 30)))
    gateway.public_task.visible_checks = [base]
    gateway.registered_checks = (base, extra)
    gateway.supplemental_checks = (SimpleNamespace(check=extra),)
    gateway.events = [{"sequence": 1, "event_type": "public_check_imported", "payload": {
        "observation_id": "public_observation_bound", "output": failed_output("check-1")}}]
    current = snapshot(gateway, status="cases_verified", pending_count=0)
    current.completion_verification.update(early_replay_reusable=True,
        baseline_failure_case_ids=["original"])
    return gateway, current


@pytest.mark.parametrize("automatic,model", [(True, 3), (False, 4)])
def test_registry_counts_original_replay_and_all_checks_without_fake_response(automatic, model):
    gateway, current = budget_gateway()
    policy = runner._tool_policy(gateway, counters(model=10, tools=12), DevLimits(),
        snapshot=current,
        repair_recheck=automatic, _preview_inspection=False)
    assert policy.minimum_completion_calls == model
    assert policy.minimum_completion_tool_actions == 5
    assert "finish_task" not in policy.allowed_tools
    assert "replace_text" in policy.allowed_tools
    assert gateway.public_task.visible_checks == [gateway.registered_checks[0]]


@pytest.mark.parametrize("calls,tools,blocking", [(3, 5, "model_calls"), (4, 4, "tool_actions")])
def test_insufficient_completion_budget_exposes_required_failure_and_cannot_finish(
    calls, tools, blocking,
):
    gateway, current = budget_gateway()
    counts = counters(model=calls, tools=tools)
    policy = runner._tool_policy(gateway, counts, DevLimits(), snapshot=current,
        repair_recheck=True,
        cost_ledger=DevCostLedger(Decimal("20"), pricing_for_model("gpt-5.4-2026-03-05")),
        completion_cost_policy="completion-recovery-v1", desired_output_ceiling=40_000,
        max_correction_output_tokens=25_000, remaining_seconds=2000, _preview_inspection=False)
    assert not policy.completion_possible
    assert policy.allowed_tools == {"stop_task"}
    horizon = runner._completion_horizon_payload(gateway, counts, DevLimits(), policy,
                                                snapshot=current)
    assert blocking in horizon["blocking_resources"]
    assert horizon["required_public_checks"][0]["check_id"] == "check-1"
    assert horizon["required_public_checks"][0]["status"] == "FAIL"


def test_imported_observation_is_superseded_by_real_pass_and_old_identity_is_unchanged():
    gateway, _ = budget_gateway()
    assert latest_repair_check(gateway.events, baseline="other",
                               registered_checks={"check-1"}) is None
    assert latest_repair_check(gateway.events, baseline="candidate",
                               registered_checks=set()) is None
    passed = gateway.observation(check_id="check-1", passed=True)
    assert passed.output["passed"] is True
    assert latest_repair_check(gateway.events, baseline="candidate",
                               registered_checks={"check-1"}) is None
    ordinary = RepairRecheck("repair", "check", "contract", "before", "after")
    old = {key: value for key, value in asdict(ordinary).items() if key != "previous_check_origin"}
    expected = "harness_recheck_" + sha256_json({"run_id": "run_dev_test", **old})[7:39]
    assert ordinary.call("run_dev_test").action_id == expected
    assert "previous_check_origin" not in ordinary.payload("run_dev_test")


@pytest.mark.parametrize("resource", ["cost", "time"])
def test_required_check_cost_and_time_exact_fit_preserve_repair_and_correction(resource):
    gateway, current = budget_gateway()
    pricing = pricing_for_model("gpt-5.4-2026-03-05")

    def policy(cap=Decimal("20"), seconds=2000):
        return runner._tool_policy(gateway, counters(model=4, tools=5), DevLimits(),
            snapshot=current, repair_recheck=True, cost_ledger=DevCostLedger(cap, pricing),
            completion_cost_policy="completion-recovery-v1", desired_output_ceiling=40_000,
            max_correction_output_tokens=25_000, remaining_seconds=seconds,
            _preview_inspection=False)

    roomy = policy()
    assert roomy.minimum_completion_calls == 3
    assert roomy.minimum_completion_tool_actions == 5
    assert roomy.completion_cost["correction_model_calls_reserved"] == 1
    if resource == "cost":
        required = (roomy.completion_cost["future_cost_reserve_nanos"]
                    + DevCostLedger(Decimal("20"), pricing).future_call_reservation_nanos(
                        output_ceiling=40_000))
        exact = policy(cap=Decimal(required) / 10**9)
        short = policy(cap=Decimal(required - 1) / 10**9)
    else:
        required = roomy.completion_cost["future_time_reserve_seconds"] + runner.FOLLOWUP_SECONDS
        exact, short = policy(seconds=required), policy(seconds=required - 0.001)
        gateway.registered_checks[1].timeout_seconds += 10
        assert (policy().completion_cost["future_time_reserve_seconds"]
                == roomy.completion_cost["future_time_reserve_seconds"] + 10)
    assert exact.allowed_tools == {"replace_text", "edit_files", "stop_task"}
    assert short.allowed_tools == {"stop_task"}
    assert short.completion_cost["resource_rejections"]["replace_text"] == resource


def test_review_links_supplemental_definition_without_claiming_requirement_coverage():
    view = {"public_task": {"visible_checks": []}, "supplemental_required_checks": [{
        "check": {"id": "public-matrix", "command": ["python", "-c", "print('observed')"]},
        "origin": "host_registered_public_check", "binding_hash": "bound",
    }], "recent_checks": [{"check_id": "public-matrix", "passed": False,
                              "origin": "imported_public_observation"}]}
    check_review.link_check_evidence(view)
    review = view["recent_checks"][0]["evidence_review"]
    assert review["definition_ref"] == "supplemental_required_checks[0].check"
    assert review["selection_kind"] == "inline_python"
    assert review["coverage_status"] == review["requirement_verification"] == "not_assessed"
