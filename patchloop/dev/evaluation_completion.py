"""Durable evaluator completion, independent of task execution and live preflight."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, RunManifest
from patchloop.dev.contracts import DevRunEnvelope, DevTerminal
from patchloop.dev.state import DevJournal
from patchloop.errors import RecoveryError
from patchloop.util import sha256_json


class EvaluationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_acceptance: Literal["PASS", "FAIL", "ERROR"]
    safety_state: Literal["PASS", "FAIL", "ERROR", "NOT_RUN"]
    failure_class: str | None
    claim_eligible: Literal[False] = False


class EvaluationCompletion(BaseModel):
    """A committed result sufficient to finish metadata without executing again."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dev-evaluation-completion-v1"] = "dev-evaluation-completion-v1"
    run_id: str
    summary: EvaluationSummary
    summary_hash: str
    agent_context_reinjected: Literal[False] = False
    terminal: Literal["EVALUATOR_PASS", "EVALUATOR_FAIL", "EVALUATOR_ERROR", "LIMIT_REACHED"]
    message: str | None = Field(default=None, max_length=1_000)
    stop_remaining: bool = Field(strict=True)
    active_elapsed_ms: int = Field(ge=0, strict=True)
    artifacts: dict[str, Artifact]

    @model_validator(mode="after")
    def result_is_consistent(self) -> EvaluationCompletion:
        expected = {
            "PASS": "EVALUATOR_PASS", "FAIL": "EVALUATOR_FAIL", "ERROR": "EVALUATOR_ERROR",
        }[self.summary.task_acceptance]
        if self.summary.failure_class == "ACTIVE_DEADLINE_EXHAUSTED":
            expected = "LIMIT_REACHED"
        if self.terminal != expected or self.summary_hash != sha256_json(self.summary.model_dump()):
            raise ValueError("evaluator completion summary differs from terminal identity")
        if self.summary.failure_class == "SANDBOX_CLEANUP_UNCONFIRMED" and not self.stop_remaining:
            raise ValueError("uncertain evaluator cleanup must stop further repetitions")
        required = {"submitted_patch", "manifest", "evaluator_summary", "terminal_provenance"}
        if not required.issubset(self.artifacts):
            raise ValueError("evaluator completion is missing required artifacts")
        return self

    @property
    def artifact_hashes(self) -> dict[str, str]:
        return {key: artifact.content_hash for key, artifact in self.artifacts.items()}


def _terminal_provenance(
    *, terminal: str, summary_hash: str, artifacts: dict[str, Artifact],
    runtime_hash: str, task_hash: str, model_hash: str,
) -> dict[str, Any]:
    provenance = artifacts.get("evaluator_provenance")
    return {
        "schema_version": "dev-terminal-provenance-v1",
        "official": False,
        "terminal": terminal,
        "manifest_content_hash": artifacts["manifest"].content_hash,
        "submitted_patch_content_hash": artifacts["submitted_patch"].content_hash,
        "evaluator_summary_hash": summary_hash,
        "evaluator_provenance_content_hash": provenance.content_hash if provenance else None,
        "runtime_content_hash": runtime_hash,
        "task_content_hash": task_hash,
        "model_hash": model_hash,
    }


def prepare_evaluation_completion(
    *, store: ArtifactStore, run_id: str, terminal: DevTerminal, summary: dict[str, Any],
    message: str | None, stop_remaining: bool, active_elapsed_ms: int,
    artifacts: dict[str, Artifact], hashes: dict[str, str],
) -> EvaluationCompletion:
    """Store all outcome bytes before the single durable evaluator_finished event."""

    artifacts = dict(artifacts)
    summary_hash = sha256_json(summary)
    artifacts["evaluator_summary"] = store.put_json(summary)
    artifacts["terminal_provenance"] = store.put_json(_terminal_provenance(
        terminal=terminal.value, summary_hash=summary_hash, artifacts=artifacts, **hashes,
    ))
    return EvaluationCompletion(
        run_id=run_id, summary=summary, summary_hash=summary_hash, terminal=terminal.value,
        message=message, stop_remaining=stop_remaining, active_elapsed_ms=active_elapsed_ms,
        artifacts=artifacts,
    )


