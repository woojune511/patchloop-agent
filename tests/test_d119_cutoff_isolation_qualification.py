from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from patchloop.memory import d119_cutoff_isolation_qualification as d119


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


class FakeDockerRunner:
    """Deterministic Docker transcript; it never starts a process or opens an input."""

    def __init__(self, sources: Sequence[dict[str, Any]]) -> None:
        self.sources = {
            str(Path(row["host_path"]).resolve()).casefold(): dict(row) for row in sources
        }
        self.commands: list[tuple[list[str], bytes | None, int]] = []
        self.containers: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _mount_source(command: Sequence[str]) -> str:
        mount = command[command.index("--mount") + 1]
        prefix = "type=bind,source="
        suffix = ",target=/input/source.parquet,readonly"
        assert mount.startswith(prefix) and mount.endswith(suffix)
        return mount[len(prefix) : -len(suffix)]

    @staticmethod
    def _probe_result(source: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": "d119-hash-only-probe-result-v1",
            "source_id": source["source_id"],
            "file_bytes": source["file_bytes"],
            "file_sha256": source["file_sha256"],
            "binary_stream_hash_only": True,
            "record_fields_read": [],
            "record_parser_imported": False,
            "uid_non_root": True,
            "environment_exact_allowlist": True,
            "input_write_denied": True,
            "root_write_denied": True,
            "non_output_runtime_write_denied": True,
            "network_connect_denied": True,
            "dns_denied": True,
            "forbidden_paths_absent": True,
            "workspace_empty": True,
            "capabilities_empty": True,
            "no_new_privileges": True,
            "seccomp_filter_active": True,
            "source_mount_read_only": True,
            "output_mount_writable": True,
            "process_spawn_denied": True,
        }

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

        if operation[:3] == ["image", "inspect", "--format"]:
            return _completed(argv, stdout=(d119.IMAGE_ID + "\n").encode())

        if operation[0] == "create":
            name = argv[argv.index("--name") + 1]
            source_path = self._mount_source(argv)
            source = self.sources[str(Path(source_path).resolve()).casefold()]
            container_id = hashlib.sha256(name.encode()).hexdigest()
            self.containers[container_id] = {
                "name": name,
                "source": source,
                "host_path": source_path,
            }
            return _completed(argv, stdout=(container_id + "\n").encode())

        if operation[0] == "inspect":
            container_id = operation[1]
            container = self.containers.get(container_id)
            if container is None:
                return _completed(argv, returncode=1, stderr=b"not found")
            value = [
                {
                    "Id": container_id,
                    "Path": "/usr/bin/env",
                    "Args": [
                        "-i",
                        "LANG=C.UTF-8",
                        "LC_ALL=C.UTF-8",
                        "PYTHONHASHSEED=0",
                        "/usr/local/bin/python",
                        "-I",
                        "/opt/patchloop/probe_runner.py",
                        "20",
                    ],
                    "Image": d119.IMAGE_ID,
                    "Config": {
                        "Cmd": [
                            "/usr/bin/env",
                            "-i",
                            "LANG=C.UTF-8",
                            "LC_ALL=C.UTF-8",
                            "PYTHONHASHSEED=0",
                            "/usr/local/bin/python",
                            "-I",
                            "/opt/patchloop/probe_runner.py",
                            "20",
                        ],
                        "WorkingDir": "/",
                        "User": "10001:10001",
                        "Tty": False,
                        "OpenStdin": True,
                        "Labels": {
                            "io.patchloop.managed": "d119-isolation",
                            "io.patchloop.role": "external-source-hash-only",
                            "io.patchloop.probe-image": "v2",
                        },
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
                        "Tmpfs": {
                            "/output": (
                                "rw,noexec,nosuid,nodev,size=64k,uid=10001,gid=10001,mode=0700"
                            ),
                            "/dev/shm": "ro,noexec,nosuid,nodev,size=64k,mode=0555",
                        },
                    },
                    "Mounts": [
                        {
                            "Type": "bind",
                            "Source": container["host_path"],
                            "Destination": "/input/source.parquet",
                            "RW": False,
                        }
                    ],
                }
            ]
            return _completed(argv, stdout=json.dumps(value).encode())

        if operation[:3] == ["start", "--attach", "--interactive"]:
            assert input_bytes is not None
            container_id = operation[3]
            source = self.containers[container_id]["source"]
            assert source["source_id"].encode() in input_bytes
            assert b"pyarrow" not in input_bytes
            result = json.dumps(
                self._probe_result(source),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            return _completed(argv, stdout=result + b"\n")

        if operation[:2] == ["rm", "--force"]:
            self.containers.pop(operation[2])
            return _completed(argv, stdout=operation[2].encode() + b"\n")

        if operation[:2] == ["ps", "--all"]:
            stdout = "".join(f"{container_id}\n" for container_id in self.containers).encode()
            return _completed(argv, stdout=stdout)

        raise AssertionError(f"unexpected fake Docker command: {argv!r}")


QualificationFixture = tuple[
    Path,
    tuple[dict[str, Any], ...],
    dict[str, Any],
    FakeDockerRunner,
    Path,
]


@pytest.fixture
def qualification_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> QualificationFixture:
    source_rows = []
    for number, content in enumerate((b"opaque-one\x00\xff", b"opaque-two\x80\x81"), start=1):
        relative = Path(f"opaque/source-{number}.parquet")
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        source_rows.append(
            {
                "source_id": f"source-{number}",
                "path": relative.as_posix(),
                "host_path": str(path.resolve()),
                "file_bytes": len(content),
                "file_sha256": _sha256(content),
            }
        )

    implementation_paths = (
        Path("implementation/module.py"),
        Path("implementation/script.py"),
        Path("implementation/test.py"),
    )
    for number, relative in enumerate(implementation_paths):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# stable implementation fixture {number}\n", encoding="utf-8")
    (tmp_path / "reports/memory-development").mkdir(parents=True, exist_ok=True)

    d118_context = {
        "artifacts": [],
        "source_gate": {
            "role": "source-gate",
            "identifier": "d118_test_gate",
            "semantic_body_hash": "sha256:" + "1" * 64,
            "file_sha256": "sha256:" + "2" * 64,
        },
        "evidence_pack": {
            "role": "evidence-pack",
            "identifier": "d118_test_pack",
            "semantic_body_hash": "sha256:" + "3" * 64,
            "file_sha256": "sha256:" + "4" * 64,
        },
    }

    monkeypatch.setattr(d119, "SOURCE_OBJECTS", tuple(source_rows))
    monkeypatch.setattr(d119, "IMPLEMENTATION_PATHS", implementation_paths)
    monkeypatch.setattr(
        d119,
        "_d118_context",
        lambda repository, *, current_objects: copy.deepcopy(d118_context),
    )
    fake_docker = tmp_path / "tools/docker.exe"
    fake_docker.parent.mkdir(parents=True, exist_ok=True)
    fake_docker.write_bytes(b"fake-docker-cli-for-injected-command-runner")
    monkeypatch.setattr(d119, "DOCKER_CLI_BYTES", fake_docker.stat().st_size)
    monkeypatch.setattr(d119, "DOCKER_CLI_SHA256", _sha256(fake_docker.read_bytes()))
    runner = FakeDockerRunner(source_rows)
    monkeypatch.setattr(d119, "SubprocessCommandRunner", lambda: runner)
    return tmp_path, tuple(source_rows), d118_context, runner, fake_docker


def _valid_inspect(host_path: str) -> dict[str, Any]:
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
        "Path": command[0],
        "Args": command[1:],
        "Image": d119.IMAGE_ID,
        "Config": {
            "Cmd": command,
            "WorkingDir": "/",
            "User": "10001:10001",
            "Tty": False,
            "OpenStdin": True,
            "Labels": {
                "io.patchloop.managed": "d119-isolation",
                "io.patchloop.role": "external-source-hash-only",
                "io.patchloop.probe-image": "v2",
            },
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


def _rewrite_envelope(
    path: Path,
    *,
    id_field: str,
    id_prefix: str,
    mutate: Any,
) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    mutate(value["semantic_body"])
    rewritten = d119._envelope(
        schema_version=value["schema_version"],
        id_field=id_field,
        id_prefix=id_prefix,
        body=value["semantic_body"],
    )
    path.write_bytes(d119._pretty_bytes(rewritten))
    return rewritten


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    assert isinstance(value, dict)
    return value


def _rebind_isolation_and_gate(
    repository: Path,
    *,
    mutate_isolation: Any,
    journal_binding: dict[str, Any] | None = None,
) -> None:
    isolation_path = repository / d119.OUTPUT_PATHS["isolation_evidence"]
    isolation = _rewrite_envelope(
        isolation_path,
        id_field="isolation_evidence_id",
        id_prefix="d119isolation_",
        mutate=mutate_isolation,
    )
    isolation_binding = d119._binding_for_payload(
        d119.OUTPUT_PATHS["isolation_evidence"],
        isolation,
        "isolation_evidence_id",
    )
    gate_path = repository / d119.OUTPUT_PATHS["source_gate"]

    def mutate_gate(body: dict[str, Any]) -> None:
        body["isolation_evidence"] = isolation_binding
        if journal_binding is not None:
            body["journal"] = journal_binding

    _rewrite_envelope(
        gate_path,
        id_field="gate_id",
        id_prefix="d119_",
        mutate=mutate_gate,
    )


def _rehash_journal_and_update_bindings(
    repository: Path,
    *,
    mutate_rows: Any,
) -> None:
    journal_path = repository / d119.OUTPUT_PATHS["journal"]
    rows = [json.loads(line) for line in journal_path.read_bytes().splitlines()]
    mutate_rows(rows)
    previous = "sha256:" + "0" * 64
    encoded_rows = []
    for row in rows:
        row["previous_record_hash"] = previous
        body = {key: value for key, value in row.items() if key != "record_hash"}
        row["record_hash"] = d119._sha256_bytes(d119._canonical_bytes(body))
        previous = row["record_hash"]
        encoded_rows.append(d119._canonical_bytes(row) + b"\n")
    journal_path.write_bytes(b"".join(encoded_rows))
    journal_binding = d119._journal_binding(journal_path)

    def mutate_isolation(body: dict[str, Any]) -> None:
        body["journal"] = journal_binding

    _rebind_isolation_and_gate(
        repository,
        mutate_isolation=mutate_isolation,
        journal_binding=journal_binding,
    )


def test_profile_and_probe_are_hash_only_and_have_no_record_parser() -> None:
    source = {
        "source_id": "opaque-source",
        "file_bytes": 17,
        "file_sha256": "sha256:" + "a" * 64,
    }
    profile = d119.isolation_profile()
    probe = d119._probe_source(source)
    tree = ast.parse(probe)
    imported = {
        alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names
    }

    assert profile["session_count"] == 2
    assert profile["one_intentionally_writable_output"] == "/output"
    assert profile["writable_mount_size_bytes"] == 65_536
    assert profile["read_only_runtime_tmpfs"] == "/dev/shm"
    assert profile["network_mode"] == "none"
    assert profile["root_filesystem_read_only"] is True
    assert profile["one_exact_read_only_input_per_session"] is True
    assert profile["parquet_footer_schema_statistics_or_row_parse_allowed"] is False
    assert profile["opaque_operation"] == "stream-byte-count-and-sha256-only"
    assert imported == {"errno", "hashlib", "json", "os", "pathlib", "socket"}
    assert "input_path.open('rb', buffering=0)" in probe
    assert "digest.update(chunk)" in probe
    assert "record_fields_read': []" in probe
    assert "record_parser_imported': False" in probe
    for forbidden in ("pyarrow", "pandas", "fastparquet", "duckdb", "datasets"):
        assert forbidden not in probe


def test_docker_create_command_is_exact(tmp_path: Path) -> None:
    host_path = str((tmp_path / "opaque source.parquet").resolve())
    assert d119._docker_create_command(
        docker="docker-test",
        name="patchloop-d119-test",
        host_path=host_path,
    ) == [
        "docker-test",
        "create",
        "--name",
        "patchloop-d119-test",
        "--label",
        "io.patchloop.managed=d119-isolation",
        "--label",
        "io.patchloop.role=external-source-hash-only",
        "-i",
        "--network",
        "none",
        "--cpus",
        "1",
        "--memory",
        "256m",
        "--pids-limit",
        "2",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--tmpfs",
        "/output:rw,noexec,nosuid,nodev,size=64k,uid=10001,gid=10001,mode=0700",
        "--tmpfs",
        "/dev/shm:ro,noexec,nosuid,nodev,size=64k,mode=0555",
        "--user",
        "10001:10001",
        "--mount",
        f"type=bind,source={host_path},target=/input/source.parquet,readonly",
        "--workdir",
        "/",
        d119.IMAGE_ID,
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


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda row: row.update(Image="sha256:" + "0" * 64), "container image differs"),
        (lambda row: row["Config"].update(User="0:0"), "container user differs"),
        (
            lambda row: row["HostConfig"].update(NetworkMode="bridge"),
            "container network differs",
        ),
        (
            lambda row: row["HostConfig"].update(ReadonlyRootfs=False),
            "container root must be read-only",
        ),
        (lambda row: row["HostConfig"].update(CapDrop=[]), "container capabilities differ"),
        (
            lambda row: row["HostConfig"].update(SecurityOpt=[]),
            "security options differ",
        ),
        (lambda row: row.update(Path="/bin/sh"), "container path differs"),
        (lambda row: row["Config"].update(WorkingDir="/workspace"), "workdir differs"),
        (lambda row: row["Config"].update(Labels={}), "container labels differ"),
        (lambda row: row["HostConfig"].update(IpcMode="host"), "host IPC namespace"),
        (lambda row: row["HostConfig"].update(Memory=0), "memory limit differs"),
        (lambda row: row["HostConfig"].update(NanoCpus=0), "CPU limit differs"),
        (lambda row: row["HostConfig"].update(Tmpfs={}), "tmpfs policy differs"),
        (lambda row: row["Mounts"][0].update(RW=True), "input mount must be read-only"),
        (
            lambda row: row["Mounts"].append(copy.deepcopy(row["Mounts"][0])),
            "exactly one bind mount",
        ),
    ],
)
def test_inspect_configuration_drift_is_rejected(
    tmp_path: Path,
    mutate: Any,
    message: str,
) -> None:
    host_path = str((tmp_path / "opaque.parquet").resolve())
    inspect_value = _valid_inspect(host_path)
    mutate(inspect_value)

    with pytest.raises(d119.D119QualificationError, match=message):
        d119._validate_created_container(inspect_value, expected_host_path=host_path)


