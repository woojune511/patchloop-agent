"""Offline qualification and future D-136 fixed-pricing successor workflow.

The D-135 procedural terminal is immutable.  This module qualifies a new
capture implementation and distinct append-only D-136 artifacts; it never
imports or invokes the consumed D-132 runner.
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

from patchloop.errors import ContractError
from patchloop.evals import d135_d134_ambiguous_gate_correction_offline as d135
from patchloop.evals import d136_fixed_pricing_capture as pricing_capture
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-136"
GATE_SCHEMA = "d135-fixed-pricing-successor-offline-source-gate-d136-v1"
GATE_STATUS = "D136_D135_FIXED_PRICING_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_FRESH_ACTIVATION_REQUIRED"
GATE_PATH = Path(
    "reports/live-pilot/artifacts/d136-d135-fixed-pricing-successor-offline-source-gate.json"
)

RECEIPT_SCHEMA = "d136-fixed-pricing-successor-activation-receipt-v1"
RECEIPT_STATUS = "D136_FIXED_PRICING_SUCCESSOR_ACTIVATION_RECEIPT_RECORDED_COMMIT_REQUIRED"
RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/d136-fixed-pricing-successor-activation-receipt.json"
)
ATTEMPT_SCHEMA = "d136-fixed-pricing-capture-attempt-intent-v1"
ATTEMPT_STATUS = "D136_FIXED_PRICING_CAPTURE_ATTEMPT_RECORDED_COMMIT_REQUIRED"
ATTEMPT_PATH = Path("reports/live-pilot/artifacts/d136-fixed-pricing-capture-attempt-intent.json")
STARTED_SCHEMA = "d136-fixed-pricing-capture-action-started-v1"
STARTED_STATUS = "D136_FIXED_PRICING_CAPTURE_ACTION_STARTED_RECORDED_TRANSITION_COMMIT_REQUIRED"
STARTED_PATH = Path("reports/live-pilot/artifacts/d136-fixed-pricing-capture-action-started.json")
TERMINAL_SCHEMA = "d136-fixed-pricing-successor-terminal-v1"
TERMINAL_STATUS = "D136_FIXED_PRICING_SUCCESSOR_CAPTURED_TRANSITION_COMMIT_REQUIRED"
TERMINAL_PATH = Path("reports/live-pilot/artifacts/d136-replayable-official-pricing-evidence.json")
D135_TERMINAL_PATH = d135.TERMINAL_PATH
D135_TERMINAL_ID = (
    "d135pricingincident_7684c346db32bac34404137a0839c852ce00209ded9d0f9aa444a0a73d519f75"
)
D135_TERMINAL_BODY_SHA256 = (
    "sha256:7684c346db32bac34404137a0839c852ce00209ded9d0f9aa444a0a73d519f75"
)
D135_TERMINAL_FILE_SHA256 = (
    "sha256:ac0f8a6a8d3282f14d3d6b5ab8176e0fe4f64a8bb509e4cd1380ca6a76b2438a"
)
D135_TERMINAL_FILE_BYTES = 22_084
D135_TERMINAL_BLOB_OID = "8efce4a2508cddd32b59d9be92f3eb65517b1552"
D135_TERMINAL_COMMIT = "98f4560e718145bc7465732c1a3d2f5a4ea8d786"
D135_TERMINAL_TREE = "901c123f425733ee77e5c8db926ffa4f98edd431"
D135_TERMINAL_PARENT = "e0a26f0134b811fca2cd76d3d8a69ec2a484cabb"

IMPLEMENTATION_PATHS = (
    Path("patchloop/evals/d136_fixed_pricing_capture.py"),
    Path("patchloop/evals/d136_d135_fixed_pricing_successor_offline.py"),
    Path("scripts/build_d136_d135_fixed_pricing_successor_offline.py"),
    Path("tests/test_d136_d135_fixed_pricing_successor_offline.py"),
)
ACTIVE_DOC_PATHS = d135.ACTIVE_DOC_PATHS
FUTURE_PATHS = (RECEIPT_PATH, ATTEMPT_PATH, STARTED_PATH, TERMINAL_PATH)
PYTHON_ROUTING_ENV_NAMES = d135.PYTHON_ROUTING_ENV_NAMES
LOADED_MODULE_PATHS = tuple(
    dict.fromkeys(
        (
            (IMPLEMENTATION_PATHS[1], __name__),
            (IMPLEMENTATION_PATHS[0], pricing_capture.__name__),
            *d135.LOADED_MODULE_PATHS,
        )
    )
)
DEPENDENCY_PATHS = tuple(
    dict.fromkeys(
        (
            *(path for path, _name in LOADED_MODULE_PATHS),
            Path("pyproject.toml"),
            Path("uv.lock"),
        )
    )
)
SOURCE_BINDING_PATHS = tuple(dict.fromkeys((*IMPLEMENTATION_PATHS, *DEPENDENCY_PATHS)))

ROOT_KEYS = ("schema_version", "artifact_id", "semantic_body_hash", "semantic_body")
GATE_ROOT_KEYS = ("schema_version", "gate_id", "semantic_body_hash", "semantic_body")
GATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "predecessor_terminal",
    "source_identity",
    "source_preparation_approval",
    "fixed_pricing_helper_contract",
    "future_activation_contract",
    "offline_qualification",
    "evidence_boundary",
    "authority",
    "next_gate",
)
RECEIPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "source_gate_binding",
    "source_identity",
    "activation_approval",
    "future_activation_contract",
    "authority",
)
ATTEMPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "activation_receipt_binding",
    "parent_commit_binding",
    "capture_contract",
    "authority",
)
STARTED_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "pricing_attempt_binding",
    "parent_commit_binding",
    "capture_contract",
    "authority",
)
TERMINAL_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "action_started_binding",
    "parent_commit_binding",
    "observation",
    "activity_accounting",
    "evidence_boundary",
    "authority",
    "next_gate",
)
SOURCE_PREPARATION_SCOPE = (
    "bind-exact-d135-procedural-terminal-bytes-commit-and-predecessor-gate-topology",
    "implement-new-only-d136-fixed-pricing-capture-helper",
    "close-every-client-send-response-explicitly-in-finally-without-context-manager-reliance",
    "preserve-exact-official-url-unauthenticated-request-redirect-size-and-replay-bounds",
    "implement-new-only-future-receipt-attempt-action-started-terminal-writers-validators-orchestrator-cli",
    "enforce-append-only-new-only-collision-orphan-idempotence-and-loaded-module-provenance",
    "run-only-fully-mocked-no-enter-close-success-redirect-and-error-focused-tests",
    "create-exact-four-path-source-only-commit-as-d135-terminal-direct-child",
    "create-d136-offline-gate-plus-exact-ten-active-doc-evidence-commit-as-source-direct-child",
    "render-fresh-exact-external-activation-template",
)
SOURCE_PREPARATION_EXCLUSIONS = (
    "modify-delete-retry-resume-repair-or-backfill-d127-d132-d133-d134-d135-source-or-evidence",
    "create-d136-activation-receipt-attempt-action-started-pricing-evidence-or-terminal",
    "official-docs-search-open-network-or-real-pricing-capture",
    "docker-sdk-credential-dotenv-environment-value-or-endpoint-observation",
    "container-create-start-run-exec-pull-load-or-other-container-operation",
    "provider-evaluator-agent-memory-retrieval-injection-hash-candidate-cost-or-four-row-ac",
)
ACTIVATION_SCOPE = (
    "create-one-exact-d136-activation-receipt-and-sole-artifact-commit",
    "create-one-exact-d136-pricing-attempt-and-sole-artifact-commit",
    "record-one-exact-d136-action-started-immediately-before-helper-dispatch",
    "perform-one-bounded-unauthenticated-official-pricing-capture",
    "commit-action-started-plus-pricing-terminal-on-success",
    "preserve-action-started-only-as-sole-child-if-post-marker-capture-fails",
    "request-a-separate-offline-successor-after-a-committed-success-terminal",
)
ACTIVATION_EXCLUSIONS = (
    "reuse-retry-resume-repair-or-backfill-consumed-d132-d133-d134-or-d135",
    "docker-or-openai-sdk-credential-dotenv-environment-value-or-endpoint-observation",
    "container-create-start-run-exec-pull-load-or-other-container-operation",
    "provider-evaluator-agent-memory-retrieval-injection-hash-candidate-cost-or-four-row-ac",
)


class D136FixedPricingSuccessorError(ContractError):
    """The D-136 successor state or topology failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D136FixedPricingSuccessorError(message)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _repo_root(repository: str | Path | None) -> Path:
    try:
        return d135._repo_root(repository)
    except ContractError as exc:
        raise D136FixedPricingSuccessorError(str(exc)) from exc


