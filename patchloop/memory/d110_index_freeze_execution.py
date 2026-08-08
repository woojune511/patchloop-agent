"""Execute the exact D-109 group-index freeze once.

D-110 consumes the maintainer's exact D-109 candidate approval.  It does not
reuse the legacy memory-store freeze helper: the approved transition needs an
exact pre-byte CAS, a one-use journal, two explicit authority mutations, an
approval-bound timestamp, and ordered index/marker commits.

The index replacement and marker creation are ordered per-file operations, not
one two-file transaction.  File contents are flushed before commit; directory
entry flushing is best-effort and platform-dependent.  Any interrupted or
ambiguous state remains fail-closed and is never automatically retried or
rolled back.
"""

from __future__ import annotations

import contextlib
import copy
import json
import os
import stat
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO

from patchloop.errors import ContractError
from patchloop.memory import d109_index_freeze_authorization as d109
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-110"
APPROVAL_SCHEMA_VERSION = "memory-index-freeze-approval-receipt-d110-v1"
JOURNAL_SCHEMA_VERSION = "memory-index-freeze-execution-event-d110-v1"
FREEZE_RECEIPT_SCHEMA_VERSION = "memory-index-freeze-receipt-d110-v1"
COMPLETION_GATE_SCHEMA_VERSION = "memory-index-freeze-completion-gate-d110-v1"

APPROVAL_RECORDED_AT = "2026-08-06T12:42:48Z"
APPROVAL_ACTION_ID = "d110-exact-d109-index-freeze-approval-1"
APPROVAL_REFERENCE = "user-message:d109-exact-index-freeze-approval"
APPROVAL_STATEMENT_CODE = (
    "approve-exact-d109-index-freeze-once-without-retrieval-runtime-injection-or-core"
)
APPROVAL_STATEMENT = (
    "Approve one exact index freeze for the repeated D-109 candidate ID, semantic body SHA, "
    "and file SHA. Do not authorize retrieval, runtime memory injection, or the core campaign."
)

EXPECTED_CANDIDATE_ID = (
    "d109freezecandidate_480d2aa8657fd143397fcfc71f252b8a8e3c0988d3950b5671089cf6dc8b8d46"
)
EXPECTED_CANDIDATE_BODY_SHA = (
    "sha256:480d2aa8657fd143397fcfc71f252b8a8e3c0988d3950b5671089cf6dc8b8d46"
)
EXPECTED_CANDIDATE_BYTES = 5_910
EXPECTED_CANDIDATE_FILE_SHA = (
    "sha256:ae8a8c6e58b058720943bae9088da2cf242168a70f654006557dd84c84d4e580"
)
EXPECTED_D109_GATE_ID = (
    "d109_e37e716aceb0a322820eada8b83d8a309e06052f6060c986f6025c61b7d999ef"
)
EXPECTED_D109_GATE_BODY_SHA = (
    "sha256:e37e716aceb0a322820eada8b83d8a309e06052f6060c986f6025c61b7d999ef"
)
EXPECTED_D109_GATE_BYTES = 3_485
EXPECTED_D109_GATE_FILE_SHA = (
    "sha256:0953687473bd25f48ad52bdc78c577d6a4daa4947b019fcd65809e7548c4f949"
)

EXPECTED_INDEX_ID = d109.EXPECTED_INDEX_ID
DEFAULT_APPROVAL_PATH = Path(
    "reports/memory-development/d110-exact-index-freeze-approval-receipt.json"
)
DEFAULT_JOURNAL_PATH = Path(
    "reports/memory-development/d110-index-freeze-execution.jsonl"
)
DEFAULT_FREEZE_RECEIPT_PATH = Path(
    "reports/memory-development/d110-index-freeze-receipt.json"
)
DEFAULT_COMPLETION_GATE_PATH = Path(
    "reports/memory-development/d110-index-freeze-completion-gate.json"
)
DEFAULT_PORTABLE_FROZEN_DIRECTORY = (
    Path("reports/memory-development/artifacts/d110") / EXPECTED_INDEX_ID
)
DEFAULT_PORTABLE_FROZEN_INDEX_PATH = DEFAULT_PORTABLE_FROZEN_DIRECTORY / "index.json"
DEFAULT_PORTABLE_FROZEN_MARKER_PATH = DEFAULT_PORTABLE_FROZEN_DIRECTORY / "FROZEN"
DEFAULT_RUNTIME_INDEX_PATH = d109.DEFAULT_RUNTIME_INDEX_PATH
DEFAULT_RUNTIME_MARKER_PATH = DEFAULT_RUNTIME_INDEX_PATH.parent / "FROZEN"
DEFAULT_EXECUTION_STATE_DIRECTORY = (
    Path(".patchloop/memory/freeze-state") / EXPECTED_INDEX_ID
)
DEFAULT_EXECUTION_LOCK_PATH = DEFAULT_EXECUTION_STATE_DIRECTORY / "D110.lock"
DEFAULT_STAGED_INDEX_PATH = DEFAULT_EXECUTION_STATE_DIRECTORY / "index.json.staged"

D110_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d110_index_freeze_execution.py"),
    Path("patchloop/memory/store.py"),
    Path("patchloop/memory/retrieval.py"),
    Path("scripts/run_d110_index_freeze.py"),
    Path("tests/test_d110_index_freeze_execution.py"),
    Path("tests/test_memory.py"),
)

ALLOWED_MUTATION_POINTERS = (
    "/frozen",
    "/frozen_at",
    "/authority/index_freeze_authorized",
    "/authority/memory_index_frozen",
    "/content_hash",
)
SUCCESS_EVENT_TYPES = (
    "FreezeExecutionClaimed",
    "RuntimeIndexMutationIssued",
    "RuntimeIndexMutationCommitted",
    "FrozenMarkerWriteIssued",
    "FrozenMarkerWriteCommitted",
    "PortableFreezeEvidenceCommitted",
    "FreezeReceiptCommitted",
    "ExecutionLockReleased",
)
JOURNAL_ROOT_KEYS = {
    "schema_version",
    "sequence",
    "event_type",
    "recorded_at",
    "previous_record_hash",
    "body",
    "record_hash",
}


