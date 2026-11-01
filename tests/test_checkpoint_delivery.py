"""Checkpoint references preserve public mutation feedback and visible source bytes."""

from __future__ import annotations

import copy
import json

import pytest

from diagnostics.checkpoint_delivery import expand_exchanges, project_exchanges
from patchloop.util import canonical_json, sha256_bytes


def case():
    lines = [f"line_{number:03d} = '{'public source ' * 8}'" for number in range(1, 81)]
    before = sha256_bytes("\n".join(lines).encode())
    after, diff = sha256_bytes(b"current file"), sha256_bytes(b"current diff")

    def span(start, end):
        return {"path": "src.py", "file_hash": before, "start_line": start, "end_line": end,
                "content": "\n".join(lines[start - 1:end])}

    evidence = {"saved_public_evidence": [
        {"initial_source": [span(1, 40), span(41, 80)]},
        {"state": {"current_sources": [span(25, 30)]}},
    ]}
    rebound = {**span(25, 65), "file_hash": after, "start_line": 27, "end_line": 67,
               "source_diff_hash": diff, "origin": "revalidated_after_mutation",
               "span_id": "current-rebound"}
    result = {"action_id": "edit", "input_hash": "input-identity", "tool": "replace_text",
              "status": "succeeded", "workspace_diff_hash": diff, "output": {
                  "worktree_diff_hash": diff, "revalidated_spans": [rebound],
                  "mutation_evidence": {"path": "src.py", "file_hash": after,
                      "start_line": 25, "end_line": 26, "content": "INSERTED = 1\nINSERTED = 2",
                      "origin": "accepted_mutation", "source_diff_hash": diff},
                  "original_recheck": {"status": "failed", "candidate_diff_hash": diff,
                      "observed": {"stdout": "F0010 remains", "exit_code": 1}},
                  "public_note": "A successful edit does not establish task correctness.",
              }}
    exchanges = [
        {"type": "function_call", "call_id": "edit", "name": "replace_text",
         "arguments": canonical_json({"path": "src.py", "old_text": "OLD", "new_text": "NEW"})},
        {"type": "function_call_output", "call_id": "edit", "output": canonical_json(result)},
    ]
    return evidence, exchanges


def output(exchanges):
    return json.loads(exchanges[-1]["output"])


def test_shifted_adjacent_source_union_roundtrips_without_changing_receipt_or_inputs():
    evidence, exchanges = case()
    originals = copy.deepcopy((evidence, exchanges))
    projected = project_exchanges(evidence, exchanges)
    old, new = output(exchanges), output(projected)
    old_span = old["output"]["revalidated_spans"][0]
    new_span = new["output"]["revalidated_spans"][0]
    assert "content" not in new_span
    assert {key: value for key, value in new_span.items() if key != "content_reference"} == {
        key: value for key, value in old_span.items() if key != "content"}
    reference = new_span["content_reference"]
    assert reference == {
        "document": "saved_public_evidence", "source_scope": "repository", "path": "src.py",
        "file_hash": evidence["saved_public_evidence"][0]["initial_source"][0]["file_hash"],
        "start_line": 25, "end_line": 65,
        "content_hash": sha256_bytes(old_span["content"].encode()),
    }
    assert reference["file_hash"] != new_span["file_hash"]
    assert new["output"]["mutation_evidence"] == old["output"]["mutation_evidence"]
    assert new["output"]["original_recheck"] == old["output"]["original_recheck"]
    assert new["output"]["public_note"] == old["output"]["public_note"]
    assert projected[0] == exchanges[0]
    assert [(item["type"], item["call_id"]) for item in projected] == [
        (item["type"], item["call_id"]) for item in exchanges]
    assert len(canonical_json(projected)) < len(canonical_json(exchanges))
    before_expansion = copy.deepcopy(projected)
    assert expand_exchanges(evidence, projected) == exchanges
    assert projected == before_expansion
    assert (evidence, exchanges) == originals


@pytest.mark.parametrize("change", [
    "mismatched", "wrong_scope", "unknown_path", "missing", "failed",
])
def test_missing_or_nonmatching_source_keeps_exact_inline_output(change):
    evidence, exchanges = case()
    result = output(exchanges)
    spans = evidence["saved_public_evidence"][0]["initial_source"]
    if change == "mismatched":
        spans[0]["content"] = spans[0]["content"].replace("line_031", "DIFFERENT_031")
    elif change == "wrong_scope":
        for body in evidence["saved_public_evidence"]:
            observed = body.get("initial_source", body.get("state", {}).get("current_sources", []))
            for span in observed:
                span["source_scope"] = "dependency:caller"
    elif change == "unknown_path":
        result["output"]["revalidated_spans"][0]["path"] = "unknown.py"
    elif change == "missing":
        evidence = {"saved_public_evidence": []}
    else:
        result["status"] = "failed"
    exchanges[-1]["output"] = canonical_json(result)
    assert project_exchanges(evidence, exchanges) == exchanges


def test_reference_that_would_be_larger_keeps_inline_source():
    evidence, exchanges = case()
    tiny = {"path": "tiny.py", "file_hash": "old-tiny", "start_line": 1,
            "end_line": 1, "content": "x = 1"}
    evidence = {"saved_public_evidence": [{"initial_source": [tiny]}]}
    result = output(exchanges)
    result["output"]["revalidated_spans"] = [{
        **tiny, "file_hash": "new-tiny", "origin": "revalidated_after_mutation",
        "source_diff_hash": result["workspace_diff_hash"],
    }]
    exchanges[-1]["output"] = canonical_json(result)
    assert project_exchanges(evidence, exchanges) == exchanges


def test_other_tools_and_nonrevalidated_spans_are_not_projected():
    evidence, exchanges = case()
    for tool, origin in (("read_file", "revalidated_after_mutation"),
                         ("run_probe", "revalidated_after_mutation"),
                         ("replace_text", "accepted_mutation")):
        changed = copy.deepcopy(exchanges)
        result = output(changed)
        result["tool"] = tool
        result["output"]["revalidated_spans"][0]["origin"] = origin
        changed[-1]["output"] = canonical_json(result)
        assert project_exchanges(evidence, changed) == changed


def test_expansion_rejects_a_reference_with_a_changed_content_hash():
    evidence, exchanges = case()
    projected = project_exchanges(evidence, exchanges)
    result = output(projected)
    result["output"]["revalidated_spans"][0]["content_reference"]["content_hash"] = (
        sha256_bytes(b"different source"))
    projected[-1]["output"] = canonical_json(result)
    with pytest.raises(ValueError, match="not covered by visible evidence"):
        expand_exchanges(evidence, projected)
