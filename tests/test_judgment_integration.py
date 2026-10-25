"""Offline correction-to-repair controls; not model uptake or repair-quality evidence."""

from __future__ import annotations

import json

import pytest
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_resources import Gateway, counters
from test_dev_planning import request as mock_request
from test_dev_probe_cases import TEXT, ExecutingProbe
from test_dev_tools import mutation_call, read_calls
from test_finish_reproduction import checks, finish, mutate, results_for
from test_finish_reproduction_budget import snapshot
from test_original_obligation import restore, view
from test_probe_purpose import probe

from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits, DevModelTurn
from patchloop.dev.cost import COMPLETION_MINIMUM_POLICY
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.state import DevJournal
from patchloop.util import sha256_bytes


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("judgment integration must not access the network")

    monkeypatch.setattr("socket.socket.connect", forbidden)


def diagnostic_probe(task, action="wrong", *, corrected=False, corrects=None):
    # Trusted fixture adapter emits a diagnostic from the public CSV behavior.
    # Caller arguments and the adapter are identical before and after source repair.
    source = (
        "import mini_data_utils.csvlite as module\n"
        "original = module.parse_rows\n"
        "def diagnostic(text):\n"
        "    rows = original(text)\n"
        "    if len(rows) > 2:\n"
        "        print('F0010: quoted record split across physical lines')\n"
        "    return rows\n"
        "module.parse_rows = diagnostic\n"
        "target = observed_target()\n"
        f"bug = target({TEXT!r})\n"
        "control = target('h,v\\na,b\\n')\n"
    )
    streams = "call.stdout + call.stderr" if corrected else "call.stderr"
    source += (
        f"def has_error(call): return 'F0010' in ({streams})\n"
        "record_observation({'bug_has_error': has_error(bug), "
        "'control_has_error': has_error(control)})\n"
    )
    call = probe(task, action, source=source)
    call.arguments["purpose"].update({
        "expected_json": json.dumps({"bug_has_error": False, "control_has_error": False}),
        "reported_failure_json": json.dumps({"bug_has_error": True, "control_has_error": False}),
        "diagnostic_rules": [
            {"field": "bug_has_error", "call_id": "call-1", "contains": "F0010"},
            {"field": "control_has_error", "call_id": "call-2", "contains": "F0010"},
        ],
    })
    if corrects:
        call.arguments["purpose"]["corrects_action_id"] = corrects
    return call


def completion(gateway):
    return gateway.completion_verification(diff_hash=gateway.current_diff_hash)


def test_conflicting_capture_is_corrected_before_repair_and_finish(gateway_factory):
    initial, journal, _ = gateway_factory()
    backend = ExecutingProbe()
    gateway = restore(initial, backend=backend)
    assert gateway.execute(read_calls()[1]).status == "succeeded"
    baseline = gateway.execute(diagnostic_probe(gateway.public_task))
    wrong = baseline.output["reproduction"]
    assert wrong["judgment"]["status"] == "conflict"
    assert wrong["comparison"] == wrong["declared_failure_comparison"] == "not_compared"
    assert view(gateway)["acquisition_status"] != "acquired"
    assert completion(gateway)["observation_correction"]["status"] == "pending"
    selected = runner._tool_policy(gateway, runner._restore_counters(journal), gateway.limits)
    assert selected.workflow_gate == "needs_observation_correction"
    assert selected.allowed_tools == {"run_probe", "stop_task"}
    blocked = gateway.execute(mutation_call(gateway, action_id="premature-edit"))
    assert blocked.status == "failed" and gateway.accepted_mutations == 0
    assert gateway.current_diff_hash == sha256_bytes(b"")

    corrected = diagnostic_probe(gateway.public_task, "corrected", corrected=True, corrects="wrong")
    statement = "The recorded observation says neither case emitted the reported error."
    corrected.turn_decision.memory_update = {
        "findings": [{"note_id": None, "statement": statement,
                      "evidence": [{"kind": "tool_result", "action_id": "wrong"}]}],
        "remove_note_ids": [], "open_question": None,
    }
    gateway.record_working_notes_update([corrected], turn_id="correction-note")
    result = gateway.execute(corrected)
    assert result.status == "succeeded", result
    corrected_case = result.output["reproduction"]["binding"]["case_id"]
    assert result.output["reproduction"]["judgment"]["status"] == "consistent"
    state = completion(gateway)
    assert state["observation_correction"]["status"] == "corrected"
    assert state["baseline_failure_case_ids"] == [corrected_case]
    assert view(gateway)["acquisition_status"] == "acquired"
    note = gateway.working_notes()["findings"][0]
    assert note["statement"] == statement
    assert note["status"] == "requires_revalidation"
    assert note["judgment_update"][0]["corrected_action_id"] == "corrected"

    mutate(gateway)
    runner._replay_original_cases(
        journal=journal, gateway=gateway, counters=runner._restore_counters(journal),
        active_elapsed_ms=lambda: 20, acquired_only=True,
    )
    current = completion(gateway)
    assert current["status"] == "cases_verified" and current["early_replay_reusable"]
    assert backend.calls == 3
    assert backend.sources[1] == backend.sources[2]
    checks(gateway)
    submitted, _ = finish(gateway)
    assert submitted.output["delivery_state"] == "cases_verified_delivery"
    assert backend.calls == 3  # Finish reuses the current corrected receipt.
    stored = results_for(journal, "run_probe")
    assert stored[0]["output"]["reproduction"] == wrong  # No retroactive rewrite.


