"""D-140 offline qualification and future fresh SDK no-call transition.

The D-139 execution identity is immutable and consumed.  This module only
replays its committed evidence and prepares a distinct D-140 one-use chain.
Importing it performs no environment, credential, SDK, endpoint, or network
observation.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import uuid
from collections.abc import Callable, Mapping
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import patchloop as patchloop_module
from patchloop import errors as patchloop_errors
from patchloop import evals as patchloop_evals
from patchloop import util as patchloop_util
from patchloop.errors import ContractError
from patchloop.evals import d140_sdk_no_call_successor as no_call
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-140"
GATE_SCHEMA = "d139-sdk-blocked-no-call-successor-offline-source-gate-d140-v1"
GATE_STATUS = (
    "D140_D139_SDK_BLOCKED_NO_CALL_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_FRESH_ACTIVATION_REQUIRED"
)
GATE_PATH = Path(
    "reports/live-pilot/artifacts/d140-d139-sdk-blocked-no-call-successor-offline-source-gate.json"
)

RECEIPT_SCHEMA = "d140-sdk-no-call-successor-activation-receipt-v1"
ATTEMPT_SCHEMA = "d140-sdk-no-call-successor-attempt-intent-v1"
STARTED_SCHEMA = "d140-sdk-no-call-successor-action-started-v1"
TERMINAL_SCHEMA = "d140-sdk-no-call-successor-terminal-v1"
RECEIPT_STATUS = "D140_SDK_NO_CALL_SUCCESSOR_ACTIVATION_RECEIPT_RECORDED_COMMIT_REQUIRED"
ATTEMPT_STATUS = "D140_SDK_NO_CALL_SUCCESSOR_ATTEMPT_RECORDED_COMMIT_REQUIRED"
STARTED_STATUS = "D140_SDK_NO_CALL_SUCCESSOR_ACTION_STARTED_TRANSITION_COMMIT_REQUIRED"
TERMINAL_READY_STATUS = "D140_SDK_NO_CALL_SUCCESSOR_READY_TRANSITION_COMMIT_REQUIRED"
TERMINAL_BLOCKED_STATUS = "D140_SDK_NO_CALL_SUCCESSOR_BLOCKED_TRANSITION_COMMIT_REQUIRED"

RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/d140-sdk-no-call-successor-activation-receipt.json"
)
ATTEMPT_PATH = Path("reports/live-pilot/artifacts/d140-sdk-no-call-successor-attempt-intent.json")
STARTED_PATH = Path("reports/live-pilot/artifacts/d140-sdk-no-call-successor-action-started.json")
TERMINAL_PATH = Path("reports/live-pilot/artifacts/d140-sdk-no-call-successor-terminal.json")
FUTURE_PATHS = (RECEIPT_PATH, ATTEMPT_PATH, STARTED_PATH, TERMINAL_PATH)

D139_SOURCE_COMMIT = "f5625be6cf98b5f8824a0d6a5068f1cf03e94d98"
D139_SOURCE_TREE = "073f821ce8f800a9bbd4cf56c228f00804a8c55a"
D139_SOURCE_PARENT = "9f31d330190aa83768077b17c3cde47eb86c639d"
D139_GATE_COMMIT = "ab7b56beb63c99321f27b8712cec281ba0106c19"
D139_GATE_TREE = "75e35d25426e2fe99b674de27bd2ee2edfe2ebfd"
D139_RECEIPT_COMMIT = "fdf2faa739723d9bf330f2d1b35eae1ad530e438"
D139_RECEIPT_TREE = "e6137ed88f590764f43718f8a7678cc7e5a1bda1"
D139_SDK_ATTEMPT_COMMIT = "d17324062acd030b198a2dc0f54e8937016de924"
D139_SDK_ATTEMPT_TREE = "7a2ae0505233f6b41ec705d1db3aafdc69678923"
D139_SDK_TRANSITION_COMMIT = "ba3af19a5cada8e49c29f514ad56c299639dc452"
D139_SDK_TRANSITION_TREE = "454e6b704ae2f758364d876642262081f2eb141f"

D139_GATE_PATH = Path(
    "reports/live-pilot/artifacts/d139-d138-sdk-blocked-no-call-successor-offline-source-gate.json"
)
D139_RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/d139-sdk-no-call-successor-activation-receipt.json"
)
D139_SDK_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d139-sdk-no-call-successor-attempt-intent.json"
)
D139_SDK_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/d139-sdk-no-call-successor-action-started.json"
)
D139_SDK_TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d139-sdk-no-call-successor-terminal.json"
)

_D139_ARTIFACTS = (
    (
        D139_GATE_PATH,
        "d139_09f2e9dfe0ee333a2683c058b772b92f025708c4bcc6b7f1eb89c007ed8df7f8",
        "sha256:09f2e9dfe0ee333a2683c058b772b92f025708c4bcc6b7f1eb89c007ed8df7f8",
        "sha256:a374b0fd1685ea7df0ab4e343dee59cfac6dba0d7a58bf01e3e7b887f1d13584",
        15_565,
        "5a48b3e7447a450929aa52aa58a4e0fcbb352c15",
        D139_GATE_COMMIT,
    ),
    (
        D139_RECEIPT_PATH,
        "d139approval_72e254cf71d8fcad24e6069ee2fb68cd220a95b70229bbee4b4643392abc1c71",
        "sha256:72e254cf71d8fcad24e6069ee2fb68cd220a95b70229bbee4b4643392abc1c71",
        "sha256:2ff140262751144c78529eabd1ca34596c59634d526bba0bd068044a677965ca",
        9_270,
        "85c60ed8a271dbce2403549f07c21feb83e4342a",
        D139_RECEIPT_COMMIT,
    ),
    (
        D139_SDK_ATTEMPT_PATH,
        "d139sdkattempt_84ee2917e702d7ed58df00fdc84ae3f5e042b271e7551ab72012b886beb27021",
        "sha256:84ee2917e702d7ed58df00fdc84ae3f5e042b271e7551ab72012b886beb27021",
        "sha256:f8a96cd6f5b7a5242037f205b728f427ac87a38ee10ec7b46c98cc301e212b44",
        5_304,
        "23f60f466a90b33dad2d57719b4227f097ae71f5",
        D139_SDK_ATTEMPT_COMMIT,
    ),
    (
        D139_SDK_STARTED_PATH,
        "d139sdkstarted_7ec011e8d177b404464534dfc238bc94a02dbd8c4e29f8a8fb2a518559d05fd2",
        "sha256:7ec011e8d177b404464534dfc238bc94a02dbd8c4e29f8a8fb2a518559d05fd2",
        "sha256:de1fefd49eef8fc653d4250e00c55d8bf953ca0b43437fce82e5b295fdae4d74",
        5_285,
        "1e336bb9c038ad026b7e0130f3074d6f4c233733",
        D139_SDK_TRANSITION_COMMIT,
    ),
    (
        D139_SDK_TERMINAL_PATH,
        "d139sdk_4154a198d2b46e884ffe535f07dfb8a21df63c24e511873e503d1628004596e5",
        "sha256:4154a198d2b46e884ffe535f07dfb8a21df63c24e511873e503d1628004596e5",
        "sha256:f9f3f18d1df737f1a814baf31d7e5f09b2b0ea2e3bc408e57361d4fead419438",
        8_568,
        "87bcc88f6e50aedff4590501e0e718adeba58f36",
        D139_SDK_TRANSITION_COMMIT,
    ),
)

D139_IMPLEMENTATION_PATHS = (
    Path("patchloop/evals/d139_sdk_no_call_successor.py"),
    Path("patchloop/evals/d139_d138_sdk_blocked_successor_offline.py"),
    Path("scripts/build_d139_d138_sdk_blocked_successor_offline.py"),
    Path("tests/test_d139_d138_sdk_blocked_successor_offline.py"),
)
IMPLEMENTATION_PATHS = (
    Path("patchloop/evals/d140_sdk_no_call_successor.py"),
    Path("patchloop/evals/d140_d139_sdk_blocked_successor_offline.py"),
    Path("scripts/build_d140_d139_sdk_blocked_successor_offline.py"),
    Path("tests/test_d140_d139_sdk_blocked_successor_offline.py"),
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
            *(path for path, _name in LOADED_MODULE_PATHS),
            Path("patchloop/agent/model.py"),
            Path("pyproject.toml"),
            Path("uv.lock"),
        )
    )
)
SOURCE_BINDING_PATHS = tuple(dict.fromkeys((*IMPLEMENTATION_PATHS, *DEPENDENCY_PATHS)))
RUNTIME_COMMITTED_SOURCE_PATHS = {
    "helper": Path("patchloop/evals/d140_sdk_no_call_successor.py"),
    "model": Path("patchloop/agent/model.py"),
    "lock": Path("uv.lock"),
}

SOURCE_PREPARATION_SCOPE = (
    "exact-bind-and-replay-validate-complete-d139-sdk-blocked-topology",
    "implement-distinct-d140-sdk-no-call-successor-helper-writer-validator-orchestrator-cli-tests",
    "run-focused-fully-mocked-tests-only",
    "never-import-or-invoke-d139-execution-runner",
    "require-exact-inherited-environment-repository-venv-launch-with-e-s-b-flags",
    "isolate-future-sdk-import-and-probe-in-empty-environment-bounded-child",
    "implement-future-receipt-attempt-fsynced-marker-terminal-or-marker-only-one-use-chain",
    "check-credential-and-routing-membership-bits-only-then-provenance-and-zero-dispatch-probe",
    "bind-credential-provisioning-as-separate-from-source-preparation-and-future-activation",
    "enforce-append-only-collision-orphan-idempotence-toctou-loaded-module-and-fixed-git",
    "create-exact-four-path-source-only-commit-as-d139-sdk-transition-sole-child",
    "create-gate-plus-exact-ten-active-doc-evidence-commit-as-source-direct-child",
    "update-active-docs-to-record-d139-consumed-blocked-and-d140-source-qualified-only",
    "render-fresh-exact-d140-activation-template",
    "create-only-described-local-git-commits",
)
SOURCE_PREPARATION_EXCLUSIONS = (
    "create-d140-receipt-attempt-action-started-terminal-or-preservation-artifact",
    "provision-set-clear-export-copy-rotate-or-mutate-any-credential",
    "read-print-log-hash-measure-prefix-or-persist-credential-or-environment-values",
    "read-or-load-dotenv",
    "rerun-reuse-repair-resume-or-backfill-d139",
    "perform-environment-membership-check-during-source-preparation",
    "import-or-inspect-sdk-runtime-during-source-preparation",
    "launch-isolated-child-during-source-preparation",
    "synthetic-or-real-transport-dispatch-official-docs-network-or-docker-operation",
    "provider-evaluator-agent-memory-retrieval-hash-candidate-cost-or-four-row-ac",
)
ACTIVATION_SCOPE = (
    "create-one-exact-d140-activation-receipt-and-sole-artifact-commit",
    "create-one-exact-d140-sdk-attempt-and-sole-artifact-commit",
    "use-exact-inherited-environment-repository-venv-python-e-s-b-launch",
    "record-one-fsynced-d140-action-started-immediately-before-first-membership-observation",
    "perform-one-membership-only-then-provenance-zero-dispatch-sdk-no-call-observation",
    "run-sdk-import-and-probe-only-in-bounded-empty-environment-isolated-child",
    "commit-action-started-plus-ready-or-blocked-terminal",
    "preserve-action-started-only-after-post-marker-failure-with-no-retry",
    "request-separate-offline-successor-after-committed-terminal",
)
ACTIVATION_EXCLUSIONS = (
    "credential-provision-set-clear-export-value-read-hash-length-prefix-or-persistence",
    "credential-value-in-approval-message-or-chat",
    "dotenv-read-load-or-live-endpoint-observation",
    "d139-retry-reuse-resume-repair-or-backfill",
    "synthetic-or-real-transport-dispatch-provider-evaluator-agent-or-network-call",
    "docker-memory-retrieval-injection-hash-candidate-cost-or-four-row-ac",
)

CREDENTIAL_PROVISIONING_BOUNDARY = {
    "source_preparation_authorizes_credential_provisioning": False,
    "future_no_call_activation_authorizes_credential_provisioning": False,
    "credential_value_in_approval_or_chat_allowed": False,
    "credential_provisioning_if_any_requires_separate_user_controlled_step": True,
}

ROOT_KEYS = ("schema_version", "artifact_id", "semantic_body_hash", "semantic_body")
GATE_ROOT_KEYS = ("schema_version", "gate_id", "semantic_body_hash", "semantic_body")


class D140SDKBlockedSuccessorError(ContractError):
    """D-140 source, evidence, ordering, or authority failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D140SDKBlockedSuccessorError(message)


