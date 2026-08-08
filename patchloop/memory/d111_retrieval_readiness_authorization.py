"""Seal the D-111 frozen-index retrieval-readiness candidate offline.

D-111 does not call the legacy retriever, encode a query, render memory into an
agent context, or authorize a core experiment.  It validates the portable
D-110 freeze evidence, audits the currently sealed retrieval implementation,
and binds a later, separately approved, read-only local scoring probe.
"""

from __future__ import annotations

import json
import math
import os
import re
import stat
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from patchloop.contracts import MemoryEntry, Phase, PublicTask
from patchloop.errors import ContractError
from patchloop.memory import d106_locked_group_index as d106
from patchloop.memory import d107_portable_index_freeze_readiness as d107
from patchloop.memory import d110_index_freeze_execution as d110
from patchloop.memory.store import entry_embedding_text
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

MILESTONE = "D-111"
PREFLIGHT_SCHEMA_VERSION = "frozen-index-retrieval-readiness-preflight-d111-v1"
CANDIDATE_SCHEMA_VERSION = "retrieval-readiness-authorization-candidate-d111-v1"
PROBE_ACTION_SCHEMA_VERSION = "exact-group-retrieval-readiness-probe-d111-v1"
SOURCE_GATE_SCHEMA_VERSION = "retrieval-readiness-authorization-source-gate-d111-v1"

PREFLIGHT_RECORDED_AT = "2026-08-07T00:00:00Z"
CANDIDATE_RECORDED_AT = "2026-08-07T00:05:00Z"
GATE_RECORDED_AT = "2026-08-07T00:10:00Z"

EXPECTED_D110_GATE_ID = "d110_bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736"
EXPECTED_D110_GATE_BODY_SHA = (
    "sha256:bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736"
)
EXPECTED_D110_GATE_BYTES = 7_754
EXPECTED_D110_GATE_FILE_SHA = (
    "sha256:79578db09955dab2a22b015ba5210baec28e7d30b9cac818b1f2c6d6eac782cd"
)
EXPECTED_FROZEN_INDEX_BYTES = 55_687
EXPECTED_FROZEN_INDEX_FILE_SHA = (
    "sha256:c0d2ec424e6cc10d64cdebd5ae493e0546fdfa08d09eb5f3269557b46025c6d0"
)
EXPECTED_FROZEN_CONTENT_HASH = (
    "sha256:3a99e6c190672d1676bc4d13604de989899de9ddac85d282cc90c4d56f426c56"
)
EXPECTED_FROZEN_MARKER_BYTES = 72
EXPECTED_FROZEN_MARKER_FILE_SHA = (
    "sha256:cdfe40b734135a30f66e34ff24469940063a7231a1fe0783420ee2ff816d9561"
)
EXPECTED_UNFROZEN_INDEX_BYTES = d107.EXPECTED_D106_INDEX_BYTES
EXPECTED_UNFROZEN_INDEX_FILE_SHA = d107.EXPECTED_D106_INDEX_FILE_SHA
EXPECTED_MEMORY_IDS = tuple(d107.EXPECTED_MEMORY_IDS)
EXPECTED_GROUP_IDS = tuple(d107.EXPECTED_GROUP_IDS)
EXPECTED_HELD_GROUP_IDS = tuple(d106.HELD_GROUP_IDS)
EXPECTED_MODEL = d106.MODEL_ID
EXPECTED_MODEL_REVISION = d106.MODEL_REVISION
EXPECTED_SNAPSHOT_MANIFEST_HASH = (
    "sha256:e497d8dad53f09ddc8b9fcc9b81e3ff778e002e120ab4254c72993d8611959cb"
)
EXPECTED_VECTOR_SET_HASH = "sha256:5f4cf40d0512092ed68fdfa05a1d0ad9b0d2ad7a2f3fd6f6ca078adfcac2fc81"
EXPECTED_RENDER_SET_HASH = "sha256:7b72fc94642d996fad5a0b199719c56bfecc8a8fc1bbe42b2060aa18e21d2667"
EXPECTED_MEMORY_BUNDLE_BYTES = d107.EXPECTED_MEMORY_BUNDLE_BYTES
EXPECTED_MEMORY_BUNDLE_SHA = d107.EXPECTED_MEMORY_BUNDLE_SHA

SCORE_WEIGHTS = {
    "semantic": 0.35,
    "failure_class": 0.25,
    "phase": 0.15,
    "language": 0.15,
    "validation": 0.10,
}
SELECTIVE_THRESHOLD = 0.72
MEMORY_TOKEN_BUDGET = 2_000
OBSERVED_FULL_BUNDLE_PROVIDER_DELTA_TOKENS = 702

DEFAULT_PREFLIGHT_PATH = Path(
    "reports/memory-development/d111-frozen-index-retrieval-readiness-preflight.json"
)
DEFAULT_CANDIDATE_PATH = Path(
    "reports/memory-development/d111-retrieval-readiness-authorization-candidate.json"
)
DEFAULT_SOURCE_GATE_PATH = Path(
    "reports/memory-development/d111-retrieval-readiness-authorization-source-gate.json"
)
DEFAULT_FROZEN_INDEX_PATH = d110.DEFAULT_PORTABLE_FROZEN_INDEX_PATH
DEFAULT_FROZEN_MARKER_PATH = d110.DEFAULT_PORTABLE_FROZEN_MARKER_PATH
DEFAULT_UNFROZEN_INDEX_PATH = d107.DEFAULT_D106_INDEX_PATH
RETRIEVAL_IMPLEMENTATION_PATH = Path("patchloop/memory/retrieval.py")

D111_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d111_retrieval_readiness_authorization.py"),
    Path("scripts/build_d111_retrieval_readiness_authorization_candidate.py"),
    Path("tests/test_d111_retrieval_readiness_authorization.py"),
)

FUTURE_D112_PATHS = (
    "patchloop/memory/d112_retrieval_readiness_probe.py",
    "scripts/run_d112_retrieval_readiness_probe.py",
    "tests/test_d112_retrieval_readiness_probe.py",
    "reports/memory-development/d112-retrieval-readiness-probe-receipt.json",
    "reports/memory-development/d112-retrieval-readiness-completion-gate.json",
)

