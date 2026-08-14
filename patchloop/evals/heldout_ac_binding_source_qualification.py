"""Append-only source gate for held-out task/evaluator and persisted adapters.

R5 binds the metadata-only 12-task plan and the source that can later
materialize evaluator-v2 contracts and authenticate durable row evidence.  It
does not open task packages, materialize a task contract, authenticate a run,
refresh pricing, create a candidate, or authorize execution.

R4 remains byte-preserved as the semantically complete predecessor superseded
only to make the final bound Python/test source formatter-conformant.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_contracts import HeldoutACFrozenModel
from patchloop.runtime import repository_root
from patchloop.util import safe_relative_path, sha256_bytes, sha256_json

SCHEMA_VERSION = "heldout-ac-binding-adapter-source-qualification-v3"
QUALIFICATION_ID = "core-ac-fixed-bundle-heldout-binding-adapter-20260814-r5"
STATUS = "OFFLINE_BINDING_ADAPTER_SOURCE_QUALIFIED_RUNTIME_MATERIALIZATION_CLOSED"
OUTPUT_PATH = Path(
    "reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r5.json"
)
R4_PATH = Path(
    "reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r4.json"
)
R4_CONTENT_HASH = "sha256:4d44fdcc2639ca2daf71933428cb87adb2fbbfc13a7dc3293354d5eadd8171cc"
R4_FILE_SHA256 = "sha256:d2aeffece5c5b4dbeb44848a71b9667b3321b574ae72653d6fa86e0113f9eb17"
R4_FILE_BYTES = 4_666
R3_PATH = Path(
    "reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r3.json"
)
R3_CONTENT_HASH = "sha256:7c8c1c57422a2bf52ddd20e53b473c2dfe3afb5d34ee86b8f58efa8a9f138ea9"
R3_FILE_SHA256 = "sha256:5ac2aa90f8d74e467ace9a6b46377516fc9d4c5397042bca36ebd701e0df88f1"
R3_FILE_BYTES = 4_366
R2_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-contract-source-qualification-r2.json")
R2_CONTENT_HASH = "sha256:0277225b0992b8e0562b21f5f8c2f8dcc4921017bea03b5087c4f6dd0e860172"
R2_FILE_SHA256 = "sha256:5f5406858603d918f296ca7b4a7bf2d62426c99a5915481964ed41f91c6b961c"
R2_FILE_BYTES = 20_052
NEXT_GATE = "authorized-task-package-materialization-and-fresh-pricing-before-candidate"

SOURCE_PATHS = tuple(
    sorted(
        (
            Path("patchloop/evals/heldout_ac_binding_source_qualification.py"),
            Path("patchloop/evals/heldout_ac_persisted_adapter.py"),
            Path("patchloop/evals/heldout_ac_task_evaluator.py"),
        ),
        key=lambda item: item.as_posix(),
    )
)
VALIDATION_PATHS = tuple(
    sorted(
        (
            Path("scripts/build_heldout_ac_binding_source_qualification.py"),
            Path("tests/test_heldout_ac_binding_source_qualification.py"),
            Path("tests/test_heldout_ac_persisted_adapter.py"),
            Path("tests/test_heldout_ac_task_evaluator.py"),
        ),
        key=lambda item: item.as_posix(),
    )
)


class HeldoutACBindingSourceQualificationError(ContractError):
    pass


class FileBinding(HeldoutACFrozenModel):
    path: str
    file_bytes: int = Field(ge=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return safe_relative_path(value, field_name="held-out binding source path")


class R4Predecessor(FileBinding):
    path: Literal[
        "reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r4.json"
    ]
    file_bytes: Literal[R4_FILE_BYTES]
    file_sha256: Literal[R4_FILE_SHA256]
    source_qualification_hash: Literal[R4_CONTENT_HASH]
    original_status: Literal[
        "OFFLINE_BINDING_ADAPTER_SOURCE_QUALIFIED_RUNTIME_MATERIALIZATION_CLOSED"
    ]
    disposition: Literal["superseded-by-final-format-conformance"]
    current_source_replay_valid: Literal[False]
    r3_source_qualification_hash: Literal[R3_CONTENT_HASH]
    r2_source_qualification_hash: Literal[R2_CONTENT_HASH]


class BindingProjection(HeldoutACFrozenModel):
    metadata_task_count: Literal[12]
    same_repo_task_count: Literal[6]
    cross_repo_task_count: Literal[6]
    task_evaluator_plan_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    r2_contract_source_replay_valid: Literal[True]
    metadata_task_bindings_present: Literal[True]
    task_package_files_opened: Literal[False]
    private_task_files_opened: Literal[False]
    task_evaluator_contract_materializations: Literal[0]
    task_evaluator_materializer_source_present: Literal[True]
    persisted_adapter_source_present: Literal[True]
    invokes_evaluator_v2_receipt_revalidation: Literal[True]
    invokes_read_only_trace_recomputation: Literal[True]
    authenticated_persisted_rows: Literal[0]
    authoritative_complete_matrix_present: Literal[False]
    official_analysis_present: Literal[False]


class ClosedAuthority(HeldoutACFrozenModel):
    heldout_task_package_access_authorized: Literal[False] = False
    heldout_private_content_access_authorized: Literal[False] = False
    task_evaluator_contract_materialization_authorized: Literal[False] = False
    persisted_runtime_evidence_access_authorized: Literal[False] = False
    pricing_refresh_authorized: Literal[False] = False
    docker_sdk_or_credential_observation_authorized: Literal[False] = False
    provider_evaluator_or_agent_execution_authorized: Literal[False] = False
    execution_candidate_authorized: Literal[False] = False
    approval_reservation_or_spend_authorized: Literal[False] = False
    official_analysis_or_claim_authorized: Literal[False] = False
    task_packages_opened: Literal[0] = 0
    task_evaluator_contracts_materialized: Literal[0] = 0
    persisted_rows_authenticated: Literal[0] = 0
    provider_calls_made: Literal[0] = 0
    evaluator_calls_made: Literal[0] = 0
    agent_runs_made: Literal[0] = 0
    docker_calls_made: Literal[0] = 0
    sdk_calls_made: Literal[0] = 0
    added_model_cost_usd: Literal[0.0] = 0.0


class HeldoutACBindingSourceQualification(HeldoutACFrozenModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    qualification_id: Literal[QUALIFICATION_ID] = QUALIFICATION_ID
    status: Literal[STATUS] = STATUS
    recorded_at: datetime
    predecessor: R4Predecessor
    suite_content_hash: Literal[
        "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
    ]
    dataset_manifest_file_sha256: Literal[
        "sha256:e8cf14ca9dabebcc03c3522e400dfcb79606541e9b11e59f49510ea5c40bebed"
    ]
    source_files: tuple[FileBinding, ...] = Field(min_length=3, max_length=3)
    source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_files: tuple[FileBinding, ...] = Field(min_length=4, max_length=4)
    validation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projection: BindingProjection
    authority: ClosedAuthority
    next_gate: Literal[NEXT_GATE] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_inventory_and_hashes(self) -> HeldoutACBindingSourceQualification:
        source_paths = tuple(item.path for item in self.source_files)
        validation_paths = tuple(item.path for item in self.validation_files)
        if source_paths != tuple(item.as_posix() for item in SOURCE_PATHS):
            raise ValueError("held-out binding source inventory differs")
        if validation_paths != tuple(item.as_posix() for item in VALIDATION_PATHS):
            raise ValueError("held-out binding validation inventory differs")
        if self.source_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ):
            raise ValueError("held-out binding source hash mismatch")
        if self.validation_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("held-out binding validation hash mismatch")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out binding source qualification content hash mismatch")
        return self


def _root(repository: str | Path | None) -> Path:
    return Path(repository).resolve() if repository is not None else repository_root().resolve()


def _binding(root: Path, relative: Path) -> FileBinding:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path.is_symlink() or not path.is_file():
        raise HeldoutACBindingSourceQualificationError(
            f"held-out binding source path is unavailable: {relative.as_posix()}"
        )
    raw = path.read_bytes()
    return FileBinding(path=relative.as_posix(), file_bytes=len(raw), file_sha256=sha256_bytes(raw))


def _r4_predecessor(root: Path) -> R4Predecessor:
    raw = (root / R4_PATH).read_bytes()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HeldoutACBindingSourceQualificationError(
            "held-out R4 predecessor is invalid"
        ) from exc
    if (
        len(raw) != R4_FILE_BYTES
        or sha256_bytes(raw) != R4_FILE_SHA256
        or not isinstance(payload, dict)
        or payload.get("content_hash") != R4_CONTENT_HASH
        or payload.get("status") != STATUS
        or (payload.get("predecessor") or {}).get("source_qualification_hash") != R3_CONTENT_HASH
        or (payload.get("predecessor") or {}).get("r2_source_qualification_hash") != R2_CONTENT_HASH
        or (payload.get("projection") or {}).get("r2_contract_source_replay_valid") is not True
    ):
        raise HeldoutACBindingSourceQualificationError("held-out R4 predecessor drifted")
    return R4Predecessor(
        path=R4_PATH.as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        source_qualification_hash=payload["content_hash"],
        original_status=payload["status"],
        disposition="superseded-by-final-format-conformance",
        current_source_replay_valid=False,
        r3_source_qualification_hash=R3_CONTENT_HASH,
        r2_source_qualification_hash=R2_CONTENT_HASH,
    )


def _build_candidate(root: Path, *, recorded_at: datetime) -> HeldoutACBindingSourceQualification:
    from patchloop.evals.heldout_ac_source_qualification import (
        validate_heldout_ac_source_qualification,
    )
    from patchloop.evals.heldout_ac_task_evaluator import (
        load_heldout_ac_task_evaluator_plan,
    )

    predecessor = _r4_predecessor(root)
    r2_summary = validate_heldout_ac_source_qualification(repository=root)
    if r2_summary.get("source_qualification_hash") != R2_CONTENT_HASH:
        raise HeldoutACBindingSourceQualificationError("held-out R2 contract source replay differs")
    plan = load_heldout_ac_task_evaluator_plan(repository=root)
    source_files = tuple(_binding(root, item) for item in SOURCE_PATHS)
    validation_files = tuple(_binding(root, item) for item in VALIDATION_PATHS)
    projection = BindingProjection(
        metadata_task_count=len(plan.tasks),
        same_repo_task_count=sum(item.role == "core-same-repo" for item in plan.tasks),
        cross_repo_task_count=sum(item.role == "core-cross-repo" for item in plan.tasks),
        task_evaluator_plan_content_hash=plan.content_hash,
        r2_contract_source_replay_valid=True,
        metadata_task_bindings_present=True,
        task_package_files_opened=False,
        private_task_files_opened=False,
        task_evaluator_contract_materializations=0,
        task_evaluator_materializer_source_present=True,
        persisted_adapter_source_present=True,
        invokes_evaluator_v2_receipt_revalidation=True,
        invokes_read_only_trace_recomputation=True,
        authenticated_persisted_rows=0,
        authoritative_complete_matrix_present=False,
        official_analysis_present=False,
    )
    body = {
        "schema_version": SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": STATUS,
        "recorded_at": recorded_at.isoformat().replace("+00:00", "Z"),
        "predecessor": predecessor.model_dump(mode="json"),
        "suite_content_hash": plan.suite_content_hash,
        "dataset_manifest_file_sha256": plan.dataset_manifest_file_sha256,
        "source_files": [item.model_dump(mode="json") for item in source_files],
        "source_hash": sha256_json([item.model_dump(mode="json") for item in source_files]),
        "validation_files": [item.model_dump(mode="json") for item in validation_files],
        "validation_hash": sha256_json([item.model_dump(mode="json") for item in validation_files]),
        "projection": projection.model_dump(mode="json"),
        "authority": ClosedAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    return HeldoutACBindingSourceQualification(
        schema_version=SCHEMA_VERSION,
        qualification_id=QUALIFICATION_ID,
        status=STATUS,
        recorded_at=recorded_at,
        predecessor=predecessor,
        suite_content_hash=plan.suite_content_hash,
        dataset_manifest_file_sha256=plan.dataset_manifest_file_sha256,
        source_files=source_files,
        source_hash=body["source_hash"],
        validation_files=validation_files,
        validation_hash=body["validation_hash"],
        projection=projection,
        authority=ClosedAuthority(),
        next_gate=NEXT_GATE,
        content_hash=sha256_json(body),
    )


def _canonical_bytes(value: HeldoutACBindingSourceQualification) -> bytes:
    return (value.model_dump_json(indent=2) + "\n").encode("utf-8")


def _load_validated(root: Path) -> tuple[HeldoutACBindingSourceQualification, bytes]:
    path = (root / OUTPUT_PATH).resolve()
    try:
        raw = path.read_bytes()
        payload = HeldoutACBindingSourceQualification.model_validate_json(raw)
    except (OSError, ValidationError) as exc:
        raise HeldoutACBindingSourceQualificationError(
            "held-out binding source qualification is invalid"
        ) from exc
    if raw != _canonical_bytes(payload):
        raise HeldoutACBindingSourceQualificationError(
            "held-out binding source qualification bytes are not canonical"
        )
    expected = _build_candidate(root, recorded_at=payload.recorded_at)
    if payload != expected:
        raise HeldoutACBindingSourceQualificationError(
            "held-out binding source qualification has drifted"
        )
    return payload, raw


def _summary(payload: HeldoutACBindingSourceQualification, raw: bytes) -> dict[str, object]:
    return {
        "status": payload.status,
        "qualification_id": payload.qualification_id,
        "source_qualification_hash": payload.content_hash,
        "predecessor_source_qualification_hash": payload.predecessor.source_qualification_hash,
        "source_hash": payload.source_hash,
        "task_evaluator_plan_content_hash": payload.projection.task_evaluator_plan_content_hash,
        "metadata_task_bindings": payload.projection.metadata_task_count,
        "task_evaluator_contract_materializations": 0,
        "authenticated_persisted_rows": 0,
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_authorized": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "agent_runs_made": 0,
        "docker_calls_made": 0,
        "sdk_calls_made": 0,
        "added_model_cost_usd": 0.0,
    }


def validate_heldout_ac_binding_source_qualification(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    root = _root(repository)
    payload, raw = _load_validated(root)
    return _summary(payload, raw)


def run_heldout_ac_binding_source_qualification(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    root = _root(repository)
    output = (root / OUTPUT_PATH).resolve()
    if output.exists():
        return validate_heldout_ac_binding_source_qualification(repository=root)
    payload = _build_candidate(root, recorded_at=datetime.now(UTC))
    content = _canonical_bytes(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise HeldoutACBindingSourceQualificationError(
            "held-out binding source qualification already exists"
        ) from None
    validated, raw = _load_validated(root)
    if raw != content or validated != payload:
        raise HeldoutACBindingSourceQualificationError(
            "held-out binding source qualification reread differs"
        )
    return _summary(validated, raw)


__all__ = [
    "NEXT_GATE",
    "OUTPUT_PATH",
    "QUALIFICATION_ID",
    "R4_CONTENT_HASH",
    "R4_FILE_BYTES",
    "R4_FILE_SHA256",
    "R4_PATH",
    "R3_CONTENT_HASH",
    "R3_FILE_BYTES",
    "R3_FILE_SHA256",
    "R3_PATH",
    "R2_CONTENT_HASH",
    "R2_FILE_BYTES",
    "R2_FILE_SHA256",
    "R2_PATH",
    "SCHEMA_VERSION",
    "SOURCE_PATHS",
    "STATUS",
    "VALIDATION_PATHS",
    "HeldoutACBindingSourceQualification",
    "HeldoutACBindingSourceQualificationError",
    "run_heldout_ac_binding_source_qualification",
    "validate_heldout_ac_binding_source_qualification",
]
