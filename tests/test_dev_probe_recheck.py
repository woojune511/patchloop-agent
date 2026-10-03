"""Saved-program scheduling, delivery and crash recovery, not agent-quality claims."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from test_dev_planning import request as mock_request
from test_dev_probe_cases import REPRODUCER, ExecutingProbe, call, setup_gateway
from test_dev_runner import _crash_journal_once, _enveloped_run_id, _SimulatedCrash
from test_dev_tools import mutation_call, read_calls
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.dev import native_compaction, probe_cases, probe_recheck, runner, segments
from patchloop.dev.contracts import DevModelTurn, DevRunRequest, PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import WINDOW_RULES
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas


def request(tmp_path):
    return DevRunRequest.model_validate({
        **mock_request(tmp_path, "none").model_dump(), "enable_probes": True,
        "probe_policy": "cases-v1", "probe_recheck": probe_recheck.POLICY,
        "context_policy": "segmented-v1", "repair_recheck": True,
    })


def test_child_receipts_advance_context_cursor_without_archiving_active_selection(tmp_path):
    journal = DevJournal(tmp_path, 'run_dev_cursor')
    for kind in ['tool_batch_finished', 'probe_recheck_skipped', 'probe_recheck_finished']:
        journal.append(kind, {'action_id': kind, 'turn_id': kind})
        expected = journal.events()[-1]['event_hash']
        assert segments.cursor(journal.events()) == native_compaction.cursor(journal) == expected
    assert list(WINDOW_RULES.observations({'probe_recheck': {'active_case_id': 'expired'}})) == []


def mutate(gateway):
    for read in read_calls():
        gateway.execute(read)
    result = gateway.execute(mutation_call(gateway))
    assert result.status == "succeeded"
    return [result]


def drain(gateway, results, req, counters=None):
    counters = counters or runner._restore_counters(gateway.journal)
    result = runner._run_probe_recheck(
        journal=gateway.journal, gateway=gateway, latest_results=results, counters=counters,
        active_elapsed_ms=lambda: 10, request=req,
    )
    return result, counters


def test_cli_validation_off_parity_and_model_identity(tmp_path, monkeypatch):
    base = mock_request(tmp_path, "none")
    assert "probe_recheck" not in base.model_dump()
    with pytest.raises(ValidationError, match="probe-recheck requires"):
        DevRunRequest.model_validate({**base.model_dump(), "probe_recheck": probe_recheck.POLICY})
    on = request(tmp_path)
    manual = on.model_copy(update={"probe_recheck": "none"})
    assert runner._model_hash(on, None) != runner._model_hash(manual, None)
    captured = []
    monkeypatch.setattr(runner, "run_dev", lambda req: captured.append(req) or {})
    result = CliRunner().invoke(app, [
        "dev", "--provider", "mock", "--task", str(base.task), "--model", "mock-dev",
        "--enable-probes", "--probe-policy", "cases-v1", "--probe-recheck", probe_recheck.POLICY,
    ])
    assert result.exit_code == 0, result.output
    assert captured[0].probe_recheck == probe_recheck.POLICY
    manual_schema = dev_tool_schemas(
        finish_enabled=False, allowed_tools=['run_probe'], probe_policy='cases-v1',
    )
    automatic_schema = dev_tool_schemas(
        finish_enabled=False, allowed_tools=['run_probe'], probe_policy='cases-v1',
        probe_recheck_policy=probe_recheck.POLICY,
    )
    assert manual_schema[0]['parameters'] == automatic_schema[0]['parameters']
    assert 'never block finish or trigger automatic execution' in manual_schema[0]['description']
    assert 'automatically reruns' in automatic_schema[0]['description']
    assert 'never block finish or trigger automatic execution' not in automatic_schema[0][
        'description']


def test_selection_save_replaces_manual_replay_does_not_and_eviction_does_not_revive(
    gateway_factory,
):
    gateway, journal, _, _ = setup_gateway(gateway_factory)
    first = gateway.execute(call("save-one", source="print(1)", reference=None, save=True))
    first_id = first.output["case_comparison"]["case_id"]
    second = gateway.execute(call("save-two", source="print(2)", reference=None, save=True))
    second_id = second.output["case_comparison"]["case_id"]
    gateway.execute(call("manual-old", case_id=first_id))
    assert probe_recheck.active_program(journal.events())["definition"]["case_id"] == second_id
    gateway.execute(call("case-reference", source="print(3)", reference=None))
    for number in (3, 4):
        gateway.execute(call(f"reference-{number}", source=f"print({number})"))
    assert first_id in probe_cases.saved_cases(journal.events())
    assert probe_recheck.active_program(journal.events()) is None


def test_saved_failure_replays_current_diff_once_without_model_call(gateway_factory, tmp_path):
    gateway, journal, _, backend = setup_gateway(gateway_factory)
    gateway.execute(call(reference=None, save=True, source=REPRODUCER))
    latest = mutate(gateway)
    assert drain(gateway, latest, request(tmp_path))[0] == (None, None)
    counters = runner._restore_counters(journal)
    assert counters.model_calls == 0 and counters.tool_actions == 1
    assert backend.calls == 2 and backend.sources == [REPRODUCER, REPRODUCER]
    view = probe_recheck.context(journal, gateway.current_diff_hash)
    assert view["last_result"]["currency"] == "current"
    assert view["last_result"]["case_comparison"]["execution"]["exit_code"] == 0
    assert view["behavior_verdict"] == "not_assessed"
    drain(gateway, latest, request(tmp_path), counters)
    assert backend.calls == 2 and runner._restore_counters(journal) == counters


@pytest.mark.parametrize("kind", ["import", "assertion", "truncated", "timeout"])
def test_execution_failure_is_delivered_without_behavior_verdict(
    gateway_factory, tmp_path, kind,
):
    gateway, journal, _, backend = setup_gateway(gateway_factory)
    source = "import absent_probe_recheck_module" if kind == "import" else "assert False"
    gateway.execute(call(reference=None, save=True, source=source))
    latest = mutate(gateway)
    original = backend.run_probe

    def run(*args, **kwargs):
        output = original(*args, **kwargs)
        if kind in {"truncated", "timeout"}:
            output.update({"truncated": kind == "truncated", "timed_out": kind == "timeout"})
        return output

    backend.run_probe = run
    drain(gateway, latest, request(tmp_path))
    view = probe_recheck.context(journal, gateway.current_diff_hash)
    assert view["last_result"]["case_comparison"]["status"] == "not_compared"
    assert view["behavior_verdict"] == "not_assessed"
    assert not view["last_result"]["case_comparison"]["counts_toward_completion"]


def test_budget_skip_is_durable_and_does_not_consume_action(gateway_factory, tmp_path):
    gateway, journal, _, backend = setup_gateway(gateway_factory)
    gateway.execute(call(reference=None, save=True, source=REPRODUCER))
    latest = mutate(gateway)
    counters = runner._RunCounters(tool_actions=gateway.limits.max_tool_actions - 1)
    drain(gateway, latest, request(tmp_path), counters)
    assert backend.calls == 1 and counters.tool_actions == gateway.limits.max_tool_actions - 1
    assert probe_recheck.context(journal, gateway.current_diff_hash)["last_result"][
        "status"] == "NOT_RUN"
    drain(gateway, latest, request(tmp_path))
    assert backend.calls == 1  # No later retry of a skipped action.


def test_no_trigger_without_saved_program_or_successful_changed_edit(gateway_factory):
    gateway, journal, _, _ = setup_gateway(gateway_factory)
    latest = mutate(gateway)
    assert probe_recheck.select(journal, latest) is None
    gateway.execute(call(reference=None, save=True, source=REPRODUCER))
    assert probe_recheck.select(journal, latest) is None  # Save was after this edit.
    result = latest[0]
    for changed in (result.model_copy(update={"status": "failed"}),
                    result.model_copy(update={"tool": "read_file"}),
                    result.model_copy(update={"output": {
                        **result.output, "worktree_diff_hash": result.output["baseline_diff_hash"],
                    }})):
        assert probe_recheck.select(journal, [changed]) is None


def scripted(monkeypatch, source=REPRODUCER):
    backend = ExecutingProbe()
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    original = MockDevAdapter.next_turn
    observations = []

    def next_turn(self, context_text, tools):
        state = json.loads(context_text)
        observations.append(state)
        if not state.get("recent_probes"):
            return DevModelTurn(tool_calls=[call(reference=None, save=True, source=source)])
        return original(self, context_text, tools)

    monkeypatch.setattr(MockDevAdapter, "next_turn", next_turn)
    return backend, observations


def test_invalid_model_assertion_does_not_block_correct_submission(tmp_path, monkeypatch):
    backend, observations = scripted(monkeypatch, source='assert False')
    result = runner.run_dev(request(tmp_path))['runs'][0]
    assert result['terminal'] == 'EVALUATOR_PASS', result
    assert backend.sources == ['assert False', 'assert False']
    delivered = [s['probe_recheck']['last_result'] for s in observations
                 if s['probe_recheck']['last_result'] is not None]
    assert delivered and all(r['case_comparison']['execution']['exit_code'] == 1 for r in delivered)


def test_wrong_edit_feedback_then_real_repair_and_final_evaluation(tmp_path, monkeypatch):
    backend = ExecutingProbe()
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    original = MockDevAdapter.next_turn
    saw_failed = False

    def next_turn(self, context_text, tools):
        nonlocal saw_failed
        state = json.loads(context_text)
        if not state.get("recent_probes"):
            return DevModelTurn(tool_calls=[call(reference=None, save=True, source=REPRODUCER)])
        last = state["probe_recheck"]["last_result"]
        if last and last["case_comparison"]["execution"]["exit_code"] == 1:
            saw_failed = True
            latest = state.get("latest_tool_results", [])
            if not any(r["action_id"] == "refresh-repair" for r in latest):
                action = read_calls()[1].model_copy(update={"action_id": "refresh-repair"})
            else:
                action = RequestedTool(
                    name="replace_text", action_id="real-repair", arguments={
                        "path": self.mutation.path, "old_text": self.mutation.old_text,
                        "new_text": self.mutation.new_text, "occurrence": 1,
                        "hypothesis": "The executed reproducer still fails after the first edit.",
                        "expected_behavior": "Preserve quoted newlines through the public parser.",
                    }, turn_decision=PublicTurnDecision(
                        mode="mutate", basis="Use observed failure.",
                    ),
                )
            return DevModelTurn(tool_calls=[action])
        turn = original(self, context_text, tools)
        if turn.tool_calls[0].name == "replace_text":
            turn.tool_calls[0].arguments["new_text"] = self.mutation.old_text + "\n# experiment\n"
        return turn

    monkeypatch.setattr(MockDevAdapter, "next_turn", next_turn)
    result = runner.run_dev(request(tmp_path))["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert saw_failed and result["accepted_mutations"] == 2
    assert backend.sources == [REPRODUCER] * 3


@pytest.mark.parametrize('policy', ['append-v1', 'native-window-v1'])
def test_automatic_feedback_reaches_other_context_policies(tmp_path, monkeypatch, policy):
    backend, observations = scripted(monkeypatch)
    result = runner.run_dev(request(tmp_path).model_copy(update={'context_policy': policy}))[
        'runs'][0]
    assert result['terminal'] == 'EVALUATOR_PASS', result
    assert backend.sources == [REPRODUCER] * 2
    assert any(s['probe_recheck']['last_result'] is not None for s in observations)


@pytest.mark.parametrize("boundary,when", [
    ("probe_recheck_started", "before"), ("probe_recheck_started", "after"),
    ("action_started", "after"), ("action_finished", "after"),
    ("probe_recheck_finished", "before"), ("probe_recheck_finished", "after"),
])
def test_mock_smoke_crash_delivery_and_single_accounting(tmp_path, monkeypatch, boundary, when):
    backend, observations = scripted(monkeypatch)
    req = request(tmp_path)
    _crash_journal_once(monkeypatch, event_type=boundary, when=when,
                        predicate=lambda p: p.get("action_id", "").startswith("harness_probe_"))
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(req)
    run_id = _enveloped_run_id(tmp_path)
    resumed = req.model_copy(update={"resume_run_id": run_id})
    outcome = runner.run_dev(resumed)["runs"][0]
    assert outcome["terminal"] == "EVALUATOR_PASS", outcome
    assert outcome["evaluator"]["safety_state"] == "NOT_RUN"
    journal = DevJournal(tmp_path, run_id)
    events = journal.events()
    for event_type in ("probe_recheck_started", "probe_recheck_finished"):
        assert sum(e["event_type"] == event_type for e in events) == 1
    assert backend.sources == [REPRODUCER, REPRODUCER]
    assert any(s["probe_recheck"]["last_result"] is not None for s in observations)
    assert runner._restore_counters(journal).tool_actions == (
        sum(len(e["payload"]["tool_calls"]) for e in events
            if e["event_type"] == "tool_batch_started")
        + sum(e["event_type"] in {"probe_recheck_started", "repair_recheck_started"}
              for e in events)
    )
    before = journal.path.read_bytes()
    assert runner.run_dev(resumed)["runs"][0] == outcome
    assert journal.path.read_bytes() == before