def _is_linklike(path: Path) -> bool:
    metadata = path.lstat()
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & 0x400
    )


def _assert_nonlink_absolute_chain(path: Path, *, label: str) -> Path:
    _require(path.is_absolute(), f"D-140 {label} is not absolute")
    lexical = Path(os.path.abspath(path))
    _require(path == lexical, f"D-140 {label} lexical spelling differs")
    resolved = lexical.resolve(strict=True)
    _require(lexical == resolved, f"D-140 {label} lexical and resolved paths differ")
    current = lexical
    while True:
        _require(not _is_linklike(current), f"D-140 {label} ancestor is link-like")
        if current.parent == current:
            break
        current = current.parent
    return resolved


def _repo_root(repository: str | Path | None) -> Path:
    root = Path(__file__).absolute().parents[2] if repository is None else Path(repository)
    if not root.is_absolute():
        root = Path(os.path.abspath(root))
    return _assert_nonlink_absolute_chain(root, label="repository root")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_time(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"D-140 {label} differs")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise D140SDKBlockedSuccessorError(f"D-140 {label} differs") from exc
    _require(parsed.tzinfo is not None, f"D-140 {label} lacks timezone")
    return parsed


def _stable_read(root: Path, relative: Path) -> bytes:
    path = _logical_path(root, relative, must_exist=True)
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    _require(
        (before.st_size, before.st_mtime_ns, before.st_ino)
        == (after.st_size, after.st_mtime_ns, after.st_ino),
        f"D-140 file changed during read: {relative}",
    )
    _require(
        _logical_path(root, relative, must_exist=True) == path,
        f"D-140 path drifted during read: {relative}",
    )
    return raw


def _file_binding(root: Path, relative: Path) -> dict[str, Any]:
    path = _logical_path(root, relative, must_exist=True)
    _require(not _is_linklike(path), f"D-140 link-like source: {relative}")
    raw = _stable_read(root, relative)
    return {
        "path": relative.as_posix(),
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "linklike": False,
    }


def _logical_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    _require(not relative.is_absolute() and ".." not in relative.parts, "D-140 unsafe path")
    resolved_root = _assert_nonlink_absolute_chain(root, label="repository root")
    selected = Path(os.path.abspath(resolved_root / relative))
    _require(selected.is_relative_to(resolved_root), f"D-140 path escapes repository: {relative}")
    if os.path.lexists(selected):
        _require(
            _assert_nonlink_absolute_chain(selected, label=f"repository path {relative}")
            == selected,
            f"D-140 path differs: {relative}",
        )
    else:
        _require(not must_exist, f"D-140 path missing: {relative}")
        _require(
            _assert_nonlink_absolute_chain(
                selected.parent, label=f"repository path parent {relative}"
            )
            == selected.parent,
            f"D-140 path parent differs: {relative}",
        )
    return selected


def _path_absent(root: Path, relative: Path) -> None:
    selected = _logical_path(root, relative, must_exist=False)
    _require(not os.path.lexists(selected), f"D-140 path collision: {relative}")


def _pretty_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


PrepublishCheck = Callable[[Path, bytes], None]


def _write_new(
    root: Path,
    relative: Path,
    raw: bytes,
    *,
    prepublish: PrepublishCheck | None = None,
) -> None:
    selected = _logical_path(root, relative, must_exist=False)
    _require(not os.path.lexists(selected), f"D-140 publication collision: {relative}")
    temporary = selected.with_name(f".{selected.name}.d140-{uuid.uuid4().hex}.tmp")
    temporary_relative = temporary.relative_to(root)
    _require(
        _logical_path(root, temporary_relative, must_exist=False) == temporary,
        "D-140 temporary output path differs",
    )
    _require(not os.path.lexists(temporary), "D-140 temporary output collision")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_raw = _stable_read(root, temporary_relative)
        _require(temporary_raw == raw, "D-140 temporary output differs")
        if prepublish is not None:
            prepublish(temporary_relative, temporary_raw)
        _require(
            _logical_path(root, temporary_relative, must_exist=True) == temporary
            and _logical_path(root, relative, must_exist=False) == selected
            and not os.path.lexists(selected),
            "D-140 publication path drifted",
        )
        try:
            os.link(temporary, selected)
        except FileExistsError as exc:
            raise D140SDKBlockedSuccessorError(f"D-140 publication collision: {relative}") from exc
        _require(_stable_read(root, relative) == raw, "D-140 persisted output differs")
    finally:
        if os.path.lexists(temporary):
            with suppress(OSError, D140SDKBlockedSuccessorError):
                _logical_path(root, temporary_relative, must_exist=True).unlink()


def _require_prepublish_status(
    root: Path,
    *,
    temporary: Path,
    expected_without_temporary: tuple[str, ...],
) -> None:
    expected = sorted((*expected_without_temporary, f"?? {temporary.as_posix()}"))
    _require(sorted(_status_lines(root)) == expected, "D-140 prepublication status drifted")


