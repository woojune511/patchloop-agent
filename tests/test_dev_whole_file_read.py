from __future__ import annotations

import pytest

from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas, validate_tool_batch
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes


@pytest.fixture
def source_reader(tmp_path, monkeypatch):
    """Exercise source paging without Git or an execution sandbox."""
    source = tmp_path / "src.py"
    source.write_bytes(b"first\nsecond\n")
    gateway = object.__new__(DevToolGateway)
    gateway.read_range_only = False
    gateway.dependency_sources = None
    monkeypatch.setattr(gateway, "_tracked_path", lambda path: (path, source))
    return gateway, source


def read_call(action_id, **bounds):
    return RequestedTool(
        name="read_file", action_id=action_id,
        arguments={"path": "mini_data_utils/csvlite.py", **bounds},
        turn_decision=PublicTurnDecision(
            mode="inspect", basis="Read the selected public source.",
            evidence_goal="Observe the complete replacement context.",
        ),
    )


def restart(gateway, *, range_only=False):
    return DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task,
        sandbox=gateway.sandbox, journal=gateway.journal, limits=gateway.limits,
        read_range_only=range_only,
    )


def test_whole_file_over_400_lines_preserves_explicit_range_output(source_reader):
    gateway, source = source_reader
    lines = [f"value_{number} = {number}" for number in range(675)]
    source.write_bytes(("\r\n".join(lines) + "\r\n").encode())

    whole = gateway._read_file("src.py")
    assert whole == gateway._read_file("src.py", None, None)
    assert whole["start_line"] == 1 and whole["end_line"] == 675
    assert whole["line_count"] == 675 and whole["truncated"] is False
    assert whole["next_start_line"] is None and whole["eof"] is False
    assert whole["diagnostic"] is None
    assert whole["spans"][0]["content"] == "\n".join(lines)
    assert whole["spans"][0]["file_hash"] == sha256_bytes(source.read_bytes())

    bounded = gateway._read_file("src.py", 1, 400)
    assert set(bounded) == set(whole)
    assert bounded["end_line"] == 400 and bounded["truncated"] is False
    assert bounded["spans"][0]["content"] == "\n".join(lines[:400])
    assert gateway._read_file("src.py", 1, 675) == whole
    gateway.read_range_only = True
    with pytest.raises(ContractError, match="1-400"):
        gateway._read_file("src.py", 1, 401)


def test_pages_are_contiguous_complete_lines_with_character_not_byte_limit(source_reader):
    gateway, source = source_reader
    lines = [f"row_{number:04} " + "가" * 90 for number in range(700)]
    source.write_bytes(("\n".join(lines) + "\n").encode())
    start, delivered = None, []
    pages = []
    while True:
        page = gateway._read_file("src.py", start_line=start)
        pages.append(page)
        span = page["spans"][0]
        assert span["start_line"] == (start or 1)
        assert span["content"] == "\n".join(lines[span["start_line"] - 1:span["end_line"]])
        assert len(span["content"]) <= 24_000 < len(span["content"].encode())
        delivered.extend(span["content"].split("\n"))
        start = page["next_start_line"]
        if start is None:
            assert page["truncated"] is False
            break
        assert page["truncated"] is True and start == span["end_line"] + 1
        assert len(pages) < 4
    assert len(pages) == 3 and delivered == lines
    assert len({page["spans"][0]["file_hash"] for page in pages}) == 1


@pytest.mark.parametrize("start,end", [
    (None, 1), (True, None), (1, False), (1.0, None), ("1", None),
    (0, None), (-1, None), (2, 1), (None, False),
])
def test_invalid_or_half_specified_bounds_fail_before_read(source_reader, monkeypatch, start, end):
    gateway, _ = source_reader
    monkeypatch.setattr(
        gateway, "_tracked_path", lambda path: pytest.fail("invalid read dispatched"),
    )
    with pytest.raises(ContractError):
        gateway._read_file("src.py", start, end)


def test_empty_eof_and_oversized_lines_never_claim_unreturned_source(source_reader):
    gateway, source = source_reader
    source.write_bytes(b"")
    empty = gateway._read_file("src.py")
    assert empty["spans"] == [] and empty["line_count"] == 0
    assert empty["eof"] is True and empty["truncated"] is False
    assert empty["end_line"] is None and empty["next_start_line"] is None

    source.write_bytes(b"small\n" + b"x" * 24_001 + b"\nlast\n")
    first = gateway._read_file("src.py")
    assert first["spans"][0]["content"] == "small"
    assert first["next_start_line"] == 2 and first["truncated"] is True
    blocked = gateway._read_file("src.py", 2)
    assert blocked["spans"] == [] and blocked["end_line"] is None
    assert blocked["truncated"] is True and blocked["next_start_line"] == 2
    assert "exceeds the 24000-character" in blocked["diagnostic"]
    beyond = gateway._read_file("src.py", 4)
    assert beyond["spans"] == [] and beyond["eof"] is True
    assert beyond["truncated"] is False


