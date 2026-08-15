"""Successor source gate for the held-out preflight and paid dispatcher.

R2 through R14 remain immutable.  R15 binds the append-only R14 campaign
inconclusive index and its historical-reason/post-runtime-attribution boundary
into the current paid closure.  It grants no observation, candidate, approval,
reauthentication, retry, execution, or spend authority.
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
    OUTPUT_PATH as R11_CAMPAIGN_EVIDENCE_PATH,
)
from patchloop.evals.heldout_ac_r14_campaign_evidence import (
    EVIDENCE_ID as R14_CAMPAIGN_EVIDENCE_ID,
)
from patchloop.evals.heldout_ac_r14_campaign_evidence import (
    EXECUTION_HASH as R14_EXECUTION_HASH,
)
from patchloop.evals.heldout_ac_r14_campaign_evidence import (
    OUTPUT_PATH as R14_CAMPAIGN_EVIDENCE_PATH,
)
from patchloop.evals.heldout_ac_r14_campaign_evidence import (
    STATUS as R14_CAMPAIGN_STATUS,
)
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_json

SCHEMA_VERSION = "heldout-ac-preflight-dispatch-source-qualification-v14"
QUALIFICATION_ID = "core-ac-fixed-bundle-heldout-preflight-source-20260815-r15"
STATUS = "OFFLINE_PREFLIGHT_AND_DISPATCH_SOURCE_QUALIFIED_EXECUTION_CLOSED"
OUTPUT_PATH = Path(
    "reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r15.json"
)
R14_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r14.json")
R14_FILE_BYTES = 21_984
R14_FILE_SHA256 = "sha256:259407d7c30113096844541b01f93ea18e78c5dd0d471c261311657acd7135a3"
R14_CONTENT_HASH = "sha256:d71f0ad53cadb2957e1870cc40291a4979d0eed93321a0d082233408c03aed5c"
R14_EVALUATOR_SOURCE_HASH = (
    "sha256:f9660226185d33726bc3585381d0606234e6231faf5d9a9f62b79b44b67c20fd"
)
R14_CAMPAIGN_FILE_BYTES = 12_856
R14_CAMPAIGN_FILE_SHA256 = "sha256:21cda8f99aa835b196aa54cc6f7ad2483942f43d986fd935ce511a0d6974cd7b"
R14_CAMPAIGN_CONTENT_HASH = (
    "sha256:1b602c1900ddfbd6867c81818d48ee9ada72f0b2fb2503d5eb83db7faf0e5341"
)
R13_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r13.json")
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
    Path("patchloop/evals/heldout_ac_r14_campaign_evidence.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)
VALIDATION_PATHS = (
    Path("scripts/build_heldout_ac_execution_source_qualification.py"),
    Path("scripts/build_heldout_ac_preflight_source_qualification.py"),
    Path("scripts/build_heldout_ac_r11_campaign_evidence.py"),
    Path("scripts/build_heldout_ac_r14_campaign_evidence.py"),
    Path("scripts/run_heldout_ac_preflight.py"),
    Path("scripts/run_heldout_ac_campaign.py"),
    Path("tests/test_evaluator_v2_contracts.py"),
    Path("tests/test_heldout_ac_binding_source_qualification.py"),
    Path("tests/test_heldout_ac_budget_amendment.py"),
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
    Path("tests/test_heldout_ac_r14_runtime_evidence_index.py"),
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


class R14Binding(FileBinding):
    path: Literal["reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r14.json"]
    file_bytes: Literal[R14_FILE_BYTES]
    file_sha256: Literal[R14_FILE_SHA256]
    source_qualification_hash: Literal[R14_CONTENT_HASH]
    evaluator_source_hash: Literal[R14_EVALUATOR_SOURCE_HASH]
    original_schema_version: Literal["heldout-ac-preflight-dispatch-source-qualification-v13"]
    original_qualification_id: Literal["core-ac-fixed-bundle-heldout-preflight-source-20260815-r14"]
    original_status: Literal["OFFLINE_PREFLIGHT_AND_DISPATCH_SOURCE_QUALIFIED_EXECUTION_CLOSED"]
    successor_reason: Literal[
        "r14-campaign-inconclusive-runtime-budget-attribution-index-successor"
    ]


class R14CampaignEvidenceBinding(FileBinding):
    path: Literal["reports/heldout-ac/artifacts/heldout-ac-r14-campaign-inconclusive-r1.json"]
    file_bytes: Literal[R14_CAMPAIGN_FILE_BYTES]
    file_sha256: Literal[R14_CAMPAIGN_FILE_SHA256]
    schema_version: Literal["heldout-ac-campaign-evidence-index-v3"]
    evidence_id: Literal[R14_CAMPAIGN_EVIDENCE_ID]
    status: Literal[R14_CAMPAIGN_STATUS]
    content_hash: Literal[R14_CAMPAIGN_CONTENT_HASH]
    execution_hash: Literal[R14_EXECUTION_HASH]
    approval_consumed: Literal[True]
    disposition: Literal["inconclusive-matrix"]
    terminal_settled_runs: Literal[0]
    observed_unsettled_runs: Literal[1]
    not_started_runs: Literal[47]
    settled_model_cost_nanos: Literal[0]
    observed_unsettled_model_cost_nanos: Literal[126_342_000]
    observed_started_model_cost_nanos: Literal[126_342_000]
    historical_reason_code: Literal["DURABLE_EVIDENCE_AUTHENTICATION_FAILED"]
    post_runtime_attribution_code: Literal["TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH"]
    historical_reason_preserved_without_relabeling: Literal[True]
    historical_typed_diagnosis_code_observed: Literal[False]
    post_runtime_deterministic_attribution: Literal[True]
    post_runtime_attribution_changes_historical_reason: Literal[False]
    historical_row_reclassified: Literal[False]
    campaign_settlement_preserved_without_reauthentication: Literal[True]
    attribution_only: Literal[True]
    r14_campaign_is_immutable_and_consumed: Literal[True]
    historical_runtime_files_mutated: Literal[False]
    historical_row_reauthentication_authorized: Literal[False]
    retry_replacement_or_resume_performed: Literal[False]
    candidate_creation_authorized: Literal[False]
    future_execution_authorized: Literal[False]
    future_spend_authorized: Literal[False]


class PreflightProjection(HeldoutACFrozenModel):
    suite_content_hash: Literal[
        "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
    ]
    scheduled_rows: Literal[48]
    r14_predecessor_bytes_preserved: Literal[True]
    r14_campaign_inconclusive_index_bound: Literal[True]
    r14_historical_reason_and_post_runtime_attribution_distinct: Literal[True]
    r14_observed_unsettled_cost_bound: Literal[True]
    r14_reauthentication_retry_or_runtime_authority_granted: Literal[False]
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
    current_candidate_schema: Literal["heldout-ac-execution-candidate-v3"]
    current_persisted_evidence_schema: Literal["heldout-ac-authenticated-persisted-evidence-v5"]
    current_persisted_row_schema: Literal["heldout-ac-authenticated-persisted-row-v2"]
    candidate_v3_realized_schedule_bound: Literal[True]
    candidate_runtime_tuple_recomputed_before_plan_write: Literal[True]
    current_prior_row_requires_persisted_v5_row_v2: Literal[True]
    prior_row_runtime_cost_usage_budget_revalidated: Literal[True]
    known_r7_r11_r14_exact_result_content_journal_triple_required: Literal[True]
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
    predecessor: R14Binding
    campaign_predecessor: R14CampaignEvidenceBinding
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


def _r14_binding(root: Path) -> R14Binding:
    selected = (root / R14_PATH).resolve()
    if not selected.is_relative_to(root) or selected.is_symlink() or not selected.is_file():
        raise HeldoutACPreflightSourceQualificationError(
            "held-out R14 source qualification predecessor is unavailable"
        )
    try:
        raw = selected.read_bytes()
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACPreflightSourceQualificationError(
            "held-out R14 source qualification predecessor is invalid"
        ) from exc
    exact = (
        len(raw) == R14_FILE_BYTES
        and sha256_bytes(raw) == R14_FILE_SHA256
        and isinstance(payload, dict)
        and payload.get("schema_version")
        == "heldout-ac-preflight-dispatch-source-qualification-v13"
        and payload.get("qualification_id")
        == "core-ac-fixed-bundle-heldout-preflight-source-20260815-r14"
        and payload.get("status")
        == "OFFLINE_PREFLIGHT_AND_DISPATCH_SOURCE_QUALIFIED_EXECUTION_CLOSED"
        and payload.get("content_hash") == R14_CONTENT_HASH
        and payload.get("evaluator_source_hash") == R14_EVALUATOR_SOURCE_HASH
        and sha256_json({key: value for key, value in payload.items() if key != "content_hash"})
        == R14_CONTENT_HASH
    )
    if not exact:
        raise HeldoutACPreflightSourceQualificationError(
            "held-out R14 source qualification predecessor bytes differ"
        )
    return R14Binding(
        path=R14_PATH.as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        source_qualification_hash=str(payload["content_hash"]),
        evaluator_source_hash=str(payload["evaluator_source_hash"]),
        original_schema_version=str(payload["schema_version"]),
        original_qualification_id=str(payload["qualification_id"]),
        original_status=str(payload["status"]),
        successor_reason=("r14-campaign-inconclusive-runtime-budget-attribution-index-successor"),
    )


def _r14_campaign_evidence_binding(root: Path) -> R14CampaignEvidenceBinding:
    selected = (root / R14_CAMPAIGN_EVIDENCE_PATH).resolve()
    if not selected.is_relative_to(root) or selected.is_symlink() or not selected.is_file():
        raise HeldoutACPreflightSourceQualificationError(
            "held-out R14 campaign evidence predecessor is unavailable"
        )
    try:
        raw = selected.read_bytes()
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACPreflightSourceQualificationError(
            "held-out R14 campaign evidence predecessor is invalid"
        ) from exc
    campaign = payload.get("campaign_observation") if isinstance(payload, dict) else None
    historical = payload.get("historical_confound") if isinstance(payload, dict) else None
    attribution = payload.get("post_runtime_attribution") if isinstance(payload, dict) else None
    authority = payload.get("authority") if isinstance(payload, dict) else None
    exact = (
        len(raw) == R14_CAMPAIGN_FILE_BYTES
        and sha256_bytes(raw) == R14_CAMPAIGN_FILE_SHA256
        and isinstance(payload, dict)
        and payload.get("schema_version") == "heldout-ac-campaign-evidence-index-v3"
        and payload.get("evidence_id") == R14_CAMPAIGN_EVIDENCE_ID
        and payload.get("status") == R14_CAMPAIGN_STATUS
        and payload.get("content_hash") == R14_CAMPAIGN_CONTENT_HASH
        and sha256_json({key: value for key, value in payload.items() if key != "content_hash"})
        == R14_CAMPAIGN_CONTENT_HASH
        and isinstance(payload.get("approval"), dict)
        and payload["approval"].get("execution_hash") == R14_EXECUTION_HASH
        and payload["approval"].get("approval_consumed") is True
        and isinstance(campaign, dict)
        and campaign.get("disposition") == "inconclusive-matrix"
        and campaign.get("terminal_settled_runs") == 0
        and campaign.get("observed_unsettled_runs") == 1
        and campaign.get("not_started_runs") == 47
        and campaign.get("settled_model_cost_nanos") == 0
        and campaign.get("observed_unsettled_model_cost_nanos") == 126_342_000
        and campaign.get("observed_started_model_cost_nanos") == 126_342_000
        and campaign.get("campaign_settlement_preserved_without_reauthentication") is True
        and isinstance(historical, dict)
        and historical.get("historical_reason_code") == "DURABLE_EVIDENCE_AUTHENTICATION_FAILED"
        and historical.get("historical_reason_preserved_without_relabeling") is True
        and isinstance(attribution, dict)
        and attribution.get("diagnosis_code")
        == "TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH"
        and attribution.get("historical_typed_diagnosis_code_observed") is False
        and attribution.get("post_runtime_deterministic_attribution") is True
        and attribution.get("changes_historical_reason_code") is False
        and attribution.get("historical_row_reauthenticated") is False
        and attribution.get("historical_row_reclassified") is False
        and isinstance(authority, dict)
        and authority.get("r14_campaign_is_immutable_and_consumed") is True
        and authority.get("evidence_index_is_append_only_attribution_only") is True
        and authority.get("historical_runtime_files_mutated") is False
        and authority.get("historical_row_reauthentication_authorized") is False
        and authority.get("retry_replacement_or_resume_performed") is False
        and authority.get("candidate_creation_authorized") is False
        and authority.get("future_provider_evaluator_or_agent_execution_authorized") is False
        and authority.get("future_cost_reservation_or_spend_authorized") is False
        and authority.get("execution_candidates_created") == 0
    )
    if not exact:
        raise HeldoutACPreflightSourceQualificationError(
            "held-out R14 campaign evidence predecessor bytes differ"
        )
    return R14CampaignEvidenceBinding(
        path=R14_CAMPAIGN_EVIDENCE_PATH.as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        schema_version=str(payload["schema_version"]),
        evidence_id=str(payload["evidence_id"]),
        status=str(payload["status"]),
        content_hash=str(payload["content_hash"]),
        execution_hash=str(payload["approval"]["execution_hash"]),
        approval_consumed=True,
        disposition=str(campaign["disposition"]),
        terminal_settled_runs=int(campaign["terminal_settled_runs"]),
        observed_unsettled_runs=int(campaign["observed_unsettled_runs"]),
        not_started_runs=int(campaign["not_started_runs"]),
        settled_model_cost_nanos=int(campaign["settled_model_cost_nanos"]),
        observed_unsettled_model_cost_nanos=int(campaign["observed_unsettled_model_cost_nanos"]),
        observed_started_model_cost_nanos=int(campaign["observed_started_model_cost_nanos"]),
        historical_reason_code=str(historical["historical_reason_code"]),
        post_runtime_attribution_code=str(attribution["diagnosis_code"]),
        historical_reason_preserved_without_relabeling=True,
        historical_typed_diagnosis_code_observed=False,
        post_runtime_deterministic_attribution=True,
        post_runtime_attribution_changes_historical_reason=False,
        historical_row_reclassified=False,
        campaign_settlement_preserved_without_reauthentication=True,
        attribution_only=True,
        r14_campaign_is_immutable_and_consumed=True,
        historical_runtime_files_mutated=False,
        historical_row_reauthentication_authorized=False,
        retry_replacement_or_resume_performed=False,
        candidate_creation_authorized=False,
        future_execution_authorized=False,
        future_spend_authorized=False,
    )


def _build_candidate(
    root: Path,
    *,
    recorded_at: datetime,
) -> HeldoutACPreflightSourceQualification:
    predecessor = _r14_binding(root)
    campaign_predecessor = _r14_campaign_evidence_binding(root)
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
            "r14_predecessor_bytes_preserved": True,
            "r14_campaign_inconclusive_index_bound": True,
            "r14_historical_reason_and_post_runtime_attribution_distinct": True,
            "r14_observed_unsettled_cost_bound": True,
            "r14_reauthentication_retry_or_runtime_authority_granted": False,
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
            "current_candidate_schema": "heldout-ac-execution-candidate-v3",
            "current_persisted_evidence_schema": ("heldout-ac-authenticated-persisted-evidence-v5"),
            "current_persisted_row_schema": "heldout-ac-authenticated-persisted-row-v2",
            "candidate_v3_realized_schedule_bound": True,
            "candidate_runtime_tuple_recomputed_before_plan_write": True,
            "current_prior_row_requires_persisted_v5_row_v2": True,
            "prior_row_runtime_cost_usage_budget_revalidated": True,
            "known_r7_r11_r14_exact_result_content_journal_triple_required": True,
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
    "R13_PATH",
    "R14_CAMPAIGN_CONTENT_HASH",
    "R14_CAMPAIGN_EVIDENCE_PATH",
    "R14_CAMPAIGN_FILE_BYTES",
    "R14_CAMPAIGN_FILE_SHA256",
    "R14_CONTENT_HASH",
    "R14_EVALUATOR_SOURCE_HASH",
    "R14_FILE_BYTES",
    "R14_FILE_SHA256",
    "R14_PATH",
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
