from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from patchloop.memory import d121_hash_only_isolation_successor as d121

REPOSITORY = Path(__file__).resolve().parents[1]


def _sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _completed(
    command: Sequence[str],
    *,
    returncode: int = 0,
    stdout: bytes = b"",
    stderr: bytes = b"",
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(list(command), returncode, stdout, stderr)


def _write_copy(repository: Path, relative: str | Path) -> None:
    selected = Path(relative)
    source = REPOSITORY / selected
    target = repository / selected
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    assert isinstance(value, dict)
    return value


def _valid_inspect(*, container_id: str, container_name: str, host_path: str) -> dict[str, Any]:
    command = [
        "/usr/bin/env",
        "-i",
        "LANG=C.UTF-8",
        "LC_ALL=C.UTF-8",
        "PYTHONHASHSEED=0",
        "/usr/local/bin/python",
        "-I",
        "/opt/patchloop/probe_runner.py",
        "20",
    ]
    return {
        "Id": container_id,
        "Name": "/" + container_name,
        "Path": command[0],
        "Args": command[1:],
        "Image": d121.IMAGE_ID,
        "MountCount": 1,
        "Config": {
            "Cmd": command,
            "WorkingDir": "/",
            "User": "10001:10001",
            "Tty": False,
            "OpenStdin": True,
            "Labels": {
                "io.patchloop.managed": "d121-isolation-successor",
                "io.patchloop.role": "external-source-hash-only",
                "io.patchloop.probe-image": "v2",
            },
        },
        "State": {
            "Status": "created",
            "Running": False,
            "Paused": False,
            "Restarting": False,
            "Dead": False,
            "Pid": 0,
            "StartedAt": "0001-01-01T00:00:00Z",
        },
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "Privileged": False,
            "PidsLimit": 2,
            "CapDrop": ["ALL"],
            "CapAdd": None,
            "SecurityOpt": ["no-new-privileges"],
            "PidMode": "",
            "IpcMode": "private",
            "Devices": [],
            "DeviceRequests": None,
            "Binds": None,
            "Memory": 268_435_456,
            "NanoCpus": 1_000_000_000,
            "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
            "Tmpfs": {
                "/output": ("rw,noexec,nosuid,nodev,size=64k,uid=10001,gid=10001,mode=0700"),
                "/dev/shm": "ro,noexec,nosuid,nodev,size=64k,mode=0555",
            },
        },
        "Mounts": [
            {
                "Type": "bind",
                "Source": host_path,
                "Destination": "/input/source.parquet",
                "RW": False,
            }
        ],
    }


class FakeReadinessRunner:
    """An exact no-start Docker transcript that never opens a mounted path."""

    def __init__(
        self,
        *,
        missing_inspect_stdout: bytes = b"[]\n",
        image_returncode: int = 0,
        image_stdout: bytes | None = None,
        create_stdout: bytes | None = None,
        inspect_stdout: bytes | None = None,
        projection_mutate: Any | None = None,
    ) -> None:
        self.missing_inspect_stdout = missing_inspect_stdout
        self.image_returncode = image_returncode
        self.image_stdout = image_stdout
        self.create_stdout = create_stdout
        self.inspect_stdout = inspect_stdout
        self.projection_mutate = projection_mutate
        self.commands: list[tuple[list[str], bytes | None, int]] = []
        self.containers: dict[str, dict[str, str]] = {}

    @staticmethod
    def _mounted_source(command: Sequence[str]) -> str:
        mount = command[command.index("--mount") + 1]
        prefix = "type=bind,source="
        suffix = ",target=/input/source.parquet,readonly"
        assert mount.startswith(prefix) and mount.endswith(suffix)
        return mount[len(prefix) : -len(suffix)]

    def run(
        self,
        command: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        timeout_seconds: int = 30,
    ) -> subprocess.CompletedProcess[bytes]:
        argv = list(command)
        self.commands.append((argv, input_bytes, timeout_seconds))
        assert input_bytes is None
        operation = argv[1:]

        if operation[:2] == ["image", "inspect"]:
            if self.image_returncode:
                return _completed(argv, returncode=self.image_returncode, stderr=b"image failure")
            return _completed(
                argv,
                stdout=(
                    self.image_stdout
                    if self.image_stdout is not None
                    else (d121.IMAGE_ID + "\n").encode("ascii")
                ),
            )

        if operation[:2] == ["ps", "--all"]:
            filter_value = operation[operation.index("--filter") + 1]
            if filter_value.startswith("id="):
                selected = filter_value.removeprefix("id=")
                ids = [selected] if selected in self.containers else []
            elif filter_value == f"label={d121.MANAGED_LABEL}":
                ids = list(self.containers)
            else:  # pragma: no cover - any unexpected transcript is a test bug
                raise AssertionError(f"unexpected inventory filter: {filter_value}")
            return _completed(argv, stdout=b"".join(value.encode() + b"\n" for value in ids))

        if operation[0] == "create":
            name = operation[operation.index("--name") + 1]
            host_path = self._mounted_source(argv)
            container_id = hashlib.sha256(name.encode()).hexdigest()
            self.containers[container_id] = {"name": name, "host_path": host_path}
            return _completed(
                argv,
                stdout=(
                    self.create_stdout
                    if self.create_stdout is not None
                    else container_id.encode() + b"\n"
                ),
            )

        if operation[0] == "inspect":
            target = operation[-1]
            container_id = target if target in self.containers else None
            if container_id is None:
                container_id = next(
                    (value for value, row in self.containers.items() if row["name"] == target),
                    None,
                )
            container = self.containers.get(container_id) if container_id is not None else None
            if container is None:
                return _completed(
                    argv,
                    returncode=1,
                    stdout=self.missing_inspect_stdout,
                    stderr=b"Error: No such object\n",
                )
            value = _valid_inspect(
                container_id=container_id,
                container_name=container["name"],
                host_path=container["host_path"],
            )
            if self.projection_mutate is not None:
                self.projection_mutate(value)
            projection = d121._created_container_projection(value)
            return _completed(
                argv,
                stdout=(
                    self.inspect_stdout
                    if self.inspect_stdout is not None
                    else d121._inspect_projection_stdout(
                        projection,
                        exact_host_path=container["host_path"],
                    )
                ),
            )

        if operation[:2] == ["rm", "--force"]:
            container_id = operation[2]
            self.containers.pop(container_id, None)
            return _completed(argv, stdout=container_id.encode() + b"\n")

        raise AssertionError(f"unexpected fake Docker command: {argv!r}")


