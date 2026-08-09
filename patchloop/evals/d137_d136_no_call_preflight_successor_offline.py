"""D-137 offline qualification and future two-phase no-call preflight.

The module binds the completed D-136 pricing successor without importing any
historical external runner.  Gate construction is offline.  Future Docker and
SDK observations remain separately activation-gated and use attempt-first,
durable marker, terminal-or-marker-only one-use transitions.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import patchloop as patchloop_module
from patchloop import errors as patchloop_errors
from patchloop import evals as patchloop_evals
from patchloop import util as patchloop_util
from patchloop.errors import ContractError
from patchloop.evals import d137_no_call_preflight as no_call
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-137"
GATE_SCHEMA = "d136-success-terminal-no-call-preflight-successor-offline-source-gate-d137-v1"
GATE_STATUS = (
    "D137_D136_SUCCESS_TERMINAL_NO_CALL_PREFLIGHT_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_"
    "FRESH_ACTIVATION_REQUIRED"
)
GATE_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d137-d136-success-terminal-no-call-preflight-successor-offline-source-gate.json"
)

RECEIPT_SCHEMA = "d137-no-call-preflight-successor-activation-receipt-v1"
RECEIPT_STATUS = "D137_NO_CALL_PREFLIGHT_SUCCESSOR_ACTIVATION_RECEIPT_RECORDED_COMMIT_REQUIRED"
RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/d137-no-call-preflight-successor-activation-receipt.json"
)

DOCKER_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d137-docker-no-call-preflight-attempt-intent.json"
)
DOCKER_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/d137-docker-no-call-preflight-action-started.json"
)
DOCKER_TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d137-docker-no-call-preflight-terminal.json"
)
SDK_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d137-sdk-no-call-preflight-attempt-intent.json"
)
SDK_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/d137-sdk-no-call-preflight-action-started.json"
)
SDK_TERMINAL_PATH = Path("reports/live-pilot/artifacts/d137-sdk-no-call-preflight-terminal.json")

ATTEMPT_SCHEMA = "d137-no-call-preflight-phase-attempt-intent-v1"
STARTED_SCHEMA = "d137-no-call-preflight-phase-action-started-v1"
TERMINAL_SCHEMA = "d137-no-call-preflight-phase-terminal-v1"
DOCKER_ATTEMPT_STATUS = "D137_DOCKER_NO_CALL_PREFLIGHT_ATTEMPT_RECORDED_COMMIT_REQUIRED"
SDK_ATTEMPT_STATUS = "D137_SDK_NO_CALL_PREFLIGHT_ATTEMPT_RECORDED_COMMIT_REQUIRED"
DOCKER_STARTED_STATUS = "D137_DOCKER_NO_CALL_PREFLIGHT_ACTION_STARTED_TRANSITION_COMMIT_REQUIRED"
SDK_STARTED_STATUS = "D137_SDK_NO_CALL_PREFLIGHT_ACTION_STARTED_TRANSITION_COMMIT_REQUIRED"
DOCKER_TERMINAL_READY_STATUS = "D137_DOCKER_NO_CALL_PREFLIGHT_READY_TRANSITION_COMMIT_REQUIRED"
DOCKER_TERMINAL_BLOCKED_STATUS = "D137_DOCKER_NO_CALL_PREFLIGHT_BLOCKED_TRANSITION_COMMIT_REQUIRED"
SDK_TERMINAL_READY_STATUS = "D137_SDK_NO_CALL_PREFLIGHT_READY_TRANSITION_COMMIT_REQUIRED"
SDK_TERMINAL_BLOCKED_STATUS = "D137_SDK_NO_CALL_PREFLIGHT_BLOCKED_TRANSITION_COMMIT_REQUIRED"

PHASE_DOCKER = "docker"
PHASE_SDK = "sdk"
PHASE_PATHS: dict[str, tuple[Path, Path, Path]] = {
    PHASE_DOCKER: (DOCKER_ATTEMPT_PATH, DOCKER_STARTED_PATH, DOCKER_TERMINAL_PATH),
    PHASE_SDK: (SDK_ATTEMPT_PATH, SDK_STARTED_PATH, SDK_TERMINAL_PATH),
}
FUTURE_PATHS = (
    RECEIPT_PATH,
    DOCKER_ATTEMPT_PATH,
    DOCKER_STARTED_PATH,
    DOCKER_TERMINAL_PATH,
    SDK_ATTEMPT_PATH,
    SDK_STARTED_PATH,
    SDK_TERMINAL_PATH,
)

D136_GATE_PATH = Path(
    "reports/live-pilot/artifacts/d136-d135-fixed-pricing-successor-offline-source-gate.json"
)
D136_RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/d136-fixed-pricing-successor-activation-receipt.json"
)
D136_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d136-fixed-pricing-capture-attempt-intent.json"
)
D136_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/d136-fixed-pricing-capture-action-started.json"
)
D136_TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d136-replayable-official-pricing-evidence.json"
)
D136_SOURCE_COMMIT = "96916ac481ac8beced2db0be9022607e0705e018"
D136_SOURCE_TREE = "7e0a07eed6e780265a5d73cab008a0fabe935fe1"
D136_SOURCE_PARENT = "98f4560e718145bc7465732c1a3d2f5a4ea8d786"
D136_GATE_COMMIT = "5fad5756d2b40b5f72c0bbc38680120d780ef899"
D136_GATE_TREE = "54499e4d1f708cc3e815e062da8e33f3aa0a6d6b"
D136_RECEIPT_COMMIT = "1f9c62ac9309d087d1ef32a237b86ea11bf9d51e"
D136_RECEIPT_TREE = "6988fda8dfac16e0097937c4b9b4f8dd3019fb0b"
D136_ATTEMPT_COMMIT = "5f419828c358ee9c5f68cdacf38b588705e71e2e"
D136_ATTEMPT_TREE = "879c38f0d1575adbf03867d172c65d5ab20bc5af"
D136_SUCCESS_COMMIT = "2378569536c2367a3186f575a7517e3de7282336"
D136_SUCCESS_TREE = "c6253191e0a5d96fd6503ad9f9f4f6df91af13cc"

_D136_ARTIFACTS = (
    (
        D136_GATE_PATH,
        "d136_aef9768fcc24b48df09034d14aefcd02b1812531fe77bf56ca1601ac4e5e00fd",
        "sha256:aef9768fcc24b48df09034d14aefcd02b1812531fe77bf56ca1601ac4e5e00fd",
        "sha256:c9e00304383839c656b6a2753fefee459fb14934dec8dfabcf4f39f44a34a53b",
        23_767,
        "062fc2ed4445e073ff2b9e96feff6a6b3e7fd9b4",
        D136_GATE_COMMIT,
    ),
    (
        D136_RECEIPT_PATH,
        "d136approval_630c0694f307c0434e4bb5692bdf23bd76f45f31d1b6c3558415ca588dd50f66",
        "sha256:630c0694f307c0434e4bb5692bdf23bd76f45f31d1b6c3558415ca588dd50f66",
        "sha256:c5cc8211678b12740af3c3c4ea3329d820c86a985942517e5fa4d1be247a6bbb",
        17_724,
        "be0095604f1eb9dcc364f013082e62bafe9637de",
        D136_RECEIPT_COMMIT,
    ),
    (
        D136_ATTEMPT_PATH,
        "d136pricingattempt_3b5d5e23666ea56bfb2fbdeeede3bf845a73b3b2dc12668e12c9ed1de2e34b7e",
        "sha256:3b5d5e23666ea56bfb2fbdeeede3bf845a73b3b2dc12668e12c9ed1de2e34b7e",
        "sha256:d7e883c3efa36274266ebcec5cce7615a58bf0f9d33868752bb92a778b2c12f9",
        2_570,
        "f58c7f1d3f125da8bb9d1b88be0a827b291597e2",
        D136_ATTEMPT_COMMIT,
    ),
    (
        D136_STARTED_PATH,
        "d136pricingstarted_6f4847c856150b0d6bef6108d858ff332d3a1b2c95b0c9ea6bec80d024729fc1",
        "sha256:6f4847c856150b0d6bef6108d858ff332d3a1b2c95b0c9ea6bec80d024729fc1",
        "sha256:4c11a5e087759ecb2a57f5a64271000214469a35f952e8789cc68b297173cd0a",
        2_387,
        "b6090028bb40a6dce721bb1a2c6126cb094537f4",
        D136_SUCCESS_COMMIT,
    ),
    (
        D136_TERMINAL_PATH,
        "d136pricing_dbaa24227565316ef404fb1fc2967e2eb45600a92d7365b8fbbfd7d264881362",
        "sha256:dbaa24227565316ef404fb1fc2967e2eb45600a92d7365b8fbbfd7d264881362",
        "sha256:7ce984e1b7f11bfe9aaaed8a4db38af22ab1299086c54ca20e090badc2d33bc0",
        10_191,
        "ee61520b3325e7a4e2ab891aeccff1a92862a543",
        D136_SUCCESS_COMMIT,
    ),
)

D136_IMPLEMENTATION_PATHS = (
    Path("patchloop/evals/d136_fixed_pricing_capture.py"),
    Path("patchloop/evals/d136_d135_fixed_pricing_successor_offline.py"),
    Path("scripts/build_d136_d135_fixed_pricing_successor_offline.py"),
    Path("tests/test_d136_d135_fixed_pricing_successor_offline.py"),
)
IMPLEMENTATION_PATHS = (
    Path("patchloop/evals/d137_no_call_preflight.py"),
    Path("patchloop/evals/d137_d136_no_call_preflight_successor_offline.py"),
    Path("scripts/build_d137_d136_no_call_preflight_successor_offline.py"),
    Path("tests/test_d137_d136_no_call_preflight_successor_offline.py"),
)
ACTIVE_DOC_PATHS = (
    Path("AGENTS.md"),
    Path("README.md"),
    Path("docs/current-status.md"),
    Path("docs/03-contracts.md"),
    Path("docs/04-evaluation-protocol.md"),
    Path("docs/05-implementation-plan.md"),
    Path("docs/06-decisions.md"),
    Path("docs/07-reproduction.md"),
    Path("docs/08-limitations.md"),
    Path("docs/09-evidence.md"),
)
GIT_ENGINE_PATH = Path(r"C:\Program Files\Git\mingw64\bin\git.exe")
GIT_ENGINE_FILE_BYTES = 4_422_544
GIT_ENGINE_FILE_SHA256 = "sha256:cab4c4eea1d869cf9f7be73868dc9a90ad2df1b1b673e5f8c8714a576c25ea96"
GIT_VERSION = "git version 2.54.0.windows.1"
FIXED_GIT_ENVIRONMENT = {
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
LOADED_MODULE_PATHS = (
    (IMPLEMENTATION_PATHS[1], __name__),
    (IMPLEMENTATION_PATHS[0], no_call.__name__),
    (Path("patchloop/__init__.py"), patchloop_module.__name__),
    (Path("patchloop/evals/__init__.py"), patchloop_evals.__name__),
    (Path("patchloop/errors.py"), patchloop_errors.__name__),
    (Path("patchloop/util.py"), patchloop_util.__name__),
)
DEPENDENCY_PATHS = tuple(
    dict.fromkeys(
        (
            *(path for path, _module_name in LOADED_MODULE_PATHS),
            Path("patchloop/agent/model.py"),
            Path("pyproject.toml"),
            Path("uv.lock"),
        )
    )
)
SOURCE_BINDING_PATHS = tuple(dict.fromkeys((*IMPLEMENTATION_PATHS, *DEPENDENCY_PATHS)))

SOURCE_PREPARATION_SCOPE = (
    "exact-bind-and-replay-validate-complete-d136-gate-receipt-attempt-started-terminal-topology",
    "implement-new-d137-docker-sdk-no-call-preflight-helper-writer-validator-orchestrator-cli-tests",
    "avoid-import-or-execution-of-historical-external-runners-and-mutation-remediation-helpers",
    "implement-separate-future-docker-and-sdk-attempt-first-fsynced-marker-terminal-contracts",
    "constrain-docker-to-bounded-read-only-daemon-digest-image-zero-container-stable-snapshots",
    "constrain-sdk-to-provenance-routing-and-credential-presence-bits-with-zero-transport-dispatch",
    "enforce-append-only-collision-orphan-idempotence-toctou-loaded-module-and-git-provenance",
    "create-exact-four-path-source-only-commit-as-d136-success-direct-child",
    "create-gate-plus-exact-ten-active-doc-evidence-commit-as-source-direct-child",
    "render-fresh-exact-d137-activation-template",
)
SOURCE_PREPARATION_EXCLUSIONS = (
    "create-d137-receipt-attempt-action-started-terminal-or-preservation-artifact",
    "execute-or-observe-docker-daemon-images-containers-or-docker-cli",
    "import-inspect-sdk-runtime-or-observe-credential-environment-dotenv-or-endpoint-state",
    "official-docs-search-open-network-or-pricing-refresh",
    "docker-mutation-image-pull-load-or-container-operation",
    "provider-evaluator-agent-memory-retrieval-hash-candidate-cost-or-four-row-ac",
    "modify-retry-resume-repair-or-backfill-d127-through-d136-source-or-artifacts",
)
ACTIVATION_SCOPE = (
    "create-one-exact-d137-activation-receipt-and-sole-artifact-commit",
    "create-one-exact-d137-docker-attempt-and-sole-artifact-commit",
    "record-one-fsynced-d137-docker-action-started-immediately-before-first-observation",
    "perform-one-bounded-read-only-docker-no-call-preflight",
    "commit-docker-action-started-plus-ready-or-blocked-terminal",
    "preserve-docker-action-started-only-after-post-marker-failure-with-no-retry",
    "after-committed-docker-ready-create-one-sdk-attempt-and-sole-artifact-commit",
    "record-one-fsynced-sdk-action-started-immediately-before-first-observation",
    "perform-one-sdk-presence-and-routing-no-call-preflight-with-zero-transport-dispatch",
    "commit-sdk-action-started-plus-ready-or-blocked-terminal",
    "preserve-sdk-action-started-only-after-post-marker-failure-with-no-retry",
    "request-separate-offline-successor-after-committed-sdk-terminal",
)
ACTIVATION_EXCLUSIONS = (
    "docker-desktop-or-daemon-start-image-pull-load-or-container-create-start-run-exec",
    "credential-or-environment-value-read-hash-length-prefix-or-persistence",
    "dotenv-read-load-or-live-endpoint-observation",
    "provider-evaluator-agent-memory-retrieval-injection-hash-candidate-cost-or-four-row-ac",
    "retry-resume-repair-or-backfill-any-consumed-attempt",
)

ROOT_KEYS = ("schema_version", "artifact_id", "semantic_body_hash", "semantic_body")
GATE_ROOT_KEYS = ("schema_version", "gate_id", "semantic_body_hash", "semantic_body")


class D137NoCallPreflightSuccessorError(ContractError):
    """D-137 evidence, ordering, or authority failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D137NoCallPreflightSuccessorError(message)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_time(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str), f"D-137 {label} differs")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise D137NoCallPreflightSuccessorError(f"D-137 {label} differs") from exc
    _require(parsed.tzinfo is not None, f"D-137 {label} lacks timezone")
    return parsed.astimezone(UTC)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else Path.cwd()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise D137NoCallPreflightSuccessorError("D-137 repository root differs") from exc
    _require(root.is_dir() and (root / ".git").exists(), "D-137 repository root differs")
    return root