def test_envelope_and_journal_are_content_addressed(tmp_path: Path) -> None:
    body = {"z": [2, 1], "a": {"closed": True}}
    envelope = d119._envelope(
        schema_version="test-v1",
        id_field="gate_id",
        id_prefix="test_",
        body=body,
    )
    expected_hash = d119._sha256_bytes(d119._canonical_bytes(body))

    assert envelope["semantic_body_hash"] == expected_hash
    assert envelope["gate_id"] == "test_" + expected_hash.removeprefix("sha256:")
    d119._validate_envelope(
        envelope,
        id_field="gate_id",
        id_prefix="test_",
        label="test envelope",
    )

    journal_path = tmp_path / "journal.jsonl"
    journal = d119._Journal(journal_path)
    first = journal.append("Started", {"value": 1})
    second = journal.append("Completed", {"value": 2})
    binding = d119._journal_binding(journal_path)

    assert first["previous_record_hash"] == "sha256:" + "0" * 64
    assert second["previous_record_hash"] == first["record_hash"]
    assert binding["record_count"] == 2
    assert binding["head_hash"] == second["record_hash"]

    rows = journal_path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(rows[0])
    tampered["event"] = "Tampered"
    rows[0] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
    journal_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(d119.D119QualificationError, match="journal row hash differs"):
        d119._journal_binding(journal_path)


