"""Exact replacement keeps observed unchanged line fragments, not unseen source."""

from __future__ import annotations

import copy
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_dev_context_v12 import note_call, source_note
from test_dev_notes_lifecycle_v15 import _mutation, _read, _restart

from patchloop.dev.context import source_lines, valid_observed_span
from patchloop.dev.contracts import DevLimits
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import RecoveryError
from patchloop.repository import WorkspaceManager
from patchloop.util import sha256_bytes


class SimulatedCrash(BaseException):
    pass


def _gateway(
    tmp_path: Path, *, newline="\n", duplicate=False, final_newline=True,
) -> DevToolGateway:
    workspace = tmp_path / "work"
    workspace.mkdir(parents=True)
    lines = [f"line_{number} = {number}" for number in range(1, 20)]
    if duplicate:
        lines[4] = lines[14] = "duplicate = 1"
    content = newline.join(lines) + (newline if final_newline else "")
    (workspace / "src.py").write_bytes(content.encode())
    for args in [
        ["init", "--quiet"], ["config", "core.autocrlf", "false"], ["add", "src.py"],
        ["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"],
    ]:
        subprocess.run(["git", *args], cwd=workspace, check=True, capture_output=True)
    public = SimpleNamespace(
        constraints=SimpleNamespace(
            allowed_paths=["src.py"], forbidden_paths=[], max_diff_lines=50, max_changed_files=1,
        ),
        visible_checks=[],
    )
    return DevToolGateway(
        workspace=workspace, public_task=public, sandbox=None,
        journal=DevJournal(tmp_path / "state", "run_dev_mapping"), limits=DevLimits(),
    )


def _mapped_ranges(output):
    return sorted((span["start_line"], span["end_line"]) for span in output["revalidated_spans"])


def _assert_current_complete_spans(gateway, output):
    raw = (gateway.workspace / "src.py").read_bytes()
    lines = source_lines(raw.decode())
    for span in output["revalidated_spans"]:
        assert valid_observed_span(span, lines, sha256_bytes(raw))
        assert span["source_diff_hash"] == gateway.current_diff_hash
        assert span["span_id"] in gateway.spans


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_small_middle_edit_keeps_observed_tail_for_note_and_edit_without_reread(tmp_path, newline):
    gateway = _gateway(tmp_path, newline=newline)
    _read(gateway, start=1, end=19)
    accepted = gateway.execute(_mutation("middle", "line_10 = 10", "line_10 = 110"))
    assert accepted.status == "succeeded"
    assert _mapped_ranges(accepted.output) == [(1, 9), (11, 19)]
    _assert_current_complete_spans(gateway, accepted.output)
    # The ordinary mutation post-image stops before this already observed tail.
    assert accepted.output["mutation_evidence"]["end_line"] < 15
    payload = gateway.record_working_notes_update([
        note_call("tail-note", source_note("The unchanged tail retains public values.", 15, 19)),
    ], turn_id="after-middle")
    assert payload["allocated_note_ids"] == ["n1"]
    assert gateway.working_notes()["findings"][0]["evidence"][0]["start_line"] == 15
    following = gateway.execute(_mutation("tail", "line_18 = 18", "line_18 = 118"))
    assert following.status == "succeeded"
    read_events = [
        event for event in gateway.journal.events()
        if event["event_type"] == "action_finished"
        and event["payload"]["result"]["tool"] == "read_file"
    ]
    assert len(read_events) == 1
    raw = (gateway.workspace / "src.py").read_bytes()
    assert raw.count(b"\r\n") == (19 if newline == "\r\n" else 0)


@pytest.mark.parametrize("old,new,expected", [
    ("line_10 = 10", "replacement_a = 1\nreplacement_b = 2\nreplacement_c = 3",
     [(1, 9), (13, 21)]),
    # Removing the complete line makes the observed prefix/suffix adjacent.
    ("line_10 = 10\n", "", [(1, 18)]),
])
def test_exact_insertion_deletion_shifts_observed_tail_by_known_position(
    tmp_path, old, new, expected,
):
    gateway = _gateway(tmp_path)
    _read(gateway, start=1, end=19)
    result = gateway.execute(_mutation("shift", old, new))
    assert result.status == "succeeded"
    assert _mapped_ranges(result.output) == expected
    _assert_current_complete_spans(gateway, result.output)
    assert gateway.execute(_mutation("tail", "line_18 = 18", "line_18 = 118")).status == (
        "succeeded"
    )


