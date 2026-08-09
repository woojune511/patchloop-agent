"""D-132 source-qualified D-130 external-activation successor.

The D-132 offline gate records that the pre-source D-130 activation message was
received but could not be exercised safely.  Gate construction performs no
credential, SDK, Docker, pricing, or network observation and never invokes a
future writer or external helper.

After a fresh post-D-132 activation, the future path records an exact
activation receipt in a receipt-only commit.  Each external phase then writes
an append-only durable attempt before its first external action and publishes a
terminal observation before the next phase.  Historical D-127/D-128 top-level
runners are deliberately not called.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from functools import cache, wraps
from pathlib import Path
from typing import Any, Literal

from patchloop import errors as errors_module
from patchloop import runtime as runtime_module
from patchloop import util as util_module
from patchloop.errors import ContractError
from patchloop.evals import d126_clean_source_pricing_no_call_preflight as d126
from patchloop.evals import d127_d126_successor_no_call_preflight as d127
from patchloop.evals import d127_docker_remediation as d127_docker
from patchloop.evals import d127_pricing_capture as pricing_capture
from patchloop.evals import d128_docker_no_start_remediation as docker_remediation
from patchloop.evals import d131_d130_local_admission_offline as d131
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-132"
SCHEMA_VERSION = "d130-external-activation-implementation-offline-source-gate-d132-v1"
STATUS = (
    "D132_D130_EXTERNAL_ACTIVATION_IMPLEMENTATION_OFFLINE_SOURCE_QUALIFIED_"
    "FRESH_ACTIVATION_REQUIRED"
)

OUTPUT_PATH = Path(
    "reports/live-pilot/artifacts/d132-d130-external-activation-successor-offline-source-gate.json"
)
ACTIVATION_RECEIPT_PATH = d131.ACTIVATION_PATH
DOCKER_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d130-docker-image-readiness-attempt-intent.json"
)
DOCKER_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/d130-docker-image-readiness-action-started.json"
)
DOCKER_TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d130-exact-docker-image-readiness-remediation-observation.json"
)
PRICING_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d130-official-pricing-capture-attempt-intent.json"
)
PRICING_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/d130-official-pricing-capture-action-started.json"
)
PRICING_TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d130-replayable-official-pricing-evidence.json"
)
PREFLIGHT_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d130-read-only-preflight-attempt-intent.json"
)
PREFLIGHT_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/d130-read-only-preflight-action-started.json"
)
PREFLIGHT_TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d130-repeated-no-call-readiness-preflight.json"
)
FINAL_GATE_PATH = Path(
    "reports/live-pilot/artifacts/d130-terminal-successor-no-call-preflight-gate.json"
)
PRICING_PATH = PRICING_TERMINAL_PATH
PREFLIGHT_PATH = PREFLIGHT_TERMINAL_PATH
GATE_PATH = FINAL_GATE_PATH

FUTURE_PATHS = (
    ACTIVATION_RECEIPT_PATH,
    DOCKER_ATTEMPT_PATH,
    DOCKER_STARTED_PATH,
    DOCKER_TERMINAL_PATH,
    PRICING_ATTEMPT_PATH,
    PRICING_STARTED_PATH,
    PRICING_TERMINAL_PATH,
    PREFLIGHT_ATTEMPT_PATH,
    PREFLIGHT_STARTED_PATH,
    PREFLIGHT_TERMINAL_PATH,
    FINAL_GATE_PATH,
)
PHASE_PATHS = {
    "docker-image-readiness-remediation": (
        DOCKER_ATTEMPT_PATH,
        DOCKER_STARTED_PATH,
        DOCKER_TERMINAL_PATH,
    ),
    "official-pricing-capture": (
        PRICING_ATTEMPT_PATH,
        PRICING_STARTED_PATH,
        PRICING_TERMINAL_PATH,
    ),
    "read-only-no-call-preflight": (
        PREFLIGHT_ATTEMPT_PATH,
        PREFLIGHT_STARTED_PATH,
        PREFLIGHT_TERMINAL_PATH,
    ),
}

IMPLEMENTATION_PATHS = (
    Path("patchloop/evals/d132_d130_external_activation_offline.py"),
    Path("scripts/build_d132_d130_external_activation_offline.py"),
    Path("tests/test_d132_d130_external_activation_offline.py"),
)
DEPENDENCY_PATHS = (
    Path("patchloop/evals/d131_d130_local_admission_offline.py"),
    Path("patchloop/evals/d128_docker_no_start_remediation.py"),
    Path("patchloop/evals/d127_pricing_capture.py"),
    Path("patchloop/evals/d127_d126_successor_no_call_preflight.py"),
    Path("patchloop/errors.py"),
    Path("patchloop/runtime.py"),
    Path("patchloop/util.py"),
    Path("patchloop/agent/model.py"),
    Path("uv.lock"),
    Path("patchloop/evals/d127_docker_remediation.py"),
    Path("patchloop/evals/d126_clean_source_pricing_no_call_preflight.py"),
)
SOURCE_BINDING_PATHS = IMPLEMENTATION_PATHS + DEPENDENCY_PATHS
LOADED_MODULE_PATHS = (
    (IMPLEMENTATION_PATHS[0], __name__),
    (DEPENDENCY_PATHS[0], d131.__name__),
    (DEPENDENCY_PATHS[1], docker_remediation.__name__),
    (DEPENDENCY_PATHS[2], pricing_capture.__name__),
    (DEPENDENCY_PATHS[3], d127.__name__),
    (DEPENDENCY_PATHS[4], errors_module.__name__),
    (DEPENDENCY_PATHS[5], runtime_module.__name__),
    (DEPENDENCY_PATHS[6], util_module.__name__),
    (DEPENDENCY_PATHS[9], d127_docker.__name__),
    (DEPENDENCY_PATHS[10], d126.__name__),
)

D131_GATE_ID = "d131_849502e63d33aa3c8ceea8dc03faf0ff86e8ec51db9321fa13544df15a4af057"
D131_BODY_SHA256 = "sha256:849502e63d33aa3c8ceea8dc03faf0ff86e8ec51db9321fa13544df15a4af057"
D131_FILE_SHA256 = "sha256:8dfcd275b3e66113bc92df64e33bcf14f80c101cba2e40246d42b61f22dac048"
D131_FILE_BYTES = 14_516
D131_EVIDENCE_COMMIT = "283b9124af38252f47a06cbb1a484807b5030be2"
D131_EVIDENCE_TREE = "78b62219f438b695ca3bf26d5de77a5ccf175e21"
D131_EVIDENCE_PARENT = "9cd736c0221bba17375c3b7ddce02e5214fc21fe"
D131_GATE_BLOB_OID = "c4e7135a66a2d1d7ca85dd60685f9cb8a8c01cfd"

D130_RECEIPT_ID = "d130approval_03c8c824f0d74122b8233df9810897b898c29b3bf907dd1a5cfd364f5026e010"
D130_RECEIPT_BODY_SHA256 = "sha256:03c8c824f0d74122b8233df9810897b898c29b3bf907dd1a5cfd364f5026e010"
D130_RECEIPT_FILE_SHA256 = "sha256:01901a4f20a0231856e0326d2bc37283794b9cff998463707bc19b15d22731ba"
D130_RECEIPT_FILE_BYTES = 11_514
D130_RECEIPT_COMMIT = "6987246b438fa6e6e711fa3b254aaf75ac4c2a66"
D130_RECEIPT_TREE = "13c52c79d3f58cc8fcfd584eb7d6df7536e76b9d"
D130_RECEIPT_PARENT = D131_EVIDENCE_COMMIT
D130_RECEIPT_BLOB_OID = "879ac90cc3a4e61cc97fadf930426d6ba74e4422"

D130_INTENT_ID = "d130intent_4cd20c7a8bbd20751b2f6a7b4a0d13de16d7aa5a41b6bf20648dedb414b6a153"
D130_INTENT_BODY_SHA256 = "sha256:4cd20c7a8bbd20751b2f6a7b4a0d13de16d7aa5a41b6bf20648dedb414b6a153"
D130_INTENT_FILE_SHA256 = "sha256:349d6680850374c1cee10e49f3319ef18bdd3640c48d075e999cbefac72c460c"
D130_INTENT_FILE_BYTES = 13_175
D130_INTENT_COMMIT = "4a40971b4e155683c49bbd6bcadc7468514ef84c"
D130_INTENT_TREE = "40dc0b5193dde2a58b176f791e807b798540888c"
D130_INTENT_PARENT = D130_RECEIPT_COMMIT
D130_INTENT_BLOB_OID = "2ac0ef87a4783db396aefa2abe1e777dc2c640bb"

ACTIVATION_RECEIPT_SCHEMA = "d130-external-no-call-preflight-activation-receipt-d132-v1"
ACTIVATION_RECEIPT_STATUS = "D132_D130_EXTERNAL_NO_CALL_PREFLIGHT_ACTIVATION_RECORDED"
ATTEMPT_SCHEMA = "d130-external-no-call-preflight-phase-attempt-d132-v1"
ACTION_STARTED_SCHEMA = "d130-external-no-call-preflight-action-started-d132-v1"
DOCKER_SCHEMA = "d130-exact-docker-image-readiness-remediation-d132-v1"
PRICING_SCHEMA = "d130-replayable-official-pricing-evidence-d132-v1"
PREFLIGHT_SCHEMA = "d130-repeated-no-call-readiness-preflight-d132-v1"
FINAL_GATE_SCHEMA = "d130-terminal-successor-no-call-preflight-gate-d132-v1"

ROOT_KEYS = ("schema_version", "artifact_id", "semantic_body_hash", "semantic_body")
GATE_ROOT_KEYS = ("schema_version", "gate_id", "semantic_body_hash", "semantic_body")
ACTIVE_DOC_PATHS = d131.ACTIVE_DOC_PATHS

DOCKER_READY_STATUS = "D132_D130_EXACT_DOCKER_IMAGE_READINESS_REMEDIATION_READY"
DOCKER_BLOCKED_STATUS = "D132_D130_EXACT_DOCKER_IMAGE_READINESS_REMEDIATION_OBSERVED_BLOCKED"
PRICING_CAPTURED_STATUS = "D132_D130_REPLAYABLE_OFFICIAL_PRICING_CAPTURED"
PREFLIGHT_READY_STATUS = "D132_D130_REPEATED_NO_CALL_PREFLIGHT_READY_EXECUTION_HASH_BLOCKED"
PREFLIGHT_BLOCKED_STATUS = "D132_D130_REPEATED_NO_CALL_PREFLIGHT_OBSERVED_BLOCKED"
FINAL_GATE_READY_STATUS = "D132_D130_EXTERNAL_NO_CALL_GATE_READY_EXECUTION_HASH_BLOCKED"
FINAL_GATE_BLOCKED_STATUS = "D132_D130_EXTERNAL_NO_CALL_GATE_OBSERVED_BLOCKED"
FRESHNESS_SECONDS = 72 * 60 * 60
SDK_MODULE_NAMES = ("openai", "httpx")
SDK_WRAPPER_KEYS = (
    "python_routing_environment_presence",
    "python_routing_environment_values_persisted",
    "d127_sdk_probe_skipped_due_to_python_routing",
    "loaded_sdk_module_bindings",
    "d127_sdk_observation",
)

FRESH_ACTIVATION_SCOPE = (
    "create-exact-d130-external-activation-receipt-and-receipt-only-commit",
    "create-and-commit-each-phase-attempt-as-an-exact-attempt-only-child-before-that-phase-action",
    "write-each-append-only-action-started-marker-immediately-before-its-external-helper",
    "perform-no-official-docs-search-open-or-pricing-network-before-the-committed-pricing-attempt",
    "use-approved-exact-docker-cli",
    "read-only-recheck-already-running-docker-desktop-linux-daemon",
    "pull-only-confirmed-missing-exact-moto-or-babel-digest-images",
    "capture-bounded-replayable-official-openai-pricing-evidence",
    "perform-sdk-credential-presence-and-official-endpoint-no-call-preflight",
    "commit-each-action-started-plus-terminal-transition-before-the-next-phase-attempt",
    "create-append-only-terminal-preflight-and-final-gate-evidence",
    "create-final-gate-plus-active-docs-evidence-commit",
)
FRESH_ACTIVATION_EXCLUSIONS = (
    "agent-docker-desktop-or-daemon-start",
    "container-create-start-run-or-exec",
    "other-image-pull-or-load",
    "provider-evaluator-or-agent-execution",
    "runtime-memory-injection-or-retrieval",
    "execution-hash-or-candidate-creation",
    "cost-reservation-or-spend",
    "four-row-ac-execution",
)
D132_SOURCE_PREPARATION_SCOPE = (
    "implement-d130-activation-receipt-and-durable-attempt-first-external-no-call-writer-validator-orchestrator-cli-and-focused-mocked-tests",
    "implement-append-only-new-only-collision-orphan-idempotence-boundaries",
    "bind-exact-d131-gate-d130-receipt-intent-git-topology-and-loaded-module-provenance",
    "require-activation-receipt-and-each-phase-attempt-commit-before-external-work",
    "modify-source-tests-docs-and-create-local-source-commit",
    "create-append-only-d132-offline-source-gate-and-local-evidence-commit",
    "render-fresh-exact-d132-qualified-activation-approval-template",
)
D132_SOURCE_PREPARATION_EXCLUSIONS = (
    "create-activation-receipt-attempt-preflight-terminal-or-final-gate-artifact",
    "official-docs-search-open-network-or-pricing-capture",
    "docker-sdk-credential-or-endpoint-observation",
    "container-create-start-run-or-exec",
    "provider-evaluator-or-agent-execution",
    "runtime-memory-injection-or-retrieval",
    "execution-hash-or-candidate-creation",
    "cost-reservation-or-spend",
    "four-row-ac-execution",
)
PHASE_ACTIONS = {
    "docker-image-readiness-remediation": [
        "observe-already-running-docker-desktop-linux-daemon-and-exact-images-read-only",
        "pull-only-confirmed-missing-moto-or-babel-exact-digest-images",
        "never-start-docker-desktop-or-daemon",
    ],
    "official-pricing-capture": [
        "perform-at-most-four-unauthenticated-official-doc-get-requests",
        "retain-at-most-128000-decoded-entity-bytes-for-replay",
    ],
    "read-only-no-call-preflight": [
        "perform-exactly-two-read-only-local-docker-readiness-snapshots",
        "observe-sdk-and-credential-presence-without-persisting-secret-material",
        "construct-local-sdk-client-against-rejecting-mock-transport",
    ],
}


class D132ActivationOfflineError(ContractError):
    """Raised when the D-132 successor contract fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D132ActivationOfflineError(message)


