"""Failure-memory construction, retrieval, rendering, and freeze gates."""

from __future__ import annotations

from pathlib import Path

from patchloop.contracts import MemoryCondition, Phase, RetrievalDecision

__all__ = ["retrieve_memory"]


def retrieve_memory(
    *,
    run_id: str,
    query: str,
    phase: Phase,
    condition: MemoryCondition,
    token_budget: int = 2000,
    threshold: float = 0.72,
    index_path: str | Path | None = None,
) -> tuple[str, RetrievalDecision | None]:
    """Load the retrieval implementation only when retrieval is requested."""

    from patchloop.memory.retrieval import retrieve_memory as _retrieve_memory

    return _retrieve_memory(
        run_id=run_id,
        query=query,
        phase=phase,
        condition=condition,
        token_budget=token_budget,
        threshold=threshold,
        index_path=index_path,
    )