def _parse_time(value: Any, *, label: str) -> datetime:
    try:
        return d135._parse_time(value, label=label)
    except ContractError as exc:
        raise D136FixedPricingSuccessorError(str(exc)) from exc


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


def _gate_envelope(body: dict[str, Any]) -> dict[str, Any]:
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": GATE_SCHEMA,
        "gate_id": f"d136_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _stable_read(root: Path, relative: Path) -> bytes:
    try:
        return d135._stable_read(root, relative)
    except ContractError as exc:
        raise D136FixedPricingSuccessorError(str(exc)) from exc


def _read_json(root: Path, relative: Path) -> tuple[dict[str, Any], bytes]:
    raw = _stable_read(root, relative)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D136FixedPricingSuccessorError(f"D-136 {relative.name} JSON differs") from exc
    _require(isinstance(payload, dict), f"D-136 {relative.name} root differs")
    return payload, raw


def _lexists(root: Path, relative: Path) -> bool:
    return os.path.lexists(root / relative)


def _path_absent(root: Path, relative: Path) -> None:
    _require(not _lexists(root, relative), f"D-136 unexpected path exists: {relative}")


def _write_new(root: Path, relative: Path, raw: bytes) -> None:
    try:
        selected = d135.d131.d129_offline._logical_path(root, relative, must_exist=False)
    except ContractError as exc:
        raise D136FixedPricingSuccessorError(str(exc)) from exc
    _require(not os.path.lexists(selected), f"D-136 {relative.name} already exists")
    temporary = selected.with_name(f".{selected.name}.d136-{uuid.uuid4().hex}.tmp")
    _require(not os.path.lexists(temporary), "D-136 temporary output collision")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        _require(temporary.read_bytes() == raw, "D-136 temporary output differs")
        try:
            os.link(temporary, selected)
        except FileExistsError as exc:
            raise D136FixedPricingSuccessorError(
                f"D-136 {relative.name} publication collision"
            ) from exc
        _require(_stable_read(root, relative) == raw, "D-136 persisted output differs")
    finally:
        with suppress(OSError):
            temporary.unlink()


def _git_command(root: Path, *args: str, binary: bool = False) -> bytes | str:
    try:
        return d135._git_command(root, *args, binary=binary)
    except ContractError as exc:
        raise D136FixedPricingSuccessorError(str(exc)) from exc


def _commit_identity(root: Path, commit: str) -> dict[str, Any]:
    try:
        return d135._commit_identity(root, commit)
    except ContractError as exc:
        raise D136FixedPricingSuccessorError(str(exc)) from exc


def _diff_rows(root: Path, commit: str) -> list[dict[str, str]]:
    try:
        return d135._diff_rows(root, commit)
    except ContractError as exc:
        raise D136FixedPricingSuccessorError(str(exc)) from exc


def _commit_blob(root: Path, commit: str, path: Path) -> tuple[str, bytes]:
    try:
        return d135._commit_blob(root, commit, path)
    except ContractError as exc:
        raise D136FixedPricingSuccessorError(str(exc)) from exc


def _status_lines(root: Path) -> list[str]:
    try:
        return d135._status_lines(root)
    except ContractError as exc:
        raise D136FixedPricingSuccessorError(str(exc)) from exc


def _head(root: Path) -> str:
    try:
        return d135._head(root)
    except ContractError as exc:
        raise D136FixedPricingSuccessorError(str(exc)) from exc


def _assert_runtime_import_boundary(root: Path) -> None:
    _require(
        not any(name in os.environ for name in PYTHON_ROUTING_ENV_NAMES),
        "D-136 Python import routing environment is present",
    )
    seen: set[tuple[str, str]] = set()
    for relative, module_name in LOADED_MODULE_PATHS:
        key = (relative.as_posix(), module_name)
        if key in seen:
            continue
        seen.add(key)
        module = sys.modules.get(module_name)
        loaded_value = getattr(module, "__file__", None)
        _require(isinstance(loaded_value, str), f"D-136 loaded module differs: {relative}")
        try:
            loaded = Path(loaded_value).resolve(strict=True)
            expected = (root / relative).resolve(strict=True)
        except OSError as exc:
            raise D136FixedPricingSuccessorError(
                f"D-136 loaded module differs: {relative}"
            ) from exc
        _require(loaded == expected, f"D-136 loaded module is outside repository: {relative}")


def _file_binding(root: Path, commit: str, path: Path) -> dict[str, Any]:
    oid, committed = _commit_blob(root, commit, path)
    current = _stable_read(root, path)
    _require(current == committed, f"D-136 source drift: {path}")
    return {
        "path": path.as_posix(),
        "blob_oid": oid,
        "file_sha256": sha256_bytes(committed),
        "file_bytes": len(committed),
        "current_bytes_match_commit": True,
    }


def _loaded_module_bindings(root: Path, commit: str) -> list[dict[str, Any]]:
    _assert_runtime_import_boundary(root)
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for path, module_name in LOADED_MODULE_PATHS:
        key = (path.as_posix(), module_name)
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                **_file_binding(root, commit, path),
                "module_name": module_name,
                "loaded_path": path.as_posix(),
                "loaded_path_matches_repository": True,
            }
        )
    return result


