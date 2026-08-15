"""Immutable, zero-authority evidence index for the consumed R15 campaign."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_contracts import HeldoutACFrozenModel
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_json

SCHEMA_VERSION = "heldout-ac-campaign-evidence-index-v4"
EVIDENCE_ID = "core-ac-fixed-bundle-heldout-r15-live-inconclusive-20260815-r1"
STATUS = "LIVE_CAMPAIGN_INCONCLUSIVE_V2_BUDGET_TERMINAL_BINDING_MISMATCH_INDEXED"
OUTPUT_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-r15-campaign-inconclusive-r1.json")
EXECUTION_HASH = "sha256:e11ece5552e2f574ee334ec98a93a9929732df7592096bcd0478717dfd64f8bc"
EXECUTION_DIGEST = EXECUTION_HASH.removeprefix("sha256:")
SUITE_ID = "core-ac-fixed-bundle-heldout-20260814-v1"
SUITE_CONTENT_HASH = "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
RUNTIME_TUPLE_HASH = "sha256:ff8ddf0a4735162820b3fd91966fb977fa996c9c04d9d4ee649d2353a01e95a8"
COST_CONTROL_HASH = "sha256:ba44f6dd5bdacff333abfecc12633d45b5233f72556fba6e49177463f3ec5e07"
PRICING_BINDING_HASH = "sha256:83bb15d171564f32d0ca6df24f733a957032e144bbd0dfed49071e1b205a27e9"
RUN3_ID = "run_heldout_0bd5b4c984234156"
NEXT_GATE = "bind-this-index-into-a-fresh-zero-authority-source-qualified-successor"


class HeldoutACR15CampaignEvidenceError(ContractError):
    pass


class BoundFile(HeldoutACFrozenModel):
    path: str
    file_bytes: int = Field(ge=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")


class RuntimeFiles(HeldoutACFrozenModel):
    candidate_preflight: BoundFile
    execution_plan: BoundFile
    journal: BoundFile
    prepared_result: BoundFile
    final_result: BoundFile
    confounded_result: BoundFile
    confounded_qualification: BoundFile
    confounded_usage: BoundFile
    confounded_cost_observation: BoundFile


class UsageSummary(HeldoutACFrozenModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    reasoning_output_tokens: int = Field(ge=0)
    model_calls: int = Field(ge=0)
    input_token_count_calls: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    wall_clock_ms: int = Field(ge=0)
    model_cost_nanos: int = Field(ge=0)


class SettledRowSummary(HeldoutACFrozenModel):
    order: int = Field(ge=1, le=2)
    task_id: Literal["loguru-post-2038-local-timezone-fallback"]
    condition: Literal["structured", "no_memory"]
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    outcome_kind: Literal["resolved", "task_failure"]
    hidden_tests: Literal["pass", "fail"]
    regression_tests: Literal["pass"]
    scope_policy: Literal["pass"]
    safety_policy: Literal["pass"]
    usage: UsageSummary


class BudgetTerminalProjection(HeldoutACFrozenModel):
    order: Literal[3]
    task_id: Literal["dagster-subset-partition-definition-selection"]
    condition: Literal["no_memory"]
    run_id: Literal[RUN3_ID]
    result_schema_version: Literal["run-result-v2"]
    result_terminal_error: dict[str, str]
    qualification_schema_version: Literal["trace-qualification-v2"]
    qualification_check_count: Literal[27]
    qualification_passed_check_count: Literal[26]
    failed_check_id: Literal["terminal_result_integrity"]
    failed_binding_required: Literal[True]
    failed_binding_valid: Literal[False]
    blocked_event_id: Literal["evt_53dea5c1ef8d4be191961be6bab495dd"]
    blocked_event_sequence: Literal[419]
    blocked_event_json_sha256: Literal[
        "sha256:79f1a1a1576df35e5fd3c7394279ddd804108f17642eca5437a36ad1bce34e4b"
    ]
    blocked_payload_hash: Literal[
        "sha256:372209421ac9ed370cb2385b8e2bc89a1b159ef22c5c353c55ade95ca7e6a557"
    ]
    blocked_reason_code: Literal["exact_request_budget_exceeded"]
    blocked_error_code: Literal["MODEL_GENERATION_BUDGET_EXCEEDED"]
    requested_input_tokens: Literal[34327]
    remaining_input_tokens: Literal[7116]
    max_cumulative_input_tokens: Literal[1000000]
    max_total_tokens: Literal[1100000]
    terminal_event_id: Literal["evt_2fa059c3fea54482a32ef3f113e68b5c"]
    terminal_event_sequence: Literal[421]
    terminal_event_json_sha256: Literal[
        "sha256:731df9bb8ce74d4b458d3ac467fa4713e314c845155cd316215dd04b836fd318"
    ]
    terminal_error_type: Literal["ModelGenerationBudgetError"]
    terminal_error_code: Literal["MODEL_GENERATION_BUDGET_EXCEEDED"]
    terminal_error_details_hash: Literal[
        "sha256:372209421ac9ed370cb2385b8e2bc89a1b159ef22c5c353c55ade95ca7e6a557"
    ]
    usage: UsageSummary

    @model_validator(mode="after")
    def validate_terminal_projection(self) -> BudgetTerminalProjection:
        if not (
            self.result_terminal_error == {"code": "AGENT_SUBMISSION_FAILED", "phase": "agent"}
            and self.blocked_payload_hash == self.terminal_error_details_hash
            and self.usage.input_tokens + self.requested_input_tokens
            > self.max_cumulative_input_tokens
            and self.usage.model_cost_nanos == 911_878_500
        ):
            raise ValueError("R15 budget terminal projection differs")
        return self


class CampaignObservation(HeldoutACFrozenModel):
    disposition: Literal["inconclusive-matrix"]
    expected_runs: Literal[48]
    started_runs: Literal[3]
    terminal_settled_runs: Literal[2]
    observed_unsettled_runs: Literal[1]
    not_started_runs: Literal[45]
    settled_model_cost_nanos: Literal[200233500]
    observed_unsettled_model_cost_nanos: Literal[911878500]
    observed_started_model_cost_nanos: Literal[1112112000]
    cost_accounting_complete: Literal[True]
    analysis_ready: Literal[False]
    official_heldout_analysis: Literal[False]
    memory_benefit_claim_authorized: Literal[False]

    @model_validator(mode="after")
    def validate_accounting(self) -> CampaignObservation:
        if not (
            self.started_runs == self.terminal_settled_runs + self.observed_unsettled_runs
            and self.expected_runs == self.started_runs + self.not_started_runs
            and self.observed_started_model_cost_nanos
            == self.settled_model_cost_nanos + self.observed_unsettled_model_cost_nanos
        ):
            raise ValueError("R15 campaign accounting differs")
        return self


class HistoricalConfound(HeldoutACFrozenModel):
    trigger: Literal["qualification-or-completion-contract-mismatch"]
    phase: Literal["authentication"]
    historical_reason_code: Literal["DURABLE_EVIDENCE_AUTHENTICATION_FAILED"]
    exception_type: Literal["ContractError"]
    durable_evidence_content_hash: Literal[
        "sha256:098ed0c294b112c33f5967de987bda0b24a8123eaffe62e79de55fe3c7634372"
    ]
    confound_content_hash: Literal[
        "sha256:0c45220ffbeafb585d5884b6e667f261d5404b341d1a5109189af60c90ea4659"
    ]
    historical_reason_preserved_without_relabeling: Literal[True]


class PostRuntimeAttribution(HeldoutACFrozenModel):
    diagnosis_code: Literal["TRACE_QUALIFICATION_V2_TERMINAL_RESULT_SCHEMA_MISMATCH"]
    direct_cause: Literal[
        "trace-qualification-v2-required-run-result-v1-rich-budget-terminal-error-from-sanitized-run-result-v2"
    ]
    version_aware_fix: Literal[
        "v1-rich-terminal-remains-exact-v2-binds-sanitized-result-to-exact-blocked-and-runfailed-events"
    ]
    historical_typed_diagnosis_code_observed: Literal[False]
    post_runtime_deterministic_attribution: Literal[True]
    changes_historical_reason_code: Literal[False]
    historical_row_reauthenticated: Literal[False]
    historical_row_reclassified: Literal[False]
    task_or_memory_effect_claimed: Literal[False]


class EvidenceAuthority(HeldoutACFrozenModel):
    r15_campaign_is_immutable_and_consumed: Literal[True]
    evidence_index_is_append_only_attribution_only: Literal[True]
    historical_runtime_files_mutated: Literal[False]
    historical_row_reauthentication_authorized: Literal[False]
    retry_replacement_or_resume_performed: Literal[False]
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


class HeldoutACR15CampaignEvidence(HeldoutACFrozenModel):
    schema_version: Literal[SCHEMA_VERSION]
    evidence_id: Literal[EVIDENCE_ID]
    status: Literal[STATUS]
    recorded_at: datetime
    historical_git_commit: Literal["2571a7a31bb0071bf1d984ea5e6ff852c1713b13"]
    historical_git_tree: Literal["e6d3f6ded652c33eb105c2ee3a24e1dbcdc5a635"]
    suite_id: Literal[SUITE_ID]
    suite_content_hash: Literal[SUITE_CONTENT_HASH]
    execution_hash: Literal[EXECUTION_HASH]
    runtime_tuple_hash: Literal[RUNTIME_TUPLE_HASH]
    campaign_cost_control_hash: Literal[COST_CONTROL_HASH]
    pricing_binding_hash: Literal[PRICING_BINDING_HASH]
    full_schedule_reserve_nanos: Literal[57600000000]
    hard_cap_nanos: Literal[60000000000]
    approval_consumed: Literal[True]
    source_chain: tuple[BoundFile, ...]
    runtime_files: RuntimeFiles
    campaign_observation: CampaignObservation
    settled_rows: tuple[SettledRowSummary, SettledRowSummary]
    budget_terminal: BudgetTerminalProjection
    historical_confound: HistoricalConfound
    post_runtime_attribution: PostRuntimeAttribution
    authority: EvidenceAuthority
    next_gate: Literal[NEXT_GATE]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_index(self) -> HeldoutACR15CampaignEvidence:
        if not (
            len(self.source_chain) == 5
            and tuple(row.order for row in self.settled_rows) == (1, 2)
            and sum(row.usage.model_cost_nanos for row in self.settled_rows)
            == self.campaign_observation.settled_model_cost_nanos
            and self.budget_terminal.usage.model_cost_nanos
            == self.campaign_observation.observed_unsettled_model_cost_nanos
            and self.post_runtime_attribution.changes_historical_reason_code is False
            and self.content_hash
            == sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("R15 campaign evidence cross-binding differs")
        return self


def _file(
    path: str,
    size: int,
    digest: str,
    *,
    content_hash: str | None = None,
    semantic_hash: str | None = None,
) -> dict[str, Any]:
    return {
        "path": path,
        "file_bytes": size,
        "file_sha256": digest,
        "content_hash": content_hash,
        "semantic_hash": semantic_hash,
    }


def _usage(
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int,
    model_calls: int,
    count_calls: int,
    tool_calls: int,
    wall_ms: int,
    cost_nanos: int,
) -> dict[str, int]:
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_output_tokens": reasoning_tokens,
        "model_calls": model_calls,
        "input_token_count_calls": count_calls,
        "tool_calls": tool_calls,
        "wall_clock_ms": wall_ms,
        "model_cost_nanos": cost_nanos,
    }


def _record(*, recorded_at: datetime) -> dict[str, Any]:
    rows_root = f".patchloop/experiments/heldout-ac/rows/{EXECUTION_DIGEST}"
    run_root = f".patchloop/artifacts/runs/{RUN3_ID}"
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": EVIDENCE_ID,
        "status": STATUS,
        "recorded_at": recorded_at,
        "historical_git_commit": "2571a7a31bb0071bf1d984ea5e6ff852c1713b13",
        "historical_git_tree": "e6d3f6ded652c33eb105c2ee3a24e1dbcdc5a635",
        "suite_id": SUITE_ID,
        "suite_content_hash": SUITE_CONTENT_HASH,
        "execution_hash": EXECUTION_HASH,
        "runtime_tuple_hash": RUNTIME_TUPLE_HASH,
        "campaign_cost_control_hash": COST_CONTROL_HASH,
        "pricing_binding_hash": PRICING_BINDING_HASH,
        "full_schedule_reserve_nanos": 57_600_000_000,
        "hard_cap_nanos": 60_000_000_000,
        "approval_consumed": True,
        "source_chain": (
            _file(
                "reports/heldout-ac/artifacts/heldout-ac-contract-source-qualification-r10.json",
                22_080,
                "sha256:3e98b35ebae9b7d4a50a23e4f984fdf4be213702cb296c55394ef1e8ceb361e0",
                content_hash="sha256:c04127095d998ee345e4449f897de5b5c6666c75ade6f12d2784e59254b97a32",
            ),
            _file(
                "reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r10.json",
                6_376,
                "sha256:376e94d84b7bdb5f0a2ec507fcc12e2016fbd718817e05a913c86824bc3e2ef4",
                content_hash="sha256:27283c8a1d1075a9e22f395eed0d845069531e230d30aab2aeda75dc76c17626",
            ),
            _file(
                "reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r6.json",
                53_250,
                "sha256:1a3568e372c9b3af1e384addfb3b5d8351138625072b3af95ccc6290bed3d975",
                content_hash="sha256:61f65a54891ef60c07c1edbadd67040cdf5d31e21e4c6e1d3ac97d7f94e419fb",
            ),
            _file(
                "reports/heldout-ac/artifacts/heldout-ac-execution-source-qualification-r7.json",
                20_007,
                "sha256:4202aa19b148e9e3567cb79c3b928fe0bfeb08a2b2d980f46e9899ff6489e7f1",
                content_hash="sha256:783b757d07b76d943899ff3a2d66d1033fc84b44026e4472f263495f9877e80a",
            ),
            _file(
                "reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r15.json",
                24_713,
                "sha256:0ed3be6f51213867acc4f27560f87ae33103e5ee60deb237affe942a7ebd6cbc",
                content_hash="sha256:f0e100d44f713cde134882025481b0038bfb0b4d880f4192e0558dc806e6809c",
            ),
        ),
        "runtime_files": {
            "candidate_preflight": _file(
                ".patchloop/heldout-ac-preflight-r15-20260815T155352146.json",
                66_841,
                "sha256:0f11065ca900d1136de44cbf30d9bf759e271fc507fddb54aaa4eafe147b9f6a",
            ),
            "execution_plan": _file(
                f".patchloop/experiments/plans/{EXECUTION_DIGEST}.json",
                83_599,
                "sha256:b8ca228a817ce732b6e450a3d9a6db3ecd13d9628a7fda674d3957adef6cf6a4",
            ),
            "journal": _file(
                f".patchloop/experiments/journals/{EXECUTION_DIGEST}.jsonl",
                51_292,
                "sha256:5459d339d2afc3d309e5c747edcaf0823df0e65fa3618e95c61b3776893be4bb",
            ),
            "prepared_result": _file(
                f".patchloop/experiments/heldout-ac/{EXECUTION_DIGEST}.prepared.json",
                87_825,
                "sha256:e6969ee9bf975c511df99abce35dd81758f55665a4fc8d47edb0b0f5df66d108",
                content_hash="sha256:bc0b8dde93a05752d153a9bfc62979cb6d950bf8f8d37da865118a34045aaa36",
            ),
            "final_result": _file(
                f".patchloop/experiments/heldout-ac/{EXECUTION_DIGEST}.json",
                88_442,
                "sha256:6cd811c27ec8533a034f95a40893780a2e90a0b5f1d35ad0a2db950691414269",
                content_hash="sha256:d6e78bd93e74aad332e93b24a7d5cacfab397978a52bfea82d59da251eeb05a8",
            ),
            "confounded_result": _file(
                f"{run_root}/result.json",
                2_467,
                "sha256:2c70166a7b523078c9bdfac08228058c2f3ab767e04245f848c1c086e2a752ab",
                semantic_hash="sha256:0f804f94320d1ba0781979b15c112a86d8885f4d16e27066838fe1b24c296865",
            ),
            "confounded_qualification": _file(
                f".patchloop/qualifications/{RUN3_ID}.json",
                17_303,
                "sha256:0951a787f29b71861a519e186f13493900578e2086341a5a92838a5146f76bbd",
                semantic_hash="sha256:ff157a784eead32bd88ab95e96b53be03b544cefa1721096415ae04939233abf",
            ),
            "confounded_usage": _file(
                f"{rows_root}/03-{RUN3_ID}-usage.json",
                1_205,
                "sha256:054c52b1c5ef8549bd11a52c0aa0a5429530e06e4809beb20150f859be93f1f6",
                content_hash="sha256:6bf73d077ee533b93df977aecc1155ca32dd09c0a3c4ede2b2082f5f630819b1",
            ),
            "confounded_cost_observation": _file(
                f"{rows_root}/03-{RUN3_ID}-cost-observation.json",
                1_147,
                "sha256:5883e89a4852e32909c967d1e350b5c21fa85148c8e79a948e47db3c75eb430d",
                content_hash="sha256:cfb2585ca46b848b597e922537c2ec0859f163db754598a88cf11533f8de6e1c",
            ),
        },
        "campaign_observation": {
            "disposition": "inconclusive-matrix",
            "expected_runs": 48,
            "started_runs": 3,
            "terminal_settled_runs": 2,
            "observed_unsettled_runs": 1,
            "not_started_runs": 45,
            "settled_model_cost_nanos": 200_233_500,
            "observed_unsettled_model_cost_nanos": 911_878_500,
            "observed_started_model_cost_nanos": 1_112_112_000,
            "cost_accounting_complete": True,
            "analysis_ready": False,
            "official_heldout_analysis": False,
            "memory_benefit_claim_authorized": False,
        },
        "settled_rows": (
            {
                "order": 1,
                "task_id": "loguru-post-2038-local-timezone-fallback",
                "condition": "structured",
                "run_id": "run_heldout_3cd568065c3447ea",
                "outcome_kind": "task_failure",
                "hidden_tests": "fail",
                "regression_tests": "pass",
                "scope_policy": "pass",
                "safety_policy": "pass",
                "usage": _usage(89_002, 15_605, 14_111, 10, 10, 10, 109_229, 136_974_000),
            },
            {
                "order": 2,
                "task_id": "loguru-post-2038-local-timezone-fallback",
                "condition": "no_memory",
                "run_id": "run_heldout_a0f3f1716b634cdc",
                "outcome_kind": "resolved",
                "hidden_tests": "pass",
                "regression_tests": "pass",
                "scope_policy": "pass",
                "safety_policy": "pass",
                "usage": _usage(50_278, 5_678, 5_173, 6, 6, 6, 45_861, 63_259_500),
            },
        ),
        "budget_terminal": {
            "order": 3,
            "task_id": "dagster-subset-partition-definition-selection",
            "condition": "no_memory",
            "run_id": RUN3_ID,
            "result_schema_version": "run-result-v2",
            "result_terminal_error": {"code": "AGENT_SUBMISSION_FAILED", "phase": "agent"},
            "qualification_schema_version": "trace-qualification-v2",
            "qualification_check_count": 27,
            "qualification_passed_check_count": 26,
            "failed_check_id": "terminal_result_integrity",
            "failed_binding_required": True,
            "failed_binding_valid": False,
            "blocked_event_id": "evt_53dea5c1ef8d4be191961be6bab495dd",
            "blocked_event_sequence": 419,
            "blocked_event_json_sha256": (
                "sha256:79f1a1a1576df35e5fd3c7394279ddd804108f17642eca5437a36ad1bce34e4b"
            ),
            "blocked_payload_hash": (
                "sha256:372209421ac9ed370cb2385b8e2bc89a1b159ef22c5c353c55ade95ca7e6a557"
            ),
            "blocked_reason_code": "exact_request_budget_exceeded",
            "blocked_error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
            "requested_input_tokens": 34_327,
            "remaining_input_tokens": 7_116,
            "max_cumulative_input_tokens": 1_000_000,
            "max_total_tokens": 1_100_000,
            "terminal_event_id": "evt_2fa059c3fea54482a32ef3f113e68b5c",
            "terminal_event_sequence": 421,
            "terminal_event_json_sha256": (
                "sha256:731df9bb8ce74d4b458d3ac467fa4713e314c845155cd316215dd04b836fd318"
            ),
            "terminal_error_type": "ModelGenerationBudgetError",
            "terminal_error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
            "terminal_error_details_hash": (
                "sha256:372209421ac9ed370cb2385b8e2bc89a1b159ef22c5c353c55ade95ca7e6a557"
            ),
            "usage": _usage(992_884, 37_159, 31_106, 49, 50, 91, 284_082, 911_878_500),
        },
        "historical_confound": {
            "trigger": "qualification-or-completion-contract-mismatch",
            "phase": "authentication",
            "historical_reason_code": "DURABLE_EVIDENCE_AUTHENTICATION_FAILED",
            "exception_type": "ContractError",
            "durable_evidence_content_hash": (
                "sha256:098ed0c294b112c33f5967de987bda0b24a8123eaffe62e79de55fe3c7634372"
            ),
            "confound_content_hash": (
                "sha256:0c45220ffbeafb585d5884b6e667f261d5404b341d1a5109189af60c90ea4659"
            ),
            "historical_reason_preserved_without_relabeling": True,
        },
        "post_runtime_attribution": {
            "diagnosis_code": "TRACE_QUALIFICATION_V2_TERMINAL_RESULT_SCHEMA_MISMATCH",
            "direct_cause": (
                "trace-qualification-v2-required-run-result-v1-rich-budget-terminal-error-from-sanitized-run-result-v2"
            ),
            "version_aware_fix": (
                "v1-rich-terminal-remains-exact-v2-binds-sanitized-result-to-exact-blocked-and-runfailed-events"
            ),
            "historical_typed_diagnosis_code_observed": False,
            "post_runtime_deterministic_attribution": True,
            "changes_historical_reason_code": False,
            "historical_row_reauthenticated": False,
            "historical_row_reclassified": False,
            "task_or_memory_effect_claimed": False,
        },
        "authority": {
            "r15_campaign_is_immutable_and_consumed": True,
            "evidence_index_is_append_only_attribution_only": True,
            "historical_runtime_files_mutated": False,
            "historical_row_reauthentication_authorized": False,
            "retry_replacement_or_resume_performed": False,
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


def _build_candidate(*, recorded_at: datetime) -> HeldoutACR15CampaignEvidence:
    body = _record(recorded_at=recorded_at)
    hash_body = {**body, "recorded_at": recorded_at.isoformat().replace("+00:00", "Z")}
    return HeldoutACR15CampaignEvidence(**body, content_hash=sha256_json(hash_body))


def _canonical_bytes(payload: HeldoutACR15CampaignEvidence) -> bytes:
    return (payload.model_dump_json(indent=2) + "\n").encode("utf-8")


def _root(repository: str | Path | None) -> Path:
    return Path(repository).resolve() if repository is not None else repository_root().resolve()


def _canonical_read(root: Path, binding: BoundFile) -> bytes:
    selected = root / binding.path
    try:
        resolved = selected.resolve(strict=True)
        raw = selected.read_bytes()
    except OSError as exc:
        raise HeldoutACR15CampaignEvidenceError(
            f"R15 evidence file is unavailable: {binding.path}"
        ) from exc
    if not (
        resolved == selected.absolute()
        and resolved.is_relative_to(root)
        and selected.is_file()
        and not selected.is_symlink()
        and len(raw) == binding.file_bytes
        and sha256_bytes(raw) == binding.file_sha256
    ):
        raise HeldoutACR15CampaignEvidenceError(f"R15 evidence file differs: {binding.path}")
    return raw


def _json(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACR15CampaignEvidenceError(f"R15 {label} JSON is invalid") from exc
    if not isinstance(parsed, dict):
        raise HeldoutACR15CampaignEvidenceError(f"R15 {label} JSON is not an object")
    return parsed


def _content_hash_matches(payload: dict[str, Any], expected: str | None) -> bool:
    return bool(
        expected is not None
        and payload.get("content_hash") == expected
        and sha256_json({key: value for key, value in payload.items() if key != "content_hash"})
        == expected
    )


def _verify_source_chain(root: Path, evidence: HeldoutACR15CampaignEvidence) -> None:
    for binding in evidence.source_chain:
        payload = _json(_canonical_read(root, binding), label="source-chain")
        if not _content_hash_matches(payload, binding.content_hash):
            raise HeldoutACR15CampaignEvidenceError("R15 historical source chain differs")


def _verify_runtime_files(root: Path, evidence: HeldoutACR15CampaignEvidence) -> None:
    files = evidence.runtime_files
    preflight = _json(_canonical_read(root, files.candidate_preflight), label="preflight")
    plan = _json(_canonical_read(root, files.execution_plan), label="plan")
    journal_raw = _canonical_read(root, files.journal)
    prepared = _json(_canonical_read(root, files.prepared_result), label="prepared-result")
    final = _json(_canonical_read(root, files.final_result), label="final-result")
    result = _json(_canonical_read(root, files.confounded_result), label="confounded-result")
    qualification = _json(
        _canonical_read(root, files.confounded_qualification), label="confounded-qualification"
    )
    usage = _json(_canonical_read(root, files.confounded_usage), label="confounded-usage")
    cost = _json(
        _canonical_read(root, files.confounded_cost_observation),
        label="confounded-cost-observation",
    )

    candidate = preflight.get("candidate") or {}
    source = candidate.get("source_qualification") or {}
    readiness_git = (candidate.get("readiness") or {}).get("git") or {}
    cost_control = candidate.get("campaign_cost_control") or {}
    if not (
        preflight.get("schema_version") == "heldout-ac-preflight-v1"
        and preflight.get("execution_hash") == EXECUTION_HASH
        and preflight.get("source_qualification_hash") == evidence.source_chain[-1].content_hash
        and preflight.get("ready") is False
        and preflight.get("execution_candidate_ready") is True
        and preflight.get("provider_calls_made") == 0
        and preflight.get("evaluator_calls_made") == 0
        and preflight.get("agent_runs_made") == 0
        and candidate.get("schema_version") == "heldout-ac-execution-candidate-v3"
        and candidate.get("execution_hash") == EXECUTION_HASH
        and candidate.get("suite_id") == SUITE_ID
        and candidate.get("suite_content_hash") == SUITE_CONTENT_HASH
        and candidate.get("runtime_tuple_hash") == RUNTIME_TUPLE_HASH
        and candidate.get("realized_schedule_hash")
        == "sha256:f75459b2cace0d3dd71920bf57a441b792209720ecc36763b706d7c2a8601739"
        and candidate.get("pricing_binding_hash") == PRICING_BINDING_HASH
        and cost_control.get("content_hash") == COST_CONTROL_HASH
        and cost_control.get("full_schedule_reserve_nanos") == 57_600_000_000
        and cost_control.get("hard_cap_nanos") == 60_000_000_000
        and source.get("source_qualification_hash") == evidence.source_chain[-1].content_hash
        and readiness_git.get("commit") == evidence.historical_git_commit
        and readiness_git.get("tree") == evidence.historical_git_tree
    ):
        raise HeldoutACR15CampaignEvidenceError("R15 candidate projection differs")

    approval = plan.get("approval") or {}
    runtime = plan.get("runtime_contract") or {}
    if not (
        plan.get("schema_version") == "experiment-execution-plan-v2"
        and plan.get("execution_hash") == EXECUTION_HASH
        and plan.get("ready") is True
        and runtime.get("runtime_tuple_hash") == RUNTIME_TUPLE_HASH
        and runtime.get("campaign_cost_control_hash") == COST_CONTROL_HASH
        and approval.get("invocation_approved_execution_hash") == EXECUTION_HASH
        and approval.get("full_schedule_reserve_nanos") == 57_600_000_000
        and approval.get("hard_cap_nanos") == 60_000_000_000
    ):
        raise HeldoutACR15CampaignEvidenceError("R15 approved plan projection differs")

    try:
        journal = [json.loads(line) for line in journal_raw.decode("utf-8").splitlines()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACR15CampaignEvidenceError("R15 journal is invalid") from exc
    terminal = journal[-1] if journal else {}
    if not (
        len(journal) == 54
        and terminal.get("sequence") == 54
        and terminal.get("event_type") == "CampaignCompleted"
        and terminal.get("event_hash")
        == "sha256:46a0cda4d5d107dcafb5d02ecf74c6f151b7582023522fc8e122a98822f8bba5"
    ):
        raise HeldoutACR15CampaignEvidenceError("R15 journal terminal differs")

    observation = evidence.campaign_observation
    for label, payload, binding in (
        ("prepared", prepared, files.prepared_result),
        ("final", final, files.final_result),
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
            and payload.get("cost_accounting_complete") is True
            and payload.get("analysis_ready") is False
            and payload.get("official_heldout_analysis") is False
            and payload.get("retry_replacement_or_resume_performed") is False
            and len(payload.get("settled_rows") or []) == 2
            and len(payload.get("not_started_rows") or []) == 45
        ):
            raise HeldoutACR15CampaignEvidenceError(f"R15 {label} result differs")

    for expected, settled in zip(evidence.settled_rows, final["settled_rows"], strict=True):
        row = (settled.get("authenticated_evidence") or {}).get("row") or {}
        row_result = row.get("result") or {}
        verdicts = row_result.get("verdicts") or {}
        row_usage = row_result.get("usage") or {}
        if not (
            row.get("order") == expected.order
            and row.get("task_id") == expected.task_id
            and row.get("condition") == expected.condition
            and row.get("run_id") == expected.run_id
            and row_result.get("outcome_kind") == expected.outcome_kind
            and verdicts.get("hidden_tests") == expected.hidden_tests
            and verdicts.get("regression_tests") == expected.regression_tests
            and verdicts.get("scope_policy") == expected.scope_policy
            and verdicts.get("safety_policy") == expected.safety_policy
            and row_usage.get("input_tokens") == expected.usage.input_tokens
            and row_usage.get("output_tokens") == expected.usage.output_tokens
            and row_usage.get("reasoning_output_tokens") == expected.usage.reasoning_output_tokens
            and row_usage.get("model_calls") == expected.usage.model_calls
            and row_usage.get("input_token_count_calls") == expected.usage.input_token_count_calls
            and row_usage.get("tool_calls") == expected.usage.tool_calls
            and row_usage.get("wall_clock_ms") == expected.usage.wall_clock_ms
            and Decimal(str(row_usage.get("model_cost_usd")))
            == Decimal(expected.usage.model_cost_nanos) / Decimal(1_000_000_000)
        ):
            raise HeldoutACR15CampaignEvidenceError("R15 settled row differs")

    budget_terminal = evidence.budget_terminal
    qualification_body = {
        key: value for key, value in qualification.items() if key != "qualification_hash"
    }
    checks = qualification.get("checks") or []
    failed = [check for check in checks if isinstance(check, dict) and check.get("passed") is False]
    failed_details = failed[0].get("details") if len(failed) == 1 else None
    result_usage = result.get("usage") or {}
    expected_usage = budget_terminal.usage
    if not (
        result.get("schema_version") == budget_terminal.result_schema_version
        and result.get("run_id") == RUN3_ID
        and result.get("agent_submission_status") == "failed"
        and result.get("evaluation_status") == "not_run"
        and result.get("outcome_kind") == "agent_failure"
        and result.get("terminal_error") == budget_terminal.result_terminal_error
        and sha256_json(result) == files.confounded_result.semantic_hash
        and qualification.get("schema_version") == budget_terminal.qualification_schema_version
        and qualification.get("qualified") is False
        and qualification.get("trace_integrity_passed") is False
        and qualification.get("leakage_scan_passed") is True
        and qualification.get("qualification_hash") == files.confounded_qualification.semantic_hash
        and sha256_json(qualification_body) == files.confounded_qualification.semantic_hash
        and len(checks) == budget_terminal.qualification_check_count
        and sum(check.get("passed") is True for check in checks if isinstance(check, dict))
        == budget_terminal.qualification_passed_check_count
        and len(failed) == 1
        and failed[0].get("check_id") == budget_terminal.failed_check_id
        and isinstance(failed_details, dict)
        and failed_details.get("model_generation_block_binding_required") is True
        and failed_details.get("model_generation_block_binding_valid") is False
        and result_usage.get("input_tokens") == expected_usage.input_tokens
        and result_usage.get("output_tokens") == expected_usage.output_tokens
        and result_usage.get("reasoning_output_tokens") == expected_usage.reasoning_output_tokens
        and result_usage.get("model_calls") == expected_usage.model_calls
        and result_usage.get("input_token_count_calls") == expected_usage.input_token_count_calls
        and result_usage.get("tool_calls") == expected_usage.tool_calls
        and result_usage.get("wall_clock_ms") == expected_usage.wall_clock_ms
        and Decimal(str(result_usage.get("model_cost_usd")))
        == Decimal(expected_usage.model_cost_nanos) / Decimal(1_000_000_000)
        and _content_hash_matches(usage, files.confounded_usage.content_hash)
        and usage.get("token_derived_cost_nanos") == expected_usage.model_cost_nanos
        and _content_hash_matches(cost, files.confounded_cost_observation.content_hash)
        and cost.get("token_derived_cost_nanos") == expected_usage.model_cost_nanos
    ):
        raise HeldoutACR15CampaignEvidenceError("R15 budget terminal evidence differs")

    confound = final.get("confound") or {}
    durable = confound.get("durable_evidence") or {}
    historical = evidence.historical_confound
    if not (
        confound.get("trigger") == historical.trigger
        and confound.get("phase") == historical.phase
        and confound.get("reason_code") == historical.historical_reason_code
        and confound.get("exception_type") == historical.exception_type
        and confound.get("secret_or_exception_message_persisted") is False
        and "message" not in confound
        and confound.get("content_hash") == historical.confound_content_hash
        and durable.get("content_hash") == historical.durable_evidence_content_hash
        and durable.get("result_file_sha256") == files.confounded_result.file_sha256
        and durable.get("qualification_file_sha256") == files.confounded_qualification.file_sha256
        and durable.get("usage_file_sha256") == files.confounded_usage.file_sha256
        and durable.get("cost_observation_file_sha256")
        == files.confounded_cost_observation.file_sha256
        and durable.get("token_derived_cost_nanos") == expected_usage.model_cost_nanos
    ):
        raise HeldoutACR15CampaignEvidenceError("R15 historical confound differs")


def _verify_state_events(root: Path, evidence: HeldoutACR15CampaignEvidence) -> None:
    database = root / ".patchloop/state.sqlite3"
    sidecars = tuple(Path(f"{database}{suffix}") for suffix in ("-wal", "-shm", "-journal"))
    if not database.is_file() or any(path.exists() for path in sidecars):
        raise HeldoutACR15CampaignEvidenceError("R15 state database is not main-only read-safe")
    before = (
        database.stat().st_size,
        database.stat().st_mtime_ns,
        sha256_bytes(database.read_bytes()),
    )
    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro&immutable=1", uri=True)
    try:
        rows = connection.execute(
            "SELECT sequence, event_json FROM events WHERE run_id = ? AND sequence IN (?, ?) "
            "ORDER BY sequence",
            (RUN3_ID, 419, 421),
        ).fetchall()
    finally:
        connection.close()
    after = (
        database.stat().st_size,
        database.stat().st_mtime_ns,
        sha256_bytes(database.read_bytes()),
    )
    if before != after or len(rows) != 2:
        raise HeldoutACR15CampaignEvidenceError("R15 state event read was not exact and read-only")
    blocked_raw = rows[0][1].encode("utf-8")
    terminal_raw = rows[1][1].encode("utf-8")
    blocked = _json(blocked_raw, label="blocked-event")
    terminal = _json(terminal_raw, label="terminal-event")
    projection = evidence.budget_terminal
    blocked_payload = blocked.get("payload") or {}
    terminal_payload = terminal.get("payload") or {}
    if not (
        rows[0][0] == projection.blocked_event_sequence
        and sha256_bytes(blocked_raw) == projection.blocked_event_json_sha256
        and blocked.get("event_id") == projection.blocked_event_id
        and blocked.get("type") == "ModelGenerationBlocked"
        and blocked.get("actor") == "budget-guard"
        and sha256_json(blocked_payload) == projection.blocked_payload_hash
        and blocked_payload.get("reason_code") == projection.blocked_reason_code
        and blocked_payload.get("error_code") == projection.blocked_error_code
        and blocked_payload.get("requested_input_tokens") == projection.requested_input_tokens
        and blocked_payload.get("remaining_input_tokens") == projection.remaining_input_tokens
        and blocked_payload.get("max_cumulative_input_tokens")
        == projection.max_cumulative_input_tokens
        and blocked_payload.get("max_total_tokens") == projection.max_total_tokens
        and rows[1][0] == projection.terminal_event_sequence
        and sha256_bytes(terminal_raw) == projection.terminal_event_json_sha256
        and terminal.get("event_id") == projection.terminal_event_id
        and terminal.get("type") == "RunFailed"
        and terminal.get("actor") == "runner"
        and terminal_payload.get("error_type") == projection.terminal_error_type
        and terminal_payload.get("error_code") == projection.terminal_error_code
        and sha256_json(terminal_payload.get("error_details"))
        == projection.terminal_error_details_hash
    ):
        raise HeldoutACR15CampaignEvidenceError("R15 typed budget terminal events differ")


def _load_validated(root: Path) -> tuple[HeldoutACR15CampaignEvidence, bytes]:
    selected = root / OUTPUT_PATH
    try:
        raw = selected.read_bytes()
        payload = HeldoutACR15CampaignEvidence.model_validate_json(raw)
    except (OSError, ValidationError) as exc:
        raise HeldoutACR15CampaignEvidenceError("R15 campaign evidence is invalid") from exc
    if raw != _canonical_bytes(payload) or payload != _build_candidate(
        recorded_at=payload.recorded_at
    ):
        raise HeldoutACR15CampaignEvidenceError("R15 campaign evidence has drifted")
    return payload, raw


def _summary(
    payload: HeldoutACR15CampaignEvidence,
    raw: bytes,
    *,
    runtime_revalidated: bool,
) -> dict[str, object]:
    observation = payload.campaign_observation
    return {
        "status": payload.status,
        "evidence_id": payload.evidence_id,
        "execution_hash": payload.execution_hash,
        "content_hash": payload.content_hash,
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "terminal_settled_runs": observation.terminal_settled_runs,
        "observed_unsettled_runs": observation.observed_unsettled_runs,
        "not_started_runs": observation.not_started_runs,
        "observed_started_model_cost_nanos": observation.observed_started_model_cost_nanos,
        "runtime_revalidated": runtime_revalidated,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "agent_runs_made": 0,
        "docker_calls_made": 0,
        "sdk_calls_made": 0,
        "added_model_cost_usd": 0.0,
        "next_gate": payload.next_gate,
    }


def validate_heldout_ac_r15_campaign_evidence(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    payload, raw = _load_validated(_root(repository))
    return _summary(payload, raw, runtime_revalidated=False)


def revalidate_heldout_ac_r15_runtime_evidence(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    root = _root(repository)
    payload, raw = _load_validated(root)
    _verify_source_chain(root, payload)
    _verify_runtime_files(root, payload)
    _verify_state_events(root, payload)
    return _summary(payload, raw, runtime_revalidated=True)


def run_heldout_ac_r15_campaign_evidence(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    root = _root(repository)
    selected = root / OUTPUT_PATH
    if selected.exists():
        return validate_heldout_ac_r15_campaign_evidence(repository=root)
    payload = _build_candidate(recorded_at=datetime.now(UTC))
    raw = _canonical_bytes(payload)
    _verify_source_chain(root, payload)
    _verify_runtime_files(root, payload)
    _verify_state_events(root, payload)
    selected.parent.mkdir(parents=True, exist_ok=True)
    try:
        with selected.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise HeldoutACR15CampaignEvidenceError("R15 campaign evidence already exists") from exc
    if selected.read_bytes() != raw:
        raise HeldoutACR15CampaignEvidenceError("R15 campaign evidence reread differs")
    return _summary(payload, raw, runtime_revalidated=True)


__all__ = [
    "EVIDENCE_ID",
    "EXECUTION_HASH",
    "NEXT_GATE",
    "OUTPUT_PATH",
    "SCHEMA_VERSION",
    "STATUS",
    "HeldoutACR15CampaignEvidence",
    "HeldoutACR15CampaignEvidenceError",
    "revalidate_heldout_ac_r15_runtime_evidence",
    "run_heldout_ac_r15_campaign_evidence",
    "validate_heldout_ac_r15_campaign_evidence",
]