def _logical_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    _require(not relative.is_absolute() and ".." not in relative.parts, "D-137 path differs")
    selected = root / relative
    try:
        parent = selected.parent.resolve(strict=True)
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise D137NoCallPreflightSuccessorError(f"D-137 path parent differs: {relative}") from exc
    _require(parent.is_relative_to(resolved_root), f"D-137 path escapes repository: {relative}")
    if must_exist:
        _require(os.path.lexists(selected), f"D-137 path is absent: {relative}")
        _require(not selected.is_symlink(), f"D-137 linklike path rejected: {relative}")
    return selected


def _stable_read(root: Path, relative: Path) -> bytes:
    selected = _logical_path(root, relative, must_exist=True)
    _require(selected.is_file(), f"D-137 non-file path rejected: {relative}")
    before = selected.stat()
    first = selected.read_bytes()
    after = selected.stat()
    _require(
        (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        and len(first) == after.st_size
        and selected.read_bytes() == first,
        f"D-137 unstable bytes: {relative}",
    )
    return first


def _read_json(root: Path, relative: Path) -> tuple[dict[str, Any], bytes]:
    raw = _stable_read(root, relative)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D137NoCallPreflightSuccessorError(f"D-137 JSON differs: {relative}") from exc
    _require(isinstance(payload, dict), f"D-137 JSON root differs: {relative}")
    return payload, raw


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
        "gate_id": f"d137_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _validate_envelope(
    payload: dict[str, Any],
    raw: bytes,
    *,
    schema: str,
    prefix: str,
    gate: bool = False,
) -> dict[str, Any]:
    _require(
        tuple(payload) == (GATE_ROOT_KEYS if gate else ROOT_KEYS), "D-137 envelope fields differ"
    )
    _require(payload["schema_version"] == schema, "D-137 envelope schema differs")
    body = payload["semantic_body"]
    _require(isinstance(body, dict), "D-137 semantic body differs")
    digest = sha256_text(canonical_json(body))
    _require(payload["semantic_body_hash"] == digest, "D-137 semantic body SHA differs")
    identifier = "gate_id" if gate else "artifact_id"
    _require(
        payload[identifier] == f"{prefix}_{digest.removeprefix('sha256:')}",
        "D-137 stable identifier differs",
    )
    _require(raw == _pretty_bytes(payload), "D-137 artifact serialization differs")
    return body


def _path_absent(root: Path, relative: Path) -> None:
    _require(not os.path.lexists(root / relative), f"D-137 unexpected path exists: {relative}")


def _write_new(root: Path, relative: Path, raw: bytes) -> None:
    selected = _logical_path(root, relative, must_exist=False)
    _require(not os.path.lexists(selected), f"D-137 publication collision: {relative}")
    temporary = selected.with_name(f".{selected.name}.d137-{uuid.uuid4().hex}.tmp")
    _require(not os.path.lexists(temporary), "D-137 temporary output collision")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        _require(temporary.read_bytes() == raw, "D-137 temporary output differs")
        try:
            os.link(temporary, selected)
        except FileExistsError as exc:
            raise D137NoCallPreflightSuccessorError(
                f"D-137 publication collision: {relative}"
            ) from exc
        _require(_stable_read(root, relative) == raw, "D-137 persisted output differs")
    finally:
        with suppress(OSError):
            temporary.unlink()


