"""Append-only source gate for held-out task/evaluator and persisted adapters.

R8 binds the metadata-only 12-task plan and the source that can later
materialize evaluator-v2 contracts and authenticate durable row evidence.  It
does not open task packages, materialize a task contract, authenticate a run,
refresh pricing, create a candidate, or authorize execution.

R7 remains byte-preserved as the zero-authority predecessor invalidated by the
formatting and contract-closure boundary advances.  R8 consumes the current R7
contract-source qualification.
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

SCHEMA_VERSION = "heldout-ac-binding-adapter-source-qualification-v6"
QUALIFICATION_ID = "core-ac-fixed-bundle-heldout-binding-adapter-20260815-r8"
STATUS = "OFFLINE_BINDING_ADAPTER_SOURCE_QUALIFIED_RUNTIME_MATERIALIZATION_CLOSED"
OUTPUT_PATH = Path(
    "reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r8.json"
)
R7_PATH = Path(
    "reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r7.json"
)
R7_CONTENT_HASH = "sha256:d1c8049f80e11b70e37895f6eca2ad7a56c74d890229f33ff2ec31d52e627b1b"
R7_SOURCE_HASH = "sha256:520d82d044edf8761a34946aca76eee4255cea10738bed138b46ac70a3644574"
R7_FILE_SHA256 = "sha256:9e9629570eae6fb2aaaeddd4be7f139a8cc0fc539f6a86cbfd5e8bf01ad76a0f"
R7_FILE_BYTES = 5_697
R7_CONTRACT_PATH = Path(
    "reports/heldout-ac/artifacts/heldout-ac-contract-source-qualification-r7.json"
)
R7_CONTRACT_CONTENT_HASH = "sha256:27cfb3d91c326c1e767a6e63580941d48e14a7872783db39dbdacdd075f08ea5"
R7_CONTRACT_FILE_SHA256 = "sha256:fec1c4ea12fdd8399f989ad9b0dba02a22071604eb8fc431f821ae5900ed36fa"
R7_CONTRACT_FILE_BYTES = 20_544
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


class R7Predecessor(FileBinding):
    path: Literal[
        "reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r7.json"
    ]
    file_bytes: Literal[R7_FILE_BYTES]
    file_sha256: Literal[R7_FILE_SHA256]
    source_qualification_hash: Literal[R7_CONTENT_HASH]
    source_hash: Literal[R7_SOURCE_HASH]
    contract_source_qualification_hash: Literal[
        "sha256:01b16ddfe83524e539fcc5624f74fa2f6922a9266f1095b1a6b992cdfd4c8fcf"
    ]
    original_status: Literal[
        "OFFLINE_BINDING_ADAPTER_SOURCE_QUALIFIED_RUNTIME_MATERIALIZATION_CLOSED"
    ]
    disposition: Literal["invalidated-by-formatting-and-contract-source-successor"]
    invalidation_reason: Literal["post-r7-formatting-and-contract-module-scope-boundary"]
    current_source_replay_valid: Literal[False]


class BindingProjection(HeldoutACFrozenModel):
    metadata_task_count: Literal[12]
    same_repo_task_count: Literal[6]
    cross_repo_task_count: Literal[6]
    task_evaluator_plan_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    r7_contract_source_replay_valid: Literal[True]
    metadata_task_bindings_present: Literal[True]
    task_package_files_opened: Literal[False]
    private_task_files_opened: Literal[False]
    task_evaluator_contract_materializations: Literal[0]
    task_evaluator_materializer_source_present: Literal[True]
    persisted_adapter_source_present: Literal[True]
    invokes_evaluator_v2_receipt_revalidation: Literal[True]
    invokes_read_only_trace_recomputation: Literal[True]
    full_trace_qualification_v2_projection_present: Literal[True]
    typed_completion_adapter_source_qualified: Literal[True]
    official_analysis_type_gate_source_qualified: Literal[True]
    typed_evaluator_confound_codes_preserved: Literal[True]
    runtime_authentication_capability_source_qualified: Literal[True]
    serialized_evidence_analysis_ineligible: Literal[True]
    persisted_official_replay_non_authorizing: Literal[True]
    authenticated_completion_cost_envelope_bound: Literal[True]
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
    predecessor: R7Predecessor
    contract_source_qualification: FileBinding
    contract_source_qualification_hash: Literal[R7_CONTRACT_CONTENT_HASH]
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
        if (
            self.contract_source_qualification.path != R7_CONTRACT_PATH.as_posix()
            or self.contract_source_qualification.file_bytes != R7_CONTRACT_FILE_BYTES
            or self.contract_source_qualification.file_sha256 != R7_CONTRACT_FILE_SHA256
        ):
            raise ValueError("held-out contract source qualification binding differs")
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


def _r7_predecessor(root: Path) -> R7Predecessor:
    raw = (root / R7_PATH).read_bytes()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HeldoutACBindingSourceQualificationError(
            "held-out R7 predecessor is invalid"
        ) from exc
    if (
        len(raw) != R7_FILE_BYTES
        or sha256_bytes(raw) != R7_FILE_SHA256
        or not isinstance(payload, dict)
        or payload.get("content_hash") != R7_CONTENT_HASH
        or payload.get("source_hash") != R7_SOURCE_HASH
        or payload.get("contract_source_qualification_hash")
        != "sha256:01b16ddfe83524e539fcc5624f74fa2f6922a9266f1095b1a6b992cdfd4c8fcf"
        or payload.get("status") != STATUS
        or (payload.get("projection") or {}).get("r6_contract_source_replay_valid") is not True
        or not isinstance(payload.get("authority"), dict)
        or not all(
            value is False
            or (type(value) is int and value == 0)
            or (type(value) is float and value == 0.0)
            for value in payload["authority"].values()
        )
        or not any(
            isinstance(item, dict)
            and isinstance(item.get("path"), str)
            and (root / item["path"]).is_file()
            and sha256_bytes((root / item["path"]).read_bytes()) != item.get("file_sha256")
            for item in (*payload.get("source_files", ()), *payload.get("validation_files", ()))
        )
    ):
        raise HeldoutACBindingSourceQualificationError("held-out R7 predecessor drifted")
    return R7Predecessor(
        path=R7_PATH.as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        source_qualification_hash=payload["content_hash"],
        source_hash=payload["source_hash"],
        contract_source_qualification_hash=payload["contract_source_qualification_hash"],
        original_status=payload["status"],
        disposition="invalidated-by-formatting-and-contract-source-successor",
        invalidation_reason="post-r7-formatting-and-contract-module-scope-boundary",
        current_source_replay_valid=False,
    )


def _build_candidate(root: Path, *, recorded_at: datetime) -> HeldoutACBindingSourceQualification:
    from patchloop.evals.heldout_ac_source_qualification import (
        validate_heldout_ac_source_qualification,
    )
    from patchloop.evals.heldout_ac_task_evaluator import (
        load_heldout_ac_task_evaluator_plan,
    )

    predecessor = _r7_predecessor(root)
    r7_summary = validate_heldout_ac_source_qualification(repository=root)
    if r7_summary.get("source_qualification_hash") != R7_CONTRACT_CONTENT_HASH:
        raise HeldoutACBindingSourceQualificationError("held-out R7 contract source replay differs")
    plan = load_heldout_ac_task_evaluator_plan(repository=root)
    source_files = tuple(_binding(root, item) for item in SOURCE_PATHS)
    validation_files = tuple(_binding(root, item) for item in VALIDATION_PATHS)
    projection = BindingProjection(
        metadata_task_count=len(plan.tasks),
        same_repo_task_count=sum(item.role == "core-same-repo" for item in plan.tasks),
        cross_repo_task_count=sum(item.role == "core-cross-repo" for item in plan.tasks),
        task_evaluator_plan_content_hash=plan.content_hash,
        r7_contract_source_replay_valid=True,
        metadata_task_bindings_present=True,
        task_package_files_opened=False,
        private_task_files_opened=False,
        task_evaluator_contract_materializations=0,
        task_evaluator_materializer_source_present=True,
        persisted_adapter_source_present=True,
        invokes_evaluator_v2_receipt_revalidation=True,
        invokes_read_only_trace_recomputation=True,
        full_trace_qualification_v2_projection_present=True,
        typed_completion_adapter_source_qualified=True,
        official_analysis_type_gate_source_qualified=True,
        typed_evaluator_confound_codes_preserved=True,
        runtime_authentication_capability_source_qualified=True,
        serialized_evidence_analysis_ineligible=True,
        persisted_official_replay_non_authorizing=True,
        authenticated_completion_cost_envelope_bound=True,
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
        "contract_source_qualification": _binding(root, R7_CONTRACT_PATH).model_dump(mode="json"),
        "contract_source_qualification_hash": R7_CONTRACT_CONTENT_HASH,
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
        contract_source_qualification=_binding(root, R7_CONTRACT_PATH),
        contract_source_qualification_hash=R7_CONTRACT_CONTENT_HASH,
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
        "contract_source_qualification_hash": payload.contract_source_qualification_hash,
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
    "R7_CONTENT_HASH",
    "R7_CONTRACT_CONTENT_HASH",
    "R7_CONTRACT_FILE_BYTES",
    "R7_CONTRACT_FILE_SHA256",
    "R7_CONTRACT_PATH",
    "R7_FILE_BYTES",
    "R7_FILE_SHA256",
    "R7_PATH",
    "R7_SOURCE_HASH",
    "SCHEMA_VERSION",
    "SOURCE_PATHS",
    "STATUS",
    "VALIDATION_PATHS",
    "HeldoutACBindingSourceQualification",
    "HeldoutACBindingSourceQualificationError",
    "run_heldout_ac_binding_source_qualification",
    "validate_heldout_ac_binding_source_qualification",
]
