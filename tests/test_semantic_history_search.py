from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from test_dev_history_search import items

from diagnostics.semantic_history_search import fuse, ranked, windows
from patchloop.dev.history_search import PublicHistory
from patchloop.errors import ContractError
from patchloop.util import canonical_json


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
