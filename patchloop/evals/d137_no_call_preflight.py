"""Prospective D-137 Docker and SDK no-call preflight helpers.

Importing this module performs no Docker, SDK, environment, credential, or
network observation.  The two public runners are deliberately separate so a
future orchestrator can durably record the phase ACTION_STARTED marker before
calling exactly one helper.  Every external boundary is injectable for focused
offline tests.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, BinaryIO, Protocol

from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes

MILESTONE = "D-137"
DOCKER_PHASE = "docker"
SDK_PHASE = "sdk"

DOCKER_OBSERVATION_SCHEMA = "d137-d136-docker-no-call-preflight-observation-v1"
SDK_OBSERVATION_SCHEMA = "d137-d136-sdk-no-call-preflight-observation-v1"

DOCKER_READY_STATUS = "D137_DOCKER_NO_CALL_PREFLIGHT_READY_SDK_PHASE_BLOCKED"
DOCKER_BLOCKED_STATUS = "D137_DOCKER_NO_CALL_PREFLIGHT_OBSERVED_BLOCKED"
SDK_READY_STATUS = "D137_SDK_NO_CALL_PREFLIGHT_READY_OFFLINE_SUCCESSOR_REQUIRED"
SDK_BLOCKED_STATUS = "D137_SDK_NO_CALL_PREFLIGHT_OBSERVED_BLOCKED"

LOCAL_DOCKER_ENDPOINT = "npipe:////./pipe/dockerDesktopLinuxEngine"
APPROVED_DOCKER_CLI_PATH = Path(
    r"C:\Users\geonj\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
)
D137_FIXED_TEMP_ROOT = Path(r"C:\Users\geonj\AppData\Local\Temp")
APPROVED_DOCKER_CLI_VERSION = "29.6.2"
APPROVED_DOCKER_CLI_BUILD = "dfc4efb"
APPROVED_DOCKER_CLI_FILE_BYTES = 43_095_472
APPROVED_DOCKER_CLI_FILE_SHA256 = (
    "sha256:8985cd8ac002c3240b5aa48fe401fcb55dca5d849b537e3c835564e8e8c49a70"
)
EXACT_DOCKER_IMAGES = (
    "docker.io/swerebenchv2/getmoto-moto@"
    "sha256:dfdf957ab30b8829e8b6bbfd693b00fab88b7979d3c856362fd5d66c489a1fee",
    "docker.io/swerebenchv2/python-babel-babel@"
    "sha256:864e84fc4bdf09252f7fda4f85665cc05155a7b1d75847d61c67325abce7ef5a",
)
DOCKER_VERSION_FORMAT = (
    '{"ClientVersion":{{json .Client.Version}},'
    '"ServerVersion":{{json .Server.Version}},'
    '"ServerOs":{{json .Server.Os}},'
    '"ServerArch":{{json .Server.Arch}}}'
)
DOCKER_IMAGE_FORMAT = '{"Id":{{json .Id}},"RepoDigests":{{json .RepoDigests}}}'
DOCKER_CONTAINER_FORMAT = "{{.ID}}"
MAX_DOCKER_OUTPUT_BYTES = 64 * 1024
DOCKER_COMMAND_TIMEOUT_SECONDS = 30

OFFICIAL_API_BASE_URL = "https://api.openai.com/v1"
SDK_ENVIRONMENT_NAMES = ("OPENAI_API_KEY", "PYTHONHOME", "PYTHONPATH")

_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")
_REPO_DIGEST = re.compile(r"[^\x00-\x20\x7f]+@sha256:[0-9a-f]{64}")
_DAEMON_VERSION = re.compile(r"[0-9]+(?:\.[0-9]+){1,3}(?:[-+][0-9A-Za-z.-]+)?")
_CONTAINER_ID = re.compile(r"[0-9a-f]{64}")

_DOCKER_ROOT_KEYS = (
    "schema_version",
    "phase",
    "status",
    "observer_contract",
    "observation",
    "blockers",
    "activity",
    "passed",
)
_SDK_ROOT_KEYS = _DOCKER_ROOT_KEYS

_DOCKER_COMMANDS = (
    ("daemon-version", ("version", "--format", DOCKER_VERSION_FORMAT)),
    (
        "image-moto",
        ("image", "inspect", "--format", DOCKER_IMAGE_FORMAT, EXACT_DOCKER_IMAGES[0]),
    ),
    (
        "image-babel",
        ("image", "inspect", "--format", DOCKER_IMAGE_FORMAT, EXACT_DOCKER_IMAGES[1]),
    ),
    (
        "container-inventory",
        ("container", "ls", "--all", "--no-trunc", "--format", DOCKER_CONTAINER_FORMAT),
    ),
)


class D137NoCallPreflightError(ContractError):
    """Raised when a D-137 prospective observation fails closed."""


@dataclass(frozen=True)
class BoundedCommandResult:
    """Bounded in-memory command result; raw bytes never enter an artifact."""

    return_code: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    stdout_bytes: int | None = None
    stderr_bytes: int | None = None
    stdout_sha256: str | None = None
    stderr_sha256: str | None = None


class DockerCommandRunner(Protocol):
    def __call__(
        self,
        argv: Sequence[str],
        *,
        environment: Mapping[str, str],
        timeout_seconds: int,
        max_output_bytes: int,
    ) -> BoundedCommandResult: ...


FileBindingReader = Callable[[Path], dict[str, Any]]


@dataclass(frozen=True)
class DockerObservationDependencies:
    cli_path: Path
    cli_binding: FileBindingReader
    command_runner: DockerCommandRunner
    child_environment: Mapping[str, str]


@dataclass(frozen=True)
class SDKObservationDependencies:
    python_executable: Path
    python_version: str
    file_binding: FileBindingReader
    distribution_version: Callable[[str], str | None]
    find_module_spec: Callable[[str], Any]
    import_module: Callable[[str], ModuleType]
    environment_present: Callable[[str], bool]


@dataclass(frozen=True)
class _ResolvedModuleOrigin:
    name: str
    path: Path | None
    repository_relative_path: str | None
    safe_repository_venv_origin: bool
    find_module_spec_performed: bool


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D137NoCallPreflightError(message)


def _repo_root(repository: str | Path | None) -> Path:
    root = Path(__file__).resolve().parents[2] if repository is None else Path(repository)
    return root.resolve(strict=True)


def _stable_read(path: Path) -> bytes:
    before = path.stat()
    payload = path.read_bytes()
    after = path.stat()
    _require(
        (before.st_size, before.st_mtime_ns, before.st_ino)
        == (after.st_size, after.st_mtime_ns, after.st_ino),
        f"D-137 file changed during read: {path.name}",
    )
    return payload


def _file_binding(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    metadata = path.lstat()
    linklike = stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & 0x400
    )
    _require(not linklike, f"D-137 link-like file is forbidden: {path.name}")
    payload = _stable_read(resolved)
    return {
        "file_name": resolved.name,
        "file_bytes": len(payload),
        "file_sha256": sha256_bytes(payload),
        "linklike": False,
    }


@dataclass
class _BoundedStream:
    limit: int
    prefix: bytearray
    digest: Any | None
    total: int = 0

    @classmethod
    def create(cls, limit: int, *, hash_output: bool) -> _BoundedStream:
        return cls(
            limit=limit,
            prefix=bytearray(),
            digest=hashlib.sha256() if hash_output else None,
        )

    def consume(self, stream: BinaryIO) -> None:
        while chunk := stream.read(8192):
            self.total += len(chunk)
            if self.digest is not None:
                self.digest.update(chunk)
            remaining = self.limit - len(self.prefix)
            if remaining > 0:
                self.prefix.extend(chunk[:remaining])


def _run_bounded_command(
    argv: Sequence[str],
    *,
    environment: Mapping[str, str],
    timeout_seconds: int,
    max_output_bytes: int,
) -> BoundedCommandResult:
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(  # noqa: S603
        list(argv),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(environment),
        shell=False,
        creationflags=creationflags,
    )
    _require(process.stdout is not None and process.stderr is not None, "D-137 pipes missing")
    inventory = tuple(argv[1:]) == _DOCKER_COMMANDS[-1][1]
    stdout = _BoundedStream.create(max_output_bytes, hash_output=not inventory)
    stderr = _BoundedStream.create(max_output_bytes, hash_output=not inventory)
    stdout_thread = threading.Thread(target=stdout.consume, args=(process.stdout,), daemon=True)
    stderr_thread = threading.Thread(target=stderr.consume, args=(process.stderr,), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    timed_out = False
    try:
        return_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        return_code = process.wait()
    stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=5)
    _require(
        not stdout_thread.is_alive() and not stderr_thread.is_alive(),
        "D-137 bounded output readers did not settle",
    )
    return BoundedCommandResult(
        return_code=return_code,
        timed_out=timed_out,
        stdout=bytes(stdout.prefix),
        stderr=bytes(stderr.prefix),
        stdout_bytes=stdout.total,
        stderr_bytes=stderr.total,
        stdout_sha256=(None if stdout.digest is None else "sha256:" + stdout.digest.hexdigest()),
        stderr_sha256=(None if stderr.digest is None else "sha256:" + stderr.digest.hexdigest()),
    )


@contextmanager
def _default_docker_dependencies() -> Iterator[DockerObservationDependencies]:
    # This wholly literal child environment cannot inherit PATH, credentials,
    # proxy settings, Docker contexts, or any parent value.
    temp_root = D137_FIXED_TEMP_ROOT.resolve(strict=True)
    temp_metadata = D137_FIXED_TEMP_ROOT.lstat()
    _require(
        temp_root.is_dir()
        and not stat.S_ISLNK(temp_metadata.st_mode)
        and not bool(getattr(temp_metadata, "st_file_attributes", 0) & 0x400),
        "D-137 fixed temporary root is unavailable or link-like",
    )
    with tempfile.TemporaryDirectory(
        prefix="patchloop-d137-docker-",
        dir=temp_root,
    ) as docker_config:
        yield DockerObservationDependencies(
            cli_path=APPROVED_DOCKER_CLI_PATH,
            cli_binding=_file_binding,
            command_runner=_run_bounded_command,
            child_environment={
                "DOCKER_CONFIG": docker_config,
                "DOCKER_HOST": LOCAL_DOCKER_ENDPOINT,
            },
        )


def _default_sdk_dependencies() -> SDKObservationDependencies:
    def distribution_version(name: str) -> str | None:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return None

    def environment_present(name: str) -> bool:
        _require(name in SDK_ENVIRONMENT_NAMES, "D-137 unexpected environment-presence name")
        return name in os.environ

    return SDKObservationDependencies(
        python_executable=Path(sys.executable),
        python_version=".".join(str(value) for value in sys.version_info[:3]),
        file_binding=_file_binding,
        distribution_version=distribution_version,
        find_module_spec=importlib.util.find_spec,
        import_module=importlib.import_module,
        environment_present=environment_present,
    )


def _exact_cli_binding(value: Any) -> None:
    _require(isinstance(value, dict), "D-137 Docker CLI binding is not an object")
    _require(
        tuple(value) == ("file_name", "file_bytes", "file_sha256", "linklike"),
        "D-137 Docker CLI binding fields differ",
    )
    _require(value["file_name"].casefold() == "docker.exe", "D-137 Docker CLI name differs")
    _require(
        value["file_bytes"] == APPROVED_DOCKER_CLI_FILE_BYTES,
        "D-137 Docker CLI bytes differ",
    )
    _require(
        value["file_sha256"] == APPROVED_DOCKER_CLI_FILE_SHA256,
        "D-137 Docker CLI SHA differs",
    )
    _require(value["linklike"] is False, "D-137 Docker CLI is link-like")


def _normalized_result(result: BoundedCommandResult, *, inventory: bool) -> dict[str, Any]:
    stdout_bytes = len(result.stdout) if result.stdout_bytes is None else result.stdout_bytes
    stderr_bytes = len(result.stderr) if result.stderr_bytes is None else result.stderr_bytes
    _require(type(stdout_bytes) is int and stdout_bytes >= len(result.stdout), "D-137 stdout size")
    _require(type(stderr_bytes) is int and stderr_bytes >= len(result.stderr), "D-137 stderr size")
    stdout_sha256: str | None = None
    stderr_sha256: str | None = None
    if not inventory:
        stdout_sha256 = result.stdout_sha256 or sha256_bytes(result.stdout)
        stderr_sha256 = result.stderr_sha256 or sha256_bytes(result.stderr)
        _require(_SHA256.fullmatch(stdout_sha256) is not None, "D-137 stdout SHA differs")
        _require(_SHA256.fullmatch(stderr_sha256) is not None, "D-137 stderr SHA differs")
        if stdout_bytes == len(result.stdout):
            _require(stdout_sha256 == sha256_bytes(result.stdout), "D-137 stdout digest mismatch")
        if stderr_bytes == len(result.stderr):
            _require(stderr_sha256 == sha256_bytes(result.stderr), "D-137 stderr digest mismatch")
    output_within_bound = (
        stdout_bytes <= MAX_DOCKER_OUTPUT_BYTES and stderr_bytes <= MAX_DOCKER_OUTPUT_BYTES
    )
    if output_within_bound:
        _require(
            stdout_bytes == len(result.stdout) and stderr_bytes == len(result.stderr),
            "D-137 bounded output bytes are incomplete",
        )
    return {
        "return_code": result.return_code,
        "timed_out": result.timed_out,
        "stdout_bytes": None if inventory else stdout_bytes,
        "stdout_sha256": None if inventory else stdout_sha256,
        "stderr_bytes": None if inventory else stderr_bytes,
        "stderr_sha256": None if inventory else stderr_sha256,
        "stdout_zero": not bool(result.stdout),
        "stderr_zero": not bool(result.stderr),
        "output_within_bound": output_within_bound,
        "raw_stdout_or_stderr_persisted": False,
    }


def _command_succeeded(facts: Mapping[str, Any]) -> bool:
    return (
        facts["return_code"] == 0
        and facts["timed_out"] is False
        and facts["output_within_bound"] is True
        and facts["stderr_zero"] is True
    )


def _json_projection(result: BoundedCommandResult, facts: Mapping[str, Any]) -> Any:
    if not _command_succeeded(facts):
        return None
    try:
        return json.loads(result.stdout.decode("utf-8").rstrip("\r\n"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _daemon_projection(
    result: BoundedCommandResult,
    facts: Mapping[str, Any],
) -> dict[str, str] | None:
    value = _json_projection(result, facts)
    if not isinstance(value, dict) or tuple(value) != (
        "ClientVersion",
        "ServerVersion",
        "ServerOs",
        "ServerArch",
    ):
        return None
    if (
        value["ClientVersion"] != APPROVED_DOCKER_CLI_VERSION
        or not isinstance(value["ServerVersion"], str)
        or _DAEMON_VERSION.fullmatch(value["ServerVersion"]) is None
        or value["ServerOs"] != "linux"
        or value["ServerArch"] != "amd64"
    ):
        return None
    return value


def _repo_aliases(requested: str) -> frozenset[str]:
    aliases = {requested}
    if requested.startswith("docker.io/"):
        aliases.add(requested.removeprefix("docker.io/"))
    return frozenset(aliases)


def _image_projection(
    result: BoundedCommandResult,
    facts: Mapping[str, Any],
    requested: str,
) -> dict[str, Any] | None:
    value = _json_projection(result, facts)
    if not isinstance(value, dict) or tuple(value) != ("Id", "RepoDigests"):
        return None
    config_id = value["Id"]
    repo_digests = value["RepoDigests"]
    if (
        not isinstance(config_id, str)
        or _IMAGE_ID.fullmatch(config_id) is None
        or not isinstance(repo_digests, list)
        or len(repo_digests) > 128
        or len(repo_digests) != len(set(repo_digests))
        or not all(
            isinstance(item, str)
            and len(item.encode("utf-8")) <= 512
            and _REPO_DIGEST.fullmatch(item) is not None
            for item in repo_digests
        )
    ):
        return None
    matches = sorted(set(repo_digests).intersection(_repo_aliases(requested)))
    if len(matches) != 1:
        return None
    return {
        "requested_repo_digest": requested,
        "requested_digest": requested.rsplit("@", 1)[1],
        "config_id": config_id,
        "repo_digests": sorted(repo_digests),
        "matched_repo_digest": matches[0],
    }


def _zero_container_inventory(
    result: BoundedCommandResult,
    facts: Mapping[str, Any],
) -> dict[str, bool]:
    valid = _command_succeeded(facts)
    if valid and result.stdout:
        try:
            lines = result.stdout.decode("ascii").splitlines()
        except UnicodeDecodeError:
            valid = False
        else:
            valid = bool(lines) and all(_CONTAINER_ID.fullmatch(line) for line in lines)
    return {
        "observation_valid": valid,
        "zero_existing_containers": valid and not result.stdout,
        "container_ids_raw_or_hashed_persisted": False,
    }


def _command_row(
    role: str,
    tail: Sequence[str],
    result: BoundedCommandResult,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    inventory = role == "container-inventory"
    facts = _normalized_result(result, inventory=inventory)
    row = {
        "role": role,
        "argv_contract": ["docker.exe", *tail],
        **facts,
    }
    if role == "daemon-version":
        projection: dict[str, Any] | None = _daemon_projection(result, facts)
    elif role == "image-moto":
        projection = _image_projection(result, facts, EXACT_DOCKER_IMAGES[0])
    elif role == "image-babel":
        projection = _image_projection(result, facts, EXACT_DOCKER_IMAGES[1])
    else:
        projection = _zero_container_inventory(result, facts)
    return row, projection


def _run_docker_snapshot(
    dependencies: DockerObservationDependencies,
    *,
    label: str,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    projections: dict[str, Any] = {}
    for role, tail in _DOCKER_COMMANDS:
        result = dependencies.command_runner(
            [str(dependencies.cli_path), *tail],
            environment=dependencies.child_environment,
            timeout_seconds=DOCKER_COMMAND_TIMEOUT_SECONDS,
            max_output_bytes=MAX_DOCKER_OUTPUT_BYTES,
        )
        row, projection = _command_row(role, tail, result)
        rows.append(row)
        projections[role] = projection
    daemon = projections["daemon-version"]
    images = {
        "moto": projections["image-moto"],
        "babel": projections["image-babel"],
    }
    containers = projections["container-inventory"]
    passed = (
        daemon is not None
        and all(value is not None for value in images.values())
        and containers["observation_valid"] is True
        and containers["zero_existing_containers"] is True
    )
    return {
        "label": label,
        "daemon": daemon,
        "images": images,
        "container_inventory": containers,
        "commands": rows,
        "passed": passed,
    }


def _docker_snapshot_identity(snapshot: Mapping[str, Any]) -> str:
    return canonical_json(
        {
            "daemon": snapshot["daemon"],
            "images": snapshot["images"],
            "container_inventory": snapshot["container_inventory"],
        }
    )


def _docker_blockers(snapshots: Sequence[Mapping[str, Any]], *, stable: bool) -> list[str]:
    blockers: list[str] = []
    if any(snapshot["daemon"] is None for snapshot in snapshots):
        blockers.append("already-running-linux-amd64-docker-daemon-not-ready")
    for key in ("moto", "babel"):
        if any(snapshot["images"][key] is None for snapshot in snapshots):
            blockers.append(f"exact-{key}-digest-image-not-ready")
    if any(
        snapshot["container_inventory"]["observation_valid"] is not True for snapshot in snapshots
    ):
        blockers.append("zero-existing-container-inventory-not-observed")
    elif any(
        snapshot["container_inventory"]["zero_existing_containers"] is not True
        for snapshot in snapshots
    ):
        blockers.append("existing-container-inventory-is-not-zero")
    if not stable:
        blockers.append("docker-readiness-snapshots-not-stable")
    return blockers


def _run_docker_with_dependencies(
    dependencies: DockerObservationDependencies,
) -> dict[str, Any]:
    expected_path = str(APPROVED_DOCKER_CLI_PATH.resolve(strict=False)).casefold()
    actual_path = str(dependencies.cli_path.resolve(strict=False)).casefold()
    _require(actual_path == expected_path, "D-137 Docker CLI path differs")
    _require(
        tuple(dependencies.child_environment) == ("DOCKER_CONFIG", "DOCKER_HOST")
        and bool(dependencies.child_environment["DOCKER_CONFIG"])
        and dependencies.child_environment["DOCKER_HOST"] == LOCAL_DOCKER_ENDPOINT,
        "D-137 Docker child environment differs",
    )
    bindings: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    for label in ("before", "after"):
        cli_before = dependencies.cli_binding(dependencies.cli_path)
        _exact_cli_binding(cli_before)
        snapshot = _run_docker_snapshot(dependencies, label=label)
        cli_after = dependencies.cli_binding(dependencies.cli_path)
        _exact_cli_binding(cli_after)
        _require(cli_before == cli_after, "D-137 Docker CLI changed during snapshot")
        bindings.extend((cli_before, cli_after))
        snapshots.append(snapshot)
    _require(all(binding == bindings[0] for binding in bindings), "D-137 Docker CLI drifted")
    stable = _docker_snapshot_identity(snapshots[0]) == _docker_snapshot_identity(snapshots[1])
    blockers = _docker_blockers(snapshots, stable=stable)
    passed = not blockers
    result = {
        "schema_version": DOCKER_OBSERVATION_SCHEMA,
        "phase": DOCKER_PHASE,
        "status": DOCKER_READY_STATUS if passed else DOCKER_BLOCKED_STATUS,
        "observer_contract": {
            "docker_cli_path": str(APPROVED_DOCKER_CLI_PATH),
            "docker_cli_version": APPROVED_DOCKER_CLI_VERSION,
            "docker_cli_build": APPROVED_DOCKER_CLI_BUILD,
            "docker_cli_file_bytes": APPROVED_DOCKER_CLI_FILE_BYTES,
            "docker_cli_file_sha256": APPROVED_DOCKER_CLI_FILE_SHA256,
            "forced_daemon_endpoint": LOCAL_DOCKER_ENDPOINT,
            "exact_images": list(EXACT_DOCKER_IMAGES),
            "snapshot_labels": ["before", "after"],
            "command_roles_per_snapshot": [role for role, _ in _DOCKER_COMMANDS],
            "max_output_bytes_per_stream": MAX_DOCKER_OUTPUT_BYTES,
            "timeout_seconds_per_command": DOCKER_COMMAND_TIMEOUT_SECONDS,
            "child_environment_names": ["DOCKER_CONFIG", "DOCKER_HOST"],
        },
        "observation": {
            "docker_cli_bindings": bindings,
            "snapshots": snapshots,
            "normalized_snapshots_stable": stable,
        },
        "blockers": blockers,
        "activity": {
            "docker_cli_file_binding_count": 4,
            "docker_cli_command_count": 8,
            "read_only_daemon_version_call_count": 2,
            "read_only_exact_image_inspect_call_count": 4,
            "read_only_container_inventory_call_count": 2,
            "docker_desktop_or_daemon_start_count": 0,
            "docker_image_pull_or_load_count": 0,
            "docker_image_store_mutation_count": 0,
            "container_create_start_run_exec_count": 0,
            "docker_workload_or_mutating_call_count": 0,
            "container_ids_raw_or_hashed_persisted": False,
            "raw_stdout_or_stderr_persisted": False,
        },
        "passed": passed,
    }
    return validate_d137_docker_no_call_preflight_observation(result)


def run_d137_docker_no_call_preflight_observation(
    *,
    repository: str | Path | None = None,
    dependencies: DockerObservationDependencies | None = None,
) -> dict[str, Any]:
    """Run the future bounded Docker read-only phase after its durable marker."""

    _repo_root(repository)
    if dependencies is not None:
        return _run_docker_with_dependencies(dependencies)
    with _default_docker_dependencies() as default_dependencies:
        return _run_docker_with_dependencies(default_dependencies)


def _validate_docker_command_row(
    row: Any,
    *,
    expected_role: str,
    expected_tail: Sequence[str],
) -> None:
    expected_keys = (
        "role",
        "argv_contract",
        "return_code",
        "timed_out",
        "stdout_bytes",
        "stdout_sha256",
        "stderr_bytes",
        "stderr_sha256",
        "stdout_zero",
        "stderr_zero",
        "output_within_bound",
        "raw_stdout_or_stderr_persisted",
    )
    _require(isinstance(row, dict) and tuple(row) == expected_keys, "D-137 command fields")
    _require(row["role"] == expected_role, "D-137 command role differs")
    _require(
        row["argv_contract"] == ["docker.exe", *expected_tail],
        "D-137 command argv differs",
    )
    _require(
        row["return_code"] is None or type(row["return_code"]) is int,
        "D-137 command return code differs",
    )
    for key in ("timed_out", "stdout_zero", "stderr_zero", "output_within_bound"):
        _require(type(row[key]) is bool, f"D-137 command {key} differs")
    inventory = expected_role == "container-inventory"
    for prefix in ("stdout", "stderr"):
        if inventory:
            _require(
                row[f"{prefix}_bytes"] is None and row[f"{prefix}_sha256"] is None,
                "D-137 container inventory output metadata persisted",
            )
        else:
            _require(
                type(row[f"{prefix}_bytes"]) is int and row[f"{prefix}_bytes"] >= 0,
                f"D-137 command {prefix} bytes differ",
            )
            _require(
                isinstance(row[f"{prefix}_sha256"], str)
                and _SHA256.fullmatch(row[f"{prefix}_sha256"]) is not None,
                f"D-137 command {prefix} SHA differs",
            )
            _require(
                row[f"{prefix}_zero"] is (row[f"{prefix}_bytes"] == 0),
                f"D-137 command {prefix} zero flag differs",
            )
            if row[f"{prefix}_zero"]:
                _require(
                    row[f"{prefix}_sha256"] == sha256_bytes(b""),
                    f"D-137 command empty {prefix} SHA differs",
                )
    if not inventory:
        expected_within_bound = (
            row["stdout_bytes"] <= MAX_DOCKER_OUTPUT_BYTES
            and row["stderr_bytes"] <= MAX_DOCKER_OUTPUT_BYTES
        )
        _require(
            row["output_within_bound"] is expected_within_bound,
            "D-137 command output-bound flag differs",
        )
    _require(
        row["raw_stdout_or_stderr_persisted"] is False,
        "D-137 raw command output boundary differs",
    )


def _validate_daemon_projection(value: Any, row: Mapping[str, Any]) -> None:
    if value is None:
        return
    _require(
        isinstance(value, dict)
        and tuple(value) == ("ClientVersion", "ServerVersion", "ServerOs", "ServerArch"),
        "D-137 daemon projection fields differ",
    )
    _require(value["ClientVersion"] == APPROVED_DOCKER_CLI_VERSION, "D-137 client version")
    _require(
        isinstance(value["ServerVersion"], str)
        and _DAEMON_VERSION.fullmatch(value["ServerVersion"]) is not None,
        "D-137 server version differs",
    )
    _require(
        value["ServerOs"] == "linux" and value["ServerArch"] == "amd64",
        "D-137 daemon platform differs",
    )
    expected = (json.dumps(value, separators=(",", ":")) + "\n").encode()
    _require(
        row["return_code"] == 0
        and row["timed_out"] is False
        and row["output_within_bound"] is True
        and row["stderr_zero"] is True
        and row["stdout_bytes"] == len(expected)
        and row["stdout_sha256"] == sha256_bytes(expected),
        "D-137 daemon projection is not bound to command evidence",
    )


def _validate_image_projection(value: Any, row: Mapping[str, Any], requested: str) -> None:
    if value is None:
        return
    _require(
        isinstance(value, dict)
        and tuple(value)
        == (
            "requested_repo_digest",
            "requested_digest",
            "config_id",
            "repo_digests",
            "matched_repo_digest",
        ),
        "D-137 image projection fields differ",
    )
    _require(value["requested_repo_digest"] == requested, "D-137 requested image differs")
    _require(value["requested_digest"] == requested.rsplit("@", 1)[1], "D-137 image digest")
    _require(
        isinstance(value["config_id"], str) and _IMAGE_ID.fullmatch(value["config_id"]),
        "D-137 image config ID differs",
    )
    repo_digests = value["repo_digests"]
    _require(
        isinstance(repo_digests, list)
        and repo_digests == sorted(repo_digests)
        and len(repo_digests) <= 128
        and len(repo_digests) == len(set(repo_digests))
        and all(
            isinstance(item, str)
            and len(item.encode("utf-8")) <= 512
            and _REPO_DIGEST.fullmatch(item)
            for item in repo_digests
        ),
        "D-137 RepoDigest projection differs",
    )
    matches = set(repo_digests).intersection(_repo_aliases(requested))
    _require(
        len(matches) == 1 and value["matched_repo_digest"] in matches,
        "D-137 matched RepoDigest differs",
    )
    raw_projection = {"Id": value["config_id"], "RepoDigests": repo_digests}
    expected = (json.dumps(raw_projection, separators=(",", ":")) + "\n").encode()
    _require(
        row["return_code"] == 0
        and row["timed_out"] is False
        and row["output_within_bound"] is True
        and row["stderr_zero"] is True
        and row["stdout_bytes"] == len(expected)
        and row["stdout_sha256"] == sha256_bytes(expected),
        "D-137 image projection is not bound to command evidence",
    )


def _validate_docker_snapshot(value: Any, *, expected_label: str) -> None:
    expected_keys = ("label", "daemon", "images", "container_inventory", "commands", "passed")
    _require(isinstance(value, dict) and tuple(value) == expected_keys, "D-137 snapshot fields")
    _require(value["label"] == expected_label, "D-137 snapshot label differs")
    rows = value["commands"]
    _require(isinstance(rows, list) and len(rows) == 4, "D-137 snapshot command count")
    for row, (role, tail) in zip(rows, _DOCKER_COMMANDS, strict=True):
        _validate_docker_command_row(row, expected_role=role, expected_tail=tail)
    _validate_daemon_projection(value["daemon"], rows[0])
    images = value["images"]
    _require(isinstance(images, dict) and tuple(images) == ("moto", "babel"), "D-137 images")
    _validate_image_projection(images["moto"], rows[1], EXACT_DOCKER_IMAGES[0])
    _validate_image_projection(images["babel"], rows[2], EXACT_DOCKER_IMAGES[1])
    containers = value["container_inventory"]
    _require(
        isinstance(containers, dict)
        and tuple(containers)
        == (
            "observation_valid",
            "zero_existing_containers",
            "container_ids_raw_or_hashed_persisted",
        ),
        "D-137 container inventory fields differ",
    )
    _require(
        type(containers["observation_valid"]) is bool
        and type(containers["zero_existing_containers"]) is bool,
        "D-137 container inventory flags differ",
    )
    _require(
        containers["container_ids_raw_or_hashed_persisted"] is False,
        "D-137 container identity boundary differs",
    )
    if containers["observation_valid"]:
        _require(
            rows[3]["return_code"] == 0
            and rows[3]["timed_out"] is False
            and rows[3]["output_within_bound"] is True
            and rows[3]["stderr_zero"] is True,
            "D-137 container inventory command did not succeed",
        )
    _require(
        containers["zero_existing_containers"]
        is (containers["observation_valid"] and rows[3]["stdout_zero"]),
        "D-137 zero-container projection differs",
    )
    passed = (
        value["daemon"] is not None
        and all(images[key] is not None for key in ("moto", "babel"))
        and containers["observation_valid"] is True
        and containers["zero_existing_containers"] is True
    )
    _require(value["passed"] is passed, "D-137 snapshot pass flag differs")


def validate_d137_docker_no_call_preflight_observation(value: Any) -> dict[str, Any]:
    """Replay a D-137 Docker observation without invoking Docker."""

    _require(isinstance(value, dict) and tuple(value) == _DOCKER_ROOT_KEYS, "D-137 Docker fields")
    _require(value["schema_version"] == DOCKER_OBSERVATION_SCHEMA, "D-137 Docker schema")
    _require(value["phase"] == DOCKER_PHASE, "D-137 Docker phase")
    contract = value["observer_contract"]
    expected_contract = {
        "docker_cli_path": str(APPROVED_DOCKER_CLI_PATH),
        "docker_cli_version": APPROVED_DOCKER_CLI_VERSION,
        "docker_cli_build": APPROVED_DOCKER_CLI_BUILD,
        "docker_cli_file_bytes": APPROVED_DOCKER_CLI_FILE_BYTES,
        "docker_cli_file_sha256": APPROVED_DOCKER_CLI_FILE_SHA256,
        "forced_daemon_endpoint": LOCAL_DOCKER_ENDPOINT,
        "exact_images": list(EXACT_DOCKER_IMAGES),
        "snapshot_labels": ["before", "after"],
        "command_roles_per_snapshot": [role for role, _ in _DOCKER_COMMANDS],
        "max_output_bytes_per_stream": MAX_DOCKER_OUTPUT_BYTES,
        "timeout_seconds_per_command": DOCKER_COMMAND_TIMEOUT_SECONDS,
        "child_environment_names": ["DOCKER_CONFIG", "DOCKER_HOST"],
    }
    _require(contract == expected_contract, "D-137 Docker observer contract differs")
    observation = value["observation"]
    _require(
        isinstance(observation, dict)
        and tuple(observation)
        == ("docker_cli_bindings", "snapshots", "normalized_snapshots_stable"),
        "D-137 Docker observation fields differ",
    )
    bindings = observation["docker_cli_bindings"]
    _require(isinstance(bindings, list) and len(bindings) == 4, "D-137 CLI binding count")
    for binding in bindings:
        _exact_cli_binding(binding)
    _require(all(binding == bindings[0] for binding in bindings), "D-137 CLI binding drift")
    snapshots = observation["snapshots"]
    _require(isinstance(snapshots, list) and len(snapshots) == 2, "D-137 snapshot count")
    for index, snapshot in enumerate(snapshots):
        _validate_docker_snapshot(snapshot, expected_label=("before", "after")[index])
    stable = _docker_snapshot_identity(snapshots[0]) == _docker_snapshot_identity(snapshots[1])
    _require(observation["normalized_snapshots_stable"] is stable, "D-137 snapshot stability")
    blockers = _docker_blockers(snapshots, stable=stable)
    _require(value["blockers"] == blockers, "D-137 Docker blockers differ")
    passed = not blockers
    _require(value["passed"] is passed, "D-137 Docker pass flag differs")
    _require(
        value["status"] == (DOCKER_READY_STATUS if passed else DOCKER_BLOCKED_STATUS),
        "D-137 Docker status differs",
    )
    expected_activity = {
        "docker_cli_file_binding_count": 4,
        "docker_cli_command_count": 8,
        "read_only_daemon_version_call_count": 2,
        "read_only_exact_image_inspect_call_count": 4,
        "read_only_container_inventory_call_count": 2,
        "docker_desktop_or_daemon_start_count": 0,
        "docker_image_pull_or_load_count": 0,
        "docker_image_store_mutation_count": 0,
        "container_create_start_run_exec_count": 0,
        "docker_workload_or_mutating_call_count": 0,
        "container_ids_raw_or_hashed_persisted": False,
        "raw_stdout_or_stderr_persisted": False,
    }
    _require(value["activity"] == expected_activity, "D-137 Docker activity differs")
    return value


def _locked_distribution_version(root: Path, package: str) -> str | None:
    text = _stable_read(root / "uv.lock").decode("utf-8")
    pattern = re.compile(rf'\[\[package\]\]\s+name = "{re.escape(package)}"\s+version = "([^"]+)"')
    match = pattern.search(text)
    return match.group(1) if match else None


def _checked_in_openai_factory_contract(root: Path) -> dict[str, Any]:
    source = _stable_read(root / "patchloop/agent/model.py").decode("utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise D137NoCallPreflightError("D-137 checked-in model source cannot be parsed") from exc
    checked_in_url: str | None = None
    factory: ast.FunctionDef | None = None
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "OFFICIAL_API_BASE_URL"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            checked_in_url = node.value.value
        if isinstance(node, ast.FunctionDef) and node.name == "create_openai_client":
            factory = node
    http_calls: list[ast.Call] = []
    openai_calls: list[ast.Call] = []
    explicit_base = False
    constructor_http_client_binding = False
    httpx_assigned_to_http_client = False
    if factory is not None:
        for node in ast.walk(factory):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "httpx"
                and node.func.attr == "Client"
            ):
                http_calls.append(node)
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "OpenAI"
            ):
                openai_calls.append(node)
        for node in factory.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "http_client"
                and isinstance(node.value, ast.Call)
                and node.value in http_calls
            ):
                httpx_assigned_to_http_client = True
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "constructor_kwargs"
                and isinstance(node.value, ast.Dict)
            ):
                pairs = {
                    key.value: item
                    for key, item in zip(node.value.keys, node.value.values, strict=True)
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
                base = pairs.get("base_url")
                explicit_base = isinstance(base, ast.Name) and base.id == "OFFICIAL_API_BASE_URL"
                http_client = pairs.get("http_client")
                constructor_http_client_binding = (
                    isinstance(http_client, ast.Name) and http_client.id == "http_client"
                )
    trust_env_false = bool(http_calls) and all(
        any(
            keyword.arg == "trust_env"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is False
            for keyword in call.keywords
        )
        for call in http_calls
    )
    exact_openai_kwargs_expansion = len(openai_calls) == 1 and (
        not openai_calls[0].args
        and len(openai_calls[0].keywords) == 1
        and openai_calls[0].keywords[0].arg is None
        and isinstance(openai_calls[0].keywords[0].value, ast.Name)
        and openai_calls[0].keywords[0].value.id == "constructor_kwargs"
    )
    return {
        "checked_in_official_base_url": checked_in_url,
        "official_base_url_exact": checked_in_url == OFFICIAL_API_BASE_URL,
        "factory_found": factory is not None,
        "single_httpx_client_constructor": len(http_calls) == 1,
        "httpx_client_assigned_to_http_client": httpx_assigned_to_http_client,
        "httpx_trust_env_false": trust_env_false,
        "explicit_official_base_url": explicit_base,
        "constructor_kwargs_http_client_binding": constructor_http_client_binding,
        "single_openai_constructor": len(openai_calls) == 1,
        "openai_exact_constructor_kwargs_expansion": exact_openai_kwargs_expansion,
    }


def _generic_file_binding(value: Any, *, label: str) -> None:
    _require(isinstance(value, dict), f"D-137 {label} binding is not an object")
    _require(
        tuple(value) == ("file_name", "file_bytes", "file_sha256", "linklike"),
        f"D-137 {label} binding fields differ",
    )
    _require(isinstance(value["file_name"], str) and bool(value["file_name"]), f"D-137 {label}")
    _require(
        type(value["file_bytes"]) is int and value["file_bytes"] > 0,
        f"D-137 {label} bytes differ",
    )
    _require(
        isinstance(value["file_sha256"], str)
        and _SHA256.fullmatch(value["file_sha256"]) is not None,
        f"D-137 {label} SHA differs",
    )
    _require(value["linklike"] is False, f"D-137 {label} is link-like")


def _resolve_module_origin(
    root: Path,
    *,
    name: str,
    dependencies: SDKObservationDependencies,
) -> _ResolvedModuleOrigin:
    find_module_spec_performed = False
    try:
        resolved_root = root.resolve(strict=True)
        repository_venv = (resolved_root / ".venv").resolve(strict=True)
        if not repository_venv.is_relative_to(resolved_root):
            raise ValueError("repository venv resolves outside repository")
        find_module_spec_performed = True
        spec = dependencies.find_module_spec(name)
        origin_value = getattr(spec, "origin", None)
        if (
            not isinstance(origin_value, str)
            or not origin_value
            or origin_value in {"built-in", "frozen"}
        ):
            raise ValueError("unsafe module origin")
        module_file = Path(origin_value).resolve(strict=True)
        under_repo_venv = module_file.is_relative_to(
            repository_venv
        ) and module_file.is_relative_to(resolved_root)
        relative_path = (
            module_file.relative_to(resolved_root).as_posix() if under_repo_venv else None
        )
    except Exception:
        return _ResolvedModuleOrigin(name, None, None, False, find_module_spec_performed)
    return _ResolvedModuleOrigin(
        name=name,
        path=module_file if under_repo_venv else None,
        repository_relative_path=relative_path,
        safe_repository_venv_origin=under_repo_venv,
        find_module_spec_performed=find_module_spec_performed,
    )


def _bind_preimport_module(
    root: Path,
    *,
    origin: _ResolvedModuleOrigin,
    dependencies: SDKObservationDependencies,
) -> dict[str, Any]:
    name = origin.name
    relative_path = origin.repository_relative_path
    _require(
        origin.safe_repository_venv_origin is True
        and origin.path is not None
        and isinstance(relative_path, str),
        f"D-137 {name} origin is not eligible for binding",
    )
    binding = dependencies.file_binding(origin.path)
    _generic_file_binding(binding, label=f"{name} module")
    distribution_version = dependencies.distribution_version(name)
    locked_version = _locked_distribution_version(root, name)
    return {
        "distribution_name": name,
        "distribution_version": distribution_version,
        "locked_version": locked_version,
        "module_file_binding_before": binding,
        "repository_relative_path": relative_path,
        "module_origin_under_repository_venv": True,
        "distribution_matches_lock": (
            isinstance(distribution_version, str) and distribution_version == locked_version
        ),
    }


def _loaded_module_provenance(
    root: Path,
    *,
    name: str,
    module: ModuleType,
    preimport: dict[str, Any],
) -> dict[str, Any]:
    module_file_value = getattr(module, "__file__", None)
    _require(isinstance(module_file_value, str) and bool(module_file_value), f"D-137 {name} file")
    module_path = Path(module_file_value).resolve(strict=True)
    relative_path = preimport["repository_relative_path"]
    _require(isinstance(relative_path, str), f"D-137 {name} preimport path is unavailable")
    expected_path = (root / Path(relative_path)).resolve(strict=True)
    _require(module_path == expected_path, f"D-137 {name} loaded module origin differs")
    module_version = getattr(module, "__version__", None)
    return {
        "distribution_name": name,
        "distribution_version": preimport["distribution_version"],
        "module_version": module_version,
        "locked_version": preimport["locked_version"],
        "module_file_binding_before": preimport["module_file_binding_before"],
        "module_file_binding_after": None,
        "module_binding_stable": None,
        "repository_relative_path": relative_path,
        "module_under_repository_venv": preimport["module_origin_under_repository_venv"],
        "versions_match": (
            isinstance(preimport["distribution_version"], str)
            and preimport["distribution_version"] == module_version == preimport["locked_version"]
        ),
    }


def _synthetic_sdk_probe(
    *,
    openai_module: ModuleType,
    httpx_module: ModuleType,
    official_base_url: str,
) -> dict[str, Any]:
    dispatch_count = 0

    def reject_dispatch(_request: Any) -> Any:
        nonlocal dispatch_count
        dispatch_count += 1
        raise D137NoCallPreflightError("D-137 synthetic transport dispatch is forbidden")

    transport = httpx_module.MockTransport(reject_dispatch)
    http_client = httpx_module.Client(transport=transport, trust_env=False)
    openai_client: Any = None
    base_url_exact = False
    max_retries_zero = False
    openai_close_call_count = 0
    http_fallback_close_call_count = 0
    http_client_closed = False
    try:
        openai_client = openai_module.OpenAI(
            api_key="d137-fixed-nonsecret-placeholder",
            organization="d137-none",
            project="d137-none",
            webhook_secret="d137-none",
            base_url=official_base_url,
            max_retries=0,
            http_client=http_client,
        )
        base_url_exact = str(openai_client.base_url).rstrip("/") == official_base_url
        max_retries_zero = openai_client.max_retries == 0
    finally:
        try:
            if openai_client is not None:
                openai_client.close()
                openai_close_call_count += 1
        finally:
            if not http_client.is_closed:
                http_client.close()
                http_fallback_close_call_count += 1
            http_client_closed = http_client.is_closed
    passed = (
        base_url_exact
        and max_retries_zero
        and dispatch_count == 0
        and openai_close_call_count == 1
        and http_fallback_close_call_count in (0, 1)
        and http_client_closed is True
    )
    return {
        "transport_kind": "httpx.MockTransport-reject-dispatch",
        "fixed_nonsecret_placeholder_used": True,
        "ambient_credential_value_used": False,
        "official_base_url": official_base_url,
        "base_url_exact": base_url_exact,
        "trust_env": False,
        "max_retries": 0,
        "observed_max_retries_zero": max_retries_zero,
        "transport_dispatch_count": dispatch_count,
        "openai_client_close_call_count": openai_close_call_count,
        "http_client_fallback_close_call_count": http_fallback_close_call_count,
        "http_client_closed": http_client_closed,
        "passed": passed,
    }


def _sdk_checks(observation: Mapping[str, Any]) -> dict[str, bool]:
    python = observation["python"]
    modules = observation["modules"]
    presence = observation["environment_presence_bits"]
    factory = observation["production_client_factory"]
    probe = observation["synthetic_probe"]
    return {
        "python_is_repository_venv": python["executable_under_repository_venv"],
        "python_executable_binding_stable": python["executable_binding_stable"],
        "openai_module_is_repository_venv": modules["openai"]["module_under_repository_venv"],
        "httpx_module_is_repository_venv": modules["httpx"]["module_under_repository_venv"],
        "openai_module_binding_stable": modules["openai"]["module_binding_stable"],
        "httpx_module_binding_stable": modules["httpx"]["module_binding_stable"],
        "openai_versions_match_lock": modules["openai"]["versions_match"],
        "httpx_versions_match_lock": modules["httpx"]["versions_match"],
        "openai_api_key_present": presence["OPENAI_API_KEY"],
        "pythonhome_absent": not presence["PYTHONHOME"],
        "pythonpath_absent": not presence["PYTHONPATH"],
        "checked_in_official_base_url_exact": factory["official_base_url_exact"],
        "production_factory_found": factory["factory_found"],
        "production_factory_single_httpx_constructor": factory["single_httpx_client_constructor"],
        "production_factory_httpx_client_binding": factory["httpx_client_assigned_to_http_client"],
        "production_factory_explicit_official_base_url": factory["explicit_official_base_url"],
        "production_factory_constructor_http_client_binding": factory[
            "constructor_kwargs_http_client_binding"
        ],
        "production_factory_trust_env_false": factory["httpx_trust_env_false"],
        "production_factory_single_openai_constructor": factory["single_openai_constructor"],
        "production_factory_exact_openai_kwargs_expansion": factory[
            "openai_exact_constructor_kwargs_expansion"
        ],
        "synthetic_no_call_probe_passed": probe["passed"],
        "synthetic_observed_max_retries_zero": probe["observed_max_retries_zero"],
        "synthetic_transport_dispatch_zero": probe["transport_dispatch_count"] == 0,
    }


_SDK_BLOCKER_BY_CHECK = {
    "python_is_repository_venv": "python-interpreter-is-not-repository-venv",
    "python_executable_binding_stable": "python-executable-binding-changed-during-sdk-probe",
    "openai_module_is_repository_venv": "openai-module-is-not-repository-venv",
    "httpx_module_is_repository_venv": "httpx-module-is-not-repository-venv",
    "openai_module_binding_stable": "openai-module-binding-changed-during-sdk-probe",
    "httpx_module_binding_stable": "httpx-module-binding-changed-during-sdk-probe",
    "openai_versions_match_lock": "openai-module-version-does-not-match-lock",
    "httpx_versions_match_lock": "httpx-module-version-does-not-match-lock",
    "openai_api_key_present": "openai-api-key-presence-bit-is-false",
    "pythonhome_absent": "pythonhome-presence-bit-is-true",
    "pythonpath_absent": "pythonpath-presence-bit-is-true",
    "checked_in_official_base_url_exact": "checked-in-official-base-url-differs",
    "production_factory_found": "production-openai-factory-not-found",
    "production_factory_single_httpx_constructor": (
        "production-factory-httpx-constructor-count-differs"
    ),
    "production_factory_httpx_client_binding": (
        "production-httpx-client-is-not-bound-to-http-client"
    ),
    "production_factory_explicit_official_base_url": (
        "production-factory-does-not-use-explicit-official-base-url"
    ),
    "production_factory_constructor_http_client_binding": (
        "production-constructor-kwargs-http-client-binding-differs"
    ),
    "production_factory_trust_env_false": "production-factory-trust-env-is-not-false",
    "production_factory_single_openai_constructor": (
        "production-factory-openai-constructor-count-differs"
    ),
    "production_factory_exact_openai_kwargs_expansion": (
        "production-openai-call-is-not-exact-constructor-kwargs-expansion"
    ),
    "synthetic_no_call_probe_passed": "synthetic-no-call-probe-did-not-pass",
    "synthetic_observed_max_retries_zero": "synthetic-client-max-retries-was-not-zero",
    "synthetic_transport_dispatch_zero": "synthetic-transport-dispatch-was-not-zero",
}


def _sdk_blockers(checks: Mapping[str, bool]) -> list[str]:
    return [blocker for name, blocker in _SDK_BLOCKER_BY_CHECK.items() if not checks[name]]


def _sdk_observer_contract() -> dict[str, Any]:
    return {
        "dynamic_import_names": ["httpx", "openai"],
        "environment_presence_names": list(SDK_ENVIRONMENT_NAMES),
        "environment_values_available_to_observer": False,
        "dotenv_read_authorized": False,
        "official_base_url": OFFICIAL_API_BASE_URL,
        "synthetic_transport": "httpx.MockTransport-reject-dispatch",
        "synthetic_transport_dispatch_limit": 0,
        "trust_env": False,
        "max_retries": 0,
    }


def _presence_suppressed_sdk_result(presence: dict[str, bool]) -> dict[str, Any]:
    checks = {
        "openai_api_key_present": presence["OPENAI_API_KEY"],
        "pythonhome_absent": not presence["PYTHONHOME"],
        "pythonpath_absent": not presence["PYTHONPATH"],
        "sdk_import_and_probe_performed": False,
    }
    blockers: list[str] = []
    if not checks["openai_api_key_present"]:
        blockers.append("openai-api-key-presence-bit-is-false")
    if not checks["pythonhome_absent"]:
        blockers.append("pythonhome-presence-bit-is-true")
    if not checks["pythonpath_absent"]:
        blockers.append("pythonpath-presence-bit-is-true")
    blockers.append("sdk-import-and-probe-suppressed-by-preliminary-presence-checks")
    result = {
        "schema_version": SDK_OBSERVATION_SCHEMA,
        "phase": SDK_PHASE,
        "status": SDK_BLOCKED_STATUS,
        "observer_contract": _sdk_observer_contract(),
        "observation": {
            "environment_presence_bits": presence,
            "python": None,
            "modules": None,
            "production_client_factory": None,
            "synthetic_probe": None,
            "checks": checks,
        },
        "blockers": blockers,
        "activity": {
            "dynamic_module_import_count": 0,
            "find_module_spec_count": 0,
            "python_executable_file_binding_count": 0,
            "sdk_module_file_binding_count": 0,
            "distribution_version_observation_count": 0,
            "locked_version_source_read_count": 0,
            "checked_in_factory_source_read_count": 0,
            "environment_presence_check_count": 3,
            "environment_value_read_count": 0,
            "dotenv_read_count": 0,
            "synthetic_transport_dispatch_count": 0,
            "network_call_count": 0,
            "provider_evaluator_or_agent_call_count": 0,
            "openai_client_close_call_count": 0,
            "http_client_fallback_close_call_count": 0,
            "http_client_closed": None,
        },
        "passed": False,
    }
    return validate_d137_sdk_no_call_preflight_observation(result)


def _resolve_python_executable(
    root: Path,
    dependencies: SDKObservationDependencies,
) -> dict[str, Any]:
    relative_path: str | None = None
    under_repo_venv = False
    try:
        resolved_root = root.resolve(strict=True)
        repository_venv = (resolved_root / ".venv").resolve(strict=True)
        python_path = dependencies.python_executable.resolve(strict=True)
        under_repo_venv = (
            repository_venv.is_relative_to(resolved_root)
            and python_path.is_relative_to(repository_venv)
            and python_path.is_relative_to(resolved_root)
        )
        if under_repo_venv:
            relative_path = python_path.relative_to(resolved_root).as_posix()
    except (OSError, RuntimeError, ValueError):
        # Missing, unresolvable, or repository-escaping interpreters are all a
        # canonical provenance block.  No path or file binding is persisted.
        pass
    return {
        "version": dependencies.python_version,
        "executable_file_binding_before": None,
        "executable_file_binding_after": None,
        "executable_binding_stable": None,
        "repository_relative_path": relative_path,
        "executable_under_repository_venv": under_repo_venv,
    }


def _bind_python_executable(
    root: Path,
    dependencies: SDKObservationDependencies,
    observation: dict[str, Any],
) -> None:
    relative_path = observation["repository_relative_path"]
    _require(
        observation["executable_under_repository_venv"] is True and isinstance(relative_path, str),
        "D-137 Python executable is not eligible for binding",
    )
    binding = dependencies.file_binding(root / Path(relative_path))
    _generic_file_binding(binding, label="Python executable")
    observation["executable_file_binding_before"] = binding


def _python_suppressed_sdk_result(
    presence: dict[str, bool],
    python_observation: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "openai_api_key_present": True,
        "pythonhome_absent": True,
        "pythonpath_absent": True,
        "python_is_repository_venv": False,
        "sdk_import_and_probe_performed": False,
    }
    result = {
        "schema_version": SDK_OBSERVATION_SCHEMA,
        "phase": SDK_PHASE,
        "status": SDK_BLOCKED_STATUS,
        "observer_contract": _sdk_observer_contract(),
        "observation": {
            "environment_presence_bits": presence,
            "python": python_observation,
            "modules": None,
            "production_client_factory": None,
            "synthetic_probe": None,
            "checks": checks,
        },
        "blockers": [
            "python-interpreter-is-not-repository-venv",
            "sdk-import-and-probe-suppressed-by-python-provenance",
        ],
        "activity": {
            "dynamic_module_import_count": 0,
            "find_module_spec_count": 0,
            "python_executable_file_binding_count": 0,
            "sdk_module_file_binding_count": 0,
            "distribution_version_observation_count": 0,
            "locked_version_source_read_count": 0,
            "checked_in_factory_source_read_count": 0,
            "environment_presence_check_count": 3,
            "environment_value_read_count": 0,
            "dotenv_read_count": 0,
            "synthetic_transport_dispatch_count": 0,
            "network_call_count": 0,
            "provider_evaluator_or_agent_call_count": 0,
            "openai_client_close_call_count": 0,
            "http_client_fallback_close_call_count": 0,
            "http_client_closed": None,
        },
        "passed": False,
    }
    return validate_d137_sdk_no_call_preflight_observation(result)


def _module_origins_ready(modules: Mapping[str, _ResolvedModuleOrigin]) -> bool:
    return all(modules[name].safe_repository_venv_origin for name in ("openai", "httpx"))


def _module_origin_suppressed_sdk_result(
    presence: dict[str, bool],
    python_observation: dict[str, Any],
    origins: dict[str, _ResolvedModuleOrigin],
) -> dict[str, Any]:
    safe_origin_bits = {
        "openai_origin_is_repository_venv": origins["openai"].safe_repository_venv_origin,
        "httpx_origin_is_repository_venv": origins["httpx"].safe_repository_venv_origin,
    }
    find_spec_bits = {
        "openai_find_module_spec_performed": origins["openai"].find_module_spec_performed,
        "httpx_find_module_spec_performed": origins["httpx"].find_module_spec_performed,
    }
    checks = {
        "openai_api_key_present": True,
        "pythonhome_absent": True,
        "pythonpath_absent": True,
        "python_is_repository_venv": True,
        **safe_origin_bits,
        "sdk_import_and_probe_performed": False,
    }
    blockers = [
        f"{name}-module-origin-is-not-repository-venv"
        for name in ("openai", "httpx")
        if not checks[f"{name}_origin_is_repository_venv"]
    ]
    blockers.append("sdk-import-and-probe-suppressed-by-module-origin-provenance")
    result = {
        "schema_version": SDK_OBSERVATION_SCHEMA,
        "phase": SDK_PHASE,
        "status": SDK_BLOCKED_STATUS,
        "observer_contract": _sdk_observer_contract(),
        "observation": {
            "environment_presence_bits": presence,
            "python": python_observation,
            "modules": {**safe_origin_bits, **find_spec_bits},
            "production_client_factory": None,
            "synthetic_probe": None,
            "checks": checks,
        },
        "blockers": blockers,
        "activity": {
            "dynamic_module_import_count": 0,
            "find_module_spec_count": sum(find_spec_bits.values()),
            "python_executable_file_binding_count": 1,
            "sdk_module_file_binding_count": 0,
            "distribution_version_observation_count": 0,
            "locked_version_source_read_count": 0,
            "checked_in_factory_source_read_count": 0,
            "environment_presence_check_count": 3,
            "environment_value_read_count": 0,
            "dotenv_read_count": 0,
            "synthetic_transport_dispatch_count": 0,
            "network_call_count": 0,
            "provider_evaluator_or_agent_call_count": 0,
            "openai_client_close_call_count": 0,
            "http_client_fallback_close_call_count": 0,
            "http_client_closed": None,
        },
        "passed": False,
    }
    return validate_d137_sdk_no_call_preflight_observation(result)


def _preimport_modules_ready(modules: Mapping[str, Mapping[str, Any]]) -> bool:
    return all(
        modules[name]["module_origin_under_repository_venv"] is True
        and modules[name]["distribution_matches_lock"] is True
        for name in ("openai", "httpx")
    )


def _module_preimport_suppressed_sdk_result(
    presence: dict[str, bool],
    python_observation: dict[str, Any],
    modules: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    checks = {
        "openai_api_key_present": True,
        "pythonhome_absent": True,
        "pythonpath_absent": True,
        "python_is_repository_venv": True,
        "openai_origin_is_repository_venv": modules["openai"][
            "module_origin_under_repository_venv"
        ],
        "httpx_origin_is_repository_venv": modules["httpx"]["module_origin_under_repository_venv"],
        "openai_distribution_matches_lock": modules["openai"]["distribution_matches_lock"],
        "httpx_distribution_matches_lock": modules["httpx"]["distribution_matches_lock"],
        "sdk_import_and_probe_performed": False,
    }
    blockers: list[str] = []
    for name in ("openai", "httpx"):
        if not checks[f"{name}_origin_is_repository_venv"]:
            blockers.append(f"{name}-module-origin-is-not-repository-venv")
        if not checks[f"{name}_distribution_matches_lock"]:
            blockers.append(f"{name}-distribution-version-does-not-match-lock")
    blockers.append("sdk-import-and-probe-suppressed-by-module-preimport-provenance")
    result = {
        "schema_version": SDK_OBSERVATION_SCHEMA,
        "phase": SDK_PHASE,
        "status": SDK_BLOCKED_STATUS,
        "observer_contract": _sdk_observer_contract(),
        "observation": {
            "environment_presence_bits": presence,
            "python": python_observation,
            "modules": modules,
            "production_client_factory": None,
            "synthetic_probe": None,
            "checks": checks,
        },
        "blockers": blockers,
        "activity": {
            "dynamic_module_import_count": 0,
            "find_module_spec_count": 2,
            "python_executable_file_binding_count": 1,
            "sdk_module_file_binding_count": 2,
            "distribution_version_observation_count": 2,
            "locked_version_source_read_count": 2,
            "checked_in_factory_source_read_count": 0,
            "environment_presence_check_count": 3,
            "environment_value_read_count": 0,
            "dotenv_read_count": 0,
            "synthetic_transport_dispatch_count": 0,
            "network_call_count": 0,
            "provider_evaluator_or_agent_call_count": 0,
            "openai_client_close_call_count": 0,
            "http_client_fallback_close_call_count": 0,
            "http_client_closed": None,
        },
        "passed": False,
    }
    return validate_d137_sdk_no_call_preflight_observation(result)


def _run_sdk_with_dependencies(
    root: Path,
    dependencies: SDKObservationDependencies,
    presence: dict[str, bool],
    python_observation: dict[str, Any],
    preimport_modules: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    httpx_module = dependencies.import_module("httpx")
    openai_module = dependencies.import_module("openai")
    modules = {
        "openai": _loaded_module_provenance(
            root,
            name="openai",
            module=openai_module,
            preimport=preimport_modules["openai"],
        ),
        "httpx": _loaded_module_provenance(
            root,
            name="httpx",
            module=httpx_module,
            preimport=preimport_modules["httpx"],
        ),
    }
    production_factory = _checked_in_openai_factory_contract(root)
    probe = _synthetic_sdk_probe(
        openai_module=openai_module,
        httpx_module=httpx_module,
        official_base_url=OFFICIAL_API_BASE_URL,
    )
    python_binding_after = dependencies.file_binding(dependencies.python_executable)
    _generic_file_binding(python_binding_after, label="Python executable after probe")
    python_observation["executable_file_binding_after"] = python_binding_after
    python_observation["executable_binding_stable"] = (
        python_observation["executable_file_binding_before"] == python_binding_after
    )
    for name in ("openai", "httpx"):
        relative_path = modules[name]["repository_relative_path"]
        _require(isinstance(relative_path, str), f"D-137 {name} relative path is unavailable")
        binding_after = dependencies.file_binding(root / Path(relative_path))
        _generic_file_binding(binding_after, label=f"{name} module after probe")
        modules[name]["module_file_binding_after"] = binding_after
        modules[name]["module_binding_stable"] = (
            modules[name]["module_file_binding_before"] == binding_after
        )
    observation = {
        "environment_presence_bits": presence,
        "python": python_observation,
        "modules": modules,
        "production_client_factory": production_factory,
        "synthetic_probe": probe,
    }
    checks = _sdk_checks(observation)
    blockers = _sdk_blockers(checks)
    passed = not blockers
    result = {
        "schema_version": SDK_OBSERVATION_SCHEMA,
        "phase": SDK_PHASE,
        "status": SDK_READY_STATUS if passed else SDK_BLOCKED_STATUS,
        "observer_contract": _sdk_observer_contract(),
        "observation": observation,
        "blockers": blockers,
        "activity": {
            "dynamic_module_import_count": 2,
            "find_module_spec_count": 2,
            "python_executable_file_binding_count": 2,
            "sdk_module_file_binding_count": 4,
            "distribution_version_observation_count": 2,
            "locked_version_source_read_count": 2,
            "checked_in_factory_source_read_count": 1,
            "environment_presence_check_count": 3,
            "environment_value_read_count": 0,
            "dotenv_read_count": 0,
            "synthetic_transport_dispatch_count": probe["transport_dispatch_count"],
            "network_call_count": 0,
            "provider_evaluator_or_agent_call_count": 0,
            "openai_client_close_call_count": probe["openai_client_close_call_count"],
            "http_client_fallback_close_call_count": probe["http_client_fallback_close_call_count"],
            "http_client_closed": probe["http_client_closed"],
        },
        "passed": passed,
    }
    result["observation"]["checks"] = checks
    return validate_d137_sdk_no_call_preflight_observation(result)


def run_d137_sdk_no_call_preflight_observation(
    *,
    repository: str | Path | None = None,
    dependencies: SDKObservationDependencies | None = None,
) -> dict[str, Any]:
    """Run the future SDK no-call phase after its distinct durable marker."""

    active_dependencies = dependencies or _default_sdk_dependencies()
    # These are the only ambient-state queries.  The dependency contract returns
    # membership bits and gives the helper no mechanism to obtain values.
    presence = {
        name: active_dependencies.environment_present(name) for name in SDK_ENVIRONMENT_NAMES
    }
    _require(all(type(value) is bool for value in presence.values()), "D-137 presence bits differ")
    if not presence["OPENAI_API_KEY"] or presence["PYTHONHOME"] or presence["PYTHONPATH"]:
        return _presence_suppressed_sdk_result(presence)
    root = _repo_root(repository)
    python_observation = _resolve_python_executable(root, active_dependencies)
    if not python_observation["executable_under_repository_venv"]:
        return _python_suppressed_sdk_result(presence, python_observation)
    _bind_python_executable(root, active_dependencies, python_observation)
    httpx_origin = _resolve_module_origin(
        root,
        name="httpx",
        dependencies=active_dependencies,
    )
    openai_origin = _resolve_module_origin(
        root,
        name="openai",
        dependencies=active_dependencies,
    )
    module_origins = {"openai": openai_origin, "httpx": httpx_origin}
    if not _module_origins_ready(module_origins):
        return _module_origin_suppressed_sdk_result(
            presence,
            python_observation,
            module_origins,
        )
    httpx_preimport = _bind_preimport_module(
        root,
        origin=httpx_origin,
        dependencies=active_dependencies,
    )
    openai_preimport = _bind_preimport_module(
        root,
        origin=openai_origin,
        dependencies=active_dependencies,
    )
    preimport_modules = {"openai": openai_preimport, "httpx": httpx_preimport}
    if not _preimport_modules_ready(preimport_modules):
        return _module_preimport_suppressed_sdk_result(
            presence,
            python_observation,
            preimport_modules,
        )
    return _run_sdk_with_dependencies(
        root,
        active_dependencies,
        presence,
        python_observation,
        preimport_modules,
    )


def _validate_presence_suppressed_sdk_observation(value: dict[str, Any]) -> dict[str, Any]:
    observation = value["observation"]
    presence = observation["environment_presence_bits"]
    _require(
        observation["python"] is None
        and observation["modules"] is None
        and observation["production_client_factory"] is None
        and observation["synthetic_probe"] is None,
        "D-137 preliminary-blocked SDK state performed a suppressed observation",
    )
    expected_checks = {
        "openai_api_key_present": presence["OPENAI_API_KEY"],
        "pythonhome_absent": not presence["PYTHONHOME"],
        "pythonpath_absent": not presence["PYTHONPATH"],
        "sdk_import_and_probe_performed": False,
    }
    _require(observation["checks"] == expected_checks, "D-137 presence-blocked SDK checks differ")
    expected_blockers: list[str] = []
    if not expected_checks["openai_api_key_present"]:
        expected_blockers.append("openai-api-key-presence-bit-is-false")
    if not expected_checks["pythonhome_absent"]:
        expected_blockers.append("pythonhome-presence-bit-is-true")
    if not expected_checks["pythonpath_absent"]:
        expected_blockers.append("pythonpath-presence-bit-is-true")
    expected_blockers.append("sdk-import-and-probe-suppressed-by-preliminary-presence-checks")
    _require(value["blockers"] == expected_blockers, "D-137 presence-blocked SDK blockers differ")
    expected_activity = {
        "dynamic_module_import_count": 0,
        "find_module_spec_count": 0,
        "python_executable_file_binding_count": 0,
        "sdk_module_file_binding_count": 0,
        "distribution_version_observation_count": 0,
        "locked_version_source_read_count": 0,
        "checked_in_factory_source_read_count": 0,
        "environment_presence_check_count": 3,
        "environment_value_read_count": 0,
        "dotenv_read_count": 0,
        "synthetic_transport_dispatch_count": 0,
        "network_call_count": 0,
        "provider_evaluator_or_agent_call_count": 0,
        "openai_client_close_call_count": 0,
        "http_client_fallback_close_call_count": 0,
        "http_client_closed": None,
    }
    _require(value["activity"] == expected_activity, "D-137 presence-blocked SDK activity differs")
    _require(value["status"] == SDK_BLOCKED_STATUS, "D-137 presence-blocked SDK status differs")
    _require(value["passed"] is False, "D-137 presence-blocked SDK pass flag differs")
    return value


def _validate_python_suppressed_sdk_observation(value: dict[str, Any]) -> dict[str, Any]:
    observation = value["observation"]
    _require(
        observation["modules"] is None
        and observation["production_client_factory"] is None
        and observation["synthetic_probe"] is None,
        "D-137 Python-blocked SDK state performed a suppressed observation",
    )
    expected_checks = {
        "openai_api_key_present": True,
        "pythonhome_absent": True,
        "pythonpath_absent": True,
        "python_is_repository_venv": False,
        "sdk_import_and_probe_performed": False,
    }
    _require(observation["checks"] == expected_checks, "D-137 Python-blocked SDK checks differ")
    _require(
        value["blockers"]
        == [
            "python-interpreter-is-not-repository-venv",
            "sdk-import-and-probe-suppressed-by-python-provenance",
        ],
        "D-137 Python-blocked SDK blockers differ",
    )
    expected_activity = {
        "dynamic_module_import_count": 0,
        "find_module_spec_count": 0,
        "python_executable_file_binding_count": 0,
        "sdk_module_file_binding_count": 0,
        "distribution_version_observation_count": 0,
        "locked_version_source_read_count": 0,
        "checked_in_factory_source_read_count": 0,
        "environment_presence_check_count": 3,
        "environment_value_read_count": 0,
        "dotenv_read_count": 0,
        "synthetic_transport_dispatch_count": 0,
        "network_call_count": 0,
        "provider_evaluator_or_agent_call_count": 0,
        "openai_client_close_call_count": 0,
        "http_client_fallback_close_call_count": 0,
        "http_client_closed": None,
    }
    _require(value["activity"] == expected_activity, "D-137 Python-blocked SDK activity differs")
    _require(value["status"] == SDK_BLOCKED_STATUS, "D-137 Python-blocked SDK status differs")
    _require(value["passed"] is False, "D-137 Python-blocked SDK pass flag differs")
    return value


def _validate_module_origin_suppressed_sdk_observation(
    value: dict[str, Any],
) -> dict[str, Any]:
    observation = value["observation"]
    python = observation["python"]
    _require(
        python["executable_file_binding_after"] is None
        and python["executable_binding_stable"] is None,
        "D-137 module-origin-blocked Python binding was re-read",
    )
    modules = observation["modules"]
    _require(
        isinstance(modules, dict)
        and tuple(modules)
        == (
            "openai_origin_is_repository_venv",
            "httpx_origin_is_repository_venv",
            "openai_find_module_spec_performed",
            "httpx_find_module_spec_performed",
        )
        and all(type(bit) is bool for bit in modules.values())
        and not all(modules[f"{name}_origin_is_repository_venv"] for name in ("openai", "httpx")),
        "D-137 module-origin suppression fields differ",
    )
    for name in ("openai", "httpx"):
        _require(
            not modules[f"{name}_origin_is_repository_venv"]
            or modules[f"{name}_find_module_spec_performed"],
            f"D-137 {name} safe origin lacks a spec query",
        )
    _require(
        observation["production_client_factory"] is None and observation["synthetic_probe"] is None,
        "D-137 module-origin-blocked state performed a suppressed observation",
    )
    expected_checks = {
        "openai_api_key_present": True,
        "pythonhome_absent": True,
        "pythonpath_absent": True,
        "python_is_repository_venv": True,
        "openai_origin_is_repository_venv": modules["openai_origin_is_repository_venv"],
        "httpx_origin_is_repository_venv": modules["httpx_origin_is_repository_venv"],
        "sdk_import_and_probe_performed": False,
    }
    _require(observation["checks"] == expected_checks, "D-137 module-origin checks differ")
    expected_blockers = [
        f"{name}-module-origin-is-not-repository-venv"
        for name in ("openai", "httpx")
        if not modules[f"{name}_origin_is_repository_venv"]
    ]
    expected_blockers.append("sdk-import-and-probe-suppressed-by-module-origin-provenance")
    _require(value["blockers"] == expected_blockers, "D-137 module-origin blockers differ")
    expected_activity = {
        "dynamic_module_import_count": 0,
        "find_module_spec_count": sum(
            modules[f"{name}_find_module_spec_performed"] for name in ("openai", "httpx")
        ),
        "python_executable_file_binding_count": 1,
        "sdk_module_file_binding_count": 0,
        "distribution_version_observation_count": 0,
        "locked_version_source_read_count": 0,
        "checked_in_factory_source_read_count": 0,
        "environment_presence_check_count": 3,
        "environment_value_read_count": 0,
        "dotenv_read_count": 0,
        "synthetic_transport_dispatch_count": 0,
        "network_call_count": 0,
        "provider_evaluator_or_agent_call_count": 0,
        "openai_client_close_call_count": 0,
        "http_client_fallback_close_call_count": 0,
        "http_client_closed": None,
    }
    _require(value["activity"] == expected_activity, "D-137 module-origin activity differs")
    _require(value["status"] == SDK_BLOCKED_STATUS, "D-137 module-origin status differs")
    _require(value["passed"] is False, "D-137 module-origin pass flag differs")
    return value


def _validate_preimport_module(value: Any, *, name: str) -> None:
    _require(
        isinstance(value, dict)
        and tuple(value)
        == (
            "distribution_name",
            "distribution_version",
            "locked_version",
            "module_file_binding_before",
            "repository_relative_path",
            "module_origin_under_repository_venv",
            "distribution_matches_lock",
        ),
        f"D-137 {name} preimport fields differ",
    )
    _require(value["distribution_name"] == name, f"D-137 {name} preimport name differs")
    for key in ("distribution_version", "locked_version"):
        _require(value[key] is None or isinstance(value[key], str), f"D-137 {name} {key}")
    _generic_file_binding(value["module_file_binding_before"], label=f"{name} module")
    _require(
        isinstance(value["repository_relative_path"], str)
        and value["repository_relative_path"].startswith(".venv/"),
        f"D-137 {name} preimport path differs",
    )
    _require(value["module_origin_under_repository_venv"] is True, f"D-137 {name} origin")
    expected_match = (
        isinstance(value["distribution_version"], str)
        and value["distribution_version"] == value["locked_version"]
    )
    _require(value["distribution_matches_lock"] is expected_match, f"D-137 {name} lock match")


def _validate_module_preimport_suppressed_sdk_observation(
    value: dict[str, Any],
) -> dict[str, Any]:
    observation = value["observation"]
    python = observation["python"]
    _require(
        python["executable_file_binding_after"] is None
        and python["executable_binding_stable"] is None,
        "D-137 module-preimport-blocked Python binding was re-read",
    )
    modules = observation["modules"]
    _require(isinstance(modules, dict) and tuple(modules) == ("openai", "httpx"), "D-137 modules")
    for name in ("openai", "httpx"):
        _validate_preimport_module(modules[name], name=name)
    _require(
        not all(modules[name]["distribution_matches_lock"] for name in ("openai", "httpx")),
        "D-137 preimport suppression has no version blocker",
    )
    _require(
        observation["production_client_factory"] is None and observation["synthetic_probe"] is None,
        "D-137 preimport-blocked state performed a suppressed observation",
    )
    expected_checks = {
        "openai_api_key_present": True,
        "pythonhome_absent": True,
        "pythonpath_absent": True,
        "python_is_repository_venv": True,
        "openai_origin_is_repository_venv": True,
        "httpx_origin_is_repository_venv": True,
        "openai_distribution_matches_lock": modules["openai"]["distribution_matches_lock"],
        "httpx_distribution_matches_lock": modules["httpx"]["distribution_matches_lock"],
        "sdk_import_and_probe_performed": False,
    }
    _require(observation["checks"] == expected_checks, "D-137 module-preimport checks differ")
    expected_blockers = [
        f"{name}-distribution-version-does-not-match-lock"
        for name in ("openai", "httpx")
        if not modules[name]["distribution_matches_lock"]
    ]
    expected_blockers.append("sdk-import-and-probe-suppressed-by-module-preimport-provenance")
    _require(value["blockers"] == expected_blockers, "D-137 module-preimport blockers differ")
    expected_activity = {
        "dynamic_module_import_count": 0,
        "find_module_spec_count": 2,
        "python_executable_file_binding_count": 1,
        "sdk_module_file_binding_count": 2,
        "distribution_version_observation_count": 2,
        "locked_version_source_read_count": 2,
        "checked_in_factory_source_read_count": 0,
        "environment_presence_check_count": 3,
        "environment_value_read_count": 0,
        "dotenv_read_count": 0,
        "synthetic_transport_dispatch_count": 0,
        "network_call_count": 0,
        "provider_evaluator_or_agent_call_count": 0,
        "openai_client_close_call_count": 0,
        "http_client_fallback_close_call_count": 0,
        "http_client_closed": None,
    }
    _require(value["activity"] == expected_activity, "D-137 module-preimport activity differs")
    _require(value["status"] == SDK_BLOCKED_STATUS, "D-137 module-preimport status differs")
    _require(value["passed"] is False, "D-137 module-preimport pass flag differs")
    return value


def validate_d137_sdk_no_call_preflight_observation(value: Any) -> dict[str, Any]:
    """Replay a D-137 SDK observation without importing an SDK or reading env."""

    _require(isinstance(value, dict) and tuple(value) == _SDK_ROOT_KEYS, "D-137 SDK fields")
    _require(value["schema_version"] == SDK_OBSERVATION_SCHEMA, "D-137 SDK schema")
    _require(value["phase"] == SDK_PHASE, "D-137 SDK phase")
    expected_contract = _sdk_observer_contract()
    _require(value["observer_contract"] == expected_contract, "D-137 SDK observer contract")
    observation = value["observation"]
    _require(
        isinstance(observation, dict)
        and tuple(observation)
        == (
            "environment_presence_bits",
            "python",
            "modules",
            "production_client_factory",
            "synthetic_probe",
            "checks",
        ),
        "D-137 SDK observation fields differ",
    )
    presence = observation["environment_presence_bits"]
    _require(
        isinstance(presence, dict) and tuple(presence) == SDK_ENVIRONMENT_NAMES,
        "D-137 environment presence fields differ",
    )
    _require(all(type(bit) is bool for bit in presence.values()), "D-137 presence bit types")
    preliminary_presence_blocked = (
        not presence["OPENAI_API_KEY"] or presence["PYTHONHOME"] or presence["PYTHONPATH"]
    )
    if preliminary_presence_blocked:
        return _validate_presence_suppressed_sdk_observation(value)
    python = observation["python"]
    _require(
        isinstance(python, dict)
        and tuple(python)
        == (
            "version",
            "executable_file_binding_before",
            "executable_file_binding_after",
            "executable_binding_stable",
            "repository_relative_path",
            "executable_under_repository_venv",
        ),
        "D-137 Python observation fields differ",
    )
    _require(isinstance(python["version"], str) and bool(python["version"]), "D-137 Python version")
    _require(
        python["repository_relative_path"] is None
        or isinstance(python["repository_relative_path"], str),
        "D-137 Python relative path differs",
    )
    _require(
        type(python["executable_under_repository_venv"]) is bool,
        "D-137 Python provenance flag",
    )
    python_path_is_venv = isinstance(python["repository_relative_path"], str) and python[
        "repository_relative_path"
    ].startswith(".venv/")
    _require(
        python["executable_under_repository_venv"] is python_path_is_venv,
        "D-137 Python repository-venv path differs",
    )
    if not python["executable_under_repository_venv"]:
        _require(
            python["executable_file_binding_before"] is None
            and python["executable_file_binding_after"] is None
            and python["executable_binding_stable"] is None,
            "D-137 external Python executable was read or hashed",
        )
        return _validate_python_suppressed_sdk_observation(value)
    _generic_file_binding(python["executable_file_binding_before"], label="Python executable")
    modules = observation["modules"]
    if (
        observation["production_client_factory"] is None
        and observation["synthetic_probe"] is None
        and isinstance(modules, dict)
        and tuple(modules)
        == (
            "openai_origin_is_repository_venv",
            "httpx_origin_is_repository_venv",
            "openai_find_module_spec_performed",
            "httpx_find_module_spec_performed",
        )
    ):
        return _validate_module_origin_suppressed_sdk_observation(value)
    _require(isinstance(modules, dict) and tuple(modules) == ("openai", "httpx"), "D-137 modules")
    first_module_keys = tuple(modules["openai"]) if isinstance(modules["openai"], dict) else ()
    if observation["production_client_factory"] is None and observation["synthetic_probe"] is None:
        if first_module_keys == (
            "distribution_name",
            "distribution_version",
            "locked_version",
            "module_file_binding_before",
            "repository_relative_path",
            "module_origin_under_repository_venv",
            "distribution_matches_lock",
        ):
            return _validate_module_preimport_suppressed_sdk_observation(value)
        raise D137NoCallPreflightError("D-137 suppressed module provenance fields differ")
    _generic_file_binding(
        python["executable_file_binding_after"],
        label="Python executable after probe",
    )
    _require(
        type(python["executable_binding_stable"]) is bool
        and python["executable_binding_stable"]
        is (python["executable_file_binding_before"] == python["executable_file_binding_after"]),
        "D-137 Python executable binding stability differs",
    )
    for name in ("openai", "httpx"):
        module = modules[name]
        _require(
            isinstance(module, dict)
            and tuple(module)
            == (
                "distribution_name",
                "distribution_version",
                "module_version",
                "locked_version",
                "module_file_binding_before",
                "module_file_binding_after",
                "module_binding_stable",
                "repository_relative_path",
                "module_under_repository_venv",
                "versions_match",
            ),
            f"D-137 {name} provenance fields differ",
        )
        _require(module["distribution_name"] == name, f"D-137 {name} distribution name")
        for version_key in ("distribution_version", "module_version", "locked_version"):
            _require(
                module[version_key] is None or isinstance(module[version_key], str),
                f"D-137 {name} {version_key} differs",
            )
        _generic_file_binding(module["module_file_binding_before"], label=f"{name} module")
        _generic_file_binding(
            module["module_file_binding_after"],
            label=f"{name} module after probe",
        )
        _require(
            type(module["module_binding_stable"]) is bool
            and module["module_binding_stable"]
            is (module["module_file_binding_before"] == module["module_file_binding_after"]),
            f"D-137 {name} module binding stability differs",
        )
        _require(
            module["repository_relative_path"] is None
            or isinstance(module["repository_relative_path"], str),
            f"D-137 {name} relative path differs",
        )
        _require(
            type(module["module_under_repository_venv"]) is bool,
            f"D-137 {name} repository-venv flag",
        )
        module_path_is_venv = isinstance(module["repository_relative_path"], str) and module[
            "repository_relative_path"
        ].startswith(".venv/")
        _require(
            module["module_under_repository_venv"] is module_path_is_venv,
            f"D-137 {name} repository-venv path differs",
        )
        expected_versions_match = (
            isinstance(module["distribution_version"], str)
            and module["distribution_version"]
            == module["module_version"]
            == module["locked_version"]
        )
        _require(module["versions_match"] is expected_versions_match, f"D-137 {name} versions")
    factory = observation["production_client_factory"]
    _require(
        isinstance(factory, dict)
        and tuple(factory)
        == (
            "checked_in_official_base_url",
            "official_base_url_exact",
            "factory_found",
            "single_httpx_client_constructor",
            "httpx_client_assigned_to_http_client",
            "httpx_trust_env_false",
            "explicit_official_base_url",
            "constructor_kwargs_http_client_binding",
            "single_openai_constructor",
            "openai_exact_constructor_kwargs_expansion",
        ),
        "D-137 production factory fields differ",
    )
    _require(
        factory["checked_in_official_base_url"] is None
        or isinstance(factory["checked_in_official_base_url"], str),
        "D-137 checked-in base URL type differs",
    )
    _require(
        factory["official_base_url_exact"]
        is (factory["checked_in_official_base_url"] == OFFICIAL_API_BASE_URL),
        "D-137 checked-in base URL flag differs",
    )
    for key in tuple(factory)[1:]:
        _require(type(factory[key]) is bool, f"D-137 production factory {key} differs")
    probe = observation["synthetic_probe"]
    expected_probe_keys = (
        "transport_kind",
        "fixed_nonsecret_placeholder_used",
        "ambient_credential_value_used",
        "official_base_url",
        "base_url_exact",
        "trust_env",
        "max_retries",
        "observed_max_retries_zero",
        "transport_dispatch_count",
        "openai_client_close_call_count",
        "http_client_fallback_close_call_count",
        "http_client_closed",
        "passed",
    )
    _require(isinstance(probe, dict) and tuple(probe) == expected_probe_keys, "D-137 probe fields")
    _require(probe["transport_kind"] == "httpx.MockTransport-reject-dispatch", "D-137 transport")
    _require(probe["fixed_nonsecret_placeholder_used"] is True, "D-137 fixed placeholder")
    _require(probe["ambient_credential_value_used"] is False, "D-137 ambient credential use")
    _require(probe["official_base_url"] == OFFICIAL_API_BASE_URL, "D-137 probe base URL")
    _require(probe["trust_env"] is False and probe["max_retries"] == 0, "D-137 probe routing")
    for key in (
        "base_url_exact",
        "observed_max_retries_zero",
        "http_client_closed",
        "passed",
    ):
        _require(type(probe[key]) is bool, f"D-137 probe {key} differs")
    for key in (
        "transport_dispatch_count",
        "openai_client_close_call_count",
        "http_client_fallback_close_call_count",
    ):
        _require(type(probe[key]) is int and probe[key] >= 0, f"D-137 probe {key}")
    expected_probe_pass = (
        probe["base_url_exact"] is True
        and probe["observed_max_retries_zero"] is True
        and probe["transport_dispatch_count"] == 0
        and probe["openai_client_close_call_count"] == 1
        and probe["http_client_fallback_close_call_count"] in (0, 1)
        and probe["http_client_closed"] is True
    )
    _require(probe["passed"] is expected_probe_pass, "D-137 probe pass flag differs")
    checks = _sdk_checks(observation)
    _require(observation["checks"] == checks, "D-137 SDK checks differ")
    blockers = _sdk_blockers(checks)
    _require(value["blockers"] == blockers, "D-137 SDK blockers differ")
    passed = not blockers
    _require(value["passed"] is passed, "D-137 SDK pass flag differs")
    _require(
        value["status"] == (SDK_READY_STATUS if passed else SDK_BLOCKED_STATUS),
        "D-137 SDK status differs",
    )
    expected_activity = {
        "dynamic_module_import_count": 2,
        "find_module_spec_count": 2,
        "python_executable_file_binding_count": 2,
        "sdk_module_file_binding_count": 4,
        "distribution_version_observation_count": 2,
        "locked_version_source_read_count": 2,
        "checked_in_factory_source_read_count": 1,
        "environment_presence_check_count": 3,
        "environment_value_read_count": 0,
        "dotenv_read_count": 0,
        "synthetic_transport_dispatch_count": probe["transport_dispatch_count"],
        "network_call_count": 0,
        "provider_evaluator_or_agent_call_count": 0,
        "openai_client_close_call_count": probe["openai_client_close_call_count"],
        "http_client_fallback_close_call_count": probe["http_client_fallback_close_call_count"],
        "http_client_closed": probe["http_client_closed"],
    }
    _require(value["activity"] == expected_activity, "D-137 SDK activity differs")
    return value


__all__ = [
    "APPROVED_DOCKER_CLI_BUILD",
    "APPROVED_DOCKER_CLI_FILE_BYTES",
    "APPROVED_DOCKER_CLI_FILE_SHA256",
    "APPROVED_DOCKER_CLI_PATH",
    "APPROVED_DOCKER_CLI_VERSION",
    "BoundedCommandResult",
    "D137NoCallPreflightError",
    "D137_FIXED_TEMP_ROOT",
    "DOCKER_BLOCKED_STATUS",
    "DOCKER_COMMAND_TIMEOUT_SECONDS",
    "DOCKER_OBSERVATION_SCHEMA",
    "DOCKER_PHASE",
    "DOCKER_READY_STATUS",
    "DockerObservationDependencies",
    "EXACT_DOCKER_IMAGES",
    "LOCAL_DOCKER_ENDPOINT",
    "MAX_DOCKER_OUTPUT_BYTES",
    "OFFICIAL_API_BASE_URL",
    "SDK_BLOCKED_STATUS",
    "SDK_ENVIRONMENT_NAMES",
    "SDK_OBSERVATION_SCHEMA",
    "SDK_PHASE",
    "SDK_READY_STATUS",
    "SDKObservationDependencies",
    "run_d137_docker_no_call_preflight_observation",
    "run_d137_sdk_no_call_preflight_observation",
    "validate_d137_docker_no_call_preflight_observation",
    "validate_d137_sdk_no_call_preflight_observation",
]