def _clear_validation_caches() -> None:
    for validator in (
        _d130_predecessor_binding,
        _load_activation_receipt,
        _validate_attempt_artifact,
        _rebuild_attempt_commit,
        _validate_action_started_artifact,
        _validate_terminal_artifact,
        _rebuild_phase_transition_commit,
        _validate_final_gate_artifact,
    ):
        clear = getattr(validator, "cache_clear", None)
        if clear is not None:
            clear()


def _fresh_validation_cache(function: Any) -> Any:
    @wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        _clear_validation_caches()
        try:
            return function(*args, **kwargs)
        finally:
            _clear_validation_caches()

    return wrapped


def _repo_root(repository: str | Path | None) -> Path:
    root = Path(repository).resolve() if repository is not None else repository_root().resolve()
    _require(root.is_dir(), "D-132 repository root is unavailable")
    return root


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any, *, label: str = "recorded_at") -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"D-132 {label} differs")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise D132ActivationOfflineError(f"D-132 {label} differs") from exc
    _require(parsed.tzinfo is not None, f"D-132 {label} lacks timezone")
    return parsed


def _age_microseconds(earlier: Any, later: Any, *, label: str) -> int:
    delta = _parse_time(later, label=f"{label} later") - _parse_time(
        earlier, label=f"{label} earlier"
    )
    return delta.days * 86_400 * 1_000_000 + delta.seconds * 1_000_000 + delta.microseconds


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
        "schema_version": SCHEMA_VERSION,
        "gate_id": f"d132_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _stable_read(root: Path, relative: Path) -> bytes:
    try:
        return d131._stable_read(root, relative)
    except ContractError as exc:
        raise D132ActivationOfflineError(str(exc)) from exc


def _read_json(root: Path, relative: Path) -> tuple[dict[str, Any], bytes]:
    raw = _stable_read(root, relative)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D132ActivationOfflineError(
            f"D-132 {relative.as_posix()} is not canonical JSON"
        ) from exc
    _require(isinstance(payload, dict), f"D-132 {relative.as_posix()} root differs")
    return payload, raw


def _path_absent(root: Path, relative: Path) -> None:
    try:
        d131._path_absent(root, relative)
    except ContractError as exc:
        raise D132ActivationOfflineError(str(exc)) from exc


def _write_new(root: Path, relative: Path, raw: bytes) -> None:
    try:
        d131._write_new(root, relative, raw)
    except ContractError as exc:
        raise D132ActivationOfflineError(str(exc)) from exc
    _clear_validation_caches()


def _git_command(root: Path, *args: str, binary: bool = False) -> bytes | str:
    try:
        return d131._git_command(root, *args, binary=binary)
    except ContractError as exc:
        raise D132ActivationOfflineError(str(exc)) from exc


def _status_lines(root: Path) -> list[str]:
    return [
        line
        for line in str(
            _git_command(root, "status", "--porcelain", "--untracked-files=all")
        ).splitlines()
        if line
    ]


def _head(root: Path) -> str:
    return str(_git_command(root, "rev-parse", "HEAD"))


def _commit_identity(root: Path, commit: str) -> dict[str, Any]:
    try:
        identity = d131._commit_identity(root, commit)
    except ContractError as exc:
        raise D132ActivationOfflineError("D-132 Git commit identity differs") from exc
    return {
        "commit": identity["commit"],
        "tree": identity["tree"],
        "parents": list(identity["parents"]),
    }


def _diff_rows(root: Path, commit: str) -> list[dict[str, str]]:
    try:
        return d131._diff_rows(root, commit)
    except ContractError as exc:
        raise D132ActivationOfflineError("D-132 Git commit diff differs") from exc


def _commit_blob(root: Path, commit: str, path: Path) -> tuple[str, bytes]:
    try:
        return d131._commit_blob(root, commit, path)
    except ContractError as exc:
        raise D132ActivationOfflineError("D-132 committed blob differs") from exc


def _assert_runtime_import_boundary(root: Path) -> None:
    module_files = {
        __name__: Path(__file__),
        d131.__name__: Path(str(d131.__file__)),
        docker_remediation.__name__: Path(str(docker_remediation.__file__)),
        pricing_capture.__name__: Path(str(pricing_capture.__file__)),
        d127.__name__: Path(str(d127.__file__)),
        d127_docker.__name__: Path(str(d127_docker.__file__)),
        d126.__name__: Path(str(d126.__file__)),
        errors_module.__name__: Path(str(errors_module.__file__)),
        runtime_module.__name__: Path(str(runtime_module.__file__)),
        util_module.__name__: Path(str(util_module.__file__)),
    }
    for relative, module_name in LOADED_MODULE_PATHS:
        _require(
            module_files[module_name].resolve(strict=True)
            == (root / relative).resolve(strict=True),
            f"D-132 loaded module path differs: {module_name}",
        )


def _file_binding(root: Path, commit: str, path: Path) -> dict[str, Any]:
    oid, committed = _commit_blob(root, commit, path)
    current = _stable_read(root, path)
    _require(
        committed == current, f"D-132 current file differs from source commit: {path.as_posix()}"
    )
    return {
        "path": path.as_posix(),
        "blob_oid": oid,
        "file_sha256": sha256_bytes(committed),
        "file_bytes": len(committed),
        "current_bytes_match_commit": True,
    }


def _loaded_module_bindings(root: Path, *, source_commit: str) -> list[dict[str, Any]]:
    _assert_runtime_import_boundary(root)
    return [
        {
            "module_name": module_name,
            **_file_binding(root, source_commit, relative),
        }
        for relative, module_name in LOADED_MODULE_PATHS
    ]


def _artifact_binding(
    *, path: Path, payload: dict[str, Any], raw: bytes, status: str
) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": status,
        "recorded_at": payload["semantic_body"]["recorded_at"],
        "artifact_mutated": False,
    }


