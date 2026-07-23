"""Versioned memory indexes built only from reviewed dev-train failures."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from patchloop.contracts import FailurePattern, FailureRecord, MemoryEntry
from patchloop.errors import ContractError
from patchloop.runtime import runtime_root
from patchloop.util import canonical_json, sha256_text, utc_now

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def index_root() -> Path:
    root = runtime_root() / "memory" / "indexes"
    root.mkdir(parents=True, exist_ok=True)
    return root


def review_failure(
    failure_id: str,
    *,
    split: str = "dev-train",
    approve: bool,
    reviewer: str = "human",
) -> dict:
    if split != "dev-train":
        raise ContractError("only dev-train failures may enter the memory review queue")
    path = runtime_root() / "failures" / split / f"{failure_id}.json"
    if not path.exists():
        raise ContractError(f"unknown failure record: {failure_id}")
    original = path.read_bytes()
    record = FailureRecord.model_validate_json(original)
    record.review_status = "reviewed" if approve else "rejected"
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    audit = {
        "failure_id": failure_id,
        "decision": record.review_status,
        "reviewer": reviewer,
        "reviewed_at": utc_now().isoformat(),
        "pre_review_hash": sha256_text(original.decode("utf-8")),
        "post_review_hash": sha256_text(path.read_text(encoding="utf-8")),
    }
    audit_path = path.with_suffix(".review-audit")
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return {**audit, "record_path": str(path), "audit_path": str(audit_path)}


def _entry_from_failure(record: FailureRecord, version: str) -> MemoryEntry:
    symptoms = record.observed_symptoms or [record.primary_cause]
    return MemoryEntry(
        memory_id=f"mem_{uuid.uuid5(uuid.NAMESPACE_URL, record.failure_id).hex[:16]}",
        index_version=version,
        failure_pattern=FailurePattern(
            failure_class=record.primary_cause,
            phase=record.phase,
            description="; ".join(symptoms),
        ),
        preconditions=symptoms,
        diagnostic_evidence=[str(item) for item in record.evidence],
        recommended_actions=[
            "Check repository evidence for the "
            f"{record.primary_cause} failure pattern before editing."
        ],
        do_not_apply_when=["The current repository evidence does not match the recorded symptoms."],
        source_run_ids=[record.run_id],
        validation_count=1,
        confidence=record.confidence,
    )


def entry_embedding_text(entry: MemoryEntry) -> str:
    return (
        f"Failure class: {entry.failure_pattern.failure_class}\n"
        f"Pattern: {entry.failure_pattern.description}\n"
        f"Preconditions: {'; '.join(entry.preconditions)}\n"
        f"Recommended actions: {'; '.join(entry.recommended_actions)}\n"
        f"Do not apply when: {'; '.join(entry.do_not_apply_when)}"
    )


def _build_embeddings(entries: list[MemoryEntry], revision: str | None) -> dict[str, list[float]]:
    if not entries:
        return {}
    if not revision:
        raise ContractError("non-empty memory build requires --embedding-revision")
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ContractError("install the memory extra with `uv sync --extra memory`") from exc
    model = SentenceTransformer(
        EMBEDDING_MODEL,
        revision=revision,
        trust_remote_code=False,
    )
    vectors = model.encode(
        [entry_embedding_text(entry) for entry in entries],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return {
        entry.memory_id: vector.tolist() for entry, vector in zip(entries, vectors, strict=True)
    }


def _leak_scan(payload: str) -> list[str]:
    prohibited = ["reference.patch", "private.yaml", ".patchloop-hidden/", "hidden/test_"]
    return [token for token in prohibited if token.lower() in payload.lower()]


def build_index_from_failures(
    split: str = "dev-train", embedding_revision: str | None = None
) -> dict:
    if split != "dev-train":
        raise ContractError("memory entries may only be built from the dev-train split")
    version = f"idx_{utc_now().strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    source_dir = runtime_root() / "failures" / split
    entries: list[MemoryEntry] = []
    rejected = []
    for path in sorted(source_dir.glob("*.json")) if source_dir.exists() else []:
        record = FailureRecord.model_validate_json(path.read_text(encoding="utf-8"))
        if record.review_status != "reviewed":
            rejected.append({"path": str(path), "reason": "not reviewed"})
            continue
        entries.append(_entry_from_failure(record, version))
    embeddings = _build_embeddings(entries, embedding_revision)
    payload = {
        "schema_version": "memory-index-v1",
        "index_version": version,
        "split": split,
        "frozen": False,
        "embedding": {
            "model": EMBEDDING_MODEL,
            "revision": embedding_revision,
            "implementation": "sentence-transformers" if entries else "empty-no-embedding",
        },
        "embeddings": embeddings,
        "entries": [entry.model_dump(mode="json") for entry in entries],
        "rejected_sources": rejected,
    }
    leaks = _leak_scan(canonical_json(payload))
    if leaks:
        raise ContractError(f"memory leak scan failed: {', '.join(leaks)}")
    payload["content_hash"] = sha256_text(canonical_json(payload))
    directory = index_root() / version
    directory.mkdir(parents=True, exist_ok=False)
    index_path = directory / "index.json"
    index_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "index_id": version,
        "path": str(index_path),
        "entries": len(entries),
        "rejected": len(rejected),
        "leak_scan": "pass",
    }


def freeze_index(index_id: str, embedding_revision: str | None = None) -> dict:
    path = index_root() / index_id / "index.json"
    if not path.exists():
        raise ContractError(f"unknown memory index: {index_id}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload["entries"]:
        raise ContractError("cannot freeze an empty memory index")
    recorded_revision = payload["embedding"].get("revision")
    if embedding_revision and embedding_revision != recorded_revision:
        raise ContractError("freeze revision differs from the revision used to build embeddings")
    revision = payload["embedding"].get("revision")
    if not revision:
        raise ContractError("set an exact all-MiniLM-L6-v2 revision in index.json before freezing")
    if payload["embedding"].get("implementation") != "sentence-transformers":
        raise ContractError("memory index does not contain sentence-transformers vectors")
    if payload.get("frozen"):
        return {
            "index_id": index_id,
            "frozen": True,
            "content_hash": payload["content_hash"],
        }
    payload["frozen"] = True
    payload["frozen_at"] = utc_now().isoformat()
    payload["content_hash"] = sha256_text(
        canonical_json({key: value for key, value in payload.items() if key != "content_hash"})
    )
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (path.parent / "FROZEN").write_text(payload["content_hash"] + "\n", encoding="utf-8")
    return {
        "index_id": index_id,
        "frozen": True,
        "content_hash": payload["content_hash"],
    }


def latest_frozen_index() -> Path | None:
    candidates = sorted(path.parent for path in index_root().glob("*/FROZEN"))
    return candidates[-1] / "index.json" if candidates else None
