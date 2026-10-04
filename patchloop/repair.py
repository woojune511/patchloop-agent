"""Public-only repair admission and delivery, sharing the development solver."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, ValidationError, model_validator

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, PublicTask, StrictModel, TaskConstraints
from patchloop.dev.contracts import RunEnvelope, RunRequest
from patchloop.errors import ContractError, RecoveryError
from patchloop.sandbox.runner import DockerSandbox, LocalSandbox
from patchloop.util import sha256_json


class RepairTask(PublicTask):
    schema_version: Literal["repair-task-v1"] = "repair-task-v1"
    split: Literal["repair"] = "repair"
    constraints: TaskConstraints = Field(...)

    @model_validator(mode="after")
    def public_checks_are_explicit(self) -> RepairTask:
        if (not self.visible_checks or not self.constraints.allowed_paths
                or "allowed_paths" not in self.constraints.model_fields_set):
            raise ValueError("repair requires approved visible checks and allowed paths")
        ids = [check.id for check in self.visible_checks]
        if len(ids) != len(set(ids)):
            raise ValueError("repair check IDs must be unique")
        if self.probe_profiles:
            raise ValueError("repair-task-v1 does not support probe profiles")
        return self


class RepairSandbox(StrictModel):
    backend: Literal["local", "docker"]
    image: str | None = None
    image_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def pinned_image(self) -> RepairSandbox:
        if self.backend == "docker":
            if not self.image_digest or not self.image or not self.image.endswith(
                "@" + self.image_digest,
            ):
                raise ValueError("repair sandbox needs a digest-pinned prepared image")
        elif self.image is not None or self.image_digest is not None:
            raise ValueError("local sandbox has no image")
        return self


class RepairRunRequest(RunRequest):
    """Explicit public source, execution configuration and cost authorization."""

    source: Path
    sandbox: RepairSandbox

    @model_validator(mode="after")
    def public_execution_boundary(self) -> RepairRunRequest:
        expected = "docker" if self.provider == "openai" else "local"
        if self.sandbox.backend != expected:
            raise ValueError("OpenAI repair requires Docker; mock repair uses local checks")
        if self.prepared_source is not None or self.enable_probes:
            raise ValueError("repair uses --source; prepared-source and probes are unsupported")
        return self


class RepairEnvelope(RunEnvelope):
    schema_version: Literal["repair-run-envelope-v1"] = "repair-run-envelope-v1"
    split: Literal["repair"] = "repair"
    source_path: str
    sandbox_image_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")

    @property
    def execution_image_digest(self) -> str | None:
        return self.sandbox_image_digest


class RepairPackage(StrictModel):
    public: RepairTask
    public_spec_hash: str
    task_content_hash: str


def load_repair_task(path: Path) -> RepairPackage:
    try:
        public = RepairTask.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise ContractError(f"invalid public repair task: {exc}") from exc
    # Local source admission uses an exact Git object, never a mutable branch or URL fetch.
    if re.fullmatch(r"[0-9a-f]{40}", public.repository.base_commit) is None:
        raise ContractError("repair requires a full 40-character base commit")
    if public.repository.url.startswith("snapshot://"):
        raise ContractError("repair requires a local Git source, not a benchmark snapshot")
    digest = sha256_json(public.model_dump(mode="json"))
    return RepairPackage(public=public, public_spec_hash=digest, task_content_hash=digest)


def prepared_sandbox(request: RepairRunRequest, *, deadline=None):
    if request.sandbox.backend == "local":
        return LocalSandbox()
    sandbox = DockerSandbox(request.sandbox.image)
    if not DockerSandbox.available(deadline=deadline):
        raise ContractError("Docker unavailable; repair never starts or installs it")
    if sandbox.image_identity(deadline=deadline) != request.sandbox.image_digest:
        raise ContractError("prepared repair image unavailable or mismatched; no pull/build")
    return sandbox


def run_repair(request: RepairRunRequest | dict) -> dict[str, Any]:
    from patchloop.dev.runner import _run_invocation

    try:
        request = RepairRunRequest.model_validate(request)
    except ValidationError as exc:
        raise ContractError(str(exc)) from exc
    package = load_repair_task(request.task)
    source = request.source.resolve()
    if request.resume_run_id is None and not source.is_dir():
        raise ContractError("repair source must be an existing local Git repository")
    if request.state_root is None:
        from patchloop.dev.runner import default_state_root

        state_root = default_state_root().resolve()
    else:
        state_root = request.state_root.resolve()
    if (state_root == source or state_root.is_relative_to(source)
            or source.is_relative_to(state_root)):
        raise ContractError("repair source and generated state must be separate trees")
    result = _run_invocation(request, request.task.resolve().parent, package)
    result["schema_version"] = "repair-invocation-v1"
    for run in result["runs"]:
        run["schema_version"] = "repair-run-v1"
        run["acceptance"] = "NOT_RUN"
    return result


def record_delivery(journal, store: ArtifactStore, envelope: RepairEnvelope, submitted: Artifact,
                    finish_output: dict, active_elapsed_ms: int) -> dict:
    """Commit public evidence before the terminal event; never call an evaluator."""
    checks = _public_checks(journal.events())
    receipt = store.put_json({
        "schema_version": "repair-delivery-v1", "run_id": journal.run_id,
        "envelope_hash": sha256_json(envelope.model_dump(mode="json")),
        "patch": submitted.model_dump(mode="json"),
        "finish": finish_output, "public_checks": checks,
        "acceptance": "NOT_RUN", "active_elapsed_ms": active_elapsed_ms,
    })
    journal.append("repair_delivered", {"receipt": receipt.model_dump(mode="json")})
    return load_delivery(journal, store, envelope)


def _public_checks(events: list[dict]) -> list[dict]:
    return [e for e in events if e["event_type"] == "action_finished"
            and e["payload"]["result"]["tool"] in {"run_check", "run_tests"}]


def load_delivery(journal, store: ArtifactStore, envelope: RepairEnvelope) -> dict | None:
    events = journal.events()
    completed = [e for e in events if e["event_type"] == "repair_delivered"]
    if not completed:
        return None
    if len(completed) != 1:
        raise RecoveryError("conflicting public repair deliveries")
    try:
        receipt = Artifact.model_validate(completed[0]["payload"]["receipt"])
        data = json.loads(store.read_bytes(receipt))
        patch = Artifact.model_validate(data["patch"])
        store.read_bytes(patch)
        if (data["run_id"] != journal.run_id
                or data["envelope_hash"] != sha256_json(envelope.model_dump(mode="json"))
                or data["acceptance"] != "NOT_RUN"
                or data["finish"]["patch_hash"] != patch.content_hash):
            raise ValueError("public delivery identity mismatch")
        preceding = [e for e in events if e["sequence"] < completed[0]["sequence"]]
        if data["public_checks"] != _public_checks(preceding):
            raise ValueError("public delivery check evidence mismatch")
        finished = [e["payload"]["result"] for e in preceding
                    if e["event_type"] == "action_finished"
                    and e["payload"]["result"]["tool"] == "finish_task"
                    and e["payload"]["result"]["status"] == "succeeded"]
        if len(finished) != 1 or finished[0]["output"] != data["finish"]:
            raise ValueError("public delivery has no matching successful finish")
        submissions = [e for e in events if e["event_type"] == "submission_recorded"]
        if len(submissions) != 1 or submissions[0]["payload"] != {
            "patch_hash": patch.content_hash, "visible_check_diff_hash": patch.content_hash,
            "changed_files": data["finish"]["changed_files"],
        }:
            raise ValueError("public delivery submission mismatch")
    except (ValueError, KeyError, TypeError) as exc:
        raise RecoveryError("invalid public repair delivery") from exc
    return {"patch": patch.model_dump(mode="json"), "public_verification": receipt.model_dump(
        mode="json"), "acceptance": "NOT_RUN", "active_elapsed_ms": data["active_elapsed_ms"]}