def test_partial_output_state_consumes_capability_without_repair(
    qualification_repository: QualificationFixture,
) -> None:
    repository, _source_rows, _context, runner, fake_docker = qualification_repository
    conflict = repository / d119.OUTPUT_PATHS["preflight"]
    conflict.parent.mkdir(parents=True, exist_ok=True)
    conflict.write_bytes(b"partial-evidence")
    with pytest.raises(
        d119.D119QualificationError,
        match="partial D-119 evidence consumes the one-use capability",
    ):
        d119.run_d119_cutoff_isolation_qualification(
            repository=repository,
            docker_path=str(fake_docker),
        )

    assert conflict.read_bytes() == b"partial-evidence"
    assert runner.commands == []
    assert sum((repository / path).exists() for path in d119.OUTPUT_PATHS.values()) == 1


def test_fake_two_session_execution_seals_closed_authority_and_is_idempotent(
    qualification_repository: QualificationFixture,
) -> None:
    repository, _source_rows, _context, runner, fake_docker = qualification_repository

    result = d119.run_d119_cutoff_isolation_qualification(
        repository=repository,
        docker_path=str(fake_docker),
    )

    assert result["status"] == "BLOCKED_INSUFFICIENT_PREEXISTENCE"
    assert result["trusted_cutoff_anchor_verified"] is False
    assert result["hash_only_isolation_profile_verified"] is True
    assert result["record_projection_isolation_verified"] is False
    assert result["independent"] is False
    assert result["execution_authorization_candidate_ready"] is False
    assert len(runner.commands) == 15
    assert runner.containers == {}
    assert sum((repository / path).is_file() for path in d119.OUTPUT_PATHS.values()) == 6

    gate = json.loads((repository / d119.OUTPUT_PATHS["source_gate"]).read_bytes())["semantic_body"]
    assert gate["evidence_boundary"]["record_container_parse_count"] == 0
    assert gate["evidence_boundary"]["pool_member_id_read_count"] == 0
    assert gate["evidence_boundary"]["issue_labeling_or_review_count"] == 0
    assert gate["evidence_boundary"]["retrieval_agent_provider_evaluator_call_count"] == 0
    assert gate["aggregate_disposition"] == {
        "status": "BLOCKED_INSUFFICIENT_PREEXISTENCE",
        "trusted_cutoff_anchor_verified": False,
        "hash_only_isolation_profile_verified": True,
        "record_projection_isolation_verified": False,
        "post_hoc": True,
        "independent": False,
        "eligible_for_independent_calibration": False,
        "execution_authorization_candidate_ready": False,
    }
    assert all(
        gate["authority"][key] is False
        for key in (
            "d117_proposed_next_action_authorized",
            "d117_proposed_next_action_consumed",
            "pool_selection_acquisition_or_freeze_authorized",
            "matcher_classifier_or_calibration_authorized",
            "score_policy_or_index_changed",
            "retrieval_ready",
            "core_campaign_unlocked",
            "analysis_campaign_unlocked",
        )
    )
    assert gate["authority"]["runtime_memory_injection_count"] == 0
    assert gate["authority"]["agent_runs"] == 0
    assert gate["authority"]["provider_calls"] == 0
    assert gate["authority"]["evaluator_calls"] == 0

    command_count = len(runner.commands)
    replay = d119.run_d119_cutoff_isolation_qualification(
        repository=repository,
        docker_path=str(fake_docker),
    )
    assert replay == result
    assert len(runner.commands) == command_count


