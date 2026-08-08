"""Prepare an exact candidate for a later D-121 successor run.

The preparation authorized by D-120 may create and inspect a container but
must never start it or open either opaque benchmark object.  It seals an exact
future execution candidate. The future execution path is implemented and bound
here, but is deliberately absent from the public preparation CLI. Approval is
repository-local and self-attested rather than an authenticated capability, so
a later orchestrator must still verify the separate user message before calling
the internal execution entrypoint.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import unicodedata
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from patchloop.errors import ContractError
from patchloop.memory import d119_cutoff_isolation_qualification as d119
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes

MILESTONE = "D-121"

D120_ACTION_HASH = "sha256:88195baf93289f3d4613a2d33e6bf16b271fb65d6cf6384a2fdbc8fff20512c4"
D120_CANDIDATE_SPEC = {
    "path": "reports/memory-development/d120-d119-cleanup-correction-authorization-candidate.json",
    "id_field": "candidate_id",
    "identifier": (
        "d120cleanupcandidate_86d95b4b3cf0b49a20724b136075bfa9da281fce4dc6b20b6063a07bfcdd9b82"
    ),
    "semantic_body_hash": (
        "sha256:86d95b4b3cf0b49a20724b136075bfa9da281fce4dc6b20b6063a07bfcdd9b82"
    ),
    "file_bytes": 10_464,
    "file_sha256": "sha256:f4f985e6574ead218ffea4813d234c1b5c35cdf60e109de5bbe0849dd25127d8",
}
D120_GATE_SPEC = {
    "path": "reports/memory-development/d120-d119-cleanup-correction-source-gate.json",
    "id_field": "gate_id",
    "identifier": "d120_8172bae0e2446e647edb8d03272cf5499a9faa8f92a1f26b8cd08b5a9dc6abbd",
    "semantic_body_hash": (
        "sha256:8172bae0e2446e647edb8d03272cf5499a9faa8f92a1f26b8cd08b5a9dc6abbd"
    ),
    "file_bytes": 12_140,
    "file_sha256": "sha256:cd4fe9024bfb1b44e9e762412e442f3c2958085629b15e19f7a9423aefa3581b",
}

PROTECTED_FILE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "path": "reports/memory-development/d119-cutoff-isolation-approval-receipt.json",
        "file_bytes": 5_299,
        "file_sha256": "sha256:625cd6487fffe50b2429e011c67da222ec0da020dbf62d65a911fa83da3f550c",
    },
    {
        "path": "reports/memory-development/d119-cutoff-isolation-preflight.json",
        "file_bytes": 11_229,
        "file_sha256": "sha256:57f59fc29054276947851abdfe3dbf0040fe10cef5624946e66dc84a698fb18a",
    },
    {
        "path": "reports/memory-development/d119-isolation-execution.jsonl",
        "file_bytes": 2_075,
        "file_sha256": "sha256:fadda3b86b2ad954a1d233b0dbf11d67b8a9a86f3db6704eab555eec5f2a4950",
    },
    {
        "path": "patchloop/memory/d119_cutoff_isolation_qualification.py",
        "file_bytes": 79_260,
        "file_sha256": "sha256:8428dc47241ee8698eb8edc075521d4fa2044f9e793325771df2fab0c917312b",
    },
    {
        "path": "scripts/run_d119_cutoff_isolation_qualification.py",
        "file_bytes": 1_906,
        "file_sha256": "sha256:fff81e5c6d8218f1102c5ff5bd485513db56ce3a2fe205faa219e708c8acc21b",
    },
    {
        "path": "tests/test_d119_cutoff_isolation_qualification.py",
        "file_bytes": 32_427,
        "file_sha256": "sha256:f2c4f3b50980d4697aca81967d5d19e2021df455dc320d5ddffdd3458d761650",
    },
    {
        "path": "reports/memory-development/d120-d119-partial-failure-preflight.json",
        "file_bytes": 21_101,
        "file_sha256": "sha256:6ec5ff207fdf24cb8baab733b9db096ece3d1fe1ba0ba5c6c644ac6c20ccd5ea",
    },
    D120_CANDIDATE_SPEC,
    D120_GATE_SPEC,
    {
        "path": "patchloop/memory/d120_d119_cleanup_correction_authorization.py",
        "file_bytes": 44_386,
        "file_sha256": "sha256:d7b15d103c9940818178d17eb9f226417f06012ca0eace5f9fdb106c5c0a7895",
    },
    {
        "path": "scripts/build_d120_d119_cleanup_correction_authorization.py",
        "file_bytes": 1_124,
        "file_sha256": "sha256:1250211b93b70e568ac96ccf756415d20c7de6e974b79546b6c58d67cf05c907",
    },
    {
        "path": "tests/test_d120_d119_cleanup_correction_authorization.py",
        "file_bytes": 23_763,
        "file_sha256": "sha256:974e4920146c90a3bf675dfd28792574f07ba50bae655e89222acb0c5a0d5b82",
    },
    {
        "path": "docker/Dockerfile.sandbox",
        "file_bytes": 386,
        "file_sha256": "sha256:f310b88e8a2769b83202c3fb7a5cb776142c70a6d45935b648db258d3bc2d944",
    },
)

D119_ABSENT_OUTPUTS = (
    "reports/memory-development/d119-external-anchor-evidence.json",
    "reports/memory-development/d119-isolation-evidence.json",
    "reports/memory-development/d119-cutoff-isolation-source-gate.json",
)

IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d121_hash_only_isolation_successor.py"),
    Path("scripts/run_d121_hash_only_isolation_successor.py"),
    Path("tests/test_d121_hash_only_isolation_successor.py"),
)

PREPARATION_OUTPUT_PATHS = {
    "approval_receipt": Path(
        "reports/memory-development/d121-isolation-successor-preparation-approval-receipt.json"
    ),
    "readiness": Path(
        "reports/memory-development/d121-isolation-successor-readiness-preflight.json"
    ),
    "execution_candidate": Path(
        "reports/memory-development/d121-isolation-successor-execution-authorization-candidate.json"
    ),
    "source_gate": Path(
        "reports/memory-development/d121-isolation-successor-authorization-source-gate.json"
    ),
}

EXECUTION_OUTPUT_PATHS = {
    "approval_receipt": Path(
        "reports/memory-development/d121-isolation-successor-execution-approval-receipt.json"
    ),
    "journal": Path("reports/memory-development/d121-isolation-successor-execution.jsonl"),
    "evidence": Path("reports/memory-development/d121-isolation-successor-evidence.json"),
    "completion_gate": Path(
        "reports/memory-development/d121-isolation-successor-completion-gate.json"
    ),
}

IMAGE_TAG = d119.IMAGE_TAG
IMAGE_ID = d119.IMAGE_ID
DOCKER_CLI_BYTES = d119.DOCKER_CLI_BYTES
DOCKER_CLI_SHA256 = d119.DOCKER_CLI_SHA256
PROFILE_HASH = "sha256:82511cd9e7e25be999955e260f009204703ef5dcdbc2340897d821c4f52cf6a5"
SOURCE_FINGERPRINT = "sha256:912c8ad78849f7f674756ab9d4084ed92e3c8a535bc04a6b89a7a14f7170a53f"
MANAGED_LABEL = "io.patchloop.managed=d121-isolation-successor"
ROLE_LABEL = "io.patchloop.role=external-source-hash-only"
SENTINEL_PATH = Path("docker/Dockerfile.sandbox")

SOURCE_PLAN: tuple[dict[str, Any], ...] = (
    {
        "source_id": "swe-bench-dev-f5351",
        "path": (
            ".patchloop/external-evidence/d118/swe-bench-f5351/data/dev-00000-of-00001.parquet"
        ),
        "file_bytes": 1_382_594,
        "file_sha256": "sha256:d758d54540aa4140d0274ed0cc93b8288aa6f323c3c603e2557e7666a47fc41b",
        "probe_source_sha256": (
            "sha256:76dac3eec570730dc9fa9b1ce1cc4344b42971ffc4339b22caf4a569c65bd2bc"
        ),
    },
    {
        "source_id": "swe-gym-train-26a6",
        "path": (
            ".patchloop/external-evidence/d118/swe-gym-26a6/data/train-00000-of-00001.parquet"
        ),
        "file_bytes": 43_644_473,
        "file_sha256": "sha256:60569cea74bb281f7a5579467436a2bc1932c6e0c5f2f7fa0d084392abd9ad97",
        "probe_source_sha256": (
            "sha256:39e64b76b26d8c53e2e128a1ef5c6e09354ca009d1b45157dc9cd0028a493dc7"
        ),
    },
)

ALLOWED_MISSING_INSPECT_STDOUT: dict[bytes, str] = {
    b"": "empty-bytes",
    b"[]": "empty-json-array",
    b"[]\n": "empty-json-array-lf",
    b"[]\r\n": "empty-json-array-crlf",
}

_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
_CONTAINER_ID = re.compile(r"[0-9a-f]{64}\Z")
_MAX_COMMAND_OUTPUT = 16_384
_LOCAL_DOCKER_CONTEXT = "desktop-linux"
_LOCAL_DOCKER_ENDPOINT = "npipe:////./pipe/dockerDesktopLinuxEngine"
_IMAGE_ID_FORMAT = "{{.Id}}"
_INSPECT_PROJECTION_FORMAT = (
    '{"Id":{{json .Id}},"Name":{{json .Name}},"Path":{{json .Path}},'
    '"Args":{{json .Args}},"Image":{{json .Image}},'
    '"Config":{"Cmd":{{json .Config.Cmd}},"WorkingDir":{{json .Config.WorkingDir}},'
    '"User":{{json .Config.User}},"Tty":{{json .Config.Tty}},'
    '"OpenStdin":{{json .Config.OpenStdin}},"Labels":{{json .Config.Labels}}},'
    '"HostConfig":{"NetworkMode":{{json .HostConfig.NetworkMode}},'
    '"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},'
    '"Privileged":{{json .HostConfig.Privileged}},"PidsLimit":{{json .HostConfig.PidsLimit}},'
    '"CapDrop":{{json .HostConfig.CapDrop}},"CapAdd":{{json .HostConfig.CapAdd}},'
    '"SecurityOpt":{{json .HostConfig.SecurityOpt}},"PidMode":{{json .HostConfig.PidMode}},'
    '"IpcMode":{{json .HostConfig.IpcMode}},"Devices":{{json .HostConfig.Devices}},'
    '"DeviceRequests":{{json .HostConfig.DeviceRequests}},"Binds":{{json .HostConfig.Binds}},'
    '"Memory":{{json .HostConfig.Memory}},"NanoCpus":{{json .HostConfig.NanoCpus}},'
    '"RestartPolicy":{{json .HostConfig.RestartPolicy}},"Tmpfs":{{json .HostConfig.Tmpfs}}},'
    '"MountCount":{{len .Mounts}},'
    '"Mounts":[{{with index .Mounts 0}}{"Type":{{json .Type}},'
    '"Source":{{json .Source}},"Destination":{{json .Destination}},'
    '"RW":{{json .RW}}}{{end}}],"State":{"Status":{{json .State.Status}},'
    '"Running":{{json .State.Running}},"Paused":{{json .State.Paused}},'
    '"Restarting":{{json .State.Restarting}},"Dead":{{json .State.Dead}},'
    '"Pid":{{json .State.Pid}},"StartedAt":{{json .State.StartedAt}}}}'
)


class D121PreparationError(ContractError):
    """Raised when D-121 preparation or its sealed evidence is invalid."""


class D121ExecutionError(RuntimeError):
    """Raised by the separately approved D-121 execution path."""


class CommandRunner(Protocol):
    def run(
        self,
        command: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        timeout_seconds: int = 30,
    ) -> subprocess.CompletedProcess[bytes]: ...


class SubprocessCommandRunner:
    def run(
        self,
        command: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        timeout_seconds: int = 30,
    ) -> subprocess.CompletedProcess[bytes]:
        environment = os.environ.copy()
        for key in tuple(environment):
            if key.upper().startswith("DOCKER_"):
                environment.pop(key, None)
        environment["DOCKER_HOST"] = _LOCAL_DOCKER_ENDPOINT
        return subprocess.run(  # noqa: S603
            list(command),
            input=input_bytes,
            capture_output=True,
            check=False,
            env=environment,
            timeout=timeout_seconds,
            shell=False,
        )


def _new_runner() -> CommandRunner:
    return SubprocessCommandRunner()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D121PreparationError(message)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def _pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise D121PreparationError("D-121 repository root cannot be resolved") from exc
    _require(root.is_dir(), "D-121 repository root must be a directory")
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


def _safe_path(
    repository: Path,
    relative: str | Path,
    *,
    must_exist: bool,
    label: str,
) -> Path:
    selected = Path(relative)
    _require(not selected.is_absolute(), f"D-121 {label} must be repository-relative")
    _require(".." not in selected.parts, f"D-121 {label} traverses a parent")
    for part in selected.parts:
        _require(":" not in part, f"D-121 {label} uses an alternate data stream")
        _require(not part.endswith((".", " ")), f"D-121 {label} is ambiguous on Windows")
    logical = repository / selected
    cursor = repository
    for part in selected.parts:
        cursor /= part
        _require(not _is_linklike(cursor), f"D-121 {label} traverses a link or junction")
    try:
        if must_exist:
            resolved = logical.resolve(strict=True)
        else:
            resolved = logical.parent.resolve(strict=True) / logical.name
        resolved.relative_to(repository)
    except (OSError, ValueError) as exc:
        raise D121PreparationError(f"D-121 {label} escapes the repository") from exc
    return resolved


def _read_stable(path: Path, *, label: str) -> bytes:
    _require(path.is_file(), f"D-121 {label} is missing")
    before = path.stat()
    with path.open("rb", buffering=0) as handle:
        opened = os.fstat(handle.fileno())
        _require(
            (before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino),
            f"D-121 {label} identity changed before read",
        )
        content = handle.read()
        after_fd = os.fstat(handle.fileno())
    after_path = path.stat()
    identity = lambda value: (  # noqa: E731
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
    )
    _require(
        identity(before) == identity(opened) == identity(after_fd) == identity(after_path),
        f"D-121 {label} changed during read",
    )
    return content


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D121PreparationError(f"D-121 {label} is not JSON") from exc
    _require(isinstance(value, dict), f"D-121 {label} root must be an object")
    _require(content == _pretty_bytes(value), f"D-121 {label} bytes are not canonical")
    return value


def _envelope(
    *, schema_version: str, id_field: str, id_prefix: str, body: Mapping[str, Any]
) -> dict[str, Any]:
    body_hash = sha256_bytes(_canonical_bytes(body))
    return {
        "schema_version": schema_version,
        id_field: f"{id_prefix}{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": dict(body),
    }


def _binding(path: str | Path, content: bytes, **identity: Any) -> dict[str, Any]:
    return {
        "path": Path(path).as_posix(),
        **identity,
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _parse_time(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"D-121 {label} time invalid")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise D121PreparationError(f"D-121 {label} time invalid") from exc
    _require(parsed.utcoffset() == UTC.utcoffset(parsed), f"D-121 {label} time must be UTC")
    return parsed


def _exact_file_state(repository: Path, specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    for spec in specs:
        path = _safe_path(repository, spec["path"], must_exist=True, label="protected input")
        content = _read_stable(path, label="protected input")
        _require(len(content) == spec["file_bytes"], "D-121 protected input bytes differ")
        _require(
            sha256_bytes(content) == spec["file_sha256"],
            "D-121 protected input SHA differs",
        )
        rows.append(dict(spec))
    return {"files": rows, "fingerprint": sha256_bytes(_canonical_bytes(rows))}


def _implementation_state(repository: Path) -> dict[str, Any]:
    rows = []
    for relative in IMPLEMENTATION_PATHS:
        path = _safe_path(repository, relative, must_exist=True, label="implementation")
        content = _read_stable(path, label="implementation")
        rows.append(_binding(relative, content))
    return {"files": rows, "fingerprint": sha256_bytes(_canonical_bytes(rows))}


def _validate_d120_authority(repository: Path) -> dict[str, Any]:
    candidate_path = _safe_path(
        repository, D120_CANDIDATE_SPEC["path"], must_exist=True, label="D-120 candidate"
    )
    candidate_content = _read_stable(candidate_path, label="D-120 candidate")
    candidate = _parse_json(candidate_content, label="D-120 candidate")
    for key in ("file_bytes", "file_sha256"):
        observed = (
            len(candidate_content) if key == "file_bytes" else sha256_bytes(candidate_content)
        )
        _require(observed == D120_CANDIDATE_SPEC[key], f"D-120 candidate {key} differs")
    _require(
        candidate.get("candidate_id") == D120_CANDIDATE_SPEC["identifier"],
        "D-120 candidate ID differs",
    )
    _require(
        candidate.get("semantic_body_hash") == D120_CANDIDATE_SPEC["semantic_body_hash"],
        "D-120 candidate body SHA differs",
    )
    body = candidate.get("semantic_body")
    _require(isinstance(body, dict), "D-120 candidate body missing")
    _require(body.get("proposed_action_hash") == D120_ACTION_HASH, "D-120 action hash differs")
    action = body.get("proposed_action")
    _require(isinstance(action, dict), "D-120 proposed action missing")
    _require(
        sha256_bytes(_canonical_bytes(action)) == D120_ACTION_HASH,
        "D-120 proposed action payload differs",
    )
    _require(
        action.get("action") == "implement-test-and-prepare-d121-execution-authorization-candidate",
        "D-120 action name differs",
    )
    _require(
        action.get("new_paths")
        == [
            *(value.as_posix() for value in IMPLEMENTATION_PATHS),
            *(value.as_posix() for value in PREPARATION_OUTPUT_PATHS.values()),
        ],
        "D-120 D-121 preparation path scope differs",
    )
    _require(
        action.get("prospective_run_output_paths_not_authorized")
        == [value.as_posix() for value in EXECUTION_OUTPUT_PATHS.values()],
        "D-120 future run output boundary differs",
    )
    gate_path = _safe_path(repository, D120_GATE_SPEC["path"], must_exist=True, label="D-120 gate")
    gate_content = _read_stable(gate_path, label="D-120 gate")
    gate = _parse_json(gate_content, label="D-120 gate")
    _require(len(gate_content) == D120_GATE_SPEC["file_bytes"], "D-120 gate bytes differ")
    _require(sha256_bytes(gate_content) == D120_GATE_SPEC["file_sha256"], "D-120 gate SHA differs")
    _require(gate.get("gate_id") == D120_GATE_SPEC["identifier"], "D-120 gate ID differs")
    _require(
        gate.get("semantic_body_hash") == D120_GATE_SPEC["semantic_body_hash"],
        "D-120 gate body SHA differs",
    )
    return {
        "candidate": _binding(
            D120_CANDIDATE_SPEC["path"],
            candidate_content,
            candidate_id=candidate["candidate_id"],
            semantic_body_hash=candidate["semantic_body_hash"],
        ),
        "source_gate": _binding(
            D120_GATE_SPEC["path"],
            gate_content,
            gate_id=gate["gate_id"],
            semantic_body_hash=gate["semantic_body_hash"],
        ),
        "action": action,
        "action_hash": D120_ACTION_HASH,
    }


def _declared_path_contract(repository: Path) -> dict[str, Any]:
    groups = {
        "protected": [Path(spec["path"]) for spec in PROTECTED_FILE_SPECS],
        "d119_absent": [Path(value) for value in D119_ABSENT_OUTPUTS],
        "d121_implementation": list(IMPLEMENTATION_PATHS),
        "d121_preparation_outputs": list(PREPARATION_OUTPUT_PATHS.values()),
        "d121_future_execution_outputs": list(EXECUTION_OUTPUT_PATHS.values()),
    }
    normalized: dict[str, tuple[str, str]] = {}
    inode_owner: dict[tuple[int, int], tuple[str, str]] = {}
    rendered: dict[str, list[str]] = {}
    for group, relatives in groups.items():
        rendered[group] = []
        for relative in relatives:
            logical = relative.as_posix()
            folded = unicodedata.normalize("NFKC", logical).casefold()
            _require(folded not in normalized, f"D-121 path alias: {normalized.get(folded)}")
            normalized[folded] = (group, logical)
            selected = repository / relative
            if group == "d119_absent":
                path = _safe_path(
                    repository,
                    relative,
                    must_exist=False,
                    label="D-119 historically absent output",
                )
                _require(
                    not path.exists() and not _is_linklike(path),
                    "D-119 historically absent output appeared",
                )
                rendered[group].append(logical)
                continue
            resolved = _safe_path(
                repository,
                relative,
                must_exist=selected.exists(),
                label=f"{group} path",
            )
            if selected.exists():
                _require(resolved.is_file(), f"D-121 {group} path is not a file")
                info = resolved.stat()
                identity = (info.st_dev, info.st_ino)
                _require(identity not in inode_owner, "D-121 path inode alias")
                inode_owner[identity] = (group, logical)
            rendered[group].append(logical)
    return {
        "normalization": "unicode-nfkc-casefold-posix",
        "sets_pairwise_disjoint": True,
        "alternate_data_streams_forbidden": True,
        "symlink_junction_reparse_traversal_forbidden": True,
        "existing_inode_aliases_absent": True,
        "d119_historical_completion_outputs_absent": True,
        "path_sets": rendered,
    }


def _require_d119_outputs_absent(repository: Path) -> None:
    for relative in D119_ABSENT_OUTPUTS:
        path = _safe_path(
            repository,
            relative,
            must_exist=False,
            label="D-119 historically absent output",
        )
        _require(
            not path.exists() and not _is_linklike(path),
            "D-119 historically absent output appeared",
        )


def _assert_preparation_start_state(repository: Path) -> str:
    present = [
        key
        for key, relative in PREPARATION_OUTPUT_PATHS.items()
        if (repository / relative).exists() or _is_linklike(repository / relative)
    ]
    if not present:
        return "empty"
    if len(present) == len(PREPARATION_OUTPUT_PATHS):
        return "complete"
    if present == ["approval_receipt"]:
        return "claimed-partial-consumed"
    return "ambiguous-partial"


def _require_future_outputs_absent(repository: Path) -> None:
    for relative in EXECUTION_OUTPUT_PATHS.values():
        path = _safe_path(repository, relative, must_exist=False, label="future output")
        _require(
            not path.exists() and not _is_linklike(path),
            "D-121 future execution output already exists",
        )


def _write_new(repository: Path, relative: Path, payload: Mapping[str, Any]) -> bytes:
    path = _safe_path(repository, relative, must_exist=False, label="preparation output")
    _require(not path.exists() and not _is_linklike(path), "D-121 output collision")
    content = _pretty_bytes(payload)
    parent_before = path.parent.stat()
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        opened = os.fstat(handle.fileno())
    parent_after = path.parent.stat()
    _require(
        (parent_before.st_dev, parent_before.st_ino) == (parent_after.st_dev, parent_after.st_ino),
        "D-121 output parent changed",
    )
    _require(
        (opened.st_dev, opened.st_ino) == (path.stat().st_dev, path.stat().st_ino),
        "D-121 output identity changed",
    )
    _require(_read_stable(path, label="preparation output") == content, "output reread differs")
    return content


def _external_file_binding(path: Path, *, label: str) -> dict[str, Any]:
    _require(not _is_linklike(path), f"D-121 {label} must not be link-like")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise D121PreparationError(f"D-121 {label} cannot be resolved") from exc
    content = _read_stable(resolved, label=label)
    return {
        "file_name": resolved.name,
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
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


def _verified_docker_path(selected: str | Path) -> tuple[str, dict[str, Any]]:
    path = Path(selected)
    binding = _external_file_binding(path, label="Docker CLI")
    _require(binding["file_name"].casefold() == "docker.exe", "Docker CLI name differs")
    _require(binding["file_bytes"] == DOCKER_CLI_BYTES, "Docker CLI bytes differ")
    _require(binding["file_sha256"] == DOCKER_CLI_SHA256, "Docker CLI SHA differs")
    return str(path.resolve(strict=True)), {
        **binding,
        "runner_kind": "subprocess-exact-argv-no-shell-forced-local-docker-host",
    }


def _docker_environment_contract() -> dict[str, Any]:
    values = {key: None for key in ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CONFIG")}
    return {
        "parent_checked_variables": values,
        "parent_all_unset_or_empty": True,
        "child_environment_policy": {
            "remove_all_inherited_docker_prefixed_variables": True,
            "force_docker_host": _LOCAL_DOCKER_ENDPOINT,
            "docker_context_inherited": False,
            "docker_config_inherited": False,
        },
        "every_subprocess_runner_command_forced_to_local_named_pipe": True,
        "socket_level_instrumentation_verified": False,
    }


def _docker_environment_boundary() -> dict[str, Any]:
    values = {
        key: os.environ.get(key) or None
        for key in ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CONFIG")
    }
    _require(
        all(value in {None, ""} for value in values.values()),
        "Docker routing environment is not default-local",
    )
    return _docker_environment_contract()


def _image_id_command(docker: str) -> list[str]:
    return [docker, "image", "inspect", "--format", _IMAGE_ID_FORMAT, IMAGE_TAG]


def _inspect_projection_command(docker: str, target: str) -> list[str]:
    return [docker, "inspect", "--format", _INSPECT_PROJECTION_FORMAT, target]


def _bounded_summary(
    role: str,
    command_contract: Sequence[str],
    result: subprocess.CompletedProcess[bytes],
    *,
    enforce_bounds: bool = True,
) -> dict[str, Any]:
    stdout_within_bound = len(result.stdout) <= _MAX_COMMAND_OUTPUT
    stderr_within_bound = len(result.stderr) <= _MAX_COMMAND_OUTPUT
    if enforce_bounds:
        _require(stdout_within_bound, f"D-121 {role} stdout too large")
        _require(stderr_within_bound, f"D-121 {role} stderr too large")
    return {
        "role": role,
        "argv_contract": list(command_contract),
        "return_code": result.returncode,
        "stdout_bytes": len(result.stdout),
        "stdout_sha256": sha256_bytes(result.stdout),
        "stderr_bytes": len(result.stderr),
        "stderr_sha256": sha256_bytes(result.stderr),
        "stdout_within_bound": stdout_within_bound,
        "stderr_within_bound": stderr_within_bound,
    }


def _invoke(
    runner: CommandRunner,
    command: Sequence[str],
    *,
    timeout_seconds: int,
    allowed_create_host_path: str | None = None,
    allowed_readiness_name: str | None = None,
    allowed_container_id: str | None = None,
) -> subprocess.CompletedProcess[bytes]:
    _validate_no_start_argv(
        command,
        allowed_create_host_path=allowed_create_host_path,
        allowed_readiness_name=allowed_readiness_name,
        allowed_container_id=allowed_container_id,
    )
    return runner.run(command, input_bytes=None, timeout_seconds=timeout_seconds)


def _validate_no_start_argv(
    command: Sequence[str],
    *,
    allowed_create_host_path: str | None = None,
    allowed_readiness_name: str | None = None,
    allowed_container_id: str | None = None,
) -> None:
    _require(len(command) >= 2, "D-121 Docker command missing")
    verb = command[1]
    if verb == "image":
        _require(
            list(command) == _image_id_command(command[0]),
            "D-121 image command differs",
        )
        return
    if verb == "ps":
        _require(
            len(command) == 7
            and list(command[1:6]) == ["ps", "--all", "--quiet", "--no-trunc", "--filter"],
            "D-121 inventory command differs",
        )
        filter_value = command[6]
        id_filter = filter_value.removeprefix("id=") if filter_value.startswith("id=") else None
        _require(
            filter_value == f"label={MANAGED_LABEL}"
            or id_filter is not None
            and _CONTAINER_ID.fullmatch(id_filter) is not None
            and allowed_container_id is not None
            and id_filter == allowed_container_id,
            "D-121 inventory filter differs",
        )
        return
    if verb == "create":
        _require(
            len(command) > 10 and list(command[1:3]) == ["create", "--name"],
            "D-121 create command prefix differs",
        )
        name = command[3]
        _require(
            re.fullmatch(r"patchloop-d121-readiness-[0-9a-f]{12}", name) is not None
            and allowed_readiness_name is not None
            and name == allowed_readiness_name,
            "D-121 container name differs",
        )
        try:
            mount_index = command.index("--mount")
        except ValueError as exc:
            raise D121PreparationError("D-121 create mount missing") from exc
        mount_value = command[mount_index + 1]
        prefix = "type=bind,source="
        suffix = ",target=/input/source.parquet,readonly"
        _require(
            mount_value.startswith(prefix) and mount_value.endswith(suffix),
            "D-121 create mount differs",
        )
        host_path = mount_value[len(prefix) : -len(suffix)]
        _require(
            allowed_create_host_path is not None
            and str(Path(host_path).resolve(strict=True)).casefold()
            == str(Path(allowed_create_host_path).resolve(strict=True)).casefold(),
            "D-121 readiness mount is not the exact sentinel",
        )
        _require(
            list(command) == _create_command(docker=command[0], name=name, host_path=host_path),
            "D-121 create argv differs",
        )
        return
    if verb in {"inspect", "rm"}:
        if verb == "inspect" and "--format" in command:
            _require(len(command) == 5, "D-121 projection inspect length differs")
            _require(
                command[2:4] == ["--format", _INSPECT_PROJECTION_FORMAT],
                "D-121 projection inspect differs",
            )
            target = command[4]
            _require(
                _CONTAINER_ID.fullmatch(target) is not None
                and allowed_container_id is not None
                and target == allowed_container_id
                or allowed_readiness_name is not None
                and target == allowed_readiness_name,
                "D-121 projection inspect target differs",
            )
            return
        expected_length = 3 if verb == "inspect" else 4
        _require(len(command) == expected_length, "D-121 cleanup command length differs")
        if verb == "rm":
            _require(command[2] == "--force", "D-121 remove flags differ")
            target = command[3]
            _require(
                _CONTAINER_ID.fullmatch(target) is not None,
                "D-121 remove target is not an exact container ID",
            )
            _require(target == allowed_container_id, "D-121 remove target binding differs")
        else:
            target = command[2]
            _require(
                _CONTAINER_ID.fullmatch(target) is not None and target == allowed_container_id,
                "D-121 inspect target differs",
            )
        return
    raise D121PreparationError("D-121 Docker verb is not in the no-start allowlist")


def _inventory_command(docker: str, filter_value: str) -> list[str]:
    return [
        docker,
        "ps",
        "--all",
        "--quiet",
        "--no-trunc",
        "--filter",
        filter_value,
    ]


def _parse_inventory(result: subprocess.CompletedProcess[bytes], *, label: str) -> list[str]:
    _require(result.returncode == 0, f"D-121 {label} inventory failed")
    _require(result.stderr == b"", f"D-121 {label} inventory stderr differs")
    try:
        lines = result.stdout.decode("ascii", errors="strict").splitlines()
    except UnicodeDecodeError as exc:
        raise D121PreparationError(f"D-121 {label} inventory is not ASCII") from exc
    rows = [line for line in lines if line]
    _require(all(_CONTAINER_ID.fullmatch(value) for value in rows), "inventory ID invalid")
    return rows


def _create_command(
    *, docker: str, name: str, host_path: str, role_label: str = ROLE_LABEL
) -> list[str]:
    return [
        docker,
        "create",
        "--name",
        name,
        "--label",
        MANAGED_LABEL,
        "--label",
        role_label,
        "--pull=never",
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


def _portable_create_manifest(*, name_kind: str, source_kind: str) -> dict[str, Any]:
    return {
        "contract_version": "d121-docker-create-v1",
        "docker_executable": "<exact-pinned-docker-cli>",
        "container_name": name_kind,
        "labels": [MANAGED_LABEL, ROLE_LABEL],
        "source": source_kind,
        "target": "/input/source.parquet",
        "image_id": IMAGE_ID,
        "profile_hash": PROFILE_HASH,
        "image_pull_policy": "never",
        "container_start_forbidden": True,
    }


def _expected_config_checks() -> dict[str, bool | int]:
    return {
        "image_exact": True,
        "lifecycle_never_started": True,
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
        "restart_policy_none": True,
        "one_read_only_input_mount": True,
        "one_bounded_tmpfs_output": True,
        "read_only_dev_shm": True,
        "repository_directory_tree_mount_count": 0,
        "exact_nonopaque_file_bind_mount_count": 1,
    }


def _validate_created_container(
    inspect_value: Mapping[str, Any],
    *,
    expected_host_path: str,
    expected_name: str,
) -> dict[str, bool | int]:
    _require(inspect_value.get("Image") == IMAGE_ID, "D-121 container image differs")
    _require(
        inspect_value.get("Name") in {expected_name, "/" + expected_name},
        "container name differs",
    )
    config = inspect_value.get("Config")
    host = inspect_value.get("HostConfig")
    mounts = inspect_value.get("Mounts")
    state = inspect_value.get("State")
    _require(isinstance(config, dict), "D-121 container config missing")
    _require(isinstance(host, dict), "D-121 host config missing")
    _require(isinstance(mounts, list), "D-121 mounts missing")
    _require(isinstance(state, dict), "D-121 state missing")
    _require(inspect_value.get("MountCount") == 1, "D-121 mount count differs")
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
    _require(config.get("Tty") is False, "container TTY differs")
    _require(config.get("OpenStdin") is True, "container stdin differs")
    _require(
        config.get("Labels")
        == {
            "io.patchloop.managed": "d121-isolation-successor",
            "io.patchloop.role": "external-source-hash-only",
            "io.patchloop.probe-image": "v2",
        },
        "container labels differ",
    )
    _require(state.get("Status") == "created", "container was not left in created state")
    _require(state.get("Running") is False, "container is running")
    _require(state.get("Paused") is False, "container is paused")
    _require(state.get("Restarting") is False, "container is restarting")
    _require(state.get("Dead") is False, "container is dead")
    _require(type(state.get("Pid")) is int and state.get("Pid") == 0, "container PID differs")
    started_at = state.get("StartedAt")
    _require(started_at == "0001-01-01T00:00:00Z", "container has a start timestamp")
    _require(host.get("NetworkMode") == "none", "container network differs")
    _require(host.get("ReadonlyRootfs") is True, "container root differs")
    _require(host.get("Privileged") is False, "container privilege differs")
    _require(host.get("PidsLimit") == 2, "container PID limit differs")
    _require(host.get("CapDrop") == ["ALL"], "container capabilities differ")
    _require(host.get("CapAdd") is None, "container capability add differs")
    _require(host.get("SecurityOpt") == ["no-new-privileges"], "security option differs")
    _require(host.get("PidMode") == "", "host PID namespace requested")
    _require(host.get("IpcMode") == "private", "host IPC namespace requested")
    _require(host.get("Devices") == [], "container devices differ")
    _require(host.get("DeviceRequests") is None, "device requests differ")
    _require(host.get("Binds") is None, "legacy binds are forbidden")
    _require(host.get("Memory") == 268_435_456, "container memory differs")
    _require(host.get("NanoCpus") == 1_000_000_000, "container CPU differs")
    _require(
        host.get("RestartPolicy") == {"Name": "no", "MaximumRetryCount": 0},
        "restart policy differs",
    )
    _require(
        host.get("Tmpfs")
        == {
            "/output": "rw,noexec,nosuid,nodev,size=64k,uid=10001,gid=10001,mode=0700",
            "/dev/shm": "ro,noexec,nosuid,nodev,size=64k,mode=0555",
        },
        "tmpfs policy differs",
    )
    _require(len(mounts) == 1, "container bind mount count differs")
    mount = mounts[0]
    _require(mount.get("Type") == "bind", "input mount type differs")
    _require(mount.get("Destination") == "/input/source.parquet", "input target differs")
    _require(mount.get("RW") is False, "input mount is writable")
    _require(
        str(Path(str(mount.get("Source"))).resolve()).casefold()
        == str(Path(expected_host_path).resolve()).casefold(),
        "input source path differs",
    )
    return _expected_config_checks()


def _created_container_projection(
    inspect_value: Mapping[str, Any], *, source_token: str = "<exact-nonopaque-sentinel>"
) -> dict[str, Any]:
    config = inspect_value["Config"]
    host = inspect_value["HostConfig"]
    state = inspect_value["State"]
    return {
        "Id": inspect_value.get("Id"),
        "Name": inspect_value.get("Name"),
        "Path": inspect_value.get("Path"),
        "Args": inspect_value.get("Args"),
        "Image": inspect_value.get("Image"),
        "Config": {
            key: config.get(key)
            for key in ("Cmd", "WorkingDir", "User", "Tty", "OpenStdin", "Labels")
        },
        "HostConfig": {
            key: host.get(key)
            for key in (
                "NetworkMode",
                "ReadonlyRootfs",
                "Privileged",
                "PidsLimit",
                "CapDrop",
                "CapAdd",
                "SecurityOpt",
                "PidMode",
                "IpcMode",
                "Devices",
                "DeviceRequests",
                "Binds",
                "Memory",
                "NanoCpus",
                "RestartPolicy",
                "Tmpfs",
            )
        },
        "MountCount": inspect_value.get("MountCount"),
        "Mounts": [
            {
                "Type": row.get("Type"),
                "Source": source_token,
                "Destination": row.get("Destination"),
                "RW": row.get("RW"),
            }
            for row in inspect_value["Mounts"]
        ],
        "State": {
            key: state.get(key)
            for key in (
                "Status",
                "Running",
                "Paused",
                "Restarting",
                "Dead",
                "Pid",
                "StartedAt",
            )
        },
    }


def _inspect_projection_stdout(
    portable_projection: Mapping[str, Any], *, exact_host_path: str
) -> bytes:
    hydrated = {
        **portable_projection,
        "Mounts": [{**row, "Source": exact_host_path} for row in portable_projection["Mounts"]],
    }
    return (
        json.dumps(hydrated, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode(
            "utf-8"
        )
        + b"\n"
    )


def _readiness_argv_contracts() -> list[list[str]]:
    return [
        _image_id_command("<exact-pinned-docker-cli>"),
        _inventory_command("<exact-pinned-docker-cli>", f"label={MANAGED_LABEL}"),
        [
            "<exact-pinned-docker-cli>",
            *_create_command(
                docker="<exact-pinned-docker-cli>",
                name="<runtime-readiness-name>",
                host_path="<exact-nonopaque-sentinel>",
            )[1:],
        ],
        _inspect_projection_command("<exact-pinned-docker-cli>", "<exact-container-id>"),
        ["<exact-pinned-docker-cli>", "rm", "--force", "<exact-container-id>"],
        ["<exact-pinned-docker-cli>", "inspect", "<exact-container-id>"],
        _inventory_command("<exact-pinned-docker-cli>", "id=<exact-container-id>"),
        _inventory_command("<exact-pinned-docker-cli>", f"label={MANAGED_LABEL}"),
    ]


def _cleanup_observations(
    *,
    runner: CommandRunner,
    docker: str,
    container_id: str,
) -> tuple[dict[str, subprocess.CompletedProcess[bytes]], list[dict[str, Any]]]:
    commands = [
        (
            "remove-by-exact-id",
            [docker, "rm", "--force", container_id],
            ["<exact-pinned-docker-cli>", "rm", "--force", "<exact-container-id>"],
        ),
        (
            "inspect-by-exact-id",
            [docker, "inspect", container_id],
            ["<exact-pinned-docker-cli>", "inspect", "<exact-container-id>"],
        ),
        (
            "exact-id-inventory",
            _inventory_command(docker, f"id={container_id}"),
            _inventory_command("<exact-pinned-docker-cli>", "id=<exact-container-id>"),
        ),
        (
            "successor-label-inventory",
            _inventory_command(docker, f"label={MANAGED_LABEL}"),
            _inventory_command("<exact-pinned-docker-cli>", f"label={MANAGED_LABEL}"),
        ),
    ]
    results: dict[str, subprocess.CompletedProcess[bytes]] = {}
    summaries = []
    for role, command, contract in commands:
        try:
            result = _invoke(
                runner,
                command,
                timeout_seconds=20,
                allowed_container_id=container_id,
            )
        except Exception as exc:  # noqa: BLE001 - preserve later cleanup observations
            result = subprocess.CompletedProcess(
                list(command),
                returncode=-1,
                stdout=b"",
                stderr=f"runner-exception:{type(exc).__name__}".encode("ascii"),
            )
        results[role] = result
        summaries.append(_bounded_summary(role, contract, result, enforce_bounds=False))
    return results, summaries


def _validate_cleanup_results(
    results: Mapping[str, subprocess.CompletedProcess[bytes]],
    summaries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    removed = results["remove-by-exact-id"]
    inspected = results["inspect-by-exact-id"]
    exact_inventory = results["exact-id-inventory"]
    label_inventory = results["successor-label-inventory"]
    errors = []
    if any(not row["stdout_within_bound"] or not row["stderr_within_bound"] for row in summaries):
        errors.append("CLEANUP_OUTPUT_OVERSIZE")
    if removed.returncode != 0:
        errors.append("REMOVE_FAILED")
    if inspected.returncode == 0:
        errors.append("REMOVED_CONTAINER_STILL_INSPECTABLE")
    presentation = ALLOWED_MISSING_INSPECT_STDOUT.get(inspected.stdout)
    if presentation is None:
        errors.append("REMOVED_INSPECT_PRESENTATION_INVALID")
    try:
        exact_ids = _parse_inventory(exact_inventory, label="exact-ID")
    except D121PreparationError:
        exact_ids = ["<invalid>"]
        errors.append("EXACT_ID_INVENTORY_INVALID")
    try:
        label_ids = _parse_inventory(label_inventory, label="label")
    except D121PreparationError:
        label_ids = ["<invalid>"]
        errors.append("LABEL_INVENTORY_INVALID")
    if exact_ids:
        errors.append("EXACT_ID_RESIDUAL_PRESENT")
    if label_ids:
        errors.append("LABEL_RESIDUAL_PRESENT")
    _require(not errors, "D-121 cleanup verification failed: " + ",".join(errors))
    return {
        "observation_order": [row["role"] for row in summaries],
        "all_observations_collected_before_validation": True,
        "remove_return_code": removed.returncode,
        "missing_inspect_return_code_nonzero": True,
        "missing_inspect_stdout_presentation": presentation,
        "missing_inspect_stdout_bytes": len(inspected.stdout),
        "missing_inspect_stdout_sha256": sha256_bytes(inspected.stdout),
        "missing_inspect_stderr_bytes": len(inspected.stderr),
        "missing_inspect_stderr_sha256": sha256_bytes(inspected.stderr),
        "exact_id_residual_count": 0,
        "successor_label_residual_count": 0,
        "raw_stderr_persisted": False,
        "command_summaries": [dict(row) for row in summaries],
    }


def _emergency_cleanup_by_name(
    *,
    runner: CommandRunner,
    docker: str,
    container_name: str,
    expected_host_path: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Best-effort cleanup when Docker did not return a trustworthy exact ID.

    This path can never qualify readiness or execution. It exists only to avoid
    abandoning a container after a successful create with malformed stdout.
    Every observation is attempted before returning.
    """

    summaries: list[dict[str, Any]] = []

    def observe(
        role: str,
        command: list[str],
        contract: list[str],
        *,
        allowed_name: str | None = None,
        allowed_id: str | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        try:
            result = _invoke(
                runner,
                command,
                timeout_seconds=20,
                allowed_readiness_name=allowed_name,
                allowed_container_id=allowed_id,
            )
        except Exception as exc:  # noqa: BLE001 - continue to the label inventory
            result = subprocess.CompletedProcess(
                list(command),
                returncode=-1,
                stdout=b"",
                stderr=f"runner-exception:{type(exc).__name__}".encode("ascii"),
            )
        summaries.append(_bounded_summary(role, contract, result, enforce_bounds=False))
        return result

    errors: list[str] = []
    inspected = observe(
        "emergency-inspect-by-known-name",
        _inspect_projection_command(docker, container_name),
        _inspect_projection_command("<exact-pinned-docker-cli>", "<known-created-name>"),
        allowed_name=container_name,
    )
    trusted_id: str | None = None
    if inspected.returncode == 0 and len(inspected.stdout) <= _MAX_COMMAND_OUTPUT:
        try:
            row = json.loads(inspected.stdout)
            _require(
                isinstance(row, dict),
                "emergency inspect projection differs",
            )
            candidate_id = row.get("Id")
            _require(
                isinstance(candidate_id, str) and _CONTAINER_ID.fullmatch(candidate_id) is not None,
                "emergency exact ID differs",
            )
            _require(
                row.get("Name") in {container_name, "/" + container_name},
                "emergency container name differs",
            )
            _validate_created_container(
                row,
                expected_host_path=expected_host_path,
                expected_name=container_name,
            )
            _require(
                inspected.stdout
                == _inspect_projection_stdout(
                    _created_container_projection(row), exact_host_path=expected_host_path
                ),
                "emergency inspect projection bytes differ",
            )
            trusted_id = candidate_id
        except (D121PreparationError, TypeError, ValueError, json.JSONDecodeError):
            errors.append("EMERGENCY_OWNERSHIP_UNPROVED")
    elif inspected.returncode == 0:
        errors.append("EMERGENCY_INSPECT_OUTPUT_OVERSIZE")

    if trusted_id is not None:
        removed = observe(
            "emergency-remove-by-exact-id",
            [docker, "rm", "--force", trusted_id],
            ["<exact-pinned-docker-cli>", "rm", "--force", "<exact-container-id>"],
            allowed_id=trusted_id,
        )
        post_inspect = observe(
            "emergency-inspect-by-exact-id",
            [docker, "inspect", trusted_id],
            ["<exact-pinned-docker-cli>", "inspect", "<exact-container-id>"],
            allowed_id=trusted_id,
        )
        exact_inventory = observe(
            "emergency-exact-id-inventory",
            _inventory_command(docker, f"id={trusted_id}"),
            _inventory_command("<exact-pinned-docker-cli>", "id=<exact-container-id>"),
            allowed_id=trusted_id,
        )
        if removed.returncode != 0:
            errors.append("EMERGENCY_REMOVE_FAILED")
        if post_inspect.returncode == 0:
            errors.append("EMERGENCY_TARGET_STILL_INSPECTABLE")
        try:
            if _parse_inventory(exact_inventory, label="emergency exact ID"):
                errors.append("EMERGENCY_EXACT_ID_RESIDUAL_PRESENT")
        except D121PreparationError:
            errors.append("EMERGENCY_EXACT_ID_INVENTORY_INVALID")

    label_inventory = observe(
        "emergency-successor-label-inventory",
        _inventory_command(docker, f"label={MANAGED_LABEL}"),
        _inventory_command("<exact-pinned-docker-cli>", f"label={MANAGED_LABEL}"),
    )
    if any(not row["stdout_within_bound"] or not row["stderr_within_bound"] for row in summaries):
        errors.append("EMERGENCY_OUTPUT_OVERSIZE")
    try:
        residual = _parse_inventory(
            label_inventory,
            label="emergency successor label",
        )
    except D121PreparationError:
        residual = ["<invalid>"]
        errors.append("EMERGENCY_LABEL_INVENTORY_INVALID")
    if residual:
        errors.append("EMERGENCY_LABEL_RESIDUAL_PRESENT")
    return summaries, errors


def _run_no_start_readiness(
    *,
    repository: Path,
    docker_path: str,
    runner: CommandRunner,
) -> dict[str, Any]:
    docker, docker_pre = _verified_docker_path(docker_path)
    docker_environment_pre = _docker_environment_boundary()
    sentinel = _safe_path(repository, SENTINEL_PATH, must_exist=True, label="readiness sentinel")
    sentinel_content = _read_stable(sentinel, label="readiness sentinel")
    _require(len(sentinel_content) == 386, "D-121 sentinel bytes differ")
    _require(
        sha256_bytes(sentinel_content) == d119.DOCKERFILE_SHA256,
        "D-121 sentinel SHA differs",
    )
    transcript: list[dict[str, Any]] = []
    image_command = _image_id_command(docker)
    image_result = _invoke(runner, image_command, timeout_seconds=30)
    transcript.append(
        _bounded_summary(
            "image-inspect",
            _image_id_command("<exact-pinned-docker-cli>"),
            image_result,
        )
    )
    _require(image_result.returncode == 0, "D-121 image inspect failed")
    _require(image_result.stderr == b"", "D-121 image inspect stderr differs")
    _require(
        image_result.stdout == (IMAGE_ID + "\n").encode("ascii"),
        "D-121 image identity differs",
    )

    pre_command = _inventory_command(docker, f"label={MANAGED_LABEL}")
    pre_result = _invoke(runner, pre_command, timeout_seconds=20)
    transcript.append(
        _bounded_summary(
            "preexisting-label-inventory",
            _inventory_command("<exact-pinned-docker-cli>", f"label={MANAGED_LABEL}"),
            pre_result,
        )
    )
    _require(
        _parse_inventory(pre_result, label="preexisting label") == [],
        "preexisting D-121 container found",
    )

    name = f"patchloop-d121-readiness-{uuid.uuid4().hex[:12]}"
    create_command = _create_command(docker=docker, name=name, host_path=str(sentinel))
    created = False
    container_id: str | None = None
    primary_error: BaseException | None = None
    config_checks: dict[str, bool | int] | None = None
    created_projection: dict[str, Any] | None = None
    cleanup: dict[str, Any] | None = None
    try:
        created = True  # The create attempt may mutate before returning or timing out.
        create_result = _invoke(
            runner,
            create_command,
            timeout_seconds=30,
            allowed_create_host_path=str(sentinel),
            allowed_readiness_name=name,
        )
        transcript.append(
            _bounded_summary(
                "container-create",
                [
                    "<exact-pinned-docker-cli>",
                    *_create_command(
                        docker="<exact-pinned-docker-cli>",
                        name="<runtime-readiness-name>",
                        host_path="<exact-nonopaque-sentinel>",
                    )[1:],
                ],
                create_result,
            )
        )
        _require(create_result.returncode == 0, "D-121 container create failed")
        _require(create_result.stderr == b"", "D-121 container create stderr differs")
        _require(
            len(create_result.stdout) == 65 and create_result.stdout.endswith(b"\n"),
            "D-121 container ID output bytes differ",
        )
        try:
            candidate_id = create_result.stdout[:-1].decode("ascii", errors="strict")
        except UnicodeDecodeError as exc:
            raise D121PreparationError("D-121 container ID output invalid") from exc
        _require(_CONTAINER_ID.fullmatch(candidate_id) is not None, "container ID invalid")
        container_id = candidate_id
        inspect_command = _inspect_projection_command(docker, container_id)
        inspect_result = _invoke(
            runner,
            inspect_command,
            timeout_seconds=20,
            allowed_container_id=container_id,
        )
        transcript.append(
            _bounded_summary(
                "container-inspect-before-start",
                _inspect_projection_command("<exact-pinned-docker-cli>", "<exact-container-id>"),
                inspect_result,
            )
        )
        _require(inspect_result.returncode == 0, "D-121 created-container inspect failed")
        _require(inspect_result.stderr == b"", "created-container inspect stderr differs")
        try:
            inspect_value = json.loads(inspect_result.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise D121PreparationError("created-container inspect output invalid") from exc
        _require(
            isinstance(inspect_value, dict),
            "created-container inspect projection differs",
        )
        _require(inspect_value.get("Id") == container_id, "inspected container ID differs")
        config_checks = _validate_created_container(
            inspect_value,
            expected_host_path=str(sentinel),
            expected_name=name,
        )
        created_projection = _created_container_projection(inspect_value)
        _require(
            inspect_result.stdout
            == _inspect_projection_stdout(created_projection, exact_host_path=str(sentinel)),
            "created-container inspect projection bytes differ",
        )
    except BaseException as exc:  # noqa: BLE001 - cleanup must not mask the primary result
        primary_error = exc
    finally:
        if created:
            if container_id is not None:
                cleanup_results, cleanup_summaries = _cleanup_observations(
                    runner=runner,
                    docker=docker,
                    container_id=container_id,
                )
                transcript.extend(cleanup_summaries)
                try:
                    cleanup = _validate_cleanup_results(cleanup_results, cleanup_summaries)
                except BaseException as exc:  # noqa: BLE001
                    if primary_error is None:
                        primary_error = exc
                    else:
                        primary_error.add_note(f"cleanup_error={type(exc).__name__}:{exc}")
            else:
                emergency_summaries, emergency_errors = _emergency_cleanup_by_name(
                    runner=runner,
                    docker=docker,
                    container_name=name,
                    expected_host_path=str(sentinel),
                )
                transcript.extend(emergency_summaries)
                emergency = D121PreparationError(
                    "D-121 created container ID was untrusted; emergency cleanup used"
                    + (":" + ",".join(emergency_errors) if emergency_errors else "")
                )
                if primary_error is None:
                    primary_error = emergency
                else:
                    primary_error.add_note(str(emergency))
    if primary_error is not None:
        raise primary_error
    _require(container_id is not None, "D-121 readiness container ID missing")
    _require(config_checks is not None, "D-121 readiness config evidence missing")
    _require(created_projection is not None, "D-121 readiness inspect projection missing")
    _require(cleanup is not None, "D-121 readiness cleanup evidence missing")
    docker_environment_post = _docker_environment_boundary()
    _require(
        docker_environment_post == docker_environment_pre,
        "Docker routing environment changed during readiness",
    )
    _, docker_post = _verified_docker_path(docker)
    _require(docker_post == docker_pre, "Docker CLI changed during readiness")
    return {
        "evidence_kind": "live-no-start-docker-configuration-realization",
        "recorded_at": _now(),
        "docker_cli_pre": docker_pre,
        "docker_cli_post": docker_post,
        "docker_environment_pre": docker_environment_pre,
        "docker_environment_post": docker_environment_post,
        "image_tag": IMAGE_TAG,
        "immutable_image_id": IMAGE_ID,
        "profile_hash": PROFILE_HASH,
        "sentinel": {
            "path": SENTINEL_PATH.as_posix(),
            "file_bytes": len(sentinel_content),
            "file_sha256": sha256_bytes(sentinel_content),
            "opaque_source": False,
        },
        "portable_create_manifest": _portable_create_manifest(
            name_kind="<runtime-readiness-name>",
            source_kind="<exact-nonopaque-sentinel>",
        ),
        "container_name_prefix": "patchloop-d121-readiness-",
        "container_id": container_id,
        "created_container_projection": created_projection,
        "config_checks": config_checks,
        "cleanup": cleanup,
        "command_transcript": transcript,
        "counters": {
            "docker_command_count": len(transcript),
            "docker_create_count": 1,
            "docker_start_count": 0,
            "docker_run_count": 0,
            "docker_exec_count": 0,
            "probe_execution_count": 0,
            "probe_stdin_bytes": 0,
            "readiness_docker_opaque_path_reference_count": 0,
            "opaque_source_mount_count": 0,
            "opaque_source_filesystem_access_count": 0,
            "opaque_source_filesystem_byte_read_count": 0,
            "sealed_source_identifier_reuse_count": 2,
            "record_parse_count": 0,
            "residual_container_count": 0,
        },
        "qualification": {
            "no_start_readiness_passed": True,
            "docker_configuration_realization_verified": True,
            "hash_only_isolation_profile_verified": False,
            "technical_isolation_verified": False,
            "record_projection_isolation_verified": False,
            "trusted_cutoff_anchor_verified": False,
            "independent": False,
        },
    }


def _binding_for_payload(
    relative: Path, payload: Mapping[str, Any], id_field: str
) -> dict[str, Any]:
    content = _pretty_bytes(payload)
    return _binding(
        relative,
        content,
        **{
            id_field: payload[id_field],
            "semantic_body_hash": payload["semantic_body_hash"],
        },
    )


def _approved_preparation_scope() -> dict[str, Any]:
    return {
        "exact_d120_candidate_user_approval_received": True,
        "d120_candidate_id": D120_CANDIDATE_SPEC["identifier"],
        "d120_candidate_semantic_body_hash": D120_CANDIDATE_SPEC["semantic_body_hash"],
        "d120_candidate_file_sha256": D120_CANDIDATE_SPEC["file_sha256"],
        "d120_proposed_action_hash": D120_ACTION_HASH,
        "authorized": {
            "d121_new_only_implementation": True,
            "offline_tests": True,
            "no_start_exact_docker_readiness_preflight": True,
            "execution_authorization_candidate_preparation": True,
        },
        "not_authorized": {
            "docker_container_start_run_exec_attach_cp_or_export": True,
            "opaque_source_filesystem_open_mount_or_byte_read": True,
            "d121_successor_execution": True,
            "prospective_run_output_write": True,
            "d119_mutation_retry_resume_or_repair": True,
            "pool_review_matcher_classifier_calibration": True,
            "score_index_retrieval_injection_agent_provider_evaluator_core": True,
        },
    }


def _preparation_authority(*, materialized: bool) -> dict[str, Any]:
    return {
        "exact_d120_candidate_user_approval_received": True,
        "d121_new_only_implementation_authorized": True,
        "offline_tests_authorized": True,
        "no_start_docker_readiness_authorized": True,
        "execution_authorization_candidate_preparation_authorized": True,
        "d121_preparation_materialized": materialized,
        "no_start_readiness_passed": materialized,
        "docker_configuration_realization_verified": materialized,
        "execution_authorization_candidate_ready": materialized,
        "d119_mutation_authorized": False,
        "d119_retry_resume_or_repair_authorized": False,
        "fresh_successor_run_authorized": False,
        "docker_start_run_exec_attach_cp_or_export_authorized": False,
        "prospective_run_output_write_authorized": False,
        "opaque_source_filesystem_open_mount_or_read_authorized": False,
        "successor_run_count": 0,
        "container_create_count_during_readiness": 1 if materialized else 0,
        "docker_daemon_command_count_during_readiness": 8 if materialized else 0,
        "local_docker_desktop_named_pipe_forced_by_child_environment": materialized,
        "image_pull_forbidden_by_create_argv": True,
        "container_start_count": 0,
        "probe_execution_count": 0,
        "opaque_source_read_count": 0,
        "sealed_source_identifier_reuse_count": 2,
        "record_container_parse_count": 0,
        "record_field_read_count": 0,
        "hash_only_isolation_profile_verified": False,
        "technical_isolation_verified": False,
        "record_projection_isolation_verified": False,
        "trusted_cutoff_anchor_verified": False,
        "independent": False,
        "pool_selection_acquisition_or_freeze_authorized": False,
        "issue_labeling_or_review_authorized": False,
        "matcher_classifier_or_calibration_authorized": False,
        "score_policy_or_index_mutation_authorized": False,
        "retrieval_or_runtime_injection_authorized": False,
        "agent_provider_evaluator_or_core_authorized": False,
        "external_network_call_not_requested_by_patchloop_command_path": True,
        "external_network_socket_instrumentation_verified": False,
        "model_provider_evaluator_call_count": 0,
        "added_model_cost_usd": 0,
    }


def _preparation_receipt_body(
    *,
    recorded_at: str,
    d120_context: Mapping[str, Any],
    protected_state: Mapping[str, Any],
    implementation_state: Mapping[str, Any],
    path_contract: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d121-preparation-approval-receipt",
        "approval_recorded_at": recorded_at,
        "approval_action_id": "d121-prepare-from-exact-d120-candidate",
        "approval_reference": {
            "mode": "exact-candidate-triple-in-current-user-message",
            "candidate_id": D120_CANDIDATE_SPEC["identifier"],
            "semantic_body_hash": D120_CANDIDATE_SPEC["semantic_body_hash"],
            "file_sha256": D120_CANDIDATE_SPEC["file_sha256"],
        },
        "approval_statement_code": "exact-d120-triple-d121-preparation-approved",
        "d120_candidate": d120_context["candidate"],
        "d120_source_gate": d120_context["source_gate"],
        "d120_proposed_action_hash": d120_context["action_hash"],
        "authorized_scope": _approved_preparation_scope(),
        "materialization_scope": {
            "new_only_paths": [
                *(value.as_posix() for value in IMPLEMENTATION_PATHS),
                *(value.as_posix() for value in PREPARATION_OUTPUT_PATHS.values()),
            ],
            "mutation_whitelist": [
                *(value.as_posix() for value in IMPLEMENTATION_PATHS),
                *(value.as_posix() for value in PREPARATION_OUTPUT_PATHS.values()),
            ],
            "prospective_run_outputs_not_authorized": [
                value.as_posix() for value in EXECUTION_OUTPUT_PATHS.values()
            ],
        },
        "protected_pre_state": dict(protected_state),
        "implementation_pre_state": dict(implementation_state),
        "declared_path_contract": dict(path_contract),
        "claim_semantics": {
            "receipt_exclusive_create_is_repository_local_preparation_claim": True,
            "failure_after_receipt_consumes_claim": True,
            "automatic_retry_repair_or_rollback": False,
            "global_or_cross_clone_one_use_proved": False,
            "reviewer_identity_authenticated": False,
            "cryptographic_signature_verified": False,
            "actual_successor_execution_approved": False,
        },
        "execution_result_present": False,
        "authority": _preparation_authority(materialized=False),
    }


def _validate_readiness_evidence(value: Mapping[str, Any], *, repository: Path) -> None:
    _require(
        set(value)
        == {
            "evidence_kind",
            "recorded_at",
            "docker_cli_pre",
            "docker_cli_post",
            "docker_environment_pre",
            "docker_environment_post",
            "image_tag",
            "immutable_image_id",
            "profile_hash",
            "sentinel",
            "portable_create_manifest",
            "container_name_prefix",
            "container_id",
            "created_container_projection",
            "config_checks",
            "cleanup",
            "command_transcript",
            "counters",
            "qualification",
        },
        "D-121 readiness evidence fields differ",
    )
    _parse_time(value["recorded_at"], label="readiness observation")
    _require(
        value["evidence_kind"] == "live-no-start-docker-configuration-realization",
        "D-121 readiness evidence kind differs",
    )
    expected_cli = {
        "file_name": "docker.exe",
        "file_bytes": DOCKER_CLI_BYTES,
        "file_sha256": DOCKER_CLI_SHA256,
        "runner_kind": "subprocess-exact-argv-no-shell-forced-local-docker-host",
    }
    _require(
        _canonical_bytes(value["docker_cli_pre"]) == _canonical_bytes(expected_cli),
        "Docker pre-binding differs",
    )
    _require(
        _canonical_bytes(value["docker_cli_post"]) == _canonical_bytes(expected_cli),
        "Docker post-binding differs",
    )
    expected_environment = _docker_environment_contract()
    _require(
        _canonical_bytes(value["docker_environment_pre"])
        == _canonical_bytes(value["docker_environment_post"])
        == _canonical_bytes(expected_environment),
        "Docker routing environment evidence differs",
    )
    _require(value["image_tag"] == IMAGE_TAG, "readiness image tag differs")
    _require(value["immutable_image_id"] == IMAGE_ID, "readiness image ID differs")
    _require(value["profile_hash"] == PROFILE_HASH, "readiness profile differs")
    _require(
        value["sentinel"]
        == {
            "path": SENTINEL_PATH.as_posix(),
            "file_bytes": 386,
            "file_sha256": d119.DOCKERFILE_SHA256,
            "opaque_source": False,
        },
        "readiness sentinel differs",
    )
    _require(
        value["portable_create_manifest"]
        == _portable_create_manifest(
            name_kind="<runtime-readiness-name>",
            source_kind="<exact-nonopaque-sentinel>",
        ),
        "readiness portable create manifest differs",
    )
    _require(
        value["container_name_prefix"] == "patchloop-d121-readiness-",
        "readiness name prefix differs",
    )
    _require(
        isinstance(value["container_id"], str)
        and _CONTAINER_ID.fullmatch(value["container_id"]) is not None,
        "readiness container ID differs",
    )
    projection = value["created_container_projection"]
    _require(isinstance(projection, dict), "readiness inspect projection missing")
    _require(
        set(projection)
        == {
            "Id",
            "Name",
            "Path",
            "Args",
            "Image",
            "Config",
            "HostConfig",
            "MountCount",
            "Mounts",
            "State",
        },
        "readiness inspect projection fields differ",
    )
    _require(
        isinstance(projection["Config"], dict)
        and set(projection["Config"])
        == {"Cmd", "WorkingDir", "User", "Tty", "OpenStdin", "Labels"},
        "readiness config projection fields differ",
    )
    _require(
        isinstance(projection["HostConfig"], dict)
        and set(projection["HostConfig"])
        == {
            "NetworkMode",
            "ReadonlyRootfs",
            "Privileged",
            "PidsLimit",
            "CapDrop",
            "CapAdd",
            "SecurityOpt",
            "PidMode",
            "IpcMode",
            "Devices",
            "DeviceRequests",
            "Binds",
            "Memory",
            "NanoCpus",
            "RestartPolicy",
            "Tmpfs",
        },
        "readiness host-config projection fields differ",
    )
    _require(
        isinstance(projection["State"], dict)
        and set(projection["State"])
        == {"Status", "Running", "Paused", "Restarting", "Dead", "Pid", "StartedAt"},
        "readiness state projection fields differ",
    )
    _require(
        isinstance(projection["Mounts"], list)
        and len(projection["Mounts"]) == 1
        and set(projection["Mounts"][0]) == {"Type", "Source", "Destination", "RW"}
        and projection["Mounts"][0]["Source"] == "<exact-nonopaque-sentinel>",
        "readiness mount projection differs",
    )
    _require(projection.get("Id") == value["container_id"], "projection ID differs")
    projected_name = str(projection.get("Name", "")).lstrip("/")
    _require(
        re.fullmatch(r"patchloop-d121-readiness-[0-9a-f]{12}", projected_name) is not None,
        "projection name differs",
    )
    sentinel_path = _safe_path(
        repository,
        SENTINEL_PATH,
        must_exist=True,
        label="readiness sentinel",
    )
    rehydrated_projection = {
        **projection,
        "Mounts": [{**row, "Source": str(sentinel_path)} for row in projection["Mounts"]],
    }
    observed_checks = _validate_created_container(
        rehydrated_projection,
        expected_host_path=str(sentinel_path),
        expected_name=projected_name,
    )
    _require(
        _canonical_bytes(value["config_checks"])
        == _canonical_bytes(observed_checks)
        == _canonical_bytes(_expected_config_checks()),
        "readiness config checks differ",
    )
    cleanup = value["cleanup"]
    _require(isinstance(cleanup, dict), "readiness cleanup evidence missing")
    _require(
        set(cleanup)
        == {
            "observation_order",
            "all_observations_collected_before_validation",
            "remove_return_code",
            "missing_inspect_return_code_nonzero",
            "missing_inspect_stdout_presentation",
            "missing_inspect_stdout_bytes",
            "missing_inspect_stdout_sha256",
            "missing_inspect_stderr_bytes",
            "missing_inspect_stderr_sha256",
            "exact_id_residual_count",
            "successor_label_residual_count",
            "raw_stderr_persisted",
            "command_summaries",
        },
        "readiness cleanup fields differ",
    )
    _require(
        cleanup.get("observation_order")
        == [
            "remove-by-exact-id",
            "inspect-by-exact-id",
            "exact-id-inventory",
            "successor-label-inventory",
        ],
        "readiness cleanup observation order differs",
    )
    _require(
        cleanup.get("all_observations_collected_before_validation") is True,
        "cleanup observations incomplete",
    )
    _require(cleanup.get("remove_return_code") == 0, "cleanup remove result differs")
    _require(
        cleanup.get("missing_inspect_return_code_nonzero") is True, "cleanup inspect result differs"
    )
    presentation = cleanup.get("missing_inspect_stdout_presentation")
    reverse = {name: content for content, name in ALLOWED_MISSING_INSPECT_STDOUT.items()}
    _require(presentation in reverse, "cleanup presentation differs")
    inspect_content = reverse[presentation]
    _require(
        cleanup.get("missing_inspect_stdout_bytes") == len(inspect_content),
        "cleanup stdout bytes differ",
    )
    _require(
        cleanup.get("missing_inspect_stdout_sha256") == sha256_bytes(inspect_content),
        "cleanup stdout SHA differs",
    )
    _require(
        type(cleanup.get("missing_inspect_stderr_bytes")) is int, "cleanup stderr byte type differs"
    )
    _require(
        0 <= cleanup["missing_inspect_stderr_bytes"] <= _MAX_COMMAND_OUTPUT,
        "cleanup stderr bytes invalid",
    )
    _require(
        isinstance(cleanup.get("missing_inspect_stderr_sha256"), str)
        and _SHA256.fullmatch(cleanup["missing_inspect_stderr_sha256"]) is not None,
        "cleanup stderr SHA invalid",
    )
    _require(
        type(cleanup.get("exact_id_residual_count")) is int
        and cleanup["exact_id_residual_count"] == 0,
        "exact-ID residual differs",
    )
    _require(
        type(cleanup.get("successor_label_residual_count")) is int
        and cleanup["successor_label_residual_count"] == 0,
        "label residual differs",
    )
    _require(cleanup.get("raw_stderr_persisted") is False, "raw cleanup stderr persisted")
    transcript = value["command_transcript"]
    _require(
        isinstance(transcript, list) and len(transcript) == 8,
        "readiness transcript count differs",
    )
    expected_roles = [
        "image-inspect",
        "preexisting-label-inventory",
        "container-create",
        "container-inspect-before-start",
        "remove-by-exact-id",
        "inspect-by-exact-id",
        "exact-id-inventory",
        "successor-label-inventory",
    ]
    _require(
        [row.get("role") for row in transcript] == expected_roles,
        "readiness transcript roles differ",
    )
    _require(
        [row.get("argv_contract") for row in transcript] == _readiness_argv_contracts(),
        "readiness transcript argv differs",
    )
    _require(
        cleanup.get("command_summaries") == transcript[4:8],
        "cleanup summaries differ",
    )
    for row in transcript:
        _require(
            isinstance(row, dict)
            and set(row)
            == {
                "role",
                "argv_contract",
                "return_code",
                "stdout_bytes",
                "stdout_sha256",
                "stderr_bytes",
                "stderr_sha256",
                "stdout_within_bound",
                "stderr_within_bound",
            },
            "readiness transcript row fields differ",
        )
        _require(
            isinstance(row["argv_contract"], list)
            and row["argv_contract"][0] == "<exact-pinned-docker-cli>",
            "readiness argv contract differs",
        )
        _require(type(row["return_code"]) is int, "readiness return-code type differs")
        _require(
            row["stdout_within_bound"] is True and row["stderr_within_bound"] is True,
            "readiness transcript output exceeded bound",
        )
        for size_key in ("stdout_bytes", "stderr_bytes"):
            _require(
                type(row[size_key]) is int and 0 <= row[size_key] <= _MAX_COMMAND_OUTPUT,
                "readiness transcript size differs",
            )
        for hash_key in ("stdout_sha256", "stderr_sha256"):
            _require(
                isinstance(row[hash_key], str) and _SHA256.fullmatch(row[hash_key]) is not None,
                "readiness transcript SHA differs",
            )
    empty_hash = sha256_bytes(b"")
    container_stdout = value["container_id"].encode("ascii") + b"\n"
    _require(
        [row["return_code"] for row in transcript[:5]] == [0, 0, 0, 0, 0]
        and transcript[5]["return_code"] != 0
        and [row["return_code"] for row in transcript[6:]] == [0, 0],
        "readiness transcript return codes differ",
    )
    for index in (0, 1, 2, 3, 4, 6, 7):
        _require(
            transcript[index]["stderr_bytes"] == 0
            and transcript[index]["stderr_sha256"] == empty_hash,
            "readiness successful command stderr differs",
        )
    for index in (1, 6, 7):
        _require(
            transcript[index]["stdout_bytes"] == 0
            and transcript[index]["stdout_sha256"] == empty_hash,
            "readiness inventory stdout differs",
        )
    image_stdout = (IMAGE_ID + "\n").encode("ascii")
    inspect_stdout = _inspect_projection_stdout(
        projection,
        exact_host_path=str(sentinel_path),
    )
    for index, expected_stdout in (
        (0, image_stdout),
        (2, container_stdout),
        (3, inspect_stdout),
        (4, container_stdout),
    ):
        _require(
            transcript[index]["stdout_bytes"] == len(expected_stdout)
            and transcript[index]["stdout_sha256"] == sha256_bytes(expected_stdout),
            "readiness deterministic command stdout differs",
        )
    _require(
        transcript[5]["stdout_bytes"] == cleanup["missing_inspect_stdout_bytes"]
        and transcript[5]["stdout_sha256"] == cleanup["missing_inspect_stdout_sha256"]
        and transcript[5]["stderr_bytes"] == cleanup["missing_inspect_stderr_bytes"]
        and transcript[5]["stderr_sha256"] == cleanup["missing_inspect_stderr_sha256"],
        "readiness cleanup transcript binding differs",
    )
    _require(
        value["counters"]
        == {
            "docker_command_count": 8,
            "docker_create_count": 1,
            "docker_start_count": 0,
            "docker_run_count": 0,
            "docker_exec_count": 0,
            "probe_execution_count": 0,
            "probe_stdin_bytes": 0,
            "readiness_docker_opaque_path_reference_count": 0,
            "opaque_source_mount_count": 0,
            "opaque_source_filesystem_access_count": 0,
            "opaque_source_filesystem_byte_read_count": 0,
            "sealed_source_identifier_reuse_count": 2,
            "record_parse_count": 0,
            "residual_container_count": 0,
        },
        "readiness counters differ",
    )
    _require(
        value["qualification"]
        == {
            "no_start_readiness_passed": True,
            "docker_configuration_realization_verified": True,
            "hash_only_isolation_profile_verified": False,
            "technical_isolation_verified": False,
            "record_projection_isolation_verified": False,
            "trusted_cutoff_anchor_verified": False,
            "independent": False,
        },
        "readiness qualification differs",
    )


def _future_execution_action(
    *, implementation_state: Mapping[str, Any], readiness_binding: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "action": "execute-one-fresh-d121-hash-only-isolation-successor-run",
        "relationship_to_d119": {
            "fresh_successor_run": True,
            "d119_retry": False,
            "d119_resume": False,
            "d119_repair": False,
            "d119_partial_artifacts_and_implementation_immutable": True,
        },
        "ancestor_d120_action_hash": D120_ACTION_HASH,
        "implementation_state": dict(implementation_state),
        "readiness_evidence": dict(readiness_binding),
        "unchanged_execution_tuple": {
            "immutable_image_id": IMAGE_ID,
            "docker_cli_file_bytes": DOCKER_CLI_BYTES,
            "docker_cli_file_sha256": DOCKER_CLI_SHA256,
            "profile_hash": PROFILE_HASH,
            "source_fingerprint": SOURCE_FINGERPRINT,
            "ordered_sources": [dict(row) for row in SOURCE_PLAN],
        },
        "docker_daemon_routing_contract": {
            "subprocess_environment_removes_all_inherited_docker_prefixed_variables": True,
            "subprocess_environment_forces_docker_host": _LOCAL_DOCKER_ENDPOINT,
            "docker_cli_global_host_or_context_flags_forbidden": True,
            "image_pull_policy": "never",
            "socket_level_instrumentation_verified": False,
        },
        "planned_behavioral_changes_from_d119": [
            "fresh-d121-container-label-and-name-namespace",
            "cleanup-no-row-presentation-normalization",
            "exact-id-and-label-wide-residual-inventories",
            "primary-probe-outcome-preserved-before-cleanup-validation",
            "expanded-cleanup-and-session-journal-events",
        ],
        "container_namespace": {
            "managed_label": MANAGED_LABEL,
            "role_label": ROLE_LABEL,
            "name_prefix": "patchloop-d121-",
        },
        "execution_contract": {
            "fresh_run_count": 1,
            "session_count": 2,
            "source_order": [row["source_id"] for row in SOURCE_PLAN],
            "automatic_retry_count": 0,
            "execution_receipt_and_claim_before_first_docker_mutation": True,
            "successful_journal_events": [
                "ExecutionClaimed",
                "ImageIdentityVerified",
                "IsolationSessionStarted",
                "ProbeResultValidated",
                "ContainerRemovalVerified",
                "IsolationSessionCompleted",
                "IsolationSessionStarted",
                "ProbeResultValidated",
                "ContainerRemovalVerified",
                "IsolationSessionCompleted",
                "ExecutionCompleted",
            ],
            "non_journal_io_failure_after_claim_appends_execution_failed": True,
            "journal_io_failure_may_leave_only_a_durable_prefix": True,
            "failure_before_durable_journal_claim_leaves_partial_consumed_state": True,
            "every_failure_remains_consumed": True,
        },
        "cleanup_contract": {
            "primary_probe_outcome_captured_before_cleanup": True,
            "cleanup_never_masks_primary": True,
            "observation_order_before_validation": [
                "remove-by-exact-id",
                "inspect-by-exact-id",
                "exact-id-inventory",
                "successor-label-inventory",
            ],
            "accepted_missing_inspect_stdout_exact_hex": [
                {"presentation": name, "hex": content.hex()}
                for content, name in ALLOWED_MISSING_INSPECT_STDOUT.items()
            ],
            "both_inventories_always_attempted": True,
            "raw_stderr_persisted": False,
        },
        "execution_output_paths": [value.as_posix() for value in EXECUTION_OUTPUT_PATHS.values()],
        "success_boundary": {
            "hash_only_isolation_profile_verified_may_become_true": True,
            "trusted_cutoff_anchor_verified_remains_false": True,
            "record_projection_isolation_verified_remains_false": True,
            "independence_remains_false": True,
            "retrieval_agent_and_core_remain_closed": True,
        },
    }


def _readiness_body(
    *,
    recorded_at: str,
    receipt_binding: Mapping[str, Any],
    d120_context: Mapping[str, Any],
    protected_state: Mapping[str, Any],
    implementation_state: Mapping[str, Any],
    readiness_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d121-no-start-docker-readiness-preflight",
        "recorded_at": recorded_at,
        "approval_receipt": dict(receipt_binding),
        "d120_candidate": d120_context["candidate"],
        "d120_source_gate": d120_context["source_gate"],
        "d120_proposed_action_hash": D120_ACTION_HASH,
        "readiness_evidence": dict(readiness_evidence),
        "protected_pre_state": dict(protected_state),
        "protected_post_state": dict(protected_state),
        "implementation_pre_state": dict(implementation_state),
        "implementation_post_state": dict(implementation_state),
        "evidence_boundary": {
            "synthetic_nonopaque_sentinel_only": True,
            "opaque_source_filesystem_paths_opened_or_mounted": False,
            "opaque_source_filesystem_bytes_rehashed_or_read": False,
            "sealed_source_metadata_identifiers_reused": True,
            "container_created_but_never_started": True,
            "configuration_realization_only": True,
            "runtime_probe_or_isolation_success": False,
        },
        "authority": _preparation_authority(materialized=True),
    }


def _execution_candidate_body(
    *,
    recorded_at: str,
    receipt_binding: Mapping[str, Any],
    readiness_binding: Mapping[str, Any],
    implementation_state: Mapping[str, Any],
) -> dict[str, Any]:
    action = _future_execution_action(
        implementation_state=implementation_state,
        readiness_binding=readiness_binding,
    )
    action_hash = sha256_bytes(_canonical_bytes(action))
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d121-successor-execution-authorization-candidate",
        "recorded_at": recorded_at,
        "approval_receipt": dict(receipt_binding),
        "readiness": dict(readiness_binding),
        "candidate_status": "awaiting-separate-exact-user-approval",
        "proposed_action": action,
        "proposed_action_hash": action_hash,
        "approval_contract": {
            "exact_candidate_id_required": True,
            "exact_semantic_body_sha_required": True,
            "exact_file_sha_required": True,
            "approval_authorizes_exactly_one_fresh_successor_run": True,
            "approval_does_not_authorize_d119_retry_resume_or_repair": True,
            "automatic_retry_after_failure": False,
            "approval_is_repository_local_self_attested": True,
            "technical_user_authentication_or_unforgeable_capability": False,
            "cooperative_orchestrator_must_confirm_separate_user_message": True,
        },
        "authority": _preparation_authority(materialized=True),
    }


def _source_gate_body(
    *,
    recorded_at: str,
    d120_context: Mapping[str, Any],
    receipt_binding: Mapping[str, Any],
    readiness_binding: Mapping[str, Any],
    candidate_binding: Mapping[str, Any],
    protected_state: Mapping[str, Any],
    implementation_state: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d121-successor-preparation-source-gate",
        "recorded_at": recorded_at,
        "d120_candidate": d120_context["candidate"],
        "d120_source_gate": d120_context["source_gate"],
        "approval_receipt": dict(receipt_binding),
        "readiness": dict(readiness_binding),
        "execution_candidate": dict(candidate_binding),
        "protected_input_integrity": {
            "pre": dict(protected_state),
            "post": dict(protected_state),
            "fingerprints_equal": True,
        },
        "implementation_integrity": {
            "pre": dict(implementation_state),
            "post": dict(implementation_state),
            "fingerprints_equal": True,
        },
        "qualification": {
            "exact_d120_approval_consumed_once_for_preparation": True,
            "offline_contract_and_tamper_tests_required": True,
            "no_start_readiness_passed": True,
            "docker_configuration_realization_verified": True,
            "container_start_count": 0,
            "opaque_source_read_count": 0,
            "execution_authorization_candidate_ready": True,
            "actual_successor_execution_completed": False,
        },
        "evidence_boundary": {
            "preparation_claim_is_repository_local_cooperative_only": True,
            "global_or_cross_clone_one_use_proved": False,
            "synthetic_nonopaque_readiness_only": True,
            "hash_only_runtime_isolation_not_yet_verified": True,
            "trusted_cutoff_record_projection_and_independence_unverified": True,
        },
        "authority": _preparation_authority(materialized=True),
        "next_gate": {
            "action": "exact-d121-candidate-triple-one-fresh-successor-run-approval",
            "requires_candidate_id": True,
            "requires_semantic_body_sha": True,
            "requires_file_sha": True,
            "does_not_authorize_d119_retry_resume_or_repair": True,
            "does_not_unlock_retrieval_agent_or_core": True,
            "approval_is_cooperative_not_cryptographically_enforced": True,
        },
    }


def _build_preparation_artifacts(
    *,
    d120_context: Mapping[str, Any],
    protected_state: Mapping[str, Any],
    implementation_state: Mapping[str, Any],
    path_contract: Mapping[str, Any],
    readiness_evidence: Mapping[str, Any],
    receipt_recorded_at: str,
    readiness_recorded_at: str,
    candidate_recorded_at: str,
    gate_recorded_at: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    receipt = _envelope(
        schema_version="isolation-successor-preparation-approval-receipt-d121-v1",
        id_field="receipt_id",
        id_prefix="d121preparationapproval_",
        body=_preparation_receipt_body(
            recorded_at=receipt_recorded_at,
            d120_context=d120_context,
            protected_state=protected_state,
            implementation_state=implementation_state,
            path_contract=path_contract,
        ),
    )
    receipt_binding = _binding_for_payload(
        PREPARATION_OUTPUT_PATHS["approval_receipt"], receipt, "receipt_id"
    )
    readiness = _envelope(
        schema_version="hash-only-isolation-successor-readiness-preflight-d121-v1",
        id_field="readiness_id",
        id_prefix="d121readiness_",
        body=_readiness_body(
            recorded_at=readiness_recorded_at,
            receipt_binding=receipt_binding,
            d120_context=d120_context,
            protected_state=protected_state,
            implementation_state=implementation_state,
            readiness_evidence=readiness_evidence,
        ),
    )
    readiness_binding = _binding_for_payload(
        PREPARATION_OUTPUT_PATHS["readiness"], readiness, "readiness_id"
    )
    candidate = _envelope(
        schema_version="hash-only-isolation-successor-execution-authorization-candidate-d121-v1",
        id_field="candidate_id",
        id_prefix="d121executioncandidate_",
        body=_execution_candidate_body(
            recorded_at=candidate_recorded_at,
            receipt_binding=receipt_binding,
            readiness_binding=readiness_binding,
            implementation_state=implementation_state,
        ),
    )
    candidate_binding = _binding_for_payload(
        PREPARATION_OUTPUT_PATHS["execution_candidate"], candidate, "candidate_id"
    )
    gate = _envelope(
        schema_version="hash-only-isolation-successor-authorization-source-gate-d121-v1",
        id_field="gate_id",
        id_prefix="d121_",
        body=_source_gate_body(
            recorded_at=gate_recorded_at,
            d120_context=d120_context,
            receipt_binding=receipt_binding,
            readiness_binding=readiness_binding,
            candidate_binding=candidate_binding,
            protected_state=protected_state,
            implementation_state=implementation_state,
        ),
    )
    return receipt, readiness, candidate, gate


def _read_preparation_outputs(
    repository: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, bytes]]:
    specs = {
        "approval_receipt": (
            "isolation-successor-preparation-approval-receipt-d121-v1",
            "receipt_id",
            "d121preparationapproval_",
        ),
        "readiness": (
            "hash-only-isolation-successor-readiness-preflight-d121-v1",
            "readiness_id",
            "d121readiness_",
        ),
        "execution_candidate": (
            "hash-only-isolation-successor-execution-authorization-candidate-d121-v1",
            "candidate_id",
            "d121executioncandidate_",
        ),
        "source_gate": (
            "hash-only-isolation-successor-authorization-source-gate-d121-v1",
            "gate_id",
            "d121_",
        ),
    }
    values: dict[str, dict[str, Any]] = {}
    contents: dict[str, bytes] = {}
    for key, (schema, id_field, prefix) in specs.items():
        path = _safe_path(
            repository,
            PREPARATION_OUTPUT_PATHS[key],
            must_exist=True,
            label=f"D-121 {key}",
        )
        content = _read_stable(path, label=f"D-121 {key}")
        value = _parse_json(content, label=f"D-121 {key}")
        _require(
            set(value) == {"schema_version", id_field, "semantic_body_hash", "semantic_body"},
            f"D-121 {key} root fields differ",
        )
        _require(value["schema_version"] == schema, f"D-121 {key} schema differs")
        body = value["semantic_body"]
        _require(isinstance(body, dict), f"D-121 {key} body missing")
        body_hash = sha256_bytes(_canonical_bytes(body))
        _require(value["semantic_body_hash"] == body_hash, f"D-121 {key} body SHA differs")
        _require(
            value[id_field] == prefix + body_hash.removeprefix("sha256:"), f"D-121 {key} ID differs"
        )
        values[key] = value
        contents[key] = content
    return values, contents


def prepare_d121_execution_candidate(
    *,
    repository: str | Path | None = None,
    docker_path: str | None = None,
) -> dict[str, Any]:
    """Consume the D-120 preparation approval and run only no-start readiness."""

    repo = _repo_root(repository)
    state = _assert_preparation_start_state(repo)
    if state == "complete":
        return validate_d121_preparation(repository=repo)
    _require(state == "empty", f"D-121 preparation state is not executable: {state}")
    _require_future_outputs_absent(repo)
    _require_d119_outputs_absent(repo)
    d120_context = _validate_d120_authority(repo)
    protected_pre = _exact_file_state(repo, PROTECTED_FILE_SPECS)
    implementation_pre = _implementation_state(repo)
    path_contract = _declared_path_contract(repo)
    receipt_recorded_at = _now()
    placeholder_evidence = {
        "evidence_kind": "not-executed-placeholder",
        "recorded_at": receipt_recorded_at,
    }
    receipt = _build_preparation_artifacts(
        d120_context=d120_context,
        protected_state=protected_pre,
        implementation_state=implementation_pre,
        path_contract=path_contract,
        readiness_evidence=placeholder_evidence,
        receipt_recorded_at=receipt_recorded_at,
        readiness_recorded_at=receipt_recorded_at,
        candidate_recorded_at=receipt_recorded_at,
        gate_recorded_at=receipt_recorded_at,
    )[0]
    _write_new(repo, PREPARATION_OUTPUT_PATHS["approval_receipt"], receipt)
    # From this point the repository-local approval is consumed. Any error is
    # intentionally left as a receipt-only partial state with no auto retry.
    runner = _new_runner()
    readiness_evidence = _run_no_start_readiness(
        repository=repo,
        docker_path=docker_path or _docker_path(),
        runner=runner,
    )
    _validate_readiness_evidence(readiness_evidence, repository=repo)
    protected_post = _exact_file_state(repo, PROTECTED_FILE_SPECS)
    implementation_post = _implementation_state(repo)
    _require(protected_post == protected_pre, "protected inputs changed during readiness")
    _require(implementation_post == implementation_pre, "implementation changed during readiness")
    _require_d119_outputs_absent(repo)
    _require_future_outputs_absent(repo)
    readiness_recorded_at = readiness_evidence["recorded_at"]
    candidate_recorded_at = _now()
    gate_recorded_at = _now()
    artifacts = _build_preparation_artifacts(
        d120_context=d120_context,
        protected_state=protected_pre,
        implementation_state=implementation_pre,
        path_contract=path_contract,
        readiness_evidence=readiness_evidence,
        receipt_recorded_at=receipt_recorded_at,
        readiness_recorded_at=readiness_recorded_at,
        candidate_recorded_at=candidate_recorded_at,
        gate_recorded_at=gate_recorded_at,
    )
    _require(_pretty_bytes(artifacts[0]) == _pretty_bytes(receipt), "receipt changed after claim")
    for key, payload in zip(
        ("readiness", "execution_candidate", "source_gate"),
        artifacts[1:],
        strict=True,
    ):
        _write_new(repo, PREPARATION_OUTPUT_PATHS[key], payload)
    return validate_d121_preparation(repository=repo)


def _validate_d121_preparation(
    *, repository: Path, allow_complete_execution: bool
) -> dict[str, Any]:
    repo = repository
    _require(_assert_preparation_start_state(repo) == "complete", "D-121 preparation is incomplete")
    execution_state = _execution_output_state(repo)
    if allow_complete_execution:
        _require(execution_state == "complete", "D-121 execution is not complete")
    else:
        _require(
            execution_state == "empty",
            "D-121 prospective execution outputs are not authorized during preparation",
        )
    _require_d119_outputs_absent(repo)
    d120_context = _validate_d120_authority(repo)
    protected_state = _exact_file_state(repo, PROTECTED_FILE_SPECS)
    implementation_state = _implementation_state(repo)
    path_contract = _declared_path_contract(repo)
    values, contents = _read_preparation_outputs(repo)
    receipt_body = values["approval_receipt"]["semantic_body"]
    readiness_body = values["readiness"]["semantic_body"]
    candidate_body = values["execution_candidate"]["semantic_body"]
    gate_body = values["source_gate"]["semantic_body"]
    readiness_evidence = readiness_body.get("readiness_evidence")
    _require(isinstance(readiness_evidence, dict), "D-121 readiness evidence missing")
    _validate_readiness_evidence(readiness_evidence, repository=repo)
    times = [
        receipt_body.get("approval_recorded_at"),
        readiness_body.get("recorded_at"),
        candidate_body.get("recorded_at"),
        gate_body.get("recorded_at"),
    ]
    parsed = [_parse_time(value, label="preparation artifact") for value in times]
    d120_gate_time = _parse_time(
        _parse_json(
            _read_stable(
                _safe_path(repo, D120_GATE_SPEC["path"], must_exist=True, label="D-120 gate"),
                label="D-120 gate",
            ),
            label="D-120 gate",
        )["semantic_body"]["recorded_at"],
        label="D-120 gate",
    )
    _require(
        d120_gate_time <= parsed[0]
        and all(left <= right for left, right in zip(parsed, parsed[1:], strict=False)),
        "D-121 preparation chronology differs",
    )
    expected = _build_preparation_artifacts(
        d120_context=d120_context,
        protected_state=protected_state,
        implementation_state=implementation_state,
        path_contract=path_contract,
        readiness_evidence=readiness_evidence,
        receipt_recorded_at=times[0],
        readiness_recorded_at=times[1],
        candidate_recorded_at=times[2],
        gate_recorded_at=times[3],
    )
    for key, expected_payload in zip(
        ("approval_receipt", "readiness", "execution_candidate", "source_gate"),
        expected,
        strict=True,
    ):
        _require(
            contents[key] == _pretty_bytes(expected_payload),
            f"D-121 {key} expected payload differs",
        )
    # Repeat every protected and output read so a cross-file swap during
    # validation cannot be mistaken for a sealed result.
    _require(_validate_d120_authority(repo) == d120_context, "D-120 changed during validation")
    _require(
        _exact_file_state(repo, PROTECTED_FILE_SPECS) == protected_state,
        "protected inputs changed during validation",
    )
    _require(
        _implementation_state(repo) == implementation_state,
        "D-121 implementation changed during validation",
    )
    _require_d119_outputs_absent(repo)
    _require(
        _execution_output_state(repo) == execution_state,
        "D-121 execution output state changed during preparation validation",
    )
    reread_values, reread_contents = _read_preparation_outputs(repo)
    _require(
        reread_values == values and reread_contents == contents,
        "D-121 artifacts changed during validation",
    )
    candidate = values["execution_candidate"]
    gate = values["source_gate"]
    return {
        "status": "D121_EXECUTION_CANDIDATE_READY_PENDING_EXACT_APPROVAL",
        "approval_receipt_id": values["approval_receipt"]["receipt_id"],
        "readiness_id": values["readiness"]["readiness_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_semantic_body_hash": candidate["semantic_body_hash"],
        "candidate_file_bytes": len(contents["execution_candidate"]),
        "candidate_file_sha256": sha256_bytes(contents["execution_candidate"]),
        "proposed_action_hash": candidate_body["proposed_action_hash"],
        "source_gate_id": gate["gate_id"],
        "source_gate_semantic_body_hash": gate["semantic_body_hash"],
        "source_gate_file_bytes": len(contents["source_gate"]),
        "source_gate_file_sha256": sha256_bytes(contents["source_gate"]),
        "docker_command_count": readiness_evidence["counters"]["docker_command_count"],
        "docker_start_count": 0,
        "opaque_source_read_count": 0,
        "docker_configuration_realization_verified": True,
        "hash_only_isolation_profile_verified": False,
        "fresh_successor_run_authorized": False,
        "fresh_successor_run_count": 0,
        "trusted_cutoff_anchor_verified": False,
        "record_projection_isolation_verified": False,
        "independent": False,
        "retrieval_agent_and_core_authorized": False,
    }


def validate_d121_preparation(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Validate sealed preparation while requiring all future run outputs absent."""

    return _validate_d121_preparation(
        repository=_repo_root(repository),
        allow_complete_execution=False,
    )


class _ExecutionJournal:
    def __init__(self, *, repository: Path) -> None:
        self.path = _safe_path(
            repository,
            EXECUTION_OUTPUT_PATHS["journal"],
            must_exist=False,
            label="D-121 execution journal",
        )
        _require(
            not self.path.exists() and not _is_linklike(self.path), "execution journal collision"
        )
        self._parent = self.path.parent.stat()
        self._handle = self.path.open("xb")
        opened = os.fstat(self._handle.fileno())
        selected = self.path.stat()
        _require(
            (opened.st_dev, opened.st_ino) == (selected.st_dev, selected.st_ino),
            "execution journal identity differs",
        )
        self._identity = (opened.st_dev, opened.st_ino)
        self.sequence = 0
        self.head = "sha256:" + "0" * 64

    def append(self, event: str, data: Mapping[str, Any]) -> dict[str, Any]:
        body = {
            "schema_version": "hash-only-isolation-successor-journal-record-d121-v1",
            "sequence": self.sequence,
            "recorded_at": _now(),
            "event": event,
            "previous_record_hash": self.head,
            "data": dict(data),
        }
        record = {**body, "record_hash": sha256_bytes(_canonical_bytes(body))}
        self._handle.write(_canonical_bytes(record) + b"\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())
        self.sequence += 1
        self.head = record["record_hash"]
        return record

    def close(self) -> None:
        if self._handle.closed:
            return
        self._handle.flush()
        os.fsync(self._handle.fileno())
        opened = os.fstat(self._handle.fileno())
        selected = self.path.stat()
        parent = self.path.parent.stat()
        _require(
            (opened.st_dev, opened.st_ino) == self._identity == (selected.st_dev, selected.st_ino),
            "execution journal changed",
        )
        _require(
            (parent.st_dev, parent.st_ino) == (self._parent.st_dev, self._parent.st_ino),
            "execution journal parent changed",
        )
        self._handle.close()


def _execution_output_state(repository: Path) -> str:
    present = [
        key
        for key, relative in EXECUTION_OUTPUT_PATHS.items()
        if (repository / relative).exists() or _is_linklike(repository / relative)
    ]
    if not present:
        return "empty"
    if len(present) == len(EXECUTION_OUTPUT_PATHS):
        return "complete"
    return "partial-consumed"


def _execution_receipt_body(
    *,
    recorded_at: str,
    candidate_binding: Mapping[str, Any],
    proposed_action_hash: str,
    implementation_state: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d121-successor-execution-approval-receipt",
        "approval_recorded_at": recorded_at,
        "approval_reference": {
            "mode": "separate-exact-d121-candidate-triple-user-message",
            "candidate_id": candidate_binding["candidate_id"],
            "semantic_body_hash": candidate_binding["semantic_body_hash"],
            "file_sha256": candidate_binding["file_sha256"],
        },
        "candidate": dict(candidate_binding),
        "authorized_action_hash": proposed_action_hash,
        "implementation_state": dict(implementation_state),
        "authorized_scope": {
            "fresh_successor_run_count": 1,
            "exact_session_count": 2,
            "source_order": [row["source_id"] for row in SOURCE_PLAN],
            "d119_retry_resume_or_repair": False,
            "automatic_retry_count": 0,
            "execution_output_paths": [
                value.as_posix() for value in EXECUTION_OUTPUT_PATHS.values()
            ],
        },
        "claim_semantics": {
            "receipt_then_journal_claim_precede_first_docker_mutation": True,
            "failure_consumes_repository_local_capability": True,
            "automatic_retry_repair_or_rollback": False,
            "global_or_cross_clone_one_use_proved": False,
            "reviewer_identity_authenticated": False,
            "cryptographic_signature_verified": False,
        },
        "execution_result_present": False,
    }


def _invoke_execution(
    runner: CommandRunner,
    command: Sequence[str],
    *,
    input_bytes: bytes | None = None,
    timeout_seconds: int,
    allowed_create_host_path: str | None = None,
    allowed_execution_name: str | None = None,
    allowed_container_id: str | None = None,
    expected_input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    _require(len(command) >= 2, "execution Docker command missing")
    verb = command[1]
    if verb == "image":
        _require(list(command) == _image_id_command(command[0]), "execution image argv differs")
    elif verb == "ps":
        _validate_no_start_argv(command)
    elif verb == "create":
        _require(
            allowed_create_host_path is not None and allowed_execution_name is not None,
            "execution create binding missing",
        )
        _require(
            list(command)
            == _create_command(
                docker=command[0],
                name=allowed_execution_name,
                host_path=allowed_create_host_path,
            ),
            "execution create argv differs",
        )
    elif verb == "inspect":
        if "--format" in command:
            _require(
                len(command) == 5
                and command[2:4] == ["--format", _INSPECT_PROJECTION_FORMAT]
                and _CONTAINER_ID.fullmatch(command[4]) is not None,
                "execution projection inspect argv differs",
            )
            _require(
                command[4] == allowed_container_id, "execution projection inspect target differs"
            )
        else:
            _require(
                len(command) == 3 and _CONTAINER_ID.fullmatch(command[2]) is not None,
                "execution inspect argv differs",
            )
            _require(command[2] == allowed_container_id, "execution inspect target differs")
    elif verb == "rm":
        _require(
            len(command) == 4
            and command[2] == "--force"
            and _CONTAINER_ID.fullmatch(command[3]) is not None,
            "execution remove argv differs",
        )
        _require(command[3] == allowed_container_id, "execution remove target differs")
    elif verb == "start":
        _require(command[2:4] == ["--attach", "--interactive"], "execution start flags differ")
        _require(
            len(command) == 5 and _CONTAINER_ID.fullmatch(command[4]) is not None,
            "execution start target differs",
        )
        _require(command[4] == allowed_container_id, "execution start target binding differs")
    else:
        raise D121ExecutionError("execution Docker verb is not in the exact allowlist")
    if verb == "start":
        _require(
            input_bytes is not None
            and expected_input_bytes is not None
            and input_bytes == expected_input_bytes,
            "execution start probe input differs",
        )
    else:
        _require(input_bytes is None, "non-start Docker input forbidden")
    return runner.run(
        command,
        input_bytes=input_bytes,
        timeout_seconds=timeout_seconds,
    )


def _expected_probe_result(source: Mapping[str, Any]) -> dict[str, Any]:
    return d119._expected_probe_result(source)  # noqa: SLF001 - exact sealed tuple reuse


def _probe_source(source: Mapping[str, Any]) -> bytes:
    content = d119._probe_source(source).encode("utf-8")  # noqa: SLF001
    _require(sha256_bytes(content) == source["probe_source_sha256"], "probe source SHA differs")
    return content


def _execute_successor_session(
    *,
    repository: Path,
    docker: str,
    runner: CommandRunner,
    source: Mapping[str, Any],
) -> tuple[
    dict[str, Any] | None, BaseException | None, dict[str, Any] | None, BaseException | None
]:
    # Resolution and metadata checks do not open or hash the opaque object.
    host_path = _safe_path(
        repository, source["path"], must_exist=True, label="opaque execution source"
    )
    name = f"patchloop-d121-{source['source_id']}-{uuid.uuid4().hex[:12]}"
    create_command = _create_command(docker=docker, name=name, host_path=str(host_path))
    primary_error: BaseException | None = None
    cleanup_error: BaseException | None = None
    evidence: dict[str, Any] | None = None
    cleanup: dict[str, Any] | None = None
    container_id: str | None = None
    created = False
    try:
        created = True  # The create attempt may mutate before returning or timing out.
        create_result = _invoke_execution(
            runner,
            create_command,
            timeout_seconds=30,
            allowed_create_host_path=str(host_path),
            allowed_execution_name=name,
        )
        _require(
            create_result.returncode == 0 and create_result.stderr == b"",
            "successor container create failed",
        )
        _require(
            len(create_result.stdout) == 65 and create_result.stdout.endswith(b"\n"),
            "successor container ID output bytes differ",
        )
        try:
            candidate_id = create_result.stdout[:-1].decode("ascii", errors="strict")
        except UnicodeDecodeError as exc:
            raise D121ExecutionError("successor container ID is not ASCII") from exc
        _require(
            _CONTAINER_ID.fullmatch(candidate_id) is not None, "successor container ID invalid"
        )
        container_id = candidate_id
        inspect_result = _invoke_execution(
            runner,
            _inspect_projection_command(docker, container_id),
            timeout_seconds=20,
            allowed_container_id=container_id,
        )
        _require(
            inspect_result.returncode == 0 and inspect_result.stderr == b"",
            "successor inspect failed",
        )
        _require(
            len(inspect_result.stdout) <= _MAX_COMMAND_OUTPUT
            and len(inspect_result.stderr) <= _MAX_COMMAND_OUTPUT,
            "successor inspect projection output too large",
        )
        try:
            inspect_value = json.loads(inspect_result.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise D121ExecutionError("successor inspect output invalid") from exc
        _require(
            isinstance(inspect_value, dict) and inspect_value.get("Id") == container_id,
            "successor inspect projection differs",
        )
        config_checks = _validate_created_container(
            inspect_value, expected_host_path=str(host_path), expected_name=name
        )
        portable_projection = _created_container_projection(
            inspect_value,
            source_token="<exact-opaque-source>",
        )
        _require(
            inspect_result.stdout
            == _inspect_projection_stdout(portable_projection, exact_host_path=str(host_path)),
            "successor inspect projection bytes differ",
        )
        probe = _probe_source(source)
        started = _invoke_execution(
            runner,
            [docker, "start", "--attach", "--interactive", container_id],
            input_bytes=probe,
            timeout_seconds=40,
            allowed_container_id=container_id,
            expected_input_bytes=probe,
        )
        _require(started.returncode == 0, "successor probe returned nonzero")
        _require(
            len(started.stdout) <= 4096 and len(started.stderr) <= 4096,
            "successor probe output too large",
        )
        _require(started.stderr == b"", "successor probe stderr differs")
        try:
            result = json.loads(started.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise D121ExecutionError("successor probe output invalid") from exc
        expected_result = _expected_probe_result(source)
        _require(result == expected_result, "successor probe result differs")
        _require(
            started.stdout == _canonical_bytes(expected_result) + b"\n",
            "successor probe stdout differs",
        )
        evidence = {
            "source_id": source["source_id"],
            "container_name": name,
            "container_id": container_id,
            "image_id": IMAGE_ID,
            "probe_source_sha256": sha256_bytes(probe),
            "config_checks": config_checks,
            "created_container_projection": portable_projection,
            "result": result,
            "stdout_bytes": len(started.stdout),
            "stdout_sha256": sha256_bytes(started.stdout),
            "stderr_bytes": len(started.stderr),
            "stderr_sha256": sha256_bytes(started.stderr),
            "raw_record_bytes_emitted": False,
            "primary_status": "PROBE_RESULT_VALIDATED",
        }
    except BaseException as exc:  # noqa: BLE001 - preserve primary outcome through cleanup
        primary_error = exc
    finally:
        if created:
            if container_id is not None:
                cleanup_results, cleanup_summaries = _cleanup_observations(
                    runner=runner,
                    docker=docker,
                    container_id=container_id,
                )
                try:
                    cleanup = _validate_cleanup_results(cleanup_results, cleanup_summaries)
                except BaseException as exc:  # noqa: BLE001 - returned separately
                    cleanup_error = exc
            else:
                _, emergency_errors = _emergency_cleanup_by_name(
                    runner=runner,
                    docker=docker,
                    container_name=name,
                    expected_host_path=str(host_path),
                )
                cleanup_error = D121ExecutionError(
                    "untrusted container ID required emergency name cleanup"
                    + (":" + ",".join(emergency_errors) if emergency_errors else "")
                )
    if evidence is not None:
        evidence["cleanup"] = cleanup
        evidence["cleanup_status"] = (
            "CONTAINER_REMOVAL_VERIFIED" if cleanup_error is None else "CLEANUP_FAILED"
        )
    return evidence, primary_error, cleanup, cleanup_error


def _execution_evidence_body(
    *,
    recorded_at: str,
    execution_receipt_binding: Mapping[str, Any],
    preparation_candidate_binding: Mapping[str, Any],
    proposed_action_hash: str,
    journal_binding: Mapping[str, Any],
    sessions: Sequence[Mapping[str, Any]],
    protected_state: Mapping[str, Any],
    implementation_state: Mapping[str, Any],
    docker_environment_pre: Mapping[str, Any],
    docker_environment_post: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d121-successor-hash-only-isolation-evidence",
        "recorded_at": recorded_at,
        "execution_approval_receipt": dict(execution_receipt_binding),
        "preparation_candidate": dict(preparation_candidate_binding),
        "authorized_action_hash": proposed_action_hash,
        "journal": dict(journal_binding),
        "sessions": [dict(row) for row in sessions],
        "source_order": [row["source_id"] for row in SOURCE_PLAN],
        "docker_environment_pre": dict(docker_environment_pre),
        "docker_environment_post": dict(docker_environment_post),
        "protected_pre_state": dict(protected_state),
        "protected_post_state": dict(protected_state),
        "implementation_pre_state": dict(implementation_state),
        "implementation_post_state": dict(implementation_state),
        "qualification": {
            "fresh_successor_run_count": 1,
            "isolation_session_count": 2,
            "opaque_stream_hash_read_count": 2,
            "hash_only_isolation_profile_verified": True,
            "record_container_parse_count": 0,
            "record_field_read_count": 0,
            "raw_record_bytes_emitted": False,
            "residual_container_count": 0,
            "trusted_cutoff_anchor_verified": False,
            "record_projection_isolation_verified": False,
            "independent": False,
        },
        "authority": {
            "score_policy_or_index_mutation_authorized": False,
            "retrieval_or_runtime_injection_authorized": False,
            "agent_provider_evaluator_or_core_authorized": False,
            "added_model_cost_usd": 0,
        },
    }


def _execution_gate_body(
    *,
    recorded_at: str,
    candidate_binding: Mapping[str, Any],
    receipt_binding: Mapping[str, Any],
    journal_binding: Mapping[str, Any],
    evidence_binding: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d121-successor-execution-completion-gate",
        "recorded_at": recorded_at,
        "preparation_candidate": dict(candidate_binding),
        "execution_approval_receipt": dict(receipt_binding),
        "journal": dict(journal_binding),
        "isolation_evidence": dict(evidence_binding),
        "qualification": {
            "fresh_successor_run_completed": True,
            "hash_only_isolation_profile_verified": True,
            "session_count": 2,
            "automatic_retry_count": 0,
            "residual_container_count": 0,
            "trusted_cutoff_anchor_verified": False,
            "record_projection_isolation_verified": False,
            "independent": False,
        },
        "authority": {
            "d119_retry_resume_or_repair_performed": False,
            "score_policy_or_index_mutation_authorized": False,
            "retrieval_or_runtime_injection_authorized": False,
            "agent_provider_evaluator_or_core_authorized": False,
        },
    }


def _read_execution_journal(repository: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = _safe_path(
        repository,
        EXECUTION_OUTPUT_PATHS["journal"],
        must_exist=True,
        label="D-121 execution journal",
    )
    content = _read_stable(path, label="D-121 execution journal")
    _require(content.endswith(b"\n"), "execution journal newline missing")
    rows: list[dict[str, Any]] = []
    previous = "sha256:" + "0" * 64
    for sequence, line in enumerate(content.splitlines()):
        try:
            row = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise D121ExecutionError("execution journal row invalid") from exc
        _require(isinstance(row, dict), "execution journal row root differs")
        _require(line == _canonical_bytes(row), "execution journal row bytes differ")
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
            "execution journal row fields differ",
        )
        _require(
            row["schema_version"] == "hash-only-isolation-successor-journal-record-d121-v1",
            "execution journal schema differs",
        )
        _require(
            type(row["sequence"]) is int and row["sequence"] == sequence,
            "execution journal sequence differs",
        )
        _parse_time(row["recorded_at"], label="execution journal")
        _require(isinstance(row["event"], str), "execution journal event differs")
        _require(row["previous_record_hash"] == previous, "execution journal chain differs")
        body = {key: value for key, value in row.items() if key != "record_hash"}
        _require(
            row["record_hash"] == sha256_bytes(_canonical_bytes(body)),
            "execution journal hash differs",
        )
        previous = row["record_hash"]
        rows.append(row)
    _require(rows, "execution journal empty")
    _require(
        content == b"".join(_canonical_bytes(row) + b"\n" for row in rows),
        "execution journal file bytes differ",
    )
    return rows, {
        "path": EXECUTION_OUTPUT_PATHS["journal"].as_posix(),
        "record_count": len(rows),
        "head_hash": previous,
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _validate_execution_cleanup(value: Mapping[str, Any], *, container_id: str) -> None:
    expected_keys = {
        "observation_order",
        "all_observations_collected_before_validation",
        "remove_return_code",
        "missing_inspect_return_code_nonzero",
        "missing_inspect_stdout_presentation",
        "missing_inspect_stdout_bytes",
        "missing_inspect_stdout_sha256",
        "missing_inspect_stderr_bytes",
        "missing_inspect_stderr_sha256",
        "exact_id_residual_count",
        "successor_label_residual_count",
        "raw_stderr_persisted",
        "command_summaries",
    }
    _require(set(value) == expected_keys, "execution cleanup fields differ")
    expected_roles = [
        "remove-by-exact-id",
        "inspect-by-exact-id",
        "exact-id-inventory",
        "successor-label-inventory",
    ]
    _require(value["observation_order"] == expected_roles, "execution cleanup order differs")
    _require(
        value["all_observations_collected_before_validation"] is True,
        "execution cleanup observations incomplete",
    )
    _require(
        type(value["remove_return_code"]) is int and value["remove_return_code"] == 0,
        "execution cleanup remove differs",
    )
    _require(
        value["missing_inspect_return_code_nonzero"] is True, "execution cleanup inspect differs"
    )
    reverse = {name: content for content, name in ALLOWED_MISSING_INSPECT_STDOUT.items()}
    presentation = value["missing_inspect_stdout_presentation"]
    _require(presentation in reverse, "execution cleanup presentation differs")
    inspect_stdout = reverse[presentation]
    _require(
        value["missing_inspect_stdout_bytes"] == len(inspect_stdout)
        and value["missing_inspect_stdout_sha256"] == sha256_bytes(inspect_stdout),
        "execution cleanup inspect stdout binding differs",
    )
    _require(
        type(value["missing_inspect_stderr_bytes"]) is int
        and 0 <= value["missing_inspect_stderr_bytes"] <= _MAX_COMMAND_OUTPUT
        and isinstance(value["missing_inspect_stderr_sha256"], str)
        and _SHA256.fullmatch(value["missing_inspect_stderr_sha256"]) is not None,
        "execution cleanup inspect stderr binding differs",
    )
    _require(
        type(value["exact_id_residual_count"]) is int
        and value["exact_id_residual_count"] == 0
        and type(value["successor_label_residual_count"]) is int
        and value["successor_label_residual_count"] == 0
        and value["raw_stderr_persisted"] is False,
        "execution cleanup residual boundary differs",
    )
    summaries = value["command_summaries"]
    _require(
        isinstance(summaries, list) and len(summaries) == 4, "execution cleanup summaries differ"
    )
    expected_argv = [
        ["<exact-pinned-docker-cli>", "rm", "--force", "<exact-container-id>"],
        ["<exact-pinned-docker-cli>", "inspect", "<exact-container-id>"],
        _inventory_command("<exact-pinned-docker-cli>", "id=<exact-container-id>"),
        _inventory_command("<exact-pinned-docker-cli>", f"label={MANAGED_LABEL}"),
    ]
    _require(
        [row.get("role") for row in summaries] == expected_roles,
        "execution cleanup summary roles differ",
    )
    _require(
        [row.get("argv_contract") for row in summaries] == expected_argv,
        "execution cleanup argv differs",
    )
    for row in summaries:
        _require(
            isinstance(row, dict)
            and set(row)
            == {
                "role",
                "argv_contract",
                "return_code",
                "stdout_bytes",
                "stdout_sha256",
                "stderr_bytes",
                "stderr_sha256",
                "stdout_within_bound",
                "stderr_within_bound",
            },
            "execution cleanup summary fields differ",
        )
        _require(type(row["return_code"]) is int, "execution cleanup return-code type differs")
        _require(
            row["stdout_within_bound"] is True and row["stderr_within_bound"] is True,
            "execution cleanup output exceeded bound",
        )
        for key in ("stdout_bytes", "stderr_bytes"):
            _require(
                type(row[key]) is int and 0 <= row[key] <= _MAX_COMMAND_OUTPUT,
                "execution cleanup size differs",
            )
        for key in ("stdout_sha256", "stderr_sha256"):
            _require(
                isinstance(row[key], str) and _SHA256.fullmatch(row[key]) is not None,
                "execution cleanup SHA differs",
            )
    empty_hash = sha256_bytes(b"")
    id_stdout = container_id.encode("ascii") + b"\n"
    _require(
        summaries[0]["return_code"] == 0
        and summaries[0]["stdout_bytes"] == len(id_stdout)
        and summaries[0]["stdout_sha256"] == sha256_bytes(id_stdout)
        and summaries[0]["stderr_bytes"] == 0
        and summaries[0]["stderr_sha256"] == empty_hash,
        "execution cleanup remove summary differs",
    )
    _require(
        summaries[1]["return_code"] != 0
        and summaries[1]["stdout_bytes"] == len(inspect_stdout)
        and summaries[1]["stdout_sha256"] == sha256_bytes(inspect_stdout)
        and summaries[1]["stderr_bytes"] == value["missing_inspect_stderr_bytes"]
        and summaries[1]["stderr_sha256"] == value["missing_inspect_stderr_sha256"],
        "execution cleanup missing-inspect summary differs",
    )
    for row in summaries[2:]:
        _require(
            row["return_code"] == 0
            and row["stdout_bytes"] == 0
            and row["stdout_sha256"] == empty_hash
            and row["stderr_bytes"] == 0
            and row["stderr_sha256"] == empty_hash,
            "execution cleanup inventory summary differs",
        )


def _validate_execution_session(
    value: Mapping[str, Any], *, source: Mapping[str, Any], repository: Path
) -> None:
    expected_keys = {
        "source_id",
        "container_name",
        "container_id",
        "image_id",
        "probe_source_sha256",
        "config_checks",
        "created_container_projection",
        "result",
        "stdout_bytes",
        "stdout_sha256",
        "stderr_bytes",
        "stderr_sha256",
        "raw_record_bytes_emitted",
        "primary_status",
        "cleanup",
        "cleanup_status",
    }
    _require(set(value) == expected_keys, "execution session fields differ")
    _require(value["source_id"] == source["source_id"], "execution session source differs")
    _require(
        isinstance(value["container_name"], str)
        and re.fullmatch(
            rf"patchloop-d121-{re.escape(source['source_id'])}-[0-9a-f]{{12}}",
            value["container_name"],
        )
        is not None,
        "execution session name differs",
    )
    _require(
        isinstance(value["container_id"], str)
        and _CONTAINER_ID.fullmatch(value["container_id"]) is not None,
        "execution session container ID differs",
    )
    _require(value["image_id"] == IMAGE_ID, "execution session image differs")
    _require(
        value["probe_source_sha256"] == source["probe_source_sha256"], "execution probe SHA differs"
    )
    projection = value["created_container_projection"]
    _require(isinstance(projection, dict), "execution container projection missing")
    _require(
        set(projection)
        == {
            "Id",
            "Name",
            "Path",
            "Args",
            "Image",
            "Config",
            "HostConfig",
            "MountCount",
            "Mounts",
            "State",
        },
        "execution container projection fields differ",
    )
    _require(
        projection.get("Id") == value["container_id"],
        "execution projection container ID differs",
    )
    _require(
        isinstance(projection["Config"], dict)
        and set(projection["Config"])
        == {"Cmd", "WorkingDir", "User", "Tty", "OpenStdin", "Labels"},
        "execution config projection fields differ",
    )
    _require(
        isinstance(projection["HostConfig"], dict)
        and set(projection["HostConfig"])
        == {
            "NetworkMode",
            "ReadonlyRootfs",
            "Privileged",
            "PidsLimit",
            "CapDrop",
            "CapAdd",
            "SecurityOpt",
            "PidMode",
            "IpcMode",
            "Devices",
            "DeviceRequests",
            "Binds",
            "Memory",
            "NanoCpus",
            "RestartPolicy",
            "Tmpfs",
        },
        "execution host-config projection fields differ",
    )
    _require(
        isinstance(projection["State"], dict)
        and set(projection["State"])
        == {"Status", "Running", "Paused", "Restarting", "Dead", "Pid", "StartedAt"},
        "execution state projection fields differ",
    )
    _require(
        isinstance(projection.get("Mounts"), list)
        and len(projection["Mounts"]) == 1
        and set(projection["Mounts"][0]) == {"Type", "Source", "Destination", "RW"}
        and projection["Mounts"][0]["Source"] == "<exact-opaque-source>",
        "execution source mount projection differs",
    )
    host_path = _safe_path(
        repository, source["path"], must_exist=True, label="sealed execution source"
    )
    hydrated = {
        **projection,
        "Mounts": [{**projection["Mounts"][0], "Source": str(host_path)}],
    }
    checks = _validate_created_container(
        hydrated,
        expected_host_path=str(host_path),
        expected_name=value["container_name"],
    )
    _require(
        _canonical_bytes(value["config_checks"])
        == _canonical_bytes(checks)
        == _canonical_bytes(_expected_config_checks()),
        "execution config checks differ",
    )
    expected_result = _expected_probe_result(source)
    expected_stdout = _canonical_bytes(expected_result) + b"\n"
    _require(
        _canonical_bytes(value["result"]) == _canonical_bytes(expected_result),
        "execution probe result differs",
    )
    _require(
        type(value["stdout_bytes"]) is int
        and value["stdout_bytes"] == len(expected_stdout)
        and value["stdout_sha256"] == sha256_bytes(expected_stdout)
        and type(value["stderr_bytes"]) is int
        and value["stderr_bytes"] == 0
        and value["stderr_sha256"] == sha256_bytes(b""),
        "execution probe output binding differs",
    )
    _require(
        value["raw_record_bytes_emitted"] is False
        and value["primary_status"] == "PROBE_RESULT_VALIDATED"
        and value["cleanup_status"] == "CONTAINER_REMOVAL_VERIFIED",
        "execution session status differs",
    )
    _require(isinstance(value["cleanup"], dict), "execution cleanup missing")
    _validate_execution_cleanup(value["cleanup"], container_id=value["container_id"])


def _execute_d121_successor_after_cooperative_approval(
    *,
    candidate_id: str,
    semantic_body_sha: str,
    file_sha: str,
    repository: str | Path | None = None,
    docker_path: str | None = None,
) -> dict[str, Any]:
    """Internal executor; the caller must establish the separate user approval."""

    repo = _repo_root(repository)
    state = _execution_output_state(repo)
    if state == "complete":
        completed_preparation = _validate_d121_preparation(
            repository=repo,
            allow_complete_execution=True,
        )
        _require(
            candidate_id == completed_preparation["candidate_id"],
            "exact D-121 candidate ID approval differs",
        )
        _require(
            semantic_body_sha == completed_preparation["candidate_semantic_body_hash"],
            "exact D-121 body SHA approval differs",
        )
        _require(
            file_sha == completed_preparation["candidate_file_sha256"],
            "exact D-121 file SHA approval differs",
        )
        return validate_d121_execution(repository=repo)
    _require(state == "empty", "D-121 execution state is partial and consumed")
    prepared = validate_d121_preparation(repository=repo)
    _require(candidate_id == prepared["candidate_id"], "exact D-121 candidate ID approval differs")
    _require(
        semantic_body_sha == prepared["candidate_semantic_body_hash"],
        "exact D-121 body SHA approval differs",
    )
    _require(file_sha == prepared["candidate_file_sha256"], "exact D-121 file SHA approval differs")
    values, preparation_contents = _read_preparation_outputs(repo)
    candidate = values["execution_candidate"]
    candidate_binding = _binding_for_payload(
        PREPARATION_OUTPUT_PATHS["execution_candidate"], candidate, "candidate_id"
    )
    proposed_action_hash = candidate["semantic_body"]["proposed_action_hash"]
    protected_pre = _exact_file_state(repo, PROTECTED_FILE_SPECS)
    implementation_pre = _implementation_state(repo)
    receipt = _envelope(
        schema_version="hash-only-isolation-successor-execution-approval-receipt-d121-v1",
        id_field="receipt_id",
        id_prefix="d121executionapproval_",
        body=_execution_receipt_body(
            recorded_at=_now(),
            candidate_binding=candidate_binding,
            proposed_action_hash=proposed_action_hash,
            implementation_state=implementation_pre,
        ),
    )
    receipt_content = _write_new(repo, EXECUTION_OUTPUT_PATHS["approval_receipt"], receipt)
    receipt_binding = _binding(
        EXECUTION_OUTPUT_PATHS["approval_receipt"],
        receipt_content,
        receipt_id=receipt["receipt_id"],
        semantic_body_hash=receipt["semantic_body_hash"],
    )
    journal = _ExecutionJournal(repository=repo)
    failure_event_appended = False
    active_stage = "journal-claim"
    primary_failure: BaseException | None = None
    sessions: list[dict[str, Any]] = []
    docker_environment_pre: dict[str, Any] | None = None
    docker_environment_post: dict[str, Any] | None = None
    try:
        journal.append(
            "ExecutionClaimed",
            {
                "candidate_id": candidate_id,
                "authorized_action_hash": proposed_action_hash,
                "fresh_successor_run_count": 1,
                "automatic_retry_count": 0,
            },
        )
        runner = _new_runner()
        active_stage = "docker-routing-environment"
        docker_environment_pre = _docker_environment_boundary()
        docker, docker_pre = _verified_docker_path(docker_path or _docker_path())
        active_stage = "image-identity"
        image_result = _invoke_execution(
            runner,
            _image_id_command(docker),
            timeout_seconds=30,
        )
        _require(
            image_result.returncode == 0 and image_result.stderr == b"",
            "execution image inspect failed",
        )
        _require(
            image_result.stdout == (IMAGE_ID + "\n").encode("ascii"),
            "execution image identity differs",
        )
        journal.append(
            "ImageIdentityVerified",
            {
                "immutable_image_id": IMAGE_ID,
                "docker_cli_binding": docker_pre,
                "docker_environment": docker_environment_pre,
            },
        )
        active_stage = "preexisting-container-inventory"
        preexisting = _invoke_execution(
            runner,
            _inventory_command(docker, f"label={MANAGED_LABEL}"),
            timeout_seconds=20,
        )
        _require(
            _parse_inventory(preexisting, label="execution preexisting label") == [],
            "preexisting D-121 execution container found",
        )
        for source in SOURCE_PLAN:
            active_stage = f"session:{source['source_id']}"
            journal.append(
                "IsolationSessionStarted",
                {
                    "source_id": source["source_id"],
                    "probe_source_sha256": source["probe_source_sha256"],
                },
            )
            evidence, primary_error, cleanup, cleanup_error = _execute_successor_session(
                repository=repo,
                docker=docker,
                runner=runner,
                source=source,
            )
            if primary_error is not None or cleanup_error is not None or evidence is None:
                journal.append(
                    "ExecutionFailed",
                    {
                        "source_id": source["source_id"],
                        "primary_status": (
                            "FAILED" if primary_error is not None else "PROBE_RESULT_VALIDATED"
                        ),
                        "primary_error_class": (
                            type(primary_error).__name__ if primary_error is not None else None
                        ),
                        "cleanup_status": ("FAILED" if cleanup_error is not None else "VERIFIED"),
                        "cleanup_error_class": (
                            type(cleanup_error).__name__ if cleanup_error is not None else None
                        ),
                        "automatic_retry_count": 0,
                    },
                )
                failure_event_appended = True
                if primary_error is not None:
                    if cleanup_error is not None:
                        primary_error.add_note(
                            f"cleanup_error={type(cleanup_error).__name__}:{cleanup_error}"
                        )
                    raise primary_error
                raise cleanup_error or D121ExecutionError("session evidence missing")
            journal.append(
                "ProbeResultValidated",
                {
                    "source_id": source["source_id"],
                    "result_sha256": sha256_bytes(_canonical_bytes(evidence["result"])),
                },
            )
            journal.append(
                "ContainerRemovalVerified",
                {
                    "source_id": source["source_id"],
                    "cleanup_sha256": sha256_bytes(_canonical_bytes(cleanup)),
                },
            )
            journal.append(
                "IsolationSessionCompleted",
                {
                    "source_id": source["source_id"],
                    "session_evidence_sha256": sha256_bytes(_canonical_bytes(evidence)),
                },
            )
            sessions.append(evidence)
        _, docker_post = _verified_docker_path(docker)
        _require(docker_post == docker_pre, "Docker CLI changed during execution")
        _require(
            _exact_file_state(repo, PROTECTED_FILE_SPECS) == protected_pre,
            "protected inputs changed during execution",
        )
        _require(
            _implementation_state(repo) == implementation_pre,
            "implementation changed during execution",
        )
        docker_environment_post = _docker_environment_boundary()
        _require(
            docker_environment_post == docker_environment_pre,
            "Docker routing environment changed during execution",
        )
        active_stage = "execution-completion"
        journal.append(
            "ExecutionCompleted",
            {
                "session_count": 2,
                "source_order": [row["source_id"] for row in SOURCE_PLAN],
                "residual_container_count": 0,
            },
        )
    except BaseException as exc:  # noqa: BLE001 - seal every failure without masking it
        primary_failure = exc
        if not failure_event_appended:
            try:
                journal.append(
                    "ExecutionFailed",
                    {
                        "failure_stage": active_stage,
                        "primary_status": "FAILED",
                        "primary_error_class": type(exc).__name__,
                        "cleanup_status": "NOT_APPLICABLE_OR_RECORDED_IN_SESSION",
                        "cleanup_error_class": None,
                        "automatic_retry_count": 0,
                    },
                )
                failure_event_appended = True
            except BaseException as append_exc:  # noqa: BLE001
                exc.add_note(
                    f"execution_failed_event_append_error={type(append_exc).__name__}:{append_exc}"
                )
        raise
    finally:
        try:
            journal.close()
        except BaseException as close_exc:  # noqa: BLE001
            if primary_failure is not None:
                primary_failure.add_note(
                    f"journal_close_error={type(close_exc).__name__}:{close_exc}"
                )
            else:
                raise
    _require(docker_environment_pre is not None, "execution Docker environment missing")
    _require(docker_environment_post is not None, "execution Docker post-environment missing")
    _, journal_binding = _read_execution_journal(repo)
    evidence = _envelope(
        schema_version="hash-only-isolation-successor-evidence-d121-v1",
        id_field="evidence_id",
        id_prefix="d121isolationevidence_",
        body=_execution_evidence_body(
            recorded_at=_now(),
            execution_receipt_binding=receipt_binding,
            preparation_candidate_binding=candidate_binding,
            proposed_action_hash=proposed_action_hash,
            journal_binding=journal_binding,
            sessions=sessions,
            protected_state=protected_pre,
            implementation_state=implementation_pre,
            docker_environment_pre=docker_environment_pre,
            docker_environment_post=docker_environment_post,
        ),
    )
    evidence_content = _write_new(repo, EXECUTION_OUTPUT_PATHS["evidence"], evidence)
    evidence_binding = _binding(
        EXECUTION_OUTPUT_PATHS["evidence"],
        evidence_content,
        evidence_id=evidence["evidence_id"],
        semantic_body_hash=evidence["semantic_body_hash"],
    )
    gate = _envelope(
        schema_version="hash-only-isolation-successor-completion-gate-d121-v1",
        id_field="gate_id",
        id_prefix="d121execution_",
        body=_execution_gate_body(
            recorded_at=_now(),
            candidate_binding=candidate_binding,
            receipt_binding=receipt_binding,
            journal_binding=journal_binding,
            evidence_binding=evidence_binding,
        ),
    )
    _write_new(repo, EXECUTION_OUTPUT_PATHS["completion_gate"], gate)
    _require(
        preparation_contents == _read_preparation_outputs(repo)[1],
        "preparation artifacts changed during execution",
    )
    return validate_d121_execution(repository=repo)


def validate_d121_execution(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Validate a later, separately approved completed successor run."""

    repo = _repo_root(repository)
    _require(_execution_output_state(repo) == "complete", "D-121 execution is not complete")
    prepared = _validate_d121_preparation(
        repository=repo,
        allow_complete_execution=True,
    )
    preparation_values, preparation_contents = _read_preparation_outputs(repo)
    candidate = preparation_values["execution_candidate"]
    candidate_content = preparation_contents["execution_candidate"]
    candidate_binding = _binding(
        PREPARATION_OUTPUT_PATHS["execution_candidate"],
        candidate_content,
        candidate_id=candidate["candidate_id"],
        semantic_body_hash=candidate["semantic_body_hash"],
    )
    proposed_action_hash = candidate["semantic_body"]["proposed_action_hash"]
    protected_state = _exact_file_state(repo, PROTECTED_FILE_SPECS)
    implementation_state = _implementation_state(repo)
    specs = {
        "approval_receipt": (
            EXECUTION_OUTPUT_PATHS["approval_receipt"],
            "hash-only-isolation-successor-execution-approval-receipt-d121-v1",
            "receipt_id",
            "d121executionapproval_",
        ),
        "evidence": (
            EXECUTION_OUTPUT_PATHS["evidence"],
            "hash-only-isolation-successor-evidence-d121-v1",
            "evidence_id",
            "d121isolationevidence_",
        ),
        "completion_gate": (
            EXECUTION_OUTPUT_PATHS["completion_gate"],
            "hash-only-isolation-successor-completion-gate-d121-v1",
            "gate_id",
            "d121execution_",
        ),
    }
    values: dict[str, dict[str, Any]] = {}
    contents: dict[str, bytes] = {}
    for key, (relative, schema, id_field, prefix) in specs.items():
        content = _read_stable(
            _safe_path(repo, relative, must_exist=True, label=f"execution {key}"),
            label=f"execution {key}",
        )
        value = _parse_json(content, label=f"execution {key}")
        _require(
            set(value) == {"schema_version", id_field, "semantic_body_hash", "semantic_body"},
            f"execution {key} root fields differ",
        )
        _require(value["schema_version"] == schema, f"execution {key} schema differs")
        _require(isinstance(value["semantic_body"], dict), f"execution {key} body missing")
        body_hash = sha256_bytes(_canonical_bytes(value["semantic_body"]))
        _require(value["semantic_body_hash"] == body_hash, f"execution {key} body SHA differs")
        _require(
            value[id_field] == prefix + body_hash.removeprefix("sha256:"),
            f"execution {key} ID differs",
        )
        values[key] = value
        contents[key] = content
    rows, journal_binding = _read_execution_journal(repo)
    expected_events = [
        "ExecutionClaimed",
        "ImageIdentityVerified",
        "IsolationSessionStarted",
        "ProbeResultValidated",
        "ContainerRemovalVerified",
        "IsolationSessionCompleted",
        "IsolationSessionStarted",
        "ProbeResultValidated",
        "ContainerRemovalVerified",
        "IsolationSessionCompleted",
        "ExecutionCompleted",
    ]
    _require([row["event"] for row in rows] == expected_events, "execution journal events differ")
    evidence_body = values["evidence"]["semantic_body"]
    sessions = evidence_body.get("sessions")
    _require(
        isinstance(sessions, list) and len(sessions) == len(SOURCE_PLAN),
        "execution sessions differ",
    )
    for session, source in zip(sessions, SOURCE_PLAN, strict=True):
        _require(isinstance(session, dict), "execution session root differs")
        _validate_execution_session(session, source=source, repository=repo)
    _require(
        len({session["container_id"] for session in sessions}) == len(sessions),
        "execution session container IDs are not distinct",
    )

    expected_cli = {
        "file_name": "docker.exe",
        "file_bytes": DOCKER_CLI_BYTES,
        "file_sha256": DOCKER_CLI_SHA256,
        "runner_kind": "subprocess-exact-argv-no-shell-forced-local-docker-host",
    }
    expected_environment = _docker_environment_contract()
    _require(
        evidence_body.get("docker_environment_pre")
        == evidence_body.get("docker_environment_post")
        == expected_environment,
        "execution Docker environment evidence differs",
    )
    expected_data: list[dict[str, Any]] = [
        {
            "candidate_id": candidate["candidate_id"],
            "authorized_action_hash": proposed_action_hash,
            "fresh_successor_run_count": 1,
            "automatic_retry_count": 0,
        },
        {
            "immutable_image_id": IMAGE_ID,
            "docker_cli_binding": expected_cli,
            "docker_environment": expected_environment,
        },
    ]
    for source, session in zip(SOURCE_PLAN, sessions, strict=True):
        expected_data.extend(
            [
                {
                    "source_id": source["source_id"],
                    "probe_source_sha256": source["probe_source_sha256"],
                },
                {
                    "source_id": source["source_id"],
                    "result_sha256": sha256_bytes(_canonical_bytes(session["result"])),
                },
                {
                    "source_id": source["source_id"],
                    "cleanup_sha256": sha256_bytes(_canonical_bytes(session["cleanup"])),
                },
                {
                    "source_id": source["source_id"],
                    "session_evidence_sha256": sha256_bytes(_canonical_bytes(session)),
                },
            ]
        )
    expected_data.append(
        {
            "session_count": len(SOURCE_PLAN),
            "source_order": [row["source_id"] for row in SOURCE_PLAN],
            "residual_container_count": 0,
        }
    )
    _require(len(expected_data) == len(rows), "execution journal data count differs")
    for row, event, data in zip(rows, expected_events, expected_data, strict=True):
        _require(row["event"] == event, "execution journal event differs")
        _require(
            _canonical_bytes(row["data"]) == _canonical_bytes(data),
            "execution journal event data differs",
        )
    parsed_times = [_parse_time(row["recorded_at"], label="execution journal") for row in rows]
    _require(
        all(left <= right for left, right in zip(parsed_times, parsed_times[1:], strict=False)),
        "execution journal chronology differs",
    )

    receipt_body = values["approval_receipt"]["semantic_body"]
    receipt_time = receipt_body.get("approval_recorded_at")
    expected_receipt = _envelope(
        schema_version="hash-only-isolation-successor-execution-approval-receipt-d121-v1",
        id_field="receipt_id",
        id_prefix="d121executionapproval_",
        body=_execution_receipt_body(
            recorded_at=receipt_time,
            candidate_binding=candidate_binding,
            proposed_action_hash=proposed_action_hash,
            implementation_state=implementation_state,
        ),
    )
    _require(
        contents["approval_receipt"] == _pretty_bytes(expected_receipt),
        "execution approval receipt expected payload differs",
    )
    receipt_binding = _binding(
        EXECUTION_OUTPUT_PATHS["approval_receipt"],
        contents["approval_receipt"],
        receipt_id=values["approval_receipt"]["receipt_id"],
        semantic_body_hash=values["approval_receipt"]["semantic_body_hash"],
    )
    evidence_time = evidence_body.get("recorded_at")
    expected_evidence = _envelope(
        schema_version="hash-only-isolation-successor-evidence-d121-v1",
        id_field="evidence_id",
        id_prefix="d121isolationevidence_",
        body=_execution_evidence_body(
            recorded_at=evidence_time,
            execution_receipt_binding=receipt_binding,
            preparation_candidate_binding=candidate_binding,
            proposed_action_hash=proposed_action_hash,
            journal_binding=journal_binding,
            sessions=sessions,
            protected_state=protected_state,
            implementation_state=implementation_state,
            docker_environment_pre=expected_environment,
            docker_environment_post=expected_environment,
        ),
    )
    _require(
        contents["evidence"] == _pretty_bytes(expected_evidence),
        "execution evidence expected payload differs",
    )
    evidence_binding = _binding(
        EXECUTION_OUTPUT_PATHS["evidence"],
        contents["evidence"],
        evidence_id=values["evidence"]["evidence_id"],
        semantic_body_hash=values["evidence"]["semantic_body_hash"],
    )
    gate_body = values["completion_gate"]["semantic_body"]
    gate_time = gate_body.get("recorded_at")
    expected_gate = _envelope(
        schema_version="hash-only-isolation-successor-completion-gate-d121-v1",
        id_field="gate_id",
        id_prefix="d121execution_",
        body=_execution_gate_body(
            recorded_at=gate_time,
            candidate_binding=candidate_binding,
            receipt_binding=receipt_binding,
            journal_binding=journal_binding,
            evidence_binding=evidence_binding,
        ),
    )
    _require(
        contents["completion_gate"] == _pretty_bytes(expected_gate),
        "execution completion gate expected payload differs",
    )
    preparation_gate_time = _parse_time(
        preparation_values["source_gate"]["semantic_body"]["recorded_at"],
        label="preparation source gate",
    )
    receipt_parsed = _parse_time(receipt_time, label="execution approval receipt")
    evidence_parsed = _parse_time(evidence_time, label="execution evidence")
    gate_parsed = _parse_time(gate_time, label="execution completion gate")
    _require(
        preparation_gate_time <= receipt_parsed <= parsed_times[0]
        and parsed_times[-1] <= evidence_parsed <= gate_parsed,
        "execution artifact chronology differs",
    )

    _require(
        _exact_file_state(repo, PROTECTED_FILE_SPECS) == protected_state,
        "protected inputs changed during execution validation",
    )
    _require(
        _implementation_state(repo) == implementation_state,
        "implementation changed during execution validation",
    )
    _require_d119_outputs_absent(repo)
    reread_preparation_values, reread_preparation_contents = _read_preparation_outputs(repo)
    _require(
        reread_preparation_values == preparation_values
        and reread_preparation_contents == preparation_contents,
        "preparation artifacts changed during execution validation",
    )
    reread_values: dict[str, dict[str, Any]] = {}
    reread_contents: dict[str, bytes] = {}
    for key, (relative, _schema, _id_field, _prefix) in specs.items():
        content = _read_stable(
            _safe_path(repo, relative, must_exist=True, label=f"execution {key}"),
            label=f"execution {key}",
        )
        reread_contents[key] = content
        reread_values[key] = _parse_json(content, label=f"execution {key}")
    _require(
        reread_values == values and reread_contents == contents,
        "execution artifacts changed during validation",
    )
    reread_rows, reread_journal_binding = _read_execution_journal(repo)
    _require(
        reread_rows == rows and reread_journal_binding == journal_binding,
        "execution journal changed during validation",
    )
    return {
        "status": "D121_FRESH_SUCCESSOR_RUN_COMPLETED",
        "preparation_candidate_id": prepared["candidate_id"],
        "execution_gate_id": values["completion_gate"]["gate_id"],
        "execution_gate_file_sha256": sha256_bytes(contents["completion_gate"]),
        "journal_record_count": len(rows),
        "session_count": 2,
        "hash_only_isolation_profile_verified": True,
        "trusted_cutoff_anchor_verified": False,
        "record_projection_isolation_verified": False,
        "independent": False,
        "retrieval_agent_and_core_authorized": False,
    }


__all__ = [
    "D121ExecutionError",
    "D121PreparationError",
    "prepare_d121_execution_candidate",
    "validate_d121_execution",
    "validate_d121_preparation",
]
