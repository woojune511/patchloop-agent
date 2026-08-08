"""D-107 portable index validation and no-call token-count planning.

This module deliberately stops before every externally authorized boundary. It
rebuilds the exact D-106 portable index from its stored vectors, prepares the
two Responses input-token-count payloads required by the D-105 policy, and
seals an offline source gate. It never loads the embedding model, reads the
runtime ``.patchloop`` index copy, constructs a real OpenAI client, calls a
provider, freezes an index, runs retrieval, or starts a core experiment.
"""

from __future__ import annotations

import importlib.metadata
import json
import math
import stat
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml
from pydantic import ValidationError

from patchloop.agent.context import build_context_with_evidence
from patchloop.agent.model import SYSTEM_PROMPT_V3, OpenAIResponsesAdapter
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Budget, DatasetRole, ModelConfig, PublicTask
from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.memory import d105_renderer_authorization as d105
from patchloop.memory import d106_locked_group_index as d106
from patchloop.runtime import repository_root
from patchloop.util import (
    canonical_json,
    sha256_bytes,
    sha256_json,
    sha256_text,
)

MILESTONE = "D-107"
PORTABLE_REPORT_SCHEMA_VERSION = "portable-group-index-validation-d107-v1"
TOKEN_PLAN_SCHEMA_VERSION = "provider-memory-token-count-plan-d107-v1"
TOKEN_RECEIPT_SCHEMA_VERSION = "provider-memory-token-count-receipt-d107-v1"
GATE_SCHEMA_VERSION = "portable-index-token-count-source-gate-d107-v1"

PORTABLE_RECORDED_AT = "2026-08-06T09:00:00Z"
TOKEN_PLAN_RECORDED_AT = "2026-08-06T09:05:00Z"
GATE_RECORDED_AT = "2026-08-06T09:10:00Z"
DOCS_OBSERVED_AT = "2026-08-06T08:50:00Z"

EXPECTED_D106_GATE_ID = "d106_fc2eeb0800e72d4aa0f7331110baf46caaa848879306454a4e0e6476e8fbe9a8"
EXPECTED_D106_BODY_SHA = "sha256:fc2eeb0800e72d4aa0f7331110baf46caaa848879306454a4e0e6476e8fbe9a8"
EXPECTED_D106_GATE_BYTES = 8_709
EXPECTED_D106_GATE_FILE_SHA = (
    "sha256:3ac34d27b4eab1facbeb86adb1e37de8927fa312f9e2b68a03e8f39c19008ea7"
)
EXPECTED_D106_INDEX_ID = "idxgrp_563976c4443a725e287225cef1e718daf134fbb96574921cb9e020049ea52064"
EXPECTED_D106_INDEX_BYTES = 55_644
EXPECTED_D106_INDEX_FILE_SHA = (
    "sha256:c9b292f67fcb3c4bf524065801681e76c5df22142bbbb8b2db36d3c932df358a"
)
EXPECTED_D106_INDEX_CONTENT_HASH = (
    "sha256:86dbd991fa411bc43a8ec65927630fe8ad3365a1a41d9a6eafdeb036d9aab3fd"
)

EXPECTED_MEMORY_BUNDLE_BYTES = 3_528
EXPECTED_MEMORY_BUNDLE_SHA = (
    "sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf"
)
EXPECTED_MEMORY_IDS = (
    "memgrp_649483b80292fea26e4009ebdb72df31",
    "memgrp_b421547d481faabf9be3511217258de5",
    "memgrp_5a23f463cba43bf3ba395f67cf976047",
)
EXPECTED_GROUP_IDS = (
    "platform-emulation-matrix-gap",
    "request-context-propagation-gap",
    "exception-origin-state-conflation",
)

PROVIDER_MODEL_ID = "gpt-5.4-mini-2026-03-17"
PROVIDER_SDK_VERSION = "2.47.0"
CONTEXT_POLICY_VERSION = "phase-evidence-v5"
MAX_OUTPUT_TOKENS = 25_000
MEMORY_TOKEN_LIMIT = 2_000
COUNT_ENDPOINT = "POST /v1/responses/input_tokens"
COUNT_SDK_METHOD = "client.responses.input_tokens.count"
COUNT_GUIDE_URL = "https://developers.openai.com/api/docs/guides/token-counting"
COUNT_REFERENCE_URL = (
    "https://developers.openai.com/api/reference/python/resources/responses/"
    "subresources/input_tokens/methods/count"
)

CARRIER_TASK_ID = "moto-query-scanned-count"
CARRIER_PUBLIC_PATH = Path("tasks/dev-validation/moto-query-scanned-count/public.yaml")
CARRIER_PUBLIC_SPEC_HASH = "sha256:15b4c9f378d48ae8eadbfad1a375d367fc973c230abf0996c617282ca0df8ea7"
DATASET_MANIFEST_PATH = Path("data/dataset-manifest.yaml")

DEFAULT_PORTABLE_REPORT_PATH = Path(
    "reports/memory-development/d107-portable-index-validation.json"
)
DEFAULT_TOKEN_PLAN_PATH = Path("reports/memory-development/d107-provider-token-count-plan.json")
DEFAULT_GATE_PATH = Path(
    "reports/memory-development/d107-portable-index-token-count-source-gate.json"
)
DEFAULT_ARTIFACT_DIRECTORY = Path("reports/memory-development/artifacts/d107")
DEFAULT_D106_GATE_PATH = d106.DEFAULT_GATE_PATH
DEFAULT_D106_INDEX_PATH = d106.DEFAULT_PORTABLE_INDEX_DIRECTORY / f"{EXPECTED_D106_INDEX_ID}.json"

ARTIFACT_NAMES = {
    "baseline_context": "baseline-context.json",
    "with_memory_context": "with-memory-context.json",
    "baseline_full_request": "baseline-full-request.json",
    "with_memory_full_request": "with-memory-full-request.json",
    "baseline_count_request": "baseline-count-request.json",
    "with_memory_count_request": "with-memory-count-request.json",
}