class FakeExecutionRunner:
    """A two-session successor transcript that never reads a mounted source."""

    def __init__(self, repository: Path) -> None:
        self.repository = repository.resolve()
        self.commands: list[tuple[list[str], bytes | None, int]] = []
        self.containers: dict[str, dict[str, Any]] = {}
        self.sources_by_path = {
            str((self.repository / source["path"]).resolve()).casefold(): source
            for source in d121.SOURCE_PLAN
        }

    @staticmethod
    def _mounted_source(command: Sequence[str]) -> str:
        mount = command[command.index("--mount") + 1]
        prefix = "type=bind,source="
        suffix = ",target=/input/source.parquet,readonly"
        assert mount.startswith(prefix) and mount.endswith(suffix)
        return mount[len(prefix) : -len(suffix)]

    def run(
        self,
        command: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        timeout_seconds: int = 30,
    ) -> subprocess.CompletedProcess[bytes]:
        argv = list(command)
        self.commands.append((argv, input_bytes, timeout_seconds))
        operation = argv[1:]

        if operation[:2] == ["image", "inspect"]:
            assert input_bytes is None
            return _completed(argv, stdout=(d121.IMAGE_ID + "\n").encode("ascii"))

        if operation[:2] == ["ps", "--all"]:
            assert input_bytes is None
            filter_value = operation[operation.index("--filter") + 1]
            if filter_value.startswith("id="):
                selected = filter_value.removeprefix("id=")
                ids = [selected] if selected in self.containers else []
            elif filter_value == f"label={d121.MANAGED_LABEL}":
                ids = list(self.containers)
            else:  # pragma: no cover - unexpected argv is a fixture defect
                raise AssertionError(f"unexpected inventory filter: {filter_value}")
            return _completed(argv, stdout=b"".join(value.encode() + b"\n" for value in ids))

        if operation[0] == "create":
            assert input_bytes is None
            name = operation[operation.index("--name") + 1]
            host_path = self._mounted_source(argv)
            source = self.sources_by_path[str(Path(host_path).resolve()).casefold()]
            container_id = hashlib.sha256(name.encode()).hexdigest()
            self.containers[container_id] = {
                "name": name,
                "host_path": host_path,
                "source": source,
            }
            return _completed(argv, stdout=container_id.encode() + b"\n")

        if operation[0] == "inspect":
            assert input_bytes is None
            target = operation[-1]
            container = self.containers.get(target)
            if container is None:
                return _completed(
                    argv,
                    returncode=1,
                    stdout=b"[]\n",
                    stderr=b"Error: No such object\n",
                )
            value = _valid_inspect(
                container_id=target,
                container_name=container["name"],
                host_path=container["host_path"],
            )
            projection = d121._created_container_projection(
                value,
                source_token="<exact-opaque-source>",
            )
            return _completed(
                argv,
                stdout=d121._inspect_projection_stdout(
                    projection,
                    exact_host_path=container["host_path"],
                ),
            )

        if operation[0] == "start":
            container_id = operation[-1]
            container = self.containers[container_id]
            source = container["source"]
            assert input_bytes == d121._probe_source(source)
            result = d121._expected_probe_result(source)
            return _completed(argv, stdout=d121._canonical_bytes(result) + b"\n")

        if operation[:2] == ["rm", "--force"]:
            assert input_bytes is None
            container_id = operation[2]
            self.containers.pop(container_id, None)
            return _completed(argv, stdout=container_id.encode() + b"\n")

        raise AssertionError(f"unexpected fake execution command: {argv!r}")


def _preparation_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    missing_inspect_stdout: bytes = b"[]\n",
    image_returncode: int = 0,
    image_stdout: bytes | None = None,
    create_stdout: bytes | None = None,
    inspect_stdout: bytes | None = None,
    projection_mutate: Any | None = None,
) -> tuple[Path, FakeReadinessRunner, Path]:
    for spec in d121.PROTECTED_FILE_SPECS:
        _write_copy(tmp_path, spec["path"])
    for relative in d121.IMPLEMENTATION_PATHS:
        _write_copy(tmp_path, relative)
    (tmp_path / "reports/memory-development").mkdir(parents=True, exist_ok=True)

    docker = tmp_path / "tools/docker.exe"
    docker.parent.mkdir(parents=True, exist_ok=True)
    docker_bytes = b"offline-fake-docker-cli-for-d121-readiness"
    docker.write_bytes(docker_bytes)
    monkeypatch.setattr(d121, "DOCKER_CLI_BYTES", len(docker_bytes))
    monkeypatch.setattr(d121, "DOCKER_CLI_SHA256", _sha256(docker_bytes))
    for key in tuple(os.environ):
        if key.upper().startswith("DOCKER_"):
            monkeypatch.delenv(key, raising=False)

    runner = FakeReadinessRunner(
        missing_inspect_stdout=missing_inspect_stdout,
        image_returncode=image_returncode,
        image_stdout=image_stdout,
        create_stdout=create_stdout,
        inspect_stdout=inspect_stdout,
        projection_mutate=projection_mutate,
    )
    monkeypatch.setattr(d121, "_new_runner", lambda: runner)
    return tmp_path, runner, docker


