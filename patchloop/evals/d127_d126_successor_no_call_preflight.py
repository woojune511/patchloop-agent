"""D-127 blocker remediation and repeated no-call preflight evidence.

Receipt creation and static checks make no external calls.  The separately
invoked production path may use an already-running local Docker daemon, pull
only two digest-pinned images when absent, capture one bounded official pricing
response, and perform two read-only Docker readiness snapshots.  A daemon-down
state blocks because starting Desktop could auto-start pre-existing containers.
The path never creates or runs a container, calls a provider/evaluator/agent,
builds an execution hash or candidate, injects memory, or reserves or spends
cost.
"""

from __future__ import annotations

import ast
import importlib.metadata
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.evals import d126_clean_source_pricing_no_call_preflight as d126
from patchloop.evals import d127_docker_remediation as docker_remediation
from patchloop.evals import d127_pricing_capture as pricing_capture
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-127"
RECEIPT_SCHEMA = "d126-successor-blocker-remediation-no-call-approval-receipt-d127-v1"
RECEIPT_STATUS = "D127_D126_SUCCESSOR_BLOCKER_REMEDIATION_NO_CALL_APPROVAL_RECORDED"
STATIC_READY_STATUS = "D127_STATIC_PREREQUISITES_READY_EXTERNAL_ACTION_NOT_STARTED"
REMEDIATION_READY_STATUS = "D127_EXACT_DOCKER_REMEDIATION_READY"
REMEDIATION_BLOCKED_STATUS = "D127_EXACT_DOCKER_REMEDIATION_OBSERVED_BLOCKED"
PRICING_CAPTURED_STATUS = "D127_REPLAYABLE_OFFICIAL_PRICING_CAPTURED"
PREFLIGHT_READY_STATUS = "D127_REPEATED_NO_CALL_PREFLIGHT_READY_EXECUTION_HASH_BLOCKED"
PREFLIGHT_BLOCKED_STATUS = "D127_REPEATED_NO_CALL_PREFLIGHT_OBSERVED_BLOCKED"
GATE_READY_STATUS = "D127_BLOCKER_REMEDIATION_NO_CALL_GATE_READY_EXECUTION_HASH_BLOCKED"
GATE_BLOCKED_STATUS = "D127_BLOCKER_REMEDIATION_NO_CALL_GATE_OBSERVED_BLOCKED"

REMEDIATION_SCHEMA = "d126-successor-docker-remediation-d127-v1"
PRICING_SCHEMA = "d126-successor-replayable-official-pricing-d127-v1"
PREFLIGHT_SCHEMA = "d126-successor-repeated-no-call-preflight-d127-v1"
GATE_SCHEMA = "d126-successor-blocker-remediation-no-call-gate-d127-v1"
ATTEMPT_SCHEMA = "d126-successor-external-phase-attempt-intent-d127-v1"
FRESHNESS_SECONDS = 72 * 60 * 60

D126_GATE_PATH = Path(
    "reports/live-pilot/artifacts/d126-ac-clean-source-pricing-no-call-preflight-gate.json"
)
D126_GATE_ID = "d126_d2ab27d34a7b56e51ba21d1d6274707b13e8345de6feb3bc9719d047ca834c4d"
D126_BODY_SHA256 = "sha256:d2ab27d34a7b56e51ba21d1d6274707b13e8345de6feb3bc9719d047ca834c4d"
D126_FILE_SHA256 = "sha256:e08e8f7aad8f425c7069290a98ac04a5c471bc8c948e1a08121c962b5ba18696"
D126_FILE_BYTES = 3_078
D126_STATUS = "D126_CLEAN_SOURCE_PRICING_NO_CALL_PREFLIGHT_OBSERVED_BLOCKED"

RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d127-d126-successor-blocker-remediation-no-call-preflight-approval-receipt.json"
)
REMEDIATION_PATH = Path(
    "reports/live-pilot/artifacts/d127-exact-docker-remediation-observation.json"
)
REMEDIATION_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d127-docker-remediation-attempt-intent.json"
)
PRICING_PATH = Path(
    "reports/live-pilot/artifacts/d127-replayable-official-pricing-evidence.json"
)
PRICING_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d127-official-pricing-capture-attempt-intent.json"
)
PREFLIGHT_PATH = Path(
    "reports/live-pilot/artifacts/d127-repeated-no-call-readiness-preflight.json"
)
PREFLIGHT_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d127-read-only-preflight-attempt-intent.json"
)
GATE_PATH = Path(
    "reports/live-pilot/artifacts/d127-blocker-remediation-no-call-preflight-gate.json"
)

DOCKER_CLI_VERSION = "29.6.2"
DOCKER_CLI_BYTES = 43_095_472
DOCKER_CLI_SHA256 = "sha256:8985cd8ac002c3240b5aa48fe401fcb55dca5d849b537e3c835564e8e8c49a70"
DAEMON_START_SKIPPED_REASON = "preexisting-container-auto-restart-state-unverified"
DOCKER_IMAGE_REFS = (
    "docker.io/swerebenchv2/getmoto-moto@"
    "sha256:dfdf957ab30b8829e8b6bbfd693b00fab88b7979d3c856362fd5d66c489a1fee",
    "docker.io/swerebenchv2/python-babel-babel@"
    "sha256:864e84fc4bdf09252f7fda4f85665cc05155a7b1d75847d61c67325abce7ef5a",
)
OFFICIAL_API_BASE_URL = "https://api.openai.com/v1"

APPROVED_SCOPE = (
    "set-production-openai-client-official-base-url-and-trust-env-false",
    "retain-replayable-bounded-official-pricing-evidence",
    "modify-related-source-tests-docs-and-create-local-git-commit",
    "use-exact-approved-docker-cli-identity",
    "start-docker-desktop-linux-daemon",
    "pull-or-load-only-the-two-exact-approved-images-if-missing",
    "run-read-only-docker-sdk-credential-presence-and-endpoint-preflight",
    "read-official-pricing-and-create-append-only-successor-evidence",
)
NOT_AUTHORIZED = (
    "provider-evaluator-or-agent-execution",
    "runtime-memory-injection-or-retrieval",
    "container-create-start-run-or-exec",
    "execution-hash-or-execution-candidate-creation",
    "cost-reservation-or-spend",
    "four-row-ac-execution",
)

FORBIDDEN_ROUTING_ENV_NAMES = (
    "OPENAI_ADMIN_KEY",
    "OPENAI_AD_TOKEN",
    "OPENAI_BASE_URL",
    "OPENAI_API_BASE",
    "OPENAI_API_TYPE",
    "OPENAI_API_VERSION",
    "OPENAI_CUSTOM_HEADERS",
    "OPENAI_ENDPOINT",
    "OPENAI_LOG",
    "OPENAI_ORG_ID",
    "OPENAI_ORGANIZATION",
    "OPENAI_PROJECT_ID",
    "OPENAI_PROJECT",
    "OPENAI_WEBHOOK_SECRET",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
    "SSLKEYLOGFILE",
)
FORBIDDEN_PYTHON_ROUTING_ENV_NAMES = ("PYTHONHOME", "PYTHONPATH")

ROOT_KEYS = ("schema_version", "artifact_id", "semantic_body_hash", "semantic_body")
MODEL_FACTORY_CHECK_KEYS = (
    "official_api_base_url_constant_exact",
    "factory_http_client_trust_env_false",
    "factory_constructor_uses_official_base_url",
    "factory_constructor_uses_explicit_http_client",
    "factory_constructor_mutation_is_retry_only",
    "factory_openai_uses_bounded_constructor_kwargs",
    "factory_has_single_openai_return",
    "factory_has_no_unrecognized_mutator_calls",
    "adapter_uses_production_factory_without_direct_openai_call",
)
RECEIPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "predecessor_binding",
    "approval",
    "authority",
    "evidence_boundary",
)
REMEDIATION_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "receipt_binding",
    "attempt_binding",
    "source_identity",
    "observation",
    "authority",
)
PRICING_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "receipt_binding",
    "attempt_binding",
    "source_identity",
    "official_pricing_evidence",
    "authority",
)
PREFLIGHT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "receipt_binding",
    "attempt_binding",
    "source_identity",
    "remediation_binding",
    "pricing_binding",
    "pricing_observed_at",
    "pricing_age_microseconds",
    "approved_docker_cli_bindings",
    "docker_readiness_snapshots",
    "docker_snapshots_stable",
    "sdk_credential_factory_observation",
    "observed_blockers",
    "authority",
)
ATTEMPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "phase",
    "receipt_binding",
    "source_identity",
    "loaded_module_bindings",
    "authority",
    "failure_boundary",
)
GATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "receipt_binding",
    "source_identity",
    "remediation_binding",
    "pricing_binding",
    "preflight_binding",
    "qualification",
    "authority",
    "next_gate",
)


