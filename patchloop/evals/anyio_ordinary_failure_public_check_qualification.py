"""One-use Docker qualification for the AnyIO ordinary-failure public check.

Candidate construction is local-filesystem/Git only.  It binds the immutable
source qualification, the consumed AnyIO-v4 source/image tuple, and the exact
base/reference schedule without invoking Docker.  A separate exact approval is
required before one image identity inspection and two check containers.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.contracts import RegisteredCheck
from patchloop.evals import public_behavior_check_qualification_v6 as support
from patchloop.evals.anyio_ordinary_failure_public_check import (
    CHECK_ID,
)
from patchloop.evals.anyio_ordinary_failure_public_check import (
    QUALIFICATION_PATH as SOURCE_QUALIFICATION_PATH,
)
from patchloop.evals.anyio_ordinary_failure_public_check import (
    build_qualification as build_source_qualification,
)
from patchloop.evals.anyio_ordinary_failure_public_check import (
    qualification_bytes as source_qualification_bytes,
)
from patchloop.sandbox import DockerSandbox, SandboxResult
from patchloop.sandbox.runner import registered_check_execution_policy
from patchloop.util import ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "anyio-ordinary-failure-public-check-qualification-candidate-v1"
CANDIDATE_ID = "anyio-ordinary-failure-public-check-qualification-20260827-r1"
CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "anyio-ordinary-failure-public-check-qualification-candidate-v1.json"
)
APPROVAL_PATH = Path(
    "reports/rapid-development/artifacts/"
    "anyio-ordinary-failure-public-check-qualification-approval-v1.json"
)
ATTEMPT_PATH = Path(
    "reports/rapid-development/artifacts/"
    "anyio-ordinary-failure-public-check-qualification-attempt-v1.json"
)
RESULT_PATH = Path(
    "reports/rapid-development/artifacts/"
    "anyio-ordinary-failure-public-check-qualification-result-v1.json"
)

SOURCE_QUALIFICATION_FILE_SHA256 = (
    "sha256:f92590a5dd1ae8d5baf68541c3013dd24dd76bd43ab298b9299ed5f8e381b369"
)
SOURCE_QUALIFICATION_CONTENT_HASH = (
    "sha256:dbd9b94fbe1ca3aadf34f59bd5045c05d234ac907c192368abef42a973ca4307"
)
V6_CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-anyio-public-behavior-check-qualification-candidate-v6.json"
)
V6_CANDIDATE_FILE_SHA256 = "sha256:0c6147c3bac5a8fdc82b3f996c6ae640131d7edecb4081eb30f416066ac7b9d4"
V6_EXECUTION_HASH = "sha256:1c8dc99447e27d3674e63592adccea8323d74def99b69de0667756c9f5f4e027"
V6_RESULT_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-anyio-public-behavior-check-qualification-result-v6.json"
)
V6_RESULT_FILE_SHA256 = "sha256:1d35a3b1defb140118fb5097dd6849d1aafbbe35e7fe5e2721242a39a3bbd7db"
R14_CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-causal-plan-projection-ab-20260826-r14-candidate-v21.json"
)
R14_CANDIDATE_FILE_SHA256 = (
    "sha256:9fe924b88abafa30c2dcb3abc6fa51271d6d22521eec16d051d3e9f07b3df877"
)
R14_EXECUTION_HASH = "sha256:f077496605d0776d7d2f2e677391cc2ae9135550077486126258429917986c1b"

APPROVAL_TEMPLATE = (
    "execution hash {execution_hash}에 대해 AnyIO public ordinary-failure behavior check "
    "base/reference qualification 2행을 승인합니다. 고정된 로컬 AnyIO 이미지의 identity "
    "inspect 1회와 --pull never, --network none, read-only workspace로 base/reference 각 "
    "1회씩 총 2개의 Docker 컨테이너 실행을 승인합니다. 이미지 "
    "pull/build/tag/remove/prune, agent/evaluator/provider 호출, 네트워크와 비용 발생은 "
    "승인하지 않습니다."
)

ANYIO_SPEC = {
    "task_path": "fixtures/task-packages/anyio-interrupt-runner-cleanup-v4",
    "task_id": "anyio-interrupt-runner-cleanup",
    "task_version": 4,
    "schedule": True,
    "check_id": "public-interrupt-runner-lifecycle",
    "seed_workspace": ".patchloop/workspaces/run_rapid_v6_5ae158b3ed65_03/repo",
    "target_path": "src/anyio/_backends/_asyncio.py",
}
SOURCE_PATHS = (
    "patchloop/evals/anyio_ordinary_failure_public_check_qualification.py",
    "patchloop/evals/anyio_ordinary_failure_public_check.py",
    "patchloop/evals/public_behavior_check_qualification_v6.py",
    "patchloop/sandbox/runner.py",
    "patchloop/contracts.py",
    "patchloop/util.py",
    "scripts/build_anyio_ordinary_failure_public_check_candidate.py",
    "scripts/run_anyio_ordinary_failure_public_check_qualification.py",
)
PUBLIC_FAILURE_PATTERN = re.compile(r"PUBLIC_CASE:anyio:ordinary-failure-(?:status|events|summary)")
PUBLIC_FAILURE_ALLOWLIST = (
    "PUBLIC_CASE:anyio:ordinary-failure-events",
    "PUBLIC_CASE:anyio:ordinary-failure-status",
    "PUBLIC_CASE:anyio:ordinary-failure-summary",
)

PublicBehaviorCheckQualificationError = support.PublicBehaviorCheckQualificationError
ArchiveProvider = Callable[[Path, dict[str, Any], dict[str, Any]], tuple[bytes, dict[str, Any]]]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _json_bytes(value: dict[str, Any]) -> bytes:
    return support._json_bytes(value)


def _binding(root: Path, relative: str | Path) -> dict[str, Any]:
    return support._binding(root, relative)


def _load_canonical(root: Path, relative: Path) -> dict[str, Any]:
    return support._load_json_artifact(root, relative)


def _load_exact_json(root: Path, relative: Path) -> dict[str, Any]:
    path = ensure_within(root, relative.as_posix())
    if path.is_symlink() or not path.is_file():
        raise PublicBehaviorCheckQualificationError(f"artifact is unavailable: {relative}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicBehaviorCheckQualificationError(f"artifact is invalid: {relative}") from exc
    if not isinstance(value, dict):
        raise PublicBehaviorCheckQualificationError(f"artifact is invalid: {relative}")
    content = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(content):
        raise PublicBehaviorCheckQualificationError(f"artifact hash differs: {relative}")
    return value


def _load_fixed_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source = _load_canonical(root, SOURCE_QUALIFICATION_PATH)
    source_binding = _binding(root, SOURCE_QUALIFICATION_PATH)
    if (
        source_binding["file_sha256"] != SOURCE_QUALIFICATION_FILE_SHA256
        or source.get("content_hash") != SOURCE_QUALIFICATION_CONTENT_HASH
        or source_qualification_bytes(build_source_qualification(root))
        != (root / SOURCE_QUALIFICATION_PATH).read_bytes()
        or source.get("status") != "offline-source-qualified"
        or source.get("activation_authorized") is not False
        or source.get("proposed_check", {}).get("id") != CHECK_ID
    ):
        raise PublicBehaviorCheckQualificationError("source qualification differs")

    v6 = _load_canonical(root, V6_CANDIDATE_PATH)
    v6_result = _load_canonical(root, V6_RESULT_PATH)
    if (
        _binding(root, V6_CANDIDATE_PATH)["file_sha256"] != V6_CANDIDATE_FILE_SHA256
        or _binding(root, V6_RESULT_PATH)["file_sha256"] != V6_RESULT_FILE_SHA256
        or v6.get("execution_hash") != V6_EXECUTION_HASH
        or v6_result.get("execution_hash") != V6_EXECUTION_HASH
        or v6_result.get("docker_image_inspect_calls") != 1
        or v6_result.get("docker_container_run_attempts") != 2
        or v6_result.get("docker_container_run_completions") != 2
        or v6_result.get("provider_calls") != 0
        or v6_result.get("network_calls") != 0
        or v6_result.get("added_cost_usd") != 0
    ):
        raise PublicBehaviorCheckQualificationError("consumed AnyIO qualification differs")

    r14 = _load_exact_json(root, R14_CANDIDATE_PATH)
    if (
        _binding(root, R14_CANDIDATE_PATH)["file_sha256"] != R14_CANDIDATE_FILE_SHA256
        or r14.get("execution_hash") != R14_EXECUTION_HASH
        or r14.get("official") is not False
    ):
        raise PublicBehaviorCheckQualificationError("consumed R14 candidate differs")
    return source, v6, r14


def _anyio_binding(
    root: Path,
    v6: dict[str, Any],
    r14: dict[str, Any],
    git_cli: dict[str, Any],
) -> dict[str, Any]:
    current, _archive = support._task_binding(root, ANYIO_SPEC, git_cli)
    consumed = next(
        (
            item
            for item in v6.get("task_bindings", [])
            if item.get("task_id") == ANYIO_SPEC["task_id"]
        ),
        None,
    )
    r14_binding = r14.get("task_bindings")
    if isinstance(r14_binding, list):
        r14_binding = next(
            (item for item in r14_binding if item.get("task_id") == ANYIO_SPEC["task_id"]),
            None,
        )
    if current != consumed or not isinstance(r14_binding, dict):
        raise PublicBehaviorCheckQualificationError("AnyIO-v4 task binding differs")
    shared = {
        "task_id": current["task_id"],
        "task_version": current["task_version"],
        "base_commit": current["base_commit"],
        "public_spec_hash": current["public_spec_hash"],
        "private_spec_hash": current["private_spec_hash"],
        "image": current["image"],
        "image_digest": current["image_digest"],
        "package_file_count": current["package_file_count"],
        "package_inventory_hash": current["package_inventory_hash"],
    }
    r14_shared = {
        "task_id": r14_binding.get("task_id"),
        "task_version": r14_binding.get("task_version"),
        "base_commit": r14_binding.get("base_commit"),
        "public_spec_hash": r14_binding.get("public_spec_hash"),
        "private_spec_hash": r14_binding.get("private_spec_hash"),
        "image": r14_binding.get("evaluator_image"),
        "image_digest": r14_binding.get("evaluator_image_digest"),
        "package_file_count": r14_binding.get("package_file_count"),
        "package_inventory_hash": r14_binding.get("package_inventory_hash"),
    }
    if shared != r14_shared:
        raise PublicBehaviorCheckQualificationError("R14 AnyIO-v4 binding differs")
    return current


def _registered_check(source: dict[str, Any]) -> RegisteredCheck:
    proposed = source.get("proposed_check")
    if not isinstance(proposed, dict):
        raise PublicBehaviorCheckQualificationError("proposed public check is unavailable")
    payload = {
        key: value
        for key, value in proposed.items()
        if key
        in {
            "id",
            "command",
            "timeout_seconds",
            "working_directory",
            "environment",
            "output_limit_bytes",
        }
    }
    try:
        check = RegisteredCheck.model_validate(payload)
    except Exception as exc:
        raise PublicBehaviorCheckQualificationError("proposed public check is invalid") from exc
    if check.id != CHECK_ID or check.expected_exit_codes != [0]:
        raise PublicBehaviorCheckQualificationError("proposed public check contract differs")
    return check


def _candidate_body(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    source, v6, r14 = _load_fixed_inputs(root)
    docker_cli = support._executable_binding("docker")
    git_cli = support._executable_binding("git")
    docker_context = support._docker_context_binding()
    anyio = _anyio_binding(root, v6, r14, git_cli)
    check = _registered_check(source)
    check_json = check.model_dump(mode="json")
    policy = registered_check_execution_policy(
        image=anyio["image"],
        working_directory="/workspace",
        timeout_seconds=check.timeout_seconds,
        output_limit_bytes=check.output_limit_bytes,
    )
    schedule: list[dict[str, Any]] = []
    for order, state in enumerate(("base", "reference"), start=1):
        row = {
            "order": order,
            "task_id": anyio["task_id"],
            "task_version": anyio["task_version"],
            "check_id": check.id,
            "source_state": state,
            "expected_observation": "pass",
            "image_digest": anyio["image_digest"],
            "base_source_archive_sha256": anyio["base_source"]["archive_sha256"],
            "reference_patch_sha256": anyio["reference_patch"]["file_sha256"],
            "check_hash": sha256_json(check_json),
            "check_command_hash": sha256_json(list(check.command)),
        }
        schedule.append({**row, "schedule_row_id": sha256_json(row)})
    source_files = [_binding(root, path) for path in SOURCE_PATHS]
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": CANDIDATE_ID,
        "purpose": "anyio-ordinary-failure-public-check-base-reference-qualification",
        "official": False,
        "source_qualification": _binding(root, SOURCE_QUALIFICATION_PATH),
        "source_qualification_content_hash": source["content_hash"],
        "consumed_anyio_qualification_candidate": _binding(root, V6_CANDIDATE_PATH),
        "consumed_anyio_qualification_result": _binding(root, V6_RESULT_PATH),
        "consumed_r14_candidate": _binding(root, R14_CANDIDATE_PATH),
        "source_files": source_files,
        "source_inventory_hash": sha256_json(source_files),
        "docker_cli": docker_cli,
        "git_cli": git_cli,
        "docker_context": docker_context,
        "candidate_build_contract": {
            "docker_cli_invocations": 0,
            "docker_daemon_calls": 0,
            "container_runs": 0,
            "registered_check_calls": 0,
            "network_calls": 0,
            "provider_calls": 0,
            "evaluator_calls": 0,
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
        "public_private_boundary": {
            "check_derived_only_from_public_task": True,
            "reference_patch_runner_only": True,
            "reference_patch_projected_to_check_or_result": False,
            "private_spec_projected_to_check_or_result": False,
            "hidden_evaluator_read_or_called": False,
            "agent_context_created": False,
        },
        "task_binding": anyio,
        "proposed_check": check_json,
        "proposed_check_hash": sha256_json(check_json),
        "requested_execution_policy": policy,
        "public_failure_projection": {
            "schema_version": "allowlisted-public-case-id-v1",
            "pattern": PUBLIC_FAILURE_PATTERN.pattern,
            "allowlist": list(PUBLIC_FAILURE_ALLOWLIST),
            "raw_output_persisted": False,
        },
        "schedule": schedule,
        "schedule_hash": sha256_json(schedule),
        "task_successor_created": False,
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
        or candidate.get("task_successor_created") is not False
        or candidate.get("proposed_check", {}).get("id") != CHECK_ID
        or not isinstance(schedule, list)
        or len(schedule) != 2
        or [row.get("source_state") for row in schedule] != ["base", "reference"]
        or any(row.get("expected_observation") != "pass" for row in schedule)
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
        "schema_version": "anyio-ordinary-failure-public-check-qualification-approval-v1",
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
    support._write_once(root / APPROVAL_PATH, approval)
    return approval


def _text_evidence(value: str) -> dict[str, Any]:
    raw = value.encode("utf-8")
    return {"bounded_bytes": len(raw), "bounded_sha256": sha256_bytes(raw)}


def _result_projection(
    row: dict[str, Any],
    result: SandboxResult,
    requested_policy: dict[str, Any],
) -> dict[str, Any]:
    combined = result.stdout + "\n" + result.stderr
    markers = sorted(set(PUBLIC_FAILURE_PATTERN.findall(combined)))
    marker_projection_valid = all(marker in PUBLIC_FAILURE_ALLOWLIST for marker in markers)
    matched = (
        result.passed
        and not result.timed_out
        and not result.truncated
        and result.execution_policy == requested_policy
        and sha256_json(result.command) == row["check_command_hash"]
        and marker_projection_valid
        and not markers
    )
    return {
        **row,
        "observation": "pass" if matched else "unexpected-result",
        "expected_observation_matched": matched,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "truncated": result.truncated,
        "original_output_bytes": result.original_output_bytes,
        "public_case_markers": markers,
        "stdout": _text_evidence(result.stdout),
        "stderr": _text_evidence(result.stderr),
        "requested_execution_policy": result.execution_policy,
        "raw_output_persisted": False,
    }


def observe_candidate(
    repository: str | Path,
    candidate: dict[str, Any],
    *,
    archive_provider: ArchiveProvider = support._source_archive,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    task = candidate["task_binding"]
    check = RegisteredCheck.model_validate(candidate["proposed_check"])
    identities: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    execution_error: str | None = None
    inspect_calls = 1
    container_run_attempts = 0
    identity_ok = False
    try:
        projection = DockerSandbox(task["image"]).image_identity_projection()
        identity_ok = projection.verified_identity == task["image_digest"]
        identities.append(
            {
                "task_id": task["task_id"],
                "requested_digest": task["image_digest"],
                "matched": identity_ok,
                "config_id": projection.config_id,
                "matched_repo_digest": projection.matched_repo_digest,
                "error_class": None,
            }
        )
        if identity_ok:
            git_cli = support._executable_binding("git")
            archive, binding = archive_provider(root, ANYIO_SPEC, git_cli)
            if binding != task["base_source"]:
                raise PublicBehaviorCheckQualificationError("base source archive drifted")
            with tempfile.TemporaryDirectory(
                prefix="patchloop-anyio-ordinary-failure-check-"
            ) as selected:
                staging = Path(selected)
                for row in candidate["schedule"]:
                    workspace = staging / f"{row['order']:02d}-{row['source_state']}"
                    support._extract_archive(
                        archive,
                        workspace,
                        required_path=ANYIO_SPEC["target_path"],
                    )
                    if row["source_state"] == "reference":
                        patch = ensure_within(root, task["reference_patch"]["path"])
                        support._apply_reference_patch(workspace, patch, git_cli)
                    container_run_attempts += 1
                    result = DockerSandbox(task["image"]).run_check(workspace, check)
                    observations.append(
                        _result_projection(
                            row,
                            result,
                            candidate["requested_execution_policy"],
                        )
                    )
    except Exception as exc:  # append-only terminal keeps only the exception class
        execution_error = type(exc).__name__
        if not identities:
            identities.append(
                {
                    "task_id": task["task_id"],
                    "requested_digest": task["image_digest"],
                    "matched": False,
                    "config_id": None,
                    "matched_repo_digest": None,
                    "error_class": execution_error,
                }
            )

    status = "PUBLIC_ORDINARY_FAILURE_CHECK_QUALIFIED"
    if not identity_ok:
        status = "PUBLIC_ORDINARY_FAILURE_CHECK_BLOCKED_IMAGE_IDENTITY"
    elif (
        execution_error is not None
        or len(observations) != 2
        or not all(item["expected_observation_matched"] for item in observations)
    ):
        status = "PUBLIC_ORDINARY_FAILURE_CHECK_NOT_QUALIFIED"
    body = {
        "schema_version": "anyio-ordinary-failure-public-check-qualification-result-v1",
        "recorded_at": _now(),
        "status": status,
        "official": False,
        "execution_hash": candidate["execution_hash"],
        "source_qualification": candidate["source_qualification"],
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
        "raw_output_persisted": False,
        "next_gate": (
            "design-append-only-anyio-public-task-successor"
            if status == "PUBLIC_ORDINARY_FAILURE_CHECK_QUALIFIED"
            else "preserve-result-and-review-public-check"
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
    approval = _load_canonical(root, APPROVAL_PATH)
    if (
        approval.get("execution_hash") != candidate["execution_hash"]
        or approval.get("candidate") != _binding(root, CANDIDATE_PATH)
        or approval.get("user_message_sha256")
        != sha256_bytes(expected_approval_message(candidate).encode())
    ):
        raise PublicBehaviorCheckQualificationError("runtime approval differs")
    if support._executable_binding("docker") != candidate["docker_cli"]:
        raise PublicBehaviorCheckQualificationError("Docker CLI identity drifted")
    if support._executable_binding("git") != candidate["git_cli"]:
        raise PublicBehaviorCheckQualificationError("Git CLI identity drifted")
    if support._docker_context_binding() != candidate["docker_context"]:
        raise PublicBehaviorCheckQualificationError("Docker context drifted")
    attempt_body = {
        "schema_version": "anyio-ordinary-failure-public-check-qualification-attempt-v1",
        "recorded_at": _now(),
        "status": "DOCKER_QUALIFICATION_ATTEMPT_CLAIMED_BEFORE_CALL",
        "execution_hash": candidate["execution_hash"],
        "candidate": _binding(root, CANDIDATE_PATH),
        "approval": _binding(root, APPROVAL_PATH),
        "docker_calls_before_claim": 0,
    }
    attempt = {**attempt_body, "content_hash": sha256_json(attempt_body)}
    support._write_once(root / ATTEMPT_PATH, attempt)
    result = observe_candidate(root, candidate)
    support._write_once(root / RESULT_PATH, result)
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