def _rewrite_envelope(
    path: Path,
    *,
    id_field: str,
    id_prefix: str,
    mutate: Any,
) -> None:
    value = _json(path)
    mutate(value["semantic_body"])
    rewritten = d121._envelope(
        schema_version=value["schema_version"],
        id_field=id_field,
        id_prefix=id_prefix,
        body=value["semantic_body"],
    )
    path.write_bytes(d121._pretty_bytes(rewritten))


def _rewrite_execution_journal(repository: Path, *, mutate: Any) -> None:
    path = repository / d121.EXECUTION_OUTPUT_PATHS["journal"]
    rows = [json.loads(line) for line in path.read_bytes().splitlines()]
    mutate(rows)
    previous = "sha256:" + "0" * 64
    rewritten: list[dict[str, Any]] = []
    for sequence, row in enumerate(rows):
        body = {
            "schema_version": row["schema_version"],
            "sequence": sequence,
            "recorded_at": row["recorded_at"],
            "event": row["event"],
            "previous_record_hash": previous,
            "data": row["data"],
        }
        record = {**body, "record_hash": _sha256(d121._canonical_bytes(body))}
        previous = record["record_hash"]
        rewritten.append(record)
    path.write_bytes(b"".join(d121._canonical_bytes(row) + b"\n" for row in rewritten))


def _completed_execution_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, FakeExecutionRunner, Path, dict[str, Any], dict[str, Any]]:
    repository, _readiness_runner, docker = _preparation_repository(tmp_path, monkeypatch)
    prepared = d121.prepare_d121_execution_candidate(
        repository=repository,
        docker_path=str(docker),
    )
    opaque_paths: set[Path] = set()
    for source in d121.SOURCE_PLAN:
        path = (repository / source["path"]).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"offline-placeholder-never-opened")
        opaque_paths.add(path)

    original_open = Path.open

    def reject_opaque_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path.resolve() in opaque_paths:
            raise AssertionError(f"opaque source was opened: {path}")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_opaque_open)
    runner = FakeExecutionRunner(repository)
    monkeypatch.setattr(d121, "_new_runner", lambda: runner)
    completed = d121._execute_d121_successor_after_cooperative_approval(
        candidate_id=prepared["candidate_id"],
        semantic_body_sha=prepared["candidate_semantic_body_hash"],
        file_sha=prepared["candidate_file_sha256"],
        repository=repository,
        docker_path=str(docker),
    )
    return repository, runner, docker, prepared, completed


def test_exact_d120_action_binds_the_unchanged_execution_tuple() -> None:
    context = d121._validate_d120_authority(REPOSITORY)
    action = context["action"]
    execution_tuple = action["unchanged_d119_execution_tuple"]

    assert context["action_hash"] == d121.D120_ACTION_HASH
    assert action["unchanged_probe_image_profile_source_tuple"] is True
    assert execution_tuple["immutable_image_id"] == d121.IMAGE_ID
    assert execution_tuple["docker_cli_file_bytes"] == d121.DOCKER_CLI_BYTES
    assert execution_tuple["docker_cli_file_sha256"] == d121.DOCKER_CLI_SHA256
    assert execution_tuple["profile_hash"] == d121.PROFILE_HASH
    assert execution_tuple["source_fingerprint"] == d121.SOURCE_FINGERPRINT
    assert execution_tuple["ordered_sources"] == [dict(row) for row in d121.SOURCE_PLAN]
    assert action["d120_approval_does_not_authorize"] == {
        "docker_container_start": True,
        "opaque_source_read": True,
        "d121_successor_execution": True,
    }