class D127PreflightError(ContractError):
    """Raised when D-127 receipt or static prerequisites fail closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D127PreflightError(message)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any, *, label: str = "recorded_at") -> datetime:
    _require(isinstance(value, str), f"D-127 {label} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise D127PreflightError(f"D-127 {label} is invalid") from exc
    _require(parsed.tzinfo is not None, f"D-127 {label} is timezone-naive")
    return parsed.astimezone(UTC)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise D127PreflightError("D-127 repository root is unavailable") from exc
    _require(root.is_dir(), "D-127 repository root is not a directory")
    return root


def _is_linklike(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and is_junction():
        return True
    try:
        info = path.lstat()
    except OSError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(info.st_mode) or bool(reparse and attributes & reparse)


def _safe_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    _require(not relative.is_absolute(), "D-127 path must be repository-relative")
    _require(".." not in relative.parts, "D-127 path traversal is forbidden")
    _require(":" not in relative.as_posix(), "D-127 alternate-stream path is forbidden")
    current = root
    for part in (relative.parts if must_exist else relative.parent.parts):
        current = current / part
        _require(current.exists(), f"D-127 path parent is missing: {relative.as_posix()}")
        _require(not _is_linklike(current), f"D-127 path is linklike: {relative.as_posix()}")
    selected = root / relative
    if must_exist:
        _require(selected.is_file(), f"D-127 file is missing: {relative.as_posix()}")
        _require(not _is_linklike(selected), f"D-127 file is linklike: {relative.as_posix()}")
    else:
        _require(not selected.exists(), f"D-127 output already exists: {relative.as_posix()}")
    try:
        resolved = selected.resolve(strict=must_exist)
    except OSError as exc:
        raise D127PreflightError(f"D-127 path cannot be resolved: {relative.as_posix()}") from exc
    _require(resolved.is_relative_to(root), "D-127 path escapes repository")
    return selected


def _stable_read(root: Path, relative: Path) -> bytes:
    path = _safe_path(root, relative, must_exist=True)
    try:
        before = path.stat()
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            content = stream.read()
            after_open = os.fstat(stream.fileno())
        after = path.stat()
    except OSError as exc:
        raise D127PreflightError(f"D-127 cannot stably read {relative.as_posix()}") from exc

    def identity(value: os.stat_result) -> tuple[int, int, int, int]:
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)

    _require(
        identity(before) == identity(opened) == identity(after_open) == identity(after),
        f"D-127 file changed while reading: {relative.as_posix()}",
    )
    _require(len(content) == after.st_size, f"D-127 file size differs: {relative.as_posix()}")
    return content


def _stable_external_binding(path: Path) -> dict[str, Any]:
    _require(path.is_file(), "D-127 approved Docker CLI is missing")
    _require(not _is_linklike(path), "D-127 approved Docker CLI is linklike")
    try:
        resolved = path.resolve(strict=True)
        before = resolved.stat()
        _require(before.st_size == DOCKER_CLI_BYTES, "D-127 Docker CLI bytes differ")
        with resolved.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            content = stream.read(DOCKER_CLI_BYTES + 1)
            after_open = os.fstat(stream.fileno())
        after = resolved.stat()
    except OSError as exc:
        raise D127PreflightError("D-127 approved Docker CLI cannot be read") from exc
    def identity(value: os.stat_result) -> tuple[int, int, int, int]:
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)

    _require(
        identity(before) == identity(opened) == identity(after_open) == identity(after),
        "D-127 approved Docker CLI changed while reading",
    )
    return {
        "file_name": resolved.name,
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _write_new(root: Path, relative: Path, content: bytes) -> None:
    target = _safe_path(root, relative, must_exist=False)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        _require(temporary.read_bytes() == content, "D-127 temporary artifact bytes differ")
        try:
            os.link(temporary, target)
        except FileExistsError as exc:
            raise D127PreflightError(f"D-127 output collision: {relative.as_posix()}") from exc
        _require(_stable_read(root, relative) == content, "D-127 persisted artifact bytes differ")
    finally:
        with suppress(OSError):
            temporary.unlink()


def _pretty_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _envelope(body: dict[str, Any]) -> dict[str, Any]:
    return _artifact_envelope(RECEIPT_SCHEMA, "d127approval_", body)


def _artifact_envelope(schema: str, prefix: str, body: dict[str, Any]) -> dict[str, Any]:
    digest = sha256_text(canonical_json(body))
    return {
        "schema_version": schema,
        "artifact_id": f"{prefix}{digest.removeprefix('sha256:')}",
        "semantic_body_hash": digest,
        "semantic_body": body,
    }


def _load_artifact(
    root: Path,
    path: Path,
    *,
    schema: str,
    prefix: str,
) -> dict[str, Any]:
    raw = _stable_read(root, path)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D127PreflightError(f"D-127 artifact JSON is invalid: {path.as_posix()}") from exc
    _require(isinstance(payload, dict), "D-127 artifact root is not an object")
    _require(tuple(payload) == ROOT_KEYS, "D-127 artifact root fields differ")
    _require(payload.get("schema_version") == schema, "D-127 artifact schema differs")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-127 artifact body is not an object")
    expected = _artifact_envelope(schema, prefix, body)
    _require(canonical_json(payload) == canonical_json(expected), "D-127 artifact envelope differs")
    _require(_pretty_bytes(payload) == raw, "D-127 artifact bytes are noncanonical")
    return payload


def _artifact_binding(root: Path, path: Path) -> dict[str, Any]:
    raw = _stable_read(root, path)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D127PreflightError(f"D-127 artifact JSON is invalid: {path.as_posix()}") from exc
    _require(isinstance(payload, dict), "D-127 artifact root is not an object")
    return {
        "path": path.as_posix(),
        "artifact_id": payload.get("artifact_id"),
        "semantic_body_hash": payload.get("semantic_body_hash"),
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }


def _d126_binding(root: Path) -> dict[str, Any]:
    _require(
        d126.SEALED_HISTORICAL_GATE_ID == D126_GATE_ID
        and d126.SEALED_HISTORICAL_BODY_SHA256 == D126_BODY_SHA256
        and d126.SEALED_HISTORICAL_FILE_SHA256 == D126_FILE_SHA256
        and d126.SEALED_HISTORICAL_FILE_BYTES == D126_FILE_BYTES,
        "D-127 D-126 sealed constants differ",
    )
    result = d126.validate_d126_preflight_gate(repository=root, mode="sealed-historical")
    _require(result.get("gate_id") == D126_GATE_ID, "D-127 D-126 gate ID differs")
    _require(
        result.get("semantic_body_hash") == D126_BODY_SHA256,
        "D-127 D-126 body SHA differs",
    )
    _require(result.get("file_sha256") == D126_FILE_SHA256, "D-127 D-126 file SHA differs")
    _require(result.get("file_bytes") == D126_FILE_BYTES, "D-127 D-126 file bytes differ")
    raw = _stable_read(root, D126_GATE_PATH)
    _require(len(raw) == D126_FILE_BYTES, "D-127 D-126 artifact byte count differs")
    _require(sha256_bytes(raw) == D126_FILE_SHA256, "D-127 D-126 artifact file SHA differs")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D127PreflightError("D-127 D-126 artifact JSON is invalid") from exc
    _require(payload.get("artifact_id") == D126_GATE_ID, "D-127 D-126 artifact ID differs")
    _require(
        payload.get("semantic_body_hash") == D126_BODY_SHA256,
        "D-127 D-126 artifact body SHA differs",
    )
    _require(
        payload.get("semantic_body", {}).get("status") == D126_STATUS,
        "D-127 D-126 status differs",
    )
    return {
        "path": D126_GATE_PATH.as_posix(),
        "gate_id": D126_GATE_ID,
        "semantic_body_hash": D126_BODY_SHA256,
        "file_bytes": D126_FILE_BYTES,
        "file_sha256": D126_FILE_SHA256,
        "status": D126_STATUS,
        "artifact_mutated": False,
    }


def _receipt_body(root: Path, recorded_at: str) -> dict[str, Any]:
    _parse_time(recorded_at)
    return {
        "milestone": MILESTONE,
        "evidence_kind": "exact-d126-successor-blocker-remediation-no-call-user-approval-receipt",
        "recorded_at": recorded_at,
        "status": RECEIPT_STATUS,
        "predecessor_binding": _d126_binding(root),
        "approval": {
            "statement_code": "D126_SUCCESSOR_BLOCKER_REMEDIATION_NO_CALL_APPROVAL_KO_20260809_V1",
            "approved_scope": list(APPROVED_SCOPE),
            "explicitly_not_authorized": list(NOT_AUTHORIZED),
            "approved_docker_cli": {
                "version": DOCKER_CLI_VERSION,
                "file_bytes": DOCKER_CLI_BYTES,
                "file_sha256": DOCKER_CLI_SHA256,
            },
            "approved_exact_image_refs": list(DOCKER_IMAGE_REFS),
            "approval_is_self_attested": True,
            "approval_is_authenticated_or_signed": False,
        },
        "authority": {
            "production_client_remediation_authorized": True,
            "pricing_evidence_remediation_and_lookup_authorized": True,
            "local_source_test_doc_commit_authorized": True,
            "docker_desktop_linux_daemon_start_authorized": True,
            "exact_missing_image_pull_or_load_authorized": True,
            "read_only_no_call_preflight_authorized": True,
            "provider_evaluator_agent_execution_authorized": False,
            "runtime_memory_or_retrieval_authorized": False,
            "container_workload_authorized": False,
            "execution_hash_or_candidate_authorized": False,
            "cost_reservation_or_spend_authorized": False,
        },
        "evidence_boundary": {
            "receipt_does_not_prove_static_or_external_readiness": True,
            "receipt_does_not_authorize_execution": True,
            "receipt_creation_does_not_start_external_remediation_or_preflight": True,
            "external_path_requires_a_separate_explicit_cli_mode_after_static_checks": True,
            "daemon_start_approval_does_not_override_no_container_start_scope": True,
            "daemon_down_with_unverified_restart_state_is_deliberately_blocking": True,
            "receipt_output_is_append_only_new_or_exact-idempotent": True,
        },
    }


def _load_receipt(root: Path) -> dict[str, Any]:
    raw = _stable_read(root, RECEIPT_PATH)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D127PreflightError("D-127 receipt JSON is invalid") from exc
    _require(isinstance(payload, dict), "D-127 receipt root is not an object")
    _require(tuple(payload) == ROOT_KEYS, "D-127 receipt root fields differ")
    _require(payload.get("schema_version") == RECEIPT_SCHEMA, "D-127 receipt schema differs")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-127 receipt body is not an object")
    _require(tuple(body) == RECEIPT_BODY_KEYS, "D-127 receipt body fields differ")
    expected = _envelope(_receipt_body(root, body.get("recorded_at")))
    _require(canonical_json(payload) == canonical_json(expected), "D-127 receipt payload differs")
    _require(_pretty_bytes(payload) == raw, "D-127 receipt bytes are noncanonical")
    return payload


def create_d127_approval_receipt(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Create the canonical D-127 approval receipt without external calls."""

    root = _repo_root(repository)
    if (root / RECEIPT_PATH).exists():
        payload = _load_receipt(root)
    else:
        downstream = (
            REMEDIATION_ATTEMPT_PATH,
            REMEDIATION_PATH,
            PRICING_ATTEMPT_PATH,
            PRICING_PATH,
            PREFLIGHT_ATTEMPT_PATH,
            PREFLIGHT_PATH,
            GATE_PATH,
        )
        _require(
            not any((root / path).exists() for path in downstream),
            "D-127 downstream evidence exists without approval receipt",
        )
        payload = _envelope(_receipt_body(root, _now()))
        _write_new(root, RECEIPT_PATH, _pretty_bytes(payload))
        payload = _load_receipt(root)
    raw = _stable_read(root, RECEIPT_PATH)
    return {
        "status": RECEIPT_STATUS,
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }


def _git_environment() -> dict[str, str]:
    routed = sorted(
        name
        for name, value in os.environ.items()
        if name.upper().startswith("GIT_") and bool(value)
    )
    _require(not routed, "D-127 Git routing environment is present")
    environment = {
        name: value
        for name in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP")
        if (value := os.environ.get(name))
    }
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "NUL",
            "GIT_CONFIG_SYSTEM": "NUL",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def _git_executable() -> Path:
    selected = shutil.which("git")
    _require(bool(selected), "D-127 Git executable is unavailable")
    launcher = Path(str(selected))
    _require(launcher.is_absolute(), "D-127 Git executable path is not absolute")
    _require(
        launcher.is_file() and not _is_linklike(launcher),
        "D-127 Git launcher is linklike",
    )
    launcher = launcher.resolve(strict=True)
    if launcher.parent.name.casefold() == "cmd":
        engine = launcher.parent.parent / "mingw64/bin/git.exe"
    else:
        engine = launcher
    _require(engine.is_file() and not _is_linklike(engine), "D-127 Git engine is unavailable")
    return engine.resolve(strict=True)


def _git_command(root: Path, *args: str, text: bool) -> subprocess.CompletedProcess[Any]:
    executable = _git_executable()
    before = _bounded_external_file_binding(executable, maximum_bytes=8 * 1024 * 1024)
    result = subprocess.run(
        [
            str(executable),
            "-c",
            "core.fsmonitor=false",
            "-c",
            "commit.gpgSign=false",
            *args,
        ],
        cwd=root,
        capture_output=True,
        text=text,
        check=False,
        shell=False,
        env=_git_environment(),
    )
    after = _bounded_external_file_binding(executable, maximum_bytes=8 * 1024 * 1024)
    _require(before == after, "D-127 Git executable changed during command")
    return result


def _run_git(root: Path, *args: str) -> str:
    result = _git_command(root, *args, text=True)
    _require(result.returncode == 0, f"D-127 git command failed: {' '.join(args)}")
    return result.stdout.strip()


def _run_git_bytes(root: Path, *args: str) -> bytes:
    result = _git_command(root, *args, text=False)
    _require(result.returncode == 0, f"D-127 git command failed: {' '.join(args)}")
    return result.stdout