def test_whole_file_still_rejects_sources_over_two_megabytes(source_reader):
    gateway, source = source_reader
    source.write_bytes(b"x" * 2_000_001)
    with pytest.raises(ContractError, match="larger than 2 MB"):
        gateway._read_file("src.py")


def test_nullable_schema_and_exact_legacy_range_schema():
    options = {
        "finish_enabled": False, "allowed_tools": ["read_file"],
        "path_diagnosis_pending": True, "read_paths": ["src.py"],
    }
    whole = dev_tool_schemas(**options)[0]
    parameters = whole["parameters"]
    assert parameters["required"] == ["path", "start_line", "end_line"]
    assert parameters["properties"]["start_line"]["type"] == ["integer", "null"]
    assert parameters["properties"]["end_line"]["type"] == ["integer", "null"]
    assert "next_start_line" in whole["description"]
    assert dev_tool_schemas(**options, read_range_only=True) == [{
        "type": "function", "name": "read_file", "strict": True,
        "description": (
            "Read one inclusive line range from a tracked public source file. "
            "Request at most 400 lines: end_line - start_line + 1 must be between 1 and 400. "
            "The existing output bound may return fewer complete lines."
        ),
        "parameters": {
            "type": "object", "properties": {
                "path": {"type": "string", "minLength": 1, "enum": ["src.py"]},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
            },
            "required": ["path", "start_line", "end_line"], "additionalProperties": False,
        },
    }]


def test_range_only_mode_rejects_new_shapes_even_with_cached_whole_read(gateway_factory):
    gateway, _, _ = gateway_factory()
    whole = read_call("whole")
    assert gateway.execute(whole).status == "succeeded"
    restricted = restart(gateway, range_only=True)
    for index, bounds in enumerate(({}, {"start_line": None, "end_line": None},
                                    {"start_line": 1, "end_line": None})):
        call = read_call(f"restricted-{index}", **bounds)
        with pytest.raises(ContractError, match="line bounds must be integers"):
            validate_tool_batch([call], read_range_only=True)
        with pytest.raises(ContractError, match="line bounds must be integers"):
            restricted.execute_batch([call])
        result = restricted.execute(call)
        assert result.status == "failed" and result.output.get("spans", []) == []
    allowed = read_call("legacy-range", start_line=1, end_line=80)
    assert validate_tool_batch([allowed], read_range_only=True) == "parallel_read"
    assert restricted.execute_batch([allowed])[0].status == "succeeded"


def test_whole_and_legacy_reads_replay_without_reading_source(gateway_factory, monkeypatch):
    gateway, _, _ = gateway_factory()
    calls = [read_call("whole"), read_call("legacy", start_line=1, end_line=4)]
    results = [gateway.execute(call) for call in calls]
    restored = restart(gateway)
    assert set(restored.spans) == set(gateway.spans)
    monkeypatch.setattr(restored, "_perform", lambda *args: pytest.fail("replayed read dispatched"))
    for call, result in zip(calls, results, strict=True):
        replay = restored.execute(call)
        assert replay.replayed is True and replay.output == result.output
        assert replay.input_hash == result.input_hash


def test_unread_page_has_no_anchor_until_delivered_and_restored(gateway_factory):
    gateway, _, workspace = gateway_factory()
    path = workspace / "mini_data_utils/csvlite.py"
    original = path.read_text(encoding="utf-8")
    path.write_text("# padding\n" * 2_700 + original, encoding="utf-8", newline="\n")
    first = gateway.execute(read_call("first-page"))
    assert first.status == "succeeded" and first.output["truncated"] is True
    assert "import csv" not in first.output["spans"][0]["content"]
    intent = {
        "path": "mini_data_utils/csvlite.py", "old_text": "import csv",
        "new_text": "import csv as csv_module", "occurrence": 1,
        "hypothesis": "Use an explicit module name.",
        "expected_behavior": "The public module binding is explicit.", "causal_revision": None,
    }
    with pytest.raises(ContractError, match="evidence spans"):
        gateway._validate_replacement_intent(intent)
    restored = restart(gateway)
    with pytest.raises(ContractError, match="evidence spans"):
        restored._validate_replacement_intent(intent)
    second = restored.execute(read_call(
        "second-page", start_line=first.output["next_start_line"], end_line=None,
    ))
    assert second.status == "succeeded" and second.output["truncated"] is False
    assert "import csv" in second.output["spans"][0]["content"]
    admitted = restored._validate_replacement_intent(intent)
    assert admitted.anchor_evidence_span_ids == (second.output["spans"][0]["span_id"],)
    path.write_text(path.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
    with pytest.raises(ContractError, match="evidence spans"):
        restored._validate_replacement_intent(intent)


@pytest.mark.parametrize("path", ["../outside.py", ".patchloop-hidden/private.py", "untracked.py"])
def test_whole_file_mode_keeps_public_tracked_path_boundary(gateway_factory, path):
    gateway, _, workspace = gateway_factory()
    (workspace / "untracked.py").write_text("public = 1\n", encoding="utf-8")
    with pytest.raises(ContractError):
        gateway._read_file(path)
