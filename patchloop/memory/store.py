"""Versioned memory indexes built only from reviewed dev-train failures."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from patchloop.contracts import DatasetRole, FailurePattern, FailureRecord, MemoryEntry
from patchloop.dataset import require_dataset_role, require_frozen_dataset
from patchloop.errors import ContractError, RecoveryError
from patchloop.evals.qualification import (
    calculate_source_evidence_hash,
    load_trace_qualification,
)
from patchloop.runtime import runtime_root
from patchloop.state import StateStore
from patchloop.util import canonical_json, sha256_bytes, sha256_text, utc_now

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _runtime_root(root: str | Path | None = None) -> Path:
    return Path(root) if root is not None else runtime_root()


def index_root(root: str | Path | None = None) -> Path:
    root = _runtime_root(root) / "memory" / "indexes"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _require_memory_source(
    record: FailureRecord,
    *,
    dataset_manifest_path: str | Path | None = None,
    root: str | Path | None = None,
) -> tuple[str, str, str, str]:
    source_root = _runtime_root(root)
    state = StateStore(source_root / "state.sqlite3")
    try:
        manifest = state.get_manifest(record.run_id)
    except RecoveryError as exc:
        raise ContractError(f"failure source run manifest is unavailable: {record.run_id}") from exc
    entry = require_dataset_role(
        task_id=manifest.task_id,
        task_version=manifest.task_version,
        public_spec_hash=manifest.public_spec_hash,
        allowed_roles={DatasetRole.MEMORY_DEVELOPMENT},
        manifest_path=dataset_manifest_path,
    )
    _, dataset_hash, _ = require_frozen_dataset(dataset_manifest_path)
    qualification = load_trace_qualification(record.run_id, root=source_root)
    if not qualification.get("qualified"):
        raise ContractError(f"failure source trace did not pass qualification: {record.run_id}")
    if not qualification.get("memory_candidate_eligible"):
        raise ContractError(
            f"failure source is not eligible for memory generation: {record.run_id}"
        )
    if qualification.get("failure_record_id") != record.failure_id:
        raise ContractError("trace qualification does not link this failure record")
    record_path = (
        source_root / "failures" / "dev-train" / f"{record.failure_id}.json"
    )
    if qualification.get("failure_record_hash") != sha256_bytes(record_path.read_bytes()):
        raise ContractError("failure record changed after trace qualification")
    if qualification.get("dataset_manifest_hash") != dataset_hash:
        raise ContractError("failure source run does not match the frozen dataset manifest")
    current_source_hash = calculate_source_evidence_hash(
        record.run_id,
        root=source_root,
    )
    if qualification.get("source_evidence_hash") != current_source_hash:
        raise ContractError("source evidence changed after trace qualification")
    return (
        entry.role.value,
        dataset_hash,
        str(qualification["qualification_hash"]),
        current_source_hash,
    )


def _review_history_path(failure_path: Path) -> Path:
    return failure_path.with_suffix(".review-history.jsonl")


def _review_history(failure_path: Path) -> list[dict]:
    path = _review_history_path(failure_path)
    if not path.is_file():
        return []
    history: list[dict] = []
    previous_hash: str | None = None
    expected_failure_id = failure_path.stem
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ContractError(
                f"invalid review history at {path.name}:{line_number}"
            ) from exc
        if not isinstance(item, dict):
            raise ContractError(f"invalid review history at {path.name}:{line_number}")
        recorded_hash = item.get("review_hash")
        unhashed = {key: value for key, value in item.items() if key != "review_hash"}
        if (
            item.get("schema_version") != "failure-review-v1"
            or item.get("failure_id") != expected_failure_id
            or item.get("previous_review_hash") != previous_hash
            or not isinstance(recorded_hash, str)
            or sha256_text(canonical_json(unhashed)) != recorded_hash
        ):
            raise ContractError(f"broken review history chain at {path.name}:{line_number}")
        history.append(item)
        previous_hash = recorded_hash
    return history


def review_failure(
    failure_id: str,
    *,
    split: str = "dev-train",
    approve: bool,
    reviewer: str = "human",
    dataset_manifest_path: str | Path | None = None,
    root: str | Path | None = None,
) -> dict:
    if split != "dev-train":
        raise ContractError("only dev-train failures may enter the memory review queue")
    source_root = _runtime_root(root)
    path = source_root / "failures" / split / f"{failure_id}.json"
    if not path.exists():
        raise ContractError(f"unknown failure record: {failure_id}")
    original = path.read_bytes()
    record = FailureRecord.model_validate_json(original)
    (
        dataset_role,
        dataset_manifest_hash,
        qualification_hash,
        source_evidence_hash,
    ) = _require_memory_source(
        record,
        dataset_manifest_path=dataset_manifest_path,
        root=source_root,
    )
    history = _review_history(path)
    audit: dict = {
        "schema_version": "failure-review-v1",
        "review_id": f"review_{uuid.uuid4().hex}",
        "failure_id": failure_id,
        "run_id": record.run_id,
        "decision": "reviewed" if approve else "rejected",
        "reviewer": reviewer,
        "reviewed_at": utc_now().isoformat(),
        "failure_record_hash": sha256_bytes(original),
        "qualification_hash": qualification_hash,
        "source_evidence_hash": source_evidence_hash,
        "dataset_role": dataset_role,
        "dataset_manifest_hash": dataset_manifest_hash,
        "previous_review_hash": (
            history[-1]["review_hash"] if history else None
        ),
    }
    audit["review_hash"] = sha256_text(canonical_json(audit))
    audit_path = _review_history_path(path)
    with audit_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(audit) + "\n")
    return {
        **audit,
        "record_path": str(path),
        "audit_path": str(audit_path),
        "history_length": len(history) + 1,
    }


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
        validation_count=0,
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
    split: str = "dev-train",
    embedding_revision: str | None = None,
    dataset_manifest_path: str | Path | None = None,
    root: str | Path | None = None,
) -> dict:
    if split != "dev-train":
        raise ContractError("memory entries may only be built from the dev-train split")
    source_root = _runtime_root(root)
    dataset, dataset_manifest_hash, _ = require_frozen_dataset(dataset_manifest_path)
    version = f"idx_{utc_now().strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    source_dir = source_root / "failures" / split
    entries: list[MemoryEntry] = []
    rejected = []
    for path in sorted(source_dir.glob("*.json")) if source_dir.exists() else []:
        record = FailureRecord.model_validate_json(path.read_text(encoding="utf-8"))
        history = _review_history(path)
        if not history or history[-1].get("decision") != "reviewed":
            rejected.append({"path": str(path), "reason": "not reviewed"})
            continue
        try:
            (
                dataset_role,
                source_dataset_hash,
                qualification_hash,
                source_evidence_hash,
            ) = _require_memory_source(
                record,
                dataset_manifest_path=dataset_manifest_path,
                root=source_root,
            )
        except ContractError as exc:
            rejected.append({"path": str(path), "reason": str(exc)})
            continue
        latest_review = history[-1]
        failure_record_hash = sha256_bytes(path.read_bytes())
        if (
            latest_review.get("failure_record_hash") != failure_record_hash
            or latest_review.get("qualification_hash") != qualification_hash
            or latest_review.get("source_evidence_hash") != source_evidence_hash
            or latest_review.get("dataset_role") != dataset_role
            or latest_review.get("dataset_manifest_hash") != source_dataset_hash
        ):
            rejected.append(
                {
                    "path": str(path),
                    "reason": "review provenance no longer matches the qualified source",
                }
            )
            continue
        entries.append(_entry_from_failure(record, version))
    embeddings = _build_embeddings(entries, embedding_revision)
    payload = {
        "schema_version": "memory-index-v1",
        "index_version": version,
        "split": split,
        "dataset_id": dataset.dataset_id,
        "dataset_manifest_hash": dataset_manifest_hash,
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
    directory = index_root(source_root) / version
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
    build_contract = payload.get("build_contract", {})
    if build_contract.get("schema_version") == "group-aware-memory-index-builder-d106-v1":
        raise ContractError(
            "D-106 group-aware index must use its exact candidate-bound freeze executor"
        )
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