D106_BOUND_IMPLEMENTATION_PATHS = tuple(d106.IMPLEMENTATION_PATHS)
D107_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d107_portable_index_freeze_readiness.py"),
    Path("scripts/build_d107_portable_index_freeze_readiness.py"),
    Path("tests/test_d107_portable_index_freeze_readiness.py"),
)


class D107ReadinessError(ContractError):
    """Raised when the D-107 offline contract fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D107ReadinessError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        return selected.resolve()
    except OSError as exc:
        raise D107ReadinessError("D-107 repository root cannot be resolved") from exc


def _is_linklike(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse and attributes & reparse)


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
        resolved = selected.resolve()
    except OSError as exc:
        raise D107ReadinessError(f"D-107 {label} cannot be resolved") from exc
    _require(
        resolved.is_relative_to(repository),
        f"D-107 {label} escapes the repository",
    )
    if must_exist:
        _require(resolved.is_file(), f"D-107 {label} is unavailable")
    _require(not _is_linklike(selected), f"D-107 {label} cannot be a link or junction")
    return resolved


def _read_stable(path: Path, *, label: str) -> bytes:
    _require(not _is_linklike(path), f"D-107 {label} cannot be a link or junction")
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except OSError as exc:
        raise D107ReadinessError(f"D-107 {label} is unavailable") from exc
    _require(first == second, f"D-107 {label} changed while being read")
    return first


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D107ReadinessError(f"D-107 {label} JSON is invalid") from exc
    _require(isinstance(payload, dict), f"D-107 {label} JSON root is invalid")
    return payload


def _pretty_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _render_context(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def _file_binding(path: str | Path, *, repository: Path, label: str) -> dict[str, Any]:
    selected = _resolved(path, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _content_binding(
    path: Path,
    content: bytes,
    *,
    repository: Path,
    semantic_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    selected = _resolved(
        path,
        repository=repository,
        label="prospective D-107 artifact",
        must_exist=False,
    )
    binding = {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }
    if semantic_payload is not None:
        binding["semantic_payload_sha256"] = sha256_text(canonical_json(semantic_payload))
    return binding


def _write_exact(path: Path, content: bytes, *, repository: Path) -> dict[str, Any]:
    return d105.write_d105_new_exact(path, content, repository=repository)


def _preflight_exact(path: Path, content: bytes, *, repository: Path) -> None:
    d105.preflight_d105_exact_output(path, content, repository=repository)


def _validate_root_identity(
    payload: Mapping[str, Any],
    *,
    schema_version: str,
    id_field: str,
    id_prefix: str,
    label: str,
) -> None:
    _require(payload.get("schema_version") == schema_version, f"D-107 {label} schema drifted")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), f"D-107 {label} body is invalid")
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload.get("semantic_body_hash") == body_hash
        and payload.get(id_field) == f"{id_prefix}{body_hash.removeprefix('sha256:')}",
        f"D-107 {label} identity drifted",
    )


def _validate_pinned_d106_gate_content(
    content: bytes,
    *,
    repository: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _require(
        len(content) == EXPECTED_D106_GATE_BYTES,
        "D-107 D-106 gate byte count drifted",
    )
    _require(
        sha256_bytes(content) == EXPECTED_D106_GATE_FILE_SHA,
        "D-107 D-106 gate file hash drifted",
    )
    parsed = _parse_json(content, label="D-106 completion gate")
    _require(content == _pretty_json(parsed), "D-107 D-106 gate JSON is not canonical")
    _require(
        parsed.get("schema_version") == d106.GATE_SCHEMA_VERSION
        and parsed.get("gate_id") == EXPECTED_D106_GATE_ID
        and parsed.get("semantic_body_hash") == EXPECTED_D106_BODY_SHA,
        "D-107 D-106 gate external identity drifted",
    )
    body = parsed.get("semantic_body")
    _require(isinstance(body, dict), "D-107 D-106 gate body is invalid")
    _require(
        sha256_text(canonical_json(body)) == EXPECTED_D106_BODY_SHA,
        "D-107 D-106 gate semantic hash drifted",
    )
    expected_paths = [path.as_posix() for path in D106_BOUND_IMPLEMENTATION_PATHS]
    implementation = body.get("implementation_files")
    _require(
        isinstance(implementation, list)
        and [row.get("path") for row in implementation] == expected_paths,
        "D-107 D-106 implementation binding set drifted",
    )
    for row in implementation:
        _require(
            row
            == _file_binding(
                row["path"],
                repository=repository,
                label="D-106 bound implementation",
            ),
            "D-107 D-106 implementation bytes drifted",
        )
    authority = body.get("authority", {})
    _require(
        authority.get("memory_index_built") is True
        and authority.get("actual_memory_entry_count") == 3
        and authority.get("embedding_count") == 3
        and authority.get("memory_index_frozen") is False
        and authority.get("index_freeze_authorized") is False
        and authority.get("retrieval_ready") is False
        and authority.get("retrieval_experiment_authorized") is False
        and authority.get("runtime_memory_injection_count") == 0
        and authority.get("provider_exact_budget_validated") is False
        and authority.get("core_campaign_unlocked") is False
        and authority.get("analysis_ready") is False,
        "D-107 D-106 authority widened or drifted",
    )
    index = body.get("index")
    _require(isinstance(index, dict), "D-107 D-106 index descriptor is invalid")
    _require(
        index.get("path") == DEFAULT_D106_INDEX_PATH.as_posix()
        and index.get("file_bytes") == EXPECTED_D106_INDEX_BYTES
        and index.get("file_sha256") == EXPECTED_D106_INDEX_FILE_SHA
        and index.get("index_id") == EXPECTED_D106_INDEX_ID
        and index.get("content_hash") == EXPECTED_D106_INDEX_CONTENT_HASH
        and index.get("entries") == 3
        and index.get("embeddings") == 3
        and index.get("frozen") is False
        and index.get("retrieval_ready") is False
        and index.get("runtime_copy_required_for_portable_validation") is False,
        "D-107 D-106 index descriptor drifted",
    )
    return parsed, index


def _load_pinned_d106_gate(repository: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = _resolved(
        DEFAULT_D106_GATE_PATH,
        repository=repository,
        label="D-106 completion gate",
    )
    return _validate_pinned_d106_gate_content(
        _read_stable(path, label="D-106 completion gate"),
        repository=repository,
    )


def _load_exact_portable_index(repository: Path) -> tuple[dict[str, Any], bytes]:
    directory = _resolved(
        DEFAULT_D106_INDEX_PATH,
        repository=repository,
        label="D-106 portable index",
    ).parent
    _require(not _is_linklike(directory), "D-107 portable index directory is linked")
    try:
        names = sorted(item.name for item in directory.iterdir())
    except OSError as exc:
        raise D107ReadinessError("D-107 portable index directory is unavailable") from exc
    _require(
        names == [DEFAULT_D106_INDEX_PATH.name],
        "D-107 portable index directory has missing or extra artifacts",
    )
    _require(
        not (directory / "FROZEN").exists(),
        "D-107 portable index has an unauthorized FROZEN marker",
    )
    selected = directory / DEFAULT_D106_INDEX_PATH.name
    content = _read_stable(selected, label="D-106 portable index")
    _require(
        len(content) == EXPECTED_D106_INDEX_BYTES,
        "D-107 portable index byte count drifted",
    )
    _require(
        sha256_bytes(content) == EXPECTED_D106_INDEX_FILE_SHA,
        "D-107 portable index file hash drifted",
    )
    payload = _parse_json(content, label="D-106 portable index")
    _require(content == _pretty_json(payload), "D-107 portable index JSON is not canonical")
    _require(
        payload.get("index_version") == EXPECTED_D106_INDEX_ID
        and payload.get("content_hash") == EXPECTED_D106_INDEX_CONTENT_HASH
        and payload.get("frozen") is False,
        "D-107 portable index identity or state drifted",
    )
    return payload, content


def build_d107_portable_validation(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Rebuild the portable D-106 index without runtime state or model weights."""

    repo = _repo_root(repository)
    gate, descriptor = _load_pinned_d106_gate(repo)
    payload, content = _load_exact_portable_index(repo)
    embeddings = payload.get("embeddings")
    _require(isinstance(embeddings, dict), "D-107 portable embedding map is invalid")
    rebuilt = d106.build_d106_group_index(embeddings, repository=repo)
    rebuilt_content = _pretty_json(rebuilt)
    _require(
        rebuilt_content == content and rebuilt == payload,
        "D-107 portable index does not exactly rebuild from stored vectors",
    )
    _require(
        descriptor["file_sha256"] == sha256_bytes(rebuilt_content),
        "D-107 rebuilt index differs from the D-106 gate binding",
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "portable-d106-group-index-offline-rebuild-validation",
        "recorded_at": PORTABLE_RECORDED_AT,
        "d106_gate": {
            "path": DEFAULT_D106_GATE_PATH.as_posix(),
            "schema_version": gate["schema_version"],
            "gate_id": gate["gate_id"],
            "semantic_body_hash": gate["semantic_body_hash"],
            "file_bytes": EXPECTED_D106_GATE_BYTES,
            "file_sha256": EXPECTED_D106_GATE_FILE_SHA,
        },
        "portable_index": {
            "path": DEFAULT_D106_INDEX_PATH.as_posix(),
            "index_id": payload["index_version"],
            "file_bytes": len(content),
            "file_sha256": sha256_bytes(content),
            "content_hash": payload["content_hash"],
            "entry_count": len(payload["entries"]),
            "embedding_count": len(payload["embeddings"]),
            "memory_ids": list(payload["embeddings"]),
            "semantic_group_ids": [row["semantic_group_id"] for row in payload["group_provenance"]],
            "frozen": payload["frozen"],
        },
        "validation": {
            "external_d106_gate_anchor": "pass",
            "current_d106_implementation_file_bindings": "pass",
            "portable_directory_exact_file_set": "pass",
            "canonical_index_json": "pass",
            "stored_vector_full_index_rebuild": "pass",
            "rebuilt_bytes_equal_portable_bytes": True,
            "admitted_group_order_exact": (
                [row["semantic_group_id"] for row in payload["group_provenance"]]
                == list(EXPECTED_GROUP_IDS)
            ),
            "held_group_in_index": False,
            "frozen_marker_present": False,
        },
        "evidence_boundary": {
            "runtime_dot_patchloop_index_required": False,
            "runtime_dot_patchloop_index_read": False,
            "embedding_snapshot_required": False,
            "embedding_model_loaded": False,
            "provider_request_made": False,
            "provider_response_read": False,
            "retrieval_called": False,
            "freeze_called": False,
            "private_or_evaluator_body_read": False,
        },
        "authority": {
            "portable_index_validated": True,
            "provider_exact_budget_validated": False,
            "index_freeze_authorized": False,
            "memory_index_frozen": False,
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
    _require(
        body["portable_index"]["memory_ids"] == list(EXPECTED_MEMORY_IDS)
        and body["portable_index"]["semantic_group_ids"] == list(EXPECTED_GROUP_IDS),
        "D-107 portable group or memory order drifted",
    )
    _require(
        body["validation"]["admitted_group_order_exact"] is True,
        "D-107 admitted group order drifted",
    )
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": PORTABLE_REPORT_SCHEMA_VERSION,
        "validation_id": f"d107portable_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _deep_diff_pointers(left: Any, right: Any, *, pointer: str = "") -> list[str]:
    if type(left) is not type(right):
        return [pointer or "/"]
    if isinstance(left, dict):
        if list(left) != list(right):
            return [pointer or "/"]
        differences: list[str] = []
        for key in left:
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            differences.extend(
                _deep_diff_pointers(
                    left[key],
                    right[key],
                    pointer=f"{pointer}/{escaped}",
                )
            )
        return differences
    if isinstance(left, list):
        if len(left) != len(right):
            return [pointer or "/"]
        differences = []
        for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
            differences.extend(
                _deep_diff_pointers(
                    left_item,
                    right_item,
                    pointer=f"{pointer}/{index}",
                )
            )
        return differences
    return [] if left == right else [pointer or "/"]


def _exact_memory_bundle(index_payload: Mapping[str, Any]) -> str:
    texts = index_payload.get("model_facing_text")
    _require(isinstance(texts, dict), "D-107 model-facing memory map is invalid")
    _require(list(texts) == list(EXPECTED_MEMORY_IDS), "D-107 memory text order drifted")
    _require(
        all(isinstance(value, str) and value.endswith("\n") for value in texts.values()),
        "D-107 memory text entry framing drifted",
    )
    bundle = d105.RENDER_SEPARATOR.join(value.removesuffix("\n") for value in texts.values()) + "\n"
    try:
        content = bundle.encode("ascii")
    except UnicodeEncodeError as exc:
        raise D107ReadinessError("D-107 memory bundle is not ASCII") from exc
    _require(
        len(content) == EXPECTED_MEMORY_BUNDLE_BYTES
        and sha256_bytes(content) == EXPECTED_MEMORY_BUNDLE_SHA,
        "D-107 exact D-105 memory bundle drifted",
    )
    return bundle


def _load_carrier_task(repository: Path) -> tuple[PublicTask, dict[str, Any]]:
    manifest, manifest_hash, manifest_path = load_dataset_manifest(
        repository / DATASET_MANIFEST_PATH
    )
    _require(
        manifest_hash == d106.DATASET_MANIFEST_HASH,
        "D-107 dataset manifest hash drifted",
    )
    development = [
        entry for entry in manifest.tasks if entry.role == DatasetRole.DEVELOPMENT_VALIDATION
    ]
    _require(
        development
        and development[0].task_id == CARRIER_TASK_ID
        and development[0].path == CARRIER_PUBLIC_PATH.parent.as_posix()
        and development[0].public_spec_hash == CARRIER_PUBLIC_SPEC_HASH,
        "D-107 canonical carrier task order or identity drifted",
    )
    public_path = _resolved(
        CARRIER_PUBLIC_PATH,
        repository=repository,
        label="D-107 public carrier task",
    )
    content = _read_stable(public_path, label="D-107 public carrier task")
    try:
        raw = yaml.safe_load(content.decode("utf-8"))
        task = PublicTask.model_validate(raw)
    except (UnicodeDecodeError, yaml.YAMLError, ValidationError) as exc:
        raise D107ReadinessError("D-107 public carrier task is invalid") from exc
    public_hash = sha256_json(task.model_dump(mode="json"))
    _require(
        task.task_id == CARRIER_TASK_ID
        and task.split == "dev-validation"
        and public_hash == CARRIER_PUBLIC_SPEC_HASH,
        "D-107 public carrier task semantic identity drifted",
    )
    return task, {
        "selection": "first-admitted-development-validation-task-in-frozen-manifest-order",
        "task_id": task.task_id,
        "task_version": task.task_version,
        "split": task.split,
        "path": public_path.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "public_spec_hash": public_hash,
        "dataset_manifest": {
            "path": manifest_path.relative_to(repository).as_posix(),
            "semantic_hash": manifest_hash,
        },
        "events": [],
        "checkpoint": None,
        "public_spec_only_read": True,
        "private_spec_read": False,
    }


def _build_context_pair(
    task: PublicTask,
    memory_bundle: str,
) -> tuple[str, str, dict[str, Any]]:
    budget = Budget(
        max_model_calls=None,
        max_tool_calls=None,
        max_total_tokens=3_000_000,
        wall_clock_timeout_seconds=3_600,
    )
    with tempfile.TemporaryDirectory(prefix="patchloop-d107-context-") as temporary:
        artifact_store = ArtifactStore(temporary)
        common = {
            "policy_version": CONTEXT_POLICY_VERSION,
            "artifact_store": artifact_store,
            "budget": budget,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "model_provider": "openai",
        }
        baseline = build_context_with_evidence(task, [], None, "", **common)
        with_memory = build_context_with_evidence(
            task,
            [],
            None,
            memory_bundle,
            **common,
        )
    baseline_payload = json.loads(baseline.rendered)
    memory_payload = json.loads(with_memory.rendered)
    pointers = _deep_diff_pointers(baseline_payload, memory_payload)
    _require(
        pointers == ["/selected_memory"],
        "D-107 canonical contexts differ outside /selected_memory",
    )
    _require(
        baseline_payload.get("selected_memory") is None
        and memory_payload.get("selected_memory") == memory_bundle,
        "D-107 selected-memory slot values drifted",
    )
    normalized = dict(memory_payload)
    normalized["selected_memory"] = None
    _require(
        _render_context(normalized) == baseline.rendered,
        "D-107 contexts are not byte-identical after slot normalization",
    )
    return (
        baseline.rendered,
        with_memory.rendered,
        {
            "allowed_deep_diff_json_pointers": ["/selected_memory"],
            "observed_deep_diff_json_pointers": pointers,
            "baseline_selected_memory": None,
            "with_memory_matches_exact_bundle": True,
            "byte_identical_after_slot_normalization": True,
            "baseline_context_sha256": baseline.content_hash,
            "with_memory_context_sha256": with_memory.content_hash,
            "baseline_context_characters": len(baseline.rendered),
            "with_memory_context_characters": len(with_memory.rendered),
        },
    )


def _model_config() -> ModelConfig:
    return ModelConfig(
        provider="openai",
        model_id=PROVIDER_MODEL_ID,
        reasoning_effort="medium",
        reasoning_mode="standard",
        service_tier="default",
        transport_max_retries=0,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )


def _normalize_request_context(
    request: Mapping[str, Any],
    *,
    baseline_context: str,
) -> dict[str, Any]:
    normalized = json.loads(canonical_json(request))
    input_items = normalized.get("input")
    _require(
        isinstance(input_items, list)
        and len(input_items) == 2
        and input_items[0].get("role") == "system"
        and input_items[1].get("role") == "user",
        "D-107 Responses input envelope drifted",
    )
    input_items[1]["content"] = baseline_context
    return normalized


def _request_pair(
    baseline_context: str,
    with_memory_context: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    client = SimpleNamespace(max_retries=0)
    adapter = OpenAIResponsesAdapter(_model_config(), client=client)
    baseline_full = adapter.request_payload(
        baseline_context,
        TOOL_SCHEMAS_V2,
        system_prompt=SYSTEM_PROMPT_V3,
    )
    memory_full = adapter.request_payload(
        with_memory_context,
        TOOL_SCHEMAS_V2,
        system_prompt=SYSTEM_PROMPT_V3,
    )
    _require(
        _normalize_request_context(
            memory_full,
            baseline_context=baseline_context,
        )
        == json.loads(canonical_json(baseline_full)),
        "D-107 full requests differ after context-slot normalization",
    )
    baseline_count = OpenAIResponsesAdapter._token_count_payload(baseline_full)
    memory_count = OpenAIResponsesAdapter._token_count_payload(memory_full)
    _require(
        list(baseline_count) == ["model", "input", "tools", "reasoning", "truncation"]
        and list(memory_count) == list(baseline_count),
        "D-107 token-count endpoint payload field set drifted",
    )
    _require(
        _normalize_request_context(
            memory_count,
            baseline_context=baseline_context,
        )
        == json.loads(canonical_json(baseline_count)),
        "D-107 count requests differ after context-slot normalization",
    )
    return baseline_full, memory_full, baseline_count, memory_count


def build_d107_token_count_plan(
    *,
    repository: str | Path | None = None,
    artifact_directory: str | Path = DEFAULT_ARTIFACT_DIRECTORY,
) -> tuple[dict[str, Any], dict[Path, bytes]]:
    """Build exact request artifacts without constructing or calling a provider."""

    repo = _repo_root(repository)
    _load_pinned_d106_gate(repo)
    index_payload, _ = _load_exact_portable_index(repo)
    memory_bundle = _exact_memory_bundle(index_payload)
    task, carrier = _load_carrier_task(repo)
    baseline_context, memory_context, context_validation = _build_context_pair(
        task,
        memory_bundle,
    )
    baseline_full, memory_full, baseline_count, memory_count = _request_pair(
        baseline_context,
        memory_context,
    )
    sdk_version = importlib.metadata.version("openai")
    _require(sdk_version == PROVIDER_SDK_VERSION, "D-107 OpenAI SDK version drifted")
    root = Path(artifact_directory)
    artifacts: dict[Path, bytes] = {
        root / ARTIFACT_NAMES["baseline_context"]: baseline_context.encode("utf-8"),
        root / ARTIFACT_NAMES["with_memory_context"]: memory_context.encode("utf-8"),
        root / ARTIFACT_NAMES["baseline_full_request"]: _pretty_json(baseline_full),
        root / ARTIFACT_NAMES["with_memory_full_request"]: _pretty_json(memory_full),
        root / ARTIFACT_NAMES["baseline_count_request"]: _pretty_json(baseline_count),
        root / ARTIFACT_NAMES["with_memory_count_request"]: _pretty_json(memory_count),
    }
    request_payloads: dict[str, Mapping[str, Any]] = {
        "baseline_context": json.loads(baseline_context),
        "with_memory_context": json.loads(memory_context),
        "baseline_full_request": baseline_full,
        "with_memory_full_request": memory_full,
        "baseline_count_request": baseline_count,
        "with_memory_count_request": memory_count,
    }
    artifact_bindings = {
        key: _content_binding(
            root / ARTIFACT_NAMES[key],
            artifacts[root / ARTIFACT_NAMES[key]],
            repository=repo,
            semantic_payload=request_payloads[key],
        )
        for key in ARTIFACT_NAMES
    }
    runtime_bindings = {
        "context_builder": _file_binding(
            "patchloop/agent/context.py",
            repository=repo,
            label="D-107 context builder",
        ),
        "model_adapter": _file_binding(
            "patchloop/agent/model.py",
            repository=repo,
            label="D-107 model adapter",
        ),
        "tool_schemas": _file_binding(
            "patchloop/agent/tools.py",
            repository=repo,
            label="D-107 tool schemas",
        ),
        "dependency_lock": _file_binding(
            "uv.lock",
            repository=repo,
            label="D-107 dependency lock",
        ),
    }
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "exact-responses-input-token-count-no-call-execution-plan",
        "recorded_at": TOKEN_PLAN_RECORDED_AT,
        "d106_gate": {
            "gate_id": EXPECTED_D106_GATE_ID,
            "semantic_body_hash": EXPECTED_D106_BODY_SHA,
            "file_bytes": EXPECTED_D106_GATE_BYTES,
            "file_sha256": EXPECTED_D106_GATE_FILE_SHA,
        },
        "portable_index": {
            "index_id": EXPECTED_D106_INDEX_ID,
            "file_bytes": EXPECTED_D106_INDEX_BYTES,
            "file_sha256": EXPECTED_D106_INDEX_FILE_SHA,
            "content_hash": EXPECTED_D106_INDEX_CONTENT_HASH,
            "memory_ids": list(EXPECTED_MEMORY_IDS),
            "semantic_group_ids": list(EXPECTED_GROUP_IDS),
        },
        "carrier_context": carrier,
        "memory_bundle": {
            "entry_count": 3,
            "file_bytes": len(memory_bundle.encode("ascii")),
            "file_sha256": sha256_bytes(memory_bundle.encode("ascii")),
            "entry_separator": d105.RENDER_SEPARATOR,
            "whole_entry_only": True,
            "partial_truncation_allowed": False,
        },
        "runtime_tuple": {
            "model": PROVIDER_MODEL_ID,
            "reasoning_effort": "medium",
            "reasoning_mode": "standard",
            "service_tier": "default",
            "transport_max_retries": 0,
            "system_prompt_version": "SYSTEM_PROMPT_V3",
            "system_prompt_sha256": sha256_text(SYSTEM_PROMPT_V3),
            "tool_schema_version": "v2",
            "tool_schema_count": len(TOOL_SCHEMAS_V2),
            "tool_schema_sha256": sha256_text(canonical_json(TOOL_SCHEMAS_V2)),
            "context_policy_version": CONTEXT_POLICY_VERSION,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "budget": {
                "max_model_calls": None,
                "max_tool_calls": None,
                "max_total_tokens": 3_000_000,
                "wall_clock_timeout_seconds": 3_600,
            },
            "openai_sdk_version": sdk_version,
            "store": False,
            "previous_response_id": None,
            "truncation": "disabled",
        },
        "runtime_source_bindings": runtime_bindings,
        "context_pair": {
            **context_validation,
            "baseline_artifact": artifact_bindings["baseline_context"],
            "with_memory_artifact": artifact_bindings["with_memory_context"],
        },
        "full_request_pair": {
            "baseline_artifact": artifact_bindings["baseline_full_request"],
            "with_memory_artifact": artifact_bindings["with_memory_full_request"],
            "baseline_semantic_hash": sha256_text(canonical_json(baseline_full)),
            "with_memory_semantic_hash": sha256_text(canonical_json(memory_full)),
            "equal_after_context_slot_normalization": True,
            "responses_create_calls_planned": 0,
        },
        "count_request_pair": {
            "endpoint": COUNT_ENDPOINT,
            "sdk_method": COUNT_SDK_METHOD,
            "exact_payload_fields": [
                "model",
                "input",
                "tools",
                "reasoning",
                "truncation",
            ],
            "baseline_artifact": artifact_bindings["baseline_count_request"],
            "with_memory_artifact": artifact_bindings["with_memory_count_request"],
            "baseline_semantic_hash": sha256_text(canonical_json(baseline_count)),
            "with_memory_semantic_hash": sha256_text(canonical_json(memory_count)),
            "equal_after_context_slot_normalization": True,
            "call_order": ["baseline", "with_memory"],
        },
        "official_documentation_observation": {
            "observed_at": DOCS_OBSERVED_AT,
            "guide_url": COUNT_GUIDE_URL,
            "api_reference_url": COUNT_REFERENCE_URL,
            "endpoint": COUNT_ENDPOINT,
            "response_object": "response.input_tokens",
            "response_input_tokens_type": "integer",
            "documentation_signature_or_snapshot_verified": False,
        },
        "future_execution_contract": {
            "separate_exact_gate_approval_required": True,
            "input_token_count_calls": 2,
            "generation_calls": 0,
            "sdk_transport_max_retries": 0,
            "automatic_retry_allowed": False,
            "first_or_second_call_failure_yields_no_delta": True,
            "response_fields_retained": ["object", "input_tokens"],
            "request_hashes_retained": True,
            "api_key_read_from_host_only": True,
            "api_key_persisted_in_artifact": False,
            "billing_or_free_tier_claim": None,
        },
        "unobserved_counts": {
            "baseline_input_tokens": None,
            "with_memory_input_tokens": None,
            "memory_delta_tokens": None,
            "maximum_memory_delta_tokens": MEMORY_TOKEN_LIMIT,
            "provider_exact_budget_validated": False,
            "provider_receipt_present": False,
        },
        "authority": {
            "request_pair_prepared": True,
            "provider_input_token_count_calls_authorized": False,
            "provider_input_token_count_calls_made": 0,
            "provider_generation_calls_authorized": False,
            "provider_generation_calls_made": 0,
            "provider_exact_budget_validated": False,
            "index_freeze_authorized": False,
            "memory_index_frozen": False,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
    }
    body_hash = sha256_text(canonical_json(body))
    return (
        {
            "schema_version": TOKEN_PLAN_SCHEMA_VERSION,
            "plan_id": f"d107plan_{body_hash.removeprefix('sha256:')}",
            "semantic_body_hash": body_hash,
            "semantic_body": body,
        },
        artifacts,
    )


def validate_d107_token_count_plan_payload(
    payload: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    _validate_root_identity(
        payload,
        schema_version=TOKEN_PLAN_SCHEMA_VERSION,
        id_field="plan_id",
        id_prefix="d107plan_",
        label="token-count plan",
    )
    expected, artifacts = build_d107_token_count_plan(repository=repo)
    _require(payload == expected, "D-107 token-count plan semantic content drifted")
    for path, expected_content in artifacts.items():
        selected = _resolved(path, repository=repo, label="D-107 request artifact")
        _require(
            _read_stable(selected, label="D-107 request artifact") == expected_content,
            "D-107 request artifact bytes drifted",
        )
    body = expected["semantic_body"]
    return {
        "ok": True,
        "plan_id": expected["plan_id"],
        "semantic_body_hash": expected["semantic_body_hash"],
        "request_artifact_count": len(artifacts),
        "provider_calls_made": body["authority"]["provider_input_token_count_calls_made"],
        "provider_exact_budget_validated": body["authority"]["provider_exact_budget_validated"],
        "index_freeze_authorized": body["authority"]["index_freeze_authorized"],
    }


def validate_d107_token_count_plan(
    plan_path: str | Path = DEFAULT_TOKEN_PLAN_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(plan_path, repository=repo, label="D-107 token-count plan")
    content = _read_stable(selected, label="D-107 token-count plan")
    payload = _parse_json(content, label="D-107 token-count plan")
    validation = validate_d107_token_count_plan_payload(payload, repository=repo)
    _require(content == _pretty_json(payload), "D-107 token-count plan is not canonical")
    return {
        "path": selected.relative_to(repo).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        **validation,
    }


def validate_d107_future_provider_receipt(
    receipt: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a future two-count receipt without performing either call."""

    _validate_root_identity(
        plan,
        schema_version=TOKEN_PLAN_SCHEMA_VERSION,
        id_field="plan_id",
        id_prefix="d107plan_",
        label="receipt token-count plan",
    )
    _validate_root_identity(
        receipt,
        schema_version=TOKEN_RECEIPT_SCHEMA_VERSION,
        id_field="receipt_id",
        id_prefix="d107countreceipt_",
        label="provider token-count receipt",
    )
    body = receipt["semantic_body"]
    plan_content = _pretty_json(plan)
    _require(
        body.get("plan")
        == {
            "plan_id": plan["plan_id"],
            "semantic_body_hash": plan["semantic_body_hash"],
            "file_sha256": sha256_bytes(plan_content),
        },
        "D-107 provider receipt plan binding drifted",
    )
    calls = body.get("calls")
    _require(isinstance(calls, list) and len(calls) == 2, "D-107 receipt call set drifted")
    count_pair = plan["semantic_body"]["count_request_pair"]
    expected = (
        ("baseline", count_pair["baseline_artifact"]),
        ("with_memory", count_pair["with_memory_artifact"]),
    )
    counts: list[int] = []
    for order, (call, (label, binding)) in enumerate(
        zip(calls, expected, strict=True),
        start=1,
    ):
        response = call.get("response")
        _require(isinstance(response, dict), "D-107 receipt response is invalid")
        count = response.get("input_tokens")
        _require(
            call.get("order") == order
            and call.get("label") == label
            and call.get("request_file_sha256") == binding["file_sha256"]
            and call.get("request_semantic_hash") == count_pair[f"{label}_semantic_hash"]
            and response.get("object") == "response.input_tokens"
            and type(count) is int
            and count >= 0,
            "D-107 receipt call identity or response drifted",
        )
        counts.append(count)
    delta = d105.validate_d105_provider_budget_delta(counts[0], counts[1])
    _require(
        body.get("baseline_input_tokens") == counts[0]
        and body.get("with_memory_input_tokens") == counts[1]
        and body.get("memory_delta_tokens") == delta
        and body.get("provider_input_token_count_calls_made") == 2
        and body.get("provider_generation_calls_made") == 0
        and body.get("sdk_transport_max_retries") == 0
        and body.get("automatic_retry_used") is False
        and body.get("api_key_persisted_in_artifact") is False
        and body.get("provider_exact_budget_validated") is True
        and body.get("index_freeze_authorized") is False,
        "D-107 receipt outcome or authority drifted",
    )
    return {
        "ok": True,
        "baseline_input_tokens": counts[0],
        "with_memory_input_tokens": counts[1],
        "memory_delta_tokens": delta,
        "provider_exact_budget_validated": True,
        "index_freeze_authorized": False,
    }


def _artifact_set_for_plan(
    plan: Mapping[str, Any],
    artifacts: Mapping[Path, bytes],
) -> dict[Path, bytes]:
    return {
        **dict(artifacts),
        DEFAULT_TOKEN_PLAN_PATH: _pretty_json(plan),
    }


def build_d107_source_gate(
    portable_report: Mapping[str, Any],
    token_plan: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    _validate_root_identity(
        portable_report,
        schema_version=PORTABLE_REPORT_SCHEMA_VERSION,
        id_field="validation_id",
        id_prefix="d107portable_",
        label="portable validation report",
    )
    _validate_root_identity(
        token_plan,
        schema_version=TOKEN_PLAN_SCHEMA_VERSION,
        id_field="plan_id",
        id_prefix="d107plan_",
        label="token-count plan",
    )
    portable_content = _pretty_json(portable_report)
    plan_content = _pretty_json(token_plan)
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "portable-index-validation-and-token-count-no-call-source-gate",
        "recorded_at": GATE_RECORDED_AT,
        "d106_gate": {
            "gate_id": EXPECTED_D106_GATE_ID,
            "semantic_body_hash": EXPECTED_D106_BODY_SHA,
            "file_bytes": EXPECTED_D106_GATE_BYTES,
            "file_sha256": EXPECTED_D106_GATE_FILE_SHA,
        },
        "portable_index_validation": {
            "path": DEFAULT_PORTABLE_REPORT_PATH.as_posix(),
            "validation_id": portable_report["validation_id"],
            "semantic_body_hash": portable_report["semantic_body_hash"],
            "file_bytes": len(portable_content),
            "file_sha256": sha256_bytes(portable_content),
            "portable_index_validated": True,
            "runtime_index_required": False,
            "runtime_index_read": False,
        },
        "provider_token_count_plan": {
            "path": DEFAULT_TOKEN_PLAN_PATH.as_posix(),
            "plan_id": token_plan["plan_id"],
            "semantic_body_hash": token_plan["semantic_body_hash"],
            "file_bytes": len(plan_content),
            "file_sha256": sha256_bytes(plan_content),
            "prepared_request_count": 2,
            "provider_counts": None,
            "provider_receipt": None,
        },
        "implementation_files": [
            _file_binding(path, repository=repo, label="D-107 implementation")
            for path in D107_IMPLEMENTATION_PATHS
        ],
        "evidence_boundary": {
            "official_token_count_endpoint": COUNT_ENDPOINT,
            "provider_api_key_read": False,
            "provider_client_constructed": False,
            "provider_input_token_count_calls_made": 0,
            "provider_generation_calls_made": 0,
            "provider_response_body_read": False,
            "embedding_model_loaded": False,
            "runtime_dot_patchloop_index_read": False,
            "private_or_evaluator_body_read": False,
            "retrieval_called": False,
            "freeze_called": False,
        },
        "authority": {
            "portable_index_validated": True,
            "token_count_execution_plan_prepared": True,
            "provider_input_token_count_calls_authorized": False,
            "provider_input_token_count_calls_made": 0,
            "provider_generation_calls_authorized": False,
            "provider_generation_calls_made": 0,
            "provider_exact_budget_validated": False,
            "provider_token_count_receipt_present": False,
            "freeze_authorization_preconditions_defined": True,
            "index_freeze_authorization_candidate_ready": False,
            "index_freeze_authorized": False,
            "memory_index_frozen": False,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "memory_effect_established": False,
            "negative_transfer_established": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": ("exact-d107-source-gate-approval-for-two-provider-input-token-count-calls"),
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "gate_id": f"d107_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def run_d107_offline_source_gate(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Materialize the complete D-107 no-call source gate atomically by preflight."""

    repo = _repo_root(repository)
    portable_report = build_d107_portable_validation(repository=repo)
    token_plan, request_artifacts = build_d107_token_count_plan(repository=repo)
    gate = build_d107_source_gate(portable_report, token_plan, repository=repo)
    outputs: dict[Path, bytes] = {
        DEFAULT_PORTABLE_REPORT_PATH: _pretty_json(portable_report),
        **_artifact_set_for_plan(token_plan, request_artifacts),
        DEFAULT_GATE_PATH: _pretty_json(gate),
    }
    for path, content in outputs.items():
        _preflight_exact(path, content, repository=repo)
    writes: dict[str, dict[str, Any]] = {}
    for path, content in outputs.items():
        writes[path.as_posix()] = _write_exact(path, content, repository=repo)
    return {
        "portable_validation_id": portable_report["validation_id"],
        "token_plan_id": token_plan["plan_id"],
        "gate_id": gate["gate_id"],
        "gate_semantic_body_hash": gate["semantic_body_hash"],
        "gate_file_sha256": sha256_bytes(outputs[DEFAULT_GATE_PATH]),
        "request_artifact_count": len(request_artifacts),
        "writes": writes,
        "provider_calls_made": 0,
        "memory_index_frozen": False,
        "retrieval_ready": False,
        "core_campaign_unlocked": False,
    }


def validate_d107_source_gate(
    gate_path: str | Path = DEFAULT_GATE_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Deeply rebuild all D-107 source evidence without external calls."""

    repo = _repo_root(repository)
    selected = _resolved(gate_path, repository=repo, label="D-107 source gate")
    content = _read_stable(selected, label="D-107 source gate")
    parsed = _parse_json(content, label="D-107 source gate")
    _validate_root_identity(
        parsed,
        schema_version=GATE_SCHEMA_VERSION,
        id_field="gate_id",
        id_prefix="d107_",
        label="source gate",
    )
    portable_report = build_d107_portable_validation(repository=repo)
    plan, request_artifacts = build_d107_token_count_plan(repository=repo)
    expected = build_d107_source_gate(portable_report, plan, repository=repo)
    _require(content == _pretty_json(expected), "D-107 source gate exact bytes drifted")
    _require(parsed == expected, "D-107 source gate semantic content drifted")
    portable_path = _resolved(
        DEFAULT_PORTABLE_REPORT_PATH,
        repository=repo,
        label="D-107 portable validation report",
    )
    _require(
        _read_stable(portable_path, label="D-107 portable validation report")
        == _pretty_json(portable_report),
        "D-107 portable validation report drifted",
    )
    plan_path = _resolved(
        DEFAULT_TOKEN_PLAN_PATH,
        repository=repo,
        label="D-107 token-count plan",
    )
    _require(
        _read_stable(plan_path, label="D-107 token-count plan") == _pretty_json(plan),
        "D-107 token-count plan drifted",
    )
    for path, expected_content in request_artifacts.items():
        artifact_path = _resolved(path, repository=repo, label="D-107 request artifact")
        _require(
            _read_stable(artifact_path, label="D-107 request artifact") == expected_content,
            "D-107 request artifact drifted",
        )
    authority = expected["semantic_body"]["authority"]
    _require(
        authority["portable_index_validated"] is True
        and authority["provider_input_token_count_calls_made"] == 0
        and authority["provider_exact_budget_validated"] is False
        and authority["index_freeze_authorized"] is False
        and authority["memory_index_frozen"] is False
        and authority["retrieval_ready"] is False
        and authority["core_campaign_unlocked"] is False,
        "D-107 source gate authority widened",
    )
    return {
        "ok": True,
        "schema_version": expected["schema_version"],
        "gate_id": expected["gate_id"],
        "semantic_body_hash": expected["semantic_body_hash"],
        "gate_file_bytes": len(content),
        "gate_file_sha256": sha256_bytes(content),
        "portable_validation_id": portable_report["validation_id"],
        "token_plan_id": plan["plan_id"],
        "request_artifact_count": len(request_artifacts),
        "provider_calls_made": 0,
        "provider_exact_budget_validated": False,
        "index_freeze_authorized": False,
        "memory_index_frozen": False,
        "retrieval_ready": False,
        "core_campaign_unlocked": False,
    }


def portable_vector_norms(
    index_payload: Mapping[str, Any],
) -> dict[str, float]:
    """Return deterministic validation diagnostics without changing the index."""

    embeddings = index_payload.get("embeddings")
    _require(isinstance(embeddings, dict), "D-107 embedding map is invalid")
    norms: dict[str, float] = {}
    for memory_id, values in embeddings.items():
        _require(
            isinstance(values, Sequence) and not isinstance(values, (str, bytes)),
            "D-107 embedding row is invalid",
        )
        row = [float(value) for value in values]
        _require(
            len(row) == d106.VECTOR_DIMENSION and all(math.isfinite(value) for value in row),
            "D-107 embedding row shape or finiteness drifted",
        )
        norm = math.sqrt(sum(value * value for value in row))
        _require(abs(norm - 1.0) <= 1e-5, "D-107 embedding row is not normalized")
        norms[str(memory_id)] = norm
    return norms


__all__ = [
    "D107ReadinessError",
    "build_d107_portable_validation",
    "build_d107_source_gate",
    "build_d107_token_count_plan",
    "portable_vector_norms",
    "run_d107_offline_source_gate",
    "validate_d107_future_provider_receipt",
    "validate_d107_source_gate",
    "validate_d107_token_count_plan",
    "validate_d107_token_count_plan_payload",
]
