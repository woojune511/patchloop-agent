"""Append-only source gate for held-out candidate and runtime-authority contracts.

The gate binds the dedicated held-out activation source and the existing
AgentRunner import closure.  It performs no readiness observation, credential
read, Docker/SDK probe, provider call, evaluator call, agent run, candidate
creation, reservation or spend.  A later no-call preflight may consume the
validated binding returned here.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator

from patchloop.errors import ContractError
from patchloop.evals.evaluator_v2_source_qualification import (
    _paid_path_import_closure,
)
from patchloop.evals.heldout_ac_contracts import HeldoutACFrozenModel
from patchloop.evals.heldout_ac_execution import (
    MATERIALIZATION_CONTENT_HASH,
    MATERIALIZATION_FILE_BYTES,
    MATERIALIZATION_FILE_SHA256,
    MATERIALIZATION_PATH,
    MATERIALIZATION_PRICING_HASH,
    MATERIALIZATION_TASK_BINDINGS_HASH,
    SUITE_PATH,
    HeldoutACFileBinding,
    HeldoutACSourceQualificationBinding,
)
from patchloop.evals.heldout_ac_suite import load_heldout_ac_suite
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_json

SCHEMA_VERSION = "heldout-ac-execution-source-qualification-v1"
QUALIFICATION_ID = "core-ac-fixed-bundle-heldout-execution-source-20260814-r1"
STATUS = "OFFLINE_EXECUTION_CONTRACT_SOURCE_QUALIFIED_NO_CANDIDATE"
OUTPUT_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-execution-source-qualification-r1.json")
NEXT_GATE = "run-dedicated-heldout-no-call-readiness-before-candidate"

SOURCE_ENTRYPOINTS = (
    Path("patchloop/agent/runner.py"),
    Path("patchloop/evals/heldout_ac_execution.py"),
)
SOURCE_EXTRAS = (
    Path("patchloop/evals/heldout_ac_execution_source_qualification.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)
VALIDATION_PATHS = (
    Path("scripts/build_heldout_ac_execution_source_qualification.py"),
    Path("tests/test_heldout_ac_execution.py"),
    Path("tests/test_heldout_ac_execution_source_qualification.py"),
)


class HeldoutACExecutionSourceQualificationError(ContractError):
    pass


class FileBinding(HeldoutACFrozenModel):
    path: str
    file_bytes: int = Field(gt=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class MaterializationBinding(FileBinding):
    path: Literal["reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r1.json"]
    file_bytes: Literal[MATERIALIZATION_FILE_BYTES]
    file_sha256: Literal[MATERIALIZATION_FILE_SHA256]
    content_hash: Literal[MATERIALIZATION_CONTENT_HASH]
    task_bindings_hash: Literal[MATERIALIZATION_TASK_BINDINGS_HASH]
    pricing_binding_hash: Literal[MATERIALIZATION_PRICING_HASH]


class ExecutionSourceProjection(HeldoutACFrozenModel):
    suite_id: Literal["core-ac-fixed-bundle-heldout-20260814-v1"]
    suite_content_hash: Literal[
        "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
    ]
    scheduled_rows: Literal[48]
    runtime_tuple_factory_present: Literal[True]
    candidate_factory_present: Literal[True]
    runtime_secret_encoder_present: Literal[True]
    evaluator_template_expander_present: Literal[True]
    run_manifest_v2_factory_present: Literal[True]
    completion_schedule_identity_match_test_bound: Literal[True]
    completion_cost_control_identity_match_test_bound: Literal[True]
    evaluator_v2_manifest_authority_test_bound: Literal[True]
    candidate_created: Literal[False]
    runtime_secret_markers_materialized: Literal[0]
    final_evaluator_contracts_materialized: Literal[0]


class QualificationAuthority(HeldoutACFrozenModel):
    offline_source_qualification_authorized: Literal[True]
    source_and_validation_file_reads_authorized: Literal[True]
    heldout_task_package_or_private_content_access_authorized: Literal[False]
    heldout_outcome_access_authorized: Literal[False]
    credential_presence_or_value_observation_authorized: Literal[False]
    runtime_secret_materialization_authorized: Literal[False]
    docker_or_sdk_observation_authorized: Literal[False]
    provider_evaluator_or_agent_execution_authorized: Literal[False]
    execution_candidate_authorized: Literal[False]
    approval_reservation_or_spend_authorized: Literal[False]
    official_analysis_or_claim_authorized: Literal[False]
    heldout_task_packages_opened: Literal[0]
    credential_values_observed: Literal[0]
    runtime_secret_markers_materialized: Literal[0]
    final_evaluator_contracts_materialized: Literal[0]
    candidates_created: Literal[0]
    provider_calls_made: Literal[0]
    evaluator_calls_made: Literal[0]
    agent_runs_made: Literal[0]
    docker_calls_made: Literal[0]
    sdk_calls_made: Literal[0]
    added_model_cost_usd: Literal[0.0]


class HeldoutACExecutionSourceQualification(HeldoutACFrozenModel):
    schema_version: Literal[SCHEMA_VERSION]
    qualification_id: Literal[QUALIFICATION_ID]
    status: Literal[STATUS]
    recorded_at: datetime
    suite: FileBinding
    materialization: MaterializationBinding
    source_entrypoints: tuple[str, ...] = Field(min_length=2, max_length=2)
    paid_path_import_closure: tuple[str, ...] = Field(min_length=1)
    paid_path_import_closure_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_files: tuple[FileBinding, ...] = Field(min_length=1)
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_files: tuple[FileBinding, ...] = Field(min_length=len(VALIDATION_PATHS))
    validation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projection: ExecutionSourceProjection
    authority: QualificationAuthority
    next_gate: Literal[NEXT_GATE]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_record(self) -> HeldoutACExecutionSourceQualification:
        if self.source_entrypoints != tuple(item.as_posix() for item in SOURCE_ENTRYPOINTS):
            raise ValueError("held-out execution source entrypoints differ")
        if self.paid_path_import_closure != tuple(sorted(self.paid_path_import_closure)):
            raise ValueError("held-out execution import closure is not canonical")
        if self.paid_path_import_closure_hash != sha256_json(list(self.paid_path_import_closure)):
            raise ValueError("held-out execution import closure hash differs")
        source_projection = [item.model_dump(mode="json") for item in self.source_files]
        validation_projection = [item.model_dump(mode="json") for item in self.validation_files]
        source_paths = {item.path for item in self.source_files}
        if not set(self.paid_path_import_closure).issubset(source_paths):
            raise ValueError("held-out execution source omits an imported module")
        if self.evaluator_source_hash != sha256_json(source_projection):
            raise ValueError("held-out evaluator source fingerprint differs")
        if self.validation_hash != sha256_json(validation_projection):
            raise ValueError("held-out execution validation fingerprint differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("held-out execution source qualification hash differs")
        return self


def _root(repository: str | Path | None) -> Path:
    return Path(repository).resolve() if repository is not None else repository_root().resolve()


def _binding(root: Path, relative: Path) -> FileBinding:
    selected = (root / relative).resolve()
    if not selected.is_relative_to(root) or selected.is_symlink() or not selected.is_file():
        raise HeldoutACExecutionSourceQualificationError(
            f"held-out execution source file is unavailable: {relative.as_posix()}"
        )
    raw = selected.read_bytes()
    return FileBinding(
        path=relative.as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
    )


def _materialization(root: Path) -> MaterializationBinding:
    selected = root / MATERIALIZATION_PATH
    try:
        raw = selected.read_bytes()
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise HeldoutACExecutionSourceQualificationError(
            "held-out R1 materialization is unavailable"
        ) from exc
    if not (
        len(raw) == MATERIALIZATION_FILE_BYTES
        and sha256_bytes(raw) == MATERIALIZATION_FILE_SHA256
        and isinstance(payload, dict)
        and payload.get("content_hash") == MATERIALIZATION_CONTENT_HASH
        and payload.get("task_bindings_hash") == MATERIALIZATION_TASK_BINDINGS_HASH
        and (payload.get("pricing") or {}).get("content_hash") == MATERIALIZATION_PRICING_HASH
    ):
        raise HeldoutACExecutionSourceQualificationError(
            "held-out R1 materialization bytes drifted"
        )
    return MaterializationBinding(
        path=MATERIALIZATION_PATH.as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=payload["content_hash"],
        task_bindings_hash=payload["task_bindings_hash"],
        pricing_binding_hash=payload["pricing"]["content_hash"],
    )


def _build_candidate(
    root: Path,
    *,
    recorded_at: datetime,
) -> HeldoutACExecutionSourceQualification:
    suite = load_heldout_ac_suite(SUITE_PATH, repository=root)
    closure = _paid_path_import_closure(root, entrypoints=SOURCE_ENTRYPOINTS)
    source_paths = tuple(
        sorted(
            {*closure, *SOURCE_EXTRAS},
            key=lambda item: item.as_posix(),
        )
    )
    source_files = tuple(_binding(root, item) for item in source_paths)
    validation_files = tuple(_binding(root, item) for item in VALIDATION_PATHS)
    source_projection = [item.model_dump(mode="json") for item in source_files]
    validation_projection = [item.model_dump(mode="json") for item in validation_files]
    body = {
        "schema_version": SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": STATUS,
        "recorded_at": recorded_at,
        "suite": _binding(root, SUITE_PATH).model_dump(mode="json"),
        "materialization": _materialization(root).model_dump(mode="json"),
        "source_entrypoints": tuple(item.as_posix() for item in SOURCE_ENTRYPOINTS),
        "paid_path_import_closure": tuple(item.as_posix() for item in closure),
        "paid_path_import_closure_hash": sha256_json([item.as_posix() for item in closure]),
        "source_files": tuple(source_projection),
        "evaluator_source_hash": sha256_json(source_projection),
        "validation_files": tuple(validation_projection),
        "validation_hash": sha256_json(validation_projection),
        "projection": {
            "suite_id": suite.suite_id,
            "suite_content_hash": suite.content_hash,
            "scheduled_rows": len(suite.schedule),
            "runtime_tuple_factory_present": True,
            "candidate_factory_present": True,
            "runtime_secret_encoder_present": True,
            "evaluator_template_expander_present": True,
            "run_manifest_v2_factory_present": True,
            "completion_schedule_identity_match_test_bound": True,
            "completion_cost_control_identity_match_test_bound": True,
            "evaluator_v2_manifest_authority_test_bound": True,
            "candidate_created": False,
            "runtime_secret_markers_materialized": 0,
            "final_evaluator_contracts_materialized": 0,
        },
        "authority": {
            "offline_source_qualification_authorized": True,
            "source_and_validation_file_reads_authorized": True,
            "heldout_task_package_or_private_content_access_authorized": False,
            "heldout_outcome_access_authorized": False,
            "credential_presence_or_value_observation_authorized": False,
            "runtime_secret_materialization_authorized": False,
            "docker_or_sdk_observation_authorized": False,
            "provider_evaluator_or_agent_execution_authorized": False,
            "execution_candidate_authorized": False,
            "approval_reservation_or_spend_authorized": False,
            "official_analysis_or_claim_authorized": False,
            "heldout_task_packages_opened": 0,
            "credential_values_observed": 0,
            "runtime_secret_markers_materialized": 0,
            "final_evaluator_contracts_materialized": 0,
            "candidates_created": 0,
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
    return HeldoutACExecutionSourceQualification(
        **body,
        content_hash=sha256_json(hash_body),
    )


def _canonical_bytes(payload: HeldoutACExecutionSourceQualification) -> bytes:
    return (payload.model_dump_json(indent=2) + "\n").encode("utf-8")


def _load_validated(
    root: Path,
) -> tuple[HeldoutACExecutionSourceQualification, bytes]:
    selected = root / OUTPUT_PATH
    try:
        raw = selected.read_bytes()
        payload = HeldoutACExecutionSourceQualification.model_validate_json(raw)
    except (OSError, ValidationError) as exc:
        raise HeldoutACExecutionSourceQualificationError(
            "held-out execution source qualification is invalid"
        ) from exc
    if raw != _canonical_bytes(payload):
        raise HeldoutACExecutionSourceQualificationError(
            "held-out execution source qualification is not canonical"
        )
    expected = _build_candidate(root, recorded_at=payload.recorded_at)
    if payload != expected:
        raise HeldoutACExecutionSourceQualificationError(
            "held-out execution source qualification has drifted"
        )
    return payload, raw


def _summary(
    payload: HeldoutACExecutionSourceQualification,
    raw: bytes,
) -> dict[str, object]:
    return {
        "status": payload.status,
        "qualification_id": payload.qualification_id,
        "source_qualification_hash": payload.content_hash,
        "evaluator_source_hash": payload.evaluator_source_hash,
        "suite_content_hash": payload.projection.suite_content_hash,
        "scheduled_rows": payload.projection.scheduled_rows,
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


def validate_heldout_ac_execution_source_qualification(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    payload, raw = _load_validated(_root(repository))
    return _summary(payload, raw)


def load_heldout_ac_execution_source_binding(
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


def run_heldout_ac_execution_source_qualification(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    root = _root(repository)
    output = root / OUTPUT_PATH
    if output.exists():
        return validate_heldout_ac_execution_source_qualification(repository=root)
    payload = _build_candidate(root, recorded_at=datetime.now(UTC))
    raw = _canonical_bytes(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise HeldoutACExecutionSourceQualificationError(
            "held-out execution source qualification already exists"
        ) from None
    validated, observed = _load_validated(root)
    if validated != payload or observed != raw:
        raise HeldoutACExecutionSourceQualificationError(
            "held-out execution source qualification reread differs"
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
    "HeldoutACExecutionSourceQualification",
    "HeldoutACExecutionSourceQualificationError",
    "load_heldout_ac_execution_source_binding",
    "run_heldout_ac_execution_source_qualification",
    "validate_heldout_ac_execution_source_qualification",
]