def test_fully_rehashed_authority_tamper_fails_closed(
    qualification_repository: QualificationFixture,
) -> None:
    repository, _source_rows, _context, _runner, fake_docker = qualification_repository
    d119.run_d119_cutoff_isolation_qualification(
        repository=repository,
        docker_path=str(fake_docker),
    )
    gate_path = repository / d119.OUTPUT_PATHS["source_gate"]
    _rewrite_envelope(
        gate_path,
        id_field="gate_id",
        id_prefix="d119_",
        mutate=lambda body: body["authority"].update(retrieval_ready=True),
    )

    with pytest.raises(d119.D119QualificationError, match="authority expanded: retrieval_ready"):
        d119.validate_d119_artifacts(repository=repository, current_objects=True)


@pytest.mark.parametrize(
    ("artifact_key", "id_field", "id_prefix"),
    [
        ("approval_receipt", "receipt_id", "d119approval_"),
        ("preflight", "preflight_id", "d119preflight_"),
        ("anchor_evidence", "anchor_evidence_id", "d119anchor_"),
        ("isolation_evidence", "isolation_evidence_id", "d119isolation_"),
    ],
)
def test_fully_rehashed_paired_artifact_tamper_fails_closed(
    qualification_repository: QualificationFixture,
    artifact_key: str,
    id_field: str,
    id_prefix: str,
) -> None:
    repository, _source_rows, _context, _runner, fake_docker = qualification_repository
    d119.run_d119_cutoff_isolation_qualification(
        repository=repository,
        docker_path=str(fake_docker),
    )
    artifact_path = repository / d119.OUTPUT_PATHS[artifact_key]
    _rewrite_envelope(
        artifact_path,
        id_field=id_field,
        id_prefix=id_prefix,
        mutate=lambda body: body.update(tampered_but_rehashed=True),
    )

    with pytest.raises(d119.D119QualificationError, match=f"gate {artifact_key} binding differs"):
        d119.validate_d119_artifacts(repository=repository, current_objects=True)


