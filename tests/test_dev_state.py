from __future__ import annotations

import errno
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from patchloop.dev.contracts import DevToolResult
from patchloop.dev.state import DevJournal
from patchloop.errors import ActionConflict, RecoveryError
from patchloop.util import canonical_json


@pytest.mark.parametrize("fail_write", [False, True])
def test_reader_waits_for_append_and_still_rejects_failed_partial_write(
    tmp_path, monkeypatch, fail_write,
) -> None:
    journal = DevJournal(tmp_path, "run_dev_concurrentread")
    first = journal.append("run_started")
    reader = DevJournal(tmp_path, journal.run_id)
    partial_written = threading.Event()
    release_write = threading.Event()
    read_started = threading.Event()
    read_finished = threading.Event()
    write = os.write

    def paused_write(descriptor, data):
        count = write(descriptor, data[:11])
        partial_written.set()
        assert release_write.wait(5)
        if fail_write:
            raise OSError(errno.ENOSPC, "injected disk full")
        return count

    def read_events():
        read_started.set()
        try:
            return reader.events()
        finally:
            read_finished.set()

    monkeypatch.setattr(os, "write", paused_write)
    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(journal.append, "observation", {"text": "한글🙂"})
        try:
            assert partial_written.wait(5)
            reading = pool.submit(read_events)
            assert read_started.wait(5)
            assert not read_finished.wait(0.1)
        finally:
            release_write.set()
        if fail_write:
            with pytest.raises(OSError, match="injected disk full"):
                writer.result(timeout=5)
            with pytest.raises(RecoveryError, match="invalid JSONL"):
                reading.result(timeout=5)
        else:
            second = writer.result(timeout=5)
            assert reading.result(timeout=5) == [first, second]


def test_journal_completes_short_writes_before_sync(tmp_path, monkeypatch) -> None:
    journal = DevJournal(tmp_path, "run_dev_shortwrite")
    first = journal.append("run_started")
    prefix = journal.path.read_bytes()
    write = os.write
    fsync = os.fsync
    write_count = 0
    synced = []

    def short_write(descriptor, data):
        nonlocal write_count
        write_count += 1
        return write(descriptor, data[:7])

    def sync_complete_record(descriptor):
        synced.append(journal._events_unlocked())
        fsync(descriptor)

    with monkeypatch.context() as patch:
        patch.setattr(os, "write", short_write)
        patch.setattr(os, "fsync", sync_complete_record)
        second = journal.append("observation", {"text": "한글🙂"})

    assert write_count > 1
    assert synced == [[first, second]]
    assert journal.path.read_bytes() == prefix + (canonical_json(second) + "\n").encode("utf-8")
    assert DevJournal(tmp_path, journal.run_id).events() == [first, second]


@pytest.mark.parametrize("failure", ["zero", "disk_full"])
@pytest.mark.parametrize("partial", [False, True])
def test_journal_write_failure_preserves_bytes_and_rejects_torn_tail(
    tmp_path, monkeypatch, failure, partial,
) -> None:
    journal = DevJournal(tmp_path, "run_dev_writefailure")
    first = journal.append("run_started")
    prefix = journal.path.read_bytes()
    write = os.write
    suffix = b""
    calls = 0

    def fail_write(descriptor, data):
        nonlocal calls, suffix
        calls += 1
        if partial and calls == 1:
            suffix = bytes(data[:11])
            return write(descriptor, suffix)
        assert calls == (2 if partial else 1), "failed writes must not be retried"
        if failure == "zero":
            return 0
        raise OSError(errno.ENOSPC, "injected disk full")

    def unexpected_sync(descriptor):
        pytest.fail("an incomplete write must not reach fsync")

    with monkeypatch.context() as patch:
        patch.setattr(os, "write", fail_write)
        patch.setattr(os, "fsync", unexpected_sync)
        with pytest.raises(OSError) as raised:
            journal.append("observation", {"text": "incomplete"})

    assert raised.value.errno == (errno.EIO if failure == "zero" else errno.ENOSPC)
    assert journal.path.read_bytes() == prefix + suffix
    reopened = DevJournal(tmp_path, journal.run_id)
    if partial:
        with pytest.raises(RecoveryError, match="invalid JSONL"):
            reopened.events()
        with pytest.raises(RecoveryError, match="invalid JSONL"):
            reopened.append("observation", {"text": "must not discard the torn tail"})
        assert journal.path.read_bytes() == prefix + suffix
    else:
        assert reopened.events() == [first]


def test_journal_sync_failure_is_reported_without_rewriting_record(tmp_path, monkeypatch) -> None:
    journal = DevJournal(tmp_path, "run_dev_syncfailure")
    first = journal.append("run_started")
    prefix = journal.path.read_bytes()
    payload = {"call_id": "call-1", "cost_nanos": 5}

    def fail_sync(descriptor):
        raise OSError(errno.EIO, "injected fsync failure")

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", fail_sync)
        with pytest.raises(OSError, match="injected fsync failure"):
            journal.append("provider_call_finished", payload)

    retained = journal.path.read_bytes()
    assert retained.startswith(prefix)
    # Readability in this process does not establish durability after the failed fsync.
    reopened = DevJournal(tmp_path, journal.run_id)
    events = reopened.events()
    assert events[0] == first
    assert len(events) == 2
    assert events[1]["payload"] == payload
    assert reopened.append("provider_call_finished", payload) == events[1]
    assert journal.path.read_bytes() == retained
    assert reopened.provider_usage() == [payload]


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


def test_run_lifetime_execution_lock_is_non_reentrant_and_released(tmp_path) -> None:
    journal = DevJournal(tmp_path, "run_dev_state00000004")
    with (
        journal.execution_lock(),
        pytest.raises(RecoveryError, match="already active"),
        journal.execution_lock(),
    ):
        raise AssertionError("nested run execution must not acquire the lock")
    with journal.execution_lock():
        pass