def _git_cli_observation(root: Path) -> dict[str, Any]:
    executable = _git_executable()
    before = _bounded_external_file_binding(executable, maximum_bytes=8 * 1024 * 1024)
    result = subprocess.run(
        [str(executable), "--version"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
        env=_git_environment(),
    )
    after = _bounded_external_file_binding(executable, maximum_bytes=8 * 1024 * 1024)
    _require(result.returncode == 0 and before == after, "D-127 Git identity probe failed")
    version = result.stdout.strip()
    _require(
        re.fullmatch(r"git version [0-9]+\.[0-9]+\.[0-9]+(?:\.[^\s]+)?", version)
        is not None,
        "D-127 Git version differs",
    )
    normalization = _git_command(
        root,
        "config",
        "--local",
        "--get",
        "core.autocrlf",
        text=True,
    )
    _require(
        normalization.returncode == 0 and normalization.stdout.strip().casefold() == "false",
        "D-127 checkout must bind repository-local core.autocrlf=false",
    )
    return {
        "resolved_path": str(executable),
        **before,
        "version": version,
        "actual_git_engine_invoked_directly": True,
        "repository_local_core_autocrlf": "false",
        "authenticated_or_vendor_signed_identity_claimed": False,
        "stable_during_observation": True,
        "minimal_secret_free_environment": True,
        "fsmonitor_disabled": True,
    }


def _allowed_output_status(paths: tuple[Path, ...]) -> set[str]:
    return {f"?? {path.as_posix()}" for path in paths}


def _source_identity(
    root: Path,
    *,
    allowed_outputs: tuple[Path, ...] = (),
) -> dict[str, Any]:
    git_before = _git_cli_observation(root)
    top_level = Path(_run_git(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    _require(top_level == root, "D-127 Git top-level differs from repository root")
    status = _run_git(root, "status", "--porcelain", "--untracked-files=all")
    status_lines = {line for line in status.splitlines() if line}
    _require(
        status_lines.issubset(_allowed_output_status(allowed_outputs)),
        "D-127 static prerequisites require clean committed source paths",
    )
    commit = _run_git(root, "rev-parse", "HEAD")
    tree = _run_git(root, "rev-parse", "HEAD^{tree}")
    parents = _run_git(root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    branch = _run_git(root, "branch", "--show-current") or None
    _require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "D-127 source commit differs")
    _require(re.fullmatch(r"[0-9a-f]{40}", tree) is not None, "D-127 source tree differs")
    _require(parents and parents[0] == commit, "D-127 source ancestry identity differs")
    _require(
        all(re.fullmatch(r"[0-9a-f]{40}", parent) is not None for parent in parents[1:]),
        "D-127 source parent identity differs",
    )
    git_after = _git_cli_observation(root)
    _require(git_before == git_after, "D-127 Git identity changed during source observation")
    return {
        "commit": commit,
        "tree": tree,
        "parents": parents[1:],
        "branch": branch,
        "source_paths_and_index_clean": True,
        "git_cli_observation": git_before,
    }


def _require_source_unchanged(
    root: Path,
    source: dict[str, Any],
    *,
    allowed_outputs: tuple[Path, ...] = (),
) -> None:
    _require(
        _git_cli_observation(root) == source["git_cli_observation"],
        "D-127 current Git engine differs from source identity",
    )
    status = _run_git(root, "status", "--porcelain", "--untracked-files=all")
    status_lines = {line for line in status.splitlines() if line}
    _require(
        status_lines.issubset(_allowed_output_status(allowed_outputs)),
        "D-127 source changed during static prerequisite checks",
    )
    _require(
        _run_git(root, "rev-parse", "HEAD") == source["commit"]
        and _run_git(root, "rev-parse", "HEAD^{tree}") == source["tree"],
        "D-127 committed source identity changed during static prerequisite checks",
    )
    _require(
        _git_cli_observation(root) == source["git_cli_observation"],
        "D-127 Git engine changed during source check",
    )


def _docker_cli_path() -> Path:
    _require(not os.environ.get("PATCHLOOP_DOCKER_CLI"), "D-127 Docker CLI override is forbidden")
    local_app_data = os.environ.get("LOCALAPPDATA")
    _require(bool(local_app_data), "D-127 LOCALAPPDATA is unavailable")
    return Path(str(local_app_data)) / "Programs/DockerDesktop/resources/bin/docker.exe"


def _approved_docker_cli_identity() -> dict[str, Any]:
    binding = _stable_external_binding(_docker_cli_path())
    _require(binding["file_name"].casefold() == "docker.exe", "D-127 Docker CLI name differs")
    _require(binding["file_bytes"] == DOCKER_CLI_BYTES, "D-127 Docker CLI bytes differ")
    _require(binding["file_sha256"] == DOCKER_CLI_SHA256, "D-127 Docker CLI SHA differs")
    return {
        **binding,
        "approved_version": DOCKER_CLI_VERSION,
        "version_bound_by_exact_approved_file_identity": True,
        "version_process_observation_performed": False,
    }


def _name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _model_factory_contract(root: Path) -> dict[str, bool]:
    source = _stable_read(root, Path("patchloop/agent/model.py")).decode("utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise D127PreflightError("D-127 production model source cannot be parsed") from exc
    constant_assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "OFFICIAL_API_BASE_URL"
            for target in node.targets
        )
    ]
    factories = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_openai_client"
    ]
    _require(len(factories) == 1, "D-127 production OpenAI client factory differs")
    factory = factories[0]
    official_constant = (
        len(constant_assignments) == 1
        and isinstance(constant_assignments[0].value, ast.Constant)
        and constant_assignments[0].value.value == OFFICIAL_API_BASE_URL
    )
    http_calls = [
        node
        for node in ast.walk(factory)
        if isinstance(node, ast.Call) and _name(node.func) == "httpx.Client"
    ]
    openai_calls = [
        node
        for node in ast.walk(factory)
        if isinstance(node, ast.Call) and _name(node.func) == "OpenAI"
    ]
    http_client_assignments = [
        node
        for node in ast.walk(factory)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "http_client"
            for target in node.targets
        )
    ]
    constructor_assignments: list[ast.Assign | ast.AnnAssign] = [
        node
        for node in ast.walk(factory)
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "constructor_kwargs"
                for target in node.targets
            )
        )
        or (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "constructor_kwargs"
        )
    ]
    http_client_trust_env_false = False
    if len(http_calls) == 1 and len(http_client_assignments) == 1:
        call = http_calls[0]
        keywords = {item.arg: item.value for item in call.keywords if item.arg is not None}
        trust = keywords.get("trust_env")
        http_client_trust_env_false = (
            not call.args
            and set(keywords) == {"trust_env"}
            and isinstance(trust, ast.Constant)
            and trust.value is False
            and http_client_assignments[0].value is call
        )
    constructor_has_official_base = False
    constructor_has_http_client = False
    if len(constructor_assignments) == 1 and isinstance(
        constructor_assignments[0].value, ast.Dict
    ):
        value = constructor_assignments[0].value
        items = {
            key.value: item
            for key, item in zip(value.keys, value.values, strict=True)
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        constructor_has_official_base = (
            set(items) == {"base_url", "http_client"}
            and isinstance(items["base_url"], ast.Name)
            and items["base_url"].id == "OFFICIAL_API_BASE_URL"
        )
        constructor_has_http_client = (
            isinstance(items["http_client"], ast.Name)
            and items["http_client"].id == "http_client"
        )
    allowed_dynamic_constructor_keys = all(
        isinstance(node.slice, ast.Constant) and node.slice.value == "max_retries"
        for node in ast.walk(factory)
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "constructor_kwargs"
        and isinstance(node.ctx, ast.Store)
    )
    openai_uses_constructor_kwargs = False
    factory_has_single_openai_return = False
    if len(openai_calls) == 1:
        call = openai_calls[0]
        all_returns = [node for node in ast.walk(factory) if isinstance(node, ast.Return)]
        returned_calls = [
            node.value
            for node in ast.walk(factory)
            if isinstance(node, ast.Return) and node.value is call
        ]
        openai_uses_constructor_kwargs = (
            not call.args
            and len(call.keywords) == 1
            and call.keywords[0].arg is None
            and isinstance(call.keywords[0].value, ast.Name)
            and call.keywords[0].value.id == "constructor_kwargs"
            and len(returned_calls) == 1
        )
        factory_has_single_openai_return = (
            len(all_returns) == 1 and all_returns[0].value is call
        )
    mutator_calls = [
        node
        for node in ast.walk(factory)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "constructor_kwargs"
    ]
    no_unrecognized_mutator_calls = not mutator_calls
    adapters = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "OpenAIResponsesAdapter"
    ]
    adapter_uses_factory = False
    if len(adapters) == 1:
        initializers = [
            node
            for node in adapters[0].body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        ]
        if len(initializers) == 1:
            calls = [node for node in ast.walk(initializers[0]) if isinstance(node, ast.Call)]
            factory_calls = [call for call in calls if _name(call.func) == "create_openai_client"]
            direct_openai_calls = [call for call in calls if _name(call.func) == "OpenAI"]
            adapter_uses_factory = len(factory_calls) == 1 and not direct_openai_calls
    checks = {
        "official_api_base_url_constant_exact": official_constant,
        "factory_http_client_trust_env_false": http_client_trust_env_false,
        "factory_constructor_uses_official_base_url": constructor_has_official_base,
        "factory_constructor_uses_explicit_http_client": constructor_has_http_client,
        "factory_constructor_mutation_is_retry_only": allowed_dynamic_constructor_keys,
        "factory_openai_uses_bounded_constructor_kwargs": openai_uses_constructor_kwargs,
        "factory_has_single_openai_return": factory_has_single_openai_return,
        "factory_has_no_unrecognized_mutator_calls": no_unrecognized_mutator_calls,
        "adapter_uses_production_factory_without_direct_openai_call": adapter_uses_factory,
    }
    _require(tuple(checks) == MODEL_FACTORY_CHECK_KEYS, "D-127 model factory check fields differ")
    _require(all(checks.values()), "D-127 production OpenAI client factory contract differs")
    return checks


