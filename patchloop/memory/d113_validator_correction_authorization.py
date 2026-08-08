"""Seal an offline authorization candidate for correcting D-112 validators.

D-113 does not rewrite or replay D-112.  It binds the exact checked-in D-112
receipt, completion gate, and executed implementation; records validator gaps
that were found after execution; and describes a separately approved,
append-only D-114 correction.  No model, retriever, provider, evaluator, or
agent is called here.
"""

from __future__ import annotations

import ast
import json
import os
import stat
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-113"
PREFLIGHT_SCHEMA_VERSION = "d112-validator-gap-audit-d113-v1"
CANDIDATE_SCHEMA_VERSION = "validator-correction-authorization-candidate-d113-v1"
CORRECTION_ACTION_SCHEMA_VERSION = "append-only-d112-validator-correction-d113-v1"
SOURCE_GATE_SCHEMA_VERSION = "validator-correction-authorization-source-gate-d113-v1"

PREFLIGHT_RECORDED_AT = "2026-08-07T02:22:30Z"
CANDIDATE_RECORDED_AT = "2026-08-07T02:22:31Z"
GATE_RECORDED_AT = "2026-08-07T02:22:32Z"

DEFAULT_D112_RECEIPT_PATH = Path(
    "reports/memory-development/d112-retrieval-readiness-probe-receipt.json"
)
DEFAULT_D112_GATE_PATH = Path(
    "reports/memory-development/d112-retrieval-readiness-completion-gate.json"
)
DEFAULT_PREFLIGHT_PATH = Path(
    "reports/memory-development/d113-d112-validator-correction-preflight.json"
)
DEFAULT_CANDIDATE_PATH = Path(
    "reports/memory-development/d113-validator-correction-authorization-candidate.json"
)
DEFAULT_SOURCE_GATE_PATH = Path(
    "reports/memory-development/d113-validator-correction-source-gate.json"
)

EXPECTED_D112_RECEIPT_ID = (
    "d112probereceipt_ad73368b4b0f47174f53762c917f9f39f17e22ac3bd077d795b0b9e1ac8c9257"
)
EXPECTED_D112_RECEIPT_BODY_SHA = (
    "sha256:ad73368b4b0f47174f53762c917f9f39f17e22ac3bd077d795b0b9e1ac8c9257"
)
EXPECTED_D112_RECEIPT_BYTES = 13_835
EXPECTED_D112_RECEIPT_FILE_SHA = (
    "sha256:74fcd761cac65a9cab26529076b7cde60eaa14a1faf40475e680f526e00ba1d1"
)
EXPECTED_D112_GATE_ID = "d112_3242bed73c9a322ff1d346eba61cfec2f9eae3b57e4cc7e4d7b0e9a5456367b6"
EXPECTED_D112_GATE_BODY_SHA = (
    "sha256:3242bed73c9a322ff1d346eba61cfec2f9eae3b57e4cc7e4d7b0e9a5456367b6"
)
EXPECTED_D112_GATE_BYTES = 77_591
EXPECTED_D112_GATE_FILE_SHA = (
    "sha256:a7e691ae43c60405cbb10cd27caf3055eabaa96bb7fa6f2a02142d97aa903951"
)
EXPECTED_D112_INPUT_FINGERPRINT = (
    "sha256:d54454b2693e231c0ef50c94b20d75d58f00a885dfae98d3b6b190665f9d2e17"
)
EXPECTED_APPROVAL_RECORDED_AT = "2026-08-06T16:41:32.316176Z"
EXPECTED_EXECUTION_CLAIMED_AT = "2026-08-06T17:16:20.878831Z"
EXPECTED_COMPLETION_RECORDED_AT = "2026-08-06T17:18:33.876453Z"

D112_IMPLEMENTATION_SPECS = (
    {
        "path": "patchloop/memory/d112_retrieval_readiness_probe.py",
        "file_bytes": 54_182,
        "file_sha256": "sha256:3df099f518b8c0707a6f6a81921c8735037fb97f1357a45b238148ac67c70d2b",
    },
    {
        "path": "scripts/run_d112_retrieval_readiness_probe.py",
        "file_bytes": 2_000,
        "file_sha256": "sha256:308ed1e6499da73edf064a8ecd211c526c4ef4c0fc0123623f1723135b78cd9e",
    },
    {
        "path": "tests/test_d112_retrieval_readiness_probe.py",
        "file_bytes": 11_297,
        "file_sha256": "sha256:3629de37190cd8337fb3a5c2da07eb6795ca65f8e6599f4ac275fd135e393bb6",
    },
)

D113_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d113_validator_correction_authorization.py"),
    Path("scripts/build_d113_validator_correction_authorization_candidate.py"),
    Path("tests/test_d113_validator_correction_authorization.py"),
)

FUTURE_D114_PATHS = (
    "patchloop/memory/d114_d112_validator_correction.py",
    "scripts/build_d114_d112_validator_correction.py",
    "tests/test_d114_d112_validator_correction.py",
    "reports/memory-development/d114-d112-validator-correction-receipt.json",
    "reports/memory-development/d114-d112-validator-correction-gate.json",
)

