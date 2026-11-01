"""File transactions retain exact observed source through edit, undo and recovery."""

from __future__ import annotations

import subprocess

import pytest
from test_dev_notes_lifecycle_v15 import _read, _restart
from test_dev_source_rebind_v19 import _gateway
from test_file_edits import Crash, batch, edit, source_read

from patchloop.dev.context import SOURCE_OUTPUT_CHARS, source_lines, valid_observed_span
from patchloop.dev.state import DevJournal
from patchloop.util import sha256_bytes


def _current_lines(gateway, path="src.py"):
    return {
        number for span in gateway.prepare_context_projection().delivered_spans
        if span["path"] == path
        for number in range(span["start_line"], span["end_line"] + 1)
    }


def _assert_evidence(gateway, output):
    spans = [output["mutation_evidence"], *output["revalidated_spans"]]
    for span in (item for item in spans if item is not None):
        raw = (gateway.workspace / span["path"]).read_bytes()
        assert valid_observed_span(span, source_lines(raw.decode()), sha256_bytes(raw))
        assert span["source_diff_hash"] == gateway.current_diff_hash
        assert span["span_id"] in gateway.spans
        assert len(span["content"]) <= SOURCE_OUTPUT_CHARS


def _distant_edit(gateway, action="distant"):
    lines = (gateway.workspace / "src.py").read_text().splitlines()
    old = "\n".join(lines[4:15])
    new = old.replace("line_5 = 5", "line_5 = 105").replace(
        "line_15 = 15", "line_15 = 115\ninserted = 1",
    )
    return batch(action, [edit("src.py", old, new)])


@pytest.mark.parametrize("newline,final_newline", [("\n", True), ("\r\n", False)])
def test_distant_changes_keep_observed_prefix_tail_and_complete_changed_span(
    tmp_path, newline, final_newline,
):
    gateway = _gateway(tmp_path, newline=newline, final_newline=final_newline)
    _read(gateway, start=1, end=19)
    result = gateway.execute(_distant_edit(gateway))
    assert result.status == "succeeded", result.message
    assert _current_lines(gateway) == set(range(1, 21))
    evidence = result.output["mutation_evidence"]
    assert evidence["start_line"] <= 5 and evidence["end_line"] >= 16
    assert "line_15 = 115\ninserted = 1" in evidence["content"]
    _assert_evidence(gateway, result.output)
    raw = (gateway.workspace / "src.py").read_bytes()
    assert raw.endswith(b"\n") == final_newline
    assert raw.count(b"\r\n") == (19 if newline == "\r\n" else 0)
    # The untouched tail is current edit authority without another read.
    following = gateway.execute(batch("tail", [edit("src.py", "line_19 = 19", "line_19 = 119")]))
    assert following.status == "succeeded", following.message


def _commit_fixture(gateway, paths):
    for args in (["add", *paths], ["-c", "user.name=Test", "-c",
                                  "user.email=test@example.invalid", "commit", "-qm", "fixture"]):
        subprocess.run(["git", *args], cwd=gateway.workspace, check=True, capture_output=True)
    return _restart(gateway)


def test_large_replacement_keeps_preview_bound_and_does_not_certify_unread_tail(tmp_path):
    gateway = _gateway(tmp_path)
    lines = [f"line_{i} = '{'x' * 95}'" for i in range(1, 601)]
    lines[9] = lines[499] = "duplicate = 1"
    (gateway.workspace / "src.py").write_text("\n".join(lines) + "\n", encoding="utf-8")
    gateway = _commit_fixture(gateway, ["src.py"])
    for line in (10, 500, 550):
        _read(gateway, f"read-{line}", line, line)
    result = gateway.execute(batch("all", [
        edit("src.py", "duplicate = 1", "duplicate = 2", "all"),
    ]))
    assert result.status == "succeeded", result.message
    preview = result.output["mutation_evidence"]
    assert preview["start_line"] == 7 and preview["end_line"] < 500
    assert preview["truncated"] is True and len(preview["content"]) <= SOURCE_OUTPUT_CHARS
    current = _current_lines(gateway)
    assert any(span["start_line"] <= 550 <= span["end_line"]
               for span in result.output["revalidated_spans"])
    # Retention authority survives, but the existing 24k projection may select
    # only the large postimage; keeping source does not increase context budget.
    assert sum(len(span["content"]) for span in
               gateway.prepare_context_projection().delivered_spans) <= SOURCE_OUTPUT_CHARS
    assert not current.intersection({1, 2, 3, 4, 5, 6, 500, 599, 600})
    _assert_evidence(gateway, result.output)
    rejected = gateway.execute(batch("unseen-tail", [edit("src.py", lines[599], "tail = 1")]))
    assert rejected.status == "failed" and gateway.accepted_mutations == 1


