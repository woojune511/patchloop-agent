"""Execute the exact D-111-authorized local scoring diagnostic once.

D-112 is a read-only sidecar diagnostic.  It never calls the runtime retriever,
returns memory text, injects context, runs an agent, or changes the frozen score
policy.  The probe receipt is created exclusively before model loading and is
the irreversible one-use claim.  A claimed but incomplete execution is not
retried.
"""

from __future__ import annotations

import json
import math
import os
import re
import stat
import struct
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from patchloop.contracts import MemoryEntry, Phase, PublicTask
from patchloop.errors import ContractError
from patchloop.memory import d106_locked_group_index as d106
from patchloop.memory import d111_retrieval_readiness_authorization as d111
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-112"
PROBE_RECEIPT_SCHEMA_VERSION = "retrieval-readiness-scoring-diagnostic-receipt-d112-v1"
COMPLETION_GATE_SCHEMA_VERSION = "retrieval-readiness-scoring-diagnostic-completion-gate-d112-v1"

EXPECTED_CANDIDATE_ID = (
    "d111retrievalcandidate_bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a"
)
EXPECTED_CANDIDATE_BODY_SHA = (
    "sha256:bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a"
)
EXPECTED_CANDIDATE_BYTES = 6_465
EXPECTED_CANDIDATE_FILE_SHA = (
    "sha256:f91aa284cc7a2add2516f44b4397b29e3aee5caa4cf0f83ec7913e6e5d7899d6"
)
EXPECTED_ACTION_HASH = "sha256:4b94f6ba6d10a2e939e1f3dea9c9ce3d52a4cfafffa0fae68915b2287b1b449b"
EXPECTED_D111_GATE_ID = "d111_348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524"
EXPECTED_D111_GATE_BODY_SHA = (
    "sha256:348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524"
)
EXPECTED_D111_GATE_BYTES = 3_308
EXPECTED_D111_GATE_FILE_SHA = (
    "sha256:d550cb048e417965e482c64682df4a1b91b90067f66b36e370912f5a8d759c16"
)

APPROVAL_RECORDED_AT = "2026-08-06T16:41:32.316176Z"
APPROVAL_ACTION_ID = "d112-exact-d111-local-read-only-scoring-diagnostic-1"
APPROVAL_REFERENCE = "user-message:d111-exact-d112-scoring-diagnostic-approval"
APPROVAL_STATEMENT_CODE = "EXPLICITLY_APPROVE_D111_EXACT_D112_LOCAL_SCORING_ONCE"

DEFAULT_PROBE_RECEIPT_PATH = Path(
    "reports/memory-development/d112-retrieval-readiness-probe-receipt.json"
)
DEFAULT_COMPLETION_GATE_PATH = Path(
    "reports/memory-development/d112-retrieval-readiness-completion-gate.json"
)
DEFAULT_SNAPSHOT_DIRECTORY = d106.DEFAULT_SNAPSHOT_DIRECTORY

D112_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d112_retrieval_readiness_probe.py"),
    Path("scripts/run_d112_retrieval_readiness_probe.py"),
    Path("tests/test_d112_retrieval_readiness_probe.py"),
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")
_AUTHORIZED_SCOPE = {
    "action_schema_version": d111.PROBE_ACTION_SCHEMA_VERSION,
    "maximum_executions": 1,
    "automatic_retry_authorized": False,
    "local_embedding_model_load_count": 1,
    "local_batch_encode_call_count": 1,
    "local_batch_query_row_count": 3,
    "expected_query_vector_shape": [3, d106.VECTOR_DIMENSION],
    "expected_query_vector_dtype": d106.VECTOR_DTYPE,
    "device": "cpu",
    "local_files_only": True,
    "trust_remote_code": False,
    "network_access_authorized": False,
    "legacy_retrieve_memory_authorized": False,
    "memory_text_return_authorized": False,
    "runtime_memory_injection_authorized": False,
    "agent_context_rendering_authorized": False,
    "agent_run_authorized": False,
    "provider_calls_authorized": 0,
    "evaluator_calls_authorized": 0,
    "score_policy_change_authorized": False,
    "threshold_change_authorized": False,
    "memory_entry_change_authorized": False,
    "retrieval_experiment_authorized": False,
    "core_campaign_authorized": False,
    "analysis_campaign_authorized": False,
}