def load_evaluation_completion(
    journal: DevJournal, store: ArtifactStore, envelope: DevRunEnvelope,
) -> EvaluationCompletion | None:
    """Read and bind a committed completion before any workspace/provider preflight."""

    events = journal.events()
    finished = [event for event in events if event["event_type"] == "evaluator_finished"]
    if not finished:
        return None
    if len(finished) != 1:
        raise RecoveryError("development run has conflicting evaluator completions")
    try:
        completion = EvaluationCompletion.model_validate(finished[0]["payload"])
        raw = {name: store.read_bytes(artifact) for name, artifact in completion.artifacts.items()}
        manifest = RunManifest.model_validate_json(raw["manifest"])
        summary = json.loads(raw["evaluator_summary"])
        terminal_provenance = json.loads(raw["terminal_provenance"])
    except (ValidationError, ValueError, UnicodeError) as exc:
        raise RecoveryError("durable evaluator completion is invalid") from exc

    expected_manifest = {
        "run_id": envelope.run_id,
        "task_id": envelope.task_id,
        "task_version": envelope.task_version,
        "base_commit": envelope.base_commit,
        "public_spec_hash": envelope.public_spec_hash,
        "private_spec_hash": envelope.private_spec_hash,
        "task_content_hash": envelope.task_content_hash,
        "runtime_content_hash": envelope.runtime_hash,
        "model_hash": envelope.model_hash,
        "sandbox_identity_hash": envelope.sandbox_identity_hash,
        "sandbox_backend": envelope.sandbox_backend,
        "probe_image_digest": envelope.probe_image_digest,
        "probe_profile_hash": envelope.probe_profile_hash,
        "created_at": envelope.created_at,
        "submitted_patch_content_hash": completion.artifacts["submitted_patch"].content_hash,
        "visible_check_diff_hash": completion.artifacts["submitted_patch"].content_hash,
    }
    if completion.run_id != journal.run_id or any(
        getattr(manifest, key) != value for key, value in expected_manifest.items()
    ):
        raise RecoveryError("evaluator completion differs from its run envelope")
    if summary != completion.summary.model_dump() or terminal_provenance != _terminal_provenance(
        terminal=completion.terminal, summary_hash=completion.summary_hash,
        artifacts=completion.artifacts, runtime_hash=envelope.runtime_hash,
        task_hash=envelope.task_content_hash, model_hash=envelope.model_hash,
    ):
        raise RecoveryError("evaluator completion artifact binding is invalid")

    expected_events = {
        "submission_recorded": {
            "patch_hash": completion.artifacts["submitted_patch"].content_hash,
            "visible_check_diff_hash": completion.artifacts["submitted_patch"].content_hash,
            "changed_files": manifest.submitted_changed_files,
        },
        "manifest_recorded": {
            "manifest_content_hash": completion.artifacts["manifest"].content_hash,
            "submitted_patch_content_hash": completion.artifacts["submitted_patch"].content_hash,
        },
    }
    for event_type, expected in expected_events.items():
        recorded = [event for event in events if event["event_type"] == event_type]
        if (
            len(recorded) != 1 or recorded[0]["payload"] != expected
            or recorded[0]["sequence"] >= finished[0]["sequence"]
        ):
            raise RecoveryError("evaluator completion has no matching durable submission")

    expected_artifacts = {
        "submitted_patch", "manifest", "evaluator_summary", "terminal_provenance",
        *(f"probe_receipt_{index + 1}" for index in range(len(manifest.probe_evidence))),
    }
    if "evaluator_provenance" in completion.artifacts:
        expected_artifacts.add("evaluator_provenance")
    if set(completion.artifacts) != expected_artifacts:
        raise RecoveryError("evaluator completion artifact inventory is inconsistent")
    for index, evidence in enumerate(manifest.probe_evidence, start=1):
        if completion.artifacts[f"probe_receipt_{index}"].content_hash != evidence.content_hash:
            raise RecoveryError("evaluator completion probe binding is invalid")

    run_dir = store.root / "runs" / journal.run_id
    derived = {"manifest.json": "manifest", "provenance.json": "evaluator_provenance"}
    for filename, name in derived.items():
        if name not in raw:
            continue
        path = run_dir / filename
        if not path.is_file() or path.is_symlink() or path.read_bytes() != raw[name]:
            raise RecoveryError("evaluator completion differs from its recorded provenance")
    return completion