def _historical_commit_binding(
    root: Path,
    *,
    commit: str,
    tree: str,
    parent: str,
    path: Path,
    blob_oid: str,
    raw: bytes,
    artifact_only: bool,
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(
        identity["tree"] == tree and identity["parents"] == [parent],
        "D-132 predecessor commit differs",
    )
    oid, committed = _commit_blob(root, commit, path)
    _require(oid == blob_oid and committed == raw, "D-132 predecessor committed artifact differs")
    if artifact_only:
        _require(
            _diff_rows(root, commit) == [{"status": "A", "path": path.as_posix()}],
            "D-132 predecessor artifact-only topology differs",
        )
    return {
        "commit": commit,
        "tree": tree,
        "parents": [parent],
        "artifact_path": path.as_posix(),
        "artifact_blob_oid": blob_oid,
        "artifact_file_sha256": sha256_bytes(committed),
        "artifact_file_bytes": len(committed),
        "single_artifact_add_commit"
        if artifact_only
        else "exact_gate_add_and_active_docs_modify_commit": True,
    }


def _exact_gate_artifact(root: Path) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    payload, raw = _read_json(root, d131.OUTPUT_PATH)
    _require(tuple(payload) == GATE_ROOT_KEYS, "D-132 D-131 gate root differs")
    _require(
        payload["schema_version"] == d131.SCHEMA_VERSION
        and payload["gate_id"] == D131_GATE_ID
        and payload["semantic_body_hash"] == D131_BODY_SHA256
        and sha256_bytes(raw) == D131_FILE_SHA256
        and len(raw) == D131_FILE_BYTES
        and payload["semantic_body"].get("status") == d131.STATUS,
        "D-132 D-131 gate tuple differs",
    )
    commit = _historical_commit_binding(
        root,
        commit=D131_EVIDENCE_COMMIT,
        tree=D131_EVIDENCE_TREE,
        parent=D131_EVIDENCE_PARENT,
        path=d131.OUTPUT_PATH,
        blob_oid=D131_GATE_BLOB_OID,
        raw=raw,
        artifact_only=False,
    )
    return payload, raw, commit


def _exact_local_artifact(
    root: Path,
    *,
    path: Path,
    schema: str,
    artifact_id: str,
    body_sha256: str,
    file_sha256: str,
    file_bytes: int,
    status: str,
    commit: str,
    tree: str,
    parent: str,
    blob_oid: str,
) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    payload, raw = _read_json(root, path)
    _require(tuple(payload) == ROOT_KEYS, f"D-132 {path.name} root differs")
    _require(
        payload["schema_version"] == schema
        and payload["artifact_id"] == artifact_id
        and payload["semantic_body_hash"] == body_sha256
        and sha256_bytes(raw) == file_sha256
        and len(raw) == file_bytes
        and payload["semantic_body"].get("status") == status,
        f"D-132 {path.name} exact tuple differs",
    )
    _require(_pretty_bytes(payload) == raw, f"D-132 {path.name} canonical bytes differ")
    commit_binding = _historical_commit_binding(
        root,
        commit=commit,
        tree=tree,
        parent=parent,
        path=path,
        blob_oid=blob_oid,
        raw=raw,
        artifact_only=True,
    )
    return payload, raw, commit_binding


@cache
def _d130_predecessor_binding(root: Path) -> dict[str, Any]:
    gate_payload, gate_raw, gate_commit = _exact_gate_artifact(root)
    receipt_payload, receipt_raw, receipt_commit = _exact_local_artifact(
        root,
        path=d131.RECEIPT_PATH,
        schema=d131.RECEIPT_SCHEMA,
        artifact_id=D130_RECEIPT_ID,
        body_sha256=D130_RECEIPT_BODY_SHA256,
        file_sha256=D130_RECEIPT_FILE_SHA256,
        file_bytes=D130_RECEIPT_FILE_BYTES,
        status=d131.RECEIPT_STATUS,
        commit=D130_RECEIPT_COMMIT,
        tree=D130_RECEIPT_TREE,
        parent=D130_RECEIPT_PARENT,
        blob_oid=D130_RECEIPT_BLOB_OID,
    )
    intent_payload, intent_raw, intent_commit = _exact_local_artifact(
        root,
        path=d131.INTENT_PATH,
        schema=d131.INTENT_SCHEMA,
        artifact_id=D130_INTENT_ID,
        body_sha256=D130_INTENT_BODY_SHA256,
        file_sha256=D130_INTENT_FILE_SHA256,
        file_bytes=D130_INTENT_FILE_BYTES,
        status=d131.INTENT_STATUS,
        commit=D130_INTENT_COMMIT,
        tree=D130_INTENT_TREE,
        parent=D130_INTENT_PARENT,
        blob_oid=D130_INTENT_BLOB_OID,
    )
    receipt_body = receipt_payload["semantic_body"]
    intent_body = intent_payload["semantic_body"]
    _require(
        receipt_body["d131_gate_binding"]["gate_id"] == D131_GATE_ID
        and receipt_body["d131_gate_binding"]["evidence_commit_binding"]["commit"]
        == D131_EVIDENCE_COMMIT,
        "D-132 receipt does not bind the exact D-131 gate",
    )
    _require(
        intent_body["receipt_binding"]["artifact_id"] == D130_RECEIPT_ID
        and intent_body["receipt_commit_binding"]["commit"] == D130_RECEIPT_COMMIT
        and intent_body["armed_state"]["state"] == "ARMED_WAITING_EXACT_ACTIVATION"
        and intent_body["armed_state"]["activation_recorded"] is False
        and intent_body["armed_state"]["external_phase_attempt_created"] is False,
        "D-132 intent does not bind the exact unactivated receipt",
    )
    _require(
        _parse_time(gate_payload["semantic_body"]["recorded_at"], label="D-131 gate recorded_at")
        < _parse_time(receipt_body["recorded_at"], label="D-130 receipt recorded_at")
        < _parse_time(intent_body["recorded_at"], label="D-130 intent recorded_at"),
        "D-132 predecessor chronology differs",
    )
    return {
        "d131_gate": {
            "path": d131.OUTPUT_PATH.as_posix(),
            "gate_id": D131_GATE_ID,
            "semantic_body_hash": D131_BODY_SHA256,
            "file_sha256": D131_FILE_SHA256,
            "file_bytes": D131_FILE_BYTES,
            "status": d131.STATUS,
            "recorded_at": gate_payload["semantic_body"]["recorded_at"],
            "evidence_commit_binding": gate_commit,
            "artifact_mutated": False,
        },
        "d130_local_admission_receipt": {
            **_artifact_binding(
                path=d131.RECEIPT_PATH,
                payload=receipt_payload,
                raw=receipt_raw,
                status=d131.RECEIPT_STATUS,
            ),
            "commit_binding": receipt_commit,
        },
        "d130_armed_intent": {
            **_artifact_binding(
                path=d131.INTENT_PATH,
                payload=intent_payload,
                raw=intent_raw,
                status=d131.INTENT_STATUS,
            ),
            "commit_binding": intent_commit,
            "state": "ARMED_WAITING_EXACT_ACTIVATION",
        },
    }


def _source_identity_for_gate(root: Path) -> dict[str, Any]:
    _assert_runtime_import_boundary(root)
    _require(_status_lines(root) == [], "D-132 source gate requires a clean source commit")
    head = _head(root)
    identity = _commit_identity(root, head)
    _require(
        identity["parents"] == [D130_INTENT_COMMIT],
        "D-132 source must be a sole child of the intent commit",
    )
    expected = [{"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS]
    _require(
        sorted(_diff_rows(root, head), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-132 source commit scope differs",
    )
    return {
        **identity,
        "direct_predecessor_intent_commit": D130_INTENT_COMMIT,
        "implementation_paths_added": [path.as_posix() for path in IMPLEMENTATION_PATHS],
        "file_bindings": [_file_binding(root, head, path) for path in SOURCE_BINDING_PATHS],
        "loaded_module_bindings": _loaded_module_bindings(root, source_commit=head),
        "git_cli_observation": d131._git_cli_observation(root),
        "clean_committed_source": True,
    }


def _validate_source_identity(root: Path, source: Any) -> None:
    _require(isinstance(source, dict), "D-132 source identity differs")
    required = (
        "commit",
        "tree",
        "parents",
        "direct_predecessor_intent_commit",
        "implementation_paths_added",
        "file_bindings",
        "loaded_module_bindings",
        "git_cli_observation",
        "clean_committed_source",
    )
    _require(tuple(source) == required, "D-132 source identity fields differ")
    identity = _commit_identity(root, source["commit"])
    _require(
        {key: source[key] for key in ("commit", "tree", "parents")} == identity,
        "D-132 source commit identity differs",
    )
    _require(
        source["parents"] == [D130_INTENT_COMMIT]
        and source["direct_predecessor_intent_commit"] == D130_INTENT_COMMIT,
        "D-132 source predecessor differs",
    )
    expected = [{"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS]
    _require(
        sorted(_diff_rows(root, source["commit"]), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-132 sealed source scope differs",
    )
    _require(
        source["implementation_paths_added"] == [path.as_posix() for path in IMPLEMENTATION_PATHS]
        and source["file_bindings"]
        == [_file_binding(root, source["commit"], path) for path in SOURCE_BINDING_PATHS]
        and source["loaded_module_bindings"]
        == _loaded_module_bindings(root, source_commit=source["commit"])
        and source["clean_committed_source"] is True,
        "D-132 source provenance differs",
    )
    try:
        d131._validate_git_observation(root, source["git_cli_observation"])
    except ContractError as exc:
        raise D132ActivationOfflineError("D-132 Git observation differs") from exc


def _gate_body(
    *, recorded_at: str, predecessor: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d130-external-activation-successor-offline-source-gate",
        "recorded_at": recorded_at,
        "status": STATUS,
        "predecessor_chain": predecessor,
        "source_identity": source,
        "pre_source_activation_incident": {
            "exact_activation_request_or_challenge_received": True,
            "message_explicitly_said_challenge_is_not_activation": True,
            "effective_activation_approval_recorded": False,
            (
                "activation_message_was_received_before_committed_activation_receipt_writer_existed"
            ): True,
            "received_activation_binding": {
                "request_title": "D-130 external no-call preflight exact activation request",
                "quoted_d131_gate_receipt_intent_and_both_commit_tuples": True,
                "approved_scope": list(d131.ACTIVATION_SCOPE),
                "explicitly_not_authorized": list(d131.ACTIVATION_EXCLUSIONS),
            },
            "activation_receipt_created": False,
            "external_phase_attempt_created": False,
            "external_action_count": 0,
            "activation_exercised": False,
            "activation_is_nonretroactive": True,
            "activation_is_nonreusable_after_d132_topology_change": True,
        },
        "d132_source_preparation_approval": {
            "approval_received": True,
            "approval_mode": "current-user-message-self-attested-unsigned",
            "approval_is_authenticated_or_cryptographically_signed": False,
            "approved_scope": list(D132_SOURCE_PREPARATION_SCOPE),
            "explicitly_not_authorized": list(D132_SOURCE_PREPARATION_EXCLUSIONS),
            "offline_source_only": True,
            "future_writer_or_external_helper_invocation_authorized": False,
        },
        "qualified_activation_contract": {
            "activation_receipt_path": ACTIVATION_RECEIPT_PATH.as_posix(),
            "activation_receipt_schema": ACTIVATION_RECEIPT_SCHEMA,
            "activation_receipt_status": ACTIVATION_RECEIPT_STATUS,
            "activation_receipt_must_be_only_change_in_direct_child_of_gate_evidence": True,
            "phase_order": list(PHASE_PATHS),
            "attempt_paths": [attempt.as_posix() for attempt, _, _ in PHASE_PATHS.values()],
            "action_started_paths": [started.as_posix() for _, started, _ in PHASE_PATHS.values()],
            "terminal_paths": [terminal.as_posix() for _, _, terminal in PHASE_PATHS.values()],
            "attempt_must_be_committed_before_first_phase_action": True,
            "action_started_marker_must_be_durable_immediately_before_external_helper": True,
            "started_without_terminal_is_uncertain_consumed_and_never_retried": True,
            "terminal_transition_must_be_committed_before_next_phase_attempt": True,
            "orphaned_attempt_or_blocked_terminal_consumes_activation": True,
            "historical_d127_d128_top_level_runner_reuse_authorized": False,
            "final_gate_path": FINAL_GATE_PATH.as_posix(),
        },
        "implementation_integrity": {
            "implementation_paths": [path.as_posix() for path in IMPLEMENTATION_PATHS],
            "dependency_paths": [path.as_posix() for path in DEPENDENCY_PATHS],
            "loaded_module_bindings": source["loaded_module_bindings"],
            "gate_builder_activation_receipt_writer_invocation_count": 0,
            "gate_builder_external_runner_invocation_count": 0,
            "gate_builder_docker_helper_invocation_count": 0,
            "gate_builder_pricing_helper_invocation_count": 0,
            "gate_builder_sdk_observation_count": 0,
        },
        "offline_qualification": {
            "exact_gate_receipt_intent_and_commit_topology_bound": True,
            "received_pre_source_activation_preserved_unexercised": True,
            "activation_receipt_only_topology_implemented": True,
            (
                "three_phase_committed_attempt_then-started-marker-"
                "before-action-contract_implemented"
            ): True,
            "append_only_collision_orphan_and_idempotence_fail_closed": True,
            "source_and_loaded_module_provenance_bound": True,
            "offline_builder_performed_no_future_action": True,
        },
        "blocked_prerequisites": [
            "fresh-exact-post-d132-activation-not-recorded",
            "activation-receipt-not-created-or-committed",
            "external-phase-not-started",
        ],
        "evidence_boundary": {
            "gate_is_source_qualification_not_activation": True,
            "pre_source_activation_cannot_be_replayed_or_retroactively_receipted": True,
            "no_credential_sdk_docker_pricing_or_network_observation": True,
            "no_provider_evaluator_agent_memory_hash_candidate_cost_or_ac": True,
        },
        "authority": {
            "fresh_post_d132_activation_recorded": False,
            "activation_receipt_creation_authorized": False,
            "external_phase_authorized": False,
            "official_docs_or_network_call_count": 0,
            "canonical_pricing_capture_get_count": 0,
            "docker_cli_daemon_image_or_container_call_count": 0,
            "sdk_credential_or_endpoint_observation_count": 0,
            "provider_evaluator_agent_call_count": 0,
            "retrieval_or_memory_injection_count": 0,
            "docker_desktop_or_daemon_start_authorized": False,
            "container_create_start_run_exec_authorized": False,
            "provider_evaluator_agent_execution_authorized": False,
            "runtime_memory_injection_or_retrieval_authorized": False,
            "execution_hash_or_candidate_authorized": False,
            "execution_hash_created": False,
            "execution_candidate_created": False,
            "cost_reservation_or_spend_authorized": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_execution_authorized": False,
            "activation_receipt_created_during_source_preparation": False,
            "phase_attempt_created_during_source_preparation": False,
            "external_preflight_or_final_gate_created_during_source_preparation": False,
        },
        "next_gate": {
            "action": "request-fresh-exact-d132-qualified-external-activation",
            (
                "must_quote_d132-gate-and-evidence-plus-d131-gate-d130-receipt-intent-and-commits"
            ): True,
            "fresh_activation_may_create_receipt-only-commit-before-external-actions": True,
            "external_actions_remain_zero_until_fresh_activation": True,
        },
    }


def _validate_gate_payload(
    root: Path,
    payload: Any,
    raw: bytes,
    *,
    require_future_absence: bool,
) -> dict[str, Any]:
    _require(
        isinstance(payload, dict) and tuple(payload) == GATE_ROOT_KEYS, "D-132 gate root differs"
    )
    _require(payload["schema_version"] == SCHEMA_VERSION, "D-132 gate schema differs")
    body = payload["semantic_body"]
    _require(isinstance(body, dict), "D-132 gate body differs")
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload["semantic_body_hash"] == body_hash
        and payload["gate_id"] == f"d132_{body_hash.removeprefix('sha256:')}"
        and _pretty_bytes(payload) == raw,
        "D-132 gate envelope differs",
    )
    predecessor = _d130_predecessor_binding(root)
    source = body.get("source_identity")
    _validate_source_identity(root, source)
    expected = _gate_envelope(
        _gate_body(
            recorded_at=body.get("recorded_at"),
            predecessor=predecessor,
            source=source,
        )
    )
    _require(canonical_json(payload) == canonical_json(expected), "D-132 gate full rebuild differs")
    _require(
        _parse_time(body["recorded_at"], label="gate recorded_at")
        > _parse_time(predecessor["d130_armed_intent"]["recorded_at"], label="intent recorded_at"),
        "D-132 gate predates the armed intent",
    )
    if require_future_absence:
        for path in FUTURE_PATHS:
            _path_absent(root, path)
    return payload


def _rebuild_gate_evidence_commit(
    root: Path, *, commit: str, source: dict[str, Any], gate_raw: bytes
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [source["commit"]], "D-132 gate evidence parent differs")
    expected = [
        {"status": "A", "path": OUTPUT_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
    ]
    _require(
        sorted(_diff_rows(root, commit), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-132 gate evidence scope differs",
    )
    oid, committed = _commit_blob(root, commit, OUTPUT_PATH)
    _require(committed == gate_raw, "D-132 gate evidence bytes differ")
    return {
        "commit": commit,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "artifact_path": OUTPUT_PATH.as_posix(),
        "artifact_blob_oid": oid,
        "artifact_file_sha256": sha256_bytes(committed),
        "artifact_file_bytes": len(committed),
        "exact_gate_add_and_active_docs_modify_commit": True,
    }


def _gate_result(
    payload: dict[str, Any], raw: bytes, *, evidence_commit: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        "status": STATUS,
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "source_commit": payload["semantic_body"]["source_identity"]["commit"],
        "evidence_commit": None if evidence_commit is None else evidence_commit["commit"],
        "fresh_activation_required": True,
        "pre_source_activation_exercised": False,
        "external_call_count": 0,
    }


@_fresh_validation_cache
def run_d132_offline_source_gate(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Build the D-132 source gate without invoking future or external paths."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    if os.path.lexists(root / OUTPUT_PATH):
        return validate_d132_offline_source_gate(repository=root)
    for path in FUTURE_PATHS:
        _path_absent(root, path)
    predecessor = _d130_predecessor_binding(root)
    source = _source_identity_for_gate(root)
    recorded_at = _now()
    _require(
        _parse_time(recorded_at, label="gate recorded_at")
        > _parse_time(predecessor["d130_armed_intent"]["recorded_at"], label="intent recorded_at"),
        "D-132 gate does not follow the intent",
    )
    payload = _gate_envelope(
        _gate_body(recorded_at=recorded_at, predecessor=predecessor, source=source)
    )
    raw = _pretty_bytes(payload)
    _validate_gate_payload(root, payload, raw, require_future_absence=True)
    _write_new(root, OUTPUT_PATH, raw)
    return validate_d132_offline_source_gate(repository=root)


@_fresh_validation_cache
def validate_d132_offline_source_gate(
    *,
    repository: str | Path | None = None,
    mode: Literal["current-source", "post-evidence-commit"] = "current-source",
) -> dict[str, Any]:
    """Replay the offline source gate without future writers or external observations."""

    root = _repo_root(repository)
    payload, raw = _read_json(root, OUTPUT_PATH)
    validated = _validate_gate_payload(root, payload, raw, require_future_absence=True)
    source = validated["semantic_body"]["source_identity"]
    evidence_commit = None
    if mode == "current-source":
        _require(_head(root) == source["commit"], "D-132 current source HEAD differs")
        _require(
            _status_lines(root) == [f"?? {OUTPUT_PATH.as_posix()}"],
            "D-132 current-source checkout differs",
        )
    elif mode == "post-evidence-commit":
        _require(_status_lines(root) == [], "D-132 post-evidence checkout is not clean")
        evidence_commit = _rebuild_gate_evidence_commit(
            root, commit=_head(root), source=source, gate_raw=raw
        )
    else:
        raise D132ActivationOfflineError("D-132 offline validation mode differs")
    return _gate_result(validated, raw, evidence_commit=evidence_commit)


def _d132_gate_for_activation(
    root: Path, *, stored_commit: dict[str, Any] | None = None
) -> tuple[dict[str, Any], bytes, dict[str, Any], dict[str, Any]]:
    payload, raw = _read_json(root, OUTPUT_PATH)
    payload = _validate_gate_payload(root, payload, raw, require_future_absence=False)
    source = payload["semantic_body"]["source_identity"]
    if stored_commit is None:
        _require(
            _status_lines(root) == [], "D-132 activation requires a clean gate evidence commit"
        )
        gate_commit = _rebuild_gate_evidence_commit(
            root, commit=_head(root), source=source, gate_raw=raw
        )
    else:
        _require(isinstance(stored_commit, dict), "D-132 stored gate commit differs")
        gate_commit = _rebuild_gate_evidence_commit(
            root, commit=stored_commit.get("commit", ""), source=source, gate_raw=raw
        )
        _require(
            canonical_json(stored_commit) == canonical_json(gate_commit),
            "D-132 stored gate commit full rebuild differs",
        )
    binding = {
        "path": OUTPUT_PATH.as_posix(),
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": STATUS,
        "recorded_at": payload["semantic_body"]["recorded_at"],
        "source_commit": source["commit"],
        "evidence_commit_binding": gate_commit,
        "artifact_mutated": False,
    }
    return payload, raw, source, binding


@_fresh_validation_cache
def render_d132_external_activation_template(*, repository: str | Path | None = None) -> str:
    """Render the explicit fresh post-D-132 activation approval response."""

    root = _repo_root(repository)
    _payload, _raw, _source, gate = _d132_gate_for_activation(root)
    predecessor = _d130_predecessor_binding(root)
    g131 = predecessor["d131_gate"]
    receipt = predecessor["d130_local_admission_receipt"]
    intent = predecessor["d130_armed_intent"]
    lines = [
        "D-132-qualified D-130 external no-call preflight fresh exact activation approval",
        "",
        f"D-132 gate: {gate['gate_id']}",
        f"D-132 gate body SHA: {gate['semantic_body_hash']}",
        f"D-132 gate file SHA: {gate['file_sha256']}",
        f"D-132 gate file bytes: {gate['file_bytes']}",
        f"D-132 gate evidence commit tuple: {canonical_json(gate['evidence_commit_binding'])}",
        f"D-131 gate: {g131['gate_id']}",
        f"D-131 gate body SHA: {g131['semantic_body_hash']}",
        f"D-131 gate file SHA: {g131['file_sha256']}",
        f"D-131 gate file bytes: {g131['file_bytes']}",
        f"D-131 gate evidence commit tuple: {canonical_json(g131['evidence_commit_binding'])}",
        f"D-130 local receipt ID: {receipt['artifact_id']}",
        f"D-130 local receipt body SHA: {receipt['semantic_body_hash']}",
        f"D-130 local receipt file SHA: {receipt['file_sha256']}",
        f"D-130 local receipt file bytes: {receipt['file_bytes']}",
        f"D-130 local receipt commit tuple: {canonical_json(receipt['commit_binding'])}",
        f"D-130 armed intent ID: {intent['artifact_id']}",
        f"D-130 armed intent body SHA: {intent['semantic_body_hash']}",
        f"D-130 armed intent file SHA: {intent['file_sha256']}",
        f"D-130 armed intent file bytes: {intent['file_bytes']}",
        f"D-130 armed intent commit tuple: {canonical_json(intent['commit_binding'])}",
        "",
        "Approved scope:",
        *(f"- {item}" for item in FRESH_ACTIVATION_SCOPE),
        "",
        "Explicitly not authorized:",
        *(f"- {item}" for item in FRESH_ACTIVATION_EXCLUSIONS),
        "",
        "The pre-D-132 request/challenge was not effective activation and is non-reusable.",
        "I approve the exact ordered scope above under every quoted tuple and exclusion.",
        "I understand that each phase attempt must be committed before its external action,",
        "and that an ACTION_STARTED marker without a terminal consumes activation "
        "and is never retried.",
    ]
    return "\n".join(lines)


def _rebuild_single_artifact_commit(
    root: Path,
    *,
    commit: str,
    parent: str,
    path: Path,
    raw: bytes,
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [parent], f"D-132 {path.name} commit parent differs")
    _require(
        _diff_rows(root, commit) == [{"status": "A", "path": path.as_posix()}],
        f"D-132 {path.name} commit is not artifact-only",
    )
    oid, committed = _commit_blob(root, commit, path)
    _require(committed == raw, f"D-132 {path.name} commit bytes differ")
    return {
        "commit": commit,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "artifact_path": path.as_posix(),
        "artifact_blob_oid": oid,
        "artifact_file_sha256": sha256_bytes(committed),
        "artifact_file_bytes": len(committed),
        "single_artifact_add_commit": True,
    }


def _activation_receipt_body(
    *,
    recorded_at: str,
    gate: dict[str, Any],
    predecessor: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": "D-132/D-130-external-activation",
        "evidence_kind": "fresh-exact-external-no-call-preflight-activation-receipt",
        "recorded_at": recorded_at,
        "status": ACTIVATION_RECEIPT_STATUS,
        "d132_gate_binding": gate,
        "d130_predecessor_chain": predecessor,
        "source_identity": source,
        "loaded_module_bindings": source["loaded_module_bindings"],
        "activation_approval": {
            "approval_mode": "current-user-message-self-attested-unsigned",
            "approval_is_authenticated_or_cryptographically_signed": False,
            "quotes_d132_gate_and_evidence_commit": True,
            "quotes_d131_gate_d130_receipt_intent_and_all_commit_tuples": True,
            "approved_scope": list(FRESH_ACTIVATION_SCOPE),
            "explicitly_not_authorized": list(FRESH_ACTIVATION_EXCLUSIONS),
            "pre_source_activation_reused": False,
            "fresh_post_d132_activation": True,
        },
        "event_order": [
            {"ordinal": 1, "event": "d132-offline-source-gate-committed"},
            {"ordinal": 2, "event": "fresh-exact-post-d132-activation-approved"},
            {"ordinal": 3, "event": "activation-receipt-recorded"},
        ],
        "phase_commit_contract": {
            "activation_receipt_must_be_committed_as_exact_receipt-only-child": True,
            "each_attempt_must_be_committed_as_exact-attempt-only-child": True,
            "action_started_marker_is_written_immediately_before_external_helper": True,
            "started_without_terminal_is_uncertain_consumed_and_never_retried": True,
            "started_plus_terminal_transition_must_be_committed_before_next_attempt": True,
            "final_gate_plus_active_docs_commit_follows_last_terminal_transition": True,
        },
        "activity_accounting": {
            "official_docs_or_network_call_count": 0,
            "canonical_pricing_capture_get_count": 0,
            "docker_cli_daemon_image_or_container_call_count": 0,
            "sdk_credential_or_endpoint_observation_count": 0,
            "provider_evaluator_agent_call_count": 0,
            "retrieval_or_memory_injection_count": 0,
            "cost_reserved_or_spent_usd": "0",
        },
        "evidence_boundary": {
            "receipt_writer_reads_dotenv_or_credential_value": False,
            "receipt_writer_reads_parent_environment_values_for_git": False,
            "receipt_writer_uses_fixed_literal_secret_free_git_environment": True,
            "receipt_writer_external_call_count": 0,
            "receipt_is_not_phase-attempt-or-external-action": True,
            "receipt_is_append-only-new-or-exact-idempotent": True,
        },
        "authority": {
            "fresh_activation_recorded": True,
            "activation_receipt_created": True,
            "activation_receipt_committed": False,
            "phase_attempt_creation_before_receipt_commit_authorized": False,
            "external_action_before_committed_phase_attempt_authorized": False,
            "docker_desktop_or_daemon_start_authorized": False,
            "container_create_start_run_exec_authorized": False,
            "provider_evaluator_agent_execution_authorized": False,
            "runtime_memory_injection_or_retrieval_authorized": False,
            "execution_hash_or_candidate_authorized": False,
            "cost_reservation_or_spend_authorized": False,
            "four_row_ac_execution_authorized": False,
        },
        "next_gate": {
            "action": "commit-activation-receipt-only-then-create-docker-attempt-only",
            "external_actions_remain_zero_until-docker-attempt-is-committed": True,
        },
    }


def _validate_activation_receipt_payload(
    root: Path,
    payload: Any,
    raw: bytes,
    *,
    require_downstream_absence: bool,
) -> dict[str, Any]:
    _require(
        isinstance(payload, dict) and tuple(payload) == ROOT_KEYS,
        "D-132 activation receipt root differs",
    )
    _require(
        payload["schema_version"] == ACTIVATION_RECEIPT_SCHEMA,
        "D-132 activation receipt schema differs",
    )
    body = payload["semantic_body"]
    _require(isinstance(body, dict), "D-132 activation receipt body differs")
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload["semantic_body_hash"] == body_hash
        and payload["artifact_id"] == f"d132d130activation_{body_hash.removeprefix('sha256:')}"
        and _pretty_bytes(payload) == raw,
        "D-132 activation receipt envelope differs",
    )
    gate_commit = body.get("d132_gate_binding", {}).get("evidence_commit_binding")
    _gate_payload, _gate_raw, source, gate = _d132_gate_for_activation(
        root, stored_commit=gate_commit
    )
    predecessor = _d130_predecessor_binding(root)
    expected = _envelope(
        ACTIVATION_RECEIPT_SCHEMA,
        "d132d130activation",
        _activation_receipt_body(
            recorded_at=body.get("recorded_at"),
            gate=gate,
            predecessor=predecessor,
            source=source,
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected),
        "D-132 activation receipt full rebuild differs",
    )
    _require(
        _parse_time(body["recorded_at"], label="activation receipt recorded_at")
        > _parse_time(gate["recorded_at"], label="D-132 gate recorded_at"),
        "D-132 activation receipt chronology differs",
    )
    if require_downstream_absence:
        for path in FUTURE_PATHS[1:]:
            _path_absent(root, path)
    return payload


def _activation_receipt_result(
    payload: dict[str, Any],
    raw: bytes,
    *,
    receipt_commit: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "status": ACTIVATION_RECEIPT_STATUS,
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "receipt_commit": None if receipt_commit is None else receipt_commit["commit"],
        "external_activity_started": False,
        "external_call_count": 0,
    }


@_fresh_validation_cache
def create_d130_external_activation_receipt(
    *, repository: str | Path | None = None
) -> dict[str, Any]:
    """Create the fresh activation receipt without any external observation."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    downstream = FUTURE_PATHS[1:]
    for path in downstream:
        _path_absent(root, path)
    if os.path.lexists(root / ACTIVATION_RECEIPT_PATH):
        mode: Literal["receipt", "post-receipt-commit"] = (
            "post-receipt-commit" if _status_lines(root) == [] else "receipt"
        )
        return validate_d130_external_activation_receipt(repository=root, mode=mode)
    _gate_payload, _gate_raw, source, gate = _d132_gate_for_activation(root)
    predecessor = _d130_predecessor_binding(root)
    recorded_at = _now()
    _require(
        _parse_time(recorded_at, label="activation receipt recorded_at")
        > _parse_time(gate["recorded_at"], label="D-132 gate recorded_at"),
        "D-132 activation receipt predates the gate",
    )
    payload = _envelope(
        ACTIVATION_RECEIPT_SCHEMA,
        "d132d130activation",
        _activation_receipt_body(
            recorded_at=recorded_at,
            gate=gate,
            predecessor=predecessor,
            source=source,
        ),
    )
    raw = _pretty_bytes(payload)
    _validate_activation_receipt_payload(root, payload, raw, require_downstream_absence=True)
    _write_new(root, ACTIVATION_RECEIPT_PATH, raw)
    return validate_d130_external_activation_receipt(repository=root, mode="receipt")


@_fresh_validation_cache
def validate_d130_external_activation_receipt(
    *,
    repository: str | Path | None = None,
    mode: Literal["receipt", "post-receipt-commit"] = "receipt",
) -> dict[str, Any]:
    """Validate the activation receipt and optional exact receipt-only commit."""

    root = _repo_root(repository)
    payload, raw = _read_json(root, ACTIVATION_RECEIPT_PATH)
    payload = _validate_activation_receipt_payload(
        root, payload, raw, require_downstream_absence=True
    )
    gate_commit = payload["semantic_body"]["d132_gate_binding"]["evidence_commit_binding"]
    receipt_commit = None
    if mode == "receipt":
        _require(
            _head(root) == gate_commit["commit"],
            "D-132 uncommitted activation receipt HEAD differs",
        )
        _require(
            _status_lines(root) == [f"?? {ACTIVATION_RECEIPT_PATH.as_posix()}"],
            "D-132 activation receipt checkout differs",
        )
    elif mode == "post-receipt-commit":
        _require(_status_lines(root) == [], "D-132 activation receipt commit is not clean")
        receipt_commit = _rebuild_single_artifact_commit(
            root,
            commit=_head(root),
            parent=gate_commit["commit"],
            path=ACTIVATION_RECEIPT_PATH,
            raw=raw,
        )
    else:
        raise D132ActivationOfflineError("D-132 activation receipt validation mode differs")
    return _activation_receipt_result(payload, raw, receipt_commit=receipt_commit)


@cache
def _load_activation_receipt(root: Path) -> tuple[dict[str, Any], bytes]:
    payload, raw = _read_json(root, ACTIVATION_RECEIPT_PATH)
    return (
        _validate_activation_receipt_payload(root, payload, raw, require_downstream_absence=False),
        raw,
    )


def _activation_receipt_binding(payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return _artifact_binding(
        path=ACTIVATION_RECEIPT_PATH,
        payload=payload,
        raw=raw,
        status=ACTIVATION_RECEIPT_STATUS,
    )


def _rebuild_activation_receipt_commit(
    root: Path,
    *,
    commit: str,
    receipt_payload: dict[str, Any],
    receipt_raw: bytes,
) -> dict[str, Any]:
    gate_commit = receipt_payload["semantic_body"]["d132_gate_binding"]["evidence_commit_binding"]
    return _rebuild_single_artifact_commit(
        root,
        commit=commit,
        parent=gate_commit["commit"],
        path=ACTIVATION_RECEIPT_PATH,
        raw=receipt_raw,
    )


def _current_receipt_commit_identity(root: Path) -> dict[str, Any]:
    receipt, receipt_raw = _load_activation_receipt(root)
    _require(_status_lines(root) == [], "D-132 receipt commit state is not clean")
    return _rebuild_activation_receipt_commit(
        root,
        commit=_head(root),
        receipt_payload=receipt,
        receipt_raw=receipt_raw,
    )


def _require_external_helper_contracts() -> None:
    _require(
        docker_remediation.APPROVED_CLI_VERSION == "29.6.2"
        and docker_remediation.APPROVED_CLI_BYTES == 43_095_472
        and docker_remediation.APPROVED_CLI_SHA256
        == "sha256:8985cd8ac002c3240b5aa48fe401fcb55dca5d849b537e3c835564e8e8c49a70"
        and docker_remediation.LOCAL_DOCKER_ENDPOINT == "npipe:////./pipe/dockerDesktopLinuxEngine"
        and len(tuple(docker_remediation.EXACT_DOCKER_IMAGES)) == 2,
        "D-132 exact Docker helper contract differs",
    )
    _require(
        not hasattr(docker_remediation, "ALLOW_DAEMON_START_WITH_UNVERIFIED_RESTART_STATE")
        or docker_remediation.ALLOW_DAEMON_START_WITH_UNVERIFIED_RESTART_STATE is False,
        "D-132 Docker helper permits daemon start",
    )
    _require(
        pricing_capture.OFFICIAL_MODEL_PAGE_URL
        == "https://developers.openai.com/api/docs/models/gpt-5.4-mini.md"
        and pricing_capture.MODEL_ID == "gpt-5.4-mini-2026-03-17"
        and str(pricing_capture.INPUT_RATE) == "0.75"
        and str(pricing_capture.CACHED_INPUT_RATE) == "0.075"
        and str(pricing_capture.OUTPUT_RATE) == "4.5"
        and pricing_capture.MAX_DECODED_ENTITY_BYTES == 128_000,
        "D-132 bounded pricing helper contract differs",
    )


def _loaded_sdk_module_bindings(root: Path) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for module_name in SDK_MODULE_NAMES:
        module = sys.modules.get(module_name)
        module_file = getattr(module, "__file__", None)
        if not isinstance(module_file, str):
            continue
        try:
            path = Path(module_file).resolve(strict=True)
            file_binding = d127._bounded_external_file_binding(path, maximum_bytes=4 * 1024 * 1024)
        except (OSError, ContractError) as exc:
            raise D132ActivationOfflineError(
                f"D-132 loaded {module_name} module binding failed"
            ) from exc
        bindings.append(
            {
                "module_name": module_name,
                "resolved_path": str(path),
                **file_binding,
                "under_repository_venv": path.is_relative_to(root / ".venv"),
            }
        )
    return bindings


def _sdk_observation(
    root: Path, source: dict[str, Any], factory_checks: dict[str, bool]
) -> dict[str, Any]:
    python_routing = {
        name: bool(os.environ.get(name)) for name in d127.FORBIDDEN_PYTHON_ROUTING_ENV_NAMES
    }
    if any(python_routing.values()):
        return {
            "python_routing_environment_presence": python_routing,
            "python_routing_environment_values_persisted": False,
            "d127_sdk_probe_skipped_due_to_python_routing": True,
            "loaded_sdk_module_bindings": _loaded_sdk_module_bindings(root),
            "d127_sdk_observation": None,
        }
    try:
        observation = d127._sdk_observation(root, source, factory_checks)
    except ContractError as exc:
        raise D132ActivationOfflineError("D-132 SDK no-call observation failed") from exc
    return {
        "python_routing_environment_presence": python_routing,
        "python_routing_environment_values_persisted": False,
        "d127_sdk_probe_skipped_due_to_python_routing": False,
        "loaded_sdk_module_bindings": _loaded_sdk_module_bindings(root),
        "d127_sdk_observation": observation,
    }


def _validate_sdk_module_bindings(root: Path, value: Any) -> list[dict[str, Any]]:
    _require(isinstance(value, list), "D-132 loaded SDK module bindings differ")
    names: list[str] = []
    for binding in value:
        _require(
            isinstance(binding, dict)
            and tuple(binding)
            == (
                "module_name",
                "resolved_path",
                "file_name",
                "file_bytes",
                "file_sha256",
                "linklike",
                "under_repository_venv",
            )
            and binding["module_name"] in SDK_MODULE_NAMES
            and binding["module_name"] not in names
            and isinstance(binding["resolved_path"], str),
            "D-132 loaded SDK module binding shape differs",
        )
        path = Path(binding["resolved_path"])
        _require(path.is_absolute(), "D-132 loaded SDK module path is not absolute")
        try:
            resolved = path.resolve(strict=True)
            expected_file = d127._bounded_external_file_binding(
                resolved, maximum_bytes=4 * 1024 * 1024
            )
        except (OSError, ContractError) as exc:
            raise D132ActivationOfflineError("D-132 loaded SDK module file replay failed") from exc
        expected = {
            "module_name": binding["module_name"],
            "resolved_path": str(resolved),
            **expected_file,
            "under_repository_venv": resolved.is_relative_to(root / ".venv"),
        }
        _require(
            canonical_json(binding) == canonical_json(expected),
            "D-132 loaded SDK module binding differs",
        )
        names.append(binding["module_name"])
    _require(
        names == [name for name in SDK_MODULE_NAMES if name in names],
        "D-132 SDK module order differs",
    )
    return value


def _validate_sdk_observation(root: Path, value: Any, *, source: dict[str, Any]) -> None:
    _require(
        isinstance(value, dict) and tuple(value) == SDK_WRAPPER_KEYS,
        "D-132 SDK wrapper fields differ",
    )
    routing = value["python_routing_environment_presence"]
    _require(
        isinstance(routing, dict)
        and tuple(routing) == d127.FORBIDDEN_PYTHON_ROUTING_ENV_NAMES
        and all(type(present) is bool for present in routing.values())
        and value["python_routing_environment_values_persisted"] is False,
        "D-132 Python routing presence evidence differs",
    )
    _validate_sdk_module_bindings(root, value["loaded_sdk_module_bindings"])
    skipped = value["d127_sdk_probe_skipped_due_to_python_routing"]
    if any(routing.values()):
        _require(
            skipped is True and value["d127_sdk_observation"] is None,
            "D-132 routed Python environment did not skip the D-127 SDK probe",
        )
        return
    _require(skipped is False, "D-132 clean Python routing unexpectedly skipped SDK probe")
    try:
        d127._validate_sdk_observation(root, value["d127_sdk_observation"], source=source)
    except ContractError as exc:
        raise D132ActivationOfflineError("D-132 SDK no-call evidence differs") from exc


def _write_artifact(
    root: Path, path: Path, *, schema: str, prefix: str, body: dict[str, Any]
) -> dict[str, Any]:
    payload = _envelope(schema, prefix, body)
    _write_new(root, path, _pretty_bytes(payload))
    stored, _raw = _read_json(root, path)
    return stored


def _load_envelope(
    root: Path, path: Path, *, schema: str, prefix: str
) -> tuple[dict[str, Any], bytes]:
    payload, raw = _read_json(root, path)
    _require(tuple(payload) == ROOT_KEYS, f"D-132 {path.name} root differs")
    body = payload.get("semantic_body")
    _require(
        payload.get("schema_version") == schema and isinstance(body, dict),
        f"D-132 {path.name} schema differs",
    )
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload.get("semantic_body_hash") == body_hash
        and payload.get("artifact_id") == f"{prefix}_{body_hash.removeprefix('sha256:')}"
        and _pretty_bytes(payload) == raw,
        f"D-132 {path.name} envelope differs",
    )
    return payload, raw


def _phase_index(phase: str) -> int:
    phases = list(PHASE_PATHS)
    _require(phase in phases, "D-132 external phase differs")
    return phases.index(phase)


def _phase_prefix(phase: str) -> str:
    return "d132d130" + phase.replace("-", "")


def _attempt_body(
    *,
    phase: str,
    recorded_at: str,
    receipt: dict[str, Any],
    receipt_commit: dict[str, Any],
    source: dict[str, Any],
    parent_commit: dict[str, Any],
    predecessor_terminal: dict[str, Any] | None,
) -> dict[str, Any]:
    _phase_index(phase)
    return {
        "milestone": "D-132/D-130-external-activation",
        "evidence_kind": "committed-before-action-external-phase-attempt-intent",
        "recorded_at": recorded_at,
        "status": f"D132_D130_{phase.replace('-', '_').upper()}_ATTEMPT_RECORDED_COMMIT_REQUIRED",
        "phase": phase,
        "activation_receipt_binding": receipt,
        "activation_receipt_commit_binding": receipt_commit,
        "source_identity": source,
        "loaded_module_bindings": source["loaded_module_bindings"],
        "parent_commit_binding": parent_commit,
        "predecessor_terminal_binding": predecessor_terminal,
        "authority": {
            "authorized_actions_after_exact_attempt_commit": PHASE_ACTIONS[phase],
            "external_action_before_exact_attempt_commit_authorized": False,
            "docker_desktop_or_daemon_start_authorized": False,
            "container_create_start_run_exec_authorized": False,
            "provider_evaluator_agent_execution_authorized": False,
            "runtime_memory_injection_or_retrieval_authorized": False,
            "execution_hash_or_candidate_authorized": False,
            "cost_reservation_or_spend_authorized": False,
        },
        "failure_boundary": {
            "attempt_writer_external_call_count": 0,
            "attempt_must_be_exact-attempt-only-commit-before-action": True,
            "action_started_marker_required_immediately-before-helper": True,
            "started_without_terminal_is_uncertain_consumed_and_never_retried": True,
        },
    }


def _validate_parent_commit_binding(root: Path, *, phase: str, value: Any) -> dict[str, Any]:
    index = _phase_index(phase)
    if index == 0:
        receipt, receipt_raw = _load_activation_receipt(root)
        rebuilt = _rebuild_activation_receipt_commit(
            root,
            commit=value.get("commit", "") if isinstance(value, dict) else "",
            receipt_payload=receipt,
            receipt_raw=receipt_raw,
        )
    else:
        previous = list(PHASE_PATHS)[index - 1]
        rebuilt = _rebuild_phase_transition_commit(
            root,
            phase=previous,
            commit=value.get("commit", "") if isinstance(value, dict) else "",
        )
    _require(
        isinstance(value, dict) and canonical_json(value) == canonical_json(rebuilt),
        f"D-132 {phase} parent commit binding differs",
    )
    return rebuilt


@cache
def _validate_attempt_artifact(root: Path, phase: str) -> tuple[dict[str, Any], bytes]:
    attempt_path, _started_path, _terminal_path = PHASE_PATHS[phase]
    prefix = _phase_prefix(phase) + "attempt"
    payload, raw = _load_envelope(root, attempt_path, schema=ATTEMPT_SCHEMA, prefix=prefix)
    body = payload["semantic_body"]
    receipt, receipt_raw = _load_activation_receipt(root)
    receipt_binding = _activation_receipt_binding(receipt, receipt_raw)
    receipt_commit_value = body.get("activation_receipt_commit_binding")
    receipt_commit = _rebuild_activation_receipt_commit(
        root,
        commit=(
            receipt_commit_value.get("commit", "") if isinstance(receipt_commit_value, dict) else ""
        ),
        receipt_payload=receipt,
        receipt_raw=receipt_raw,
    )
    _require(
        canonical_json(receipt_commit_value) == canonical_json(receipt_commit),
        "D-132 attempt activation receipt commit differs",
    )
    source = receipt["semantic_body"]["source_identity"]
    parent = _validate_parent_commit_binding(
        root, phase=phase, value=body.get("parent_commit_binding")
    )
    predecessor_terminal = None
    index = _phase_index(phase)
    if index > 0:
        previous = list(PHASE_PATHS)[index - 1]
        previous_payload, previous_raw = _validate_terminal_artifact(root, previous)
        predecessor_terminal = _artifact_binding(
            path=PHASE_PATHS[previous][2],
            payload=previous_payload,
            raw=previous_raw,
            status=previous_payload["semantic_body"]["status"],
        )
        _require(
            previous_payload["semantic_body"].get("phase_ready_for_successor") is True,
            f"D-132 {phase} predecessor phase is not ready",
        )
    expected = _envelope(
        ATTEMPT_SCHEMA,
        prefix,
        _attempt_body(
            phase=phase,
            recorded_at=body.get("recorded_at"),
            receipt=receipt_binding,
            receipt_commit=receipt_commit,
            source=source,
            parent_commit=parent,
            predecessor_terminal=predecessor_terminal,
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected),
        f"D-132 {phase} attempt full rebuild differs",
    )
    lower = (
        receipt["semantic_body"]["recorded_at"]
        if predecessor_terminal is None
        else predecessor_terminal["recorded_at"]
    )
    _require(
        _parse_time(body["recorded_at"], label=f"{phase} attempt recorded_at")
        > _parse_time(lower, label=f"{phase} predecessor recorded_at"),
        f"D-132 {phase} attempt chronology differs",
    )
    return payload, raw


def _create_attempt_artifact(
    root: Path,
    *,
    phase: str,
    parent_commit: dict[str, Any],
    predecessor_terminal: dict[str, Any] | None,
) -> tuple[dict[str, Any], bytes]:
    _clear_validation_caches()
    attempt_path, started_path, terminal_path = PHASE_PATHS[phase]
    for path in (attempt_path, started_path, terminal_path):
        _path_absent(root, path)
    _require(_status_lines(root) == [], f"D-132 {phase} attempt requires clean parent commit")
    receipt, receipt_raw = _load_activation_receipt(root)
    receipt_binding = _activation_receipt_binding(receipt, receipt_raw)
    index = _phase_index(phase)
    if index == 0:
        fresh_parent = _current_receipt_commit_identity(root)
        fresh_predecessor_terminal = None
        _require(
            predecessor_terminal is None,
            "D-132 first phase unexpectedly has a predecessor terminal",
        )
        receipt_commit_value = fresh_parent
    else:
        previous = list(PHASE_PATHS)[index - 1]
        fresh_parent = _current_phase_transition_commit_identity(root, phase=previous)
        previous_payload, previous_raw = _validate_terminal_artifact(root, previous)
        _require(
            previous_payload["semantic_body"]["phase_ready_for_successor"] is True,
            f"D-132 {phase} predecessor phase is not ready",
        )
        fresh_predecessor_terminal = _artifact_binding(
            path=PHASE_PATHS[previous][2],
            payload=previous_payload,
            raw=previous_raw,
            status=previous_payload["semantic_body"]["status"],
        )
        first_attempt, _ = _validate_attempt_artifact(root, list(PHASE_PATHS)[0])
        stored = first_attempt["semantic_body"]["activation_receipt_commit_binding"]
        receipt_commit_value = _rebuild_activation_receipt_commit(
            root,
            commit=stored["commit"],
            receipt_payload=receipt,
            receipt_raw=receipt_raw,
        )
    _require(
        canonical_json(parent_commit) == canonical_json(fresh_parent),
        f"D-132 {phase} attempt parent drifted before publication",
    )
    _require(
        canonical_json(predecessor_terminal) == canonical_json(fresh_predecessor_terminal),
        f"D-132 {phase} predecessor terminal drifted before publication",
    )
    parent_commit = fresh_parent
    predecessor_terminal = fresh_predecessor_terminal
    recorded_at = _now()
    lower = (
        receipt["semantic_body"]["recorded_at"]
        if predecessor_terminal is None
        else predecessor_terminal["recorded_at"]
    )
    _require(
        _parse_time(recorded_at, label=f"{phase} attempt recorded_at")
        > _parse_time(lower, label=f"{phase} predecessor recorded_at"),
        f"D-132 {phase} attempt clock regressed",
    )
    body = _attempt_body(
        phase=phase,
        recorded_at=recorded_at,
        receipt=receipt_binding,
        receipt_commit=receipt_commit_value,
        source=receipt["semantic_body"]["source_identity"],
        parent_commit=parent_commit,
        predecessor_terminal=predecessor_terminal,
    )
    prefix = _phase_prefix(phase) + "attempt"
    _write_artifact(root, attempt_path, schema=ATTEMPT_SCHEMA, prefix=prefix, body=body)
    return _validate_attempt_artifact(root, phase)


@cache
def _rebuild_attempt_commit(root: Path, *, phase: str, commit: str) -> dict[str, Any]:
    attempt, attempt_raw = _validate_attempt_artifact(root, phase)
    parent = attempt["semantic_body"]["parent_commit_binding"]
    return _rebuild_single_artifact_commit(
        root,
        commit=commit,
        parent=parent["commit"],
        path=PHASE_PATHS[phase][0],
        raw=attempt_raw,
    )


def _current_attempt_commit_identity(root: Path, *, phase: str) -> dict[str, Any]:
    _require(_status_lines(root) == [], f"D-132 {phase} attempt commit is not clean")
    return _rebuild_attempt_commit(root, phase=phase, commit=_head(root))


def _action_started_body(
    *,
    phase: str,
    recorded_at: str,
    attempt: dict[str, Any],
    attempt_commit: dict[str, Any],
    receipt: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": "D-132/D-130-external-activation",
        "evidence_kind": "append-only-external-action-started-marker",
        "recorded_at": recorded_at,
        "status": f"D132_D130_{phase.replace('-', '_').upper()}_ACTION_STARTED",
        "phase": phase,
        "activation_receipt_binding": receipt,
        "source_identity": source,
        "attempt_binding": attempt,
        "attempt_commit_binding": attempt_commit,
        "activity_before_marker": {
            "phase_external_action_count": 0,
            "provider_evaluator_agent_call_count": 0,
            "container_create_start_run_exec_count": 0,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
        },
        "failure_boundary": {
            "marker_is_fsynced_immediately_before_external_helper": True,
            "marker_without_terminal_means_action_state_is_uncertain": True,
            "marker_without_terminal_consumes_activation_and_forbids_retry": True,
        },
    }


@cache
def _validate_action_started_artifact(root: Path, phase: str) -> tuple[dict[str, Any], bytes]:
    attempt_path, started_path, _terminal_path = PHASE_PATHS[phase]
    del attempt_path
    prefix = _phase_prefix(phase) + "started"
    payload, raw = _load_envelope(root, started_path, schema=ACTION_STARTED_SCHEMA, prefix=prefix)
    body = payload["semantic_body"]
    attempt, attempt_raw = _validate_attempt_artifact(root, phase)
    attempt_binding = _artifact_binding(
        path=PHASE_PATHS[phase][0],
        payload=attempt,
        raw=attempt_raw,
        status=attempt["semantic_body"]["status"],
    )
    attempt_commit_value = body.get("attempt_commit_binding")
    attempt_commit = _rebuild_attempt_commit(
        root,
        phase=phase,
        commit=(
            attempt_commit_value.get("commit", "") if isinstance(attempt_commit_value, dict) else ""
        ),
    )
    _require(
        canonical_json(attempt_commit_value) == canonical_json(attempt_commit),
        f"D-132 {phase} started attempt commit differs",
    )
    receipt, receipt_raw = _load_activation_receipt(root)
    receipt_binding = _activation_receipt_binding(receipt, receipt_raw)
    expected = _envelope(
        ACTION_STARTED_SCHEMA,
        prefix,
        _action_started_body(
            phase=phase,
            recorded_at=body.get("recorded_at"),
            attempt=attempt_binding,
            attempt_commit=attempt_commit,
            receipt=receipt_binding,
            source=receipt["semantic_body"]["source_identity"],
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected),
        f"D-132 {phase} action-started full rebuild differs",
    )
    _require(
        _parse_time(body["recorded_at"], label=f"{phase} started recorded_at")
        > _parse_time(
            attempt["semantic_body"]["recorded_at"],
            label=f"{phase} attempt recorded_at",
        ),
        f"D-132 {phase} action-started chronology differs",
    )
    return payload, raw


def _write_action_started(
    root: Path, *, phase: str, attempt_commit: dict[str, Any]
) -> tuple[dict[str, Any], bytes]:
    _clear_validation_caches()
    attempt_path, started_path, terminal_path = PHASE_PATHS[phase]
    _path_absent(root, started_path)
    _path_absent(root, terminal_path)
    current_attempt_commit = _current_attempt_commit_identity(root, phase=phase)
    _require(
        canonical_json(attempt_commit) == canonical_json(current_attempt_commit),
        f"D-132 {phase} action-started attempt commit differs",
    )
    attempt, attempt_raw = _validate_attempt_artifact(root, phase)
    receipt, receipt_raw = _load_activation_receipt(root)
    recorded_at = _now()
    _require(
        _parse_time(recorded_at, label=f"{phase} started recorded_at")
        > _parse_time(
            attempt["semantic_body"]["recorded_at"],
            label=f"{phase} attempt recorded_at",
        ),
        f"D-132 {phase} action-started clock regressed",
    )
    body = _action_started_body(
        phase=phase,
        recorded_at=recorded_at,
        attempt=_artifact_binding(
            path=attempt_path,
            payload=attempt,
            raw=attempt_raw,
            status=attempt["semantic_body"]["status"],
        ),
        attempt_commit=attempt_commit,
        receipt=_activation_receipt_binding(receipt, receipt_raw),
        source=receipt["semantic_body"]["source_identity"],
    )
    prefix = _phase_prefix(phase) + "started"
    _write_artifact(root, started_path, schema=ACTION_STARTED_SCHEMA, prefix=prefix, body=body)
    return _validate_action_started_artifact(root, phase)


def _terminal_schema(phase: str) -> str:
    return {
        "docker-image-readiness-remediation": DOCKER_SCHEMA,
        "official-pricing-capture": PRICING_SCHEMA,
        "read-only-no-call-preflight": PREFLIGHT_SCHEMA,
    }[phase]


def _terminal_status_and_boundary(
    root: Path, phase: str, recorded_at: str, observation: dict[str, Any]
) -> tuple[str, bool, list[str], dict[str, Any]]:
    if phase == "docker-image-readiness-remediation":
        try:
            docker_remediation.validate_docker_no_start_remediation_observation(observation)
        except ContractError as exc:
            raise D132ActivationOfflineError("D-132 Docker terminal differs") from exc
        ready = observation["passed"] is True
        blockers = list(observation["observed_blockers"])
        status = DOCKER_READY_STATUS if ready else DOCKER_BLOCKED_STATUS
        counts = {
            "docker_cli_command_count": observation["docker_cli_command_count"],
            "read_only_daemon_or_image_call_count": observation[
                "read_only_daemon_or_image_call_count"
            ],
            "image_pull_call_count": observation["image_pull_call_count"],
            "docker_image_store_mutation_count": observation["image_store_mutation_count"],
            "official_public_get_request_count": 0,
            "sdk_credential_or_endpoint_observation_count": 0,
            "sdk_transport_attempt_count": 0,
            "sdk_network_call_count": 0,
        }
    elif phase == "official-pricing-capture":
        try:
            pricing_capture.validate_official_pricing_evidence(observation)
        except (ContractError, ValueError, TypeError) as exc:
            raise D132ActivationOfflineError("D-132 pricing terminal differs") from exc
        age = (
            _parse_time(recorded_at, label="pricing terminal recorded_at")
            - _parse_time(observation["observed_at"], label="pricing observed_at")
        ).total_seconds()
        _require(age >= 0, "D-132 pricing evidence postdates its terminal")
        ready = True
        blockers = []
        status = PRICING_CAPTURED_STATUS
        counts = {
            "docker_cli_command_count": 0,
            "read_only_daemon_or_image_call_count": 0,
            "image_pull_call_count": 0,
            "docker_image_store_mutation_count": 0,
            "official_public_get_request_count": observation["public_get_request_count"],
            "sdk_credential_or_endpoint_observation_count": 0,
            "sdk_transport_attempt_count": 0,
            "sdk_network_call_count": 0,
        }
    else:
        _require(
            tuple(observation)
            == (
                "approved_docker_cli_bindings",
                "docker_readiness_snapshots",
                "sdk_credential_factory_observation",
            ),
            "D-132 preflight observation fields differ",
        )
        snapshots = observation["docker_readiness_snapshots"]
        _require(
            isinstance(snapshots, list) and len(snapshots) == 2,
            "D-132 preflight snapshot count differs",
        )
        for snapshot in snapshots:
            try:
                docker_remediation.validate_docker_readiness_snapshot(snapshot)
            except ContractError as exc:
                raise D132ActivationOfflineError("D-132 preflight Docker snapshot differs") from exc
        snapshot_stable = canonical_json(snapshots[0]) == canonical_json(snapshots[1])
        snapshot_ready = all(snapshot["observation"]["passed"] is True for snapshot in snapshots)
        receipt, _receipt_raw = _load_activation_receipt(root)
        source = receipt["semantic_body"]["source_identity"]
        _validate_sdk_observation(
            root,
            observation["sdk_credential_factory_observation"],
            source=source,
        )
        cli = observation["approved_docker_cli_bindings"]
        try:
            d127_docker._validate_file_binding(cli.get("before"), desktop=False)
            d127_docker._validate_file_binding(cli.get("after"), desktop=False)
        except (AttributeError, ContractError) as exc:
            raise D132ActivationOfflineError(
                "D-132 preflight Docker CLI binding shape differs"
            ) from exc
        _require(
            isinstance(cli, dict)
            and tuple(cli) == ("before", "after")
            and cli["before"] == cli["after"]
            and cli["before"].get("file_bytes") == docker_remediation.APPROVED_CLI_BYTES
            and cli["before"].get("file_sha256") == docker_remediation.APPROVED_CLI_SHA256
            and cli["before"].get("linklike") is False,
            "D-132 preflight Docker CLI bindings differ",
        )
        sdk_wrapper = observation["sdk_credential_factory_observation"]
        routing = sdk_wrapper["python_routing_environment_presence"]
        sdk = sdk_wrapper["d127_sdk_observation"]
        bindings = sdk_wrapper["loaded_sdk_module_bindings"]
        if sdk_wrapper["d127_sdk_probe_skipped_due_to_python_routing"] is True:
            blockers = ["python-module-routing-environment-present"]
            sdk_transport_attempt_count = 0
            sdk_network_call_count = 0
        else:
            _require(isinstance(sdk, dict), "D-132 SDK observation is absent")
            blockers = [key for key, passed in sdk["checks"].items() if passed is not True]
            sdk_transport_attempt_count = sdk["synthetic_endpoint_probe"]["transport_attempt_count"]
            sdk_network_call_count = sdk["network_call_count"]
        if any(routing.values()):
            blockers.append("python-module-routing-environment-present")
        if [binding["module_name"] for binding in bindings] != list(SDK_MODULE_NAMES) or not all(
            binding["under_repository_venv"] is True for binding in bindings
        ):
            blockers.append("openai-httpx-loaded-module-provenance-incomplete")
        if not snapshot_ready or not snapshot_stable:
            blockers.append("read-only-docker-readiness-snapshots-are-not-stable")
        pricing, _pricing_raw = _validate_terminal_artifact(root, "official-pricing-capture")
        pricing_observed_at = pricing["semantic_body"]["observation"]["observed_at"]
        pricing_age = (
            _parse_time(recorded_at, label="preflight terminal recorded_at")
            - _parse_time(pricing_observed_at, label="pricing observed_at")
        ).total_seconds()
        if not 0 <= pricing_age <= FRESHNESS_SECONDS:
            blockers.append("official-pricing-evidence-older-than-72-hours")
        blockers = sorted(set(blockers))
        ready = not blockers
        status = PREFLIGHT_READY_STATUS if ready else PREFLIGHT_BLOCKED_STATUS
        counts = {
            "docker_cli_command_count": sum(
                snapshot["docker_cli_command_count"] for snapshot in snapshots
            ),
            "read_only_daemon_or_image_call_count": sum(
                snapshot["read_only_daemon_or_image_call_count"] for snapshot in snapshots
            ),
            "image_pull_call_count": 0,
            "docker_image_store_mutation_count": 0,
            "official_public_get_request_count": 0,
            "sdk_credential_or_endpoint_observation_count": 1,
            "sdk_transport_attempt_count": sdk_transport_attempt_count,
            "sdk_network_call_count": sdk_network_call_count,
        }
    return status, ready, blockers, counts


def _terminal_body(
    root: Path,
    *,
    phase: str,
    recorded_at: str,
    observation: dict[str, Any],
    attempt: dict[str, Any],
    attempt_commit: dict[str, Any],
    started: dict[str, Any],
    receipt: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    status, ready, blockers, counts = _terminal_status_and_boundary(
        root, phase, recorded_at, observation
    )
    return {
        "milestone": "D-132/D-130-external-activation",
        "evidence_kind": "append-only-external-phase-terminal",
        "recorded_at": recorded_at,
        "status": status,
        "phase": phase,
        "activation_receipt_binding": receipt,
        "source_identity": source,
        "attempt_binding": attempt,
        "attempt_commit_binding": attempt_commit,
        "action_started_binding": started,
        "observation": observation,
        "observed_blockers": blockers,
        "phase_ready_for_successor": ready,
        "activity_accounting": {
            **counts,
            "sdk_transport_and_network_count_scope": "d127-synthetic-sdk-probe-only",
            "docker_desktop_or_daemon_start_count": 0,
            "container_create_start_run_exec_count": 0,
            "provider_evaluator_agent_call_count": 0,
            "runtime_memory_injection_or_retrieval_count": 0,
            "execution_hash_created": False,
            "execution_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "system_wide_socket_or_import_side_effect_denial_claimed": False,
        },
        "failure_boundary": {
            "action_started_marker_preceded_external_helper": True,
            "terminal_is_append-only-new": True,
            "started-plus-terminal-transition-commit-required-before-next-phase": True,
            "blocked_terminal_consumes_activation": not ready,
        },
    }


@cache
def _validate_terminal_artifact(root: Path, phase: str) -> tuple[dict[str, Any], bytes]:
    attempt_path, started_path, terminal_path = PHASE_PATHS[phase]
    prefix = _phase_prefix(phase) + "terminal"
    payload, raw = _load_envelope(
        root, terminal_path, schema=_terminal_schema(phase), prefix=prefix
    )
    body = payload["semantic_body"]
    attempt, attempt_raw = _validate_attempt_artifact(root, phase)
    started, started_raw = _validate_action_started_artifact(root, phase)
    attempt_binding = _artifact_binding(
        path=attempt_path,
        payload=attempt,
        raw=attempt_raw,
        status=attempt["semantic_body"]["status"],
    )
    started_binding = _artifact_binding(
        path=started_path,
        payload=started,
        raw=started_raw,
        status=started["semantic_body"]["status"],
    )
    attempt_commit = started["semantic_body"]["attempt_commit_binding"]
    receipt, receipt_raw = _load_activation_receipt(root)
    expected = _envelope(
        _terminal_schema(phase),
        prefix,
        _terminal_body(
            root,
            phase=phase,
            recorded_at=body.get("recorded_at"),
            observation=body.get("observation"),
            attempt=attempt_binding,
            attempt_commit=attempt_commit,
            started=started_binding,
            receipt=_activation_receipt_binding(receipt, receipt_raw),
            source=receipt["semantic_body"]["source_identity"],
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected),
        f"D-132 {phase} terminal full rebuild differs",
    )
    _require(
        _parse_time(attempt["semantic_body"]["recorded_at"], label="attempt recorded_at")
        < _parse_time(started["semantic_body"]["recorded_at"], label="started recorded_at")
        < _parse_time(body["recorded_at"], label="terminal recorded_at"),
        f"D-132 {phase} terminal chronology differs",
    )
    return payload, raw


def _write_terminal(
    root: Path,
    *,
    phase: str,
    observation: dict[str, Any],
    attempt_commit: dict[str, Any],
) -> tuple[dict[str, Any], bytes]:
    _clear_validation_caches()
    attempt_path, started_path, terminal_path = PHASE_PATHS[phase]
    _path_absent(root, terminal_path)
    attempt, attempt_raw = _validate_attempt_artifact(root, phase)
    started, started_raw = _validate_action_started_artifact(root, phase)
    _require(
        canonical_json(attempt_commit)
        == canonical_json(started["semantic_body"]["attempt_commit_binding"]),
        f"D-132 {phase} terminal attempt commit differs",
    )
    _require(
        _pending_only(root, (started_path,), parent=attempt_commit["commit"]),
        f"D-132 {phase} terminal publication checkout drifted",
    )
    receipt, receipt_raw = _load_activation_receipt(root)
    recorded_at = _now()
    _require(
        _parse_time(recorded_at, label=f"{phase} terminal recorded_at")
        > _parse_time(
            started["semantic_body"]["recorded_at"],
            label=f"{phase} started recorded_at",
        ),
        f"D-132 {phase} terminal clock regressed",
    )
    body = _terminal_body(
        root,
        phase=phase,
        recorded_at=recorded_at,
        observation=observation,
        attempt=_artifact_binding(
            path=attempt_path,
            payload=attempt,
            raw=attempt_raw,
            status=attempt["semantic_body"]["status"],
        ),
        attempt_commit=attempt_commit,
        started=_artifact_binding(
            path=started_path,
            payload=started,
            raw=started_raw,
            status=started["semantic_body"]["status"],
        ),
        receipt=_activation_receipt_binding(receipt, receipt_raw),
        source=receipt["semantic_body"]["source_identity"],
    )
    prefix = _phase_prefix(phase) + "terminal"
    _write_artifact(root, terminal_path, schema=_terminal_schema(phase), prefix=prefix, body=body)
    return _validate_terminal_artifact(root, phase)


@cache
def _rebuild_phase_transition_commit(root: Path, *, phase: str, commit: str) -> dict[str, Any]:
    attempt, _attempt_raw = _validate_attempt_artifact(root, phase)
    started, started_raw = _validate_action_started_artifact(root, phase)
    terminal, terminal_raw = _validate_terminal_artifact(root, phase)
    attempt_commit = started["semantic_body"]["attempt_commit_binding"]
    identity = _commit_identity(root, commit)
    _require(
        identity["parents"] == [attempt_commit["commit"]],
        f"D-132 {phase} transition parent differs",
    )
    expected = [
        {"status": "A", "path": PHASE_PATHS[phase][1].as_posix()},
        {"status": "A", "path": PHASE_PATHS[phase][2].as_posix()},
    ]
    _require(
        sorted(_diff_rows(root, commit), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        f"D-132 {phase} transition commit scope differs",
    )
    started_oid, committed_started = _commit_blob(root, commit, PHASE_PATHS[phase][1])
    terminal_oid, committed_terminal = _commit_blob(root, commit, PHASE_PATHS[phase][2])
    _require(
        committed_started == started_raw and committed_terminal == terminal_raw,
        f"D-132 {phase} transition committed bytes differ",
    )
    return {
        "commit": commit,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "phase": phase,
        "action_started_path": PHASE_PATHS[phase][1].as_posix(),
        "action_started_blob_oid": started_oid,
        "action_started_file_sha256": sha256_bytes(committed_started),
        "action_started_file_bytes": len(committed_started),
        "terminal_path": PHASE_PATHS[phase][2].as_posix(),
        "terminal_blob_oid": terminal_oid,
        "terminal_file_sha256": sha256_bytes(committed_terminal),
        "terminal_file_bytes": len(committed_terminal),
        "exact_action_started_plus_terminal_add_commit": True,
    }


def _current_phase_transition_commit_identity(root: Path, *, phase: str) -> dict[str, Any]:
    _require(_status_lines(root) == [], f"D-132 {phase} transition is not clean")
    return _rebuild_phase_transition_commit(root, phase=phase, commit=_head(root))


def _pending_only(root: Path, paths: tuple[Path, ...], *, parent: str) -> bool:
    lines = _status_lines(root)
    actual = {line[3:].replace("\\", "/") for line in lines if len(line) > 3}
    return bool(lines) and actual == {path.as_posix() for path in paths} and _head(root) == parent


def _transition_commit_from_successor(
    root: Path, *, phase: str, next_phase: str | None
) -> dict[str, Any] | None:
    if next_phase is not None and os.path.lexists(root / PHASE_PATHS[next_phase][0]):
        next_attempt, _raw = _load_envelope(
            root,
            PHASE_PATHS[next_phase][0],
            schema=ATTEMPT_SCHEMA,
            prefix=_phase_prefix(next_phase) + "attempt",
        )
        value = next_attempt["semantic_body"].get("parent_commit_binding")
        rebuilt = _rebuild_phase_transition_commit(
            root,
            phase=phase,
            commit=value.get("commit", "") if isinstance(value, dict) else "",
        )
        _require(
            canonical_json(value) == canonical_json(rebuilt),
            f"D-132 {phase} successor parent differs",
        )
        return rebuilt
    if os.path.lexists(root / FINAL_GATE_PATH):
        gate, _raw = _load_envelope(
            root, FINAL_GATE_PATH, schema=FINAL_GATE_SCHEMA, prefix="d132d130finalgate"
        )
        for record in gate["semantic_body"].get("phase_records", []):
            if record.get("phase") == phase:
                value = record.get("transition_commit_binding")
                rebuilt = _rebuild_phase_transition_commit(
                    root,
                    phase=phase,
                    commit=value.get("commit", "") if isinstance(value, dict) else "",
                )
                _require(
                    canonical_json(value) == canonical_json(rebuilt),
                    f"D-132 {phase} final-gate transition differs",
                )
                return rebuilt
    return None


def _phase_record(root: Path, *, phase: str, transition: dict[str, Any]) -> dict[str, Any]:
    terminal, terminal_raw = _validate_terminal_artifact(root, phase)
    return {
        "phase": phase,
        "attempt_path": PHASE_PATHS[phase][0].as_posix(),
        "action_started_path": PHASE_PATHS[phase][1].as_posix(),
        "terminal_binding": _artifact_binding(
            path=PHASE_PATHS[phase][2],
            payload=terminal,
            raw=terminal_raw,
            status=terminal["semantic_body"]["status"],
        ),
        "transition_commit_binding": transition,
        "ready_for_successor": terminal["semantic_body"]["phase_ready_for_successor"],
        "observed_blockers": terminal["semantic_body"]["observed_blockers"],
    }


def _final_gate_body(
    root: Path,
    *,
    recorded_at: str,
    receipt: dict[str, Any],
    source: dict[str, Any],
    phase_records: list[dict[str, Any]],
) -> dict[str, Any]:
    complete = [record["phase"] for record in phase_records]
    blockers = sorted(
        {blocker for record in phase_records for blocker in record["observed_blockers"]}
    )
    pricing_completed = "official-pricing-capture" in complete
    pricing_age_microseconds: int | None = None
    pricing_fresh_at_gate = False
    if pricing_completed:
        pricing, _pricing_raw = _validate_terminal_artifact(root, "official-pricing-capture")
        pricing_age_microseconds = _age_microseconds(
            pricing["semantic_body"]["observation"]["observed_at"],
            recorded_at,
            label="final-gate pricing age",
        )
        pricing_fresh_at_gate = 0 <= pricing_age_microseconds <= FRESHNESS_SECONDS * 1_000_000
        if not pricing_fresh_at_gate:
            blockers.append("replayable-official-pricing-is-not-fresh-at-final-gate-creation")
            blockers = sorted(set(blockers))
    all_phases = complete == list(PHASE_PATHS)
    ready = (
        all_phases
        and not blockers
        and all(record["ready_for_successor"] is True for record in phase_records)
    )
    status = FINAL_GATE_READY_STATUS if ready else FINAL_GATE_BLOCKED_STATUS
    counts = {
        "official_public_get_request_count": 0,
        "docker_cli_command_count": 0,
        "read_only_daemon_or_image_call_count": 0,
        "image_pull_call_count": 0,
        "docker_image_store_mutation_count": 0,
        "sdk_credential_or_endpoint_observation_count": 0,
        "sdk_transport_attempt_count": 0,
        "sdk_network_call_count": 0,
    }
    for record in phase_records:
        terminal, _raw = _validate_terminal_artifact(root, record["phase"])
        activity = terminal["semantic_body"]["activity_accounting"]
        for key in counts:
            counts[key] += activity[key]
    return {
        "milestone": "D-132/D-130-external-activation",
        "evidence_kind": "terminal-successor-external-no-call-preflight-gate",
        "recorded_at": recorded_at,
        "status": status,
        "activation_receipt_binding": receipt,
        "source_identity": source,
        "phase_records": phase_records,
        "qualification": {
            "completed_phases": complete,
            "all_three_phases_completed": all_phases,
            "official_pricing_capture_completed": pricing_completed,
            "official_pricing_fresh_within_72_hours_at_final_gate": pricing_fresh_at_gate,
            "official_pricing_age_microseconds_at_final_gate": pricing_age_microseconds,
            "environment_ready_for_execution_hash": ready,
            "observed_blockers": blockers,
            "blocked_terminal_consumed_activation": not ready,
        },
        "activity_accounting": {
            **counts,
            "sdk_transport_and_network_count_scope": "d127-synthetic-sdk-probe-only",
            "docker_desktop_or_daemon_start_count": 0,
            "container_create_start_run_exec_count": 0,
            "provider_evaluator_agent_call_count": 0,
            "runtime_memory_injection_or_retrieval_count": 0,
            "execution_hash_created": False,
            "execution_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "system_wide_socket_or_import_side_effect_denial_claimed": False,
        },
        "authority": {
            "docker_desktop_or_daemon_start_authorized": False,
            "container_create_start_run_exec_authorized": False,
            "execution_hash_or_candidate_authorized": False,
            "provider_evaluator_agent_execution_authorized": False,
            "provider_evaluator_agent_call_count": 0,
            "runtime_memory_injection_or_retrieval_authorized": False,
            "cost_reservation_or_spend_authorized": False,
            "four_row_ac_execution_authorized": False,
        },
        "next_gate": {
            "action": (
                "request-separate-execution-hash-authorization"
                if ready
                else "preserve-terminal-and-request-separate-successor"
            ),
            "final-gate-plus-active-docs-commit-required": True,
        },
    }


def _build_final_gate_body(
    root: Path,
    *,
    recorded_at: str,
    receipt: dict[str, Any],
    source: dict[str, Any],
    phase_records: list[dict[str, Any]],
) -> dict[str, Any]:
    return _final_gate_body(
        root,
        recorded_at=recorded_at,
        receipt=receipt,
        source=source,
        phase_records=phase_records,
    )


@cache
def _validate_final_gate_artifact(
    root: Path,
) -> tuple[dict[str, Any], bytes, list[dict[str, Any]]]:
    payload, raw = _load_envelope(
        root, FINAL_GATE_PATH, schema=FINAL_GATE_SCHEMA, prefix="d132d130finalgate"
    )
    body = payload["semantic_body"]
    receipt, receipt_raw = _load_activation_receipt(root)
    receipt_binding = _activation_receipt_binding(receipt, receipt_raw)
    records: list[dict[str, Any]] = []
    expected_phases: list[str] = []
    for stored in body.get("phase_records", []):
        phase = stored.get("phase")
        _require(
            isinstance(phase, str) and phase in PHASE_PATHS,
            "D-132 final gate phase record differs",
        )
        _require(phase not in expected_phases, "D-132 final gate duplicates a phase")
        transition_value = stored.get("transition_commit_binding")
        transition = _rebuild_phase_transition_commit(
            root,
            phase=phase,
            commit=(
                transition_value.get("commit", "") if isinstance(transition_value, dict) else ""
            ),
        )
        record = _phase_record(root, phase=phase, transition=transition)
        _require(
            canonical_json(stored) == canonical_json(record),
            "D-132 final gate phase record full rebuild differs",
        )
        expected_phases.append(phase)
        records.append(record)
    _require(
        expected_phases == list(PHASE_PATHS)[: len(expected_phases)] and records,
        "D-132 final gate phase sequence differs",
    )
    if len(records) < len(PHASE_PATHS):
        _require(
            records[-1]["ready_for_successor"] is False,
            "D-132 final gate stops before a ready phase",
        )
    expected = _envelope(
        FINAL_GATE_SCHEMA,
        "d132d130finalgate",
        _build_final_gate_body(
            root,
            recorded_at=body.get("recorded_at"),
            receipt=receipt_binding,
            source=receipt["semantic_body"]["source_identity"],
            phase_records=records,
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected),
        "D-132 final gate full rebuild differs",
    )
    _require(
        _parse_time(body["recorded_at"], label="final gate recorded_at")
        > _parse_time(
            records[-1]["terminal_binding"]["recorded_at"],
            label="last terminal recorded_at",
        ),
        "D-132 final gate chronology differs",
    )
    return payload, raw, records


def _write_final_gate(
    root: Path, *, phase_records: list[dict[str, Any]]
) -> tuple[dict[str, Any], bytes, list[dict[str, Any]]]:
    _clear_validation_caches()
    fresh_records: list[dict[str, Any]] = []
    for stored in phase_records:
        transition_value = stored["transition_commit_binding"]
        transition = _rebuild_phase_transition_commit(
            root,
            phase=stored["phase"],
            commit=transition_value["commit"],
        )
        fresh = _phase_record(root, phase=stored["phase"], transition=transition)
        _require(
            canonical_json(stored) == canonical_json(fresh),
            "D-132 final gate input phase record drifted",
        )
        fresh_records.append(fresh)
    phase_records = fresh_records
    _path_absent(root, FINAL_GATE_PATH)
    last_transition = phase_records[-1]["transition_commit_binding"]
    _require(_status_lines(root) == [], "D-132 final gate requires a clean transition")
    _require(
        _head(root) == last_transition["commit"],
        "D-132 final gate parent transition HEAD differs",
    )
    receipt, receipt_raw = _load_activation_receipt(root)
    recorded_at = _now()
    _require(
        _parse_time(recorded_at, label="final gate recorded_at")
        > _parse_time(
            phase_records[-1]["terminal_binding"]["recorded_at"],
            label="last terminal recorded_at",
        ),
        "D-132 final gate clock regressed",
    )
    body = _build_final_gate_body(
        root,
        recorded_at=recorded_at,
        receipt=_activation_receipt_binding(receipt, receipt_raw),
        source=receipt["semantic_body"]["source_identity"],
        phase_records=phase_records,
    )
    _write_artifact(
        root,
        FINAL_GATE_PATH,
        schema=FINAL_GATE_SCHEMA,
        prefix="d132d130finalgate",
        body=body,
    )
    return _validate_final_gate_artifact(root)


def _rebuild_final_gate_evidence_commit(
    root: Path,
    *,
    commit: str,
    parent: str,
    gate_raw: bytes,
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [parent], "D-132 final evidence parent differs")
    expected = [
        {"status": "A", "path": FINAL_GATE_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
    ]
    _require(
        sorted(_diff_rows(root, commit), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-132 final gate evidence scope differs",
    )
    oid, committed = _commit_blob(root, commit, FINAL_GATE_PATH)
    _require(committed == gate_raw, "D-132 final gate evidence bytes differ")
    return {
        "commit": commit,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "artifact_path": FINAL_GATE_PATH.as_posix(),
        "artifact_blob_oid": oid,
        "artifact_file_sha256": sha256_bytes(committed),
        "artifact_file_bytes": len(committed),
        "exact_gate_add_and_active_docs_modify_commit": True,
    }


def _waiting_result(
    *,
    status: str,
    phase: str | None,
    artifact: dict[str, Any],
    raw: bytes,
    external_counts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "phase": phase,
        "artifact_id": artifact["artifact_id"],
        "semantic_body_hash": artifact["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "commit_required_before_next_action": True,
        "external_activity": external_counts
        or {
            "docker_cli_command_count": 0,
            "official_public_get_request_count": 0,
            "sdk_credential_or_endpoint_observation_count": 0,
        },
        "provider_evaluator_agent_call_count": 0,
        "container_create_start_run_exec_count": 0,
        "execution_hash_created": False,
        "execution_candidate_created": False,
        "cost_reserved_or_spent_usd": "0",
    }


def _perform_phase(root: Path, *, phase: str, attempt_commit: dict[str, Any]) -> dict[str, Any]:
    _require_external_helper_contracts()
    _write_action_started(root, phase=phase, attempt_commit=attempt_commit)
    _clear_validation_caches()
    fresh_attempt_commit = _rebuild_attempt_commit(
        root, phase=phase, commit=attempt_commit["commit"]
    )
    _require(
        canonical_json(attempt_commit) == canonical_json(fresh_attempt_commit),
        f"D-132 {phase} attempt drifted before helper",
    )
    _validate_action_started_artifact(root, phase)
    _load_activation_receipt(root)
    _require(
        _pending_only(
            root,
            (PHASE_PATHS[phase][1],),
            parent=attempt_commit["commit"],
        ),
        f"D-132 {phase} action boundary checkout drifted before helper",
    )
    # ACTION_STARTED is now durable.  From this line onward any exception leaves
    # an uncertain consumed marker, and the runner will never call the helper again.
    if phase == "docker-image-readiness-remediation":
        observation = docker_remediation.remediate_already_running_docker_environment()
        docker_remediation.validate_docker_no_start_remediation_observation(observation)
    elif phase == "official-pricing-capture":
        observation = pricing_capture.capture_official_pricing_evidence()
        pricing_capture.validate_official_pricing_evidence(observation)
    else:
        cli_before = docker_remediation.approved_cli_binding()
        snapshots = [
            docker_remediation.observe_docker_readiness(),
            docker_remediation.observe_docker_readiness(),
        ]
        cli_after = docker_remediation.approved_cli_binding()
        try:
            factory = d127._model_factory_contract(root)
        except ContractError as exc:
            raise D132ActivationOfflineError(
                "D-132 production model factory contract failed"
            ) from exc
        receipt, _receipt_raw = _load_activation_receipt(root)
        source = receipt["semantic_body"]["source_identity"]
        sdk = _sdk_observation(root, source, factory)
        _validate_sdk_observation(root, sdk, source=source)
        observation = {
            "approved_docker_cli_bindings": {
                "before": cli_before,
                "after": cli_after,
            },
            "docker_readiness_snapshots": snapshots,
            "sdk_credential_factory_observation": sdk,
        }
    _clear_validation_caches()
    terminal, terminal_raw = _write_terminal(
        root,
        phase=phase,
        observation=observation,
        attempt_commit=attempt_commit,
    )
    activity = terminal["semantic_body"]["activity_accounting"]
    return _waiting_result(
        status=f"WAITING_{phase.replace('-', '_').upper()}_TERMINAL_TRANSITION_COMMIT",
        phase=phase,
        artifact=terminal,
        raw=terminal_raw,
        external_counts={
            "docker_cli_command_count": activity["docker_cli_command_count"],
            "official_public_get_request_count": activity["official_public_get_request_count"],
            "sdk_credential_or_endpoint_observation_count": activity[
                "sdk_credential_or_endpoint_observation_count"
            ],
        },
    )


def _validate_future_inventory(root: Path) -> None:
    """Reject every non-prefix future-artifact state before mutation or I/O.

    A later phase may exist only after every earlier phase has a validated,
    ready terminal.  Once a phase is absent, pending, action-started without a
    terminal, or terminally blocked, all later phase paths must be absent.  A
    final gate is possible only after all phases complete or the first blocked
    terminal closes the activation.
    """

    phases = list(PHASE_PATHS)
    prefix_closed = False
    completed_phases: list[str] = []
    blocked_phase: str | None = None

    for phase in phases:
        attempt_path, started_path, terminal_path = PHASE_PATHS[phase]
        exists = (
            os.path.lexists(root / attempt_path),
            os.path.lexists(root / started_path),
            os.path.lexists(root / terminal_path),
        )
        if prefix_closed:
            _require(
                not any(exists),
                f"D-132 {phase} evidence is out of order after a closed prefix",
            )
            continue

        attempt_exists, started_exists, terminal_exists = exists
        _require(
            not started_exists or attempt_exists,
            f"D-132 {phase} ACTION_STARTED exists without attempt",
        )
        _require(
            not terminal_exists or started_exists,
            f"D-132 {phase} terminal exists without ACTION_STARTED",
        )
        if not attempt_exists:
            prefix_closed = True
            continue

        _validate_attempt_artifact(root, phase)
        if not started_exists:
            prefix_closed = True
            continue

        _validate_action_started_artifact(root, phase)
        if not terminal_exists:
            prefix_closed = True
            continue

        terminal, _terminal_raw = _validate_terminal_artifact(root, phase)
        completed_phases.append(phase)
        if terminal["semantic_body"]["phase_ready_for_successor"] is not True:
            blocked_phase = phase
            prefix_closed = True

    if os.path.lexists(root / FINAL_GATE_PATH):
        _require(
            blocked_phase is not None or completed_phases == phases,
            "D-132 final gate exists before a terminally closed phase prefix",
        )
        _validate_final_gate_artifact(root)


@_fresh_validation_cache
def run_d130_external_no_call_preflight(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Advance one tamper-checked, chronological state without orphan retry.

    The private phase executor is the only call site for
    ``remediate_already_running_docker_environment`` and
    ``capture_official_pricing_evidence``. A blocked terminal closes the
    current activation; an ``action_started`` marker without a terminal is an
    uncertain consumed state.
    """

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    _require_external_helper_contracts()
    _load_activation_receipt(root)
    _validate_future_inventory(root)
    if os.path.lexists(root / FINAL_GATE_PATH):
        mode: Literal["current-source", "post-evidence-commit"] = (
            "post-evidence-commit" if _status_lines(root) == [] else "current-source"
        )
        return validate_d130_external_no_call_gate(repository=root, mode=mode)

    phases = list(PHASE_PATHS)
    records: list[dict[str, Any]] = []
    for index, phase in enumerate(phases):
        attempt_path, started_path, terminal_path = PHASE_PATHS[phase]
        attempt_exists = os.path.lexists(root / attempt_path)
        started_exists = os.path.lexists(root / started_path)
        terminal_exists = os.path.lexists(root / terminal_path)
        _require(
            not started_exists or attempt_exists,
            f"D-132 {phase} ACTION_STARTED exists without attempt",
        )
        _require(
            not terminal_exists or started_exists,
            f"D-132 {phase} terminal exists without ACTION_STARTED",
        )

        if not attempt_exists:
            _require(
                not started_exists and not terminal_exists,
                f"D-132 {phase} orphaned descendant differs",
            )
            if index == 0:
                parent = _current_receipt_commit_identity(root)
                predecessor_terminal = None
            else:
                parent = records[-1]["transition_commit_binding"]
                predecessor_terminal = records[-1]["terminal_binding"]
                _require(
                    records[-1]["ready_for_successor"] is True,
                    f"D-132 {phase} follows a blocked predecessor",
                )
                _require(
                    _status_lines(root) == [] and _head(root) == parent["commit"],
                    f"D-132 {phase} attempt requires clean predecessor transition",
                )
            attempt, attempt_raw = _create_attempt_artifact(
                root,
                phase=phase,
                parent_commit=parent,
                predecessor_terminal=predecessor_terminal,
            )
            return _waiting_result(
                status=f"WAITING_{phase.replace('-', '_').upper()}_ATTEMPT_COMMIT",
                phase=phase,
                artifact=attempt,
                raw=attempt_raw,
            )

        attempt, attempt_raw = _validate_attempt_artifact(root, phase)
        parent_commit = attempt["semantic_body"]["parent_commit_binding"]
        if not started_exists:
            _require(not terminal_exists, f"D-132 {phase} terminal is orphaned")
            if _pending_only(root, (attempt_path,), parent=parent_commit["commit"]):
                return _waiting_result(
                    status=f"WAITING_{phase.replace('-', '_').upper()}_ATTEMPT_COMMIT",
                    phase=phase,
                    artifact=attempt,
                    raw=attempt_raw,
                )
            attempt_commit = _current_attempt_commit_identity(root, phase=phase)
            return _perform_phase(root, phase=phase, attempt_commit=attempt_commit)

        started, started_raw = _validate_action_started_artifact(root, phase)
        if not terminal_exists:
            raise D132ActivationOfflineError(
                f"D-132 {phase} ACTION_STARTED has no terminal; activation is consumed "
                "and retry is forbidden"
            )
        terminal, terminal_raw = _validate_terminal_artifact(root, phase)
        attempt_commit = started["semantic_body"]["attempt_commit_binding"]
        next_phase = phases[index + 1] if index + 1 < len(phases) else None
        transition = _transition_commit_from_successor(root, phase=phase, next_phase=next_phase)
        if transition is None:
            if _pending_only(
                root,
                (started_path, terminal_path),
                parent=attempt_commit["commit"],
            ):
                return _waiting_result(
                    status=f"WAITING_{phase.replace('-', '_').upper()}_TERMINAL_TRANSITION_COMMIT",
                    phase=phase,
                    artifact=terminal,
                    raw=terminal_raw,
                    external_counts={
                        "docker_cli_command_count": terminal["semantic_body"][
                            "activity_accounting"
                        ]["docker_cli_command_count"],
                        "official_public_get_request_count": terminal["semantic_body"][
                            "activity_accounting"
                        ]["official_public_get_request_count"],
                        "sdk_credential_or_endpoint_observation_count": terminal["semantic_body"][
                            "activity_accounting"
                        ]["sdk_credential_or_endpoint_observation_count"],
                    },
                )
            transition = _current_phase_transition_commit_identity(root, phase=phase)
        record = _phase_record(root, phase=phase, transition=transition)
        records.append(record)
        if record["ready_for_successor"] is False:
            for later in phases[index + 1 :]:
                for path in PHASE_PATHS[later]:
                    _path_absent(root, path)
            gate, gate_raw, _records = _write_final_gate(root, phase_records=records)
            return _waiting_result(
                status="WAITING_FINAL_GATE_EVIDENCE_COMMIT",
                phase=None,
                artifact=gate,
                raw=gate_raw,
            )

    gate, gate_raw, _records = _write_final_gate(root, phase_records=records)
    return _waiting_result(
        status="WAITING_FINAL_GATE_EVIDENCE_COMMIT",
        phase=None,
        artifact=gate,
        raw=gate_raw,
    )


@_fresh_validation_cache
def validate_d130_external_no_call_gate(
    *,
    repository: str | Path | None = None,
    mode: Literal["current-source", "post-evidence-commit"] = "current-source",
) -> dict[str, Any]:
    """Replay the terminal gate without Docker, SDK, credential, or network calls."""

    root = _repo_root(repository)
    gate, gate_raw, records = _validate_final_gate_artifact(root)
    last_transition = records[-1]["transition_commit_binding"]
    evidence_commit = None
    if mode == "current-source":
        _require(
            _pending_only(root, (FINAL_GATE_PATH,), parent=last_transition["commit"]),
            "D-132 final gate is not the sole pending evidence path",
        )
    elif mode == "post-evidence-commit":
        _require(_status_lines(root) == [], "D-132 final evidence checkout is not clean")
        evidence_commit = _rebuild_final_gate_evidence_commit(
            root,
            commit=_head(root),
            parent=last_transition["commit"],
            gate_raw=gate_raw,
        )
    else:
        raise D132ActivationOfflineError("D-132 final gate validation mode differs")
    body = gate["semantic_body"]
    return {
        "status": body["status"],
        "gate_id": gate["artifact_id"],
        "semantic_body_hash": gate["semantic_body_hash"],
        "file_sha256": sha256_bytes(gate_raw),
        "file_bytes": len(gate_raw),
        "environment_ready_for_execution_hash": body["qualification"][
            "environment_ready_for_execution_hash"
        ],
        "observed_blockers": body["qualification"]["observed_blockers"],
        "completed_phases": body["qualification"]["completed_phases"],
        "evidence_commit": None if evidence_commit is None else evidence_commit["commit"],
        "provider_evaluator_agent_call_count": 0,
        "container_create_start_run_exec_count": 0,
        "execution_hash_created": False,
        "execution_candidate_created": False,
        "cost_reserved_or_spent_usd": "0",
    }


__all__ = [
    "ACTIVATION_RECEIPT_PATH",
    "ACTIVATION_RECEIPT_STATUS",
    "D132ActivationOfflineError",
    "FINAL_GATE_PATH",
    "GATE_PATH",
    "OUTPUT_PATH",
    "PREFLIGHT_PATH",
    "PRICING_PATH",
    "STATUS",
    "create_d130_external_activation_receipt",
    "render_d132_external_activation_template",
    "run_d130_external_no_call_preflight",
    "run_d132_offline_source_gate",
    "validate_d130_external_activation_receipt",
    "validate_d130_external_no_call_gate",
    "validate_d132_offline_source_gate",
]
