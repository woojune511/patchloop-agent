"""Approval-gated PDM-only Docker qualification successor v6.

This append-only successor preserves consumed v5, reuses its exact qualifying
AnyIO pair, and schedules only the revised PDM public check on immutable base
and trusted-reference trees. PDM qualifies only when base reaches one exact
allowlisted public assertion and reference passes. No agent, evaluator,
provider or network entrypoint is used.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from patchloop.errors import ContractError
from patchloop.sandbox import DockerSandbox, SandboxResult
from patchloop.sandbox.runner import registered_check_execution_policy
from patchloop.task_loader import load_task_package
from patchloop.util import ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "public-behavior-check-qualification-candidate-v6"
CANDIDATE_ID = "pdm-anyio-public-behavior-check-qualification-20260822-r6"
CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-anyio-public-behavior-check-qualification-candidate-v6.json"
)
APPROVAL_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-anyio-public-behavior-check-qualification-approval-v6.json"
)
ATTEMPT_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-anyio-public-behavior-check-qualification-attempt-v6.json"
)
RESULT_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-anyio-public-behavior-check-qualification-result-v6.json"
)
PREDECESSOR_CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-anyio-public-behavior-check-qualification-candidate-v5.json"
)
PREDECESSOR_RESULT_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-anyio-public-behavior-check-qualification-result-v5.json"
)
PREDECESSOR_EXECUTION_HASH = (
    "sha256:f7b0159d622ee6329db6560ab253d117187e6a05a5e7bb630ba325588eb211b3"
)
PREDECESSOR_CANDIDATE_FILE_SHA256 = (
    "sha256:d63beb7bd71cb610d351d01eeef27b98dc73d57d5c9aec4cb5e34a48db3be9f9"
)
PREDECESSOR_RESULT_FILE_SHA256 = (
    "sha256:57ac80b98f26970aba4927157c91eba6964a20b9326cca5470bfa28b4a5b54e4"
)
DOCKER_CONTEXT = "desktop-linux"
DOCKER_ENDPOINT = "npipe:////./pipe/dockerDesktopLinuxEngine"
APPROVAL_TEMPLATE = (
    "execution hash {execution_hash}에 대해 PDM public behavior targeted-check qualification "
    "successor-v6 2행을 승인합니다. 고정된 로컬 PDM 이미지의 identity inspect 1회와 --pull never, "
    "--network none, read-only workspace로 base/reference 각 1회씩 총 2개의 Docker 컨테이너 "
    "실행을 승인합니다. 이미지 pull/build/tag/remove/prune, "
    "agent/evaluator/provider 호출, 네트워크와 비용 발생은 승인하지 않습니다."
)

SOURCE_PATHS = (
    "patchloop/evals/public_behavior_check_qualification_v6.py",
    "patchloop/sandbox/runner.py",
    "patchloop/contracts.py",
    "patchloop/task_loader.py",
    "patchloop/util.py",
    "patchloop/errors.py",
    "scripts/run_public_behavior_check_qualification_v6.py",
)

TASK_SPECS = (
    {
        "task_path": "fixtures/task-packages/pdm-ignore-active-venv-resolution-v5",
        "task_id": "pdm-ignore-active-venv-resolution",
        "task_version": 5,
        "schedule": True,
        "check_id": "public-ignore-active-venv-resolution",
        "seed_workspace": (".patchloop/workspaces/run_rapid_v6_5ae158b3ed65_01/repo"),
        "target_path": "src/pdm/project/core.py",
    },
    {
        "task_path": "fixtures/task-packages/anyio-interrupt-runner-cleanup-v4",
        "task_id": "anyio-interrupt-runner-cleanup",
        "task_version": 4,
        "schedule": False,
        "check_id": "public-interrupt-runner-lifecycle",
        "seed_workspace": (".patchloop/workspaces/run_rapid_v6_5ae158b3ed65_03/repo"),
        "target_path": "src/anyio/_backends/_asyncio.py",
    },
)
PUBLIC_CASE_PATTERN = re.compile(r"PUBLIC_CASE:(?:pdm|anyio):[a-z0-9-]+(?::[a-z0-9-]+)?")
PDM_CASE_IDS = (
    "false-unset",
    "false-empty",
    "false-zero",
    "false-false",
    "false-no",
    "conda-false-zero",
    "exact-active-sibling",
    "conda-other",
    "create-fallback",
)
PUBLIC_CASE_ALLOWLIST = {
    "pdm-ignore-active-venv-resolution": [
        f"PUBLIC_CASE:pdm:{case_id}:{failure}"
        for case_id in PDM_CASE_IDS
        for failure in ("no-python", "wrong-path")
    ],
    "anyio-interrupt-runner-cleanup": [
        "PUBLIC_CASE:anyio:interrupt-timeout",
        "PUBLIC_CASE:anyio:interrupt-not-propagated",
        "PUBLIC_CASE:anyio:test-resumed",
        "PUBLIC_CASE:anyio:fixture-cleanup-count",
        "PUBLIC_CASE:anyio:outcome-status",
        "PUBLIC_CASE:anyio:outcome-events",
    ],
}


class PublicBehaviorCheckQualificationError(ContractError):
    """The candidate, approval, local source, or one-use result differs."""


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _binding(root: Path, relative: str | Path) -> dict[str, Any]:
    path = ensure_within(root, Path(relative).as_posix())
    if path.is_symlink() or not path.is_file():
        raise PublicBehaviorCheckQualificationError(
            f"required qualification file is unavailable: {relative}"
        )
    raw = path.read_bytes()
    result: dict[str, Any] = {
        "path": path.relative_to(root).as_posix(),
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }
    if path.suffix == ".json":
        try:
            parsed = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, dict) and isinstance(parsed.get("content_hash"), str):
            result["content_hash"] = parsed["content_hash"]
    return result


def _executable_binding(name: str) -> dict[str, Any]:
    selected = DockerSandbox.cli_path() if name == "docker" else shutil.which(name)
    if selected is None:
        raise PublicBehaviorCheckQualificationError(f"{name} CLI is unavailable")
    path = Path(selected).resolve()
    if not path.is_file():
        raise PublicBehaviorCheckQualificationError(f"{name} CLI is unavailable")
    raw = path.read_bytes()
    return {
        "resolved_path": str(path),
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }


def _docker_context_binding() -> dict[str, str]:
    if os.environ.get("DOCKER_HOST") or os.environ.get("DOCKER_CONTEXT"):
        raise PublicBehaviorCheckQualificationError(
            "Docker endpoint environment override is present"
        )
    docker_root = Path.home() / ".docker"
    config_path = docker_root / "config.json"
    if not config_path.is_file():
        raise PublicBehaviorCheckQualificationError("Docker client config is unavailable")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicBehaviorCheckQualificationError("Docker client config is invalid") from exc
    if config.get("currentContext") != DOCKER_CONTEXT:
        raise PublicBehaviorCheckQualificationError("Docker current context differs")
    endpoints: list[str] = []
    for path in (docker_root / "contexts" / "meta").glob("*/meta.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if value.get("Name") == DOCKER_CONTEXT:
            endpoint = ((value.get("Endpoints") or {}).get("docker") or {}).get("Host")
            if isinstance(endpoint, str):
                endpoints.append(endpoint)
    if endpoints != [DOCKER_ENDPOINT]:
        raise PublicBehaviorCheckQualificationError("Docker local endpoint differs")
    return {"context": DOCKER_CONTEXT, "endpoint": DOCKER_ENDPOINT}


def _git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY"):
        environment.pop(key, None)
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def _safe_tar_members(raw: bytes, *, required_path: str) -> tuple[int, tuple[str, ...]]:
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
            members = archive.getmembers()
    except tarfile.TarError as exc:
        raise PublicBehaviorCheckQualificationError("base source archive is invalid") from exc
    names: list[str] = []
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or member.isdev():
            raise PublicBehaviorCheckQualificationError("base source archive is unsafe")
        if member.issym() or member.islnk():
            target = PurePosixPath(member.linkname)
            if target.is_absolute() or ".." in target.parts:
                raise PublicBehaviorCheckQualificationError("base source link is unsafe")
        names.append(member.name.rstrip("/"))
    if required_path not in names:
        raise PublicBehaviorCheckQualificationError(
            f"base source archive omits required path: {required_path}"
        )
    return len(members), tuple(names)


def _source_archive(
    root: Path,
    spec: dict[str, str],
    git_cli: dict[str, Any],
) -> tuple[bytes, dict[str, Any]]:
    workspace = ensure_within(root, spec["seed_workspace"])
    if workspace.is_symlink() or not (workspace / ".git").exists():
        raise PublicBehaviorCheckQualificationError(
            f"consumed local source workspace is unavailable: {spec['task_id']}"
        )
    git = git_cli["resolved_path"]
    environment = _git_environment()
    head = subprocess.run(
        [git, "-C", str(workspace), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        timeout=10,
        env=environment,
    )
    if head.returncode != 0:
        raise PublicBehaviorCheckQualificationError("local source HEAD is unavailable")
    actual_head = head.stdout.decode("ascii", errors="strict").strip()
    package = load_task_package(root / spec["task_path"])
    if actual_head != package.public.repository.base_commit:
        raise PublicBehaviorCheckQualificationError(
            f"local source commit differs: {spec['task_id']}"
        )
    archived = subprocess.run(
        [git, "-C", str(workspace), "archive", "--format=tar", actual_head],
        check=False,
        capture_output=True,
        timeout=60,
        env=environment,
    )
    if archived.returncode != 0 or archived.stderr:
        raise PublicBehaviorCheckQualificationError(
            f"local source archive failed: {spec['task_id']}"
        )
    count, names = _safe_tar_members(archived.stdout, required_path=spec["target_path"])
    return archived.stdout, {
        "provenance": "consumed-rapid-v6-local-git-object",
        "seed_workspace": spec["seed_workspace"],
        "base_commit": actual_head,
        "archive_format": "git-archive-tar-v1",
        "archive_bytes": len(archived.stdout),
        "archive_sha256": sha256_bytes(archived.stdout),
        "archive_member_count": count,
        "target_path_present": spec["target_path"] in names,
    }


def _extract_archive(raw: bytes, destination: Path, *, required_path: str) -> None:
    _safe_tar_members(raw, required_path=required_path)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
            archive.extractall(destination, filter="data")
    except (OSError, tarfile.TarError) as exc:
        raise PublicBehaviorCheckQualificationError("base source extraction failed") from exc


def _apply_reference_patch(
    workspace: Path,
    patch_path: Path,
    git_cli: dict[str, Any],
) -> None:
    command = [
        git_cli["resolved_path"],
        "-C",
        str(workspace),
        "apply",
        "--whitespace=nowarn",
        str(patch_path),
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        timeout=30,
        env=_git_environment(),
    )
    if completed.returncode != 0:
        raise PublicBehaviorCheckQualificationError("trusted reference patch did not apply")


def _validate_reference_patch_applies(
    raw: bytes,
    *,
    required_path: str,
    patch_path: Path,
    git_cli: dict[str, Any],
) -> None:
    with tempfile.TemporaryDirectory(prefix="patchloop-public-check-") as selected:
        workspace = Path(selected) / "repo"
        _extract_archive(raw, workspace, required_path=required_path)
        _apply_reference_patch(workspace, patch_path, git_cli)


def _package_inventory(task_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(task_dir.rglob("*")):
        if path.is_symlink():
            raise PublicBehaviorCheckQualificationError("task package contains a link")
        if not path.is_file():
            continue
        raw = path.read_bytes()
        rows.append(
            {
                "path": path.relative_to(task_dir).as_posix(),
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
            }
        )
    if not rows:
        raise PublicBehaviorCheckQualificationError("task package is empty")
    return {"file_count": len(rows), "inventory_hash": sha256_json(rows)}


def _task_binding(
    root: Path,
    spec: dict[str, Any],
    git_cli: dict[str, Any],
) -> tuple[dict[str, Any], bytes]:
    task_dir = ensure_within(root, spec["task_path"])
    package = load_task_package(task_dir)
    if (
        package.public.task_id != spec["task_id"]
        or package.public.task_version != spec["task_version"]
        or package.environment is None
        or not package.public.visible_checks
        or package.public.visible_checks[0].id != spec["check_id"]
    ):
        raise PublicBehaviorCheckQualificationError("public check task identity differs")
    check = package.public.visible_checks[0]
    archive, archive_binding = _source_archive(root, spec, git_cli)
    patch_path = ensure_within(task_dir, package.private.reference_patch.path)
    _validate_reference_patch_applies(
        archive,
        required_path=spec["target_path"],
        patch_path=patch_path,
        git_cli=git_cli,
    )
    workdir = "/workspace"
    if check.working_directory != ".":
        workdir = f"/workspace/{check.working_directory}"
    policy = registered_check_execution_policy(
        image=package.environment.evaluator_image,
        working_directory=workdir,
        timeout_seconds=check.timeout_seconds,
        output_limit_bytes=check.output_limit_bytes,
    )
    inventory = _package_inventory(task_dir)
    return (
        {
            "task_path": spec["task_path"],
            "task_id": package.public.task_id,
            "task_version": package.public.task_version,
            "base_commit": package.public.repository.base_commit,
            "public_spec_hash": package.public_spec_hash,
            "private_spec_hash": package.private_spec_hash,
            "package_file_count": inventory["file_count"],
            "package_inventory_hash": inventory["inventory_hash"],
            "image": package.environment.evaluator_image,
            "image_digest": package.environment.image_digest,
            "targeted_check_id": check.id,
            "targeted_check_hash": sha256_json(check.model_dump(mode="json")),
            "targeted_check_command_hash": sha256_json(list(check.command)),
            "requested_execution_policy": policy,
            "docker_pull_policy": "never",
            "reference_patch": _binding(root, patch_path.relative_to(root)),
            "base_source": archive_binding,
            "expected_base_observation": "public-assertion-failure",
            "expected_reference_observation": "pass",
        },
        archive,
    )


def _retained_anyio_qualification(
    predecessor_result: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:
    identities = [
        item
        for item in predecessor_result.get("image_identity_observations", [])
        if item.get("task_id") == task["task_id"]
    ]
    rows = [
        item
        for item in predecessor_result.get("row_observations", [])
        if item.get("task_id") == task["task_id"]
    ]
    if len(identities) != 1 or len(rows) != 2:
        raise PublicBehaviorCheckQualificationError("retained AnyIO evidence is incomplete")
    identity = identities[0]
    base, reference = rows
    shared_row_checks = all(
        row.get("task_version") == task["task_version"]
        and row.get("targeted_check_id") == task["targeted_check_id"]
        and row.get("image_digest") == task["image_digest"]
        and row.get("base_source_archive_sha256") == task["base_source"]["archive_sha256"]
        and row.get("reference_patch_sha256") == task["reference_patch"]["file_sha256"]
        and row.get("expected_observation_matched") is True
        and row.get("raw_output_persisted") is False
        for row in rows
    )
    if (
        predecessor_result.get("execution_error_class") is not None
        or predecessor_result.get("docker_image_inspect_calls") != 2
        or predecessor_result.get("docker_container_run_attempts") != 4
        or predecessor_result.get("docker_container_run_completions") != 4
        or predecessor_result.get("image_pull_build_tag_remove_prune_calls") != 0
        or predecessor_result.get("agent_calls") != 0
        or predecessor_result.get("evaluator_calls") != 0
        or predecessor_result.get("provider_calls") != 0
        or predecessor_result.get("network_calls") != 0
        or predecessor_result.get("added_cost_usd") != 0
        or identity.get("matched") is not True
        or identity.get("requested_digest") != task["image_digest"]
        or not shared_row_checks
        or base.get("source_state") != "base"
        or base.get("observation") != "public-assertion-failure"
        or base.get("public_case_markers") != ["PUBLIC_CASE:anyio:test-resumed"]
        or reference.get("source_state") != "reference"
        or reference.get("observation") != "pass"
        or reference.get("exit_code") != 0
        or reference.get("public_case_markers") != []
    ):
        raise PublicBehaviorCheckQualificationError("retained AnyIO evidence differs")
    return {
        "schema_version": "retained-public-task-qualification-v1",
        "status": "QUALIFIED_FROM_CONSUMED_V5_ROWS",
        "task_id": task["task_id"],
        "task_version": task["task_version"],
        "image_digest": task["image_digest"],
        "image_identity_hash": sha256_json(identity),
        "base_row_hash": sha256_json(base),
        "reference_row_hash": sha256_json(reference),
        "raw_output_persisted": False,
    }


def _candidate_body(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    predecessor = _binding(root, PREDECESSOR_CANDIDATE_PATH)
    parsed = json.loads((root / PREDECESSOR_CANDIDATE_PATH).read_text(encoding="utf-8"))
    if (
        predecessor.get("file_sha256") != PREDECESSOR_CANDIDATE_FILE_SHA256
        or parsed.get("execution_hash") != PREDECESSOR_EXECUTION_HASH
    ):
        raise PublicBehaviorCheckQualificationError("v5 qualification candidate differs")
    predecessor_result_binding = _binding(root, PREDECESSOR_RESULT_PATH)
    predecessor_result = _load_json_artifact(root, PREDECESSOR_RESULT_PATH)
    if (
        predecessor_result_binding.get("file_sha256") != PREDECESSOR_RESULT_FILE_SHA256
        or predecessor_result.get("execution_hash") != PREDECESSOR_EXECUTION_HASH
        or predecessor_result.get("status") != "PUBLIC_BEHAVIOR_CHECKS_NOT_QUALIFIED"
    ):
        raise PublicBehaviorCheckQualificationError("v5 qualification result differs")
    docker_cli = _executable_binding("docker")
    git_cli = _executable_binding("git")
    context = _docker_context_binding()
    tasks: list[dict[str, Any]] = []
    for spec in TASK_SPECS:
        binding, _archive = _task_binding(root, spec, git_cli)
        tasks.append(binding)
    task_by_id = {item["task_id"]: item for item in tasks}
    retained_anyio = _retained_anyio_qualification(
        predecessor_result,
        task_by_id["anyio-interrupt-runner-cleanup"],
    )
    spec_by_id = {item["task_id"]: item for item in TASK_SPECS}
    schedule: list[dict[str, Any]] = []
    order = 0
    for task in tasks:
        if not spec_by_id[task["task_id"]]["schedule"]:
            continue
        for state in ("base", "reference"):
            order += 1
            row = {
                "order": order,
                "task_id": task["task_id"],
                "task_version": task["task_version"],
                "targeted_check_id": task["targeted_check_id"],
                "source_state": state,
                "expected_observation": task[f"expected_{state}_observation"],
                "image_digest": task["image_digest"],
                "base_source_archive_sha256": task["base_source"]["archive_sha256"],
                "reference_patch_sha256": task["reference_patch"]["file_sha256"],
            }
            schedule.append({**row, "schedule_row_id": sha256_json(row)})
    source_files = [_binding(root, path) for path in SOURCE_PATHS]
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": CANDIDATE_ID,
        "purpose": "pdm-public-behavior-check-qualification-with-retained-anyio",
        "official": False,
        "predecessor_candidate": predecessor,
        "predecessor_result": predecessor_result_binding,
        "predecessor_execution_hash": PREDECESSOR_EXECUTION_HASH,
        "retained_anyio_qualification": retained_anyio,
        "source_files": source_files,
        "source_inventory_hash": sha256_json(source_files),
        "docker_cli": docker_cli,
        "git_cli": git_cli,
        "docker_context": context,
        "docker_contract": {
            "image_identity_inspect_calls": 1,
            "container_run_calls": 2,
            "pull_policy": "never",
            "network": "none",
            "root_filesystem": "read_only",
            "workspace_mount": "read_only",
            "agent_calls": 0,
            "evaluator_calls": 0,
            "provider_calls": 0,
            "network_calls": 0,
            "added_cost_usd": 0,
        },
        "public_failure_projection": {
            "schema_version": "allowlisted-public-case-id-v1",
            "pattern": PUBLIC_CASE_PATTERN.pattern,
            "task_allowlists": PUBLIC_CASE_ALLOWLIST,
            "raw_output_persisted": False,
        },
        "task_bindings": tasks,
        "schedule": schedule,
        "schedule_hash": sha256_json(schedule),
    }


def build_candidate(repository: str | Path = ".") -> dict[str, Any]:
    body = _candidate_body(repository)
    candidate = {
        **body,
        "execution_hash": sha256_json(body),
        "source_qualified": True,
        "execution_authorized": False,
        "approval_required": True,
        "docker_calls_made": 0,
        "provider_calls_made": 0,
        "added_cost_usd": 0,
        "approval_message_template": APPROVAL_TEMPLATE,
    }
    return {**candidate, "content_hash": sha256_json(candidate)}


def _validate_candidate(candidate: dict[str, Any]) -> None:
    if not isinstance(candidate, dict):
        raise PublicBehaviorCheckQualificationError("candidate is not an object")
    content = {key: value for key, value in candidate.items() if key != "content_hash"}
    body = {
        key: value
        for key, value in candidate.items()
        if key
        not in {
            "execution_hash",
            "source_qualified",
            "execution_authorized",
            "approval_required",
            "docker_calls_made",
            "provider_calls_made",
            "added_cost_usd",
            "approval_message_template",
            "content_hash",
        }
    }
    schedule = candidate.get("schedule")
    if (
        candidate.get("schema_version") != SCHEMA_VERSION
        or candidate.get("candidate_id") != CANDIDATE_ID
        or candidate.get("official") is not False
        or candidate.get("predecessor_execution_hash") != PREDECESSOR_EXECUTION_HASH
        or candidate.get("retained_anyio_qualification", {}).get("status")
        != "QUALIFIED_FROM_CONSUMED_V5_ROWS"
        or not isinstance(schedule, list)
        or len(schedule) != 2
        or candidate.get("schedule_hash") != sha256_json(schedule)
        or candidate.get("execution_hash") != sha256_json(body)
        or candidate.get("source_qualified") is not True
        or candidate.get("execution_authorized") is not False
        or candidate.get("approval_required") is not True
        or candidate.get("docker_calls_made") != 0
        or candidate.get("provider_calls_made") != 0
        or candidate.get("added_cost_usd") != 0
        or candidate.get("approval_message_template") != APPROVAL_TEMPLATE
        or candidate.get("content_hash") != sha256_json(content)
    ):
        raise PublicBehaviorCheckQualificationError("candidate identity differs")


def materialize_candidate(
    repository: str | Path = ".",
    output_path: str | Path = CANDIDATE_PATH,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    output = ensure_within(root, Path(output_path).as_posix())
    current = build_candidate(root)
    raw = _json_bytes(current)
    if output.exists():
        if output.is_symlink() or output.read_bytes() != raw:
            raise PublicBehaviorCheckQualificationError("append-only candidate differs")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    return load_candidate(root, output_path)


def load_candidate(
    repository: str | Path = ".",
    candidate_path: str | Path = CANDIDATE_PATH,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    path = ensure_within(root, Path(candidate_path).as_posix())
    if path.is_symlink() or not path.is_file():
        raise PublicBehaviorCheckQualificationError("candidate is unavailable")
    try:
        candidate = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicBehaviorCheckQualificationError("candidate is invalid") from exc
    _validate_candidate(candidate)
    if _json_bytes(candidate) != path.read_bytes() or candidate != build_candidate(root):
        raise PublicBehaviorCheckQualificationError("candidate bytes or source drifted")
    return candidate


def expected_approval_message(candidate: dict[str, Any]) -> str:
    _validate_candidate(candidate)
    return APPROVAL_TEMPLATE.format(execution_hash=candidate["execution_hash"])


def _write_once(path: Path, value: dict[str, Any]) -> None:
    raw = _json_bytes(value)
    if path.exists():
        if path.is_symlink() or path.read_bytes() != raw:
            raise PublicBehaviorCheckQualificationError(
                f"append-only artifact differs: {path.name}"
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def materialize_approval(repository: str | Path, user_message: str) -> dict[str, Any]:
    root = Path(repository).resolve()
    candidate = load_candidate(root)
    if user_message != expected_approval_message(candidate):
        raise PublicBehaviorCheckQualificationError("exact approval message differs")
    body = {
        "schema_version": "public-behavior-check-qualification-approval-v6",
        "recorded_at": _now(),
        "status": "EXACT_DOCKER_QUALIFICATION_APPROVED_ONCE",
        "candidate": _binding(root, CANDIDATE_PATH),
        "execution_hash": candidate["execution_hash"],
        "user_message_sha256": sha256_bytes(user_message.encode()),
        "approved_docker_calls": 3,
        "approved_container_runs": 2,
        "image_pull_build_tag_remove_prune_authorized": False,
        "agent_evaluator_provider_network_cost_authorized": False,
    }
    approval = {**body, "content_hash": sha256_json(body)}
    _write_once(root / APPROVAL_PATH, approval)
    return approval


def _load_json_artifact(root: Path, path: Path) -> dict[str, Any]:
    selected = ensure_within(root, path.as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise PublicBehaviorCheckQualificationError(f"artifact is unavailable: {path}")
    try:
        value = json.loads(selected.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicBehaviorCheckQualificationError(f"artifact is invalid: {path}") from exc
    if not isinstance(value, dict) or _json_bytes(value) != selected.read_bytes():
        raise PublicBehaviorCheckQualificationError(f"artifact is noncanonical: {path}")
    content = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(content):
        raise PublicBehaviorCheckQualificationError(f"artifact hash differs: {path}")
    return value


def _text_evidence(value: str) -> dict[str, Any]:
    raw = value.encode("utf-8")
    return {"bounded_bytes": len(raw), "bounded_sha256": sha256_bytes(raw)}


def _result_projection(
    row: dict[str, Any],
    result: SandboxResult,
) -> dict[str, Any]:
    assertion = "AssertionError" in result.stderr
    public_case_markers = sorted(set(PUBLIC_CASE_PATTERN.findall(result.stderr)))
    allowed_markers = PUBLIC_CASE_ALLOWLIST[row["task_id"]]
    if row["source_state"] == "base":
        matched = (
            not result.timed_out
            and not result.truncated
            and result.exit_code not in (None, 0)
            and assertion
            and len(public_case_markers) == 1
            and public_case_markers[0] in allowed_markers
        )
        observation = "public-assertion-failure" if matched else "unexpected-base-result"
    else:
        matched = result.passed and not result.truncated
        observation = "pass" if matched else "unexpected-reference-result"
    return {
        **row,
        "observation": observation,
        "expected_observation_matched": matched,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "truncated": result.truncated,
        "original_output_bytes": result.original_output_bytes,
        "public_assertion_marker_observed": assertion,
        "public_case_markers": public_case_markers,
        "stdout": _text_evidence(result.stdout),
        "stderr": _text_evidence(result.stderr),
        "requested_execution_policy": result.execution_policy,
        "raw_output_persisted": False,
    }


ArchiveProvider = Callable[[Path, dict[str, Any], dict[str, Any]], tuple[bytes, dict[str, Any]]]


def observe_candidate(
    repository: str | Path,
    candidate: dict[str, Any],
    *,
    archive_provider: ArchiveProvider = _source_archive,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    task_by_id = {item["task_id"]: item for item in candidate["task_bindings"]}
    spec_by_id = {item["task_id"]: item for item in TASK_SPECS}
    scheduled_task_ids = {item["task_id"] for item in candidate["schedule"]}
    identities: list[dict[str, Any]] = []
    identity_ok = True
    observations: list[dict[str, Any]] = []
    execution_error: str | None = None
    inspect_calls = 0
    container_run_attempts = 0
    try:
        git_cli = _executable_binding("git")
        for task in candidate["task_bindings"]:
            if task["task_id"] not in scheduled_task_ids:
                continue
            inspect_calls += 1
            projection = None
            projection_error: str | None = None
            try:
                projection = DockerSandbox(task["image"]).image_identity_projection()
            except Exception as exc:  # the terminal must survive a Docker CLI failure
                projection_error = type(exc).__name__
            matched = (
                projection is not None and projection.verified_identity == task["image_digest"]
            )
            identity_ok = identity_ok and matched
            identities.append(
                {
                    "task_id": task["task_id"],
                    "requested_digest": task["image_digest"],
                    "matched": matched,
                    "config_id": projection.config_id if projection is not None else None,
                    "matched_repo_digest": (
                        projection.matched_repo_digest if projection is not None else None
                    ),
                    "error_class": projection_error,
                }
            )
        if identity_ok:
            archives: dict[str, bytes] = {}
            for task_id, spec in spec_by_id.items():
                if task_id not in scheduled_task_ids:
                    continue
                raw, binding = archive_provider(root, spec, git_cli)
                if binding != task_by_id[task_id]["base_source"]:
                    raise PublicBehaviorCheckQualificationError("base source archive drifted")
                archives[task_id] = raw
            with tempfile.TemporaryDirectory(prefix="patchloop-public-check-run-") as selected:
                staging = Path(selected)
                for row in candidate["schedule"]:
                    task = task_by_id[row["task_id"]]
                    spec = spec_by_id[row["task_id"]]
                    workspace = staging / f"{row['order']:02d}-{row['source_state']}"
                    _extract_archive(
                        archives[row["task_id"]],
                        workspace,
                        required_path=spec["target_path"],
                    )
                    if row["source_state"] == "reference":
                        patch = ensure_within(root, task["reference_patch"]["path"])
                        _apply_reference_patch(workspace, patch, git_cli)
                    package = load_task_package(root / task["task_path"])
                    check = package.public.visible_checks[0]
                    container_run_attempts += 1
                    result = DockerSandbox(task["image"]).run_check(workspace, check)
                    observations.append(_result_projection(row, result))
    except Exception as exc:  # append-only terminal projects the failure class
        execution_error = type(exc).__name__
    status = "PUBLIC_BEHAVIOR_CHECKS_QUALIFIED"
    if not identity_ok:
        status = "PUBLIC_BEHAVIOR_CHECKS_BLOCKED_IMAGE_IDENTITY"
    elif (
        execution_error is not None
        or len(observations) != 2
        or not all(item["expected_observation_matched"] for item in observations)
    ):
        status = "PUBLIC_BEHAVIOR_CHECKS_NOT_QUALIFIED"
    body = {
        "schema_version": "public-behavior-check-qualification-result-v6",
        "recorded_at": _now(),
        "status": status,
        "official": False,
        "execution_hash": candidate["execution_hash"],
        "retained_anyio_qualification": candidate["retained_anyio_qualification"],
        "image_identity_observations": identities,
        "row_observations": observations,
        "execution_error_class": execution_error,
        "docker_image_inspect_calls": inspect_calls,
        "docker_container_run_attempts": container_run_attempts,
        "docker_container_run_completions": len(observations),
        "image_pull_build_tag_remove_prune_calls": 0,
        "agent_calls": 0,
        "evaluator_calls": 0,
        "provider_calls": 0,
        "network_calls": 0,
        "added_cost_usd": 0,
        "next_gate": (
            "build-no-call-task-v5-rapid-candidate"
            if status == "PUBLIC_BEHAVIOR_CHECKS_QUALIFIED"
            else "preserve-result-and-review-public-qualification-surface"
        ),
    }
    return {**body, "content_hash": sha256_json(body)}


def run_once(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    if (root / RESULT_PATH).exists():
        raise PublicBehaviorCheckQualificationError("qualification is already consumed")
    if (root / ATTEMPT_PATH).exists():
        raise PublicBehaviorCheckQualificationError(
            "qualification attempt is consumed or its outcome is uncertain"
        )
    candidate = load_candidate(root)
    approval = _load_json_artifact(root, APPROVAL_PATH)
    if (
        approval.get("execution_hash") != candidate["execution_hash"]
        or approval.get("candidate") != _binding(root, CANDIDATE_PATH)
        or approval.get("user_message_sha256")
        != sha256_bytes(expected_approval_message(candidate).encode())
    ):
        raise PublicBehaviorCheckQualificationError("runtime approval differs")
    if _executable_binding("docker") != candidate["docker_cli"]:
        raise PublicBehaviorCheckQualificationError("Docker CLI identity drifted")
    if _executable_binding("git") != candidate["git_cli"]:
        raise PublicBehaviorCheckQualificationError("Git CLI identity drifted")
    if _docker_context_binding() != candidate["docker_context"]:
        raise PublicBehaviorCheckQualificationError("Docker context drifted")
    attempt_body = {
        "schema_version": "public-behavior-check-qualification-attempt-v6",
        "recorded_at": _now(),
        "status": "DOCKER_QUALIFICATION_ATTEMPT_CLAIMED_BEFORE_CALL",
        "execution_hash": candidate["execution_hash"],
        "candidate": _binding(root, CANDIDATE_PATH),
        "approval": _binding(root, APPROVAL_PATH),
        "docker_calls_before_claim": 0,
    }
    attempt = {**attempt_body, "content_hash": sha256_json(attempt_body)}
    _write_once(root / ATTEMPT_PATH, attempt)
    result = observe_candidate(root, candidate)
    _write_once(root / RESULT_PATH, result)
    return result


__all__ = [
    "APPROVAL_PATH",
    "ATTEMPT_PATH",
    "CANDIDATE_PATH",
    "RESULT_PATH",
    "PublicBehaviorCheckQualificationError",
    "build_candidate",
    "expected_approval_message",
    "load_candidate",
    "materialize_approval",
    "materialize_candidate",
    "observe_candidate",
    "run_once",
]