class D110ExecutionError(ContractError):
    """Raised when the exact D-110 freeze cannot proceed safely."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D110ExecutionError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        return selected.resolve()
    except OSError as exc:
        raise D110ExecutionError("D-110 repository root cannot be resolved") from exc


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
    selected = Path(os.path.abspath(selected))
    try:
        selected.relative_to(repository)
        resolved = selected.resolve(strict=must_exist)
        resolved.relative_to(repository)
    except (OSError, ValueError) as exc:
        raise D110ExecutionError(f"D-110 {label} escapes the repository") from exc
    cursor = selected
    while cursor != repository:
        if cursor.exists() or cursor.is_symlink():
            _require(
                not _is_linklike(cursor),
                f"D-110 {label} cannot traverse a link or junction",
            )
        _require(cursor.parent != cursor, f"D-110 {label} has an invalid parent chain")
        cursor = cursor.parent
    return resolved


def _read_stable(path: Path, *, label: str) -> bytes:
    _require(not _is_linklike(path), f"D-110 {label} cannot be a link or junction")
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except OSError as exc:
        raise D110ExecutionError(f"D-110 {label} is unavailable") from exc
    _require(first == second, f"D-110 {label} changed while being read")
    return first


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D110ExecutionError(f"D-110 {label} JSON is invalid") from exc
    _require(isinstance(value, dict), f"D-110 {label} JSON root is invalid")
    return value


def _pretty_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _validate_utc(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"D-110 {label} is not UTC")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise D110ExecutionError(f"D-110 {label} is invalid") from exc
    _require(
        parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0,
        f"D-110 {label} is not UTC",
    )
    return parsed


def _root_identity(
    payload: Mapping[str, Any],
    *,
    schema_version: str,
    id_field: str,
    id_prefix: str,
    label: str,
) -> None:
    _require(payload.get("schema_version") == schema_version, f"D-110 {label} schema drifted")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), f"D-110 {label} body is invalid")
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload.get("semantic_body_hash") == body_hash
        and payload.get(id_field) == f"{id_prefix}{body_hash.removeprefix('sha256:')}",
        f"D-110 {label} identity drifted",
    )


def _file_binding(path: Path, *, repository: Path, label: str) -> dict[str, Any]:
    selected = _resolved(path, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _bytes_binding(path: Path, content: bytes, *, repository: Path) -> dict[str, Any]:
    selected = _resolved(path, repository=repository, label=path.name, must_exist=False)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _fsync_directory(directory: Path) -> bool:
    """Best-effort directory durability; Windows does not expose portable directory fsync."""

    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return False
    try:
        os.fsync(descriptor)
    except OSError:
        return False
    finally:
        os.close(descriptor)
    return True


def _write_new_fsynced(path: Path, content: bytes, *, exact_retry: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = _read_stable(path, label=path.name)
        _require(exact_retry and existing == content, f"D-110 {path.name} already exists")
        return
    try:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        existing = _read_stable(path, label=path.name)
        _require(
            exact_retry and existing == content,
            f"D-110 {path.name} was concurrently created",
        )
    _fsync_directory(path.parent)


def _candidate_binding(
    content: bytes,
    payload: Mapping[str, Any],
    *,
    repository: Path,
) -> dict[str, Any]:
    return {
        "path": d109.DEFAULT_CANDIDATE_PATH.as_posix(),
        "schema_version": payload["schema_version"],
        "candidate_id": payload["candidate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _load_exact_d109(
    repository: Path,
    *,
    verify_live_runtime: bool,
) -> dict[str, Any]:
    validation = d109.validate_d109_source_gate(
        repository=repository,
        verify_live_runtime=verify_live_runtime,
    )
    _require(
        validation["gate_id"] == EXPECTED_D109_GATE_ID
        and validation["semantic_body_hash"] == EXPECTED_D109_GATE_BODY_SHA
        and validation["file_bytes"] == EXPECTED_D109_GATE_BYTES
        and validation["file_sha256"] == EXPECTED_D109_GATE_FILE_SHA
        and validation["candidate_id"] == EXPECTED_CANDIDATE_ID
        and validation["candidate_semantic_body_hash"] == EXPECTED_CANDIDATE_BODY_SHA
        and validation["candidate_file_bytes"] == EXPECTED_CANDIDATE_BYTES
        and validation["candidate_file_sha256"] == EXPECTED_CANDIDATE_FILE_SHA,
        "D-110 exact D-109 source gate or candidate drifted",
    )
    candidate_path = _resolved(
        d109.DEFAULT_CANDIDATE_PATH,
        repository=repository,
        label="D-109 authorization candidate",
    )
    candidate_content = _read_stable(candidate_path, label="D-109 authorization candidate")
    candidate = _parse_json(candidate_content, label="D-109 authorization candidate")
    _require(
        candidate_content == _pretty_json(candidate),
        "D-109 candidate bytes are not canonical",
    )
    _require(
        candidate["candidate_id"] == EXPECTED_CANDIDATE_ID
        and candidate["semantic_body_hash"] == EXPECTED_CANDIDATE_BODY_SHA
        and len(candidate_content) == EXPECTED_CANDIDATE_BYTES
        and sha256_bytes(candidate_content) == EXPECTED_CANDIDATE_FILE_SHA,
        "D-110 exact D-109 candidate binding drifted",
    )
    gate_binding = _file_binding(
        d109.DEFAULT_SOURCE_GATE_PATH,
        repository=repository,
        label="D-109 source gate",
    )
    gate_binding.update(
        {
            "schema_version": d109.SOURCE_GATE_SCHEMA_VERSION,
            "gate_id": EXPECTED_D109_GATE_ID,
            "semantic_body_hash": EXPECTED_D109_GATE_BODY_SHA,
        }
    )
    return {
        "validation": validation,
        "candidate": candidate,
        "candidate_binding": _candidate_binding(
            candidate_content,
            candidate,
            repository=repository,
        ),
        "source_gate_binding": gate_binding,
    }


def build_d110_approval_receipt(
    *,
    repository: str | Path | None = None,
    _d109_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic self-attested receipt for the exact user approval."""

    repo = _repo_root(repository)
    context = dict(_d109_context) if _d109_context is not None else _load_exact_d109(
        repo,
        verify_live_runtime=False,
    )
    candidate = context["candidate"]
    action = candidate["semantic_body"]["authorized_action_template"]
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "self-attested-exact-d109-index-freeze-approval",
        "recorded_at": APPROVAL_RECORDED_AT,
        "d109_source_gate": context["source_gate_binding"],
        "d109_candidate": context["candidate_binding"],
        "approval_action_id": APPROVAL_ACTION_ID,
        "approver_kind": "human",
        "approver_label": "chat-maintainer-self-attested",
        "approval_reference": APPROVAL_REFERENCE,
        "approval_reference_mode": "explicit-same-message-exact-candidate-triple",
        "approval_statement_code": APPROVAL_STATEMENT_CODE,
        "approval_statement": APPROVAL_STATEMENT,
        "authorized_scope": {
            "index_id": EXPECTED_INDEX_ID,
            "runtime_index_path": DEFAULT_RUNTIME_INDEX_PATH.as_posix(),
            "freeze_execution_count": 1,
            "action_schema_version": action["schema_version"],
            "allowed_existing_json_mutations": action["allowed_existing_json_mutations"],
            "marker_path": action["marker_path"],
            "marker_content_rule": action["marker_content_rule"],
            "marker_written_after_index": True,
            "automatic_retry_authorized": False,
            "provider_calls_authorized": 0,
            "evaluator_calls_authorized": 0,
            "retrieval_authorized": False,
            "runtime_memory_injection_authorized": False,
            "core_campaign_authorized": False,
            "analysis_authorized": False,
        },
        "explicit_approval_receipt_recorded": True,
        "reviewer_identity_authenticated": False,
        "cryptographic_signature_verified": False,
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "receipt_id": f"d110approval_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def materialize_d110_approval_receipt(
    approval_path: str | Path = DEFAULT_APPROVAL_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(
        approval_path,
        repository=repo,
        label="D-110 approval receipt",
        must_exist=False,
    )
    payload = build_d110_approval_receipt(repository=repo)
    content = _pretty_json(payload)
    _write_new_fsynced(selected, content, exact_retry=True)
    return {
        **_file_binding(selected, repository=repo, label="D-110 approval receipt"),
        "receipt_id": payload["receipt_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
    }


def validate_d110_approval_receipt(
    approval_path: str | Path = DEFAULT_APPROVAL_PATH,
    *,
    repository: str | Path | None = None,
    _d109_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(approval_path, repository=repo, label="D-110 approval receipt")
    content = _read_stable(selected, label="D-110 approval receipt")
    payload = _parse_json(content, label="D-110 approval receipt")
    expected = build_d110_approval_receipt(repository=repo, _d109_context=_d109_context)
    _require(payload == expected and content == _pretty_json(expected), "D-110 approval drifted")
    scope = payload["semantic_body"]["authorized_scope"]
    _require(
        scope["freeze_execution_count"] == 1
        and scope["automatic_retry_authorized"] is False
        and scope["provider_calls_authorized"] == 0
        and scope["evaluator_calls_authorized"] == 0
        and scope["retrieval_authorized"] is False
        and scope["runtime_memory_injection_authorized"] is False
        and scope["core_campaign_authorized"] is False
        and scope["analysis_authorized"] is False,
        "D-110 approval scope widened",
    )
    return {
        **_file_binding(selected, repository=repo, label="D-110 approval receipt"),
        "schema_version": payload["schema_version"],
        "receipt_id": payload["receipt_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "self_attested": True,
        "reviewer_identity_authenticated": False,
        "cryptographic_signature_verified": False,
    }


def _json_diff_paths(before: Any, after: Any, pointer: str = "") -> list[str]:
    if isinstance(before, dict) and isinstance(after, dict):
        paths: list[str] = []
        for key in sorted(set(before) | set(after)):
            child = f"{pointer}/{key}"
            if key not in before or key not in after:
                paths.append(child)
            else:
                paths.extend(_json_diff_paths(before[key], after[key], child))
        return paths
    if isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            return [pointer]
        paths = []
        for index, (left, right) in enumerate(zip(before, after, strict=True)):
            paths.extend(_json_diff_paths(left, right, f"{pointer}/{index}"))
        return paths
    return [] if before == after else [pointer]


def _validate_exact_pre_index_payload(payload: Mapping[str, Any]) -> None:
    _require(
        payload.get("index_version") == EXPECTED_INDEX_ID
        and payload.get("frozen") is False
        and "frozen_at" not in payload
        and payload.get("content_hash") == d109.EXPECTED_INDEX_CONTENT_HASH,
        "D-110 pre-index semantic state drifted",
    )
    authority = payload.get("authority")
    _require(isinstance(authority, dict), "D-110 pre-index authority is invalid")
    _require(
        authority.get("index_freeze_authorized") is False
        and authority.get("memory_index_frozen") is False
        and authority.get("retrieval_ready") is False
        and authority.get("retrieval_experiment_authorized") is False
        and authority.get("runtime_memory_injection_count") == 0
        and authority.get("core_campaign_unlocked") is False
        and authority.get("analysis_ready") is False
        and authority.get("provider_calls_made") == 0
        and authority.get("evaluator_calls_made") == 0
        and authority.get("added_model_cost_usd") == 0,
        "D-110 pre-index authority drifted",
    )
    without_hash = {key: value for key, value in payload.items() if key != "content_hash"}
    _require(
        sha256_text(canonical_json(without_hash)) == d109.EXPECTED_INDEX_CONTENT_HASH,
        "D-110 pre-index content does not match its exact content hash",
    )


def _load_exact_pre_index(repository: Path) -> tuple[dict[str, Any], bytes]:
    path = _resolved(
        d109.DEFAULT_PORTABLE_INDEX_PATH,
        repository=repository,
        label="D-106 portable unfrozen index",
    )
    content = _read_stable(path, label="D-106 portable unfrozen index")
    _require(
        len(content) == d109.EXPECTED_INDEX_BYTES
        and sha256_bytes(content) == d109.EXPECTED_INDEX_FILE_SHA,
        "D-110 portable pre-index file identity drifted",
    )
    payload = _parse_json(content, label="D-106 portable unfrozen index")
    _require(content == _pretty_json(payload), "D-110 portable pre-index is not canonical")
    _validate_exact_pre_index_payload(payload)
    return payload, content


def build_d110_post_freeze_index(
    pre_index: Mapping[str, Any],
    *,
    execution_started_at: str,
) -> dict[str, Any]:
    """Apply exactly the five candidate-authorized JSON changes in memory."""

    _validate_utc(execution_started_at, label="freeze execution start")
    _require(pre_index.get("index_version") == EXPECTED_INDEX_ID, "D-110 index ID drifted")
    _require(pre_index.get("frozen") is False, "D-110 pre-index is already frozen")
    _require("frozen_at" not in pre_index, "D-110 pre-index already has frozen_at")
    _validate_exact_pre_index_payload(pre_index)
    authority = pre_index.get("authority")
    _require(isinstance(authority, dict), "D-110 pre-index authority is invalid")
    _require(
        authority.get("index_freeze_authorized") is False
        and authority.get("memory_index_frozen") is False,
        "D-110 pre-index freeze authority is not false",
    )
    post = copy.deepcopy(dict(pre_index))
    post["frozen"] = True
    post["frozen_at"] = execution_started_at
    post["authority"]["index_freeze_authorized"] = True
    post["authority"]["memory_index_frozen"] = True
    post_without_hash = {key: value for key, value in post.items() if key != "content_hash"}
    post["content_hash"] = sha256_text(canonical_json(post_without_hash))
    validate_d110_post_freeze_index(
        pre_index,
        post,
        execution_started_at=execution_started_at,
    )
    return post


def validate_d110_post_freeze_index(
    pre_index: Mapping[str, Any],
    post_index: Mapping[str, Any],
    *,
    execution_started_at: str,
) -> dict[str, Any]:
    _validate_utc(execution_started_at, label="freeze execution start")
    _validate_exact_pre_index_payload(pre_index)
    diff_paths = _json_diff_paths(pre_index, post_index)
    _require(
        set(diff_paths) == set(ALLOWED_MUTATION_POINTERS) and len(diff_paths) == 5,
        "D-110 post-index changed fields outside the exact five-pointer whitelist",
    )
    _require(
        post_index.get("frozen") is True
        and post_index.get("frozen_at") == execution_started_at,
        "D-110 post-index freeze state drifted",
    )
    authority = post_index.get("authority")
    _require(isinstance(authority, dict), "D-110 post-index authority is invalid")
    _require(
        authority.get("index_freeze_authorized") is True
        and authority.get("memory_index_frozen") is True
        and authority.get("retrieval_ready") is False
        and authority.get("retrieval_experiment_authorized") is False
        and authority.get("runtime_memory_injection_count") == 0
        and authority.get("core_campaign_unlocked") is False
        and authority.get("analysis_ready") is False
        and authority.get("provider_calls_made") == 0
        and authority.get("evaluator_calls_made") == 0
        and authority.get("added_model_cost_usd") == 0,
        "D-110 post-index adjacent authority widened",
    )
    without_hash = {key: value for key, value in post_index.items() if key != "content_hash"}
    expected_hash = sha256_text(canonical_json(without_hash))
    _require(post_index.get("content_hash") == expected_hash, "D-110 post-index hash drifted")
    reversed_payload = copy.deepcopy(dict(post_index))
    reversed_payload["frozen"] = False
    reversed_payload.pop("frozen_at", None)
    reversed_payload["authority"]["index_freeze_authorized"] = False
    reversed_payload["authority"]["memory_index_frozen"] = False
    reversed_payload["content_hash"] = pre_index["content_hash"]
    _require(reversed_payload == dict(pre_index), "D-110 post-index is not exactly reversible")
    return {
        "index_id": post_index["index_version"],
        "frozen": True,
        "frozen_at": execution_started_at,
        "content_hash": expected_hash,
        "mutation_paths": list(ALLOWED_MUTATION_POINTERS),
        "retrieval_ready": False,
        "runtime_memory_injection_count": 0,
        "core_campaign_unlocked": False,
    }


def _pre_state_descriptor(candidate: Mapping[str, Any]) -> dict[str, Any]:
    target = candidate["semantic_body"]["freeze_target"]
    return {
        "index_id": target["index_id"],
        "runtime_index_path": target["runtime_index_path"],
        "file_bytes": target["pre_freeze_file_bytes"],
        "file_sha256": target["pre_freeze_file_sha256"],
        "content_hash": target["pre_freeze_content_hash"],
        "frozen": False,
        "frozen_at_present": False,
        "index_freeze_authorized": False,
        "memory_index_frozen": False,
    }


def _post_state_descriptor(
    post_index: Mapping[str, Any],
    post_content: bytes,
    *,
    runtime_path: Path = DEFAULT_RUNTIME_INDEX_PATH,
) -> dict[str, Any]:
    return {
        "index_id": post_index["index_version"],
        "runtime_index_path": runtime_path.as_posix(),
        "file_bytes": len(post_content),
        "file_sha256": sha256_bytes(post_content),
        "content_hash": post_index["content_hash"],
        "frozen": True,
        "frozen_at": post_index["frozen_at"],
        "index_freeze_authorized": True,
        "memory_index_frozen": True,
        "retrieval_ready": False,
        "retrieval_experiment_authorized": False,
        "runtime_memory_injection_count": 0,
        "core_campaign_unlocked": False,
        "analysis_ready": False,
    }


def _marker_descriptor(
    content: bytes,
    *,
    path: Path = DEFAULT_RUNTIME_MARKER_PATH,
) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


class _ExecutionJournal:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle: BinaryIO | None = None
        self.records: list[dict[str, Any]] = []

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._handle = self.path.open("xb")
        except FileExistsError as exc:
            raise D110ExecutionError("D-110 one-use execution journal already exists") from exc
        _fsync_directory(self.path.parent)

    def append(
        self,
        event_type: str,
        body: Mapping[str, Any],
        *,
        recorded_at: str | None = None,
    ) -> dict[str, Any]:
        _require(self._handle is not None, "D-110 journal is not open")
        timestamp = recorded_at or _utc_now()
        _validate_utc(timestamp, label="journal timestamp")
        row_without_hash = {
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "sequence": len(self.records) + 1,
            "event_type": event_type,
            "recorded_at": timestamp,
            "previous_record_hash": self.records[-1]["record_hash"] if self.records else None,
            "body": dict(body),
        }
        row = {
            **row_without_hash,
            "record_hash": sha256_text(canonical_json(row_without_hash)),
        }
        self._handle.write((canonical_json(row) + "\n").encode("utf-8"))
        self._handle.flush()
        os.fsync(self._handle.fileno())
        self.records.append(row)
        return row

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None


def _load_journal(path: Path) -> dict[str, Any]:
    content = _read_stable(path, label="D-110 execution journal")
    _require(content.endswith(b"\n") and content.strip(), "D-110 journal is incomplete")
    records: list[dict[str, Any]] = []
    previous: str | None = None
    previous_time: datetime | None = None
    for sequence, raw in enumerate(content.splitlines(keepends=True), start=1):
        _require(raw.endswith(b"\n"), "D-110 journal row lacks LF")
        row = _parse_json(raw[:-1], label=f"journal row {sequence}")
        _require(set(row) == JOURNAL_ROOT_KEYS, "D-110 journal row keys drifted")
        _require(
            raw == (canonical_json(row) + "\n").encode("utf-8"),
            "D-110 journal row is not canonical",
        )
        _require(
            row["schema_version"] == JOURNAL_SCHEMA_VERSION
            and type(row["sequence"]) is int
            and row["sequence"] == sequence
            and isinstance(row["event_type"], str)
            and isinstance(row["body"], dict)
            and row["previous_record_hash"] == previous,
            "D-110 journal sequence or shape drifted",
        )
        timestamp = _validate_utc(row["recorded_at"], label="journal row timestamp")
        _require(
            previous_time is None or timestamp >= previous_time,
            "D-110 journal time regressed",
        )
        without_hash = {key: value for key, value in row.items() if key != "record_hash"}
        _require(
            row["record_hash"] == sha256_text(canonical_json(without_hash)),
            "D-110 journal record hash drifted",
        )
        previous = row["record_hash"]
        previous_time = timestamp
        records.append(row)
    return {
        "records": records,
        "record_count": len(records),
        "head": previous,
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _atomic_replace_index(
    target: Path,
    staged: Path,
    *,
    expected_pre_content: bytes,
    post_content: bytes,
    marker_path: Path,
    fault_injector: Callable[[str], None] | None = None,
) -> None:
    _require(
        _read_stable(target, label="runtime pre-index CAS") == expected_pre_content,
        "D-110 runtime pre-index CAS failed",
    )
    _require(not marker_path.exists(), "D-110 marker appeared before index commit")
    staged.parent.mkdir(parents=True, exist_ok=True)
    _require(not staged.exists(), "D-110 staged index already exists")
    original_mode = stat.S_IMODE(target.stat().st_mode)
    _write_new_fsynced(staged, post_content)
    os.chmod(staged, original_mode)
    _require(
        _read_stable(staged, label="staged frozen index") == post_content,
        "D-110 staged index drifted",
    )
    if fault_injector is not None:
        fault_injector("after_index_staged")
    _require(
        _read_stable(target, label="runtime pre-index CAS") == expected_pre_content,
        "D-110 runtime pre-index changed after staging",
    )
    os.replace(staged, target)
    _fsync_directory(target.parent)
    if fault_injector is not None:
        fault_injector("after_index_replaced")
    _require(
        _read_stable(target, label="runtime frozen index") == post_content,
        "D-110 runtime index replace drifted",
    )
    _require(
        not marker_path.exists(),
        "D-110 marker appeared before the committed index was recorded",
    )


def _create_marker(
    marker_path: Path,
    content: bytes,
    *,
    fault_injector: Callable[[str], None] | None = None,
) -> None:
    _require(not marker_path.exists(), "D-110 FROZEN marker already exists")
    _write_new_fsynced(marker_path, content)
    if fault_injector is not None:
        fault_injector("after_marker_created")
    _require(
        _read_stable(marker_path, label="runtime FROZEN marker") == content,
        "D-110 FROZEN marker drifted",
    )


def _runtime_post_binding(
    repository: Path,
    *,
    expected_index: bytes,
    expected_marker: bytes,
) -> dict[str, Any]:
    index_path = _resolved(
        DEFAULT_RUNTIME_INDEX_PATH,
        repository=repository,
        label="runtime frozen index",
    )
    marker_path = _resolved(
        DEFAULT_RUNTIME_MARKER_PATH,
        repository=repository,
        label="runtime FROZEN marker",
    )
    directory = index_path.parent
    _require(not _is_linklike(directory), "D-110 runtime index directory is linked")
    names = sorted(path.name for path in directory.iterdir())
    _require(names == ["FROZEN", "index.json"], "D-110 runtime frozen directory is ambiguous")
    index_content = _read_stable(index_path, label="runtime frozen index")
    marker_content = _read_stable(marker_path, label="runtime FROZEN marker")
    _require(index_content == expected_index, "D-110 runtime frozen index differs from evidence")
    _require(marker_content == expected_marker, "D-110 runtime marker differs from evidence")
    return {
        "directory_path": directory.relative_to(repository).as_posix(),
        "directory_file_names": names,
        "index": _file_binding(index_path, repository=repository, label="runtime frozen index"),
        "marker": _file_binding(marker_path, repository=repository, label="runtime FROZEN marker"),
    }


def _output_paths(repository: Path) -> dict[str, Path]:
    return {
        "approval": _resolved(DEFAULT_APPROVAL_PATH, repository=repository, label="approval"),
        "journal": _resolved(
            DEFAULT_JOURNAL_PATH,
            repository=repository,
            label="journal",
            must_exist=False,
        ),
        "portable_index": _resolved(
            DEFAULT_PORTABLE_FROZEN_INDEX_PATH,
            repository=repository,
            label="portable frozen index",
            must_exist=False,
        ),
        "portable_marker": _resolved(
            DEFAULT_PORTABLE_FROZEN_MARKER_PATH,
            repository=repository,
            label="portable frozen marker",
            must_exist=False,
        ),
        "receipt": _resolved(
            DEFAULT_FREEZE_RECEIPT_PATH,
            repository=repository,
            label="freeze receipt",
            must_exist=False,
        ),
        "gate": _resolved(
            DEFAULT_COMPLETION_GATE_PATH,
            repository=repository,
            label="completion gate",
            must_exist=False,
        ),
        "runtime_index": _resolved(
            DEFAULT_RUNTIME_INDEX_PATH,
            repository=repository,
            label="runtime index",
        ),
        "runtime_marker": _resolved(
            DEFAULT_RUNTIME_MARKER_PATH,
            repository=repository,
            label="runtime marker",
            must_exist=False,
        ),
        "lock": _resolved(
            DEFAULT_EXECUTION_LOCK_PATH,
            repository=repository,
            label="execution lock",
            must_exist=False,
        ),
        "staged_index": _resolved(
            DEFAULT_STAGED_INDEX_PATH,
            repository=repository,
            label="staged index",
            must_exist=False,
        ),
    }


def preflight_d110_execution(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Read-only preflight for the approved exact freeze."""

    repo = _repo_root(repository)
    context = _load_exact_d109(repo, verify_live_runtime=True)
    approval = validate_d110_approval_receipt(repository=repo, _d109_context=context)
    paths = _output_paths(repo)
    output_labels = (
        "journal",
        "portable_index",
        "portable_marker",
        "receipt",
        "gate",
        "lock",
        "staged_index",
    )
    for label in output_labels:
        _require(not paths[label].exists(), f"D-110 {label} already exists")
    return {
        "ok": True,
        "candidate_id": context["candidate"]["candidate_id"],
        "approval_receipt_id": approval["receipt_id"],
        "index_id": EXPECTED_INDEX_ID,
        "live_runtime_verified": True,
        "one_use_execution_available": True,
        "freeze_execution_authorized": True,
        "memory_index_frozen": False,
        "retrieval_authorized": False,
        "runtime_memory_injection_authorized": False,
        "core_campaign_authorized": False,
        "provider_calls_authorized": 0,
        "evaluator_calls_authorized": 0,
    }


def build_d110_freeze_receipt(
    *,
    recorded_at: str,
    execution_started_at: str,
    source_gate_binding: Mapping[str, Any],
    candidate_binding: Mapping[str, Any],
    approval_binding: Mapping[str, Any],
    journal_prefix_head: str,
    pre_state: Mapping[str, Any],
    post_state: Mapping[str, Any],
    marker: Mapping[str, Any],
    portable_index: Mapping[str, Any],
    portable_marker: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_utc(recorded_at, label="freeze receipt timestamp")
    _validate_utc(execution_started_at, label="freeze execution start")
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "exact-d109-index-freeze-execution-receipt",
        "recorded_at": recorded_at,
        "d109_source_gate": dict(source_gate_binding),
        "d109_candidate": dict(candidate_binding),
        "approval_receipt": dict(approval_binding),
        "approval_action_id": APPROVAL_ACTION_ID,
        "execution_started_at": execution_started_at,
        "execution_journal_prefix": {
            "record_count": 6,
            "head": journal_prefix_head,
        },
        "pre_freeze_state": dict(pre_state),
        "post_freeze_state": dict(post_state),
        "exact_semantic_mutation_paths": list(ALLOWED_MUTATION_POINTERS),
        "runtime_marker": dict(marker),
        "portable_frozen_index": dict(portable_index),
        "portable_frozen_marker": dict(portable_marker),
        "transaction_semantics": {
            "index_commit": "same-filesystem-staged-file-fsync-os-replace",
            "marker_commit": "exclusive-create-binary-file-fsync-after-index",
            "directory_entry_fsync": "best-effort-platform-dependent",
            "arbitrary_external_writer_exclusion_claimed": False,
            "cooperating_d110_executor_lock": True,
            "two_file_atomic_transaction_claimed": False,
            "partial_or_ambiguous_state_fails_closed": True,
            "automatic_retry_or_rollback": False,
        },
        "authority": {
            "exact_candidate_user_approval_received": True,
            "freeze_execution_authorized": True,
            "index_freeze_authorized": True,
            "memory_index_frozen": True,
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
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": FREEZE_RECEIPT_SCHEMA_VERSION,
        "receipt_id": f"d110freezereceipt_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _implementation_bindings(repository: Path) -> list[dict[str, Any]]:
    return [
        _file_binding(path, repository=repository, label="D-110 implementation")
        for path in D110_IMPLEMENTATION_PATHS
    ]


def build_d110_completion_gate(
    *,
    recorded_at: str,
    source_gate_binding: Mapping[str, Any],
    candidate_binding: Mapping[str, Any],
    approval_binding: Mapping[str, Any],
    journal_binding: Mapping[str, Any],
    freeze_receipt_binding: Mapping[str, Any],
    execution_started_at: str,
    pre_state: Mapping[str, Any],
    post_state: Mapping[str, Any],
    portable_index: Mapping[str, Any],
    portable_marker: Mapping[str, Any],
    repository: Path,
    implementation_bindings: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    _validate_utc(recorded_at, label="completion gate timestamp")
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "exact-index-freeze-completion-gate",
        "recorded_at": recorded_at,
        "d109_source_gate": dict(source_gate_binding),
        "d109_candidate": dict(candidate_binding),
        "approval_receipt": dict(approval_binding),
        "execution_journal": dict(journal_binding),
        "freeze_receipt": dict(freeze_receipt_binding),
        "execution_started_at": execution_started_at,
        "pre_freeze_state": dict(pre_state),
        "post_freeze_state": dict(post_state),
        "exact_semantic_mutation_paths": list(ALLOWED_MUTATION_POINTERS),
        "portable_frozen_index": dict(portable_index),
        "portable_frozen_marker": dict(portable_marker),
        "implementation_files": [
            dict(binding)
            for binding in (
                implementation_bindings
                if implementation_bindings is not None
                else _implementation_bindings(repository)
            )
        ],
        "qualification": {
            "exact_candidate_and_approval_bound": True,
            "one_use_journal_consumed": True,
            "cooperative_lock_and_repeated_live_pre_byte_check_passed": True,
            "atomic_compare_and_swap_claimed": False,
            "post_index_exact_five_pointer_diff_passed": True,
            "post_content_hash_passed": True,
            "index_committed_before_marker": True,
            "runtime_and_portable_frozen_evidence_match": True,
            "portable_d106_pre_index_unchanged": True,
            "execution_lock_and_staged_file_absent": True,
            "partial_or_ambiguous_state": False,
        },
        "authority": {
            "exact_candidate_user_approval_received": True,
            "freeze_execution_authorized": True,
            "index_freeze_authorized": True,
            "memory_index_frozen": True,
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
        "next_gate": "separate-retrieval-readiness-authorization-candidate",
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": COMPLETION_GATE_SCHEMA_VERSION,
        "gate_id": f"d110_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _acquire_execution_lock(path: Path) -> bytes:
    content = _pretty_json(
        {
            "schema_version": "memory-index-freeze-lock-d110-v1",
            "candidate_id": EXPECTED_CANDIDATE_ID,
            "approval_action_id": APPROVAL_ACTION_ID,
            "acquired_at": _utc_now(),
            "process_id": os.getpid(),
        }
    )
    _write_new_fsynced(path, content)
    return content


def execute_d110_index_freeze(
    *,
    repository: str | Path | None = None,
    _fault_injector: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Consume the exact approval and commit the D-109 index freeze once."""

    repo = _repo_root(repository)
    paths = _output_paths(repo)
    _require(not paths["lock"].exists(), "D-110 execution lock already exists")
    _require(not paths["journal"].exists(), "D-110 one-use execution is already consumed")
    _acquire_execution_lock(paths["lock"])
    journal: _ExecutionJournal | None = None
    capability_consumed = False
    success = False
    lock_released = False
    completion_validation: dict[str, Any] | None = None
    stage = "locked-live-preflight"
    try:
        context = _load_exact_d109(repo, verify_live_runtime=True)
        approval = validate_d110_approval_receipt(repository=repo, _d109_context=context)
        output_labels = (
            "journal",
            "portable_index",
            "portable_marker",
            "receipt",
            "gate",
            "staged_index",
        )
        for label in output_labels:
            _require(not paths[label].exists(), f"D-110 {label} already exists")
        pre_index, pre_content = _load_exact_pre_index(repo)
        runtime_content = _read_stable(paths["runtime_index"], label="runtime pre-index")
        _require(
            runtime_content == pre_content,
            "D-110 runtime pre-index differs from portable bytes",
        )
        _require(not paths["runtime_marker"].exists(), "D-110 marker exists before execution")

        execution_started_at = _utc_now()
        post_index = build_d110_post_freeze_index(
            pre_index,
            execution_started_at=execution_started_at,
        )
        post_content = _pretty_json(post_index)
        marker_content = (post_index["content_hash"] + "\n").encode("ascii")
        _require(len(marker_content) == 72, "D-110 marker length drifted")
        pre_state = _pre_state_descriptor(context["candidate"])
        post_state = _post_state_descriptor(post_index, post_content)
        marker_state = _marker_descriptor(marker_content)

        journal = _ExecutionJournal(paths["journal"])
        journal.open()
        capability_consumed = True
        journal.append(
            "FreezeExecutionClaimed",
            {
                "approval_receipt": approval,
                "d109_source_gate": context["source_gate_binding"],
                "d109_candidate": context["candidate_binding"],
                "approval_action_id": APPROVAL_ACTION_ID,
                "execution_started_at": execution_started_at,
                "pre_freeze_state": pre_state,
            },
            recorded_at=execution_started_at,
        )

        stage = "index-mutation-issued"
        journal.append(
            "RuntimeIndexMutationIssued",
            {
                "pre_freeze_state": pre_state,
                "prepared_post_freeze_state": post_state,
                "exact_semantic_mutation_paths": list(ALLOWED_MUTATION_POINTERS),
                "expected_marker": marker_state,
            },
        )
        _atomic_replace_index(
            paths["runtime_index"],
            paths["staged_index"],
            expected_pre_content=pre_content,
            post_content=post_content,
            marker_path=paths["runtime_marker"],
            fault_injector=_fault_injector,
        )
        stage = "index-committed"
        runtime_index_binding = _file_binding(
            paths["runtime_index"],
            repository=repo,
            label="runtime frozen index",
        )
        journal.append(
            "RuntimeIndexMutationCommitted",
            {
                "runtime_frozen_index": runtime_index_binding,
                "post_freeze_state": post_state,
                "frozen_marker_present": False,
            },
        )

        stage = "marker-write-issued"
        journal.append("FrozenMarkerWriteIssued", {"expected_marker": marker_state})
        _create_marker(
            paths["runtime_marker"],
            marker_content,
            fault_injector=_fault_injector,
        )
        stage = "marker-committed"
        runtime_marker_binding = _file_binding(
            paths["runtime_marker"],
            repository=repo,
            label="runtime FROZEN marker",
        )
        _runtime_post_binding(
            repo,
            expected_index=post_content,
            expected_marker=marker_content,
        )
        journal.append(
            "FrozenMarkerWriteCommitted",
            {
                "runtime_frozen_index": runtime_index_binding,
                "runtime_frozen_marker": runtime_marker_binding,
                "directory_file_names": ["FROZEN", "index.json"],
            },
        )

        stage = "portable-evidence"
        _write_new_fsynced(paths["portable_index"], post_content)
        _write_new_fsynced(paths["portable_marker"], marker_content)
        portable_index_binding = _file_binding(
            paths["portable_index"],
            repository=repo,
            label="portable frozen index",
        )
        portable_marker_binding = _file_binding(
            paths["portable_marker"],
            repository=repo,
            label="portable frozen marker",
        )
        _require(
            portable_index_binding["file_sha256"] == runtime_index_binding["file_sha256"]
            and portable_marker_binding["file_sha256"] == runtime_marker_binding["file_sha256"],
            "D-110 portable frozen evidence differs from runtime",
        )
        journal.append(
            "PortableFreezeEvidenceCommitted",
            {
                "portable_frozen_index": portable_index_binding,
                "portable_frozen_marker": portable_marker_binding,
            },
        )

        stage = "freeze-receipt"
        receipt_recorded_at = _utc_now()
        receipt = build_d110_freeze_receipt(
            recorded_at=receipt_recorded_at,
            execution_started_at=execution_started_at,
            source_gate_binding=context["source_gate_binding"],
            candidate_binding=context["candidate_binding"],
            approval_binding=approval,
            journal_prefix_head=journal.records[-1]["record_hash"],
            pre_state=pre_state,
            post_state=post_state,
            marker=runtime_marker_binding,
            portable_index=portable_index_binding,
            portable_marker=portable_marker_binding,
        )
        receipt_content = _pretty_json(receipt)
        _write_new_fsynced(paths["receipt"], receipt_content)
        freeze_receipt_binding = {
            **_file_binding(paths["receipt"], repository=repo, label="freeze receipt"),
            "schema_version": receipt["schema_version"],
            "receipt_id": receipt["receipt_id"],
            "semantic_body_hash": receipt["semantic_body_hash"],
        }
        journal.append(
            "FreezeReceiptCommitted",
            {"freeze_receipt": freeze_receipt_binding},
        )

        stage = "execution-lock-release"
        try:
            paths["lock"].unlink()
        except OSError as exc:
            raise D110ExecutionError("D-110 execution lock could not be released") from exc
        _fsync_directory(paths["lock"].parent)
        _require(not paths["lock"].exists(), "D-110 execution lock remained after release")
        _require(
            not paths["staged_index"].exists(),
            "D-110 staged index remained after runtime commit",
        )
        lock_released = True
        journal.append(
            "ExecutionLockReleased",
            {
                "execution_lock_path": DEFAULT_EXECUTION_LOCK_PATH.as_posix(),
                "execution_lock_absent": True,
                "staged_index_absent": True,
            },
        )

        stage = "completion-gate"
        journal_data = _load_journal(paths["journal"])
        journal_binding = {
            "path": DEFAULT_JOURNAL_PATH.as_posix(),
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "record_count": journal_data["record_count"],
            "head": journal_data["head"],
            "file_bytes": journal_data["file_bytes"],
            "file_sha256": journal_data["file_sha256"],
        }
        gate = build_d110_completion_gate(
            recorded_at=journal_data["records"][-1]["recorded_at"],
            source_gate_binding=context["source_gate_binding"],
            candidate_binding=context["candidate_binding"],
            approval_binding=approval,
            journal_binding=journal_binding,
            freeze_receipt_binding=freeze_receipt_binding,
            execution_started_at=execution_started_at,
            pre_state=pre_state,
            post_state=post_state,
            portable_index=portable_index_binding,
            portable_marker=portable_marker_binding,
            repository=repo,
        )
        gate_content = _pretty_json(gate)
        if _fault_injector is not None:
            _fault_injector("before_completion_gate_write")
        _write_new_fsynced(paths["gate"], gate_content)
        if _fault_injector is not None:
            _fault_injector("after_completion_gate_write")
        completion_validation = validate_d110_completion_gate(
            repository=repo,
            verify_live_runtime=True,
            verify_current_implementation=True,
        )
        journal.close()
        success = True
    except Exception as exc:
        if journal is not None and capability_consumed:
            with contextlib.suppress(Exception):
                journal.append(
                    "FreezeExecutionFailed",
                    {
                        "stage": stage,
                        "error_type": type(exc).__name__,
                        "error_message_sha256": sha256_text(str(exc)),
                        "automatic_retry_or_rollback": False,
                    },
                )
        if isinstance(exc, D110ExecutionError):
            raise
        raise D110ExecutionError(f"D-110 exact freeze failed at {stage}") from exc
    finally:
        if journal is not None:
            journal.close()
        if not capability_consumed:
            try:
                paths["lock"].unlink(missing_ok=True)
                if paths["lock"].parent.exists() and not any(paths["lock"].parent.iterdir()):
                    paths["lock"].parent.rmdir()
            except OSError:
                pass

    _require(success and lock_released, "D-110 execution did not complete cleanly")
    _require(
        completion_validation is not None,
        "D-110 completion validation result is missing",
    )
    return {
        **completion_validation,
        "execution_started_at": execution_started_at,
        "approval_receipt_id": approval["receipt_id"],
        "freeze_receipt_id": receipt["receipt_id"],
        "index_file_sha256": post_state["file_sha256"],
        "content_hash": post_state["content_hash"],
        "marker_file_sha256": runtime_marker_binding["file_sha256"],
    }


def _validate_success_journal_bodies(
    journal: Mapping[str, Any],
    *,
    approval: Mapping[str, Any],
    context: Mapping[str, Any],
    pre_state: Mapping[str, Any],
    post_state: Mapping[str, Any],
    marker_state: Mapping[str, Any],
    runtime_index_binding: Mapping[str, Any],
    runtime_marker_binding: Mapping[str, Any],
    portable_index_binding: Mapping[str, Any],
    portable_marker_binding: Mapping[str, Any],
    freeze_receipt_binding: Mapping[str, Any],
) -> str:
    records = journal["records"]
    _require(
        len(records) == len(SUCCESS_EVENT_TYPES)
        and tuple(row["event_type"] for row in records) == SUCCESS_EVENT_TYPES,
        "D-110 successful journal event sequence drifted",
    )
    execution_started_at = records[0]["body"].get("execution_started_at")
    _require(
        execution_started_at == records[0]["recorded_at"],
        "D-110 execution start is not bound to the claim timestamp",
    )
    _validate_utc(execution_started_at, label="execution start")
    expected_bodies = (
        {
            "approval_receipt": dict(approval),
            "d109_source_gate": context["source_gate_binding"],
            "d109_candidate": context["candidate_binding"],
            "approval_action_id": APPROVAL_ACTION_ID,
            "execution_started_at": execution_started_at,
            "pre_freeze_state": dict(pre_state),
        },
        {
            "pre_freeze_state": dict(pre_state),
            "prepared_post_freeze_state": dict(post_state),
            "exact_semantic_mutation_paths": list(ALLOWED_MUTATION_POINTERS),
            "expected_marker": dict(marker_state),
        },
        {
            "runtime_frozen_index": dict(runtime_index_binding),
            "post_freeze_state": dict(post_state),
            "frozen_marker_present": False,
        },
        {"expected_marker": dict(marker_state)},
        {
            "runtime_frozen_index": dict(runtime_index_binding),
            "runtime_frozen_marker": dict(runtime_marker_binding),
            "directory_file_names": ["FROZEN", "index.json"],
        },
        {
            "portable_frozen_index": dict(portable_index_binding),
            "portable_frozen_marker": dict(portable_marker_binding),
        },
        {"freeze_receipt": dict(freeze_receipt_binding)},
        {
            "execution_lock_path": DEFAULT_EXECUTION_LOCK_PATH.as_posix(),
            "execution_lock_absent": True,
            "staged_index_absent": True,
        },
    )
    _require(
        all(
            row["body"] == expected
            for row, expected in zip(records, expected_bodies, strict=True)
        ),
        "D-110 successful journal body drifted",
    )
    return execution_started_at


def validate_d110_completion_gate(
    gate_path: str | Path = DEFAULT_COMPLETION_GATE_PATH,
    *,
    repository: str | Path | None = None,
    verify_live_runtime: bool = False,
    verify_current_implementation: bool = False,
) -> dict[str, Any]:
    """Validate portable D-110 evidence and optionally the current runtime copy."""

    repo = _repo_root(repository)
    context = _load_exact_d109(repo, verify_live_runtime=False)
    approval = validate_d110_approval_receipt(repository=repo, _d109_context=context)
    pre_index, pre_content = _load_exact_pre_index(repo)
    candidate = context["candidate"]
    pre_state = _pre_state_descriptor(candidate)

    journal_path = _resolved(DEFAULT_JOURNAL_PATH, repository=repo, label="execution journal")
    journal = _load_journal(journal_path)
    _require(journal["record_count"] == 8, "D-110 completion requires eight journal records")
    execution_started_at = journal["records"][0]["body"].get("execution_started_at")
    post_index = build_d110_post_freeze_index(
        pre_index,
        execution_started_at=execution_started_at,
    )
    post_content = _pretty_json(post_index)
    marker_content = (post_index["content_hash"] + "\n").encode("ascii")
    post_state = _post_state_descriptor(post_index, post_content)
    marker_state = _marker_descriptor(marker_content)

    portable_index_path = _resolved(
        DEFAULT_PORTABLE_FROZEN_INDEX_PATH,
        repository=repo,
        label="portable frozen index",
    )
    portable_marker_path = _resolved(
        DEFAULT_PORTABLE_FROZEN_MARKER_PATH,
        repository=repo,
        label="portable frozen marker",
    )
    portable_index_content = _read_stable(portable_index_path, label="portable frozen index")
    portable_marker_content = _read_stable(portable_marker_path, label="portable frozen marker")
    _require(portable_index_content == post_content, "D-110 portable frozen index drifted")
    _require(portable_marker_content == marker_content, "D-110 portable frozen marker drifted")
    _require(
        len(pre_content) == d109.EXPECTED_INDEX_BYTES
        and sha256_bytes(pre_content) == d109.EXPECTED_INDEX_FILE_SHA,
        "D-110 D-106 portable pre-index changed",
    )
    portable_index_binding = _file_binding(
        portable_index_path,
        repository=repo,
        label="portable frozen index",
    )
    portable_marker_binding = _file_binding(
        portable_marker_path,
        repository=repo,
        label="portable frozen marker",
    )
    runtime_index_binding = {
        **_bytes_binding(DEFAULT_RUNTIME_INDEX_PATH, post_content, repository=repo),
    }
    runtime_marker_binding = {
        **_bytes_binding(DEFAULT_RUNTIME_MARKER_PATH, marker_content, repository=repo),
    }

    receipt_path = _resolved(
        DEFAULT_FREEZE_RECEIPT_PATH,
        repository=repo,
        label="freeze receipt",
    )
    receipt_content = _read_stable(receipt_path, label="freeze receipt")
    receipt = _parse_json(receipt_content, label="freeze receipt")
    _root_identity(
        receipt,
        schema_version=FREEZE_RECEIPT_SCHEMA_VERSION,
        id_field="receipt_id",
        id_prefix="d110freezereceipt_",
        label="freeze receipt",
    )
    _require(receipt_content == _pretty_json(receipt), "D-110 freeze receipt is not canonical")
    freeze_receipt_binding = {
        **_file_binding(receipt_path, repository=repo, label="freeze receipt"),
        "schema_version": receipt["schema_version"],
        "receipt_id": receipt["receipt_id"],
        "semantic_body_hash": receipt["semantic_body_hash"],
    }
    execution_started_at = _validate_success_journal_bodies(
        journal,
        approval=approval,
        context=context,
        pre_state=pre_state,
        post_state=post_state,
        marker_state=marker_state,
        runtime_index_binding=runtime_index_binding,
        runtime_marker_binding=runtime_marker_binding,
        portable_index_binding=portable_index_binding,
        portable_marker_binding=portable_marker_binding,
        freeze_receipt_binding=freeze_receipt_binding,
    )
    expected_receipt = build_d110_freeze_receipt(
        recorded_at=receipt["semantic_body"]["recorded_at"],
        execution_started_at=execution_started_at,
        source_gate_binding=context["source_gate_binding"],
        candidate_binding=context["candidate_binding"],
        approval_binding=approval,
        journal_prefix_head=journal["records"][5]["record_hash"],
        pre_state=pre_state,
        post_state=post_state,
        marker=runtime_marker_binding,
        portable_index=portable_index_binding,
        portable_marker=portable_marker_binding,
    )
    _require(receipt == expected_receipt, "D-110 freeze receipt semantic content drifted")

    journal_binding = {
        "path": DEFAULT_JOURNAL_PATH.as_posix(),
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "record_count": journal["record_count"],
        "head": journal["head"],
        "file_bytes": journal["file_bytes"],
        "file_sha256": journal["file_sha256"],
    }
    gate_selected = _resolved(gate_path, repository=repo, label="completion gate")
    gate_content = _read_stable(gate_selected, label="completion gate")
    gate = _parse_json(gate_content, label="completion gate")
    _root_identity(
        gate,
        schema_version=COMPLETION_GATE_SCHEMA_VERSION,
        id_field="gate_id",
        id_prefix="d110_",
        label="completion gate",
    )
    recorded_implementation = gate["semantic_body"].get("implementation_files")
    _require(
        isinstance(recorded_implementation, list)
        and len(recorded_implementation) == len(D110_IMPLEMENTATION_PATHS)
        and all(
            isinstance(binding, dict)
            and set(binding) == {"path", "file_bytes", "file_sha256"}
            and binding["path"] == expected_path.as_posix()
            and type(binding["file_bytes"]) is int
            and binding["file_bytes"] > 0
            and isinstance(binding["file_sha256"], str)
            and binding["file_sha256"].startswith("sha256:")
            and len(binding["file_sha256"]) == 71
            for binding, expected_path in zip(
                recorded_implementation,
                D110_IMPLEMENTATION_PATHS,
                strict=True,
            )
        ),
        "D-110 recorded implementation bindings are invalid",
    )
    current_implementation_verified = False
    if verify_current_implementation:
        _require(
            recorded_implementation == _implementation_bindings(repo),
            "D-110 current implementation differs from executed implementation",
        )
        current_implementation_verified = True
    expected_gate = build_d110_completion_gate(
        recorded_at=journal["records"][-1]["recorded_at"],
        source_gate_binding=context["source_gate_binding"],
        candidate_binding=context["candidate_binding"],
        approval_binding=approval,
        journal_binding=journal_binding,
        freeze_receipt_binding=freeze_receipt_binding,
        execution_started_at=execution_started_at,
        pre_state=pre_state,
        post_state=post_state,
        portable_index=portable_index_binding,
        portable_marker=portable_marker_binding,
        repository=repo,
        implementation_bindings=recorded_implementation,
    )
    _require(
        gate == expected_gate and gate_content == _pretty_json(expected_gate),
        "D-110 completion gate drifted",
    )
    lock_path = _resolved(
        DEFAULT_EXECUTION_LOCK_PATH,
        repository=repo,
        label="execution lock",
        must_exist=False,
    )
    staged_path = _resolved(
        DEFAULT_STAGED_INDEX_PATH,
        repository=repo,
        label="staged index",
        must_exist=False,
    )
    _require(
        not lock_path.exists() and not staged_path.exists(),
        "D-110 completion has a stale execution lock or staged index",
    )

    live_verified = False
    if verify_live_runtime:
        live = _runtime_post_binding(
            repo,
            expected_index=post_content,
            expected_marker=marker_content,
        )
        _require(
            live["index"]["file_sha256"] == portable_index_binding["file_sha256"]
            and live["marker"]["file_sha256"] == portable_marker_binding["file_sha256"],
            "D-110 live runtime differs from portable evidence",
        )
        live_verified = True
    return {
        "ok": True,
        "gate_id": gate["gate_id"],
        "semantic_body_hash": gate["semantic_body_hash"],
        "file_bytes": len(gate_content),
        "file_sha256": sha256_bytes(gate_content),
        "approval_receipt_id": approval["receipt_id"],
        "freeze_receipt_id": receipt["receipt_id"],
        "journal_record_count": journal["record_count"],
        "journal_head": journal["head"],
        "execution_started_at": execution_started_at,
        "index_id": EXPECTED_INDEX_ID,
        "index_file_sha256": portable_index_binding["file_sha256"],
        "content_hash": post_index["content_hash"],
        "marker_file_sha256": portable_marker_binding["file_sha256"],
        "live_runtime_verified": live_verified,
        "current_implementation_verified": current_implementation_verified,
        "freeze_execution_evidence_validated": True,
        "memory_index_frozen_at_execution": True,
        "current_runtime_memory_index_frozen": True if live_verified else None,
        "index_freeze_authorized": True,
        "memory_index_frozen": True if live_verified else None,
        "retrieval_ready": False,
        "retrieval_experiment_authorized": False,
        "runtime_memory_injection_count": 0,
        "core_campaign_unlocked": False,
        "analysis_ready": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "added_model_cost_usd": 0,
    }


__all__ = [
    "ALLOWED_MUTATION_POINTERS",
    "APPROVAL_SCHEMA_VERSION",
    "COMPLETION_GATE_SCHEMA_VERSION",
    "DEFAULT_APPROVAL_PATH",
    "DEFAULT_COMPLETION_GATE_PATH",
    "DEFAULT_FREEZE_RECEIPT_PATH",
    "DEFAULT_JOURNAL_PATH",
    "DEFAULT_PORTABLE_FROZEN_INDEX_PATH",
    "DEFAULT_PORTABLE_FROZEN_MARKER_PATH",
    "D110ExecutionError",
    "FREEZE_RECEIPT_SCHEMA_VERSION",
    "JOURNAL_SCHEMA_VERSION",
    "build_d110_approval_receipt",
    "build_d110_post_freeze_index",
    "execute_d110_index_freeze",
    "materialize_d110_approval_receipt",
    "preflight_d110_execution",
    "validate_d110_approval_receipt",
    "validate_d110_completion_gate",
    "validate_d110_post_freeze_index",
]
