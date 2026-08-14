"""Successor source gate for the dedicated held-out no-call preflight."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator

from patchloop.errors import ContractError
from patchloop.evals.evaluator_v2_source_qualification import _paid_path_import_closure
from patchloop.evals.heldout_ac_contracts import HeldoutACFrozenModel
from patchloop.evals.heldout_ac_execution import (
    HeldoutACFileBinding,
    HeldoutACSourceQualificationBinding,
)
from patchloop.evals.heldout_ac_execution_source_qualification import (
    OUTPUT_PATH as R1_PATH,
)
from patchloop.evals.heldout_ac_execution_source_qualification import (
    validate_heldout_ac_execution_source_qualification,
)
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_json

SCHEMA_VERSION = "heldout-ac-preflight-source-qualification-v1"
QUALIFICATION_ID = "core-ac-fixed-bundle-heldout-preflight-source-20260814-r2"
STATUS = "OFFLINE_NO_CALL_PREFLIGHT_SOURCE_QUALIFIED_CANDIDATE_CLOSED"
OUTPUT_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r2.json")
NEXT_GATE = "run-heldout-no-call-preflight-on-clean-committed-source"

SOURCE_ENTRYPOINTS = (
    Path("patchloop/agent/runner.py"),
    Path("patchloop/evals/heldout_ac_preflight.py"),
)
SOURCE_EXTRAS = (
    Path("patchloop/evals/heldout_ac_preflight_source_qualification.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)
VALIDATION_PATHS = (
    Path("scripts/build_heldout_ac_execution_source_qualification.py"),
    Path("scripts/build_heldout_ac_preflight_source_qualification.py"),
    Path("scripts/run_heldout_ac_preflight.py"),
    Path("tests/test_heldout_ac_execution.py"),
    Path("tests/test_heldout_ac_execution_source_qualification.py"),
    Path("tests/test_heldout_ac_preflight.py"),
    Path("tests/test_heldout_ac_preflight_source_qualification.py"),
)


class HeldoutACPreflightSourceQualificationError(ContractError):
    pass


class FileBinding(HeldoutACFrozenModel):
    path: str
    file_bytes: int = Field(gt=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class R1Binding(FileBinding):
    path: Literal["reports/heldout-ac/artifacts/heldout-ac-execution-source-qualification-r1.json"]
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_status: Literal["OFFLINE_EXECUTION_CONTRACT_SOURCE_QUALIFIED_NO_CANDIDATE"]


class PreflightProjection(HeldoutACFrozenModel):
    suite_content_hash: Literal[
        "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
    ]
    scheduled_rows: Literal[48]
    r1_source_replay_valid: Literal[True]
    git_commit_tree_and_execution_clean_observation_present: Literal[True]
    digest_pinned_docker_image_observation_present: Literal[True]
    sdk_version_observation_present: Literal[True]
    credential_presence_only_boundary_present: Literal[True]
    custom_base_url_block_present: Literal[True]
    candidate_factory_bound: Literal[True]
    blocked_preflight_candidate_count: Literal[0]
    execution_candidates_created: Literal[0]


class QualificationAuthority(HeldoutACFrozenModel):
    offline_source_qualification_authorized: Literal[True]
    source_and_validation_file_reads_authorized: Literal[True]
    git_docker_sdk_or_credential_observation_authorized: Literal[False]
    heldout_task_package_or_private_content_access_authorized: Literal[False]
    heldout_outcome_access_authorized: Literal[False]
    runtime_secret_materialization_authorized: Literal[False]
    provider_evaluator_or_agent_execution_authorized: Literal[False]
    execution_candidate_authorized: Literal[False]
    approval_reservation_or_spend_authorized: Literal[False]
    official_analysis_or_claim_authorized: Literal[False]
    execution_candidates_created: Literal[0]
    credential_values_observed: Literal[0]
    provider_calls_made: Literal[0]
    evaluator_calls_made: Literal[0]
    agent_runs_made: Literal[0]
    docker_calls_made: Literal[0]
    sdk_calls_made: Literal[0]
    added_model_cost_usd: Literal[0.0]


class HeldoutACPreflightSourceQualification(HeldoutACFrozenModel):
    schema_version: Literal[SCHEMA_VERSION]
    qualification_id: Literal[QUALIFICATION_ID]
    status: Literal[STATUS]
    recorded_at: datetime
    predecessor: R1Binding
    source_entrypoints: tuple[str, ...] = Field(min_length=2, max_length=2)
    import_closure: tuple[str, ...] = Field(min_length=1)
    import_closure_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_files: tuple[FileBinding, ...] = Field(min_length=1)
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_files: tuple[FileBinding, ...] = Field(min_length=len(VALIDATION_PATHS))
    validation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projection: PreflightProjection
    authority: QualificationAuthority
    next_gate: Literal[NEXT_GATE]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_record(self) -> HeldoutACPreflightSourceQualification:
        if self.source_entrypoints != tuple(item.as_posix() for item in SOURCE_ENTRYPOINTS):
            raise ValueError("held-out preflight entrypoints differ")
        if self.import_closure != tuple(sorted(self.import_closure)):
            raise ValueError("held-out preflight import closure is not canonical")
        if self.import_closure_hash != sha256_json(list(self.import_closure)):
            raise ValueError("held-out preflight import closure hash differs")
        source_projection = [item.model_dump(mode="json") for item in self.source_files]
        validation_projection = [item.model_dump(mode="json") for item in self.validation_files]
        if not set(self.import_closure).issubset({item.path for item in self.source_files}):
            raise ValueError("held-out preflight source omits an imported module")
        if self.evaluator_source_hash != sha256_json(source_projection):
            raise ValueError("held-out preflight source fingerprint differs")
        if self.validation_hash != sha256_json(validation_projection):
            raise ValueError("held-out preflight validation fingerprint differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("held-out preflight source qualification hash differs")
        return self


def _root(repository: str | Path | None) -> Path:
    return Path(repository).resolve() if repository is not None else repository_root().resolve()


def _binding(root: Path, relative: Path) -> FileBinding:
    selected = (root / relative).resolve()
    if not selected.is_relative_to(root) or selected.is_symlink() or not selected.is_file():
        raise HeldoutACPreflightSourceQualificationError(
            f"held-out preflight source file is unavailable: {relative.as_posix()}"
        )
    raw = selected.read_bytes()
    return FileBinding(
        path=relative.as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
    )


def _r1_binding(root: Path) -> R1Binding:
    summary = validate_heldout_ac_execution_source_qualification(repository=root)
    selected = root / R1_PATH
    raw = selected.read_bytes()
    return R1Binding(
        path=R1_PATH.as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        source_qualification_hash=str(summary["source_qualification_hash"]),
        evaluator_source_hash=str(summary["evaluator_source_hash"]),
        original_status=str(summary["status"]),
    )


def _build_candidate(
    root: Path,
    *,
    recorded_at: datetime,
) -> HeldoutACPreflightSourceQualification:
    predecessor = _r1_binding(root)
    closure = _paid_path_import_closure(root, entrypoints=SOURCE_ENTRYPOINTS)
    source_paths = tuple(sorted({*closure, *SOURCE_EXTRAS}, key=lambda item: item.as_posix()))
    source_files = tuple(_binding(root, item) for item in source_paths)
    validation_files = tuple(_binding(root, item) for item in VALIDATION_PATHS)
    source_projection = [item.model_dump(mode="json") for item in source_files]
    validation_projection = [item.model_dump(mode="json") for item in validation_files]
    body = {
        "schema_version": SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": STATUS,
        "recorded_at": recorded_at,
        "predecessor": predecessor.model_dump(mode="json"),
        "source_entrypoints": tuple(item.as_posix() for item in SOURCE_ENTRYPOINTS),
        "import_closure": tuple(item.as_posix() for item in closure),
        "import_closure_hash": sha256_json([item.as_posix() for item in closure]),
        "source_files": tuple(source_projection),
        "evaluator_source_hash": sha256_json(source_projection),
        "validation_files": tuple(validation_projection),
        "validation_hash": sha256_json(validation_projection),
        "projection": {
            "suite_content_hash": (
                "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
            ),
            "scheduled_rows": 48,
            "r1_source_replay_valid": True,
            "git_commit_tree_and_execution_clean_observation_present": True,
            "digest_pinned_docker_image_observation_present": True,
            "sdk_version_observation_present": True,
            "credential_presence_only_boundary_present": True,
            "custom_base_url_block_present": True,
            "candidate_factory_bound": True,
            "blocked_preflight_candidate_count": 0,
            "execution_candidates_created": 0,
        },
        "authority": {
            "offline_source_qualification_authorized": True,
            "source_and_validation_file_reads_authorized": True,
            "git_docker_sdk_or_credential_observation_authorized": False,
            "heldout_task_package_or_private_content_access_authorized": False,
            "heldout_outcome_access_authorized": False,
            "runtime_secret_materialization_authorized": False,
            "provider_evaluator_or_agent_execution_authorized": False,
            "execution_candidate_authorized": False,
            "approval_reservation_or_spend_authorized": False,
            "official_analysis_or_claim_authorized": False,
            "execution_candidates_created": 0,
            "credential_values_observed": 0,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "agent_runs_made": 0,
            "docker_calls_made": 0,
            "sdk_calls_made": 0,
            "added_model_cost_usd": 0.0,
        },
        "next_gate": NEXT_GATE,
    }
    hash_body = {
        **body,
        "recorded_at": recorded_at.isoformat().replace("+00:00", "Z"),
    }
    return HeldoutACPreflightSourceQualification(
        **body,
        content_hash=sha256_json(hash_body),
    )


def _canonical_bytes(payload: HeldoutACPreflightSourceQualification) -> bytes:
    return (payload.model_dump_json(indent=2) + "\n").encode("utf-8")


def _load_validated(root: Path) -> tuple[HeldoutACPreflightSourceQualification, bytes]:
    selected = root / OUTPUT_PATH
    try:
        raw = selected.read_bytes()
        payload = HeldoutACPreflightSourceQualification.model_validate_json(raw)
    except (OSError, ValidationError) as exc:
        raise HeldoutACPreflightSourceQualificationError(
            "held-out preflight source qualification is invalid"
        ) from exc
    if raw != _canonical_bytes(payload):
        raise HeldoutACPreflightSourceQualificationError(
            "held-out preflight source qualification is not canonical"
        )
    if payload != _build_candidate(root, recorded_at=payload.recorded_at):
        raise HeldoutACPreflightSourceQualificationError(
            "held-out preflight source qualification has drifted"
        )
    return payload, raw


def _summary(
    payload: HeldoutACPreflightSourceQualification,
    raw: bytes,
) -> dict[str, object]:
    return {
        "status": payload.status,
        "qualification_id": payload.qualification_id,
        "source_qualification_hash": payload.content_hash,
        "evaluator_source_hash": payload.evaluator_source_hash,
        "predecessor_source_qualification_hash": (payload.predecessor.source_qualification_hash),
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_candidate_created": False,
        "credential_values_observed": 0,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "agent_runs_made": 0,
        "docker_calls_made": 0,
        "sdk_calls_made": 0,
        "added_model_cost_usd": 0.0,
        "next_gate": payload.next_gate,
    }


def validate_heldout_ac_preflight_source_qualification(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    payload, raw = _load_validated(_root(repository))
    return _summary(payload, raw)


def load_heldout_ac_preflight_source_binding(
    *, repository: str | Path | None = None
) -> HeldoutACSourceQualificationBinding:
    payload, raw = _load_validated(_root(repository))
    return HeldoutACSourceQualificationBinding(
        schema_version="heldout-ac-execution-source-qualification-binding-v1",
        qualification_id=payload.qualification_id,
        qualification_file=HeldoutACFileBinding(
            path=OUTPUT_PATH.as_posix(),
            file_bytes=len(raw),
            file_sha256=sha256_bytes(raw),
            content_hash=payload.content_hash,
        ),
        source_qualification_hash=payload.content_hash,
        evaluator_source_hash=payload.evaluator_source_hash,
        source_replay_valid=True,
        provider_evaluator_agent_calls_made=0,
    )


def run_heldout_ac_preflight_source_qualification(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    root = _root(repository)
    output = root / OUTPUT_PATH
    if output.exists():
        return validate_heldout_ac_preflight_source_qualification(repository=root)
    payload = _build_candidate(root, recorded_at=datetime.now(UTC))
    raw = _canonical_bytes(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise HeldoutACPreflightSourceQualificationError(
            "held-out preflight source qualification already exists"
        ) from None
    validated, observed = _load_validated(root)
    if validated != payload or observed != raw:
        raise HeldoutACPreflightSourceQualificationError(
            "held-out preflight source qualification reread differs"
        )
    return _summary(validated, observed)


__all__ = [
    "NEXT_GATE",
    "OUTPUT_PATH",
    "QUALIFICATION_ID",
    "SCHEMA_VERSION",
    "SOURCE_ENTRYPOINTS",
    "SOURCE_EXTRAS",
    "STATUS",
    "VALIDATION_PATHS",
    "HeldoutACPreflightSourceQualification",
    "HeldoutACPreflightSourceQualificationError",
    "load_heldout_ac_preflight_source_binding",
    "run_heldout_ac_preflight_source_qualification",
    "validate_heldout_ac_preflight_source_qualification",
]
