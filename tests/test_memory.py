from __future__ import annotations

import json

import pytest

from patchloop.contracts import MemoryCondition, Phase
from patchloop.errors import ContractError
from patchloop.memory import store as memory_store
from patchloop.memory.retrieval import retrieve_memory


def test_selective_memory_has_auditable_no_match(tmp_path) -> None:
    index = tmp_path / "index.json"
    index.write_text(
        json.dumps(
            {
                "index_version": "idx_test",
                "entries": [],
            }
        ),
        encoding="utf-8",
    )
    text, decision = retrieve_memory(
        run_id="run_test",
        query="quoted csv newline",
        phase=Phase.REPRODUCE,
        condition=MemoryCondition.SELECTIVE_STRUCTURED,
        index_path=index,
    )
    assert text == ""
    assert decision is not None and decision.no_match is True
    assert decision.selected_memory_ids == []


def test_empty_memory_index_cannot_be_frozen(tmp_path, monkeypatch) -> None:
    root = tmp_path / "indexes"
    index_dir = root / "idx_empty"
    index_dir.mkdir(parents=True)
    (index_dir / "index.json").write_text(
        json.dumps(
            {
                "index_version": "idx_empty",
                "entries": [],
                "embedding": {
                    "model": memory_store.EMBEDDING_MODEL,
                    "revision": "abc123",
                    "implementation": "empty-no-embedding",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(memory_store, "index_root", lambda: root)
    with pytest.raises(ContractError, match="empty"):
        memory_store.freeze_index("idx_empty", "abc123")
