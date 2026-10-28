"""Request attempts stay auditable without poisoning established public cases."""

from __future__ import annotations

import copy

import pytest
from test_dev_probe_cases import TEXT, ExecutingProbe
from test_dev_tools import mutation_call, read_calls
from test_finish_reproduction import checks, finish
from test_probe_purpose import probe

from patchloop.dev import completion_reproduction as completion
from patchloop.dev import original_obligation, probe_invocation
from patchloop.dev.model_state import compact_model_state
from patchloop.util import sha256_bytes


class CompletedFixtureProbe(ExecutingProbe):
    def run_probe(self, *args, **kwargs):
        result = super().run_probe(*args, **kwargs)
        # The small local fixture adapter predates the explicit capture flag.
        return {**result, "truncated": False}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("pre-target obligation tests must not access the network")

    monkeypatch.setattr("socket.socket.connect", forbidden)


@pytest.fixture
def failed_request(gateway_factory, request):
    gateway, journal, _ = gateway_factory()
    backend = gateway.probe_sandbox = CompletedFixtureProbe()
    configuration = getattr(request, "param", "binding") == "configuration"
    source = ("observed_target(expected_exceptions=[ValueError])\n" if configuration
              else f"observed_target()({TEXT!r}, option=False)\n")
    call = probe(gateway.public_task, "bad-request", source=source)
    result = gateway.execute(call)
    assert result.status == "succeeded", result
    assert result.output["status"] == "failed"
    trace = result.output["reproduction"]["call_observation"]
    assert trace["binding_method"] == probe_invocation.CHANNEL
    if configuration:
        assert trace["calls"] == []
        assert trace["request_phase"] == {"settings_rejected": True, "target_entries": 0}
    else:
        assert trace["calls"][0]["target_started"] is False
    return gateway, journal, backend, call


def project(gateway, journal, *, events=None):
    return completion.review(
        journal.events() if events is None else events, gateway.current_diff_hash,
        public_task=gateway.public_task, run_id=journal.run_id)


@pytest.mark.parametrize("failed_request", ["binding", "configuration"], indirect=True)
def test_no_target_entry_retains_request_identity_but_never_verifies_task(failed_request):
    gateway, journal, backend, call = failed_request
    before = journal.path.read_bytes()
    state = project(gateway, journal)
    assert state["case_count"] == state["replayable_case_count"] == 0
    assert state["pending_cases"] == [] and state["status"] == "unverified"
    assert state["request_attempt_count"] == state["request_attempt_case_count"] == 1
    attempt = state["request_attempts"][0]
    assert attempt["action_id"] == attempt["root_action_id"] == "bad-request"
    assert attempt["input_hash"] and attempt["case_id"] and attempt["program_hash"]
    assert attempt["target_started"] is False and attempt["execution_status"] == "failed"
    obligation = original_obligation.review(
        journal.events(), gateway.public_task, state, acquisition="bounded-v1")
    assert obligation["status"] == "unverified" and obligation["stage"] == "pending"
    assert obligation["original_attempts"] == 1
    public = compact_model_state({"reproduction_review": {"completion": state}}, [])
    assert public["reproduction_review"]["completion"]["request_attempts"] == [attempt]
    assert gateway.execute(call).replayed and backend.calls == 1
    assert journal.path.read_bytes() == before


@pytest.mark.parametrize("failed_request", ["binding", "configuration"], indirect=True)
def test_correct_request_then_repair_can_verify_and_finish_without_erasing_attempt(
    failed_request,
):
    gateway, journal, backend, _ = failed_request
    root = gateway.execute(probe(gateway.public_task, "original"))
    assert root.output["reproduction"]["comparison"] == "mismatched"
    assert root.output["reproduction"]["call_observation"]["calls"][0]["target_started"] is True
    gateway.execute_batch(read_calls())
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    pending = project(gateway, journal)
    assert pending["status"] == "pending" and pending["case_count"] == 1
    assert pending["request_attempt_count"] == 1
    case = pending["pending_cases"][0]
    replay = completion.replay_call(journal.run_id, case["case_id"],
                                   case["root_action_id"], gateway.current_diff_hash)
    assert gateway.execute(replay).output["reproduction"]["comparison"] == "matched"
    current = project(gateway, journal)
    assert current["status"] == "cases_verified" and current["early_replay_reusable"]
    assert current["request_attempts"] == pending["request_attempts"]
    checks(gateway)
    submitted, _ = finish(gateway)
    assert submitted.output["delivery_state"] == "cases_verified_delivery"
    assert submitted.output["submission_verification"]["request_attempt_count"] == 1
    assert backend.calls == 3


