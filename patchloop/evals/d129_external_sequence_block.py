"""Seal the non-retroactive D-129 external-sequence incident.

The user authorized a D-129 no-call environment preflight, but one public
OpenAI documentation lookup was performed before the required machine receipt
and durable phase intent existed.  This module does not attempt to repair that
ordering.  It can only record the exact approval in a non-retroactive receipt,
consume that receipt in a procedural blocked terminal, and validate the
append-only Git topology.  It has no Docker, network, SDK, provider, evaluator,
agent, retrieval, execution-hash, candidate, cost, or experiment entrypoint.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import patchloop.errors as errors_module
import patchloop.runtime as runtime_module
import patchloop.util as util_module
from patchloop.errors import ContractError
from patchloop.evals import d129_d128_terminal_successor_offline as d129
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-129"

RECEIPT_SCHEMA = "terminal-successor-external-sequence-approval-receipt-d129-v1"
RECEIPT_STATUS = "D129_EXTERNAL_NO_CALL_APPROVAL_RECORDED_AFTER_PRE_RECEIPT_ACTIVITY"
RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/d129-terminal-successor-external-no-call-approval-receipt.json"
)

TERMINAL_SCHEMA = "terminal-successor-external-sequence-blocked-d129-v1"
TERMINAL_STATUS = "D129_EXTERNAL_NO_CALL_SEQUENCE_OBSERVED_BLOCKED"
TERMINAL_BLOCKER = "durable-receipt-and-phase-attempt-did-not-precede-first-external-docs-lookup"
TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d129-external-no-call-sequence-observed-blocked.json"
)

D129_GATE_PATH = d129.OUTPUT_PATH
D129_GATE_ID = "d129_fa5412dd269ba6d4f502220fe1655d6f84b746eff6fa95633691464d6e29243c"
D129_GATE_BODY_SHA256 = "sha256:fa5412dd269ba6d4f502220fe1655d6f84b746eff6fa95633691464d6e29243c"
D129_GATE_FILE_SHA256 = "sha256:fd57c187d1f260952b581e60f7d0ff98243f3b4ef172c9a6d6669b3e84968512"
D129_GATE_FILE_BYTES = 18_678
D129_GATE_STATUS = "D129_D128_TERMINAL_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_APPROVAL_REQUIRED"
D129_GATE_BLOB_OID = "5ccf4a0e4ddaf7b4096186bc960035fdb76f337e"

D129_EVIDENCE_COMMIT = "70f9955dca8d873f91d622505f7afe7f3cfec59e"
D129_EVIDENCE_TREE = "ad9e348284c1161f258ef7e20ea7cc63cd55399d"
D129_EVIDENCE_PARENT = "1fef6716cddca571777c8b7f9f1dc4501f988d1c"

SOURCE_PATHS = (
    Path("patchloop/evals/d129_external_sequence_block.py"),
    Path("scripts/build_d129_external_sequence_block.py"),
    Path("tests/test_d129_external_sequence_block.py"),
)
DEPENDENCY_PATHS = (
    Path("patchloop/evals/d129_d128_terminal_successor_offline.py"),
    Path("patchloop/errors.py"),
    Path("patchloop/runtime.py"),
    Path("patchloop/util.py"),
)
SOURCE_BINDING_PATHS = SOURCE_PATHS + DEPENDENCY_PATHS
ACTIVE_DOC_PATHS = d129.ACTIVE_DOC_PATHS
PYTHON_ROUTING_ENV_NAMES = ("PYTHONHOME", "PYTHONPATH")
LOADED_MODULE_PATHS = (
    (SOURCE_PATHS[0], __name__),
    (DEPENDENCY_PATHS[0], d129.__name__),
    (DEPENDENCY_PATHS[1], errors_module.__name__),
    (DEPENDENCY_PATHS[2], runtime_module.__name__),
    (DEPENDENCY_PATHS[3], util_module.__name__),
)

OFFICIAL_DOCS_URL = "https://developers.openai.com/api/docs/pricing"

APPROVED_SCOPE = d129.FUTURE_APPROVED_SCOPE
NOT_AUTHORIZED = d129.FUTURE_NOT_AUTHORIZED

FORBIDDEN_DESCENDANT_PATHS = (
    Path(
        "reports/live-pilot/artifacts/d129-docker-image-readiness-remediation-attempt-intent.json"
    ),
    Path(
        "reports/live-pilot/artifacts/d129-exact-docker-image-readiness-remediation-observation.json"
    ),
    Path("reports/live-pilot/artifacts/d129-official-pricing-capture-attempt-intent.json"),
    Path("reports/live-pilot/artifacts/d129-replayable-official-pricing-evidence.json"),
    Path("reports/live-pilot/artifacts/d129-read-only-preflight-attempt-intent.json"),
    Path("reports/live-pilot/artifacts/d129-repeated-no-call-readiness-preflight.json"),
    Path(
        "reports/live-pilot/artifacts/d129-terminal-successor-external-no-call-preflight-gate.json"
    ),
)

ROOT_KEYS = ("schema_version", "artifact_id", "semantic_body_hash", "semantic_body")
RECEIPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "predecessor_binding",
    "source_identity",
    "approval_binding",
    "event_order",
    "pre_receipt_activity",
    "evidence_boundary",
    "authority",
    "next_gate",
)
TERMINAL_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "predecessor_binding",
    "source_identity",
    "receipt_binding",
    "receipt_commit_binding",
    "sequence_block",
    "activity_accounting",
    "evidence_boundary",
    "authority",
    "next_gate",
)
RECEIPT_COMMIT_KEYS = (
    "commit",
    "tree",
    "parents",
    "receipt_path",
    "receipt_blob_oid",
    "receipt_file_sha256",
    "receipt_file_bytes",
    "receipt_only_add_commit",
)


class D129ExternalSequenceBlockError(ContractError):
    """Raised when the D-129 incident evidence is not exact."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D129ExternalSequenceBlockError(message)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any, *, label: str) -> datetime:
    try:
        return d129._parse_time(value, label=label)
    except ContractError as exc:
        raise D129ExternalSequenceBlockError(str(exc)) from exc


