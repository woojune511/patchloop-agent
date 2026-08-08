"""D-119 trusted-cutoff research and hash-only isolation qualification.

This successor is intentionally narrow.  It never parses a benchmark record,
constructs a pool, labels an issue, or invokes the memory runtime.  The only
container-side read of an opaque Parquet object is a streaming byte count and
SHA-256 calculation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import textwrap
import uuid
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from patchloop.memory.d118_external_source_evidence import (
    validate_d118_artifacts,
)

MILESTONE = "D-119"
D116_CUTOFF = "2026-08-07T06:22:51.021003Z"
IMAGE_TAG = "patchloop-sandbox:py312"
IMAGE_ID = "sha256:1144b4be9927ac5882401185c326003383630eac9db84102ee3d71c06e261cac"
DOCKERFILE_SHA256 = "sha256:f310b88e8a2769b83202c3fb7a5cb776142c70a6d45935b648db258d3bc2d944"
PROBE_RUNNER_SHA256 = "sha256:ed07d48a2e2129645aa0ae4765d0f248750125eb685bf55767a21db636e15509"
DOCKER_CLI_BYTES = 43_095_472
DOCKER_CLI_SHA256 = "sha256:8985cd8ac002c3240b5aa48fe401fcb55dca5d849b537e3c835564e8e8c49a70"

D118_BINDINGS: tuple[dict[str, Any], ...] = (
    {
        "role": "approval-receipt",
        "path": "reports/memory-development/d118-external-source-evidence-approval-receipt.json",
        "id_field": "receipt_id",
        "identifier": (
            "d118approval_2a7461b834374e4a34db8c02850501d0ad9e8416e7a4bf7f73613abef08713a2"
        ),
        "semantic_body_hash": (
            "sha256:2a7461b834374e4a34db8c02850501d0ad9e8416e7a4bf7f73613abef08713a2"
        ),
        "file_bytes": 4199,
        "file_sha256": "sha256:0adb87887b42a19aa8d1b9be3ca5268801666bbecb2cf94b4664e3df1dba8344",
    },
    {
        "role": "preflight",
        "path": "reports/memory-development/d118-external-source-evidence-preflight.json",
        "id_field": "preflight_id",
        "identifier": (
            "d118preflight_1f11c66f174e5e475ef9d94df7810c568857f02a8164edf30287778276dab4b0"
        ),
        "semantic_body_hash": (
            "sha256:1f11c66f174e5e475ef9d94df7810c568857f02a8164edf30287778276dab4b0"
        ),
        "file_bytes": 17476,
        "file_sha256": "sha256:4f4bff33cbf55e841f86da0a30fc67885f9302fa2f149dde040a3d85a2c4c0b3",
    },
    {
        "role": "evidence-pack",
        "path": "reports/memory-development/d118-external-source-evidence-pack.json",
        "id_field": "evidence_pack_id",
        "identifier": (
            "d118evidencepack_e40dad5ceac6dcfbb29d47bec3a548c44bdcbeba964e4e7a43818b76e8c62f10"
        ),
        "semantic_body_hash": (
            "sha256:e40dad5ceac6dcfbb29d47bec3a548c44bdcbeba964e4e7a43818b76e8c62f10"
        ),
        "file_bytes": 25451,
        "file_sha256": "sha256:318d4f58276283e6e6ae6c45c4afe50af5bca6b6937ffa841b8b791a0357c6b1",
    },
    {
        "role": "source-gate",
        "path": "reports/memory-development/d118-external-source-evidence-source-gate.json",
        "id_field": "gate_id",
        "identifier": "d118_cdd55277ad1dc1215a45aa3588e7862df3535b91b7274681fe0a8488abd3e707",
        "semantic_body_hash": (
            "sha256:cdd55277ad1dc1215a45aa3588e7862df3535b91b7274681fe0a8488abd3e707"
        ),
        "file_bytes": 17748,
        "file_sha256": "sha256:0f01a2b315f9c32c34b8c2400af6f22a1c4f2538b2538f8597f2ab0b8d57c343",
    },
)

SOURCE_OBJECTS: tuple[dict[str, Any], ...] = (
    {
        "source_id": "swe-bench-dev-f5351",
        "path": ".patchloop/external-evidence/d118/swe-bench-f5351/data/dev-00000-of-00001.parquet",
        "file_bytes": 1_382_594,
        "file_sha256": "sha256:d758d54540aa4140d0274ed0cc93b8288aa6f323c3c603e2557e7666a47fc41b",
    },
    {
        "source_id": "swe-gym-train-26a6",
        "path": ".patchloop/external-evidence/d118/swe-gym-26a6/data/train-00000-of-00001.parquet",
        "file_bytes": 43_644_473,
        "file_sha256": "sha256:60569cea74bb281f7a5579467436a2bc1932c6e0c5f2f7fa0d084392abd9ad97",
    },
)

IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d119_cutoff_isolation_qualification.py"),
    Path("scripts/run_d119_cutoff_isolation_qualification.py"),
    Path("tests/test_d119_cutoff_isolation_qualification.py"),
)

OUTPUT_PATHS = {
    "approval_receipt": Path(
        "reports/memory-development/d119-cutoff-isolation-approval-receipt.json"
    ),
    "preflight": Path("reports/memory-development/d119-cutoff-isolation-preflight.json"),
    "anchor_evidence": Path("reports/memory-development/d119-external-anchor-evidence.json"),
    "journal": Path("reports/memory-development/d119-isolation-execution.jsonl"),
    "isolation_evidence": Path("reports/memory-development/d119-isolation-evidence.json"),
    "source_gate": Path("reports/memory-development/d119-cutoff-isolation-source-gate.json"),
}

_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
_FORBIDDEN_CONTAINER_PATHS = (
    "/workspace/.git",
    "/workspace/AGENTS.md",
    "/workspace/docs",
    "/workspace/tasks",
    "/testbed",
    "/repo",
    "/artifacts",
    "/memory",
    "/traces",
    "/patches",
    "/evaluator",
    "/private",
)


class D119QualificationError(RuntimeError):
    """Raised when D-119 cannot preserve its evidence boundary."""


class CommandRunner(Protocol):
    def run(
        self,
        command: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        timeout_seconds: int = 30,
    ) -> subprocess.CompletedProcess[bytes]: ...


@dataclass(frozen=True)
class SubprocessCommandRunner:
    """Run exact argv lists without a shell."""

    def run(
        self,
        command: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        timeout_seconds: int = 30,
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            list(command),
            input=input_bytes,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D119QualificationError(message)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _envelope(
    *,
    schema_version: str,
    id_field: str,
    id_prefix: str,
    body: Mapping[str, Any],
) -> dict[str, Any]:
    digest = _sha256_bytes(_canonical_bytes(body))
    return {
        "schema_version": schema_version,
        id_field: f"{id_prefix}{digest.removeprefix('sha256:')}",
        "semantic_body_hash": digest,
        "semantic_body": dict(body),
    }


def _repo_root(repository: str | Path | None) -> Path:
    root = Path(repository or Path.cwd()).resolve(strict=True)
    _require(root.is_dir(), "repository must be a directory")
    return root


def _is_linklike(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and is_junction():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def _validate_logical_path_contract() -> None:
    paths = [
        *(Path(binding["path"]) for binding in D118_BINDINGS),
        *(Path(source["path"]) for source in SOURCE_OBJECTS),
        *IMPLEMENTATION_PATHS,
        *OUTPUT_PATHS.values(),
    ]
    normalized: list[str] = []
    for path in paths:
        _require(not path.is_absolute(), "absolute contract path is forbidden")
        _require(".." not in path.parts, "contract path traversal is forbidden")
        for part in path.parts:
            _require(":" not in part, "alternate data stream path is forbidden")
            _require(not part.endswith((".", " ")), "ambiguous Windows path is forbidden")
        normalized.append(path.as_posix().casefold())
    _require(len(normalized) == len(set(normalized)), "contract paths overlap")


def _safe_path(
    repository: Path,
    relative: str | Path,
    *,
    must_exist: bool,
) -> Path:
    rel = Path(relative)
    _require(not rel.is_absolute(), "absolute repository path is forbidden")
    _require(".." not in rel.parts, "path traversal is forbidden")
    for part in rel.parts:
        _require(":" not in part, "alternate data stream path is forbidden")
        _require(not part.endswith((".", " ")), "ambiguous Windows path is forbidden")
    logical = repository.joinpath(rel)
    cursor = repository
    for part in rel.parts:
        cursor = cursor / part
        _require(not _is_linklike(cursor), f"link-like path is forbidden: {rel}")
    if must_exist:
        resolved = logical.resolve(strict=True)
    else:
        resolved_parent = logical.parent.resolve(strict=True)
        resolved = resolved_parent / logical.name
    _require(
        resolved == repository or repository in resolved.parents,
        f"path escapes repository: {rel}",
    )
    return resolved


def _stable_binding(path: Path, *, label: str) -> dict[str, Any]:
    _require(path.exists(), f"{label} is missing")
    _require(path.is_file(), f"{label} must be a file")
    before = path.stat()
    digest = hashlib.sha256()
    size = 0
    with path.open("rb", buffering=0) as handle:
        opened = os.fstat(handle.fileno())
        _require(
            (before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino),
            f"{label} identity changed before read",
        )
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
        after_fd = os.fstat(handle.fileno())
    after_path = path.stat()

    def identity(value: os.stat_result) -> tuple[int, int, int, int]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
        )

    _require(
        identity(before) == identity(opened) == identity(after_fd) == identity(after_path),
        f"{label} changed during stable read",
    )
    return {
        "file_bytes": size,
        "file_sha256": f"sha256:{digest.hexdigest()}",
    }


def _read_stable_content(path: Path, *, label: str) -> bytes:
    _require(path.exists() and path.is_file(), f"{label} is missing")
    before = path.stat()
    with path.open("rb", buffering=0) as handle:
        opened = os.fstat(handle.fileno())
        _require(
            (before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino),
            f"{label} identity changed before read",
        )
        content = handle.read()
        after_fd = os.fstat(handle.fileno())
    after_path = path.stat()

    def identity(value: os.stat_result) -> tuple[int, int, int, int]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
        )

    _require(
        identity(before) == identity(opened) == identity(after_fd) == identity(after_path),
        f"{label} changed during read",
    )
    return content


def _read_json_canonical(path: Path, *, label: str) -> dict[str, Any]:
    content = _read_stable_content(path, label=label)
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D119QualificationError(f"{label} is not canonical JSON") from exc
    _require(isinstance(value, dict), f"{label} root must be an object")
    _require(content == _pretty_bytes(value), f"{label} bytes are not canonical pretty JSON")
    return value


def _validate_envelope(
    value: Mapping[str, Any],
    *,
    id_field: str,
    id_prefix: str,
    label: str,
    expected_schema_version: str | None = None,
) -> None:
    _require(
        set(value) == {"schema_version", id_field, "semantic_body_hash", "semantic_body"},
        f"{label} root fields differ",
    )
    body = value["semantic_body"]
    _require(isinstance(body, dict), f"{label} semantic_body must be an object")
    digest = _sha256_bytes(_canonical_bytes(body))
    _require(value["semantic_body_hash"] == digest, f"{label} body hash differs")
    _require(
        value[id_field] == f"{id_prefix}{digest.removeprefix('sha256:')}",
        f"{label} identifier differs",
    )
    if expected_schema_version is not None:
        _require(
            value["schema_version"] == expected_schema_version,
            f"{label} schema version differs",
        )


def _d118_context(repository: Path, *, current_objects: bool) -> dict[str, Any]:
    validate_d118_artifacts(
        repository=repository,
        mode="current-object" if current_objects else "sealed-historical",
    )
    rows: list[dict[str, Any]] = []
    for expected in D118_BINDINGS:
        path = _safe_path(repository, expected["path"], must_exist=True)
        value = _read_json_canonical(path, label=expected["role"])
        binding = _stable_binding(path, label=expected["role"])
        _require(binding["file_bytes"] == expected["file_bytes"], "D-118 byte count differs")
        _require(binding["file_sha256"] == expected["file_sha256"], "D-118 file SHA differs")
        _require(value[expected["id_field"]] == expected["identifier"], "D-118 ID differs")
        _require(
            value["semantic_body_hash"] == expected["semantic_body_hash"],
            "D-118 body SHA differs",
        )
        rows.append({**expected})
    return {
        "artifacts": rows,
        "source_gate": rows[-1],
        "evidence_pack": rows[-2],
    }


def _source_state(repository: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for expected in SOURCE_OBJECTS:
        path = _safe_path(repository, expected["path"], must_exist=True)
        binding = _stable_binding(path, label=expected["source_id"])
        _require(binding["file_bytes"] == expected["file_bytes"], "source bytes differ")
        _require(binding["file_sha256"] == expected["file_sha256"], "source SHA differs")
        rows.append({**expected})
    fingerprint = _sha256_bytes(_canonical_bytes(rows))
    return {
        "files": rows,
        "file_count": len(rows),
        "total_bytes": sum(row["file_bytes"] for row in rows),
        "fingerprint": fingerprint,
    }


def _expected_source_state() -> dict[str, Any]:
    rows = [{**row} for row in SOURCE_OBJECTS]
    return {
        "files": rows,
        "file_count": len(rows),
        "total_bytes": sum(row["file_bytes"] for row in rows),
        "fingerprint": _sha256_bytes(_canonical_bytes(rows)),
    }


def _implementation_state(repository: Path) -> dict[str, Any]:
    rows = []
    for relative in IMPLEMENTATION_PATHS:
        path = _safe_path(repository, relative, must_exist=True)
        rows.append({"path": relative.as_posix(), **_stable_binding(path, label=str(relative))})
    return {"files": rows, "fingerprint": _sha256_bytes(_canonical_bytes(rows))}


def _anchor_evidence_body(recorded_at: str) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "sanitized-source-level-trusted-cutoff-research",
        "recorded_at": recorded_at,
        "d116_cutoff": D116_CUTOFF,
        "exact_content_binding_observed": {
            "source_id": "swe-bench-dev-f5351",
            "revision": "f5351ee8c6663736817027db3ad03fe662cb5bb8",
            "membership_rule": "data/dev-*",
            "provider_declared_member_count": 225,
            "shard_sha256": SOURCE_OBJECTS[0]["file_sha256"],
            "shard_bytes": SOURCE_OBJECTS[0]["file_bytes"],
            "evidence_url": "https://huggingface.co/api/datasets/princeton-nlp/SWE-bench/revision/f5351ee8c6663736817027db3ad03fe662cb5bb8?blobs=true",
            "provider_metadata_is_independent_timestamp": False,
        },
        "anchor_attempts": [
            {
                "kind": "software-heritage-origin-and-revision",
                "result": "not-found",
                "exact_snapshot_and_membership_bound": False,
                "trusted_pre_d116_time_bound": False,
                "evidence_kind": "current-source-level-api-research-self-attested",
            },
            {
                "kind": "internet-archive-exact-commit-and-shard-cdx",
                "result": "no-exact-captures",
                "exact_snapshot_and_membership_bound": False,
                "trusted_pre_d116_time_bound": False,
                "evidence_kind": "current-source-level-api-research-self-attested",
            },
            {
                "kind": "internet-archive-dataset-root",
                "result": "2024-07-05-root-page-only",
                "exact_snapshot_and_membership_bound": False,
                "trusted_pre_d116_time_bound": True,
                "evidence_kind": "independent-archive-page-presence-only",
            },
            {
                "kind": "common-crawl-exact-source-urls",
                "result": "no-capture-metadata",
                "exact_snapshot_and_membership_bound": False,
                "trusted_pre_d116_time_bound": False,
                "evidence_kind": "current-source-level-index-research-self-attested",
            },
            {
                "kind": "sigstore-rekor-shard-sha256",
                "result": "zero-entry-uuids",
                "exact_snapshot_and_membership_bound": False,
                "trusted_pre_d116_time_bound": False,
                "evidence_kind": "current-source-level-log-search-self-attested",
            },
            {
                "kind": "signed-git-tree",
                "result": "provider-reports-gpg-verified-content",
                "exact_snapshot_and_membership_bound": True,
                "trusted_pre_d116_time_bound": False,
                "evidence_kind": "provider-asserted-not-independent-timestamp",
            },
        ],
        "research_boundary": {
            "network_request_count": None,
            "network_request_count_instrumented": False,
            "dataset_container_opened_by_anchor_research": False,
            "dataset_record_read_count": 0,
            "incidental_public_example_parser_overreturn_count": 1,
            "incidental_content_used_for_source_selection_or_verdict": False,
            "zero_prohibited_content_exposure_claimed": False,
            "raw_issue_or_gold_example_persisted_in_d119": False,
        },
        "qualification": {
            "acceptable_exact_anchor_found": False,
            "trusted_cutoff_anchor_verified": False,
            "snapshot_and_membership_jointly_time_bound": False,
            "strictly_before_d116_verified": False,
            "reason_codes": [
                "TRUSTED_CUTOFF_ANCHOR_MISSING",
                "PROVIDER_DATE_IS_NOT_INDEPENDENT_TIMESTAMP",
                "INDEPENDENT_ARCHIVES_DO_NOT_BIND_EXACT_SNAPSHOT_AND_MEMBERSHIP",
            ],
        },
    }


def isolation_profile() -> dict[str, Any]:
    profile = {
        "profile_version": "exact-opaque-hash-only-isolation-d119-v1",
        "image_tag_observed_before_execution": IMAGE_TAG,
        "immutable_image_id": IMAGE_ID,
        "dockerfile_sha256": DOCKERFILE_SHA256,
        "probe_runner_sha256": PROBE_RUNNER_SHA256,
        "session_count": 2,
        "one_exact_read_only_input_per_session": True,
        "one_intentionally_writable_output": "/output",
        "writable_mount_size_bytes": 65_536,
        "read_only_runtime_tmpfs": "/dev/shm",
        "network_mode": "none",
        "root_filesystem_read_only": True,
        "user": "10001:10001",
        "cap_drop": ["ALL"],
        "no_new_privileges": True,
        "pids_limit": 2,
        "privileged": False,
        "host_pid_ipc_or_docker_socket_mounted": False,
        "container_environment": {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONHASHSEED": "0",
        },
        "environment_cleared_with_env_i": True,
        "repository_or_project_tree_mount_count": 0,
        "exact_opaque_input_file_mount_count": 1,
        "docker_managed_runtime_mounts_are_not_project_mounts": True,
        "opaque_operation": "stream-byte-count-and-sha256-only",
        "parquet_footer_schema_statistics_or_row_parse_allowed": False,
        "stdout_stderr_record_bytes_allowed": False,
        "forbidden_container_paths": list(_FORBIDDEN_CONTAINER_PATHS),
    }
    return {
        **profile,
        "profile_hash": _sha256_bytes(_canonical_bytes(profile)),
    }


def _docker_cli_binding() -> dict[str, Any]:
    return {
        "file_name": "docker.exe",
        "file_bytes": DOCKER_CLI_BYTES,
        "file_sha256": DOCKER_CLI_SHA256,
        "runner_kind": "subprocess-exact-argv-no-shell",
    }


def _expected_config_checks() -> dict[str, bool | int]:
    return {
        "image_exact": True,
        "user_exact": True,
        "network_none": True,
        "root_read_only": True,
        "privileged_false": True,
        "pids_limit_exact": True,
        "cap_drop_all": True,
        "no_new_privileges": True,
        "command_and_workdir_exact": True,
        "labels_exact": True,
        "host_pid_ipc_and_devices_absent": True,
        "one_read_only_input_mount": True,
        "one_bounded_tmpfs_output": True,
        "read_only_dev_shm": True,
        "repository_or_project_tree_mount_count": 0,
    }


def _expected_probe_result(source: Mapping[str, Any]) -> dict[str, Any]:
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


def _portable_command_manifest(session: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "command_contract_version": "d119-docker-create-command-v1",
        "container_name": "<runtime-random-name>",
        "docker_executable": "<exact-docker-cli-binding>",
        "input_source": "<exact-d118-object-host-path>",
        "input_target": "/input/source.parquet",
        "source_id": session["source_id"],
        "image_id": IMAGE_ID,
        "profile_hash": isolation_profile()["profile_hash"],
        "probe_source_sha256": session["probe_source_sha256"],
    }


def _probe_source(source: Mapping[str, Any]) -> str:
    expected_sha = source["file_sha256"].removeprefix("sha256:")
    expected_size = int(source["file_bytes"])
    source_id = str(source["source_id"])
    forbidden = repr(_FORBIDDEN_CONTAINER_PATHS)
    return textwrap.dedent(
        f"""
        import errno
        import hashlib
        import json
        import os
        import pathlib
        import socket

        source_id = {source_id!r}
        expected_sha256 = {expected_sha!r}
        expected_bytes = {expected_size!r}
        input_path = pathlib.Path('/input/source.parquet')
        expected_env = {{'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'PYTHONHASHSEED': '0'}}
        assert dict(os.environ) == expected_env
        assert os.getuid() == 10001 and os.getgid() == 10001

        digest = hashlib.sha256()
        observed_bytes = 0
        with input_path.open('rb', buffering=0) as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                observed_bytes += len(chunk)
                digest.update(chunk)
        observed_sha256 = digest.hexdigest()
        assert observed_bytes == expected_bytes
        assert observed_sha256 == expected_sha256

        input_write_denied = False
        try:
            input_path.open('r+b').close()
        except OSError:
            input_write_denied = True
        assert input_write_denied

        root_write_denied = False
        try:
            pathlib.Path('/d119-root-write-forbidden').write_bytes(b'x')
        except OSError:
            root_write_denied = True
        assert root_write_denied

        non_output_runtime_write_denied = True
        for forbidden_write in ('/tmp/d119', '/dev/shm/d119', '/etc/hosts'):
            try:
                pathlib.Path(forbidden_write).write_bytes(b'x')
            except OSError:
                pass
            else:
                non_output_runtime_write_denied = False
        assert non_output_runtime_write_denied

        network_connect_denied = False
        try:
            socket.create_connection(('1.1.1.1', 53), timeout=0.25).close()
        except OSError:
            network_connect_denied = True
        assert network_connect_denied

        dns_denied = False
        try:
            socket.getaddrinfo('example.com', 443)
        except OSError:
            dns_denied = True
        assert dns_denied

        forbidden_paths_absent = all(not pathlib.Path(p).exists() for p in {forbidden})
        workspace = pathlib.Path('/workspace')
        workspace_empty = workspace.is_dir() and not any(workspace.iterdir())
        assert forbidden_paths_absent and workspace_empty

        status = {{}}
        for line in pathlib.Path('/proc/self/status').read_text(encoding='ascii').splitlines():
            if ':' in line:
                key, value = line.split(':', 1)
                status[key] = value.strip()
        assert int(status['CapEff'], 16) == 0
        assert status['NoNewPrivs'] == '1'
        assert status['Seccomp'] == '2'

        source_mount_read_only = False
        output_mount_writable = False
        for line in pathlib.Path('/proc/self/mountinfo').read_text(encoding='utf-8').splitlines():
            fields = line.split()
            if len(fields) >= 6 and fields[4] == '/input/source.parquet':
                source_mount_read_only = 'ro' in fields[5].split(',')
            if len(fields) >= 6 and fields[4] == '/output':
                output_mount_writable = 'rw' in fields[5].split(',')
        assert source_mount_read_only and output_mount_writable

        process_spawn_denied = False
        try:
            os.posix_spawn('/bin/true', ['true'], {{}})
        except OSError as exc:
            process_spawn_denied = exc.errno == errno.EPERM
        assert process_spawn_denied

        result = {{
            'schema_version': 'd119-hash-only-probe-result-v1',
            'source_id': source_id,
            'file_bytes': observed_bytes,
            'file_sha256': 'sha256:' + observed_sha256,
            'binary_stream_hash_only': True,
            'record_fields_read': [],
            'record_parser_imported': False,
            'uid_non_root': True,
            'environment_exact_allowlist': True,
            'input_write_denied': input_write_denied,
            'root_write_denied': root_write_denied,
            'non_output_runtime_write_denied': non_output_runtime_write_denied,
            'network_connect_denied': network_connect_denied,
            'dns_denied': dns_denied,
            'forbidden_paths_absent': forbidden_paths_absent,
            'workspace_empty': workspace_empty,
            'capabilities_empty': True,
            'no_new_privileges': True,
            'seccomp_filter_active': True,
            'source_mount_read_only': source_mount_read_only,
            'output_mount_writable': output_mount_writable,
            'process_spawn_denied': process_spawn_denied,
        }}
        encoded = json.dumps(result, sort_keys=True, separators=(',', ':')).encode('utf-8')
        pathlib.Path('/output/result.json').write_bytes(encoded + b'\\n')
        print(encoded.decode('utf-8'), flush=True)
        """
    ).lstrip()


def _session_plan(repository: Path | None = None) -> list[dict[str, Any]]:
    rows = []
    for source in SOURCE_OBJECTS:
        if repository is not None:
            _safe_path(repository, source["path"], must_exist=True)
        probe = _probe_source(source)
        rows.append(
            {
                **source,
                "container_path": "/input/source.parquet",
                "probe_source_sha256": _sha256_bytes(probe.encode("utf-8")),
                "probe_source_bytes": len(probe.encode("utf-8")),
            }
        )
    return rows


def _preflight_body(
    *,
    recorded_at: str,
    d118: Mapping[str, Any],
    source_state: Mapping[str, Any],
    implementation_state: Mapping[str, Any],
    docker_cli_binding: Mapping[str, Any],
    repository: Path | None,
) -> dict[str, Any]:
    profile = isolation_profile()
    sessions = _session_plan(repository)
    action = {
        "action": "execute-two-exact-object-hash-only-isolation-sessions",
        "d118_source_gate": d118["source_gate"],
        "source_fingerprint": source_state["fingerprint"],
        "profile_hash": profile["profile_hash"],
        "session_probe_hashes": [row["probe_source_sha256"] for row in sessions],
        "docker_cli_file_sha256": docker_cli_binding["file_sha256"],
    }
    return {
        "milestone": MILESTONE,
        "evidence_kind": "trusted-cutoff-and-hash-only-isolation-preflight",
        "recorded_at": recorded_at,
        "approval_reference": "current-thread-user-message:proceed",
        "approval_is_self_attested": True,
        "reviewer_identity_authenticated": False,
        "cryptographic_signature_verified": False,
        "d118_context": dict(d118),
        "source_pre_state": dict(source_state),
        "implementation_pre_state": dict(implementation_state),
        "docker_cli_binding": dict(docker_cli_binding),
        "anchor_research_plan": {
            "source_level_only": True,
            "trusted_anchor_required_to_bind_snapshot_and_membership": True,
            "provider_or_git_date_alone_sufficient": False,
            "record_or_issue_content_allowed": False,
        },
        "isolation_profile": profile,
        "session_plan": sessions,
        "authorized_action": action,
        "authorized_action_hash": _sha256_bytes(_canonical_bytes(action)),
        "authority": _preflight_authority(),
    }


def _approval_body(
    *,
    recorded_at: str,
    d118: Mapping[str, Any],
    source_state: Mapping[str, Any],
    implementation_state: Mapping[str, Any],
    preflight_body: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "self-attested-user-approval-receipt",
        "recorded_at": recorded_at,
        "approval_statement_code": "PROCEED_D119_TRUSTED_ANCHOR_AND_HASH_ONLY_ISOLATION_EVIDENCE",
        "approval_reference": "current-thread-user-message:proceed",
        "d118_source_gate": d118["source_gate"],
        "d118_evidence_pack": d118["evidence_pack"],
        "source_pre_state": dict(source_state),
        "implementation_pre_state": dict(implementation_state),
        "authorized_action": preflight_body["authorized_action"],
        "authorized_action_hash": preflight_body["authorized_action_hash"],
        "isolation_profile_hash": preflight_body["isolation_profile"]["profile_hash"],
        "session_probe_hashes": [
            row["probe_source_sha256"] for row in preflight_body["session_plan"]
        ],
        "docker_cli_binding": preflight_body["docker_cli_binding"],
        "claim_semantics": {
            "approval_is_self_attested": True,
            "repository_local_one_use_only": True,
            "global_or_cross_clone_exclusion_proved": False,
            "record_or_pool_access_authorized": False,
        },
        "execution_result_present": False,
    }


def _docker_path() -> str:
    configured = os.environ.get("PATCHLOOP_DOCKER_CLI")
    if configured:
        return configured
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidate = Path(local_app_data) / "Programs/DockerDesktop/resources/bin/docker.exe"
        if candidate.is_file():
            return str(candidate)
    return "docker"


def _run_ok(
    runner: CommandRunner,
    command: Sequence[str],
    *,
    input_bytes: bytes | None = None,
    timeout_seconds: int = 30,
    label: str,
) -> subprocess.CompletedProcess[bytes]:
    result = runner.run(command, input_bytes=input_bytes, timeout_seconds=timeout_seconds)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")[:1000]
        raise D119QualificationError(f"{label} failed: {stderr}")
    return result


def _docker_create_command(
    *,
    docker: str,
    name: str,
    host_path: str,
) -> list[str]:
    return [
        docker,
        "create",
        "--name",
        name,
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
        IMAGE_ID,
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


def _validate_created_container(
    inspect_value: Mapping[str, Any],
    *,
    expected_host_path: str,
) -> dict[str, Any]:
    _require(inspect_value.get("Image") == IMAGE_ID, "container image differs")
    config = inspect_value.get("Config")
    host = inspect_value.get("HostConfig")
    mounts = inspect_value.get("Mounts")
    _require(isinstance(config, dict), "container config missing")
    _require(isinstance(host, dict), "container host config missing")
    _require(isinstance(mounts, list), "container mounts missing")
    expected_command = [
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
    _require(inspect_value.get("Path") == expected_command[0], "container path differs")
    _require(inspect_value.get("Args") == expected_command[1:], "container args differ")
    _require(config.get("Cmd") == expected_command, "container command differs")
    _require(config.get("WorkingDir") == "/", "container workdir differs")
    _require(config.get("User") == "10001:10001", "container user differs")
    _require(config.get("Tty") is False, "container TTY must be disabled")
    _require(config.get("OpenStdin") is True, "container stdin must be bounded input")
    expected_labels = {
        "io.patchloop.managed": "d119-isolation",
        "io.patchloop.role": "external-source-hash-only",
        "io.patchloop.probe-image": "v2",
    }
    _require(config.get("Labels") == expected_labels, "container labels differ")
    _require(host.get("NetworkMode") == "none", "container network differs")
    _require(host.get("ReadonlyRootfs") is True, "container root must be read-only")
    _require(host.get("Privileged") is False, "container must not be privileged")
    _require(host.get("PidsLimit") == 2, "container PID limit differs")
    _require(host.get("CapDrop") == ["ALL"], "container capabilities differ")
    _require(host.get("CapAdd") is None, "container capability add differs")
    _require(host.get("SecurityOpt") == ["no-new-privileges"], "security options differ")
    _require(host.get("PidMode") == "", "host PID namespace requested")
    _require(host.get("IpcMode") == "private", "host IPC namespace requested")
    _require(host.get("Devices") == [], "container devices differ")
    _require(host.get("DeviceRequests") is None, "container device requests differ")
    _require(host.get("Binds") is None, "legacy bind mounts are forbidden")
    _require(host.get("Memory") == 268_435_456, "container memory limit differs")
    _require(host.get("NanoCpus") == 1_000_000_000, "container CPU limit differs")
    expected_tmpfs = {
        "/output": "rw,noexec,nosuid,nodev,size=64k,uid=10001,gid=10001,mode=0700",
        "/dev/shm": "ro,noexec,nosuid,nodev,size=64k,mode=0555",
    }
    _require(host.get("Tmpfs") == expected_tmpfs, "tmpfs policy differs")
    _require(len(mounts) == 1, "container must have exactly one bind mount")
    mount = mounts[0]
    _require(mount.get("Type") == "bind", "input mount must be bind")
    _require(mount.get("Destination") == "/input/source.parquet", "input destination differs")
    _require(mount.get("RW") is False, "input mount must be read-only")
    _require(
        str(Path(str(mount.get("Source"))).resolve()).casefold()
        == str(Path(expected_host_path).resolve()).casefold(),
        "input host path differs",
    )
    return _expected_config_checks()


def _execute_session(
    *,
    session: Mapping[str, Any],
    repository: Path,
    docker: str,
    runner: CommandRunner,
) -> dict[str, Any]:
    host_path = _safe_path(repository, str(session["path"]), must_exist=True)
    name = f"patchloop-d119-{session['source_id']}-{uuid.uuid4().hex[:12]}"
    create = _docker_create_command(
        docker=docker,
        name=name,
        host_path=str(host_path),
    )
    probe = _probe_source(session).encode("utf-8")
    preexisting = _managed_container_ids(runner=runner, docker=docker)
    _require(preexisting == [], "preexisting D-119 isolation container found")
    created = False
    container_id: str | None = None
    evidence: dict[str, Any] | None = None
    try:
        create_result = _run_ok(runner, create, label="docker create")
        created = True
        candidate_id = create_result.stdout.decode("ascii", errors="strict").strip()
        _require(re.fullmatch(r"[0-9a-f]{64}", candidate_id) is not None, "container ID invalid")
        container_id = candidate_id
        inspected = _run_ok(
            runner,
            [docker, "inspect", container_id],
            label="docker inspect before start",
        )
        try:
            inspect_rows = json.loads(inspected.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise D119QualificationError("docker inspect output invalid") from exc
        _require(
            isinstance(inspect_rows, list) and len(inspect_rows) == 1, "inspect row count differs"
        )
        _require(inspect_rows[0].get("Id") == container_id, "inspected container ID differs")
        config_checks = _validate_created_container(
            inspect_rows[0],
            expected_host_path=str(host_path),
        )
        started = _run_ok(
            runner,
            [docker, "start", "--attach", "--interactive", container_id],
            input_bytes=probe,
            timeout_seconds=40,
            label="docker start",
        )
        stdout = started.stdout.decode("utf-8", errors="strict").strip()
        stderr = started.stderr.decode("utf-8", errors="strict")
        _require(len(stdout.encode("utf-8")) <= 4096, "probe stdout too large")
        _require(len(stderr.encode("utf-8")) <= 4096, "probe stderr too large")
        _require(stderr == "", "probe stderr must be empty")
        try:
            result = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise D119QualificationError("probe stdout is not JSON") from exc
        _require(isinstance(result, dict), "probe result root differs")
        _require(result == _expected_probe_result(session), "probe result payload differs")
        _require(
            started.stdout == _canonical_bytes(result) + b"\n",
            "probe stdout contains non-result bytes",
        )
        evidence = {
            "source_id": session["source_id"],
            "container_name": name,
            "container_id": container_id,
            "image_id": IMAGE_ID,
            "probe_source_sha256": _sha256_bytes(probe),
            "command_manifest_sha256": _sha256_bytes(
                _canonical_bytes(_portable_command_manifest(session))
            ),
            "config_checks": config_checks,
            "result": result,
            "stdout_sha256": _sha256_bytes(started.stdout),
            "stdout_bytes": len(started.stdout),
            "stderr_sha256": _sha256_bytes(started.stderr),
            "stderr_bytes": len(started.stderr),
            "raw_record_bytes_emitted": False,
        }
    finally:
        if created:
            cleanup_target = container_id or name
            removed = runner.run(
                [docker, "rm", "--force", cleanup_target],
                timeout_seconds=20,
            )
            _require(removed.returncode == 0, "container cleanup failed")
            removed_inspect = runner.run(
                [docker, "inspect", cleanup_target],
                timeout_seconds=20,
            )
            _require(removed_inspect.returncode != 0, "removed container is still inspectable")
            _require(removed_inspect.stdout == b"", "removed-container inspect emitted stdout")
            _require(
                _managed_container_ids(runner=runner, docker=docker) == [],
                "labeled D-119 container remains after cleanup",
            )
    _require(evidence is not None, "session evidence missing")
    evidence["cleanup"] = {
        "removed_by_exact_container_id": True,
        "removed_container_not_inspectable": True,
        "label_wide_residual_container_count": 0,
    }
    return evidence


def _managed_container_ids(*, runner: CommandRunner, docker: str) -> list[str]:
    result = _run_ok(
        runner,
        [
            docker,
            "ps",
            "--all",
            "--filter",
            "label=io.patchloop.managed=d119-isolation",
            "--format",
            "{{.ID}}",
        ],
        label="D-119 labeled container inventory",
    )
    ids = [line for line in result.stdout.decode("ascii", errors="strict").splitlines() if line]
    _require(
        all(re.fullmatch(r"[0-9a-f]{12,64}", value) for value in ids), "container inventory invalid"
    )
    return ids


class _Journal:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.sequence = 0
        self.head = "sha256:" + "0" * 64
        parent = path.parent.stat()
        self._parent_identity = (parent.st_dev, parent.st_ino)
        self._handle = path.open("xb")
        opened = os.fstat(self._handle.fileno())
        selected = path.stat()
        _require(
            (opened.st_dev, opened.st_ino) == (selected.st_dev, selected.st_ino),
            "journal identity changed during create",
        )
        self._file_identity = (opened.st_dev, opened.st_ino)

    def append(self, event: str, data: Mapping[str, Any]) -> dict[str, Any]:
        body = {
            "schema_version": "cutoff-isolation-journal-record-d119-v1",
            "sequence": self.sequence,
            "recorded_at": _now(),
            "event": event,
            "previous_record_hash": self.head,
            "data": dict(data),
        }
        record_hash = _sha256_bytes(_canonical_bytes(body))
        record = {**body, "record_hash": record_hash}
        self._handle.write(_canonical_bytes(record) + b"\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())
        self.sequence += 1
        self.head = record_hash
        return record

    def close(self) -> None:
        if not self._handle.closed:
            self._handle.flush()
            os.fsync(self._handle.fileno())
            opened = os.fstat(self._handle.fileno())
            selected = self.path.stat()
            parent = self.path.parent.stat()
            _require(
                (opened.st_dev, opened.st_ino)
                == (selected.st_dev, selected.st_ino)
                == self._file_identity,
                "journal identity changed before close",
            )
            _require(
                (parent.st_dev, parent.st_ino) == self._parent_identity,
                "journal parent identity changed",
            )
            self._handle.close()


def _write_new(
    path: Path,
    payload: Mapping[str, Any],
    *,
    repository: Path,
) -> None:
    relative = path.relative_to(repository)
    selected = _safe_path(repository, relative, must_exist=False)
    _require(selected == path, "output path resolution differs")
    path.parent.mkdir(parents=True, exist_ok=True)
    _require(not path.exists() and not path.is_symlink(), f"output collision: {path.name}")
    _require(not _is_linklike(path), f"output link collision: {path.name}")
    parent_before = path.parent.stat()
    content = _pretty_bytes(payload)
    with path.open("xb") as handle:
        opened = os.fstat(handle.fileno())
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        after_fd = os.fstat(handle.fileno())
        after_path = path.stat()
        _require(
            (opened.st_dev, opened.st_ino)
            == (after_fd.st_dev, after_fd.st_ino)
            == (after_path.st_dev, after_path.st_ino),
            f"output identity changed: {path.name}",
        )
        _require(after_fd.st_size == len(content), f"output size differs: {path.name}")
    parent_after = path.parent.stat()
    _require(
        (parent_before.st_dev, parent_before.st_ino) == (parent_after.st_dev, parent_after.st_ino),
        f"output parent identity changed: {path.name}",
    )
    reread = _read_json_canonical(path, label=path.name)
    _require(reread == payload, f"output reread differs: {path.name}")


def _output_state(repository: Path) -> str:
    present = [
        key
        for key, relative in OUTPUT_PATHS.items()
        if repository.joinpath(relative).exists() or repository.joinpath(relative).is_symlink()
    ]
    if not present:
        return "empty"
    if len(present) == len(OUTPUT_PATHS):
        return "complete"
    return "partial"


def _read_journal(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    content = _read_stable_content(path, label="D-119 execution journal")
    _require(content.endswith(b"\n"), "journal must end with a newline")
    rows = []
    previous = "sha256:" + "0" * 64
    for sequence, line in enumerate(content.splitlines()):
        try:
            row = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise D119QualificationError("journal row invalid") from exc
        _require(isinstance(row, dict), "journal row must be an object")
        _require(line == _canonical_bytes(row), "journal row bytes are not canonical")
        _require(
            set(row)
            == {
                "schema_version",
                "sequence",
                "recorded_at",
                "event",
                "previous_record_hash",
                "data",
                "record_hash",
            },
            "journal record fields differ",
        )
        _require(type(row["sequence"]) is int, "journal sequence type differs")
        _require(row["sequence"] == sequence, "journal sequence differs")
        _require(
            isinstance(row["previous_record_hash"], str)
            and _SHA256.fullmatch(row["previous_record_hash"]) is not None,
            "journal previous hash invalid",
        )
        _require(row["previous_record_hash"] == previous, "journal chain differs")
        claimed_hash = row["record_hash"]
        _require(
            isinstance(claimed_hash, str) and _SHA256.fullmatch(claimed_hash) is not None,
            "journal record hash invalid",
        )
        body = {key: value for key, value in row.items() if key != "record_hash"}
        _require(claimed_hash == _sha256_bytes(_canonical_bytes(body)), "journal row hash differs")
        previous = claimed_hash
        rows.append(row)
    _require(rows, "journal must contain records")
    _require(
        content == b"".join(_canonical_bytes(row) + b"\n" for row in rows),
        "journal file bytes are not canonical",
    )
    binding = {
        "path": OUTPUT_PATHS["journal"].as_posix(),
        "record_count": len(rows),
        "head_hash": previous,
        "file_bytes": len(content),
        "file_sha256": _sha256_bytes(content),
    }
    return rows, binding


def _journal_binding(path: Path) -> dict[str, Any]:
    return _read_journal(path)[1]


def _binding_for_payload(
    relative: Path, payload: Mapping[str, Any], id_field: str
) -> dict[str, Any]:
    content = _pretty_bytes(payload)
    return {
        "path": relative.as_posix(),
        id_field: payload[id_field],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(content),
        "file_sha256": _sha256_bytes(content),
    }


def _preflight_authority() -> dict[str, bool]:
    return {
        "trusted_cutoff_research_authorized": True,
        "hash_only_isolation_negative_probe_authorized": True,
        "opaque_container_record_parse_authorized": False,
        "pool_selection_acquisition_or_freeze_authorized": False,
        "issue_labeling_or_review_authorized": False,
        "matcher_classifier_or_calibration_authorized": False,
        "score_policy_or_index_mutation_authorized": False,
        "retrieval_or_runtime_injection_authorized": False,
        "agent_provider_evaluator_or_core_authorized": False,
        "d117_proposed_next_action_authorized": False,
        "d117_proposed_next_action_consumed": False,
    }


def _isolation_qualification() -> dict[str, Any]:
    return {
        "hash_only_isolation_profile_verified": True,
        "isolation_session_count": 2,
        "opaque_stream_hash_read_count": 2,
        "record_container_parse_count": 0,
        "record_field_read_count": 0,
        "record_projection_isolation_verified": False,
        "blind_role_isolation_verified": False,
        "residual_container_count": 0,
    }


def _aggregate_disposition() -> dict[str, Any]:
    return {
        "status": "BLOCKED_INSUFFICIENT_PREEXISTENCE",
        "trusted_cutoff_anchor_verified": False,
        "hash_only_isolation_profile_verified": True,
        "record_projection_isolation_verified": False,
        "post_hoc": True,
        "independent": False,
        "eligible_for_independent_calibration": False,
        "execution_authorization_candidate_ready": False,
    }


def _gate_evidence_boundary() -> dict[str, Any]:
    return {
        "dataset_record_read_count": 0,
        "incidental_public_example_parser_overreturn_count": 1,
        "opaque_stream_hash_read_count": 2,
        "record_container_parse_count": 0,
        "pool_member_id_read_count": 0,
        "pool_selection_acquisition_or_freeze_count": 0,
        "issue_labeling_or_review_count": 0,
        "matcher_classifier_calibration_execution_count": 0,
        "retrieval_agent_provider_evaluator_call_count": 0,
        "added_model_cost_usd": 0,
    }


def _gate_authority() -> dict[str, Any]:
    return {
        "trusted_cutoff_anchor_verified": False,
        "hash_only_isolation_profile_verified": True,
        "record_projection_isolation_verified": False,
        "independent_generalization_validated": False,
        "true_relevance_established": False,
        "d117_proposed_next_action_authorized": False,
        "d117_proposed_next_action_consumed": False,
        "pool_selection_acquisition_or_freeze_authorized": False,
        "matcher_classifier_or_calibration_authorized": False,
        "score_policy_or_index_changed": False,
        "retrieval_ready": False,
        "runtime_memory_injection_count": 0,
        "agent_runs": 0,
        "provider_calls": 0,
        "evaluator_calls": 0,
        "core_campaign_unlocked": False,
        "analysis_campaign_unlocked": False,
    }


def _isolation_evidence_body(
    *,
    recorded_at: str,
    approval_binding: Mapping[str, Any],
    preflight_binding: Mapping[str, Any],
    journal_binding: Mapping[str, Any],
    sessions: Sequence[Mapping[str, Any]],
    source_state: Mapping[str, Any],
    implementation_state: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "two-session-exact-object-hash-only-isolation-evidence",
        "recorded_at": recorded_at,
        "approval_receipt": dict(approval_binding),
        "preflight": dict(preflight_binding),
        "journal": dict(journal_binding),
        "profile": isolation_profile(),
        "sessions": [dict(session) for session in sessions],
        "source_pre_state": dict(source_state),
        "source_post_state": dict(source_state),
        "source_fingerprints_equal": True,
        "implementation_pre_state": dict(implementation_state),
        "implementation_post_state": dict(implementation_state),
        "implementation_fingerprints_equal": True,
        "qualification": _isolation_qualification(),
    }


def _gate_body(
    *,
    recorded_at: str,
    d118: Mapping[str, Any],
    approval_binding: Mapping[str, Any],
    preflight_binding: Mapping[str, Any],
    anchor_binding: Mapping[str, Any],
    journal_binding: Mapping[str, Any],
    isolation_binding: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "trusted-cutoff-and-hash-only-isolation-source-gate",
        "recorded_at": recorded_at,
        "d118_source_gate": d118["source_gate"],
        "d118_evidence_pack": d118["evidence_pack"],
        "approval_receipt": dict(approval_binding),
        "preflight": dict(preflight_binding),
        "anchor_evidence": dict(anchor_binding),
        "journal": dict(journal_binding),
        "isolation_evidence": dict(isolation_binding),
        "aggregate_disposition": _aggregate_disposition(),
        "evidence_boundary": _gate_evidence_boundary(),
        "authority": _gate_authority(),
        "next_gate": "explicit-post-hoc-diagnostic-control-decision-or-new-trusted-anchor",
    }


def _parse_recorded_at(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"{label} timestamp invalid")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise D119QualificationError(f"{label} timestamp invalid") from exc
    _require(parsed.tzinfo is not None, f"{label} timestamp must be timezone-aware")
    _require(parsed.utcoffset() == UTC.utcoffset(parsed), f"{label} timestamp must be UTC")
    return parsed


def _require_exact_payload(actual: Any, expected: Any, message: str) -> None:
    _require(_canonical_bytes(actual) == _canonical_bytes(expected), message)


def _validate_session_evidence(
    session: Mapping[str, Any],
    *,
    plan: Mapping[str, Any],
) -> None:
    _require(
        set(session)
        == {
            "source_id",
            "container_name",
            "container_id",
            "image_id",
            "probe_source_sha256",
            "command_manifest_sha256",
            "config_checks",
            "result",
            "stdout_sha256",
            "stdout_bytes",
            "stderr_sha256",
            "stderr_bytes",
            "raw_record_bytes_emitted",
            "cleanup",
        },
        "session evidence fields differ",
    )
    source_id = str(plan["source_id"])
    _require(session["source_id"] == source_id, "session source ID differs")
    _require(
        re.fullmatch(
            rf"patchloop-d119-{re.escape(source_id)}-[0-9a-f]{{12}}",
            str(session["container_name"]),
        )
        is not None,
        "session container name differs",
    )
    _require(
        isinstance(session["container_id"], str)
        and re.fullmatch(r"[0-9a-f]{64}", session["container_id"]) is not None,
        "session container ID differs",
    )
    _require(session["image_id"] == IMAGE_ID, "session image differs")
    _require(
        session["probe_source_sha256"] == plan["probe_source_sha256"],
        "session probe SHA differs",
    )
    expected_command_sha = _sha256_bytes(_canonical_bytes(_portable_command_manifest(plan)))
    _require(
        session["command_manifest_sha256"] == expected_command_sha,
        "session command manifest differs",
    )
    _require_exact_payload(
        session["config_checks"], _expected_config_checks(), "session config differs"
    )
    expected_result = _expected_probe_result(plan)
    _require_exact_payload(session["result"], expected_result, "session result differs")
    stdout = _canonical_bytes(expected_result) + b"\n"
    _require(session["stdout_sha256"] == _sha256_bytes(stdout), "session stdout SHA differs")
    _require(
        type(session["stdout_bytes"]) is int and session["stdout_bytes"] == len(stdout),
        "session stdout bytes differ",
    )
    _require(session["stderr_sha256"] == _sha256_bytes(b""), "session stderr SHA differs")
    _require(
        type(session["stderr_bytes"]) is int and session["stderr_bytes"] == 0,
        "session stderr bytes differ",
    )
    _require(session["raw_record_bytes_emitted"] is False, "raw record output overclaim")
    _require_exact_payload(
        session["cleanup"],
        {
            "removed_by_exact_container_id": True,
            "removed_container_not_inspectable": True,
            "label_wide_residual_container_count": 0,
        },
        "session cleanup differs",
    )


def _validate_journal_records(
    rows: Sequence[Mapping[str, Any]],
    *,
    approval: Mapping[str, Any],
    preflight: Mapping[str, Any],
    sessions: Sequence[Mapping[str, Any]],
) -> list[datetime]:
    _require(len(rows) == 7, "journal record count differs")
    plans = preflight["semantic_body"]["session_plan"]
    expected_events: list[tuple[str, dict[str, Any]]] = [
        (
            "ExecutionClaimed",
            {
                "approval_receipt_id": approval["receipt_id"],
                "preflight_id": preflight["preflight_id"],
                "authorized_action_hash": preflight["semantic_body"]["authorized_action_hash"],
                "automatic_retry_allowed": False,
            },
        ),
        ("ImageIdentityVerified", {"image_id": IMAGE_ID}),
    ]
    for plan, session in zip(plans, sessions, strict=True):
        expected_events.extend(
            [
                (
                    "IsolationSessionStarted",
                    {
                        "source_id": plan["source_id"],
                        "input_file_sha256": plan["file_sha256"],
                        "probe_source_sha256": plan["probe_source_sha256"],
                    },
                ),
                (
                    "IsolationSessionCompleted",
                    {
                        "source_id": plan["source_id"],
                        "result_sha256": _sha256_bytes(_canonical_bytes(session)),
                        "cleanup_verified": True,
                    },
                ),
            ]
        )
    expected_events.append(
        (
            "ExecutionCompleted",
            {
                "session_count": 2,
                "source_fingerprints_equal": True,
                "implementation_fingerprints_equal": True,
                "trusted_cutoff_anchor_verified": False,
            },
        )
    )
    timestamps: list[datetime] = []
    for sequence, (row, (event, data)) in enumerate(zip(rows, expected_events, strict=True)):
        _require(
            set(row)
            == {
                "schema_version",
                "sequence",
                "recorded_at",
                "event",
                "previous_record_hash",
                "data",
                "record_hash",
            },
            "journal record fields differ",
        )
        _require(
            row["schema_version"] == "cutoff-isolation-journal-record-d119-v1",
            "journal schema version differs",
        )
        _require(row["sequence"] == sequence, "journal sequence differs")
        _require(row["event"] == event, "journal event differs")
        _require_exact_payload(row["data"], data, "journal event data differs")
        timestamps.append(_parse_recorded_at(row["recorded_at"], label=f"journal[{sequence}]"))
    _require(
        all(left <= right for left, right in zip(timestamps, timestamps[1:], strict=False)),
        "journal chronology differs",
    )
    return timestamps


def run_d119_cutoff_isolation_qualification(
    *,
    repository: str | Path | None = None,
    docker_path: str | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Execute the approved one-use D-119 hash-only isolation qualification."""

    _require(
        command_runner is None,
        "custom command runners are forbidden for D-119 evidence materialization",
    )
    repo = _repo_root(repository)
    _validate_logical_path_contract()
    state = _output_state(repo)
    if state == "complete":
        return validate_d119_artifacts(repository=repo, current_objects=True)
    _require(state == "empty", "partial D-119 evidence consumes the one-use capability")

    docker_candidate = Path(docker_path or _docker_path())
    _require(not _is_linklike(docker_candidate), "Docker CLI path must not be link-like")
    docker = str(docker_candidate.resolve(strict=True))
    _require(Path(docker).name.casefold() == "docker.exe", "Docker CLI file name differs")
    docker_file = _stable_binding(Path(docker), label="Docker CLI")
    _require(docker_file["file_bytes"] == DOCKER_CLI_BYTES, "Docker CLI byte count differs")
    _require(docker_file["file_sha256"] == DOCKER_CLI_SHA256, "Docker CLI SHA differs")
    docker_binding = _docker_cli_binding()
    runner: CommandRunner = SubprocessCommandRunner()

    d118 = _d118_context(repo, current_objects=True)
    source_pre = _source_state(repo)
    implementation_pre = _implementation_state(repo)
    recorded_at = _now()
    preflight_body = _preflight_body(
        recorded_at=recorded_at,
        d118=d118,
        source_state=source_pre,
        implementation_state=implementation_pre,
        docker_cli_binding=docker_binding,
        repository=repo,
    )
    approval = _envelope(
        schema_version="cutoff-isolation-approval-receipt-d119-v1",
        id_field="receipt_id",
        id_prefix="d119approval_",
        body=_approval_body(
            recorded_at=recorded_at,
            d118=d118,
            source_state=source_pre,
            implementation_state=implementation_pre,
            preflight_body=preflight_body,
        ),
    )
    preflight_body["approval_receipt"] = _binding_for_payload(
        OUTPUT_PATHS["approval_receipt"], approval, "receipt_id"
    )
    preflight = _envelope(
        schema_version="cutoff-isolation-preflight-d119-v1",
        id_field="preflight_id",
        id_prefix="d119preflight_",
        body=preflight_body,
    )
    _write_new(
        repo / OUTPUT_PATHS["approval_receipt"],
        approval,
        repository=repo,
    )
    _write_new(
        repo / OUTPUT_PATHS["preflight"],
        preflight,
        repository=repo,
    )

    journal_path = _safe_path(repo, OUTPUT_PATHS["journal"], must_exist=False)
    journal = _Journal(journal_path)
    journal.append(
        "ExecutionClaimed",
        {
            "approval_receipt_id": approval["receipt_id"],
            "preflight_id": preflight["preflight_id"],
            "authorized_action_hash": preflight["semantic_body"]["authorized_action_hash"],
            "automatic_retry_allowed": False,
        },
    )

    try:
        tag = (
            _run_ok(
                runner,
                [docker, "image", "inspect", "--format", "{{.Id}}", IMAGE_TAG],
                label="docker image identity",
            )
            .stdout.decode("utf-8", errors="strict")
            .strip()
        )
        _require(tag == IMAGE_ID, "Docker image tag identity differs")
        journal.append("ImageIdentityVerified", {"image_id": IMAGE_ID})
        sessions = []
        for session in preflight["semantic_body"]["session_plan"]:
            journal.append(
                "IsolationSessionStarted",
                {
                    "source_id": session["source_id"],
                    "input_file_sha256": session["file_sha256"],
                    "probe_source_sha256": session["probe_source_sha256"],
                },
            )
            result = _execute_session(
                session=session,
                repository=repo,
                docker=docker,
                runner=runner,
            )
            sessions.append(result)
            journal.append(
                "IsolationSessionCompleted",
                {
                    "source_id": session["source_id"],
                    "result_sha256": _sha256_bytes(_canonical_bytes(result)),
                    "cleanup_verified": True,
                },
            )
        source_post = _source_state(repo)
        implementation_post = _implementation_state(repo)
        _require(source_post == source_pre, "opaque source changed during D-119")
        _require(
            implementation_post == implementation_pre,
            "D-119 implementation changed during execution",
        )
        journal.append(
            "ExecutionCompleted",
            {
                "session_count": len(sessions),
                "source_fingerprints_equal": True,
                "implementation_fingerprints_equal": True,
                "trusted_cutoff_anchor_verified": False,
            },
        )
    except BaseException as exc:
        with suppress(BaseException):
            journal.append(
                "ExecutionFailed",
                {
                    "error_type": type(exc).__name__,
                    "automatic_retry_allowed": False,
                },
            )
        with suppress(BaseException):
            journal.close()
        raise

    journal.close()
    journal_binding = _journal_binding(journal_path)
    anchor = _envelope(
        schema_version="external-anchor-evidence-d119-v1",
        id_field="anchor_evidence_id",
        id_prefix="d119anchor_",
        body=_anchor_evidence_body(_now()),
    )
    anchor_binding = _binding_for_payload(
        OUTPUT_PATHS["anchor_evidence"], anchor, "anchor_evidence_id"
    )
    approval_binding = _binding_for_payload(
        OUTPUT_PATHS["approval_receipt"], approval, "receipt_id"
    )
    preflight_binding = _binding_for_payload(OUTPUT_PATHS["preflight"], preflight, "preflight_id")
    isolation_body = _isolation_evidence_body(
        recorded_at=_now(),
        approval_binding=approval_binding,
        preflight_binding=preflight_binding,
        journal_binding=journal_binding,
        sessions=sessions,
        source_state=source_pre,
        implementation_state=implementation_pre,
    )
    isolation = _envelope(
        schema_version="hash-only-isolation-evidence-d119-v1",
        id_field="isolation_evidence_id",
        id_prefix="d119isolation_",
        body=isolation_body,
    )
    isolation_binding = _binding_for_payload(
        OUTPUT_PATHS["isolation_evidence"], isolation, "isolation_evidence_id"
    )
    gate_body = _gate_body(
        recorded_at=_now(),
        d118=d118,
        approval_binding=approval_binding,
        preflight_binding=preflight_binding,
        anchor_binding=anchor_binding,
        journal_binding=journal_binding,
        isolation_binding=isolation_binding,
    )
    gate = _envelope(
        schema_version="cutoff-isolation-source-gate-d119-v1",
        id_field="gate_id",
        id_prefix="d119_",
        body=gate_body,
    )
    _write_new(
        repo / OUTPUT_PATHS["anchor_evidence"],
        anchor,
        repository=repo,
    )
    _write_new(
        repo / OUTPUT_PATHS["isolation_evidence"],
        isolation,
        repository=repo,
    )
    _write_new(
        repo / OUTPUT_PATHS["source_gate"],
        gate,
        repository=repo,
    )
    return validate_d119_artifacts(repository=repo, current_objects=True)


def validate_d119_artifacts(
    *,
    repository: str | Path | None = None,
    current_objects: bool = False,
) -> dict[str, Any]:
    """Validate the sealed D-119 evidence without starting Docker."""

    repo = _repo_root(repository)
    _validate_logical_path_contract()
    _require(_output_state(repo) == "complete", "D-119 evidence is not complete")
    d118 = _d118_context(repo, current_objects=current_objects)
    source_state = _source_state(repo) if current_objects else _expected_source_state()
    implementation_state = _implementation_state(repo)
    specs = (
        (
            "approval_receipt",
            "receipt_id",
            "d119approval_",
            "cutoff-isolation-approval-receipt-d119-v1",
        ),
        (
            "preflight",
            "preflight_id",
            "d119preflight_",
            "cutoff-isolation-preflight-d119-v1",
        ),
        (
            "anchor_evidence",
            "anchor_evidence_id",
            "d119anchor_",
            "external-anchor-evidence-d119-v1",
        ),
        (
            "isolation_evidence",
            "isolation_evidence_id",
            "d119isolation_",
            "hash-only-isolation-evidence-d119-v1",
        ),
        (
            "source_gate",
            "gate_id",
            "d119_",
            "cutoff-isolation-source-gate-d119-v1",
        ),
    )
    values: dict[str, dict[str, Any]] = {}
    id_fields: dict[str, str] = {}
    artifact_file_bindings: dict[str, dict[str, Any]] = {}
    for key, id_field, prefix, schema_version in specs:
        path = _safe_path(repo, OUTPUT_PATHS[key], must_exist=True)
        value = _read_json_canonical(path, label=key)
        _validate_envelope(
            value,
            id_field=id_field,
            id_prefix=prefix,
            label=key,
            expected_schema_version=schema_version,
        )
        values[key] = value
        id_fields[key] = id_field
        artifact_file_bindings[key] = _stable_binding(path, label=key)

    journal_rows, journal_binding = _read_journal(
        _safe_path(repo, OUTPUT_PATHS["journal"], must_exist=True)
    )
    actual_bindings = {
        key: _binding_for_payload(OUTPUT_PATHS[key], values[key], id_fields[key])
        for key in (
            "approval_receipt",
            "preflight",
            "anchor_evidence",
            "isolation_evidence",
        )
    }
    gate = values["source_gate"]["semantic_body"]
    for key in (
        "approval_receipt",
        "preflight",
        "anchor_evidence",
        "isolation_evidence",
    ):
        _require(gate.get(key) == actual_bindings[key], f"gate {key} binding differs")
    _require(gate.get("d118_source_gate") == d118["source_gate"], "gate D-118 binding differs")
    _require(gate.get("d118_evidence_pack") == d118["evidence_pack"], "gate D-118 pack differs")
    _require(gate.get("journal") == journal_binding, "gate journal binding differs")

    aggregate = gate.get("aggregate_disposition")
    _require(isinstance(aggregate, dict), "D-119 aggregate disposition missing")
    _require(aggregate.get("status") == "BLOCKED_INSUFFICIENT_PREEXISTENCE", "D-119 status differs")
    _require(aggregate.get("trusted_cutoff_anchor_verified") is False, "cutoff overclaim")
    _require(
        aggregate.get("hash_only_isolation_profile_verified") is True,
        "isolation evidence missing",
    )
    _require(aggregate.get("record_projection_isolation_verified") is False, "projection overclaim")
    _require(aggregate.get("independent") is False, "independence overclaim")
    authority = gate.get("authority")
    _require(isinstance(authority, dict), "gate authority missing")
    for key in (
        "d117_proposed_next_action_authorized",
        "d117_proposed_next_action_consumed",
        "pool_selection_acquisition_or_freeze_authorized",
        "matcher_classifier_or_calibration_authorized",
        "score_policy_or_index_changed",
        "retrieval_ready",
        "core_campaign_unlocked",
        "analysis_campaign_unlocked",
    ):
        _require(authority.get(key) is False, f"authority expanded: {key}")

    approval = values["approval_receipt"]
    preflight = values["preflight"]
    approval_body = approval["semantic_body"]
    preflight_body = preflight["semantic_body"]
    approval_time = _parse_recorded_at(approval_body.get("recorded_at"), label="approval")
    preflight_time = _parse_recorded_at(preflight_body.get("recorded_at"), label="preflight")
    _require(approval_time == preflight_time, "approval/preflight chronology differs")

    expected_preflight_body = _preflight_body(
        recorded_at=preflight_body["recorded_at"],
        d118=d118,
        source_state=source_state,
        implementation_state=implementation_state,
        docker_cli_binding=_docker_cli_binding(),
        repository=None,
    )
    expected_approval_body = _approval_body(
        recorded_at=approval_body["recorded_at"],
        d118=d118,
        source_state=source_state,
        implementation_state=implementation_state,
        preflight_body=expected_preflight_body,
    )
    _require_exact_payload(
        approval_body, expected_approval_body, "approval expected payload differs"
    )
    expected_preflight_body["approval_receipt"] = actual_bindings["approval_receipt"]
    _require_exact_payload(
        preflight_body, expected_preflight_body, "preflight expected payload differs"
    )

    anchor = values["anchor_evidence"]
    anchor_body = anchor["semantic_body"]
    anchor_time = _parse_recorded_at(anchor_body.get("recorded_at"), label="anchor")
    _require_exact_payload(
        anchor_body,
        _anchor_evidence_body(anchor_body["recorded_at"]),
        "anchor expected payload differs",
    )

    isolation = values["isolation_evidence"]
    isolation_body = isolation["semantic_body"]
    isolation_time = _parse_recorded_at(
        isolation_body.get("recorded_at"), label="isolation evidence"
    )
    _require(
        isolation_body.get("approval_receipt") == actual_bindings["approval_receipt"],
        "isolation approval binding differs",
    )
    _require(
        isolation_body.get("preflight") == actual_bindings["preflight"],
        "isolation preflight binding differs",
    )
    _require(isolation_body.get("journal") == journal_binding, "isolation journal differs")
    sessions = isolation_body.get("sessions")
    _require(isinstance(sessions, list) and len(sessions) == 2, "isolation session count differs")
    plans = expected_preflight_body["session_plan"]
    for session, plan in zip(sessions, plans, strict=True):
        _require(isinstance(session, dict), "session evidence must be an object")
        _validate_session_evidence(session, plan=plan)
    _require(
        len({session["container_name"] for session in sessions}) == 2,
        "session container names must be distinct",
    )
    _require(
        len({session["container_id"] for session in sessions}) == 2,
        "session container IDs must be distinct",
    )
    expected_isolation_body = _isolation_evidence_body(
        recorded_at=isolation_body["recorded_at"],
        approval_binding=actual_bindings["approval_receipt"],
        preflight_binding=actual_bindings["preflight"],
        journal_binding=journal_binding,
        sessions=sessions,
        source_state=source_state,
        implementation_state=implementation_state,
    )
    _require_exact_payload(
        isolation_body, expected_isolation_body, "isolation expected payload differs"
    )

    journal_times = _validate_journal_records(
        journal_rows,
        approval=approval,
        preflight=preflight,
        sessions=sessions,
    )
    gate_time = _parse_recorded_at(gate.get("recorded_at"), label="source gate")
    _require(
        approval_time <= journal_times[0]
        and journal_times[-1] <= anchor_time <= isolation_time <= gate_time,
        "D-119 artifact chronology differs",
    )

    expected_gate_body = _gate_body(
        recorded_at=gate["recorded_at"],
        d118=d118,
        approval_binding=actual_bindings["approval_receipt"],
        preflight_binding=actual_bindings["preflight"],
        anchor_binding=actual_bindings["anchor_evidence"],
        journal_binding=journal_binding,
        isolation_binding=actual_bindings["isolation_evidence"],
    )
    _require_exact_payload(gate, expected_gate_body, "gate expected payload differs")

    for key, expected_binding in artifact_file_bindings.items():
        path = _safe_path(repo, OUTPUT_PATHS[key], must_exist=True)
        _require(
            _stable_binding(path, label=f"{key} final reread") == expected_binding,
            f"{key} changed during validation",
        )
    _require(
        _journal_binding(_safe_path(repo, OUTPUT_PATHS["journal"], must_exist=True))
        == journal_binding,
        "journal changed during validation",
    )
    _require(
        _implementation_state(repo) == implementation_state,
        "implementation changed during validation",
    )
    if current_objects:
        _require(_source_state(repo) == source_state, "source changed during validation")

    return {
        "status": aggregate["status"],
        "gate_id": values["source_gate"]["gate_id"],
        "gate_semantic_body_hash": values["source_gate"]["semantic_body_hash"],
        "gate_file_sha256": artifact_file_bindings["source_gate"]["file_sha256"],
        "anchor_evidence_id": values["anchor_evidence"]["anchor_evidence_id"],
        "isolation_evidence_id": values["isolation_evidence"]["isolation_evidence_id"],
        "journal": journal_binding,
        "trusted_cutoff_anchor_verified": False,
        "hash_only_isolation_profile_verified": True,
        "record_projection_isolation_verified": False,
        "independent": False,
        "execution_authorization_candidate_ready": False,
    }
