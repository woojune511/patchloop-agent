"""D-108 exact two-call provider token-count execution.

This module consumes the user's exact D-107 approval, enforces a one-use
append-only execution journal, and can issue only the two prepared Responses
input-token-count requests.  It has no generation, freeze, retrieval, runtime
memory-injection, evaluator, or core-campaign path.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any, BinaryIO

from patchloop.errors import ContractError
from patchloop.memory import d107_portable_index_freeze_readiness as d107
from patchloop.util import canonical_json, sha256_text

MILESTONE = "D-108"
APPROVAL_SCHEMA_VERSION = "provider-token-count-approval-receipt-d108-v1"
JOURNAL_SCHEMA_VERSION = "provider-token-count-execution-event-d108-v1"
COMPLETION_GATE_SCHEMA_VERSION = "provider-token-count-completion-gate-d108-v1"

EXPECTED_D107_GATE_ID = (
    "d107_4bc473796fd4564bb4d4cc9bf975ea9e41addb4fda620135e6ae4d6a21e645d4"
)
EXPECTED_D107_BODY_SHA = (
    "sha256:4bc473796fd4564bb4d4cc9bf975ea9e41addb4fda620135e6ae4d6a21e645d4"
)
EXPECTED_D107_GATE_BYTES = 4_175
EXPECTED_D107_GATE_FILE_SHA = (
    "sha256:b3e24975062e379ec94c77187570b392026bacdcc855adedb00943467aaf09f2"
)
EXPECTED_PLAN_ID = (
    "d107plan_7ace0e204f367fc857bfbc1ddaa1bbdc58dd9ff3c9272f9d9c7e2b7241160ee6"
)
EXPECTED_PLAN_BODY_SHA = (
    "sha256:7ace0e204f367fc857bfbc1ddaa1bbdc58dd9ff3c9272f9d9c7e2b7241160ee6"
)
EXPECTED_PLAN_BYTES = 10_143
EXPECTED_PLAN_FILE_SHA = (
    "sha256:2a3d817d14d500863d56d5446010866a6feb2361eb684c3575400020bc31a085"
)

APPROVAL_RECORDED_AT = "2026-08-06T10:09:39.7619586Z"
APPROVAL_ACTION_ID = "d108-exact-d107-two-provider-input-token-count-calls-1"
APPROVAL_STATEMENT_CODE = "EXPLICITLY_APPROVE_D107_EXACT_TWO_INPUT_TOKEN_COUNT_CALLS"
APPROVAL_STATEMENT = (
    f"{APPROVAL_STATEMENT_CODE} {EXPECTED_D107_GATE_ID} "
    f"{EXPECTED_D107_BODY_SHA} {EXPECTED_D107_GATE_FILE_SHA}"
)

OFFICIAL_BASE_URL = "https://api.openai.com/v1"
EXPECTED_ENDPOINT = "POST /v1/responses/input_tokens"
EXPECTED_SDK_VERSION = "2.47.0"
EXPECTED_REQUEST_KEYS = frozenset({"model", "input", "tools", "reasoning", "truncation"})

DEFAULT_APPROVAL_PATH = Path(
    "reports/memory-development/d108-provider-token-count-approval-receipt.json"
)
DEFAULT_JOURNAL_PATH = Path(
    "reports/memory-development/d108-provider-token-count-execution.jsonl"
)
DEFAULT_PROVIDER_RECEIPT_PATH = Path(
    "reports/memory-development/d108-provider-token-count-receipt.json"
)
DEFAULT_COMPLETION_GATE_PATH = Path(
    "reports/memory-development/d108-provider-token-count-completion-gate.json"
)
IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d108_provider_token_count_execution.py"),
    Path("scripts/run_d108_provider_token_counts.py"),
    Path("tests/test_d108_provider_token_count_execution.py"),
)


class D108ExecutionError(ContractError):
    """Raised when the D-108 authorization or execution contract is violated."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D108ExecutionError(message)


def _repo_root(repository: str | Path | None) -> Path:
    root = Path(repository) if repository is not None else Path(__file__).resolve().parents[2]
    root = root.resolve()
    _require(root.is_dir(), "D-108 repository root is unavailable")
    return root


def _resolved(
    path: str | Path,
    *,
    repository: Path,
    label: str,
    must_exist: bool = True,
) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = repository / candidate
    parent = candidate.parent.resolve(strict=True)
    selected = parent / candidate.name
    root = repository.resolve()
    _require(selected == root or root in selected.parents, f"{label} escapes repository")
    if must_exist:
        _require(selected.is_file(), f"{label} is unavailable")
    if selected.exists():
        _require(not selected.is_symlink(), f"{label} must not be a symlink")
    return selected


