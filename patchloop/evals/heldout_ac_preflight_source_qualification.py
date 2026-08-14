"""Successor source gate for the held-out preflight and paid dispatcher.

R2 through R12 remain immutable.  R13 binds the append-only R11 campaign
correction index and the closed lifecycle/replay contracts required before a
fresh candidate can exist.  It grants no observation, candidate, approval,
execution, or spend authority.
"""

from __future__ import annotations

import json
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
from patchloop.evals.heldout_ac_r11_campaign_evidence import (
    EVIDENCE_ID as R11_CAMPAIGN_EVIDENCE_ID,
)
from patchloop.evals.heldout_ac_r11_campaign_evidence import (
    EXECUTION_HASH as R11_EXECUTION_HASH,
)
from patchloop.evals.heldout_ac_r11_campaign_evidence import (
    OUTPUT_PATH as R11_CAMPAIGN_EVIDENCE_PATH,
)
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_json

SCHEMA_VERSION = "heldout-ac-preflight-dispatch-source-qualification-v12"
QUALIFICATION_ID = "core-ac-fixed-bundle-heldout-preflight-source-20260815-r13"
STATUS = "OFFLINE_PREFLIGHT_AND_DISPATCH_SOURCE_QUALIFIED_EXECUTION_CLOSED"
OUTPUT_PATH = Path(
    "reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r13.json"
)
R12_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r12.json")
R11_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r11.json")
R10_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r10.json")
R9_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r9.json")
R8_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r8.json")
R7_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r7.json")
R7_CAMPAIGN_EVIDENCE_PATH = Path(
    "reports/heldout-ac/artifacts/heldout-ac-r7-campaign-inconclusive-r1.json"
)
R6_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r6.json")
R5_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r5.json")
R4_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r4.json")
R3_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r3.json")
R2_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r2.json")
NEXT_GATE = "run-fresh-heldout-no-call-preflight-on-clean-committed-successor"