def test_correction_beyond_two_attempts_recovers_once_without_redispatch(gateway_factory):
    initial, journal, _ = gateway_factory()
    backend = ExecutingProbe()
    gateway = restore(initial, backend=backend)
    setup_error = diagnostic_probe(gateway.public_task, "setup-error")
    setup_error.arguments["python_source"] = "raise RuntimeError('fixture setup failed')"
    gateway.execute(setup_error)
    gateway.execute(diagnostic_probe(gateway.public_task))
    assert view(gateway)["original_attempts"] == 2
    assert completion(gateway)["observation_correction"]["status"] == "pending"
    fixed = diagnostic_probe(gateway.public_task, "corrected", corrected=True, corrects="wrong")
    result = restore(gateway).execute(fixed)
    assert result.status == "succeeded", result
    assert backend.calls == 3
    assert view(gateway)["original_attempts"] == 3
    before = journal.path.read_bytes()
    recovered = restore(gateway)
    assert recovered.execute(fixed).replayed
    assert journal.path.read_bytes() == before and backend.calls == 3
    repeated = fixed.model_copy(deep=True, update={"action_id": "second-correction"})
    assert recovered.execute(repeated).status == "failed"
    assert backend.calls == 3


@pytest.mark.parametrize("short", [None, "model", "tool", "money"])
def test_correction_preserves_minimum_repair_replay_check_and_finish(short):
    gateway = Gateway(initial=True)
    gateway.current_diff.patch_hash = sha256_bytes(b"")
    state = snapshot(gateway, status="unverified", case_count=0, pending_count=0)
    state.completion_verification["observation_correction"] = {
        "status": "pending", "pending_started": False, "blocked": True,
        "target_action_id": "wrong", "target_case_id": "old-case", "attempt_action_id": None,
        "reason": "observation_conflict", "superseded_case_ids": [], "corrections": [],
    }
    selected = runner._tool_policy(
        gateway, counters(model=3 if short == "model" else 4,
                          tools=4 if short == "tool" else 5), DevLimits(), snapshot=state,
        cost_ledger=ledger_for_slots(3 if short == "money" else 4),
        completion_cost_policy=COMPLETION_MINIMUM_POLICY, _preview_inspection=False,
    )
    if short:
        assert selected.allowed_tools == {"stop_task"}
        assert selected.workflow_gate == "verification_incomplete"
    else:
        assert selected.minimum_completion_calls == 4  # correction, edit, check, finish
        assert selected.minimum_completion_tool_actions == 5  # plus automatic original replay
        assert selected.allowed_tools == {"run_probe", "stop_task"}
        assert selected.workflow_gate == "needs_observation_correction"
        public = compact_model_state({
            "action_horizon": runner._repair_inspection_payload(selected),
        }, [])
        assert public["action_horizon"]["observation_correction"] == (
            selected.observation_correction)


