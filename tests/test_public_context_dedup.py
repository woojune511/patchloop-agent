"""Lossless public-context representation, without model or target execution."""
from __future__ import annotations

from copy import deepcopy

import pytest

from diagnostics.public_context_dedup import deduplicate, expand, statistics


def source(start, end, *, lines=None, scope="repository", file_hash="sha256:pinned"):
    lines = lines if lines is not None else [f"source line {n}" for n in range(start, end + 1)]
    return {"path": "package/module.py", "file_hash": file_hash, "source_scope": scope,
            "start_line": start, "end_line": end, "content": "\n".join(lines),
            "read_only": scope != "repository"}


def test_overlapping_sources_are_printed_once_and_metadata_is_lossless():
    document = {"initial": [source(1, 90)], "current": [source(30, 60), source(85, 100)],
                "original_result": {"status": "failed", "F0010": True},
                "helper": {"path": ".", "exception": "ImportError", "result": None}}
    before = deepcopy(document)
    result = deduplicate(document)
    assert expand(result) == document == before
    assert result["sources"] == [{"id": "source_1", "source_scope": "repository",
        "path": "package/module.py", "file_hash": "sha256:pinned",
        "ranges": [{"start_line": 1, "end_line": 100,
                    "content": "\n".join(f"source line {n}" for n in range(1, 101))}]}]
    assert result["document"]["helper"] == document["helper"]
    assert statistics(result)["source_lines"] == 100


def test_repeated_large_values_keep_unique_negative_evidence():
    shared = {"program": "print('public diagnostic')\n" * 30, "outcome": "failed"}
    document = {"initial": deepcopy(shared), "handoff": deepcopy(shared),
                "unique_negative": {"call": "different", "stdout": "F0010", "supported": False}}
    result = deduplicate(document)
    assert result["definitions"]
    assert expand(result) == document
    counts = statistics(result)
    assert counts["deduplicated_json_chars"] < counts["original_json_chars"]
    assert result["document"]["unique_negative"] == document["unique_negative"]


def test_source_identity_and_gaps_remain_distinct():
    document = [source(1, 2), source(5, 6),
                source(1, 2, scope="dependency:caller", lines=["external", "source"]),
                source(1, 2, file_hash="sha256:other", lines=["different", "candidate"])]
    result = deduplicate(document)
    assert len(result["sources"]) == 3
    assert sum(len(item["ranges"]) for item in result["sources"]) == 4
    assert expand(result) == document


def test_conflicting_same_identity_line_is_rejected_without_mutation():
    document = [source(1, 2), source(2, 3, lines=["changed line", "source line 3"])]
    before = deepcopy(document)
    with pytest.raises(ValueError, match="conflicting"):
        deduplicate(document)
    assert document == before


@pytest.mark.parametrize("literal", [{"$ref": "value_1"},
                                    {"$source": "source_1", "start_line": 1, "end_line": 2},
                                    {"$literal": {"$ref": "value_1"}},
                                    {"$ref": "literal", "other": "unchanged"}])
def test_literal_reference_looking_values_round_trip(literal):
    document = {"literal": literal, "source": source(1, 2)}
    assert expand(deduplicate(document)) == document


def test_empty_lines_unicode_and_trailing_newline_survive():
    document = [source(1, 4, lines=["한국어", "", "return 1", ""])]
    assert expand(deduplicate(document)) == document


def test_repeated_large_literal_reference_objects_stay_literal():
    literal = {"$ref": "literal reference name " * 40,
               "$literal": {"$source": "not a source", "notes": "public note " * 50}}
    document = [deepcopy(literal), deepcopy(literal)]
    assert expand(deduplicate(document)) == document


def test_references_reject_missing_sources_and_cycles():
    result = deduplicate([source(1, 2)])
    result["document"][0]["content"]["end_line"] = 3
    with pytest.raises(ValueError, match="not covered"):
        expand(result)
    result = deduplicate({"data": "small"})
    result["document"] = {"$ref": "cycle"}
    result["definitions"] = {"cycle": {"$ref": "cycle"}}
    with pytest.raises(ValueError, match="cyclic"):
        expand(result)


def test_result_is_deterministic_and_independent_of_input_mutations():
    document = {"source": source(1, 2), "values": ["a", "b", None, True, 4, 1.25]}
    result = deduplicate(document)
    assert result == deduplicate(deepcopy(document))
    restored = expand(result)
    restored["values"].append("new")
    assert expand(result) == document
