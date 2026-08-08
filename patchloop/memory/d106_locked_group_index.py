"""D-106 locked embedding preflight and exact group-aware index build.

This module consumes the exact D-105 authorization gate.  It downloads only
the files required by the pinned SentenceTransformer snapshot, proves that the
three admitted D-105 renders can be encoded locally without truncation, and
builds one deterministic, *unfrozen* index entry per admitted semantic group.

It deliberately does not call the legacy failure-by-failure builder, freeze an
index, run retrieval, contact an OpenAI provider, or unlock a core campaign.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import struct
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from patchloop.contracts import MemoryEntry
from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.memory import d104_unindexed_sources as d104
from patchloop.memory import d105_renderer_authorization as d105
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-106"
RECEIPT_SCHEMA_VERSION = "memory-index-build-approval-receipt-d106-v1"
PREFLIGHT_SCHEMA_VERSION = "locked-embedding-snapshot-preflight-d106-v1"
INDEX_SCHEMA_VERSION = "memory-index-v1"
INDEX_IDENTITY_SCHEMA_VERSION = "group-aware-index-identity-d106-v1"
INDEX_BUILD_SCHEMA_VERSION = "group-aware-memory-index-builder-d106-v1"
GATE_SCHEMA_VERSION = "locked-group-index-completion-gate-d106-v1"

APPROVAL_RECORDED_AT = "2026-08-06T07:23:15.8755387Z"
PREFLIGHT_RECORDED_AT = "2026-08-06T07:30:00Z"
INDEX_CREATED_AT = "2026-08-06T07:35:00Z"
GATE_RECORDED_AT = "2026-08-06T07:40:00Z"

EXPECTED_D105_GATE_ID = (
    "d105_0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70"
)
EXPECTED_D105_BODY_SHA = (
    "sha256:0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70"
)
EXPECTED_D105_FILE_BYTES = 12_368
EXPECTED_D105_FILE_SHA = (
    "sha256:db6303f3de834b3c36493f2863dcc5be3ca697490d18df15c86a18e7ee7b17eb"
)

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
VECTOR_DIMENSION = 384
VECTOR_DTYPE = "float32"

DATASET_ID = "patchloop-benchmark-v1"
DATASET_MANIFEST_HASH = (
    "sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786"
)

DEFAULT_RECEIPT_PATH = Path(
    "reports/memory-development/d106-exact-index-build-approval-receipt.json"
)
DEFAULT_PREFLIGHT_PATH = Path(
    "reports/memory-development/d106-locked-embedding-snapshot-preflight.json"
)
DEFAULT_PORTABLE_INDEX_DIRECTORY = Path("reports/memory-development/artifacts/d106")
DEFAULT_GATE_PATH = Path("reports/memory-development/d106-locked-group-index-gate.json")
DEFAULT_SNAPSHOT_DIRECTORY = Path(
    ".patchloop/memory/embedding-snapshots/"
    "sentence-transformers--all-MiniLM-L6-v2/"
    f"{MODEL_REVISION}"
)

HELD_GROUP_IDS = (
    "interrupt-lifecycle-unresolved",
    "diagnostic-contract-unresolved",
)

APPROVAL_STATEMENT_CODE = (
    "EXPLICITLY_APPROVE_D105_LOCKED_EMBEDDING_AND_ONE_UNFROZEN_GROUP_INDEX"
)
APPROVAL_STATEMENT = (
    f"{APPROVAL_STATEMENT_CODE} {EXPECTED_D105_GATE_ID} "
    f"{EXPECTED_D105_BODY_SHA} {EXPECTED_D105_FILE_SHA}"
)

# The exact runtime files required by SentenceTransformer for the pinned
# PyTorch/safetensors path.  Small-file blob IDs are Git blob SHA-1 values;
# model.safetensors is an LFS object and therefore binds its upstream SHA-256.
SNAPSHOT_FILES: tuple[dict[str, Any], ...] = (
    {
        "path": "1_Pooling/config.json",
        "bytes": 190,
        "git_blob_sha1": "d1514c3162bbe87b343f565fadc62e6c06f04f03",
        "lfs_sha256": None,
    },
    {
        "path": "config.json",
        "bytes": 612,
        "git_blob_sha1": "72b987fd805cfa2b58c4c8c952b274a11bfd5a00",
        "lfs_sha256": None,
    },
    {
        "path": "config_sentence_transformers.json",
        "bytes": 116,
        "git_blob_sha1": "fd1b291129c607e5d49799f87cb219b27f98acdf",
        "lfs_sha256": None,
    },
    {
        "path": "model.safetensors",
        "bytes": 90_868_376,
        "git_blob_sha1": "d49eff1e4a6f0e3ba5069f21c6d20aad156dd2c9",
        "lfs_sha256": "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db",
    },
    {
        "path": "modules.json",
        "bytes": 349,
        "git_blob_sha1": "952a9b81c0bfd99800fabf352f69c7ccd46c5e43",
        "lfs_sha256": None,
    },
    {
        "path": "sentence_bert_config.json",
        "bytes": 53,
        "git_blob_sha1": "59d594003bf59880a884c574bf88ef7555bb0202",
        "lfs_sha256": None,
    },
    {
        "path": "special_tokens_map.json",
        "bytes": 112,
        "git_blob_sha1": "e7b0375001f109a6b8873d756ad4f7bbb15fbaa5",
        "lfs_sha256": None,
    },
    {
        "path": "tokenizer.json",
        "bytes": 466_247,
        "git_blob_sha1": "cb202bfe2e3c98645018a6d12f182a434c9d3e02",
        "lfs_sha256": None,
    },
    {
        "path": "tokenizer_config.json",
        "bytes": 350,
        "git_blob_sha1": "c79f2b6a0cea6f4b564fed1938984bace9d30ff0",
        "lfs_sha256": None,
    },
    {
        "path": "vocab.txt",
        "bytes": 231_508,
        "git_blob_sha1": "fb140275c155a9c7c5a3b3e0e77a9e839594a938",
        "lfs_sha256": None,
    },
)

LOCKED_PACKAGES = {
    "huggingface-hub": "1.24.0",
    "numpy": "2.5.1",
    "safetensors": "0.8.0",
    "sentence-transformers": "5.6.0",
    "tokenizers": "0.22.2",
    "torch": "2.13.0",
    "transformers": "5.14.1",
}

IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d106_locked_group_index.py"),
    Path("scripts/build_d106_locked_group_index.py"),
    Path("tests/test_d106_locked_group_index.py"),
    Path("tests/test_memory.py"),
    Path("patchloop/memory/store.py"),
    Path("patchloop/memory/retrieval.py"),
)

_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


class D106IndexError(ContractError):
    """Stable fail-closed error for the approved D-106 boundary."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D106IndexError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = (
        Path(repository).absolute()
        if repository is not None
        else Path(__file__).absolute().parents[2]
    )
    resolved = selected.resolve()
    _require(resolved.is_dir(), "D-106 repository root is unavailable")
    return resolved


