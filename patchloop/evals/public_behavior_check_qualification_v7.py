"""Execution-closed PDM public-check qualification successor v7.

Candidate construction is filesystem/Git-only. It inherits the consumed v6
Docker/source boundary, binds the append-only task-v6 public correction, and
does not invoke the Docker CLI or daemon. An exact approval remains required
before one image identity inspection and two registered-check containers.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.evals import public_behavior_check_qualification_v6 as predecessor_runtime
from patchloop.sandbox import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import ensure_within, sha256_bytes, sha256_json

PublicBehaviorCheckQualificationError = (
    predecessor_runtime.PublicBehaviorCheckQualificationError
)

SCHEMA_VERSION = "public-behavior-check-qualification-candidate-v7"
CANDIDATE_ID = "pdm-public-behavior-check-qualification-20260822-r7"
CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-public-behavior-check-qualification-candidate-v7.json"
)
APPROVAL_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-public-behavior-check-qualification-approval-v7.json"
)
ATTEMPT_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-public-behavior-check-qualification-attempt-v7.json"
)
RESULT_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-public-behavior-check-qualification-result-v7.json"
)
PREDECESSOR_CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-anyio-public-behavior-check-qualification-candidate-v6.json"
)
PREDECESSOR_RESULT_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-anyio-public-behavior-check-qualification-result-v6.json"
)
PREDECESSOR_EXECUTION_HASH = (
    "sha256:1c8dc99447e27d3674e63592adccea8323d74def99b69de0667756c9f5f4e027"
)
PREDECESSOR_CANDIDATE_FILE_SHA256 = (
    "sha256:0c6147c3bac5a8fdc82b3f996c6ae640131d7edecb4081eb30f416066ac7b9d4"
)
PREDECESSOR_RESULT_FILE_SHA256 = (
    "sha256:1d35a3b1defb140118fb5097dd6849d1aafbbe35e7fe5e2721242a39a3bbd7db"
)
APPROVAL_TEMPLATE = (
    "execution hash {execution_hash}에 대해 PDM public behavior targeted-check qualification "
    "successor-v7 2행을 승인합니다. 고정된 로컬 PDM 이미지의 identity inspect 1회와 "
    "--pull never, --network none, read-only workspace로 base/reference 각 1회씩 총 2개의 "
    "Docker 컨테이너 실행을 승인합니다. 이미지 pull/build/tag/remove/prune, "
    "agent/evaluator/provider 호출, 네트워크와 비용 발생은 승인하지 않습니다."
)

PDM_V5_PATH = Path("fixtures/task-packages/pdm-ignore-active-venv-resolution-v5")
PDM_V6_PATH = Path("fixtures/task-packages/pdm-ignore-active-venv-resolution-v6")
ANYIO_V4_PATH = Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v4")
TASK_SPECS = (
    {
        "task_path": PDM_V6_PATH.as_posix(),
        "task_id": "pdm-ignore-active-venv-resolution",
        "task_version": 6,
        "schedule": True,
        "check_id": "public-ignore-active-venv-resolution",
        "seed_workspace": ".patchloop/workspaces/run_rapid_v6_5ae158b3ed65_01/repo",
        "target_path": "src/pdm/project/core.py",
    },
    {
        "task_path": ANYIO_V4_PATH.as_posix(),
        "task_id": "anyio-interrupt-runner-cleanup",
        "task_version": 4,
        "schedule": False,
        "check_id": "public-interrupt-runner-lifecycle",
        "seed_workspace": ".patchloop/workspaces/run_rapid_v6_5ae158b3ed65_03/repo",
        "target_path": "src/anyio/_backends/_asyncio.py",
    },
)
SOURCE_PATHS = (
    "patchloop/evals/public_behavior_check_qualification_v7.py",
    "patchloop/evals/public_behavior_check_qualification_v6.py",
    "patchloop/sandbox/runner.py",
    "patchloop/contracts.py",
    "patchloop/task_loader.py",
    "patchloop/util.py",
    "patchloop/errors.py",
    "scripts/run_public_behavior_check_qualification_v7.py",
)
PUBLIC_SOURCE_RECONCILIATION = {
    "schema_version": "pdm-public-source-reconciliation-v1",
    "base_commit": "881cd4e38d31663ae67bdae227ec1ccdfd5e2c77",
    "core_source_url": (
        "https://github.com/pdm-project/pdm/blob/"
        "881cd4e38d31663ae67bdae227ec1ccdfd5e2c77/src/pdm/project/core.py"
    ),
    "config_source_url": (
        "https://github.com/pdm-project/pdm/blob/"
        "881cd4e38d31663ae67bdae227ec1ccdfd5e2c77/src/pdm/project/config.py"
    ),
    "exact_public_delta": "conda-case-virtual-env-empty-to-absent",
    "case_removed": False,
    "expected_result_changed": False,
    "reference_result_is_semantic_authority": False,
}


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _json_bytes(value: dict[str, Any]) -> bytes:
    return predecessor_runtime._json_bytes(value)


def _binding(root: Path, relative: str | Path) -> dict[str, Any]:
    return predecessor_runtime._binding(root, relative)


def _load_predecessor(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate_binding = _binding(root, PREDECESSOR_CANDIDATE_PATH)
    result_binding = _binding(root, PREDECESSOR_RESULT_PATH)
    candidate = predecessor_runtime._load_json_artifact(root, PREDECESSOR_CANDIDATE_PATH)
    result = predecessor_runtime._load_json_artifact(root, PREDECESSOR_RESULT_PATH)
    if (
        candidate_binding["file_sha256"] != PREDECESSOR_CANDIDATE_FILE_SHA256
        or result_binding["file_sha256"] != PREDECESSOR_RESULT_FILE_SHA256
        or candidate.get("execution_hash") != PREDECESSOR_EXECUTION_HASH
        or result.get("execution_hash") != PREDECESSOR_EXECUTION_HASH
        or result.get("status") != "PUBLIC_BEHAVIOR_CHECKS_NOT_QUALIFIED"
        or candidate.get("retained_anyio_qualification")
        != result.get("retained_anyio_qualification")
        or result.get("docker_image_inspect_calls") != 1
        or result.get("docker_container_run_attempts") != 2
        or result.get("docker_container_run_completions") != 2
        or result.get("image_pull_build_tag_remove_prune_calls") != 0
        or result.get("agent_calls") != 0
        or result.get("evaluator_calls") != 0
        or result.get("provider_calls") != 0
        or result.get("network_calls") != 0
        or result.get("added_cost_usd") != 0
    ):
        raise PublicBehaviorCheckQualificationError("consumed v6 evidence differs")
    return candidate, result


def _replace_once(value: str, before: str, after: str) -> str:
    if value.count(before) != 1:
        raise PublicBehaviorCheckQualificationError("task-v6 predecessor delta is ambiguous")
    return value.replace(before, after, 1)


def _validate_task_v6_delta(root: Path) -> None:
    v5 = ensure_within(root, PDM_V5_PATH.as_posix())
    v6 = ensure_within(root, PDM_V6_PATH.as_posix())
    v5_public = (v5 / "public.yaml").read_text(encoding="utf-8")
    expected_public = _replace_once(v5_public, "task_version: 5", "task_version: 6")
    expected_public = _replace_once(
        expected_public,
        '            virtual_env="",\n            conda_prefix="conda",',
        '            virtual_env=None,\n            conda_prefix="conda",',
    )
    expected_public = _replace_once(
        expected_public,
        "  - public-behavior-check-v5",
        "  - public-behavior-check-v6",
    )
    if (v6 / "public.yaml").read_text(encoding="utf-8") != expected_public:
        raise PublicBehaviorCheckQualificationError("task-v6 public delta differs")

    v5_private = (v5 / "private.yaml").read_text(encoding="utf-8")
    expected_private = _replace_once(v5_private, "task_version: 5", "task_version: 6")
    if (v6 / "private.yaml").read_text(encoding="utf-8") != expected_private:
        raise PublicBehaviorCheckQualificationError("task-v6 private metadata delta differs")

    for relative in ("environment.yaml", "reference.patch"):
        if (v5 / relative).read_bytes() != (v6 / relative).read_bytes():
            raise PublicBehaviorCheckQualificationError(f"task-v6 opaque bytes differ: {relative}")
    if predecessor_runtime._package_inventory(
        v5 / "hidden"
    ) != predecessor_runtime._package_inventory(v6 / "hidden"):
        raise PublicBehaviorCheckQualificationError("task-v6 hidden bytes differ")


def _task_bindings(
    root: Path,
    predecessor: dict[str, Any],
    git_cli: dict[str, Any],
) -> list[dict[str, Any]]:
    _validate_task_v6_delta(root)
    current: list[dict[str, Any]] = []
    for spec in TASK_SPECS:
        binding, _archive = predecessor_runtime._task_binding(root, spec, git_cli)
        current.append(binding)

    old_by_id = {item["task_id"]: item for item in predecessor["task_bindings"]}
    new_by_id = {item["task_id"]: item for item in current}
    anyio_id = "anyio-interrupt-runner-cleanup"
    if new_by_id[anyio_id] != old_by_id[anyio_id]:
        raise PublicBehaviorCheckQualificationError("retained AnyIO task binding differs")

    pdm_id = "pdm-ignore-active-venv-resolution"
    before = old_by_id[pdm_id]
    after = new_by_id[pdm_id]
    stable_keys = (
        "task_id",
        "base_commit",
        "image",
        "image_digest",
        "targeted_check_id",
        "requested_execution_policy",
        "docker_pull_policy",
        "base_source",
        "expected_base_observation",
        "expected_reference_observation",
    )
    if any(after[key] != before[key] for key in stable_keys):
        raise PublicBehaviorCheckQualificationError("task-v6 stable binding differs")
    if (
        after["task_path"] != PDM_V6_PATH.as_posix()
        or after["task_version"] != 6
        or after["reference_patch"]["file_bytes"]
        != before["reference_patch"]["file_bytes"]
        or after["reference_patch"]["file_sha256"]
        != before["reference_patch"]["file_sha256"]
        or after["targeted_check_hash"] == before["targeted_check_hash"]
        or after["targeted_check_command_hash"] == before["targeted_check_command_hash"]
    ):
        raise PublicBehaviorCheckQualificationError("task-v6 successor binding differs")
    return current


def _candidate_body(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    predecessor, predecessor_result = _load_predecessor(root)
    docker_cli = predecessor_runtime._executable_binding("docker")
    git_cli = predecessor_runtime._executable_binding("git")
    docker_context = predecessor_runtime._docker_context_binding()
    tasks = _task_bindings(root, predecessor, git_cli)
    retained_anyio = predecessor["retained_anyio_qualification"]
    if (
        retained_anyio.get("status") != "QUALIFIED_FROM_CONSUMED_V5_ROWS"
        or retained_anyio != predecessor_result["retained_anyio_qualification"]
    ):
        raise PublicBehaviorCheckQualificationError("retained AnyIO qualification differs")

    pdm = next(item for item in tasks if item["task_id"].startswith("pdm-"))
    schedule: list[dict[str, Any]] = []
    for order, state in enumerate(("base", "reference"), start=1):
        row = {
            "order": order,
            "task_id": pdm["task_id"],
            "task_version": pdm["task_version"],
            "targeted_check_id": pdm["targeted_check_id"],
            "source_state": state,
            "expected_observation": pdm[f"expected_{state}_observation"],
            "image_digest": pdm["image_digest"],
            "base_source_archive_sha256": pdm["base_source"]["archive_sha256"],
            "reference_patch_sha256": pdm["reference_patch"]["file_sha256"],
        }
        schedule.append({**row, "schedule_row_id": sha256_json(row)})
    source_files = [_binding(root, path) for path in SOURCE_PATHS]
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": CANDIDATE_ID,
        "purpose": "pdm-task-v6-public-behavior-check-qualification",
        "official": False,
        "predecessor_candidate": _binding(root, PREDECESSOR_CANDIDATE_PATH),
        "predecessor_result": _binding(root, PREDECESSOR_RESULT_PATH),
        "predecessor_execution_hash": PREDECESSOR_EXECUTION_HASH,
        "public_source_reconciliation": PUBLIC_SOURCE_RECONCILIATION,
        "retained_anyio_qualification": retained_anyio,
        "source_files": source_files,
        "source_inventory_hash": sha256_json(source_files),
        "docker_cli": docker_cli,
        "git_cli": git_cli,
        "docker_context": docker_context,
        "candidate_build_contract": {
            "docker_cli_invocations": 0,
            "docker_daemon_calls": 0,
            "container_runs": 0,
            "network_calls": 0,
            "provider_calls": 0,
            "added_cost_usd": 0,
        },
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
            "pattern": predecessor_runtime.PUBLIC_CASE_PATTERN.pattern,
            "task_allowlists": predecessor_runtime.PUBLIC_CASE_ALLOWLIST,
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
    task_versions = {
        (item.get("task_id"), item.get("task_version"))
        for item in candidate.get("task_bindings", [])
        if isinstance(item, dict)
    }
    if (
        candidate.get("schema_version") != SCHEMA_VERSION
        or candidate.get("candidate_id") != CANDIDATE_ID
        or candidate.get("official") is not False
        or candidate.get("predecessor_execution_hash") != PREDECESSOR_EXECUTION_HASH
        or candidate.get("public_source_reconciliation") != PUBLIC_SOURCE_RECONCILIATION
        or candidate.get("retained_anyio_qualification", {}).get("status")
        != "QUALIFIED_FROM_CONSUMED_V5_ROWS"
        or task_versions
        != {
            ("pdm-ignore-active-venv-resolution", 6),
            ("anyio-interrupt-runner-cleanup", 4),
        }
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


def materialize_approval(repository: str | Path, user_message: str) -> dict[str, Any]:
    root = Path(repository).resolve()
    candidate = load_candidate(root)
    if user_message != expected_approval_message(candidate):
        raise PublicBehaviorCheckQualificationError("exact approval message differs")
    body = {
        "schema_version": "public-behavior-check-qualification-approval-v7",
        "recorded_at": _now(),
        "status": "EXACT_DOCKER_QUALIFICATION_APPROVED_ONCE",
        "candidate": _binding(root, CANDIDATE_PATH),
        "execution_hash": candidate["execution_hash"],
        "user_message_sha256": sha256_bytes(user_message.encode()),
        "approved_image_identity_inspects": 1,
        "approved_container_runs": 2,
        "image_pull_build_tag_remove_prune_authorized": False,
        "agent_evaluator_provider_network_cost_authorized": False,
    }
    approval = {**body, "content_hash": sha256_json(body)}
    predecessor_runtime._write_once(root / APPROVAL_PATH, approval)
    return approval


ArchiveProvider = Callable[[Path, dict[str, Any], dict[str, Any]], tuple[bytes, dict[str, Any]]]


def observe_candidate(
    repository: str | Path,
    candidate: dict[str, Any],
    *,
    archive_provider: ArchiveProvider = predecessor_runtime._source_archive,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    pdm_spec = TASK_SPECS[0]
    pdm = next(
        item
        for item in candidate["task_bindings"]
        if item["task_id"] == pdm_spec["task_id"]
    )
    identities: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    execution_error: str | None = None
    inspect_calls = 1
    container_run_attempts = 0
    identity_ok = False
    try:
        projection = DockerSandbox(pdm["image"]).image_identity_projection()
        identity_ok = projection.verified_identity == pdm["image_digest"]
        identities.append(
            {
                "task_id": pdm["task_id"],
                "requested_digest": pdm["image_digest"],
                "matched": identity_ok,
                "config_id": projection.config_id,
                "matched_repo_digest": projection.matched_repo_digest,
                "error_class": None,
            }
        )
        if identity_ok:
            git_cli = predecessor_runtime._executable_binding("git")
            archive, binding = archive_provider(root, pdm_spec, git_cli)
            if binding != pdm["base_source"]:
                raise PublicBehaviorCheckQualificationError("base source archive drifted")
            with tempfile.TemporaryDirectory(prefix="patchloop-public-check-v7-") as selected:
                staging = Path(selected)
                for row in candidate["schedule"]:
                    workspace = staging / f"{row['order']:02d}-{row['source_state']}"
                    predecessor_runtime._extract_archive(
                        archive,
                        workspace,
                        required_path=pdm_spec["target_path"],
                    )
                    if row["source_state"] == "reference":
                        patch = ensure_within(root, pdm["reference_patch"]["path"])
                        predecessor_runtime._apply_reference_patch(workspace, patch, git_cli)
                    package = load_task_package(root / pdm["task_path"])
                    container_run_attempts += 1
                    result = DockerSandbox(pdm["image"]).run_check(
                        workspace,
                        package.public.visible_checks[0],
                    )
                    observations.append(predecessor_runtime._result_projection(row, result))
    except Exception as exc:  # terminal evidence records only the exception class
        execution_error = type(exc).__name__
        if not identities:
            identities.append(
                {
                    "task_id": pdm["task_id"],
                    "requested_digest": pdm["image_digest"],
                    "matched": False,
                    "config_id": None,
                    "matched_repo_digest": None,
                    "error_class": execution_error,
                }
            )

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
        "schema_version": "public-behavior-check-qualification-result-v7",
        "recorded_at": _now(),
        "status": status,
        "official": False,
        "execution_hash": candidate["execution_hash"],
        "public_source_reconciliation": candidate["public_source_reconciliation"],
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
            "freeze-next-rapid-public-development-candidate"
            if status == "PUBLIC_BEHAVIOR_CHECKS_QUALIFIED"
            else "preserve-result-and-retire-pdm-targeted-check"
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
    approval = predecessor_runtime._load_json_artifact(root, APPROVAL_PATH)
    if (
        approval.get("execution_hash") != candidate["execution_hash"]
        or approval.get("candidate") != _binding(root, CANDIDATE_PATH)
        or approval.get("user_message_sha256")
        != sha256_bytes(expected_approval_message(candidate).encode())
    ):
        raise PublicBehaviorCheckQualificationError("runtime approval differs")
    if predecessor_runtime._executable_binding("docker") != candidate["docker_cli"]:
        raise PublicBehaviorCheckQualificationError("Docker CLI identity drifted")
    if predecessor_runtime._executable_binding("git") != candidate["git_cli"]:
        raise PublicBehaviorCheckQualificationError("Git CLI identity drifted")
    if predecessor_runtime._docker_context_binding() != candidate["docker_context"]:
        raise PublicBehaviorCheckQualificationError("Docker context drifted")
    attempt_body = {
        "schema_version": "public-behavior-check-qualification-attempt-v7",
        "recorded_at": _now(),
        "status": "DOCKER_QUALIFICATION_ATTEMPT_CLAIMED_BEFORE_CALL",
        "execution_hash": candidate["execution_hash"],
        "candidate": _binding(root, CANDIDATE_PATH),
        "approval": _binding(root, APPROVAL_PATH),
        "docker_calls_before_claim": 0,
    }
    attempt = {**attempt_body, "content_hash": sha256_json(attempt_body)}
    predecessor_runtime._write_once(root / ATTEMPT_PATH, attempt)
    result = observe_candidate(root, candidate)
    predecessor_runtime._write_once(root / RESULT_PATH, result)
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