def _git_engine_binding() -> dict[str, Any]:
    selected = _assert_nonlink_absolute_chain(GIT_ENGINE_PATH, label="Git engine")
    _require(selected == GIT_ENGINE_PATH and selected.is_file(), "D-140 Git path differs")
    before = selected.stat()
    raw = selected.read_bytes()
    after = selected.stat()
    _require(
        (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
        "D-140 Git changed during binding",
    )
    _require(len(raw) == GIT_ENGINE_FILE_BYTES, "D-140 Git bytes differ")
    _require(sha256_bytes(raw) == GIT_ENGINE_FILE_SHA256, "D-140 Git SHA differs")
    return {
        "path": str(selected),
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "linklike": selected.is_symlink(),
    }


def _git_command(root: Path, *args: str, binary: bool = False) -> str | bytes:
    before = _git_engine_binding()
    try:
        completed = subprocess.run(  # noqa: S603
            [str(GIT_ENGINE_PATH), *args],
            cwd=root,
            env=dict(FIXED_GIT_ENVIRONMENT),
            capture_output=True,
            shell=False,
            check=False,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise D140SDKBlockedSuccessorError("D-140 bounded Git observation failed") from exc
    _require(_git_engine_binding() == before, "D-140 Git changed during command")
    _require(
        len(completed.stdout) <= MAX_GIT_OUTPUT_BYTES
        and len(completed.stderr) <= MAX_GIT_OUTPUT_BYTES,
        "D-140 Git output exceeds bound",
    )
    _require(completed.returncode == 0, f"D-140 Git failed: {' '.join(args)}")
    if binary:
        return completed.stdout
    return completed.stdout.decode("utf-8").strip()


def _head(root: Path) -> str:
    return str(_git_command(root, "rev-parse", "HEAD"))


def _status_lines(root: Path) -> list[str]:
    value = str(_git_command(root, "status", "--porcelain=v1", "--untracked-files=all"))
    return [line.replace("\\", "/") for line in value.splitlines() if line]


def _commit_identity(root: Path, commit: str) -> dict[str, Any]:
    resolved = str(_git_command(root, "rev-parse", f"{commit}^{{commit}}"))
    _require(resolved == commit, "D-140 commit identity differs")
    value = str(_git_command(root, "show", "-s", "--format=%T%x00%P", commit))
    tree, parents = value.split("\x00", 1)
    return {"commit": commit, "tree": tree, "parents": parents.split() if parents else []}


def _diff_rows(root: Path, commit: str) -> list[dict[str, str]]:
    value = str(
        _git_command(root, "diff-tree", "--root", "--no-commit-id", "--name-status", "-r", commit)
    )
    rows: list[dict[str, str]] = []
    for line in value.splitlines():
        if line:
            status, path = line.split("\t", 1)
            rows.append({"status": status, "path": path.replace("\\", "/")})
    return rows


def _commit_blob(root: Path, commit: str, path: Path) -> tuple[str, bytes]:
    oid = str(_git_command(root, "rev-parse", f"{commit}:{path.as_posix()}"))
    raw = _git_command(root, "cat-file", "blob", oid, binary=True)
    _require(isinstance(raw, bytes), "D-140 committed blob differs")
    return oid, raw


def _git_cli_observation(root: Path) -> dict[str, Any]:
    binding = _git_engine_binding()
    version = _git_command(root, "--version")
    normalization = _git_command(root, "config", "--local", "--get", "core.autocrlf")
    _require(version == GIT_VERSION, "D-140 Git version differs")
    _require(normalization == "false", "D-140 core.autocrlf differs")
    return {
        **binding,
        "version": version,
        "repository_local_core_autocrlf": "false",
        "minimal_secret_free_environment": True,
        "environment_value_observation_count": 0,
        "shell_used": False,
    }


def _assert_runtime_import_boundary(root: Path) -> None:
    for relative, module_name in LOADED_MODULE_PATHS:
        module = sys.modules.get(module_name)
        value = getattr(module, "__file__", None)
        _require(isinstance(value, str), f"D-140 loaded module differs: {relative}")
        actual = _assert_nonlink_absolute_chain(Path(value), label=f"loaded module {relative}")
        expected = _logical_path(root, relative, must_exist=True)
        _require(actual == expected, f"D-140 loaded module provenance differs: {relative}")


def _envelope(
    schema: str, prefix: str, body: dict[str, Any], *, gate: bool = False
) -> dict[str, Any]:
    body_hash = sha256_text(canonical_json(body))
    key = "gate_id" if gate else "artifact_id"
    return {
        "schema_version": schema,
        key: f"{prefix}_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _validate_envelope(
    payload: Any, raw: bytes, *, schema: str, prefix: str, gate: bool = False
) -> dict[str, Any]:
    expected_keys = GATE_ROOT_KEYS if gate else ROOT_KEYS
    _require(isinstance(payload, dict) and tuple(payload) == expected_keys, "D-140 envelope fields")
    _require(payload["schema_version"] == schema, "D-140 envelope schema")
    body = payload["semantic_body"]
    _require(isinstance(body, dict), "D-140 semantic body differs")
    expected = _envelope(schema, prefix, body, gate=gate)
    _require(canonical_json(payload) == canonical_json(expected), "D-140 envelope rebuild differs")
    _require(_pretty_bytes(payload) == raw, "D-140 artifact formatting differs")
    return body


def _read_json(root: Path, path: Path) -> tuple[dict[str, Any], bytes]:
    raw = _stable_read(root, path)
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D140SDKBlockedSuccessorError(f"D-140 invalid JSON: {path}") from exc
    _require(isinstance(value, dict), f"D-140 JSON root differs: {path}")
    return value, raw


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


def _single_artifact_commit(
    root: Path, *, commit: str, parent: str, path: Path, raw: bytes
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [parent], f"D-140 {path.name} parent differs")
    _require(
        _diff_rows(root, commit) == [{"status": "A", "path": path.as_posix()}],
        f"D-140 {path.name} commit scope differs",
    )
    oid, committed = _commit_blob(root, commit, path)
    _require(committed == raw, f"D-140 {path.name} committed bytes differ")
    return {
        **identity,
        "artifact_path": path.as_posix(),
        "artifact_blob_oid": oid,
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_file_bytes": len(raw),
        "single_artifact_add_commit": True,
    }


def _transition_commit(
    root: Path, *, commit: str, parent: str, started_raw: bytes, terminal_raw: bytes
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [parent], "D-140 transition parent differs")
    expected = sorted(
        [
            {"status": "A", "path": STARTED_PATH.as_posix()},
            {"status": "A", "path": TERMINAL_PATH.as_posix()},
        ],
        key=lambda row: row["path"],
    )
    _require(
        sorted(_diff_rows(root, commit), key=lambda row: row["path"]) == expected,
        "D-140 transition scope differs",
    )
    started_oid, committed_started = _commit_blob(root, commit, STARTED_PATH)
    terminal_oid, committed_terminal = _commit_blob(root, commit, TERMINAL_PATH)
    _require(
        committed_started == started_raw and committed_terminal == terminal_raw, "D-140 commit"
    )
    return {
        **identity,
        "artifact_paths": [STARTED_PATH.as_posix(), TERMINAL_PATH.as_posix()],
        "artifact_blob_oids": {
            STARTED_PATH.as_posix(): started_oid,
            TERMINAL_PATH.as_posix(): terminal_oid,
        },
        "exact_action_started_and_terminal_add_commit": True,
    }


def _pending_only(root: Path, paths: tuple[Path, ...], *, parent: str) -> bool:
    expected = sorted(f"?? {path.as_posix()}" for path in paths)
    return _head(root) == parent and sorted(_status_lines(root)) == expected


def _validate_d139_chain(root: Path) -> dict[str, Any]:
    source = _commit_identity(root, D139_SOURCE_COMMIT)
    _require(
        source
        == {
            "commit": D139_SOURCE_COMMIT,
            "tree": D139_SOURCE_TREE,
            "parents": [D139_SOURCE_PARENT],
        },
        "D-140 D-139 source identity differs",
    )
    _require(
        sorted(_diff_rows(root, D139_SOURCE_COMMIT), key=lambda row: row["path"])
        == sorted(
            [{"status": "A", "path": path.as_posix()} for path in D139_IMPLEMENTATION_PATHS],
            key=lambda row: row["path"],
        ),
        "D-140 D-139 source scope differs",
    )
    expected_commits = {
        D139_GATE_COMMIT: (D139_GATE_TREE, D139_SOURCE_COMMIT),
        D139_RECEIPT_COMMIT: (D139_RECEIPT_TREE, D139_GATE_COMMIT),
        D139_SDK_ATTEMPT_COMMIT: (D139_SDK_ATTEMPT_TREE, D139_RECEIPT_COMMIT),
        D139_SDK_TRANSITION_COMMIT: (D139_SDK_TRANSITION_TREE, D139_SDK_ATTEMPT_COMMIT),
    }
    for commit, (tree, parent) in expected_commits.items():
        _require(
            _commit_identity(root, commit) == {"commit": commit, "tree": tree, "parents": [parent]},
            f"D-140 D-139 commit topology differs: {commit}",
        )
    expected_diff_by_commit = {
        D139_GATE_COMMIT: sorted(
            [
                {"status": "A", "path": D139_GATE_PATH.as_posix()},
                *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
            ],
            key=lambda row: row["path"],
        ),
        D139_RECEIPT_COMMIT: [{"status": "A", "path": D139_RECEIPT_PATH.as_posix()}],
        D139_SDK_ATTEMPT_COMMIT: [{"status": "A", "path": D139_SDK_ATTEMPT_PATH.as_posix()}],
        D139_SDK_TRANSITION_COMMIT: sorted(
            [
                {"status": "A", "path": D139_SDK_STARTED_PATH.as_posix()},
                {"status": "A", "path": D139_SDK_TERMINAL_PATH.as_posix()},
            ],
            key=lambda row: row["path"],
        ),
    }
    bindings: dict[str, Any] = {}
    for path, artifact_id, body_sha, file_sha, size, blob, commit in _D139_ARTIFACTS:
        payload, raw = _read_json(root, path)
        _require(payload.get("gate_id", payload.get("artifact_id")) == artifact_id, "D-140 ID")
        _require(payload.get("semantic_body_hash") == body_sha, "D-140 body SHA")
        _require(len(raw) == size and sha256_bytes(raw) == file_sha, "D-140 artifact bytes")
        actual_blob, committed = _commit_blob(root, commit, path)
        _require(actual_blob == blob and committed == raw, "D-140 D-139 committed artifact differs")
        bindings[path.as_posix()] = {
            **_artifact_binding(path, payload, raw),
            "blob_oid": blob,
            "introduction_commit": commit,
        }
    for commit, expected in expected_diff_by_commit.items():
        actual = sorted(_diff_rows(root, commit), key=lambda row: row["path"])
        _require(actual == expected, f"D-140 D-139 commit scope differs: {commit}")
    terminal_payload, _terminal_raw = _read_json(root, D139_SDK_TERMINAL_PATH)
    terminal = terminal_payload["semantic_body"]
    observation = terminal.get("observation")
    _require(isinstance(observation, dict), "D-140 D-139 observation differs")
    inner = observation.get("observation")
    activity = observation.get("activity")
    _require(
        terminal.get("status") == "D139_SDK_NO_CALL_SUCCESSOR_BLOCKED_TRANSITION_COMMIT_REQUIRED"
        and observation.get("status") == "D139_SDK_NO_CALL_SUCCESSOR_OBSERVED_BLOCKED"
        and observation.get("passed") is False
        and isinstance(inner, dict)
        and inner.get("stage") == "presence"
        and inner.get("environment_presence_bits")
        == {"OPENAI_API_KEY": False, "PYTHONHOME": False, "PYTHONPATH": False}
        and inner.get("checks")
        == {
            "openai_api_key_present": False,
            "pythonhome_absent": True,
            "pythonpath_absent": True,
        }
        and inner.get("isolated_child") is None
        and inner.get("python") is None
        and inner.get("source_bindings") is None
        and observation.get("blockers")
        == [
            "openai-api-key-presence-bit-is-false",
            "isolated-sdk-worker-suppressed-by-presence-checks",
        ]
        and isinstance(activity, dict)
        and activity.get("environment_presence_check_count") == 3
        and activity.get("environment_value_read_count") == 0
        and activity.get("dotenv_read_count") == 0
        and activity.get("parent_sdk_dynamic_import_count") == 0
        and activity.get("parent_network_call_count") == 0
        and activity.get("child_process_start_count") == 0
        and activity.get("child_environment_entry_forward_count") == 0
        and activity.get("child_credential_value_forward_count") == 0
        and activity.get("provider_evaluator_or_agent_call_count") == 0,
        "D-140 D-139 terminal boundary differs",
    )
    return {
        "source_commit": source,
        "artifacts": bindings,
        "final_transition_commit": _commit_identity(root, D139_SDK_TRANSITION_COMMIT),
        "consumed": True,
        "retry_allowed": False,
        "credential_value_observation_count": 0,
        "environment_presence_check_count": 3,
        "dotenv_read_count": 0,
        "child_process_start_count": 0,
        "sdk_import_count": 0,
        "sdk_probe_count": 0,
        "transport_dispatch_count": 0,
        "network_call_count": 0,
    }


def _source_identity(root: Path, commit: str) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [D139_SDK_TRANSITION_COMMIT], "D-140 source parent differs")
    expected = sorted(
        [{"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS],
        key=lambda row: row["path"],
    )
    _require(
        sorted(_diff_rows(root, commit), key=lambda row: row["path"]) == expected,
        "D-140 source commit scope differs",
    )
    bindings: list[dict[str, Any]] = []
    for path in SOURCE_BINDING_PATHS:
        raw = _commit_blob(root, commit, path)[1]
        current = _stable_read(root, path)
        _require(raw == current, f"D-140 loaded source differs: {path}")
        binding = _file_binding(root, path)
        bindings.append(binding)
    _assert_runtime_import_boundary(root)
    return {
        **identity,
        "exact_four_path_add_commit": True,
        "source_bindings": bindings,
        "loaded_module_provenance_validated": True,
    }


def _runtime_committed_source_bindings(source: Any) -> dict[str, dict[str, Any]]:
    _require(isinstance(source, dict), "D-140 runtime source identity differs")
    rows = source.get("source_bindings")
    _require(isinstance(rows, list), "D-140 runtime source bindings differ")
    by_path: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict), "D-140 runtime source binding row differs")
        path = row.get("path")
        _require(isinstance(path, str) and path not in by_path, "D-140 duplicate source binding")
        by_path[path] = row
    expected: dict[str, dict[str, Any]] = {}
    for name, relative in RUNTIME_COMMITTED_SOURCE_PATHS.items():
        row = by_path.get(relative.as_posix())
        _require(
            isinstance(row, dict)
            and type(row.get("file_bytes")) is int
            and row["file_bytes"] > 0
            and isinstance(row.get("file_sha256"), str)
            and row.get("linklike") is False,
            f"D-140 committed {name} source binding differs",
        )
        expected[name] = {
            "repository_relative_path": relative.as_posix(),
            "file_bytes": row["file_bytes"],
            "file_sha256": row["file_sha256"],
            "linklike": False,
        }
    return expected


def _runtime_committed_source_bindings_from_receipt(root: Path) -> dict[str, dict[str, Any]]:
    receipt_payload, receipt_raw = _read_json(root, RECEIPT_PATH)
    receipt_body = _validate_receipt_payload(root, receipt_payload, receipt_raw)
    return _runtime_committed_source_bindings(receipt_body.get("source_identity"))


def _cross_validate_observation_source_bindings(
    observation: dict[str, Any], expected: Mapping[str, Mapping[str, Any]]
) -> None:
    try:
        no_call.validate_d140_sdk_no_call_successor_committed_source_bindings(observation, expected)
    except no_call.D140SDKNoCallSuccessorError as exc:
        raise D140SDKBlockedSuccessorError(
            "D-140 helper committed source cross-validation failed"
        ) from exc
    inner = observation.get("observation")
    _require(isinstance(inner, dict), "D-140 observation body differs")
    facts = inner.get("source_bindings")
    if facts is None:
        return
    _require(
        isinstance(facts, dict) and set(facts) == set(RUNTIME_COMMITTED_SOURCE_PATHS),
        "D-140 observation source binding names differ",
    )
    for name in RUNTIME_COMMITTED_SOURCE_PATHS:
        fact = facts.get(name)
        binding = expected.get(name)
        _require(
            isinstance(fact, dict)
            and isinstance(binding, Mapping)
            and fact.get("repository_relative_path") == binding.get("repository_relative_path")
            and fact.get("expected_committed_file_bytes") == binding.get("file_bytes")
            and fact.get("expected_committed_file_sha256") == binding.get("file_sha256")
            and fact.get("expected_committed_linklike") is False
            and binding.get("linklike") is False,
            f"D-140 observation committed {name} source binding differs",
        )
    child = inner.get("isolated_child")
    if child is None:
        return
    _require(isinstance(child, dict), "D-140 isolated child facts differ")
    worker = child.get("worker_observation")
    _require(isinstance(worker, dict), "D-140 isolated worker observation differs")
    worker_observation = worker.get("observation")
    _require(isinstance(worker_observation, dict), "D-140 isolated worker body differs")
    nested = worker_observation.get("committed_source_bindings")
    _require(
        isinstance(nested, dict) and set(nested) == set(RUNTIME_COMMITTED_SOURCE_PATHS),
        "D-140 isolated worker source binding names differ",
    )
    for name in RUNTIME_COMMITTED_SOURCE_PATHS:
        fact = nested.get(name)
        binding = expected.get(name)
        _require(
            isinstance(fact, dict)
            and isinstance(binding, Mapping)
            and fact.get("repository_relative_path") == binding.get("repository_relative_path")
            and fact.get("expected_committed_file_bytes") == binding.get("file_bytes")
            and fact.get("expected_committed_file_sha256") == binding.get("file_sha256")
            and fact.get("expected_committed_linklike") is False
            and binding.get("linklike") is False,
            f"D-140 isolated worker committed {name} source binding differs",
        )


def _gate_body(
    *,
    recorded_at: str,
    predecessor: dict[str, Any],
    source: dict[str, Any],
    git_cli: dict[str, Any],
) -> dict[str, Any]:
    terminal_binding = predecessor["artifacts"][D139_SDK_TERMINAL_PATH.as_posix()]
    _require(
        _parse_time(recorded_at, label="gate recorded_at")
        > _parse_time(terminal_binding["recorded_at"], label="D-139 SDK terminal recorded_at"),
        "D-140 gate chronology differs",
    )
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d139-sdk-blocked-no-call-successor-offline-source-gate",
        "recorded_at": recorded_at,
        "status": GATE_STATUS,
        "d139_sdk_blocked_predecessor": predecessor,
        "source_identity": source,
        "git_cli_observation": git_cli,
        "exact_launch_contract": no_call.EXACT_LAUNCH_CONTRACT,
        "launcher_source_contract": no_call.LAUNCHER_SOURCE_CONTRACT,
        "isolated_child_contract": no_call.ISOLATED_CHILD_CONTRACT,
        "credential_provisioning_boundary": CREDENTIAL_PROVISIONING_BOUNDARY,
        "source_preparation_scope": list(SOURCE_PREPARATION_SCOPE),
        "source_preparation_exclusions": list(SOURCE_PREPARATION_EXCLUSIONS),
        "future_activation_scope": list(ACTIVATION_SCOPE),
        "future_activation_exclusions": list(ACTIVATION_EXCLUSIONS),
        "authority": {
            "external_action_count": 0,
            "environment_or_credential_presence_observation_count": 0,
            "environment_or_credential_value_observation_count": 0,
            "environment_or_credential_mutation_count": 0,
            "dotenv_read_count": 0,
            "sdk_import_or_transport_dispatch_count": 0,
            "isolated_child_launch_count": 0,
            "network_or_docker_call_count": 0,
            "future_artifacts_created": False,
            "fresh_exact_activation_required": True,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
    }


def _validate_gate_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=GATE_SCHEMA, prefix="d140", gate=True)
    predecessor = _validate_d139_chain(root)
    source_value = body.get("source_identity")
    _require(isinstance(source_value, dict), "D-140 gate source differs")
    source = _source_identity(root, source_value.get("commit", ""))
    expected = _envelope(
        GATE_SCHEMA,
        "d140",
        _gate_body(
            recorded_at=body.get("recorded_at"),
            predecessor=predecessor,
            source=source,
            git_cli=_git_cli_observation(root),
        ),
        gate=True,
    )
    _require(canonical_json(payload) == canonical_json(expected), "D-140 gate rebuild differs")
    return body