class D112ProbeError(ContractError):
    """Raised when the D-112 approval, inputs, execution, or evidence drift."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D112ProbeError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        return selected.resolve()
    except OSError as exc:
        raise D112ProbeError("D-112 repository root cannot be resolved") from exc


def _is_linklike(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse)


def _resolved(
    path: str | Path,
    *,
    repository: Path,
    label: str,
    must_exist: bool = True,
) -> Path:
    selected = Path(path)
    if not selected.is_absolute():
        selected = repository / selected
    try:
        resolved = selected.resolve(strict=must_exist)
        resolved.relative_to(repository)
    except (OSError, ValueError) as exc:
        raise D112ProbeError(f"D-112 {label} escapes the repository") from exc
    current = selected
    while current != repository and current != current.parent:
        _require(
            not _is_linklike(current),
            f"D-112 {label} cannot traverse a link or junction",
        )
        current = current.parent
    return resolved


def _read_stable(path: Path, *, label: str) -> bytes:
    _require(not _is_linklike(path), f"D-112 {label} cannot be a link or junction")
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except OSError as exc:
        raise D112ProbeError(f"D-112 {label} is unavailable") from exc
    _require(first == second, f"D-112 {label} changed while being read")
    return first


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D112ProbeError(f"D-112 {label} JSON is invalid") from exc
    _require(isinstance(payload, dict), f"D-112 {label} JSON root is invalid")
    return payload


def _pretty_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _validate_utc(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"D-112 {label} is invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise D112ProbeError(f"D-112 {label} is invalid") from exc
    _require(parsed.tzinfo is not None, f"D-112 {label} is not timezone-aware")
    return parsed


def _root_identity(
    payload: Mapping[str, Any],
    *,
    schema_version: str,
    id_field: str,
    id_prefix: str,
    label: str,
) -> None:
    _require(payload.get("schema_version") == schema_version, f"D-112 {label} schema drifted")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), f"D-112 {label} body is invalid")
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload.get("semantic_body_hash") == body_hash
        and payload.get(id_field) == f"{id_prefix}{body_hash.removeprefix('sha256:')}",
        f"D-112 {label} identity drifted",
    )


def _file_binding(path: Path, *, repository: Path, label: str) -> dict[str, Any]:
    selected = _resolved(path, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _write_new_fsynced(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _require(not _is_linklike(path.parent), "D-112 output parent cannot be a link or junction")
    try:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise D112ProbeError("D-112 one-use execution is already consumed") from exc
    except OSError as exc:
        raise D112ProbeError("D-112 output write failed") from exc


def _implementation_bindings(repository: Path) -> list[dict[str, Any]]:
    return [
        _file_binding(path, repository=repository, label="D-112 implementation")
        for path in D112_IMPLEMENTATION_PATHS
    ]


def _load_public_queries(repository: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    task_cache: dict[str, tuple[PublicTask, bytes]] = {}
    for spec in d111.PROBE_SPECS:
        task_id = str(spec["task_id"])
        if task_id not in task_cache:
            path = _resolved(spec["path"], repository=repository, label="public probe task")
            content = _read_stable(path, label="public probe task")
            _require(
                len(content) == spec["file_bytes"] and sha256_bytes(content) == spec["file_sha256"],
                f"D-112 public probe file drifted: {task_id}",
            )
            try:
                task = PublicTask.model_validate(yaml.safe_load(content.decode("utf-8")))
            except (UnicodeDecodeError, yaml.YAMLError, ValidationError) as exc:
                raise D112ProbeError(f"D-112 public probe is invalid: {task_id}") from exc
            task_cache[task_id] = (task, content)
        task, content = task_cache[task_id]
        query = task.issue.title + "\n" + task.issue.description + "\n" + " ".join(task.tags)
        phase = Phase(str(spec["phase"]))
        _require(
            sha256_text(query) == spec["runtime_query_sha256"]
            and sha256_text(canonical_json({"query": query, "phase": phase.value}))
            == spec["query_phase_sha256"],
            f"D-112 public query identity drifted: {spec['probe_id']}",
        )
        rows.append(
            {
                "probe_id": spec["probe_id"],
                "task_id": task_id,
                "phase": phase,
                "query": query,
                "query_bytes": len(query.encode("utf-8")),
                "query_sha256": spec["runtime_query_sha256"],
                "query_phase_sha256": spec["query_phase_sha256"],
                "public_task_file_bytes": len(content),
                "public_task_file_sha256": sha256_bytes(content),
                "hypothesis_kind": spec["hypothesis_kind"],
                "hypothesized_group_id": spec["hypothesized_group_id"],
            }
        )
    _require(
        [row["probe_id"] for row in rows] == [str(spec["probe_id"]) for spec in d111.PROBE_SPECS],
        "D-112 public probe order drifted",
    )
    return rows


def _render_bindings(index: Mapping[str, Any]) -> dict[str, Any]:
    model_text = index.get("model_facing_text")
    _require(isinstance(model_text, dict), "D-112 frozen model-facing text is invalid")
    rows: list[dict[str, Any]] = []
    texts: list[str] = []
    for memory_id in d111.EXPECTED_MEMORY_IDS:
        text = model_text.get(memory_id)
        _require(isinstance(text, str), "D-112 frozen model-facing text is missing")
        content = text.encode("ascii")
        texts.append(text)
        rows.append(
            {
                "memory_id": memory_id,
                "file_bytes": len(content),
                "file_sha256": sha256_bytes(content),
            }
        )
    bundle_text = "\n\n---\n\n".join(text.removesuffix("\n") for text in texts) + "\n"
    bundle = bundle_text.encode("ascii")
    _require(
        len(bundle) == d111.EXPECTED_MEMORY_BUNDLE_BYTES
        and sha256_bytes(bundle) == d111.EXPECTED_MEMORY_BUNDLE_SHA,
        "D-112 frozen model-facing bundle drifted",
    )
    return {
        "entries": rows,
        "bundle_bytes": len(bundle),
        "bundle_sha256": sha256_bytes(bundle),
        "text_included_in_evidence": False,
    }


def _load_exact_d111_context(repository: Path) -> dict[str, Any]:
    context = d111._load_exact_inputs(repository)
    gate = d111.validate_d111_source_gate(repository=repository, _context=context)
    _require(
        gate["gate_id"] == EXPECTED_D111_GATE_ID
        and gate["semantic_body_hash"] == EXPECTED_D111_GATE_BODY_SHA
        and gate["file_bytes"] == EXPECTED_D111_GATE_BYTES
        and gate["file_sha256"] == EXPECTED_D111_GATE_FILE_SHA
        and gate["candidate_id"] == EXPECTED_CANDIDATE_ID
        and gate["candidate_semantic_body_hash"] == EXPECTED_CANDIDATE_BODY_SHA
        and gate["candidate_file_bytes"] == EXPECTED_CANDIDATE_BYTES
        and gate["candidate_file_sha256"] == EXPECTED_CANDIDATE_FILE_SHA,
        "D-112 exact D-111 source gate drifted",
    )
    candidate_path = _resolved(
        d111.DEFAULT_CANDIDATE_PATH,
        repository=repository,
        label="D-111 candidate",
    )
    candidate_content = _read_stable(candidate_path, label="D-111 candidate")
    _require(
        len(candidate_content) == EXPECTED_CANDIDATE_BYTES
        and sha256_bytes(candidate_content) == EXPECTED_CANDIDATE_FILE_SHA,
        "D-112 D-111 candidate file drifted",
    )
    candidate = _parse_json(candidate_content, label="D-111 candidate")
    _require(
        candidate.get("candidate_id") == EXPECTED_CANDIDATE_ID
        and candidate.get("semantic_body_hash") == EXPECTED_CANDIDATE_BODY_SHA,
        "D-112 D-111 candidate identity drifted",
    )
    action = candidate["semantic_body"]["proposed_one_use_action"]
    _require(
        sha256_text(canonical_json(action)) == EXPECTED_ACTION_HASH,
        "D-112 proposed action drifted",
    )
    _require(
        action["maximum_executions"] == 1
        and action["automatic_retry_allowed"] is False
        and action["local_embedding_model_load_count"] == 1
        and action["local_batch_encode_call_count"] == 1
        and action["local_batch_query_row_count"] == 3
        and action["score_policy_correction_allowed"] is False
        and action["threshold_change_allowed"] is False
        and action["memory_entry_change_allowed"] is False
        and action["runtime_memory_injection_allowed"] is False
        and action["agent_run_allowed"] is False
        and action["provider_call_allowed"] is False
        and action["evaluator_call_allowed"] is False
        and action["core_campaign_allowed"] is False
        and action["analysis_campaign_allowed"] is False,
        "D-112 proposed action scope widened",
    )
    return {
        **context,
        "d111_gate_result": gate,
        "d111_gate_binding": {
            **_file_binding(
                d111.DEFAULT_SOURCE_GATE_PATH,
                repository=repository,
                label="D-111 source gate",
            ),
            "gate_id": EXPECTED_D111_GATE_ID,
            "semantic_body_hash": EXPECTED_D111_GATE_BODY_SHA,
        },
        "candidate": candidate,
        "candidate_binding": {
            **_file_binding(candidate_path, repository=repository, label="D-111 candidate"),
            "candidate_id": EXPECTED_CANDIDATE_ID,
            "semantic_body_hash": EXPECTED_CANDIDATE_BODY_SHA,
            "action_hash": EXPECTED_ACTION_HASH,
        },
        "render_bindings": _render_bindings(context["index"]),
        "queries": _load_public_queries(repository),
    }


def _snapshot_evidence(repository: Path) -> tuple[Path, dict[str, Any], dict[str, str]]:
    snapshot_path = _resolved(
        DEFAULT_SNAPSHOT_DIRECTORY,
        repository=repository,
        label="embedding snapshot",
    )
    try:
        snapshot = d106.validate_d106_snapshot_files(snapshot_path)
        dependencies = d106._installed_dependency_versions()
    except ContractError as exc:
        raise D112ProbeError("D-112 locked local embedding runtime drifted") from exc
    _require(
        snapshot["model_id"] == d111.EXPECTED_MODEL
        and snapshot["revision"] == d111.EXPECTED_MODEL_REVISION
        and snapshot["snapshot_manifest_hash"] == d111.EXPECTED_SNAPSHOT_MANIFEST_HASH
        and snapshot["required_file_count"] == len(d106.SNAPSHOT_FILES)
        and snapshot["safetensors_only"] is True,
        "D-112 embedding snapshot identity drifted",
    )
    _require(dependencies == d106.LOCKED_PACKAGES, "D-112 locked dependency versions drifted")
    return snapshot_path, snapshot, dependencies


def _snapshot_binding(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "model_id": snapshot["model_id"],
        "revision": snapshot["revision"],
        "snapshot_manifest_hash": snapshot["snapshot_manifest_hash"],
        "required_file_count": snapshot["required_file_count"],
        "files": [
            {
                "path": row["path"],
                "bytes": row["bytes"],
                "local_sha256": row["local_sha256"],
                "upstream_verification": row["upstream_verification"],
            }
            for row in snapshot["files"]
        ],
        "safetensors_only": snapshot["safetensors_only"],
    }


def _input_state(
    repository: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path, dict[str, str]]:
    context = _load_exact_d111_context(repository)
    snapshot_path, snapshot, dependencies = _snapshot_evidence(repository)
    queries = context["queries"]
    state = {
        "d111_source_gate": context["d111_gate_binding"],
        "d111_candidate": context["candidate_binding"],
        "d110_completion_gate": context["d110_gate"],
        "portable_frozen_index": context["index_binding"],
        "portable_frozen_marker": context["marker_binding"],
        "portable_d106_unfrozen_index": context["unfrozen_binding"],
        "frozen_model_facing_text": context["render_bindings"],
        "public_probes": [
            {
                key: row[key]
                for key in (
                    "probe_id",
                    "task_id",
                    "phase",
                    "query_bytes",
                    "query_sha256",
                    "query_phase_sha256",
                    "public_task_file_bytes",
                    "public_task_file_sha256",
                    "hypothesis_kind",
                    "hypothesized_group_id",
                )
            }
            | {"phase": row["phase"].value}
            for row in queries
        ],
        "embedding_snapshot": _snapshot_binding(snapshot),
        "locked_dependencies": dict(sorted(dependencies.items())),
        "implementation_files": _implementation_bindings(repository),
    }
    return (
        {
            "schema_version": "retrieval-readiness-scoring-input-state-d112-v1",
            "fingerprint": sha256_text(canonical_json(state)),
            "state": state,
        },
        context,
        snapshot_path,
        dependencies,
    )


def build_d112_probe_receipt(
    *,
    execution_claimed_at: str,
    input_state: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the immutable approval sidecar and one-use execution claim."""

    _validate_utc(execution_claimed_at, label="execution claim timestamp")
    _require(
        input_state.get("fingerprint") == sha256_text(canonical_json(input_state.get("state"))),
        "D-112 input fingerprint is invalid",
    )
    action = context["candidate"]["semantic_body"]["proposed_one_use_action"]
    _require(
        sha256_text(canonical_json(action)) == EXPECTED_ACTION_HASH,
        "D-112 authorized action drifted",
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "self-attested-approval-and-one-use-scoring-execution-claim",
        "approval_recorded_at": APPROVAL_RECORDED_AT,
        "execution_claimed_at": execution_claimed_at,
        "approval_action_id": APPROVAL_ACTION_ID,
        "approval_reference": APPROVAL_REFERENCE,
        "approval_reference_mode": "explicit-separate-message-exact-candidate-triple",
        "approval_statement_code": APPROVAL_STATEMENT_CODE,
        "d111_source_gate": context["d111_gate_binding"],
        "d111_candidate": context["candidate_binding"],
        "authorized_action_hash": EXPECTED_ACTION_HASH,
        "authorized_scope": dict(_AUTHORIZED_SCOPE),
        "probe_ids_in_order": [row["probe_id"] for row in d111.PROBE_SPECS],
        "pre_execution_input": dict(input_state),
        "claim_semantics": {
            "exclusive_create_and_fsync_required": True,
            "claim_created_before_model_load": True,
            "receipt_is_one_use_consumption_marker": True,
            "failure_or_hard_kill_remains_consumed": True,
            "automatic_retry_or_rollback_allowed": False,
            "completion_gate_required_for_success": True,
            "sidecar_does_not_modify_frozen_authority": True,
        },
        "self_attested": True,
        "approver_kind": "human",
        "approver_label": "chat-maintainer-self-attested",
        "reviewer_identity_authenticated": False,
        "cryptographic_signature_verified": False,
        "execution_result_present": False,
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": PROBE_RECEIPT_SCHEMA_VERSION,
        "receipt_id": f"d112probereceipt_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _tokens(text: str) -> Counter[str]:
    return Counter(_TOKEN_PATTERN.findall(text.lower()))


def _counter_cosine(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(key, 0) for key, value in a.items())
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    return dot / (norm_a * norm_b)


def _float32_bytes(row: Sequence[Any]) -> bytes:
    try:
        return b"".join(struct.pack("<f", float(value)) for value in row)
    except (OverflowError, TypeError, ValueError) as exc:
        raise D112ProbeError("D-112 query vector is not float32-compatible") from exc


def _validate_query_vectors(vectors: Any) -> tuple[list[list[float]], list[dict[str, Any]]]:
    shape = getattr(vectors, "shape", None)
    dtype = str(getattr(vectors, "dtype", ""))
    _require(dtype == d106.VECTOR_DTYPE, "D-112 query embedding dtype drifted")
    _require(
        tuple(shape) == (len(d111.PROBE_SPECS), d106.VECTOR_DIMENSION),
        "D-112 query embedding shape drifted",
    )
    rows = [[float(value) for value in row] for row in vectors]
    descriptors: list[dict[str, Any]] = []
    for probe, row in zip(d111.PROBE_SPECS, rows, strict=True):
        _require(len(row) == d106.VECTOR_DIMENSION, "D-112 query vector dimension drifted")
        _require(all(math.isfinite(value) for value in row), "D-112 query vector is not finite")
        norm = math.sqrt(sum(value * value for value in row))
        _require(abs(norm - 1.0) <= 1e-5, "D-112 query vector is not normalized")
        content = _float32_bytes(row)
        descriptors.append(
            {
                "probe_id": probe["probe_id"],
                "shape": [d106.VECTOR_DIMENSION],
                "dtype": d106.VECTOR_DTYPE,
                "l2_norm": norm,
                "float32_bytes": len(content),
                "float32_sha256": sha256_bytes(content),
                "vector": row,
            }
        )
    _require(
        descriptors[0]["float32_sha256"] == descriptors[2]["float32_sha256"] and rows[0] == rows[2],
        "D-112 identical Moto query vectors differ within the batch",
    )
    return rows, descriptors


def _validate_stored_vector(row: Any, *, memory_id: str) -> list[float]:
    _require(isinstance(row, list), f"D-112 stored vector is invalid: {memory_id}")
    values = [float(value) for value in row]
    _require(
        len(values) == d106.VECTOR_DIMENSION and all(math.isfinite(value) for value in values),
        f"D-112 stored vector shape drifted: {memory_id}",
    )
    norm = math.sqrt(sum(value * value for value in values))
    _require(abs(norm - 1.0) <= 1e-5, f"D-112 stored vector is not normalized: {memory_id}")
    return values


def _score_diagnostic(
    *,
    query_vectors: Sequence[Sequence[float]],
    queries: Sequence[Mapping[str, Any]],
    index: Mapping[str, Any],
) -> dict[str, Any]:
    entries = [MemoryEntry.model_validate(item) for item in index["entries"]]
    _require(
        [entry.memory_id for entry in entries] == list(d111.EXPECTED_MEMORY_IDS),
        "D-112 memory entry order drifted",
    )
    embeddings = index.get("embeddings")
    _require(isinstance(embeddings, dict), "D-112 stored embedding map is invalid")
    provenance = {row["memory_id"]: row["semantic_group_id"] for row in index["group_provenance"]}
    probe_results: list[dict[str, Any]] = []
    for query_vector, query in zip(query_vectors, queries, strict=True):
        candidates: list[dict[str, Any]] = []
        for entry in entries:
            entry_vector = _validate_stored_vector(
                embeddings.get(entry.memory_id), memory_id=entry.memory_id
            )
            semantic_raw = sum(
                left * right for left, right in zip(query_vector, entry_vector, strict=True)
            )
            semantic = max(0.0, semantic_raw)
            class_match = _counter_cosine(str(query["query"]), entry.failure_pattern.failure_class)
            phase_match = float(entry.failure_pattern.phase == query["phase"])
            language_match = float("python" in entry.applicable_languages)
            validation = min(1.0, entry.validation_count / 3)
            components = {
                "semantic": semantic,
                "failure_class": class_match,
                "phase": phase_match,
                "language": language_match,
                "validation": validation,
            }
            weighted = {key: d111.SCORE_WEIGHTS[key] * value for key, value in components.items()}
            final_score = sum(weighted[key] for key in d111.SCORE_WEIGHTS)
            candidates.append(
                {
                    "memory_id": entry.memory_id,
                    "semantic_group_id": provenance[entry.memory_id],
                    "failure_class": entry.failure_pattern.failure_class,
                    "entry_phase": entry.failure_pattern.phase.value,
                    "semantic_raw_dot": semantic_raw,
                    "components": components,
                    "weighted_components": weighted,
                    "final_score": final_score,
                    "threshold": d111.SELECTIVE_THRESHOLD,
                    "threshold_comparator": "greater-than-or-equal",
                    "diagnostic_threshold_pass": final_score >= d111.SELECTIVE_THRESHOLD,
                }
            )
        candidates.sort(key=lambda row: (-row["final_score"], row["memory_id"]))
        for rank, candidate in enumerate(candidates, start=1):
            candidate["rank"] = rank
        passing = [row["memory_id"] for row in candidates if row["diagnostic_threshold_pass"]]
        probe_results.append(
            {
                "probe_id": query["probe_id"],
                "task_id": query["task_id"],
                "phase": query["phase"].value,
                "query_bytes": query["query_bytes"],
                "query_sha256": query["query_sha256"],
                "query_phase_sha256": query["query_phase_sha256"],
                "hypothesis_kind": query["hypothesis_kind"],
                "hypothesized_group_id": query["hypothesized_group_id"],
                "hypothesis_is_acceptance_criterion": False,
                "observed_top_memory_id": candidates[0]["memory_id"],
                "observed_top_group_id": candidates[0]["semantic_group_id"],
                "hypothesis_agrees_with_top_group": (
                    query["hypothesized_group_id"] is not None
                    and query["hypothesized_group_id"] == candidates[0]["semantic_group_id"]
                ),
                "candidates": candidates,
                "diagnostic_threshold_passing_memory_ids": passing,
                "diagnostic_no_match": not passing,
                "runtime_selection_executed": False,
                "memory_text_returned": False,
            }
        )
    _require(
        len(probe_results) == 3 and all(len(row["candidates"]) == 3 for row in probe_results),
        "D-112 scoring matrix shape drifted",
    )
    implement = {row["memory_id"]: row for row in probe_results[0]["candidates"]}
    reproduce = {row["memory_id"]: row for row in probe_results[2]["candidates"]}
    phase_deltas = {
        memory_id: implement[memory_id]["final_score"] - reproduce[memory_id]["final_score"]
        for memory_id in d111.EXPECTED_MEMORY_IDS
    }
    _require(
        all(
            math.isclose(delta, 0.15, rel_tol=0.0, abs_tol=1e-12) for delta in phase_deltas.values()
        ),
        "D-112 Moto phase-control score delta drifted",
    )
    return {
        "scoring_contract": context_scoring_contract(),
        "probe_results": probe_results,
        "score_row_count": 9,
        "all_diagnostic_no_match": all(row["diagnostic_no_match"] for row in probe_results),
        "moto_phase_control_score_deltas": phase_deltas,
        "moto_phase_control_expected_delta": 0.15,
        "runtime_selection_executed": False,
        "memory_text_returned": False,
    }


def context_scoring_contract() -> dict[str, Any]:
    return {
        "query_text": "public-title-newline-description-newline-space-joined-tags",
        "semantic_component": "max-zero-normalized-query-vector-dot-frozen-entry-vector",
        "failure_class_tokenizer_regex": "[a-z0-9_]+",
        "failure_class_component": "counter-cosine-public-query-vs-entry-failure-class",
        "phase_component": "float-entry-phase-equals-probe-phase",
        "language_component": "float-python-in-entry-applicable-languages",
        "validation_component": "min-one-entry-validation-count-divided-by-three",
        "score_weights": dict(d111.SCORE_WEIGHTS),
        "selective_threshold": d111.SELECTIVE_THRESHOLD,
        "selective_comparator": "greater-than-or-equal",
        "rank_order": "descending-score-then-ascending-memory-id",
        "scoring_policy_changed": False,
    }


@contextmanager
def _offline_library_environment() -> Iterator[None]:
    selected = {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
    }
    previous = {key: os.environ.get(key) for key in selected}
    os.environ.update(selected)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _default_model_loader(snapshot_path: Path, config: Mapping[str, Any]) -> Any:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise D112ProbeError("D-112 sentence-transformers runtime is unavailable") from exc
    with _offline_library_environment():
        return SentenceTransformer(
            str(snapshot_path),
            device=config["device"],
            trust_remote_code=config["trust_remote_code"],
            local_files_only=config["local_files_only"],
        )


def _default_batch_encoder(
    model: Any,
    texts: Sequence[str],
    config: Mapping[str, Any],
) -> Any:
    try:
        dimension = int(model.get_sentence_embedding_dimension())
    except (AttributeError, TypeError, ValueError) as exc:
        raise D112ProbeError("D-112 embedding dimension API is unavailable") from exc
    _require(dimension == d106.VECTOR_DIMENSION, "D-112 embedding dimension drifted")
    with _offline_library_environment():
        return model.encode(
            list(texts),
            normalize_embeddings=config["normalize_embeddings"],
            convert_to_numpy=config["convert_to_numpy"],
            show_progress_bar=config["show_progress_bar"],
        )


def _embedding_config() -> dict[str, Any]:
    return {
        "model": d111.EXPECTED_MODEL,
        "revision": d111.EXPECTED_MODEL_REVISION,
        "snapshot_manifest_hash": d111.EXPECTED_SNAPSHOT_MANIFEST_HASH,
        "device": "cpu",
        "trust_remote_code": False,
        "local_files_only": True,
        "library_offline_environment": {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
        },
        "os_socket_block_verified": False,
        "normalize_embeddings": True,
        "convert_to_numpy": True,
        "show_progress_bar": False,
    }


def build_d112_completion_gate(
    *,
    completed_at: str,
    probe_receipt_binding: Mapping[str, Any],
    pre_input: Mapping[str, Any],
    post_input: Mapping[str, Any],
    embedding_execution: Mapping[str, Any],
    query_vectors: Sequence[Mapping[str, Any]],
    scoring: Mapping[str, Any],
    implementation_bindings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    _validate_utc(completed_at, label="completion timestamp")
    _require(pre_input == post_input, "D-112 immutable input changed during execution")
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "local-read-only-scoring-diagnostic-completion-gate",
        "recorded_at": completed_at,
        "probe_receipt": dict(probe_receipt_binding),
        "input_integrity": {
            "pre_execution": dict(pre_input),
            "post_execution": dict(post_input),
            "fingerprints_equal": True,
        },
        "embedding_execution": dict(embedding_execution),
        "query_vectors": [dict(row) for row in query_vectors],
        "diagnostic_scoring": dict(scoring),
        "implementation_files": [dict(row) for row in implementation_bindings],
        "qualification": {
            "exact_candidate_and_user_approval_bound": True,
            "one_use_receipt_consumed_before_model_load": True,
            "local_embedding_model_load_count_exact": True,
            "local_batch_encode_call_count_exact": True,
            "ordered_three_public_queries_encoded": True,
            "query_vector_shape_dtype_finite_normalized": True,
            "all_nine_component_and_final_score_rows_recorded": True,
            "rank_and_threshold_recomputed_portably": True,
            "identical_moto_query_vectors_equal": True,
            "moto_phase_control_delta_valid": True,
            "probe_hypotheses_used_as_acceptance_criteria": False,
            "runtime_selection_executed": False,
            "memory_text_returned_or_injected": False,
            "pre_and_post_input_fingerprints_equal": True,
        },
        "evidence_boundary": {
            "public_spec_only": True,
            "private_hidden_reference_or_known_bad_read": False,
            "raw_trace_read": False,
            "legacy_retrieve_memory_calls": 0,
            "runtime_memory_injection_count": 0,
            "agent_context_render_calls": 0,
            "agent_runs": 0,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
            "network_access_authorized": False,
            "library_offline_and_local_files_only_enforced": True,
            "os_level_network_block_verified": False,
            "frozen_index_or_marker_mutated": False,
            "d106_unfrozen_index_mutated": False,
            "score_policy_or_threshold_mutated": False,
        },
        "authority": {
            "exact_candidate_user_approval_received": True,
            "local_scoring_diagnostic_authorized": True,
            "local_scoring_diagnostic_executed": True,
            "retrieval_probe_authorized": True,
            "retrieval_probe_executed": True,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "raw_trace_ready": False,
            "four_condition_retrieval_ready": False,
            "score_policy_correction_authorized": False,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "memory_effect_established": False,
            "negative_transfer_established": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": "separate-offline-score-policy-decision-candidate",
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": COMPLETION_GATE_SCHEMA_VERSION,
        "gate_id": f"d112_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def preflight_d112_execution(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Validate all no-load inputs without consuming the one-use claim."""

    repo = _repo_root(repository)
    receipt_path = _resolved(
        DEFAULT_PROBE_RECEIPT_PATH,
        repository=repo,
        label="probe receipt",
        must_exist=False,
    )
    gate_path = _resolved(
        DEFAULT_COMPLETION_GATE_PATH,
        repository=repo,
        label="completion gate",
        must_exist=False,
    )
    _require(not receipt_path.exists(), "D-112 one-use execution is already consumed")
    _require(not gate_path.exists(), "D-112 completion gate exists without a fresh claim")
    input_state, _context, _snapshot_path, _dependencies = _input_state(repo)
    return {
        "ok": True,
        "input_fingerprint": input_state["fingerprint"],
        "exact_candidate_user_approval_received": True,
        "one_use_execution_available": True,
        "model_loaded": False,
        "query_encoded": False,
        "retrieval_called": False,
        "runtime_memory_injection_count": 0,
        "agent_runs": 0,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "core_campaign_unlocked": False,
    }


def _receipt_binding(
    path: Path,
    payload: Mapping[str, Any],
    *,
    repository: Path,
) -> dict[str, Any]:
    return {
        **_file_binding(path, repository=repository, label="D-112 probe receipt"),
        "schema_version": payload["schema_version"],
        "receipt_id": payload["receipt_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
    }


def execute_d112_scoring_diagnostic(
    *,
    repository: str | Path | None = None,
    model_loader: Callable[[Path, Mapping[str, Any]], Any] | None = None,
    batch_encoder: Callable[[Any, Sequence[str], Mapping[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    """Consume the exact approval and run one local three-row scoring diagnostic."""

    repo = _repo_root(repository)
    receipt_path = _resolved(
        DEFAULT_PROBE_RECEIPT_PATH,
        repository=repo,
        label="probe receipt",
        must_exist=False,
    )
    gate_path = _resolved(
        DEFAULT_COMPLETION_GATE_PATH,
        repository=repo,
        label="completion gate",
        must_exist=False,
    )
    _require(not receipt_path.exists(), "D-112 one-use execution is already consumed")
    _require(not gate_path.exists(), "D-112 completion gate exists before execution")

    pre_input, context, snapshot_path, dependencies = _input_state(repo)
    claimed_at = _utc_now()
    receipt = build_d112_probe_receipt(
        execution_claimed_at=claimed_at,
        input_state=pre_input,
        context=context,
    )
    _write_new_fsynced(receipt_path, _pretty_json(receipt))
    receipt_binding = _receipt_binding(receipt_path, receipt, repository=repo)

    stage = "local-model-load"
    load_count = 0
    encode_count = 0
    config = _embedding_config()
    try:
        loader = model_loader or _default_model_loader
        encoder = batch_encoder or _default_batch_encoder
        model = loader(snapshot_path, config)
        load_count += 1
        _require(load_count == 1, "D-112 model load count drifted")

        stage = "ordered-batch-encode"
        query_texts = [row["query"] for row in context["queries"]]
        vectors = encoder(model, query_texts, config)
        encode_count += 1
        _require(encode_count == 1, "D-112 batch encode count drifted")
        vector_rows, vector_descriptors = _validate_query_vectors(vectors)

        stage = "diagnostic-score-computation"
        scoring = _score_diagnostic(
            query_vectors=vector_rows,
            queries=context["queries"],
            index=context["index"],
        )

        stage = "post-input-integrity"
        post_input, _post_context, _post_snapshot_path, post_dependencies = _input_state(repo)
        _require(pre_input == post_input, "D-112 immutable input changed during execution")
        _require(
            dependencies == post_dependencies,
            "D-112 dependency state changed during execution",
        )

        stage = "completion-gate-commit"
        embedding_execution = {
            "config": config,
            "model_load_count": load_count,
            "batch_encode_call_count": encode_count,
            "batch_query_row_count": len(query_texts),
            "query_vector_shape": [len(vector_rows), d106.VECTOR_DIMENSION],
            "query_vector_dtype": d106.VECTOR_DTYPE,
            "finite_normalized_query_vectors": True,
            "snapshot_path": snapshot_path.relative_to(repo).as_posix(),
            "locked_dependencies": dict(sorted(dependencies.items())),
            "provider_or_network_model_call_count": 0,
        }
        gate = build_d112_completion_gate(
            completed_at=_utc_now(),
            probe_receipt_binding=receipt_binding,
            pre_input=pre_input,
            post_input=post_input,
            embedding_execution=embedding_execution,
            query_vectors=vector_descriptors,
            scoring=scoring,
            implementation_bindings=_implementation_bindings(repo),
        )
        _write_new_fsynced(gate_path, _pretty_json(gate))
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise D112ProbeError(
            f"D-112 one-use execution failed after claim at stage {stage}; retry is closed"
        ) from exc

    validation = validate_d112_completion_gate(
        repository=repo,
        verify_current_implementation=True,
        verify_current_inputs=True,
    )
    return {
        **validation,
        "execution_claimed_at": claimed_at,
        "model_load_count": load_count,
        "batch_encode_call_count": encode_count,
        "retrieval_called": False,
        "memory_text_returned": False,
        "runtime_memory_injection_count": 0,
        "agent_runs": 0,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "added_model_cost_usd": 0,
    }


def validate_d112_probe_receipt(
    receipt_path: str | Path = DEFAULT_PROBE_RECEIPT_PATH,
    *,
    repository: str | Path | None = None,
    current_input: Mapping[str, Any] | None = None,
    current_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(receipt_path, repository=repo, label="probe receipt")
    content = _read_stable(selected, label="probe receipt")
    payload = _parse_json(content, label="probe receipt")
    _root_identity(
        payload,
        schema_version=PROBE_RECEIPT_SCHEMA_VERSION,
        id_field="receipt_id",
        id_prefix="d112probereceipt_",
        label="probe receipt",
    )
    _require(content == _pretty_json(payload), "D-112 probe receipt is not canonical")
    body = payload["semantic_body"]
    _validate_utc(body.get("approval_recorded_at"), label="approval timestamp")
    _validate_utc(body.get("execution_claimed_at"), label="execution claim timestamp")
    _require(
        body.get("approval_recorded_at") == APPROVAL_RECORDED_AT
        and body.get("approval_action_id") == APPROVAL_ACTION_ID
        and body.get("approval_reference") == APPROVAL_REFERENCE
        and body.get("approval_statement_code") == APPROVAL_STATEMENT_CODE
        and body.get("authorized_action_hash") == EXPECTED_ACTION_HASH
        and body.get("authorized_scope") == _AUTHORIZED_SCOPE
        and body.get("probe_ids_in_order") == [row["probe_id"] for row in d111.PROBE_SPECS]
        and body.get("self_attested") is True
        and body.get("reviewer_identity_authenticated") is False
        and body.get("cryptographic_signature_verified") is False
        and body.get("execution_result_present") is False,
        "D-112 probe receipt approval scope drifted",
    )
    context = dict(current_context) if current_context is not None else None
    input_state = dict(current_input) if current_input is not None else None
    if context is None or input_state is None:
        input_state, context, _snapshot, _dependencies = _input_state(repo)
    _require(
        body.get("d111_source_gate") == context["d111_gate_binding"]
        and body.get("d111_candidate") == context["candidate_binding"]
        and body.get("pre_execution_input") == input_state,
        "D-112 probe receipt input binding drifted",
    )
    claim = body.get("claim_semantics")
    _require(
        isinstance(claim, dict)
        and claim.get("exclusive_create_and_fsync_required") is True
        and claim.get("claim_created_before_model_load") is True
        and claim.get("failure_or_hard_kill_remains_consumed") is True
        and claim.get("automatic_retry_or_rollback_allowed") is False
        and claim.get("sidecar_does_not_modify_frozen_authority") is True,
        "D-112 one-use claim semantics drifted",
    )
    return {
        **_receipt_binding(selected, payload, repository=repo),
        "self_attested": True,
        "reviewer_identity_authenticated": False,
        "cryptographic_signature_verified": False,
        "execution_claimed_at": body["execution_claimed_at"],
        "input_fingerprint": input_state["fingerprint"],
    }


def _vectors_from_gate(rows: Any) -> tuple[list[list[float]], list[dict[str, Any]]]:
    _require(isinstance(rows, list) and len(rows) == 3, "D-112 query vector rows are invalid")
    vectors: list[list[float]] = []
    normalized_rows: list[dict[str, Any]] = []
    for probe, descriptor in zip(d111.PROBE_SPECS, rows, strict=True):
        _require(isinstance(descriptor, dict), "D-112 query vector descriptor is invalid")
        vector = descriptor.get("vector")
        _require(isinstance(vector, list), "D-112 portable query vector is missing")
        values = [float(value) for value in vector]
        _require(
            descriptor.get("probe_id") == probe["probe_id"]
            and descriptor.get("shape") == [d106.VECTOR_DIMENSION]
            and descriptor.get("dtype") == d106.VECTOR_DTYPE
            and len(values) == d106.VECTOR_DIMENSION
            and all(math.isfinite(value) for value in values),
            "D-112 portable query vector shape drifted",
        )
        norm = math.sqrt(sum(value * value for value in values))
        content = _float32_bytes(values)
        _require(
            abs(norm - 1.0) <= 1e-5
            and descriptor.get("l2_norm") == norm
            and descriptor.get("float32_bytes") == len(content)
            and descriptor.get("float32_sha256") == sha256_bytes(content),
            "D-112 portable query vector integrity drifted",
        )
        vectors.append(values)
        normalized_rows.append(dict(descriptor))
    _require(
        vectors[0] == vectors[2]
        and normalized_rows[0]["float32_sha256"] == normalized_rows[2]["float32_sha256"],
        "D-112 portable Moto query vectors differ",
    )
    return vectors, normalized_rows


def validate_d112_completion_gate(
    gate_path: str | Path = DEFAULT_COMPLETION_GATE_PATH,
    *,
    repository: str | Path | None = None,
    verify_current_implementation: bool = False,
    verify_current_inputs: bool = True,
) -> dict[str, Any]:
    """Validate D-112 offline; this function never reloads or re-encodes the model."""

    repo = _repo_root(repository)
    current_input, context, _snapshot_path, dependencies = _input_state(repo)
    receipt = validate_d112_probe_receipt(
        repository=repo,
        current_input=current_input,
        current_context=context,
    )
    receipt_binding = {
        key: receipt[key]
        for key in (
            "path",
            "file_bytes",
            "file_sha256",
            "schema_version",
            "receipt_id",
            "semantic_body_hash",
        )
    }
    selected = _resolved(gate_path, repository=repo, label="completion gate")
    content = _read_stable(selected, label="completion gate")
    gate = _parse_json(content, label="completion gate")
    _root_identity(
        gate,
        schema_version=COMPLETION_GATE_SCHEMA_VERSION,
        id_field="gate_id",
        id_prefix="d112_",
        label="completion gate",
    )
    _require(content == _pretty_json(gate), "D-112 completion gate is not canonical")
    body = gate["semantic_body"]
    _validate_utc(body.get("recorded_at"), label="completion timestamp")
    integrity = body.get("input_integrity")
    _require(isinstance(integrity, dict), "D-112 input integrity evidence is invalid")
    pre_input = integrity.get("pre_execution")
    post_input = integrity.get("post_execution")
    _require(
        isinstance(pre_input, dict)
        and pre_input == post_input
        and integrity.get("fingerprints_equal") is True,
        "D-112 pre/post input evidence differs",
    )
    if verify_current_inputs:
        _require(pre_input == current_input, "D-112 current immutable input drifted")
    _require(
        body.get("probe_receipt") == receipt_binding,
        "D-112 probe receipt binding drifted",
    )

    vectors, vector_descriptors = _vectors_from_gate(body.get("query_vectors"))
    expected_scoring = _score_diagnostic(
        query_vectors=vectors,
        queries=context["queries"],
        index=context["index"],
    )
    _require(
        body.get("diagnostic_scoring") == expected_scoring,
        "D-112 recorded diagnostic scores drifted",
    )
    embedding = body.get("embedding_execution")
    _require(
        isinstance(embedding, dict)
        and embedding.get("config") == _embedding_config()
        and embedding.get("model_load_count") == 1
        and embedding.get("batch_encode_call_count") == 1
        and embedding.get("batch_query_row_count") == 3
        and embedding.get("query_vector_shape") == [3, d106.VECTOR_DIMENSION]
        and embedding.get("query_vector_dtype") == d106.VECTOR_DTYPE
        and embedding.get("finite_normalized_query_vectors") is True
        and embedding.get("locked_dependencies") == dict(sorted(dependencies.items()))
        and embedding.get("provider_or_network_model_call_count") == 0,
        "D-112 embedding execution evidence drifted",
    )
    recorded_implementation = body.get("implementation_files")
    _require(
        isinstance(recorded_implementation, list)
        and [row.get("path") for row in recorded_implementation]
        == [path.as_posix() for path in D112_IMPLEMENTATION_PATHS],
        "D-112 implementation bindings are invalid",
    )
    if verify_current_implementation:
        _require(
            recorded_implementation == _implementation_bindings(repo),
            "D-112 current implementation differs from executed bytes",
        )
    expected_gate = build_d112_completion_gate(
        completed_at=body["recorded_at"],
        probe_receipt_binding=receipt_binding,
        pre_input=pre_input,
        post_input=post_input,
        embedding_execution=embedding,
        query_vectors=vector_descriptors,
        scoring=expected_scoring,
        implementation_bindings=recorded_implementation,
    )
    _require(gate == expected_gate, "D-112 completion gate semantic content drifted")
    authority = body["authority"]
    return {
        "ok": True,
        "gate_id": gate["gate_id"],
        "semantic_body_hash": gate["semantic_body_hash"],
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "probe_receipt_id": receipt["receipt_id"],
        "probe_receipt_file_sha256": receipt["file_sha256"],
        "input_fingerprint": pre_input["fingerprint"],
        "score_row_count": expected_scoring["score_row_count"],
        "all_diagnostic_no_match": expected_scoring["all_diagnostic_no_match"],
        "retrieval_ready": authority["retrieval_ready"],
        "retrieval_experiment_authorized": authority["retrieval_experiment_authorized"],
        "runtime_memory_injection_count": authority["runtime_memory_injection_count"],
        "score_policy_correction_authorized": authority["score_policy_correction_authorized"],
        "core_campaign_unlocked": authority["core_campaign_unlocked"],
        "analysis_ready": authority["analysis_ready"],
        "provider_calls_made": authority["provider_calls_made"],
        "evaluator_calls_made": authority["evaluator_calls_made"],
        "added_model_cost_usd": authority["added_model_cost_usd"],
        "current_inputs_verified": verify_current_inputs,
        "current_implementation_verified": verify_current_implementation,
    }


__all__ = [
    "APPROVAL_ACTION_ID",
    "COMPLETION_GATE_SCHEMA_VERSION",
    "DEFAULT_COMPLETION_GATE_PATH",
    "DEFAULT_PROBE_RECEIPT_PATH",
    "D112ProbeError",
    "EXPECTED_ACTION_HASH",
    "EXPECTED_CANDIDATE_BODY_SHA",
    "EXPECTED_CANDIDATE_FILE_SHA",
    "EXPECTED_CANDIDATE_ID",
    "PROBE_RECEIPT_SCHEMA_VERSION",
    "build_d112_completion_gate",
    "build_d112_probe_receipt",
    "execute_d112_scoring_diagnostic",
    "preflight_d112_execution",
    "validate_d112_completion_gate",
    "validate_d112_probe_receipt",
]