def _repo_root(repository: str | Path | None) -> Path:
    try:
        return d129._repo_root(repository)
    except ContractError as exc:
        raise D129ExternalSequenceBlockError(str(exc)) from exc


def _pretty_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=True, indent=2) + "\n").encode("utf-8")


def _envelope(schema: str, prefix: str, body: dict[str, Any]) -> dict[str, Any]:
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": schema,
        "artifact_id": f"{prefix}_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _read_json(root: Path, relative: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = d129._stable_read(root, relative)
    except ContractError as exc:
        raise D129ExternalSequenceBlockError(str(exc)) from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D129ExternalSequenceBlockError(
            f"D-129 {relative.name} is not canonical JSON"
        ) from exc
    _require(isinstance(payload, dict), f"D-129 {relative.name} root differs")
    return payload, raw


def _path_absent(root: Path, relative: Path) -> None:
    _require(not d129._lexists(root / relative), f"D-129 unexpected artifact exists: {relative}")


def _write_new(root: Path, relative: Path, raw: bytes) -> None:
    try:
        selected = d129._logical_path(root, relative, must_exist=False)
    except ContractError as exc:
        raise D129ExternalSequenceBlockError(str(exc)) from exc
    _require(not d129._lexists(selected), f"D-129 {relative.name} already exists")
    temporary = selected.with_name(f".{selected.name}.d129-incident-{uuid.uuid4().hex}.tmp")
    _require(not d129._lexists(temporary), "D-129 temporary output collision")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        _require(temporary.read_bytes() == raw, "D-129 temporary output differs")
        try:
            os.link(temporary, selected)
        except FileExistsError as exc:
            raise D129ExternalSequenceBlockError(f"D-129 {relative.name} collision") from exc
        _require(d129._stable_read(root, relative) == raw, "D-129 persisted output differs")
    finally:
        with suppress(OSError):
            temporary.unlink()


def _commit_identity(root: Path, commit: str) -> dict[str, Any]:
    try:
        return d129._commit_identity(root, commit)
    except ContractError as exc:
        raise D129ExternalSequenceBlockError(str(exc)) from exc


def _diff_rows(root: Path, commit: str) -> list[dict[str, str]]:
    try:
        return d129._diff_rows(root, commit)
    except ContractError as exc:
        raise D129ExternalSequenceBlockError(str(exc)) from exc


def _commit_blob(root: Path, commit: str, path: Path) -> tuple[str, bytes]:
    try:
        return d129._commit_blob(root, commit, path)
    except ContractError as exc:
        raise D129ExternalSequenceBlockError(str(exc)) from exc


def _status_lines(root: Path) -> list[str]:
    try:
        return d129._status_lines(root)
    except ContractError as exc:
        raise D129ExternalSequenceBlockError(str(exc)) from exc


def _head(root: Path) -> str:
    try:
        value = d129._git_command(root, "rev-parse", "HEAD")
    except ContractError as exc:
        raise D129ExternalSequenceBlockError(str(exc)) from exc
    _require(isinstance(value, str), "D-129 HEAD differs")
    return value