def _git_engine_binding() -> dict[str, Any]:
    try:
        selected = GIT_ENGINE_PATH.resolve(strict=True)
    except OSError as exc:
        raise D137NoCallPreflightSuccessorError("D-137 Git CLI path differs") from exc
    _require(selected == GIT_ENGINE_PATH, "D-137 Git CLI resolved path differs")
    _require(selected.is_file() and not selected.is_symlink(), "D-137 Git CLI path differs")
    before = selected.stat()
    raw = selected.read_bytes()
    after = selected.stat()
    _require(
        (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
        "D-137 Git CLI changed during binding",
    )
    binding = {
        "resolved_path": str(selected),
        "file_name": selected.name,
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "linklike": False,
    }
    _require(
        binding
        == {
            "resolved_path": str(GIT_ENGINE_PATH),
            "file_name": "git.exe",
            "file_bytes": GIT_ENGINE_FILE_BYTES,
            "file_sha256": GIT_ENGINE_FILE_SHA256,
            "linklike": False,
        },
        "D-137 exact Git engine binding differs",
    )
    return binding


def _git_command(root: Path, *args: str, binary: bool = False) -> bytes | str:
    before = _git_engine_binding()
    try:
        completed = subprocess.run(
            [
                str(GIT_ENGINE_PATH),
                "-c",
                "core.fsmonitor=false",
                "-c",
                "commit.gpgSign=false",
                *args,
            ],
            cwd=root,
            env=dict(FIXED_GIT_ENVIRONMENT),
            capture_output=True,
            shell=False,
            check=False,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise D137NoCallPreflightSuccessorError("D-137 bounded Git observation failed") from exc
    _require(_git_engine_binding() == before, "D-137 Git engine changed during command")
    _require(
        len(completed.stdout) <= MAX_GIT_OUTPUT_BYTES
        and len(completed.stderr) <= MAX_GIT_OUTPUT_BYTES,
        "D-137 Git output exceeds bound",
    )
    _require(
        completed.returncode == 0,
        f"D-137 Git command failed: {' '.join(args)}",
    )
    if binary:
        return completed.stdout
    try:
        return completed.stdout.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise D137NoCallPreflightSuccessorError("D-137 Git output is not UTF-8") from exc


def _head(root: Path) -> str:
    return str(_git_command(root, "rev-parse", "HEAD"))


def _status_lines(root: Path) -> list[str]:
    value = str(_git_command(root, "status", "--porcelain=v1", "--untracked-files=all"))
    return [line.replace("\\", "/") for line in value.splitlines() if line]


def _commit_identity(root: Path, commit: str) -> dict[str, Any]:
    resolved = str(_git_command(root, "rev-parse", f"{commit}^{{commit}}"))
    _require(resolved == commit, "D-137 commit identity differs")
    value = str(_git_command(root, "show", "-s", "--format=%T%x00%P", commit))
    tree, parents = value.split("\x00", 1)
    return {"commit": commit, "tree": tree, "parents": parents.split() if parents else []}


def _diff_rows(root: Path, commit: str) -> list[dict[str, str]]:
    value = str(
        _git_command(root, "diff-tree", "--root", "--no-commit-id", "--name-status", "-r", commit)
    )
    rows: list[dict[str, str]] = []
    for line in value.splitlines():
        if not line:
            continue
        status, path = line.split("\t", 1)
        rows.append({"status": status, "path": path.replace("\\", "/")})
    return rows


def _commit_blob(root: Path, commit: str, path: Path) -> tuple[str, bytes]:
    spec = f"{commit}:{path.as_posix()}"
    oid = str(_git_command(root, "rev-parse", spec))
    raw = _git_command(root, "cat-file", "blob", oid, binary=True)
    _require(isinstance(raw, bytes), "D-137 committed blob read differs")
    return oid, raw


def _artifact_binding(path: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "artifact_id": payload.get("gate_id", payload.get("artifact_id")),
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": payload["semantic_body"]["status"],
        "recorded_at": payload["semantic_body"]["recorded_at"],
    }


def _single_artifact_commit_binding(
    root: Path, *, commit: str, parent: str, path: Path, raw: bytes
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [parent], f"D-137 {path.name} commit parent differs")
    _require(
        _diff_rows(root, commit) == [{"status": "A", "path": path.as_posix()}],
        f"D-137 {path.name} commit scope differs",
    )
    oid, committed = _commit_blob(root, commit, path)
    _require(committed == raw, f"D-137 {path.name} committed bytes differ")
    return {
        **identity,
        "artifact_path": path.as_posix(),
        "artifact_blob_oid": oid,
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_file_bytes": len(raw),
        "single_artifact_add_commit": True,
    }


def _transition_commit_binding(
    root: Path,
    *,
    phase: str,
    commit: str,
    parent: str,
    started_raw: bytes,
    terminal_raw: bytes,
) -> dict[str, Any]:
    _attempt, started_path, terminal_path = _phase_paths(phase)
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [parent], f"D-137 {phase} transition parent differs")
    expected = sorted(
        [
            {"status": "A", "path": started_path.as_posix()},
            {"status": "A", "path": terminal_path.as_posix()},
        ],
        key=lambda row: row["path"],
    )
    _require(
        sorted(_diff_rows(root, commit), key=lambda row: row["path"]) == expected,
        f"D-137 {phase} transition scope differs",
    )
    started_oid, committed_started = _commit_blob(root, commit, started_path)
    terminal_oid, committed_terminal = _commit_blob(root, commit, terminal_path)
    _require(committed_started == started_raw, f"D-137 {phase} committed marker differs")
    _require(committed_terminal == terminal_raw, f"D-137 {phase} committed terminal differs")
    return {
        **identity,
        "artifact_paths": [started_path.as_posix(), terminal_path.as_posix()],
        "artifact_blob_oids": {
            started_path.as_posix(): started_oid,
            terminal_path.as_posix(): terminal_oid,
        },
        "exact_action_started_and_terminal_add_commit": True,
    }


def _pending_only(root: Path, paths: tuple[Path, ...], *, parent: str) -> bool:
    expected = sorted(f"?? {path.as_posix()}" for path in paths)
    return _head(root) == parent and sorted(_status_lines(root)) == expected


def _phase_paths(phase: str) -> tuple[Path, Path, Path]:
    _require(phase in PHASE_PATHS, "D-137 phase differs")
    return PHASE_PATHS[phase]


def _git_cli_observation(root: Path) -> dict[str, Any]:
    binding = _git_engine_binding()
    version = _git_command(root, "--version")
    normalization = _git_command(root, "config", "--local", "--get", "core.autocrlf")
    _require(version == GIT_VERSION, "D-137 Git version differs")
    _require(normalization == "false", "D-137 checkout must bind core.autocrlf=false")
    return {
        **binding,
        "version": version,
        "actual_git_engine_invoked_directly": True,
        "repository_local_core_autocrlf": "false",
        "authenticated_or_vendor_signed_identity_claimed": False,
        "stable_during_observation": True,
        "minimal_secret_free_environment": True,
        "environment_value_observation_count": 0,
        "fsmonitor_disabled": True,
        "shell_used": False,
    }


def _assert_runtime_import_boundary(root: Path) -> None:
    for relative, module_name in LOADED_MODULE_PATHS:
        module = sys.modules.get(module_name)
        value = getattr(module, "__file__", None)
        _require(isinstance(value, str), f"D-137 loaded module differs: {relative}")
        try:
            loaded = Path(value).resolve(strict=True)
            expected = (root / relative).resolve(strict=True)
        except OSError as exc:
            raise D137NoCallPreflightSuccessorError(
                f"D-137 loaded module differs: {relative}"
            ) from exc
        _require(loaded == expected, f"D-137 loaded module is outside repository: {relative}")


def _file_binding(root: Path, commit: str, path: Path) -> dict[str, Any]:
    oid, committed = _commit_blob(root, commit, path)
    current = _stable_read(root, path)
    _require(current == committed, f"D-137 source drift: {path}")
    return {
        "path": path.as_posix(),
        "blob_oid": oid,
        "file_sha256": sha256_bytes(committed),
        "file_bytes": len(committed),
        "current_bytes_match_commit": True,
    }


def _loaded_module_bindings(root: Path, commit: str) -> list[dict[str, Any]]:
    _assert_runtime_import_boundary(root)
    return [
        {
            **_file_binding(root, commit, path),
            "module_name": module_name,
            "loaded_path": path.as_posix(),
            "loaded_path_matches_repository": True,
        }
        for path, module_name in LOADED_MODULE_PATHS
    ]


def _validate_static_artifact(
    root: Path,
    row: tuple[Path, str, str, str, int, str, str],
) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    path, identifier, body_sha, file_sha, file_bytes, blob_oid, commit = row
    payload, raw = _read_json(root, path)
    gate = "gate_id" in payload
    expected_root = GATE_ROOT_KEYS if gate else ROOT_KEYS
    _require(tuple(payload) == expected_root, f"D-137 predecessor envelope differs: {path}")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), f"D-137 predecessor body differs: {path}")
    _require(
        payload.get("semantic_body_hash") == sha256_text(canonical_json(body)) == body_sha,
        f"D-137 predecessor semantic SHA differs: {path}",
    )
    _require(
        payload.get("gate_id" if gate else "artifact_id") == identifier,
        f"D-137 predecessor identifier differs: {path}",
    )
    _require(sha256_bytes(raw) == file_sha, f"D-137 predecessor file SHA differs: {path}")
    _require(len(raw) == file_bytes, f"D-137 predecessor file bytes differ: {path}")
    oid, committed = _commit_blob(root, commit, path)
    _require(oid == blob_oid and committed == raw, f"D-137 predecessor blob differs: {path}")
    return payload, raw, _artifact_binding(path, payload, raw)


def _validate_d136_pricing_replay(terminal: dict[str, Any]) -> dict[str, Any]:
    body = terminal["semantic_body"]
    observation = body.get("observation")
    _require(isinstance(observation, dict), "D-137 D-136 pricing observation differs")
    encoded = observation.get("decoded_entity_base64")
    _require(isinstance(encoded, str), "D-137 D-136 replay bytes differ")
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise D137NoCallPreflightSuccessorError("D-137 D-136 replay base64 differs") from exc
    _require(
        len(decoded) == observation.get("decoded_entity_bytes") == 3_735,
        "D-137 D-136 replay byte count differs",
    )
    _require(
        sha256_bytes(decoded) == observation.get("decoded_entity_sha256"),
        "D-137 D-136 replay SHA differs",
    )
    try:
        decoded_text = decoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise D137NoCallPreflightSuccessorError("D-137 D-136 replay text differs") from exc
    required = observation.get("required_evidence_lines")
    _require(
        isinstance(required, list)
        and required
        and all(isinstance(line, str) and line in decoded_text for line in required),
        "D-137 D-136 required pricing evidence differs",
    )
    _require(
        observation.get("source_url")
        == observation.get("final_url")
        == "https://developers.openai.com/api/docs/models/gpt-5.4-mini.md",
        "D-137 D-136 pricing URL differs",
    )
    _require(
        observation.get("http_status") == 200
        and observation.get("redirect_count") == 0
        and observation.get("public_get_request_count") == 1
        and observation.get("request_auth_or_cookie_sent") is False
        and observation.get("proxy_use_disabled") is True,
        "D-137 D-136 pricing boundary differs",
    )
    activity = body.get("activity_accounting")
    _require(
        isinstance(activity, dict)
        and activity.get("pricing_helper_invocation_count") == 1
        and activity.get("official_public_get_send_count") == 1
        and activity.get("docker_cli_call_count") == 0
        and activity.get("sdk_credential_dotenv_environment_value_or_endpoint_observation_count")
        == 0
        and activity.get("provider_evaluator_agent_call_count") == 0,
        "D-137 D-136 pricing activity differs",
    )
    return {
        "decoded_entity_bytes": len(decoded),
        "decoded_entity_sha256": sha256_bytes(decoded),
        "required_evidence_lines_replayed": len(required),
        "public_get_request_count": 1,
        "pricing_facts": observation.get("facts"),
        "planning_math": observation.get("planning_math"),
    }