def test_file_batch_rebinding_reuses_one_eight_fragment_bound(tmp_path):
    gateway = _gateway(tmp_path)
    gateway.public_task.constraints.allowed_paths = ["*.py"]
    gateway.public_task.constraints.max_changed_files = 5
    paths = ["src.py", *(f"other_{number}.py" for number in range(4))]
    for path in paths[1:]:
        (gateway.workspace / path).write_bytes((gateway.workspace / "src.py").read_bytes())
    gateway = _commit_fixture(gateway, paths[1:])
    for index, path in enumerate(paths):
        assert gateway.execute(source_read(path, f"read-{index}")).status == "succeeded"
    result = gateway.execute(batch("five-files", [
        edit(path, "line_10 = 10", "line_10 = 110") for path in paths
    ]))
    assert result.status == "succeeded", result.message
    spans = [result.output["mutation_evidence"], *result.output["revalidated_spans"]]
    assert sum(span["origin"] == "revalidated_after_mutation" for span in spans) == 8
    assert sum(span["origin"] == "accepted_mutation" for span in spans) == len(paths)
    _assert_evidence(gateway, result.output)


def test_multi_file_undo_and_recovery_preserve_the_same_current_evidence(tmp_path, monkeypatch):
    def setup(folder):
        gateway = _gateway(folder)
        gateway.public_task.constraints.allowed_paths = ["*.py"]
        gateway.public_task.constraints.max_changed_files = 2
        (gateway.workspace / "other.py").write_bytes((gateway.workspace / "src.py").read_bytes())
        gateway = _commit_fixture(gateway, ["other.py"])
        _read(gateway, start=1, end=19)
        assert gateway.execute(source_read("other.py", "read-other")).status == "succeeded"
        call = _distant_edit(gateway)
        call.arguments["edits"].append(edit("other.py", "line_10 = 10", "line_10 = 110"))
        return gateway, call

    expected_gateway, call = setup(tmp_path / "expected")
    expected = expected_gateway.execute(call)
    assert expected.status == "succeeded", expected.message
    gateway, call = setup(tmp_path / "recovered")
    append = DevJournal.append

    def crash_finished(self, event_type, payload=None):
        if event_type == "action_finished" and payload.get("action_id") == call.action_id:
            raise Crash()
        return append(self, event_type, payload)

    with monkeypatch.context() as scoped:
        scoped.setattr(DevJournal, "append", crash_finished)
        with pytest.raises(Crash):
            gateway.execute(call)
    recovered_gateway = _restart(gateway)
    recovered = recovered_gateway.execute(call)
    assert recovered.status == "succeeded", recovered.message
    for key in ("mutation_evidence", "revalidated_spans"):
        assert recovered.output[key] == expected.output[key]
    assert _current_lines(recovered_gateway) == set(range(1, 21))
    assert _current_lines(recovered_gateway, "other.py") == set(range(1, 20))
    _assert_evidence(recovered_gateway, recovered.output)
    undo = batch("undo", undo=call.action_id)
    reverted = recovered_gateway.execute(undo)
    assert reverted.status == "succeeded", reverted.message
    assert _current_lines(recovered_gateway) == set(range(1, 20))
    assert _current_lines(recovered_gateway, "other.py") == set(range(1, 20))
    _assert_evidence(recovered_gateway, reverted.output)
    journal_bytes = recovered_gateway.journal.path.read_bytes()
    resumed = _restart(recovered_gateway)
    replayed = resumed.execute(undo)
    assert replayed.replayed and replayed.output == reverted.output
    assert resumed.spans == recovered_gateway.spans
    assert resumed.journal.path.read_bytes() == journal_bytes
