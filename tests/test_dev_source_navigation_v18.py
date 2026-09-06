"""Metadata-only navigation over already delivered public source evidence."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from patchloop.dev.context import (
    OBSERVED_SOURCE_INDEX_CHARS,
    OBSERVED_SOURCE_INDEX_ENTRIES,
    build_observed_source_index,
    project_observed_sources,
)


def _span(path: str, start: int, content: str, *, file_hash: str = "sha256:current") -> dict:
    return {
        "path": path,
        "file_hash": file_hash,
        "start_line": start,
        "end_line": start + len(content.split("\n")) - 1,
        "content": content,
        "last_observed_seq": 1,
    }


def _locations(index: dict) -> list[tuple[str, str, str, int]]:
    return [
        (item["path"], item["name"], item["kind"], item["start_line"])
        for item in index["entries"]
    ]


def test_index_merged_current_delivered_ranges_and_native_results() -> None:
    first = _span("pkg/edit.py", 15, "class Editor:\n    def edit(self):")
    adjacent = _span("pkg/edit.py", 17, "        return 1\n    async def inspect(self):")
    native = _span("helper.py", 1, "def helper():\n    return 2")
    projection = project_observed_sources(
        [first, adjacent, native], native_spans=[native], priorities=[],
        editable_paths={"pkg/edit.py"},
    )
    before = copy.deepcopy(projection)
    index = build_observed_source_index(
        projection.delivered_spans, editable_paths=projection.editable_paths,
    )
    assert _locations(index) == [
        ("pkg/edit.py", "Editor", "class", 15),
        ("pkg/edit.py", "edit", "def", 16),
        ("pkg/edit.py", "inspect", "async_def", 18),
        ("helper.py", "helper", "def", 1),
    ]
    assert projection == before
    assert index["omitted_count"] == 0
    assert "Not parsed symbols" in index["interpretation"]
    assert "complete function ranges" in index["interpretation"]
    assert all("end_line" not in item and "content" not in item for item in index["entries"])


def test_duplicates_nested_declarations_and_order_are_deterministic() -> None:
    outer = _span("x.py", 40, "def outer():\n    def nested():\n        return 1")
    overlap = _span("x.py", 41, "    def nested():\n        return 1")
    other = _span("a.py", 9, "class Earlier: pass")
    left = build_observed_source_index([outer, overlap, outer, other])
    right = build_observed_source_index([other, overlap, outer])
    assert left == right
    assert _locations(left) == [
        ("a.py", "Earlier", "class", 9),
        ("x.py", "outer", "def", 40),
        ("x.py", "nested", "def", 41),
    ]


def test_unseen_gaps_and_fragmented_headers_are_not_joined() -> None:
    spans = [
        _span("x.py", 20, "def"),
        _span("x.py", 22, "unobserved_name():"),
        _span("x.py", 30, "def observed("),
        _span("x.py", 80, "    async def second("),
    ]
    assert _locations(build_observed_source_index(spans)) == [
        ("x.py", "observed", "def", 30),
        ("x.py", "second", "async_def", 80),
    ]


@pytest.mark.parametrize("body", [
    '# def comment():\n"def string():"\ndef real():',
    'text = """\ndef quoted():\nclass AlsoQuoted:\n"""\ndef real():',
    'text = """\ndef quoted():\nclass AlsoQuoted:',
])
def test_visibly_opened_strings_and_comments_are_not_declarations(body: str) -> None:
    index = build_observed_source_index([_span("x.py", 1, body)])
    expected = ["real"] if body.endswith("def real():") else []
    assert [item["name"] for item in index["entries"]] == expected


def test_quoted_body_is_excluded_across_adjacent_delivered_spans() -> None:
    first = _span("x.py", 10, 'text = """')
    second = _span("x.py", 11, 'def quoted():\n"""\ndef real():')
    assert _locations(build_observed_source_index([second, first])) == [
        ("x.py", "real", "def", 13),
    ]


def test_fragment_may_have_unknown_enclosing_string_state_and_is_labelled() -> None:
    index = build_observed_source_index([_span("x.py", 100, "def possible_header():")])
    assert index["entries"][0]["start_line"] == 100
    assert "Lexical Python header candidates" in index["interpretation"]
    assert "unseen enclosing string state is unknown" in index["interpretation"]


@pytest.mark.parametrize("span", [
    {**_span("x.py", 1, "def incomplete():"), "end_line": 2},
    {**_span("x.py", 1, "def incomplete():"), "end_line": 0},
    {**_span("x.py", 1, "def incomplete():"), "start_line": True},
    {**_span("x.py", 1, "def incomplete():"), "content": None},
    {**_span("x.py", 1, "def incomplete():"), "file_hash": ""},
    _span("readme.md", 1, "def example():"),
])
def test_incomplete_or_non_python_evidence_is_not_indexed(span: dict) -> None:
    assert build_observed_source_index([span])["entries"] == []