def _exact_d136_success_topology(root: Path) -> dict[str, Any]:
    artifacts: dict[Path, tuple[dict[str, Any], bytes, dict[str, Any]]] = {}
    for row in _D136_ARTIFACTS:
        artifacts[row[0]] = _validate_static_artifact(root, row)

    source = _commit_identity(root, D136_SOURCE_COMMIT)
    _require(
        source
        == {
            "commit": D136_SOURCE_COMMIT,
            "tree": D136_SOURCE_TREE,
            "parents": [D136_SOURCE_PARENT],
        },
        "D-137 D-136 source identity differs",
    )
    _require(
        sorted(_diff_rows(root, D136_SOURCE_COMMIT), key=lambda item: item["path"])
        == sorted(
            [{"status": "A", "path": path.as_posix()} for path in D136_IMPLEMENTATION_PATHS],
            key=lambda item: item["path"],
        ),
        "D-137 D-136 source scope differs",
    )

    gate_identity = _commit_identity(root, D136_GATE_COMMIT)
    _require(
        gate_identity
        == {
            "commit": D136_GATE_COMMIT,
            "tree": D136_GATE_TREE,
            "parents": [D136_SOURCE_COMMIT],
        },
        "D-137 D-136 gate evidence identity differs",
    )
    expected_gate_rows = sorted(
        [
            {"status": "A", "path": D136_GATE_PATH.as_posix()},
            *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
        ],
        key=lambda item: item["path"],
    )
    _require(
        sorted(_diff_rows(root, D136_GATE_COMMIT), key=lambda item: item["path"])
        == expected_gate_rows,
        "D-137 D-136 gate evidence scope differs",
    )

    receipt_payload, receipt_raw, receipt_binding = artifacts[D136_RECEIPT_PATH]
    receipt_commit = _single_artifact_commit_binding(
        root,
        commit=D136_RECEIPT_COMMIT,
        parent=D136_GATE_COMMIT,
        path=D136_RECEIPT_PATH,
        raw=receipt_raw,
    )
    _require(receipt_commit["tree"] == D136_RECEIPT_TREE, "D-137 D-136 receipt tree differs")
    attempt_payload, attempt_raw, attempt_binding = artifacts[D136_ATTEMPT_PATH]
    attempt_commit = _single_artifact_commit_binding(
        root,
        commit=D136_ATTEMPT_COMMIT,
        parent=D136_RECEIPT_COMMIT,
        path=D136_ATTEMPT_PATH,
        raw=attempt_raw,
    )
    _require(attempt_commit["tree"] == D136_ATTEMPT_TREE, "D-137 D-136 attempt tree differs")
    started_payload, started_raw, started_binding = artifacts[D136_STARTED_PATH]
    terminal_payload, terminal_raw, terminal_binding = artifacts[D136_TERMINAL_PATH]
    success_identity = _commit_identity(root, D136_SUCCESS_COMMIT)
    _require(
        success_identity
        == {
            "commit": D136_SUCCESS_COMMIT,
            "tree": D136_SUCCESS_TREE,
            "parents": [D136_ATTEMPT_COMMIT],
        },
        "D-137 D-136 success identity differs",
    )
    expected_success_rows = sorted(
        [
            {"status": "A", "path": D136_STARTED_PATH.as_posix()},
            {"status": "A", "path": D136_TERMINAL_PATH.as_posix()},
        ],
        key=lambda item: item["path"],
    )
    _require(
        sorted(_diff_rows(root, D136_SUCCESS_COMMIT), key=lambda item: item["path"])
        == expected_success_rows,
        "D-137 D-136 success scope differs",
    )
    _require(
        _commit_blob(root, D136_SUCCESS_COMMIT, D136_STARTED_PATH)[1] == started_raw
        and _commit_blob(root, D136_SUCCESS_COMMIT, D136_TERMINAL_PATH)[1] == terminal_raw,
        "D-137 D-136 success committed bytes differ",
    )

    times = [
        _parse_time(artifacts[path][0]["semantic_body"]["recorded_at"], label=path.name)
        for path in (
            D136_GATE_PATH,
            D136_RECEIPT_PATH,
            D136_ATTEMPT_PATH,
            D136_STARTED_PATH,
            D136_TERMINAL_PATH,
        )
    ]
    _require(
        times == sorted(times) and len(set(times)) == len(times), "D-137 D-136 chronology differs"
    )
    replay = _validate_d136_pricing_replay(terminal_payload)
    return {
        "source_commit_binding": source,
        "gate": {
            **artifacts[D136_GATE_PATH][2],
            "commit_binding": {
                **gate_identity,
                "exact_gate_add_and_active_docs_modify_commit": True,
            },
        },
        "activation_receipt": {**receipt_binding, "commit_binding": receipt_commit},
        "pricing_attempt": {**attempt_binding, "commit_binding": attempt_commit},
        "action_started": started_binding,
        "pricing_terminal": terminal_binding,
        "success_commit_binding": {
            **success_identity,
            "artifact_paths": [D136_STARTED_PATH.as_posix(), D136_TERMINAL_PATH.as_posix()],
            "artifact_blob_oids": {
                D136_STARTED_PATH.as_posix(): _D136_ARTIFACTS[3][5],
                D136_TERMINAL_PATH.as_posix(): _D136_ARTIFACTS[4][5],
            },
            "exact_action_started_and_terminal_add_commit": True,
        },
        "pricing_replay_validation": replay,
        "consumed_successor_is_immutable": True,
    }


