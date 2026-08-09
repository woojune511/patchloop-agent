"""Qualify the D-130 local-admission implementation without exercising it.

D-131 binds the sealed D-130 offline gate and the implementation that can,
under a later exact approval, create a receipt-only commit followed by a
durable ``ARMED_WAITING_EXACT_ACTIVATION`` intent-only commit.  Building or
validating D-131 never creates either future artifact and performs no external
observation.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
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
from patchloop.evals import d129_d128_terminal_successor_offline as d129_offline
from patchloop.evals import d130_d129_sequence_block_successor_offline as d130
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-131"
SCHEMA_VERSION = "d130-local-admission-implementation-offline-source-gate-d131-v1"
STATUS = "D131_D130_LOCAL_ADMISSION_IMPLEMENTATION_OFFLINE_SOURCE_QUALIFIED_APPROVAL_REQUIRED"
OUTPUT_PATH = Path(
    "reports/live-pilot/artifacts/d131-d130-local-admission-successor-offline-source-gate.json"
)

D130_GATE_PATH = d130.OUTPUT_PATH
D130_GATE_ID = "d130_443b0bc935ba6affd4a009dee780ae85ec1ecdc1e3ce62edcd566e12307c74db"
D130_GATE_BODY_SHA256 = "sha256:443b0bc935ba6affd4a009dee780ae85ec1ecdc1e3ce62edcd566e12307c74db"
D130_GATE_FILE_SHA256 = "sha256:6d580dd979dc77659efed07291264c4ea2a16dca02d9070a32928e9fbefff468"
D130_GATE_FILE_BYTES = 17_416
D130_GATE_STATUS = d130.STATUS
D130_EVIDENCE_COMMIT = "d6079e55fd1c4745b05c2e345228b1a66d0a3df4"
D130_EVIDENCE_TREE = "564cc3719b6acaeb709a838d574b8b0f943c4b08"
D130_EVIDENCE_PARENT = "e6acdc23050e93f5324827a2dac1ed519fe35406"
D130_GATE_BLOB_OID = "c20cf331c324d3716f9677e509a5fc0c05791b6b"

D131_GIT_ENGINE_PATH = Path(r"C:\Program Files\Git\mingw64\bin\git.exe")
D131_GIT_ENGINE_FILE_BYTES = 4_422_544
D131_GIT_ENGINE_FILE_SHA256 = (
    "sha256:cab4c4eea1d869cf9f7be73868dc9a90ad2df1b1b673e5f8c8714a576c25ea96"
)
D131_GIT_VERSION = "git version 2.54.0.windows.1"
D131_FIXED_GIT_ENVIRONMENT = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "NUL",
    "GIT_CONFIG_SYSTEM": "NUL",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_TERMINAL_PROMPT": "0",
    "LC_ALL": "C",
}
MAX_GIT_OUTPUT_BYTES = 4 * 1024 * 1024

IMPLEMENTATION_PATHS = (
    Path("patchloop/evals/d131_d130_local_admission_offline.py"),
    Path("scripts/build_d131_d130_local_admission_offline.py"),
    Path("tests/test_d131_d130_local_admission_offline.py"),
)
DEPENDENCY_PATHS = (
    Path("patchloop/evals/d130_d129_sequence_block_successor_offline.py"),
    Path("patchloop/evals/d129_d128_terminal_successor_offline.py"),
    Path("patchloop/errors.py"),
    Path("patchloop/runtime.py"),
    Path("patchloop/util.py"),
)
SOURCE_BINDING_PATHS = IMPLEMENTATION_PATHS + DEPENDENCY_PATHS
ACTIVE_DOC_PATHS = d130.ACTIVE_DOC_PATHS
PYTHON_ROUTING_ENV_NAMES = ("PYTHONHOME", "PYTHONPATH")
LOADED_MODULE_PATHS = (
    (IMPLEMENTATION_PATHS[0], __name__),
    (DEPENDENCY_PATHS[0], d130.__name__),
    (DEPENDENCY_PATHS[1], d129_offline.__name__),
    (DEPENDENCY_PATHS[2], errors_module.__name__),
    (DEPENDENCY_PATHS[3], runtime_module.__name__),
    (DEPENDENCY_PATHS[4], util_module.__name__),
)

RECEIPT_PATH = Path("reports/live-pilot/artifacts/d130-local-admission-approval-receipt.json")
INTENT_PATH = Path("reports/live-pilot/artifacts/d130-external-phase-armed-intent.json")
ACTIVATION_PATH = Path("reports/live-pilot/artifacts/d130-external-activation-receipt.json")
FUTURE_EXTERNAL_PATHS = tuple(
    path for path in d130.D130_FUTURE_PATHS if path not in {RECEIPT_PATH, INTENT_PATH}
)

RECEIPT_SCHEMA = "d130-local-admission-approval-receipt-d130-v1"
RECEIPT_STATUS = "D130_LOCAL_ADMISSION_APPROVAL_RECORDED"
INTENT_SCHEMA = "d130-external-phase-armed-intent-d130-v1"
INTENT_STATUS = "D130_EXTERNAL_PHASE_ARMED_WAITING_EXACT_ACTIVATION"

ROOT_KEYS = ("schema_version", "artifact_id", "semantic_body_hash", "semantic_body")
GATE_ROOT_KEYS = ("schema_version", "gate_id", "semantic_body_hash", "semantic_body")
GATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "predecessor_binding",
    "source_identity",
    "qualified_local_admission_contract",
    "implementation_integrity",
    "offline_qualification",
    "blocked_prerequisites",
    "evidence_boundary",
    "authority",
    "next_gate",
)
RECEIPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "d131_gate_binding",
    "source_identity",
    "approval_binding",
    "event_order",
    "evidence_boundary",
    "authority",
    "next_gate",
)
INTENT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "d131_gate_binding",
    "source_identity",
    "receipt_binding",
    "receipt_commit_binding",
    "armed_state",
    "activation_challenge_contract",
    "activity_accounting",
    "evidence_boundary",
    "authority",
    "next_gate",
)
COMMIT_BINDING_KEYS = (
    "commit",
    "tree",
    "parents",
    "artifact_path",
    "artifact_blob_oid",
    "artifact_file_sha256",
    "artifact_file_bytes",
    "single_artifact_add_commit",
)
GATE_EVIDENCE_COMMIT_BINDING_KEYS = (
    "commit",
    "tree",
    "parents",
    "artifact_path",
    "artifact_blob_oid",
    "artifact_file_sha256",
    "artifact_file_bytes",
    "exact_gate_add_and_active_docs_modify_commit",
)

FOCUSED_TESTS_PASSED = 15

LOCAL_ADMISSION_SCOPE = (
    "create-exact-d130-local-admission-approval-receipt",
    "create-receipt-only-local-git-commit",
    "create-durable-d130-external-phase-armed-intent-with-zero-external-actions",
    "create-armed-intent-only-local-git-commit",
    "render-exact-external-activation-challenge",
)
LOCAL_ADMISSION_EXCLUSIONS = (
    "official-docs-search-open-network-or-pricing-capture",
    "docker-cli-daemon-image-or-container-call",
    "sdk-credential-or-endpoint-observation",
    "provider-evaluator-agent-memory-or-retrieval",
    "execution-hash-candidate-cost-or-four-row-ac",
)
D131_SOURCE_PREPARATION_SCOPE = (
    "implement-d130-local-admission-receipt-and-armed-intent-offline-writer-validator-cli-and-focused-tests",
    "implement-append-only-new-only-orphan-collision-idempotence-exact-git-topology-and-loaded-module-provenance-validation",
    "implement-exact-activation-challenge-renderer",
    "modify-related-source-tests-docs-and-create-local-git-commits",
    "create-append-only-d131-offline-source-qualification-gate-and-local-evidence-commit",
    "render-new-exact-local-admission-approval-template",
)
D131_SOURCE_PREPARATION_EXCLUSIONS = (
    "create-d130-or-d131-approval-receipt-or-armed-intent",
    "create-activation-receipt-or-external-phase-attempt",
    "official-docs-search-open-network-or-pricing-capture",
    "docker-sdk-credential-presence-dotenv-or-environment-value-observation",
    "provider-evaluator-agent-execution",
    "retrieval-or-memory-injection",
    "execution-hash-or-candidate-creation",
    "cost-reservation-or-spending",
    "four-row-ac-execution",
)
ACTIVATION_SCOPE = (
    "use-approved-exact-docker-cli",
    "read-only-recheck-already-running-docker-desktop-linux-daemon",
    "pull-only-confirmed-missing-exact-moto-or-babel-digest-images",
    "capture-bounded-replayable-official-openai-pricing-evidence",
    "perform-sdk-credential-presence-and-official-endpoint-no-call-preflight",
    "create-append-only-attempt-terminal-preflight-and-gate-evidence",
)
ACTIVATION_EXCLUSIONS = (
    "agent-docker-desktop-or-daemon-start",
    "container-create-start-run-or-exec",
    "other-image-pull-or-load",
    "provider-evaluator-or-agent-execution",
    "runtime-memory-injection-or-retrieval",
    "execution-hash-or-candidate-creation",
    "cost-reservation-or-spend",
    "four-row-ac-execution",
)


class D131LocalAdmissionOfflineError(ContractError):
    """Raised when the D-131 source or future local admission is not exact."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D131LocalAdmissionOfflineError(message)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _repo_root(repository: str | Path | None) -> Path:
    try:
        return d129_offline._repo_root(repository)
    except ContractError as exc:
        raise D131LocalAdmissionOfflineError(str(exc)) from exc


