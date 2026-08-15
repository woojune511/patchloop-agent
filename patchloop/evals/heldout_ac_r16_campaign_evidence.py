"""Immutable, zero-call evidence index for the consumed R16 campaign."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_contracts import HeldoutACFrozenModel
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_json

SCHEMA_VERSION = "heldout-ac-complete-campaign-evidence-index-v1"
EVIDENCE_ID = "core-ac-fixed-bundle-heldout-r16-live-complete-20260815-r1"
STATUS = "LIVE_CAMPAIGN_COMPLETE_MATRIX_OFFICIAL_ANALYSIS_INDEXED"
OUTPUT_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-r16-campaign-complete-r1.json")
EXECUTION_HASH = "sha256:24044c1ed525458446f1c97d94f52331082d74051f5c6d680da995ea9aa48813"
EXECUTION_DIGEST = EXECUTION_HASH.removeprefix("sha256:")
SUITE_ID = "core-ac-fixed-bundle-heldout-20260814-v1"
SUITE_CONTENT_HASH = "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
RUNTIME_TUPLE_HASH = "sha256:ff8ddf0a4735162820b3fd91966fb977fa996c9c04d9d4ee649d2353a01e95a8"
COST_CONTROL_HASH = "sha256:c705d04b2bd6756fed96dd5d91caaa0480a9edf02d84c5a0509c3c4707590a4c"
PRICING_BINDING_HASH = "sha256:83bb15d171564f32d0ca6df24f733a957032e144bbd0dfed49071e1b205a27e9"
REALIZED_SCHEDULE_HASH = "sha256:f75459b2cace0d3dd71920bf57a441b792209720ecc36763b706d7c2a8601739"
SCHEDULE_HASH = "sha256:7eb4b583415e832e44da242de02a894152aa882255514532cfb5bd770b205b88"
SOURCE_QUALIFICATION_HASH = (
    "sha256:a15c6c0ade8bd9bb1f57cacd07ec6dbfcbb84bfc1b622b642bb4f332873b6742"
)
EVALUATOR_SOURCE_HASH = "sha256:bbc790eb53fbc7883a454d963ccc2e6195e4f73f160f162c814aec2efade92ad"
AUTHENTICATED_COMPLETION_HASH = (
    "sha256:954ccd1ead1e826fcd07c435303f1b8c859b58ee3c742b1580ec94c675d88a95"
)
OFFICIAL_ANALYSIS_ENVELOPE_HASH = (
    "sha256:7cd2e7657b2b7d878c5874f9a1e29f0aa5dea58fe8a135c9706ee903c7ccc260"
)
ANALYSIS_SEMANTIC_HASH = "sha256:635d27581c603edadf5c49f514049c446dedec37fdfe745e1faa3fa78a72c8e6"
OUTCOME_PROJECTION_SEMANTIC_HASH = (
    "sha256:4e64cbb35720229345d7ce8ec044c13d0f4bb471e4d60f66a8008e64866f325b"
)
CAMPAIGN_COMPLETED_EVENT_HASH = (
    "sha256:c7ddea5ffe5411433849668c7bc54fad57d8b2fb4a9836563c769d573d989e52"
)
NEXT_GATE = (
    "preserve-this-consumed-panel-and-require-a-new-preregistered-design-for-future-paid-work"
)


class HeldoutACR16CampaignEvidenceError(ContractError):
    pass


class BoundFile(HeldoutACFrozenModel):
    path: str
    file_bytes: int = Field(ge=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")


class RuntimeFiles(HeldoutACFrozenModel):
    candidate_preflight: BoundFile
    execution_plan: BoundFile
    journal: BoundFile
    prepared_result: BoundFile
    final_result: BoundFile


class Rational(HeldoutACFrozenModel):
    numerator: int
    denominator: int = Field(gt=0)


class OutcomeCounts(HeldoutACFrozenModel):
    resolved: Literal[15]
    task_failure: Literal[14]
    agent_failure: Literal[19]
    evaluator_completed: Literal[29]
    typed_pre_evaluator_agent_terminal: Literal[19]
    token_budget_exhaustion: Literal[18]
    submission_failure: Literal[1]


class CampaignObservation(HeldoutACFrozenModel):
    disposition: Literal["complete-matrix"]
    expected_runs: Literal[48]
    started_runs: Literal[48]
    terminal_settled_runs: Literal[48]
    observed_unsettled_runs: Literal[0]
    not_started_runs: Literal[0]
    confounded_runs: Literal[0]
    settled_model_cost_nanos: Literal[27244658250]
    observed_unsettled_model_cost_nanos: Literal[0]
    observed_started_model_cost_nanos: Literal[27244658250]
    cost_accounting_complete: Literal[True]
    analysis_ready: Literal[True]
    official_heldout_analysis: Literal[True]
    memory_benefit_claim_authorized: Literal[False]
    broad_generalization_claim_authorized: Literal[False]
    retry_replacement_or_resume_performed: Literal[False]
    outcomes: OutcomeCounts

    @model_validator(mode="after")
    def validate_accounting(self) -> CampaignObservation:
        if not (
            self.expected_runs == self.started_runs == self.terminal_settled_runs
            and self.observed_unsettled_runs == 0
            and self.not_started_runs == 0
            and self.confounded_runs == 0
            and self.observed_started_model_cost_nanos
            == self.settled_model_cost_nanos + self.observed_unsettled_model_cost_nanos
            and self.outcomes.resolved + self.outcomes.task_failure + self.outcomes.agent_failure
            == self.expected_runs
        ):
            raise ValueError("R16 campaign accounting differs")
        return self


class ConditionSummary(HeldoutACFrozenModel):
    condition: Literal["no_memory", "structured"]
    eligible_rows: Literal[24]
    successes: int = Field(ge=0, le=24)
    success_rate: Rational
    total_model_cost_usd: Rational
    cost_per_success_usd: Rational
    cost_per_success_status: Literal["defined"]


class StabilitySummary(HeldoutACFrozenModel):
    status: Literal["descriptive-stability-only"]
    method: Literal["deterministic-task-cluster-percentile-resampling"]
    samples: Literal[100000]
    lower: Rational
    upper: Rational
    confidence_interval_claim_authorized: Literal[False]


class SignFlipSummary(HeldoutACFrozenModel):
    status: Literal["sensitivity-reference-only"]
    observed_abs_integer_statistic: Literal[1]
    extreme_or_equal_sign_vectors: Literal[4096]
    sign_vectors_enumerated: Literal[4096]
    p_value: Rational
    design_based_randomization_inference_authorized: Literal[False]
    headline_use_authorized: Literal[False]


class DirectionalFlips(HeldoutACFrozenModel):
    pair_count: Literal[24]
    benefit_count: Literal[3]
    benefit_rate: Rational
    negative_transfer_count: Literal[4]
    negative_transfer_rate: Rational
    inference: Literal["counts-and-rates-only"]


class RoleStratum(HeldoutACFrozenModel):
    role: Literal["core-same-repo", "core-cross-repo"]
    task_clusters: Literal[6]
    eligible_rows: Literal[24]
    estimate: Rational
    status: Literal["secondary-descriptive"]


class VerdictDistribution(HeldoutACFrozenModel):
    verdict: Literal["hidden", "regression", "scope", "safety"]
    eligible_rows: Literal[48]
    pass_rows: int = Field(ge=0, le=48)
    fail_rows: int = Field(ge=0, le=48)
    not_run_typed_agent_terminal_rows: Literal[19]

    @model_validator(mode="after")
    def validate_distribution(self) -> VerdictDistribution:
        if self.pass_rows + self.fail_rows + self.not_run_typed_agent_terminal_rows != 48:
            raise ValueError("R16 verdict distribution differs")
        return self


class OfficialAnalysisSummary(HeldoutACFrozenModel):
    authenticated_completion_hash: Literal[AUTHENTICATED_COMPLETION_HASH]
    official_analysis_envelope_hash: Literal[OFFICIAL_ANALYSIS_ENVELOPE_HASH]
    analysis_semantic_hash: Literal[ANALYSIS_SEMANTIC_HASH]
    outcome_projection_semantic_hash: Literal[OUTCOME_PROJECTION_SEMANTIC_HASH]
    scheduled_rows: Literal[48]
    eligible_rows: Literal[48]
    task_clusters: Literal[12]
    complete_panel: Literal[True]
    primary_estimate: Rational
    conditions: tuple[ConditionSummary, ConditionSummary]
    stability_interval: StabilitySummary
    sign_flip_sensitivity: SignFlipSummary
    directional_flips: DirectionalFlips
    role_strata: tuple[RoleStratum, RoleStratum]
    verdict_distributions: tuple[
        VerdictDistribution,
        VerdictDistribution,
        VerdictDistribution,
        VerdictDistribution,
    ]
    causal_general_memory_benefit_claim_authorized: Literal[False]
    broad_generalization_claim_authorized: Literal[False]

    @model_validator(mode="after")
    def validate_analysis(self) -> OfficialAnalysisSummary:
        conditions = {item.condition: item for item in self.conditions}
        strata = {item.role: item for item in self.role_strata}
        verdicts = {item.verdict: item for item in self.verdict_distributions}
        if not (
            set(conditions) == {"no_memory", "structured"}
            and set(strata) == {"core-same-repo", "core-cross-repo"}
            and set(verdicts) == {"hidden", "regression", "scope", "safety"}
            and self.primary_estimate == Rational(numerator=-1, denominator=24)
            and conditions["no_memory"].successes == 8
            and conditions["no_memory"].success_rate == Rational(numerator=1, denominator=3)
            and conditions["no_memory"].total_model_cost_usd
            == Rational(numerator=12_380_361, denominator=1_000_000)
            and conditions["structured"].successes == 7
            and conditions["structured"].success_rate == Rational(numerator=7, denominator=24)
            and conditions["structured"].total_model_cost_usd
            == Rational(numerator=59_457_189, denominator=4_000_000)
            and self.stability_interval.lower == Rational(numerator=-1, denominator=4)
            and self.stability_interval.upper == Rational(numerator=1, denominator=6)
            and self.sign_flip_sensitivity.p_value == Rational(numerator=1, denominator=1)
            and self.directional_flips.benefit_rate == Rational(numerator=1, denominator=8)
            and self.directional_flips.negative_transfer_rate
            == Rational(numerator=1, denominator=6)
            and strata["core-same-repo"].estimate == Rational(numerator=0, denominator=1)
            and strata["core-cross-repo"].estimate == Rational(numerator=-1, denominator=12)
            and (verdicts["hidden"].pass_rows, verdicts["hidden"].fail_rows) == (15, 14)
            and all(
                (verdicts[name].pass_rows, verdicts[name].fail_rows) == (29, 0)
                for name in ("regression", "scope", "safety")
            )
        ):
            raise ValueError("R16 official analysis summary differs")
        return self


class EvidenceAuthority(HeldoutACFrozenModel):
    r16_campaign_is_immutable_and_consumed: Literal[True]
    evidence_index_is_append_only_summary_only: Literal[True]
    historical_runtime_files_mutated: Literal[False]
    retry_replacement_or_resume_performed: Literal[False]
    official_frozen_panel_analysis_recorded: Literal[True]
    causal_or_general_memory_benefit_claim_authorized: Literal[False]
    future_candidate_or_paid_execution_authorized: Literal[False]
    runtime_artifacts_created: Literal[0]
    credential_values_observed: Literal[0]
    provider_calls_made: Literal[0]
    evaluator_calls_made: Literal[0]
    agent_runs_made: Literal[0]
    docker_calls_made: Literal[0]
    sdk_calls_made: Literal[0]
    added_model_cost_usd: Literal[0.0]


class HeldoutACR16CampaignEvidence(HeldoutACFrozenModel):
    schema_version: Literal[SCHEMA_VERSION]
    evidence_id: Literal[EVIDENCE_ID]
    status: Literal[STATUS]
    recorded_at: datetime
    historical_git_commit: Literal["d82291d9332894a4e0b0fc0618e3464bfc9a77e6"]
    historical_git_tree: Literal["827eb2a0640be0ccb816affde8ff7fa2b148e0b4"]
    suite_id: Literal[SUITE_ID]
    suite_content_hash: Literal[SUITE_CONTENT_HASH]
    execution_hash: Literal[EXECUTION_HASH]
    runtime_tuple_hash: Literal[RUNTIME_TUPLE_HASH]
    campaign_cost_control_hash: Literal[COST_CONTROL_HASH]
    pricing_binding_hash: Literal[PRICING_BINDING_HASH]
    realized_schedule_hash: Literal[REALIZED_SCHEDULE_HASH]
    schedule_hash: Literal[SCHEDULE_HASH]
    full_schedule_reserve_nanos: Literal[57600000000]
    hard_cap_nanos: Literal[60000000000]
    approval_consumed: Literal[True]
    source_chain: tuple[BoundFile, ...]
    runtime_files: RuntimeFiles
    campaign_observation: CampaignObservation
    official_analysis: OfficialAnalysisSummary
    authority: EvidenceAuthority
    next_gate: Literal[NEXT_GATE]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_index(self) -> HeldoutACR16CampaignEvidence:
        if not (
            len(self.source_chain) == 5
            and self.campaign_observation.settled_model_cost_nanos
            < self.full_schedule_reserve_nanos
            < self.hard_cap_nanos
            and self.content_hash
            == sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("R16 campaign evidence cross-binding differs")
        return self


def _file(
    path: str,
    size: int,
    digest: str,
    *,
    content_hash: str | None = None,
) -> dict[str, Any]:
    return {
        "path": path,
        "file_bytes": size,
        "file_sha256": digest,
        "content_hash": content_hash,
    }


def _record(*, recorded_at: datetime) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": EVIDENCE_ID,
        "status": STATUS,
        "recorded_at": recorded_at,
        "historical_git_commit": "d82291d9332894a4e0b0fc0618e3464bfc9a77e6",
        "historical_git_tree": "827eb2a0640be0ccb816affde8ff7fa2b148e0b4",
        "suite_id": SUITE_ID,
        "suite_content_hash": SUITE_CONTENT_HASH,
        "execution_hash": EXECUTION_HASH,
        "runtime_tuple_hash": RUNTIME_TUPLE_HASH,
        "campaign_cost_control_hash": COST_CONTROL_HASH,
        "pricing_binding_hash": PRICING_BINDING_HASH,
        "realized_schedule_hash": REALIZED_SCHEDULE_HASH,
        "schedule_hash": SCHEDULE_HASH,
        "full_schedule_reserve_nanos": 57_600_000_000,
        "hard_cap_nanos": 60_000_000_000,
        "approval_consumed": True,
        "source_chain": (
            _file(
                "reports/heldout-ac/artifacts/heldout-ac-contract-source-qualification-r11.json",
                22_246,
                "sha256:8373844f7d548ecfa98d32ea712d7626cd4e1f6ced021af9c1253f3af08be42f",
                content_hash="sha256:140c747effd5621cc33ba2d2a0187774332fa31b50b978f4791039bb05f06755",
            ),
            _file(
                "reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r11.json",
                6_353,
                "sha256:9176a0671133985e3b01cfe540ab55a6a014e1db4a1a117602a7d774518ba7f8",
                content_hash="sha256:5d2b92fe34be90aabda0f2fc3fd90ff6136c5e794e362299b33f35f707aee762",
            ),
            _file(
                "reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r7.json",
                53_250,
                "sha256:7b9bb78b89e18e067476cdf172214fb4588d3f96b68427f6f8eb49761d801425",
                content_hash="sha256:2a32a034dc89a43e0d20a9dc82959d0574c82c0915a6f105f31291d7af962be4",
            ),
            _file(
                "reports/heldout-ac/artifacts/heldout-ac-execution-source-qualification-r8.json",
                20_256,
                "sha256:c8e7cc989d9730c0b9671b973dd8c79d58a39b425d3975bfc729832e9a49dfeb",
                content_hash="sha256:23d0c31bcc00a8b66dd7ab6518dffa3afacb6cbbad284a5ab4d995349098fd27",
            ),
            _file(
                "reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r16.json",
                25_319,
                "sha256:033fd414cfc0b2499171e91a8b0e9e82e823f452520dfe42f54c1c9e8469e1f5",
                content_hash=SOURCE_QUALIFICATION_HASH,
            ),
        ),
        "runtime_files": {
            "candidate_preflight": _file(
                ".patchloop/heldout-ac-preflight-r16-20260815T174458448.json",
                66_841,
                "sha256:0e9b927cdd64413e926f5d4ca478895d9a0e4097ed785042ee5602a680552c4c",
            ),
            "execution_plan": _file(
                f".patchloop/experiments/plans/{EXECUTION_DIGEST}.json",
                83_599,
                "sha256:e8e9ae072eaf7c68798572c1ae124cff90bcc67a33fc4a872c19b00d7478bf94",
            ),
            "journal": _file(
                f".patchloop/experiments/journals/{EXECUTION_DIGEST}.jsonl",
                122_930,
                "sha256:40668bfa7b1b2142c952f2a83d12fd50aa0dbadf4d984e7c88b23c5378d33669",
            ),
            "prepared_result": _file(
                f".patchloop/experiments/heldout-ac/{EXECUTION_DIGEST}.prepared.json",
                1_202_867,
                "sha256:c459886b3b65215623e4a9320f6ffe5a5f8216dda66e35d91f4bf84fdc43db2f",
                content_hash="sha256:61d791264549833b5e0ec07bdd1cf68f3289e9ca374518c70e29a1d350c6dff6",
            ),
            "final_result": _file(
                f".patchloop/experiments/heldout-ac/{EXECUTION_DIGEST}.json",
                1_203_484,
                "sha256:6a6203c049e838675925a519a8d2bd7933823779b7c5cbee850d6e18a1bbd91f",
                content_hash="sha256:2e7466eba5c5cbd9e8fcbc5fae655972b78c9854ff83e9c906881337f7f985e4",
            ),
        },
        "campaign_observation": {
            "disposition": "complete-matrix",
            "expected_runs": 48,
            "started_runs": 48,
            "terminal_settled_runs": 48,
            "observed_unsettled_runs": 0,
            "not_started_runs": 0,
            "confounded_runs": 0,
            "settled_model_cost_nanos": 27_244_658_250,
            "observed_unsettled_model_cost_nanos": 0,
            "observed_started_model_cost_nanos": 27_244_658_250,
            "cost_accounting_complete": True,
            "analysis_ready": True,
            "official_heldout_analysis": True,
            "memory_benefit_claim_authorized": False,
            "broad_generalization_claim_authorized": False,
            "retry_replacement_or_resume_performed": False,
            "outcomes": {
                "resolved": 15,
                "task_failure": 14,
                "agent_failure": 19,
                "evaluator_completed": 29,
                "typed_pre_evaluator_agent_terminal": 19,
                "token_budget_exhaustion": 18,
                "submission_failure": 1,
            },
        },
        "official_analysis": {
            "authenticated_completion_hash": AUTHENTICATED_COMPLETION_HASH,
            "official_analysis_envelope_hash": OFFICIAL_ANALYSIS_ENVELOPE_HASH,
            "analysis_semantic_hash": ANALYSIS_SEMANTIC_HASH,
            "outcome_projection_semantic_hash": OUTCOME_PROJECTION_SEMANTIC_HASH,
            "scheduled_rows": 48,
            "eligible_rows": 48,
            "task_clusters": 12,
            "complete_panel": True,
            "primary_estimate": {"numerator": -1, "denominator": 24},
            "conditions": (
                {
                    "condition": "no_memory",
                    "eligible_rows": 24,
                    "successes": 8,
                    "success_rate": {"numerator": 1, "denominator": 3},
                    "total_model_cost_usd": {
                        "numerator": 12_380_361,
                        "denominator": 1_000_000,
                    },
                    "cost_per_success_usd": {
                        "numerator": 12_380_361,
                        "denominator": 8_000_000,
                    },
                    "cost_per_success_status": "defined",
                },
                {
                    "condition": "structured",
                    "eligible_rows": 24,
                    "successes": 7,
                    "success_rate": {"numerator": 7, "denominator": 24},
                    "total_model_cost_usd": {
                        "numerator": 59_457_189,
                        "denominator": 4_000_000,
                    },
                    "cost_per_success_usd": {
                        "numerator": 59_457_189,
                        "denominator": 28_000_000,
                    },
                    "cost_per_success_status": "defined",
                },
            ),
            "stability_interval": {
                "status": "descriptive-stability-only",
                "method": "deterministic-task-cluster-percentile-resampling",
                "samples": 100_000,
                "lower": {"numerator": -1, "denominator": 4},
                "upper": {"numerator": 1, "denominator": 6},
                "confidence_interval_claim_authorized": False,
            },
            "sign_flip_sensitivity": {
                "status": "sensitivity-reference-only",
                "observed_abs_integer_statistic": 1,
                "extreme_or_equal_sign_vectors": 4_096,
                "sign_vectors_enumerated": 4_096,
                "p_value": {"numerator": 1, "denominator": 1},
                "design_based_randomization_inference_authorized": False,
                "headline_use_authorized": False,
            },
            "directional_flips": {
                "pair_count": 24,
                "benefit_count": 3,
                "benefit_rate": {"numerator": 1, "denominator": 8},
                "negative_transfer_count": 4,
                "negative_transfer_rate": {"numerator": 1, "denominator": 6},
                "inference": "counts-and-rates-only",
            },
            "role_strata": (
                {
                    "role": "core-same-repo",
                    "task_clusters": 6,
                    "eligible_rows": 24,
                    "estimate": {"numerator": 0, "denominator": 1},
                    "status": "secondary-descriptive",
                },
                {
                    "role": "core-cross-repo",
                    "task_clusters": 6,
                    "eligible_rows": 24,
                    "estimate": {"numerator": -1, "denominator": 12},
                    "status": "secondary-descriptive",
                },
            ),
            "verdict_distributions": (
                {
                    "verdict": "hidden",
                    "eligible_rows": 48,
                    "pass_rows": 15,
                    "fail_rows": 14,
                    "not_run_typed_agent_terminal_rows": 19,
                },
                {
                    "verdict": "regression",
                    "eligible_rows": 48,
                    "pass_rows": 29,
                    "fail_rows": 0,
                    "not_run_typed_agent_terminal_rows": 19,
                },
                {
                    "verdict": "scope",
                    "eligible_rows": 48,
                    "pass_rows": 29,
                    "fail_rows": 0,
                    "not_run_typed_agent_terminal_rows": 19,
                },
                {
                    "verdict": "safety",
                    "eligible_rows": 48,
                    "pass_rows": 29,
                    "fail_rows": 0,
                    "not_run_typed_agent_terminal_rows": 19,
                },
            ),
            "causal_general_memory_benefit_claim_authorized": False,
            "broad_generalization_claim_authorized": False,
        },
        "authority": {
            "r16_campaign_is_immutable_and_consumed": True,
            "evidence_index_is_append_only_summary_only": True,
            "historical_runtime_files_mutated": False,
            "retry_replacement_or_resume_performed": False,
            "official_frozen_panel_analysis_recorded": True,
            "causal_or_general_memory_benefit_claim_authorized": False,
            "future_candidate_or_paid_execution_authorized": False,
            "runtime_artifacts_created": 0,
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


def _build_candidate(*, recorded_at: datetime) -> HeldoutACR16CampaignEvidence:
    body = _record(recorded_at=recorded_at)
    hash_body = {**body, "recorded_at": recorded_at.isoformat().replace("+00:00", "Z")}
    return HeldoutACR16CampaignEvidence(**body, content_hash=sha256_json(hash_body))


def _canonical_bytes(payload: HeldoutACR16CampaignEvidence) -> bytes:
    return (payload.model_dump_json(indent=2) + "\n").encode("utf-8")


def _root(repository: str | Path | None) -> Path:
    return Path(repository).resolve() if repository is not None else repository_root().resolve()


def _canonical_read(root: Path, binding: BoundFile) -> bytes:
    selected = root / binding.path
    try:
        resolved = selected.resolve(strict=True)
        raw = selected.read_bytes()
    except OSError as exc:
        raise HeldoutACR16CampaignEvidenceError(
            f"R16 evidence file is unavailable: {binding.path}"
        ) from exc
    if not (
        resolved == selected.absolute()
        and resolved.is_relative_to(root)
        and selected.is_file()
        and not selected.is_symlink()
        and len(raw) == binding.file_bytes
        and sha256_bytes(raw) == binding.file_sha256
    ):
        raise HeldoutACR16CampaignEvidenceError(f"R16 evidence file differs: {binding.path}")
    return raw


def _json(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACR16CampaignEvidenceError(f"R16 {label} JSON is invalid") from exc
    if not isinstance(parsed, dict):
        raise HeldoutACR16CampaignEvidenceError(f"R16 {label} JSON is not an object")
    return parsed


def _content_hash_matches(payload: dict[str, Any], expected: str | None) -> bool:
    return bool(
        expected is not None
        and payload.get("content_hash") == expected
        and sha256_json({key: value for key, value in payload.items() if key != "content_hash"})
        == expected
    )


def _verify_source_chain(root: Path, evidence: HeldoutACR16CampaignEvidence) -> None:
    for binding in evidence.source_chain:
        payload = _json(_canonical_read(root, binding), label="source-chain")
        if not _content_hash_matches(payload, binding.content_hash):
            raise HeldoutACR16CampaignEvidenceError("R16 historical source chain differs")


def _verify_preflight_and_plan(
    preflight: dict[str, Any],
    plan: dict[str, Any],
    evidence: HeldoutACR16CampaignEvidence,
) -> None:
    candidate = preflight.get("candidate") or {}
    source = candidate.get("source_qualification") or {}
    readiness_git = (candidate.get("readiness") or {}).get("git") or {}
    cost_control = candidate.get("campaign_cost_control") or {}
    if not (
        preflight.get("schema_version") == "heldout-ac-preflight-v1"
        and preflight.get("execution_hash") == EXECUTION_HASH
        and preflight.get("source_qualification_hash") == SOURCE_QUALIFICATION_HASH
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
        and candidate.get("realized_schedule_hash") == REALIZED_SCHEDULE_HASH
        and candidate.get("schedule_hash") == SCHEDULE_HASH
        and candidate.get("pricing_binding_hash") == PRICING_BINDING_HASH
        and cost_control.get("content_hash") == COST_CONTROL_HASH
        and cost_control.get("full_schedule_reserve_nanos") == 57_600_000_000
        and cost_control.get("hard_cap_nanos") == 60_000_000_000
        and source.get("source_qualification_hash") == SOURCE_QUALIFICATION_HASH
        and source.get("evaluator_source_hash") == EVALUATOR_SOURCE_HASH
        and readiness_git.get("commit") == evidence.historical_git_commit
        and readiness_git.get("tree") == evidence.historical_git_tree
        and len(candidate.get("schedule") or []) == 48
    ):
        raise HeldoutACR16CampaignEvidenceError("R16 candidate projection differs")

    approval = plan.get("approval") or {}
    runtime = plan.get("runtime_contract") or {}
    if not (
        plan.get("schema_version") == "experiment-execution-plan-v2"
        and plan.get("execution_hash") == EXECUTION_HASH
        and plan.get("ready") is True
        and runtime.get("runtime_tuple_hash") == RUNTIME_TUPLE_HASH
        and runtime.get("campaign_cost_control_hash") == COST_CONTROL_HASH
        and runtime.get("realized_schedule_hash") == REALIZED_SCHEDULE_HASH
        and runtime.get("schedule_hash") == SCHEDULE_HASH
        and runtime.get("source_qualification_hash") == SOURCE_QUALIFICATION_HASH
        and runtime.get("evaluator_source_hash") == EVALUATOR_SOURCE_HASH
        and approval.get("invocation_approved_execution_hash") == EXECUTION_HASH
        and approval.get("full_schedule_reserve_nanos") == 57_600_000_000
        and approval.get("hard_cap_nanos") == 60_000_000_000
        and approval.get("scheduled_run_count") == 48
    ):
        raise HeldoutACR16CampaignEvidenceError("R16 approved plan projection differs")


def _verify_journal(raw: bytes) -> None:
    try:
        journal = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACR16CampaignEvidenceError("R16 journal is invalid") from exc
    counts = Counter(event.get("event_type") for event in journal)
    if not (
        len(journal) == 99
        and [event.get("sequence") for event in journal] == list(range(1, 100))
        and all(
            event.get("schema_version") == "heldout-ac-campaign-journal-event-v2"
            and event.get("event_hash")
            == sha256_json({key: value for key, value in event.items() if key != "event_hash"})
            and event.get("previous_event_hash")
            == (None if index == 0 else journal[index - 1].get("event_hash"))
            for index, event in enumerate(journal)
        )
        and counts
        == Counter(
            {
                "CampaignStarted": 1,
                "FullScheduleCostReserved": 1,
                "RunStarted": 48,
                "RunTerminalCostSettled": 48,
                "CampaignCompleted": 1,
            }
        )
        and journal[-1].get("event_hash") == CAMPAIGN_COMPLETED_EVENT_HASH
    ):
        raise HeldoutACR16CampaignEvidenceError("R16 journal chain differs")


def _verify_analysis(payload: dict[str, Any], evidence: HeldoutACR16CampaignEvidence) -> None:
    analysis = payload.get("analysis") or {}
    outcome_projection = payload.get("outcome_projection") or {}
    completion = payload.get("authenticated_completion") or {}
    envelope = payload.get("official_analysis_envelope") or {}
    expected = evidence.official_analysis
    if not (
        sha256_json(analysis) == expected.analysis_semantic_hash
        and sha256_json(outcome_projection) == expected.outcome_projection_semantic_hash
        and _content_hash_matches(completion, expected.authenticated_completion_hash)
        and _content_hash_matches(envelope, expected.official_analysis_envelope_hash)
        and envelope.get("official") is True
        and envelope.get("persisted_evidence_authenticated") is True
        and envelope.get("analysis_ready") is True
        and envelope.get("execution_hash") == EXECUTION_HASH
        and envelope.get("completion_projection_hash") == AUTHENTICATED_COMPLETION_HASH
        and envelope.get("analysis") == analysis
        and envelope.get("causal_general_memory_benefit_claim_authorized") is False
        and envelope.get("broad_generalization_claim_authorized") is False
    ):
        raise HeldoutACR16CampaignEvidenceError("R16 official analysis envelope differs")


def _verify_result(
    payload: dict[str, Any],
    binding: BoundFile,
    evidence: HeldoutACR16CampaignEvidence,
    *,
    schema_version: str,
) -> None:
    observation = evidence.campaign_observation
    if not (
        _content_hash_matches(payload, binding.content_hash)
        and payload.get("schema_version") == schema_version
        and payload.get("evidence_status") == "authenticated-persisted-campaign"
        and payload.get("disposition") == observation.disposition
        and payload.get("suite_id") == SUITE_ID
        and payload.get("suite_content_hash") == SUITE_CONTENT_HASH
        and payload.get("execution_hash") == EXECUTION_HASH
        and payload.get("source_qualification_hash") == SOURCE_QUALIFICATION_HASH
        and payload.get("evaluator_source_hash") == EVALUATOR_SOURCE_HASH
        and payload.get("expected_runs") == 48
        and payload.get("terminal_settled_runs") == 48
        and payload.get("unsettled_dispatched_runs") == 0
        and payload.get("not_started_runs") == 0
        and payload.get("settled_model_cost_nanos") == 27_244_658_250
        and payload.get("observed_unsettled_model_cost_nanos") == 0
        and payload.get("observed_started_model_cost_nanos") == 27_244_658_250
        and payload.get("cost_accounting_complete") is True
        and payload.get("analysis_ready") is True
        and payload.get("official_heldout_analysis") is True
        and payload.get("memory_benefit_claim_authorized") is False
        and payload.get("broad_generalization_claim_authorized") is False
        and payload.get("retry_replacement_or_resume_performed") is False
        and payload.get("confound") is None
        and payload.get("not_started_rows") == []
    ):
        raise HeldoutACR16CampaignEvidenceError("R16 campaign result projection differs")

    settled_rows = payload.get("settled_rows") or []
    orders: list[int] = []
    outcomes: Counter[str] = Counter()
    terminals: Counter[str] = Counter()
    condition_successes: Counter[str] = Counter()
    condition_rows: Counter[str] = Counter()
    total_cost = 0
    for settled in settled_rows:
        wrapper = settled.get("authenticated_evidence") or {}
        row = wrapper.get("row") or {}
        result = row.get("result") or {}
        usage = row.get("usage_evidence") or {}
        condition = row.get("condition")
        if not (
            _content_hash_matches(settled, settled.get("content_hash"))
            and _content_hash_matches(wrapper, wrapper.get("content_hash"))
            and _content_hash_matches(row, row.get("content_hash"))
            and _content_hash_matches(usage, usage.get("content_hash"))
            and settled.get("schema_version") == "heldout-ac-settled-campaign-row-v2"
            and wrapper.get("schema_version") == "heldout-ac-authenticated-persisted-evidence-v5"
            and row.get("schema_version") == "heldout-ac-authenticated-persisted-row-v2"
            and wrapper.get("persisted_evidence_authenticated") is True
            and wrapper.get("official") is False
            and wrapper.get("analysis_eligible") is False
            and wrapper.get("runtime_tuple_hash") == RUNTIME_TUPLE_HASH
            and wrapper.get("campaign_cost_control_hash") == COST_CONTROL_HASH
            and row.get("execution_hash") == EXECUTION_HASH
            and row.get("runtime_tuple_hash") == RUNTIME_TUPLE_HASH
            and row.get("campaign_cost_control_hash") == COST_CONTROL_HASH
            and usage.get("pricing_binding_hash") == PRICING_BINDING_HASH
            and type(usage.get("token_derived_cost_nanos")) is int
        ):
            raise HeldoutACR16CampaignEvidenceError("R16 settled row binding differs")
        orders.append(row["order"])
        outcomes[result.get("outcome_kind")] += 1
        terminals[wrapper.get("terminal_type") or "evaluator_completed"] += 1
        condition_rows[condition] += 1
        condition_successes[condition] += result.get("scope_compliant_success") is True
        total_cost += usage["token_derived_cost_nanos"]

    expected_outcomes = evidence.campaign_observation.outcomes
    if not (
        len(settled_rows) == 48
        and orders == list(range(1, 49))
        and outcomes
        == Counter(
            resolved=expected_outcomes.resolved,
            task_failure=expected_outcomes.task_failure,
            agent_failure=expected_outcomes.agent_failure,
        )
        and terminals
        == Counter(
            evaluator_completed=expected_outcomes.evaluator_completed,
            **{
                "token-budget-exhaustion": expected_outcomes.token_budget_exhaustion,
                "submission-failure": expected_outcomes.submission_failure,
            },
        )
        and condition_rows == Counter(no_memory=24, structured=24)
        and condition_successes == Counter(no_memory=8, structured=7)
        and total_cost == observation.settled_model_cost_nanos
    ):
        raise HeldoutACR16CampaignEvidenceError("R16 settled matrix differs")
    _verify_analysis(payload, evidence)


def _verify_runtime_files(root: Path, evidence: HeldoutACR16CampaignEvidence) -> None:
    files = evidence.runtime_files
    preflight = _json(_canonical_read(root, files.candidate_preflight), label="preflight")
    plan = _json(_canonical_read(root, files.execution_plan), label="plan")
    journal = _canonical_read(root, files.journal)
    prepared = _json(_canonical_read(root, files.prepared_result), label="prepared-result")
    final = _json(_canonical_read(root, files.final_result), label="final-result")
    _verify_preflight_and_plan(preflight, plan, evidence)
    _verify_journal(journal)
    _verify_result(
        prepared,
        files.prepared_result,
        evidence,
        schema_version="heldout-ac-campaign-prepared-result-v2",
    )
    _verify_result(
        final,
        files.final_result,
        evidence,
        schema_version="heldout-ac-authoritative-campaign-result-v2",
    )
    if not (
        final.get("execution_plan_file_sha256") == files.execution_plan.file_sha256
        and final.get("journal_file_sha256") == files.journal.file_sha256
        and final.get("prepared_result_file_sha256") == files.prepared_result.file_sha256
        and final.get("prepared_result_content_hash") == files.prepared_result.content_hash
        and final.get("campaign_completed_event_hash") == CAMPAIGN_COMPLETED_EVENT_HASH
    ):
        raise HeldoutACR16CampaignEvidenceError("R16 final artifact bindings differ")


def _load_validated(root: Path) -> tuple[HeldoutACR16CampaignEvidence, bytes]:
    selected = root / OUTPUT_PATH
    try:
        raw = selected.read_bytes()
        payload = HeldoutACR16CampaignEvidence.model_validate_json(raw)
    except (OSError, ValidationError) as exc:
        raise HeldoutACR16CampaignEvidenceError("R16 campaign evidence is invalid") from exc
    if raw != _canonical_bytes(payload) or payload != _build_candidate(
        recorded_at=payload.recorded_at
    ):
        raise HeldoutACR16CampaignEvidenceError("R16 campaign evidence has drifted")
    return payload, raw


def _summary(
    payload: HeldoutACR16CampaignEvidence,
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
        "settled_model_cost_nanos": observation.settled_model_cost_nanos,
        "analysis_ready": observation.analysis_ready,
        "official_heldout_analysis": observation.official_heldout_analysis,
        "primary_estimate": payload.official_analysis.primary_estimate.model_dump(mode="json"),
        "runtime_revalidated": runtime_revalidated,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "agent_runs_made": 0,
        "docker_calls_made": 0,
        "sdk_calls_made": 0,
        "added_model_cost_usd": 0.0,
        "next_gate": payload.next_gate,
    }


def validate_heldout_ac_r16_campaign_evidence(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    payload, raw = _load_validated(_root(repository))
    return _summary(payload, raw, runtime_revalidated=False)


def revalidate_heldout_ac_r16_runtime_evidence(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    root = _root(repository)
    payload, raw = _load_validated(root)
    _verify_source_chain(root, payload)
    _verify_runtime_files(root, payload)
    return _summary(payload, raw, runtime_revalidated=True)


def run_heldout_ac_r16_campaign_evidence(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    root = _root(repository)
    selected = root / OUTPUT_PATH
    if selected.exists():
        return validate_heldout_ac_r16_campaign_evidence(repository=root)
    payload = _build_candidate(recorded_at=datetime.now(UTC))
    raw = _canonical_bytes(payload)
    _verify_source_chain(root, payload)
    _verify_runtime_files(root, payload)
    selected.parent.mkdir(parents=True, exist_ok=True)
    try:
        with selected.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise HeldoutACR16CampaignEvidenceError("R16 campaign evidence already exists") from exc
    if selected.read_bytes() != raw:
        raise HeldoutACR16CampaignEvidenceError("R16 campaign evidence reread differs")
    return _summary(payload, raw, runtime_revalidated=True)


__all__ = [
    "EVIDENCE_ID",
    "EXECUTION_HASH",
    "NEXT_GATE",
    "OUTPUT_PATH",
    "SCHEMA_VERSION",
    "STATUS",
    "HeldoutACR16CampaignEvidence",
    "HeldoutACR16CampaignEvidenceError",
    "revalidate_heldout_ac_r16_runtime_evidence",
    "run_heldout_ac_r16_campaign_evidence",
    "validate_heldout_ac_r16_campaign_evidence",
]
