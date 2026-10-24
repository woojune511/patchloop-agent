"""Finish-time public replay integration; deterministic fixtures, no quality claims."""

from __future__ import annotations

import json

import pytest
from test_dev_probe_cases import TEXT, ExecutingProbe, mock_request
from test_dev_runner import _crash_journal_once, _enveloped_run_id, _SimulatedCrash
from test_dev_tools import mutation_call, read_calls
from test_probe_purpose import REPORTED_FAILURE, probe

from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, DevToolResult, PublicTurnDecision, RequestedTool
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("finish reproduction tests must not use provider or network calls")

    monkeypatch.setattr("socket.socket.connect", forbidden)


def original_with_control(task):
    control = "h,v\na,b\n"
    source = (
        f"original = observed_target()({TEXT!r}).value\n"
        f"control = observed_target()({control!r}).value\n"
        "record_observation([original, control])\n"
    )
    call = probe(task, source=source)
    call.arguments["purpose"]["expected_json"] = json.dumps([
        [["h", "v"], ["first\nsecond", "x"]], [["h", "v"], ["a", "b"]],
    ])
    call.arguments["purpose"]["reported_failure_json"] = json.dumps([
        REPORTED_FAILURE, [["h", "v"], ["a", "b"]],
    ])
    return call


def mutate(gateway, *, correct=True, action="candidate"):
    for index, call in enumerate(read_calls()):
        gateway.execute(call.model_copy(update={"action_id": f"{action}-read-{index}"}))
    call = mutation_call(gateway, action_id=action)
    if not correct:
        call.arguments["new_text"] = call.arguments["old_text"] + "\n# unchanged parser\n"
    result = gateway.execute(call)
    assert result.status == "succeeded", result
    return call


def checks(gateway, prefix="checked"):
    for check in gateway.public_task.visible_checks:
        result = gateway.execute(RequestedTool(
            name="run_check", action_id=f"{prefix}-{check.id}",
            arguments={"check_id": check.id},
            turn_decision=PublicTurnDecision(mode="verify", basis="Check this exact candidate."),
        ))
        assert result.status == "succeeded" and result.output["passed"] is True, result
    assert gateway.visible_checks_pass(diff_hash=gateway.current_diff_hash)


def finish_call(action="finish"):
    return RequestedTool(
        name="finish_task", action_id=action,
        arguments={"assessment": "The current public checks pass; submit this candidate."},
        turn_decision=PublicTurnDecision(mode="finish", basis="Review the current candidate."),
    )


def finish(gateway, *, action="finish", counters=None):
    call = finish_call(action)
    counters = counters or runner._restore_counters(gateway.journal)
    gateway.journal.append("tool_batch_started", {
        "turn_id": f"turn-{action}", "tool_calls": [call.model_dump(mode="json")],
        "active_elapsed_ms": 10,
    })
    counters.tool_actions += 1
    results = runner._execute_completion_batch(
        calls=[call], journal=gateway.journal, gateway=gateway, counters=counters,
        active_elapsed_ms=lambda: 20,
    )
    gateway.journal.append("tool_batch_finished", {
        "turn_id": f"turn-{action}", "action_ids": [result.action_id for result in results],
        "active_elapsed_ms": 20,
    })
    assert len(results) == 1
    return results[0], counters


def results_for(journal, tool):
    return [event["payload"]["result"] for event in journal.events()
            if event["event_type"] == "action_finished"
            and event["payload"]["result"]["tool"] == tool]


def prepare(gateway_factory, *, original=True, correct=True):
    gateway, journal, workspace = gateway_factory()
    backend = gateway.probe_sandbox = ExecutingProbe()
    if original:
        baseline = gateway.execute(probe(gateway.public_task))
        assert baseline.output["reproduction"]["comparison"] == "mismatched"
    change = mutate(gateway, correct=correct)
    checks(gateway)
    return gateway, journal, workspace, backend, change


def test_original_failure_is_not_closed_by_helper_and_regression_pass(gateway_factory, tmp_path):
    gateway, journal, _, backend, _ = prepare(gateway_factory, correct=False)
    helper = probe(gateway.public_task, "helper", source=(
        "from mini_data_utils.csvlite import parse_rows\n"
        "assert parse_rows('h,v\\na,b\\n') == [['h', 'v'], ['a', 'b']]\n"
        "print('helper passed')\n"
    ))
    helper.arguments["purpose"] = {"kind": "helper"}
    helper_result = gateway.execute(helper)
    assert helper_result.output["exit_code"] == 0
    assert "reproduction" not in helper_result.output

    # Direct gateway calls must not bypass the runner's required replay.
    pending = gateway.execute(finish_call("without-replay"))
    assert pending.status == "failed"
    assert pending.output["submission_verification"]["status"] == "pending"
    mutation = DevToolResult.model_validate(results_for(journal, "replace_text")[-1])
    runner._run_original_recheck(
        journal=journal, gateway=gateway, latest_results=[mutation],
        counters=runner._restore_counters(journal), active_elapsed_ms=lambda: 15,
        request=request(tmp_path).model_copy(update={"limits": gateway.limits}),
    )
    assert backend.calls == 3 and backend.sources[0] == backend.sources[-1]
    result, _ = finish(gateway)
    assert result.status == "failed"
    assert result.output["submission_verification"]["status"] == "refuted"
    child = results_for(journal, "run_probe")[-1]
    assert child["workspace_diff_hash"] == gateway.current_diff_hash
    assert child["output"]["reproduction"]["comparison"] == "mismatched"
    assert backend.calls == 3  # Baseline, helper and one automatic original replay.
    second, _ = finish(gateway, action="repeat-finish")
    assert second.status == "failed" and backend.calls == 3
    assert not any(
        result["status"] == "succeeded" for result in results_for(journal, "finish_task")
    )


