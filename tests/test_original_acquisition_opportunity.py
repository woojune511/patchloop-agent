"""Separate preparation from an executable original request without renewing bounds."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from patchloop.dev import original_obligation as obligation
from patchloop.dev.state import DevJournal


def task():
    return SimpleNamespace(model_dump=lambda **_: {
        "task_id": "public-acquisition-test", "problem_statement": "Reproduce the public caller."
    })


def event(kind, **payload):
    return {"event_type": kind, "payload": payload}


def registration(*, legacy=False):
    public = task()
    payload = {**obligation.definition(public), "acquisition_policy": obligation.ACQUISITION,
               "accounting_policy": obligation.PROBE_STAGES,
               "max_original_attempts": obligation.MAX_ATTEMPTS,
               "max_request_errors": obligation.MAX_REQUEST_ERRORS,
               "max_investigation_actions": obligation.MAX_ACTIONS}
    if not legacy:
        payload.update(acquisition_budget_policy=obligation.ACQUISITION_BUDGET,
                       max_preparation_actions=obligation.MAX_PREPARATION_ACTIONS,
                       max_investigation_actions=obligation.MAX_INVESTIGATION_ACTIONS)
    return event("original_obligation_registered", **payload)


def reads(count):
    return [event("action_started", action_id=f"read-{i}", tool="read_file",
                  arguments={}, baseline_diff_hash=obligation.EMPTY_DIFF) for i in range(count)]


def probe(identity, *, kind="original_requirement", rejected=False, dispatched=False,
          returned=False):
    rows = [event("action_started", action_id=identity, tool="run_probe",
                  arguments={"purpose": {"kind": kind}}, baseline_diff_hash=obligation.EMPTY_DIFF,
                  probe_request={"status": "rejected" if rejected else "accepted", "kind": kind})]
    if dispatched:
        rows.append(event("probe_execution_started", action_id=identity))
    if returned:
        rows.append(event("probe_execution_finished", action_id=identity))
    if rejected or returned:
        rows.append(event("action_finished", result={"action_id": identity, "output": {
            "status": "failed", "reproduction": {"comparison": "not_compared"}}}))
    return rows


def review(events, **kwargs):
    completion = {"status": "unverified", "current_diff_hash": obligation.EMPTY_DIFF,
                  "baseline_failure_case_ids": []}
    completion.update(kwargs.pop("completion", {}))
    return obligation.review(events, task(), completion, acquisition=obligation.ACQUISITION,
                             **kwargs)


@pytest.mark.parametrize("count,phase,remaining", [(0, "inspect", 6), (5, "inspect", 1),
                                                   (6, "request_only", 0)])
def test_preparation_cannot_consume_the_original_request_opportunity(count, phase, remaining):
    state = review([registration(), *reads(count)])
    assert state["stage"] == "pending" and state["status"] == "unverified"
    assert state["acquisition_phase"] == phase
    assert state["preparation_actions_remaining"] == remaining
    assert state["original_attempts"] == state["request_errors"] == 0
    assert state["investigation_actions"] == count
    assert state["max_investigation_actions"] == 10


def test_helpers_spend_preparation_not_an_unbounded_extra_lane():
    events = [registration()]
    for i in range(6):
        events.extend(probe(f"helper-{i}", kind="helper", dispatched=True, returned=True))
    state = review(events)
    assert state["preparation_actions"] == 6
    assert state["acquisition_phase"] == "request_only"
    assert state["stage"] == "pending" and state["original_attempts"] == 0
    assert state["original_execution_results"] == 0


def test_rejected_original_requests_have_their_own_nonrenewable_bound():
    events = [registration(), *reads(6), *probe("invalid-1", rejected=True)]
    first = review(events)
    assert first["preparation_actions"] == 6 and first["investigation_actions"] == 7
    assert first["stage"] == "pending" and first["acquisition_phase"] == "request_only"
    assert first["request_errors"] == 1 and first["original_attempts"] == 0
    events.extend(probe("invalid-2", rejected=True))
    second = review(events)
    assert second["stage"] == "released" and second["reason"] == "request_error_limit"
    assert second["status"] == "unverified" and second["acquisition_phase"] == "inactive"
    # Receipt replay uses the same identity; counting cannot create a new allowance.
    assert review(events + probe("invalid-2", rejected=True)) == second


def test_actual_attempt_limit_waits_for_pending_result_then_releases():
    events = [registration(), *reads(6), *probe("first", dispatched=True, returned=True),
              *probe("second", dispatched=True)]
    pending = review(events)
    assert pending["original_attempts"] == pending["original_attempts_reserved"] == 2
    assert pending["preparation_actions"] == 6
    assert pending["stage"] == "pending" and pending["reason"] == "attempt_pending"
    assert pending["pending_original_dispatches"] == 1
    events.extend(probe("second", dispatched=True, returned=True)[2:])
    done = review(events)
    assert done["stage"] == "released" and done["reason"] == "original_attempt_limit"
    assert done["status"] == "unverified" and done["original_execution_results"] == 2


def test_corrected_request_keeps_both_existing_nonrenewable_bounds():
    events = [registration(), *reads(6), *probe("invalid", rejected=True),
              *probe("corrected", dispatched=True, returned=True)]
    state = review(events)
    assert state["stage"] == "pending" and state["acquisition_phase"] == "request_only"
    assert state["preparation_actions_remaining"] == 0
    assert state["request_errors"] == state["original_attempts"] == 1
    assert state["original_execution_results"] == 1 and state["status"] == "unverified"
    events.extend(probe("last-attempt", dispatched=True, returned=True))
    final = review(events)
    assert final["stage"] == "released" and final["reason"] == "original_attempt_limit"
    assert final["request_errors"] == 1 and final["original_attempts"] == 2


def test_one_real_failure_acquires_without_read_or_helper_credit():
    events = [registration(), *reads(6), *probe("failure", dispatched=True, returned=True)]
    state = review(events, completion={"baseline_failure_case_ids": ["original-case"],
                                     "status": "refuted"})
    assert state["stage"] == "acquired" and state["status"] == "refuted"
    assert state["reason"] == "baseline_failure_observed"
    assert state["acquisition_phase"] == "inactive"


@pytest.mark.parametrize("reason", ["completion_budget", "probe_unavailable"])
def test_durable_release_still_wins_over_unused_original_opportunity(reason):
    identity = obligation.definition(task())["obligation_id"]
    events = [registration(), *reads(6), event("original_acquisition_released",
                                              obligation_id=identity, reason=reason)]
    state = review(events)
    assert state["stage"] == "released" and state["reason"] == reason
    assert state["status"] == "unverified" and state["acquisition_phase"] == "inactive"


@pytest.mark.parametrize("with_probe_accounting", [False, True])
def test_legacy_registration_keeps_old_shared_six_release_on_recovery(
        tmp_path, with_probe_accounting):
    journal = DevJournal(tmp_path, "run_dev_legacyacquisition")
    payload = registration(legacy=True)["payload"]
    if not with_probe_accounting:
        payload.pop("accounting_policy")
        payload.pop("max_request_errors")
    journal.append("original_obligation_registered", payload)
    for row in reads(6):
        journal.append(row["event_type"], row["payload"])
    before = journal.path.read_bytes()
    obligation.ensure(journal, task(), obligation.ACQUISITION)
    state = review(journal.events())
    assert state["acquisition_budget_policy"] == "shared-investigation-v1"
    assert state["stage"] == "released" and state["reason"] == "investigation_action_limit"
    assert state["max_investigation_actions"] == 6
    assert journal.path.read_bytes() == before


def test_fresh_registration_and_restart_preserve_split_bound(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_freshacquisition")
    obligation.ensure(journal, task(), obligation.ACQUISITION)
    for row in reads(6):
        journal.append(row["event_type"], row["payload"])
    before = journal.path.read_bytes()
    restored = DevJournal(tmp_path, journal.run_id)
    obligation.ensure(restored, task(), obligation.ACQUISITION)
    state = review(restored.events())
    assert state["stage"] == "pending" and state["acquisition_phase"] == "request_only"
    assert state["acquisition_budget_policy"] == obligation.ACQUISITION_BUDGET
    assert journal.path.read_bytes() == before


def test_legacy_uncertain_original_reserves_attempt_without_becoming_execution():
    events = [registration(), *reads(6)]
    for identity in ("legacy-one", "legacy-two"):
        events.append(event("action_started", action_id=identity, tool="run_probe",
                            arguments={"purpose": {"kind": "original_requirement"}},
                            baseline_diff_hash=obligation.EMPTY_DIFF))
    state = review(events)
    assert state["stage"] == "pending" and state["reason"] == "attempt_pending"
    assert state["original_attempts_reserved"] == state["legacy_uncertain_original_attempts"] == 2
    assert state["original_attempts"] == state["original_execution_results"] == 0
    assert state["status"] == "unverified"