@pytest.mark.parametrize(
    ("missing_stdout", "presentation"),
    [
        (b"", "empty-bytes"),
        (b"[]", "empty-json-array"),
        (b"[]\n", "empty-json-array-lf"),
        (b"[]\r\n", "empty-json-array-crlf"),
    ],
)
def test_preparation_accepts_only_the_four_exact_cleanup_presentations_and_never_starts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    missing_stdout: bytes,
    presentation: str,
) -> None:
    repository, runner, docker = _preparation_repository(
        tmp_path,
        monkeypatch,
        missing_inspect_stdout=missing_stdout,
    )
    original_open = Path.open

    def reject_parquet_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path.suffix.casefold() == ".parquet":
            raise AssertionError(f"opaque source was opened: {path}")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_parquet_open)
    result = d121.prepare_d121_execution_candidate(
        repository=repository,
        docker_path=str(docker),
    )

    assert result["status"] == "D121_EXECUTION_CANDIDATE_READY_PENDING_EXACT_APPROVAL"
    assert result["docker_command_count"] == 8
    assert result["docker_start_count"] == 0
    assert result["opaque_source_read_count"] == 0
    assert result["fresh_successor_run_authorized"] is False
    assert runner.containers == {}
    assert len(runner.commands) == 8
    operations = [command[0][1] for command in runner.commands]
    assert operations == ["image", "ps", "create", "inspect", "rm", "inspect", "ps", "ps"]
    assert not ({"start", "run", "exec", "attach", "cp", "export"} & set(operations))
    assert all(input_bytes is None for _argv, input_bytes, _timeout in runner.commands)
    assert runner.commands[0][0] == d121._image_id_command(str(docker.resolve()))
    assert runner.commands[0][0][3:5] == ["--format", "{{.Id}}"]
    assert "--pull=never" in runner.commands[2][0]
    assert runner.commands[3][0] == d121._inspect_projection_command(
        str(docker.resolve()),
        runner.commands[3][0][-1],
    )
    rendered_commands = json.dumps([row[0] for row in runner.commands])
    assert "external-evidence" not in rendered_commands
    assert "Dockerfile.sandbox" in rendered_commands

    readiness = _json(repository / d121.PREPARATION_OUTPUT_PATHS["readiness"])
    evidence = readiness["semantic_body"]["readiness_evidence"]
    assert evidence["cleanup"]["missing_inspect_stdout_presentation"] == presentation
    assert evidence["cleanup"]["missing_inspect_stdout_bytes"] == len(missing_stdout)
    assert evidence["cleanup"]["missing_inspect_stdout_sha256"] == _sha256(missing_stdout)
    assert evidence["counters"]["readiness_docker_opaque_path_reference_count"] == 0
    assert evidence["counters"]["opaque_source_filesystem_access_count"] == 0
    assert evidence["counters"]["opaque_source_filesystem_byte_read_count"] == 0
    assert evidence["created_container_projection"]["Mounts"][0]["Source"] == (
        "<exact-nonopaque-sentinel>"
    )
    assert str(repository) not in json.dumps(readiness)
    assert evidence["docker_environment_pre"] == evidence["docker_environment_post"]
    assert (
        evidence["docker_environment_pre"]["child_environment_policy"]["force_docker_host"]
        == d121._LOCAL_DOCKER_ENDPOINT
    )
    assert evidence["qualification"]["hash_only_isolation_profile_verified"] is False
    assert all(not (repository / Path(row["path"])).exists() for row in d121.SOURCE_PLAN)
    assert all(not (repository / path).exists() for path in d121.EXECUTION_OUTPUT_PATHS.values())


def test_receipt_is_written_before_readiness_failure_and_consumes_preparation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, runner, docker = _preparation_repository(
        tmp_path,
        monkeypatch,
        image_returncode=1,
    )

    with pytest.raises(d121.D121PreparationError, match="image inspect failed"):
        d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))

    receipt = repository / d121.PREPARATION_OUTPUT_PATHS["approval_receipt"]
    receipt_bytes = receipt.read_bytes()
    assert d121._assert_preparation_start_state(repository) == "claimed-partial-consumed"
    assert len(runner.commands) == 1
    assert all(
        not (repository / relative).exists()
        for key, relative in d121.PREPARATION_OUTPUT_PATHS.items()
        if key != "approval_receipt"
    )

    with pytest.raises(d121.D121PreparationError, match="claimed-partial-consumed"):
        d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))
    assert receipt.read_bytes() == receipt_bytes
    assert len(runner.commands) == 1


def test_invalid_cleanup_presentation_still_runs_both_residual_inventories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, runner, docker = _preparation_repository(
        tmp_path,
        monkeypatch,
        missing_inspect_stdout=b" \n",
    )

    with pytest.raises(
        d121.D121PreparationError,
        match="REMOVED_INSPECT_PRESENTATION_INVALID",
    ):
        d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))

    assert len(runner.commands) == 8
    assert [row[0][1] for row in runner.commands[-4:]] == ["rm", "inspect", "ps", "ps"]
    assert runner.commands[-2][0][-1].startswith("id=")
    assert runner.commands[-1][0][-1] == f"label={d121.MANAGED_LABEL}"
    assert runner.containers == {}
    assert d121._assert_preparation_start_state(repository) == "claimed-partial-consumed"


@pytest.mark.parametrize("verb", ["start", "run", "exec", "attach", "cp", "export"])
def test_no_start_invoker_rejects_forbidden_docker_verbs_before_runner(
    verb: str,
) -> None:
    runner = FakeReadinessRunner()
    with pytest.raises(d121.D121PreparationError, match="no-start allowlist"):
        d121._invoke(runner, ["docker.exe", verb], timeout_seconds=1)
    assert runner.commands == []


def test_subprocess_runner_removes_all_inherited_docker_routing_and_forces_local_pipe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DOCKER_HOST", "tcp://remote.example:2376")
    monkeypatch.setenv("DOCKER_CONTEXT", "remote-context")
    monkeypatch.setenv("DOCKER_CONFIG", "C:/foreign-docker-config")
    monkeypatch.setenv("DOCKER_TLS_VERIFY", "1")
    monkeypatch.setenv("PATCHLOOP_TEST_KEEP", "kept")
    captured: dict[str, Any] = {}

    def fake_subprocess_run(
        command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        captured["command"] = command
        captured.update(kwargs)
        return _completed(command)

    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)
    result = d121.SubprocessCommandRunner().run(
        ["docker.exe", "version"],
        input_bytes=None,
        timeout_seconds=7,
    )

    assert result.returncode == 0
    environment = captured["env"]
    assert environment["DOCKER_HOST"] == d121._LOCAL_DOCKER_ENDPOINT
    assert "DOCKER_CONTEXT" not in environment
    assert "DOCKER_CONFIG" not in environment
    assert "DOCKER_TLS_VERIFY" not in environment
    assert environment["PATCHLOOP_TEST_KEEP"] == "kept"
    assert captured["shell"] is False
    assert captured["timeout"] == 7