def test_successful_finish_replay_is_exact_and_idempotent(gateway_factory):
    gateway, journal, _, backend, _ = prepare(gateway_factory)
    result, counters = finish(gateway)
    assert result.status == "succeeded", result
    assert result.output["submission_verification"]["status"] == "cases_verified"
    assert backend.calls == 2 and backend.sources[0] == backend.sources[1]
    original_bytes = journal.path.read_bytes()
    restored_counters = runner._restore_counters(journal)
    assert restored_counters.tool_actions == counters.tool_actions == 2
    repeated = runner._execute_completion_batch(
        calls=[finish_call()], journal=journal, gateway=gateway, counters=restored_counters,
        active_elapsed_ms=lambda: 30,
    )[0]
    assert repeated.replayed
    assert journal.path.read_bytes() == original_bytes and backend.calls == 2


def test_new_edit_invalidates_a_successful_original_replay(gateway_factory):
    gateway, journal, _, backend, change = prepare(gateway_factory)
    first, _ = finish(gateway)
    assert first.output["submission_verification"]["status"] == "cases_verified"
    prior_diff = gateway.current_diff_hash
    read = read_calls()[1].model_copy(update={"action_id": "read-second-candidate"})
    gateway.execute(read)
    broken = mutation_call(gateway, action_id="regress-again")
    broken.arguments.update(
        old_text=change.arguments["new_text"],
        new_text=change.arguments["old_text"] + "\n# second candidate\n",
    )
    assert gateway.execute(broken).status == "succeeded"
    assert gateway.current_diff_hash != prior_diff
    checks(gateway, "second-check")
    second, _ = finish(gateway, action="finish-second-candidate")
    assert second.status == "failed"
    assert second.output["submission_verification"]["status"] == "refuted"
    assert backend.calls == 3 and len(set(backend.sources)) == 1
    children = [e for e in journal.events()
                if e["event_type"] == "completion_reproduction_started"]
    assert len(children) == 2
    assert len({e["payload"]["candidate_diff_hash"] for e in children}) == 2


def test_no_original_case_is_unverified_without_automatic_execution(gateway_factory):
    gateway, journal, _, backend, _ = prepare(gateway_factory, original=False)
    result, counters = finish(gateway)
    assert result.status == "succeeded", result
    assert result.output["submission_verification"]["status"] == "unverified"
    assert backend.calls == 0 and counters.tool_actions == 1
    assert not any(e["event_type"] == "completion_reproduction_started" for e in journal.events())


def test_incomplete_replay_remains_unverified_after_one_attempt(gateway_factory, monkeypatch):
    gateway, journal, _, backend, _ = prepare(gateway_factory)
    execute = backend.run_probe

    def truncated(*args, **kwargs):
        return {**execute(*args, **kwargs), "truncated": True}

    monkeypatch.setattr(backend, "run_probe", truncated)
    result, _ = finish(gateway)
    assert result.status == "succeeded", result
    assert result.output["submission_verification"]["status"] == "unverified"
    last = results_for(journal, "run_probe")[-1]["output"]["reproduction"]
    assert last["comparison"] == "not_compared"
    assert backend.calls == 2
    again, _ = finish(gateway, action="finish-still-unverified")
    assert again.status == "succeeded"
    assert again.output["submission_verification"]["status"] == "unverified"
    assert backend.calls == 2


def test_action_cap_does_not_launch_or_credit_an_original_replay(gateway_factory):
    gateway, journal, _, backend, _ = prepare(gateway_factory)
    counters = runner._RunCounters(tool_actions=gateway.limits.max_tool_actions - 1)
    result, counters = finish(gateway, counters=counters)
    assert result.status == "succeeded", result
    assert result.output["submission_verification"]["status"] == "unverified"
    assert backend.calls == 1
    assert counters.tool_actions == gateway.limits.max_tool_actions
    assert not any(e["event_type"] == "completion_reproduction_started" for e in journal.events())