def _source_identity_for_gate(root: Path) -> dict[str, Any]:
    head = _head(root)
    identity = _commit_identity(root, head)
    _require(identity["parents"] == [D136_SUCCESS_COMMIT], "D-137 source parent differs")
    _require(
        sorted(_diff_rows(root, head), key=lambda item: item["path"])
        == sorted(
            [{"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS],
            key=lambda item: item["path"],
        ),
        "D-137 source commit must add exactly four implementation paths",
    )
    _require(_status_lines(root) == [], "D-137 source qualification requires clean checkout")
    return {
        **identity,
        "implementation_paths": [path.as_posix() for path in IMPLEMENTATION_PATHS],
        "source_file_bindings": [_file_binding(root, head, path) for path in SOURCE_BINDING_PATHS],
        "loaded_module_bindings": _loaded_module_bindings(root, head),
        "python_routing_environment_observation_performed": False,
        "python_routing_environment_observation_count": 0,
        "git_cli_observation": _git_cli_observation(root),
        "exact_source_only_commit": True,
    }


def _validate_source_identity(root: Path, value: Any) -> dict[str, Any]:
    _require(isinstance(value, dict), "D-137 source identity differs")
    commit = value.get("commit")
    _require(isinstance(commit, str), "D-137 source commit differs")
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [D136_SUCCESS_COMMIT], "D-137 source parent differs")
    _require(value.get("tree") == identity["tree"], "D-137 source tree differs")
    _require(value.get("parents") == identity["parents"], "D-137 source ancestry differs")
    _require(
        sorted(_diff_rows(root, commit), key=lambda item: item["path"])
        == sorted(
            [{"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS],
            key=lambda item: item["path"],
        ),
        "D-137 source scope differs",
    )
    expected_files = [_file_binding(root, commit, path) for path in SOURCE_BINDING_PATHS]
    _require(value.get("source_file_bindings") == expected_files, "D-137 source bindings differ")
    _require(
        value.get("loaded_module_bindings") == _loaded_module_bindings(root, commit),
        "D-137 loaded module bindings differ",
    )
    _require(
        value.get("python_routing_environment_observation_performed") is False
        and value.get("python_routing_environment_observation_count") == 0,
        "D-137 offline routing-observation boundary differs",
    )
    _require(value.get("git_cli_observation") == _git_cli_observation(root), "D-137 Git differs")
    _require(
        value.get("implementation_paths") == [path.as_posix() for path in IMPLEMENTATION_PATHS]
        and value.get("exact_source_only_commit") is True,
        "D-137 source contract differs",
    )
    return value


def _helper_contract() -> dict[str, Any]:
    _require(
        no_call.DOCKER_PHASE == PHASE_DOCKER
        and no_call.SDK_PHASE == PHASE_SDK
        and no_call.LOCAL_DOCKER_ENDPOINT == "npipe:////./pipe/dockerDesktopLinuxEngine"
        and str(no_call.APPROVED_DOCKER_CLI_PATH)
        == r"C:\Users\geonj\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
        and no_call.APPROVED_DOCKER_CLI_VERSION == "29.6.2"
        and no_call.APPROVED_DOCKER_CLI_FILE_BYTES == 43_095_472
        and no_call.APPROVED_DOCKER_CLI_FILE_SHA256
        == "sha256:8985cd8ac002c3240b5aa48fe401fcb55dca5d849b537e3c835564e8e8c49a70"
        and tuple(no_call.EXACT_DOCKER_IMAGES)
        == (
            "docker.io/swerebenchv2/getmoto-moto@"
            "sha256:dfdf957ab30b8829e8b6bbfd693b00fab88b7979d3c856362fd5d66c489a1fee",
            "docker.io/swerebenchv2/python-babel-babel@"
            "sha256:864e84fc4bdf09252f7fda4f85665cc05155a7b1d75847d61c67325abce7ef5a",
        )
        and no_call.OFFICIAL_API_BASE_URL == "https://api.openai.com/v1",
        "D-137 helper constants differ",
    )
    return {
        "module_path": IMPLEMENTATION_PATHS[0].as_posix(),
        "historical_external_runner_import_count": 0,
        "historical_mutation_or_remediation_helper_import_count": 0,
        "gate_builder_helper_invocation_count": 0,
        "docker": {
            "phase": no_call.DOCKER_PHASE,
            "forced_daemon_endpoint": no_call.LOCAL_DOCKER_ENDPOINT,
            "approved_cli_path": str(no_call.APPROVED_DOCKER_CLI_PATH),
            "approved_cli_version": no_call.APPROVED_DOCKER_CLI_VERSION,
            "approved_cli_file_bytes": no_call.APPROVED_DOCKER_CLI_FILE_BYTES,
            "approved_cli_file_sha256": no_call.APPROVED_DOCKER_CLI_FILE_SHA256,
            "exact_digest_pinned_images": list(no_call.EXACT_DOCKER_IMAGES),
            "bounded_read_only_snapshots": 2,
            "zero_existing_container_inventory_required": True,
            "mutation_and_workload_operations_authorized": False,
        },
        "sdk": {
            "phase": no_call.SDK_PHASE,
            "official_api_base_url": no_call.OFFICIAL_API_BASE_URL,
            "credential_presence_bits_only": True,
            "credential_or_environment_values_read": False,
            "dotenv_read_or_load_count": 0,
            "synthetic_transport_dispatch_count": 0,
            "network_call_count": 0,
            "loaded_module_and_distribution_provenance_required": True,
        },
    }


def _future_activation_contract() -> dict[str, Any]:
    return {
        "ordered_paths": [path.as_posix() for path in FUTURE_PATHS],
        "receipt_only_commit_required": True,
        "docker_attempt_only_commit_required": True,
        "docker_action_started_fsynced_immediately_before_first_observation": True,
        "docker_marker_and_ready_or_blocked_terminal_two_artifact_commit_required": True,
        "docker_marker_only_preservation_after_post_marker_failure": True,
        "sdk_requires_committed_docker_ready_terminal": True,
        "sdk_attempt_only_commit_required": True,
        "sdk_action_started_fsynced_immediately_before_first_observation": True,
        "sdk_marker_and_ready_or_blocked_terminal_two_artifact_commit_required": True,
        "sdk_marker_only_preservation_after_post_marker_failure": True,
        "post_marker_failure_consumes_phase_and_forbids_retry": True,
        "blocked_terminal_forbids_later_phase_or_execution_progression": True,
        "ready_or_blocked_sdk_terminal_requires_separate_offline_successor": True,
        "fresh_exact_activation_must_quote_gate_source_and_evidence_commit": True,
    }


def _gate_body(
    *, recorded_at: str, predecessor: dict[str, Any], source_identity: dict[str, Any]
) -> dict[str, Any]:
    recorded = _parse_time(recorded_at, label="gate recorded_at")
    terminal_time = _parse_time(
        predecessor["pricing_terminal"]["recorded_at"], label="D-136 terminal recorded_at"
    )
    _require(recorded > terminal_time, "D-137 gate chronology differs")
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d136-success-terminal-no-call-preflight-successor-offline-source-gate",
        "recorded_at": recorded_at,
        "status": GATE_STATUS,
        "d136_success_predecessor": predecessor,
        "source_identity": source_identity,
        "source_preparation_approval": {
            "exact_user_approval_recorded": True,
            "approval_is_self_attested": True,
            "approval_is_authenticated_or_signed": False,
            "approved_scope": list(SOURCE_PREPARATION_SCOPE),
            "explicit_exclusions": list(SOURCE_PREPARATION_EXCLUSIONS),
        },
        "no_call_preflight_helper_contract": _helper_contract(),
        "future_activation_contract": _future_activation_contract(),
        "offline_qualification": {
            "gate_builder_invoked_future_writer": False,
            "gate_builder_invoked_docker_or_sdk_helper": False,
            "external_action_count": 0,
            "future_artifacts_created": False,
            "focused_tests_are_mocked_only": True,
        },
        "authority": {
            "docker_cli_or_daemon_image_container_observation_count": 0,
            "sdk_runtime_credential_dotenv_environment_value_or_endpoint_observation_count": 0,
            "official_docs_network_or_pricing_refresh_count": 0,
            "provider_evaluator_agent_call_count": 0,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
        "next_gate": {
            "status": "D137_FRESH_EXACT_NO_CALL_PREFLIGHT_ACTIVATION_REQUIRED",
            "fresh_separate_exact_user_approval_required": True,
            "must_quote_gate_source_and_evidence_commit_tuples": True,
        },
    }


def _validate_gate_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=GATE_SCHEMA, prefix="d137", gate=True)
    predecessor = _exact_d136_success_topology(root)
    source = _validate_source_identity(root, body.get("source_identity"))
    expected = _gate_envelope(
        _gate_body(
            recorded_at=body.get("recorded_at"), predecessor=predecessor, source_identity=source
        )
    )
    _require(canonical_json(payload) == canonical_json(expected), "D-137 gate full rebuild differs")
    return body


def _gate_evidence_commit_binding(
    root: Path, *, commit: str, source_commit: str, raw: bytes
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [source_commit], "D-137 evidence commit parent differs")
    expected = sorted(
        [
            {"status": "A", "path": GATE_PATH.as_posix()},
            *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
        ],
        key=lambda item: item["path"],
    )
    _require(
        sorted(_diff_rows(root, commit), key=lambda item: item["path"]) == expected,
        "D-137 evidence commit scope differs",
    )
    oid, committed = _commit_blob(root, commit, GATE_PATH)
    _require(committed == raw, "D-137 committed gate bytes differ")
    return {
        **identity,
        "artifact_path": GATE_PATH.as_posix(),
        "artifact_blob_oid": oid,
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_file_bytes": len(raw),
        "exact_gate_add_and_active_docs_modify_commit": True,
    }


def run_d137_offline_source_gate(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in FUTURE_PATHS:
        _path_absent(root, path)
    if os.path.lexists(root / GATE_PATH):
        mode: Literal["pending", "post-evidence-commit"] = (
            "post-evidence-commit" if _status_lines(root) == [] else "pending"
        )
        return validate_d137_offline_source_gate(repository=root, mode=mode)
    predecessor = _exact_d136_success_topology(root)
    source = _source_identity_for_gate(root)
    payload = _gate_envelope(
        _gate_body(recorded_at=_now(), predecessor=predecessor, source_identity=source)
    )
    fresh_predecessor = _exact_d136_success_topology(root)
    fresh_source = _source_identity_for_gate(root)
    _require(
        canonical_json(predecessor) == canonical_json(fresh_predecessor)
        and canonical_json(source) == canonical_json(fresh_source),
        "D-137 source or predecessor drifted before gate publication",
    )
    _write_new(root, GATE_PATH, _pretty_bytes(payload))
    return validate_d137_offline_source_gate(repository=root, mode="pending")


def validate_d137_offline_source_gate(
    *,
    repository: str | Path | None = None,
    mode: Literal["pending", "post-evidence-commit"] = "pending",
) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in FUTURE_PATHS:
        _path_absent(root, path)
    payload, raw = _read_json(root, GATE_PATH)
    body = _validate_gate_payload(root, payload, raw)
    source_commit = body["source_identity"]["commit"]
    evidence_commit = None
    if mode == "pending":
        _require(
            _pending_only(root, (GATE_PATH,), parent=source_commit),
            "D-137 pending gate checkout differs",
        )
    elif mode == "post-evidence-commit":
        _require(_status_lines(root) == [], "D-137 evidence checkout is not clean")
        evidence_commit = _gate_evidence_commit_binding(
            root, commit=_head(root), source_commit=source_commit, raw=raw
        )
    else:
        raise D137NoCallPreflightSuccessorError("D-137 gate validation mode differs")
    return {
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "source_identity": body["source_identity"],
        "evidence_commit": evidence_commit,
        "external_action_count": 0,
        "future_artifacts_created": False,
        "fresh_exact_activation_required": True,
    }


def _gate_binding_for_activation(
    root: Path, *, evidence_commit: str | None = None
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    payload, raw = _read_json(root, GATE_PATH)
    body = _validate_gate_payload(root, payload, raw)
    selected_commit = evidence_commit if evidence_commit is not None else _head(root)
    commit = _gate_evidence_commit_binding(
        root,
        commit=selected_commit,
        source_commit=body["source_identity"]["commit"],
        raw=raw,
    )
    return (
        {
            **_artifact_binding(GATE_PATH, payload, raw),
            "evidence_commit_binding": commit,
        },
        body,
        raw,
    )


def render_d137_external_activation_template(*, repository: str | Path | None = None) -> str:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    _require(_status_lines(root) == [], "D-137 activation template requires clean checkout")
    for path in FUTURE_PATHS:
        _path_absent(root, path)
    gate, body, _raw = _gate_binding_for_activation(root)
    evidence = gate["evidence_commit_binding"]
    source = body["source_identity"]
    predecessor = body["d136_success_predecessor"]
    return "\n".join(
        (
            "D-137 D-136 no-call-preflight successor fresh exact activation approval",
            "(bounded Docker read-only then SDK no-call presence checks; "
            "no provider or cost authority)",
            "",
            f"Gate ID: {gate['artifact_id']}",
            f"Gate body SHA: {gate['semantic_body_hash']}",
            f"Gate file SHA: {gate['file_sha256']}",
            f"Gate file bytes: {gate['file_bytes']}",
            f"Gate evidence commit tuple: {canonical_json(evidence)}",
            f"Source commit: {source['commit']}",
            f"Source tree: {source['tree']}",
            f"D-136 success commit tuple: {canonical_json(predecessor['success_commit_binding'])}",
            "",
            "Approved bounded scope:",
            *(f"- {item}" for item in ACTIVATION_SCOPE),
            "",
            "Explicitly not approved:",
            *(f"- {item}" for item in ACTIVATION_EXCLUSIONS),
            "",
            "Each ACTION_STARTED marker is written and fsynced immediately before its phase's",
            "first observation. A post-marker exception consumes that phase; the marker may",
            "only be preserved as the attempt commit's sole-child artifact and must not be "
            "retried.",
            "SDK may start only after a committed Docker READY terminal. READY or BLOCKED SDK",
            "terminal grants no execution/hash/cost authority and requires a later offline "
            "successor.",
            "This rendered template is not approval; a new exact user message is required.",
        )
    )


def _receipt_body(
    *,
    recorded_at: str,
    gate_binding: dict[str, Any],
    source_identity: dict[str, Any],
) -> dict[str, Any]:
    recorded = _parse_time(recorded_at, label="activation receipt recorded_at")
    gate_time = _parse_time(gate_binding["recorded_at"], label="gate recorded_at")
    _require(recorded > gate_time, "D-137 activation receipt chronology differs")
    return {
        "milestone": MILESTONE,
        "evidence_kind": "no-call-preflight-successor-activation-receipt",
        "recorded_at": recorded_at,
        "status": RECEIPT_STATUS,
        "source_gate_binding": gate_binding,
        "source_identity": source_identity,
        "activation_approval": {
            "exact_user_approval_recorded": True,
            "approval_is_self_attested": True,
            "approval_is_authenticated_or_signed": False,
            "approved_scope": list(ACTIVATION_SCOPE),
            "explicit_exclusions": list(ACTIVATION_EXCLUSIONS),
        },
        "future_activation_contract": _future_activation_contract(),
        "authority": {
            "docker_or_sdk_helper_invocation_count": 0,
            "docker_cli_call_count": 0,
            "sdk_import_or_credential_presence_observation_count": 0,
            "environment_value_observation_count": 0,
            "provider_evaluator_agent_call_count": 0,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
    }


def _validate_receipt_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=RECEIPT_SCHEMA, prefix="d137approval")
    gate_value = body.get("source_gate_binding")
    _require(isinstance(gate_value, dict), "D-137 receipt gate binding differs")
    evidence = gate_value.get("evidence_commit_binding")
    _require(isinstance(evidence, dict), "D-137 receipt evidence binding differs")
    gate, gate_body, _gate_raw = _gate_binding_for_activation(
        root, evidence_commit=evidence.get("commit")
    )
    source = _validate_source_identity(root, body.get("source_identity"))
    _require(source == gate_body["source_identity"], "D-137 receipt source identity differs")
    expected = _envelope(
        RECEIPT_SCHEMA,
        "d137approval",
        _receipt_body(
            recorded_at=body.get("recorded_at"), gate_binding=gate, source_identity=source
        ),
    )
    _require(canonical_json(payload) == canonical_json(expected), "D-137 receipt rebuild differs")
    return body


def create_d137_activation_receipt(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in FUTURE_PATHS[1:]:
        _path_absent(root, path)
    if os.path.lexists(root / RECEIPT_PATH):
        mode: Literal["pending", "post-commit"] = (
            "post-commit" if _status_lines(root) == [] else "pending"
        )
        return validate_d137_activation_receipt(repository=root, mode=mode)
    _require(_status_lines(root) == [], "D-137 receipt requires clean gate evidence commit")
    gate, body, _raw = _gate_binding_for_activation(root)
    payload = _envelope(
        RECEIPT_SCHEMA,
        "d137approval",
        _receipt_body(
            recorded_at=_now(), gate_binding=gate, source_identity=body["source_identity"]
        ),
    )
    fresh_gate, fresh_body, _fresh_raw = _gate_binding_for_activation(root)
    _require(
        canonical_json(gate) == canonical_json(fresh_gate)
        and canonical_json(body["source_identity"]) == canonical_json(fresh_body["source_identity"])
        and _status_lines(root) == []
        and _head(root) == fresh_gate["evidence_commit_binding"]["commit"],
        "D-137 gate or source drifted before receipt publication",
    )
    _write_new(root, RECEIPT_PATH, _pretty_bytes(payload))
    return validate_d137_activation_receipt(repository=root, mode="pending")


def validate_d137_activation_receipt(
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
            _pending_only(root, (RECEIPT_PATH,), parent=gate_commit),
            "D-137 pending receipt differs",
        )
    elif mode == "post-commit":
        _require(_status_lines(root) == [], "D-137 receipt commit checkout is not clean")
        commit = _single_artifact_commit_binding(
            root, commit=_head(root), parent=gate_commit, path=RECEIPT_PATH, raw=raw
        )
    else:
        raise D137NoCallPreflightSuccessorError("D-137 receipt validation mode differs")
    return {
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "receipt_commit": commit,
        "commit_required_before_docker_attempt": commit is None,
        "external_action_count": 0,
    }


def _phase_status(phase: str, kind: str, observation_status: str | None = None) -> str:
    _phase_paths(phase)
    if kind == "attempt":
        return DOCKER_ATTEMPT_STATUS if phase == PHASE_DOCKER else SDK_ATTEMPT_STATUS
    if kind == "started":
        return DOCKER_STARTED_STATUS if phase == PHASE_DOCKER else SDK_STARTED_STATUS
    _require(
        kind == "terminal" and isinstance(observation_status, str), "D-137 status kind differs"
    )
    if phase == PHASE_DOCKER:
        _require(
            observation_status in (no_call.DOCKER_READY_STATUS, no_call.DOCKER_BLOCKED_STATUS),
            "D-137 Docker observation status differs",
        )
        return (
            DOCKER_TERMINAL_READY_STATUS
            if observation_status == no_call.DOCKER_READY_STATUS
            else DOCKER_TERMINAL_BLOCKED_STATUS
        )
    _require(
        observation_status in (no_call.SDK_READY_STATUS, no_call.SDK_BLOCKED_STATUS),
        "D-137 SDK observation status differs",
    )
    return (
        SDK_TERMINAL_READY_STATUS
        if observation_status == no_call.SDK_READY_STATUS
        else SDK_TERMINAL_BLOCKED_STATUS
    )


def _attempt_prefix(phase: str) -> str:
    return "d137dockerattempt" if phase == PHASE_DOCKER else "d137sdkattempt"


def _started_prefix(phase: str) -> str:
    return "d137dockerstarted" if phase == PHASE_DOCKER else "d137sdkstarted"


def _terminal_prefix(phase: str) -> str:
    return "d137docker" if phase == PHASE_DOCKER else "d137sdk"


def _committed_receipt(
    root: Path, *, commit: str
) -> tuple[dict[str, Any], bytes, dict[str, Any], dict[str, Any]]:
    payload, raw = _read_json(root, RECEIPT_PATH)
    body = _validate_receipt_payload(root, payload, raw)
    gate_commit = body["source_gate_binding"]["evidence_commit_binding"]["commit"]
    binding = _single_artifact_commit_binding(
        root, commit=commit, parent=gate_commit, path=RECEIPT_PATH, raw=raw
    )
    return payload, raw, body, binding


def _attempt_parent(root: Path, phase: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    if phase == PHASE_DOCKER:
        receipt_payload, _raw, _body, receipt_commit = _committed_receipt(root, commit=_head(root))
        return (
            _artifact_binding(RECEIPT_PATH, receipt_payload, _stable_read(root, RECEIPT_PATH)),
            receipt_commit,
            receipt_payload["semantic_body"]["recorded_at"],
        )
    docker_result = validate_d137_docker_terminal(repository=root, mode="post-transition-commit")
    _require(
        docker_result["observation_status"] == no_call.DOCKER_READY_STATUS,
        "D-137 SDK attempt requires committed Docker READY terminal",
    )
    docker_payload, docker_raw = _read_json(root, DOCKER_TERMINAL_PATH)
    transition = docker_result["transition_commit"]
    _require(isinstance(transition, dict), "D-137 Docker transition binding differs")
    return (
        _artifact_binding(DOCKER_TERMINAL_PATH, docker_payload, docker_raw),
        transition,
        docker_payload["semantic_body"]["recorded_at"],
    )


def _attempt_body(
    *,
    phase: str,
    recorded_at: str,
    predecessor_binding: dict[str, Any],
    parent_commit: dict[str, Any],
    predecessor_recorded_at: str,
) -> dict[str, Any]:
    _require(
        _parse_time(recorded_at, label=f"{phase} attempt recorded_at")
        > _parse_time(predecessor_recorded_at, label=f"{phase} predecessor recorded_at"),
        f"D-137 {phase} attempt chronology differs",
    )
    return {
        "milestone": MILESTONE,
        "evidence_kind": f"{phase}-no-call-preflight-attempt-intent",
        "phase": phase,
        "recorded_at": recorded_at,
        "status": _phase_status(phase, "attempt"),
        "predecessor_artifact_binding": predecessor_binding,
        "parent_commit_binding": parent_commit,
        "phase_contract": {
            "attempt_only_commit_required": True,
            "action_started_new_only_and_fsynced_before_first_observation": True,
            "helper_invocation_limit": 1,
            "transport_retry_count": 0,
            "post_marker_exception_consumes_phase": True,
            "marker_only_preservation_commit_is_pre_authorized": True,
        },
        "authority": {
            "action_started_created": False,
            "phase_helper_invocation_count": 0,
            "phase_terminal_created": False,
            "environment_value_observation_count": 0,
            "provider_evaluator_agent_call_count": 0,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
    }


def _validate_attempt_payload(
    root: Path, phase: str, payload: dict[str, Any], raw: bytes
) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=ATTEMPT_SCHEMA, prefix=_attempt_prefix(phase))
    _require(body.get("phase") == phase, f"D-137 {phase} attempt phase differs")
    predecessor = body.get("predecessor_artifact_binding")
    parent = body.get("parent_commit_binding")
    _require(
        isinstance(predecessor, dict) and isinstance(parent, dict), "D-137 attempt binding differs"
    )
    if phase == PHASE_DOCKER:
        receipt_payload, receipt_raw = _read_json(root, RECEIPT_PATH)
        receipt_body = _validate_receipt_payload(root, receipt_payload, receipt_raw)
        gate_commit = receipt_body["source_gate_binding"]["evidence_commit_binding"]["commit"]
        expected_parent = _single_artifact_commit_binding(
            root,
            commit=parent.get("commit", ""),
            parent=gate_commit,
            path=RECEIPT_PATH,
            raw=receipt_raw,
        )
        expected_predecessor = _artifact_binding(RECEIPT_PATH, receipt_payload, receipt_raw)
        predecessor_time = receipt_body["recorded_at"]
    else:
        docker_payload, docker_raw = _read_json(root, DOCKER_TERMINAL_PATH)
        docker_body = _validate_terminal_payload(root, PHASE_DOCKER, docker_payload, docker_raw)
        _require(
            docker_body["observation"]["status"] == no_call.DOCKER_READY_STATUS,
            "D-137 SDK attempt predecessor is not Docker READY",
        )
        docker_started, docker_started_raw = _read_json(root, DOCKER_STARTED_PATH)
        docker_started_body = _validate_started_payload(
            root, PHASE_DOCKER, docker_started, docker_started_raw
        )
        expected_parent = _transition_commit_binding(
            root,
            phase=PHASE_DOCKER,
            commit=parent.get("commit", ""),
            parent=docker_started_body["parent_commit_binding"]["commit"],
            started_raw=docker_started_raw,
            terminal_raw=docker_raw,
        )
        expected_predecessor = _artifact_binding(DOCKER_TERMINAL_PATH, docker_payload, docker_raw)
        predecessor_time = docker_body["recorded_at"]
    expected = _envelope(
        ATTEMPT_SCHEMA,
        _attempt_prefix(phase),
        _attempt_body(
            phase=phase,
            recorded_at=body.get("recorded_at"),
            predecessor_binding=expected_predecessor,
            parent_commit=expected_parent,
            predecessor_recorded_at=predecessor_time,
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected),
        f"D-137 {phase} attempt rebuild differs",
    )
    return body


def _create_attempt(root: Path, phase: str) -> dict[str, Any]:
    _assert_runtime_import_boundary(root)
    attempt_path, started_path, terminal_path = _phase_paths(phase)
    if phase == PHASE_DOCKER:
        for path in FUTURE_PATHS[2:]:
            _path_absent(root, path)
    else:
        for path in (SDK_STARTED_PATH, SDK_TERMINAL_PATH):
            _path_absent(root, path)
    if os.path.lexists(root / attempt_path):
        mode: Literal["pending", "post-commit"] = (
            "post-commit" if _status_lines(root) == [] else "pending"
        )
        return _validate_attempt(repository=root, phase=phase, mode=mode)
    _path_absent(root, started_path)
    _path_absent(root, terminal_path)
    _require(_status_lines(root) == [], f"D-137 {phase} attempt requires clean predecessor commit")
    predecessor, parent, predecessor_time = _attempt_parent(root, phase)
    payload = _envelope(
        ATTEMPT_SCHEMA,
        _attempt_prefix(phase),
        _attempt_body(
            phase=phase,
            recorded_at=_now(),
            predecessor_binding=predecessor,
            parent_commit=parent,
            predecessor_recorded_at=predecessor_time,
        ),
    )
    fresh_predecessor, fresh_parent, fresh_predecessor_time = _attempt_parent(root, phase)
    _require(
        canonical_json(predecessor) == canonical_json(fresh_predecessor)
        and canonical_json(parent) == canonical_json(fresh_parent)
        and predecessor_time == fresh_predecessor_time
        and _status_lines(root) == []
        and _head(root) == fresh_parent["commit"],
        f"D-137 {phase} predecessor drifted before attempt publication",
    )
    _write_new(root, attempt_path, _pretty_bytes(payload))
    return _validate_attempt(repository=root, phase=phase, mode="pending")


def _validate_attempt(
    *, repository: str | Path | None, phase: str, mode: Literal["pending", "post-commit"]
) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    attempt_path, started_path, terminal_path = _phase_paths(phase)
    _path_absent(root, started_path)
    _path_absent(root, terminal_path)
    if phase == PHASE_DOCKER:
        for path in (SDK_ATTEMPT_PATH, SDK_STARTED_PATH, SDK_TERMINAL_PATH):
            _path_absent(root, path)
    payload, raw = _read_json(root, attempt_path)
    body = _validate_attempt_payload(root, phase, payload, raw)
    parent = body["parent_commit_binding"]["commit"]
    commit = None
    if mode == "pending":
        _require(
            _pending_only(root, (attempt_path,), parent=parent),
            f"D-137 pending {phase} attempt differs",
        )
    elif mode == "post-commit":
        _require(_status_lines(root) == [], f"D-137 {phase} attempt checkout is not clean")
        commit = _single_artifact_commit_binding(
            root, commit=_head(root), parent=parent, path=attempt_path, raw=raw
        )
    else:
        raise D137NoCallPreflightSuccessorError("D-137 attempt validation mode differs")
    return {
        "phase": phase,
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "attempt_commit": commit,
        "commit_required_before_phase_observation": commit is None,
        "external_action_count": 0,
    }


def create_d137_docker_attempt(*, repository: str | Path | None = None) -> dict[str, Any]:
    return _create_attempt(_repo_root(repository), PHASE_DOCKER)


def validate_d137_docker_attempt(
    *, repository: str | Path | None = None, mode: Literal["pending", "post-commit"] = "pending"
) -> dict[str, Any]:
    return _validate_attempt(repository=repository, phase=PHASE_DOCKER, mode=mode)


def create_d137_sdk_attempt(*, repository: str | Path | None = None) -> dict[str, Any]:
    return _create_attempt(_repo_root(repository), PHASE_SDK)


def validate_d137_sdk_attempt(
    *, repository: str | Path | None = None, mode: Literal["pending", "post-commit"] = "pending"
) -> dict[str, Any]:
    return _validate_attempt(repository=repository, phase=PHASE_SDK, mode=mode)


def _started_body(
    *,
    phase: str,
    recorded_at: str,
    attempt_binding: dict[str, Any],
    parent_commit: dict[str, Any],
) -> dict[str, Any]:
    _require(
        _parse_time(recorded_at, label=f"{phase} ACTION_STARTED recorded_at")
        > _parse_time(attempt_binding["recorded_at"], label=f"{phase} attempt recorded_at"),
        f"D-137 {phase} ACTION_STARTED chronology differs",
    )
    return {
        "milestone": MILESTONE,
        "evidence_kind": f"{phase}-no-call-preflight-action-started",
        "phase": phase,
        "recorded_at": recorded_at,
        "status": _phase_status(phase, "started"),
        "phase_attempt_binding": attempt_binding,
        "parent_commit_binding": parent_commit,
        "observation_contract": {
            "marker_is_new_only_durable_and_fsynced_before_first_observation": True,
            "phase_helper_invocation_limit": 1,
            "transport_retry_count": 0,
            "post_marker_exception_consumes_phase": True,
            "marker_only_preservation_commit_is_pre_authorized": True,
        },
        "authority": {
            "phase_helper_invocation_count_at_marker_write": 0,
            "docker_cli_call_count_at_marker_write": 0,
            "sdk_import_or_credential_presence_observation_count_at_marker_write": 0,
            "phase_terminal_created_at_marker_write": False,
            "environment_value_observation_count": 0,
            "provider_evaluator_agent_call_count": 0,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
    }


def _validate_started_payload(
    root: Path, phase: str, payload: dict[str, Any], raw: bytes
) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=STARTED_SCHEMA, prefix=_started_prefix(phase))
    _require(body.get("phase") == phase, f"D-137 {phase} ACTION_STARTED phase differs")
    attempt_path, _started_path, _terminal_path = _phase_paths(phase)
    attempt_payload, attempt_raw = _read_json(root, attempt_path)
    attempt_body = _validate_attempt_payload(root, phase, attempt_payload, attempt_raw)
    parent = body.get("parent_commit_binding")
    _require(isinstance(parent, dict), f"D-137 {phase} marker parent differs")
    attempt_commit = _single_artifact_commit_binding(
        root,
        commit=parent.get("commit", ""),
        parent=attempt_body["parent_commit_binding"]["commit"],
        path=attempt_path,
        raw=attempt_raw,
    )
    expected = _envelope(
        STARTED_SCHEMA,
        _started_prefix(phase),
        _started_body(
            phase=phase,
            recorded_at=body.get("recorded_at"),
            attempt_binding=_artifact_binding(attempt_path, attempt_payload, attempt_raw),
            parent_commit=attempt_commit,
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected),
        f"D-137 {phase} ACTION_STARTED rebuild differs",
    )
    return body


def _validate_action_started(
    *,
    repository: str | Path | None,
    phase: str,
    mode: Literal["pending-marker", "post-preservation-commit"],
) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    _attempt_path, started_path, terminal_path = _phase_paths(phase)
    if phase == PHASE_DOCKER:
        for path in (SDK_ATTEMPT_PATH, SDK_STARTED_PATH, SDK_TERMINAL_PATH):
            _path_absent(root, path)
    _path_absent(root, terminal_path)
    payload, raw = _read_json(root, started_path)
    body = _validate_started_payload(root, phase, payload, raw)
    attempt_commit = body["parent_commit_binding"]["commit"]
    commit = None
    if mode == "pending-marker":
        _require(
            _pending_only(root, (started_path,), parent=attempt_commit),
            f"D-137 pending {phase} marker differs",
        )
    elif mode == "post-preservation-commit":
        _require(_status_lines(root) == [], f"D-137 {phase} preservation checkout is not clean")
        commit = _single_artifact_commit_binding(
            root, commit=_head(root), parent=attempt_commit, path=started_path, raw=raw
        )
    else:
        raise D137NoCallPreflightSuccessorError("D-137 marker validation mode differs")
    return {
        "phase": phase,
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "marker_preservation_commit": commit,
        "phase_consumed": True,
        "retry_allowed": False,
        "phase_observation_count_reconstructed": None,
    }


def validate_d137_docker_action_started(
    *,
    repository: str | Path | None = None,
    mode: Literal["pending-marker", "post-preservation-commit"] = "pending-marker",
) -> dict[str, Any]:
    return _validate_action_started(repository=repository, phase=PHASE_DOCKER, mode=mode)


def validate_d137_sdk_action_started(
    *,
    repository: str | Path | None = None,
    mode: Literal["pending-marker", "post-preservation-commit"] = "pending-marker",
) -> dict[str, Any]:
    return _validate_action_started(repository=repository, phase=PHASE_SDK, mode=mode)


def _validate_observation(phase: str, value: Any) -> dict[str, Any]:
    try:
        if phase == PHASE_DOCKER:
            return no_call.validate_d137_docker_no_call_preflight_observation(value)
        return no_call.validate_d137_sdk_no_call_preflight_observation(value)
    except (ContractError, TypeError, ValueError) as exc:
        raise D137NoCallPreflightSuccessorError(
            f"D-137 {phase} observation validation failed"
        ) from exc


def _terminal_body(
    *,
    phase: str,
    recorded_at: str,
    started_binding: dict[str, Any],
    parent_commit: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    _require(
        _parse_time(recorded_at, label=f"{phase} terminal recorded_at")
        > _parse_time(started_binding["recorded_at"], label=f"{phase} ACTION_STARTED recorded_at"),
        f"D-137 {phase} terminal chronology differs",
    )
    ready = observation["passed"] is True
    if phase == PHASE_DOCKER:
        next_status = (
            "D137_SDK_ATTEMPT_REQUIRES_COMMITTED_DOCKER_READY_TERMINAL"
            if ready
            else "D138_DOCKER_BLOCKED_OFFLINE_SUCCESSOR_APPROVAL_REQUIRED"
        )
    else:
        next_status = (
            "D138_READY_NO_CALL_PREFLIGHT_OFFLINE_SUCCESSOR_APPROVAL_REQUIRED"
            if ready
            else "D138_SDK_BLOCKED_OFFLINE_SUCCESSOR_APPROVAL_REQUIRED"
        )
    return {
        "milestone": MILESTONE,
        "evidence_kind": f"{phase}-no-call-preflight-terminal",
        "phase": phase,
        "recorded_at": recorded_at,
        "status": _phase_status(phase, "terminal", observation["status"]),
        "action_started_binding": started_binding,
        "parent_commit_binding": parent_commit,
        "observation": observation,
        "activity_accounting": observation["activity"],
        "evidence_boundary": {
            "observation_is_replay_validated": True,
            "ready_or_blocked_is_terminal_for_this_phase": True,
            "post_marker_retry_resume_repair_or_backfill_allowed": False,
            "credential_or_environment_values_persisted": False,
            "provider_evaluator_agent_call_count": 0,
        },
        "authority": {
            "later_phase_authorized": phase == PHASE_DOCKER and ready,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
        "next_gate": {
            "status": next_status,
            "fresh_separate_approval_required": phase == PHASE_SDK or not ready,
            "current_activation_authorizes_execution_hash_candidate_cost_or_ac": False,
        },
    }


def _validate_terminal_payload(
    root: Path, phase: str, payload: dict[str, Any], raw: bytes
) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=TERMINAL_SCHEMA, prefix=_terminal_prefix(phase))
    _require(body.get("phase") == phase, f"D-137 {phase} terminal phase differs")
    _attempt_path, started_path, _terminal_path = _phase_paths(phase)
    started_payload, started_raw = _read_json(root, started_path)
    started_body = _validate_started_payload(root, phase, started_payload, started_raw)
    observation = _validate_observation(phase, body.get("observation"))
    expected = _envelope(
        TERMINAL_SCHEMA,
        _terminal_prefix(phase),
        _terminal_body(
            phase=phase,
            recorded_at=body.get("recorded_at"),
            started_binding=_artifact_binding(started_path, started_payload, started_raw),
            parent_commit=started_body["parent_commit_binding"],
            observation=observation,
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected),
        f"D-137 {phase} terminal rebuild differs",
    )
    return body


def _run_phase(root: Path, phase: str) -> dict[str, Any]:
    _assert_runtime_import_boundary(root)
    attempt_path, started_path, terminal_path = _phase_paths(phase)
    if os.path.lexists(root / terminal_path) and not os.path.lexists(root / started_path):
        raise D137NoCallPreflightSuccessorError(f"D-137 {phase} terminal is orphaned")
    if os.path.lexists(root / started_path):
        started_payload, started_raw = _read_json(root, started_path)
        _validate_started_payload(root, phase, started_payload, started_raw)
        if os.path.lexists(root / terminal_path):
            mode: Literal["pending", "post-transition-commit"] = (
                "post-transition-commit" if _status_lines(root) == [] else "pending"
            )
            return _validate_terminal(repository=root, phase=phase, mode=mode)
        raise D137NoCallPreflightSuccessorError(
            f"D-137 {phase} ACTION_STARTED has no terminal; phase is consumed and retry is "
            "forbidden"
        )
    if phase == PHASE_DOCKER:
        for path in (SDK_ATTEMPT_PATH, SDK_STARTED_PATH, SDK_TERMINAL_PATH):
            _path_absent(root, path)

    attempt_payload, attempt_raw = _read_json(root, attempt_path)
    attempt_body = _validate_attempt_payload(root, phase, attempt_payload, attempt_raw)
    _require(_status_lines(root) == [], f"D-137 {phase} requires clean committed attempt")
    attempt_commit = _single_artifact_commit_binding(
        root,
        commit=_head(root),
        parent=attempt_body["parent_commit_binding"]["commit"],
        path=attempt_path,
        raw=attempt_raw,
    )
    started = _envelope(
        STARTED_SCHEMA,
        _started_prefix(phase),
        _started_body(
            phase=phase,
            recorded_at=_now(),
            attempt_binding=_artifact_binding(attempt_path, attempt_payload, attempt_raw),
            parent_commit=attempt_commit,
        ),
    )
    started_raw = _pretty_bytes(started)
    prepublication_attempt, prepublication_attempt_raw = _read_json(root, attempt_path)
    _validate_attempt_payload(root, phase, prepublication_attempt, prepublication_attempt_raw)
    _require(
        prepublication_attempt_raw == attempt_raw
        and _status_lines(root) == []
        and _head(root) == attempt_commit["commit"],
        f"D-137 {phase} attempt drifted before ACTION_STARTED publication",
    )
    _write_new(root, started_path, started_raw)
    stored_started, stored_started_raw = _read_json(root, started_path)
    _validate_started_payload(root, phase, stored_started, stored_started_raw)
    _require(stored_started_raw == started_raw, f"D-137 {phase} marker durability differs")
    _require(
        _pending_only(root, (started_path,), parent=attempt_commit["commit"]),
        f"D-137 checkout drifted after {phase} marker and before helper",
    )

    try:
        if phase == PHASE_DOCKER:
            observation = no_call.run_d137_docker_no_call_preflight_observation(repository=root)
        else:
            observation = no_call.run_d137_sdk_no_call_preflight_observation(repository=root)
        observation = _validate_observation(phase, observation)
    except Exception as exc:
        raise D137NoCallPreflightSuccessorError(
            f"D-137 {phase} observation failed after ACTION_STARTED; phase is consumed"
        ) from exc

    fresh_attempt, fresh_attempt_raw = _read_json(root, attempt_path)
    _validate_attempt_payload(root, phase, fresh_attempt, fresh_attempt_raw)
    fresh_started, fresh_started_raw = _read_json(root, started_path)
    _validate_started_payload(root, phase, fresh_started, fresh_started_raw)
    _require(
        fresh_attempt_raw == attempt_raw
        and fresh_started_raw == stored_started_raw
        and _pending_only(root, (started_path,), parent=attempt_commit["commit"]),
        f"D-137 checkout drifted after {phase} helper and before terminal",
    )
    terminal = _envelope(
        TERMINAL_SCHEMA,
        _terminal_prefix(phase),
        _terminal_body(
            phase=phase,
            recorded_at=_now(),
            started_binding=_artifact_binding(started_path, fresh_started, fresh_started_raw),
            parent_commit=attempt_commit,
            observation=observation,
        ),
    )
    final_attempt, final_attempt_raw = _read_json(root, attempt_path)
    _validate_attempt_payload(root, phase, final_attempt, final_attempt_raw)
    final_started, final_started_raw = _read_json(root, started_path)
    _validate_started_payload(root, phase, final_started, final_started_raw)
    _require(
        final_attempt_raw == attempt_raw
        and final_started_raw == stored_started_raw
        and _pending_only(root, (started_path,), parent=attempt_commit["commit"]),
        f"D-137 checkout drifted immediately before {phase} terminal publication",
    )
    _write_new(root, terminal_path, _pretty_bytes(terminal))
    return _validate_terminal(repository=root, phase=phase, mode="pending")


def _validate_terminal(
    *,
    repository: str | Path | None,
    phase: str,
    mode: Literal["pending", "post-transition-commit"],
) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    _attempt_path, started_path, terminal_path = _phase_paths(phase)
    if phase == PHASE_DOCKER:
        for path in (SDK_ATTEMPT_PATH, SDK_STARTED_PATH, SDK_TERMINAL_PATH):
            _path_absent(root, path)
    started_payload, started_raw = _read_json(root, started_path)
    started_body = _validate_started_payload(root, phase, started_payload, started_raw)
    payload, raw = _read_json(root, terminal_path)
    body = _validate_terminal_payload(root, phase, payload, raw)
    attempt_commit = started_body["parent_commit_binding"]["commit"]
    transition = None
    if mode == "pending":
        _require(
            _pending_only(root, (started_path, terminal_path), parent=attempt_commit),
            f"D-137 pending {phase} transition differs",
        )
    elif mode == "post-transition-commit":
        _require(_status_lines(root) == [], f"D-137 {phase} transition checkout is not clean")
        transition = _transition_commit_binding(
            root,
            phase=phase,
            commit=_head(root),
            parent=attempt_commit,
            started_raw=started_raw,
            terminal_raw=raw,
        )
    else:
        raise D137NoCallPreflightSuccessorError("D-137 terminal validation mode differs")
    return {
        "phase": phase,
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "observation_status": body["observation"]["status"],
        "passed": body["observation"]["passed"],
        "transition_commit": transition,
        "commit_required_before_next_action": transition is None,
        "phase_consumed": True,
        "retry_allowed": False,
        "provider_evaluator_agent_call_count": 0,
        "cost_reserved_or_spent_usd": "0",
    }


def run_d137_docker_no_call_preflight(*, repository: str | Path | None = None) -> dict[str, Any]:
    return _run_phase(_repo_root(repository), PHASE_DOCKER)


def validate_d137_docker_terminal(
    *,
    repository: str | Path | None = None,
    mode: Literal["pending", "post-transition-commit"] = "pending",
) -> dict[str, Any]:
    return _validate_terminal(repository=repository, phase=PHASE_DOCKER, mode=mode)


def run_d137_sdk_no_call_preflight(*, repository: str | Path | None = None) -> dict[str, Any]:
    return _run_phase(_repo_root(repository), PHASE_SDK)


def validate_d137_sdk_terminal(
    *,
    repository: str | Path | None = None,
    mode: Literal["pending", "post-transition-commit"] = "pending",
) -> dict[str, Any]:
    return _validate_terminal(repository=repository, phase=PHASE_SDK, mode=mode)


__all__ = [
    "ACTIVE_DOC_PATHS",
    "ACTIVATION_EXCLUSIONS",
    "ACTIVATION_SCOPE",
    "D136_SUCCESS_COMMIT",
    "D136_SUCCESS_TREE",
    "D137NoCallPreflightSuccessorError",
    "DOCKER_ATTEMPT_PATH",
    "DOCKER_STARTED_PATH",
    "DOCKER_TERMINAL_PATH",
    "FUTURE_PATHS",
    "GATE_PATH",
    "GATE_STATUS",
    "IMPLEMENTATION_PATHS",
    "RECEIPT_PATH",
    "SDK_ATTEMPT_PATH",
    "SDK_STARTED_PATH",
    "SDK_TERMINAL_PATH",
    "SOURCE_PREPARATION_EXCLUSIONS",
    "SOURCE_PREPARATION_SCOPE",
    "create_d137_activation_receipt",
    "create_d137_docker_attempt",
    "create_d137_sdk_attempt",
    "render_d137_external_activation_template",
    "run_d137_docker_no_call_preflight",
    "run_d137_offline_source_gate",
    "run_d137_sdk_no_call_preflight",
    "validate_d137_activation_receipt",
    "validate_d137_docker_action_started",
    "validate_d137_docker_attempt",
    "validate_d137_docker_terminal",
    "validate_d137_offline_source_gate",
    "validate_d137_sdk_action_started",
    "validate_d137_sdk_attempt",
    "validate_d137_sdk_terminal",
]
