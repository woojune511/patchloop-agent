"""Auditable weighted retrieval with threshold and no-match behavior."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from patchloop.contracts import (
    MemoryCondition,
    MemoryEntry,
    Phase,
    RetrievalCandidate,
    RetrievalDecision,
)
from patchloop.errors import ContractError
from patchloop.memory.store import EMBEDDING_MODEL, entry_embedding_text, latest_frozen_index
from patchloop.runtime import runtime_root
from patchloop.state import StateStore
from patchloop.util import canonical_json, sha256_text


def _tokens(text: str) -> Counter[str]:
    return Counter(re.findall(r"[a-z0-9_]+", text.lower()))


def _cosine(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(key, 0) for key, value in a.items())
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    return dot / (norm_a * norm_b)


_MODEL_CACHE: dict[str, object] = {}


def _query_embedding(query: str, revision: str) -> list[float]:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ContractError("install the memory extra with `uv sync --extra memory`") from exc
    if revision not in _MODEL_CACHE:
        _MODEL_CACHE[revision] = SentenceTransformer(
            EMBEDDING_MODEL,
            revision=revision,
            trust_remote_code=False,
        )
    model = _MODEL_CACHE[revision]
    vector = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0]
    return vector.tolist()


def _render_raw_trace(entry: MemoryEntry) -> str:
    state = StateStore(runtime_root() / "state.sqlite3")
    parts = []
    for source_run_id in entry.source_run_ids:
        if not state.has_run(source_run_id):
            continue
        events = state.list_events(source_run_id)
        parts.append(
            canonical_json(
                [
                    {
                        "sequence": event.sequence,
                        "type": event.type.value,
                        "actor": event.actor,
                        "payload": event.payload,
                    }
                    for event in events
                    if event.type.value
                    in {"PhaseChanged", "ToolCalled", "ToolFailed", "FailureTagged"}
                ]
            )
        )
    return "\n".join(parts)


def _estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


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
    if condition == MemoryCondition.NO_MEMORY:
        return "", None
    selected_path = Path(index_path) if index_path else latest_frozen_index()
    if selected_path is None or not selected_path.exists():
        decision = RetrievalDecision(
            run_id=run_id,
            index_version="none",
            query_hash=sha256_text(query),
            threshold=threshold,
            token_budget=token_budget,
            candidates=[],
            selected_memory_ids=[],
            no_match=True,
        )
        return "", decision
    raw = json.loads(selected_path.read_text(encoding="utf-8"))
    if raw.get("frozen") is not True:
        raise ContractError("memory retrieval requires a frozen index")
    build_contract = raw.get("build_contract", {})
    if (
        build_contract.get("schema_version")
        == "group-aware-memory-index-builder-d106-v1"
        and raw.get("authority", {}).get("retrieval_experiment_authorized") is not True
    ):
        raise ContractError(
            "D-106 group-aware index retrieval requires a later explicit authorization gate"
        )
    entries = [MemoryEntry.model_validate(item) for item in raw["entries"]]
    if entries and raw.get("embedding", {}).get("implementation") != "sentence-transformers":
        raise ContractError("frozen memory index lacks sentence-transformers vectors")
    query_vector = _query_embedding(query, raw["embedding"]["revision"]) if entries else []
    ranked = []
    for entry in entries:
        structured = entry_embedding_text(entry)
        rendered = (
            _render_raw_trace(entry) if condition == MemoryCondition.RAW_TRACE else structured
        )
        entry_vector = raw.get("embeddings", {}).get(entry.memory_id)
        if entry_vector is None:
            raise ContractError(f"missing embedding vector for memory: {entry.memory_id}")
        semantic = max(0.0, sum(a * b for a, b in zip(query_vector, entry_vector, strict=True)))
        class_match = _cosine(query, entry.failure_pattern.failure_class)
        phase_match = float(entry.failure_pattern.phase == phase)
        language_match = float("python" in entry.applicable_languages)
        validation = min(1.0, entry.validation_count / 3)
        score = (
            0.35 * semantic
            + 0.25 * class_match
            + 0.15 * phase_match
            + 0.15 * language_match
            + 0.10 * validation
        )
        ranked.append((score, entry, rendered, _estimate_tokens(rendered)))
    ranked.sort(key=lambda item: (-item[0], item[1].memory_id))
    selected_ids = []
    rendered_parts = []
    used = 0
    candidates = []
    for score, entry, rendered, tokens in ranked:
        threshold_pass = condition != MemoryCondition.SELECTIVE_STRUCTURED or score >= threshold
        fits = used + tokens <= token_budget
        selected = threshold_pass and fits
        if selected:
            selected_ids.append(entry.memory_id)
            rendered_parts.append(rendered)
            used += tokens
        candidates.append(
            RetrievalCandidate(
                memory_id=entry.memory_id,
                score=score,
                selected=selected,
                rendered_tokens=tokens,
            )
        )
    decision = RetrievalDecision(
        run_id=run_id,
        index_version=raw["index_version"],
        query_hash=sha256_text(canonical_json({"query": query, "phase": phase.value})),
        threshold=threshold,
        token_budget=token_budget,
        candidates=candidates,
        selected_memory_ids=selected_ids,
        no_match=not selected_ids,
    )
    return "\n\n---\n\n".join(rendered_parts), decision