def _parse_time(value: Any, *, label: str) -> datetime:
    try:
        return d129_offline._parse_time(value, label=label)
    except ContractError as exc:
        raise D131LocalAdmissionOfflineError(str(exc)) from exc


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
        "gate_id": f"d131_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _stable_read(root: Path, relative: Path) -> bytes:
    try:
        return d129_offline._stable_read(root, relative)
    except ContractError as exc:
        raise D131LocalAdmissionOfflineError(str(exc)) from exc


def _read_json(root: Path, relative: Path) -> tuple[dict[str, Any], bytes]:
    raw = _stable_read(root, relative)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D131LocalAdmissionOfflineError(f"D-131 {relative.name} JSON differs") from exc
    _require(isinstance(payload, dict), f"D-131 {relative.name} root differs")
    return payload, raw


def _path_absent(root: Path, relative: Path) -> None:
    _require(
        not d129_offline._lexists(root / relative), f"D-131 unexpected artifact exists: {relative}"
    )


def _write_new(root: Path, relative: Path, raw: bytes) -> None:
    try:
        selected = d129_offline._logical_path(root, relative, must_exist=False)
    except ContractError as exc:
        raise D131LocalAdmissionOfflineError(str(exc)) from exc
    _require(not d129_offline._lexists(selected), f"D-131 {relative.name} already exists")
    temporary = selected.with_name(f".{selected.name}.d131-{uuid.uuid4().hex}.tmp")
    _require(not d129_offline._lexists(temporary), "D-131 temporary output collision")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        _require(temporary.read_bytes() == raw, "D-131 temporary output differs")
        try:
            os.link(temporary, selected)
        except FileExistsError as exc:
            raise D131LocalAdmissionOfflineError(f"D-131 {relative.name} collision") from exc
        _require(_stable_read(root, relative) == raw, "D-131 persisted output differs")
    finally:
        with suppress(OSError):
            temporary.unlink()


def _git_engine_binding() -> dict[str, Any]:
    try:
        binding = d129_offline._bounded_external_file_binding(D131_GIT_ENGINE_PATH)
    except ContractError as exc:
        raise D131LocalAdmissionOfflineError(str(exc)) from exc
    expected = {
        "resolved_path": str(D131_GIT_ENGINE_PATH),
        "file_name": "git.exe",
        "file_bytes": D131_GIT_ENGINE_FILE_BYTES,
        "file_sha256": D131_GIT_ENGINE_FILE_SHA256,
        "linklike": False,
    }
    _require(binding == expected, "D-131 exact Git engine binding differs")
    return binding