SOURCE_ENTRYPOINTS = (
    Path("patchloop/evals/heldout_ac_preflight.py"),
    Path("patchloop/evals/heldout_ac_dispatcher.py"),
)
SOURCE_EXTRAS = (
    Path("patchloop/evals/heldout_ac_preflight_source_qualification.py"),
    Path("patchloop/evals/heldout_ac_r11_campaign_evidence.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)
VALIDATION_PATHS = (
    Path("scripts/build_heldout_ac_execution_source_qualification.py"),
    Path("scripts/build_heldout_ac_preflight_source_qualification.py"),
    Path("scripts/build_heldout_ac_r11_campaign_evidence.py"),
    Path("scripts/run_heldout_ac_preflight.py"),
    Path("scripts/run_heldout_ac_campaign.py"),
    Path("tests/test_evaluator_v2_contracts.py"),
    Path("tests/test_heldout_ac_binding_source_qualification.py"),
    Path("tests/test_heldout_ac_completion.py"),
    Path("tests/test_heldout_ac_execution.py"),
    Path("tests/test_heldout_ac_execution_source_qualification.py"),
    Path("tests/test_heldout_ac_preflight.py"),
    Path("tests/test_heldout_ac_preflight_source_qualification.py"),
    Path("tests/test_heldout_ac_dispatcher.py"),
    Path("tests/test_heldout_ac_persisted_adapter.py"),
    Path("tests/test_heldout_ac_analysis.py"),
    Path("tests/test_heldout_ac_r7_runtime_evidence_index.py"),
    Path("tests/test_heldout_ac_r11_runtime_evidence_index.py"),
    Path("tests/test_heldout_ac_source_qualification.py"),
    Path("tests/test_heldout_ac_task_evaluator.py"),
    Path("tests/test_heldout_ac_task_pricing_materialization.py"),
    Path("tests/test_trace_qualification.py"),
)


class HeldoutACPreflightSourceQualificationError(ContractError):
    pass


class FileBinding(HeldoutACFrozenModel):
    path: str
    file_bytes: int = Field(gt=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class R12Binding(FileBinding):
    path: Literal["reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r12.json"]
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_qualification_id: Literal["core-ac-fixed-bundle-heldout-preflight-source-20260815-r12"]
    original_status: Literal["OFFLINE_PREFLIGHT_AND_DISPATCH_SOURCE_QUALIFIED_EXECUTION_CLOSED"]
    successor_reason: Literal["align-current-loader-gate-validation-expectation"]


class R11CampaignEvidenceBinding(FileBinding):
    path: Literal["reports/heldout-ac/artifacts/heldout-ac-r11-campaign-inconclusive-r1.json"]
    evidence_id: Literal[R11_CAMPAIGN_EVIDENCE_ID]
    content_hash: Literal["sha256:ff66718e1fa403baf0978de1b0e43625aac0a046117e85c5f42fb0cc4312db9b"]
    execution_hash: Literal[R11_EXECUTION_HASH]
    disposition: Literal["inconclusive-matrix"]
    observed_started_model_cost_nanos: Literal[418_016_250]
    correction_only: Literal[True]


class PreflightProjection(HeldoutACFrozenModel):
    suite_content_hash: Literal[
        "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
    ]
    scheduled_rows: Literal[48]
    r12_predecessor_bytes_preserved: Literal[True]
    r11_campaign_correction_index_bound: Literal[True]
    git_commit_tree_and_execution_clean_observation_present: Literal[True]
    digest_pinned_docker_image_observation_present: Literal[True]
    sdk_version_observation_present: Literal[True]
    credential_presence_only_boundary_present: Literal[True]
    custom_base_url_block_present: Literal[True]
    candidate_factory_bound: Literal[True]
    exact_paid_plan_boundary_bound: Literal[True]
    append_only_48_row_dispatcher_bound: Literal[True]
    one_use_row_consumption_bound: Literal[True]
    one_use_campaign_identity_ignores_observed_at: Literal[True]
    canonical_runtime_path_boundary_bound: Literal[True]
    atomic_terminal_cost_settlement_bound: Literal[True]
    durable_started_cost_observation_bound: Literal[True]
    typed_evaluator_and_agent_terminal_sidecars_bound: Literal[True]
    persisted_v2_authentication_bound: Literal[True]
    complete_or_inconclusive_finalization_bound: Literal[True]
    persisted_campaign_replay_validator_bound: Literal[True]
    historical_v1_campaign_replay_bound: Literal[True]
    current_dispatch_source_loader_bound_without_literal_id: Literal[True]
    preregistered_analysis_unlock_bound: Literal[True]
    official_completion_and_analysis_envelope_persisted: Literal[True]
    blocked_preflight_candidate_count: Literal[0]
    execution_candidates_created: Literal[0]
    approved_plans_created: Literal[0]
    campaign_journals_created: Literal[0]
    campaign_results_created: Literal[0]


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
    approved_plans_created: Literal[0]
    campaign_journals_created: Literal[0]
    campaign_results_created: Literal[0]
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
    predecessor: R12Binding
    campaign_predecessor: R11CampaignEvidenceBinding
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


def _r12_binding(root: Path) -> R12Binding:
    selected = (root / R12_PATH).resolve()
    if not selected.is_relative_to(root) or selected.is_symlink() or not selected.is_file():
        raise HeldoutACPreflightSourceQualificationError(
            "held-out R12 source qualification predecessor is unavailable"
        )
    try:
        raw = selected.read_bytes()
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACPreflightSourceQualificationError(
            "held-out R12 source qualification predecessor is invalid"
        ) from exc
    exact = (
        len(raw) == 21_550
        and sha256_bytes(raw)
        == "sha256:21d38740e1c69c60204bf234f4a75502cf4b0fe549780914cb8e2789db9cb9f9"
        and isinstance(payload, dict)
        and payload.get("qualification_id")
        == "core-ac-fixed-bundle-heldout-preflight-source-20260815-r12"
        and payload.get("status")
        == "OFFLINE_PREFLIGHT_AND_DISPATCH_SOURCE_QUALIFIED_EXECUTION_CLOSED"
        and payload.get("content_hash")
        == "sha256:cc9a0a8ffbf516310db04577dcbabbfe79e53ff43c2307cdaa5a200749ab7b4a"
        and payload.get("evaluator_source_hash")
        == "sha256:d6219fb057d7ba7a7052182e4ae7954506ab877e9d9856365c5898a5c88c921d"
    )
    if not exact:
        raise HeldoutACPreflightSourceQualificationError(
            "held-out R12 source qualification predecessor bytes differ"
        )
    return R12Binding(
        path=R12_PATH.as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        source_qualification_hash=str(payload["content_hash"]),
        evaluator_source_hash=str(payload["evaluator_source_hash"]),
        original_qualification_id=str(payload["qualification_id"]),
        original_status=str(payload["status"]),
        successor_reason="align-current-loader-gate-validation-expectation",
    )


def _r11_campaign_evidence_binding(root: Path) -> R11CampaignEvidenceBinding:
    selected = (root / R11_CAMPAIGN_EVIDENCE_PATH).resolve()
    if not selected.is_relative_to(root) or selected.is_symlink() or not selected.is_file():
        raise HeldoutACPreflightSourceQualificationError(
            "held-out R11 campaign evidence predecessor is unavailable"
        )
    try:
        raw = selected.read_bytes()
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACPreflightSourceQualificationError(
            "held-out R11 campaign evidence predecessor is invalid"
        ) from exc
    exact = (
        len(raw) == 18_525
        and sha256_bytes(raw)
        == "sha256:1badf8a78ba142f9868a3b9e836fa83df7beb0248f9c5e745fd205fd0185f48c"
        and isinstance(payload, dict)
        and payload.get("evidence_id") == R11_CAMPAIGN_EVIDENCE_ID
        and payload.get("content_hash")
        == "sha256:ff66718e1fa403baf0978de1b0e43625aac0a046117e85c5f42fb0cc4312db9b"
        and payload.get("approval", {}).get("execution_hash") == R11_EXECUTION_HASH
        and payload.get("campaign_correction", {}).get("disposition") == "inconclusive-matrix"
        and payload.get("campaign_correction", {}).get("observed_started_model_cost_nanos")
        == 418_016_250
        and payload.get("authority", {}).get("evidence_index_is_correction_only") is True
        and payload.get("authority", {}).get("execution_candidates_created") == 0
    )
    if not exact:
        raise HeldoutACPreflightSourceQualificationError(
            "held-out R11 campaign evidence predecessor bytes differ"
        )
    return R11CampaignEvidenceBinding(
        path=R11_CAMPAIGN_EVIDENCE_PATH.as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        evidence_id=str(payload["evidence_id"]),
        content_hash=str(payload["content_hash"]),
        execution_hash=str(payload["approval"]["execution_hash"]),
        disposition=str(payload["campaign_correction"]["disposition"]),
        observed_started_model_cost_nanos=int(
            payload["campaign_correction"]["observed_started_model_cost_nanos"]
        ),
        correction_only=True,
    )


def _build_candidate(
    root: Path,
    *,
    recorded_at: datetime,
) -> HeldoutACPreflightSourceQualification:
    predecessor = _r12_binding(root)
    campaign_predecessor = _r11_campaign_evidence_binding(root)
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
        "campaign_predecessor": campaign_predecessor.model_dump(mode="json"),
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
            "r12_predecessor_bytes_preserved": True,
            "r11_campaign_correction_index_bound": True,
            "git_commit_tree_and_execution_clean_observation_present": True,
            "digest_pinned_docker_image_observation_present": True,
            "sdk_version_observation_present": True,
            "credential_presence_only_boundary_present": True,
            "custom_base_url_block_present": True,
            "candidate_factory_bound": True,
            "exact_paid_plan_boundary_bound": True,
            "append_only_48_row_dispatcher_bound": True,
            "one_use_row_consumption_bound": True,
            "one_use_campaign_identity_ignores_observed_at": True,
            "canonical_runtime_path_boundary_bound": True,
            "atomic_terminal_cost_settlement_bound": True,
            "durable_started_cost_observation_bound": True,
            "typed_evaluator_and_agent_terminal_sidecars_bound": True,
            "persisted_v2_authentication_bound": True,
            "complete_or_inconclusive_finalization_bound": True,
            "persisted_campaign_replay_validator_bound": True,
            "historical_v1_campaign_replay_bound": True,
            "current_dispatch_source_loader_bound_without_literal_id": True,
            "preregistered_analysis_unlock_bound": True,
            "official_completion_and_analysis_envelope_persisted": True,
            "blocked_preflight_candidate_count": 0,
            "execution_candidates_created": 0,
            "approved_plans_created": 0,
            "campaign_journals_created": 0,
            "campaign_results_created": 0,
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
            "approved_plans_created": 0,
            "campaign_journals_created": 0,
            "campaign_results_created": 0,
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
        "predecessor_campaign_evidence_hash": payload.campaign_predecessor.content_hash,
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_candidate_created": False,
        "approved_plan_created": False,
        "campaign_journal_created": False,
        "campaign_result_created": False,
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
    "R2_PATH",
    "R3_PATH",
    "R4_PATH",
    "R5_PATH",
    "R6_PATH",
    "R7_PATH",
    "R7_CAMPAIGN_EVIDENCE_PATH",
    "R8_PATH",
    "R9_PATH",
    "R10_PATH",
    "R11_CAMPAIGN_EVIDENCE_PATH",
    "R11_PATH",
    "R12_PATH",
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