PROTECTED_D112_PATHS = (
    DEFAULT_D112_RECEIPT_PATH.as_posix(),
    DEFAULT_D112_GATE_PATH.as_posix(),
    *(row["path"] for row in D112_IMPLEMENTATION_SPECS),
)

GAP_IDS = (
    "skip-current-not-portable",
    "receipt-validator-not-exact",
    "timestamp-chronology-not-enforced",
    "one-use-repository-local-only",
    "network-zero-not-socket-instrumented",
)

RECEIPT_ROOT_KEYS = (
    "schema_version",
    "receipt_id",
    "semantic_body_hash",
    "semantic_body",
)
RECEIPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "approval_recorded_at",
    "execution_claimed_at",
    "approval_action_id",
    "approval_reference",
    "approval_reference_mode",
    "approval_statement_code",
    "d111_source_gate",
    "d111_candidate",
    "authorized_action_hash",
    "authorized_scope",
    "probe_ids_in_order",
    "pre_execution_input",
    "claim_semantics",
    "self_attested",
    "approver_kind",
    "approver_label",
    "reviewer_identity_authenticated",
    "cryptographic_signature_verified",
    "execution_result_present",
)
RECEIPT_CLAIM_KEYS = (
    "exclusive_create_and_fsync_required",
    "claim_created_before_model_load",
    "receipt_is_one_use_consumption_marker",
    "failure_or_hard_kill_remains_consumed",
    "automatic_retry_or_rollback_allowed",
    "completion_gate_required_for_success",
    "sidecar_does_not_modify_frozen_authority",
)
GATE_ROOT_KEYS = (
    "schema_version",
    "gate_id",
    "semantic_body_hash",
    "semantic_body",
)
GATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "probe_receipt",
    "input_integrity",
    "embedding_execution",
    "query_vectors",
    "diagnostic_scoring",
    "implementation_files",
    "qualification",
    "evidence_boundary",
    "authority",
    "next_gate",
)
UNCHECKED_RECEIPT_FIELDS = (
    "milestone",
    "evidence_kind",
    "approval_reference_mode",
    "approver_kind",
    "approver_label",
    "claim_semantics.receipt_is_one_use_consumption_marker",
    "claim_semantics.completion_gate_required_for_success",
)