@pytest.mark.parametrize(
    ("mutate_rows", "message"),
    [
        (
            lambda rows: rows[1].update(event="ImageIdentityAcceptedWithoutVerification"),
            "journal event differs",
        ),
        (
            lambda rows: rows[1].update(data={"image_id": "sha256:" + "0" * 64}),
            "journal event data differs",
        ),
        (
            lambda rows: rows[1].update(schema_version="cutoff-isolation-journal-drift-v2"),
            "journal schema version differs",
        ),
        (
            lambda rows: rows[1].update(recorded_at="2000-01-01T00:00:00Z"),
            "journal chronology differs",
        ),
    ],
)
def test_fully_rehashed_journal_semantic_tamper_fails_closed(
    qualification_repository: QualificationFixture,
    mutate_rows: Any,
    message: str,
) -> None:
    repository, _source_rows, _context, _runner, fake_docker = qualification_repository
    d119.run_d119_cutoff_isolation_qualification(
        repository=repository,
        docker_path=str(fake_docker),
    )
    _rehash_journal_and_update_bindings(repository, mutate_rows=mutate_rows)

    with pytest.raises(d119.D119QualificationError, match=message):
        d119.validate_d119_artifacts(repository=repository, current_objects=True)


@pytest.mark.parametrize(
    ("mutate_isolation", "message"),
    [
        (
            lambda body: body["sessions"][0]["result"].update(uid_non_root=False),
            "session result differs",
        ),
        (
            lambda body: body["sessions"][0]["config_checks"].update(network_none=False),
            "session config differs",
        ),
        (
            lambda body: body["sessions"][0]["cleanup"].update(
                label_wide_residual_container_count=1
            ),
            "session cleanup differs",
        ),
    ],
)
def test_rehashed_session_evidence_tamper_fails_closed(
    qualification_repository: QualificationFixture,
    mutate_isolation: Any,
    message: str,
) -> None:
    repository, _source_rows, _context, _runner, fake_docker = qualification_repository
    d119.run_d119_cutoff_isolation_qualification(
        repository=repository,
        docker_path=str(fake_docker),
    )
    _rebind_isolation_and_gate(
        repository,
        mutate_isolation=mutate_isolation,
    )

    with pytest.raises(d119.D119QualificationError, match=message):
        d119.validate_d119_artifacts(repository=repository, current_objects=True)