def _resolved(
    path: str | Path,
    *,
    repository: Path,
    label: str,
    require_within_repository: bool = True,
) -> Path:
    selected = Path(path)
    candidate = selected if selected.is_absolute() else repository / selected
    resolved = candidate.resolve()
    if require_within_repository:
        try:
            resolved.relative_to(repository)
        except ValueError as exc:
            raise D106IndexError(f"D-106 {label} must stay within the repository") from exc
    return resolved


def _read_stable(path: Path, *, label: str) -> bytes:
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except OSError as exc:
        raise D106IndexError(f"D-106 {label} is unavailable") from exc
    _require(first == second, f"D-106 {label} changed while being read")
    return first


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D106IndexError(f"D-106 {label} JSON is invalid") from exc
    _require(isinstance(payload, dict), f"D-106 {label} JSON root is invalid")
    return payload


def _pretty_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _file_binding(path: str | Path, *, repository: Path, label: str) -> dict[str, Any]:
    selected = _resolved(path, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _write_exact(path: Path, content: bytes, *, repository: Path) -> dict[str, Any]:
    return d105.write_d105_new_exact(path, content, repository=repository)


def _validate_exact_d105_gate(repository: Path) -> dict[str, Any]:
    result = d105.validate_d105_gate(repository=repository)
    binding = _file_binding(d105.DEFAULT_GATE_PATH, repository=repository, label="D-105 gate")
    gate_content = _read_stable(repository / d105.DEFAULT_GATE_PATH, label="D-105 gate")
    gate_payload = _parse_json(gate_content, label="D-105 gate")
    _require(result["gate_id"] == EXPECTED_D105_GATE_ID, "D-106 D-105 gate ID drifted")
    _require(
        result["semantic_body_hash"] == EXPECTED_D105_BODY_SHA,
        "D-106 D-105 gate body hash drifted",
    )
    _require(
        binding["file_bytes"] == EXPECTED_D105_FILE_BYTES
        and binding["file_sha256"] == EXPECTED_D105_FILE_SHA,
        "D-106 D-105 gate file identity drifted",
    )
    return {
        **binding,
        "schema_version": d105.GATE_SCHEMA_VERSION,
        "gate_id": result["gate_id"],
        "semantic_body_hash": result["semantic_body_hash"],
        "dependency_lock_file_sha256": gate_payload["semantic_body"][
            "locked_embedding_dependencies"
        ]["lock"]["file_sha256"],
    }


def build_d106_approval_receipt(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Build the exact self-attested receipt for the user's narrow approval."""

    repo = _repo_root(repository)
    d105_gate = _validate_exact_d105_gate(repo)
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "self-attested-exact-d105-index-build-approval",
        "recorded_at": APPROVAL_RECORDED_AT,
        "d105_gate": d105_gate,
        "approval_action_id": "d106-exact-d105-index-build-approval-1",
        "approver_kind": "human",
        "approver_label": "chat-maintainer-self-attested",
        "approval_reference": "user-message:d105-locked-embedding-and-unfrozen-index-approval",
        "approval_reference_mode": "immediate-preceding-exact-gate-reference",
        "approval_statement_code": APPROVAL_STATEMENT_CODE,
        "approval_statement": APPROVAL_STATEMENT,
        "authorized_scope": {
            "pinned_snapshot_download": True,
            "locked_snapshot_preflight": True,
            "group_aware_builder_implementation": True,
            "admitted_semantic_group_count": 3,
            "actual_unfrozen_index_count": 1,
            "index_freeze_authorized": False,
            "retrieval_experiment_authorized": False,
            "core_campaign_authorized": False,
        },
        "explicit_approval_receipt_recorded": True,
        "reviewer_identity_authenticated": False,
        "cryptographic_signature_verified": False,
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "receipt_id": f"d106receipt_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def materialize_d106_approval_receipt(
    receipt_path: str | Path = DEFAULT_RECEIPT_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(receipt_path, repository=repo, label="approval receipt")
    payload = build_d106_approval_receipt(repository=repo)
    content = _pretty_json(payload)
    write = _write_exact(selected, content, repository=repo)
    return {
        **write,
        "receipt_id": payload["receipt_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def validate_d106_approval_receipt(
    receipt_path: str | Path = DEFAULT_RECEIPT_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(receipt_path, repository=repo, label="approval receipt")
    content = _read_stable(selected, label="approval receipt")
    expected = build_d106_approval_receipt(repository=repo)
    _require(content == _pretty_json(expected), "D-106 approval receipt exact bytes drifted")
    parsed = _parse_json(content, label="approval receipt")
    _require(parsed == expected, "D-106 approval receipt semantic content drifted")
    scope = expected["semantic_body"]["authorized_scope"]
    _require(scope["actual_unfrozen_index_count"] == 1, "D-106 approval index count drifted")
    _require(
        scope["index_freeze_authorized"] is False
        and scope["retrieval_experiment_authorized"] is False
        and scope["core_campaign_authorized"] is False,
        "D-106 approval scope widened",
    )
    return {
        "path": selected.relative_to(repo).as_posix(),
        "schema_version": expected["schema_version"],
        "receipt_id": expected["receipt_id"],
        "semantic_body_hash": expected["semantic_body_hash"],
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "self_attested": True,
        "reviewer_identity_authenticated": False,
        "cryptographic_signature_verified": False,
    }


def _git_blob_sha1(content: bytes) -> str:
    prefix = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(prefix + content, usedforsecurity=False).hexdigest()


def validate_d106_snapshot_files(snapshot_directory: str | Path) -> dict[str, Any]:
    """Validate the exact safetensors-only runtime snapshot inventory."""

    root = Path(snapshot_directory).resolve()
    _require(root.is_dir(), "D-106 embedding snapshot directory is unavailable")
    actual_paths = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and ".cache" not in path.relative_to(root).parts
    )
    expected_paths = [row["path"] for row in SNAPSHOT_FILES]
    _require(actual_paths == expected_paths, "D-106 embedding snapshot file set drifted")

    descriptors: list[dict[str, Any]] = []
    for expected in SNAPSHOT_FILES:
        path = root / expected["path"]
        _require(not path.is_symlink(), "D-106 embedding snapshot file cannot be a symlink")
        content = _read_stable(path, label=f"snapshot file {expected['path']}")
        _require(len(content) == expected["bytes"], "D-106 embedding snapshot byte count drifted")
        local_sha = sha256_bytes(content)
        if expected["lfs_sha256"] is not None:
            _require(
                local_sha == f"sha256:{expected['lfs_sha256']}",
                "D-106 embedding LFS object hash drifted",
            )
            upstream_verification = "lfs-sha256"
        else:
            _require(
                _git_blob_sha1(content) == expected["git_blob_sha1"],
                "D-106 embedding Git blob hash drifted",
            )
            upstream_verification = "git-blob-sha1"
        descriptors.append(
            {
                **expected,
                "local_sha256": local_sha,
                "upstream_verification": upstream_verification,
            }
        )
    manifest_hash = sha256_text(canonical_json(descriptors))
    return {
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "required_file_count": len(descriptors),
        "files": descriptors,
        "snapshot_manifest_hash": manifest_hash,
        "safetensors_only": all(
            not row["path"].endswith((".bin", ".onnx", ".h5", ".ot"))
            for row in descriptors
        ),
    }


def download_d106_snapshot(
    snapshot_directory: str | Path = DEFAULT_SNAPSHOT_DIRECTORY,
    *,
    repository: str | Path | None = None,
    receipt_path: str | Path = DEFAULT_RECEIPT_PATH,
) -> dict[str, Any]:
    """Download only the authorized exact-revision runtime files."""

    repo = _repo_root(repository)
    validate_d106_approval_receipt(receipt_path, repository=repo)
    target = _resolved(snapshot_directory, repository=repo, label="snapshot directory")
    target.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise D106IndexError(
            "D-106 memory dependencies are unavailable; run uv sync --locked --extra memory"
        ) from exc
    downloaded = Path(
        snapshot_download(
            repo_id=MODEL_ID,
            revision=MODEL_REVISION,
            local_dir=target,
            allow_patterns=[row["path"] for row in SNAPSHOT_FILES],
        )
    ).resolve()
    _require(downloaded == target, "D-106 snapshot downloader returned an unexpected path")
    return validate_d106_snapshot_files(target)


def _installed_dependency_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for package, expected in LOCKED_PACKAGES.items():
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError as exc:
            raise D106IndexError(f"D-106 locked dependency is missing: {package}") from exc
        _require(actual == expected, f"D-106 locked dependency drifted: {package}")
        versions[package] = actual
    return versions


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


def _load_local_model(snapshot_directory: Path) -> Any:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise D106IndexError(
            "D-106 sentence-transformers runtime is unavailable; install the memory extra"
        ) from exc
    with _offline_library_environment():
        return SentenceTransformer(
            str(snapshot_directory),
            device="cpu",
            trust_remote_code=False,
            local_files_only=True,
        )


def _float32_row_bytes(row: Sequence[Any]) -> bytes:
    try:
        return b"".join(struct.pack("<f", float(value)) for value in row)
    except (OverflowError, TypeError, ValueError) as exc:
        raise D106IndexError("D-106 embedding vector is not float32-compatible") from exc


def _validate_vector_batch(
    vectors: Any,
    *,
    expected_count: int,
) -> tuple[list[list[float]], list[dict[str, Any]]]:
    shape = getattr(vectors, "shape", None)
    dtype = str(getattr(vectors, "dtype", ""))
    _require(dtype == VECTOR_DTYPE, "D-106 embedding dtype drifted")
    _require(
        tuple(shape) == (expected_count, VECTOR_DIMENSION),
        "D-106 embedding vector shape drifted",
    )
    rows = [[float(value) for value in row] for row in vectors]
    _require(len(rows) == expected_count, "D-106 embedding vector count drifted")
    descriptors: list[dict[str, Any]] = []
    for row in rows:
        _require(len(row) == VECTOR_DIMENSION, "D-106 embedding dimension drifted")
        _require(all(math.isfinite(value) for value in row), "D-106 embedding is not finite")
        norm = math.sqrt(sum(value * value for value in row))
        _require(abs(norm - 1.0) <= 1e-5, "D-106 embedding is not normalized")
        row_bytes = _float32_row_bytes(row)
        descriptors.append(
            {
                "dimension": len(row),
                "dtype": VECTOR_DTYPE,
                "l2_norm": round(norm, 12),
                "float32_sha256": sha256_bytes(row_bytes),
            }
        )
    return rows, descriptors


def _load_authorized_material(repository: Path) -> dict[str, Any]:
    """Load the exact D-104 sources and D-105 renders in admitted order."""

    d105_gate = _validate_exact_d105_gate(repository)
    d104_gate = d104.validate_d104_source_gate(repository=repository)
    source_evidence = d104.validate_d104_materialized_sources(repository=repository)
    render_evidence = d105.validate_d105_rendered_entries(repository=repository)
    _require(
        source_evidence["source_collection_id"] == render_evidence["source_collection_id"],
        "D-106 source collection and render collection differ",
    )
    _require(
        source_evidence["source_set_hash"] == render_evidence["source_set_hash"],
        "D-106 source set and render source set differ",
    )
    _require(
        source_evidence["held_group_ids"] == list(HELD_GROUP_IDS),
        "D-106 held group set drifted",
    )
    _require(
        len(source_evidence["entries"]) == len(render_evidence["entries"]) == 3,
        "D-106 requires exactly three admitted groups",
    )

    manifest, manifest_hash, manifest_path = load_dataset_manifest()
    _require(manifest.dataset_id == DATASET_ID, "D-106 dataset ID drifted")
    _require(manifest_hash == DATASET_MANIFEST_HASH, "D-106 dataset manifest hash drifted")

    records: list[dict[str, Any]] = []
    for source_descriptor, render_descriptor in zip(
        source_evidence["entries"], render_evidence["entries"], strict=True
    ):
        _require(
            source_descriptor["order"] == render_descriptor["order"],
            "D-106 source and render order differ",
        )
        _require(
            source_descriptor["source_id"] == render_descriptor["source_id"],
            "D-106 source and render identities differ",
        )
        _require(
            source_descriptor["semantic_group_id"] == render_descriptor["semantic_group_id"],
            "D-106 semantic group and render identities differ",
        )
        _require(
            source_descriptor["template_hash"] == render_descriptor["template_hash"],
            "D-106 source template and render template differ",
        )
        _require(
            source_descriptor["semantic_group_id"] not in HELD_GROUP_IDS,
            "D-106 held group cannot enter the index",
        )
        source_path = _resolved(
            source_descriptor["path"], repository=repository, label="D-104 source"
        )
        source_content = _read_stable(source_path, label="D-104 source")
        try:
            source = d104.D104SourceRecord.model_validate_json(source_content)
        except ValidationError as exc:
            raise D106IndexError("D-106 D-104 source schema is invalid") from exc
        render_path = _resolved(
            render_descriptor["path"], repository=repository, label="D-105 render"
        )
        render_content = _read_stable(render_path, label="D-105 render")
        _require(
            len(render_content) == render_descriptor["file_bytes"]
            and sha256_bytes(render_content) == render_descriptor["file_sha256"],
            "D-106 rendered memory identity drifted",
        )
        try:
            render_text = render_content.decode("ascii")
        except UnicodeDecodeError as exc:
            raise D106IndexError("D-106 rendered memory is not ASCII") from exc
        records.append(
            {
                "source": source,
                "source_descriptor": source_descriptor,
                "render_descriptor": render_descriptor,
                "render_text": render_text,
            }
        )

    uniqueness = {
        "source IDs": [row["source"].source_id for row in records],
        "memory IDs": [
            row["source"].semantic_body.projected_entry.template.proposed_memory_id
            for row in records
        ],
        "semantic group IDs": [
            row["source"].semantic_body.projected_entry.provenance.semantic_group_id
            for row in records
        ],
        "source run IDs": [
            run_id
            for row in records
            for run_id in row["source"].semantic_body.projected_entry.template.source_run_ids
        ],
        "source failure IDs": [
            failure_id
            for row in records
            for failure_id in row[
                "source"
            ].semantic_body.projected_entry.provenance.source_failure_ids
        ],
    }
    for label, values in uniqueness.items():
        _require(len(values) == len(set(values)), f"D-106 {label} must be unique")

    return {
        "d105_gate": d105_gate,
        "d104_gate": d104_gate,
        "source_collection_id": source_evidence["source_collection_id"],
        "source_set_hash": source_evidence["source_set_hash"],
        "render_set_hash": render_evidence["render_set_hash"],
        "dataset": {
            "dataset_id": manifest.dataset_id,
            "dataset_manifest_hash": manifest_hash,
            "manifest_path": manifest_path.relative_to(repository).as_posix(),
        },
        "held_group_ids": list(HELD_GROUP_IDS),
        "records": records,
    }


def _untruncated_token_counts(model: Any, texts: Sequence[str]) -> tuple[int, list[int]]:
    tokenizer = getattr(model, "tokenizer", None)
    _require(tokenizer is not None, "D-106 local model tokenizer is unavailable")
    try:
        encoded = tokenizer(
            list(texts),
            add_special_tokens=True,
            padding=False,
            truncation=False,
        )
        input_ids = encoded["input_ids"]
        max_seq_length = int(model.max_seq_length)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise D106IndexError("D-106 tokenizer preflight failed") from exc
    counts = [len(row) for row in input_ids]
    _require(len(counts) == len(texts), "D-106 tokenizer result count drifted")
    _require(max_seq_length > 0, "D-106 model maximum sequence length is invalid")
    _require(
        all(count <= max_seq_length for count in counts),
        "D-106 rendered memory would be silently truncated",
    )
    return max_seq_length, counts


def _encode_local_model(model: Any, texts: Sequence[str]) -> Any:
    try:
        dimension = int(model.get_sentence_embedding_dimension())
    except (TypeError, ValueError, AttributeError) as exc:
        raise D106IndexError("D-106 embedding dimension API is unavailable") from exc
    _require(dimension == VECTOR_DIMENSION, "D-106 model embedding dimension drifted")
    with _offline_library_environment():
        return model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )


def run_d106_embedding_preflight(
    snapshot_directory: str | Path = DEFAULT_SNAPSHOT_DIRECTORY,
    *,
    repository: str | Path | None = None,
    receipt_path: str | Path = DEFAULT_RECEIPT_PATH,
    model_loader: Any | None = None,
) -> tuple[dict[str, Any], dict[str, list[float]]]:
    """Run two fresh local-only model loads and return portable evidence plus vectors."""

    repo = _repo_root(repository)
    approval = validate_d106_approval_receipt(receipt_path, repository=repo)
    material = _load_authorized_material(repo)
    snapshot_path = _resolved(
        snapshot_directory, repository=repo, label="snapshot directory"
    )
    snapshot = validate_d106_snapshot_files(snapshot_path)
    dependencies = _installed_dependency_versions()
    texts = [row["render_text"] for row in material["records"]]
    memory_ids = [
        row["source"].semantic_body.projected_entry.template.proposed_memory_id
        for row in material["records"]
    ]
    loader = model_loader or _load_local_model

    first_model = loader(snapshot_path)
    max_seq_length, token_counts = _untruncated_token_counts(first_model, texts)
    first_raw = _encode_local_model(first_model, texts)
    first_rows, first_descriptors = _validate_vector_batch(
        first_raw, expected_count=len(texts)
    )

    second_model = loader(snapshot_path)
    second_max, second_counts = _untruncated_token_counts(second_model, texts)
    _require(
        second_max == max_seq_length and second_counts == token_counts,
        "D-106 tokenizer result changed across fresh local loads",
    )
    second_raw = _encode_local_model(second_model, texts)
    second_rows, second_descriptors = _validate_vector_batch(
        second_raw, expected_count=len(texts)
    )
    _require(
        [row["float32_sha256"] for row in first_descriptors]
        == [row["float32_sha256"] for row in second_descriptors],
        "D-106 vectors changed across fresh local loads",
    )
    _require(
        [_float32_row_bytes(row) for row in first_rows]
        == [_float32_row_bytes(row) for row in second_rows],
        "D-106 vectors are not bit-identical in the current environment",
    )

    vector_checks = []
    vectors: dict[str, list[float]] = {}
    for order, (record, memory_id, token_count, descriptor, row) in enumerate(
        zip(
            material["records"],
            memory_ids,
            token_counts,
            first_descriptors,
            first_rows,
            strict=True,
        ),
        start=1,
    ):
        vectors[memory_id] = row
        vector_checks.append(
            {
                "order": order,
                "memory_id": memory_id,
                "semantic_group_id": record[
                    "source"
                ].semantic_body.projected_entry.provenance.semantic_group_id,
                "render_file_sha256": record["render_descriptor"]["file_sha256"],
                "untruncated_token_count": token_count,
                **descriptor,
            }
        )

    vector_set_hash = sha256_text(
        canonical_json(
            [
                {
                    "memory_id": row["memory_id"],
                    "float32_sha256": row["float32_sha256"],
                }
                for row in vector_checks
            ]
        )
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "locked-local-embedding-snapshot-preflight",
        "recorded_at": PREFLIGHT_RECORDED_AT,
        "d105_gate": material["d105_gate"],
        "approval_receipt": approval,
        "source_collection_id": material["source_collection_id"],
        "source_set_hash": material["source_set_hash"],
        "render_set_hash": material["render_set_hash"],
        "embedding": {
            "model_id": MODEL_ID,
            "revision": MODEL_REVISION,
            "normalize_embeddings": True,
            "trust_remote_code": False,
            "device": "cpu",
            "dimension": VECTOR_DIMENSION,
            "dtype": VECTOR_DTYPE,
            "snapshot_manifest_hash": snapshot["snapshot_manifest_hash"],
        },
        "snapshot": snapshot,
        "dependencies": dependencies,
        "runtime": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "offline_reload": {
            "local_files_only": True,
            "hf_hub_offline_environment": True,
            "transformers_offline_environment": True,
            "network_socket_blocked": False,
            "fresh_local_model_load_count": 2,
            "local_embedding_encode_call_count": 2,
        },
        "tokenization": {
            "truncation_requested": False,
            "max_seq_length": max_seq_length,
            "all_renders_fit_without_truncation": True,
        },
        "vector_checks": vector_checks,
        "vector_set_hash": vector_set_hash,
        "validation": {
            "exact_snapshot_file_set": "pass",
            "upstream_file_identity": "pass",
            "safetensors_only": True,
            "exact_three_renders": "pass",
            "no_silent_truncation": "pass",
            "shape_dtype_finite_normalized": "pass",
            "fresh_load_current_host_determinism": "pass",
        },
        "authority": {
            "embedding_snapshot_verified": True,
            "actual_embedding_count": 3,
            "memory_index_build_authorized": True,
            "memory_index_built": False,
            "memory_index_frozen": False,
            "retrieval_ready": False,
            "core_campaign_unlocked": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
    }
    body_hash = sha256_text(canonical_json(body))
    report = {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "preflight_id": f"d106preflight_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }
    return report, vectors


def validate_d106_preflight_report(
    preflight_path: str | Path = DEFAULT_PREFLIGHT_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Portable validation that does not need the 91 MB local model snapshot."""

    repo = _repo_root(repository)
    selected = _resolved(preflight_path, repository=repo, label="embedding preflight")
    content = _read_stable(selected, label="embedding preflight")
    payload = _parse_json(content, label="embedding preflight")
    _require(
        payload.get("schema_version") == PREFLIGHT_SCHEMA_VERSION,
        "D-106 embedding preflight schema drifted",
    )
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-106 embedding preflight body is invalid")
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload.get("semantic_body_hash") == body_hash
        and payload.get("preflight_id")
        == f"d106preflight_{body_hash.removeprefix('sha256:')}",
        "D-106 embedding preflight identity drifted",
    )
    approval = validate_d106_approval_receipt(repository=repo)
    _require(body.get("approval_receipt") == approval, "D-106 preflight approval binding drifted")
    material = _load_authorized_material(repo)
    _require(body.get("d105_gate") == material["d105_gate"], "D-106 preflight gate drifted")
    embedding = body.get("embedding", {})
    _require(
        embedding.get("model_id") == MODEL_ID
        and embedding.get("revision") == MODEL_REVISION
        and embedding.get("dimension") == VECTOR_DIMENSION
        and embedding.get("dtype") == VECTOR_DTYPE
        and embedding.get("normalize_embeddings") is True
        and embedding.get("trust_remote_code") is False,
        "D-106 preflight embedding contract drifted",
    )
    snapshot = body.get("snapshot", {})
    files = snapshot.get("files")
    _require(isinstance(files, list), "D-106 preflight snapshot manifest is invalid")
    _require(
        [
            {
                "path": row.get("path"),
                "bytes": row.get("bytes"),
                "git_blob_sha1": row.get("git_blob_sha1"),
                "lfs_sha256": row.get("lfs_sha256"),
            }
            for row in files
        ]
        == list(SNAPSHOT_FILES),
        "D-106 preflight snapshot upstream manifest drifted",
    )
    _require(
        snapshot.get("snapshot_manifest_hash") == sha256_text(canonical_json(files)),
        "D-106 preflight snapshot manifest hash drifted",
    )
    _require(body.get("dependencies") == LOCKED_PACKAGES, "D-106 dependency evidence drifted")
    checks = body.get("vector_checks")
    _require(isinstance(checks, list) and len(checks) == 3, "D-106 vector checks drifted")
    expected_memory_ids = [
        row["source"].semantic_body.projected_entry.template.proposed_memory_id
        for row in material["records"]
    ]
    _require(
        [row.get("memory_id") for row in checks] == expected_memory_ids,
        "D-106 vector check order drifted",
    )
    _require(
        all(
            row.get("dimension") == VECTOR_DIMENSION
            and row.get("dtype") == VECTOR_DTYPE
            and isinstance(row.get("l2_norm"), (int, float))
            and abs(float(row["l2_norm"]) - 1.0) <= 1e-5
            and isinstance(row.get("untruncated_token_count"), int)
            and row["untruncated_token_count"] <= body["tokenization"]["max_seq_length"]
            and isinstance(row.get("float32_sha256"), str)
            and _SHA256.fullmatch(row["float32_sha256"]) is not None
            for row in checks
        ),
        "D-106 vector check values are invalid",
    )
    expected_vector_set = sha256_text(
        canonical_json(
            [
                {
                    "memory_id": row["memory_id"],
                    "float32_sha256": row["float32_sha256"],
                }
                for row in checks
            ]
        )
    )
    _require(body.get("vector_set_hash") == expected_vector_set, "D-106 vector set drifted")
    authority = body.get("authority", {})
    _require(
        authority.get("embedding_snapshot_verified") is True
        and authority.get("actual_embedding_count") == 3
        and authority.get("memory_index_build_authorized") is True
        and authority.get("memory_index_built") is False
        and authority.get("memory_index_frozen") is False
        and authority.get("retrieval_ready") is False
        and authority.get("core_campaign_unlocked") is False,
        "D-106 preflight authority drifted",
    )
    return {
        "path": selected.relative_to(repo).as_posix(),
        "schema_version": payload["schema_version"],
        "preflight_id": payload["preflight_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "snapshot_manifest_hash": snapshot["snapshot_manifest_hash"],
        "vector_set_hash": body["vector_set_hash"],
        "vector_checks": checks,
    }


def _vector_map_checks(
    vectors: Mapping[str, Sequence[Any]],
    *,
    expected_memory_ids: Sequence[str],
    preflight_checks: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, list[float]], list[dict[str, Any]]]:
    _require(
        list(vectors) == list(expected_memory_ids),
        "D-106 embedding vector keys or order drifted",
    )
    normalized: dict[str, list[float]] = {}
    descriptors: list[dict[str, Any]] = []
    for memory_id, expected in zip(expected_memory_ids, preflight_checks, strict=True):
        row = [float(value) for value in vectors[memory_id]]
        _require(len(row) == VECTOR_DIMENSION, "D-106 index vector dimension drifted")
        _require(all(math.isfinite(value) for value in row), "D-106 index vector is not finite")
        norm = math.sqrt(sum(value * value for value in row))
        _require(abs(norm - 1.0) <= 1e-5, "D-106 index vector is not normalized")
        vector_sha = sha256_bytes(_float32_row_bytes(row))
        _require(
            vector_sha == expected.get("float32_sha256"),
            "D-106 index vector differs from the preflight vector",
        )
        normalized[memory_id] = row
        descriptors.append(
            {
                "memory_id": memory_id,
                "float32_sha256": vector_sha,
                "dimension": VECTOR_DIMENSION,
                "dtype": VECTOR_DTYPE,
            }
        )
    return normalized, descriptors


def build_d106_group_index(
    vectors: Mapping[str, Sequence[Any]],
    *,
    repository: str | Path | None = None,
    preflight_path: str | Path = DEFAULT_PREFLIGHT_PATH,
) -> dict[str, Any]:
    """Build an exact-three, deterministic, unfrozen group-aware index payload."""

    repo = _repo_root(repository)
    preflight = validate_d106_preflight_report(preflight_path, repository=repo)
    approval = validate_d106_approval_receipt(repository=repo)
    material = _load_authorized_material(repo)
    records = material["records"]
    memory_ids = [
        row["source"].semantic_body.projected_entry.template.proposed_memory_id
        for row in records
    ]
    normalized_vectors, vector_descriptors = _vector_map_checks(
        vectors,
        expected_memory_ids=memory_ids,
        preflight_checks=preflight["vector_checks"],
    )

    ordered_identity_entries: list[dict[str, Any]] = []
    for record, vector_descriptor in zip(records, vector_descriptors, strict=True):
        source = record["source"]
        projected = source.semantic_body.projected_entry
        ordered_identity_entries.append(
            {
                "memory_id": projected.template.proposed_memory_id,
                "source_id": source.source_id,
                "semantic_group_id": projected.provenance.semantic_group_id,
                "template_hash": projected.template_hash,
                "render_file_sha256": record["render_descriptor"]["file_sha256"],
                "embedding_float32_sha256": vector_descriptor["float32_sha256"],
            }
        )
    identity_body = {
        "schema_version": INDEX_IDENTITY_SCHEMA_VERSION,
        "d105_gate": {
            "gate_id": material["d105_gate"]["gate_id"],
            "semantic_body_hash": material["d105_gate"]["semantic_body_hash"],
            "file_sha256": material["d105_gate"]["file_sha256"],
        },
        "approval_receipt": {
            "receipt_id": approval["receipt_id"],
            "semantic_body_hash": approval["semantic_body_hash"],
            "file_sha256": approval["file_sha256"],
        },
        "embedding_preflight": {
            "preflight_id": preflight["preflight_id"],
            "model": MODEL_ID,
            "revision": MODEL_REVISION,
            "snapshot_manifest_hash": preflight["snapshot_manifest_hash"],
            "dependency_lock_hash": material["d105_gate"][
                "dependency_lock_file_sha256"
            ],
        },
        "source_collection_id": material["source_collection_id"],
        "source_set_hash": material["source_set_hash"],
        "render_set_hash": material["render_set_hash"],
        "dataset_id": material["dataset"]["dataset_id"],
        "dataset_manifest_hash": material["dataset"]["dataset_manifest_hash"],
        "held_group_ids": material["held_group_ids"],
        "ordered_entries": ordered_identity_entries,
    }
    identity_hash = sha256_text(canonical_json(identity_body))
    index_version = f"idxgrp_{identity_hash.removeprefix('sha256:')}"

    entries: list[MemoryEntry] = []
    model_facing_text: dict[str, str] = {}
    group_provenance: list[dict[str, Any]] = []
    for order, record in enumerate(records, start=1):
        source = record["source"]
        projected = source.semantic_body.projected_entry
        template = projected.template
        entry = MemoryEntry(
            memory_id=template.proposed_memory_id,
            index_version=index_version,
            failure_pattern=template.failure_pattern,
            preconditions=template.preconditions,
            diagnostic_evidence=template.diagnostic_evidence,
            recommended_actions=template.recommended_actions,
            do_not_apply_when=template.do_not_apply_when,
            applicable_languages=template.applicable_languages,
            source_run_ids=template.source_run_ids,
            validation_count=template.validation_count,
            confidence=template.confidence,
        )
        entries.append(entry)
        model_facing_text[entry.memory_id] = record["render_text"]
        group_provenance.append(
            {
                "order": order,
                "memory_id": entry.memory_id,
                "source_id": source.source_id,
                "source_file_sha256": record["source_descriptor"]["file_sha256"],
                "render_file_sha256": record["render_descriptor"]["file_sha256"],
                "semantic_group_id": projected.provenance.semantic_group_id,
                "semantic_group_fingerprint": projected.provenance.semantic_group_fingerprint,
                "decision_hash": projected.provenance.decision_hash,
                "template_hash": projected.template_hash,
                "source_run_ids": template.source_run_ids,
                "source_failure_ids": projected.provenance.source_failure_ids,
                "evidence_ref_ids": projected.provenance.evidence_ref_ids,
                "dedup_confidence": projected.provenance.dedup_confidence,
            }
        )

    payload: dict[str, Any] = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "index_version": index_version,
        "split": "dev-train",
        "dataset_id": material["dataset"]["dataset_id"],
        "dataset_manifest_hash": material["dataset"]["dataset_manifest_hash"],
        "created_at": INDEX_CREATED_AT,
        "frozen": False,
        "embedding": {
            "model": MODEL_ID,
            "revision": MODEL_REVISION,
            "implementation": "sentence-transformers",
            "normalize_embeddings": True,
            "trust_remote_code": False,
            "dimension": VECTOR_DIMENSION,
            "dtype": VECTOR_DTYPE,
            "snapshot_manifest_hash": preflight["snapshot_manifest_hash"],
            "vector_set_hash": preflight["vector_set_hash"],
        },
        "embeddings": normalized_vectors,
        "entries": [entry.model_dump(mode="json") for entry in entries],
        "model_facing_text": model_facing_text,
        "group_provenance": group_provenance,
        "held_group_ids": material["held_group_ids"],
        "rejected_sources": [],
        "build_contract": {
            "schema_version": INDEX_BUILD_SCHEMA_VERSION,
            "identity_body": identity_body,
            "identity_hash": identity_hash,
            "one_entry_per_admitted_group": True,
            "exact_three_or_fail": True,
            "legacy_failure_builder_used": False,
            "embedding_input": "exact-d105-render-bytes",
            "d105_gate": material["d105_gate"],
            "approval_receipt": approval,
            "embedding_preflight": {
                key: preflight[key]
                for key in (
                    "path",
                    "schema_version",
                    "preflight_id",
                    "semantic_body_hash",
                    "file_bytes",
                    "file_sha256",
                    "snapshot_manifest_hash",
                    "vector_set_hash",
                )
            },
        },
        "authority": {
            "memory_index_build_authorized": True,
            "actual_memory_entry_count": 3,
            "embedding_count": 3,
            "memory_index_built": True,
            "memory_index_frozen": False,
            "index_freeze_authorized": False,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
    }
    payload["content_hash"] = sha256_text(canonical_json(payload))
    validate_d106_group_index_payload(payload, repository=repo)
    return payload


def validate_d106_group_index_payload(
    payload: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    material = _load_authorized_material(repo)
    _require(payload.get("schema_version") == INDEX_SCHEMA_VERSION, "D-106 index schema drifted")
    build_contract = payload.get("build_contract")
    _require(isinstance(build_contract, dict), "D-106 index build contract is invalid")
    _require(
        build_contract.get("schema_version") == INDEX_BUILD_SCHEMA_VERSION,
        "D-106 group-aware builder schema drifted",
    )
    identity_body = build_contract.get("identity_body")
    _require(isinstance(identity_body, dict), "D-106 index identity body is invalid")
    identity_hash = sha256_text(canonical_json(identity_body))
    index_version = f"idxgrp_{identity_hash.removeprefix('sha256:')}"
    _require(
        payload.get("index_version") == index_version
        and build_contract.get("identity_hash") == identity_hash,
        "D-106 deterministic index identity drifted",
    )
    without_hash = dict(payload)
    content_hash = without_hash.pop("content_hash", None)
    _require(
        content_hash == sha256_text(canonical_json(without_hash)),
        "D-106 index content hash drifted",
    )
    _require(
        payload.get("dataset_id") == DATASET_ID
        and payload.get("dataset_manifest_hash") == DATASET_MANIFEST_HASH,
        "D-106 index dataset binding drifted",
    )
    _require(payload.get("split") == "dev-train", "D-106 index split drifted")
    _require(payload.get("frozen") is False, "D-106 index must remain unfrozen")
    _require(payload.get("held_group_ids") == list(HELD_GROUP_IDS), "D-106 held groups drifted")
    _require(payload.get("rejected_sources") == [], "D-106 cannot partially reject sources")
    raw_entries = payload.get("entries")
    _require(isinstance(raw_entries, list) and len(raw_entries) == 3, "D-106 entry count drifted")
    try:
        entries = [MemoryEntry.model_validate(row) for row in raw_entries]
    except ValidationError as exc:
        raise D106IndexError("D-106 MemoryEntry schema is invalid") from exc
    expected_memory_ids = [
        row["source"].semantic_body.projected_entry.template.proposed_memory_id
        for row in material["records"]
    ]
    _require(
        [entry.memory_id for entry in entries] == expected_memory_ids,
        "D-106 MemoryEntry order drifted",
    )
    _require(
        all(entry.index_version == index_version for entry in entries),
        "D-106 MemoryEntry index binding drifted",
    )
    embeddings = payload.get("embeddings")
    _require(isinstance(embeddings, dict), "D-106 embedding map is invalid")
    _require(list(embeddings) == expected_memory_ids, "D-106 embedding order drifted")
    model_text = payload.get("model_facing_text")
    _require(isinstance(model_text, dict), "D-106 model-facing text map is invalid")
    _require(list(model_text) == expected_memory_ids, "D-106 model-facing text order drifted")
    provenance = payload.get("group_provenance")
    _require(isinstance(provenance, list) and len(provenance) == 3, "D-106 provenance drifted")

    identity_entries = identity_body.get("ordered_entries")
    _require(
        isinstance(identity_entries, list) and len(identity_entries) == 3,
        "D-106 identity entry set drifted",
    )
    for order, (entry, record, provenance_row, identity_row) in enumerate(
        zip(entries, material["records"], provenance, identity_entries, strict=True),
        start=1,
    ):
        projected = record["source"].semantic_body.projected_entry
        expected_entry = MemoryEntry(
            memory_id=projected.template.proposed_memory_id,
            index_version=index_version,
            failure_pattern=projected.template.failure_pattern,
            preconditions=projected.template.preconditions,
            diagnostic_evidence=projected.template.diagnostic_evidence,
            recommended_actions=projected.template.recommended_actions,
            do_not_apply_when=projected.template.do_not_apply_when,
            applicable_languages=projected.template.applicable_languages,
            source_run_ids=projected.template.source_run_ids,
            validation_count=projected.template.validation_count,
            confidence=projected.template.confidence,
        )
        _require(entry == expected_entry, "D-106 MemoryEntry source projection drifted")
        _require(
            model_text[entry.memory_id] == record["render_text"],
            "D-106 model-facing text differs from the exact D-105 render",
        )
        _require(
            provenance_row["order"] == order
            and provenance_row["memory_id"] == entry.memory_id
            and provenance_row["semantic_group_id"] == projected.provenance.semantic_group_id
            and provenance_row["semantic_group_id"] not in HELD_GROUP_IDS,
            "D-106 group provenance drifted",
        )
        vector = embeddings[entry.memory_id]
        _require(
            isinstance(vector, list) and len(vector) == VECTOR_DIMENSION,
            "D-106 stored vector dimension drifted",
        )
        _require(
            all(math.isfinite(float(value)) for value in vector),
            "D-106 stored vector invalid",
        )
        vector_sha = sha256_bytes(_float32_row_bytes(vector))
        _require(
            identity_row["embedding_float32_sha256"] == vector_sha,
            "D-106 stored vector identity drifted",
        )

    authority = payload.get("authority", {})
    _require(
        authority.get("memory_index_build_authorized") is True
        and authority.get("actual_memory_entry_count") == 3
        and authority.get("embedding_count") == 3
        and authority.get("memory_index_built") is True
        and authority.get("memory_index_frozen") is False
        and authority.get("index_freeze_authorized") is False
        and authority.get("retrieval_ready") is False
        and authority.get("retrieval_experiment_authorized") is False
        and authority.get("core_campaign_unlocked") is False,
        "D-106 index authority widened or drifted",
    )
    return {
        "index_id": index_version,
        "entries": len(entries),
        "embeddings": len(embeddings),
        "content_hash": content_hash,
        "frozen": False,
        "retrieval_ready": False,
    }


def validate_d106_group_index_file(
    index_path: str | Path,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(index_path, repository=repo, label="group-aware index")
    content = _read_stable(selected, label="group-aware index")
    payload = _parse_json(content, label="group-aware index")
    validation = validate_d106_group_index_payload(payload, repository=repo)
    _require(content == _pretty_json(payload), "D-106 index JSON is not canonical")
    _require(
        not (selected.parent / "FROZEN").exists(),
        "D-106 index has an unauthorized FROZEN marker",
    )
    return {
        "path": selected.relative_to(repo).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        **validation,
    }


def _preflight_exact_output(path: Path, content: bytes, *, repository: Path) -> None:
    d105.preflight_d105_exact_output(path, content, repository=repository)


def materialize_d106_group_index(
    payload: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
    portable_directory: str | Path = DEFAULT_PORTABLE_INDEX_DIRECTORY,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    validation = validate_d106_group_index_payload(payload, repository=repo)
    index_id = validation["index_id"]
    content = _pretty_json(payload)
    portable_root = _resolved(
        portable_directory, repository=repo, label="portable index directory"
    )
    portable_path = portable_root / f"{index_id}.json"
    runtime_path = repo / ".patchloop" / "memory" / "indexes" / index_id / "index.json"
    _preflight_exact_output(portable_path, content, repository=repo)
    _preflight_exact_output(runtime_path, content, repository=repo)
    _require(
        not (runtime_path.parent / "FROZEN").exists(),
        "D-106 runtime target already has an unauthorized FROZEN marker",
    )
    portable_write = _write_exact(portable_path, content, repository=repo)
    runtime_write = _write_exact(runtime_path, content, repository=repo)
    _require(
        not (runtime_path.parent / "FROZEN").exists(),
        "D-106 runtime index was unexpectedly frozen",
    )
    return {
        "index_id": index_id,
        "portable_index": {
            "path": portable_path.relative_to(repo).as_posix(),
            **portable_write,
        },
        "runtime_index": {
            "path": runtime_path.relative_to(repo).as_posix(),
            **runtime_write,
        },
        "frozen_marker_created": False,
    }


def build_d106_completion_gate(
    portable_index_path: str | Path,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Build portable evidence for the completed but deliberately unfrozen index."""

    repo = _repo_root(repository)
    material = _load_authorized_material(repo)
    approval = validate_d106_approval_receipt(repository=repo)
    preflight = validate_d106_preflight_report(repository=repo)
    index = validate_d106_group_index_file(portable_index_path, repository=repo)
    portable_path = _resolved(
        portable_index_path, repository=repo, label="portable group-aware index"
    )
    index_payload = _parse_json(
        _read_stable(portable_path, label="portable group-aware index"),
        label="portable group-aware index",
    )
    build_contract = index_payload["build_contract"]
    _require(
        build_contract["d105_gate"] == material["d105_gate"],
        "D-106 index D-105 gate binding drifted",
    )
    _require(
        build_contract["approval_receipt"] == approval,
        "D-106 index approval receipt binding drifted",
    )
    _require(
        build_contract["embedding_preflight"]["preflight_id"]
        == preflight["preflight_id"],
        "D-106 index preflight binding drifted",
    )
    runtime_path = (
        Path(".patchloop")
        / "memory"
        / "indexes"
        / index["index_id"]
        / "index.json"
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "locked-snapshot-group-aware-unfrozen-index-completion-gate",
        "recorded_at": GATE_RECORDED_AT,
        "d105_gate": material["d105_gate"],
        "approval_receipt": approval,
        "embedding_preflight": preflight,
        "source_collection_id": material["source_collection_id"],
        "source_set_hash": material["source_set_hash"],
        "render_set_hash": material["render_set_hash"],
        "dataset": material["dataset"],
        "index": {
            **index,
            "schema_version": INDEX_SCHEMA_VERSION,
            "builder_schema_version": INDEX_BUILD_SCHEMA_VERSION,
            "portable_copy_is_reproduction_evidence": True,
            "runtime_path": runtime_path.as_posix(),
            "runtime_copy_materialized_during_build": True,
            "runtime_copy_required_for_portable_validation": False,
            "frozen_marker_created": False,
        },
        "held_group_ids": list(HELD_GROUP_IDS),
        "implementation_files": [
            _file_binding(path, repository=repo, label="D-106 implementation")
            for path in IMPLEMENTATION_PATHS
        ],
        "evidence_boundary": {
            "embedding_input": "exact-d105-render-bytes",
            "legacy_failure_builder_called": False,
            "legacy_entry_embedding_text_called": False,
            "snapshot_payload_checked_into_repository": False,
            "snapshot_manifest_and_hashes_checked_in": True,
            "offline_library_mode_verified": True,
            "operating_system_network_block_verified": False,
            "provider_exact_token_budget_validated": False,
            "provider_request_or_response_bodies_read": False,
            "private_or_evaluator_bodies_read": False,
            "historical_index_state_modified": False,
        },
        "authority": {
            "d105_exact_gate_approved": True,
            "approval_receipt_present": True,
            "approval_receipt_self_attested": True,
            "reviewer_identity_authenticated": False,
            "cryptographic_signature_verified": False,
            "embedding_snapshot_verified": True,
            "group_aware_builder_implemented": True,
            "admitted_semantic_group_count": 3,
            "held_group_count": 2,
            "actual_memory_entry_count": 3,
            "embedding_count": 3,
            "d106_created_index_count": 1,
            "memory_index_build_authorized": True,
            "memory_index_built": True,
            "memory_index_frozen": False,
            "index_freeze_authorized": False,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "provider_exact_budget_validated": False,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "memory_effect_established": False,
            "negative_transfer_established": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": (
            "provider-exact-token-delta-index-validation-and-explicit-freeze-authorization"
        ),
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "gate_id": f"d106_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def validate_d106_completion_gate(
    gate_path: str | Path = DEFAULT_GATE_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(gate_path, repository=repo, label="D-106 completion gate")
    content = _read_stable(selected, label="D-106 completion gate")
    parsed = _parse_json(content, label="D-106 completion gate")
    index_path = parsed.get("semantic_body", {}).get("index", {}).get("path")
    _require(isinstance(index_path, str), "D-106 completion gate index path is invalid")
    expected = build_d106_completion_gate(index_path, repository=repo)
    _require(content == _pretty_json(expected), "D-106 completion gate exact bytes drifted")
    _require(parsed == expected, "D-106 completion gate semantic content drifted")
    authority = expected["semantic_body"]["authority"]
    return {
        "ok": True,
        "schema_version": expected["schema_version"],
        "gate_id": expected["gate_id"],
        "semantic_body_hash": expected["semantic_body_hash"],
        "gate_file_bytes": len(content),
        "gate_file_sha256": sha256_bytes(content),
        "index_id": expected["semantic_body"]["index"]["index_id"],
        "actual_memory_entry_count": authority["actual_memory_entry_count"],
        "embedding_count": authority["embedding_count"],
        "memory_index_built": authority["memory_index_built"],
        "memory_index_frozen": authority["memory_index_frozen"],
        "retrieval_ready": authority["retrieval_ready"],
        "core_campaign_unlocked": authority["core_campaign_unlocked"],
    }


def run_d106_authorized_build(
    *,
    repository: str | Path | None = None,
    snapshot_directory: str | Path = DEFAULT_SNAPSHOT_DIRECTORY,
    download_snapshot: bool = True,
) -> dict[str, Any]:
    """Execute the one approved local preflight and unfrozen three-group build."""

    repo = _repo_root(repository)
    receipt = materialize_d106_approval_receipt(repository=repo)
    snapshot_path = _resolved(
        snapshot_directory, repository=repo, label="snapshot directory"
    )
    snapshot_validation: dict[str, Any] | None = None
    if snapshot_path.is_dir():
        try:
            snapshot_validation = validate_d106_snapshot_files(snapshot_path)
        except D106IndexError:
            snapshot_validation = None
    if snapshot_validation is None:
        _require(download_snapshot, "D-106 exact snapshot is absent and download is disabled")
        snapshot_validation = download_d106_snapshot(
            snapshot_path,
            repository=repo,
        )

    preflight_payload, vectors = run_d106_embedding_preflight(
        snapshot_path,
        repository=repo,
    )
    preflight_content = _pretty_json(preflight_payload)
    preflight_path = _resolved(
        DEFAULT_PREFLIGHT_PATH, repository=repo, label="embedding preflight"
    )
    preflight_write = _write_exact(preflight_path, preflight_content, repository=repo)
    preflight = validate_d106_preflight_report(repository=repo)

    index_payload = build_d106_group_index(vectors, repository=repo)
    materialized = materialize_d106_group_index(index_payload, repository=repo)
    portable_index_path = materialized["portable_index"]["path"]
    index_validation = validate_d106_group_index_file(
        portable_index_path, repository=repo
    )

    gate_payload = build_d106_completion_gate(portable_index_path, repository=repo)
    gate_content = _pretty_json(gate_payload)
    gate_path = _resolved(DEFAULT_GATE_PATH, repository=repo, label="D-106 completion gate")
    gate_write = _write_exact(gate_path, gate_content, repository=repo)
    gate = validate_d106_completion_gate(repository=repo)
    return {
        "receipt": receipt,
        "snapshot": snapshot_validation,
        "preflight": {**preflight, **preflight_write},
        "index": {**materialized, **index_validation},
        "gate": {**gate, **gate_write},
        "frozen": False,
        "retrieval_ready": False,
        "core_campaign_unlocked": False,
    }