def test_parent_docker_routing_environment_must_be_default_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DOCKER_CONTEXT", "remote-context")
    with pytest.raises(d121.D121PreparationError, match="not default-local"):
        d121._docker_environment_boundary()


def test_no_start_allowlist_requires_exact_create_name_sentinel_flags_and_id(
    tmp_path: Path,
) -> None:
    sentinel = tmp_path / "sentinel.txt"
    sentinel.write_bytes(b"nonopaque")
    other = tmp_path / "other.txt"
    other.write_bytes(b"other")
    name = "patchloop-d121-readiness-0123456789ab"
    exact = d121._create_command(
        docker="docker.exe",
        name=name,
        host_path=str(sentinel),
    )
    d121._validate_no_start_argv(
        exact,
        allowed_create_host_path=str(sentinel),
        allowed_readiness_name=name,
    )

    missing_pull = list(exact)
    missing_pull.remove("--pull=never")
    with pytest.raises(d121.D121PreparationError, match="create argv differs"):
        d121._validate_no_start_argv(
            missing_pull,
            allowed_create_host_path=str(sentinel),
            allowed_readiness_name=name,
        )

    foreign_name = d121._create_command(
        docker="docker.exe",
        name="patchloop-d121-readiness-fedcba987654",
        host_path=str(sentinel),
    )
    with pytest.raises(d121.D121PreparationError, match="container name differs"):
        d121._validate_no_start_argv(
            foreign_name,
            allowed_create_host_path=str(sentinel),
            allowed_readiness_name=name,
        )

    wrong_sentinel = d121._create_command(
        docker="docker.exe",
        name=name,
        host_path=str(other),
    )
    with pytest.raises(d121.D121PreparationError, match="not the exact sentinel"):
        d121._validate_no_start_argv(
            wrong_sentinel,
            allowed_create_host_path=str(sentinel),
            allowed_readiness_name=name,
        )

    with pytest.raises(d121.D121PreparationError, match="projection inspect target differs"):
        d121._validate_no_start_argv(
            d121._inspect_projection_command("docker.exe", "foreign-name"),
        )
    with pytest.raises(d121.D121PreparationError, match="remove target"):
        d121._validate_no_start_argv(["docker.exe", "rm", "--force", name])
    with pytest.raises(d121.D121PreparationError, match="image command differs"):
        d121._validate_no_start_argv(["docker.exe", "image", "inspect", d121.IMAGE_TAG])


@pytest.mark.parametrize(
    ("create_stdout", "message"),
    [
        (b"malformed-id\n", "container ID output bytes differ"),
        (b"x" * (d121._MAX_COMMAND_OUTPUT + 1), "container-create stdout too large"),
    ],
)
def test_malformed_or_oversize_create_output_uses_emergency_cleanup_without_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    create_stdout: bytes,
    message: str,
) -> None:
    repository, runner, docker = _preparation_repository(
        tmp_path,
        monkeypatch,
        create_stdout=create_stdout,
    )

    with pytest.raises(d121.D121PreparationError, match=message):
        d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))

    verbs = [row[0][1] for row in runner.commands]
    assert "start" not in verbs and "run" not in verbs and "exec" not in verbs
    assert runner.containers == {}
    assert any(
        row[0][1] == "ps" and row[0][-1] == f"label={d121.MANAGED_LABEL}" for row in runner.commands
    )
    assert d121._assert_preparation_start_state(repository) == "claimed-partial-consumed"


def test_oversize_projection_is_rejected_then_exact_cleanup_still_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, runner, docker = _preparation_repository(
        tmp_path,
        monkeypatch,
        inspect_stdout=b"x" * (d121._MAX_COMMAND_OUTPUT + 1),
    )

    with pytest.raises(d121.D121PreparationError, match="stdout too large"):
        d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))

    assert [row[0][1] for row in runner.commands[-4:]] == ["rm", "inspect", "ps", "ps"]
    assert runner.containers == {}


def test_foreign_projected_container_name_is_rejected_before_qualification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, runner, docker = _preparation_repository(
        tmp_path,
        monkeypatch,
        projection_mutate=lambda value: value.update(Name="/foreign-container"),
    )

    with pytest.raises(d121.D121PreparationError, match="container name differs"):
        d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))

    assert len(runner.commands) == 8
    assert runner.containers == {}


def test_exact_d120_file_tamper_fails_before_receipt_or_docker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, runner, docker = _preparation_repository(tmp_path, monkeypatch)
    candidate_path = repository / d121.D120_CANDIDATE_SPEC["path"]
    candidate = _json(candidate_path)
    candidate["semantic_body"]["candidate_status"] = "tampered"
    candidate_path.write_bytes(d121._pretty_bytes(candidate))

    with pytest.raises(d121.D121PreparationError, match="D-120 candidate file_bytes differs"):
        d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))

    assert runner.commands == []
    assert not any((repository / path).exists() for path in d121.PREPARATION_OUTPUT_PATHS.values())


