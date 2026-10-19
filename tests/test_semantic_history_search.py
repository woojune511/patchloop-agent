from __future__ import annotations

import copy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from test_dev_history_search import items

from diagnostics.semantic_history_index import EvidenceHistory, separate
from diagnostics.semantic_history_search import fuse, ranked, windows
from patchloop.dev.history_search import PublicHistory
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json


def test_semantic_candidates_are_run_local_even_when_cache_contains_future_records():
    corpus = PublicHistory()
    for index, text in enumerate(("retry network", "connection is restored")):
        corpus.ingest(items(observation={"text": text}), sequence=index,
                      turn_id=str(index), input_hash=str(index))
    first, second = list(corpus.records)
    lexical, excerpts = corpus.rank("retry")
    # A semantic match with no shared keyword must be considered, but foreign keys cannot leak.
    dense = ranked(corpus.records, {first: .1, second: .9, "future-or-other-run": 1.0})
    assert [r["record_id"] for _, r in dense] == [second, first]
    hybrid = fuse(corpus.records, lexical, dense)
    assert hybrid[0][1]["record_id"] == first
    assert len(hybrid) == 2
    with patch.object(corpus, "rank", return_value=(dense, excerpts)):
        result = corpus.search("retry", current_diff_hash="current")
    assert result["records"][0]["body"] == corpus.records[second]["body"]
    assert all(r["delivery"] == "complete" for r in result["records"])


def test_every_overflow_window_is_used_and_silent_tail_truncation_fails():
    tail = SimpleNamespace(ids=[101, 22, 102], offsets=[(0, 0), (4, 9), (0, 0)])
    head = SimpleNamespace(ids=[101, 11, 102], offsets=[(0, 0), (0, 5), (0, 0)],
                           overflowing=[tail])
    tokenizer = SimpleNamespace(encode=lambda text: head)
    parts, spans = windows(tokenizer, "head tail")
    assert parts == [head, tail] and spans == [(0, 5), (4, 9)]
    head.overflowing = []
    with pytest.raises(ContractError, match="truncated"):
        windows(tokenizer, "head tail")


def test_ranking_change_keeps_whole_body_priority_and_same_eight_hit_result_budget():
    corpus = PublicHistory()
    for index in range(10):
        corpus.ingest(items(observation={"index": index, "text": "evidence " * 800}),
                      sequence=index, turn_id=str(index), input_hash=str(index))
    order = ranked(corpus.records, {key: float(i) for i, key in enumerate(corpus.records)})
    with patch.object(corpus, "rank", return_value=(order, {})):
        result = corpus.search("paraphrase", current_diff_hash="current")
    assert len(result["records"]) == 8 and len(canonical_json(result)) <= 48_000
    full = [r for r in result["records"] if r["delivery"] == "complete"]
    assert full and len(full) < 8
    assert all(r["body"] == corpus.records[r["record_id"]]["body"] for r in full)


def test_projection_moves_owned_annotations_reversibly_without_touching_execution():
    for tool, arguments, output in (
        ("read_file", {"path": "a.py"}, {
            "inspection_intent": {"plan_update": "unverified", "basis": "guess"},
            "inspection_intent_ref": {"action_id": "old"},
            "spans": [{"content": 'hypothesis = "keep this source"', "start_line": 3}]}),
        ("replace_text", {"path": "a.py", "old_text": "x", "new_text": "y",
                          "hypothesis": "guess", "expected_behavior": "hope",
                          "causal_revision": {"alternative_mechanism": "unconfirmed"}},
            {"mutation": {"hypothesis": "guess", "expected_behavior": "hope",
                          "changed_hunk": "-x\n+y"}, "mutation_evidence": {"content": "y"}}),
        ("run_probe", {"question": "Does it work?", "python_source": "assert dispatch(3) == 4"},
            {"question": "Does it work?", "stdout": '{"hypothesis":"actual captured value"}',
             "stderr": "", "exit_code": 1,
             "setup_checks": {"checks": [{"actual": "a", "expected": "b", "matched": False}]}}),
    ):
        body = {"call": {"tool": tool, "arguments": arguments},
                "result": {"output": output, "status": "succeeded"}}
        before = copy.deepcopy(body)
        split = separate(body)
        assert split["annotations"] and body == before
        restored = copy.deepcopy(split["observed"])
        for pointer, value in split["annotations"].items():
            path = pointer.strip("/").split("/")
            node = restored
            for part in path[:-1]:
                node = node[part]
            node[path[-1]] = value
        assert restored == body
        if tool == "read_file":
            assert split["observed"]["result"]["output"]["spans"] == output["spans"]
        if tool == "run_probe":
            assert split["observed"]["call"]["arguments"] == {
                "python_source": arguments["python_source"]}
            assert split["observed"]["result"]["output"]["stdout"] == output["stdout"]
            assert split["observed"]["result"]["output"]["setup_checks"] == output["setup_checks"]


def test_supplied_or_source_data_is_not_deleted_by_matching_key_names():
    body = {"field": "public_observation", "value": {"hypothesis": "a captured literal",
            "inspection_intent": {"plan_update": "a domain input"}, "source": True}}
    assert separate(body) == {"observed": body, "annotations": {}}


def test_clean_rank_ignores_intent_but_returns_original_body_and_excerpt_bytes():
    from test_dev_history_search import exchange

    history = EvidenceHistory()
    events = exchange(text="actual execution")
    result = json.loads(events[1]["output"])
    result["output"]["question"] = "unverifiedmotive"
    events[1]["output"] = canonical_json(result)
    history.ingest(items(exchanges=events), sequence=1, turn_id="old", input_hash="input")
    # Tool question is metadata; it cannot supply ranking support on its own.
    assert not history.search("unverifiedmotive", current_diff_hash="current")["records"]
    raw_order, raw_excerpts = PublicHistory.rank(history, "actual execution")
    order, excerpts = history.rank("actual execution")
    assert excerpts == raw_excerpts
    assert order[0][1] == raw_order[0][1]
    found = history.search("actual execution", current_diff_hash="current")["records"][0]
    assert found["body"]["result"]["output"]["question"] == "unverifiedmotive"
    assert found["delivery"] == "complete"
    assert sha256_json(found["body"]) == found["record_id"]