@pytest.mark.parametrize("flag,terminal", [
    ("cleanup_failed", "TASK_FAILED"), ("deadline_exhausted", "LIMIT_REACHED"),
])
def test_resume_preserves_terminal_child_result_after_its_completion_marker(
    gateway_factory, monkeypatch, flag, terminal,
):
    gateway, journal, _, backend, _ = prepare(gateway_factory)
    execute = backend.run_probe

    def aborted(*args, **kwargs):
        return {**execute(*args, **kwargs), flag: True}

    monkeypatch.setattr(backend, "run_probe", aborted)
    _crash_journal_once(
        monkeypatch, event_type="completion_reproduction_finished", when="after",
    )
    with pytest.raises(_SimulatedCrash):
        finish(gateway)
    counts = runner._restore_counters(journal)
    with pytest.raises(runner._CompletionVerificationAbort) as stopped:
        runner._execute_completion_batch(
            calls=[finish_call()], journal=journal, gateway=gateway, counters=counts,
            active_elapsed_ms=lambda: 30,
        )
    assert stopped.value.terminal.value == terminal
    assert backend.calls == 2
    assert not results_for(journal, "finish_task")


def install_full_loop(monkeypatch, smoke_package):
    backend = ExecutingProbe()

    class OriginalThenRepair(MockDevAdapter):
        def next_turn(self, context, tools):
            state = json.loads(context)
            if not state["reproduction_review"]["items"]:
                return DevModelTurn(tool_calls=[original_with_control(smoke_package.public)])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", OriginalThenRepair)
    return backend


def request(tmp_path):
    return mock_request(tmp_path, policy="none").model_copy(update={
        "enable_probes": True, "context_policy": "segmented-v1",
    })


def assert_full_loop(outcome, journal, backend):
    assert outcome["terminal"] == "EVALUATOR_PASS", outcome
    assert outcome["evaluator"]["claim_eligible"] is False
    assert outcome["evaluator"]["safety_state"] == "NOT_RUN"
    assert backend.calls == 2 and backend.sources[0] == backend.sources[1]
    probes = results_for(journal, "run_probe")
    assert [p["output"]["reproduction"]["comparison"] for p in probes] == [
        "mismatched", "matched",
    ]
    observed = json.loads(probes[-1]["output"]["reproduction"]["observed_json"])
    assert observed == [
        [["h", "v"], ["first\nsecond", "x"]], [["h", "v"], ["a", "b"]],
    ]
    submitted = results_for(journal, "finish_task")[-1]
    assert submitted["status"] == "succeeded"
    assert submitted["output"]["submission_verification"]["status"] == "cases_verified"
    events = journal.events()
    for kind in ("completion_reproduction_started", "completion_reproduction_finished"):
        assert sum(e["event_type"] == kind for e in events) == 1
    restored = runner._restore_counters(journal)
    assert restored.tool_actions == sum(
        len(e["payload"]["tool_calls"]) for e in events if e["event_type"] == "tool_batch_started"
    ) + 1


def test_correct_patch_and_normal_control_reach_isolated_evaluation(
    tmp_path, monkeypatch, smoke_package,
):
    backend = install_full_loop(monkeypatch, smoke_package)
    outcome = runner.run_dev(request(tmp_path))["runs"][0]
    assert_full_loop(outcome, DevJournal(tmp_path, outcome["run_id"]), backend)


@pytest.mark.parametrize("boundary", ["mutation_result", "child_admitted", "child_result",
                                      "child_finished", "finish_result"])
def test_resume_never_reexecutes_a_durable_completion_replay(
    tmp_path, monkeypatch, smoke_package, boundary,
):
    backend = install_full_loop(monkeypatch, smoke_package)
    req = request(tmp_path)
    if boundary == "child_admitted":
        _crash_journal_once(monkeypatch, event_type="completion_reproduction_started", when="after")
    elif boundary == "child_finished":
        _crash_journal_once(
            monkeypatch, event_type="completion_reproduction_finished", when="after",
        )
    else:
        def selected(payload):
            result = payload.get("result", {})
            if boundary == "finish_result":
                return result.get("tool") == "finish_task"
            if boundary == "mutation_result":
                return result.get("tool") == "replace_text"
            return result.get("tool") == "run_probe" and result.get("action_id") != "original"

        _crash_journal_once(
            monkeypatch, event_type="action_finished", when="after", predicate=selected,
        )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(req)
    run_id = _enveloped_run_id(tmp_path)
    resumed = req.model_copy(update={"resume_run_id": run_id})
    outcome = runner.run_dev(resumed)["runs"][0]
    journal = DevJournal(tmp_path, run_id)
    assert_full_loop(outcome, journal, backend)
    before = journal.path.read_bytes()
    assert runner.run_dev(resumed)["runs"][0] == outcome
    assert journal.path.read_bytes() == before and backend.calls == 2