PROBE_SPECS = (
    {
        "probe_id": "moto-implement-positive-hypothesis",
        "task_id": "moto-query-scanned-count",
        "path": "tasks/dev-validation/moto-query-scanned-count/public.yaml",
        "file_bytes": 2_839,
        "file_sha256": ("sha256:4005b070d9e46c72a68554fbe998e9d81e920321a31e8bf633d3fd32277857f7"),
        "public_spec_hash": (
            "sha256:15b4c9f378d48ae8eadbfad1a375d367fc973c230abf0996c617282ca0df8ea7"
        ),
        "phase": "IMPLEMENT",
        "runtime_query_sha256": (
            "sha256:8ad844e48f313b1b86bbc17a14492797e512fec47a5842b834e4302cf7b74f5e"
        ),
        "query_phase_sha256": (
            "sha256:bd143addcb62ae16038b4eb2c8edbec1b15653f6003a999a7e667fc38e95bc17"
        ),
        "hypothesis_kind": "semantic-positive-not-acceptance-criterion",
        "hypothesized_group_id": "platform-emulation-matrix-gap",
    },
    {
        "probe_id": "babel-implement-no-match-control",
        "task_id": "babel-strict-grouped-decimal-trailing-zeroes",
        "path": ("tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml"),
        "file_bytes": 2_023,
        "file_sha256": ("sha256:d65e09fe70bb0449c85e663d0eeb695fe52bc7fb34619debbbe81a0b16ab2aca"),
        "public_spec_hash": (
            "sha256:dd7151171da2a60e2c772fafe7eb53840c335145206016bdc5a4f8f7486cc5cf"
        ),
        "phase": "IMPLEMENT",
        "runtime_query_sha256": (
            "sha256:d400778dbaf3d084d52d7b8c82dfc0dfcbe989dbb241b68e26d38abf42f6f48b"
        ),
        "query_phase_sha256": (
            "sha256:133c56d6b2c92d416ddf2f3e36d45bf6b7c062f7d676911c3e6ee3e358b3d7fb"
        ),
        "hypothesis_kind": "no-match-negative-transfer-control-not-acceptance-criterion",
        "hypothesized_group_id": None,
    },
    {
        "probe_id": "moto-reproduce-phase-control",
        "task_id": "moto-query-scanned-count",
        "path": "tasks/dev-validation/moto-query-scanned-count/public.yaml",
        "file_bytes": 2_839,
        "file_sha256": ("sha256:4005b070d9e46c72a68554fbe998e9d81e920321a31e8bf633d3fd32277857f7"),
        "public_spec_hash": (
            "sha256:15b4c9f378d48ae8eadbfad1a375d367fc973c230abf0996c617282ca0df8ea7"
        ),
        "phase": "REPRODUCE",
        "runtime_query_sha256": (
            "sha256:8ad844e48f313b1b86bbc17a14492797e512fec47a5842b834e4302cf7b74f5e"
        ),
        "query_phase_sha256": (
            "sha256:5e8cae5fa2c4dc1949c5a2a33a6483ca39d790c4389cdd7c6470d78f65e4a0e5"
        ),
        "hypothesis_kind": "phase-sensitivity-control-not-acceptance-criterion",
        "hypothesized_group_id": None,
    },
)