def test_conflicting_observations_are_not_chosen_by_input_order() -> None:
    first = _span("x.py", 9, "def first():")
    second = _span("x.py", 9, "def second():")
    assert build_observed_source_index([first, second]) == build_observed_source_index(
        [second, first]
    )
    assert build_observed_source_index([first, second])["entries"] == []


def test_count_bound_prefers_editable_and_counts_all_omissions() -> None:
    spans = [_span(f"a{i:02}.py", 1, f"def item{i}():") for i in range(30)]
    spans.append(_span("z_edit.py", 5, "def editable():"))
    index = build_observed_source_index(spans, editable_paths=("z_edit.py",))
    assert len(index["entries"]) == OBSERVED_SOURCE_INDEX_ENTRIES
    assert index["entries"][0]["path"] == "z_edit.py"
    assert index["omitted_count"] == 31 - OBSERVED_SOURCE_INDEX_ENTRIES
    assert len(json.dumps(index, sort_keys=True)) <= OBSERVED_SOURCE_INDEX_CHARS


def test_character_bound_skips_oversized_metadata_without_truncating_names() -> None:
    too_long = "large_" + "x" * 5_000
    spans = [_span("a.py", 1, f"def {too_long}():"), _span("b.py", 3, "def fits():")]
    spans += [_span("long/" * 30 + f"c{i}.py", 2, f"def extra{i}():") for i in range(20)]
    index = build_observed_source_index(spans)
    assert len(json.dumps(index, sort_keys=True)) <= OBSERVED_SOURCE_INDEX_CHARS
    assert index["entries"][0]["name"] == "fits"
    assert index["omitted_count"] == len(spans) - len(index["entries"])
    assert too_long not in json.dumps(index)


def test_only_metadata_from_delivered_evidence_without_file_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("navigation must not read files")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    body = "def public_name():\n    secret_body_sentinel = 3"
    spans = [_span("public.py", 25, body)]
    original = copy.deepcopy(spans)
    result = build_observed_source_index(iter(spans))
    assert spans == original
    serialized = json.dumps(result)
    assert "secret_body_sentinel" not in serialized
    assert "span_id" not in serialized
    assert "public_name" in serialized
    assert result == build_observed_source_index(spans)


def test_crlf_and_unicode_names_keep_observed_line_numbers() -> None:
    body = "class Café:\r\n    def 수정(self):"
    index = build_observed_source_index([_span("types.pyi", 71, body)])
    assert _locations(index) == [
        ("types.pyi", "Café", "class", 71),
        ("types.pyi", "수정", "def", 72),
    ]


def test_final_observed_blank_line_does_not_hide_earlier_header() -> None:
    index = build_observed_source_index([_span("x.py", 11, "def present():\n")])
    assert _locations(index) == [("x.py", "present", "def", 11)]


@pytest.mark.parametrize("quote", ['"""', "'''", '"""  # may be a closing delimiter'])
def test_unknown_initial_bare_quote_does_not_hide_observed_real_headers(quote: str) -> None:
    body = (
        f"        Existing prose from an unseen opening literal.\n        {quote}\n"
        "        return old_value\n\n    def observed_wrapper(self):\n"
        '        """A later visible docstring.\n        More prose.\n        """\n'
        "        return self.helper()\n\n    async def another(self):"
    )
    index = build_observed_source_index([_span("public.py", 50, body)])
    assert _locations(index) == [
        ("public.py", "observed_wrapper", "def", 54),
        ("public.py", "another", "async_def", 60),
    ]
    assert "Ambiguous bare-quote fragments retain lexical candidates" in index["interpretation"]


def test_ambiguous_bare_opener_in_fragment_is_not_certified_as_code_or_string() -> None:
    fragment = _span("x.py", 50, '"""\ndef possible_only():\n"""')
    index = build_observed_source_index([fragment])
    assert _locations(index) == [("x.py", "possible_only", "def", 51)]
    assert "Not parsed symbols" in index["interpretation"]
    # At the actual file start the opening state is known; literal text is excluded.
    file_start = {**fragment, "start_line": 1, "end_line": 3}
    assert build_observed_source_index([file_start])["entries"] == []


def test_unambiguous_fragment_literal_still_excludes_quoted_headers() -> None:
    body = 'text = """\ndef quoted():\n"""\ndef observed():'
    index = build_observed_source_index([_span("x.py", 50, body)])
    assert _locations(index) == [("x.py", "observed", "def", 53)]


def test_fragment_with_bare_quote_and_no_later_quote_keeps_candidate() -> None:
    body = '    Earlier docstring text.\n    """\n    def candidate():'
    index = build_observed_source_index([_span("x.py", 50, body)])
    assert _locations(index) == [("x.py", "candidate", "def", 52)]