def _git_command(root: Path, *args: str, binary: bool = False) -> bytes | str:
    before = _git_engine_binding()
    try:
        result = subprocess.run(
            [
                str(D131_GIT_ENGINE_PATH),
                "-c",
                "core.fsmonitor=false",
                "-c",
                "commit.gpgSign=false",
                *args,
            ],
            cwd=root,
            capture_output=True,
            text=False,
            check=False,
            shell=False,
            env=dict(D131_FIXED_GIT_ENVIRONMENT),
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise D131LocalAdmissionOfflineError("D-131 bounded local Git observation failed") from exc
    _require(_git_engine_binding() == before, "D-131 Git engine changed during command")
    _require(
        len(result.stdout) <= MAX_GIT_OUTPUT_BYTES and len(result.stderr) <= MAX_GIT_OUTPUT_BYTES,
        "D-131 Git output exceeds bound",
    )
    _require(result.returncode == 0, f"D-131 git command failed: {' '.join(args)}")
    if binary:
        return result.stdout
    try:
        return result.stdout.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise D131LocalAdmissionOfflineError("D-131 Git output is not UTF-8") from exc


def _git_cli_observation(root: Path) -> dict[str, Any]:
    binding = _git_engine_binding()
    version = _git_command(root, "--version")
    normalization = _git_command(root, "config", "--local", "--get", "core.autocrlf")
    _require(version == D131_GIT_VERSION, "D-131 Git version differs")
    _require(normalization == "false", "D-131 checkout must bind core.autocrlf=false")
    return {
        **binding,
        "version": version,
        "actual_git_engine_invoked_directly": True,
        "repository_local_core_autocrlf": "false",
        "authenticated_or_vendor_signed_identity_claimed": False,
        "stable_during_observation": True,
        "minimal_secret_free_environment": True,
        "fsmonitor_disabled": True,
        "shell_used": False,
    }


def _validate_git_observation(root: Path, value: Any) -> None:
    try:
        d129_offline._validate_git_observation(value)
    except ContractError as exc:
        raise D131LocalAdmissionOfflineError(str(exc)) from exc
    _require(value == _git_cli_observation(root), "D-131 current Git engine differs")


def _commit_identity(root: Path, commit: str) -> dict[str, Any]:
    tree = _git_command(root, "rev-parse", f"{commit}^{{tree}}")
    ancestry = _git_command(root, "rev-list", "--parents", "-n", "1", commit)
    _require(isinstance(tree, str) and isinstance(ancestry, str), "D-131 commit differs")
    values = ancestry.split()
    _require(values and values[0] == commit, "D-131 commit ancestry differs")
    return {"commit": commit, "tree": tree, "parents": values[1:]}


def _diff_rows(root: Path, commit: str) -> list[dict[str, str]]:
    value = _git_command(
        root,
        "diff-tree",
        "--no-renames",
        "--no-ext-diff",
        "--no-commit-id",
        "--name-status",
        "-r",
        commit,
    )
    _require(isinstance(value, str), "D-131 commit diff differs")
    rows: list[dict[str, str]] = []
    for line in value.splitlines() if value else []:
        parts = line.split("\t")
        _require(len(parts) == 2, "D-131 commit diff row differs")
        rows.append({"status": parts[0], "path": parts[1].replace("\\", "/")})
    return rows


def _commit_blob(root: Path, commit: str, path: Path) -> tuple[str, bytes]:
    listing = _git_command(root, "ls-tree", commit, "--", path.as_posix())
    _require(isinstance(listing, str), "D-131 committed blob differs")
    match = re.fullmatch(r"100644 blob ([0-9a-f]{40})\t(.+)", listing)
    _require(
        match is not None and match.group(2) == path.as_posix(),
        "D-131 committed blob differs",
    )
    raw = _git_command(root, "cat-file", "blob", f"{commit}:{path.as_posix()}", binary=True)
    _require(isinstance(raw, bytes), "D-131 committed blob differs")
    return match.group(1), raw


def _status_lines(root: Path) -> list[str]:
    value = _git_command(root, "status", "--porcelain", "--untracked-files=all")
    _require(isinstance(value, str), "D-131 Git status differs")
    return [line for line in value.splitlines() if line]


def _head(root: Path) -> str:
    value = _git_command(root, "rev-parse", "HEAD")
    _require(isinstance(value, str) and len(value) == 40, "D-131 HEAD differs")
    return value


def _assert_runtime_import_boundary(root: Path) -> None:
    presence = {name: name in os.environ for name in PYTHON_ROUTING_ENV_NAMES}
    _require(not any(presence.values()), "D-131 Python import routing environment is present")
    for relative, module_name in LOADED_MODULE_PATHS:
        module = sys.modules.get(module_name)
        loaded_value = getattr(module, "__file__", None)
        _require(isinstance(loaded_value, str), f"D-131 loaded module differs: {relative}")
        try:
            loaded = Path(loaded_value).resolve(strict=True)
            expected = (root / relative).resolve(strict=True)
        except OSError as exc:
            raise D131LocalAdmissionOfflineError(
                f"D-131 loaded module differs: {relative}"
            ) from exc
        _require(loaded == expected, f"D-131 loaded module is outside repository: {relative}")


def _file_binding(root: Path, commit: str, path: Path) -> dict[str, Any]:
    oid, committed = _commit_blob(root, commit, path)
    current = _stable_read(root, path)
    _require(current == committed, f"D-131 source drift: {path}")
    return {
        "path": path.as_posix(),
        "file_bytes": len(committed),
        "file_sha256": sha256_bytes(committed),
        "blob_oid": oid,
        "current_bytes_match_commit": True,
    }


def _loaded_module_bindings(root: Path, commit: str) -> list[dict[str, Any]]:
    _assert_runtime_import_boundary(root)
    return [
        {
            **_file_binding(root, commit, relative),
            "module_name": module_name,
            "loaded_path": relative.as_posix(),
            "loaded_path_matches_repository": True,
        }
        for relative, module_name in LOADED_MODULE_PATHS
    ]


def _d130_predecessor_binding(root: Path) -> dict[str, Any]:
    identity = _commit_identity(root, D130_EVIDENCE_COMMIT)
    _require(
        identity["tree"] == D130_EVIDENCE_TREE and identity["parents"] == [D130_EVIDENCE_PARENT],
        "D-131 D-130 evidence topology differs",
    )
    expected = [
        {"status": "A", "path": D130_GATE_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
    ]
    _require(
        sorted(_diff_rows(root, D130_EVIDENCE_COMMIT), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-131 D-130 evidence scope differs",
    )
    oid, committed = _commit_blob(root, D130_EVIDENCE_COMMIT, D130_GATE_PATH)
    raw = _stable_read(root, D130_GATE_PATH)
    _require(
        oid == D130_GATE_BLOB_OID
        and committed == raw
        and len(raw) == D130_GATE_FILE_BYTES
        and sha256_bytes(raw) == D130_GATE_FILE_SHA256,
        "D-131 D-130 gate bytes differ",
    )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D131LocalAdmissionOfflineError("D-131 D-130 gate JSON differs") from exc
    body = payload.get("semantic_body")
    _require(
        isinstance(payload, dict)
        and isinstance(body, dict)
        and payload.get("schema_version") == d130.SCHEMA_VERSION
        and payload.get("gate_id") == D130_GATE_ID
        and payload.get("semantic_body_hash") == D130_GATE_BODY_SHA256
        and sha256_text(canonical_json(body)) == D130_GATE_BODY_SHA256
        and body.get("status") == D130_GATE_STATUS
        and _pretty_bytes(payload) == raw,
        "D-131 D-130 gate tuple differs",
    )
    return {
        "path": D130_GATE_PATH.as_posix(),
        "schema_version": d130.SCHEMA_VERSION,
        "gate_id": D130_GATE_ID,
        "semantic_body_hash": D130_GATE_BODY_SHA256,
        "file_sha256": D130_GATE_FILE_SHA256,
        "file_bytes": D130_GATE_FILE_BYTES,
        "status": D130_GATE_STATUS,
        "recorded_at": body["recorded_at"],
        "evidence_commit": D130_EVIDENCE_COMMIT,
        "evidence_tree": D130_EVIDENCE_TREE,
        "evidence_parents": [D130_EVIDENCE_PARENT],
        "gate_blob_oid": D130_GATE_BLOB_OID,
        "artifact_mutated": False,
    }


def _source_identity_for_gate(root: Path) -> dict[str, Any]:
    _assert_runtime_import_boundary(root)
    _require(_status_lines(root) == [], "D-131 gate requires clean committed source")
    head = _head(root)
    identity = _commit_identity(root, head)
    _require(identity["parents"] == [D130_EVIDENCE_COMMIT], "D-131 source parent differs")
    expected = [{"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS]
    _require(
        sorted(_diff_rows(root, head), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-131 source scope differs",
    )
    return {
        "commit": head,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "implementation_paths_added": [path.as_posix() for path in IMPLEMENTATION_PATHS],
        "file_bindings": [_file_binding(root, head, path) for path in SOURCE_BINDING_PATHS],
        "loaded_module_bindings": _loaded_module_bindings(root, head),
        "python_routing_env_presence": {name: False for name in PYTHON_ROUTING_ENV_NAMES},
        "git_cli_observation": _git_cli_observation(root),
        "worktree_and_index_clean_before_gate": True,
        "git_identity_vendor_authenticated_or_signed": False,
    }


def _validate_source_identity(root: Path, source: Any) -> None:
    _assert_runtime_import_boundary(root)
    expected_keys = {
        "commit",
        "tree",
        "parents",
        "implementation_paths_added",
        "file_bindings",
        "loaded_module_bindings",
        "python_routing_env_presence",
        "git_cli_observation",
        "worktree_and_index_clean_before_gate",
        "git_identity_vendor_authenticated_or_signed",
    }
    _require(
        isinstance(source, dict) and set(source) == expected_keys, "D-131 source fields differ"
    )
    identity = _commit_identity(root, source["commit"])
    _require(
        identity["tree"] == source["tree"]
        and identity["parents"] == [D130_EVIDENCE_COMMIT]
        and source["parents"] == [D130_EVIDENCE_COMMIT],
        "D-131 source topology differs",
    )
    expected = [{"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS]
    _require(
        sorted(_diff_rows(root, source["commit"]), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-131 source commit scope differs",
    )
    _require(
        source["implementation_paths_added"] == [path.as_posix() for path in IMPLEMENTATION_PATHS]
        and source["python_routing_env_presence"]
        == {name: False for name in PYTHON_ROUTING_ENV_NAMES}
        and source["worktree_and_index_clean_before_gate"] is True
        and source["git_identity_vendor_authenticated_or_signed"] is False,
        "D-131 source claims differ",
    )
    expected_files = [_file_binding(root, source["commit"], path) for path in SOURCE_BINDING_PATHS]
    _require(
        canonical_json(source["file_bindings"]) == canonical_json(expected_files),
        "D-131 source file bindings differ",
    )
    _require(
        canonical_json(source["loaded_module_bindings"])
        == canonical_json(_loaded_module_bindings(root, source["commit"])),
        "D-131 loaded module bindings differ",
    )
    _validate_git_observation(root, source["git_cli_observation"])


def _gate_authority() -> dict[str, Any]:
    return {
        "d131_offline_source_gate_materialized": True,
        "d130_stage1_prior_approval_received_but_not_exercised": True,
        "d130_stage1_prior_approval_reusable_after_topology_change": False,
        "d131_local_admission_approval_recorded": False,
        "d130_receipt_created": False,
        "d130_armed_intent_created": False,
        "d130_external_activation_recorded": False,
        "d130_external_phase_attempt_created": False,
        "d131_official_docs_or_network_call_count": 0,
        "d131_docker_sdk_or_credential_observation_count": 0,
        "d131_provider_evaluator_agent_call_count": 0,
        "d131_retrieval_or_memory_injection_count": 0,
        "d131_execution_hash_created": False,
        "d131_execution_candidate_created": False,
        "d131_cost_reserved_or_spent_usd": "0",
        "d131_four_row_ac_execution_authorized": False,
    }


def _qualified_contract() -> dict[str, Any]:
    return {
        "receipt_path": RECEIPT_PATH.as_posix(),
        "receipt_schema": RECEIPT_SCHEMA,
        "receipt_status": RECEIPT_STATUS,
        "receipt_writer_requires_clean_d131_evidence_commit": True,
        "receipt_commit_must_be_single_artifact_add": True,
        "intent_path": INTENT_PATH.as_posix(),
        "intent_schema": INTENT_SCHEMA,
        "intent_status": INTENT_STATUS,
        "intent_writer_requires_clean_receipt_only_commit": True,
        "intent_commit_must_be_single_artifact_add": True,
        "writers_are_append_only_idempotent_and_collision_fail_closed": True,
        "orphan_or_descendant_collision_blocks_without_repair": True,
        "challenge_requires_clean_committed_intent": True,
        "challenge_quotes_gate_receipt_intent_and_both_commits": True,
        "challenge_is_not_activation": True,
        "external_action_count_during_local_admission": 0,
    }


def _gate_body(
    *, recorded_at: str, predecessor: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d130-local-admission-implementation-offline-source-gate",
        "recorded_at": recorded_at,
        "status": STATUS,
        "predecessor_binding": predecessor,
        "source_identity": source,
        "qualified_local_admission_contract": _qualified_contract(),
        "implementation_integrity": {
            "implementation_paths": [path.as_posix() for path in IMPLEMENTATION_PATHS],
            "dependency_paths": [path.as_posix() for path in DEPENDENCY_PATHS],
            "focused_tests_passed": FOCUSED_TESTS_PASSED,
            "gate_builder_writer_invocation_count": 0,
            "gate_builder_challenge_render_count": 0,
            "gate_builder_reads_dotenv_or_credential_value": False,
            "gate_builder_reads_parent_environment_values_for_git": False,
            "gate_builder_uses_fixed_literal_secret_free_git_environment": True,
        },
        "offline_qualification": {
            "exact_d130_gate_and_evidence_commit_verified": True,
            "source_commit_and_loaded_modules_verified": True,
            "receipt_and_intent_writer_contracts_qualified_offline": True,
            "receipt_or_intent_materialized": False,
            "qualification_grade": "offline-source-and-mock-only",
        },
        "blocked_prerequisites": [
            "fresh-exact-d131-local-admission-approval-not-recorded",
            "d130-receipt-only-commit-not-created",
            "d130-armed-intent-only-commit-not-created",
            "separate-exact-external-activation-not-recorded",
            "docker-pricing-sdk-no-call-readiness-not-observed",
            "execution-hash-candidate-cost-and-ac-remain-later-gates",
        ],
        "evidence_boundary": {
            "today_d130_approval_was_not_exercised_due_missing_committed_writer": True,
            "today_d130_approval_must_not_be_reused_after_d131_topology_change": True,
            "d131_implemented_but_did_not_invoke_future_writers": True,
            "d131_performed_no_external_or_credential_observation": True,
            "git_identity_is_observed_not_vendor_authenticated_or_signed": True,
            "gate_does_not_self_bind_its_future_evidence_commit": True,
            "d131_source_preparation_approval": {
                "approval_mode": "current-user-message-self-attested-unsigned",
                "approval_is_authenticated_or_cryptographically_signed": False,
                "approved_scope": list(D131_SOURCE_PREPARATION_SCOPE),
                "not_authorized": list(D131_SOURCE_PREPARATION_EXCLUSIONS),
                "local_admission_authority_recorded": False,
            },
        },
        "authority": _gate_authority(),
        "next_gate": {
            "action": "request-fresh-exact-d131-qualified-d130-local-admission-approval",
            "must_quote_exact_d131_gate_tuple_bytes_and_evidence_commit": True,
            "may_create_only_receipt-and-armed-intent-local-commits": True,
            "must_keep-all-external-actions-zero": True,
            "requires-separate-exact-activation-after-committed-intent": True,
            "does_not_authorize-execution-hash-candidate-cost-or-ac": True,
        },
    }


def _validate_gate_checkout(root: Path, source: dict[str, Any], raw: bytes) -> dict[str, Any]:
    head = _head(root)
    status = _status_lines(root)
    if head == source["commit"]:
        _require(status == [f"?? {OUTPUT_PATH.as_posix()}"], "D-131 source checkout state differs")
        return {"source_commit": head, "evidence_commit": None}
    identity = _commit_identity(root, head)
    _require(identity["parents"] == [source["commit"]], "D-131 evidence parent differs")
    expected = [
        {"status": "A", "path": OUTPUT_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
    ]
    _require(
        sorted(_diff_rows(root, head), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-131 evidence scope differs",
    )
    _require(status == [], "D-131 post-evidence checkout is not clean")
    _, committed = _commit_blob(root, head, OUTPUT_PATH)
    _require(committed == raw, "D-131 committed gate bytes differ")
    return {"source_commit": source["commit"], "evidence_commit": head}


def _validate_gate_payload(
    root: Path,
    payload: Any,
    raw: bytes,
    *,
    check_checkout: bool = True,
    require_future_absence: bool = True,
) -> dict[str, Any]:
    _require(
        isinstance(payload, dict) and tuple(payload) == GATE_ROOT_KEYS, "D-131 gate root differs"
    )
    _require(payload["schema_version"] == SCHEMA_VERSION, "D-131 gate schema differs")
    body = payload["semantic_body"]
    _require(isinstance(body, dict) and tuple(body) == GATE_BODY_KEYS, "D-131 gate fields differ")
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload["semantic_body_hash"] == body_hash
        and payload["gate_id"] == f"d131_{body_hash.removeprefix('sha256:')}"
        and _pretty_bytes(payload) == raw,
        "D-131 gate envelope differs",
    )
    predecessor = _d130_predecessor_binding(root)
    _validate_source_identity(root, body["source_identity"])
    expected = _gate_envelope(
        _gate_body(
            recorded_at=body["recorded_at"],
            predecessor=predecessor,
            source=body["source_identity"],
        )
    )
    _require(canonical_json(payload) == canonical_json(expected), "D-131 gate full rebuild differs")
    _require(
        _parse_time(body["recorded_at"], label="gate recorded_at")
        > _parse_time(predecessor["recorded_at"], label="D-130 gate recorded_at"),
        "D-131 gate chronology differs",
    )
    if require_future_absence:
        for path in (RECEIPT_PATH, INTENT_PATH, *FUTURE_EXTERNAL_PATHS):
            _path_absent(root, path)
    checkout = (
        _validate_gate_checkout(root, body["source_identity"], raw)
        if check_checkout
        else {"source_commit": body["source_identity"]["commit"], "evidence_commit": None}
    )
    return {**payload, "_checkout": checkout}


def _gate_result(payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    checkout = payload.get("_checkout", {})
    return {
        "status": STATUS,
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "source_commit": payload["semantic_body"]["source_identity"]["commit"],
        "evidence_commit": checkout.get("evidence_commit"),
        "fresh_local_admission_approval_required": True,
        "receipt_created": False,
        "armed_intent_created": False,
        "external_call_count": 0,
    }


def run_d131_offline_source_gate(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Materialize only the append-only D-131 offline source gate."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    if d129_offline._lexists(root / OUTPUT_PATH):
        return validate_d131_offline_source_gate(repository=root)
    for path in (RECEIPT_PATH, INTENT_PATH, *FUTURE_EXTERNAL_PATHS):
        _path_absent(root, path)
    predecessor = _d130_predecessor_binding(root)
    source = _source_identity_for_gate(root)
    recorded_at = _now()
    _require(
        _parse_time(recorded_at, label="gate recorded_at")
        > _parse_time(predecessor["recorded_at"], label="D-130 gate recorded_at"),
        "D-131 gate chronology differs before publication",
    )
    payload = _gate_envelope(
        _gate_body(recorded_at=recorded_at, predecessor=predecessor, source=source)
    )
    raw = _pretty_bytes(payload)
    _validate_gate_payload(root, payload, raw, check_checkout=False)
    _write_new(root, OUTPUT_PATH, raw)
    return validate_d131_offline_source_gate(repository=root)


def validate_d131_offline_source_gate(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Validate the exact D-131 source gate without invoking future writers."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    payload, raw = _read_json(root, OUTPUT_PATH)
    return _gate_result(_validate_gate_payload(root, payload, raw), raw)


def render_d131_local_admission_template(*, repository: str | Path | None = None) -> str:
    """Render the next local-only approval template without side effects."""

    result = validate_d131_offline_source_gate(repository=repository)
    evidence = result["evidence_commit"] or "<exact D-131 gate+docs evidence commit>"
    return "\n".join(
        (
            "D-131-qualified D-130 local admission approval (external actions remain zero)",
            "",
            f"Gate ID: {result['gate_id']}",
            f"Body SHA: {result['semantic_body_hash']}",
            f"File SHA: {result['file_sha256']}",
            f"File bytes: {result['file_bytes']}",
            f"Source/evidence commit: {evidence}",
            "",
            "Approved local-only scope:",
            "- create and commit one exact D-130 approval receipt",
            "- create and commit one durable ARMED_WAITING_EXACT_ACTIVATION intent",
            "- render the exact external activation challenge",
            "",
            "Explicitly not approved:",
            "- official docs, network, pricing, Docker, SDK, credential or endpoint observation",
            "- provider/evaluator/agent, memory/retrieval",
            "- execution hash/candidate, cost, or four-row A/C",
            "",
            "A later exact activation must quote the gate, receipt, intent, "
            "receipt commit, and intent commit tuples.",
        )
    )


def _artifact_binding(
    *,
    path: Path,
    payload: dict[str, Any],
    raw: bytes,
    status: str,
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


def _rebuild_single_artifact_commit(
    root: Path,
    *,
    commit: str,
    parent: str,
    path: Path,
    raw: bytes,
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [parent], f"D-131 {path.name} commit parent differs")
    _require(
        _diff_rows(root, commit) == [{"status": "A", "path": path.as_posix()}],
        f"D-131 {path.name} commit is not artifact-only",
    )
    oid, committed = _commit_blob(root, commit, path)
    _require(committed == raw, f"D-131 {path.name} commit blob differs")
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


def _rebuild_gate_evidence_commit(
    root: Path,
    *,
    commit: str,
    source: dict[str, Any],
    gate_raw: bytes,
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [source["commit"]], "D-131 gate evidence parent differs")
    expected = [
        {"status": "A", "path": OUTPUT_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
    ]
    _require(
        sorted(_diff_rows(root, commit), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-131 gate evidence scope differs",
    )
    oid, committed = _commit_blob(root, commit, OUTPUT_PATH)
    _require(committed == gate_raw, "D-131 gate evidence bytes differ")
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


def _d131_gate_for_admission(
    root: Path,
    *,
    stored_commit: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bytes, dict[str, Any], dict[str, Any]]:
    gate_payload, gate_raw = _read_json(root, OUTPUT_PATH)
    validated = _validate_gate_payload(
        root,
        gate_payload,
        gate_raw,
        check_checkout=False,
        require_future_absence=False,
    )
    source = validated["semantic_body"]["source_identity"]
    if stored_commit is None:
        _require(_status_lines(root) == [], "D-130 receipt requires clean D-131 evidence commit")
        gate_commit = _rebuild_gate_evidence_commit(
            root,
            commit=_head(root),
            source=source,
            gate_raw=gate_raw,
        )
    else:
        _require(
            isinstance(stored_commit, dict)
            and tuple(stored_commit) == GATE_EVIDENCE_COMMIT_BINDING_KEYS,
            "D-131 gate commit fields differ",
        )
        gate_commit = _rebuild_gate_evidence_commit(
            root,
            commit=stored_commit["commit"],
            source=source,
            gate_raw=gate_raw,
        )
        _require(
            canonical_json(stored_commit) == canonical_json(gate_commit),
            "D-131 gate commit full rebuild differs",
        )
    gate_binding = {
        "path": OUTPUT_PATH.as_posix(),
        "gate_id": gate_payload["gate_id"],
        "semantic_body_hash": gate_payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(gate_raw),
        "file_bytes": len(gate_raw),
        "status": STATUS,
        "recorded_at": gate_payload["semantic_body"]["recorded_at"],
        "source_commit": source["commit"],
        "evidence_commit_binding": gate_commit,
        "artifact_mutated": False,
    }
    return gate_payload, gate_raw, source, gate_binding


def _local_admission_authority(*, receipt: bool, intent: bool) -> dict[str, Any]:
    return {
        "d131_local_admission_approval_recorded": receipt,
        "d130_receipt_created": receipt,
        "d130_receipt_committed": intent,
        "d130_armed_intent_created": intent,
        "d130_external_activation_recorded": False,
        "d130_external_phase_attempt_created": False,
        "official_docs_or_network_call_count": 0,
        "canonical_pricing_capture_get_count": 0,
        "docker_cli_daemon_image_or_container_call_count": 0,
        "sdk_credential_or_endpoint_observation_count": 0,
        "provider_evaluator_agent_call_count": 0,
        "retrieval_or_memory_injection_count": 0,
        "execution_hash_created": False,
        "execution_candidate_created": False,
        "cost_reserved_or_spent_usd": "0",
        "four_row_ac_execution_authorized": False,
    }


def _receipt_body(
    *,
    recorded_at: str,
    gate: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": "D-130-local-admission",
        "evidence_kind": "exact-local-admission-approval-receipt",
        "recorded_at": recorded_at,
        "status": RECEIPT_STATUS,
        "d131_gate_binding": gate,
        "source_identity": source,
        "approval_binding": {
            "approval_mode": "current-user-message-self-attested-unsigned",
            "approval_is_authenticated_or_cryptographically_signed": False,
            "approved_scope": list(LOCAL_ADMISSION_SCOPE),
            "not_authorized": list(LOCAL_ADMISSION_EXCLUSIONS),
            "fresh_approval_quotes_d131_gate_and_evidence_commit": True,
            "prior_d130_approval_reused": False,
        },
        "event_order": [
            {"ordinal": 1, "event": "fresh-exact-d131-qualified-local-admission-approved"},
            {"ordinal": 2, "event": "approval-receipt-recorded"},
        ],
        "evidence_boundary": {
            "receipt_writer_reads_dotenv_or_credential_value": False,
            "receipt_writer_reads_parent_environment_values_for_git": False,
            "receipt_writer_uses_fixed_literal_secret_free_git_environment": True,
            "receipt_writer_external_call_count": 0,
            "receipt_is_not_activation_attempt_or-candidate": True,
            "receipt_requires-single-artifact-commit-before-intent": True,
        },
        "authority": _local_admission_authority(receipt=True, intent=False),
        "next_gate": {
            "action": "commit-receipt-only-then-create-durable-armed-intent",
            "receipt_commit_must_be-single-artifact-add": True,
            "external-actions-remain-zero": True,
            "does-not-authorize-activation-or-execution": True,
        },
    }


def _validate_receipt_payload(root: Path, payload: Any, raw: bytes) -> dict[str, Any]:
    _require(
        isinstance(payload, dict) and tuple(payload) == ROOT_KEYS, "D-130 receipt root differs"
    )
    _require(payload["schema_version"] == RECEIPT_SCHEMA, "D-130 receipt schema differs")
    body = payload["semantic_body"]
    _require(
        isinstance(body, dict) and tuple(body) == RECEIPT_BODY_KEYS,
        "D-130 receipt fields differ",
    )
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload["semantic_body_hash"] == body_hash
        and payload["artifact_id"] == f"d130approval_{body_hash.removeprefix('sha256:')}"
        and _pretty_bytes(payload) == raw,
        "D-130 receipt envelope differs",
    )
    gate_commit = body.get("d131_gate_binding", {}).get("evidence_commit_binding")
    _, _, source, gate = _d131_gate_for_admission(root, stored_commit=gate_commit)
    _validate_source_identity(root, source)
    expected = _envelope(
        RECEIPT_SCHEMA,
        "d130approval",
        _receipt_body(recorded_at=body["recorded_at"], gate=gate, source=source),
    )
    _require(
        canonical_json(payload) == canonical_json(expected), "D-130 receipt full rebuild differs"
    )
    _require(
        _parse_time(body["recorded_at"], label="receipt recorded_at")
        > _parse_time(gate["recorded_at"], label="D-131 gate recorded_at"),
        "D-130 receipt chronology differs",
    )
    return payload


def _receipt_result(payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "status": RECEIPT_STATUS,
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "receipt_created": True,
        "armed_intent_created": False,
        "external_call_count": 0,
    }


def create_d130_local_admission_receipt(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Create the future D-130 receipt under a fresh exact approval; no external action."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in (INTENT_PATH, *FUTURE_EXTERNAL_PATHS):
        _path_absent(root, path)
    if d129_offline._lexists(root / RECEIPT_PATH):
        payload, raw = _read_json(root, RECEIPT_PATH)
        return _receipt_result(_validate_receipt_payload(root, payload, raw), raw)
    _, _, source, gate = _d131_gate_for_admission(root)
    recorded_at = _now()
    _require(
        _parse_time(recorded_at, label="receipt recorded_at")
        > _parse_time(gate["recorded_at"], label="D-131 gate recorded_at"),
        "D-130 receipt chronology differs before publication",
    )
    payload = _envelope(
        RECEIPT_SCHEMA,
        "d130approval",
        _receipt_body(recorded_at=recorded_at, gate=gate, source=source),
    )
    raw = _pretty_bytes(payload)
    _validate_receipt_payload(root, payload, raw)
    _write_new(root, RECEIPT_PATH, raw)
    stored, stored_raw = _read_json(root, RECEIPT_PATH)
    return _receipt_result(_validate_receipt_payload(root, stored, stored_raw), stored_raw)


def _receipt_binding(payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return _artifact_binding(
        path=RECEIPT_PATH,
        payload=payload,
        raw=raw,
        status=RECEIPT_STATUS,
    )


def _rebuild_receipt_commit_binding(
    root: Path,
    *,
    commit: str,
    receipt: dict[str, Any],
    receipt_raw: bytes,
) -> dict[str, Any]:
    parent = receipt["semantic_body"]["d131_gate_binding"]["evidence_commit_binding"]["commit"]
    return _rebuild_single_artifact_commit(
        root,
        commit=commit,
        parent=parent,
        path=RECEIPT_PATH,
        raw=receipt_raw,
    )


def _receipt_commit_binding(
    root: Path, receipt: dict[str, Any], receipt_raw: bytes
) -> dict[str, Any]:
    _require(_status_lines(root) == [], "D-130 armed intent requires clean receipt commit")
    return _rebuild_receipt_commit_binding(
        root,
        commit=_head(root),
        receipt=receipt,
        receipt_raw=receipt_raw,
    )


def _intent_body(
    *,
    recorded_at: str,
    gate: dict[str, Any],
    source: dict[str, Any],
    receipt: dict[str, Any],
    receipt_commit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": "D-130-local-admission",
        "evidence_kind": "durable-external-phase-armed-intent",
        "recorded_at": recorded_at,
        "status": INTENT_STATUS,
        "d131_gate_binding": gate,
        "source_identity": source,
        "receipt_binding": receipt,
        "receipt_commit_binding": receipt_commit,
        "armed_state": {
            "state": "ARMED_WAITING_EXACT_ACTIVATION",
            "receipt_consumed_for_single_intent": True,
            "activation_recorded": False,
            "external_phase_attempt_created": False,
            "retry_resume_or_replacement_authorized": False,
        },
        "activation_challenge_contract": {
            "proposed_approved_scope": list(ACTIVATION_SCOPE),
            "explicitly_not_authorized": list(ACTIVATION_EXCLUSIONS),
            "must_quote_gate_receipt_intent_receipt_commit_and_intent_commit": True,
            "challenge_is_not_activation": True,
        },
        "activity_accounting": {
            "official_docs_or_network_call_count": 0,
            "docker_cli_daemon_image_or_container_call_count": 0,
            "sdk_credential_or_endpoint_observation_count": 0,
            "provider_evaluator_agent_call_count": 0,
            "retrieval_or_memory_injection_count": 0,
            "cost_reserved_or_spent_usd": "0",
        },
        "evidence_boundary": {
            "intent_writer_reads_dotenv_or_credential_value": False,
            "intent_writer_reads_parent_environment_values_for_git": False,
            "intent_writer_uses_fixed_literal_secret_free_git_environment": True,
            "intent_writer_external_call_count": 0,
            "intent_requires-single-artifact-commit-before-challenge": True,
            "intent_does_not_authorize_external-action": True,
        },
        "authority": _local_admission_authority(receipt=True, intent=True),
        "next_gate": {
            "action": "commit-intent-only-then-request-separate-exact-external-activation",
            "intent_commit_must_be-single-artifact-add": True,
            "activation-must-quote-all-five-tuples": True,
            "external-actions-remain-zero-until-activation": True,
        },
    }


def _validate_intent_payload(root: Path, payload: Any, raw: bytes) -> dict[str, Any]:
    _require(isinstance(payload, dict) and tuple(payload) == ROOT_KEYS, "D-130 intent root differs")
    _require(payload["schema_version"] == INTENT_SCHEMA, "D-130 intent schema differs")
    body = payload["semantic_body"]
    _require(
        isinstance(body, dict) and tuple(body) == INTENT_BODY_KEYS,
        "D-130 intent fields differ",
    )
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload["semantic_body_hash"] == body_hash
        and payload["artifact_id"] == f"d130intent_{body_hash.removeprefix('sha256:')}"
        and _pretty_bytes(payload) == raw,
        "D-130 intent envelope differs",
    )
    receipt_payload, receipt_raw = _read_json(root, RECEIPT_PATH)
    _validate_receipt_payload(root, receipt_payload, receipt_raw)
    source = receipt_payload["semantic_body"]["source_identity"]
    gate = receipt_payload["semantic_body"]["d131_gate_binding"]
    receipt = _receipt_binding(receipt_payload, receipt_raw)
    receipt_commit = body["receipt_commit_binding"]
    _require(
        isinstance(receipt_commit, dict) and tuple(receipt_commit) == COMMIT_BINDING_KEYS,
        "D-130 receipt commit fields differ",
    )
    rebuilt = _rebuild_receipt_commit_binding(
        root,
        commit=receipt_commit["commit"],
        receipt=receipt_payload,
        receipt_raw=receipt_raw,
    )
    _require(
        canonical_json(receipt_commit) == canonical_json(rebuilt),
        "D-130 receipt commit full rebuild differs",
    )
    expected = _envelope(
        INTENT_SCHEMA,
        "d130intent",
        _intent_body(
            recorded_at=body["recorded_at"],
            gate=gate,
            source=source,
            receipt=receipt,
            receipt_commit=receipt_commit,
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected), "D-130 intent full rebuild differs"
    )
    _require(
        _parse_time(body["recorded_at"], label="intent recorded_at")
        > _parse_time(receipt["recorded_at"], label="receipt recorded_at"),
        "D-130 intent chronology differs",
    )
    for path in FUTURE_EXTERNAL_PATHS:
        _path_absent(root, path)
    return payload


def _intent_result(
    payload: dict[str, Any], raw: bytes, *, intent_commit: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "status": INTENT_STATUS,
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "receipt_artifact_id": payload["semantic_body"]["receipt_binding"]["artifact_id"],
        "intent_commit": None if intent_commit is None else intent_commit["commit"],
        "armed_waiting_exact_activation": True,
        "external_call_count": 0,
    }


def create_d130_armed_intent(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Create the future durable armed intent after an exact receipt-only commit."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    if d129_offline._lexists(root / INTENT_PATH):
        payload, raw = _read_json(root, INTENT_PATH)
        return _intent_result(_validate_intent_payload(root, payload, raw), raw)
    for path in FUTURE_EXTERNAL_PATHS:
        _path_absent(root, path)
    receipt_payload, receipt_raw = _read_json(root, RECEIPT_PATH)
    _validate_receipt_payload(root, receipt_payload, receipt_raw)
    receipt_commit = _receipt_commit_binding(root, receipt_payload, receipt_raw)
    source = receipt_payload["semantic_body"]["source_identity"]
    gate = receipt_payload["semantic_body"]["d131_gate_binding"]
    receipt = _receipt_binding(receipt_payload, receipt_raw)
    recorded_at = _now()
    _require(
        _parse_time(recorded_at, label="intent recorded_at")
        > _parse_time(receipt["recorded_at"], label="receipt recorded_at"),
        "D-130 intent chronology differs before publication",
    )
    payload = _envelope(
        INTENT_SCHEMA,
        "d130intent",
        _intent_body(
            recorded_at=recorded_at,
            gate=gate,
            source=source,
            receipt=receipt,
            receipt_commit=receipt_commit,
        ),
    )
    raw = _pretty_bytes(payload)
    _validate_intent_payload(root, payload, raw)
    _write_new(root, INTENT_PATH, raw)
    stored, stored_raw = _read_json(root, INTENT_PATH)
    return _intent_result(_validate_intent_payload(root, stored, stored_raw), stored_raw)


def _rebuild_intent_commit_binding(
    root: Path,
    *,
    commit: str,
    intent: dict[str, Any],
    intent_raw: bytes,
) -> dict[str, Any]:
    parent = intent["semantic_body"]["receipt_commit_binding"]["commit"]
    return _rebuild_single_artifact_commit(
        root,
        commit=commit,
        parent=parent,
        path=INTENT_PATH,
        raw=intent_raw,
    )


def validate_d130_local_admission(
    *,
    repository: str | Path | None = None,
    mode: Literal["receipt", "armed-intent", "post-intent-commit"] = "armed-intent",
) -> dict[str, Any]:
    """Validate a future local-admission phase without external activity."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    if mode == "receipt":
        payload, raw = _read_json(root, RECEIPT_PATH)
        return _receipt_result(_validate_receipt_payload(root, payload, raw), raw)
    _require(mode in {"armed-intent", "post-intent-commit"}, "D-130 validation mode differs")
    payload, raw = _read_json(root, INTENT_PATH)
    validated = _validate_intent_payload(root, payload, raw)
    intent_commit = None
    if mode == "post-intent-commit":
        _require(_status_lines(root) == [], "D-130 challenge requires clean intent commit")
        intent_commit = _rebuild_intent_commit_binding(
            root,
            commit=_head(root),
            intent=validated,
            intent_raw=raw,
        )
    return _intent_result(validated, raw, intent_commit=intent_commit)


def render_d130_external_activation_challenge(*, repository: str | Path | None = None) -> str:
    """Render the future exact activation challenge after a committed intent."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    _require(_status_lines(root) == [], "D-130 challenge requires clean intent commit")
    intent_payload, intent_raw = _read_json(root, INTENT_PATH)
    intent_payload = _validate_intent_payload(root, intent_payload, intent_raw)
    receipt_payload, receipt_raw = _read_json(root, RECEIPT_PATH)
    receipt_payload = _validate_receipt_payload(root, receipt_payload, receipt_raw)
    gate = intent_payload["semantic_body"]["d131_gate_binding"]
    receipt_commit = intent_payload["semantic_body"]["receipt_commit_binding"]
    rebuilt_receipt_commit = _rebuild_receipt_commit_binding(
        root,
        commit=receipt_commit["commit"],
        receipt=receipt_payload,
        receipt_raw=receipt_raw,
    )
    _require(
        canonical_json(receipt_commit) == canonical_json(rebuilt_receipt_commit),
        "D-130 challenge receipt commit differs",
    )
    receipt = _receipt_binding(receipt_payload, receipt_raw)
    _require(
        canonical_json(receipt)
        == canonical_json(intent_payload["semantic_body"]["receipt_binding"]),
        "D-130 challenge receipt binding differs",
    )
    _require(_status_lines(root) == [], "D-130 challenge checkout changed during validation")
    intent_commit = _rebuild_intent_commit_binding(
        root,
        commit=_head(root),
        intent=intent_payload,
        intent_raw=intent_raw,
    )
    intent = _artifact_binding(
        path=INTENT_PATH,
        payload=intent_payload,
        raw=intent_raw,
        status=INTENT_STATUS,
    )
    lines = [
        "D-130 external no-call preflight exact activation request",
        "",
        f"D-131 gate: {gate['gate_id']}",
        f"D-131 gate body SHA: {gate['semantic_body_hash']}",
        f"D-131 gate file SHA: {gate['file_sha256']}",
        f"D-131 gate file bytes: {gate['file_bytes']}",
        f"D-131 gate evidence commit tuple: {canonical_json(gate['evidence_commit_binding'])}",
        f"Receipt ID: {receipt['artifact_id']}",
        f"Receipt body SHA: {receipt['semantic_body_hash']}",
        f"Receipt file SHA: {receipt['file_sha256']}",
        f"Receipt file bytes: {receipt['file_bytes']}",
        f"Receipt commit tuple: {canonical_json(receipt_commit)}",
        f"Intent ID: {intent['artifact_id']}",
        f"Intent body SHA: {intent['semantic_body_hash']}",
        f"Intent file SHA: {intent['file_sha256']}",
        f"Intent file bytes: {intent['file_bytes']}",
        f"Intent commit tuple: {canonical_json(intent_commit)}",
        "",
        "Proposed approved scope:",
        *(f"- {item}" for item in ACTIVATION_SCOPE),
        "",
        "Explicitly not authorized:",
        *(f"- {item}" for item in ACTIVATION_EXCLUSIONS),
        "",
        "This challenge is not activation. A new exact user message must quote every tuple above.",
    ]
    return "\n".join(lines)


__all__ = [
    "D131LocalAdmissionOfflineError",
    "INTENT_PATH",
    "INTENT_SCHEMA",
    "INTENT_STATUS",
    "OUTPUT_PATH",
    "RECEIPT_PATH",
    "RECEIPT_SCHEMA",
    "RECEIPT_STATUS",
    "SCHEMA_VERSION",
    "STATUS",
    "create_d130_armed_intent",
    "create_d130_local_admission_receipt",
    "render_d130_external_activation_challenge",
    "render_d131_local_admission_template",
    "run_d131_offline_source_gate",
    "validate_d130_local_admission",
    "validate_d131_offline_source_gate",
]