class D111ReadinessError(ContractError):
    """Raised when D-111 evidence or scope drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D111ReadinessError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        return selected.resolve()
    except OSError as exc:
        raise D111ReadinessError("D-111 repository root cannot be resolved") from exc


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
        raise D111ReadinessError(f"D-111 {label} escapes the repository") from exc
    current = selected
    while current != repository and current != current.parent:
        _require(
            not _is_linklike(current),
            f"D-111 {label} cannot traverse a link or junction",
        )
        current = current.parent
    return resolved


def _read_stable(path: Path, *, label: str) -> bytes:
    _require(not _is_linklike(path), f"D-111 {label} cannot be a link or junction")
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except OSError as exc:
        raise D111ReadinessError(f"D-111 {label} is unavailable") from exc
    _require(first == second, f"D-111 {label} changed while being read")
    return first


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D111ReadinessError(f"D-111 {label} JSON is invalid") from exc
    _require(isinstance(payload, dict), f"D-111 {label} JSON root is invalid")
    return payload


def _pretty_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _file_binding(path: Path, *, repository: Path, label: str) -> dict[str, Any]:
    selected = _resolved(path, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _root_identity(
    payload: Mapping[str, Any],
    *,
    schema_version: str,
    id_field: str,
    id_prefix: str,
    label: str,
) -> None:
    _require(payload.get("schema_version") == schema_version, f"D-111 {label} schema drifted")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), f"D-111 {label} body is invalid")
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload.get("semantic_body_hash") == body_hash
        and payload.get(id_field) == f"{id_prefix}{body_hash.removeprefix('sha256:')}",
        f"D-111 {label} identity drifted",
    )


def _artifact_binding(
    payload: Mapping[str, Any],
    content: bytes,
    *,
    path: Path,
    id_field: str,
) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "schema_version": payload["schema_version"],
        id_field: payload[id_field],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _tokens(text: str) -> Counter[str]:
    return Counter(re.findall(r"[a-z0-9_]+", text.lower()))


def _runtime_query(task: PublicTask) -> str:
    return task.issue.title + "\n" + task.issue.description + "\n" + " ".join(task.tags)


def _load_probe_inputs(repository: Path) -> list[dict[str, Any]]:
    tasks: dict[str, tuple[PublicTask, bytes]] = {}
    probes: list[dict[str, Any]] = []
    for spec in PROBE_SPECS:
        task_id = str(spec["task_id"])
        if task_id not in tasks:
            selected = _resolved(spec["path"], repository=repository, label="public probe task")
            content = _read_stable(selected, label="public probe task")
            _require(
                len(content) == spec["file_bytes"] and sha256_bytes(content) == spec["file_sha256"],
                f"D-111 public probe file drifted: {task_id}",
            )
            try:
                raw = yaml.safe_load(content.decode("utf-8"))
                task = PublicTask.model_validate(raw)
            except (UnicodeDecodeError, yaml.YAMLError, ValidationError) as exc:
                raise D111ReadinessError(f"D-111 public probe is invalid: {task_id}") from exc
            _require(
                task.task_id == task_id
                and task.split == "dev-validation"
                and task.repository.language == "python"
                and sha256_json(task.model_dump(mode="json")) == spec["public_spec_hash"],
                f"D-111 public probe semantic identity drifted: {task_id}",
            )
            tasks[task_id] = (task, content)
        task, content = tasks[task_id]
        query = _runtime_query(task)
        phase = Phase(str(spec["phase"]))
        _require(
            sha256_text(query) == spec["runtime_query_sha256"]
            and sha256_text(canonical_json({"query": query, "phase": phase.value}))
            == spec["query_phase_sha256"],
            f"D-111 runtime query identity drifted: {spec['probe_id']}",
        )
        probes.append(
            {
                "probe_id": spec["probe_id"],
                "task_id": task_id,
                "task_version": task.task_version,
                "split": task.split,
                "public_task": {
                    "path": spec["path"],
                    "file_bytes": len(content),
                    "file_sha256": sha256_bytes(content),
                    "public_spec_hash": spec["public_spec_hash"],
                },
                "phase": phase.value,
                "runtime_query_sha256": spec["runtime_query_sha256"],
                "query_phase_sha256": spec["query_phase_sha256"],
                "hypothesis_kind": spec["hypothesis_kind"],
                "hypothesized_group_id": spec["hypothesized_group_id"],
                "hypothesis_is_acceptance_criterion": False,
                "public_spec_only_read": True,
                "private_hidden_reference_or_bad_patch_read": False,
            }
        )
    return probes


def _load_exact_inputs(
    repository: Path,
    *,
    verify_live_runtime: bool = False,
) -> dict[str, Any]:
    d110_result = d110.validate_d110_completion_gate(
        repository=repository,
        verify_live_runtime=verify_live_runtime,
        verify_current_implementation=False,
    )
    _require(
        d110_result["gate_id"] == EXPECTED_D110_GATE_ID
        and d110_result["semantic_body_hash"] == EXPECTED_D110_GATE_BODY_SHA
        and d110_result["file_bytes"] == EXPECTED_D110_GATE_BYTES
        and d110_result["file_sha256"] == EXPECTED_D110_GATE_FILE_SHA
        and d110_result["index_file_sha256"] == EXPECTED_FROZEN_INDEX_FILE_SHA
        and d110_result["content_hash"] == EXPECTED_FROZEN_CONTENT_HASH
        and d110_result["marker_file_sha256"] == EXPECTED_FROZEN_MARKER_FILE_SHA
        and d110_result["retrieval_ready"] is False
        and d110_result["retrieval_experiment_authorized"] is False
        and d110_result["runtime_memory_injection_count"] == 0,
        "D-111 exact D-110 completion gate drifted",
    )
    gate_binding = _file_binding(
        d110.DEFAULT_COMPLETION_GATE_PATH,
        repository=repository,
        label="D-110 completion gate",
    )
    gate_binding.update(
        {
            "gate_id": EXPECTED_D110_GATE_ID,
            "semantic_body_hash": EXPECTED_D110_GATE_BODY_SHA,
        }
    )

    frozen_directory = _resolved(
        DEFAULT_FROZEN_INDEX_PATH.parent,
        repository=repository,
        label="portable frozen index directory",
    )
    _require(
        sorted(item.name for item in frozen_directory.iterdir()) == ["FROZEN", "index.json"],
        "D-111 portable frozen index directory inventory drifted",
    )
    index_path = _resolved(
        DEFAULT_FROZEN_INDEX_PATH,
        repository=repository,
        label="portable frozen index",
    )
    marker_path = _resolved(
        DEFAULT_FROZEN_MARKER_PATH,
        repository=repository,
        label="portable frozen marker",
    )
    index_content = _read_stable(index_path, label="portable frozen index")
    marker_content = _read_stable(marker_path, label="portable frozen marker")
    _require(
        len(index_content) == EXPECTED_FROZEN_INDEX_BYTES
        and sha256_bytes(index_content) == EXPECTED_FROZEN_INDEX_FILE_SHA,
        "D-111 frozen index file identity drifted",
    )
    _require(
        len(marker_content) == EXPECTED_FROZEN_MARKER_BYTES
        and sha256_bytes(marker_content) == EXPECTED_FROZEN_MARKER_FILE_SHA
        and marker_content == (EXPECTED_FROZEN_CONTENT_HASH + "\n").encode("ascii"),
        "D-111 frozen marker identity drifted",
    )
    index = _parse_json(index_content, label="portable frozen index")
    _require(index_content == _pretty_json(index), "D-111 frozen index is not canonical")
    authority = index.get("authority")
    embedding = index.get("embedding")
    _require(isinstance(authority, dict), "D-111 frozen index authority is invalid")
    _require(isinstance(embedding, dict), "D-111 frozen index embedding is invalid")
    _require(
        index.get("index_version") == d110.EXPECTED_INDEX_ID
        and index.get("content_hash") == EXPECTED_FROZEN_CONTENT_HASH
        and index.get("frozen") is True
        and authority.get("memory_index_frozen") is True
        and authority.get("index_freeze_authorized") is True
        and authority.get("retrieval_ready") is False
        and authority.get("retrieval_experiment_authorized") is False
        and authority.get("runtime_memory_injection_count") == 0
        and authority.get("core_campaign_unlocked") is False
        and authority.get("analysis_ready") is False
        and embedding.get("model") == EXPECTED_MODEL
        and embedding.get("revision") == EXPECTED_MODEL_REVISION
        and embedding.get("snapshot_manifest_hash") == EXPECTED_SNAPSHOT_MANIFEST_HASH
        and embedding.get("vector_set_hash") == EXPECTED_VECTOR_SET_HASH,
        "D-111 frozen index semantic or authority state drifted",
    )
    entries = index.get("entries")
    model_text = index.get("model_facing_text")
    _require(isinstance(entries, list) and len(entries) == 3, "D-111 entry count drifted")
    _require(isinstance(model_text, dict) and len(model_text) == 3, "D-111 render count drifted")
    validated_entries = [MemoryEntry.model_validate(item) for item in entries]
    _require(
        tuple(entry.memory_id for entry in validated_entries) == EXPECTED_MEMORY_IDS
        and tuple(row["semantic_group_id"] for row in index["group_provenance"])
        == EXPECTED_GROUP_IDS
        and tuple(index["held_group_ids"]) == EXPECTED_HELD_GROUP_IDS,
        "D-111 frozen semantic group inventory drifted",
    )
    unfrozen_path = _resolved(
        DEFAULT_UNFROZEN_INDEX_PATH,
        repository=repository,
        label="portable D-106 unfrozen index",
    )
    unfrozen_content = _read_stable(unfrozen_path, label="portable D-106 unfrozen index")
    _require(
        len(unfrozen_content) == EXPECTED_UNFROZEN_INDEX_BYTES
        and sha256_bytes(unfrozen_content) == EXPECTED_UNFROZEN_INDEX_FILE_SHA,
        "D-111 portable D-106 unfrozen index drifted",
    )
    return {
        "d110_result": d110_result,
        "d110_gate": gate_binding,
        "index": index,
        "index_content": index_content,
        "index_binding": _file_binding(
            index_path, repository=repository, label="portable frozen index"
        ),
        "marker_binding": _file_binding(
            marker_path, repository=repository, label="portable frozen marker"
        ),
        "unfrozen_binding": _file_binding(
            unfrozen_path, repository=repository, label="portable D-106 unfrozen index"
        ),
        "entries": validated_entries,
        "probes": _load_probe_inputs(repository),
        "live_runtime_verified": verify_live_runtime,
    }


def _audit_legacy_retriever(repository: Path, context: Mapping[str, Any]) -> dict[str, Any]:
    source_path = _resolved(
        RETRIEVAL_IMPLEMENTATION_PATH,
        repository=repository,
        label="legacy retrieval implementation",
    )
    source_content = _read_stable(source_path, label="legacy retrieval implementation")
    try:
        source = source_content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise D111ReadinessError("D-111 retrieval source is not UTF-8") from exc
    required_snippets = (
        'raw.get("authority", {}).get("retrieval_experiment_authorized") is not True',
        "structured = entry_embedding_text(entry)",
        "class_match = _cosine(query, entry.failure_pattern.failure_class)",
        "validation = min(1.0, entry.validation_count / 3)",
        "threshold: float = 0.72",
        "return max(1, math.ceil(len(text) / 4))",
    )
    _require(
        all(snippet in source for snippet in required_snippets),
        "D-111 sealed legacy retrieval observations drifted",
    )
    _require(
        "SentenceTransformer(" in source and "local_files_only" not in source,
        "D-111 legacy query encoder observation drifted",
    )

    index = context["index"]
    probes = context["probes"]
    entries: list[MemoryEntry] = context["entries"]
    model_text: Mapping[str, str] = index["model_facing_text"]
    render_mismatches = []
    for entry in entries:
        legacy = entry_embedding_text(entry)
        exact = model_text[entry.memory_id]
        render_mismatches.append(
            {
                "memory_id": entry.memory_id,
                "legacy_renderer_bytes": len(legacy.encode("utf-8")),
                "legacy_renderer_sha256": sha256_bytes(legacy.encode("utf-8")),
                "d105_exact_renderer_bytes": len(exact.encode("utf-8")),
                "d105_exact_renderer_sha256": sha256_bytes(exact.encode("utf-8")),
                "byte_identical": legacy == exact,
            }
        )
    _require(
        all(row["byte_identical"] is False for row in render_mismatches),
        "D-111 expected legacy/D-105 render mismatch disappeared",
    )

    query_by_hash: dict[str, str] = {}
    for spec in PROBE_SPECS:
        selected = _resolved(spec["path"], repository=repository, label="public probe task")
        task = PublicTask.model_validate(yaml.safe_load(selected.read_text(encoding="utf-8")))
        query_by_hash[str(spec["runtime_query_sha256"])] = _runtime_query(task)
    class_match_matrix: list[dict[str, Any]] = []
    for probe in probes:
        query_tokens = _tokens(query_by_hash[probe["runtime_query_sha256"]])
        for entry in entries:
            class_token = entry.failure_pattern.failure_class.lower()
            class_match_matrix.append(
                {
                    "probe_id": probe["probe_id"],
                    "memory_id": entry.memory_id,
                    "failure_class_token": class_token,
                    "exact_failure_class_token_present_in_public_query": class_token
                    in query_tokens,
                    "observed_current_class_match": 0.0,
                }
            )
    _require(
        all(
            not row["exact_failure_class_token_present_in_public_query"]
            for row in class_match_matrix
        ),
        "D-111 public query unexpectedly contains an internal failure-class label",
    )
    _require(
        all(entry.validation_count == 0 for entry in entries),
        "D-111 validation-count readiness assumption drifted",
    )
    implement_upper_bound = (
        SCORE_WEIGHTS["semantic"] + SCORE_WEIGHTS["phase"] + SCORE_WEIGHTS["language"]
    )
    reproduce_upper_bound = SCORE_WEIGHTS["semantic"] + SCORE_WEIGHTS["language"]
    _require(
        math.isclose(implement_upper_bound, 0.65)
        and math.isclose(reproduce_upper_bound, 0.50)
        and implement_upper_bound < SELECTIVE_THRESHOLD,
        "D-111 selective-score upper-bound proof drifted",
    )
    return {
        "implementation": {
            "path": RETRIEVAL_IMPLEMENTATION_PATH.as_posix(),
            "file_bytes": len(source_content),
            "file_sha256": sha256_bytes(source_content),
            "d110_bound_file": True,
            "modified_by_d111": False,
        },
        "inline_frozen_index_authority_guard_present": True,
        "current_inline_retrieval_authority": False,
        "guard_fails_before_query_embedding": True,
        "locked_local_snapshot_enforced_by_query_encoder": False,
        "d105_exact_model_facing_text_used_by_structured_renderer": False,
        "legacy_and_d105_render_comparison": render_mismatches,
        "raw_trace_uses_mutable_local_state_store": True,
        "raw_trace_portable_contract_ready": False,
        "token_budget_uses_character_divide_by_four_estimate": True,
        "d108_exact_full_bundle_provider_delta_tokens": (
            OBSERVED_FULL_BUNDLE_PROVIDER_DELTA_TOKENS
        ),
        "d108_maximum_memory_delta_tokens": MEMORY_TOKEN_BUDGET,
        "class_match_matrix": class_match_matrix,
        "entry_validation_counts": {entry.memory_id: entry.validation_count for entry in entries},
        "score_weights": dict(SCORE_WEIGHTS),
        "selective_threshold": SELECTIVE_THRESHOLD,
        "perfect_semantic_implement_python_upper_bound": implement_upper_bound,
        "perfect_semantic_reproduce_python_upper_bound": reproduce_upper_bound,
        "natural_public_query_can_reach_selective_threshold": False,
        "synthetic_internal_label_injection_used": False,
        "legacy_retriever_ready": False,
    }


def _validate_recorded_audit(audit: Mapping[str, Any]) -> None:
    _require(
        audit.get("current_inline_retrieval_authority") is False
        and audit.get("guard_fails_before_query_embedding") is True
        and audit.get("locked_local_snapshot_enforced_by_query_encoder") is False
        and audit.get("d105_exact_model_facing_text_used_by_structured_renderer") is False
        and audit.get("raw_trace_portable_contract_ready") is False
        and audit.get("natural_public_query_can_reach_selective_threshold") is False
        and audit.get("legacy_retriever_ready") is False
        and audit.get("score_weights") == SCORE_WEIGHTS
        and audit.get("selective_threshold") == SELECTIVE_THRESHOLD
        and audit.get("perfect_semantic_implement_python_upper_bound") == 0.65,
        "D-111 recorded retrieval audit semantic content drifted",
    )


def build_d111_preflight(
    *,
    repository: str | Path | None = None,
    _context: Mapping[str, Any] | None = None,
    recorded_retrieval_audit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    context = dict(_context) if _context is not None else _load_exact_inputs(repo)
    audit = (
        dict(recorded_retrieval_audit)
        if recorded_retrieval_audit is not None
        else _audit_legacy_retriever(repo, context)
    )
    _validate_recorded_audit(audit)
    index = context["index"]
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "frozen-index-retrieval-readiness-gap-preflight",
        "recorded_at": PREFLIGHT_RECORDED_AT,
        "d110_completion_gate": context["d110_gate"],
        "portable_frozen_index": {
            **context["index_binding"],
            "index_id": index["index_version"],
            "content_hash": index["content_hash"],
            "frozen": True,
            "frozen_at": index["frozen_at"],
        },
        "portable_frozen_marker": context["marker_binding"],
        "portable_d106_unfrozen_index": {
            **context["unfrozen_binding"],
            "unchanged_by_d111": True,
        },
        "memory_material": {
            "memory_ids": list(EXPECTED_MEMORY_IDS),
            "semantic_group_ids": list(EXPECTED_GROUP_IDS),
            "held_group_ids": list(EXPECTED_HELD_GROUP_IDS),
            "model": EXPECTED_MODEL,
            "model_revision": EXPECTED_MODEL_REVISION,
            "snapshot_manifest_hash": EXPECTED_SNAPSHOT_MANIFEST_HASH,
            "vector_set_hash": EXPECTED_VECTOR_SET_HASH,
            "render_set_hash": EXPECTED_RENDER_SET_HASH,
            "full_bundle_bytes": EXPECTED_MEMORY_BUNDLE_BYTES,
            "full_bundle_sha256": EXPECTED_MEMORY_BUNDLE_SHA,
        },
        "public_probe_plan": context["probes"],
        "legacy_retriever_audit": audit,
        "readiness_assessment": {
            "frozen_index_integrity_ready": True,
            "structured_probe_candidate_ready": True,
            "legacy_runtime_retrieval_ready": False,
            "selective_scoring_non_degenerate": False,
            "raw_trace_ready": False,
            "four_condition_retrieval_ready": False,
            "retrieval_experiment_ready": False,
            "core_campaign_ready": False,
        },
        "evidence_boundary": {
            "retrieval_function_called": False,
            "query_embedding_encoded": False,
            "embedding_model_loaded": False,
            "network_accessed": False,
            "runtime_memory_injected": False,
            "agent_run_started": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "index_or_marker_mutations": 0,
            "private_hidden_reference_or_bad_patch_read": False,
            "added_model_cost_usd": 0,
        },
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "preflight_id": f"d111preflight_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def validate_d111_preflight_payload(preflight: Mapping[str, Any]) -> None:
    _root_identity(
        preflight,
        schema_version=PREFLIGHT_SCHEMA_VERSION,
        id_field="preflight_id",
        id_prefix="d111preflight_",
        label="preflight",
    )
    body = preflight["semantic_body"]
    d110_gate = body.get("d110_completion_gate")
    frozen = body.get("portable_frozen_index")
    marker = body.get("portable_frozen_marker")
    unfrozen = body.get("portable_d106_unfrozen_index")
    material = body.get("memory_material")
    assessment = body.get("readiness_assessment")
    boundary = body.get("evidence_boundary")
    probes = body.get("public_probe_plan")
    audit = body.get("legacy_retriever_audit")
    _require(
        isinstance(d110_gate, dict)
        and d110_gate.get("gate_id") == EXPECTED_D110_GATE_ID
        and d110_gate.get("semantic_body_hash") == EXPECTED_D110_GATE_BODY_SHA
        and d110_gate.get("file_bytes") == EXPECTED_D110_GATE_BYTES
        and d110_gate.get("file_sha256") == EXPECTED_D110_GATE_FILE_SHA,
        "D-111 preflight D-110 binding drifted",
    )
    _require(
        isinstance(frozen, dict)
        and frozen.get("path") == DEFAULT_FROZEN_INDEX_PATH.as_posix()
        and frozen.get("file_bytes") == EXPECTED_FROZEN_INDEX_BYTES
        and frozen.get("file_sha256") == EXPECTED_FROZEN_INDEX_FILE_SHA
        and frozen.get("content_hash") == EXPECTED_FROZEN_CONTENT_HASH
        and frozen.get("frozen") is True,
        "D-111 preflight frozen-index binding drifted",
    )
    _require(
        isinstance(marker, dict)
        and marker.get("path") == DEFAULT_FROZEN_MARKER_PATH.as_posix()
        and marker.get("file_bytes") == EXPECTED_FROZEN_MARKER_BYTES
        and marker.get("file_sha256") == EXPECTED_FROZEN_MARKER_FILE_SHA,
        "D-111 preflight frozen-marker binding drifted",
    )
    _require(
        isinstance(unfrozen, dict)
        and unfrozen.get("file_bytes") == EXPECTED_UNFROZEN_INDEX_BYTES
        and unfrozen.get("file_sha256") == EXPECTED_UNFROZEN_INDEX_FILE_SHA
        and unfrozen.get("unchanged_by_d111") is True,
        "D-111 preflight D-106 binding drifted",
    )
    _require(
        isinstance(material, dict)
        and material.get("memory_ids") == list(EXPECTED_MEMORY_IDS)
        and material.get("semantic_group_ids") == list(EXPECTED_GROUP_IDS)
        and material.get("held_group_ids") == list(EXPECTED_HELD_GROUP_IDS)
        and material.get("model") == EXPECTED_MODEL
        and material.get("model_revision") == EXPECTED_MODEL_REVISION
        and material.get("snapshot_manifest_hash") == EXPECTED_SNAPSHOT_MANIFEST_HASH
        and material.get("vector_set_hash") == EXPECTED_VECTOR_SET_HASH
        and material.get("render_set_hash") == EXPECTED_RENDER_SET_HASH
        and material.get("full_bundle_bytes") == EXPECTED_MEMORY_BUNDLE_BYTES
        and material.get("full_bundle_sha256") == EXPECTED_MEMORY_BUNDLE_SHA,
        "D-111 preflight memory-material binding drifted",
    )
    _require(isinstance(probes, list) and len(probes) == 3, "D-111 probe plan drifted")
    for probe, spec in zip(probes, PROBE_SPECS, strict=True):
        _require(
            probe.get("probe_id") == spec["probe_id"]
            and probe.get("task_id") == spec["task_id"]
            and probe.get("phase") == spec["phase"]
            and probe.get("runtime_query_sha256") == spec["runtime_query_sha256"]
            and probe.get("query_phase_sha256") == spec["query_phase_sha256"]
            and probe.get("hypothesis_is_acceptance_criterion") is False
            and probe.get("private_hidden_reference_or_bad_patch_read") is False,
            "D-111 exact public probe plan drifted",
        )
    _require(isinstance(audit, dict), "D-111 retrieval audit is invalid")
    _validate_recorded_audit(audit)
    _require(
        isinstance(assessment, dict)
        and assessment.get("structured_probe_candidate_ready") is True
        and assessment.get("legacy_runtime_retrieval_ready") is False
        and assessment.get("selective_scoring_non_degenerate") is False
        and assessment.get("raw_trace_ready") is False
        and assessment.get("four_condition_retrieval_ready") is False
        and assessment.get("retrieval_experiment_ready") is False
        and assessment.get("core_campaign_ready") is False,
        "D-111 readiness assessment drifted",
    )
    _require(
        isinstance(boundary, dict)
        and boundary.get("retrieval_function_called") is False
        and boundary.get("query_embedding_encoded") is False
        and boundary.get("runtime_memory_injected") is False
        and boundary.get("provider_calls_made") == 0
        and boundary.get("evaluator_calls_made") == 0
        and boundary.get("index_or_marker_mutations") == 0
        and boundary.get("added_model_cost_usd") == 0,
        "D-111 evidence boundary drifted",
    )


def build_d111_authorization_candidate(
    preflight: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    validate_d111_preflight_payload(preflight)
    preflight_content = _pretty_json(preflight)
    assessment = preflight["semantic_body"]["readiness_assessment"]
    _require(
        assessment["structured_probe_candidate_ready"] is True
        and assessment["legacy_runtime_retrieval_ready"] is False
        and assessment["raw_trace_ready"] is False
        and assessment["core_campaign_ready"] is False,
        "D-111 preflight readiness boundary drifted",
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "retrieval-readiness-authorization-candidate",
        "recorded_at": CANDIDATE_RECORDED_AT,
        "preflight": _artifact_binding(
            preflight,
            preflight_content,
            path=DEFAULT_PREFLIGHT_PATH,
            id_field="preflight_id",
        ),
        "candidate_status": "awaiting-exact-user-approval",
        "proposed_one_use_action": {
            "schema_version": PROBE_ACTION_SCHEMA_VERSION,
            "execution_kind": "local-read-only-scoring-diagnostic",
            "maximum_executions": 1,
            "automatic_retry_allowed": False,
            "sidecar_authorization_required": True,
            "frozen_index_mutation_allowed": False,
            "frozen_marker_mutation_allowed": False,
            "d106_unfrozen_index_mutation_allowed": False,
            "legacy_retrieve_memory_call_allowed": False,
            "runtime_memory_injection_allowed": False,
            "agent_context_rendering_allowed": False,
            "agent_run_allowed": False,
            "provider_call_allowed": False,
            "evaluator_call_allowed": False,
            "core_campaign_allowed": False,
            "analysis_campaign_allowed": False,
            "network_access_allowed": False,
            "local_embedding_model_load_count": 1,
            "local_batch_encode_call_count": 1,
            "local_batch_query_row_count": 3,
            "expected_query_vector_shape": [3, 384],
            "expected_query_vector_dtype": "float32",
            "finite_normalized_query_vectors_required": True,
            "device": "cpu",
            "exact_frozen_index_file_sha256": EXPECTED_FROZEN_INDEX_FILE_SHA,
            "exact_frozen_marker_file_sha256": EXPECTED_FROZEN_MARKER_FILE_SHA,
            "exact_embedding_model": EXPECTED_MODEL,
            "exact_embedding_revision": EXPECTED_MODEL_REVISION,
            "exact_snapshot_manifest_hash": EXPECTED_SNAPSHOT_MANIFEST_HASH,
            "query_encoder_requires_local_files_only": True,
            "structured_text_source": "frozen-index-model_facing_text-exact-bytes",
            "raw_trace_in_scope": False,
            "diagnostic_scoring_contract": {
                "query_text": "public-title-newline-description-newline-space-joined-tags",
                "semantic_component": ("max-zero-normalized-query-vector-dot-frozen-entry-vector"),
                "failure_class_tokenizer_regex": "[a-z0-9_]+",
                "failure_class_component": ("counter-cosine-public-query-vs-entry-failure-class"),
                "phase_component": "float-entry-phase-equals-probe-phase",
                "language_component": "float-python-in-entry-applicable-languages",
                "validation_component": "min-one-entry-validation-count-divided-by-three",
                "score_weights": dict(SCORE_WEIGHTS),
                "selective_threshold": SELECTIVE_THRESHOLD,
                "selective_comparator": "greater-than-or-equal",
                "rank_order": "descending-score-then-ascending-memory-id",
                "component_and_final_scores_must_be_recorded": True,
                "scoring_policy_is_diagnostic_not_core_qualification": True,
            },
            "memory_token_budget": MEMORY_TOKEN_BUDGET,
            "probe_ids_in_order": [row["probe_id"] for row in PROBE_SPECS],
            "future_output_paths": list(FUTURE_D112_PATHS),
            "score_policy_correction_allowed": False,
            "threshold_change_allowed": False,
            "memory_entry_change_allowed": False,
        },
        "diagnostic_acceptance": {
            "all_three_public_probe_identities_match": True,
            "local_only_pinned_query_encoder_required": True,
            "component_scores_and_final_score_recorded": True,
            "deterministic_tie_order_by_memory_id_required": True,
            "no_memory_text_returned_or_injected": True,
            "pre_and_post_input_fingerprints_equal": True,
            "observed_ranking_or_selection_must_not_be_precommitted": True,
            "probe_hypotheses_are_not_pass_fail_criteria": True,
            "selective_degeneracy_must_be_reported_not_hidden": True,
        },
        "explicitly_excluded": {
            "synthetic_internal_failure_label_query": True,
            "private_task": True,
            "hidden_tests": True,
            "reference_patch": True,
            "known_bad_patch": True,
            "raw_trace": True,
            "provider_generation": True,
            "runtime_retrieval_integration": True,
            "memory_effect_claim": True,
            "negative_transfer_claim": True,
        },
        "approval_contract": {
            "separate_user_message_required": True,
            "exact_candidate_id_required": True,
            "exact_semantic_body_hash_required": True,
            "exact_file_sha256_required": True,
            "generic_continue_message_is_approval": False,
            "approval_receipt_created_by_d111": False,
        },
        "authority": {
            "retrieval_readiness_candidate_ready": True,
            "exact_candidate_user_approval_received": False,
            "retrieval_probe_authorized": False,
            "retrieval_probe_executed": False,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "raw_trace_ready": False,
            "four_condition_retrieval_ready": False,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "candidate_id": f"d111retrievalcandidate_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def validate_d111_candidate_payload(
    candidate: Mapping[str, Any],
    preflight: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
) -> None:
    _root_identity(
        candidate,
        schema_version=CANDIDATE_SCHEMA_VERSION,
        id_field="candidate_id",
        id_prefix="d111retrievalcandidate_",
        label="candidate",
    )
    expected = build_d111_authorization_candidate(preflight, repository=repository)
    _require(candidate == expected, "D-111 candidate semantic content drifted")


def build_d111_source_gate(
    preflight: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
    implementation_bindings: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    validate_d111_preflight_payload(preflight)
    validate_d111_candidate_payload(candidate, preflight, repository=repo)
    preflight_content = _pretty_json(preflight)
    candidate_content = _pretty_json(candidate)
    bindings = (
        [dict(row) for row in implementation_bindings]
        if implementation_bindings is not None
        else [
            _file_binding(path, repository=repo, label="D-111 implementation")
            for path in D111_IMPLEMENTATION_PATHS
        ]
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "retrieval-readiness-authorization-source-gate",
        "recorded_at": GATE_RECORDED_AT,
        "preflight": _artifact_binding(
            preflight,
            preflight_content,
            path=DEFAULT_PREFLIGHT_PATH,
            id_field="preflight_id",
        ),
        "candidate": _artifact_binding(
            candidate,
            candidate_content,
            path=DEFAULT_CANDIDATE_PATH,
            id_field="candidate_id",
        ),
        "implementation_files": bindings,
        "qualification": {
            "exact_d110_portable_freeze_evidence_validated": True,
            "d106_unfrozen_index_unchanged": True,
            "three_public_dev_validation_probes_bound": True,
            "legacy_retrieval_gaps_recorded": True,
            "selective_score_upper_bound_below_threshold_proved": True,
            "candidate_only_no_approval_receipt": True,
            "retrieval_or_embedding_executed": False,
            "runtime_or_core_boundary_crossed": False,
        },
        "authority": {
            "retrieval_readiness_candidate_ready": True,
            "exact_candidate_user_approval_received": False,
            "retrieval_probe_authorized": False,
            "retrieval_probe_executed": False,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "raw_trace_ready": False,
            "four_condition_retrieval_ready": False,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": "exact-d111-candidate-id-body-sha-file-sha-user-approval",
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": SOURCE_GATE_SCHEMA_VERSION,
        "gate_id": f"d111_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _preflight_output(path: Path, content: bytes, *, repository: Path) -> Path:
    selected = _resolved(
        path,
        repository=repository,
        label="D-111 output",
        must_exist=False,
    )
    selected.parent.mkdir(parents=True, exist_ok=True)
    _require(not _is_linklike(selected.parent), "D-111 output parent cannot be linked")
    if selected.exists():
        _require(
            _read_stable(selected, label="D-111 existing output") == content,
            f"D-111 output already exists with different bytes: {path.as_posix()}",
        )
    return selected


def _write_exact(path: Path, content: bytes) -> None:
    if path.exists():
        _require(path.read_bytes() == content, "D-111 exact retry output drifted")
        return
    try:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise D111ReadinessError("D-111 output write failed") from exc


def run_d111_offline_source_gate(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    context = _load_exact_inputs(repo)
    before = {
        "frozen_index": sha256_bytes(context["index_content"]),
        "frozen_marker": context["marker_binding"]["file_sha256"],
        "unfrozen_index": context["unfrozen_binding"]["file_sha256"],
    }
    preflight = build_d111_preflight(repository=repo, _context=context)
    candidate = build_d111_authorization_candidate(preflight, repository=repo)
    gate = build_d111_source_gate(preflight, candidate, repository=repo)
    outputs = {
        DEFAULT_PREFLIGHT_PATH: _pretty_json(preflight),
        DEFAULT_CANDIDATE_PATH: _pretty_json(candidate),
        DEFAULT_SOURCE_GATE_PATH: _pretty_json(gate),
    }
    selected_outputs = {
        path: _preflight_output(path, content, repository=repo) for path, content in outputs.items()
    }
    for path, content in outputs.items():
        _write_exact(selected_outputs[path], content)
    after_context = _load_exact_inputs(repo)
    after = {
        "frozen_index": sha256_bytes(after_context["index_content"]),
        "frozen_marker": after_context["marker_binding"]["file_sha256"],
        "unfrozen_index": after_context["unfrozen_binding"]["file_sha256"],
    }
    _require(before == after, "D-111 predecessor artifact changed during build")
    validation = validate_d111_source_gate(repository=repo, _context=after_context)
    candidate_content = outputs[DEFAULT_CANDIDATE_PATH]
    return {
        **validation,
        "preflight_id": preflight["preflight_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_semantic_body_hash": candidate["semantic_body_hash"],
        "candidate_file_bytes": len(candidate_content),
        "candidate_file_sha256": sha256_bytes(candidate_content),
        "retrieval_called": False,
        "query_embedding_encoded": False,
        "runtime_memory_injection_count": 0,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "added_model_cost_usd": 0,
    }


def validate_d111_source_gate(
    gate_path: str | Path = DEFAULT_SOURCE_GATE_PATH,
    *,
    repository: str | Path | None = None,
    verify_live_runtime: bool = False,
    verify_current_implementation: bool = False,
    _context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    context = (
        dict(_context)
        if _context is not None
        else _load_exact_inputs(repo, verify_live_runtime=verify_live_runtime)
    )
    _require(
        context.get("live_runtime_verified") is verify_live_runtime,
        "D-111 supplied validation context has the wrong live-runtime scope",
    )
    preflight_path = _resolved(DEFAULT_PREFLIGHT_PATH, repository=repo, label="D-111 preflight")
    candidate_path = _resolved(DEFAULT_CANDIDATE_PATH, repository=repo, label="D-111 candidate")
    selected_gate = _resolved(gate_path, repository=repo, label="D-111 source gate")
    preflight_content = _read_stable(preflight_path, label="D-111 preflight")
    candidate_content = _read_stable(candidate_path, label="D-111 candidate")
    gate_content = _read_stable(selected_gate, label="D-111 source gate")
    preflight = _parse_json(preflight_content, label="D-111 preflight")
    candidate = _parse_json(candidate_content, label="D-111 candidate")
    gate = _parse_json(gate_content, label="D-111 source gate")
    _root_identity(
        preflight,
        schema_version=PREFLIGHT_SCHEMA_VERSION,
        id_field="preflight_id",
        id_prefix="d111preflight_",
        label="preflight",
    )
    _root_identity(
        candidate,
        schema_version=CANDIDATE_SCHEMA_VERSION,
        id_field="candidate_id",
        id_prefix="d111retrievalcandidate_",
        label="candidate",
    )
    _root_identity(
        gate,
        schema_version=SOURCE_GATE_SCHEMA_VERSION,
        id_field="gate_id",
        id_prefix="d111_",
        label="source gate",
    )
    _require(
        preflight_content == _pretty_json(preflight)
        and candidate_content == _pretty_json(candidate)
        and gate_content == _pretty_json(gate),
        "D-111 checked-in artifact is not canonical",
    )
    recorded_audit = preflight["semantic_body"].get("legacy_retriever_audit")
    _require(isinstance(recorded_audit, dict), "D-111 recorded retrieval audit is invalid")
    _validate_recorded_audit(recorded_audit)
    if verify_current_implementation:
        _require(
            recorded_audit == _audit_legacy_retriever(repo, context),
            "D-111 current legacy retriever differs from audited bytes",
        )
    expected_preflight = build_d111_preflight(
        repository=repo,
        _context=context,
        recorded_retrieval_audit=recorded_audit,
    )
    expected_candidate = build_d111_authorization_candidate(
        expected_preflight,
        repository=repo,
    )
    recorded_implementation = gate["semantic_body"].get("implementation_files")
    _require(
        isinstance(recorded_implementation, list)
        and len(recorded_implementation) == len(D111_IMPLEMENTATION_PATHS),
        "D-111 implementation bindings are invalid",
    )
    if verify_current_implementation:
        current = [
            _file_binding(path, repository=repo, label="D-111 implementation")
            for path in D111_IMPLEMENTATION_PATHS
        ]
        _require(
            recorded_implementation == current,
            "D-111 current implementation differs from source-gate binding",
        )
    expected_gate = build_d111_source_gate(
        expected_preflight,
        expected_candidate,
        repository=repo,
        implementation_bindings=recorded_implementation,
    )
    _require(
        preflight == expected_preflight
        and candidate == expected_candidate
        and gate == expected_gate,
        "D-111 source-gate semantic content drifted",
    )
    authority = gate["semantic_body"]["authority"]
    return {
        "ok": True,
        "gate_id": gate["gate_id"],
        "semantic_body_hash": gate["semantic_body_hash"],
        "file_bytes": len(gate_content),
        "file_sha256": sha256_bytes(gate_content),
        "preflight_id": preflight["preflight_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_semantic_body_hash": candidate["semantic_body_hash"],
        "candidate_file_bytes": len(candidate_content),
        "candidate_file_sha256": sha256_bytes(candidate_content),
        "live_runtime_verified": verify_live_runtime,
        "current_implementation_verified": verify_current_implementation,
        "retrieval_readiness_candidate_ready": authority["retrieval_readiness_candidate_ready"],
        "exact_candidate_user_approval_received": False,
        "retrieval_probe_authorized": False,
        "retrieval_probe_executed": False,
        "retrieval_ready": False,
        "retrieval_experiment_authorized": False,
        "runtime_memory_injection_count": 0,
        "raw_trace_ready": False,
        "four_condition_retrieval_ready": False,
        "core_campaign_unlocked": False,
        "analysis_ready": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "added_model_cost_usd": 0,
    }


__all__ = [
    "CANDIDATE_SCHEMA_VERSION",
    "DEFAULT_CANDIDATE_PATH",
    "DEFAULT_PREFLIGHT_PATH",
    "DEFAULT_SOURCE_GATE_PATH",
    "D111ReadinessError",
    "PREFLIGHT_SCHEMA_VERSION",
    "PROBE_ACTION_SCHEMA_VERSION",
    "PROBE_SPECS",
    "SOURCE_GATE_SCHEMA_VERSION",
    "build_d111_authorization_candidate",
    "build_d111_preflight",
    "build_d111_source_gate",
    "run_d111_offline_source_gate",
    "validate_d111_candidate_payload",
    "validate_d111_preflight_payload",
    "validate_d111_source_gate",
]
