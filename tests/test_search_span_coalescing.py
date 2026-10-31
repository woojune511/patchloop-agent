"""Search output deduplicates selected lines without expanding the search budget."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from test_dev_dependency_tools import dependencies as dependencies
from test_dev_dependency_tools import rebuild
from test_dev_search_v16 import search_gateway as search_gateway
from test_dev_tools import inspection_decision

from patchloop.dev.contracts import RequestedTool
from patchloop.dev.dependency_sources import DependencySources
from patchloop.dev.tools import DevToolGateway
from patchloop.prepared_probe_dependencies import PreparedDependencies, read_descriptor
from patchloop.util import sha256_bytes, sha256_json


@pytest.fixture(params=["repository", "dependency:caller"])
def source_case(request, search_gateway, dependencies):
    """Use real tracked reads or pinned dependency reads, never import target code."""
    scope = request.param

    def configure(text):
        sources = None
        if scope == "repository":
            path = "root.py"
            (search_gateway.workspace / path).write_bytes(text.encode())
        else:
            _, directory = dependencies
            path = "caller/matches.py"
            (directory / path).write_bytes(text.encode())
            manifest = directory.parent / "prepared-probe-dependencies.json"
            descriptor = json.loads(manifest.read_bytes())
            descriptor["files"][path] = sha256_bytes(text.encode())
            descriptor["content_hash"] = sha256_json(descriptor["files"])
            manifest.write_text(json.dumps(descriptor), encoding="utf-8")
            prepared = PreparedDependencies(
                manifest, read_descriptor(manifest)[1], descriptor["repository_url"],
                descriptor["base_commit"], callers=("caller==1.2",),
            )
            sources = DependencySources(prepared, {"caller": "caller"})
        gateway = rebuild(search_gateway, sources)
        call = RequestedTool(
            name="search_files", action_id="selected-search",
            arguments={"query": "needle", "path_glob": path, "source_scope": scope},
            turn_decision=inspection_decision("selected-lines"),
        )
        return SimpleNamespace(
            gateway=gateway, sources=sources, call=call, path=path, text=text,
            key="spans" if scope == "repository" else "dependency_spans",
        )

    return configure


def source_payload(span):
    # Observation order can be added/promoted by execution and hydration; it is
    # not part of the source span's canonical identity or selected line payload.
    return {key: value for key, value in span.items() if key != "last_observed_seq"}


def assert_canonical_span(case, span, start, end, content):
    assert span["file_hash"] == sha256_bytes(case.text.encode())
    if case.sources is None:
        expected = DevToolGateway._span(case.path, start, end, content, span["file_hash"])
    else:
        _, provenance = case.sources.read("dependency:caller", case.path)
        expected = DevToolGateway._dependency_span(provenance, start, end, content)
    assert source_payload(span) == expected


def test_search_merges_overlap_preserving_matches_but_not_adjacent_windows(source_case):
    lines = [f"line {number:02d}" for number in range(1, 23)]
    for number in (4, 7, 15, 20):
        lines[number - 1] = f"needle {number:02d}"
    case = source_case("\n".join(lines) + "\n")
    result = case.gateway.execute(case.call)
    assert result.status == "succeeded", result.message
    assert result.output["searched_file_count"] == 1
    assert result.output["truncated"] is False
    spans = result.output[case.key]
    assert [(span["start_line"], span["end_line"]) for span in spans] == [
        (2, 9), (13, 17), (18, 22),
    ]
    for span in spans:
        start, end = span["start_line"], span["end_line"]
        assert_canonical_span(case, span, start, end, "\n".join(lines[start - 1:end]))
    displayed = "\n".join(span["content"] for span in spans)
    assert all(displayed.count(f"needle {number:02d}") == 1 for number in (4, 7, 15, 20))
    assert "line 10" not in displayed and "line 12" not in displayed


def test_dense_search_does_not_replenish_twenty_selected_windows(source_case):
    lines = [f"needle {number:02d}" for number in range(1, 36)]
    case = source_case("\n".join(lines) + "\n")
    result = case.gateway.execute(case.call)
    assert result.status == "succeeded", result.message
    assert result.output["searched_file_count"] == 1
    assert result.output["truncated"] is True
    # Twenty selected hit windows cover lines1..22. Deduplication cannot buy
    # additional hits/lines from the rest of the file.
    spans = result.output[case.key]
    assert len(spans) == 1
    assert_canonical_span(case, spans[0], 1, 22, "\n".join(lines[:22]))
    assert "needle 23" not in spans[0]["content"]
    if case.sources is not None:
        assert result.output["read_only"] is True
        assert case.gateway.context_spans() == []
        assert [source_payload(span) for span in case.gateway.dependency_context_spans()] == [
            source_payload(span) for span in spans
        ]


def test_character_limit_is_spent_before_overlap_is_removed(source_case):
    lines = [f"needle {number:02d} " + "x" * 3989 for number in range(1, 9)]
    assert all(len(line) == 3999 for line in lines)
    case = source_case("\n".join(lines) + "\n")
    result = case.gateway.execute(case.call)
    assert result.status == "succeeded", result.message
    assert result.output["truncated"] is True
    assert result.output["searched_file_count"] == 1
    # First window has11999 characters. The second clips to the same three
    # lines, spending23998 total; its freed space must not admit line4.
    spans = result.output[case.key]
    assert len(spans) == 1
    assert_canonical_span(case, spans[0], 1, 3, "\n".join(lines[:3]))
    assert len(spans[0]["content"]) == 11999
    assert "needle 04" not in spans[0]["content"]


def test_overlapping_windows_keep_normalized_eof_blank_lines(source_case):
    case = source_case("first\r\nneedle a\r\nneedle b\r\n\r\n\r\n")
    result = case.gateway.execute(case.call)
    assert result.status == "succeeded", result.message
    assert result.output["truncated"] is False
    spans = result.output[case.key]
    assert len(spans) == 1
    assert_canonical_span(case, spans[0], 1, 5, "first\nneedle a\nneedle b\n\n")


def test_merged_search_receipt_replays_and_hydrates_exact_source(source_case, monkeypatch):
    case = source_case("before\nneedle a\nneedle b\nafter\n")
    first = case.gateway.execute(case.call)
    assert first.status == "succeeded", first.message
    assert len(first.output[case.key]) == 1
    restarted = rebuild(case.gateway, case.sources)
    event_count = len(restarted.journal.events())
    original_search = restarted._search_files

    def no_search(*args, **kwargs):
        raise AssertionError("persisted same-diff source evidence must not be searched again")

    monkeypatch.setattr(restarted, "_search_files", no_search)
    replay = restarted.execute(case.call)
    assert replay.replayed is True
    assert replay.input_hash == first.input_hash
    assert replay.output == first.output
    assert len(restarted.journal.events()) == event_count
    retained = (restarted.context_spans() if case.sources is None
                else restarted.dependency_context_spans())
    expected = [source_payload(span) for span in first.output[case.key]]
    assert [source_payload(span) for span in retained] == expected
    if case.sources is not None:
        # Only repository reads use the same-diff inspection cache. Dependency
        # reads still revalidate their pinned source on a new action.
        monkeypatch.setattr(restarted, "_search_files", original_search)
    cached = restarted.execute(case.call.model_copy(update={"action_id": "cached-search"}))
    assert cached.status == "succeeded", cached.message
    assert cached.evidence_cache_hit is (case.sources is None)
    assert [source_payload(span) for span in cached.output[case.key]] == expected
    assert cached.output["searched_file_count"] == first.output["searched_file_count"]


@pytest.mark.parametrize(
    "identity", ["source_scope", "path", "file_hash", "provenance", "read_only"],
)
def test_overlap_never_crosses_source_identity_or_authority(identity):
    provenance = {
        "scope": "dependency:caller", "path": "caller/shared.py", "file_hash": "sha256:file",
        "manifest_hash": "sha256:manifest", "origin": "prepared_dependency",
    }
    first = DevToolGateway._dependency_span(provenance, 1, 3, "a\nb\nc")
    second = DevToolGateway._dependency_span(provenance, 2, 4, "b\nc\nd")
    second[identity] = (
        {**provenance, "manifest_hash": "sha256:other"} if identity == "provenance"
        else False if identity == "read_only" else "different-identity"
    )
    original = copy.deepcopy([first, second])
    assert DevToolGateway._coalesce_search_spans([first, second]) == original
    assert [first, second] == original


def test_nested_and_transitive_overlap_deduplicates_only_observed_lines():
    def span(start, end, text):
        return DevToolGateway._span("source.py", start, end, text, "sha256:file")

    selected = [span(1, 3, "a\nb\nc"), span(2, 2, "b"), span(3, 5, "c\nd\ne"),
                span(6, 6, "f"), span(8, 8, "h")]
    original = copy.deepcopy(selected)
    assert DevToolGateway._coalesce_search_spans(selected) == [
        span(1, 5, "a\nb\nc\nd\ne"), span(6, 6, "f"), span(8, 8, "h"),
    ]
    assert selected == original


def test_clipping_can_move_a_later_window_start_backwards():
    def span(start, end, text):
        return DevToolGateway._span("source.py", start, end, text, "sha256:file")

    selected = [span(1, 3, "a\nb\nc"), span(4, 4, "d"), span(3, 5, "c\nd\ne")]
    assert DevToolGateway._coalesce_search_spans(selected) == [span(1, 5, "a\nb\nc\nd\ne")]