def test_duplicate_observed_bodies_map_by_position_not_global_substring_uniqueness(
    tmp_path, monkeypatch,
):
    gateway = _gateway(tmp_path, duplicate=True)
    _read(gateway, "first-duplicate", 5, 5)
    _read(gateway, "anchor", 10, 10)
    _read(gateway, "second-duplicate", 15, 15)
    monkeypatch.setattr(gateway, "_mutation_postimage_evidence", lambda **kwargs: None)
    result = gateway.execute(_mutation("middle", "line_10 = 10", "line_10 = 110"))
    assert result.status == "succeeded"
    assert _mapped_ranges(result.output) == [(5, 5), (15, 15)]
    assert [span["content"] for span in result.output["revalidated_spans"]] == [
        "duplicate = 1", "duplicate = 1",
    ]
    _assert_current_complete_spans(gateway, result.output)
    # A new note can cite the exact observed occurrence even though prose repeats.
    payload = gateway.record_working_notes_update([
        note_call("duplicate-note", source_note("The second observed occurrence is still present.",
                                                15, 15)),
    ], turn_id="after-duplicates")
    assert payload["allocated_note_ids"] == ["n1"]


def test_partial_line_edit_does_not_certify_untouched_characters_as_a_full_line(
    tmp_path, monkeypatch,
):
    gateway = _gateway(tmp_path)
    _read(gateway, start=1, end=19)
    monkeypatch.setattr(gateway, "_mutation_postimage_evidence", lambda **kwargs: None)
    result = gateway.execute(_mutation("partial", "line_10", "renamed_10"))
    assert result.status == "succeeded"
    assert _mapped_ranges(result.output) == [(1, 9), (11, 19)]
    assert all(not span["start_line"] <= 10 <= span["end_line"]
               for span in gateway.prepare_context_projection().delivered_spans)
    rejected = gateway.execute(_mutation(
        "unobserved-postimage", "renamed_10 = 10", "renamed_10 = 20",
    ))
    assert rejected.status == "failed"
    assert rejected.output["mutation_failure"]["class"] == "evidence_invalid"
    assert gateway.accepted_mutations == 1


def test_mapping_never_fills_unobserved_gaps(tmp_path, monkeypatch):
    gateway = _gateway(tmp_path)
    for start, end in [(1, 3), (9, 11), (17, 19)]:
        _read(gateway, f"read-{start}", start, end)
    monkeypatch.setattr(gateway, "_mutation_postimage_evidence", lambda **kwargs: None)
    result = gateway.execute(_mutation("middle", "line_10 = 10", "line_10 = 110"))
    assert result.status == "succeeded"
    assert _mapped_ranges(result.output) == [(1, 3), (9, 9), (11, 11), (17, 19)]
    observed = {
        number for span in result.output["revalidated_spans"]
        for number in range(span["start_line"], span["end_line"] + 1)
    }
    assert observed.isdisjoint({4, 5, 6, 7, 8, 10, 12, 13, 14, 15, 16})
    _assert_current_complete_spans(gateway, result.output)


@pytest.mark.parametrize("boundary", ["atomic_write", "before_finished_record"])
def test_mapped_evidence_is_identical_after_crash_and_durable_restart(
    tmp_path, monkeypatch, boundary,
):
    expected_gateway = _gateway(tmp_path / "expected")
    _read(expected_gateway, start=1, end=19)
    call = _mutation("middle", "line_10 = 10", "line_10 = 110")
    expected = expected_gateway.execute(call)
    assert expected.status == "succeeded"
    gateway = _gateway(tmp_path / "crashed")
    _read(gateway, start=1, end=19)
    original_replace = WorkspaceManager.atomic_replace_source
    original_append = gateway.journal.append
    writes = 0

    def crash_write(workspace, path, content):
        nonlocal writes
        original_replace(workspace, path, content)
        writes += 1
        if boundary == "atomic_write":
            raise SimulatedCrash()

    def crash_finished(event_type, payload=None):
        if (boundary == "before_finished_record" and event_type == "action_finished"
                and (payload or {}).get("result", {}).get("tool") == "replace_text"):
            raise SimulatedCrash()
        return original_append(event_type, payload)

    monkeypatch.setattr(WorkspaceManager, "atomic_replace_source", staticmethod(crash_write))
    monkeypatch.setattr(gateway.journal, "append", crash_finished)
    with pytest.raises(SimulatedCrash):
        gateway.execute(call)
    monkeypatch.setattr(gateway.journal, "append", original_append)
    restored = _restart(gateway)
    recovered = restored.execute(call)
    assert recovered.status == "succeeded"
    assert recovered.output["recovered_after_crash"] is True
    assert recovered.output["revalidated_spans"] == expected.output["revalidated_spans"]
    assert recovered.output["mutation_evidence"] == expected.output["mutation_evidence"]
    assert _mapped_ranges(recovered.output) == [(1, 9), (11, 19)]
    assert writes == restored.accepted_mutations == 1
    before_bytes = restored.journal.path.read_bytes()
    before_spans = copy.deepcopy(restored.spans)
    once_more = _restart(restored)
    replayed = once_more.execute(call)
    assert replayed.replayed
    assert replayed.output == recovered.output
    assert once_more.spans == before_spans
    assert once_more.journal.path.read_bytes() == before_bytes