def _git_cli_observation(root: Path) -> dict[str, Any]:
    try:
        return d135.d131._git_cli_observation(root)
    except ContractError as exc:
        raise D136FixedPricingSuccessorError(str(exc)) from exc


def _validate_envelope(
    payload: dict[str, Any],
    raw: bytes,
    *,
    schema: str,
    prefix: str,
    gate: bool = False,
) -> dict[str, Any]:
    expected_root = GATE_ROOT_KEYS if gate else ROOT_KEYS
    _require(tuple(payload) == expected_root, "D-136 envelope fields differ")
    _require(payload["schema_version"] == schema, "D-136 envelope schema differs")
    body = payload["semantic_body"]
    _require(isinstance(body, dict), "D-136 semantic body differs")
    body_hash = sha256_text(canonical_json(body))
    _require(payload["semantic_body_hash"] == body_hash, "D-136 body SHA differs")
    id_key = "gate_id" if gate else "artifact_id"
    expected_id = f"{prefix}_{body_hash.removeprefix('sha256:')}"
    _require(payload[id_key] == expected_id, "D-136 stable ID differs")
    _require(raw == _pretty_bytes(payload), "D-136 artifact serialization differs")
    return body


def _artifact_binding(path: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    identifier = payload.get("gate_id", payload.get("artifact_id"))
    return {
        "path": path.as_posix(),
        "artifact_id": identifier,
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": payload["semantic_body"]["status"],
        "recorded_at": payload["semantic_body"]["recorded_at"],
    }


def _single_artifact_commit_binding(
    root: Path,
    *,
    commit: str,
    parent: str,
    path: Path,
    raw: bytes,
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [parent], f"D-136 {path.name} commit parent differs")
    _require(
        _diff_rows(root, commit) == [{"status": "A", "path": path.as_posix()}],
        f"D-136 {path.name} commit scope differs",
    )
    oid, committed = _commit_blob(root, commit, path)
    _require(committed == raw, f"D-136 {path.name} committed bytes differ")
    return {
        "commit": commit,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "artifact_path": path.as_posix(),
        "artifact_blob_oid": oid,
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_file_bytes": len(raw),
        "single_artifact_add_commit": True,
    }


def _pending_only(root: Path, path: Path, *, parent: str) -> bool:
    return _head(root) == parent and _status_lines(root) == [f"?? {path.as_posix()}"]


def _exact_d135_terminal(root: Path) -> dict[str, Any]:
    payload, raw = _read_json(root, D135_TERMINAL_PATH)
    try:
        body = d135._validate_terminal_payload(root, payload, raw)
    except ContractError as exc:
        raise D136FixedPricingSuccessorError("D-136 D-135 terminal validation failed") from exc
    _require(payload["artifact_id"] == D135_TERMINAL_ID, "D-136 D-135 terminal ID differs")
    _require(
        payload["semantic_body_hash"] == D135_TERMINAL_BODY_SHA256,
        "D-136 D-135 terminal body SHA differs",
    )
    _require(
        sha256_bytes(raw) == D135_TERMINAL_FILE_SHA256, "D-136 D-135 terminal file SHA differs"
    )
    _require(len(raw) == D135_TERMINAL_FILE_BYTES, "D-136 D-135 terminal bytes differ")
    identity = _commit_identity(root, D135_TERMINAL_COMMIT)
    _require(identity["tree"] == D135_TERMINAL_TREE, "D-136 D-135 terminal tree differs")
    _require(identity["parents"] == [D135_TERMINAL_PARENT], "D-136 D-135 terminal parent differs")
    _require(
        _diff_rows(root, D135_TERMINAL_COMMIT)
        == [{"status": "A", "path": D135_TERMINAL_PATH.as_posix()}],
        "D-136 D-135 terminal commit scope differs",
    )
    oid, committed = _commit_blob(root, D135_TERMINAL_COMMIT, D135_TERMINAL_PATH)
    _require(oid == D135_TERMINAL_BLOB_OID, "D-136 D-135 terminal blob differs")
    _require(committed == raw, "D-136 D-135 terminal committed bytes differ")
    return {
        **_artifact_binding(D135_TERMINAL_PATH, payload, raw),
        "terminal_body_status": body["status"],
        "d135_gate_binding": body["d135_gate_binding"],
        "incident_observation": body["incident_observation"],
        "next_gate": body["next_gate"],
        "commit_binding": {
            "commit": D135_TERMINAL_COMMIT,
            "tree": identity["tree"],
            "parents": identity["parents"],
            "artifact_path": D135_TERMINAL_PATH.as_posix(),
            "artifact_blob_oid": oid,
            "artifact_file_sha256": sha256_bytes(raw),
            "artifact_file_bytes": len(raw),
            "single_artifact_add_commit": True,
        },
    }


def _source_identity_for_gate(root: Path) -> dict[str, Any]:
    head = _head(root)
    identity = _commit_identity(root, head)
    _require(
        identity["parents"] == [D135_TERMINAL_COMMIT],
        "D-136 source parent is not the D-135 terminal commit",
    )
    expected = sorted(
        ({"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS),
        key=lambda row: row["path"],
    )
    _require(
        sorted(_diff_rows(root, head), key=lambda row: row["path"]) == expected,
        "D-136 source commit scope differs",
    )
    return {
        "commit": head,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "implementation_paths": [path.as_posix() for path in IMPLEMENTATION_PATHS],
        "source_file_bindings": [_file_binding(root, head, path) for path in SOURCE_BINDING_PATHS],
        "loaded_module_bindings": _loaded_module_bindings(root, head),
        "python_routing_env_presence": {name: False for name in PYTHON_ROUTING_ENV_NAMES},
        "git_cli_observation": _git_cli_observation(root),
        "exact_source_only_commit": True,
    }


def _validate_source_identity(root: Path, value: Any) -> None:
    _require(isinstance(value, dict), "D-136 source identity differs")
    commit = value.get("commit")
    _require(isinstance(commit, str), "D-136 source commit differs")
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [D135_TERMINAL_COMMIT], "D-136 stored source parent differs")
    expected = sorted(
        ({"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS),
        key=lambda row: row["path"],
    )
    _require(
        sorted(_diff_rows(root, commit), key=lambda row: row["path"]) == expected,
        "D-136 stored source scope differs",
    )
    rebuilt = {
        "commit": commit,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "implementation_paths": [path.as_posix() for path in IMPLEMENTATION_PATHS],
        "source_file_bindings": [
            _file_binding(root, commit, path) for path in SOURCE_BINDING_PATHS
        ],
        "loaded_module_bindings": _loaded_module_bindings(root, commit),
        "python_routing_env_presence": {name: False for name in PYTHON_ROUTING_ENV_NAMES},
        "git_cli_observation": _git_cli_observation(root),
        "exact_source_only_commit": True,
    }
    _require(
        canonical_json(value) == canonical_json(rebuilt), "D-136 source identity rebuild differs"
    )


def _fixed_helper_contract() -> dict[str, Any]:
    _require(
        pricing_capture.OFFICIAL_MODEL_PAGE_URL
        == "https://developers.openai.com/api/docs/models/gpt-5.4-mini.md"
        and pricing_capture.MODEL_ID == "gpt-5.4-mini-2026-03-17"
        and str(pricing_capture.INPUT_RATE) == "0.75"
        and str(pricing_capture.CACHED_INPUT_RATE) == "0.075"
        and str(pricing_capture.OUTPUT_RATE) == "4.5"
        and pricing_capture.MAX_REDIRECTS == 3
        and pricing_capture.MAX_DECODED_ENTITY_BYTES == 128_000
        and pricing_capture.REQUEST_TIMEOUT_SECONDS == 30.0,
        "D-136 fixed pricing helper contract differs",
    )
    return {
        "helper_module_path": IMPLEMENTATION_PATHS[0].as_posix(),
        "sealed_d127_helper_imported_or_invoked": False,
        "consumed_d132_runner_imported_or_invoked": False,
        "official_model_page_url": pricing_capture.OFFICIAL_MODEL_PAGE_URL,
        "model_id": pricing_capture.MODEL_ID,
        "maximum_redirects": pricing_capture.MAX_REDIRECTS,
        "maximum_application_level_public_get_send_count": pricing_capture.MAX_REDIRECTS + 1,
        "maximum_decoded_entity_bytes": pricing_capture.MAX_DECODED_ENTITY_BYTES,
        "request_timeout_seconds": pricing_capture.REQUEST_TIMEOUT_SECONDS,
        "request_auth_cookie_or_proxy_authority_forbidden": True,
        "response_context_manager_protocol_required": False,
        "response_closed_explicitly_in_finally": True,
        "wire_bytes_retained": False,
        "decoded_entity_replay_required": True,
    }


def _future_activation_contract() -> dict[str, Any]:
    return {
        "ordered_paths": [path.as_posix() for path in FUTURE_PATHS],
        "receipt_only_commit_required": True,
        "attempt_only_commit_required": True,
        "action_started_written_and_fsynced_immediately_before_helper": True,
        "action_started_and_terminal_two_artifact_commit_required_on_success": True,
        "action_started_only_preservation_commit_authorized_on_post_marker_failure": True,
        "post_marker_failure_consumes_activation_and_forbids_retry": True,
        "post_capture_successor_gate_requires_separate_offline_source_approval": True,
        "fresh_exact_activation_must_quote_gate_source_and_evidence_commit": True,
    }


def _gate_body(
    root: Path,
    *,
    recorded_at: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    recorded = _parse_time(recorded_at, label="D-136 gate recorded_at")
    predecessor = _exact_d135_terminal(root)
    predecessor_time = _parse_time(predecessor["recorded_at"], label="D-135 terminal recorded_at")
    _require(recorded > predecessor_time, "D-136 gate chronology differs")
    return {
        "milestone": MILESTONE,
        "evidence_kind": "fixed-pricing-successor-offline-source-qualification",
        "recorded_at": recorded_at,
        "status": GATE_STATUS,
        "predecessor_terminal": predecessor,
        "source_identity": source,
        "source_preparation_approval": {
            "exact_user_approval_recorded": True,
            "approval_is_self_attested": True,
            "approval_is_authenticated_or_signed": False,
            "approved_scope": list(SOURCE_PREPARATION_SCOPE),
            "approved_source_paths": [path.as_posix() for path in IMPLEMENTATION_PATHS],
            "explicit_exclusions": list(SOURCE_PREPARATION_EXCLUSIONS),
        },
        "fixed_pricing_helper_contract": _fixed_helper_contract(),
        "future_activation_contract": _future_activation_contract(),
        "offline_qualification": {
            "append_only_new_only_collision_orphan_and_idempotence_validated": True,
            "exact_d135_terminal_and_terminal_commit_bound": True,
            "exact_source_and_loaded_patchloop_modules_bound": True,
            "response_without_context_manager_mock_validated": True,
            "response_close_success_redirect_and_error_paths_mock_validated": True,
            "gate_builder_invoked_future_writer_count": 0,
            "gate_builder_invoked_pricing_helper_count": 0,
        },
        "evidence_boundary": {
            "d135_procedural_terminal_remains_immutable": True,
            "d132_activation_and_attempt_remain_consumed": True,
            "d132_completed_replayable_canonical_pricing_evidence_count": 0,
            "d132_canonical_pricing_evidence_artifact_created": False,
            "d132_canonical_replay_bytes_retained": 0,
            "d136_pricing_evidence_created": False,
            "source_qualification_is_not_external_activation": True,
            "mocked_transport_tests_are_not_official_pricing_evidence": True,
        },
        "authority": {
            "activation_receipt_created": False,
            "pricing_attempt_created": False,
            "action_started_created": False,
            "pricing_terminal_created": False,
            "official_docs_search_or_open_count": 0,
            "network_or_real_pricing_capture_count": 0,
            "docker_cli_call_count": 0,
            "sdk_credential_dotenv_environment_value_or_endpoint_observation_count": 0,
            "provider_evaluator_agent_call_count": 0,
            "memory_retrieval_or_injection_count": 0,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
        "next_gate": {
            "status": "D136_FRESH_EXACT_EXTERNAL_ACTIVATION_APPROVAL_REQUIRED",
            "current_d132_activation_reusable": False,
            "rendered_template_is_approval": False,
        },
    }


def _validate_gate_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=GATE_SCHEMA, prefix="d136", gate=True)
    _require(tuple(body) == GATE_BODY_KEYS, "D-136 gate body fields differ")
    _require(body["status"] == GATE_STATUS, "D-136 gate status differs")
    _validate_source_identity(root, body["source_identity"])
    expected = _gate_envelope(
        _gate_body(
            root,
            recorded_at=body.get("recorded_at"),
            source=body["source_identity"],
        )
    )
    _require(canonical_json(payload) == canonical_json(expected), "D-136 gate full rebuild differs")
    return body


def _pending_gate_only(root: Path, *, source_commit: str) -> bool:
    return _pending_only(root, GATE_PATH, parent=source_commit)


def _rebuild_gate_evidence_commit(
    root: Path,
    *,
    commit: str,
    source_commit: str,
    gate_raw: bytes,
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [source_commit], "D-136 gate evidence parent differs")
    expected = [
        {"status": "A", "path": GATE_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
    ]
    _require(
        sorted(_diff_rows(root, commit), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-136 gate evidence scope differs",
    )
    oid, committed = _commit_blob(root, commit, GATE_PATH)
    _require(committed == gate_raw, "D-136 committed gate bytes differ")
    return {
        "commit": commit,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "artifact_path": GATE_PATH.as_posix(),
        "artifact_blob_oid": oid,
        "artifact_file_sha256": sha256_bytes(committed),
        "artifact_file_bytes": len(committed),
        "exact_gate_add_and_active_docs_modify_commit": True,
    }


def run_d136_offline_source_gate(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in FUTURE_PATHS:
        _path_absent(root, path)
    if _lexists(root, GATE_PATH):
        mode: Literal["current-source", "post-evidence-commit"] = (
            "post-evidence-commit" if _status_lines(root) == [] else "current-source"
        )
        return validate_d136_offline_source_gate(repository=root, mode=mode)
    _require(_status_lines(root) == [], "D-136 source checkout is not clean")
    source = _source_identity_for_gate(root)
    payload = _gate_envelope(_gate_body(root, recorded_at=_now(), source=source))
    raw = _pretty_bytes(payload)
    _write_new(root, GATE_PATH, raw)
    return validate_d136_offline_source_gate(repository=root)


def validate_d136_offline_source_gate(
    *,
    repository: str | Path | None = None,
    mode: Literal["current-source", "post-evidence-commit"] = "current-source",
) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in FUTURE_PATHS:
        _path_absent(root, path)
    payload, raw = _read_json(root, GATE_PATH)
    body = _validate_gate_payload(root, payload, raw)
    source_commit = body["source_identity"]["commit"]
    evidence_commit = None
    if mode == "current-source":
        _require(
            _pending_gate_only(root, source_commit=source_commit),
            "D-136 pending gate checkout differs",
        )
    elif mode == "post-evidence-commit":
        _require(_status_lines(root) == [], "D-136 evidence checkout is not clean")
        evidence_commit = _rebuild_gate_evidence_commit(
            root,
            commit=_head(root),
            source_commit=source_commit,
            gate_raw=raw,
        )
    else:
        raise D136FixedPricingSuccessorError("D-136 gate validation mode differs")
    return {
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "source_commit": source_commit,
        "gate_evidence_commit": evidence_commit,
        "future_artifacts_created": False,
        "external_call_count": 0,
    }


def _gate_binding_for_activation(
    root: Path,
) -> tuple[dict[str, Any], bytes, dict[str, Any], dict[str, Any]]:
    payload, raw = _read_json(root, GATE_PATH)
    body = _validate_gate_payload(root, payload, raw)
    _require(_status_lines(root) == [], "D-136 activation requires a clean gate checkout")
    evidence = _rebuild_gate_evidence_commit(
        root,
        commit=_head(root),
        source_commit=body["source_identity"]["commit"],
        gate_raw=raw,
    )
    binding = {
        **_artifact_binding(GATE_PATH, payload, raw),
        "evidence_commit_binding": evidence,
    }
    return payload, raw, body, binding


def render_d136_external_activation_template(*, repository: str | Path | None = None) -> str:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in FUTURE_PATHS:
        _path_absent(root, path)
    payload, _raw, body, binding = _gate_binding_for_activation(root)
    evidence = binding["evidence_commit_binding"]
    source = body["source_identity"]
    return "\n".join(
        (
            "D-136 fixed-pricing successor fresh exact activation approval",
            "(bounded official public pricing capture only; no provider or cost authority)",
            "",
            f"Gate ID: {payload['gate_id']}",
            f"Gate body SHA: {payload['semantic_body_hash']}",
            f"Gate file SHA: {binding['file_sha256']}",
            f"Gate file bytes: {binding['file_bytes']}",
            "Gate evidence commit tuple: "
            + json.dumps(evidence, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
            f"Source commit: {source['commit']}",
            f"Source tree: {source['tree']}",
            f"D-135 terminal commit: {D135_TERMINAL_COMMIT}",
            "",
            "Approved bounded scope:",
            *(f"- {item}" for item in ACTIVATION_SCOPE),
            "",
            "Explicitly not approved:",
            *(f"- {item}" for item in ACTIVATION_EXCLUSIONS),
            "",
            "ACTION_STARTED is written and fsynced immediately before the one helper dispatch.",
            "A post-marker exception consumes this activation; the marker may only be preserved",
            "as the sole artifact in the attempt commit's direct child and must never be retried.",
            "A successful terminal authorizes no Docker/SDK preflight;",
            "that needs a later offline successor.",
            "This rendered template is not approval; a new exact user message is required.",
        )
    )


def _receipt_body(
    *,
    recorded_at: str,
    gate_binding: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    recorded = _parse_time(recorded_at, label="D-136 receipt recorded_at")
    gate_time = _parse_time(gate_binding["recorded_at"], label="D-136 gate recorded_at")
    _require(recorded > gate_time, "D-136 receipt chronology differs")
    return {
        "milestone": MILESTONE,
        "evidence_kind": "fixed-pricing-successor-activation-receipt",
        "recorded_at": recorded_at,
        "status": RECEIPT_STATUS,
        "source_gate_binding": gate_binding,
        "source_identity": source,
        "activation_approval": {
            "exact_user_approval_recorded": True,
            "approval_is_self_attested": True,
            "approval_is_authenticated_or_signed": False,
            "approved_scope": list(ACTIVATION_SCOPE),
            "explicit_exclusions": list(ACTIVATION_EXCLUSIONS),
        },
        "future_activation_contract": _future_activation_contract(),
        "authority": {
            "pricing_helper_invocation_count": 0,
            "official_public_get_send_count": 0,
            "docker_sdk_credential_provider_or_agent_call_count": 0,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
    }


def _validate_receipt_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(
        payload,
        raw,
        schema=RECEIPT_SCHEMA,
        prefix="d136approval",
    )
    _require(tuple(body) == RECEIPT_BODY_KEYS, "D-136 receipt body fields differ")
    gate_payload, gate_raw = _read_json(root, GATE_PATH)
    gate_body = _validate_gate_payload(root, gate_payload, gate_raw)
    gate_binding = body.get("source_gate_binding")
    _require(isinstance(gate_binding, dict), "D-136 receipt gate binding differs")
    evidence = gate_binding.get("evidence_commit_binding")
    _require(isinstance(evidence, dict), "D-136 receipt gate commit binding differs")
    rebuilt_evidence = _rebuild_gate_evidence_commit(
        root,
        commit=evidence.get("commit", ""),
        source_commit=gate_body["source_identity"]["commit"],
        gate_raw=gate_raw,
    )
    expected_gate = {
        **_artifact_binding(GATE_PATH, gate_payload, gate_raw),
        "evidence_commit_binding": rebuilt_evidence,
    }
    expected = _envelope(
        RECEIPT_SCHEMA,
        "d136approval",
        _receipt_body(
            recorded_at=body.get("recorded_at"),
            gate_binding=expected_gate,
            source=gate_body["source_identity"],
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected), "D-136 receipt full rebuild differs"
    )
    return body


def _receipt_result(
    payload: dict[str, Any],
    raw: bytes,
    *,
    commit: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": payload["semantic_body"]["status"],
        "receipt_commit": commit,
        "commit_required_before_next_action": commit is None,
        "external_call_count": 0,
    }


def create_d136_activation_receipt(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in FUTURE_PATHS[1:]:
        _path_absent(root, path)
    if _lexists(root, RECEIPT_PATH):
        mode: Literal["pending", "post-commit"] = (
            "post-commit" if _status_lines(root) == [] else "pending"
        )
        return validate_d136_activation_receipt(repository=root, mode=mode)
    _payload, _raw, gate_body, gate_binding = _gate_binding_for_activation(root)
    payload = _envelope(
        RECEIPT_SCHEMA,
        "d136approval",
        _receipt_body(
            recorded_at=_now(),
            gate_binding=gate_binding,
            source=gate_body["source_identity"],
        ),
    )
    raw = _pretty_bytes(payload)
    _write_new(root, RECEIPT_PATH, raw)
    return validate_d136_activation_receipt(repository=root, mode="pending")


def validate_d136_activation_receipt(
    *,
    repository: str | Path | None = None,
    mode: Literal["pending", "post-commit"] = "pending",
) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in FUTURE_PATHS[1:]:
        _path_absent(root, path)
    payload, raw = _read_json(root, RECEIPT_PATH)
    body = _validate_receipt_payload(root, payload, raw)
    gate_commit = body["source_gate_binding"]["evidence_commit_binding"]["commit"]
    commit = None
    if mode == "pending":
        _require(
            _pending_only(root, RECEIPT_PATH, parent=gate_commit), "D-136 pending receipt differs"
        )
    elif mode == "post-commit":
        _require(_status_lines(root) == [], "D-136 receipt commit checkout is not clean")
        commit = _single_artifact_commit_binding(
            root,
            commit=_head(root),
            parent=gate_commit,
            path=RECEIPT_PATH,
            raw=raw,
        )
    else:
        raise D136FixedPricingSuccessorError("D-136 receipt validation mode differs")
    return _receipt_result(payload, raw, commit=commit)


def _attempt_body(
    *,
    recorded_at: str,
    receipt_binding: dict[str, Any],
    parent_commit: dict[str, Any],
) -> dict[str, Any]:
    recorded = _parse_time(recorded_at, label="D-136 attempt recorded_at")
    receipt_time = _parse_time(receipt_binding["recorded_at"], label="D-136 receipt recorded_at")
    _require(recorded > receipt_time, "D-136 attempt chronology differs")
    return {
        "milestone": MILESTONE,
        "evidence_kind": "fixed-pricing-capture-attempt-intent",
        "recorded_at": recorded_at,
        "status": ATTEMPT_STATUS,
        "activation_receipt_binding": receipt_binding,
        "parent_commit_binding": parent_commit,
        "capture_contract": {
            "helper_module_path": IMPLEMENTATION_PATHS[0].as_posix(),
            "official_model_page_url": pricing_capture.OFFICIAL_MODEL_PAGE_URL,
            "maximum_redirects": pricing_capture.MAX_REDIRECTS,
            "maximum_application_level_public_get_send_count": pricing_capture.MAX_REDIRECTS + 1,
            "action_started_must_be_newly_written_and_fsynced_before_helper": True,
            "post_marker_exception_consumes_attempt": True,
            "transport_retry_count": 0,
        },
        "authority": {
            "action_started_created": False,
            "pricing_helper_invocation_count": 0,
            "official_public_get_send_count": 0,
            "pricing_terminal_created": False,
            "docker_sdk_credential_provider_or_agent_call_count": 0,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
    }


def _validate_attempt_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=ATTEMPT_SCHEMA, prefix="d136pricingattempt")
    _require(tuple(body) == ATTEMPT_BODY_KEYS, "D-136 attempt body fields differ")
    receipt_payload, receipt_raw = _read_json(root, RECEIPT_PATH)
    receipt_body = _validate_receipt_payload(root, receipt_payload, receipt_raw)
    parent = body.get("parent_commit_binding")
    _require(isinstance(parent, dict), "D-136 attempt parent binding differs")
    gate_commit = receipt_body["source_gate_binding"]["evidence_commit_binding"]["commit"]
    receipt_commit = _single_artifact_commit_binding(
        root,
        commit=parent.get("commit", ""),
        parent=gate_commit,
        path=RECEIPT_PATH,
        raw=receipt_raw,
    )
    expected_receipt = _artifact_binding(RECEIPT_PATH, receipt_payload, receipt_raw)
    expected = _envelope(
        ATTEMPT_SCHEMA,
        "d136pricingattempt",
        _attempt_body(
            recorded_at=body.get("recorded_at"),
            receipt_binding=expected_receipt,
            parent_commit=receipt_commit,
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected), "D-136 attempt full rebuild differs"
    )
    return body


def _attempt_result(
    payload: dict[str, Any], raw: bytes, *, commit: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": payload["semantic_body"]["status"],
        "attempt_commit": commit,
        "commit_required_before_next_action": commit is None,
        "external_call_count": 0,
    }


def create_d136_pricing_attempt(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in FUTURE_PATHS[2:]:
        _path_absent(root, path)
    if _lexists(root, ATTEMPT_PATH):
        mode: Literal["pending", "post-commit"] = (
            "post-commit" if _status_lines(root) == [] else "pending"
        )
        return validate_d136_pricing_attempt(repository=root, mode=mode)
    receipt_payload, receipt_raw = _read_json(root, RECEIPT_PATH)
    receipt_body = _validate_receipt_payload(root, receipt_payload, receipt_raw)
    _require(_status_lines(root) == [], "D-136 attempt requires a clean receipt commit")
    gate_commit = receipt_body["source_gate_binding"]["evidence_commit_binding"]["commit"]
    receipt_commit = _single_artifact_commit_binding(
        root,
        commit=_head(root),
        parent=gate_commit,
        path=RECEIPT_PATH,
        raw=receipt_raw,
    )
    payload = _envelope(
        ATTEMPT_SCHEMA,
        "d136pricingattempt",
        _attempt_body(
            recorded_at=_now(),
            receipt_binding=_artifact_binding(RECEIPT_PATH, receipt_payload, receipt_raw),
            parent_commit=receipt_commit,
        ),
    )
    raw = _pretty_bytes(payload)
    _write_new(root, ATTEMPT_PATH, raw)
    return validate_d136_pricing_attempt(repository=root, mode="pending")


def validate_d136_pricing_attempt(
    *,
    repository: str | Path | None = None,
    mode: Literal["pending", "post-commit"] = "pending",
) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in FUTURE_PATHS[2:]:
        _path_absent(root, path)
    payload, raw = _read_json(root, ATTEMPT_PATH)
    body = _validate_attempt_payload(root, payload, raw)
    receipt_commit = body["parent_commit_binding"]["commit"]
    commit = None
    if mode == "pending":
        _require(
            _pending_only(root, ATTEMPT_PATH, parent=receipt_commit),
            "D-136 pending attempt differs",
        )
    elif mode == "post-commit":
        _require(_status_lines(root) == [], "D-136 attempt commit checkout is not clean")
        commit = _single_artifact_commit_binding(
            root,
            commit=_head(root),
            parent=receipt_commit,
            path=ATTEMPT_PATH,
            raw=raw,
        )
    else:
        raise D136FixedPricingSuccessorError("D-136 attempt validation mode differs")
    return _attempt_result(payload, raw, commit=commit)


def _started_body(
    *,
    recorded_at: str,
    attempt_binding: dict[str, Any],
    parent_commit: dict[str, Any],
) -> dict[str, Any]:
    recorded = _parse_time(recorded_at, label="D-136 ACTION_STARTED recorded_at")
    attempt_time = _parse_time(attempt_binding["recorded_at"], label="D-136 attempt recorded_at")
    _require(recorded > attempt_time, "D-136 ACTION_STARTED chronology differs")
    return {
        "milestone": MILESTONE,
        "evidence_kind": "fixed-pricing-capture-action-started",
        "recorded_at": recorded_at,
        "status": STARTED_STATUS,
        "pricing_attempt_binding": attempt_binding,
        "parent_commit_binding": parent_commit,
        "capture_contract": {
            "marker_is_durable_before_helper_dispatch": True,
            "helper_invocation_limit": 1,
            "transport_retry_count": 0,
            "post_marker_exception_consumes_attempt": True,
            "marker_only_preservation_commit_is_pre_authorized": True,
        },
        "authority": {
            "pricing_helper_invocation_count_at_marker_write": 0,
            "official_public_get_send_count_at_marker_write": 0,
            "pricing_terminal_created_at_marker_write": False,
            "docker_sdk_credential_provider_or_agent_call_count": 0,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
    }


def _validate_started_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=STARTED_SCHEMA, prefix="d136pricingstarted")
    _require(tuple(body) == STARTED_BODY_KEYS, "D-136 ACTION_STARTED body fields differ")
    attempt_payload, attempt_raw = _read_json(root, ATTEMPT_PATH)
    attempt_body = _validate_attempt_payload(root, attempt_payload, attempt_raw)
    parent = body.get("parent_commit_binding")
    _require(isinstance(parent, dict), "D-136 ACTION_STARTED parent binding differs")
    receipt_commit = attempt_body["parent_commit_binding"]["commit"]
    attempt_commit = _single_artifact_commit_binding(
        root,
        commit=parent.get("commit", ""),
        parent=receipt_commit,
        path=ATTEMPT_PATH,
        raw=attempt_raw,
    )
    expected = _envelope(
        STARTED_SCHEMA,
        "d136pricingstarted",
        _started_body(
            recorded_at=body.get("recorded_at"),
            attempt_binding=_artifact_binding(ATTEMPT_PATH, attempt_payload, attempt_raw),
            parent_commit=attempt_commit,
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected),
        "D-136 ACTION_STARTED full rebuild differs",
    )
    return body


def validate_d136_action_started(
    *,
    repository: str | Path | None = None,
    mode: Literal["pending-marker", "post-preservation-commit"] = "pending-marker",
) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    _path_absent(root, TERMINAL_PATH)
    payload, raw = _read_json(root, STARTED_PATH)
    body = _validate_started_payload(root, payload, raw)
    attempt_commit = body["parent_commit_binding"]["commit"]
    commit = None
    if mode == "pending-marker":
        _require(
            _pending_only(root, STARTED_PATH, parent=attempt_commit),
            "D-136 pending ACTION_STARTED marker differs",
        )
    elif mode == "post-preservation-commit":
        _require(_status_lines(root) == [], "D-136 marker preservation checkout is not clean")
        commit = _single_artifact_commit_binding(
            root,
            commit=_head(root),
            parent=attempt_commit,
            path=STARTED_PATH,
            raw=raw,
        )
    else:
        raise D136FixedPricingSuccessorError("D-136 ACTION_STARTED validation mode differs")
    return {
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "marker_preservation_commit": commit,
        "activation_consumed": True,
        "retry_allowed": False,
        "external_call_count_reconstructed": None,
    }


def _terminal_body(
    *,
    recorded_at: str,
    started_binding: dict[str, Any],
    parent_commit: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    recorded = _parse_time(recorded_at, label="D-136 pricing terminal recorded_at")
    started_time = _parse_time(
        started_binding["recorded_at"], label="D-136 ACTION_STARTED recorded_at"
    )
    observed = _parse_time(observation.get("observed_at"), label="D-136 pricing observed_at")
    _require(recorded >= observed > started_time, "D-136 pricing terminal chronology differs")
    return {
        "milestone": MILESTONE,
        "evidence_kind": "replayable-official-pricing-evidence-terminal",
        "recorded_at": recorded_at,
        "status": TERMINAL_STATUS,
        "action_started_binding": started_binding,
        "parent_commit_binding": parent_commit,
        "observation": observation,
        "activity_accounting": {
            "pricing_helper_invocation_count": 1,
            "official_public_get_send_count": observation["public_get_request_count"],
            "maximum_authorized_public_get_send_count": pricing_capture.MAX_REDIRECTS + 1,
            "docker_cli_call_count": 0,
            "sdk_credential_dotenv_environment_value_or_endpoint_observation_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
        "evidence_boundary": {
            "decoded_entity_is_bounded_and_replayable": True,
            "wire_bytes_retained": False,
            "origin_signature_present": False,
            "d132_evidence_was_not_repaired_or_backfilled": True,
            "d136_evidence_is_a_distinct_successor": True,
        },
        "authority": {
            "docker_or_sdk_no_call_preflight_authorized": False,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
        "next_gate": {
            "status": "D137_NO_CALL_PREFLIGHT_SUCCESSOR_OFFLINE_SOURCE_APPROVAL_REQUIRED",
            "fresh_separate_approval_required": True,
            "current_activation_authorizes_next_gate": False,
        },
    }


def _validate_terminal_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=TERMINAL_SCHEMA, prefix="d136pricing")
    _require(tuple(body) == TERMINAL_BODY_KEYS, "D-136 pricing terminal body fields differ")
    started_payload, started_raw = _read_json(root, STARTED_PATH)
    started_body = _validate_started_payload(root, started_payload, started_raw)
    try:
        observation = pricing_capture.validate_official_pricing_evidence(body.get("observation"))
    except (ValueError, TypeError) as exc:
        raise D136FixedPricingSuccessorError("D-136 pricing evidence validation failed") from exc
    expected = _envelope(
        TERMINAL_SCHEMA,
        "d136pricing",
        _terminal_body(
            recorded_at=body.get("recorded_at"),
            started_binding=_artifact_binding(STARTED_PATH, started_payload, started_raw),
            parent_commit=started_body["parent_commit_binding"],
            observation=observation,
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected),
        "D-136 pricing terminal full rebuild differs",
    )
    return body


def _success_transition_commit_binding(
    root: Path,
    *,
    commit: str,
    parent: str,
    started_raw: bytes,
    terminal_raw: bytes,
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [parent], "D-136 success transition parent differs")
    expected = sorted(
        (
            {"status": "A", "path": STARTED_PATH.as_posix()},
            {"status": "A", "path": TERMINAL_PATH.as_posix()},
        ),
        key=lambda row: row["path"],
    )
    _require(
        sorted(_diff_rows(root, commit), key=lambda row: row["path"]) == expected,
        "D-136 success transition scope differs",
    )
    started_oid, committed_started = _commit_blob(root, commit, STARTED_PATH)
    terminal_oid, committed_terminal = _commit_blob(root, commit, TERMINAL_PATH)
    _require(committed_started == started_raw, "D-136 committed ACTION_STARTED bytes differ")
    _require(committed_terminal == terminal_raw, "D-136 committed terminal bytes differ")
    return {
        "commit": commit,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "artifact_paths": [STARTED_PATH.as_posix(), TERMINAL_PATH.as_posix()],
        "artifact_blob_oids": {
            STARTED_PATH.as_posix(): started_oid,
            TERMINAL_PATH.as_posix(): terminal_oid,
        },
        "exact_action_started_and_terminal_add_commit": True,
    }


def run_d136_fixed_pricing_capture(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    if _lexists(root, TERMINAL_PATH) and not _lexists(root, STARTED_PATH):
        raise D136FixedPricingSuccessorError("D-136 pricing terminal is orphaned")
    if _lexists(root, STARTED_PATH):
        started_payload, started_raw = _read_json(root, STARTED_PATH)
        _validate_started_payload(root, started_payload, started_raw)
        if _lexists(root, TERMINAL_PATH):
            mode: Literal["pending", "post-transition-commit"] = (
                "post-transition-commit" if _status_lines(root) == [] else "pending"
            )
            return validate_d136_pricing_terminal(repository=root, mode=mode)
        # The marker was written immediately before a prior dispatch.  Whether
        # that dispatch reached HTTP is deliberately not reconstructed here.
        raise D136FixedPricingSuccessorError(
            "D-136 ACTION_STARTED has no terminal; activation is consumed and retry is forbidden"
        )

    attempt_payload, attempt_raw = _read_json(root, ATTEMPT_PATH)
    attempt_body = _validate_attempt_payload(root, attempt_payload, attempt_raw)
    _require(_status_lines(root) == [], "D-136 capture requires a clean attempt commit")
    receipt_commit = attempt_body["parent_commit_binding"]["commit"]
    attempt_commit = _single_artifact_commit_binding(
        root,
        commit=_head(root),
        parent=receipt_commit,
        path=ATTEMPT_PATH,
        raw=attempt_raw,
    )
    started = _envelope(
        STARTED_SCHEMA,
        "d136pricingstarted",
        _started_body(
            recorded_at=_now(),
            attempt_binding=_artifact_binding(ATTEMPT_PATH, attempt_payload, attempt_raw),
            parent_commit=attempt_commit,
        ),
    )
    started_raw = _pretty_bytes(started)
    _write_new(root, STARTED_PATH, started_raw)
    stored_started, stored_started_raw = _read_json(root, STARTED_PATH)
    _validate_started_payload(root, stored_started, stored_started_raw)
    _require(stored_started_raw == started_raw, "D-136 ACTION_STARTED durability differs")
    _require(
        _pending_only(root, STARTED_PATH, parent=attempt_commit["commit"]),
        "D-136 checkout drifted after ACTION_STARTED and before helper",
    )

    try:
        observation = pricing_capture.capture_official_pricing_evidence()
        pricing_capture.validate_official_pricing_evidence(observation)
    except Exception as exc:
        raise D136FixedPricingSuccessorError(
            "D-136 pricing capture failed after ACTION_STARTED; activation is consumed"
        ) from exc

    fresh_attempt, fresh_attempt_raw = _read_json(root, ATTEMPT_PATH)
    _validate_attempt_payload(root, fresh_attempt, fresh_attempt_raw)
    _require(
        fresh_attempt_raw == attempt_raw,
        "D-136 pricing attempt drifted after helper",
    )
    fresh_started, fresh_started_raw = _read_json(root, STARTED_PATH)
    _validate_started_payload(root, fresh_started, fresh_started_raw)
    _require(
        fresh_started_raw == stored_started_raw
        and _pending_only(root, STARTED_PATH, parent=attempt_commit["commit"]),
        "D-136 checkout drifted after helper and before terminal",
    )

    terminal = _envelope(
        TERMINAL_SCHEMA,
        "d136pricing",
        _terminal_body(
            recorded_at=_now(),
            started_binding=_artifact_binding(STARTED_PATH, fresh_started, fresh_started_raw),
            parent_commit=attempt_commit,
            observation=observation,
        ),
    )
    terminal_raw = _pretty_bytes(terminal)
    _write_new(root, TERMINAL_PATH, terminal_raw)
    return validate_d136_pricing_terminal(repository=root, mode="pending")


def validate_d136_pricing_terminal(
    *,
    repository: str | Path | None = None,
    mode: Literal["pending", "post-transition-commit"] = "pending",
) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    started_payload, started_raw = _read_json(root, STARTED_PATH)
    started_body = _validate_started_payload(root, started_payload, started_raw)
    payload, raw = _read_json(root, TERMINAL_PATH)
    body = _validate_terminal_payload(root, payload, raw)
    attempt_commit = started_body["parent_commit_binding"]["commit"]
    transition = None
    if mode == "pending":
        expected = sorted((f"?? {STARTED_PATH.as_posix()}", f"?? {TERMINAL_PATH.as_posix()}"))
        _require(
            _head(root) == attempt_commit and sorted(_status_lines(root)) == expected,
            "D-136 pending success transition differs",
        )
    elif mode == "post-transition-commit":
        _require(_status_lines(root) == [], "D-136 success transition checkout is not clean")
        transition = _success_transition_commit_binding(
            root,
            commit=_head(root),
            parent=attempt_commit,
            started_raw=started_raw,
            terminal_raw=raw,
        )
    else:
        raise D136FixedPricingSuccessorError("D-136 pricing terminal validation mode differs")
    return {
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "success_transition_commit": transition,
        "commit_required_before_successor": transition is None,
        "official_public_get_send_count": body["activity_accounting"][
            "official_public_get_send_count"
        ],
        "provider_evaluator_agent_call_count": 0,
        "cost_reserved_or_spent_usd": "0",
    }


__all__ = [
    "ACTIVE_DOC_PATHS",
    "ATTEMPT_PATH",
    "ATTEMPT_SCHEMA",
    "ATTEMPT_STATUS",
    "D135_TERMINAL_COMMIT",
    "D135_TERMINAL_PATH",
    "D136FixedPricingSuccessorError",
    "FUTURE_PATHS",
    "GATE_PATH",
    "GATE_SCHEMA",
    "GATE_STATUS",
    "IMPLEMENTATION_PATHS",
    "RECEIPT_PATH",
    "RECEIPT_SCHEMA",
    "RECEIPT_STATUS",
    "STARTED_PATH",
    "STARTED_SCHEMA",
    "STARTED_STATUS",
    "TERMINAL_PATH",
    "TERMINAL_SCHEMA",
    "TERMINAL_STATUS",
    "create_d136_activation_receipt",
    "create_d136_pricing_attempt",
    "render_d136_external_activation_template",
    "run_d136_fixed_pricing_capture",
    "run_d136_offline_source_gate",
    "validate_d136_action_started",
    "validate_d136_activation_receipt",
    "validate_d136_offline_source_gate",
    "validate_d136_pricing_attempt",
    "validate_d136_pricing_terminal",
]
