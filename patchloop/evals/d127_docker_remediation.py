"""Exact Docker Desktop remediation used by the D-126 successor gate.

The public operation in this module may start Docker Desktop and pull only the
two digest-pinned evaluator images explicitly authorized by the user.  It never
creates or starts a container and never runs an image workload.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from patchloop.errors import ContractError
from patchloop.evals import d126_clean_source_pricing_no_call_preflight as d126
from patchloop.util import sha256_bytes

APPROVED_CLI_BYTES = 43_095_472
APPROVED_CLI_SHA256 = "sha256:8985cd8ac002c3240b5aa48fe401fcb55dca5d849b537e3c835564e8e8c49a70"
APPROVED_CLI_VERSION = "29.6.2"
APPROVED_CLI_BUILD = "dfc4efb"
OBSERVED_DESKTOP_BYTES = 15_142_320
OBSERVED_DESKTOP_SHA256 = "sha256:531781fa62cd8fa58023eff5aecb01ed88a93574f79696fd8fe327dfe1ff93e6"
DOCKER_IMAGES = d126.DOCKER_IMAGES
LOCAL_DOCKER_ENDPOINT = d126.LOCAL_DOCKER_ENDPOINT
IMAGE_PROJECTION_FORMAT = '{"Id":{{json .Id}},"RepoDigests":{{json .RepoDigests}}}'
MAX_OUTPUT_BYTES = 64 * 1024
MAX_REPO_DIGESTS = 128
POLL_INTERVAL_SECONDS = 3
MAX_DAEMON_POLLS = 60
ALLOW_DAEMON_START_WITH_UNVERIFIED_RESTART_STATE = False
DAEMON_START_SKIPPED_REASON = "preexisting-container-auto-restart-state-unverified"

_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")
_REPO_DIGEST = re.compile(r"[^\x00-\x20\x7f]+@sha256:[0-9a-f]{64}")
_CLI_VERSION = re.compile(r"Docker version ([0-9]+\.[0-9]+\.[0-9]+), build ([0-9A-Za-z.-]+)\r?\n?")
_DAEMON_VERSION = re.compile(r"[0-9]+(?:\.[0-9]+){1,3}(?:[-+][0-9A-Za-z.-]+)?")
_ACTIVE_DOCKER_CONFIG: ContextVar[str | None] = ContextVar(
    "d127_active_docker_config",
    default=None,
)


class D127DockerRemediationError(ContractError):
    """Raised when exact Docker remediation cannot proceed safely."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D127DockerRemediationError(message)


def _local_app_data() -> Path:
    value = os.environ.get("LOCALAPPDATA")
    _require(bool(value), "D-127 LOCALAPPDATA is unavailable")
    return Path(str(value))


def docker_cli_path() -> Path:
    return _local_app_data() / "Programs/DockerDesktop/resources/bin/docker.exe"


def docker_desktop_path() -> Path:
    return _local_app_data() / "Programs/DockerDesktop/Docker Desktop.exe"


def _file_binding(path: Path, *, label: str) -> dict[str, Any]:
    try:
        binding = d126._external_file_binding(path, label=label)
    except d126.D126PreflightError as exc:
        raise D127DockerRemediationError(str(exc).replace("D-126", "D-127")) from exc
    return binding


def approved_cli_binding() -> dict[str, Any]:
    binding = _file_binding(docker_cli_path(), label="Docker CLI")
    _require(binding["file_bytes"] == APPROVED_CLI_BYTES, "D-127 Docker CLI bytes differ")
    _require(binding["file_sha256"] == APPROVED_CLI_SHA256, "D-127 Docker CLI SHA differs")
    return binding


def observed_desktop_binding() -> dict[str, Any]:
    binding = _file_binding(docker_desktop_path(), label="Docker Desktop launcher")
    _require(
        binding["file_bytes"] == OBSERVED_DESKTOP_BYTES,
        "D-127 Docker Desktop launcher bytes differ",
    )
    _require(
        binding["file_sha256"] == OBSERVED_DESKTOP_SHA256,
        "D-127 Docker Desktop launcher SHA differs",
    )
    return binding