def test_noncanonical_artifact_bytes_fail_before_binding_validation(
    qualification_repository: QualificationFixture,
) -> None:
    repository, _source_rows, _context, _runner, fake_docker = qualification_repository
    d119.run_d119_cutoff_isolation_qualification(
        repository=repository,
        docker_path=str(fake_docker),
    )
    anchor_path = repository / d119.OUTPUT_PATHS["anchor_evidence"]
    anchor_path.write_bytes(anchor_path.read_bytes() + b" \n")

    with pytest.raises(d119.D119QualificationError, match="canonical pretty JSON"):
        d119.validate_d119_artifacts(repository=repository, current_objects=True)


def test_artifact_schema_drift_fails_even_when_body_hash_is_unchanged(
    qualification_repository: QualificationFixture,
) -> None:
    repository, _source_rows, _context, _runner, fake_docker = qualification_repository
    d119.run_d119_cutoff_isolation_qualification(
        repository=repository,
        docker_path=str(fake_docker),
    )
    anchor_path = repository / d119.OUTPUT_PATHS["anchor_evidence"]
    anchor = _json(anchor_path)
    anchor["schema_version"] = "external-anchor-evidence-d119-v2"
    anchor_path.write_bytes(d119._pretty_bytes(anchor))

    with pytest.raises(
        d119.D119QualificationError,
        match="anchor_evidence schema version differs",
    ):
        d119.validate_d119_artifacts(repository=repository, current_objects=True)