def _read_stable(path: Path, *, label: str) -> bytes:
    _require(path.is_file() and not path.is_symlink(), f"{label} is unavailable")
    before = path.stat()
    content = path.read_bytes()
    after = path.stat()
    _require(
        (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
        f"{label} changed while it was read",
    )
    return content


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D108ExecutionError(f"{label} is not canonical UTF-8 JSON") from exc
    _require(isinstance(parsed, dict), f"{label} root must be an object")
    return parsed


def _pretty_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _jsonl_row(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _strict_keys(value: Any, expected: set[str] | frozenset[str], *, label: str) -> None:
    _require(isinstance(value, dict), f"{label} must be an object")
    _require(set(value) == set(expected), f"{label} field set drifted")


def _root_identity(
    payload: Mapping[str, Any],
    *,
    schema_version: str,
    id_field: str,
    id_prefix: str,
    label: str,
) -> None:
    _strict_keys(
        payload,
        {"schema_version", id_field, "semantic_body_hash", "semantic_body"},
        label=label,
    )
    body = payload["semantic_body"]
    _require(isinstance(body, dict), f"{label} semantic body must be an object")
    body_hash = sha256_text(canonical_json(body))
    _require(payload["schema_version"] == schema_version, f"{label} schema drifted")
    _require(payload["semantic_body_hash"] == body_hash, f"{label} body hash drifted")
    _require(
        payload[id_field] == f"{id_prefix}{body_hash.removeprefix('sha256:')}",
        f"{label} ID drifted",
    )


def _file_binding(path: Path, *, repository: Path, label: str) -> dict[str, Any]:
    content = _read_stable(path, label=label)
    return {
        "path": path.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": d107.sha256_bytes(content),
    }


def _write_exact_or_new(path: Path, content: bytes, *, exact_retry: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = _read_stable(path, label=path.name)
        _require(
            exact_retry and existing == content,
            f"{path.name} already exists with conflicting bytes",
        )
        return
    try:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        existing = _read_stable(path, label=path.name)
        _require(exact_retry and existing == content, f"{path.name} was concurrently created")


def _validate_iso_timestamp(value: Any, *, label: str) -> None:
    _require(isinstance(value, str) and value.endswith("Z"), f"{label} timestamp is invalid")
    try:
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise D108ExecutionError(f"{label} timestamp is invalid") from exc


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _load_exact_d107_gate(repository: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = _resolved(
        d107.DEFAULT_GATE_PATH,
        repository=repository,
        label="D-107 source gate",
    )
    content = _read_stable(path, label="D-107 source gate")
    payload = _parse_json(content, label="D-107 source gate")
    _root_identity(
        payload,
        schema_version=d107.GATE_SCHEMA_VERSION,
        id_field="gate_id",
        id_prefix="d107_",
        label="D-107 source gate",
    )
    _require(
        payload["gate_id"] == EXPECTED_D107_GATE_ID
        and payload["semantic_body_hash"] == EXPECTED_D107_BODY_SHA
        and len(content) == EXPECTED_D107_GATE_BYTES
        and d107.sha256_bytes(content) == EXPECTED_D107_GATE_FILE_SHA,
        "D-108 exact D-107 gate binding drifted",
    )
    return payload, {
        "path": path.relative_to(repository).as_posix(),
        "schema_version": payload["schema_version"],
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(content),
        "file_sha256": d107.sha256_bytes(content),
    }


def _load_exact_plan(repository: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = _resolved(
        d107.DEFAULT_TOKEN_PLAN_PATH,
        repository=repository,
        label="D-107 token-count plan",
    )
    content = _read_stable(path, label="D-107 token-count plan")
    payload = _parse_json(content, label="D-107 token-count plan")
    _root_identity(
        payload,
        schema_version=d107.TOKEN_PLAN_SCHEMA_VERSION,
        id_field="plan_id",
        id_prefix="d107plan_",
        label="D-107 token-count plan",
    )
    _require(content == _pretty_json(payload), "D-107 token-count plan is not pretty canonical")
    _require(
        payload["plan_id"] == EXPECTED_PLAN_ID
        and payload["semantic_body_hash"] == EXPECTED_PLAN_BODY_SHA
        and len(content) == EXPECTED_PLAN_BYTES
        and d107.sha256_bytes(content) == EXPECTED_PLAN_FILE_SHA,
        "D-108 exact D-107 plan binding drifted",
    )
    return payload, {
        "path": path.relative_to(repository).as_posix(),
        "schema_version": payload["schema_version"],
        "plan_id": payload["plan_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(content),
        "file_sha256": d107.sha256_bytes(content),
    }


def _request_pair(plan: Mapping[str, Any], repository: Path) -> list[dict[str, Any]]:
    pair = plan["semantic_body"]["count_request_pair"]
    results: list[dict[str, Any]] = []
    for order, label in enumerate(("baseline", "with_memory"), start=1):
        binding = pair[f"{label}_artifact"]
        path = _resolved(binding["path"], repository=repository, label=f"{label} count request")
        content = _read_stable(path, label=f"{label} count request")
        payload = _parse_json(content, label=f"{label} count request")
        _strict_keys(payload, EXPECTED_REQUEST_KEYS, label=f"{label} count request")
        _require(content == _pretty_json(payload), f"{label} count request is not pretty canonical")
        _require(
            len(content) == binding["file_bytes"]
            and d107.sha256_bytes(content) == binding["file_sha256"]
            and sha256_text(canonical_json(payload)) == binding["semantic_payload_sha256"]
            and pair[f"{label}_semantic_hash"] == binding["semantic_payload_sha256"],
            f"{label} count request binding drifted",
        )
        results.append(
            {
                "order": order,
                "label": label,
                "payload": payload,
                "request_file_sha256": binding["file_sha256"],
                "request_semantic_hash": pair[f"{label}_semantic_hash"],
            }
        )
    return results


def build_d108_approval_receipt(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Build the exact self-attested receipt for the user's two-call approval."""

    repo = _repo_root(repository)
    _, gate_binding = _load_exact_d107_gate(repo)
    _, plan_binding = _load_exact_plan(repo)
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "self-attested-exact-d107-two-count-call-approval",
        "recorded_at": APPROVAL_RECORDED_AT,
        "d107_gate": gate_binding,
        "token_count_plan": plan_binding,
        "approval_action_id": APPROVAL_ACTION_ID,
        "approver_kind": "human",
        "approver_label": "chat-maintainer-self-attested",
        "approval_reference": "user-message:d107-exact-two-provider-input-token-count-calls",
        "approval_reference_mode": "immediate-preceding-exact-gate-reference",
        "approval_statement_code": APPROVAL_STATEMENT_CODE,
        "approval_statement": APPROVAL_STATEMENT,
        "authorized_scope": {
            "provider_input_token_count_calls": 2,
            "call_order": ["baseline", "with_memory"],
            "provider_generation_calls": 0,
            "sdk_transport_max_retries": 0,
            "automatic_retry_authorized": False,
            "index_freeze_authorized": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_authorized": False,
            "core_campaign_authorized": False,
        },
        "explicit_approval_receipt_recorded": True,
        "reviewer_identity_authenticated": False,
        "cryptographic_signature_verified": False,
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "receipt_id": f"d108approval_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def materialize_d108_approval_receipt(
    approval_path: str | Path = DEFAULT_APPROVAL_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    path = _resolved(
        approval_path,
        repository=repo,
        label="D-108 approval receipt",
        must_exist=False,
    )
    payload = build_d108_approval_receipt(repository=repo)
    content = _pretty_json(payload)
    _write_exact_or_new(path, content, exact_retry=True)
    return {
        **_file_binding(path, repository=repo, label="D-108 approval receipt"),
        "receipt_id": payload["receipt_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
    }


def validate_d108_approval_receipt(
    approval_path: str | Path = DEFAULT_APPROVAL_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    path = _resolved(approval_path, repository=repo, label="D-108 approval receipt")
    content = _read_stable(path, label="D-108 approval receipt")
    payload = _parse_json(content, label="D-108 approval receipt")
    expected = build_d108_approval_receipt(repository=repo)
    _require(
        payload == expected and content == _pretty_json(expected),
        "D-108 approval receipt drifted",
    )
    scope = payload["semantic_body"]["authorized_scope"]
    _require(
        scope
        == {
            "provider_input_token_count_calls": 2,
            "call_order": ["baseline", "with_memory"],
            "provider_generation_calls": 0,
            "sdk_transport_max_retries": 0,
            "automatic_retry_authorized": False,
            "index_freeze_authorized": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_authorized": False,
            "core_campaign_authorized": False,
        },
        "D-108 approval scope widened",
    )
    return {
        **_file_binding(path, repository=repo, label="D-108 approval receipt"),
        "schema_version": payload["schema_version"],
        "receipt_id": payload["receipt_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "self_attested": True,
        "reviewer_identity_authenticated": False,
        "cryptographic_signature_verified": False,
    }


def _implementation_bindings(repository: Path) -> list[dict[str, Any]]:
    return [
        _file_binding(
            _resolved(path, repository=repository, label=path.as_posix()),
            repository=repository,
            label=path.as_posix(),
        )
        for path in IMPLEMENTATION_PATHS
    ]


@dataclass(frozen=True)
class ExecutionPaths:
    approval: Path
    journal: Path
    provider_receipt: Path
    completion_gate: Path


def _execution_paths(
    repository: Path,
    *,
    approval_path: str | Path,
    journal_path: str | Path,
    provider_receipt_path: str | Path,
    completion_gate_path: str | Path,
) -> ExecutionPaths:
    return ExecutionPaths(
        approval=_resolved(approval_path, repository=repository, label="approval receipt"),
        journal=_resolved(
            journal_path,
            repository=repository,
            label="execution journal",
            must_exist=False,
        ),
        provider_receipt=_resolved(
            provider_receipt_path,
            repository=repository,
            label="provider receipt",
            must_exist=False,
        ),
        completion_gate=_resolved(
            completion_gate_path,
            repository=repository,
            label="completion gate",
            must_exist=False,
        ),
    )


class _ExecutionJournal:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._handle: BinaryIO = path.open("xb")
        except FileExistsError as exc:
            raise D108ExecutionError(
                "D-108 execution is one-use and the journal already exists"
            ) from exc
        self.path = path
        self.sequence = 0
        self.previous_hash: str | None = None

    def append(self, event_type: str, body: Mapping[str, Any]) -> dict[str, Any]:
        self.sequence += 1
        record_without_hash = {
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "sequence": self.sequence,
            "event_type": event_type,
            "recorded_at": _utc_now(),
            "previous_record_hash": self.previous_hash,
            "body": dict(body),
        }
        record_hash = sha256_text(canonical_json(record_without_hash))
        record = {**record_without_hash, "record_hash": record_hash}
        self._handle.write(_jsonl_row(record))
        self._handle.flush()
        os.fsync(self._handle.fileno())
        self.previous_hash = record_hash
        return record

    def close(self) -> None:
        if not self._handle.closed:
            self._handle.flush()
            os.fsync(self._handle.fileno())
            self._handle.close()


def _environment_preflight() -> tuple[str, dict[str, Any]]:
    key = os.environ.get("OPENAI_API_KEY")
    _require(isinstance(key, str) and bool(key.strip()), "OPENAI_API_KEY is unavailable")
    forbidden = {
        name: bool(os.environ.get(name))
        for name in (
            "OPENAI_BASE_URL",
            "OPENAI_API_BASE",
            "OPENAI_ORG_ID",
            "OPENAI_ORGANIZATION",
            "OPENAI_PROJECT",
        )
    }
    _require(not any(forbidden.values()), "custom OpenAI routing environment is not allowed")
    return key, {
        "api_key_present": True,
        "api_key_persisted_in_artifact": False,
        "custom_base_url_present": False,
        "organization_or_project_override_present": False,
    }


def _expected_environment_evidence() -> dict[str, Any]:
    return {
        "api_key_present": True,
        "api_key_persisted_in_artifact": False,
        "custom_base_url_present": False,
        "organization_or_project_override_present": False,
    }


def _expected_transport_evidence() -> dict[str, Any]:
    return {
        "base_url": OFFICIAL_BASE_URL,
        "sdk_version": EXPECTED_SDK_VERSION,
        "max_retries": 0,
        "timeout_source": "openai-sdk-2.47.0-default",
        "timeout_seconds": {
            "connect": 5.0,
            "read": 600.0,
            "write": 600.0,
            "pool": 600.0,
        },
    }


def _client_transport_evidence(client: Any) -> dict[str, Any]:
    _require(getattr(client, "max_retries", None) == 0, "OpenAI client retry policy drifted")
    _require(
        str(getattr(client, "base_url", "")).rstrip("/") == OFFICIAL_BASE_URL,
        "OpenAI client base URL drifted",
    )
    timeout = getattr(client, "timeout", None)
    values = {
        name: getattr(timeout, name, None)
        for name in ("connect", "read", "write", "pool")
    }
    _require(
        values == {"connect": 5.0, "read": 600.0, "write": 600.0, "pool": 600.0},
        "OpenAI SDK default timeout drifted",
    )
    expected = _expected_transport_evidence()
    _require(expected["timeout_seconds"] == values, "OpenAI timeout evidence drifted")
    return expected


def _execution_claim_body(
    *,
    approval: Mapping[str, Any],
    plan_binding: Mapping[str, Any],
    implementation_files: list[dict[str, Any]],
    environment: Mapping[str, Any],
    transport: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "approval_receipt": dict(approval),
        "token_count_plan": dict(plan_binding),
        "implementation_files": implementation_files,
        "endpoint": EXPECTED_ENDPOINT,
        "expected_call_count": 2,
        "call_order": ["baseline", "with_memory"],
        "provider_generation_calls_authorized": 0,
        "automatic_retry_authorized": False,
        "environment": dict(environment),
        "transport": dict(transport),
    }


def _build_provider_receipt(
    plan: Mapping[str, Any],
    responses: list[dict[str, Any]],
) -> dict[str, Any]:
    _require(len(responses) == 2, "D-108 successful receipt requires two responses")
    pair = plan["semantic_body"]["count_request_pair"]
    calls: list[dict[str, Any]] = []
    for response, label, order in zip(
        responses,
        ("baseline", "with_memory"),
        (1, 2),
        strict=True,
    ):
        calls.append(
            {
                "order": order,
                "label": label,
                "request_file_sha256": pair[f"{label}_artifact"]["file_sha256"],
                "request_semantic_hash": pair[f"{label}_semantic_hash"],
                "response": {
                    "object": response["object"],
                    "input_tokens": response["input_tokens"],
                },
            }
        )
    baseline = responses[0]["input_tokens"]
    with_memory = responses[1]["input_tokens"]
    body = {
        "plan": {
            "plan_id": plan["plan_id"],
            "semantic_body_hash": plan["semantic_body_hash"],
            "file_sha256": d107.sha256_bytes(_pretty_json(plan)),
        },
        "calls": calls,
        "baseline_input_tokens": baseline,
        "with_memory_input_tokens": with_memory,
        "memory_delta_tokens": with_memory - baseline,
        "provider_input_token_count_calls_made": 2,
        "provider_generation_calls_made": 0,
        "sdk_transport_max_retries": 0,
        "automatic_retry_used": False,
        "api_key_persisted_in_artifact": False,
        "provider_exact_budget_validated": True,
        "index_freeze_authorized": False,
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": d107.TOKEN_RECEIPT_SCHEMA_VERSION,
        "receipt_id": f"d107countreceipt_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def validate_strict_provider_receipt(
    receipt: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    _root_identity(
        receipt,
        schema_version=d107.TOKEN_RECEIPT_SCHEMA_VERSION,
        id_field="receipt_id",
        id_prefix="d107countreceipt_",
        label="D-108 provider receipt",
    )
    body = receipt["semantic_body"]
    _strict_keys(
        body,
        {
            "plan",
            "calls",
            "baseline_input_tokens",
            "with_memory_input_tokens",
            "memory_delta_tokens",
            "provider_input_token_count_calls_made",
            "provider_generation_calls_made",
            "sdk_transport_max_retries",
            "automatic_retry_used",
            "api_key_persisted_in_artifact",
            "provider_exact_budget_validated",
            "index_freeze_authorized",
        },
        label="D-108 provider receipt body",
    )
    _strict_keys(
        body["plan"],
        {"plan_id", "semantic_body_hash", "file_sha256"},
        label="D-108 provider receipt plan",
    )
    calls = body["calls"]
    _require(isinstance(calls, list) and len(calls) == 2, "D-108 provider call set drifted")
    for call in calls:
        _strict_keys(
            call,
            {
                "order",
                "label",
                "request_file_sha256",
                "request_semantic_hash",
                "response",
            },
            label="D-108 provider receipt call",
        )
        _strict_keys(
            call["response"],
            {"object", "input_tokens"},
            label="D-108 provider receipt response",
        )
    return d107.validate_d107_future_provider_receipt(receipt, plan)


def _safe_failure(error: BaseException) -> dict[str, Any]:
    return {
        "error_type": type(error).__name__,
        "status_code": getattr(error, "status_code", None),
        "request_id": getattr(error, "request_id", None),
        "error_message_persisted": False,
    }


def _validate_deep_source_gate(repository: Path) -> None:
    result = d107.validate_d107_source_gate(repository=repository)
    _require(
        result["gate_id"] == EXPECTED_D107_GATE_ID
        and result["semantic_body_hash"] == EXPECTED_D107_BODY_SHA
        and result["provider_calls_made"] == 0
        and result["provider_exact_budget_validated"] is False
        and result["index_freeze_authorized"] is False
        and result["retrieval_ready"] is False,
        "D-108 deep D-107 source validation drifted",
    )


def preflight_d108_execution(
    *,
    repository: str | Path | None = None,
    approval_path: str | Path = DEFAULT_APPROVAL_PATH,
    journal_path: str | Path = DEFAULT_JOURNAL_PATH,
    provider_receipt_path: str | Path = DEFAULT_PROVIDER_RECEIPT_PATH,
    completion_gate_path: str | Path = DEFAULT_COMPLETION_GATE_PATH,
    require_api_key: bool = True,
    deep_source_validator: Callable[[Path], None] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    paths = _execution_paths(
        repo,
        approval_path=approval_path,
        journal_path=journal_path,
        provider_receipt_path=provider_receipt_path,
        completion_gate_path=completion_gate_path,
    )
    approval = validate_d108_approval_receipt(paths.approval, repository=repo)
    validator = deep_source_validator or _validate_deep_source_gate
    validator(repo)
    plan, plan_binding = _load_exact_plan(repo)
    requests = _request_pair(plan, repo)
    _require(package_version("openai") == EXPECTED_SDK_VERSION, "OpenAI SDK version drifted")
    _require(not paths.journal.exists(), "D-108 one-use execution journal already exists")
    _require(not paths.provider_receipt.exists(), "D-108 provider receipt already exists")
    _require(not paths.completion_gate.exists(), "D-108 completion gate already exists")
    environment = None
    if require_api_key:
        _, environment = _environment_preflight()
    return {
        "repository": repo,
        "paths": paths,
        "approval": approval,
        "plan": plan,
        "plan_binding": plan_binding,
        "requests": requests,
        "implementation_files": _implementation_bindings(repo),
        "environment": environment,
        "provider_calls_made": 0,
        "generation_calls_made": 0,
        "ready": True,
    }


def _default_client_factory(api_key: str) -> Any:
    from openai import OpenAI

    return OpenAI(
        api_key=api_key,
        base_url=OFFICIAL_BASE_URL,
        max_retries=0,
    )


def execute_d108_provider_token_counts(
    *,
    repository: str | Path | None = None,
    approval_path: str | Path = DEFAULT_APPROVAL_PATH,
    journal_path: str | Path = DEFAULT_JOURNAL_PATH,
    provider_receipt_path: str | Path = DEFAULT_PROVIDER_RECEIPT_PATH,
    completion_gate_path: str | Path = DEFAULT_COMPLETION_GATE_PATH,
    client_factory: Callable[[str], Any] | None = None,
    deep_source_validator: Callable[[Path], None] | None = None,
) -> dict[str, Any]:
    """Perform the approved baseline and with-memory count calls exactly once."""

    preflight = preflight_d108_execution(
        repository=repository,
        approval_path=approval_path,
        journal_path=journal_path,
        provider_receipt_path=provider_receipt_path,
        completion_gate_path=completion_gate_path,
        require_api_key=True,
        deep_source_validator=deep_source_validator,
    )
    repo: Path = preflight["repository"]
    paths: ExecutionPaths = preflight["paths"]
    api_key, environment = _environment_preflight()
    factory = client_factory or _default_client_factory
    client = factory(api_key)
    transport = _client_transport_evidence(client)
    journal = _ExecutionJournal(paths.journal)
    responses: list[dict[str, Any]] = []
    try:
        journal.append(
            "ExecutionClaimed",
            _execution_claim_body(
                approval=preflight["approval"],
                plan_binding=preflight["plan_binding"],
                implementation_files=preflight["implementation_files"],
                environment=environment,
                transport=transport,
            ),
        )
        for request in preflight["requests"]:
            journal.append(
                "ProviderInputTokenCountCallIssued",
                {
                    "order": request["order"],
                    "label": request["label"],
                    "request_file_sha256": request["request_file_sha256"],
                    "request_semantic_hash": request["request_semantic_hash"],
                    "endpoint": EXPECTED_ENDPOINT,
                },
            )
            try:
                raw = client.responses.input_tokens.with_raw_response.count(
                    **request["payload"]
                )
                parsed = raw.parse()
                response = {
                    "object": getattr(parsed, "object", None),
                    "input_tokens": getattr(parsed, "input_tokens", None),
                }
                _require(
                    response["object"] == "response.input_tokens"
                    and type(response["input_tokens"]) is int
                    and response["input_tokens"] >= 0,
                    "provider token-count response shape drifted",
                )
                retries_taken = getattr(raw, "retries_taken", None)
                _require(retries_taken == 0, "provider token-count call used a retry")
                status_code = getattr(raw, "status_code", None)
                _require(status_code == 200, "provider token-count HTTP status drifted")
                journal.append(
                    "ProviderInputTokenCountCallCompleted",
                    {
                        "order": request["order"],
                        "label": request["label"],
                        "request_file_sha256": request["request_file_sha256"],
                        "request_semantic_hash": request["request_semantic_hash"],
                        "response": response,
                        "request_id": getattr(raw, "request_id", None),
                        "status_code": status_code,
                        "retries_taken": retries_taken,
                    },
                )
                responses.append(response)
            except BaseException as exc:
                journal.append(
                    "ProviderInputTokenCountCallFailed",
                    {
                        "order": request["order"],
                        "label": request["label"],
                        "request_file_sha256": request["request_file_sha256"],
                        "request_semantic_hash": request["request_semantic_hash"],
                        **_safe_failure(exc),
                    },
                )
                raise D108ExecutionError(
                    "D-108 provider token-count call failed; no retry or receipt is allowed"
                ) from exc

        receipt = _build_provider_receipt(preflight["plan"], responses)
        validated = validate_strict_provider_receipt(receipt, preflight["plan"])
        receipt_content = _pretty_json(receipt)
        _write_exact_or_new(paths.provider_receipt, receipt_content, exact_retry=False)
        receipt_binding = {
            **_file_binding(paths.provider_receipt, repository=repo, label="provider receipt"),
            "schema_version": receipt["schema_version"],
            "receipt_id": receipt["receipt_id"],
            "semantic_body_hash": receipt["semantic_body_hash"],
        }
        journal.append(
            "ProviderReceiptCommitted",
            {
                "provider_receipt": receipt_binding,
                "baseline_input_tokens": validated["baseline_input_tokens"],
                "with_memory_input_tokens": validated["with_memory_input_tokens"],
                "memory_delta_tokens": validated["memory_delta_tokens"],
                "provider_exact_budget_validated": True,
                "index_freeze_authorized": False,
            },
        )
    finally:
        journal.close()

    gate = build_d108_completion_gate(
        repository=repo,
        approval_path=paths.approval,
        journal_path=paths.journal,
        provider_receipt_path=paths.provider_receipt,
    )
    gate_content = _pretty_json(gate)
    _write_exact_or_new(paths.completion_gate, gate_content, exact_retry=False)
    return {
        "gate_id": gate["gate_id"],
        "semantic_body_hash": gate["semantic_body_hash"],
        "gate_file_sha256": d107.sha256_bytes(gate_content),
        "receipt_id": receipt["receipt_id"],
        "receipt_file_sha256": d107.sha256_bytes(receipt_content),
        "baseline_input_tokens": validated["baseline_input_tokens"],
        "with_memory_input_tokens": validated["with_memory_input_tokens"],
        "memory_delta_tokens": validated["memory_delta_tokens"],
        "provider_input_token_count_calls_made": 2,
        "provider_generation_calls_made": 0,
        "automatic_retry_used": False,
        "provider_exact_budget_validated": True,
        "index_freeze_authorized": False,
        "retrieval_ready": False,
        "core_campaign_unlocked": False,
        "billing_or_free_tier_claim": None,
    }


def _load_journal_success(path: Path) -> dict[str, Any]:
    content = _read_stable(path, label="D-108 execution journal")
    lines = content.splitlines(keepends=True)
    _require(len(lines) == 6, "D-108 successful journal event count drifted")
    expected_types = [
        "ExecutionClaimed",
        "ProviderInputTokenCountCallIssued",
        "ProviderInputTokenCountCallCompleted",
        "ProviderInputTokenCountCallIssued",
        "ProviderInputTokenCountCallCompleted",
        "ProviderReceiptCommitted",
    ]
    records: list[dict[str, Any]] = []
    previous_hash: str | None = None
    for sequence, (line, event_type) in enumerate(zip(lines, expected_types, strict=True), start=1):
        payload = _parse_json(line.rstrip(b"\r\n"), label="D-108 journal row")
        _strict_keys(
            payload,
            {
                "schema_version",
                "sequence",
                "event_type",
                "recorded_at",
                "previous_record_hash",
                "body",
                "record_hash",
            },
            label="D-108 journal row",
        )
        _require(line == _jsonl_row(payload), "D-108 journal row is not canonical")
        record_without_hash = {key: value for key, value in payload.items() if key != "record_hash"}
        _require(
            payload["schema_version"] == JOURNAL_SCHEMA_VERSION
            and payload["sequence"] == sequence
            and payload["event_type"] == event_type
            and payload["previous_record_hash"] == previous_hash
            and payload["record_hash"] == sha256_text(canonical_json(record_without_hash)),
            "D-108 journal hash chain drifted",
        )
        _validate_iso_timestamp(payload["recorded_at"], label="D-108 journal row")
        previous_hash = payload["record_hash"]
        records.append(payload)

    issued = [records[1], records[3]]
    completed = [records[2], records[4]]
    responses: list[dict[str, Any]] = []
    for order, label, issue, complete in zip(
        (1, 2),
        ("baseline", "with_memory"),
        issued,
        completed,
        strict=True,
    ):
        _strict_keys(
            issue["body"],
            {"order", "label", "request_file_sha256", "request_semantic_hash", "endpoint"},
            label="D-108 issued call body",
        )
        _strict_keys(
            complete["body"],
            {
                "order",
                "label",
                "request_file_sha256",
                "request_semantic_hash",
                "response",
                "request_id",
                "status_code",
                "retries_taken",
            },
            label="D-108 completed call body",
        )
        _strict_keys(
            complete["body"]["response"],
            {"object", "input_tokens"},
            label="D-108 completed response",
        )
        _require(
            issue["body"]["order"] == order
            and complete["body"]["order"] == order
            and issue["body"]["label"] == label
            and complete["body"]["label"] == label
            and issue["body"]["request_file_sha256"]
            == complete["body"]["request_file_sha256"]
            and issue["body"]["request_semantic_hash"]
            == complete["body"]["request_semantic_hash"]
            and issue["body"]["endpoint"] == EXPECTED_ENDPOINT
            and complete["body"]["status_code"] == 200
            and complete["body"]["retries_taken"] == 0,
            "D-108 journal call identity drifted",
        )
        response = complete["body"]["response"]
        _require(
            response["object"] == "response.input_tokens"
            and type(response["input_tokens"]) is int
            and response["input_tokens"] >= 0,
            "D-108 journal response drifted",
        )
        responses.append(response)

    return {
        "records": records,
        "responses": responses,
        "event_count": len(records),
        "head": previous_hash,
        "file_bytes": len(content),
        "file_sha256": d107.sha256_bytes(content),
    }


def build_d108_completion_gate(
    *,
    repository: str | Path | None = None,
    approval_path: str | Path = DEFAULT_APPROVAL_PATH,
    journal_path: str | Path = DEFAULT_JOURNAL_PATH,
    provider_receipt_path: str | Path = DEFAULT_PROVIDER_RECEIPT_PATH,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    approval = validate_d108_approval_receipt(approval_path, repository=repo)
    _, d107_gate = _load_exact_d107_gate(repo)
    plan, plan_binding = _load_exact_plan(repo)
    journal_selected = _resolved(journal_path, repository=repo, label="D-108 execution journal")
    journal = _load_journal_success(journal_selected)
    expected_requests = _request_pair(plan, repo)
    expected_claim = _execution_claim_body(
        approval=approval,
        plan_binding=plan_binding,
        implementation_files=_implementation_bindings(repo),
        environment=_expected_environment_evidence(),
        transport=_expected_transport_evidence(),
    )
    _require(
        journal["records"][0]["body"] == expected_claim,
        "D-108 execution claim binding drifted",
    )
    for record, request in zip(
        (journal["records"][1], journal["records"][3]),
        expected_requests,
        strict=True,
    ):
        _require(
            record["body"]
            == {
                "order": request["order"],
                "label": request["label"],
                "request_file_sha256": request["request_file_sha256"],
                "request_semantic_hash": request["request_semantic_hash"],
                "endpoint": EXPECTED_ENDPOINT,
            },
            "D-108 issued request binding drifted",
        )
    receipt_selected = _resolved(
        provider_receipt_path,
        repository=repo,
        label="D-108 provider receipt",
    )
    receipt_content = _read_stable(receipt_selected, label="D-108 provider receipt")
    receipt = _parse_json(receipt_content, label="D-108 provider receipt")
    _require(receipt_content == _pretty_json(receipt), "D-108 provider receipt is not canonical")
    validated = validate_strict_provider_receipt(receipt, plan)
    receipt_binding = {
        **_file_binding(receipt_selected, repository=repo, label="D-108 provider receipt"),
        "schema_version": receipt["schema_version"],
        "receipt_id": receipt["receipt_id"],
        "semantic_body_hash": receipt["semantic_body_hash"],
    }
    committed = journal["records"][-1]["body"]
    _strict_keys(
        committed,
        {
            "provider_receipt",
            "baseline_input_tokens",
            "with_memory_input_tokens",
            "memory_delta_tokens",
            "provider_exact_budget_validated",
            "index_freeze_authorized",
        },
        label="D-108 committed receipt body",
    )
    _require(
        committed["provider_receipt"] == receipt_binding
        and committed["baseline_input_tokens"] == validated["baseline_input_tokens"]
        and committed["with_memory_input_tokens"] == validated["with_memory_input_tokens"]
        and committed["memory_delta_tokens"] == validated["memory_delta_tokens"]
        and committed["provider_exact_budget_validated"] is True
        and committed["index_freeze_authorized"] is False,
        "D-108 committed receipt evidence drifted",
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "exact-two-provider-input-token-count-completion-gate",
        "recorded_at": journal["records"][-1]["recorded_at"],
        "d107_gate": d107_gate,
        "approval_receipt": approval,
        "token_count_plan": plan_binding,
        "execution_journal": {
            "path": journal_selected.relative_to(repo).as_posix(),
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "event_count": journal["event_count"],
            "head": journal["head"],
            "file_bytes": journal["file_bytes"],
            "file_sha256": journal["file_sha256"],
        },
        "provider_receipt": receipt_binding,
        "observed_counts": {
            "baseline_input_tokens": validated["baseline_input_tokens"],
            "with_memory_input_tokens": validated["with_memory_input_tokens"],
            "memory_delta_tokens": validated["memory_delta_tokens"],
            "maximum_memory_delta_tokens": 2_000,
        },
        "implementation_files": _implementation_bindings(repo),
        "authority": {
            "provider_input_token_count_calls_authorized": True,
            "provider_input_token_count_calls_made": 2,
            "provider_generation_calls_authorized": False,
            "provider_generation_calls_made": 0,
            "sdk_transport_max_retries": 0,
            "automatic_retry_used": False,
            "provider_exact_budget_validated": True,
            "index_freeze_authorization_candidate_ready": True,
            "index_freeze_authorized": False,
            "memory_index_frozen": False,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "memory_effect_established": False,
            "negative_transfer_established": False,
            "evaluator_calls_made": 0,
            "billing_or_free_tier_claim": None,
        },
        "next_gate": "explicit-d108-exact-index-freeze-authorization",
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": COMPLETION_GATE_SCHEMA_VERSION,
        "gate_id": f"d108_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def validate_d108_completion_gate(
    completion_gate_path: str | Path = DEFAULT_COMPLETION_GATE_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    path = _resolved(completion_gate_path, repository=repo, label="D-108 completion gate")
    content = _read_stable(path, label="D-108 completion gate")
    payload = _parse_json(content, label="D-108 completion gate")
    _root_identity(
        payload,
        schema_version=COMPLETION_GATE_SCHEMA_VERSION,
        id_field="gate_id",
        id_prefix="d108_",
        label="D-108 completion gate",
    )
    body = payload["semantic_body"]
    expected = build_d108_completion_gate(
        repository=repo,
        approval_path=body["approval_receipt"]["path"],
        journal_path=body["execution_journal"]["path"],
        provider_receipt_path=body["provider_receipt"]["path"],
    )
    _require(
        payload == expected and content == _pretty_json(expected),
        "D-108 completion gate drifted",
    )
    authority = body["authority"]
    _require(
        authority["provider_input_token_count_calls_made"] == 2
        and authority["provider_generation_calls_made"] == 0
        and authority["automatic_retry_used"] is False
        and authority["provider_exact_budget_validated"] is True
        and authority["index_freeze_authorization_candidate_ready"] is True
        and authority["index_freeze_authorized"] is False
        and authority["retrieval_ready"] is False
        and authority["core_campaign_unlocked"] is False,
        "D-108 completion authority widened",
    )
    return {
        "path": path.relative_to(repo).as_posix(),
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(content),
        "file_sha256": d107.sha256_bytes(content),
        **body["observed_counts"],
        "provider_input_token_count_calls_made": 2,
        "provider_generation_calls_made": 0,
        "automatic_retry_used": False,
        "provider_exact_budget_validated": True,
        "index_freeze_authorization_candidate_ready": True,
        "index_freeze_authorized": False,
        "retrieval_ready": False,
        "core_campaign_unlocked": False,
    }


__all__ = [
    "APPROVAL_SCHEMA_VERSION",
    "COMPLETION_GATE_SCHEMA_VERSION",
    "D108ExecutionError",
    "DEFAULT_APPROVAL_PATH",
    "DEFAULT_COMPLETION_GATE_PATH",
    "DEFAULT_JOURNAL_PATH",
    "DEFAULT_PROVIDER_RECEIPT_PATH",
    "JOURNAL_SCHEMA_VERSION",
    "build_d108_approval_receipt",
    "build_d108_completion_gate",
    "execute_d108_provider_token_counts",
    "materialize_d108_approval_receipt",
    "preflight_d108_execution",
    "validate_d108_approval_receipt",
    "validate_d108_completion_gate",
    "validate_strict_provider_receipt",
]
