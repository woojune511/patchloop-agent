"""Read-only local preflight for the held-out A/C activation contract."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_dispatcher import heldout_ac_paid_campaign_identity_consumed
from patchloop.evals.heldout_ac_execution import (
    MATERIALIZATION_PATH,
    build_heldout_ac_execution_candidate,
    build_heldout_ac_no_call_readiness,
)
from patchloop.evals.heldout_ac_preflight_source_qualification import (
    load_heldout_ac_preflight_source_binding,
)
from patchloop.runtime import repository_root, runtime_root
from patchloop.sandbox import DockerSandbox
from patchloop.util import utc_now


def _root(repository: str | Path | None) -> Path:
    return Path(repository).resolve() if repository is not None else repository_root().resolve()


def _git_observation(root: Path) -> dict[str, Any]:
    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )

    commit = run("rev-parse", "HEAD")
    tree = run("rev-parse", "HEAD^{tree}")
    status = run("status", "--porcelain=v1", "--untracked-files=all")
    available = commit.returncode == tree.returncode == status.returncode == 0
    dirty_paths = sorted(
        {line[3:].replace("\\", "/") for line in status.stdout.splitlines() if len(line) >= 4}
    )
    execution_dirty_paths = [
        path
        for path in dirty_paths
        if path not in {"AGENTS.md", "README.md"} and not path.startswith("docs/")
    ]
    return {
        "available": available,
        "commit": commit.stdout.strip(),
        "tree": tree.stdout.strip(),
        "execution_clean": available and not execution_dirty_paths,
        "execution_dirty_paths": execution_dirty_paths,
    }


def _required_images(root: Path) -> tuple[tuple[str, str], ...]:
    try:
        payload = __import__("json").loads((root / MATERIALIZATION_PATH).read_text("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("held-out task/pricing materialization is unavailable") from exc
    bindings = payload.get("task_bindings") if isinstance(payload, dict) else None
    if not isinstance(bindings, list):
        raise ContractError("held-out task/pricing materialization has no task bindings")
    try:
        identities = {
            (item["task"]["evaluator_image"], item["task"]["evaluator_image_digest"])
            for item in bindings
        }
    except (KeyError, TypeError) as exc:
        raise ContractError("held-out evaluator image bindings are invalid") from exc
    if len(identities) != 12:
        raise ContractError("held-out evaluator image set is incomplete")
    return tuple(sorted(identities))


def _docker_observation(images: tuple[tuple[str, str], ...]) -> dict[str, Any]:
    available = DockerSandbox.available()
    rows: list[dict[str, Any]] = []
    for image, expected_digest in images:
        observed = DockerSandbox(image).image_identity() if available else None
        rows.append(
            {
                "evaluator_image": image,
                "expected_digest": expected_digest,
                "observed_digest": observed,
                "ready": observed == expected_digest,
            }
        )
    return {"available": available, "images": rows}


def _sdk_observation() -> dict[str, Any]:
    try:
        installed = version("openai")
    except PackageNotFoundError:
        installed = None
    return {"installed": installed is not None, "version": installed}


def preflight_heldout_ac(
    *,
    credential_present: bool,
    repository: str | Path | None = None,
    runtime: str | Path | None = None,
    _git_observer: Callable[[Path], dict[str, Any]] = _git_observation,
    _docker_observer: Callable[[tuple[tuple[str, str], ...]], dict[str, Any]] = (
        _docker_observation
    ),
    _sdk_observer: Callable[[], dict[str, Any]] = _sdk_observation,
) -> dict[str, Any]:
    """Produce a secret-free candidate only when every local no-call gate is ready."""

    if type(credential_present) is not bool:
        raise ContractError("held-out credential_present must be a boolean")
    root = _root(repository)
    source_binding = load_heldout_ac_preflight_source_binding(repository=root)
    required_images = _required_images(root)
    git = _git_observer(root)
    docker = _docker_observer(required_images)
    sdk = _sdk_observer()
    custom_base_url_present = bool(
        os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
    )
    blockers: list[dict[str, str]] = []

    def block(code: str, message: str) -> None:
        blockers.append({"code": code, "message": message})

    if git.get("available") is not True:
        block("GIT_UNAVAILABLE", "held-out preflight could not read Git identity")
    elif git.get("execution_clean") is not True:
        block("GIT_EXECUTION_SOURCE_DIRTY", "held-out execution source is dirty")
    if docker.get("available") is not True:
        block("DOCKER_UNAVAILABLE", "held-out preflight could not read the Docker daemon")
    elif any(row.get("ready") is not True for row in docker.get("images", [])):
        block("DOCKER_IMAGE_UNAVAILABLE", "a digest-pinned held-out evaluator image is unavailable")
    if sdk.get("installed") is not True or not isinstance(sdk.get("version"), str):
        block("OPENAI_SDK_UNAVAILABLE", "the OpenAI SDK is not installed")
    if not credential_present:
        block("OPENAI_CREDENTIAL_MISSING", "OPENAI_API_KEY presence was not established")
    if custom_base_url_present:
        block("CUSTOM_OPENAI_BASE_URL", "custom OpenAI base URLs are forbidden")

    candidate = None
    if not blockers:
        observed_images = tuple(
            (str(row["evaluator_image"]), str(row["observed_digest"])) for row in docker["images"]
        )
        readiness = build_heldout_ac_no_call_readiness(
            observed_at=utc_now(),
            git_commit=str(git["commit"]),
            git_tree=str(git["tree"]),
            docker_images=observed_images,
            openai_sdk_version=str(sdk["version"]),
            credential_present=True,
            custom_base_url_present=False,
        )
        candidate = build_heldout_ac_execution_candidate(
            readiness=readiness,
            source_qualification=source_binding,
            repository=root,
        )
        selected_runtime = (
            Path(runtime).resolve() if runtime is not None else runtime_root().resolve()
        )
        if heldout_ac_paid_campaign_identity_consumed(candidate, root=selected_runtime):
            block(
                "PAID_CAMPAIGN_IDENTITY_CONSUMED",
                "this qualified source, suite and schedule already consumed paid authority",
            )
            candidate = None
    return {
        "schema_version": "heldout-ac-preflight-v1",
        "execution_candidate_ready": candidate is not None,
        "ready": False,
        "blockers": blockers,
        "candidate": candidate.model_dump(mode="json") if candidate is not None else None,
        "execution_hash": candidate.execution_hash if candidate is not None else None,
        "environment": {
            "git": git,
            "docker": docker,
            "openai_sdk": sdk,
            "credential": {
                "name": "OPENAI_API_KEY",
                "present": credential_present,
                "custom_base_url_present": custom_base_url_present,
                "value_observed_or_serialized": False,
            },
        },
        "source_qualification_hash": source_binding.source_qualification_hash,
        "full_schedule_reserve_usd": 252.0,
        "hard_cap_usd": 275.0,
        "paid_approval_present": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "agent_runs_made": 0,
        "model_cost_usd": 0.0,
    }


__all__ = ["preflight_heldout_ac"]