def test_unadmitted_target_drift_cannot_generate_mapped_evidence_on_resume(tmp_path, monkeypatch):
    gateway = _gateway(tmp_path)
    _read(gateway, start=1, end=19)
    original = WorkspaceManager.atomic_replace_source

    def crash_after_write(*args):
        original(*args)
        raise SimulatedCrash()

    monkeypatch.setattr(WorkspaceManager, "atomic_replace_source", staticmethod(crash_after_write))
    call = _mutation("middle", "line_10 = 10", "line_10 = 110")
    with pytest.raises(SimulatedCrash):
        gateway.execute(call)
    target = gateway.workspace / "src.py"
    target.write_bytes(target.read_bytes().replace(b"line_18 = 18", b"line_18 = 918"))
    before_journal = gateway.journal.path.read_bytes()
    before_target = target.read_bytes()
    restored = _restart(gateway)
    pending = next(event["payload"] for event in restored.journal.events()
                   if event["event_type"] == "action_started"
                   and event["payload"]["tool"] == "replace_text")
    with pytest.raises(RecoveryError, match="cannot be reconciled"):
        restored._reconcile_or_apply(call.arguments, pending)
    assert restored.accepted_mutations == 0
    assert not any(span.get("origin") == "revalidated_after_mutation"
                   for span in restored.spans.values())
    assert gateway.journal.path.read_bytes() == before_journal
    assert target.read_bytes() == before_target


def test_crlf_no_final_newline_second_duplicate_shift_reconciles_exactly(tmp_path, monkeypatch):
    call = _mutation("second-occurrence", "duplicate = 1", "duplicate = 2\ninserted = 3")
    call = call.model_copy(update={"arguments": {**call.arguments, "occurrence": 2}})
    expected_gateway = _gateway(
        tmp_path / "normal", newline="\r\n", duplicate=True, final_newline=False,
    )
    _read(expected_gateway, start=1, end=19)
    expected = expected_gateway.execute(call)
    assert expected.status == "succeeded"
    assert _mapped_ranges(expected.output) == [(1, 14), (17, 20)]

    gateway = _gateway(
        tmp_path / "crashed", newline="\r\n", duplicate=True, final_newline=False,
    )
    _read(gateway, start=1, end=19)
    original = WorkspaceManager.atomic_replace_source
    writes = 0

    def crash_after_write(*args):
        nonlocal writes
        original(*args)
        writes += 1
        raise SimulatedCrash()

    monkeypatch.setattr(WorkspaceManager, "atomic_replace_source", staticmethod(crash_after_write))
    with pytest.raises(SimulatedCrash):
        gateway.execute(call)
    restarted = _restart(gateway)
    recovered = restarted.execute(call)
    assert recovered.status == "succeeded"
    assert recovered.output["recovered_after_crash"] is True
    assert recovered.output["revalidated_spans"] == expected.output["revalidated_spans"]
    assert recovered.output["mutation_evidence"] == expected.output["mutation_evidence"]
    _assert_current_complete_spans(restarted, recovered.output)
    raw = (gateway.workspace / "src.py").read_bytes()
    assert raw == (expected_gateway.workspace / "src.py").read_bytes()
    assert raw.count(b"\r\n") == 19
    assert not raw.endswith(b"\n")
    assert raw.split(b"\r\n")[4] == b"duplicate = 1"
    assert raw.split(b"\r\n")[14:16] == [b"duplicate = 2", b"inserted = 3"]
    before = restarted.journal.path.read_bytes()
    replayed = _restart(restarted).execute(call)
    assert replayed.replayed
    assert replayed.output == recovered.output
    assert restarted.journal.path.read_bytes() == before
    assert writes == restarted.accepted_mutations == 1