@pytest.mark.parametrize("failed_request", ["configuration"], indirect=True)
def test_configuration_attempt_requires_settled_typed_host_evidence(failed_request):
    gateway, journal, _, _ = failed_request
    original = journal.events()
    for fault in ("absent", "legacy", "bool_entries", "inconsistent_entries", "untyped",
                  "not_rejected", "truncated", "no_return"):
        events = copy.deepcopy(original)
        result = next(e["payload"]["result"] for e in events
                      if e["event_type"] == "action_finished")
        output = result["output"]
        trace = output["reproduction"]["call_observation"]
        if fault == "absent":
            trace.pop("request_phase")
        elif fault == "legacy":
            start = next(e["payload"] for e in events if e["event_type"] == "action_started")
            for binding in (start["reproduction_binding"], output["reproduction"]["binding"]):
                binding["definition"]["observation_channel"] = probe_invocation.SIGNATURE_CHANNEL
            trace["binding_method"] = probe_invocation.SIGNATURE_CHANNEL
        elif fault in {"bool_entries", "inconsistent_entries"}:
            trace["request_phase"]["target_entries"] = False if fault == "bool_entries" else 1
        elif fault == "untyped":
            trace["request_phase"]["settings_rejected"] = 1
        elif fault == "not_rejected":
            trace["request_phase"]["settings_rejected"] = False
        elif fault == "truncated":
            output["truncated"] = True
        elif fault == "no_return":
            events = [e for e in events if e["event_type"] != "action_finished"]
        state = project(gateway, journal, events=events)
        assert state["case_count"] == 1 and state["status"] == "unverified", fault
        assert state.get("request_attempt_count", 0) == 0, fault
        assert state["baseline_failure_case_ids"] == [], fault


@pytest.mark.parametrize("source", [
    "raise ValueError('invalid observed_target settings')\n",
    f"observed_target()({TEXT!r})\nobserved_target(expected_exceptions=[ValueError])\n",
])
def test_text_or_settings_failure_after_target_entry_cannot_exclude_case(gateway_factory, source):
    gateway, journal, _ = gateway_factory()
    gateway.probe_sandbox = CompletedFixtureProbe()
    result = gateway.execute(probe(gateway.public_task, "unproven", source=source))
    phase = result.output["reproduction"]["call_observation"]["request_phase"]
    assert phase in ({"settings_rejected": False, "target_entries": 0},
                     {"settings_rejected": True, "target_entries": 1})
    state = project(gateway, journal)
    assert state["case_count"] == 1 and state["status"] == "unverified"
    assert state.get("request_attempt_count", 0) == 0


@pytest.mark.parametrize("fault", [
    "legacy", "missing_phase", "malformed_frame", "no_return", "pending_replay",
    "target_entered", "truncated", "timed_out", "cleanup_unknown", "negative_exit",
    "input_identity", "missing_start", "missing_truncation_flag",
])
def test_uncertain_or_entered_or_legacy_failure_remains_an_obligation(failed_request, fault):
    gateway, journal, _, _ = failed_request
    events = copy.deepcopy(journal.events())
    start = next(e["payload"] for e in events if e["event_type"] == "action_started")
    result = next(e["payload"]["result"] for e in events
                  if e["event_type"] == "action_finished")
    output = result["output"]
    observed = output["reproduction"]
    trace = observed["call_observation"]
    call = trace["calls"][0]
    if fault == "legacy":
        start["reproduction_binding"]["definition"]["observation_channel"] = (
            "invoke-declared-call-v6")
        observed["binding"]["definition"]["observation_channel"] = "invoke-declared-call-v6"
        trace["binding_method"] = "invoke-declared-call-v6"
        call.pop("target_started")
    elif fault == "missing_phase":
        call.pop("target_started")
    elif fault == "malformed_frame":
        trace["calls"] = []
    elif fault == "no_return":
        events = [e for e in events if e["event_type"] != "action_finished"]
    elif fault == "pending_replay":
        replay = copy.deepcopy(start)
        replay["action_id"] = "unsettled-replay"
        events.append({"event_type": "action_started", "payload": replay})
    elif fault == "target_entered":
        call.update(target_started=True, outcome="raised",
                    exception={"type": "builtins.TypeError", "message": "inside target"})
        call["capture"]["status"] = "complete"
    elif fault in {"truncated", "timed_out"}:
        output[fault] = True
    elif fault == "cleanup_unknown":
        output["execution_policy"]["cleanup_status"] = "unknown"
    elif fault == "negative_exit":
        output["exit_code"] = -9
    elif fault == "input_identity":
        result["input_hash"] = "different-request"
    elif fault == "missing_start":
        events = [e for e in events if e["event_type"] != "action_started"]
    elif fault == "missing_truncation_flag":
        output.pop("truncated")
    state = project(gateway, journal, events=events)
    assert state["status"] == "unverified" and state["case_count"] == 1
    assert state.get("request_attempt_count", 0) == 0
    assert state["baseline_failure_case_ids"] == []


def test_successful_target_call_before_bad_second_request_is_not_excluded(gateway_factory):
    gateway, journal, _ = gateway_factory()
    gateway.probe_sandbox = CompletedFixtureProbe()
    source = (f"observed_target()({TEXT!r})\n"
              f"observed_target()({TEXT!r}, option=False)\n")
    result = gateway.execute(probe(gateway.public_task, "mixed", source=source))
    trace = result.output["reproduction"]["call_observation"]
    assert [c["target_started"] for c in trace["calls"]] == [True, False]
    state = project(gateway, journal)
    assert state["case_count"] == 1 and state["status"] == "unverified"
    assert state.get("request_attempt_count", 0) == 0
    assert gateway.current_diff_hash == sha256_bytes(b"")