def _gate_binding(root: Path) -> dict[str, Any]:
    identity = _commit_identity(root, D129_EVIDENCE_COMMIT)
    _require(
        identity["tree"] == D129_EVIDENCE_TREE and identity["parents"] == [D129_EVIDENCE_PARENT],
        "D-129 evidence topology differs",
    )
    expected_diff = [
        {"status": "A", "path": D129_GATE_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
    ]
    _require(
        sorted(_diff_rows(root, D129_EVIDENCE_COMMIT), key=lambda row: row["path"])
        == sorted(expected_diff, key=lambda row: row["path"]),
        "D-129 evidence commit scope differs",
    )
    raw = d129._stable_read(root, D129_GATE_PATH)
    _require(len(raw) == D129_GATE_FILE_BYTES, "D-129 gate bytes differ")
    _require(sha256_bytes(raw) == D129_GATE_FILE_SHA256, "D-129 gate file SHA differs")
    oid, committed = _commit_blob(root, D129_EVIDENCE_COMMIT, D129_GATE_PATH)
    _require(oid == D129_GATE_BLOB_OID and committed == raw, "D-129 gate blob differs")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D129ExternalSequenceBlockError("D-129 gate JSON differs") from exc
    _require(
        isinstance(payload, dict) and tuple(payload) == d129.ROOT_KEYS, "D-129 gate root differs"
    )
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-129 gate body differs")
    _require(
        payload.get("gate_id") == D129_GATE_ID
        and payload.get("semantic_body_hash") == D129_GATE_BODY_SHA256
        and sha256_text(canonical_json(body)) == D129_GATE_BODY_SHA256
        and body.get("status") == D129_GATE_STATUS
        and d129._pretty_bytes(payload) == raw,
        "D-129 gate tuple differs",
    )
    return {
        "path": D129_GATE_PATH.as_posix(),
        "gate_id": D129_GATE_ID,
        "semantic_body_hash": D129_GATE_BODY_SHA256,
        "file_sha256": D129_GATE_FILE_SHA256,
        "file_bytes": D129_GATE_FILE_BYTES,
        "status": D129_GATE_STATUS,
        "recorded_at": body["recorded_at"],
        "evidence_commit": D129_EVIDENCE_COMMIT,
        "evidence_tree": D129_EVIDENCE_TREE,
        "evidence_parent": D129_EVIDENCE_PARENT,
        "blob_oid": D129_GATE_BLOB_OID,
        "artifact_mutated": False,
    }


def _binding_for_path(root: Path, commit: str, path: Path) -> dict[str, Any]:
    oid, committed = _commit_blob(root, commit, path)
    current = d129._stable_read(root, path)
    _require(current == committed, f"D-129 source drift: {path}")
    return {
        "path": path.as_posix(),
        "file_bytes": len(committed),
        "file_sha256": sha256_bytes(committed),
        "blob_oid": oid,
        "current_bytes_match_commit": True,
    }


def _python_routing_env_presence() -> dict[str, bool]:
    presence = {name: name in os.environ for name in PYTHON_ROUTING_ENV_NAMES}
    _require(not any(presence.values()), "D-129 Python import routing environment is present")
    return presence


def _assert_runtime_import_boundary(root: Path) -> None:
    _python_routing_env_presence()
    for relative, module_name in LOADED_MODULE_PATHS:
        module = sys.modules.get(module_name)
        loaded_value = getattr(module, "__file__", None)
        _require(isinstance(loaded_value, str), f"D-129 loaded module path differs: {relative}")
        try:
            loaded = Path(loaded_value).resolve(strict=True)
            expected = (root / relative).resolve(strict=True)
        except OSError as exc:
            raise D129ExternalSequenceBlockError(
                f"D-129 loaded module path differs: {relative}"
            ) from exc
        _require(loaded == expected, f"D-129 loaded module is outside repository: {relative}")


def _loaded_module_bindings(root: Path, commit: str) -> list[dict[str, Any]]:
    _assert_runtime_import_boundary(root)
    bindings: list[dict[str, Any]] = []
    for relative, module_name in LOADED_MODULE_PATHS:
        module = sys.modules.get(module_name)
        loaded_value = getattr(module, "__file__", None)
        _require(isinstance(loaded_value, str), f"D-129 loaded module path differs: {relative}")
        try:
            loaded = Path(loaded_value).resolve(strict=True)
            expected = (root / relative).resolve(strict=True)
        except OSError as exc:
            raise D129ExternalSequenceBlockError(
                f"D-129 loaded module path differs: {relative}"
            ) from exc
        _require(loaded == expected, f"D-129 loaded module is outside repository: {relative}")
        file_binding = _binding_for_path(root, commit, relative)
        bindings.append(
            {
                **file_binding,
                "module_name": module_name,
                "loaded_path": relative.as_posix(),
                "loaded_path_matches_repository": True,
            }
        )
    return bindings


def _source_identity_for_receipt(root: Path) -> dict[str, Any]:
    _assert_runtime_import_boundary(root)
    _require(_status_lines(root) == [], "D-129 receipt requires clean source")
    head = _head(root)
    identity = _commit_identity(root, head)
    _require(identity["parents"] == [D129_EVIDENCE_COMMIT], "D-129 source parent differs")
    expected = [{"status": "A", "path": path.as_posix()} for path in SOURCE_PATHS]
    _require(
        sorted(_diff_rows(root, head), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-129 incident source commit scope differs",
    )
    bindings = [_binding_for_path(root, head, path) for path in SOURCE_BINDING_PATHS]
    python_routing = _python_routing_env_presence()
    loaded_modules = _loaded_module_bindings(root, head)
    return {
        "commit": head,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "source_paths_added": [path.as_posix() for path in SOURCE_PATHS],
        "module_bindings": bindings,
        "loaded_module_bindings": loaded_modules,
        "python_routing_env_presence": python_routing,
        "worktree_and_index_clean_before_receipt": True,
        "git_cli_observation": d129._git_cli_observation(root),
        "git_identity_vendor_authenticated_or_signed": False,
    }


def _validate_source_identity(root: Path, source: Any) -> None:
    _assert_runtime_import_boundary(root)
    _require(isinstance(source, dict), "D-129 source identity differs")
    _require(
        set(source)
        == {
            "commit",
            "tree",
            "parents",
            "source_paths_added",
            "module_bindings",
            "loaded_module_bindings",
            "python_routing_env_presence",
            "worktree_and_index_clean_before_receipt",
            "git_cli_observation",
            "git_identity_vendor_authenticated_or_signed",
        },
        "D-129 source identity fields differ",
    )
    identity = _commit_identity(root, source["commit"])
    _require(
        identity["tree"] == source["tree"]
        and identity["parents"] == [D129_EVIDENCE_COMMIT]
        and source["parents"] == [D129_EVIDENCE_COMMIT],
        "D-129 source topology differs",
    )
    expected_diff = [{"status": "A", "path": path.as_posix()} for path in SOURCE_PATHS]
    _require(
        sorted(_diff_rows(root, source["commit"]), key=lambda row: row["path"])
        == sorted(expected_diff, key=lambda row: row["path"]),
        "D-129 source scope differs",
    )
    _require(
        source["source_paths_added"] == [path.as_posix() for path in SOURCE_PATHS]
        and source["worktree_and_index_clean_before_receipt"] is True
        and source["git_identity_vendor_authenticated_or_signed"] is False,
        "D-129 source claims differ",
    )
    expected_bindings = [
        _binding_for_path(root, source["commit"], path) for path in SOURCE_BINDING_PATHS
    ]
    _require(
        canonical_json(source["module_bindings"]) == canonical_json(expected_bindings),
        "D-129 source bindings differ",
    )
    _require(
        source["python_routing_env_presence"] == _python_routing_env_presence(),
        "D-129 Python routing observation differs",
    )
    _require(
        canonical_json(source["loaded_module_bindings"])
        == canonical_json(_loaded_module_bindings(root, source["commit"])),
        "D-129 loaded module bindings differ",
    )
    d129._validate_git_observation(source["git_cli_observation"])


def _receipt_event_order() -> list[dict[str, Any]]:
    return [
        {"ordinal": 1, "event": "exact-user-approval-received"},
        {"ordinal": 2, "event": "official-docs-tool-open-observed"},
        {"ordinal": 3, "event": "corrective-source-committed"},
        {"ordinal": 4, "event": "approval-receipt-recorded"},
    ]


def _pre_receipt_activity() -> dict[str, Any]:
    return {
        "activity_kind": "public-official-documentation-tool-open",
        "official_url": OFFICIAL_DOCS_URL,
        "agent_visible_web_tool_open_invocation_count": 1,
        "underlying_http_request_or_redirect_count": "unknown",
        "agent_supplied_openai_api_key_or_explicit_authentication": False,
        "agent_supplied_cookie": False,
        "underlying_tool_cookie_service_auth_or_header_state": "unknown",
        "provider_response_api_call_count": 0,
        "canonical_pricing_capture_get_count": 0,
        "canonical_pricing_evidence_artifact_created": False,
        "canonical_replayable_entity_retained": False,
        "canonical_retained_entity_bytes": 0,
        "canonical_retained_entity_sha256": None,
        "web_tool_returned_content_bytes": "unknown",
        "used_as_pricing_evidence": False,
        "exact_lookup_timestamp_retained": False,
    }


def _zero_authority() -> dict[str, Any]:
    return {
        "d129_receipt_created": True,
        "d129_external_phase_attempt_created": False,
        "d129_agent_docker_cli_call_count": 0,
        "d129_agent_docker_daemon_call_count": 0,
        "d129_agent_docker_desktop_or_daemon_start_count": 0,
        "d129_image_pull_or_load_count": 0,
        "d129_image_store_mutation_count": 0,
        "d129_container_create_start_run_exec_count": 0,
        "d129_canonical_pricing_capture_get_count": 0,
        "d129_sdk_probe_count": 0,
        "d129_sdk_transport_attempt_count": 0,
        "d129_credential_presence_observed": False,
        "d129_provider_call_count": 0,
        "d129_evaluator_call_count": 0,
        "d129_agent_run_count": 0,
        "d129_retrieval_call_count": 0,
        "d129_runtime_memory_injection_count": 0,
        "d129_execution_hash_created": False,
        "d129_execution_candidate_created": False,
        "d129_cost_reserved_or_spent_usd": "0",
        "d129_four_row_ac_execution_authorized": False,
    }


def _receipt_body(
    *, recorded_at: str, predecessor: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "non-retroactive-terminal-successor-external-no-call-approval-receipt",
        "recorded_at": recorded_at,
        "status": RECEIPT_STATUS,
        "predecessor_binding": predecessor,
        "source_identity": source,
        "approval_binding": {
            "approval_mode": "current-user-message-self-attested-unsigned",
            "approval_is_authenticated_or_cryptographically_signed": False,
            "approved_scope": list(APPROVED_SCOPE),
            "not_authorized": list(NOT_AUTHORIZED),
            "approval_preceded_official_docs_lookup": True,
            "receipt_preceded_official_docs_lookup": False,
            "phase_attempt_preceded_official_docs_lookup": False,
            "receipt_created_before_any_docker_canonical_pricing_capture_or_sdk_probe": True,
            "receipt_does_not_repair_or_retroactively_authorize_sequence": True,
        },
        "event_order": _receipt_event_order(),
        "pre_receipt_activity": _pre_receipt_activity(),
        "evidence_boundary": {
            "ordinal_order_used_without_inventing_lookup_timestamp": True,
            "official_docs_lookup_was_within_user_scope": True,
            "official_docs_lookup_violated_machine_receipt_and_attempt_order": True,
            "official_docs_lookup_is_not_canonical_pricing_evidence": True,
            "receipt_reads_dotenv_or_credential_value": False,
            "no_external_action_performed_by_receipt_writer": True,
        },
        "authority": _zero_authority(),
        "next_gate": {
            "action": "record-d129-external-no-call-sequence-observed-blocked",
            "no_docker_pricing_sdk_or_other_external_phase_may_follow_this_receipt": True,
            "does_not_authorize_retry_resume_repair_or_execution": True,
        },
    }


def _validate_receipt_payload(root: Path, payload: Any, raw: bytes) -> dict[str, Any]:
    _require(
        isinstance(payload, dict) and tuple(payload) == ROOT_KEYS, "D-129 receipt root differs"
    )
    _require(payload["schema_version"] == RECEIPT_SCHEMA, "D-129 receipt schema differs")
    body = payload["semantic_body"]
    _require(
        isinstance(body, dict) and tuple(body) == RECEIPT_BODY_KEYS,
        "D-129 receipt body fields differ",
    )
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload["semantic_body_hash"] == body_hash
        and payload["artifact_id"] == f"d129approval_{body_hash.removeprefix('sha256:')}"
        and _pretty_bytes(payload) == raw,
        "D-129 receipt envelope differs",
    )
    _require(
        body["milestone"] == MILESTONE and body["status"] == RECEIPT_STATUS,
        "D-129 receipt status differs",
    )
    predecessor = _gate_binding(root)
    _require(
        canonical_json(body["predecessor_binding"]) == canonical_json(predecessor),
        "D-129 receipt predecessor differs",
    )
    _validate_source_identity(root, body["source_identity"])
    expected = _envelope(
        RECEIPT_SCHEMA,
        "d129approval",
        _receipt_body(
            recorded_at=body["recorded_at"],
            predecessor=predecessor,
            source=body["source_identity"],
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected), "D-129 receipt full rebuild differs"
    )
    _require(
        _parse_time(body["recorded_at"], label="receipt recorded_at")
        > _parse_time(predecessor["recorded_at"], label="gate recorded_at"),
        "D-129 receipt chronology differs",
    )
    return payload


def _receipt_result(payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "status": RECEIPT_STATUS,
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "source_commit": payload["semantic_body"]["source_identity"]["commit"],
        "pre_receipt_official_docs_web_tool_open_invocation_count": 1,
        "canonical_pricing_capture_get_count": 0,
        "external_phase_attempt_created": False,
    }


def create_d129_approval_receipt(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Create the exact non-retroactive approval receipt; perform no external action."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    if d129._lexists(root / RECEIPT_PATH):
        payload, raw = _read_json(root, RECEIPT_PATH)
        return _receipt_result(_validate_receipt_payload(root, payload, raw), raw)
    _path_absent(root, TERMINAL_PATH)
    for path in FORBIDDEN_DESCENDANT_PATHS:
        _path_absent(root, path)
    predecessor = _gate_binding(root)
    source = _source_identity_for_receipt(root)
    recorded_at = _now()
    _require(
        _parse_time(recorded_at, label="receipt recorded_at")
        > _parse_time(predecessor["recorded_at"], label="gate recorded_at"),
        "D-129 receipt chronology differs before publication",
    )
    payload = _envelope(
        RECEIPT_SCHEMA,
        "d129approval",
        _receipt_body(recorded_at=recorded_at, predecessor=predecessor, source=source),
    )
    raw = _pretty_bytes(payload)
    _validate_receipt_payload(root, payload, raw)
    _write_new(root, RECEIPT_PATH, raw)
    stored, stored_raw = _read_json(root, RECEIPT_PATH)
    return _receipt_result(_validate_receipt_payload(root, stored, stored_raw), stored_raw)


def _receipt_binding(payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "path": RECEIPT_PATH.as_posix(),
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": RECEIPT_STATUS,
        "recorded_at": payload["semantic_body"]["recorded_at"],
        "receipt_is_non_retroactive": True,
        "artifact_mutated": False,
    }


def _rebuild_receipt_commit_binding(
    root: Path,
    *,
    commit: str,
    source: dict[str, Any],
    receipt_raw: bytes,
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [source["commit"]], "D-129 receipt commit parent differs")
    _require(
        _diff_rows(root, commit) == [{"status": "A", "path": RECEIPT_PATH.as_posix()}],
        "D-129 receipt commit is not receipt-only",
    )
    oid, committed = _commit_blob(root, commit, RECEIPT_PATH)
    _require(committed == receipt_raw, "D-129 receipt commit blob differs")
    for binding in source["module_bindings"]:
        path = Path(binding["path"])
        source_oid, source_raw = _commit_blob(root, source["commit"], path)
        receipt_oid, receipt_source_raw = _commit_blob(root, commit, path)
        _require(
            source_oid == receipt_oid and source_raw == receipt_source_raw,
            "D-129 receipt commit changed source",
        )
    return {
        "commit": commit,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "receipt_path": RECEIPT_PATH.as_posix(),
        "receipt_blob_oid": oid,
        "receipt_file_sha256": sha256_bytes(committed),
        "receipt_file_bytes": len(committed),
        "receipt_only_add_commit": True,
    }


def _receipt_commit_binding(
    root: Path, source: dict[str, Any], receipt_raw: bytes
) -> dict[str, Any]:
    _require(_status_lines(root) == [], "D-129 terminal requires clean receipt commit")
    return _rebuild_receipt_commit_binding(
        root,
        commit=_head(root),
        source=source,
        receipt_raw=receipt_raw,
    )


def _terminal_authority() -> dict[str, Any]:
    value = _zero_authority()
    value.update(
        {
            "d129_receipt_consumed": True,
            "d129_retry_resume_or_repair_authorized": False,
            "d129_environment_ready": False,
        }
    )
    return value


def _terminal_body(
    *,
    recorded_at: str,
    predecessor: dict[str, Any],
    source: dict[str, Any],
    receipt: dict[str, Any],
    receipt_commit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "append-only-pre-receipt-external-sequence-incident-terminal",
        "recorded_at": recorded_at,
        "status": TERMINAL_STATUS,
        "predecessor_binding": predecessor,
        "source_identity": source,
        "receipt_binding": receipt,
        "receipt_commit_binding": receipt_commit,
        "sequence_block": {
            "observed_blockers": [TERMINAL_BLOCKER],
            "passed": False,
            "event_order": [
                *_receipt_event_order(),
                {"ordinal": 5, "event": "procedural-block-terminal-recorded"},
            ],
            "approval_preceded_lookup": True,
            "receipt_preceded_lookup": False,
            "phase_attempt_preceded_lookup": False,
            "all_external_activity_was_attempt_first": False,
            "attempt_artifact_created": False,
            "no_attempt_retroactively_created": True,
            "terminal_without_attempt_is_deliberate_incident_record": True,
            "receipt_does_not_repair_sequence": True,
        },
        "activity_accounting": {
            "pre_receipt_official_docs_activity": _pre_receipt_activity(),
            "post_receipt_docker_cli_or_daemon_call_count": 0,
            "post_receipt_image_pull_or_load_count": 0,
            "post_receipt_canonical_pricing_capture_get_count": 0,
            "post_receipt_sdk_probe_count": 0,
            "post_receipt_provider_evaluator_or_agent_call_count": 0,
            "canonical_pricing_capture_attempted": False,
            "canonical_pricing_artifact_created": False,
        },
        "evidence_boundary": {
            "lookup_was_approved_but_machine_order_was_not_satisfied": True,
            "underlying_http_request_or_redirect_count_is_unknown": True,
            "canonical_raw_response_body_etag_hash_or_bytes_retained_in_project": False,
            "web_tool_returned_content_retention_state": "unknown",
            "lookup_is_not_used_as_replayable_pricing_evidence": True,
            "no_dotenv_or_credential_value_read_by_recorder": True,
            "no_docker_network_sdk_or_provider_entrypoint_exposed": True,
        },
        "authority": _terminal_authority(),
        "next_gate": {
            "action": "prepare-separate-d130-offline-successor-gate",
            "requires_new_exact_user_approval_after-d130": True,
            "this_d129_receipt_is_consumed": True,
            "does_not_authorize_external_retry_resume_repair_or_execution": True,
        },
    }


def _validate_terminal_payload(root: Path, payload: Any, raw: bytes) -> dict[str, Any]:
    _require(
        isinstance(payload, dict) and tuple(payload) == ROOT_KEYS, "D-129 terminal root differs"
    )
    _require(payload["schema_version"] == TERMINAL_SCHEMA, "D-129 terminal schema differs")
    body = payload["semantic_body"]
    _require(
        isinstance(body, dict) and tuple(body) == TERMINAL_BODY_KEYS,
        "D-129 terminal body fields differ",
    )
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload["semantic_body_hash"] == body_hash
        and payload["artifact_id"] == f"d129sequenceblock_{body_hash.removeprefix('sha256:')}"
        and _pretty_bytes(payload) == raw,
        "D-129 terminal envelope differs",
    )
    _require(
        body["milestone"] == MILESTONE and body["status"] == TERMINAL_STATUS,
        "D-129 terminal status differs",
    )
    predecessor = _gate_binding(root)
    receipt_payload, receipt_raw = _read_json(root, RECEIPT_PATH)
    _validate_receipt_payload(root, receipt_payload, receipt_raw)
    source = receipt_payload["semantic_body"]["source_identity"]
    _validate_source_identity(root, source)
    receipt = _receipt_binding(receipt_payload, receipt_raw)
    receipt_commit = body["receipt_commit_binding"]
    _require(
        isinstance(receipt_commit, dict) and tuple(receipt_commit) == RECEIPT_COMMIT_KEYS,
        "D-129 receipt commit binding fields differ",
    )
    _require(
        isinstance(receipt_commit["commit"], str)
        and len(receipt_commit["commit"]) == 40
        and receipt_commit["receipt_path"] == RECEIPT_PATH.as_posix()
        and receipt_commit["receipt_only_add_commit"] is True,
        "D-129 receipt commit binding differs",
    )
    rebuilt_receipt_commit = _rebuild_receipt_commit_binding(
        root,
        commit=receipt_commit["commit"],
        source=source,
        receipt_raw=receipt_raw,
    )
    _require(
        canonical_json(receipt_commit) == canonical_json(rebuilt_receipt_commit),
        "D-129 receipt commit full rebuild differs",
    )
    expected = _envelope(
        TERMINAL_SCHEMA,
        "d129sequenceblock",
        _terminal_body(
            recorded_at=body["recorded_at"],
            predecessor=predecessor,
            source=source,
            receipt=receipt,
            receipt_commit=receipt_commit,
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected), "D-129 terminal full rebuild differs"
    )
    _require(
        _parse_time(body["recorded_at"], label="terminal recorded_at")
        > _parse_time(receipt["recorded_at"], label="receipt recorded_at"),
        "D-129 terminal chronology differs",
    )
    for path in FORBIDDEN_DESCENDANT_PATHS:
        _path_absent(root, path)
    return payload


def _terminal_result(
    payload: dict[str, Any], raw: bytes, *, evidence_commit: str | None = None
) -> dict[str, Any]:
    return {
        "status": TERMINAL_STATUS,
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "receipt_artifact_id": payload["semantic_body"]["receipt_binding"]["artifact_id"],
        "receipt_consumed": True,
        "pre_receipt_official_docs_web_tool_open_invocation_count": 1,
        "canonical_pricing_capture_get_count": 0,
        "docker_cli_call_count": 0,
        "sdk_probe_count": 0,
        "execution_hash_created": False,
        "execution_candidate_created": False,
        "evidence_commit": evidence_commit,
    }


def record_d129_sequence_block_terminal(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Consume the D-129 receipt in a procedural terminal; perform no external action."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    if d129._lexists(root / TERMINAL_PATH):
        payload, raw = _read_json(root, TERMINAL_PATH)
        return _terminal_result(_validate_terminal_payload(root, payload, raw), raw)
    for path in FORBIDDEN_DESCENDANT_PATHS:
        _path_absent(root, path)
    receipt_payload, receipt_raw = _read_json(root, RECEIPT_PATH)
    _validate_receipt_payload(root, receipt_payload, receipt_raw)
    source = receipt_payload["semantic_body"]["source_identity"]
    receipt_commit = _receipt_commit_binding(root, source, receipt_raw)
    predecessor = _gate_binding(root)
    receipt = _receipt_binding(receipt_payload, receipt_raw)
    recorded_at = _now()
    _require(
        _parse_time(recorded_at, label="terminal recorded_at")
        > _parse_time(receipt["recorded_at"], label="receipt recorded_at"),
        "D-129 terminal chronology differs before publication",
    )
    payload = _envelope(
        TERMINAL_SCHEMA,
        "d129sequenceblock",
        _terminal_body(
            recorded_at=recorded_at,
            predecessor=predecessor,
            source=source,
            receipt=receipt,
            receipt_commit=receipt_commit,
        ),
    )
    raw = _pretty_bytes(payload)
    _validate_terminal_payload(root, payload, raw)
    _write_new(root, TERMINAL_PATH, raw)
    stored, stored_raw = _read_json(root, TERMINAL_PATH)
    return _terminal_result(_validate_terminal_payload(root, stored, stored_raw), stored_raw)


def _validate_post_evidence_checkout(
    root: Path, terminal: dict[str, Any], terminal_raw: bytes
) -> str:
    _require(_status_lines(root) == [], "D-129 post-evidence checkout is not clean")
    head = _head(root)
    receipt_commit = terminal["semantic_body"]["receipt_commit_binding"]["commit"]
    identity = _commit_identity(root, head)
    _require(identity["parents"] == [receipt_commit], "D-129 evidence commit parent differs")
    expected = [
        {"status": "A", "path": TERMINAL_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
    ]
    _require(
        sorted(_diff_rows(root, head), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-129 evidence commit scope differs",
    )
    oid, committed = _commit_blob(root, head, TERMINAL_PATH)
    _require(committed == terminal_raw and bool(oid), "D-129 terminal commit bytes differ")
    return head


def validate_d129_sequence_block(
    *,
    repository: str | Path | None = None,
    mode: Literal["receipt", "terminal", "post-evidence"] = "terminal",
) -> dict[str, Any]:
    """Validate the receipt, terminal, or exact post-evidence topology without external calls."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    if mode == "receipt":
        payload, raw = _read_json(root, RECEIPT_PATH)
        return _receipt_result(_validate_receipt_payload(root, payload, raw), raw)
    _require(mode in {"terminal", "post-evidence"}, "D-129 validation mode differs")
    payload, raw = _read_json(root, TERMINAL_PATH)
    validated = _validate_terminal_payload(root, payload, raw)
    evidence_commit = (
        _validate_post_evidence_checkout(root, validated, raw) if mode == "post-evidence" else None
    )
    return _terminal_result(validated, raw, evidence_commit=evidence_commit)


__all__ = [
    "D129ExternalSequenceBlockError",
    "RECEIPT_PATH",
    "RECEIPT_SCHEMA",
    "RECEIPT_STATUS",
    "TERMINAL_PATH",
    "TERMINAL_SCHEMA",
    "TERMINAL_STATUS",
    "create_d129_approval_receipt",
    "record_d129_sequence_block_terminal",
    "validate_d129_sequence_block",
]