def test_full_paired_rehash_cannot_hide_approval_payload_tamper(
    qualification_repository: QualificationFixture,
) -> None:
    repository, _source_rows, _context, _runner, fake_docker = qualification_repository
    d119.run_d119_cutoff_isolation_qualification(
        repository=repository,
        docker_path=str(fake_docker),
    )

    approval_path = repository / d119.OUTPUT_PATHS["approval_receipt"]
    approval = _rewrite_envelope(
        approval_path,
        id_field="receipt_id",
        id_prefix="d119approval_",
        mutate=lambda body: body.update(fully_rehashed_unknown_claim=False),
    )
    approval_binding = d119._binding_for_payload(
        d119.OUTPUT_PATHS["approval_receipt"], approval, "receipt_id"
    )

    preflight_path = repository / d119.OUTPUT_PATHS["preflight"]
    preflight = _rewrite_envelope(
        preflight_path,
        id_field="preflight_id",
        id_prefix="d119preflight_",
        mutate=lambda body: body.update(approval_receipt=approval_binding),
    )
    preflight_binding = d119._binding_for_payload(
        d119.OUTPUT_PATHS["preflight"], preflight, "preflight_id"
    )

    isolation_path = repository / d119.OUTPUT_PATHS["isolation_evidence"]

    def mutate_isolation(body: dict[str, Any]) -> None:
        body["approval_receipt"] = approval_binding
        body["preflight"] = preflight_binding

    isolation = _rewrite_envelope(
        isolation_path,
        id_field="isolation_evidence_id",
        id_prefix="d119isolation_",
        mutate=mutate_isolation,
    )
    isolation_binding = d119._binding_for_payload(
        d119.OUTPUT_PATHS["isolation_evidence"],
        isolation,
        "isolation_evidence_id",
    )

    gate_path = repository / d119.OUTPUT_PATHS["source_gate"]

    def mutate_gate(body: dict[str, Any]) -> None:
        body["approval_receipt"] = approval_binding
        body["preflight"] = preflight_binding
        body["isolation_evidence"] = isolation_binding

    _rewrite_envelope(
        gate_path,
        id_field="gate_id",
        id_prefix="d119_",
        mutate=mutate_gate,
    )

    with pytest.raises(d119.D119QualificationError, match="approval expected payload differs"):
        d119.validate_d119_artifacts(repository=repository, current_objects=True)