def test_fully_rehashed_authority_expansion_fails_expected_payload_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, _runner, docker = _preparation_repository(tmp_path, monkeypatch)
    d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))
    candidate_path = repository / d121.PREPARATION_OUTPUT_PATHS["execution_candidate"]
    _rewrite_envelope(
        candidate_path,
        id_field="candidate_id",
        id_prefix="d121executioncandidate_",
        mutate=lambda body: body["authority"].update(fresh_successor_run_authorized=True),
    )

    with pytest.raises(
        d121.D121PreparationError,
        match="execution_candidate expected payload differs",
    ):
        d121.validate_d121_preparation(repository=repository)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda body: body["readiness_evidence"]["command_transcript"][2][
                "argv_contract"
            ].remove("--pull=never"),
            "readiness transcript argv differs",
        ),
        (
            lambda body: body["readiness_evidence"]["created_container_projection"].update(
                UnboundedSecret="must-not-survive"
            ),
            "readiness inspect projection fields differ",
        ),
        (
            lambda body: body["readiness_evidence"]["created_container_projection"]["Mounts"][
                0
            ].update(Source="C:/unredacted/host/path"),
            "readiness mount projection differs",
        ),
    ],
)
def test_fully_rehashed_transcript_or_sanitized_projection_tamper_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate: Any,
    message: str,
) -> None:
    repository, _runner, docker = _preparation_repository(tmp_path, monkeypatch)
    d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))
    readiness_path = repository / d121.PREPARATION_OUTPUT_PATHS["readiness"]
    _rewrite_envelope(
        readiness_path,
        id_field="readiness_id",
        id_prefix="d121readiness_",
        mutate=mutate,
    )

    with pytest.raises(d121.D121PreparationError, match=message):
        d121.validate_d121_preparation(repository=repository)


def test_noncanonical_artifact_bytes_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, _runner, docker = _preparation_repository(tmp_path, monkeypatch)
    d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))
    readiness_path = repository / d121.PREPARATION_OUTPUT_PATHS["readiness"]
    readiness_path.write_bytes(readiness_path.read_bytes() + b" ")

    with pytest.raises(d121.D121PreparationError, match="bytes are not canonical"):
        d121.validate_d121_preparation(repository=repository)


@pytest.mark.parametrize(
    "collision",
    [
        d121.PREPARATION_OUTPUT_PATHS["readiness"],
        d121.EXECUTION_OUTPUT_PATHS["journal"],
    ],
)
def test_partial_or_future_output_collision_fails_before_docker_and_preserves_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    collision: Path,
) -> None:
    repository, runner, docker = _preparation_repository(tmp_path, monkeypatch)
    selected = repository / collision
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_bytes(b"unapproved-collision")

    with pytest.raises(d121.D121PreparationError):
        d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))

    assert selected.read_bytes() == b"unapproved-collision"
    assert runner.commands == []


def test_complete_preparation_rerun_validates_without_new_docker_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, runner, docker = _preparation_repository(tmp_path, monkeypatch)
    first = d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))
    command_count = len(runner.commands)
    output_bytes = {
        key: (repository / relative).read_bytes()
        for key, relative in d121.PREPARATION_OUTPUT_PATHS.items()
    }
    monkeypatch.setattr(
        d121,
        "_new_runner",
        lambda: (_ for _ in ()).throw(AssertionError("Docker runner must not be created")),
    )

    second = d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))

    assert second == first
    assert len(runner.commands) == command_count
    assert {
        key: (repository / relative).read_bytes()
        for key, relative in d121.PREPARATION_OUTPUT_PATHS.items()
    } == output_bytes


def test_future_execution_requires_each_member_of_the_separate_exact_triple(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, _runner, docker = _preparation_repository(tmp_path, monkeypatch)
    prepared = d121.prepare_d121_execution_candidate(repository=repository, docker_path=str(docker))
    monkeypatch.setattr(
        d121,
        "_new_runner",
        lambda: (_ for _ in ()).throw(AssertionError("execution runner must not be created")),
    )
    exact = {
        "candidate_id": prepared["candidate_id"],
        "semantic_body_sha": prepared["candidate_semantic_body_hash"],
        "file_sha": prepared["candidate_file_sha256"],
    }
    cases = [
        ({**exact, "candidate_id": "d121executioncandidate_" + "0" * 64}, "candidate ID"),
        ({**exact, "semantic_body_sha": "sha256:" + "0" * 64}, "body SHA"),
        ({**exact, "file_sha": "sha256:" + "0" * 64}, "file SHA"),
    ]
    for supplied, message in cases:
        with pytest.raises(d121.D121PreparationError, match=message):
            d121._execute_d121_successor_after_cooperative_approval(
                repository=repository,
                docker_path=str(docker),
                **supplied,
            )
    assert all(not (repository / path).exists() for path in d121.EXECUTION_OUTPUT_PATHS.values())


class PrimaryAndCleanupFailureRunner:
    """Return separate primary and cleanup failures while attempting both inventories."""

    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.container_id = "a" * 64
        self.inspect_count = 0

    def run(
        self,
        command: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        timeout_seconds: int = 30,
    ) -> subprocess.CompletedProcess[bytes]:
        argv = list(command)
        self.commands.append(argv)
        operation = argv[1:]
        if operation[0] == "create":
            return _completed(argv, stdout=self.container_id.encode() + b"\n")
        if operation[0] == "inspect":
            self.inspect_count += 1
            if self.inspect_count == 1:
                return _completed(argv, returncode=1, stderr=b"primary inspect failure")
            return _completed(argv, returncode=1, stdout=b"{}\n", stderr=b"missing")
        if operation[:2] == ["rm", "--force"]:
            return _completed(argv, stdout=self.container_id.encode() + b"\n")
        if operation[:2] == ["ps", "--all"]:
            return _completed(argv)
        raise AssertionError(f"unexpected command: {argv!r}")


def test_future_session_returns_primary_and_cleanup_errors_separately_without_source_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "synthetic/source.bin"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"offline-synthetic-not-a-benchmark-object")
    original_open = Path.open

    def reject_source_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path == source_path:
            raise AssertionError("future-session helper opened source bytes")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_source_open)
    runner = PrimaryAndCleanupFailureRunner()
    evidence, primary_error, cleanup, cleanup_error = d121._execute_successor_session(
        repository=tmp_path,
        docker="docker.exe",
        runner=runner,
        source={"source_id": "offline-source", "path": "synthetic/source.bin"},
    )

    assert evidence is None
    assert cleanup is None
    assert primary_error is not None
    assert "successor inspect failed" in str(primary_error)
    assert cleanup_error is not None
    assert "REMOVED_INSPECT_PRESENTATION_INVALID" in str(cleanup_error)
    assert [command[1] for command in runner.commands] == [
        "create",
        "inspect",
        "rm",
        "inspect",
        "ps",
        "ps",
    ]
    assert len([command for command in runner.commands if command[1] == "ps"]) == 2