def _gate_evidence_commit(
    root: Path, *, commit: str, source_commit: str, raw: bytes
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [source_commit], "D-140 gate commit parent differs")
    expected = sorted(
        [
            {"status": "A", "path": GATE_PATH.as_posix()},
            *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
        ],
        key=lambda row: row["path"],
    )
    _require(
        sorted(_diff_rows(root, commit), key=lambda row: row["path"]) == expected,
        "D-140 gate evidence scope differs",
    )
    oid, committed = _commit_blob(root, commit, GATE_PATH)
    _require(committed == raw, "D-140 committed gate differs")
    return {
        **identity,
        "artifact_path": GATE_PATH.as_posix(),
        "artifact_blob_oid": oid,
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_file_bytes": len(raw),
        "exact_gate_add_and_active_docs_modify_commit": True,
    }


def run_d140_offline_source_gate(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in FUTURE_PATHS:
        _path_absent(root, path)
    if os.path.lexists(root / GATE_PATH):
        mode: Literal["pending", "post-evidence-commit"] = (
            "post-evidence-commit" if _status_lines(root) == [] else "pending"
        )
        return validate_d140_offline_source_gate(repository=root, mode=mode)
    _require(_status_lines(root) == [], "D-140 gate requires clean source commit")
    source_commit = _head(root)
    predecessor = _validate_d139_chain(root)
    source = _source_identity(root, source_commit)
    git_cli = _git_cli_observation(root)
    payload = _envelope(
        GATE_SCHEMA,
        "d140",
        _gate_body(recorded_at=_now(), predecessor=predecessor, source=source, git_cli=git_cli),
        gate=True,
    )
    raw = _pretty_bytes(payload)

    def prepublish(temporary: Path, temporary_raw: bytes) -> None:
        _require(temporary_raw == raw, "D-140 gate temporary bytes drifted")
        _require(_head(root) == source_commit, "D-140 source HEAD drifted before gate publication")
        _require_prepublish_status(root, temporary=temporary, expected_without_temporary=())
        for path in FUTURE_PATHS:
            _path_absent(root, path)
        fresh_predecessor = _validate_d139_chain(root)
        fresh_source = _source_identity(root, source_commit)
        fresh_git = _git_cli_observation(root)
        _require(
            canonical_json(fresh_predecessor) == canonical_json(predecessor)
            and canonical_json(fresh_source) == canonical_json(source)
            and canonical_json(fresh_git) == canonical_json(git_cli),
            "D-140 source binding drifted before gate publication",
        )
        fresh_payload = _envelope(
            GATE_SCHEMA,
            "d140",
            _gate_body(
                recorded_at=payload["semantic_body"]["recorded_at"],
                predecessor=fresh_predecessor,
                source=fresh_source,
                git_cli=fresh_git,
            ),
            gate=True,
        )
        _require(
            canonical_json(fresh_payload) == canonical_json(payload),
            "D-140 gate changed before publication",
        )

    _write_new(root, GATE_PATH, raw, prepublish=prepublish)
    return validate_d140_offline_source_gate(repository=root, mode="pending")


def validate_d140_offline_source_gate(
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
    evidence = None
    if mode == "pending":
        _require(_pending_only(root, (GATE_PATH,), parent=source_commit), "D-140 pending gate")
    elif mode == "post-evidence-commit":
        _require(_status_lines(root) == [], "D-140 evidence checkout is not clean")
        evidence = _gate_evidence_commit(
            root, commit=_head(root), source_commit=source_commit, raw=raw
        )
    else:
        raise D140SDKBlockedSuccessorError("D-140 gate validation mode differs")
    return {
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "source_identity": body["source_identity"],
        "evidence_commit": evidence,
        "external_action_count": 0,
        "future_artifacts_created": False,
        "fresh_exact_activation_required": True,
    }


def _gate_for_activation(
    root: Path, *, evidence_commit: str | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, raw = _read_json(root, GATE_PATH)
    body = _validate_gate_payload(root, payload, raw)
    commit = evidence_commit or _head(root)
    evidence = _gate_evidence_commit(
        root, commit=commit, source_commit=body["source_identity"]["commit"], raw=raw
    )
    return (
        {**_artifact_binding(GATE_PATH, payload, raw), "evidence_commit_binding": evidence},
        body,
    )


def render_d140_external_activation_template(*, repository: str | Path | None = None) -> str:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    _require(_status_lines(root) == [], "D-140 activation template requires clean checkout")
    for path in FUTURE_PATHS:
        _path_absent(root, path)
    gate, body = _gate_for_activation(root)
    source = body["source_identity"]
    predecessor = body["d139_sdk_blocked_predecessor"]
    launch = (
        "& 'C:\\Users\\geonj\\Documents\\PatchLoop\\.venv\\Scripts\\python.exe' "
        "-E -s -B 'C:\\Users\\geonj\\Documents\\PatchLoop\\scripts\\"
        "build_d140_d139_sdk_blocked_successor_offline.py' --run-sdk-preflight"
    )
    return "\n".join(
        (
            "D-140 D-139 SDK-blocked fresh exact no-call successor activation approval",
            "(membership-only credential/routing bits then provenance and zero-dispatch probe)",
            "",
            f"Gate ID: {gate['artifact_id']}",
            f"Gate body SHA: {gate['semantic_body_hash']}",
            f"Gate file SHA: {gate['file_sha256']}",
            f"Gate file bytes: {gate['file_bytes']}",
            f"Gate evidence commit tuple: {canonical_json(gate['evidence_commit_binding'])}",
            f"Source commit: {source['commit']}",
            f"Source tree: {source['tree']}",
            "D-139 SDK transition commit tuple: "
            f"{canonical_json(predecessor['final_transition_commit'])}",
            f"Exact launch command: {launch}",
            f"Parent launcher source contract: {canonical_json(no_call.LAUNCHER_SOURCE_CONTRACT)}",
            f"Isolated child contract: {canonical_json(no_call.ISOLATED_CHILD_CONTRACT)}",
            f"Credential provisioning boundary: {canonical_json(CREDENTIAL_PROVISIONING_BOUNDARY)}",
            "",
            "Approved bounded scope:",
            *(f"- {item}" for item in ACTIVATION_SCOPE),
            "",
            "Explicitly not approved:",
            *(f"- {item}" for item in ACTIVATION_EXCLUSIONS),
            "",
            "The parent launch is required to inherit the ambient environment unchanged. Python",
            "-E ignores PYTHON* routing during startup; after the marker the parent observes only",
            "the three approved membership bits. Eligible SDK import/probe work runs in the",
            "bounded empty-environment child above with no ambient value forwarding.",
            "Credential provisioning is separate and is not authorized by this activation.",
            "Do not include any credential value in this approval or chat.",
            "A post-marker exception consumes D-140 and must never be retried.",
            "This rendered template is not approval; a new exact user message is required.",
        )
    )


def _receipt_body(
    *, recorded_at: str, gate: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    _require(
        _parse_time(recorded_at, label="receipt recorded_at")
        > _parse_time(gate["recorded_at"], label="gate recorded_at"),
        "D-140 receipt chronology differs",
    )
    return {
        "milestone": MILESTONE,
        "evidence_kind": "sdk-no-call-successor-activation-receipt",
        "recorded_at": recorded_at,
        "status": RECEIPT_STATUS,
        "source_gate_binding": gate,
        "source_identity": source,
        "activation_approval": {
            "exact_user_approval_recorded": True,
            "approval_is_self_attested": True,
            "approval_is_authenticated_or_signed": False,
            "approved_scope": list(ACTIVATION_SCOPE),
            "explicit_exclusions": list(ACTIVATION_EXCLUSIONS),
        },
        "exact_launch_contract": no_call.EXACT_LAUNCH_CONTRACT,
        "launcher_source_contract": no_call.LAUNCHER_SOURCE_CONTRACT,
        "isolated_child_contract": no_call.ISOLATED_CHILD_CONTRACT,
        "credential_provisioning_boundary": CREDENTIAL_PROVISIONING_BOUNDARY,
        "authority": {
            "sdk_helper_invocation_count": 0,
            "credential_or_environment_presence_observation_count": 0,
            "credential_or_environment_value_observation_count": 0,
            "credential_or_environment_mutation_count": 0,
            "sdk_import_or_transport_dispatch_count": 0,
            "network_call_count": 0,
            "cost_reserved_or_spent_usd": "0",
        },
    }


def _validate_receipt_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=RECEIPT_SCHEMA, prefix="d140approval")
    gate_value = body.get("source_gate_binding")
    _require(isinstance(gate_value, dict), "D-140 receipt gate differs")
    evidence = gate_value.get("evidence_commit_binding")
    _require(isinstance(evidence, dict), "D-140 receipt evidence differs")
    gate, gate_body = _gate_for_activation(root, evidence_commit=evidence.get("commit"))
    expected = _envelope(
        RECEIPT_SCHEMA,
        "d140approval",
        _receipt_body(
            recorded_at=body.get("recorded_at"),
            gate=gate,
            source=gate_body["source_identity"],
        ),
    )
    _require(canonical_json(payload) == canonical_json(expected), "D-140 receipt rebuild differs")
    return body


def create_d140_activation_receipt(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in FUTURE_PATHS[1:]:
        _path_absent(root, path)
    if os.path.lexists(root / RECEIPT_PATH):
        mode: Literal["pending", "post-commit"] = (
            "post-commit" if not _status_lines(root) else "pending"
        )
        return validate_d140_activation_receipt(repository=root, mode=mode)
    _require(_status_lines(root) == [], "D-140 receipt requires clean evidence commit")
    gate, body = _gate_for_activation(root)
    payload = _envelope(
        RECEIPT_SCHEMA,
        "d140approval",
        _receipt_body(recorded_at=_now(), gate=gate, source=body["source_identity"]),
    )
    raw = _pretty_bytes(payload)
    evidence_commit = gate["evidence_commit_binding"]["commit"]

    def prepublish(temporary: Path, temporary_raw: bytes) -> None:
        _require(temporary_raw == raw, "D-140 receipt temporary bytes drifted")
        _require(_head(root) == evidence_commit, "D-140 gate HEAD drifted before receipt")
        _require_prepublish_status(root, temporary=temporary, expected_without_temporary=())
        for path in FUTURE_PATHS[1:]:
            _path_absent(root, path)
        fresh_gate, fresh_gate_body = _gate_for_activation(root, evidence_commit=evidence_commit)
        _require(
            canonical_json(fresh_gate) == canonical_json(gate)
            and canonical_json(fresh_gate_body) == canonical_json(body),
            "D-140 gate binding drifted before receipt publication",
        )
        fresh_payload = _envelope(
            RECEIPT_SCHEMA,
            "d140approval",
            _receipt_body(
                recorded_at=payload["semantic_body"]["recorded_at"],
                gate=fresh_gate,
                source=fresh_gate_body["source_identity"],
            ),
        )
        _require(
            canonical_json(fresh_payload) == canonical_json(payload),
            "D-140 receipt changed before publication",
        )

    _write_new(root, RECEIPT_PATH, raw, prepublish=prepublish)
    return validate_d140_activation_receipt(repository=root, mode="pending")


def validate_d140_activation_receipt(
    *, repository: str | Path | None = None, mode: Literal["pending", "post-commit"] = "pending"
) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in FUTURE_PATHS[1:]:
        _path_absent(root, path)
    payload, raw = _read_json(root, RECEIPT_PATH)
    body = _validate_receipt_payload(root, payload, raw)
    parent = body["source_gate_binding"]["evidence_commit_binding"]["commit"]
    commit = None
    if mode == "pending":
        _require(_pending_only(root, (RECEIPT_PATH,), parent=parent), "D-140 pending receipt")
    elif mode == "post-commit":
        _require(_status_lines(root) == [], "D-140 receipt checkout is not clean")
        commit = _single_artifact_commit(
            root, commit=_head(root), parent=parent, path=RECEIPT_PATH, raw=raw
        )
    else:
        raise D140SDKBlockedSuccessorError("D-140 receipt mode differs")
    return {
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "receipt_commit": commit,
        "commit_required_before_attempt": commit is None,
        "external_action_count": 0,
    }


def _committed_receipt(root: Path, commit: str) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    payload, raw = _read_json(root, RECEIPT_PATH)
    body = _validate_receipt_payload(root, payload, raw)
    parent = body["source_gate_binding"]["evidence_commit_binding"]["commit"]
    binding = _single_artifact_commit(
        root, commit=commit, parent=parent, path=RECEIPT_PATH, raw=raw
    )
    return payload, raw, binding


def _attempt_body(
    *, recorded_at: str, receipt: dict[str, Any], parent: dict[str, Any], receipt_time: str
) -> dict[str, Any]:
    _require(
        _parse_time(recorded_at, label="attempt recorded_at")
        > _parse_time(receipt_time, label="receipt recorded_at"),
        "D-140 attempt chronology differs",
    )
    return {
        "milestone": MILESTONE,
        "evidence_kind": "sdk-no-call-successor-attempt-intent",
        "recorded_at": recorded_at,
        "status": ATTEMPT_STATUS,
        "activation_receipt_binding": receipt,
        "parent_commit_binding": parent,
        "exact_launch_contract": no_call.EXACT_LAUNCH_CONTRACT,
        "launcher_source_contract": no_call.LAUNCHER_SOURCE_CONTRACT,
        "isolated_child_contract": no_call.ISOLATED_CHILD_CONTRACT,
        "credential_provisioning_boundary": CREDENTIAL_PROVISIONING_BOUNDARY,
        "phase_contract": {
            "attempt_only_commit_required": True,
            "exact_inherited_environment_launch_required": True,
            "action_started_new_only_and_fsynced_before_first_membership_observation": True,
            "helper_invocation_limit": 1,
            "transport_retry_count": 0,
            "post_marker_exception_consumes_phase": True,
            "marker_only_preservation_commit_is_pre_authorized": True,
        },
        "authority": {
            "action_started_created": False,
            "sdk_helper_invocation_count": 0,
            "environment_presence_observation_count": 0,
            "environment_value_observation_count": 0,
            "credential_or_environment_mutation_count": 0,
            "sdk_import_or_transport_dispatch_count": 0,
            "network_call_count": 0,
        },
    }


def _validate_attempt_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=ATTEMPT_SCHEMA, prefix="d140sdkattempt")
    parent = body.get("parent_commit_binding")
    _require(isinstance(parent, dict), "D-140 attempt parent differs")
    receipt_payload, receipt_raw, receipt_commit = _committed_receipt(
        root, parent.get("commit", "")
    )
    receipt_body = receipt_payload["semantic_body"]
    expected = _envelope(
        ATTEMPT_SCHEMA,
        "d140sdkattempt",
        _attempt_body(
            recorded_at=body.get("recorded_at"),
            receipt=_artifact_binding(RECEIPT_PATH, receipt_payload, receipt_raw),
            parent=receipt_commit,
            receipt_time=receipt_body["recorded_at"],
        ),
    )
    _require(canonical_json(payload) == canonical_json(expected), "D-140 attempt rebuild differs")
    return body


def create_d140_sdk_attempt(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in (STARTED_PATH, TERMINAL_PATH):
        _path_absent(root, path)
    if os.path.lexists(root / ATTEMPT_PATH):
        mode: Literal["pending", "post-commit"] = (
            "post-commit" if not _status_lines(root) else "pending"
        )
        return validate_d140_sdk_attempt(repository=root, mode=mode)
    _require(_status_lines(root) == [], "D-140 attempt requires clean receipt commit")
    receipt_payload, receipt_raw, receipt_commit = _committed_receipt(root, _head(root))
    payload = _envelope(
        ATTEMPT_SCHEMA,
        "d140sdkattempt",
        _attempt_body(
            recorded_at=_now(),
            receipt=_artifact_binding(RECEIPT_PATH, receipt_payload, receipt_raw),
            parent=receipt_commit,
            receipt_time=receipt_payload["semantic_body"]["recorded_at"],
        ),
    )
    raw = _pretty_bytes(payload)
    receipt_commit_id = receipt_commit["commit"]

    def prepublish(temporary: Path, temporary_raw: bytes) -> None:
        _require(temporary_raw == raw, "D-140 attempt temporary bytes drifted")
        _require(_head(root) == receipt_commit_id, "D-140 receipt HEAD drifted before attempt")
        _require_prepublish_status(root, temporary=temporary, expected_without_temporary=())
        for path in (STARTED_PATH, TERMINAL_PATH):
            _path_absent(root, path)
        fresh_receipt_payload, fresh_receipt_raw, fresh_receipt_commit = _committed_receipt(
            root, receipt_commit_id
        )
        _require(
            fresh_receipt_raw == receipt_raw
            and canonical_json(fresh_receipt_payload) == canonical_json(receipt_payload)
            and canonical_json(fresh_receipt_commit) == canonical_json(receipt_commit),
            "D-140 receipt binding drifted before attempt publication",
        )
        fresh_payload = _envelope(
            ATTEMPT_SCHEMA,
            "d140sdkattempt",
            _attempt_body(
                recorded_at=payload["semantic_body"]["recorded_at"],
                receipt=_artifact_binding(RECEIPT_PATH, fresh_receipt_payload, fresh_receipt_raw),
                parent=fresh_receipt_commit,
                receipt_time=fresh_receipt_payload["semantic_body"]["recorded_at"],
            ),
        )
        _require(
            canonical_json(fresh_payload) == canonical_json(payload),
            "D-140 attempt changed before publication",
        )

    _write_new(root, ATTEMPT_PATH, raw, prepublish=prepublish)
    return validate_d140_sdk_attempt(repository=root, mode="pending")


def validate_d140_sdk_attempt(
    *, repository: str | Path | None = None, mode: Literal["pending", "post-commit"] = "pending"
) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    _path_absent(root, STARTED_PATH)
    _path_absent(root, TERMINAL_PATH)
    payload, raw = _read_json(root, ATTEMPT_PATH)
    body = _validate_attempt_payload(root, payload, raw)
    parent = body["parent_commit_binding"]["commit"]
    commit = None
    if mode == "pending":
        _require(_pending_only(root, (ATTEMPT_PATH,), parent=parent), "D-140 pending attempt")
    elif mode == "post-commit":
        _require(not _status_lines(root), "D-140 attempt checkout is not clean")
        commit = _single_artifact_commit(
            root, commit=_head(root), parent=parent, path=ATTEMPT_PATH, raw=raw
        )
    else:
        raise D140SDKBlockedSuccessorError("D-140 attempt mode differs")
    return {
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "attempt_commit": commit,
        "commit_required_before_observation": commit is None,
        "external_action_count": 0,
    }


def _started_body(
    *, recorded_at: str, attempt: dict[str, Any], parent: dict[str, Any]
) -> dict[str, Any]:
    _require(
        _parse_time(recorded_at, label="ACTION_STARTED recorded_at")
        > _parse_time(attempt["recorded_at"], label="attempt recorded_at"),
        "D-140 marker chronology differs",
    )
    return {
        "milestone": MILESTONE,
        "evidence_kind": "sdk-no-call-successor-action-started",
        "recorded_at": recorded_at,
        "status": STARTED_STATUS,
        "sdk_attempt_binding": attempt,
        "parent_commit_binding": parent,
        "exact_launch_contract": no_call.EXACT_LAUNCH_CONTRACT,
        "launcher_source_contract": no_call.LAUNCHER_SOURCE_CONTRACT,
        "isolated_child_contract": no_call.ISOLATED_CHILD_CONTRACT,
        "credential_provisioning_boundary": CREDENTIAL_PROVISIONING_BOUNDARY,
        "observation_contract": {
            "marker_is_new_only_durable_and_fsynced_before_first_membership_observation": True,
            "sdk_helper_invocation_limit": 1,
            "transport_retry_count": 0,
            "post_marker_exception_consumes_phase": True,
            "marker_only_preservation_commit_is_pre_authorized": True,
        },
        "authority": {
            "sdk_helper_invocation_count_at_marker_write": 0,
            "credential_or_environment_presence_observation_count_at_marker_write": 0,
            "credential_or_environment_value_observation_count": 0,
            "credential_or_environment_mutation_count": 0,
            "sdk_import_or_transport_dispatch_count_at_marker_write": 0,
            "terminal_created_at_marker_write": False,
            "network_call_count": 0,
        },
    }


def _validate_started_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=STARTED_SCHEMA, prefix="d140sdkstarted")
    attempt_payload, attempt_raw = _read_json(root, ATTEMPT_PATH)
    attempt_body = _validate_attempt_payload(root, attempt_payload, attempt_raw)
    parent = body.get("parent_commit_binding")
    _require(isinstance(parent, dict), "D-140 marker parent differs")
    attempt_commit = _single_artifact_commit(
        root,
        commit=parent.get("commit", ""),
        parent=attempt_body["parent_commit_binding"]["commit"],
        path=ATTEMPT_PATH,
        raw=attempt_raw,
    )
    expected = _envelope(
        STARTED_SCHEMA,
        "d140sdkstarted",
        _started_body(
            recorded_at=body.get("recorded_at"),
            attempt=_artifact_binding(ATTEMPT_PATH, attempt_payload, attempt_raw),
            parent=attempt_commit,
        ),
    )
    _require(canonical_json(payload) == canonical_json(expected), "D-140 marker rebuild differs")
    return body


def validate_d140_sdk_action_started(
    *,
    repository: str | Path | None = None,
    mode: Literal["pending-marker", "post-preservation-commit"] = "pending-marker",
) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    _path_absent(root, TERMINAL_PATH)
    payload, raw = _read_json(root, STARTED_PATH)
    body = _validate_started_payload(root, payload, raw)
    parent = body["parent_commit_binding"]["commit"]
    commit = None
    if mode == "pending-marker":
        _require(_pending_only(root, (STARTED_PATH,), parent=parent), "D-140 pending marker")
    elif mode == "post-preservation-commit":
        _require(not _status_lines(root), "D-140 preservation checkout is not clean")
        commit = _single_artifact_commit(
            root, commit=_head(root), parent=parent, path=STARTED_PATH, raw=raw
        )
    else:
        raise D140SDKBlockedSuccessorError("D-140 marker mode differs")
    return {
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "marker_preservation_commit": commit,
        "phase_consumed": True,
        "retry_allowed": False,
    }


def _terminal_body(
    *,
    recorded_at: str,
    started: dict[str, Any],
    parent: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    _require(
        _parse_time(recorded_at, label="terminal recorded_at")
        > _parse_time(started["recorded_at"], label="marker recorded_at"),
        "D-140 terminal chronology differs",
    )
    ready = observation["passed"] is True
    return {
        "milestone": MILESTONE,
        "evidence_kind": "sdk-no-call-successor-terminal",
        "recorded_at": recorded_at,
        "status": TERMINAL_READY_STATUS if ready else TERMINAL_BLOCKED_STATUS,
        "action_started_binding": started,
        "parent_commit_binding": parent,
        "observation": observation,
        "credential_provisioning_boundary": CREDENTIAL_PROVISIONING_BOUNDARY,
        "activity_accounting": observation["activity"],
        "evidence_boundary": {
            "observation_is_replay_validated": True,
            "observation_expected_committed_source_bindings_cross_validated": True,
            "ready_or_blocked_is_terminal": True,
            "post_marker_retry_resume_repair_or_backfill_allowed": False,
            "credential_or_environment_values_persisted": False,
            "credential_or_environment_mutation_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
        "authority": {
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
        "next_gate": {
            "status": (
                "D141_READY_SDK_NO_CALL_OFFLINE_SUCCESSOR_APPROVAL_REQUIRED"
                if ready
                else "D141_SDK_BLOCKED_OFFLINE_SUCCESSOR_APPROVAL_REQUIRED"
            ),
            "fresh_separate_approval_required": True,
            "current_activation_authorizes_execution_hash_candidate_cost_or_ac": False,
        },
    }


def _validate_terminal_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=TERMINAL_SCHEMA, prefix="d140sdk")
    started_payload, started_raw = _read_json(root, STARTED_PATH)
    started_body = _validate_started_payload(root, started_payload, started_raw)
    try:
        observation = no_call.validate_d140_sdk_no_call_successor_observation(
            body.get("observation")
        )
    except (no_call.D140SDKNoCallSuccessorError, ContractError, TypeError, ValueError) as exc:
        raise D140SDKBlockedSuccessorError("D-140 observation validation failed") from exc
    expected_source_bindings = _runtime_committed_source_bindings_from_receipt(root)
    _cross_validate_observation_source_bindings(observation, expected_source_bindings)
    expected = _envelope(
        TERMINAL_SCHEMA,
        "d140sdk",
        _terminal_body(
            recorded_at=body.get("recorded_at"),
            started=_artifact_binding(STARTED_PATH, started_payload, started_raw),
            parent=started_body["parent_commit_binding"],
            observation=observation,
        ),
    )
    _require(canonical_json(payload) == canonical_json(expected), "D-140 terminal rebuild differs")
    return body


def run_d140_sdk_no_call_successor(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    if os.path.lexists(root / TERMINAL_PATH) and not os.path.lexists(root / STARTED_PATH):
        raise D140SDKBlockedSuccessorError("D-140 terminal is orphaned")
    if os.path.lexists(root / STARTED_PATH):
        started_payload, started_raw = _read_json(root, STARTED_PATH)
        _validate_started_payload(root, started_payload, started_raw)
        if os.path.lexists(root / TERMINAL_PATH):
            mode: Literal["pending", "post-transition-commit"] = (
                "post-transition-commit" if not _status_lines(root) else "pending"
            )
            return validate_d140_sdk_terminal(repository=root, mode=mode)
        raise D140SDKBlockedSuccessorError(
            "D-140 ACTION_STARTED has no terminal; phase is consumed and retry is forbidden"
        )
    launch = no_call.current_d140_sdk_launch_contract()
    no_call.validate_d140_sdk_launch_contract(launch)
    attempt_payload, attempt_raw = _read_json(root, ATTEMPT_PATH)
    attempt_body = _validate_attempt_payload(root, attempt_payload, attempt_raw)
    expected_source_bindings = _runtime_committed_source_bindings_from_receipt(root)
    _require(not _status_lines(root), "D-140 run requires clean committed attempt")
    attempt_commit = _single_artifact_commit(
        root,
        commit=_head(root),
        parent=attempt_body["parent_commit_binding"]["commit"],
        path=ATTEMPT_PATH,
        raw=attempt_raw,
    )
    started = _envelope(
        STARTED_SCHEMA,
        "d140sdkstarted",
        _started_body(
            recorded_at=_now(),
            attempt=_artifact_binding(ATTEMPT_PATH, attempt_payload, attempt_raw),
            parent=attempt_commit,
        ),
    )
    started_raw = _pretty_bytes(started)

    def marker_prepublish(temporary: Path, temporary_raw: bytes) -> None:
        _require(temporary_raw == started_raw, "D-140 marker temporary bytes drifted")
        _require(
            _head(root) == attempt_commit["commit"],
            "D-140 attempt HEAD drifted before marker",
        )
        _require_prepublish_status(root, temporary=temporary, expected_without_temporary=())
        _path_absent(root, TERMINAL_PATH)
        fresh_attempt_payload, fresh_attempt_raw = _read_json(root, ATTEMPT_PATH)
        fresh_attempt_body = _validate_attempt_payload(
            root, fresh_attempt_payload, fresh_attempt_raw
        )
        fresh_attempt_commit = _single_artifact_commit(
            root,
            commit=attempt_commit["commit"],
            parent=fresh_attempt_body["parent_commit_binding"]["commit"],
            path=ATTEMPT_PATH,
            raw=fresh_attempt_raw,
        )
        _require(
            fresh_attempt_raw == attempt_raw
            and canonical_json(fresh_attempt_payload) == canonical_json(attempt_payload)
            and canonical_json(fresh_attempt_commit) == canonical_json(attempt_commit),
            "D-140 attempt binding drifted before marker publication",
        )
        fresh_started = _envelope(
            STARTED_SCHEMA,
            "d140sdkstarted",
            _started_body(
                recorded_at=started["semantic_body"]["recorded_at"],
                attempt=_artifact_binding(ATTEMPT_PATH, fresh_attempt_payload, fresh_attempt_raw),
                parent=fresh_attempt_commit,
            ),
        )
        _require(
            canonical_json(fresh_started) == canonical_json(started),
            "D-140 marker changed before publication",
        )

    _write_new(root, STARTED_PATH, started_raw, prepublish=marker_prepublish)
    stored_started, stored_started_raw = _read_json(root, STARTED_PATH)
    _validate_started_payload(root, stored_started, stored_started_raw)
    _require(
        stored_started_raw == started_raw
        and _pending_only(root, (STARTED_PATH,), parent=attempt_commit["commit"]),
        "D-140 marker durability differs",
    )
    try:
        observation = no_call.run_d140_sdk_no_call_successor_observation(
            repository=root,
            expected_committed_source_bindings=expected_source_bindings,
        )
        observation = no_call.validate_d140_sdk_no_call_successor_observation(observation)
        _cross_validate_observation_source_bindings(observation, expected_source_bindings)
    except Exception as exc:
        raise D140SDKBlockedSuccessorError(
            "D-140 observation failed after ACTION_STARTED; phase is consumed"
        ) from exc
    fresh_attempt, fresh_attempt_raw = _read_json(root, ATTEMPT_PATH)
    _validate_attempt_payload(root, fresh_attempt, fresh_attempt_raw)
    fresh_started, fresh_started_raw = _read_json(root, STARTED_PATH)
    _validate_started_payload(root, fresh_started, fresh_started_raw)
    _require(
        fresh_attempt_raw == attempt_raw
        and fresh_started_raw == started_raw
        and _pending_only(root, (STARTED_PATH,), parent=attempt_commit["commit"]),
        "D-140 checkout drifted after helper",
    )
    terminal = _envelope(
        TERMINAL_SCHEMA,
        "d140sdk",
        _terminal_body(
            recorded_at=_now(),
            started=_artifact_binding(STARTED_PATH, fresh_started, fresh_started_raw),
            parent=attempt_commit,
            observation=observation,
        ),
    )
    terminal_raw = _pretty_bytes(terminal)

    def terminal_prepublish(temporary: Path, temporary_raw: bytes) -> None:
        _require(temporary_raw == terminal_raw, "D-140 terminal temporary bytes drifted")
        _require(
            _head(root) == attempt_commit["commit"],
            "D-140 attempt HEAD drifted before terminal",
        )
        _require_prepublish_status(
            root,
            temporary=temporary,
            expected_without_temporary=(f"?? {STARTED_PATH.as_posix()}",),
        )
        fresh_attempt_payload, fresh_attempt_raw = _read_json(root, ATTEMPT_PATH)
        fresh_attempt_body = _validate_attempt_payload(
            root, fresh_attempt_payload, fresh_attempt_raw
        )
        fresh_attempt_commit = _single_artifact_commit(
            root,
            commit=attempt_commit["commit"],
            parent=fresh_attempt_body["parent_commit_binding"]["commit"],
            path=ATTEMPT_PATH,
            raw=fresh_attempt_raw,
        )
        latest_started, latest_started_raw = _read_json(root, STARTED_PATH)
        _validate_started_payload(root, latest_started, latest_started_raw)
        _require(
            fresh_attempt_raw == attempt_raw
            and canonical_json(fresh_attempt_payload) == canonical_json(attempt_payload)
            and canonical_json(fresh_attempt_commit) == canonical_json(attempt_commit)
            and latest_started_raw == started_raw
            and canonical_json(latest_started) == canonical_json(stored_started),
            "D-140 predecessor drifted before terminal publication",
        )
        rebuilt_observation = no_call.validate_d140_sdk_no_call_successor_observation(observation)
        fresh_expected_source_bindings = _runtime_committed_source_bindings_from_receipt(root)
        _require(
            canonical_json(fresh_expected_source_bindings)
            == canonical_json(expected_source_bindings),
            "D-140 committed source bindings drifted before terminal publication",
        )
        _cross_validate_observation_source_bindings(
            rebuilt_observation, fresh_expected_source_bindings
        )
        fresh_terminal = _envelope(
            TERMINAL_SCHEMA,
            "d140sdk",
            _terminal_body(
                recorded_at=terminal["semantic_body"]["recorded_at"],
                started=_artifact_binding(STARTED_PATH, latest_started, latest_started_raw),
                parent=fresh_attempt_commit,
                observation=rebuilt_observation,
            ),
        )
        _require(
            canonical_json(fresh_terminal) == canonical_json(terminal),
            "D-140 terminal changed before publication",
        )

    _write_new(root, TERMINAL_PATH, terminal_raw, prepublish=terminal_prepublish)
    return validate_d140_sdk_terminal(repository=root, mode="pending")


def validate_d140_sdk_terminal(
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
    parent = started_body["parent_commit_binding"]["commit"]
    transition = None
    if mode == "pending":
        _require(
            _pending_only(root, (STARTED_PATH, TERMINAL_PATH), parent=parent),
            "D-140 pending transition differs",
        )
    elif mode == "post-transition-commit":
        _require(not _status_lines(root), "D-140 transition checkout is not clean")
        transition = _transition_commit(
            root,
            commit=_head(root),
            parent=parent,
            started_raw=started_raw,
            terminal_raw=raw,
        )
    else:
        raise D140SDKBlockedSuccessorError("D-140 terminal mode differs")
    return {
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


__all__ = [
    "ACTIVE_DOC_PATHS",
    "ACTIVATION_EXCLUSIONS",
    "ACTIVATION_SCOPE",
    "ATTEMPT_PATH",
    "CREDENTIAL_PROVISIONING_BOUNDARY",
    "D139_SDK_TRANSITION_COMMIT",
    "D140SDKBlockedSuccessorError",
    "FUTURE_PATHS",
    "GATE_PATH",
    "GATE_STATUS",
    "IMPLEMENTATION_PATHS",
    "RECEIPT_PATH",
    "SOURCE_PREPARATION_EXCLUSIONS",
    "SOURCE_PREPARATION_SCOPE",
    "STARTED_PATH",
    "TERMINAL_PATH",
    "create_d140_activation_receipt",
    "create_d140_sdk_attempt",
    "render_d140_external_activation_template",
    "run_d140_offline_source_gate",
    "run_d140_sdk_no_call_successor",
    "validate_d140_activation_receipt",
    "validate_d140_offline_source_gate",
    "validate_d140_sdk_action_started",
    "validate_d140_sdk_attempt",
    "validate_d140_sdk_terminal",
]
