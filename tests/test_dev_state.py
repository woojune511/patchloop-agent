from __future__ import annotations

from patchloop.dev.contracts import DevToolResult
from patchloop.dev.state import DevJournal
from patchloop.errors import ActionConflict


def test_jsonl_is_append_only_hash_chained_and_action_idempotent(tmp_path) -> None:
    journal = DevJournal(tmp_path, "run_dev_state00000001")
    journal.append("run_started", {"value": 1})
    prefix = journal.path.read_bytes()
    result = DevToolResult(
        action_id="read-1",
        input_hash="sha256:input-a",
        tool="read_file",
        status="succeeded",
        output={"spans": []},
    )
    journal.append(
        "action_finished",
        {
            "action_id": result.action_id,
            "input_hash": result.input_hash,
            "result": result.model_dump(mode="json"),
        },
    )
    assert journal.path.read_bytes().startswith(prefix)
    assert journal.action_result("read-1", "sha256:input-a").replayed is True
    try:
        journal.action_result("read-1", "sha256:different")
    except ActionConflict:
        pass
    else:
        raise AssertionError("action ID reuse with another input must fail")
    assert [event["sequence"] for event in journal.events()] == [1, 2]


def test_unfinished_provider_dispatch_is_never_treated_as_retryable(tmp_path) -> None:
    journal = DevJournal(tmp_path, "run_dev_state00000002")
    journal.append("provider_call_started", {"call_id": "call-1", "request_hash": "h"})
    assert journal.unresolved_provider_call()["call_id"] == "call-1"
    journal.append("provider_call_finished", {"call_id": "call-1", "cost_nanos": 5})
    assert journal.unresolved_provider_call() is None
    assert journal.provider_usage() == [{"call_id": "call-1", "cost_nanos": 5}]
    journal.append("provider_call_started", {"call_id": "call-2", "request_hash": "h2"})
    assert journal.unresolved_provider_call()["call_id"] == "call-2"


def test_recorded_provider_usage_is_idempotent_and_never_double_counted(tmp_path) -> None:
    journal = DevJournal(tmp_path, "run_dev_state00000003")
    usage = {"call_id": "call-1", "cost_nanos": 5, "input_tokens": 2}
    first = journal.append("provider_call_finished", usage)
    replay = journal.append("provider_call_finished", usage)
    assert replay == first
    assert journal.provider_usage() == [usage]
    try:
        journal.append("provider_call_finished", {**usage, "cost_nanos": 6})
    except ActionConflict:
        pass
    else:
        raise AssertionError("conflicting durable provider usage must fail")