def test_runner_stops_after_unresolved_correction_without_another_dispatch(
    tmp_path, monkeypatch, smoke_package,
):
    backend = ExecutingProbe()
    dispatched_states = []

    class StillWrongCorrection(MockDevAdapter):
        def next_turn(self, context, tools):
            state = json.loads(context)
            dispatched_states.append(state)
            if len(dispatched_states) == 1:
                call = diagnostic_probe(smoke_package.public)
            elif len(dispatched_states) == 2:
                assert state["workflow_gate"] == "needs_observation_correction"
                correction = state["reproduction_review"]["completion"]["observation_correction"]
                assert correction["status"] == "pending"
                assert correction["target_action_id"] == "wrong"
                assert correction["target_request"]["python_source"] == (
                    diagnostic_probe(smoke_package.public).arguments["python_source"])
                proof = correction["target_judgment"]
                assert proof["host_json"] != proof["authored_json"]
                assert proof["witnesses"][0]["matches"][0]["channel"] == "stdout"
                assert state["action_horizon"]["observation_correction"]["target_action_id"] == (
                    "wrong")
                call = diagnostic_probe(smoke_package.public, "failed-correction", corrects="wrong")
                # A changed program is not a corrected observation. Keep the bad extractor.
                call.arguments["python_source"] += "\n# attempted correction, predicate unchanged\n"
            else:
                pytest.fail("unresolved correction must terminate before another provider dispatch")
            return DevModelTurn(tool_calls=[call])

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", StillWrongCorrection)
    request = mock_request(tmp_path, policy="none").model_copy(update={
        "enable_probes": True, "context_policy": "segmented-v1",
        "reproduction_acquisition": "bounded-v1",
    })
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "VERIFICATION_INCOMPLETE", result
    assert result["call_counts"]["model"] == len(dispatched_states) == 2
    assert result["accepted_mutations"] == 0 and result["evaluator"] is None
    assert backend.calls == 2
    journal = DevJournal(tmp_path, result["run_id"])
    events = journal.events()
    assert not any(e["event_type"] == "original_acquisition_released" for e in events)
    actions = [e["payload"]["result"] for e in events if e["event_type"] == "action_finished"]
    assert [r["tool"] for r in actions] == ["run_probe", "run_probe"]
    assert all(r["workspace_diff_hash"] == sha256_bytes(b"") for r in actions)
    assert actions[-1]["output"]["reproduction"]["judgment"]["status"] == "conflict"


def test_output_exhaustion_preserves_unresolved_judgment_and_stop_cause(
    tmp_path, monkeypatch, smoke_package,
):
    backend = ExecutingProbe()

    class ExhaustedCorrection(MockDevAdapter):
        calls = 0

        def next_turn(self, context, tools):
            self.calls += 1
            if self.calls == 1:
                return DevModelTurn(tool_calls=[diagnostic_probe(smoke_package.public)])
            assert self.calls == 2
            assert json.loads(context)["workflow_gate"] == "needs_observation_correction"
            return DevModelTurn(
                error_code="incomplete_response", incomplete_reason="max_output_tokens")

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", ExhaustedCorrection)
    request = mock_request(tmp_path, policy="none").model_copy(update={
        "enable_probes": True, "reproduction_acquisition": "bounded-v1",
        "limits": DevLimits(max_protocol_recoveries=0),
    })
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "VERIFICATION_INCOMPLETE", result
    assert result["call_counts"]["model"] == 2 and backend.calls == 1
    assert result["accepted_mutations"] == 0 and result["evaluator"] is None
    terminal = DevJournal(tmp_path, result["run_id"]).events()[-1]["payload"]
    assert terminal["completion_horizon"]["stop_cause"] == "INCOMPLETE_RESPONSE"
    assert terminal["completion_horizon"]["observation_correction"]["blocked"] is True
