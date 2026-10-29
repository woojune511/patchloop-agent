"""A public revision request retains one edit route without new funding or verdicts."""
import copy
import json
from dataclasses import asdict
from decimal import Decimal

import pytest
from test_counterexample_check import harness, saved  # noqa: F401
from test_dev_completion_resources import Gateway, counters
from test_finish_reproduction_budget import snapshot

from diagnostics import counterexample_repair
from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits
from patchloop.dev.cost import DevCostLedger, pricing_for_model


def policy(*, calls=5, tools=8, money="20", seconds=2000, requested="candidate",
           anchor=True, edits=2, correction=1, current="candidate", preview=False):
    gateway = Gateway(statuses=("PASS",), initial=False, mutations=edits, anchor=anchor)
    gateway.current_diff.patch_hash = current
    gateway.public_task.visible_checks[0].timeout_seconds = 10
    state = snapshot(gateway, status="cases_verified", pending_count=0)
    state.completion_verification.update(early_replay_reusable=True,
        early_reproduction_count=1, baseline_failure_case_ids=["original"])
    return runner._tool_policy(gateway, counters(model=calls, tools=tools),
        # Gateway's `edits` argument uses a fixed four-edit fixture budget.
        DevLimits(max_protocol_recoveries=correction, max_accepted_mutations=4),
        snapshot=state, repair_recheck=True,
        cost_ledger=DevCostLedger(Decimal(money), pricing_for_model("gpt-5.4-2026-03-05")),
        completion_cost_policy="completion-recovery-v1", desired_output_ceiling=40_000,
        max_correction_output_tokens=25_000, remaining_seconds=seconds,
        requested_revision_diff_hash=requested, _preview_inspection=preview)


def test_probe_before_last_edit_window_is_closed_but_edit_and_finish_stay_available():
    before = policy(calls=5)
    assert {"run_probe", "read_file", "replace_text", "finish_task"} <= before.allowed_tools
    after_probe = policy(calls=4, tools=7)
    assert after_probe.allowed_tools == {"replace_text", "edit_files", "finish_task", "stop_task"}
    assert after_probe.mutation_completion_possible
    assert after_probe.workflow_gate == "ready_to_submit"
    assert after_probe.minimum_completion_calls == 1  # No invented mandatory task failure.
    assert after_probe.completion_cost["correction_model_calls_reserved"] == 1
    assert after_probe.completion_cost["resource_rejections"]["run_probe"] == "model_calls"
    route = before.completion_cost["completion_routes"]["run_probe"]
    assert (route["kind"], route["model_calls"], route["tool_actions"]) == (
        "requested_revision", 4, 5)


@pytest.mark.parametrize("boundary", ["money", "tools", "time", "calls"])
def test_same_revision_path_has_exact_physical_cost_and_time_boundaries(boundary):
    # Current helper, repair, check and finish use four responses. Host original
    # replay adds an action. An unused protocol correction adds one response.
    # Five 60K inputs + outputs 8192/40000/8192/8192/25000 cost USD2.09364.
    options = dict(calls=5, tools=5, money="2.093640000", seconds=235)
    fit = policy(**options)
    assert "run_probe" in fit.allowed_tools
    row = fit.completion_cost["completion_routes"]["run_probe"]
    assert (row["model_calls"], row["tool_actions"]) == (4, 5)
    if boundary == "money":
        options["money"] = "2.093639999"
    elif boundary == "tools":
        options["tools"] = 4
    elif boundary == "time":
        options["seconds"] = 234
    else:
        options["calls"] = 4
    short = policy(**options)
    assert "run_probe" not in short.allowed_tools
    assert {"replace_text", "finish_task", "stop_task"} <= short.allowed_tools


def test_caller_read_does_not_spend_the_still_missing_source_anchor():
    fit = policy(calls=6, anchor=False)
    assert "read_file" in fit.allowed_tools
    route = fit.completion_cost["completion_routes"]["read_file"]
    assert (route["model_calls"], route["tool_actions"]) == (5, 6)
    assert "read_file" not in policy(calls=5, anchor=False).allowed_tools


def test_no_request_stale_diff_and_zero_edits_preserve_ordinary_policy():
    ordinary = policy(requested=None, calls=4)
    assert "run_probe" in ordinary.allowed_tools
    assert asdict(policy(requested="other", calls=4)) == asdict(ordinary)
    assert asdict(policy(current="new", requested="candidate", calls=4)) == asdict(
        policy(current="new", requested=None, calls=4))
    assert asdict(policy(edits=0)) == asdict(policy(edits=0, requested=None))
    assert "requested_revision" not in ordinary.completion_cost


def test_preview_and_reconstruction_keep_the_same_nonrenewing_reservation():
    first = policy(preview=True)
    restored = policy(preview=True)
    assert asdict(first) == asdict(restored)
    assert "run_probe" in first.tools_closing_after_this_turn
    assert "replace_text" not in first.tools_closing_after_this_turn
    # Rejected/no-op edits leave the measured diff unchanged: the reserve stays.
    assert "requested_revision" in policy(calls=4).completion_cost
    # A genuinely changed diff does not inherit evidence that its tests failed.
    assert "requested_revision" not in policy(current="edited").completion_cost


def test_diagnostic_binding_comes_from_the_frozen_packet_not_model_notes(
    monkeypatch, harness,  # noqa: F811
):
    captured = []

    def original(*args, **kwargs):
        captured.append(kwargs)
        return "policy"

    class Gateway:
        def __init__(self, **kwargs):
            self.arguments = kwargs

    state = {"current_diff": {"patch_hash": harness.packet["candidate_diff_hash"]},
             "working_notes": [{"statement": "All public counterexamples pass."}]}
    def build_context(**kwargs):
        return json.dumps(state)

    def build_input(**kwargs):
        return [{"role": "user", "content": json.dumps({"state": state})}]

    monkeypatch.setattr(runner, "_tool_policy", original)
    monkeypatch.setattr(runner, "DevToolGateway", Gateway)
    monkeypatch.setattr(runner, "_build_context", build_context)
    monkeypatch.setattr(runner, "_build_model_input", build_input)
    packet = copy.deepcopy(harness.packet)
    with counterexample_repair.public_feedback(packet):
        packet["regressions"] = []
        packet["program_text"] += "# later mutable caller input\n"
        gateway = runner.DevToolGateway(sandbox=harness.delegate,
            probe_sandbox=harness.probe, journal=harness.journal)
        entry, = gateway.arguments["supplemental_checks"]
        assert entry == harness.sandbox.entry
        assert entry.observation["passed"] is False
        assert gateway.arguments["sandbox"].entry == entry
        assert gateway.arguments["sandbox"].delegate is harness.delegate
        assert runner._tool_policy is original
        assert runner._tool_policy() == "policy"
        for delivered in (json.loads(runner._build_context()),
                          json.loads(runner._build_model_input()[-1]["content"])["state"]):
            feedback = delivered[counterexample_repair.FIELD]
            assert feedback["regressions"] == harness.packet["regressions"]
            assert feedback["program_definition_ref"]["program_hash"] == (
                harness.packet["program_hash"])
            assert feedback["required_check_status"] == "NOT_RUN"
            assert feedback["new_verification_required"]
            assert delivered["working_notes"] == state["working_notes"]
    assert captured == [{}]
    assert runner._tool_policy is original
    assert runner.DevToolGateway is Gateway
    assert runner._build_context is build_context
    assert runner._build_model_input is build_input
    assert harness.journal.events() == [] and harness.probe.calls == []
