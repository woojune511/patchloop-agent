"""Immutable, zero-authority correction index for the consumed R11 campaign.

The live R11 files use the historical campaign-result v1 schema.  That schema
settled two rows, stopped after row three, and did not retain row-three usage in
the final cost totals.  This module records the original bytes unchanged and
adds a content-addressed accounting/root-cause correction.  It never creates a
candidate, observes credentials, or crosses a provider, evaluator, Docker, or
agent boundary.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from patchloop.contracts import EvaluatorV2EvaluationReceipt, RunResult
from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_contracts import HeldoutACFrozenModel
from patchloop.evals.heldout_ac_persisted_adapter import (
    HELDOUT_AC_PRICE_NANOS_PER_TOKEN,
    HeldoutACPersistedUsageEvidence,
    validate_heldout_ac_persisted_usage_cross_binding,
)
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_json

SCHEMA_VERSION = "heldout-ac-campaign-evidence-index-v2"
EVIDENCE_ID = "core-ac-fixed-bundle-heldout-r11-live-inconclusive-20260815-r1"
STATUS = "LIVE_CAMPAIGN_INCONCLUSIVE_EVALUATOR_CONTROL_COLLISION_ACCOUNTED"
OUTPUT_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-r11-campaign-inconclusive-r1.json")
EXECUTION_HASH = "sha256:f48a0de27f8b3e46e627d957dfd714b395c94855587ccfc36e78028fa711a6b0"
EXECUTION_DIGEST = EXECUTION_HASH.removeprefix("sha256:")
SUITE_ID = "core-ac-fixed-bundle-heldout-20260814-v1"
SUITE_CONTENT_HASH = "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
PRICING_BINDING_HASH = "sha256:03e9cde4d6d04a09995da669d7e3aea26fda31310615640508f6bd0a9c2cbd34"
NEXT_GATE = "bind-this-index-into-a-fresh-offline-source-qualified-successor"


class HeldoutACR11CampaignEvidenceError(ContractError):
    pass


class FileBinding(HeldoutACFrozenModel):
    path: str
    file_bytes: int = Field(ge=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ContentFileBinding(FileBinding):
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class SemanticFileBinding(FileBinding):
    semantic_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class QualificationFileBinding(FileBinding):
    qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class JournalFileBinding(FileBinding):
    campaign_completed_event_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class HistoricalSource(HeldoutACFrozenModel):
    git_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    git_tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    suite_id: str
    suite_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_id: str
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_file: FileBinding


class Approval(HeldoutACFrozenModel):
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    scheduled_rows: int = Field(ge=1)
    full_schedule_reserve_nanos: int = Field(ge=0)
    hard_cap_nanos: int = Field(ge=0)
    approval_consumed: Literal[True]
    retry_replacement_or_resume_authorized: Literal[False]


class RuntimeFiles(HeldoutACFrozenModel):
    candidate: FileBinding
    execution_plan: FileBinding
    journal: JournalFileBinding
    prepared_result: ContentFileBinding
    final_result: ContentFileBinding
    stdout: FileBinding
    stderr: FileBinding
    historical_state_database: FileBinding


class CampaignCorrection(HeldoutACFrozenModel):
    disposition: Literal["inconclusive-matrix"]
    expected_runs: int = Field(ge=1)
    started_runs: int = Field(ge=0)
    terminal_settled_runs: int = Field(ge=0)
    observed_unsettled_runs: int = Field(ge=0)
    not_started_runs: int = Field(ge=0)
    settled_model_cost_nanos: int = Field(ge=0)
    observed_unsettled_model_cost_nanos: int = Field(ge=0)
    observed_started_model_cost_nanos: int = Field(ge=0)
    historical_result_cost_accounting_complete: Literal[False]
    corrected_observation_accounting_complete: Literal[True]
    analysis_ready: Literal[False]
    official_heldout_analysis: Literal[False]
    memory_benefit_claim_authorized: Literal[False]
    broad_generalization_claim_authorized: Literal[False]

    @model_validator(mode="after")
    def validate_accounting(self) -> CampaignCorrection:
        if not (
            self.started_runs == self.terminal_settled_runs + self.observed_unsettled_runs
            and self.expected_runs == self.started_runs + self.not_started_runs
            and self.observed_started_model_cost_nanos
            == self.settled_model_cost_nanos + self.observed_unsettled_model_cost_nanos
        ):
            raise ValueError("R11 corrected campaign accounting differs")
        return self


class VerdictProjection(HeldoutACFrozenModel):
    hidden_tests: Literal["pass", "fail", "not_run"]
    regression_tests: Literal["pass", "fail", "not_run"]
    scope_policy: Literal["pass", "fail", "not_run"]
    safety_policy: Literal["pass", "fail", "not_run"]


class ObservedRow(HeldoutACFrozenModel):
    order: int = Field(ge=1)
    schedule_row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_id: str
    role: Literal["core-same-repo", "core-cross-repo"]
    condition: Literal["no_memory", "structured"]
    repetition: int = Field(ge=1)
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    outcome_kind: Literal["resolved", "task_failure", "infrastructure_error"]
    agent_submission_status: Literal["completed"]
    evaluation_status: Literal["completed", "not_run"]
    verdicts: VerdictProjection
    model_cost_nanos: int = Field(ge=0)
    campaign_settled: bool
    result: SemanticFileBinding
    qualification: QualificationFileBinding
    usage: ContentFileBinding
    receipt: ContentFileBinding | None
    authenticated_row: ContentFileBinding | None


class MarkerScan(HeldoutACFrozenModel):
    role: Literal["scanned_artifact_inventory", "scanned_event_prefix", "scanned_patch"]
    observation: ContentFileBinding
    match_count: int = Field(ge=0)
    agent_visible: bool


class MarkerBoundary(HeldoutACFrozenModel):
    run_id: Literal["run_heldout_21bf0f4da50c4e35"]
    provenance: FileBinding
    safety_bundle: ContentFileBinding
    scans: tuple[MarkerScan, MarkerScan, MarkerScan]
    evaluator_private_redaction_match_count: Literal[14]
    event_prefix_match_count: Literal[0]
    submitted_patch_match_count: Literal[0]
    agent_visible_marker_match_count: Literal[0]
    private_marker_values_serialized: Literal[False]

    @model_validator(mode="after")
    def validate_scans(self) -> MarkerBoundary:
        if tuple(item.role for item in self.scans) != (
            "scanned_artifact_inventory",
            "scanned_event_prefix",
            "scanned_patch",
        ):
            raise ValueError("R11 marker scan roles differ")
        if tuple(item.match_count for item in self.scans) != (
            self.evaluator_private_redaction_match_count,
            self.event_prefix_match_count,
            self.submitted_patch_match_count,
        ):
            raise ValueError("R11 marker scan counts differ")
        if sum(item.match_count for item in self.scans if item.agent_visible) != 0:
            raise ValueError("R11 agent-visible marker count differs")
        return self


class HistoricalFailureEvent(HeldoutACFrozenModel):
    schema_version: Literal["historical-run-failed-safe-projection-v1"]
    event_id: str
    run_id: Literal["run_heldout_8360c76db8664058"]
    sequence: Literal[166]
    type: Literal["RunFailed"]
    timestamp: Literal["2026-08-14T13:39:40.731776Z"]
    actor: Literal["runner"]
    observed_runtime_error_code: Literal["CONTRACT_ERROR"]
    raw_event_json_bytes: Literal[472]
    raw_event_json_sha256: Literal[
        "sha256:1c52f38fb7570d979f36c0733735d4688b01723f3f7e573b878e10ec4e386560"
    ]
    error_type_sha256: Literal[
        "sha256:6bfd746d4dd0a8d77ab8e414de41fe4e68585c4e5e832dedbada062f8851909a"
    ]
    message_sha256: Literal[
        "sha256:bcfbe348ca134b5c55cf12c2756c076f191c808d7f9a7f4b09fc519b3c8efac7"
    ]
    outcome_kind: Literal["infrastructure_error"]
    model_cost_nanos: Literal[261_021_000]
    raw_error_type_or_message_serialized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> HistoricalFailureEvent:
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("historical RunFailed safe projection hash differs")
        return self


class SourceQualificationBinding(ContentFileBinding):
    qualification_id: str
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class CorrectionSourceChain(HeldoutACFrozenModel):
    contract_source: ContentFileBinding
    binding_adapter_source: ContentFileBinding
    task_pricing_materialization: ContentFileBinding
    execution_source: SourceQualificationBinding
    materialized_task_bindings_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    pricing_binding_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class FailureAttribution(HeldoutACFrozenModel):
    historical_event: HistoricalFailureEvent
    successor_diagnosis_code: Literal["EVALUATOR_CONTROL_CONTRACT_COLLISION"]
    direct_cause: Literal["fixed-redaction-placeholder-control-contract-collision"]
    historical_runtime_typed_code_observed: Literal[False]
    successor_diagnosis_is_post_runtime_deterministic_attribution: Literal[True]
    task_or_memory_effect_failure: Literal[False]
    private_marker_value_serialized: Literal[False]


class QualificationAuthority(HeldoutACFrozenModel):
    r11_campaign_is_immutable_and_consumed: Literal[True]
    evidence_index_is_correction_only: Literal[True]
    execution_r3_is_correction_attribution_predecessor_only: Literal[True]
    retry_replacement_or_resume_performed: Literal[False]
    runtime_secret_materialization_authorized: Literal[False]
    candidate_creation_authorized: Literal[False]
    future_provider_evaluator_or_agent_execution_authorized: Literal[False]
    future_cost_reservation_or_spend_authorized: Literal[False]
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


class HeldoutACR11CampaignEvidence(HeldoutACFrozenModel):
    schema_version: Literal[SCHEMA_VERSION]
    evidence_id: Literal[EVIDENCE_ID]
    status: Literal[STATUS]
    recorded_at: datetime
    historical_source: HistoricalSource
    approval: Approval
    runtime_files: RuntimeFiles
    campaign_correction: CampaignCorrection
    observed_rows: tuple[ObservedRow, ObservedRow, ObservedRow]
    marker_boundary: MarkerBoundary
    failure_attribution: FailureAttribution
    correction_source_chain: CorrectionSourceChain
    authority: QualificationAuthority
    next_gate: Literal[NEXT_GATE]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_index(self) -> HeldoutACR11CampaignEvidence:
        if not (
            self.historical_source.suite_id == SUITE_ID
            and self.historical_source.suite_content_hash == SUITE_CONTENT_HASH
            and self.approval.execution_hash == EXECUTION_HASH
            and tuple(row.order for row in self.observed_rows) == (1, 2, 3)
            and len({row.run_id for row in self.observed_rows}) == 3
            and sum(row.model_cost_nanos for row in self.observed_rows if row.campaign_settled)
            == self.campaign_correction.settled_model_cost_nanos
            and sum(row.model_cost_nanos for row in self.observed_rows)
            == self.campaign_correction.observed_started_model_cost_nanos
            and self.observed_rows[2].model_cost_nanos
            == self.campaign_correction.observed_unsettled_model_cost_nanos
            and self.failure_attribution.historical_event.run_id == self.observed_rows[2].run_id
            and self.correction_source_chain.pricing_binding_hash == PRICING_BINDING_HASH
        ):
            raise ValueError("R11 campaign evidence cross-binding differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("R11 campaign evidence content hash differs")
        return self


def _root(repository: str | Path | None) -> Path:
    return Path(repository).resolve() if repository is not None else repository_root().resolve()


def _file(path: str, size: int, digest: str) -> dict[str, Any]:
    return {"path": path, "file_bytes": size, "file_sha256": digest}


def _content_file(path: str, size: int, digest: str, content_hash: str) -> dict[str, Any]:
    return {**_file(path, size, digest), "content_hash": content_hash}


def _semantic_file(path: str, size: int, digest: str, semantic_hash: str) -> dict[str, Any]:
    return {**_file(path, size, digest), "semantic_hash": semantic_hash}


def _qualification_file(
    path: str,
    size: int,
    digest: str,
    qualification_hash: str,
    source_evidence_hash: str,
) -> dict[str, Any]:
    return {
        **_file(path, size, digest),
        "qualification_hash": qualification_hash,
        "source_evidence_hash": source_evidence_hash,
    }


def _historical_failure_event() -> HistoricalFailureEvent:
    body = {
        "schema_version": "historical-run-failed-safe-projection-v1",
        "event_id": "evt_57f3aaf7f6ab4581b23dd663a6ceef93",
        "run_id": "run_heldout_8360c76db8664058",
        "sequence": 166,
        "type": "RunFailed",
        "timestamp": "2026-08-14T13:39:40.731776Z",
        "actor": "runner",
        "observed_runtime_error_code": "CONTRACT_ERROR",
        "raw_event_json_bytes": 472,
        "raw_event_json_sha256": (
            "sha256:1c52f38fb7570d979f36c0733735d4688b01723f3f7e573b878e10ec4e386560"
        ),
        "error_type_sha256": (
            "sha256:6bfd746d4dd0a8d77ab8e414de41fe4e68585c4e5e832dedbada062f8851909a"
        ),
        "message_sha256": (
            "sha256:bcfbe348ca134b5c55cf12c2756c076f191c808d7f9a7f4b09fc519b3c8efac7"
        ),
        "outcome_kind": "infrastructure_error",
        "model_cost_nanos": 261_021_000,
        "raw_error_type_or_message_serialized": False,
    }
    return HistoricalFailureEvent(**body, content_hash=sha256_json(body))


def _record(*, recorded_at: datetime) -> dict[str, Any]:
    rows_root = f".patchloop/experiments/heldout-ac/rows/{EXECUTION_DIGEST}"
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": EVIDENCE_ID,
        "status": STATUS,
        "recorded_at": recorded_at,
        "historical_source": {
            "git_commit": "2f9f920eeb63a2704b387e78af74982b98f7136d",
            "git_tree": "d67be34a7de21c4d4ebc8025e9d070887dd47cf0",
            "suite_id": SUITE_ID,
            "suite_content_hash": SUITE_CONTENT_HASH,
            "source_qualification_id": (
                "core-ac-fixed-bundle-heldout-preflight-source-20260814-r11"
            ),
            "source_qualification_hash": (
                "sha256:13e3124c7f0ca0b3ed7afca68ea0f523f2eea4dc4c358cef37db29ac53d0b22b"
            ),
            "evaluator_source_hash": (
                "sha256:50b615250f566cd0cb580ab8f16a000d2c23105d10d5c6c9b9f36e0a2ff9ce3a"
            ),
            "source_qualification_file": _file(
                "reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r11.json",
                19_359,
                "sha256:45b21684520968903ab57afc7a4e0d9f4e66022ad0752140d24b988ba0df747f",
            ),
        },
        "approval": {
            "execution_hash": EXECUTION_HASH,
            "scheduled_rows": 48,
            "full_schedule_reserve_nanos": 252_000_000_000,
            "hard_cap_nanos": 275_000_000_000,
            "approval_consumed": True,
            "retry_replacement_or_resume_authorized": False,
        },
        "runtime_files": {
            "candidate": _file(
                f".patchloop/heldout-ac-candidate-{EXECUTION_DIGEST}.json",
                58_356,
                "sha256:c79ea3911e1b6ca2a9eda771d3db12ee895479437a893e1338f0555286afe053",
            ),
            "execution_plan": _file(
                f".patchloop/experiments/plans/{EXECUTION_DIGEST}.json",
                82_470,
                "sha256:87225743e586550cb972560118f253ded1c2b625ae81b418991a011ce7ce55c2",
            ),
            "journal": {
                **_file(
                    f".patchloop/experiments/journals/{EXECUTION_DIGEST}.jsonl",
                    51_324,
                    "sha256:b5ea7ddd8cb7a5bdd5fa77d8b6ab100ad24c200f432d02b6ba23bfa962515a42",
                ),
                "campaign_completed_event_hash": (
                    "sha256:c57d7923e723d4f449e1a3b044cf3baea47058f61b9c513d0cadc1258512b1f5"
                ),
            },
            "prepared_result": _content_file(
                f".patchloop/experiments/heldout-ac/{EXECUTION_DIGEST}.prepared.json",
                77_805,
                "sha256:d3298bfba791b6fe19925a17451bab30b69e380b882371fcbb9234e694221196",
                "sha256:cd19e06388d566f08e6fa0b9d41a7f686d6732668a80bef8bf8e4b5d00e3c490",
            ),
            "final_result": _content_file(
                f".patchloop/experiments/heldout-ac/{EXECUTION_DIGEST}.json",
                78_422,
                "sha256:9298b78252bf0ed5d74003a15ddbde9ead588312df79d1fc4a423538e0a58079",
                "sha256:7f60cae9c08cea2c528482b8a1c7c9ae0ce2befb4f995413bcbc847e24c307a8",
            ),
            "stdout": _file(
                f".patchloop/heldout-ac-r11-{EXECUTION_DIGEST}.stdout.log",
                79_996,
                "sha256:1a82bf9d2cbed047d20cab473fba30695af170a12c4227cbade2acbcc3d0ac22",
            ),
            "stderr": _file(
                f".patchloop/heldout-ac-r11-{EXECUTION_DIGEST}.stderr.log",
                0,
                "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ),
            "historical_state_database": _file(
                ".patchloop/state.sqlite3",
                59_953_152,
                "sha256:3342c4d443eb6db3ffaae1de23e8c2f8fa177eec3204fd6ac8488fdf4677d9f4",
            ),
        },
        "campaign_correction": {
            "disposition": "inconclusive-matrix",
            "expected_runs": 48,
            "started_runs": 3,
            "terminal_settled_runs": 2,
            "observed_unsettled_runs": 1,
            "not_started_runs": 45,
            "settled_model_cost_nanos": 156_995_250,
            "observed_unsettled_model_cost_nanos": 261_021_000,
            "observed_started_model_cost_nanos": 418_016_250,
            "historical_result_cost_accounting_complete": False,
            "corrected_observation_accounting_complete": True,
            "analysis_ready": False,
            "official_heldout_analysis": False,
            "memory_benefit_claim_authorized": False,
            "broad_generalization_claim_authorized": False,
        },
        "observed_rows": (
            {
                "order": 1,
                "schedule_row_id": (
                    "sha256:09a37b492fa9c5f1187b21e176e30b1214e315b51f6d5cfdfb0830240c7b6e64"
                ),
                "task_id": "loguru-post-2038-local-timezone-fallback",
                "role": "core-same-repo",
                "condition": "structured",
                "repetition": 1,
                "run_id": "run_heldout_893ca7fd7c4347a4",
                "outcome_kind": "resolved",
                "agent_submission_status": "completed",
                "evaluation_status": "completed",
                "verdicts": {
                    "hidden_tests": "pass",
                    "regression_tests": "pass",
                    "scope_policy": "pass",
                    "safety_policy": "pass",
                },
                "model_cost_nanos": 97_291_500,
                "campaign_settled": True,
                "result": _semantic_file(
                    ".patchloop/artifacts/runs/run_heldout_893ca7fd7c4347a4/result.json",
                    19_645,
                    "sha256:cf48c68143b5a8c71cf0196669fa782f3753d20cff3adbaa60bf7fcc3a03cd83",
                    "sha256:25ecfa036978542b44ee2b160a1dded06c57edabf5c80c1d55e6f13ac881b5dd",
                ),
                "qualification": _qualification_file(
                    ".patchloop/qualifications/run_heldout_893ca7fd7c4347a4.json",
                    12_346,
                    "sha256:90c4b80f7868cd78bc46f5609d3b5180554ad0f89aa72cbc9fc95fe2f2a5940a",
                    "sha256:f4d9289618ec6646b2e32e649bdb3c9f6d9a6863834c4d7bef2982acd5245d98",
                    "sha256:b13b8ee934c1794c4f1b0b7086735d1d7f5a7cf47a24eb2b5403b9587f2b74d6",
                ),
                "usage": _content_file(
                    f"{rows_root}/01-run_heldout_893ca7fd7c4347a4-usage.json",
                    1_269,
                    "sha256:61401919b2d20765abb6fa86bae31618b0460aba63e3492794dcd13ffa2ccbc3",
                    "sha256:4c8bf2c5758454231ae08daa0b9d31da4a48496767fd0c2447b69b5ab32c2bae",
                ),
                "receipt": _content_file(
                    ".patchloop/artifacts/runs/run_heldout_893ca7fd7c4347a4/evaluation-receipt.json",
                    1_998,
                    "sha256:3d207181380efb0377b62e90ed3335f9ef2e54e5f19cb44b37f3f195ad7b01ae",
                    "sha256:03d5d264a7a9458a3b41dc12bbe86b42f0639859eac145d265fbbfce6b3a8e94",
                ),
                "authenticated_row": _content_file(
                    f"{rows_root}/01-run_heldout_893ca7fd7c4347a4-authenticated.json",
                    23_565,
                    "sha256:e1e25ed9cabcf512a6fddd161d9a6e25b044e420d57bdf7924567bf6945796dd",
                    "sha256:d997ebf5cc01d2f6920138d938060e2602c6d003caa83f22693263cbbb499353",
                ),
            },
            {
                "order": 2,
                "schedule_row_id": (
                    "sha256:a6f62461fb830014842355b278ed96727bd163d0725f08cd596145fde8d9e7b0"
                ),
                "task_id": "loguru-post-2038-local-timezone-fallback",
                "role": "core-same-repo",
                "condition": "no_memory",
                "repetition": 1,
                "run_id": "run_heldout_21bf0f4da50c4e35",
                "outcome_kind": "task_failure",
                "agent_submission_status": "completed",
                "evaluation_status": "completed",
                "verdicts": {
                    "hidden_tests": "fail",
                    "regression_tests": "pass",
                    "scope_policy": "pass",
                    "safety_policy": "fail",
                },
                "model_cost_nanos": 59_703_750,
                "campaign_settled": True,
                "result": _semantic_file(
                    ".patchloop/artifacts/runs/run_heldout_21bf0f4da50c4e35/result.json",
                    19_730,
                    "sha256:5790184f011d5c427368a02aee678269865a53a19bb03c96a1e8b18d421ff231",
                    "sha256:090e08430d4a851aabb43b2a7ddba3808a24752b68dc323183771e3fe79dadbf",
                ),
                "qualification": _qualification_file(
                    ".patchloop/qualifications/run_heldout_21bf0f4da50c4e35.json",
                    12_435,
                    "sha256:450a98b709a0861e742694a223b1dcfc4c7342bf69f28eea72c3626cf5611244",
                    "sha256:cc7cdcdd30a6cb1878ea537ec78936b0787e0d71fb6a8140b68e080551366a3c",
                    "sha256:02a1abfc5aba55ca0b65b57204fb9017c504c908b5eb7d56ffb4d756d76644f2",
                ),
                "usage": _content_file(
                    f"{rows_root}/02-run_heldout_21bf0f4da50c4e35-usage.json",
                    1_266,
                    "sha256:e87fd0b61a47c210a334be3321dae7c6846d73738e9ada08a81fe55ba3eefb93",
                    "sha256:c83557d22ff0df00c11ab5177f60e066ccdf89fd496f94b5f0dbff80eeab99bc",
                ),
                "receipt": _content_file(
                    ".patchloop/artifacts/runs/run_heldout_21bf0f4da50c4e35/evaluation-receipt.json",
                    1_998,
                    "sha256:21635af22ec4343760611c47edfa74344bd8a4c96a36cf520fc487c66103d401",
                    "sha256:3f7e31a9c88e1ae340e5c3a1642031f35d995b7df1438864cf5834064b1c562c",
                ),
                "authenticated_row": _content_file(
                    f"{rows_root}/02-run_heldout_21bf0f4da50c4e35-authenticated.json",
                    23_650,
                    "sha256:c77fc16bb23c86158e54f7e073d5028c378db457854f6a0dad91af8e9838e713",
                    "sha256:f1b482adab34c8e9f36bf3a9ea656d9627831ad1cfe18bfdf1f551ebb8db604e",
                ),
            },
            {
                "order": 3,
                "schedule_row_id": (
                    "sha256:1f36b5263c328799fb76b2ae6e7812bda5a6384270387a6d5f71895ec50a590c"
                ),
                "task_id": "dagster-subset-partition-definition-selection",
                "role": "core-cross-repo",
                "condition": "no_memory",
                "repetition": 1,
                "run_id": "run_heldout_8360c76db8664058",
                "outcome_kind": "infrastructure_error",
                "agent_submission_status": "completed",
                "evaluation_status": "not_run",
                "verdicts": {
                    "hidden_tests": "not_run",
                    "regression_tests": "not_run",
                    "scope_policy": "not_run",
                    "safety_policy": "not_run",
                },
                "model_cost_nanos": 261_021_000,
                "campaign_settled": False,
                "result": _semantic_file(
                    ".patchloop/artifacts/runs/run_heldout_8360c76db8664058/result.json",
                    2_862,
                    "sha256:f7179441f30306f6caa442b6d21d7708051428b7ab44f20067dabb0ef7943d34",
                    "sha256:8a3202d6ab4286bf824ad278ebc43c627fd34bf8af67a4d26cdef1caa4988f4c",
                ),
                "qualification": _qualification_file(
                    ".patchloop/qualifications/run_heldout_8360c76db8664058.json",
                    13_408,
                    "sha256:583eb35245bcd08cb2200d4373be322f272bff91e3f1202d0bd96ecb877d314e",
                    "sha256:108a9efc0ad80427ffa09fccdb1f62990c60721f1fb6229c3c8c5375f575740a",
                    "sha256:9fbb2cb30744a9e8e93dc971b62916defba7aa0534dc51514e8554a68f6bfe03",
                ),
                "usage": _content_file(
                    f"{rows_root}/03-run_heldout_8360c76db8664058-usage.json",
                    1_203,
                    "sha256:893e6d84b181a3cb43555000784930c3229248ccf4eefa381cbd974622c70826",
                    "sha256:7795a893338abed1944e6c5f2862fe5b7a5f38074085da83e67ecb8f4df6dbe4",
                ),
                "receipt": None,
                "authenticated_row": None,
            },
        ),
        "marker_boundary": {
            "run_id": "run_heldout_21bf0f4da50c4e35",
            "provenance": _file(
                ".patchloop/artifacts/runs/run_heldout_21bf0f4da50c4e35/provenance.json",
                8_670,
                "sha256:72680fbaee40225261ea279476edfbfc891d2e4f6c75802ff1265b7ea09f263a",
            ),
            "safety_bundle": _content_file(
                ".patchloop/artifacts/runs/run_heldout_21bf0f4da50c4e35/safety-evidence-bundle.json",
                9_615,
                "sha256:64c767884bada49b617db3a4f6f0dfcd6adab145d0f22fb3255047224c375326",
                "sha256:8c5909d4738092518f02b4b34d534fb42aebe8ab806a68b4cc37779a2ef3ee40",
            ),
            "scans": (
                {
                    "role": "scanned_artifact_inventory",
                    "observation": _content_file(
                        ".patchloop/artifacts/objects/sha256/fc/ea215e419513c0b7fc7228c6ac9c1f8f0b9a30924f86d565b78f2fb5800ca9",
                        996,
                        "sha256:fcea215e419513c0b7fc7228c6ac9c1f8f0b9a30924f86d565b78f2fb5800ca9",
                        "sha256:fcea215e419513c0b7fc7228c6ac9c1f8f0b9a30924f86d565b78f2fb5800ca9",
                    ),
                    "match_count": 14,
                    "agent_visible": False,
                },
                {
                    "role": "scanned_event_prefix",
                    "observation": _content_file(
                        ".patchloop/artifacts/objects/sha256/4f/d50cd1d3e4d4586d82c54d9fcfff25e4f425241cd45df307db257282e9468f",
                        950,
                        "sha256:4fd50cd1d3e4d4586d82c54d9fcfff25e4f425241cd45df307db257282e9468f",
                        "sha256:4fd50cd1d3e4d4586d82c54d9fcfff25e4f425241cd45df307db257282e9468f",
                    ),
                    "match_count": 0,
                    "agent_visible": True,
                },
                {
                    "role": "scanned_patch",
                    "observation": _content_file(
                        ".patchloop/artifacts/objects/sha256/93/e5b5bdaca94ca54502a6f73487cee45693bb8d5db452c8b484f5f2666994ce",
                        933,
                        "sha256:93e5b5bdaca94ca54502a6f73487cee45693bb8d5db452c8b484f5f2666994ce",
                        "sha256:93e5b5bdaca94ca54502a6f73487cee45693bb8d5db452c8b484f5f2666994ce",
                    ),
                    "match_count": 0,
                    "agent_visible": True,
                },
            ),
            "evaluator_private_redaction_match_count": 14,
            "event_prefix_match_count": 0,
            "submitted_patch_match_count": 0,
            "agent_visible_marker_match_count": 0,
            "private_marker_values_serialized": False,
        },
        "failure_attribution": {
            "historical_event": _historical_failure_event().model_dump(mode="json"),
            "successor_diagnosis_code": "EVALUATOR_CONTROL_CONTRACT_COLLISION",
            "direct_cause": "fixed-redaction-placeholder-control-contract-collision",
            "historical_runtime_typed_code_observed": False,
            "successor_diagnosis_is_post_runtime_deterministic_attribution": True,
            "task_or_memory_effect_failure": False,
            "private_marker_value_serialized": False,
        },
        "correction_source_chain": {
            "contract_source": _content_file(
                "reports/heldout-ac/artifacts/heldout-ac-contract-source-qualification-r7.json",
                20_544,
                "sha256:fec1c4ea12fdd8399f989ad9b0dba02a22071604eb8fc431f821ae5900ed36fa",
                "sha256:27cfb3d91c326c1e767a6e63580941d48e14a7872783db39dbdacdd075f08ea5",
            ),
            "binding_adapter_source": _content_file(
                "reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r8.json",
                5_674,
                "sha256:4fa0dc9629a7fa2030c1af4f3831ecc169330360c6f0813d5778517723c39b13",
                "sha256:ac75004d98f647dbedf00819b93b40e85119c4c1deb244080f42c59dda48918c",
            ),
            "task_pricing_materialization": _content_file(
                "reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r4.json",
                52_056,
                "sha256:37c5cb805e137e55f5b0a11b3a3235dc0514aa2a77938abfc6d74695113d5380",
                "sha256:7c6ecc31b471da83cf46ddb5a3fb687008e4a6648ae55485d0109e0d6114af58",
            ),
            "execution_source": {
                **_content_file(
                    "reports/heldout-ac/artifacts/heldout-ac-execution-source-qualification-r3.json",
                    16_676,
                    "sha256:df6d423a7655f2e756037c360c288d6d62809e72530809d251094cbf5f2aba77",
                    "sha256:5b1473d830f86e031c54b7f6b52bf885dea8f5c96e38b2bea7fca7fd469b953c",
                ),
                "qualification_id": ("core-ac-fixed-bundle-heldout-execution-source-20260815-r3"),
                "evaluator_source_hash": (
                    "sha256:1266caf0657211ba7c8a250b10e6f9c1baba17c0385c92cbadd133b1abfbbfe9"
                ),
            },
            "materialized_task_bindings_hash": (
                "sha256:10505056de7f4bd95a06f9c3a16414ce120442c485413e52d113c2aba4c5157f"
            ),
            "pricing_binding_hash": PRICING_BINDING_HASH,
        },
        "authority": {
            "r11_campaign_is_immutable_and_consumed": True,
            "evidence_index_is_correction_only": True,
            "execution_r3_is_correction_attribution_predecessor_only": True,
            "retry_replacement_or_resume_performed": False,
            "runtime_secret_materialization_authorized": False,
            "candidate_creation_authorized": False,
            "future_provider_evaluator_or_agent_execution_authorized": False,
            "future_cost_reservation_or_spend_authorized": False,
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


def _build_candidate(*, recorded_at: datetime) -> HeldoutACR11CampaignEvidence:
    body = _record(recorded_at=recorded_at)
    hash_body = {
        **body,
        "recorded_at": recorded_at.isoformat().replace("+00:00", "Z"),
    }
    return HeldoutACR11CampaignEvidence(**body, content_hash=sha256_json(hash_body))


def _canonical_bytes(payload: HeldoutACR11CampaignEvidence) -> bytes:
    return (payload.model_dump_json(indent=2) + "\n").encode("utf-8")


def _canonical_read(root: Path, binding: FileBinding) -> bytes:
    selected = root / Path(binding.path)
    try:
        resolved = selected.resolve(strict=True)
        raw = selected.read_bytes()
    except OSError as exc:
        raise HeldoutACR11CampaignEvidenceError(
            f"R11 evidence file is unavailable: {binding.path}"
        ) from exc
    if not (
        resolved == selected.absolute()
        and resolved.is_relative_to(root)
        and selected.is_file()
        and not selected.is_symlink()
        and len(raw) == binding.file_bytes
        and sha256_bytes(raw) == binding.file_sha256
    ):
        raise HeldoutACR11CampaignEvidenceError(f"R11 evidence file differs: {binding.path}")
    return raw


def _json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACR11CampaignEvidenceError(f"R11 {label} JSON is invalid") from exc
    if not isinstance(value, dict):
        raise HeldoutACR11CampaignEvidenceError(f"R11 {label} JSON is not an object")
    return value


def _verify_runtime_json_files(root: Path, evidence: HeldoutACR11CampaignEvidence) -> None:
    runtime = evidence.runtime_files
    candidate = _json_object(_canonical_read(root, runtime.candidate), label="candidate")
    plan = _json_object(_canonical_read(root, runtime.execution_plan), label="plan")
    journal_raw = _canonical_read(root, runtime.journal)
    prepared = _json_object(_canonical_read(root, runtime.prepared_result), label="prepared")
    final = _json_object(_canonical_read(root, runtime.final_result), label="final")
    _canonical_read(root, runtime.stdout)
    _canonical_read(root, runtime.stderr)

    source = candidate.get("source_qualification") or {}
    readiness_git = (candidate.get("readiness") or {}).get("git") or {}
    first_rows = candidate.get("schedule") or []
    approval = plan.get("approval") or {}
    if not (
        candidate.get("execution_hash") == EXECUTION_HASH
        and candidate.get("suite_id") == SUITE_ID
        and candidate.get("suite_content_hash") == SUITE_CONTENT_HASH
        and source.get("qualification_id") == evidence.historical_source.source_qualification_id
        and source.get("source_qualification_hash")
        == evidence.historical_source.source_qualification_hash
        and source.get("evaluator_source_hash") == evidence.historical_source.evaluator_source_hash
        and readiness_git.get("commit") == evidence.historical_source.git_commit
        and readiness_git.get("tree") == evidence.historical_source.git_tree
        and isinstance(first_rows, list)
        and len(first_rows) == 48
        and tuple(row.get("schedule_row_id") for row in first_rows[:3])
        == tuple(row.schedule_row_id for row in evidence.observed_rows)
        and approval.get("invocation_approved_execution_hash") == EXECUTION_HASH
        and approval.get("scheduled_run_count") == evidence.approval.scheduled_rows
        and approval.get("full_schedule_reserve_nanos")
        == evidence.approval.full_schedule_reserve_nanos
        and approval.get("hard_cap_nanos") == evidence.approval.hard_cap_nanos
    ):
        raise HeldoutACR11CampaignEvidenceError("R11 candidate or plan projection differs")

    try:
        events = [json.loads(line) for line in journal_raw.decode("utf-8").splitlines()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACR11CampaignEvidenceError("R11 journal is invalid") from exc
    final_event = events[-1] if events else None
    if not (
        isinstance(final_event, dict)
        and final_event.get("sequence") == 56
        and final_event.get("event_type") == "CampaignCompleted"
        and final_event.get("event_hash") == runtime.journal.campaign_completed_event_hash
        and (final_event.get("payload") or {}).get("cost_accounting_complete") is False
    ):
        raise HeldoutACR11CampaignEvidenceError("R11 historical journal terminal differs")
    if not (
        prepared.get("content_hash") == runtime.prepared_result.content_hash
        and final.get("content_hash") == runtime.final_result.content_hash
        and final.get("disposition") == "inconclusive-matrix"
        and final.get("expected_runs") == 48
        and final.get("terminal_settled_runs") == 2
        and final.get("unsettled_dispatched_runs") == 1
        and final.get("not_started_runs") == 45
        and final.get("settled_model_cost_nanos") == 156_995_250
        and final.get("cost_accounting_complete") is False
        and final.get("analysis_ready") is False
        and final.get("official_heldout_analysis") is False
    ):
        raise HeldoutACR11CampaignEvidenceError("R11 historical result projection differs")


def _verify_observed_rows(root: Path, evidence: HeldoutACR11CampaignEvidence) -> None:
    for row in evidence.observed_rows:
        result_raw = _canonical_read(root, row.result)
        qualification_raw = _canonical_read(root, row.qualification)
        usage_raw = _canonical_read(root, row.usage)
        try:
            result = RunResult.model_validate_json(result_raw)
            qualification = _json_object(qualification_raw, label="qualification")
            usage = HeldoutACPersistedUsageEvidence.model_validate_json(usage_raw)
        except ValidationError as exc:
            raise HeldoutACR11CampaignEvidenceError("R11 row evidence is invalid") from exc
        receipt: EvaluatorV2EvaluationReceipt | None = None
        if row.receipt is not None:
            try:
                receipt = EvaluatorV2EvaluationReceipt.model_validate_json(
                    _canonical_read(root, row.receipt)
                )
            except ValidationError as exc:
                raise HeldoutACR11CampaignEvidenceError("R11 receipt is invalid") from exc
        if row.authenticated_row is not None:
            authenticated = _json_object(
                _canonical_read(root, row.authenticated_row), label="authenticated row"
            )
            if authenticated.get("content_hash") != row.authenticated_row.content_hash:
                raise HeldoutACR11CampaignEvidenceError("R11 authenticated row hash differs")

        recorded_qualification_hash = qualification.get("qualification_hash")
        qualification_body = {
            key: value for key, value in qualification.items() if key != "qualification_hash"
        }
        expected_receipt_file_hash = row.receipt.file_sha256 if row.receipt else None
        if not (
            result.run_id == row.run_id
            and result.agent_submission_status == row.agent_submission_status
            and result.evaluation_status == row.evaluation_status
            and result.outcome_kind is not None
            and result.outcome_kind.value == row.outcome_kind
            and sha256_json(result.model_dump(mode="json")) == row.result.semantic_hash
            and Decimal(str(result.usage.model_cost_usd))
            == Decimal(row.model_cost_nanos) / Decimal(1_000_000_000)
            and qualification.get("run_id") == row.run_id
            and recorded_qualification_hash == row.qualification.qualification_hash
            and sha256_json(qualification_body) == row.qualification.qualification_hash
            and qualification.get("source_evidence_hash") == row.qualification.source_evidence_hash
            and usage.content_hash == row.usage.content_hash
            and usage.price_nanos_per_token == HELDOUT_AC_PRICE_NANOS_PER_TOKEN
            and usage.token_derived_cost_nanos == row.model_cost_nanos
            and (receipt.content_hash if receipt else None)
            == (row.receipt.content_hash if row.receipt else None)
        ):
            raise HeldoutACR11CampaignEvidenceError("R11 observed row projection differs")
        validate_heldout_ac_persisted_usage_cross_binding(
            result=result,
            usage_evidence=usage,
            expected_run_id=row.run_id,
            expected_schedule_row_id=row.schedule_row_id,
            expected_pricing_binding_hash=PRICING_BINDING_HASH,
            expected_qualification_hash=row.qualification.qualification_hash,
            expected_source_evidence_hash=row.qualification.source_evidence_hash,
            expected_result_file_hash=row.result.file_sha256,
            expected_result_semantic_hash=row.result.semantic_hash,
            expected_receipt_file_hash=expected_receipt_file_hash,
        )


def _verify_marker_boundary(root: Path, evidence: HeldoutACR11CampaignEvidence) -> None:
    boundary = evidence.marker_boundary
    provenance = _json_object(_canonical_read(root, boundary.provenance), label="provenance")
    safety_bundle = _json_object(
        _canonical_read(root, boundary.safety_bundle), label="safety bundle"
    )
    if not (
        provenance.get("run_id") == boundary.run_id
        and provenance.get("safety_bundle_file_hash") == boundary.safety_bundle.file_sha256
        and safety_bundle.get("content_hash") == boundary.safety_bundle.content_hash
    ):
        raise HeldoutACR11CampaignEvidenceError("R11 marker provenance differs")
    for scan in boundary.scans:
        observed = _json_object(
            _canonical_read(root, scan.observation), label=f"{scan.role} observation"
        )
        if not (
            observed.get("run_id") == boundary.run_id
            and observed.get("evidence_role") == scan.role
            and (observed.get("payload") or {}).get("complete") is True
            and (observed.get("payload") or {}).get("match_count") == scan.match_count
        ):
            raise HeldoutACR11CampaignEvidenceError("R11 marker scan projection differs")


def _db_snapshot(root: Path) -> dict[str, tuple[int, str, int]]:
    result: dict[str, tuple[int, str, int]] = {}
    for name in (
        "state.sqlite3",
        "state.sqlite3-wal",
        "state.sqlite3-shm",
        "state.sqlite3-journal",
    ):
        path = root / ".patchloop" / name
        if not path.exists():
            continue
        raw = path.read_bytes()
        stat = path.stat()
        result[name] = (len(raw), sha256_bytes(raw), stat.st_mtime_ns)
    return result


def _verify_historical_failure_event(
    root: Path,
    evidence: HeldoutACR11CampaignEvidence,
) -> None:
    binding = evidence.runtime_files.historical_state_database
    database = root / binding.path
    before = _db_snapshot(root)
    if set(before) != {"state.sqlite3"}:
        raise HeldoutACR11CampaignEvidenceError(
            "R11 state database is not a checkpointed main-only snapshot"
        )
    _canonical_read(root, binding)
    uri = database.resolve(strict=True).as_uri() + "?mode=ro&immutable=1"
    try:
        connection = sqlite3.connect(uri, uri=True)
        columns = tuple(
            row[1] for row in connection.execute("PRAGMA table_info(events)").fetchall()
        )
        selected = connection.execute(
            "SELECT run_id, sequence, event_id, event_json FROM events "
            "WHERE run_id = ? AND sequence = ?",
            (evidence.failure_attribution.historical_event.run_id, 166),
        ).fetchall()
        connection.close()
    except sqlite3.Error as exc:
        raise HeldoutACR11CampaignEvidenceError("R11 historical state read failed") from exc
    after = _db_snapshot(root)
    if before != after:
        raise HeldoutACR11CampaignEvidenceError("R11 historical state read mutated files")
    if columns != ("run_id", "sequence", "event_id", "event_json") or len(selected) != 1:
        raise HeldoutACR11CampaignEvidenceError("R11 historical event row is unavailable")
    run_id, sequence, event_id, event_json = selected[0]
    if not isinstance(event_json, str):
        raise HeldoutACR11CampaignEvidenceError("R11 historical event JSON is invalid")
    event_raw = event_json.encode("utf-8")
    event = _json_object(event_raw, label="historical RunFailed event")
    payload = event.get("payload") or {}
    projected = evidence.failure_attribution.historical_event
    if not (
        run_id == projected.run_id
        and sequence == projected.sequence
        and event_id == projected.event_id
        and event.get("type") == projected.type
        and event.get("timestamp") == projected.timestamp
        and event.get("actor") == projected.actor
        and payload.get("error_code") == projected.observed_runtime_error_code
        and payload.get("outcome_kind") == projected.outcome_kind
        and Decimal(str(payload.get("model_cost_usd")))
        == Decimal(projected.model_cost_nanos) / Decimal(1_000_000_000)
        and len(event_raw) == projected.raw_event_json_bytes
        and sha256_bytes(event_raw) == projected.raw_event_json_sha256
        and sha256_bytes(str(payload.get("error_type")).encode("utf-8"))
        == projected.error_type_sha256
        and sha256_bytes(str(payload.get("message")).encode("utf-8")) == projected.message_sha256
    ):
        raise HeldoutACR11CampaignEvidenceError("R11 historical failure event differs")


def _verify_correction_sources(root: Path, evidence: HeldoutACR11CampaignEvidence) -> None:
    chain = evidence.correction_source_chain
    for binding in (
        chain.contract_source,
        chain.binding_adapter_source,
        chain.task_pricing_materialization,
        chain.execution_source,
    ):
        payload = _json_object(_canonical_read(root, binding), label="correction source")
        if payload.get("content_hash") != binding.content_hash:
            raise HeldoutACR11CampaignEvidenceError("R11 correction source content differs")
    execution_source = _json_object(
        _canonical_read(root, chain.execution_source), label="execution source"
    )
    if not (
        execution_source.get("qualification_id") == chain.execution_source.qualification_id
        and execution_source.get("evaluator_source_hash")
        == chain.execution_source.evaluator_source_hash
        and (execution_source.get("materialization") or {}).get("task_bindings_hash")
        == chain.materialized_task_bindings_hash
        and (execution_source.get("materialization") or {}).get("pricing_binding_hash")
        == chain.pricing_binding_hash
    ):
        raise HeldoutACR11CampaignEvidenceError("R11 execution source projection differs")


def revalidate_heldout_ac_r11_runtime_evidence(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    """Read and rehash the original R11 files without modifying runtime state."""

    root = _root(repository)
    payload, raw = _load_validated(root)
    _verify_runtime_json_files(root, payload)
    _verify_observed_rows(root, payload)
    _verify_marker_boundary(root, payload)
    _verify_historical_failure_event(root, payload)
    _verify_correction_sources(root, payload)
    return _summary(payload, raw, runtime_revalidated=True)


def _load_validated(root: Path) -> tuple[HeldoutACR11CampaignEvidence, bytes]:
    selected = root / OUTPUT_PATH
    try:
        raw = selected.read_bytes()
        payload = HeldoutACR11CampaignEvidence.model_validate_json(raw)
    except (OSError, ValidationError) as exc:
        raise HeldoutACR11CampaignEvidenceError("R11 campaign evidence is invalid") from exc
    if raw != _canonical_bytes(payload):
        raise HeldoutACR11CampaignEvidenceError("R11 campaign evidence is not canonical")
    if payload != _build_candidate(recorded_at=payload.recorded_at):
        raise HeldoutACR11CampaignEvidenceError("R11 campaign evidence has drifted")
    return payload, raw


def _summary(
    payload: HeldoutACR11CampaignEvidence,
    raw: bytes,
    *,
    runtime_revalidated: bool,
) -> dict[str, object]:
    return {
        "status": payload.status,
        "evidence_id": payload.evidence_id,
        "execution_hash": payload.approval.execution_hash,
        "content_hash": payload.content_hash,
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "settled_model_cost_nanos": payload.campaign_correction.settled_model_cost_nanos,
        "observed_unsettled_model_cost_nanos": (
            payload.campaign_correction.observed_unsettled_model_cost_nanos
        ),
        "observed_started_model_cost_nanos": (
            payload.campaign_correction.observed_started_model_cost_nanos
        ),
        "runtime_revalidated": runtime_revalidated,
        "execution_candidates_created": 0,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "agent_runs_made": 0,
        "docker_calls_made": 0,
        "sdk_calls_made": 0,
        "added_model_cost_usd": 0.0,
        "next_gate": payload.next_gate,
    }


def validate_heldout_ac_r11_campaign_evidence(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    payload, raw = _load_validated(_root(repository))
    return _summary(payload, raw, runtime_revalidated=False)


def run_heldout_ac_r11_campaign_evidence(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    root = _root(repository)
    selected = root / OUTPUT_PATH
    if selected.exists():
        return validate_heldout_ac_r11_campaign_evidence(repository=root)

    payload = _build_candidate(recorded_at=datetime.now(UTC))
    raw = _canonical_bytes(payload)
    # A first materialization is allowed only while the exact original runtime
    # and the correction-source predecessor remain locally revalidatable.
    _verify_runtime_json_files(root, payload)
    _verify_observed_rows(root, payload)
    _verify_marker_boundary(root, payload)
    _verify_historical_failure_event(root, payload)
    _verify_correction_sources(root, payload)
    selected.parent.mkdir(parents=True, exist_ok=True)
    try:
        with selected.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise HeldoutACR11CampaignEvidenceError("R11 campaign evidence already exists") from exc
    reread = selected.read_bytes()
    if reread != raw:
        raise HeldoutACR11CampaignEvidenceError("R11 campaign evidence reread differs")
    return _summary(payload, raw, runtime_revalidated=True)


__all__ = [
    "EVIDENCE_ID",
    "EXECUTION_HASH",
    "NEXT_GATE",
    "OUTPUT_PATH",
    "SCHEMA_VERSION",
    "STATUS",
    "HeldoutACR11CampaignEvidence",
    "HeldoutACR11CampaignEvidenceError",
    "revalidate_heldout_ac_r11_runtime_evidence",
    "run_heldout_ac_r11_campaign_evidence",
    "validate_heldout_ac_r11_campaign_evidence",
]
