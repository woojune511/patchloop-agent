"""Four local gateway crash boundaries for the one-shot original observation."""

import pytest
from test_dev_probe_action_replay import restore
from test_first_repair_integration import observe, prepare

from patchloop.dev import first_observation


@pytest.mark.parametrize("boundary", ["admitted", "dispatched", "returned", "rejected"])
def test_first_observation_recovery_reuses_admission_and_never_repeats_execution(
    gateway_factory, monkeypatch, boundary,
):
    gateway, journal, workspace, backend, _ = prepare(gateway_factory)
    call = observe(function="missing_function" if boundary == "rejected" else "parse_rows")
    append = journal.append

    def crash(kind, payload):
        if (boundary in {"returned", "rejected"} and kind == "action_finished"
                and payload["action_id"] == call.action_id):
            raise KeyboardInterrupt("lost parent result")
        result = append(kind, payload)
        if (payload.get("action_id") == call.action_id
                and kind == {"admitted": "action_started", "dispatched": "probe_execution_started"
                             }.get(boundary)):
            raise KeyboardInterrupt("lost after durable admission or dispatch")
        return result

    journal.append = crash
    try:
        with pytest.raises(KeyboardInterrupt):
            gateway.execute(call)
    finally:
        journal.append = append
    gateway = restore(gateway, journal, workspace, gateway.public_task, backend)
    with monkeypatch.context() as pending:
        pending.setattr(first_observation, "prepare",
                        lambda *_a, **_kw: pytest.fail("reconstructed durable observation"))
        recovered = gateway.execute(call)
    state = gateway.completion_verification(diff_hash=gateway.current_diff_hash)[
        "first_observation"]
    if boundary == "dispatched":
        assert recovered.error_code == "RECOVERY_ERROR" and recovered.output["execution_uncertain"]
        assert state["status"] == "incomplete" and not state["available"]
        assert state["execution_attempted"] and backend.calls == 1
    elif boundary == "rejected":
        assert recovered.status == "failed" and backend.calls == 1
        assert state["rejected_requests"] == 1 and state["available"]
        assert not state["execution_attempted"]
    else:
        assert recovered.status == "succeeded" and backend.calls == 2
        assert state["status"] == "observed" and not state["available"]
    count = backend.calls
    assert gateway.execute(call).replayed and backend.calls == count
    if boundary != "rejected":
        assert gateway.execute(observe("fresh-name")).status == "failed"
        assert backend.calls == count
    dispatches = [event for event in journal.events()
                  if event["event_type"] == "probe_execution_started"
                  and event["payload"]["action_id"] == call.action_id]
    assert len(dispatches) == (0 if boundary == "rejected" else 1)
    assert backend.calls - 1 <= 1
