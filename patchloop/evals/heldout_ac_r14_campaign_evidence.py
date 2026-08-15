"""Immutable, zero-authority evidence index for the consumed R14 campaign.

The historical campaign result is already a terminal v2 inconclusive result.
This module preserves those bytes and their typed historical reason unchanged,
then records a separate post-runtime deterministic attribution for the
producer/consumer runtime-budget mismatch.  It deliberately does not import
the persisted adapter, execution path, task loader, provider SDK, or Docker
boundary, so it cannot reauthenticate the historical row or create authority.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_contracts import HeldoutACFrozenModel
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_json

SCHEMA_VERSION = "heldout-ac-campaign-evidence-index-v3"
EVIDENCE_ID = "core-ac-fixed-bundle-heldout-r14-live-inconclusive-20260815-r1"
STATUS = "LIVE_CAMPAIGN_INCONCLUSIVE_RUNTIME_BUDGET_AUTHORITY_MISMATCH_INDEXED"
OUTPUT_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-r14-campaign-inconclusive-r1.json")
EXECUTION_HASH = "sha256:67475f578338026bc0c66ff3904ef1adfaaae8a33e2cba824d0f88a5d57307fd"
EXECUTION_DIGEST = EXECUTION_HASH.removeprefix("sha256:")
RUN_ID = "run_heldout_ca223089cb0c462e"
SUITE_ID = "core-ac-fixed-bundle-heldout-20260814-v1"
SUITE_CONTENT_HASH = "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
RUNTIME_TUPLE_HASH = "sha256:ff8ddf0a4735162820b3fd91966fb977fa996c9c04d9d4ee649d2353a01e95a8"
CAMPAIGN_COST_CONTROL_HASH = (
    "sha256:0f24b4175239c9c2539e33f3ded780c56512a1908f0907cc7200df554c5bc33e"
)
PRICING_BINDING_HASH = "sha256:83bb15d171564f32d0ca6df24f733a957032e144bbd0dfed49071e1b205a27e9"
NEXT_GATE = "bind-this-index-into-a-fresh-offline-source-qualified-successor"


class HeldoutACR14CampaignEvidenceError(ContractError):
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
    terminal_sequence: Literal[52]
    campaign_completed_event_hash: Literal[
        "sha256:e46119248590a0d7e9b2624f2ddc3638eba76af191649451562b7d6cdbff3c00"
    ]


class SourceQualificationFileBinding(ContentFileBinding):
    qualification_id: str
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class HistoricalSource(HeldoutACFrozenModel):
    git_commit: Literal["0fc8c1dbec71b292296d0ca5dd520c8b226fd1b6"]
    git_tree: Literal["3c37a307129f4dbebba9536dd44cac148be7a3cf"]
    suite_id: Literal[SUITE_ID]
    suite_content_hash: Literal[SUITE_CONTENT_HASH]
    suite_file: FileBinding
    runtime_tuple_hash: Literal[RUNTIME_TUPLE_HASH]
    schedule_hash: Literal[
        "sha256:b73e4cff23891636ec74c9f1a45993f2ad98e9f4c36e4b7ca2f6e5d18f178d86"
    ]
    source_qualification: SourceQualificationFileBinding


class Approval(HeldoutACFrozenModel):
    execution_hash: Literal[EXECUTION_HASH]
    scheduled_rows: Literal[48]
    full_schedule_reserve_nanos: Literal[57_600_000_000]
    hard_cap_nanos: Literal[60_000_000_000]
    approval_consumed: Literal[True]
    retry_replacement_or_resume_authorized: Literal[False]


class RuntimeFiles(HeldoutACFrozenModel):
    candidate_preflight: FileBinding
    execution_plan: FileBinding
    journal: JournalFileBinding
    prepared_result: ContentFileBinding
    final_result: ContentFileBinding


class CampaignObservation(HeldoutACFrozenModel):
    disposition: Literal["inconclusive-matrix"]
    expected_runs: Literal[48]
    started_runs: Literal[1]
    terminal_settled_runs: Literal[0]
    observed_unsettled_runs: Literal[1]
    not_started_runs: Literal[47]
    settled_model_cost_nanos: Literal[0]
    observed_unsettled_model_cost_nanos: Literal[126_342_000]
    observed_started_model_cost_nanos: Literal[126_342_000]
    historical_result_cost_accounting_complete: Literal[True]
    analysis_ready: Literal[False]
    official_heldout_analysis: Literal[False]
    memory_benefit_claim_authorized: Literal[False]
    broad_generalization_claim_authorized: Literal[False]
    campaign_settlement_preserved_without_reauthentication: Literal[True]

    @model_validator(mode="after")
    def validate_accounting(self) -> CampaignObservation:
        if not (
            self.started_runs == self.terminal_settled_runs + self.observed_unsettled_runs
            and self.expected_runs == self.started_runs + self.not_started_runs
            and self.observed_started_model_cost_nanos
            == self.settled_model_cost_nanos + self.observed_unsettled_model_cost_nanos
        ):
            raise ValueError("R14 campaign accounting differs")
        return self


class VerdictProjection(HeldoutACFrozenModel):
    hidden_tests: Literal["fail"]
    regression_tests: Literal["pass"]
    scope_policy: Literal["pass"]
    safety_policy: Literal["pass"]


class RuntimeBudgetProjection(HeldoutACFrozenModel):
    max_model_calls: int = Field(ge=1)
    max_tool_calls: int = Field(ge=1)
    max_total_tokens: int = Field(ge=1)
    wall_clock_timeout_seconds: int = Field(ge=1)
    token_budget_schema_version: Literal["cumulative-split-v1"]
    max_cumulative_input_tokens: int = Field(ge=1)
    max_cumulative_output_tokens: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_split(self) -> RuntimeBudgetProjection:
        if self.max_total_tokens != (
            self.max_cumulative_input_tokens + self.max_cumulative_output_tokens
        ):
            raise ValueError("R14 runtime budget split differs")
        return self


class ObservedRow(HeldoutACFrozenModel):
    order: Literal[1]
    wave: Literal[1]
    schedule_row_id: Literal[
        "sha256:8fd328a7e8684d8a24bf1bf8bf732ed7e46bf9c773d28bb5cf3c09b933939a42"
    ]
    task_id: Literal["loguru-post-2038-local-timezone-fallback"]
    role: Literal["core-same-repo"]
    condition: Literal["structured"]
    repetition: Literal[1]
    run_id: Literal[RUN_ID]
    underlying_outcome_kind: Literal["task_failure"]
    agent_submission_status: Literal["completed"]
    evaluation_status: Literal["completed"]
    raw_official: Literal[False]
    verdicts: VerdictProjection
    model_cost_nanos: Literal[126_342_000]
    campaign_settled: Literal[False]
    authenticated_row_persisted: Literal[False]
    qualification_schema_version: Literal["trace-qualification-v2"]
    qualification_check_count: Literal[28]
    qualification_passed_check_count: Literal[28]
    evaluator_v2_runtime_authenticated: Literal[True]
    evaluator_v2_completion_eligible: Literal[True]
    qualification_budget: RuntimeBudgetProjection
    result: SemanticFileBinding
    qualification: QualificationFileBinding
    receipt: ContentFileBinding
    usage: ContentFileBinding
    cost_observation: ContentFileBinding


class HistoricalConfound(HeldoutACFrozenModel):
    trigger: Literal["qualification-or-completion-contract-mismatch"]
    phase: Literal["authentication"]
    historical_reason_code: Literal["DURABLE_EVIDENCE_AUTHENTICATION_FAILED"]
    exception_type: Literal["ContractError"]
    run_started_event_written: Literal[True]
    durable_evidence_content_hash: Literal[
        "sha256:5fdde6cb0770b7414fe054627f113b98ca9ebe19ba38e67fd0bdf3511301b8b5"
    ]
    confound_content_hash: Literal[
        "sha256:aba6c2c0c837faca951abbf099822b7770de568d3a72ff57be8b26cb213487be"
    ]
    secret_or_exception_message_persisted: Literal[False]
    historical_reason_preserved_without_relabeling: Literal[True]


class PostRuntimeAttribution(HeldoutACFrozenModel):
    diagnosis_code: Literal["TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH"]
    direct_cause: Literal[
        "trace-qualification-v2-budget-compared-to-immutable-suite-runtime-instead-of-candidate-runtime-authority"
    ]
    trace_qualification_source_schema: Literal["trace-qualification-v2"]
    candidate_runtime_tuple_hash: Literal[RUNTIME_TUPLE_HASH]
    candidate_budget: RuntimeBudgetProjection
    immutable_suite_budget: RuntimeBudgetProjection
    historical_typed_diagnosis_code_observed: Literal[False]
    post_runtime_deterministic_attribution: Literal[True]
    changes_historical_reason_code: Literal[False]
    underlying_evaluator_outcome_preserved: Literal["task_failure"]
    campaign_confound_attributed_to_task_or_memory_effect: Literal[False]
    historical_row_reauthenticated: Literal[False]
    historical_row_reclassified: Literal[False]

    @model_validator(mode="after")
    def validate_mismatch(self) -> PostRuntimeAttribution:
        candidate = self.candidate_budget
        historical = self.immutable_suite_budget
        if not (
            candidate.max_cumulative_input_tokens == 1_000_000
            and candidate.max_cumulative_output_tokens == 100_000
            and candidate.max_total_tokens == 1_100_000
            and historical.max_cumulative_input_tokens == 4_000_000
            and historical.max_cumulative_output_tokens == 500_000
            and historical.max_total_tokens == 4_500_000
            and candidate != historical
        ):
            raise ValueError("R14 post-runtime budget attribution differs")
        return self


class HistoricalSourceChain(HeldoutACFrozenModel):
    contract_source: ContentFileBinding
    binding_adapter_source: ContentFileBinding
    task_pricing_materialization: ContentFileBinding
    execution_source: SourceQualificationFileBinding
    contract_source_hash: Literal[
        "sha256:218e5a2fc36aaff18474a66297f0c1a8f3fa66cb8526a893dec41829962557b8"
    ]
    persisted_adapter_source_hash: Literal[
        "sha256:9f101a615806692a8f7802e0331fc37b1d7955a97621ad61c30673c58ff70eab"
    ]
    binding_adapter_source_hash: Literal[
        "sha256:04eeab81a9a8130dbe5624068317ee3d68711465d18e3e8032ffbeb92e3fdcf6"
    ]
    materialization_source_hash: Literal[
        "sha256:c265e6f6e6484ea514d418fceacbd448c6db0972c7fdb4c21c770da8f56380cf"
    ]
    materialized_task_bindings_hash: Literal[
        "sha256:10505056de7f4bd95a06f9c3a16414ce120442c485413e52d113c2aba4c5157f"
    ]
    pricing_binding_hash: Literal[PRICING_BINDING_HASH]


class QualificationAuthority(HeldoutACFrozenModel):
    r14_campaign_is_immutable_and_consumed: Literal[True]
    evidence_index_is_append_only_attribution_only: Literal[True]
    historical_runtime_files_mutated: Literal[False]
    historical_row_reauthentication_authorized: Literal[False]
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


class HeldoutACR14CampaignEvidence(HeldoutACFrozenModel):
    schema_version: Literal[SCHEMA_VERSION]
    evidence_id: Literal[EVIDENCE_ID]
    status: Literal[STATUS]
    recorded_at: datetime
    historical_source: HistoricalSource
    approval: Approval
    runtime_files: RuntimeFiles
    campaign_observation: CampaignObservation
    observed_row: ObservedRow
    historical_confound: HistoricalConfound
    post_runtime_attribution: PostRuntimeAttribution
    historical_source_chain: HistoricalSourceChain
    authority: QualificationAuthority
    next_gate: Literal[NEXT_GATE]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_index(self) -> HeldoutACR14CampaignEvidence:
        if not (
            self.approval.execution_hash == EXECUTION_HASH
            and self.historical_source.runtime_tuple_hash == RUNTIME_TUPLE_HASH
            and self.observed_row.model_cost_nanos
            == self.campaign_observation.observed_started_model_cost_nanos
            and self.observed_row.qualification_budget
            == self.post_runtime_attribution.candidate_budget
            and self.observed_row.underlying_outcome_kind
            == self.post_runtime_attribution.underlying_evaluator_outcome_preserved
            and self.historical_source_chain.pricing_binding_hash == PRICING_BINDING_HASH
            and self.historical_confound.historical_reason_code
            == "DURABLE_EVIDENCE_AUTHENTICATION_FAILED"
            and self.post_runtime_attribution.changes_historical_reason_code is False
        ):
            raise ValueError("R14 campaign evidence cross-binding differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("R14 campaign evidence content hash differs")
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


def _candidate_budget() -> dict[str, Any]:
    return {
        "max_model_calls": 240,
        "max_tool_calls": 400,
        "max_total_tokens": 1_100_000,
        "wall_clock_timeout_seconds": 3_600,
        "token_budget_schema_version": "cumulative-split-v1",
        "max_cumulative_input_tokens": 1_000_000,
        "max_cumulative_output_tokens": 100_000,
    }


def _immutable_suite_budget() -> dict[str, Any]:
    return {
        "max_model_calls": 240,
        "max_tool_calls": 400,
        "max_total_tokens": 4_500_000,
        "wall_clock_timeout_seconds": 3_600,
        "token_budget_schema_version": "cumulative-split-v1",
        "max_cumulative_input_tokens": 4_000_000,
        "max_cumulative_output_tokens": 500_000,
    }


def _record(*, recorded_at: datetime) -> dict[str, Any]:
    rows_root = f".patchloop/experiments/heldout-ac/rows/{EXECUTION_DIGEST}"
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": EVIDENCE_ID,
        "status": STATUS,
        "recorded_at": recorded_at,
        "historical_source": {
            "git_commit": "0fc8c1dbec71b292296d0ca5dd520c8b226fd1b6",
            "git_tree": "3c37a307129f4dbebba9536dd44cac148be7a3cf",
            "suite_id": SUITE_ID,
            "suite_content_hash": SUITE_CONTENT_HASH,
            "suite_file": _file(
                "experiments/heldout-ac-suite-20260814-v1.yaml",
                13_348,
                "sha256:27157e26881cc277a9026e51d22a6f21fbf5bbb8f6c1c09eaa89aec607e52534",
            ),
            "runtime_tuple_hash": RUNTIME_TUPLE_HASH,
            "schedule_hash": (
                "sha256:b73e4cff23891636ec74c9f1a45993f2ad98e9f4c36e4b7ca2f6e5d18f178d86"
            ),
            "source_qualification": {
                **_content_file(
                    "reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r14.json",
                    21_984,
                    "sha256:259407d7c30113096844541b01f93ea18e78c5dd0d471c261311657acd7135a3",
                    "sha256:d71f0ad53cadb2957e1870cc40291a4979d0eed93321a0d082233408c03aed5c",
                ),
                "qualification_id": ("core-ac-fixed-bundle-heldout-preflight-source-20260815-r14"),
                "evaluator_source_hash": (
                    "sha256:f9660226185d33726bc3585381d0606234e6231faf5d9a9f62b79b44b67c20fd"
                ),
            },
        },
        "approval": {
            "execution_hash": EXECUTION_HASH,
            "scheduled_rows": 48,
            "full_schedule_reserve_nanos": 57_600_000_000,
            "hard_cap_nanos": 60_000_000_000,
            "approval_consumed": True,
            "retry_replacement_or_resume_authorized": False,
        },
        "runtime_files": {
            "candidate_preflight": _file(
                ".patchloop/heldout-ac-preflight-budget-v1.json",
                66_736,
                "sha256:b281a515c440896776a5205e8d7fa633c6e4db5ad922640e8f140ecc5d725efc",
            ),
            "execution_plan": _file(
                f".patchloop/experiments/plans/{EXECUTION_DIGEST}.json",
                83_389,
                "sha256:2057fc0c252ce97f1f29d55a3ec60cdeed169ece4e4de0d9517a95ab78912601",
            ),
            "journal": {
                **_file(
                    f".patchloop/experiments/journals/{EXECUTION_DIGEST}.jsonl",
                    48_045,
                    "sha256:8f4365522e647f916dcfc17fb0c4a9101b4dab1c56051a31ac03209734ce30a6",
                ),
                "terminal_sequence": 52,
                "campaign_completed_event_hash": (
                    "sha256:e46119248590a0d7e9b2624f2ddc3638eba76af191649451562b7d6cdbff3c00"
                ),
            },
            "prepared_result": _content_file(
                f".patchloop/experiments/heldout-ac/{EXECUTION_DIGEST}.prepared.json",
                27_059,
                "sha256:10d14f04c64c7868ac692b1fea7d0eff65830a2ed9ced6273326d23b1bed7170",
                "sha256:6f961ea25ea87ffe5539e0036a0f6f366a152e7c81520d2fe6225900b709a755",
            ),
            "final_result": _content_file(
                f".patchloop/experiments/heldout-ac/{EXECUTION_DIGEST}.json",
                27_676,
                "sha256:77a8a129f031041c447bc46ef8a29446bf1c39bae9ef9404cf1598f3f037ed34",
                "sha256:1860badbfc1d21b0ec244e44b04dc768b5c8530d7db179a2765c89312eec6619",
            ),
        },
        "campaign_observation": {
            "disposition": "inconclusive-matrix",
            "expected_runs": 48,
            "started_runs": 1,
            "terminal_settled_runs": 0,
            "observed_unsettled_runs": 1,
            "not_started_runs": 47,
            "settled_model_cost_nanos": 0,
            "observed_unsettled_model_cost_nanos": 126_342_000,
            "observed_started_model_cost_nanos": 126_342_000,
            "historical_result_cost_accounting_complete": True,
            "analysis_ready": False,
            "official_heldout_analysis": False,
            "memory_benefit_claim_authorized": False,
            "broad_generalization_claim_authorized": False,
            "campaign_settlement_preserved_without_reauthentication": True,
        },
        "observed_row": {
            "order": 1,
            "wave": 1,
            "schedule_row_id": (
                "sha256:8fd328a7e8684d8a24bf1bf8bf732ed7e46bf9c773d28bb5cf3c09b933939a42"
            ),
            "task_id": "loguru-post-2038-local-timezone-fallback",
            "role": "core-same-repo",
            "condition": "structured",
            "repetition": 1,
            "run_id": RUN_ID,
            "underlying_outcome_kind": "task_failure",
            "agent_submission_status": "completed",
            "evaluation_status": "completed",
            "raw_official": False,
            "verdicts": {
                "hidden_tests": "fail",
                "regression_tests": "pass",
                "scope_policy": "pass",
                "safety_policy": "pass",
            },
            "model_cost_nanos": 126_342_000,
            "campaign_settled": False,
            "authenticated_row_persisted": False,
            "qualification_schema_version": "trace-qualification-v2",
            "qualification_check_count": 28,
            "qualification_passed_check_count": 28,
            "evaluator_v2_runtime_authenticated": True,
            "evaluator_v2_completion_eligible": True,
            "qualification_budget": _candidate_budget(),
            "result": _semantic_file(
                f".patchloop/artifacts/runs/{RUN_ID}/result.json",
                19_649,
                "sha256:9bcc274f4f584bd33b319dfab260887afba00714facdd9edb399094b88933c41",
                "sha256:3a0bccaba6f50aba5db3f444cf1a368b2b53aeaa392d9877456dd5f1b4cd8c2e",
            ),
            "qualification": _qualification_file(
                f".patchloop/qualifications/{RUN_ID}.json",
                13_054,
                "sha256:d0caf49d7b0375f3a4bc7dbb972db49491aa63350ee3fa73e6c54d4c0e868824",
                "sha256:5bd8e7d67748bdbaccfe71fc9a55daed8a72635a3bddd336656abfd79ebc5d07",
                "sha256:3a3be4a82fcfb633d59229b051aacb72292dcf6c0cb50dd36a8ef9f531f777d4",
            ),
            "receipt": _content_file(
                f".patchloop/artifacts/runs/{RUN_ID}/evaluation-receipt.json",
                1_998,
                "sha256:5854fa708d2678152eb628c46e019d9b137b253956fc902afaec604e3488f3f7",
                "sha256:b7167999075e2a6798310771164f1bda78d2fdbabc1a8c8c5f56231855fe5dbe",
            ),
            "usage": _content_file(
                f"{rows_root}/01-{RUN_ID}-usage.json",
                1_270,
                "sha256:3c46007c2217f8eac64a7ad4967fb7d47c774b40b6fa0bb560a670d767ad0dbb",
                "sha256:684e561fbd3e52228e7bf4338c6cb0d2bd636d916113da0b6a2aa97858c62d69",
            ),
            "cost_observation": _content_file(
                f"{rows_root}/01-{RUN_ID}-cost-observation.json",
                1_143,
                "sha256:5462eade1d781fea8b661d1b7a34fd01a04de0dfe93f90670c0f3cd796a405fe",
                "sha256:b16ea41eb65bd718690dda1bbc2b542a2ae023a73eb467141baed1e024310642",
            ),
        },
        "historical_confound": {
            "trigger": "qualification-or-completion-contract-mismatch",
            "phase": "authentication",
            "historical_reason_code": "DURABLE_EVIDENCE_AUTHENTICATION_FAILED",
            "exception_type": "ContractError",
            "run_started_event_written": True,
            "durable_evidence_content_hash": (
                "sha256:5fdde6cb0770b7414fe054627f113b98ca9ebe19ba38e67fd0bdf3511301b8b5"
            ),
            "confound_content_hash": (
                "sha256:aba6c2c0c837faca951abbf099822b7770de568d3a72ff57be8b26cb213487be"
            ),
            "secret_or_exception_message_persisted": False,
            "historical_reason_preserved_without_relabeling": True,
        },
        "post_runtime_attribution": {
            "diagnosis_code": "TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH",
            "direct_cause": (
                "trace-qualification-v2-budget-compared-to-immutable-suite-runtime-instead-of-candidate-runtime-authority"
            ),
            "trace_qualification_source_schema": "trace-qualification-v2",
            "candidate_runtime_tuple_hash": RUNTIME_TUPLE_HASH,
            "candidate_budget": _candidate_budget(),
            "immutable_suite_budget": _immutable_suite_budget(),
            "historical_typed_diagnosis_code_observed": False,
            "post_runtime_deterministic_attribution": True,
            "changes_historical_reason_code": False,
            "underlying_evaluator_outcome_preserved": "task_failure",
            "campaign_confound_attributed_to_task_or_memory_effect": False,
            "historical_row_reauthenticated": False,
            "historical_row_reclassified": False,
        },
        "historical_source_chain": {
            "contract_source": _content_file(
                "reports/heldout-ac/artifacts/heldout-ac-contract-source-qualification-r8.json",
                21_501,
                "sha256:014085aea45b31c40d53a3c83483ca79585ec1ca105631a53b9c8e64ff465432",
                "sha256:77de0d1519cfc7032bda023bf1f1cca86449533fe3a1be39887d5784fc2d013b",
            ),
            "binding_adapter_source": _content_file(
                "reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r9.json",
                5_683,
                "sha256:6b1597d3b0f4202aeadaa424b67e06ec6e37ff7abfd8fd62f4af23208f3aaf68",
                "sha256:a26bb59cb5b16d6d3a94676b195b3fb36a21e974216088780c90c92aaac2bd2b",
            ),
            "task_pricing_materialization": _content_file(
                "reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r5.json",
                53_234,
                "sha256:34186e94134bffceaa05f893c24f9cdf5e1981e4e13c8b37de541ba49a5d6e17",
                "sha256:a7d6347c13368c60b65933041cfc33748fdb780549fa0ad9d358fcfcf4843f60",
            ),
            "execution_source": {
                **_content_file(
                    "reports/heldout-ac/artifacts/heldout-ac-execution-source-qualification-r6.json",
                    17_212,
                    "sha256:380c4ed66f1df3b7e80db490144ac7c1674de59229e6d72084b0e145b2b92232",
                    "sha256:375727d1c32c93105afb1875da0fadedb9dcb05bdfa17b088aade293bee72c1a",
                ),
                "qualification_id": "core-ac-fixed-bundle-heldout-execution-source-20260815-r6",
                "evaluator_source_hash": (
                    "sha256:965aef5aa3da61dcfbb11b7cc4e1f5ccfd3f0d83c450986f028ed812a6e1653b"
                ),
            },
            "contract_source_hash": (
                "sha256:218e5a2fc36aaff18474a66297f0c1a8f3fa66cb8526a893dec41829962557b8"
            ),
            "persisted_adapter_source_hash": (
                "sha256:9f101a615806692a8f7802e0331fc37b1d7955a97621ad61c30673c58ff70eab"
            ),
            "binding_adapter_source_hash": (
                "sha256:04eeab81a9a8130dbe5624068317ee3d68711465d18e3e8032ffbeb92e3fdcf6"
            ),
            "materialization_source_hash": (
                "sha256:c265e6f6e6484ea514d418fceacbd448c6db0972c7fdb4c21c770da8f56380cf"
            ),
            "materialized_task_bindings_hash": (
                "sha256:10505056de7f4bd95a06f9c3a16414ce120442c485413e52d113c2aba4c5157f"
            ),
            "pricing_binding_hash": PRICING_BINDING_HASH,
        },
        "authority": {
            "r14_campaign_is_immutable_and_consumed": True,
            "evidence_index_is_append_only_attribution_only": True,
            "historical_runtime_files_mutated": False,
            "historical_row_reauthentication_authorized": False,
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


def _build_candidate(*, recorded_at: datetime) -> HeldoutACR14CampaignEvidence:
    body = _record(recorded_at=recorded_at)
    hash_body = {
        **body,
        "recorded_at": recorded_at.isoformat().replace("+00:00", "Z"),
    }
    return HeldoutACR14CampaignEvidence(**body, content_hash=sha256_json(hash_body))


def _canonical_bytes(payload: HeldoutACR14CampaignEvidence) -> bytes:
    return (payload.model_dump_json(indent=2) + "\n").encode("utf-8")


def _canonical_read(root: Path, binding: FileBinding) -> bytes:
    selected = root / Path(binding.path)
    try:
        resolved = selected.resolve(strict=True)
        raw = selected.read_bytes()
    except OSError as exc:
        raise HeldoutACR14CampaignEvidenceError(
            f"R14 evidence file is unavailable: {binding.path}"
        ) from exc
    if not (
        resolved == selected.absolute()
        and resolved.is_relative_to(root)
        and selected.is_file()
        and not selected.is_symlink()
        and len(raw) == binding.file_bytes
        and sha256_bytes(raw) == binding.file_sha256
    ):
        raise HeldoutACR14CampaignEvidenceError(f"R14 evidence file differs: {binding.path}")
    return raw


def _json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACR14CampaignEvidenceError(f"R14 {label} JSON is invalid") from exc
    if not isinstance(value, dict):
        raise HeldoutACR14CampaignEvidenceError(f"R14 {label} JSON is not an object")
    return value


def _content_hash_matches(payload: dict[str, Any], expected: str) -> bool:
    return (
        payload.get("content_hash") == expected
        and sha256_json({key: value for key, value in payload.items() if key != "content_hash"})
        == expected
    )


def _verify_historical_sources(root: Path, evidence: HeldoutACR14CampaignEvidence) -> None:
    _canonical_read(root, evidence.historical_source.suite_file)
    preflight_binding = evidence.historical_source.source_qualification
    preflight = _json_object(_canonical_read(root, preflight_binding), label="preflight source")
    if not (
        _content_hash_matches(preflight, preflight_binding.content_hash)
        and preflight.get("qualification_id") == preflight_binding.qualification_id
        and preflight.get("evaluator_source_hash") == preflight_binding.evaluator_source_hash
        and preflight.get("schema_version")
        == "heldout-ac-preflight-dispatch-source-qualification-v13"
        and (preflight.get("authority") or {}).get("execution_candidates_created") == 0
    ):
        raise HeldoutACR14CampaignEvidenceError("R14 preflight source projection differs")

    chain = evidence.historical_source_chain
    contract = _json_object(_canonical_read(root, chain.contract_source), label="contract source")
    binding = _json_object(
        _canonical_read(root, chain.binding_adapter_source), label="binding source"
    )
    materialization = _json_object(
        _canonical_read(root, chain.task_pricing_materialization), label="materialization"
    )
    execution = _json_object(
        _canonical_read(root, chain.execution_source), label="execution source"
    )
    if not (
        _content_hash_matches(contract, chain.contract_source.content_hash)
        and contract.get("contract_source_hash") == chain.contract_source_hash
        and contract.get("persisted_adapter_source_hash") == chain.persisted_adapter_source_hash
        and _content_hash_matches(binding, chain.binding_adapter_source.content_hash)
        and binding.get("source_hash") == chain.binding_adapter_source_hash
        and binding.get("contract_source_qualification_hash") == chain.contract_source.content_hash
        and _content_hash_matches(materialization, chain.task_pricing_materialization.content_hash)
        and materialization.get("source_hash") == chain.materialization_source_hash
        and materialization.get("task_bindings_hash") == chain.materialized_task_bindings_hash
        and (materialization.get("pricing") or {}).get("content_hash") == chain.pricing_binding_hash
        and _content_hash_matches(execution, chain.execution_source.content_hash)
        and execution.get("qualification_id") == chain.execution_source.qualification_id
        and execution.get("evaluator_source_hash") == chain.execution_source.evaluator_source_hash
        and (execution.get("materialization") or {}).get("content_hash")
        == chain.task_pricing_materialization.content_hash
    ):
        raise HeldoutACR14CampaignEvidenceError("R14 historical source chain differs")


def _verify_runtime_files(root: Path, evidence: HeldoutACR14CampaignEvidence) -> None:
    runtime = evidence.runtime_files
    wrapper = _json_object(
        _canonical_read(root, runtime.candidate_preflight), label="candidate preflight"
    )
    plan = _json_object(_canonical_read(root, runtime.execution_plan), label="execution plan")
    journal_raw = _canonical_read(root, runtime.journal)
    prepared = _json_object(_canonical_read(root, runtime.prepared_result), label="prepared result")
    final = _json_object(_canonical_read(root, runtime.final_result), label="final result")

    candidate = wrapper.get("candidate") or {}
    readiness_git = (candidate.get("readiness") or {}).get("git") or {}
    source = candidate.get("source_qualification") or {}
    schedule = candidate.get("schedule") or []
    first = schedule[0] if isinstance(schedule, list) and schedule else {}
    if not (
        wrapper.get("schema_version") == "heldout-ac-preflight-v1"
        and wrapper.get("execution_hash") == EXECUTION_HASH
        and wrapper.get("source_qualification_hash")
        == evidence.historical_source.source_qualification.content_hash
        and wrapper.get("execution_candidate_ready") is True
        and wrapper.get("provider_calls_made") == 0
        and wrapper.get("evaluator_calls_made") == 0
        and wrapper.get("agent_runs_made") == 0
        and candidate.get("execution_hash") == EXECUTION_HASH
        and candidate.get("suite_id") == SUITE_ID
        and candidate.get("suite_content_hash") == SUITE_CONTENT_HASH
        and candidate.get("runtime_tuple_hash") == RUNTIME_TUPLE_HASH
        and candidate.get("schedule_hash") == evidence.historical_source.schedule_hash
        and candidate.get("pricing_binding_hash") == PRICING_BINDING_HASH
        and (candidate.get("campaign_cost_control") or {}).get("content_hash")
        == CAMPAIGN_COST_CONTROL_HASH
        and source.get("qualification_id")
        == evidence.historical_source.source_qualification.qualification_id
        and source.get("source_qualification_hash")
        == evidence.historical_source.source_qualification.content_hash
        and source.get("evaluator_source_hash")
        == evidence.historical_source.source_qualification.evaluator_source_hash
        and readiness_git.get("commit") == evidence.historical_source.git_commit
        and readiness_git.get("tree") == evidence.historical_source.git_tree
        and isinstance(schedule, list)
        and len(schedule) == 48
        and first.get("schedule_row_id") == evidence.observed_row.schedule_row_id
        and first.get("task_id") == evidence.observed_row.task_id
        and first.get("role") == evidence.observed_row.role
        and first.get("condition") == evidence.observed_row.condition
        and first.get("repetition") == evidence.observed_row.repetition
    ):
        raise HeldoutACR14CampaignEvidenceError("R14 candidate projection differs")

    approval = plan.get("approval") or {}
    runtime_contract = plan.get("runtime_contract") or {}
    if not (
        plan.get("schema_version") == "experiment-execution-plan-v2"
        and plan.get("plan_kind") == "heldout-ac-approved-campaign-v2"
        and plan.get("execution_hash") == EXECUTION_HASH
        and plan.get("ready") is True
        and runtime_contract.get("runtime_tuple_hash") == RUNTIME_TUPLE_HASH
        and runtime_contract.get("campaign_cost_control_hash") == CAMPAIGN_COST_CONTROL_HASH
        and runtime_contract.get("pricing_binding_hash") == PRICING_BINDING_HASH
        and approval.get("invocation_approved_execution_hash") == EXECUTION_HASH
        and approval.get("scheduled_run_count") == evidence.approval.scheduled_rows
        and approval.get("full_schedule_reserve_nanos")
        == evidence.approval.full_schedule_reserve_nanos
        and approval.get("hard_cap_nanos") == evidence.approval.hard_cap_nanos
    ):
        raise HeldoutACR14CampaignEvidenceError("R14 execution plan projection differs")

    try:
        events = [json.loads(line) for line in journal_raw.decode("utf-8").splitlines()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACR14CampaignEvidenceError("R14 journal is invalid") from exc
    terminal = events[-1] if events else None
    terminal_payload = terminal.get("payload") if isinstance(terminal, dict) else None
    if not (
        len(events) == runtime.journal.terminal_sequence
        and isinstance(terminal, dict)
        and terminal.get("sequence") == runtime.journal.terminal_sequence
        and terminal.get("event_type") == "CampaignCompleted"
        and terminal.get("event_hash") == runtime.journal.campaign_completed_event_hash
        and isinstance(terminal_payload, dict)
        and terminal_payload.get("disposition") == "inconclusive-matrix"
        and terminal_payload.get("terminal_settled_runs") == 0
        and terminal_payload.get("unsettled_dispatched_runs") == 1
        and terminal_payload.get("not_started_runs") == 47
        and terminal_payload.get("observed_started_model_cost_nanos") == 126_342_000
        and terminal_payload.get("cost_accounting_complete") is True
    ):
        raise HeldoutACR14CampaignEvidenceError("R14 journal terminal differs")

    observation = evidence.campaign_observation
    for label, payload, binding in (
        ("prepared", prepared, runtime.prepared_result),
        ("final", final, runtime.final_result),
    ):
        if not (
            _content_hash_matches(payload, binding.content_hash)
            and payload.get("disposition") == observation.disposition
            and payload.get("expected_runs") == observation.expected_runs
            and payload.get("terminal_settled_runs") == observation.terminal_settled_runs
            and payload.get("unsettled_dispatched_runs") == observation.observed_unsettled_runs
            and payload.get("not_started_runs") == observation.not_started_runs
            and payload.get("settled_model_cost_nanos") == observation.settled_model_cost_nanos
            and payload.get("observed_unsettled_model_cost_nanos")
            == observation.observed_unsettled_model_cost_nanos
            and payload.get("observed_started_model_cost_nanos")
            == observation.observed_started_model_cost_nanos
            and payload.get("cost_accounting_complete")
            is observation.historical_result_cost_accounting_complete
            and payload.get("analysis_ready") is False
            and payload.get("official_heldout_analysis") is False
            and payload.get("retry_replacement_or_resume_performed") is False
            and len(payload.get("settled_rows") or []) == 0
            and len(payload.get("not_started_rows") or []) == 47
        ):
            raise HeldoutACR14CampaignEvidenceError(f"R14 {label} result differs")
    if not (
        final.get("campaign_completed_event_hash") == runtime.journal.campaign_completed_event_hash
        and final.get("execution_plan_file_sha256") == runtime.execution_plan.file_sha256
        and final.get("journal_file_sha256") == runtime.journal.file_sha256
        and final.get("prepared_result_file_sha256") == runtime.prepared_result.file_sha256
        and final.get("prepared_result_content_hash") == runtime.prepared_result.content_hash
        and prepared.get("confound") == final.get("confound")
    ):
        raise HeldoutACR14CampaignEvidenceError("R14 terminal file cross-binding differs")


def _verify_observed_row(root: Path, evidence: HeldoutACR14CampaignEvidence) -> None:
    row = evidence.observed_row
    result = _json_object(_canonical_read(root, row.result), label="row result")
    qualification = _json_object(
        _canonical_read(root, row.qualification), label="trace qualification"
    )
    receipt = _json_object(_canonical_read(root, row.receipt), label="evaluation receipt")
    usage = _json_object(_canonical_read(root, row.usage), label="usage evidence")
    cost = _json_object(_canonical_read(root, row.cost_observation), label="cost observation")

    qualification_body = {
        key: value for key, value in qualification.items() if key != "qualification_hash"
    }
    checks = qualification.get("checks") or []
    cost_checks = [
        check
        for check in checks
        if isinstance(check, dict)
        and check.get("check_id") == "heldout_ac_full_schedule_cost_contract"
    ]
    details = cost_checks[0].get("details") if len(cost_checks) == 1 else None
    result_usage = result.get("usage") or {}
    if not (
        result.get("schema_version") == "run-result-v2"
        and result.get("run_id") == row.run_id
        and result.get("agent_submission_status") == row.agent_submission_status
        and result.get("evaluation_status") == row.evaluation_status
        and result.get("outcome_kind") == row.underlying_outcome_kind
        and result.get("official") is row.raw_official
        and result.get("verdicts") == row.verdicts.model_dump(mode="json")
        and sha256_json(result) == row.result.semantic_hash
        and Decimal(str(result_usage.get("model_cost_usd")))
        == Decimal(row.model_cost_nanos) / Decimal(1_000_000_000)
        and qualification.get("schema_version") == row.qualification_schema_version
        and qualification.get("run_id") == row.run_id
        and qualification.get("execution_hash") == EXECUTION_HASH
        and qualification.get("schedule_row_id") == row.schedule_row_id
        and qualification.get("qualified") is True
        and qualification.get("evaluation_reached") is True
        and qualification.get("outcome_kind") == row.underlying_outcome_kind
        and qualification.get("qualification_hash") == row.qualification.qualification_hash
        and sha256_json(qualification_body) == row.qualification.qualification_hash
        and qualification.get("source_evidence_hash") == row.qualification.source_evidence_hash
        and qualification.get("budget") == row.qualification_budget.model_dump(mode="json")
        and isinstance(checks, list)
        and len(checks) == row.qualification_check_count
        and sum(1 for check in checks if isinstance(check, dict) and check.get("passed") is True)
        == row.qualification_passed_check_count
        and qualification.get("evaluator_v2_runtime_authenticated")
        is row.evaluator_v2_runtime_authenticated
        and qualification.get("evaluator_v2_completion_eligible")
        is row.evaluator_v2_completion_eligible
        and isinstance(details, dict)
        and details.get("campaign_cost_control_hash") == CAMPAIGN_COST_CONTROL_HASH
        and details.get("manifest_cost_control_hash") == CAMPAIGN_COST_CONTROL_HASH
        and details.get("schedule_row_count") == 48
        and details.get("live_resume_supported") is False
    ):
        raise HeldoutACR14CampaignEvidenceError("R14 observed result or qualification differs")

    for label, payload, binding in (
        ("receipt", receipt, row.receipt),
        ("usage", usage, row.usage),
        ("cost observation", cost, row.cost_observation),
    ):
        if not _content_hash_matches(payload, binding.content_hash):
            raise HeldoutACR14CampaignEvidenceError(f"R14 {label} content differs")
    if not (
        receipt.get("run_id") == row.run_id
        and receipt.get("runtime_authenticated") is True
        and receipt.get("qualification_eligible") is True
        and receipt.get("result_file_hash") == row.result.file_sha256
        and usage.get("run_id") == row.run_id
        and usage.get("schedule_row_id") == row.schedule_row_id
        and usage.get("qualification_hash") == row.qualification.qualification_hash
        and usage.get("source_evidence_hash") == row.qualification.source_evidence_hash
        and usage.get("persisted_result_file_hash") == row.result.file_sha256
        and usage.get("evaluator_v2_receipt_file_hash") == row.receipt.file_sha256
        and usage.get("pricing_binding_hash") == PRICING_BINDING_HASH
        and usage.get("token_derived_cost_nanos") == row.model_cost_nanos
        and cost.get("run_id") == row.run_id
        and cost.get("schedule_row_id") == row.schedule_row_id
        and cost.get("pricing_binding_hash") == PRICING_BINDING_HASH
        and cost.get("result_file_sha256") == row.result.file_sha256
        and cost.get("result_semantic_hash") == row.result.semantic_hash
        and cost.get("token_derived_cost_nanos") == row.model_cost_nanos
    ):
        raise HeldoutACR14CampaignEvidenceError("R14 durable row cross-binding differs")


def _verify_historical_confound(root: Path, evidence: HeldoutACR14CampaignEvidence) -> None:
    final = _json_object(
        _canonical_read(root, evidence.runtime_files.final_result), label="final confound"
    )
    confound = final.get("confound") or {}
    durable = confound.get("durable_evidence") or {}
    row = evidence.observed_row
    historical = evidence.historical_confound
    if not (
        confound.get("trigger") == historical.trigger
        and confound.get("phase") == historical.phase
        and confound.get("reason_code") == historical.historical_reason_code
        and confound.get("exception_type") == historical.exception_type
        and confound.get("run_started_event_written") is True
        and confound.get("secret_or_exception_message_persisted") is False
        and "message" not in confound
        and confound.get("content_hash") == historical.confound_content_hash
        and durable.get("content_hash") == historical.durable_evidence_content_hash
        and durable.get("run_id") == row.run_id
        and durable.get("result_file_sha256") == row.result.file_sha256
        and durable.get("result_semantic_hash") == row.result.semantic_hash
        and durable.get("qualification_file_sha256") == row.qualification.file_sha256
        and durable.get("qualification_hash") == row.qualification.qualification_hash
        and durable.get("receipt_file_sha256") == row.receipt.file_sha256
        and durable.get("receipt_content_hash") == row.receipt.content_hash
        and durable.get("usage_file_sha256") == row.usage.file_sha256
        and durable.get("usage_evidence_hash") == row.usage.content_hash
        and durable.get("cost_observation_file_sha256") == row.cost_observation.file_sha256
        and durable.get("cost_observation_content_hash") == row.cost_observation.content_hash
        and durable.get("token_derived_cost_nanos") == row.model_cost_nanos
        and durable.get("evaluator_failure_code") is None
        and durable.get("evaluator_failure_event") is None
    ):
        raise HeldoutACR14CampaignEvidenceError("R14 historical confound differs")


def revalidate_heldout_ac_r14_runtime_evidence(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    """Read and rehash the exact historical R14 files without reauthentication."""

    root = _root(repository)
    payload, raw = _load_validated(root)
    _verify_historical_sources(root, payload)
    _verify_runtime_files(root, payload)
    _verify_observed_row(root, payload)
    _verify_historical_confound(root, payload)
    return _summary(payload, raw, runtime_revalidated=True)


def _load_validated(root: Path) -> tuple[HeldoutACR14CampaignEvidence, bytes]:
    selected = root / OUTPUT_PATH
    try:
        raw = selected.read_bytes()
        payload = HeldoutACR14CampaignEvidence.model_validate_json(raw)
    except (OSError, ValidationError) as exc:
        raise HeldoutACR14CampaignEvidenceError("R14 campaign evidence is invalid") from exc
    if raw != _canonical_bytes(payload):
        raise HeldoutACR14CampaignEvidenceError("R14 campaign evidence is not canonical")
    if payload != _build_candidate(recorded_at=payload.recorded_at):
        raise HeldoutACR14CampaignEvidenceError("R14 campaign evidence has drifted")
    return payload, raw


def _summary(
    payload: HeldoutACR14CampaignEvidence,
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
        "terminal_settled_runs": payload.campaign_observation.terminal_settled_runs,
        "observed_unsettled_runs": payload.campaign_observation.observed_unsettled_runs,
        "not_started_runs": payload.campaign_observation.not_started_runs,
        "observed_started_model_cost_nanos": (
            payload.campaign_observation.observed_started_model_cost_nanos
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


def validate_heldout_ac_r14_campaign_evidence(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    payload, raw = _load_validated(_root(repository))
    return _summary(payload, raw, runtime_revalidated=False)


def run_heldout_ac_r14_campaign_evidence(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    root = _root(repository)
    selected = root / OUTPUT_PATH
    if selected.exists():
        return validate_heldout_ac_r14_campaign_evidence(repository=root)

    payload = _build_candidate(recorded_at=datetime.now(UTC))
    raw = _canonical_bytes(payload)
    _verify_historical_sources(root, payload)
    _verify_runtime_files(root, payload)
    _verify_observed_row(root, payload)
    _verify_historical_confound(root, payload)
    selected.parent.mkdir(parents=True, exist_ok=True)
    try:
        with selected.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise HeldoutACR14CampaignEvidenceError("R14 campaign evidence already exists") from exc
    reread = selected.read_bytes()
    if reread != raw:
        raise HeldoutACR14CampaignEvidenceError("R14 campaign evidence reread differs")
    return _summary(payload, raw, runtime_revalidated=True)


__all__ = [
    "EVIDENCE_ID",
    "EXECUTION_HASH",
    "NEXT_GATE",
    "OUTPUT_PATH",
    "SCHEMA_VERSION",
    "STATUS",
    "HeldoutACR14CampaignEvidence",
    "HeldoutACR14CampaignEvidenceError",
    "revalidate_heldout_ac_r14_runtime_evidence",
    "run_heldout_ac_r14_campaign_evidence",
    "validate_heldout_ac_r14_campaign_evidence",
]