def test_offline_completed_execution_builds_exact_eleven_event_journal_and_revalidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, runner, _docker, _prepared, completed = _completed_execution_repository(
        tmp_path,
        monkeypatch,
    )

    assert completed["status"] == "D121_FRESH_SUCCESSOR_RUN_COMPLETED"
    assert completed["journal_record_count"] == 11
    assert completed["session_count"] == 2
    assert runner.containers == {}
    assert [row[0][1] for row in runner.commands] == [
        "image",
        "ps",
        "create",
        "inspect",
        "start",
        "rm",
        "inspect",
        "ps",
        "ps",
        "create",
        "inspect",
        "start",
        "rm",
        "inspect",
        "ps",
        "ps",
    ]
    assert len([row for row in runner.commands if row[0][1] == "start"]) == 2
    command_count = len(runner.commands)

    assert d121.validate_d121_execution(repository=repository) == completed
    assert len(runner.commands) == command_count


@pytest.mark.parametrize(
    ("output_key", "id_field", "id_prefix", "mutate", "message"),
    [
        (
            "approval_receipt",
            "receipt_id",
            "d121executionapproval_",
            lambda body: body["authorized_scope"].update(automatic_retry_count=1),
            "execution approval receipt expected payload differs",
        ),
        (
            "evidence",
            "evidence_id",
            "d121isolationevidence_",
            lambda body: body["qualification"].update(raw_record_bytes_emitted=True),
            "execution evidence expected payload differs",
        ),
        (
            "completion_gate",
            "gate_id",
            "d121execution_",
            lambda body: body["qualification"].update(independent=True),
            "execution completion gate expected payload differs",
        ),
    ],
)
def test_fully_rehashed_execution_artifact_tamper_fails_exact_payload_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    output_key: str,
    id_field: str,
    id_prefix: str,
    mutate: Any,
    message: str,
) -> None:
    repository, _runner, _docker, _prepared, _completed_result = _completed_execution_repository(
        tmp_path, monkeypatch
    )
    _rewrite_envelope(
        repository / d121.EXECUTION_OUTPUT_PATHS[output_key],
        id_field=id_field,
        id_prefix=id_prefix,
        mutate=mutate,
    )

    with pytest.raises(d121.D121PreparationError, match=message):
        d121.validate_d121_execution(repository=repository)


def test_fully_rehashed_journal_event_data_tamper_fails_after_chain_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, _runner, _docker, _prepared, _completed_result = _completed_execution_repository(
        tmp_path, monkeypatch
    )
    _rewrite_execution_journal(
        repository,
        mutate=lambda rows: rows[3]["data"].update(result_sha256="sha256:" + "0" * 64),
    )
    rows, binding = d121._read_execution_journal(repository)
    assert len(rows) == 11
    assert binding["record_count"] == 11

    with pytest.raises(d121.D121PreparationError, match="execution journal event data differs"):
        d121.validate_d121_execution(repository=repository)


def test_fully_rehashed_journal_chronology_tamper_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, _runner, _docker, _prepared, _completed_result = _completed_execution_repository(
        tmp_path, monkeypatch
    )
    _rewrite_execution_journal(
        repository,
        mutate=lambda rows: rows[1].update(recorded_at="2000-01-01T00:00:00Z"),
    )
    rows, _binding = d121._read_execution_journal(repository)
    assert len(rows) == 11

    with pytest.raises(d121.D121PreparationError, match="execution journal chronology differs"):
        d121.validate_d121_execution(repository=repository)


def test_fully_rehashed_session_projection_id_mismatch_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, _runner, _docker, _prepared, _completed_result = _completed_execution_repository(
        tmp_path, monkeypatch
    )
    evidence_path = repository / d121.EXECUTION_OUTPUT_PATHS["evidence"]
    _rewrite_envelope(
        evidence_path,
        id_field="evidence_id",
        id_prefix="d121isolationevidence_",
        mutate=lambda body: body["sessions"][0]["created_container_projection"].update(Id="f" * 64),
    )

    with pytest.raises(
        d121.D121PreparationError,
        match="execution projection container ID differs",
    ):
        d121.validate_d121_execution(repository=repository)