class D113AuthorizationError(ContractError):
    """Raised when D-113 evidence, scope, or exact bytes drift."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D113AuthorizationError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        return selected.resolve()
    except OSError as exc:
        raise D113AuthorizationError("D-113 repository root cannot be resolved") from exc


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
        raise D113AuthorizationError(f"D-113 {label} escapes the repository") from exc
    current = selected
    while current != repository and current != current.parent:
        _require(
            not _is_linklike(current),
            f"D-113 {label} cannot traverse a link or junction",
        )
        current = current.parent
    return resolved


def _read_stable(path: Path, *, label: str) -> bytes:
    _require(not _is_linklike(path), f"D-113 {label} cannot be a link or junction")
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except OSError as exc:
        raise D113AuthorizationError(f"D-113 {label} is unavailable") from exc
    _require(first == second, f"D-113 {label} changed while being read")
    return first


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D113AuthorizationError(f"D-113 {label} JSON is invalid") from exc
    _require(isinstance(payload, dict), f"D-113 {label} JSON root is invalid")
    return payload


def _pretty_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _parse_utc(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"D-113 {label} is invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise D113AuthorizationError(f"D-113 {label} is invalid") from exc
    _require(parsed.tzinfo is not None, f"D-113 {label} is not timezone-aware")
    return parsed.astimezone(UTC)


def _exact_root_identity(
    payload: Mapping[str, Any],
    *,
    schema_version: str,
    id_field: str,
    id_prefix: str,
    label: str,
) -> None:
    _require(
        set(payload) == {"schema_version", id_field, "semantic_body_hash", "semantic_body"},
        f"D-113 {label} root keys drifted",
    )
    _require(payload.get("schema_version") == schema_version, f"D-113 {label} schema drifted")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), f"D-113 {label} body is invalid")
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload.get("semantic_body_hash") == body_hash
        and payload.get(id_field) == f"{id_prefix}{body_hash.removeprefix('sha256:')}",
        f"D-113 {label} identity drifted",
    )


def _file_binding(path: str | Path, *, repository: Path, label: str) -> dict[str, Any]:
    selected = _resolved(path, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _artifact_binding(
    payload: Mapping[str, Any],
    content: bytes,
    *,
    path: Path,
    id_field: str,
) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        id_field: payload[id_field],
        "semantic_body_hash": payload["semantic_body_hash"],
    }


def _require_exact_keys(value: Any, expected: Sequence[str], *, label: str) -> None:
    _require(isinstance(value, dict), f"D-113 {label} is invalid")
    _require(set(value) == set(expected), f"D-113 {label} keys drifted")


def _load_exact_d112_inputs(repository: Path) -> dict[str, Any]:
    receipt_path = _resolved(
        DEFAULT_D112_RECEIPT_PATH,
        repository=repository,
        label="D-112 receipt",
    )
    gate_path = _resolved(DEFAULT_D112_GATE_PATH, repository=repository, label="D-112 gate")
    receipt_content = _read_stable(receipt_path, label="D-112 receipt")
    gate_content = _read_stable(gate_path, label="D-112 gate")
    _require(
        len(receipt_content) == EXPECTED_D112_RECEIPT_BYTES
        and sha256_bytes(receipt_content) == EXPECTED_D112_RECEIPT_FILE_SHA,
        "D-113 exact D-112 receipt bytes drifted",
    )
    _require(
        len(gate_content) == EXPECTED_D112_GATE_BYTES
        and sha256_bytes(gate_content) == EXPECTED_D112_GATE_FILE_SHA,
        "D-113 exact D-112 gate bytes drifted",
    )
    receipt = _parse_json(receipt_content, label="D-112 receipt")
    gate = _parse_json(gate_content, label="D-112 gate")
    _require(receipt_content == _pretty_json(receipt), "D-113 D-112 receipt is not canonical")
    _require(gate_content == _pretty_json(gate), "D-113 D-112 gate is not canonical")
    _require_exact_keys(receipt, RECEIPT_ROOT_KEYS, label="D-112 receipt root")
    _require_exact_keys(gate, GATE_ROOT_KEYS, label="D-112 gate root")
    _require(
        receipt["receipt_id"] == EXPECTED_D112_RECEIPT_ID
        and receipt["semantic_body_hash"] == EXPECTED_D112_RECEIPT_BODY_SHA
        and sha256_text(canonical_json(receipt["semantic_body"])) == EXPECTED_D112_RECEIPT_BODY_SHA,
        "D-113 D-112 receipt identity drifted",
    )
    _require(
        gate["gate_id"] == EXPECTED_D112_GATE_ID
        and gate["semantic_body_hash"] == EXPECTED_D112_GATE_BODY_SHA
        and sha256_text(canonical_json(gate["semantic_body"])) == EXPECTED_D112_GATE_BODY_SHA,
        "D-113 D-112 gate identity drifted",
    )
    receipt_body = receipt["semantic_body"]
    gate_body = gate["semantic_body"]
    _require_exact_keys(receipt_body, RECEIPT_BODY_KEYS, label="D-112 receipt body")
    _require_exact_keys(
        receipt_body.get("claim_semantics"),
        RECEIPT_CLAIM_KEYS,
        label="D-112 receipt claim semantics",
    )
    _require_exact_keys(gate_body, GATE_BODY_KEYS, label="D-112 gate body")

    approval_at = _parse_utc(receipt_body.get("approval_recorded_at"), label="approval time")
    execution_at = _parse_utc(receipt_body.get("execution_claimed_at"), label="execution time")
    completion_at = _parse_utc(gate_body.get("recorded_at"), label="completion time")
    _require(
        receipt_body["approval_recorded_at"] == EXPECTED_APPROVAL_RECORDED_AT
        and receipt_body["execution_claimed_at"] == EXPECTED_EXECUTION_CLAIMED_AT
        and gate_body["recorded_at"] == EXPECTED_COMPLETION_RECORDED_AT,
        "D-113 exact D-112 timestamps drifted",
    )
    _require(
        approval_at <= execution_at <= completion_at,
        "D-113 actual D-112 chronology is invalid",
    )

    receipt_binding = {
        "path": DEFAULT_D112_RECEIPT_PATH.as_posix(),
        "file_bytes": EXPECTED_D112_RECEIPT_BYTES,
        "file_sha256": EXPECTED_D112_RECEIPT_FILE_SHA,
        "schema_version": receipt["schema_version"],
        "receipt_id": EXPECTED_D112_RECEIPT_ID,
        "semantic_body_hash": EXPECTED_D112_RECEIPT_BODY_SHA,
    }
    _require(
        gate_body.get("probe_receipt") == receipt_binding,
        "D-113 D-112 gate receipt binding drifted",
    )
    pre_input = receipt_body.get("pre_execution_input")
    integrity = gate_body.get("input_integrity")
    _require(isinstance(pre_input, dict), "D-113 D-112 receipt input is invalid")
    _require(isinstance(integrity, dict), "D-113 D-112 gate integrity is invalid")
    _require(
        pre_input.get("fingerprint") == EXPECTED_D112_INPUT_FINGERPRINT
        and integrity.get("pre_execution") == pre_input
        and integrity.get("post_execution") == pre_input
        and integrity.get("fingerprints_equal") is True,
        "D-113 D-112 pre/post input evidence drifted",
    )

    implementation_bindings = [
        _file_binding(row["path"], repository=repository, label="D-112 implementation")
        for row in D112_IMPLEMENTATION_SPECS
    ]
    _require(
        implementation_bindings == [dict(row) for row in D112_IMPLEMENTATION_SPECS]
        and gate_body.get("implementation_files") == implementation_bindings,
        "D-113 executed D-112 implementation bytes drifted",
    )

    protected_evidence: list[dict[str, Any]] = []
    input_state = pre_input.get("state")
    _require(isinstance(input_state, dict), "D-113 D-112 input state is invalid")
    for field in (
        "portable_frozen_index",
        "portable_frozen_marker",
        "portable_d106_unfrozen_index",
    ):
        recorded = input_state.get(field)
        _require(isinstance(recorded, dict), f"D-113 D-112 {field} binding is invalid")
        current = _file_binding(recorded["path"], repository=repository, label=field)
        _require(current == recorded, f"D-113 D-112 {field} bytes drifted")
        protected_evidence.append(current)

    authority = gate_body.get("authority")
    boundary = gate_body.get("evidence_boundary")
    scoring = gate_body.get("diagnostic_scoring")
    _require(
        isinstance(authority, dict)
        and authority.get("retrieval_ready") is False
        and authority.get("retrieval_experiment_authorized") is False
        and authority.get("runtime_memory_injection_count") == 0
        and authority.get("score_policy_correction_authorized") is False
        and authority.get("core_campaign_unlocked") is False,
        "D-113 D-112 closed authority drifted",
    )
    _require(
        isinstance(boundary, dict)
        and boundary.get("os_level_network_block_verified") is False
        and boundary.get("provider_calls_made") == 0
        and boundary.get("evaluator_calls_made") == 0,
        "D-113 D-112 evidence boundary drifted",
    )
    _require(
        isinstance(scoring, dict)
        and scoring.get("score_row_count") == 9
        and scoring.get("all_diagnostic_no_match") is True
        and scoring.get("runtime_selection_executed") is False
        and scoring.get("memory_text_returned") is False,
        "D-113 D-112 diagnostic result drifted",
    )

    source_path = _resolved(
        D112_IMPLEMENTATION_SPECS[0]["path"],
        repository=repository,
        label="D-112 source",
    )
    source_content = _read_stable(source_path, label="D-112 source")
    try:
        source_text = source_content.decode("utf-8")
        source_tree = ast.parse(source_text)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise D113AuthorizationError("D-113 D-112 source cannot be audited") from exc
    return {
        "receipt": receipt,
        "receipt_content": receipt_content,
        "gate": gate,
        "gate_content": gate_content,
        "implementation_bindings": implementation_bindings,
        "protected_evidence": protected_evidence,
        "source_text": source_text,
        "source_tree": source_tree,
    }


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise D113AuthorizationError(f"D-113 audited function is missing: {name}")


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _call_lines(node: ast.AST, name: str) -> list[int]:
    return sorted(
        call.lineno
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and _call_name(call) == name
    )


def _if_name_lines(node: ast.AST, name: str) -> list[int]:
    return sorted(
        item.lineno
        for item in ast.walk(node)
        if isinstance(item, ast.If)
        and any(isinstance(part, ast.Name) and part.id == name for part in ast.walk(item.test))
    )


def _segment(source: str, node: ast.AST) -> str:
    return ast.get_source_segment(source, node) or ""


def _has_compare_with(source: str, node: ast.AST, names: Sequence[str]) -> bool:
    return any(
        all(name in _segment(source, item) for name in names)
        for item in ast.walk(node)
        if isinstance(item, ast.Compare)
    )


def _audit_d112_validator(context: Mapping[str, Any]) -> list[dict[str, Any]]:
    tree = context["source_tree"]
    source = context["source_text"]
    validate_gate = _function(tree, "validate_d112_completion_gate")
    validate_receipt = _function(tree, "validate_d112_probe_receipt")
    input_state = _function(tree, "_input_state")
    snapshot = _function(tree, "_snapshot_evidence")
    root_identity = _function(tree, "_root_identity")
    writer = _function(tree, "_write_new_fsynced")
    execute = _function(tree, "execute_d112_scoring_diagnostic")
    config = _function(tree, "_embedding_config")
    loader = _function(tree, "_default_model_loader")

    input_lines = _call_lines(validate_gate, "_input_state")
    verify_lines = _if_name_lines(validate_gate, "verify_current_inputs")
    _require(
        input_lines and verify_lines and input_lines[0] < verify_lines[0],
        "D-113 skip-current audit no longer matches D-112 source",
    )
    _require(
        _call_lines(input_state, "_snapshot_evidence")
        and _call_lines(snapshot, "validate_d106_snapshot_files")
        and _call_lines(snapshot, "_installed_dependency_versions"),
        "D-113 snapshot/dependency audit no longer matches D-112 source",
    )

    receipt_calls = {
        name
        for call in ast.walk(validate_receipt)
        if isinstance(call, ast.Call) and (name := _call_name(call)) is not None
    }
    gate_calls = {
        name
        for call in ast.walk(validate_gate)
        if isinstance(call, ast.Call) and (name := _call_name(call)) is not None
    }
    root_calls = {
        name
        for call in ast.walk(root_identity)
        if isinstance(call, ast.Call) and (name := _call_name(call)) is not None
    }
    _require(
        "build_d112_probe_receipt" not in receipt_calls
        and "build_d112_completion_gate" in gate_calls
        and "get" in root_calls
        and "keys" not in root_calls,
        "D-113 exact-payload audit no longer matches D-112 source",
    )

    receipt_chronology = _has_compare_with(
        source,
        validate_receipt,
        ("approval_recorded_at", "execution_claimed_at"),
    )
    gate_chronology = _has_compare_with(
        source,
        validate_gate,
        ("execution_claimed_at", "recorded_at"),
    )
    _require(
        not receipt_chronology and not gate_chronology,
        "D-113 chronology audit no longer matches D-112 source",
    )

    writer_segment = _segment(source, writer)
    execute_write_lines = _call_lines(execute, "_write_new_fsynced")
    loader_lines = _call_lines(execute, "loader")
    _require(
        '.open("xb")' in writer_segment
        and "os.fsync" in writer_segment
        and execute_write_lines
        and loader_lines
        and execute_write_lines[0] < loader_lines[0],
        "D-113 one-use ordering audit no longer matches D-112 source",
    )

    config_segment = _segment(source, config)
    loader_segment = _segment(source, loader)
    _require(
        '"os_socket_block_verified": False' in config_segment
        and '"local_files_only"' in loader_segment
        and "_offline_library_environment" in loader_segment,
        "D-113 network-boundary audit no longer matches D-112 source",
    )

    source_sha = context["implementation_bindings"][0]["file_sha256"]
    findings = [
        {
            "gap_id": "skip-current-not-portable",
            "status": "observed",
            "affected_function": "validate_d112_completion_gate",
            "source_file_sha256": source_sha,
            "evidence": {
                "input_state_call_line": input_lines[0],
                "verify_current_inputs_branch_line": verify_lines[0],
                "input_state_precedes_flag_branch": True,
                "input_state_calls_snapshot_evidence": True,
                "snapshot_requires_local_snapshot_and_exact_dependencies": True,
            },
            "claim_limit": ("verify_current_inputs=false is not a clean-clone portable mode"),
        },
        {
            "gap_id": "receipt-validator-not-exact",
            "status": "observed",
            "affected_function": "validate_d112_probe_receipt",
            "source_file_sha256": source_sha,
            "evidence": {
                "full_receipt_rebuild_call_present": False,
                "root_exact_key_set_enforced": False,
                "completion_gate_full_rebuild_call_present": True,
                "unchecked_receipt_fields": list(UNCHECKED_RECEIPT_FIELDS),
                "paired_receipt_and_gate_rehash_not_fail_closed": True,
            },
            "claim_limit": (
                "the checked-in bytes are exact, but the validator is not a general "
                "unknown-field or unchecked-claim tamper proof"
            ),
        },
        {
            "gap_id": "timestamp-chronology-not-enforced",
            "status": "observed",
            "affected_function": "validate_d112_probe_receipt/validate_d112_completion_gate",
            "source_file_sha256": source_sha,
            "evidence": {
                "timestamp_format_checked": True,
                "approval_before_execution_compare_present": False,
                "execution_before_completion_compare_present": False,
                "actual_checked_in_chronology_valid": True,
            },
            "claim_limit": (
                "the actual timestamps are ordered, but D-112 validation does not enforce order"
            ),
        },
        {
            "gap_id": "one-use-repository-local-only",
            "status": "observed",
            "affected_function": "_write_new_fsynced/execute_d112_scoring_diagnostic",
            "source_file_sha256": source_sha,
            "evidence": {
                "repository_confined_path": True,
                "exclusive_binary_create": True,
                "file_fsync": True,
                "receipt_commit_precedes_loader_call": True,
                "global_ledger_present": False,
                "authenticated_signature_present": False,
                "cross_clone_exclusion_present": False,
            },
            "claim_limit": (
                "one-use is a repository-local cooperative claim, not a global uniqueness proof"
            ),
        },
        {
            "gap_id": "network-zero-not-socket-instrumented",
            "status": "observed",
            "affected_function": "_default_model_loader/_embedding_config",
            "source_file_sha256": source_sha,
            "evidence": {
                "library_offline_environment_present": True,
                "local_files_only_present": True,
                "os_socket_block_verified": False,
                "socket_instrumentation_present": False,
                "network_zero_is_source_path_and_self_attested": True,
            },
            "claim_limit": (
                "the run records offline/local-only configuration, not OS-level socket blocking"
            ),
        },
    ]
    _require(
        tuple(row["gap_id"] for row in findings) == GAP_IDS,
        "D-113 validator gap order drifted",
    )
    return findings


def _protected_fingerprints(context: Mapping[str, Any]) -> dict[str, str]:
    values = {
        DEFAULT_D112_RECEIPT_PATH.as_posix(): sha256_bytes(context["receipt_content"]),
        DEFAULT_D112_GATE_PATH.as_posix(): sha256_bytes(context["gate_content"]),
    }
    values.update({row["path"]: row["file_sha256"] for row in context["implementation_bindings"]})
    values.update({row["path"]: row["file_sha256"] for row in context["protected_evidence"]})
    return dict(sorted(values.items()))


def build_d113_preflight(
    *,
    repository: str | Path | None = None,
    _context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    context = dict(_context) if _context is not None else _load_exact_d112_inputs(repo)
    receipt = context["receipt"]
    gate = context["gate"]
    receipt_body = receipt["semantic_body"]
    gate_body = gate["semantic_body"]
    findings = _audit_d112_validator(context)
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "exact-d112-validator-gap-audit",
        "recorded_at": PREFLIGHT_RECORDED_AT,
        "exact_d112_receipt": _artifact_binding(
            receipt,
            context["receipt_content"],
            path=DEFAULT_D112_RECEIPT_PATH,
            id_field="receipt_id",
        ),
        "exact_d112_completion_gate": _artifact_binding(
            gate,
            context["gate_content"],
            path=DEFAULT_D112_GATE_PATH,
            id_field="gate_id",
        ),
        "executed_d112_implementation_files": context["implementation_bindings"],
        "protected_portable_evidence": context["protected_evidence"],
        "actual_execution_facts": {
            "approval_recorded_at": receipt_body["approval_recorded_at"],
            "execution_claimed_at": receipt_body["execution_claimed_at"],
            "completion_recorded_at": gate_body["recorded_at"],
            "actual_chronology_valid": True,
            "pre_post_input_fingerprint": EXPECTED_D112_INPUT_FINGERPRINT,
            "pre_post_input_fingerprints_equal": True,
            "score_row_count": 9,
            "all_diagnostic_no_match": True,
            "runtime_selection_executed": False,
            "memory_text_returned": False,
        },
        "validator_gap_findings": findings,
        "assessment": {
            "exact_checked_in_d112_bytes_bound": True,
            "actual_checked_in_chronology_valid": True,
            "general_receipt_tamper_proof_established": False,
            "clean_clone_portable_validation_established": False,
            "global_one_use_established": False,
            "os_socket_block_established": False,
            "append_only_validator_correction_candidate_ready": True,
            "score_policy_decision_ready": False,
            "retrieval_ready": False,
            "core_campaign_ready": False,
        },
        "evidence_boundary": {
            "d112_validator_invoked": False,
            "d112_execution_replayed": False,
            "snapshot_or_model_file_read": False,
            "embedding_model_load_count": 0,
            "query_encode_call_count": 0,
            "retrieval_calls": 0,
            "runtime_memory_injection_count": 0,
            "agent_runs": 0,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "network_accessed": False,
            "private_hidden_reference_or_known_bad_read": False,
            "d112_or_index_mutations": 0,
            "added_model_cost_usd": 0,
        },
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "preflight_id": f"d113preflight_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def validate_d113_preflight_payload(
    preflight: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
    _context: Mapping[str, Any] | None = None,
) -> None:
    _exact_root_identity(
        preflight,
        schema_version=PREFLIGHT_SCHEMA_VERSION,
        id_field="preflight_id",
        id_prefix="d113preflight_",
        label="preflight",
    )
    repo = _repo_root(repository)
    context = dict(_context) if _context is not None else _load_exact_d112_inputs(repo)
    expected = build_d113_preflight(repository=repo, _context=context)
    _require(preflight == expected, "D-113 preflight semantic content drifted")


def build_d113_authorization_candidate(
    preflight: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
    _context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    context = dict(_context) if _context is not None else _load_exact_d112_inputs(repo)
    validate_d113_preflight_payload(preflight, repository=repo, _context=context)
    preflight_content = _pretty_json(preflight)
    future_action = {
        "schema_version": CORRECTION_ACTION_SCHEMA_VERSION,
        "action_kind": "append-only-d112-validator-correction",
        "future_milestone": "D-114",
        "future_paths": list(FUTURE_D114_PATHS),
        "new_files_only": True,
        "d112_bound_files_may_be_modified": False,
        "existing_artifact_or_index_mutation_allowlist": [],
        "d112_execution_replay_allowed": False,
        "d112_one_use_capability_recreated": False,
        "correction_evidence_materializations": 1,
        "read_only_validator_reruns_allowed": True,
        "automatic_retry_after_partial_materialization_allowed": False,
        "required_corrections": {
            "receipt_and_gate_exact_root_key_sets": True,
            "receipt_and_gate_exact_semantic_body_key_sets": True,
            "receipt_expected_payload_full_equality": True,
            "rehashed_unknown_field_rejected": True,
            "rehashed_unchecked_claim_field_rejected": True,
            "paired_receipt_gate_rehash_rejected": True,
            "approval_execution_completion_chronology_enforced": True,
            "current_input_and_sealed_historical_modes_separated": True,
            "portable_mode_avoids_local_model_snapshot": True,
            "portable_mode_avoids_exact_installed_dependency_requirement": True,
            "portable_score_replay_uses_checked_in_frozen_index_gate_vectors_and_public_specs": (
                True
            ),
            "repository_local_one_use_claim_named_accurately": True,
            "network_claim_limited_to_source_path_and_self_attestation": True,
        },
        "required_tests": {
            "exact_d112_artifacts_pass": True,
            "unknown_root_body_and_claim_fields_fail": True,
            "each_unchecked_receipt_field_flip_fails": True,
            "approval_after_execution_fails": True,
            "execution_after_completion_fails": True,
            "paired_receipt_gate_rehash_fails": True,
            "portable_mode_forbids_snapshot_and_dependency_rehydration": True,
            "portable_mode_forbids_model_load_and_encode": True,
            "retrieval_provider_evaluator_and_agent_calls_remain_zero": True,
            "d112_and_index_bytes_unchanged": True,
        },
        "claim_limits": {
            "human_reviewer_identity_authenticated": False,
            "cryptographic_signature_verified": False,
            "global_one_use_proved": False,
            "cross_clone_exclusion_proved": False,
            "os_socket_block_proved": False,
            "clean_clone_portability_already_validated": False,
            "d112_scores_or_ranking_corrected": False,
            "memory_effect_established": False,
            "negative_transfer_established": False,
        },
        "closed_runtime_boundaries": {
            "score_weights_or_threshold_change_allowed": False,
            "ranking_policy_change_allowed": False,
            "memory_entry_change_allowed": False,
            "index_or_marker_change_allowed": False,
            "retrieval_execution_allowed": False,
            "runtime_memory_injection_allowed": False,
            "agent_run_allowed": False,
            "model_load_or_encode_allowed": False,
            "provider_call_allowed": False,
            "evaluator_call_allowed": False,
            "network_access_allowed": False,
            "core_campaign_allowed": False,
            "analysis_campaign_allowed": False,
        },
    }
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "validator-correction-authorization-candidate",
        "recorded_at": CANDIDATE_RECORDED_AT,
        "preflight": _artifact_binding(
            preflight,
            preflight_content,
            path=DEFAULT_PREFLIGHT_PATH,
            id_field="preflight_id",
        ),
        "candidate_status": "awaiting-exact-user-approval",
        "proposed_action": future_action,
        "proposed_action_hash": sha256_text(canonical_json(future_action)),
        "protected_d112_paths": list(PROTECTED_D112_PATHS),
        "approval_contract": {
            "separate_user_message_required": True,
            "exact_candidate_id_required": True,
            "exact_semantic_body_hash_required": True,
            "exact_file_sha256_required": True,
            "generic_continue_message_is_approval": False,
            "approval_receipt_created_by_d113": False,
            "approval_is_self_attested_not_authenticated": True,
        },
        "authority": {
            "validator_correction_candidate_ready": True,
            "exact_candidate_user_approval_received": False,
            "validator_correction_authorized": False,
            "validator_correction_implemented": False,
            "d112_artifacts_rewritten": False,
            "score_policy_correction_authorized": False,
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
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "candidate_id": f"d113validatorcandidate_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def validate_d113_candidate_payload(
    candidate: Mapping[str, Any],
    preflight: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
    _context: Mapping[str, Any] | None = None,
) -> None:
    _exact_root_identity(
        candidate,
        schema_version=CANDIDATE_SCHEMA_VERSION,
        id_field="candidate_id",
        id_prefix="d113validatorcandidate_",
        label="candidate",
    )
    expected = build_d113_authorization_candidate(
        preflight,
        repository=repository,
        _context=_context,
    )
    _require(candidate == expected, "D-113 candidate semantic content drifted")


def build_d113_source_gate(
    preflight: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
    _context: Mapping[str, Any] | None = None,
    implementation_bindings: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    context = dict(_context) if _context is not None else _load_exact_d112_inputs(repo)
    validate_d113_preflight_payload(preflight, repository=repo, _context=context)
    validate_d113_candidate_payload(
        candidate,
        preflight,
        repository=repo,
        _context=context,
    )
    bindings = (
        [dict(row) for row in implementation_bindings]
        if implementation_bindings is not None
        else [
            _file_binding(path, repository=repo, label="D-113 implementation")
            for path in D113_IMPLEMENTATION_PATHS
        ]
    )
    preflight_content = _pretty_json(preflight)
    candidate_content = _pretty_json(candidate)
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "validator-correction-authorization-source-gate",
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
            "exact_d112_receipt_and_gate_bound": True,
            "executed_d112_implementation_bytes_bound": True,
            "actual_d112_chronology_valid": True,
            "five_validator_gaps_recorded": True,
            "d112_validator_or_execution_not_invoked": True,
            "snapshot_model_retrieval_and_external_calls_zero": True,
            "protected_d112_and_index_bytes_unchanged": True,
            "candidate_only_no_approval_receipt": True,
        },
        "authority": {
            "validator_correction_candidate_ready": True,
            "exact_candidate_user_approval_received": False,
            "validator_correction_authorized": False,
            "validator_correction_implemented": False,
            "score_policy_correction_authorized": False,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": "exact-d113-candidate-id-body-sha-file-sha-user-approval",
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": SOURCE_GATE_SCHEMA_VERSION,
        "gate_id": f"d113_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _preflight_output(path: Path, content: bytes, *, repository: Path) -> Path:
    selected = _resolved(
        path,
        repository=repository,
        label="D-113 output",
        must_exist=False,
    )
    selected.parent.mkdir(parents=True, exist_ok=True)
    _require(not _is_linklike(selected.parent), "D-113 output parent cannot be linked")
    if selected.exists():
        _require(
            _read_stable(selected, label="D-113 existing output") == content,
            f"D-113 output already exists with different bytes: {path.as_posix()}",
        )
    return selected


def _write_exact(path: Path, content: bytes) -> None:
    if path.exists():
        _require(path.read_bytes() == content, "D-113 exact retry output drifted")
        return
    try:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise D113AuthorizationError("D-113 output write failed") from exc


def run_d113_offline_source_gate(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    context = _load_exact_d112_inputs(repo)
    before = _protected_fingerprints(context)
    preflight = build_d113_preflight(repository=repo, _context=context)
    candidate = build_d113_authorization_candidate(
        preflight,
        repository=repo,
        _context=context,
    )
    gate = build_d113_source_gate(
        preflight,
        candidate,
        repository=repo,
        _context=context,
    )
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
    after_context = _load_exact_d112_inputs(repo)
    after = _protected_fingerprints(after_context)
    _require(before == after, "D-113 protected D-112 or index evidence changed")
    validation = validate_d113_source_gate(repository=repo, _context=after_context)
    candidate_content = outputs[DEFAULT_CANDIDATE_PATH]
    return {
        **validation,
        "preflight_id": preflight["preflight_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_semantic_body_hash": candidate["semantic_body_hash"],
        "candidate_file_bytes": len(candidate_content),
        "candidate_file_sha256": sha256_bytes(candidate_content),
        "protected_fingerprints_equal": before == after,
        "d112_validator_invoked": False,
        "model_load_count": 0,
        "query_encode_call_count": 0,
        "retrieval_calls": 0,
        "runtime_memory_injection_count": 0,
        "agent_runs": 0,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "added_model_cost_usd": 0,
    }


def validate_d113_source_gate(
    gate_path: str | Path = DEFAULT_SOURCE_GATE_PATH,
    *,
    repository: str | Path | None = None,
    verify_current_implementation: bool = True,
    _context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    context = dict(_context) if _context is not None else _load_exact_d112_inputs(repo)
    selected_preflight = _resolved(
        DEFAULT_PREFLIGHT_PATH,
        repository=repo,
        label="D-113 preflight",
    )
    selected_candidate = _resolved(
        DEFAULT_CANDIDATE_PATH,
        repository=repo,
        label="D-113 candidate",
    )
    selected_gate = _resolved(gate_path, repository=repo, label="D-113 source gate")
    preflight_content = _read_stable(selected_preflight, label="D-113 preflight")
    candidate_content = _read_stable(selected_candidate, label="D-113 candidate")
    gate_content = _read_stable(selected_gate, label="D-113 source gate")
    preflight = _parse_json(preflight_content, label="D-113 preflight")
    candidate = _parse_json(candidate_content, label="D-113 candidate")
    gate = _parse_json(gate_content, label="D-113 source gate")
    _require(
        preflight_content == _pretty_json(preflight)
        and candidate_content == _pretty_json(candidate)
        and gate_content == _pretty_json(gate),
        "D-113 checked-in artifact is not canonical",
    )
    _exact_root_identity(
        preflight,
        schema_version=PREFLIGHT_SCHEMA_VERSION,
        id_field="preflight_id",
        id_prefix="d113preflight_",
        label="preflight",
    )
    _exact_root_identity(
        candidate,
        schema_version=CANDIDATE_SCHEMA_VERSION,
        id_field="candidate_id",
        id_prefix="d113validatorcandidate_",
        label="candidate",
    )
    _exact_root_identity(
        gate,
        schema_version=SOURCE_GATE_SCHEMA_VERSION,
        id_field="gate_id",
        id_prefix="d113_",
        label="source gate",
    )
    expected_preflight = build_d113_preflight(repository=repo, _context=context)
    expected_candidate = build_d113_authorization_candidate(
        expected_preflight,
        repository=repo,
        _context=context,
    )
    recorded_bindings = gate["semantic_body"].get("implementation_files")
    _require(
        isinstance(recorded_bindings, list)
        and len(recorded_bindings) == len(D113_IMPLEMENTATION_PATHS),
        "D-113 implementation bindings are invalid",
    )
    if verify_current_implementation:
        current_bindings = [
            _file_binding(path, repository=repo, label="D-113 implementation")
            for path in D113_IMPLEMENTATION_PATHS
        ]
        _require(
            recorded_bindings == current_bindings,
            "D-113 current implementation differs from source-gate binding",
        )
    expected_gate = build_d113_source_gate(
        expected_preflight,
        expected_candidate,
        repository=repo,
        _context=context,
        implementation_bindings=recorded_bindings,
    )
    _require(
        preflight == expected_preflight
        and candidate == expected_candidate
        and gate == expected_gate,
        "D-113 source-gate semantic content drifted",
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
        "current_implementation_verified": verify_current_implementation,
        "gap_ids": list(GAP_IDS),
        "validator_correction_candidate_ready": authority["validator_correction_candidate_ready"],
        "exact_candidate_user_approval_received": False,
        "validator_correction_authorized": False,
        "validator_correction_implemented": False,
        "score_policy_correction_authorized": False,
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
    "CANDIDATE_SCHEMA_VERSION",
    "DEFAULT_CANDIDATE_PATH",
    "DEFAULT_PREFLIGHT_PATH",
    "DEFAULT_SOURCE_GATE_PATH",
    "D113AuthorizationError",
    "GAP_IDS",
    "PREFLIGHT_SCHEMA_VERSION",
    "SOURCE_GATE_SCHEMA_VERSION",
    "build_d113_authorization_candidate",
    "build_d113_preflight",
    "build_d113_source_gate",
    "run_d113_offline_source_gate",
    "validate_d113_candidate_payload",
    "validate_d113_preflight_payload",
    "validate_d113_source_gate",
]