def _minimal_environment(*, daemon: bool) -> dict[str, str]:
    allowed = (
        ("SYSTEMROOT", "WINDIR", "LOCALAPPDATA", "TEMP", "TMP")
        if daemon
        else ("SYSTEMROOT", "WINDIR", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP")
    )
    environment = {name: value for name in allowed if (value := os.environ.get(name))}
    if daemon:
        docker_config = _ACTIVE_DOCKER_CONFIG.get()
        _require(docker_config is not None, "D-127 isolated Docker config is unavailable")
        environment["DOCKER_HOST"] = LOCAL_DOCKER_ENDPOINT
        environment["DOCKER_CONFIG"] = docker_config
    return environment


@contextmanager
def _isolated_docker_config():
    with tempfile.TemporaryDirectory(prefix="patchloop-d127-docker-config-") as selected:
        path = Path(selected).resolve(strict=True)
        _require(path.is_dir() and not any(path.iterdir()), "D-127 Docker config is not empty")
        _require(not d126._is_linklike(path), "D-127 Docker config is linklike")
        token = _ACTIVE_DOCKER_CONFIG.set(str(path))
        try:
            yield
        finally:
            _ACTIVE_DOCKER_CONFIG.reset(token)


class _Capture:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.prefix = bytearray()
        self.total = 0
        self.digest = hashlib.sha256()

    def drain(self, stream: BinaryIO) -> None:
        try:
            while True:
                chunk = stream.read(8 * 1024)
                if not chunk:
                    break
                self.total += len(chunk)
                self.digest.update(chunk)
                remaining = self.limit - len(self.prefix)
                if remaining > 0:
                    self.prefix.extend(chunk[:remaining])
        except (OSError, ValueError):
            # The caller closes both pipes only to break readers which failed to
            # reach EOF after the process exited; that path is rejected below.
            return


@dataclass(frozen=True)
class BoundedCommandResult:
    argv: tuple[str, ...]
    return_code: int | None
    timed_out: bool
    stdout_prefix: bytes
    stderr_prefix: bytes
    stdout_bytes: int
    stderr_bytes: int
    stdout_sha256: str
    stderr_sha256: str

    @property
    def within_bound(self) -> bool:
        return self.stdout_bytes <= MAX_OUTPUT_BYTES and self.stderr_bytes <= MAX_OUTPUT_BYTES

    def summary(self, role: str) -> dict[str, Any]:
        return {
            "role": role,
            "argv_contract": [Path(self.argv[0]).name, *self.argv[1:]],
            "return_code": self.return_code,
            "timed_out": self.timed_out,
            "stdout_bytes": self.stdout_bytes,
            "stdout_sha256": self.stdout_sha256,
            "stderr_bytes": self.stderr_bytes,
            "stderr_sha256": self.stderr_sha256,
            "stdout_within_bound": self.stdout_bytes <= MAX_OUTPUT_BYTES,
            "stderr_within_bound": self.stderr_bytes <= MAX_OUTPUT_BYTES,
            "raw_stdout_persisted": False,
            "raw_stderr_persisted": False,
        }


def _startupinfo() -> subprocess.STARTUPINFO | None:  # type: ignore[name-defined]
    if os.name != "nt":
        return None
    info = subprocess.STARTUPINFO()  # type: ignore[attr-defined]
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
    info.wShowWindow = subprocess.SW_HIDE  # type: ignore[attr-defined]
    return info


def _run_bounded(
    argv: list[str],
    *,
    environment: dict[str, str],
    timeout_seconds: int,
) -> BoundedCommandResult:
    process = subprocess.Popen(  # noqa: S603
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        env=environment,
        startupinfo=_startupinfo(),
    )
    _require(process.stdout is not None and process.stderr is not None, "D-127 pipes unavailable")
    stdout = _Capture(MAX_OUTPUT_BYTES)
    stderr = _Capture(MAX_OUTPUT_BYTES)
    threads = (
        threading.Thread(target=stdout.drain, args=(process.stdout,), daemon=True),
        threading.Thread(target=stderr.drain, args=(process.stderr,), daemon=True),
    )
    for thread in threads:
        thread.start()
    timed_out = False
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        process.wait()
    for thread in threads:
        thread.join(timeout=5)
    readers_settled = all(not thread.is_alive() for thread in threads)
    if not readers_settled:
        process.stdout.close()
        process.stderr.close()
        for thread in threads:
            thread.join(timeout=1)
    _require(readers_settled, "D-127 command output readers did not settle")
    return BoundedCommandResult(
        argv=tuple(argv),
        return_code=process.returncode,
        timed_out=timed_out,
        stdout_prefix=bytes(stdout.prefix),
        stderr_prefix=bytes(stderr.prefix),
        stdout_bytes=stdout.total,
        stderr_bytes=stderr.total,
        stdout_sha256="sha256:" + stdout.digest.hexdigest(),
        stderr_sha256="sha256:" + stderr.digest.hexdigest(),
    )


def _docker_command(*tail: str, timeout_seconds: int = 30) -> BoundedCommandResult:
    before = approved_cli_binding()
    cli = str(docker_cli_path().resolve(strict=True))
    result = _run_bounded(
        [cli, *tail],
        environment=_minimal_environment(daemon=True),
        timeout_seconds=timeout_seconds,
    )
    after = approved_cli_binding()
    _require(before == after, "D-127 Docker CLI changed across command execution")
    return result


def _daemon_projection(result: BoundedCommandResult) -> dict[str, str] | None:
    if (
        result.return_code != 0
        or result.timed_out
        or not result.within_bound
        or result.stderr_bytes
    ):
        return None
    try:
        payload = json.loads(result.stdout_prefix.decode("utf-8").rstrip("\r\n"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or tuple(payload) != (
        "ClientVersion",
        "ServerVersion",
        "ServerOs",
        "ServerArch",
    ):
        return None
    if not all(isinstance(value, str) and 0 < len(value) <= 64 for value in payload.values()):
        return None
    if payload["ServerOs"] != "linux" or payload["ServerArch"] != "amd64":
        return None
    return payload


def _repo_aliases(requested: str) -> frozenset[str]:
    aliases = {requested}
    if requested.startswith("docker.io/"):
        aliases.add(requested.removeprefix("docker.io/"))
    return frozenset(aliases)


def _image_projection(result: BoundedCommandResult, image: str) -> dict[str, Any] | None:
    if (
        result.return_code != 0
        or result.timed_out
        or not result.within_bound
        or result.stderr_bytes
    ):
        return None
    try:
        payload = json.loads(result.stdout_prefix.decode("utf-8").rstrip("\r\n"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or tuple(payload) != ("Id", "RepoDigests"):
        return None
    config_id = payload["Id"]
    repo_digests = payload["RepoDigests"]
    if not isinstance(config_id, str) or _IMAGE_ID.fullmatch(config_id) is None:
        return None
    if (
        not isinstance(repo_digests, list)
        or len(repo_digests) > MAX_REPO_DIGESTS
        or len(repo_digests) != len(set(repo_digests))
        or not all(
            isinstance(value, str)
            and len(value.encode("utf-8")) <= 512
            and _REPO_DIGEST.fullmatch(value) is not None
            for value in repo_digests
        )
    ):
        return None
    matches = sorted(set(repo_digests).intersection(_repo_aliases(image)))
    if len(matches) != 1:
        return None
    return {
        "requested_repo_digest": image,
        "requested_digest": image.rsplit("@", 1)[1],
        "config_id": config_id,
        "repo_digests": sorted(repo_digests),
        "matched_repo_digest": matches[0],
    }


def _confirmed_missing_projection(
    result: BoundedCommandResult,
    image: str,
) -> dict[str, Any] | None:
    if (
        result.return_code != 1
        or result.timed_out
        or not result.within_bound
    ):
        return None
    observed = (
        result.stdout_bytes,
        result.stdout_sha256,
        result.stderr_bytes,
        result.stderr_sha256,
    )
    if observed not in _allowed_missing_output_bindings(image):
        return None
    if (
        result.stdout_bytes != len(result.stdout_prefix)
        or result.stdout_sha256 != sha256_bytes(result.stdout_prefix)
        or result.stderr_bytes != len(result.stderr_prefix)
        or result.stderr_sha256 != sha256_bytes(result.stderr_prefix)
    ):
        return None
    return {
        "state": "confirmed-absent",
        "requested_repo_digest": image,
        "absence_code": "exact-docker-no-such-image",
        "stdout_bytes": result.stdout_bytes,
        "stdout_sha256": result.stdout_sha256,
        "stderr_bytes": result.stderr_bytes,
        "stderr_sha256": result.stderr_sha256,
    }


def _allowed_missing_output_bindings(image: str) -> frozenset[tuple[int, str, int, str]]:
    stdout_variants = (b"", b"\n", b"[]\n")
    base = f"Error response from daemon: No such image: {image}".encode()
    stderr_variants = (base, base + b"\n", base + b"\r\n")
    return frozenset(
        (len(stdout), sha256_bytes(stdout), len(stderr), sha256_bytes(stderr))
        for stdout in stdout_variants
        for stderr in stderr_variants
    )


def _image_is_present(value: Any) -> bool:
    return isinstance(value, dict) and "config_id" in value


def _image_is_confirmed_absent(value: Any) -> bool:
    return isinstance(value, dict) and value.get("state") == "confirmed-absent"


def _observe_readiness() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    version = _docker_command("version", "--format", d126.DOCKER_VERSION_FORMAT)
    rows = [version.summary("daemon-version")]
    daemon = _daemon_projection(version)
    images: dict[str, Any] = {}
    for index, image in enumerate(DOCKER_IMAGES):
        result = _docker_command(
            "image",
            "inspect",
            "--format",
            IMAGE_PROJECTION_FORMAT,
            image,
        )
        rows.append(result.summary(f"image-{'moto' if index == 0 else 'babel'}"))
        projection = _image_projection(result, image)
        if projection is None:
            projection = _confirmed_missing_projection(result, image)
        images["moto" if index == 0 else "babel"] = projection
    return {
        "daemon": daemon,
        "images": images,
        "passed": daemon is not None and all(_image_is_present(value) for value in images.values()),
    }, rows


def observe_docker_readiness() -> dict[str, Any]:
    """Return one exact read-only local-daemon/image readiness snapshot."""

    with _isolated_docker_config():
        approved_cli_binding()
        observation, commands = _observe_readiness()
    return {
        "schema_version": "d127-docker-readiness-snapshot-v1",
        "forced_daemon_endpoint": LOCAL_DOCKER_ENDPOINT,
        "observation": observation,
        "commands": commands,
        "docker_cli_command_count": len(commands),
        "read_only_daemon_or_image_call_count": len(commands),
        "container_create_start_run_exec_count": 0,
        "docker_workload_or_mutating_call_count": 0,
        "raw_stdout_or_stderr_persisted": False,
    }


def _launch_desktop() -> tuple[bool, str | None]:
    try:
        subprocess.Popen(  # noqa: S603
            [str(docker_desktop_path().resolve(strict=True))],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            env=_minimal_environment(daemon=False),
            startupinfo=_startupinfo(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, type(exc).__name__
    return True, None


def remediate_docker_environment() -> dict[str, Any]:
    """Start the local daemon and pull only absent exact evaluator digests."""

    with _isolated_docker_config():
        cli_before = approved_cli_binding()
        before, before_rows = _observe_readiness()
        desktop_start_count = 0
        desktop_binding_before: dict[str, Any] | None = None
        desktop_binding_after: dict[str, Any] | None = None
        desktop_start_error: str | None = None
        desktop_start_skipped_reason: str | None = None
        daemon_poll_count = 0
        poll_rows: list[dict[str, Any]] = []
        current = before
        if before["daemon"] is None:
            if not ALLOW_DAEMON_START_WITH_UNVERIFIED_RESTART_STATE:
                desktop_start_skipped_reason = DAEMON_START_SKIPPED_REASON
            else:
                desktop_binding_before = observed_desktop_binding()
                desktop_start_count = 1
                started, desktop_start_error = _launch_desktop()
                desktop_binding_after = observed_desktop_binding()
                _require(
                    desktop_binding_before == desktop_binding_after,
                    "D-127 Docker Desktop launcher changed across launch",
                )
                if started:
                    for _ in range(MAX_DAEMON_POLLS):
                        time.sleep(POLL_INTERVAL_SECONDS)
                        daemon_poll_count += 1
                        poll = _docker_command("version", "--format", d126.DOCKER_VERSION_FORMAT)
                        poll_rows.append(poll.summary("daemon-version-poll"))
                        daemon = _daemon_projection(poll)
                        if daemon is not None:
                            current, rows = _observe_readiness()
                            poll_rows.extend(rows)
                            break

        pull_rows: list[dict[str, Any]] = []
        pulled_images: list[str] = []
        image_store_mutation_count = 0
        if current["daemon"] is not None:
            for index, image in enumerate(DOCKER_IMAGES):
                key = "moto" if index == 0 else "babel"
                if not _image_is_confirmed_absent(current["images"].get(key)):
                    continue
                result = _docker_command(
                    "image",
                    "pull",
                    "--quiet",
                    "--platform",
                    "linux/amd64",
                    image,
                    timeout_seconds=1_200,
                )
                pull_rows.append(result.summary(f"pull-{key}"))
                image_store_mutation_count += 1
                if result.return_code == 0 and not result.timed_out and result.within_bound:
                    pulled_images.append(image)

        after, after_rows = _observe_readiness()
        cli_after = approved_cli_binding()
    _require(cli_before == cli_after, "D-127 Docker CLI changed during remediation")
    command_rows = [*before_rows, *poll_rows, *pull_rows, *after_rows]
    every_output_within_bound = all(
        row["stdout_within_bound"] and row["stderr_within_bound"] for row in command_rows
    )
    pull_commands_succeeded = all(
        row["return_code"] == 0
        and row["timed_out"] is False
        and row["stdout_within_bound"]
        and row["stderr_within_bound"]
        and row["stderr_bytes"] == 0
        for row in pull_rows
    )
    passed = (
        after["passed"]
        and desktop_start_error is None
        and every_output_within_bound
        and pull_commands_succeeded
        and len(pulled_images) == len(pull_rows)
    )
    return {
        "schema_version": "d127-docker-remediation-observation-v1",
        "approved_cli_binding_before": cli_before,
        "approved_cli_binding_after": cli_after,
        "docker_desktop_binding_before": desktop_binding_before,
        "docker_desktop_binding_after": desktop_binding_after,
        "desktop_start_count": desktop_start_count,
        "desktop_start_error_code": desktop_start_error,
        "desktop_start_skipped_reason": desktop_start_skipped_reason,
        "daemon_poll_count": daemon_poll_count,
        "image_store_mutation_count": image_store_mutation_count,
        "pulled_images": pulled_images,
        "exact_authorized_images": list(DOCKER_IMAGES),
        "before": before,
        "pull_basis": current,
        "after": after,
        "commands": command_rows,
        "docker_cli_command_count": (
            len(before_rows) + len(poll_rows) + len(pull_rows) + len(after_rows)
        ),
        "container_create_start_run_exec_count": 0,
        "docker_workload_call_count": 0,
        "every_output_within_bound": every_output_within_bound,
        "pull_commands_succeeded": pull_commands_succeeded,
        "passed": passed,
        "raw_stdout_or_stderr_persisted": False,
    }


def _validate_file_binding(value: Any, *, desktop: bool) -> None:
    _require(isinstance(value, dict), "D-127 executable binding is not an object")
    _require(
        tuple(value) == ("file_name", "file_bytes", "file_sha256", "linklike"),
        "D-127 executable binding fields differ",
    )
    expected_name = "Docker Desktop.exe" if desktop else "docker.exe"
    expected_bytes = OBSERVED_DESKTOP_BYTES if desktop else APPROVED_CLI_BYTES
    expected_sha = OBSERVED_DESKTOP_SHA256 if desktop else APPROVED_CLI_SHA256
    _require(value["file_name"].casefold() == expected_name.casefold(), "D-127 name differs")
    _require(value["file_bytes"] == expected_bytes, "D-127 executable bytes differ")
    _require(value["file_sha256"] == expected_sha, "D-127 executable SHA differs")
    _require(value["linklike"] is False, "D-127 executable link claim differs")


def _validate_command_row(row: Any) -> None:
    expected_keys = (
        "role",
        "argv_contract",
        "return_code",
        "timed_out",
        "stdout_bytes",
        "stdout_sha256",
        "stderr_bytes",
        "stderr_sha256",
        "stdout_within_bound",
        "stderr_within_bound",
        "raw_stdout_persisted",
        "raw_stderr_persisted",
    )
    _require(isinstance(row, dict) and tuple(row) == expected_keys, "D-127 command fields differ")
    exact_role_argv = {
        "daemon-version": ("version", "--format", d126.DOCKER_VERSION_FORMAT),
        "daemon-version-poll": ("version", "--format", d126.DOCKER_VERSION_FORMAT),
        "image-moto": (
            "image",
            "inspect",
            "--format",
            IMAGE_PROJECTION_FORMAT,
            DOCKER_IMAGES[0],
        ),
        "image-babel": (
            "image",
            "inspect",
            "--format",
            IMAGE_PROJECTION_FORMAT,
            DOCKER_IMAGES[1],
        ),
        "pull-moto": (
            "image",
            "pull",
            "--quiet",
            "--platform",
            "linux/amd64",
            DOCKER_IMAGES[0],
        ),
        "pull-babel": (
            "image",
            "pull",
            "--quiet",
            "--platform",
            "linux/amd64",
            DOCKER_IMAGES[1],
        ),
    }
    _require(row["role"] in exact_role_argv, "D-127 command role differs")
    argv = row["argv_contract"]
    _require(
        isinstance(argv, list) and argv and argv[0].casefold() == "docker.exe", "D-127 argv differs"
    )
    _require(
        tuple(argv[1:]) == exact_role_argv[row["role"]],
        "D-127 Docker argv does not match its role",
    )
    _require(
        row["return_code"] is None or type(row["return_code"]) is int,
        "D-127 return code differs",
    )
    _require(type(row["timed_out"]) is bool, "D-127 timeout flag differs")
    for prefix in ("stdout", "stderr"):
        _require(
            type(row[f"{prefix}_bytes"]) is int and row[f"{prefix}_bytes"] >= 0,
            "D-127 byte count differs",
        )
        _require(
            isinstance(row[f"{prefix}_sha256"], str)
            and re.fullmatch(r"sha256:[0-9a-f]{64}", row[f"{prefix}_sha256"]) is not None,
            "D-127 output SHA differs",
        )
        _require(
            row[f"{prefix}_within_bound"] is (row[f"{prefix}_bytes"] <= MAX_OUTPUT_BYTES),
            "D-127 bound flag differs",
        )
        _require(row[f"raw_{prefix}_persisted"] is False, "D-127 raw-output claim differs")


def _validate_readiness(value: Any) -> None:
    _require(isinstance(value, dict), "D-127 readiness is not an object")
    _require(tuple(value) == ("daemon", "images", "passed"), "D-127 readiness fields differ")
    daemon = value["daemon"]
    if daemon is not None:
        _require(
            isinstance(daemon, dict)
            and tuple(daemon) == ("ClientVersion", "ServerVersion", "ServerOs", "ServerArch")
            and daemon["ClientVersion"] == APPROVED_CLI_VERSION
            and isinstance(daemon["ServerVersion"], str)
            and _DAEMON_VERSION.fullmatch(daemon["ServerVersion"]) is not None
            and daemon["ServerOs"] == "linux"
            and daemon["ServerArch"] == "amd64",
            "D-127 daemon projection differs",
        )
    images = value["images"]
    _require(
        isinstance(images, dict) and tuple(images) == ("moto", "babel"), "D-127 image fields differ"
    )
    for key, image in zip(("moto", "babel"), DOCKER_IMAGES, strict=True):
        projection = images[key]
        if projection is None:
            continue
        if _image_is_confirmed_absent(projection):
            _require(
                tuple(projection)
                == (
                    "state",
                    "requested_repo_digest",
                    "absence_code",
                    "stdout_bytes",
                    "stdout_sha256",
                    "stderr_bytes",
                    "stderr_sha256",
                )
                and projection["requested_repo_digest"] == image
                and projection["absence_code"] == "exact-docker-no-such-image"
                and (
                    projection["stdout_bytes"],
                    projection["stdout_sha256"],
                    projection["stderr_bytes"],
                    projection["stderr_sha256"],
                )
                in _allowed_missing_output_bindings(image),
                "D-127 confirmed-absence projection differs",
            )
            continue
        _require(
            isinstance(projection, dict)
            and tuple(projection)
            == (
                "requested_repo_digest",
                "requested_digest",
                "config_id",
                "repo_digests",
                "matched_repo_digest",
            ),
            "D-127 image projection fields differ",
        )
        _require(projection["requested_repo_digest"] == image, "D-127 requested image differs")
        _require(
            projection["requested_digest"] == image.rsplit("@", 1)[1],
            "D-127 requested digest differs",
        )
        _require(
            isinstance(projection["config_id"], str)
            and _IMAGE_ID.fullmatch(projection["config_id"]) is not None,
            "D-127 config ID differs",
        )
        repo_digests = projection["repo_digests"]
        _require(
            isinstance(repo_digests, list)
            and len(repo_digests) <= MAX_REPO_DIGESTS
            and repo_digests == sorted(repo_digests)
            and len(repo_digests) == len(set(repo_digests))
            and all(
                isinstance(item, str)
                and len(item.encode("utf-8")) <= 512
                and _REPO_DIGEST.fullmatch(item) is not None
                for item in repo_digests
            ),
            "D-127 RepoDigest projection differs",
        )
        _require(
            projection["matched_repo_digest"] in repo_digests
            and projection["matched_repo_digest"] in _repo_aliases(image)
            and len(set(repo_digests).intersection(_repo_aliases(image))) == 1,
            "D-127 matched RepoDigest differs",
        )
    expected_passed = daemon is not None and all(
        _image_is_present(images[key]) for key in ("moto", "babel")
    )
    _require(value["passed"] is expected_passed, "D-127 readiness result differs")


def _validate_readiness_rows(value: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    _require(len(rows) == 3, "D-127 readiness command count differs")
    _require(
        [row["role"] for row in rows] == ["daemon-version", "image-moto", "image-babel"],
        "D-127 readiness command order differs",
    )
    projections = (
        value["daemon"],
        (
            None
            if not _image_is_present(value["images"]["moto"])
            else {
                "Id": value["images"]["moto"]["config_id"],
                "RepoDigests": value["images"]["moto"]["repo_digests"],
            }
        ),
        (
            None
            if not _image_is_present(value["images"]["babel"])
            else {
                "Id": value["images"]["babel"]["config_id"],
                "RepoDigests": value["images"]["babel"]["repo_digests"],
            }
        ),
    )
    for row, projection in zip(rows, projections, strict=True):
        image_key = None
        if row["role"] == "image-moto":
            image_key = "moto"
        elif row["role"] == "image-babel":
            image_key = "babel"
        if image_key is not None and _image_is_confirmed_absent(value["images"][image_key]):
            absent = value["images"][image_key]
            _require(
                row["return_code"] == 1
                and row["timed_out"] is False
                and row["stdout_bytes"] == absent["stdout_bytes"]
                and row["stdout_sha256"] == absent["stdout_sha256"]
                and row["stderr_bytes"] == absent["stderr_bytes"]
                and row["stderr_sha256"] == absent["stderr_sha256"],
                "D-127 confirmed absence is not bound to command output",
            )
            continue
        if projection is None:
            continue
        expected_stdout = (json.dumps(projection, separators=(",", ":")) + "\n").encode()
        _require(
            row["return_code"] == 0
            and row["timed_out"] is False
            and row["stderr_bytes"] == 0
            and row["stderr_sha256"] == sha256_bytes(b"")
            and row["stdout_bytes"] == len(expected_stdout)
            and row["stdout_sha256"] == sha256_bytes(expected_stdout),
            "D-127 readiness projection is not bound to command output",
        )


def validate_docker_remediation_observation(value: Any) -> dict[str, Any]:
    """Replay the exact remediation evidence without invoking Docker."""

    expected_keys = (
        "schema_version",
        "approved_cli_binding_before",
        "approved_cli_binding_after",
        "docker_desktop_binding_before",
        "docker_desktop_binding_after",
        "desktop_start_count",
        "desktop_start_error_code",
        "desktop_start_skipped_reason",
        "daemon_poll_count",
        "image_store_mutation_count",
        "pulled_images",
        "exact_authorized_images",
        "before",
        "pull_basis",
        "after",
        "commands",
        "docker_cli_command_count",
        "container_create_start_run_exec_count",
        "docker_workload_call_count",
        "every_output_within_bound",
        "pull_commands_succeeded",
        "passed",
        "raw_stdout_or_stderr_persisted",
    )
    _require(
        isinstance(value, dict) and tuple(value) == expected_keys, "D-127 remediation fields differ"
    )
    _require(
        value["schema_version"] == "d127-docker-remediation-observation-v1",
        "D-127 remediation schema differs",
    )
    _validate_file_binding(value["approved_cli_binding_before"], desktop=False)
    _validate_file_binding(value["approved_cli_binding_after"], desktop=False)
    _require(
        value["approved_cli_binding_before"] == value["approved_cli_binding_after"],
        "D-127 Docker CLI stability differs",
    )
    _require(value["desktop_start_count"] in (0, 1), "D-127 desktop start count differs")
    if value["desktop_start_count"] == 0:
        _require(
            value["docker_desktop_binding_before"] is None
            and value["docker_desktop_binding_after"] is None,
            "D-127 unexpected desktop binding",
        )
    else:
        _validate_file_binding(value["docker_desktop_binding_before"], desktop=True)
        _validate_file_binding(value["docker_desktop_binding_after"], desktop=True)
        _require(
            value["docker_desktop_binding_before"]
            == value["docker_desktop_binding_after"],
            "D-127 Docker Desktop launcher stability differs",
        )
    _require(
        value["desktop_start_error_code"] is None
        or (
            isinstance(value["desktop_start_error_code"], str)
            and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", value["desktop_start_error_code"])
            is not None
        ),
        "D-127 desktop error code differs",
    )
    _require(
        value["desktop_start_skipped_reason"] in (None, DAEMON_START_SKIPPED_REASON),
        "D-127 desktop start skip reason differs",
    )
    _require(
        type(value["daemon_poll_count"]) is int and value["daemon_poll_count"] >= 0,
        "D-127 poll count differs",
    )
    _require(
        value["exact_authorized_images"] == list(DOCKER_IMAGES), "D-127 authorized images differ"
    )
    _require(
        isinstance(value["pulled_images"], list)
        and len(value["pulled_images"]) == len(set(value["pulled_images"]))
        and set(value["pulled_images"]).issubset(DOCKER_IMAGES),
        "D-127 pulled images differ",
    )
    _validate_readiness(value["before"])
    _validate_readiness(value["pull_basis"])
    _validate_readiness(value["after"])
    rows = value["commands"]
    _require(isinstance(rows, list) and len(rows) >= 6, "D-127 command rows differ")
    for row in rows:
        _validate_command_row(row)
    before_rows = rows[:3]
    after_rows = rows[-3:]
    _validate_readiness_rows(value["before"], before_rows)
    _validate_readiness_rows(value["after"], after_rows)
    middle_rows = rows[3:-3]
    cursor = 0
    while cursor < len(middle_rows) and middle_rows[cursor]["role"] == "daemon-version-poll":
        cursor += 1
    poll_rows = middle_rows[:cursor]
    intermediate_rows: list[dict[str, Any]] = []
    if (
        cursor + 3 <= len(middle_rows)
        and [row["role"] for row in middle_rows[cursor : cursor + 3]]
        == ["daemon-version", "image-moto", "image-babel"]
    ):
        intermediate_rows = middle_rows[cursor : cursor + 3]
        cursor += 3
    pull_rows = middle_rows[cursor:]
    _require(
        [row["role"] for row in pull_rows]
        in ([], ["pull-moto"], ["pull-babel"], ["pull-moto", "pull-babel"]),
        "D-127 pull command order differs",
    )
    _require(
        value["daemon_poll_count"] == len(poll_rows) <= MAX_DAEMON_POLLS,
        "D-127 poll rows differ",
    )
    if value["desktop_start_count"] == 0:
        _require(
            not poll_rows and not intermediate_rows and value["desktop_start_error_code"] is None,
            "D-127 unexpected no-start command phase",
        )
        if value["before"]["daemon"] is None:
            _require(
                value["desktop_start_skipped_reason"] == DAEMON_START_SKIPPED_REASON,
                "D-127 daemon-start authority blocker differs",
            )
        else:
            _require(
                value["desktop_start_skipped_reason"] is None,
                "D-127 unexpected daemon-start blocker",
            )
        _require(value["pull_basis"] == value["before"], "D-127 pull basis differs")
    else:
        _require(
            value["desktop_start_skipped_reason"] is None,
            "D-127 started daemon also claims a skip",
        )
        _require(value["before"]["daemon"] is None, "D-127 desktop start trigger differs")
        if value["desktop_start_error_code"] is None:
            _require(1 <= len(poll_rows) <= MAX_DAEMON_POLLS, "D-127 daemon polling differs")
            _require(
                not pull_rows or bool(intermediate_rows),
                "D-127 pulls occurred without a ready daemon observation",
            )
            if intermediate_rows:
                _validate_readiness_rows(value["pull_basis"], intermediate_rows)
            else:
                _require(value["pull_basis"] == value["before"], "D-127 pull basis differs")
        else:
            _require(
                not poll_rows and not intermediate_rows and not pull_rows,
                "D-127 commands followed a failed desktop start",
            )
            _require(value["pull_basis"] == value["before"], "D-127 pull basis differs")
    expected_pull_roles = (
        [
            f"pull-{key}"
            for key in ("moto", "babel")
            if _image_is_confirmed_absent(value["pull_basis"]["images"][key])
        ]
        if value["pull_basis"]["daemon"] is not None
        else []
    )
    _require(
        [row["role"] for row in pull_rows] == expected_pull_roles,
        "D-127 pull rows do not match images missing from the pull basis",
    )
    _require(value["image_store_mutation_count"] == len(pull_rows), "D-127 pull count differs")
    pull_image_by_role = {"pull-moto": DOCKER_IMAGES[0], "pull-babel": DOCKER_IMAGES[1]}
    successful_pulled_images = [
        pull_image_by_role[row["role"]]
        for row in pull_rows
        if row["return_code"] == 0
        and row["timed_out"] is False
        and row["stdout_within_bound"]
        and row["stderr_within_bound"]
        and row["stderr_bytes"] == 0
    ]
    _require(
        value["pulled_images"] == successful_pulled_images,
        "D-127 pulled images do not match successful pull rows",
    )
    _require(value["docker_cli_command_count"] == len(rows), "D-127 command count differs")
    _require(value["container_create_start_run_exec_count"] == 0, "D-127 container count differs")
    _require(value["docker_workload_call_count"] == 0, "D-127 workload count differs")
    within = all(row["stdout_within_bound"] and row["stderr_within_bound"] for row in rows)
    pulls_passed = all(
        row["return_code"] == 0
        and row["timed_out"] is False
        and row["stdout_within_bound"]
        and row["stderr_within_bound"]
        and row["stderr_bytes"] == 0
        for row in pull_rows
    )
    _require(value["every_output_within_bound"] is within, "D-127 output-bound result differs")
    _require(value["pull_commands_succeeded"] is pulls_passed, "D-127 pull result differs")
    expected_passed = (
        value["after"]["passed"]
        and value["desktop_start_error_code"] is None
        and within
        and pulls_passed
        and len(value["pulled_images"]) == len(pull_rows)
    )
    _require(value["passed"] is expected_passed, "D-127 remediation result differs")
    _require(value["raw_stdout_or_stderr_persisted"] is False, "D-127 raw-output boundary differs")
    return value


def validate_docker_readiness_snapshot(value: Any) -> dict[str, Any]:
    """Replay one read-only readiness snapshot without invoking Docker."""

    expected_keys = (
        "schema_version",
        "forced_daemon_endpoint",
        "observation",
        "commands",
        "docker_cli_command_count",
        "read_only_daemon_or_image_call_count",
        "container_create_start_run_exec_count",
        "docker_workload_or_mutating_call_count",
        "raw_stdout_or_stderr_persisted",
    )
    _require(
        isinstance(value, dict) and tuple(value) == expected_keys, "D-127 snapshot fields differ"
    )
    _require(
        value["schema_version"] == "d127-docker-readiness-snapshot-v1",
        "D-127 snapshot schema differs",
    )
    _require(
        value["forced_daemon_endpoint"] == LOCAL_DOCKER_ENDPOINT, "D-127 snapshot endpoint differs"
    )
    _validate_readiness(value["observation"])
    rows = value["commands"]
    _require(isinstance(rows, list) and len(rows) == 3, "D-127 snapshot rows differ")
    for row in rows:
        _validate_command_row(row)
    _require(
        [row["role"] for row in rows] == ["daemon-version", "image-moto", "image-babel"],
        "D-127 snapshot role order differs",
    )
    _require(value["observation"]["passed"] is True, "D-127 snapshot is not ready")
    projections = (
        value["observation"]["daemon"],
        {
            "Id": value["observation"]["images"]["moto"]["config_id"],
            "RepoDigests": value["observation"]["images"]["moto"]["repo_digests"],
        },
        {
            "Id": value["observation"]["images"]["babel"]["config_id"],
            "RepoDigests": value["observation"]["images"]["babel"]["repo_digests"],
        },
    )
    for row, projection in zip(rows, projections, strict=True):
        expected_stdout = (json.dumps(projection, separators=(",", ":")) + "\n").encode()
        _require(
            row["return_code"] == 0 and row["timed_out"] is False, "D-127 snapshot command failed"
        )
        _require(row["stderr_bytes"] == 0, "D-127 snapshot stderr differs")
        _require(row["stderr_sha256"] == sha256_bytes(b""), "D-127 snapshot stderr SHA differs")
        _require(row["stdout_bytes"] == len(expected_stdout), "D-127 snapshot stdout bytes differ")
        _require(
            row["stdout_sha256"] == sha256_bytes(expected_stdout),
            "D-127 snapshot stdout SHA differs",
        )
    _require(value["docker_cli_command_count"] == 3, "D-127 snapshot command count differs")
    _require(
        value["read_only_daemon_or_image_call_count"] == 3,
        "D-127 snapshot read-only count differs",
    )
    _require(
        value["container_create_start_run_exec_count"] == 0,
        "D-127 snapshot container count differs",
    )
    _require(
        value["docker_workload_or_mutating_call_count"] == 0,
        "D-127 snapshot workload count differs",
    )
    _require(
        value["raw_stdout_or_stderr_persisted"] is False, "D-127 snapshot raw-output claim differs"
    )
    return value


__all__ = [
    "APPROVED_CLI_BYTES",
    "APPROVED_CLI_SHA256",
    "APPROVED_CLI_VERSION",
    "DOCKER_IMAGES",
    "D127DockerRemediationError",
    "approved_cli_binding",
    "observe_docker_readiness",
    "remediate_docker_environment",
    "validate_docker_remediation_observation",
    "validate_docker_readiness_snapshot",
]