def test_fully_rehashed_duplicate_session_container_ids_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, _runner, _docker, _prepared, _completed_result = _completed_execution_repository(
        tmp_path, monkeypatch
    )
    evidence_path = repository / d121.EXECUTION_OUTPUT_PATHS["evidence"]

    def duplicate_container_id(body: dict[str, Any]) -> None:
        first_id = body["sessions"][0]["container_id"]
        second = body["sessions"][1]
        second["container_id"] = first_id
        second["created_container_projection"]["Id"] = first_id
        remove_stdout = first_id.encode("ascii") + b"\n"
        second["cleanup"]["command_summaries"][0]["stdout_sha256"] = _sha256(remove_stdout)

    _rewrite_envelope(
        evidence_path,
        id_field="evidence_id",
        id_prefix="d121isolationevidence_",
        mutate=duplicate_container_id,
    )

    with pytest.raises(
        d121.D121PreparationError,
        match="execution session container IDs are not distinct",
    ):
        d121.validate_d121_execution(repository=repository)


def test_fully_rehashed_execution_authority_unknown_field_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, _runner, _docker, _prepared, _completed_result = _completed_execution_repository(
        tmp_path, monkeypatch
    )
    _rewrite_envelope(
        repository / d121.EXECUTION_OUTPUT_PATHS["evidence"],
        id_field="evidence_id",
        id_prefix="d121isolationevidence_",
        mutate=lambda body: body["authority"].update(unapproved_future_authority=False),
    )

    with pytest.raises(
        d121.D121PreparationError,
        match="execution evidence expected payload differs",
    ):
        d121.validate_d121_execution(repository=repository)


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        ("mount-count", "D-121 mount count differs"),
        ("extra-mount", "execution source mount projection differs"),
    ],
)
def test_execution_validator_rejects_mount_count_or_extra_mount_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
    message: str,
) -> None:
    repository, _runner, _docker, _prepared, _completed_result = _completed_execution_repository(
        tmp_path, monkeypatch
    )
    evidence_path = repository / d121.EXECUTION_OUTPUT_PATHS["evidence"]

    def mutate_mounts(body: dict[str, Any]) -> None:
        projection = body["sessions"][0]["created_container_projection"]
        if tamper == "mount-count":
            projection["MountCount"] = 2
        else:
            projection["Mounts"].append(dict(projection["Mounts"][0]))

    _rewrite_envelope(
        evidence_path,
        id_field="evidence_id",
        id_prefix="d121isolationevidence_",
        mutate=mutate_mounts,
    )

    with pytest.raises(d121.D121PreparationError, match=message):
        d121.validate_d121_execution(repository=repository)


@pytest.mark.parametrize(
    ("command", "message", "input_bytes"),
    [
        (
            d121._inspect_projection_command("docker.exe", "b" * 64),
            "execution projection inspect target differs",
            None,
        ),
        (["docker.exe", "inspect", "b" * 64], "execution inspect target differs", None),
        (
            ["docker.exe", "rm", "--force", "b" * 64],
            "execution remove target differs",
            None,
        ),
        (
            ["docker.exe", "start", "--attach", "--interactive", "b" * 64],
            "execution start target binding differs",
            b"probe",
        ),
    ],
)
def test_execution_invoker_requires_exact_current_container_id_before_runner(
    command: list[str],
    message: str,
    input_bytes: bytes | None,
) -> None:
    runner = FakeReadinessRunner()
    kwargs: dict[str, Any] = {
        "timeout_seconds": 1,
        "allowed_container_id": "a" * 64,
    }
    if input_bytes is not None:
        kwargs.update(input_bytes=input_bytes, expected_input_bytes=input_bytes)

    with pytest.raises(d121.D121PreparationError, match=message):
        d121._invoke_execution(runner, command, **kwargs)
    assert runner.commands == []


def test_completed_execution_still_requires_exact_triple_without_new_docker_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, runner, docker, prepared, completed = _completed_execution_repository(
        tmp_path,
        monkeypatch,
    )
    exact = {
        "candidate_id": prepared["candidate_id"],
        "semantic_body_sha": prepared["candidate_semantic_body_hash"],
        "file_sha": prepared["candidate_file_sha256"],
    }
    output_bytes = {
        key: (repository / relative).read_bytes()
        for key, relative in d121.EXECUTION_OUTPUT_PATHS.items()
    }
    command_count = len(runner.commands)
    monkeypatch.setattr(
        d121,
        "_new_runner",
        lambda: (_ for _ in ()).throw(AssertionError("completed validation started Docker")),
    )

    for supplied, message in [
        ({**exact, "candidate_id": "d121executioncandidate_" + "0" * 64}, "candidate ID"),
        ({**exact, "semantic_body_sha": "sha256:" + "0" * 64}, "body SHA"),
        ({**exact, "file_sha": "sha256:" + "0" * 64}, "file SHA"),
    ]:
        with pytest.raises(d121.D121PreparationError, match=message):
            d121._execute_d121_successor_after_cooperative_approval(
                repository=repository,
                docker_path=str(docker),
                **supplied,
            )

    assert (
        d121._execute_d121_successor_after_cooperative_approval(
            repository=repository,
            docker_path=str(docker),
            **exact,
        )
        == completed
    )
    assert len(runner.commands) == command_count
    assert {
        key: (repository / relative).read_bytes()
        for key, relative in d121.EXECUTION_OUTPUT_PATHS.items()
    } == output_bytes
