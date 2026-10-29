"""Verified prefixes save parsing without trusting file metadata or caller objects."""

import os

import pytest

from patchloop.dev.state import DevJournal
from patchloop.errors import RecoveryError


def test_cached_reads_are_detached_and_external_append_is_seen(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_prefix")
    first = journal.append("observation", {"items": ["original"]})
    observed = journal.events()
    observed[0]["payload"]["items"][0] = "caller annotation"
    assert journal.events() == [first]
    other = DevJournal(tmp_path, journal.run_id)
    second = other.append("observation", {"items": ["external"]})
    assert journal.events() == [first, second]
    assert journal.events() == DevJournal(tmp_path, journal.run_id).events()


def test_same_length_same_mtime_corruption_is_not_hidden_by_cache(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_corruption")
    journal.append("observation", {"text": "original"})
    journal.events()
    original = journal.path.read_bytes()
    stat = journal.path.stat()
    journal.path.write_bytes(original.replace(b"original", b"tampered"))
    os.utime(journal.path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(RecoveryError, match="hash chain"):
        journal.events()
    with pytest.raises(RecoveryError, match="hash chain"):
        journal.append("must_not_append")
    journal.path.write_bytes(original)
    assert len(journal.events()) == 1


@pytest.mark.parametrize("suffix", [b"{", b"{}", b"{}\n", b"\xff\n"])
def test_invalid_appended_bytes_are_not_cached(tmp_path, suffix):
    journal = DevJournal(tmp_path, "run_dev_tail")
    first = journal.append("observation")
    journal.events()
    original = journal.path.read_bytes()
    journal.path.write_bytes(original + suffix)
    with pytest.raises(RecoveryError):
        journal.events()
    journal.path.write_bytes(original)
    second = journal.append("observation", {"valid": True})
    assert journal.events() == [first, second]


def test_replaced_or_truncated_file_is_revalidated(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_truncate")
    first = journal.append("observation")
    prefix = journal.path.read_bytes()
    journal.append("observation", {"second": True})
    journal.events()
    journal.path.write_bytes(prefix)
    assert journal.events() == [first]
    journal.path.unlink()
    assert journal.events() == []
    replacement = journal.append("new_chain")
    assert journal.events() == [replacement]