def _check_static_prerequisites(
    root: Path,
    *,
    allowed_outputs: tuple[Path, ...],
) -> dict[str, Any]:
    receipt = _load_receipt(root)
    source = _source_identity(root, allowed_outputs=allowed_outputs)
    api_key_present = bool(os.environ.get("OPENAI_API_KEY"))
    _require(api_key_present, "D-127 OPENAI_API_KEY presence is required")
    routing_presence = {name: bool(os.environ.get(name)) for name in FORBIDDEN_ROUTING_ENV_NAMES}
    _require(
        not any(routing_presence.values()),
        "D-127 alternate OpenAI, proxy, or TLS routing environment is present",
    )
    python_routing_presence = {
        name: bool(os.environ.get(name)) for name in FORBIDDEN_PYTHON_ROUTING_ENV_NAMES
    }
    _require(
        not any(python_routing_presence.values()),
        "D-127 Python module routing environment is present",
    )
    docker_cli = _approved_docker_cli_identity()
    factory = _model_factory_contract(root)
    _require_source_unchanged(root, source, allowed_outputs=allowed_outputs)
    return {
        "status": STATIC_READY_STATUS,
        "receipt": {
            "artifact_id": receipt["artifact_id"],
            "semantic_body_hash": receipt["semantic_body_hash"],
        },
        "source": source,
        "credential": {
            "name": "OPENAI_API_KEY",
            "present": True,
            "value_hash_length_or_prefix_persisted": False,
        },
        "alternate_routing_environment_presence": routing_presence,
        "alternate_routing_environment_values_persisted": False,
        "python_routing_environment_presence": python_routing_presence,
        "python_routing_environment_values_persisted": False,
        "docker_cli": docker_cli,
        "approved_exact_image_refs": list(DOCKER_IMAGE_REFS),
        "production_model_factory_checks": factory,
        "external_activity": {
            "network_call_count": 0,
            "docker_cli_invocation_count": 0,
            "docker_daemon_call_count": 0,
            "docker_workload_or_mutating_call_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
        "external_remediation_or_repeated_preflight_implemented": True,
        "external_activity_started": False,
        "artifact_created_by_static_check": False,
    }


def check_d127_static_prerequisites(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Require all zero-call prerequisites and return an in-memory observation."""

    root = _repo_root(repository)
    result = _check_static_prerequisites(root, allowed_outputs=())
    _require_receipt_tracked_at_head(root, source_commit=result["source"]["commit"])
    return result


def _validate_source_identity(source: Any, *, root: Path | None = None) -> None:
    _require(isinstance(source, dict), "D-127 source identity is not an object")
    _require(
        tuple(source)
        == (
            "commit",
            "tree",
            "parents",
            "branch",
            "source_paths_and_index_clean",
            "git_cli_observation",
        ),
        "D-127 source identity fields differ",
    )
    _require(
        re.fullmatch(r"[0-9a-f]{40}", source["commit"]) is not None,
        "D-127 source commit differs",
    )
    _require(
        re.fullmatch(r"[0-9a-f]{40}", source["tree"]) is not None,
        "D-127 source tree differs",
    )
    _require(
        isinstance(source["parents"], list)
        and all(
            isinstance(parent, str) and re.fullmatch(r"[0-9a-f]{40}", parent) is not None
            for parent in source["parents"]
        ),
        "D-127 source parents differ",
    )
    _require(
        source["branch"] is None or isinstance(source["branch"], str),
        "D-127 source branch differs",
    )
    _require(source["source_paths_and_index_clean"] is True, "D-127 source clean claim differs")
    git = source["git_cli_observation"]
    _require(
        isinstance(git, dict)
        and tuple(git)
        == (
            "resolved_path",
            "file_name",
            "file_bytes",
            "file_sha256",
            "linklike",
            "version",
            "actual_git_engine_invoked_directly",
            "repository_local_core_autocrlf",
            "authenticated_or_vendor_signed_identity_claimed",
            "stable_during_observation",
            "minimal_secret_free_environment",
            "fsmonitor_disabled",
        )
        and isinstance(git["resolved_path"], str)
        and Path(git["resolved_path"]).is_absolute()
        and git["file_name"].casefold() == "git.exe"
        and type(git["file_bytes"]) is int
        and git["file_bytes"] > 0
        and re.fullmatch(r"sha256:[0-9a-f]{64}", git["file_sha256"]) is not None
        and git["linklike"] is False
        and isinstance(git["version"], str)
        and git["actual_git_engine_invoked_directly"] is True
        and git["repository_local_core_autocrlf"] == "false"
        and git["authenticated_or_vendor_signed_identity_claimed"] is False
        and git["stable_during_observation"] is True
        and git["minimal_secret_free_environment"] is True
        and git["fsmonitor_disabled"] is True,
        "D-127 Git observation differs",
    )
    if root is not None:
        git_before = _git_cli_observation(root)
        _require(git_before == git, "D-127 current Git engine differs from source identity")
        _require(
            _run_git(root, "rev-parse", f"{source['commit']}^{{tree}}") == source["tree"],
            "D-127 committed source tree replay differs",
        )
        ancestry = _run_git(
            root,
            "rev-list",
            "--parents",
            "-n",
            "1",
            source["commit"],
        ).split()
        _require(
            ancestry == [source["commit"], *source["parents"]],
            "D-127 committed source ancestry replay differs",
        )
        _require(
            _git_cli_observation(root) == git_before,
            "D-127 Git engine changed during source replay",
        )


def _require_current_source(
    root: Path,
    source: dict[str, Any],
    *,
    allowed_outputs: tuple[Path, ...],
) -> None:
    _validate_source_identity(source, root=root)
    current = _source_identity(root, allowed_outputs=allowed_outputs)
    _require(canonical_json(current) == canonical_json(source), "D-127 source identity drifted")


def _locked_openai_version(root: Path) -> str | None:
    return _parse_locked_openai_version(_stable_read(root, Path("uv.lock")))


def _parse_locked_openai_version(raw: bytes) -> str | None:
    text = raw.decode("utf-8")
    match = re.search(r'\[\[package\]\]\s+name = "openai"\s+version = "([^"]+)"', text)
    return match.group(1) if match else None


def _committed_locked_openai_version(root: Path, source_commit: str) -> str | None:
    raw = _run_git_bytes(root, "cat-file", "blob", f"{source_commit}:uv.lock")
    return _parse_locked_openai_version(raw)


def _synthetic_sdk_probe(installed_version: str | None) -> dict[str, Any]:
    if installed_version is None:
        return {"passed": False, "transport_attempt_count": 0}
    attempts = 0
    try:
        import httpx
        from openai import OpenAI

        def reject_transport(_request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            raise RuntimeError("D-127 synthetic SDK probe attempted transport")

        transport = httpx.Client(
            trust_env=False,
            transport=httpx.MockTransport(reject_transport),
        )
        client = OpenAI(
            api_key="d127-nonsecret-no-call-placeholder",
            base_url=OFFICIAL_API_BASE_URL,
            max_retries=0,
            http_client=transport,
        )
        passed = (
            str(client.base_url).rstrip("/") == OFFICIAL_API_BASE_URL
            and client.max_retries == 0
        )
        client.close()
        return {"passed": passed and attempts == 0, "transport_attempt_count": attempts}
    except Exception:
        return {"passed": False, "transport_attempt_count": attempts}


def _bounded_external_file_binding(path: Path, *, maximum_bytes: int) -> dict[str, Any]:
    _require(path.is_file() and not _is_linklike(path), "D-127 external file is unavailable")
    try:
        resolved = path.resolve(strict=True)
        before = resolved.stat()
        _require(0 < before.st_size <= maximum_bytes, "D-127 external file size is outside bound")
        with resolved.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            raw = stream.read(maximum_bytes + 1)
            after_open = os.fstat(stream.fileno())
        after = resolved.stat()
    except OSError as exc:
        raise D127PreflightError("D-127 external file cannot be read") from exc

    def identity(value: os.stat_result) -> tuple[int, int, int, int]:
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)

    _require(
        identity(before) == identity(opened) == identity(after_open) == identity(after),
        "D-127 external file changed while reading",
    )
    _require(len(raw) == before.st_size, "D-127 external file byte count differs")
    return {
        "file_name": resolved.name,
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "linklike": False,
    }


def _sdk_observation(
    root: Path,
    source: dict[str, Any],
    factory_checks: dict[str, bool],
) -> dict[str, Any]:
    try:
        installed = importlib.metadata.version("openai")
    except importlib.metadata.PackageNotFoundError:
        installed = None
    locked = _locked_openai_version(root)
    routing_presence = {
        name: bool(os.environ.get(name)) for name in FORBIDDEN_ROUTING_ENV_NAMES
    }
    synthetic_probe = _synthetic_sdk_probe(installed)
    checks = {
        "python_is_repository_venv": Path(sys.executable).resolve().is_relative_to(root / ".venv"),
        "openai_sdk_installed": installed is not None,
        "openai_sdk_matches_lock": installed is not None and installed == locked,
        "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
        "alternate_routing_environment_absent": not any(routing_presence.values()),
        "production_model_factory_contract_passed": all(factory_checks.values()),
        "synthetic_official_endpoint_no_call_probe_passed": synthetic_probe["passed"],
    }
    python_path = Path(sys.executable).resolve(strict=True)
    return {
        "python_version": ".".join(str(value) for value in sys.version_info[:3]),
        "python_executable_binding": {
            "resolved_path": str(python_path),
            **_bounded_external_file_binding(
                python_path,
                maximum_bytes=64 * 1024 * 1024,
            ),
        },
        "uv_lock_binding": _committed_file_binding(
            root,
            source_commit=source["commit"],
            relative=Path("uv.lock"),
        ),
        "openai_sdk_installed_version": installed,
        "openai_sdk_locked_version": locked,
        "credential": {
            "name": "OPENAI_API_KEY",
            "present": checks["openai_api_key_present"],
            "value_hash_length_or_prefix_persisted": False,
        },
        "alternate_routing_environment_presence": routing_presence,
        "alternate_routing_environment_values_persisted": False,
        "official_endpoint": OFFICIAL_API_BASE_URL,
        "production_model_factory_checks": factory_checks,
        "synthetic_endpoint_probe": synthetic_probe,
        "checks": checks,
        "network_call_count": 0,
        "passed": all(checks.values()),
    }


def _validate_sdk_observation(
    root: Path,
    value: Any,
    *,
    source: dict[str, Any],
) -> None:
    expected_keys = (
        "python_version",
        "python_executable_binding",
        "uv_lock_binding",
        "openai_sdk_installed_version",
        "openai_sdk_locked_version",
        "credential",
        "alternate_routing_environment_presence",
        "alternate_routing_environment_values_persisted",
        "official_endpoint",
        "production_model_factory_checks",
        "synthetic_endpoint_probe",
        "checks",
        "network_call_count",
        "passed",
    )
    _require(isinstance(value, dict) and tuple(value) == expected_keys, "D-127 SDK fields differ")
    _require(
        isinstance(value["python_version"], str)
        and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value["python_version"]) is not None,
        "D-127 SDK Python version differs",
    )
    python_binding = value["python_executable_binding"]
    _require(
        isinstance(python_binding, dict)
        and tuple(python_binding)
        == ("resolved_path", "file_name", "file_bytes", "file_sha256", "linklike")
        and isinstance(python_binding["resolved_path"], str)
        and Path(python_binding["resolved_path"]).is_absolute()
        and type(python_binding["file_bytes"]) is int
        and python_binding["file_bytes"] > 0
        and re.fullmatch(r"sha256:[0-9a-f]{64}", python_binding["file_sha256"]) is not None
        and python_binding["linklike"] is False,
        "D-127 SDK Python executable binding differs",
    )
    expected_lock = _committed_file_binding(
        root,
        source_commit=source["commit"],
        relative=Path("uv.lock"),
    )
    _require(value["uv_lock_binding"] == expected_lock, "D-127 SDK lock binding differs")
    locked = _committed_locked_openai_version(root, source["commit"])
    installed = value["openai_sdk_installed_version"]
    _require(
        (installed is None or isinstance(installed, str))
        and isinstance(locked, str)
        and value["openai_sdk_locked_version"] == locked,
        "D-127 SDK version binding differs",
    )
    credential = value["credential"]
    _require(
        isinstance(credential, dict)
        and tuple(credential)
        == ("name", "present", "value_hash_length_or_prefix_persisted")
        and credential["name"] == "OPENAI_API_KEY"
        and type(credential["present"]) is bool
        and credential["value_hash_length_or_prefix_persisted"] is False,
        "D-127 SDK credential boundary differs",
    )
    routing = value["alternate_routing_environment_presence"]
    _require(
        isinstance(routing, dict)
        and tuple(routing) == FORBIDDEN_ROUTING_ENV_NAMES
        and all(type(item) is bool for item in routing.values()),
        "D-127 SDK routing boundary differs",
    )
    _require(
        value["alternate_routing_environment_values_persisted"] is False,
        "D-127 SDK routing persistence differs",
    )
    _require(value["official_endpoint"] == OFFICIAL_API_BASE_URL, "D-127 SDK endpoint differs")
    factory = value["production_model_factory_checks"]
    _require(
        isinstance(factory, dict)
        and tuple(factory) == MODEL_FACTORY_CHECK_KEYS
        and all(item is True for item in factory.values())
        and factory == _model_factory_contract(root),
        "D-127 stored model factory checks differ",
    )
    _require(
        isinstance(value["synthetic_endpoint_probe"], dict)
        and tuple(value["synthetic_endpoint_probe"])
        == ("passed", "transport_attempt_count")
        and type(value["synthetic_endpoint_probe"]["passed"]) is bool
        and type(value["synthetic_endpoint_probe"]["transport_attempt_count"]) is int
        and value["synthetic_endpoint_probe"]["transport_attempt_count"] >= 0,
        "D-127 synthetic SDK probe boundary differs",
    )
    checks = value["checks"]
    expected_check_keys = (
        "python_is_repository_venv",
        "openai_sdk_installed",
        "openai_sdk_matches_lock",
        "openai_api_key_present",
        "alternate_routing_environment_absent",
        "production_model_factory_contract_passed",
        "synthetic_official_endpoint_no_call_probe_passed",
    )
    expected_checks = {
        "python_is_repository_venv": Path(
            python_binding["resolved_path"]
        ).is_relative_to(root / ".venv"),
        "openai_sdk_installed": installed is not None,
        "openai_sdk_matches_lock": installed is not None and installed == locked,
        "openai_api_key_present": credential["present"],
        "alternate_routing_environment_absent": not any(routing.values()),
        "production_model_factory_contract_passed": all(factory.values()),
        "synthetic_official_endpoint_no_call_probe_passed": (
            value["synthetic_endpoint_probe"]["passed"]
            and value["synthetic_endpoint_probe"]["transport_attempt_count"] == 0
        ),
    }
    _require(tuple(expected_checks) == expected_check_keys, "D-127 SDK check fields differ")
    _require(checks == expected_checks, "D-127 SDK check result differs")
    _require(value["network_call_count"] == 0, "D-127 SDK network count differs")
    _require(value["passed"] is all(expected_checks.values()), "D-127 SDK result differs")


def _require_current_sdk_matches_artifact(
    root: Path,
    source: dict[str, Any],
    value: dict[str, Any],
) -> None:
    _validate_sdk_observation(root, value, source=source)
    try:
        installed = importlib.metadata.version("openai")
    except importlib.metadata.PackageNotFoundError:
        installed = None
    _require(
        installed == value["openai_sdk_installed_version"]
        and _locked_openai_version(root) == value["openai_sdk_locked_version"],
        "D-127 current SDK version differs",
    )
    _require(
        bool(os.environ.get("OPENAI_API_KEY")),
        "D-127 current OPENAI_API_KEY presence is required",
    )
    _require(
        not any(os.environ.get(name) for name in FORBIDDEN_ROUTING_ENV_NAMES),
        "D-127 current alternate routing environment is present",
    )
    _require(
        not any(os.environ.get(name) for name in FORBIDDEN_PYTHON_ROUTING_ENV_NAMES),
        "D-127 current Python routing environment is present",
    )
    _require(
        Path(sys.executable).resolve().is_relative_to(root / ".venv"),
        "D-127 current Python executable is outside repository venv",
    )
    _require(
        {
            "resolved_path": str(Path(sys.executable).resolve(strict=True)),
            **_bounded_external_file_binding(
                Path(sys.executable), maximum_bytes=64 * 1024 * 1024
            ),
        }
        == value["python_executable_binding"],
        "D-127 current Python executable differs",
    )
    _require(
        _model_factory_contract(root) == value["production_model_factory_checks"],
        "D-127 current production factory differs",
    )


def _authority_zero_boundary() -> dict[str, Any]:
    return {
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "agent_runs_started": 0,
        "runtime_memory_injection_count": 0,
        "retrieval_call_count": 0,
        "container_create_start_run_exec_count": 0,
        "execution_hash_created": False,
        "execution_candidate_created": False,
        "cost_reserved_or_spent_usd": "0",
    }


def _write_artifact(
    root: Path,
    path: Path,
    *,
    schema: str,
    prefix: str,
    body: dict[str, Any],
) -> None:
    _write_new(root, path, _pretty_bytes(_artifact_envelope(schema, prefix, body)))


_PHASE_PATHS = {
    "docker-remediation": (REMEDIATION_ATTEMPT_PATH, REMEDIATION_PATH),
    "official-pricing-capture": (PRICING_ATTEMPT_PATH, PRICING_PATH),
    "read-only-no-call-preflight": (PREFLIGHT_ATTEMPT_PATH, PREFLIGHT_PATH),
}
_PHASE_ACTIONS = {
    "docker-remediation": [
        "start-local-docker-desktop-only-if-container-auto-restart-risk-is-proven-absent",
        "pull-only-two-exact-digest-pinned-images-if-missing",
        "read-local-docker-daemon-and-exact-image-metadata",
    ],
    "official-pricing-capture": [
        "perform-at-most-four-unauthenticated-official-doc-get-requests",
        "retain-at-most-128000-decoded-entity-bytes-for-replay",
    ],
    "read-only-no-call-preflight": [
        "perform-exactly-two-three-command-read-only-local-docker-snapshots",
        "construct-local-sdk-client-against-rejecting-mock-transport",
    ],
}
_LOADED_MODULE_PATHS = (
    ("d127-orchestrator", Path("patchloop/evals/d127_d126_successor_no_call_preflight.py")),
    ("d127-docker-remediation", Path("patchloop/evals/d127_docker_remediation.py")),
    ("d127-pricing-capture", Path("patchloop/evals/d127_pricing_capture.py")),
    (
        "d126-predecessor-validator",
        Path("patchloop/evals/d126_clean_source_pricing_no_call_preflight.py"),
    ),
)


def _loaded_module_files() -> dict[str, Path]:
    return {
        "d127-orchestrator": Path(__file__),
        "d127-docker-remediation": Path(str(docker_remediation.__file__)),
        "d127-pricing-capture": Path(str(pricing_capture.__file__)),
        "d126-predecessor-validator": Path(str(d126.__file__)),
    }


def _committed_file_binding(
    root: Path,
    *,
    source_commit: str,
    relative: Path,
) -> dict[str, Any]:
    raw = _stable_read(root, relative)
    object_spec = f"{source_commit}:{relative.as_posix()}"
    committed = _run_git_bytes(root, "cat-file", "blob", object_spec)
    _require(raw == committed, f"D-127 committed bytes differ: {relative.as_posix()}")
    blob_oid = _run_git(root, "rev-parse", object_spec)
    return {
        "path": relative.as_posix(),
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "source_blob_oid": blob_oid,
    }


def _loaded_module_bindings(root: Path, *, source_commit: str) -> list[dict[str, Any]]:
    actual = _loaded_module_files()
    bindings: list[dict[str, Any]] = []
    for role, relative in _LOADED_MODULE_PATHS:
        expected = (root / relative).resolve(strict=True)
        _require(actual[role].resolve(strict=True) == expected, "D-127 loaded module path differs")
        binding = _committed_file_binding(
            root,
            source_commit=source_commit,
            relative=relative,
        )
        bindings.append(
            {
                "role": role,
                **binding,
            }
        )
    return bindings


def _validate_loaded_module_bindings(
    value: Any,
    *,
    root: Path | None = None,
    source_commit: str | None = None,
) -> None:
    _require(isinstance(value, list), "D-127 module bindings are not a list")
    _require(
        [(row.get("role"), row.get("path")) for row in value]
        == [(role, path.as_posix()) for role, path in _LOADED_MODULE_PATHS],
        "D-127 loaded module binding roles differ",
    )
    for row in value:
        _require(
            tuple(row) == ("role", "path", "file_bytes", "file_sha256", "source_blob_oid"),
            "D-127 loaded module binding fields differ",
        )
        _require(
            type(row["file_bytes"]) is int and row["file_bytes"] > 0,
            "D-127 loaded module byte count differs",
        )
        _require(
            re.fullmatch(r"sha256:[0-9a-f]{64}", row["file_sha256"]) is not None,
            "D-127 loaded module SHA differs",
        )
        _require(
            re.fullmatch(r"[0-9a-f]{40,64}", row["source_blob_oid"]) is not None,
            "D-127 loaded module Git blob differs",
        )
    if root is not None or source_commit is not None:
        _require(
            root is not None and source_commit is not None,
            "D-127 module replay inputs differ",
        )
        current = _loaded_module_bindings(root, source_commit=source_commit)
        _require(
            canonical_json(value) == canonical_json(current),
            "D-127 loaded module replay differs",
        )


def _require_receipt_tracked_at_head(root: Path, *, source_commit: str) -> None:
    relative = RECEIPT_PATH.as_posix()
    tracked = _run_git(root, "ls-files", "--error-unmatch", "--", relative)
    _require(tracked.replace("\\", "/") == relative, "D-127 receipt is not tracked")
    _committed_file_binding(
        root,
        source_commit=source_commit,
        relative=RECEIPT_PATH,
    )


def _attempt_body(
    *,
    phase: str,
    receipt_binding: dict[str, Any],
    source: dict[str, Any],
    module_bindings: list[dict[str, Any]],
    recorded_at: str,
) -> dict[str, Any]:
    _require(phase in _PHASE_PATHS, "D-127 external phase differs")
    _parse_time(recorded_at, label=f"{phase} attempt recorded_at")
    _validate_source_identity(source)
    _validate_loaded_module_bindings(module_bindings)
    return {
        "milestone": MILESTONE,
        "evidence_kind": "append-only-external-phase-attempt-intent",
        "recorded_at": recorded_at,
        "status": f"D127_{phase.replace('-', '_').upper()}_ATTEMPT_INTENT_RECORDED",
        "phase": phase,
        "receipt_binding": receipt_binding,
        "source_identity": source,
        "loaded_module_bindings": module_bindings,
        "authority": {
            "authorized_actions": _PHASE_ACTIONS[phase],
            "provider_evaluator_agent_execution_authorized": False,
            "runtime_memory_or_retrieval_authorized": False,
            "container_create_start_run_exec_authorized": False,
            "execution_hash_or_candidate_authorized": False,
            "cost_reservation_or_spend_authorized": False,
        },
        "failure_boundary": {
            "intent_is_written_before_first_phase_external_action": True,
            "missing_terminal_artifact_does_not_imply_zero_activity": True,
            "orphaned_attempt_must_not_be_retried_without_separate_exact_approval": True,
            "actual_counts_are_recorded_only_in_the_bound_terminal_artifact": True,
        },
    }


def _validate_attempt_artifact(root: Path, phase: str) -> dict[str, Any]:
    receipt = _load_receipt(root)
    path, _terminal = _PHASE_PATHS[phase]
    prefix = f"d127{phase.replace('-', '')}attempt_"
    payload = _load_artifact(root, path, schema=ATTEMPT_SCHEMA, prefix=prefix)
    body = payload["semantic_body"]
    _require(tuple(body) == ATTEMPT_BODY_KEYS, "D-127 attempt body fields differ")
    _require(
        body["receipt_binding"] == _artifact_binding(root, RECEIPT_PATH)
        and body["receipt_binding"]["artifact_id"] == receipt["artifact_id"],
        "D-127 attempt receipt binding differs",
    )
    expected = _attempt_body(
        phase=phase,
        receipt_binding=body["receipt_binding"],
        source=body["source_identity"],
        module_bindings=body["loaded_module_bindings"],
        recorded_at=body["recorded_at"],
    )
    _require(canonical_json(body) == canonical_json(expected), "D-127 attempt body differs")
    _validate_source_identity(body["source_identity"], root=root)
    _require(
        _parse_time(receipt["semantic_body"]["recorded_at"], label="receipt recorded_at")
        <= _parse_time(body["recorded_at"], label="attempt recorded_at"),
        "D-127 attempt chronology differs",
    )
    _validate_loaded_module_bindings(
        body["loaded_module_bindings"],
        root=root,
        source_commit=body["source_identity"]["commit"],
    )
    return payload


def _create_attempt_artifact(
    root: Path,
    *,
    phase: str,
    source: dict[str, Any],
    module_bindings: list[dict[str, Any]],
) -> dict[str, Any]:
    path, terminal = _PHASE_PATHS[phase]
    _require(not (root / path).exists(), f"D-127 {phase} attempt already exists")
    _require(
        not (root / terminal).exists(),
        f"D-127 {phase} terminal exists without attempt",
    )
    body = _attempt_body(
        phase=phase,
        receipt_binding=_artifact_binding(root, RECEIPT_PATH),
        source=source,
        module_bindings=module_bindings,
        recorded_at=_now(),
    )
    _write_artifact(
        root,
        path,
        schema=ATTEMPT_SCHEMA,
        prefix=f"d127{phase.replace('-', '')}attempt_",
        body=body,
    )
    return _validate_attempt_artifact(root, phase)


def _require_attempt_unchanged(
    root: Path,
    *,
    phase: str,
    expected: dict[str, Any],
) -> dict[str, Any]:
    current = _validate_attempt_artifact(root, phase)
    _require(
        canonical_json(current) == canonical_json(expected),
        f"D-127 {phase} attempt changed after intent persistence",
    )
    attempt_path, _terminal_path = _PHASE_PATHS[phase]
    _require(
        _artifact_binding(root, attempt_path)["artifact_id"] == expected["artifact_id"],
        f"D-127 {phase} attempt binding changed",
    )
    return current


def _remediation_body(
    *,
    receipt_binding: dict[str, Any],
    attempt_binding: dict[str, Any],
    source: dict[str, Any],
    observation: dict[str, Any],
    recorded_at: str,
) -> dict[str, Any]:
    _parse_time(recorded_at, label="remediation recorded_at")
    docker_remediation.validate_docker_remediation_observation(observation)
    _require(
        observation["desktop_start_count"] == 0,
        "D-127 Docker remediation crossed the incidental-container-start boundary",
    )
    status = REMEDIATION_READY_STATUS if observation["passed"] else REMEDIATION_BLOCKED_STATUS
    return {
        "milestone": MILESTONE,
        "evidence_kind": "exact-authorized-local-docker-remediation-observation",
        "recorded_at": recorded_at,
        "status": status,
        "receipt_binding": receipt_binding,
        "attempt_binding": attempt_binding,
        "source_identity": source,
        "observation": observation,
        "authority": {
            "docker_desktop_start_count": observation["desktop_start_count"],
            "docker_image_store_mutation_count": observation["image_store_mutation_count"],
            "docker_cli_command_count": observation["docker_cli_command_count"],
            "exact_authorized_images_only": observation["exact_authorized_images"]
            == list(DOCKER_IMAGE_REFS),
            "no_incidental_container_start_boundary_preserved": observation[
                "desktop_start_count"
            ]
            == 0,
            **_authority_zero_boundary(),
        },
    }


def _validate_remediation_artifact(root: Path) -> dict[str, Any]:
    receipt = _load_receipt(root)
    attempt = _validate_attempt_artifact(root, "docker-remediation")
    payload = _load_artifact(
        root,
        REMEDIATION_PATH,
        schema=REMEDIATION_SCHEMA,
        prefix="d127remediation_",
    )
    body = payload["semantic_body"]
    _require(tuple(body) == REMEDIATION_BODY_KEYS, "D-127 remediation body fields differ")
    _require(
        body["receipt_binding"] == _artifact_binding(root, RECEIPT_PATH),
        "D-127 remediation receipt binding differs",
    )
    _require(
        body["receipt_binding"]["artifact_id"] == receipt["artifact_id"],
        "D-127 remediation receipt ID differs",
    )
    _require(
        body["attempt_binding"] == _artifact_binding(root, REMEDIATION_ATTEMPT_PATH)
        and body["attempt_binding"]["artifact_id"] == attempt["artifact_id"],
        "D-127 remediation attempt binding differs",
    )
    _validate_source_identity(body["source_identity"], root=root)
    _require(
        canonical_json(body["source_identity"])
        == canonical_json(attempt["semantic_body"]["source_identity"]),
        "D-127 remediation attempt source differs",
    )
    _require(
        _parse_time(attempt["semantic_body"]["recorded_at"], label="remediation attempt")
        <= _parse_time(body["recorded_at"], label="remediation recorded_at"),
        "D-127 remediation chronology differs",
    )
    expected = _remediation_body(
        receipt_binding=body["receipt_binding"],
        attempt_binding=body["attempt_binding"],
        source=body["source_identity"],
        observation=body["observation"],
        recorded_at=body["recorded_at"],
    )
    _require(canonical_json(body) == canonical_json(expected), "D-127 remediation body differs")
    return payload


def _pricing_body(
    *,
    receipt_binding: dict[str, Any],
    attempt_binding: dict[str, Any],
    source: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    pricing_capture.validate_official_pricing_evidence(evidence)
    observed_at = evidence["observed_at"]
    _parse_time(observed_at, label="pricing observed_at")
    return {
        "milestone": MILESTONE,
        "evidence_kind": "bounded-replayable-official-pricing-decoded-entity",
        "recorded_at": observed_at,
        "status": PRICING_CAPTURED_STATUS,
        "receipt_binding": receipt_binding,
        "attempt_binding": attempt_binding,
        "source_identity": source,
        "official_pricing_evidence": evidence,
        "authority": {
            "official_public_get_request_count": evidence["public_get_request_count"],
            "decoded_entity_retained_for_replay": True,
            "decoded_entity_max_bytes": pricing_capture.MAX_DECODED_ENTITY_BYTES,
            "wire_bytes_retained": False,
            "request_auth_or_cookie_sent": False,
            **_authority_zero_boundary(),
        },
    }


def _validate_pricing_artifact(root: Path) -> dict[str, Any]:
    receipt = _load_receipt(root)
    attempt = _validate_attempt_artifact(root, "official-pricing-capture")
    remediation = _validate_remediation_artifact(root)
    payload = _load_artifact(
        root,
        PRICING_PATH,
        schema=PRICING_SCHEMA,
        prefix="d127pricing_",
    )
    body = payload["semantic_body"]
    _require(tuple(body) == PRICING_BODY_KEYS, "D-127 pricing body fields differ")
    _require(
        body["receipt_binding"] == _artifact_binding(root, RECEIPT_PATH),
        "D-127 pricing receipt binding differs",
    )
    _require(
        body["receipt_binding"]["artifact_id"] == receipt["artifact_id"],
        "D-127 pricing receipt ID differs",
    )
    _require(
        body["attempt_binding"] == _artifact_binding(root, PRICING_ATTEMPT_PATH)
        and body["attempt_binding"]["artifact_id"] == attempt["artifact_id"],
        "D-127 pricing attempt binding differs",
    )
    _validate_source_identity(body["source_identity"], root=root)
    _require(
        canonical_json(body["source_identity"])
        == canonical_json(attempt["semantic_body"]["source_identity"]),
        "D-127 pricing attempt source differs",
    )
    _require(
        canonical_json(body["source_identity"])
        == canonical_json(remediation["semantic_body"]["source_identity"]),
        "D-127 pricing predecessor source differs",
    )
    _require(
        _parse_time(remediation["semantic_body"]["recorded_at"], label="remediation")
        <= _parse_time(attempt["semantic_body"]["recorded_at"], label="pricing attempt"),
        "D-127 pricing attempt predates remediation terminal",
    )
    _require(
        _parse_time(attempt["semantic_body"]["recorded_at"], label="pricing attempt")
        <= _parse_time(body["recorded_at"], label="pricing recorded_at"),
        "D-127 pricing chronology differs",
    )
    expected = _pricing_body(
        receipt_binding=body["receipt_binding"],
        attempt_binding=body["attempt_binding"],
        source=body["source_identity"],
        evidence=body["official_pricing_evidence"],
    )
    _require(canonical_json(body) == canonical_json(expected), "D-127 pricing body differs")
    return payload


def _pricing_age_microseconds(observed_at: str, recorded_at: str) -> int:
    observed = _parse_time(observed_at, label="pricing observed_at")
    recorded = _parse_time(recorded_at, label="preflight recorded_at")
    delta = recorded - observed
    return (
        delta.days * 86_400 * 1_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )


def _preflight_blockers(
    *,
    remediation_observation: dict[str, Any],
    pricing_age_microseconds: int,
    snapshots: list[dict[str, Any]],
    snapshots_stable: bool,
    sdk: dict[str, Any],
    cli_stable: bool,
) -> list[str]:
    blockers: list[str] = []
    if not remediation_observation["passed"]:
        blockers.append("exact-docker-remediation-did-not-pass")
    if not 0 <= pricing_age_microseconds <= FRESHNESS_SECONDS * 1_000_000:
        blockers.append("replayable-official-pricing-is-not-fresh-within-72-hours")
    if not all(snapshot["observation"]["passed"] for snapshot in snapshots):
        blockers.append("read-only-docker-readiness-snapshot-failed")
    if not snapshots_stable:
        blockers.append("read-only-docker-readiness-snapshots-are-not-stable")
    if not sdk["passed"]:
        blockers.append("sdk-credential-endpoint-or-production-factory-check-failed")
    if not cli_stable:
        blockers.append("approved-docker-cli-identity-changed")
    return sorted(blockers)


def _preflight_body(
    *,
    receipt_binding: dict[str, Any],
    attempt_binding: dict[str, Any],
    source: dict[str, Any],
    remediation_binding: dict[str, Any],
    pricing_binding: dict[str, Any],
    remediation_observation: dict[str, Any],
    pricing_evidence: dict[str, Any],
    cli_bindings: dict[str, Any],
    snapshots: list[dict[str, Any]],
    sdk: dict[str, Any],
    recorded_at: str,
) -> dict[str, Any]:
    _parse_time(recorded_at, label="preflight recorded_at")
    docker_remediation.validate_docker_remediation_observation(remediation_observation)
    pricing_capture.validate_official_pricing_evidence(pricing_evidence)
    _require(
        isinstance(cli_bindings, dict) and tuple(cli_bindings) == ("before", "after"),
        "D-127 preflight CLI bindings differ",
    )
    _require(
        isinstance(snapshots, list) and len(snapshots) == 2,
        "D-127 preflight requires two Docker snapshots",
    )
    for snapshot in snapshots:
        docker_remediation.validate_docker_readiness_snapshot(snapshot)
    _require(
        isinstance(sdk, dict)
        and type(sdk.get("passed")) is bool
        and sdk.get("network_call_count") == 0,
        "D-127 preflight SDK boundary differs",
    )
    age = _pricing_age_microseconds(pricing_evidence["observed_at"], recorded_at)
    stable = canonical_json(snapshots[0]) == canonical_json(snapshots[1])
    cli_stable = canonical_json(cli_bindings["before"]) == canonical_json(
        cli_bindings["after"]
    )
    blockers = _preflight_blockers(
        remediation_observation=remediation_observation,
        pricing_age_microseconds=age,
        snapshots=snapshots,
        snapshots_stable=stable,
        sdk=sdk,
        cli_stable=cli_stable,
    )
    status = PREFLIGHT_READY_STATUS if not blockers else PREFLIGHT_BLOCKED_STATUS
    return {
        "milestone": MILESTONE,
        "evidence_kind": "repeated-read-only-docker-sdk-credential-endpoint-no-call-preflight",
        "recorded_at": recorded_at,
        "status": status,
        "receipt_binding": receipt_binding,
        "attempt_binding": attempt_binding,
        "source_identity": source,
        "remediation_binding": remediation_binding,
        "pricing_binding": pricing_binding,
        "pricing_observed_at": pricing_evidence["observed_at"],
        "pricing_age_microseconds": age,
        "approved_docker_cli_bindings": cli_bindings,
        "docker_readiness_snapshots": snapshots,
        "docker_snapshots_stable": stable,
        "sdk_credential_factory_observation": sdk,
        "observed_blockers": blockers,
        "authority": {
            "official_public_get_request_count": pricing_evidence["public_get_request_count"],
            "docker_desktop_start_count": remediation_observation["desktop_start_count"],
            "docker_image_store_mutation_count": remediation_observation[
                "image_store_mutation_count"
            ],
            "remediation_docker_cli_command_count": remediation_observation[
                "docker_cli_command_count"
            ],
            "read_only_snapshot_docker_cli_command_count": sum(
                snapshot["docker_cli_command_count"] for snapshot in snapshots
            ),
            "sdk_network_call_count": sdk["network_call_count"],
            **_authority_zero_boundary(),
        },
    }


def _validate_preflight_artifact(root: Path) -> dict[str, Any]:
    receipt = _load_receipt(root)
    attempt = _validate_attempt_artifact(root, "read-only-no-call-preflight")
    remediation = _validate_remediation_artifact(root)
    pricing = _validate_pricing_artifact(root)
    payload = _load_artifact(
        root,
        PREFLIGHT_PATH,
        schema=PREFLIGHT_SCHEMA,
        prefix="d127preflight_",
    )
    body = payload["semantic_body"]
    _require(tuple(body) == PREFLIGHT_BODY_KEYS, "D-127 preflight body fields differ")
    _require(
        body["receipt_binding"] == _artifact_binding(root, RECEIPT_PATH)
        and body["receipt_binding"]["artifact_id"] == receipt["artifact_id"],
        "D-127 preflight receipt binding differs",
    )
    _require(
        body["attempt_binding"] == _artifact_binding(root, PREFLIGHT_ATTEMPT_PATH)
        and body["attempt_binding"]["artifact_id"] == attempt["artifact_id"],
        "D-127 preflight attempt binding differs",
    )
    _require(
        body["remediation_binding"] == _artifact_binding(root, REMEDIATION_PATH)
        and body["remediation_binding"]["artifact_id"] == remediation["artifact_id"],
        "D-127 preflight remediation binding differs",
    )
    _require(
        body["pricing_binding"] == _artifact_binding(root, PRICING_PATH)
        and body["pricing_binding"]["artifact_id"] == pricing["artifact_id"],
        "D-127 preflight pricing binding differs",
    )
    _validate_source_identity(body["source_identity"], root=root)
    _require(
        canonical_json(body["source_identity"])
        == canonical_json(remediation["semantic_body"]["source_identity"])
        == canonical_json(pricing["semantic_body"]["source_identity"]),
        "D-127 preflight source bindings differ",
    )
    _require(
        canonical_json(body["source_identity"])
        == canonical_json(attempt["semantic_body"]["source_identity"]),
        "D-127 preflight attempt source differs",
    )
    _require(
        _parse_time(pricing["semantic_body"]["recorded_at"], label="pricing terminal")
        <= _parse_time(attempt["semantic_body"]["recorded_at"], label="preflight attempt"),
        "D-127 preflight attempt predates pricing terminal",
    )
    _require(
        _parse_time(attempt["semantic_body"]["recorded_at"], label="preflight attempt")
        <= _parse_time(body["recorded_at"], label="preflight recorded_at"),
        "D-127 preflight chronology differs",
    )
    _validate_sdk_observation(
        root,
        body["sdk_credential_factory_observation"],
        source=body["source_identity"],
    )
    expected = _preflight_body(
        receipt_binding=body["receipt_binding"],
        attempt_binding=body["attempt_binding"],
        source=body["source_identity"],
        remediation_binding=body["remediation_binding"],
        pricing_binding=body["pricing_binding"],
        remediation_observation=remediation["semantic_body"]["observation"],
        pricing_evidence=pricing["semantic_body"]["official_pricing_evidence"],
        cli_bindings=body["approved_docker_cli_bindings"],
        snapshots=body["docker_readiness_snapshots"],
        sdk=body["sdk_credential_factory_observation"],
        recorded_at=body["recorded_at"],
    )
    _require(canonical_json(body) == canonical_json(expected), "D-127 preflight body differs")
    return payload


def _gate_body(
    *,
    receipt_binding: dict[str, Any],
    source: dict[str, Any],
    remediation_binding: dict[str, Any],
    pricing_binding: dict[str, Any],
    preflight_binding: dict[str, Any],
    remediation_observation: dict[str, Any],
    pricing_evidence: dict[str, Any],
    preflight_body: dict[str, Any],
    recorded_at: str,
) -> dict[str, Any]:
    gate_age = _pricing_age_microseconds(pricing_evidence["observed_at"], recorded_at)
    pricing_fresh = 0 <= gate_age <= FRESHNESS_SECONDS * 1_000_000
    snapshots = preflight_body["docker_readiness_snapshots"]
    sdk = preflight_body["sdk_credential_factory_observation"]
    blockers = list(preflight_body["observed_blockers"])
    if not pricing_fresh:
        blockers.append("replayable-official-pricing-is-not-fresh-at-gate-creation")
    no_incidental_container_start = remediation_observation["desktop_start_count"] == 0
    if not no_incidental_container_start:
        blockers.append("incidental-container-start-boundary-not-preserved")
    blockers = sorted(set(blockers))
    ready = not blockers
    status = GATE_READY_STATUS if ready else GATE_BLOCKED_STATUS
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d126-successor-blocker-remediation-repeated-no-call-gate",
        "recorded_at": recorded_at,
        "status": status,
        "receipt_binding": receipt_binding,
        "source_identity": source,
        "remediation_binding": remediation_binding,
        "pricing_binding": pricing_binding,
        "preflight_binding": preflight_binding,
        "qualification": {
            "docker_remediation_passed": remediation_observation["passed"],
            "official_pricing_decoded_entity_replay_valid": True,
            "official_pricing_fresh_within_72_hours_at_gate": pricing_fresh,
            "official_pricing_age_microseconds_at_gate": gate_age,
            "two_read_only_docker_snapshots_passed": all(
                snapshot["observation"]["passed"] for snapshot in snapshots
            ),
            "read_only_docker_snapshots_stable": preflight_body[
                "docker_snapshots_stable"
            ],
            "sdk_credential_endpoint_factory_checks_passed": sdk["passed"],
            "no_incidental_container_start_boundary_preserved": (
                no_incidental_container_start
            ),
            "observed_blockers": blockers,
            "environment_ready_for_execution_hash": ready,
        },
        "authority": {
            "approved_successor_remediation_and_observations_completed": True,
            "provider_evaluator_agent_execution_authorized_or_performed": False,
            "runtime_memory_injection_or_retrieval_authorized_or_performed": False,
            "container_create_start_run_exec_authorized_or_performed": False,
            "incidental_container_start_via_desktop_launch_authorized_or_performed": False,
            "execution_hash_authorized_or_created": False,
            "execution_candidate_authorized_or_created": False,
            "cost_reservation_or_spend_authorized_or_performed": False,
            "cost_reserved_or_spent_usd": "0",
        },
        "next_gate": {
            "separate_exact_gate_approval_required": True,
            "execution_hash_or_candidate_must_not_be_created_from_this_approval": True,
            "live_execution_remains_separately_gated": True,
        },
    }


def _validate_gate_artifact(root: Path) -> dict[str, Any]:
    _require_external_helper_contracts()
    receipt = _load_receipt(root)
    remediation = _validate_remediation_artifact(root)
    pricing = _validate_pricing_artifact(root)
    preflight = _validate_preflight_artifact(root)
    payload = _load_artifact(root, GATE_PATH, schema=GATE_SCHEMA, prefix="d127_")
    body = payload["semantic_body"]
    _require(tuple(body) == GATE_BODY_KEYS, "D-127 gate body fields differ")
    expected_bindings = {
        "receipt_binding": _artifact_binding(root, RECEIPT_PATH),
        "remediation_binding": _artifact_binding(root, REMEDIATION_PATH),
        "pricing_binding": _artifact_binding(root, PRICING_PATH),
        "preflight_binding": _artifact_binding(root, PREFLIGHT_PATH),
    }
    for field, binding in expected_bindings.items():
        _require(body[field] == binding, f"D-127 gate {field} differs")
    _require(
        body["receipt_binding"]["artifact_id"] == receipt["artifact_id"]
        and body["remediation_binding"]["artifact_id"] == remediation["artifact_id"]
        and body["pricing_binding"]["artifact_id"] == pricing["artifact_id"]
        and body["preflight_binding"]["artifact_id"] == preflight["artifact_id"],
        "D-127 gate artifact IDs differ",
    )
    _require(
        canonical_json(body["source_identity"])
        == canonical_json(preflight["semantic_body"]["source_identity"]),
        "D-127 gate source differs",
    )
    _require(
        _parse_time(preflight["semantic_body"]["recorded_at"], label="preflight recorded_at")
        <= _parse_time(body["recorded_at"], label="gate recorded_at"),
        "D-127 gate chronology differs",
    )
    expected = _gate_body(
        receipt_binding=body["receipt_binding"],
        source=body["source_identity"],
        remediation_binding=body["remediation_binding"],
        pricing_binding=body["pricing_binding"],
        preflight_binding=body["preflight_binding"],
        remediation_observation=remediation["semantic_body"]["observation"],
        pricing_evidence=pricing["semantic_body"]["official_pricing_evidence"],
        preflight_body=preflight["semantic_body"],
        recorded_at=body["recorded_at"],
    )
    _require(canonical_json(body) == canonical_json(expected), "D-127 gate body differs")
    return payload


_EXTERNAL_OUTPUT_PATHS = (
    REMEDIATION_ATTEMPT_PATH,
    REMEDIATION_PATH,
    PRICING_ATTEMPT_PATH,
    PRICING_PATH,
    PREFLIGHT_ATTEMPT_PATH,
    PREFLIGHT_PATH,
    GATE_PATH,
)


def _validated_existing_outputs(root: Path) -> tuple[Path, ...]:
    allowed: list[Path] = []
    validators = {
        "docker-remediation": _validate_remediation_artifact,
        "official-pricing-capture": _validate_pricing_artifact,
        "read-only-no-call-preflight": _validate_preflight_artifact,
    }
    prior_complete = True
    for phase, (attempt_path, terminal_path) in _PHASE_PATHS.items():
        terminal_payload: dict[str, Any] | None = None
        attempt_exists = (root / attempt_path).exists()
        terminal_exists = (root / terminal_path).exists()
        _require(
            not (attempt_exists or terminal_exists) or prior_complete,
            f"D-127 {phase} exists before its predecessor phase completed",
        )
        _require(
            not terminal_exists or attempt_exists,
            f"D-127 {phase} terminal exists without attempt intent",
        )
        if attempt_exists:
            _validate_attempt_artifact(root, phase)
            allowed.append(attempt_path)
            _require(
                terminal_exists,
                f"D-127 orphaned {phase} attempt cannot be retried without separate approval",
            )
            terminal_payload = validators[phase](root)
            allowed.append(terminal_path)
        prior_complete = attempt_exists and terminal_exists
        if phase == "docker-remediation" and terminal_payload is not None:
            prior_complete = (
                prior_complete
                and terminal_payload["semantic_body"]["observation"]["passed"] is True
            )
    if (root / GATE_PATH).exists():
        _require(prior_complete, "D-127 gate exists before preflight completion")
        _validate_gate_artifact(root)
        allowed.append(GATE_PATH)
    return tuple(allowed)


def _blocked_remediation_result(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    body = payload["semantic_body"]
    observation = body["observation"]
    raw = _stable_read(root, REMEDIATION_PATH)
    skipped_reason = observation["desktop_start_skipped_reason"]
    blockers = [
        skipped_reason or "docker-remediation-did-not-establish-readiness",
    ]
    return {
        "status": body["status"],
        "phase": "docker-remediation",
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "source_commit": body["source_identity"]["commit"],
        "observed_blockers": blockers,
        "official_public_get_request_count": 0,
        "pricing_attempt_created": False,
        "read_only_preflight_attempt_created": False,
        "gate_created": False,
        "docker_cli_command_count": observation["docker_cli_command_count"],
        "docker_image_store_mutation_count": observation["image_store_mutation_count"],
        "provider_evaluator_agent_calls_made": 0,
        "container_create_start_run_exec_count": 0,
        "execution_hash_created": False,
        "execution_candidate_created": False,
        "cost_reserved_or_spent_usd": "0",
    }


def _require_external_helper_contracts() -> None:
    _require(
        docker_remediation.APPROVED_CLI_VERSION == DOCKER_CLI_VERSION
        and docker_remediation.APPROVED_CLI_BYTES == DOCKER_CLI_BYTES
        and docker_remediation.APPROVED_CLI_SHA256 == DOCKER_CLI_SHA256
        and tuple(docker_remediation.DOCKER_IMAGES) == DOCKER_IMAGE_REFS,
        "D-127 Docker helper constants differ from exact approval",
    )
    _require(
        docker_remediation.ALLOW_DAEMON_START_WITH_UNVERIFIED_RESTART_STATE is False
        and docker_remediation.DAEMON_START_SKIPPED_REASON == DAEMON_START_SKIPPED_REASON,
        "D-127 Docker helper incidental-container-start boundary differs",
    )
    _require(
        pricing_capture.OFFICIAL_MODEL_PAGE_URL
        == "https://developers.openai.com/api/docs/models/gpt-5.4-mini.md"
        and pricing_capture.MODEL_ID == "gpt-5.4-mini-2026-03-17"
        and str(pricing_capture.INPUT_RATE) == "0.75"
        and str(pricing_capture.CACHED_INPUT_RATE) == "0.075"
        and str(pricing_capture.OUTPUT_RATE) == "4.5"
        and pricing_capture.MAX_DECODED_ENTITY_BYTES == 128_000,
        "D-127 pricing helper constants differ from exact approval",
    )


def _require_modules_unchanged(
    root: Path,
    source: dict[str, Any],
    before: list[dict[str, Any]],
) -> None:
    after = _loaded_module_bindings(root, source_commit=source["commit"])
    _require(canonical_json(after) == canonical_json(before), "D-127 loaded modules changed")


def _require_existing_sources_match(
    root: Path,
    source: dict[str, Any],
    existing: tuple[Path, ...],
) -> None:
    for phase, (attempt_path, _terminal_path) in _PHASE_PATHS.items():
        if attempt_path not in existing:
            continue
        attempt = _validate_attempt_artifact(root, phase)
        _require(
            canonical_json(attempt["semantic_body"]["source_identity"])
            == canonical_json(source),
            "D-127 existing artifact source differs from current committed source",
        )


def _write_remediation_terminal(
    root: Path,
    *,
    source: dict[str, Any],
    observation: dict[str, Any],
    expected_attempt: dict[str, Any],
) -> dict[str, Any]:
    attempt = _require_attempt_unchanged(
        root,
        phase="docker-remediation",
        expected=expected_attempt,
    )
    body = _remediation_body(
        receipt_binding=_artifact_binding(root, RECEIPT_PATH),
        attempt_binding=_artifact_binding(root, REMEDIATION_ATTEMPT_PATH),
        source=source,
        observation=observation,
        recorded_at=_now(),
    )
    _require(
        body["attempt_binding"]["artifact_id"] == attempt["artifact_id"],
        "D-127 remediation attempt ID differs before write",
    )
    _write_artifact(
        root,
        REMEDIATION_PATH,
        schema=REMEDIATION_SCHEMA,
        prefix="d127remediation_",
        body=body,
    )
    return _validate_remediation_artifact(root)


def _write_pricing_terminal(
    root: Path,
    *,
    source: dict[str, Any],
    evidence: dict[str, Any],
    expected_attempt: dict[str, Any],
) -> dict[str, Any]:
    attempt = _require_attempt_unchanged(
        root,
        phase="official-pricing-capture",
        expected=expected_attempt,
    )
    body = _pricing_body(
        receipt_binding=_artifact_binding(root, RECEIPT_PATH),
        attempt_binding=_artifact_binding(root, PRICING_ATTEMPT_PATH),
        source=source,
        evidence=evidence,
    )
    _require(
        body["attempt_binding"]["artifact_id"] == attempt["artifact_id"],
        "D-127 pricing attempt ID differs before write",
    )
    _write_artifact(
        root,
        PRICING_PATH,
        schema=PRICING_SCHEMA,
        prefix="d127pricing_",
        body=body,
    )
    return _validate_pricing_artifact(root)


def _write_preflight_terminal(
    root: Path,
    *,
    source: dict[str, Any],
    cli_before: dict[str, Any],
    cli_after: dict[str, Any],
    snapshots: list[dict[str, Any]],
    sdk: dict[str, Any],
    expected_attempt: dict[str, Any],
) -> dict[str, Any]:
    attempt = _require_attempt_unchanged(
        root,
        phase="read-only-no-call-preflight",
        expected=expected_attempt,
    )
    remediation = _validate_remediation_artifact(root)
    pricing = _validate_pricing_artifact(root)
    _validate_sdk_observation(root, sdk, source=source)
    body = _preflight_body(
        receipt_binding=_artifact_binding(root, RECEIPT_PATH),
        attempt_binding=_artifact_binding(root, PREFLIGHT_ATTEMPT_PATH),
        source=source,
        remediation_binding=_artifact_binding(root, REMEDIATION_PATH),
        pricing_binding=_artifact_binding(root, PRICING_PATH),
        remediation_observation=remediation["semantic_body"]["observation"],
        pricing_evidence=pricing["semantic_body"]["official_pricing_evidence"],
        cli_bindings={"before": cli_before, "after": cli_after},
        snapshots=snapshots,
        sdk=sdk,
        recorded_at=_now(),
    )
    _require(
        body["attempt_binding"]["artifact_id"] == attempt["artifact_id"],
        "D-127 preflight attempt ID differs before write",
    )
    _write_artifact(
        root,
        PREFLIGHT_PATH,
        schema=PREFLIGHT_SCHEMA,
        prefix="d127preflight_",
        body=body,
    )
    return _validate_preflight_artifact(root)


def _write_gate(root: Path) -> dict[str, Any]:
    receipt = _load_receipt(root)
    remediation = _validate_remediation_artifact(root)
    pricing = _validate_pricing_artifact(root)
    preflight = _validate_preflight_artifact(root)
    source = preflight["semantic_body"]["source_identity"]
    body = _gate_body(
        receipt_binding=_artifact_binding(root, RECEIPT_PATH),
        source=source,
        remediation_binding=_artifact_binding(root, REMEDIATION_PATH),
        pricing_binding=_artifact_binding(root, PRICING_PATH),
        preflight_binding=_artifact_binding(root, PREFLIGHT_PATH),
        remediation_observation=remediation["semantic_body"]["observation"],
        pricing_evidence=pricing["semantic_body"]["official_pricing_evidence"],
        preflight_body=preflight["semantic_body"],
        recorded_at=_now(),
    )
    _require(
        body["receipt_binding"]["artifact_id"] == receipt["artifact_id"],
        "D-127 gate receipt ID differs before write",
    )
    _write_artifact(root, GATE_PATH, schema=GATE_SCHEMA, prefix="d127_", body=body)
    return _validate_gate_artifact(root)


def run_d127_external_remediation_and_preflight(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Run only the explicitly approved external remediation/no-call phase."""

    root = _repo_root(repository)
    _load_receipt(root)
    _require_external_helper_contracts()
    existing = _validated_existing_outputs(root)
    if GATE_PATH in existing:
        return validate_d127_no_call_gate(repository=root, mode="current-source")
    if REMEDIATION_PATH in existing:
        remediation = _validate_remediation_artifact(root)
        if remediation["semantic_body"]["observation"]["passed"] is False:
            return _blocked_remediation_result(root, remediation)

    static = _check_static_prerequisites(root, allowed_outputs=existing)
    source = static["source"]
    _require_receipt_tracked_at_head(root, source_commit=source["commit"])
    _require_current_source(root, source, allowed_outputs=existing)
    _require_existing_sources_match(root, source, existing)
    modules = _loaded_module_bindings(root, source_commit=source["commit"])
    initial_sdk = _sdk_observation(
        root,
        source,
        static["production_model_factory_checks"],
    )
    _validate_sdk_observation(root, initial_sdk, source=source)
    _require(initial_sdk["passed"] is True, "D-127 initial SDK prerequisite is not ready")

    if REMEDIATION_PATH not in existing:
        remediation_attempt = _create_attempt_artifact(
            root,
            phase="docker-remediation",
            source=source,
            module_bindings=modules,
        )
        existing = (*existing, REMEDIATION_ATTEMPT_PATH)
        _require_current_source(root, source, allowed_outputs=existing)
        _require_modules_unchanged(root, source, modules)
        _require_attempt_unchanged(
            root,
            phase="docker-remediation",
            expected=remediation_attempt,
        )
        observation = docker_remediation.remediate_docker_environment()
        docker_remediation.validate_docker_remediation_observation(observation)
        _require_current_source(root, source, allowed_outputs=existing)
        _require_modules_unchanged(root, source, modules)
        _require_attempt_unchanged(
            root,
            phase="docker-remediation",
            expected=remediation_attempt,
        )
        remediation = _write_remediation_terminal(
            root,
            source=source,
            observation=observation,
            expected_attempt=remediation_attempt,
        )
        existing = (*existing, REMEDIATION_PATH)
        if observation["passed"] is False:
            return _blocked_remediation_result(root, remediation)

    if PRICING_PATH not in existing:
        _require_current_source(root, source, allowed_outputs=existing)
        _require_modules_unchanged(root, source, modules)
        pricing_attempt = _create_attempt_artifact(
            root,
            phase="official-pricing-capture",
            source=source,
            module_bindings=modules,
        )
        existing = (*existing, PRICING_ATTEMPT_PATH)
        _require_current_source(root, source, allowed_outputs=existing)
        _require_modules_unchanged(root, source, modules)
        _require_attempt_unchanged(
            root,
            phase="official-pricing-capture",
            expected=pricing_attempt,
        )
        evidence = pricing_capture.capture_official_pricing_evidence()
        pricing_capture.validate_official_pricing_evidence(evidence)
        _require_current_source(root, source, allowed_outputs=existing)
        _require_modules_unchanged(root, source, modules)
        _require_attempt_unchanged(
            root,
            phase="official-pricing-capture",
            expected=pricing_attempt,
        )
        _write_pricing_terminal(
            root,
            source=source,
            evidence=evidence,
            expected_attempt=pricing_attempt,
        )
        existing = (*existing, PRICING_PATH)

    if PREFLIGHT_PATH not in existing:
        pricing = _validate_pricing_artifact(root)
        age = _pricing_age_microseconds(
            pricing["semantic_body"]["official_pricing_evidence"]["observed_at"],
            _now(),
        )
        _require(
            0 <= age <= FRESHNESS_SECONDS * 1_000_000,
            "D-127 pricing became stale before repeated preflight",
        )
        _require_current_source(root, source, allowed_outputs=existing)
        _require_modules_unchanged(root, source, modules)
        cli_before = _approved_docker_cli_identity()
        preflight_attempt = _create_attempt_artifact(
            root,
            phase="read-only-no-call-preflight",
            source=source,
            module_bindings=modules,
        )
        existing = (*existing, PREFLIGHT_ATTEMPT_PATH)
        _require_current_source(root, source, allowed_outputs=existing)
        _require_modules_unchanged(root, source, modules)
        _require_attempt_unchanged(
            root,
            phase="read-only-no-call-preflight",
            expected=preflight_attempt,
        )
        snapshots = [
            docker_remediation.observe_docker_readiness(),
            docker_remediation.observe_docker_readiness(),
        ]
        for snapshot in snapshots:
            docker_remediation.validate_docker_readiness_snapshot(snapshot)
        _require_current_source(root, source, allowed_outputs=existing)
        _require_modules_unchanged(root, source, modules)
        _require_attempt_unchanged(
            root,
            phase="read-only-no-call-preflight",
            expected=preflight_attempt,
        )
        cli_after = _approved_docker_cli_identity()
        final_factory = _model_factory_contract(root)
        sdk = _sdk_observation(root, source, final_factory)
        _validate_sdk_observation(root, sdk, source=source)
        _write_preflight_terminal(
            root,
            source=source,
            cli_before=cli_before,
            cli_after=cli_after,
            snapshots=snapshots,
            sdk=sdk,
            expected_attempt=preflight_attempt,
        )
        existing = (*existing, PREFLIGHT_PATH)

    _require_current_source(root, source, allowed_outputs=existing)
    _require_modules_unchanged(root, source, modules)
    gate = _write_gate(root)
    existing = (*existing, GATE_PATH)
    _require_current_source(root, source, allowed_outputs=existing)
    return _validation_result(root, gate, post_commit=None)


def _post_evidence_commit_state(root: Path, source: dict[str, Any]) -> dict[str, Any]:
    _require(
        _git_cli_observation(root) == source["git_cli_observation"],
        "D-127 post-commit Git engine differs from source identity",
    )
    head = _run_git(root, "rev-parse", "HEAD")
    ancestry = _run_git(root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    _require(
        ancestry == [head, source["commit"]],
        "D-127 evidence commit must have the exact source commit as its only parent",
    )
    _require(
        not _run_git(root, "status", "--porcelain", "--untracked-files=all"),
        "D-127 post-evidence-commit worktree is not clean",
    )
    changed = [
        path
        for path in _run_git(
            root,
            "diff",
            "--name-only",
            f"{source['commit']}..{head}",
        ).splitlines()
        if path
    ]
    status_rows = [
        line.split("\t")
        for line in _run_git(
            root,
            "diff",
            "--name-status",
            f"{source['commit']}..{head}",
        ).splitlines()
        if line
    ]
    _require(
        all(len(row) == 2 and row[0] in {"A", "M"} for row in status_rows),
        "D-127 evidence commit contains a non-add-or-modify change",
    )
    status_by_path = {row[1]: row[0] for row in status_rows}
    allowed = {
        *(path.as_posix() for path in _EXTERNAL_OUTPUT_PATHS),
        "AGENTS.md",
        "README.md",
        "docs/current-status.md",
        "docs/03-contracts.md",
        "docs/04-evaluation-protocol.md",
        "docs/05-implementation-plan.md",
        "docs/06-decisions.md",
        "docs/07-reproduction.md",
        "docs/08-limitations.md",
        "docs/09-evidence.md",
    }
    _require(set(changed).issubset(allowed), "D-127 evidence commit changed source paths")
    _require(
        set(path.as_posix() for path in _EXTERNAL_OUTPUT_PATHS).issubset(changed),
        "D-127 evidence commit is missing successor artifacts",
    )
    for path in _EXTERNAL_OUTPUT_PATHS:
        relative = path.as_posix()
        _require(
            status_by_path.get(relative) == "A",
            "D-127 successor evidence path was not newly added by the evidence commit",
        )
        predecessor_lookup = _git_command(
            root,
            "cat-file",
            "-e",
            f"{source['commit']}:{relative}",
            text=True,
        )
        _require(
            predecessor_lookup.returncode != 0,
            "D-127 successor evidence path existed in the source commit",
        )
    _require(
        _git_cli_observation(root) == source["git_cli_observation"],
        "D-127 Git engine changed during post-commit validation",
    )
    return {"head": head, "source_commit": source["commit"], "changed_paths": changed}


def _validation_result(
    root: Path,
    gate: dict[str, Any],
    *,
    post_commit: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = _stable_read(root, GATE_PATH)
    body = gate["semantic_body"]
    preflight = _validate_preflight_artifact(root)["semantic_body"]
    remediation = _validate_remediation_artifact(root)["semantic_body"]["observation"]
    pricing = _validate_pricing_artifact(root)["semantic_body"]["official_pricing_evidence"]
    return {
        "status": body["status"],
        "gate_id": gate["artifact_id"],
        "semantic_body_hash": gate["semantic_body_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "source_commit": body["source_identity"]["commit"],
        "environment_ready_for_execution_hash": body["qualification"][
            "environment_ready_for_execution_hash"
        ],
        "observed_blockers": body["qualification"]["observed_blockers"],
        "official_public_get_request_count": pricing["public_get_request_count"],
        "docker_cli_command_count": remediation["docker_cli_command_count"]
        + preflight["authority"]["read_only_snapshot_docker_cli_command_count"],
        "docker_image_store_mutation_count": remediation["image_store_mutation_count"],
        "provider_evaluator_agent_calls_made": 0,
        "container_create_start_run_exec_count": 0,
        "execution_hash_created": False,
        "execution_candidate_created": False,
        "cost_reserved_or_spent_usd": "0",
        "post_commit": post_commit,
    }


def validate_d127_no_call_gate(
    *,
    repository: str | Path | None = None,
    mode: str = "current-source",
) -> dict[str, Any]:
    """Replay D-127 evidence without Docker or network activity."""

    root = _repo_root(repository)
    gate = _validate_gate_artifact(root)
    source = gate["semantic_body"]["source_identity"]
    post_commit = None
    if mode == "current-source":
        _require_current_source(root, source, allowed_outputs=_EXTERNAL_OUTPUT_PATHS)
    elif mode == "post-evidence-commit":
        post_commit = _post_evidence_commit_state(root, source)
    else:
        raise D127PreflightError("D-127 validation mode differs")
    qualification = gate["semantic_body"]["qualification"]
    if mode == "current-source" and qualification["environment_ready_for_execution_hash"]:
        age = _pricing_age_microseconds(
            _validate_pricing_artifact(root)["semantic_body"]["recorded_at"],
            _now(),
        )
        _require(
            0 <= age <= FRESHNESS_SECONDS * 1_000_000,
            "D-127 ready gate pricing is no longer fresh",
        )
        sdk = _validate_preflight_artifact(root)["semantic_body"][
            "sdk_credential_factory_observation"
        ]
        _require_current_sdk_matches_artifact(root, source, sdk)
        _require(
            _approved_docker_cli_identity()
            == _validate_preflight_artifact(root)["semantic_body"][
                "approved_docker_cli_bindings"
            ]["after"],
            "D-127 current approved Docker CLI differs",
        )
    return _validation_result(root, gate, post_commit=post_commit)


__all__ = [
    "D127PreflightError",
    "GATE_PATH",
    "PREFLIGHT_PATH",
    "PRICING_PATH",
    "RECEIPT_PATH",
    "REMEDIATION_PATH",
    "STATIC_READY_STATUS",
    "check_d127_static_prerequisites",
    "create_d127_approval_receipt",
    "run_d127_external_remediation_and_preflight",
    "validate_d127_no_call_gate",
]
