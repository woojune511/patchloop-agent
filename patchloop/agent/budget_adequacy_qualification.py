"""Public no-call qualification for the budget-adequacy measurement contract.

Only checked-in R8 public-development projections and deterministic synthetic
boundary rows are consumed.  No task package, runtime database, provider,
runner, tool, evaluator, or R16 artifact is opened or called.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.budget_adequacy import (
    BudgetAdequacyReport,
    BudgetAdequacyRowObservation,
    BudgetAdequacyThresholdContract,
    EvidenceBinding,
    build_budget_adequacy_row,
    build_budget_envelope,
    project_budget_adequacy,
    r8_public_budget_adequacy_contract,
)
from patchloop.agent.finalization import (
    FinalizationReserveContract,
    r8_public_development_finalization_reserve,
)
from patchloop.agent.saturation_recovery_qualification import (
    SaturationRecoveryPublicQualification,
)
from patchloop.agent.saturation_recovery_qualification import (
    qualification_bytes as saturation_qualification_bytes,
)
from patchloop.agent.saturation_recovery_shadow_qualification import (
    SaturationRecoveryShadowPublicQualification,
)
from patchloop.agent.saturation_recovery_shadow_qualification import (
    qualification_bytes as admission_shadow_qualification_bytes,
)
from patchloop.errors import RecoveryError
from patchloop.util import ensure_within, sha256_bytes, sha256_json

QUALIFICATION_SCHEMA = "lean-harness-budget-adequacy-public-qualification-v1"
QUALIFICATION_ID = "lean-harness-budget-adequacy-public-20260816-v1"
QUALIFICATION_PATH = (
    "experiments/lean-harness-budget-adequacy-public-qualification-20260816-v1.json"
)

BOUNDARY_SCENARIOS = (
    "input-token-terminal",
    "output-token-terminal",
    "total-token-terminal",
    "zero-success-cost-denominator",
)

SOURCE_PATHS = (
    "patchloop/agent/budget_adequacy.py",
    "patchloop/agent/budget_adequacy_qualification.py",
    "patchloop/agent/finalization.py",
    "patchloop/agent/saturation_recovery_qualification.py",
    "patchloop/agent/saturation_recovery_shadow_qualification.py",
    "patchloop/errors.py",
    "patchloop/util.py",
    "scripts/build_lean_harness_budget_adequacy_qualification.py",
)
VALIDATION_PATHS = (
    "tests/test_budget_adequacy.py",
    "tests/test_budget_adequacy_qualification.py",
    "tests/test_finalization.py",
    "tests/test_saturation_recovery_qualification.py",
    "tests/test_saturation_recovery_shadow_qualification.py",
)


class FileBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    file_bytes: int = Field(gt=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class BoundaryObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    observation_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    scenario: Literal[
        "input-token-terminal",
        "output-token-terminal",
        "total-token-terminal",
        "zero-success-cost-denominator",
    ]
    expected_gate_passed: bool
    expected_terminal_dimension: Literal["input_tokens", "output_tokens", "total_tokens", "none"]
    report: BudgetAdequacyReport

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        expected_id = sha256_json(
            {"scenario": self.scenario, "report_hash": self.report.content_hash}
        )
        if self.observation_id != expected_id:
            raise ValueError("budget adequacy boundary identity differs")
        if self.report.budget_adequacy_gate_passed is not self.expected_gate_passed:
            raise ValueError("budget adequacy boundary gate differs")
        counts = {
            "input_tokens": self.report.overall_summary.input_token_terminal_rows,
            "output_tokens": self.report.overall_summary.output_token_terminal_rows,
            "total_tokens": self.report.overall_summary.total_token_terminal_rows,
            "none": 0,
        }
        if self.expected_terminal_dimension == "none":
            if self.report.overall_summary.any_token_terminal_rows != 0:
                raise ValueError("zero-success boundary unexpectedly has a token terminal")
        elif counts[self.expected_terminal_dimension] != 1:
            raise ValueError("budget adequacy boundary dimension differs")
        return self


class BudgetAdequacyPublicQualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-budget-adequacy-public-qualification-v1"]
    qualification_id: Literal["lean-harness-budget-adequacy-public-20260816-v1"]
    status: Literal["PUBLIC_NO_CALL_BUDGET_ADEQUACY_QUALIFIED_RUNTIME_CLOSED"]
    evidence_date: Literal["2026-08-16"]
    evidence_scope: Literal["r8-public-development-and-deterministic-synthetic-boundaries"]
    contract: BudgetAdequacyThresholdContract
    contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    r8_development_evidence: EvidenceBinding
    finalization_reserve: EvidenceBinding
    saturation_thresholds: EvidenceBinding
    admission_recovery_shadow: EvidenceBinding
    reference_report: BudgetAdequacyReport
    reference_report_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    boundary_scenarios: tuple[str, ...]
    boundary_observations: tuple[BoundaryObservation, ...]
    expected_boundary_observations: Literal[4]
    reference_rows: Literal[4]
    reference_rows_per_condition: Literal[2]
    reference_realized_schedule_hash: Literal[
        "sha256:26026929c2992473b00ce58af760481d7406509f592b8d7674cb7ac6fa4a9a6d"
    ]
    reference_full_schedule_reserve_nanos: Literal[15300000000]
    reference_hard_cap_nanos: Literal[18000000000]
    reference_settled_model_cost_nanos: Literal[366421500]
    reference_successes: Literal[4]
    reference_evaluator_reached_rows: Literal[4]
    reference_token_terminal_rows: Literal[0]
    reference_patch_attempts: Literal[6]
    reference_patch_rejections: Literal[1]
    reference_no_new_evidence_turns: Literal[3]
    reference_patch_check_diff_submission_rows: Literal[4]
    zero_terminal_criterion_exact: Literal[True]
    all_terminal_dimensions_fail_adequacy_only: Literal[True]
    fixed_budget_success_remains_estimable_with_token_terminal: Literal[True]
    zero_success_cost_denominator_is_null: Literal[True]
    equal_condition_denominator_required: Literal[True]
    threshold_selection_uses_r16: Literal[False]
    r16_artifact_files_read: Literal[0]
    trace_snapshot_files_read: Literal[0]
    runtime_state_files_read: Literal[0]
    public_task_files_read: Literal[0]
    private_task_files_read: Literal[0]
    hidden_files_read: Literal[0]
    reference_patches_read: Literal[0]
    source_files: tuple[FileBinding, ...]
    validation_files: tuple[FileBinding, ...]
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    bound_evidence_artifact_files_read: Literal[4]
    provider_transport_calls: Literal[0]
    provider_generation_calls: Literal[0]
    runner_calls: Literal[0]
    tool_execution_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    added_model_cost_usd: Literal[0]
    provider_calls_authorized: Literal[False]
    runner_activation_authorized: Literal[False]
    tool_policy_activation_authorized: Literal[False]
    request_integration_authorized: Literal[False]
    state_mutation_authorized: Literal[False]
    fresh_panel_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    next_gate: Literal[
        "preregister-versioned-lean-runtime-integration-and-fresh-development-validation"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        if self.contract != r8_public_budget_adequacy_contract() or (
            self.contract_hash != self.contract.content_hash
        ):
            raise ValueError("budget adequacy nested contract differs")
        expected_bindings = (
            self.contract.r8_development_evidence,
            self.contract.finalization_reserve,
            self.contract.saturation_thresholds,
            self.contract.admission_recovery_shadow,
        )
        if (
            self.r8_development_evidence,
            self.finalization_reserve,
            self.saturation_thresholds,
            self.admission_recovery_shadow,
        ) != expected_bindings:
            raise ValueError("budget adequacy qualification evidence differs")
        try:
            reference = BudgetAdequacyReport.model_validate(
                self.reference_report.model_dump(mode="python")
            )
            boundaries = tuple(
                BoundaryObservation.model_validate(item.model_dump(mode="python"))
                for item in self.boundary_observations
            )
        except ValueError as exc:
            raise ValueError("budget adequacy nested projection is invalid") from exc
        if reference != self.reference_report or boundaries != self.boundary_observations:
            raise ValueError("budget adequacy nested projection differs")
        if self.reference_report_hash != reference.content_hash:
            raise ValueError("budget adequacy reference hash differs")
        expected_envelope = build_budget_envelope(
            max_cumulative_input_tokens=self.contract.public_max_cumulative_input_tokens,
            max_cumulative_output_tokens=self.contract.public_max_cumulative_output_tokens,
            max_total_tokens=self.contract.public_max_total_tokens,
        )
        if reference.envelope != expected_envelope:
            raise ValueError("budget adequacy reference envelope differs")
        if (
            self.boundary_scenarios != BOUNDARY_SCENARIOS
            or tuple(item.scenario for item in boundaries) != BOUNDARY_SCENARIOS
        ):
            raise ValueError("budget adequacy boundary frame differs")
        if len(boundaries) != self.expected_boundary_observations:
            raise ValueError("budget adequacy boundary count differs")
        expected_gates = (False, False, False, True)
        expected_dimensions = ("input_tokens", "output_tokens", "total_tokens", "none")
        if (
            tuple(item.expected_gate_passed for item in boundaries) != expected_gates
            or tuple(item.expected_terminal_dimension for item in boundaries) != expected_dimensions
        ):
            raise ValueError("budget adequacy boundary expectations differ")
        reference_row_ids = tuple(item.observation_id for item in reference.rows)
        if any(
            (
                item.report.realized_schedule_hash,
                item.report.envelope,
                item.report.full_schedule_reserve_nanos,
                item.report.hard_cap_nanos,
                tuple(row.observation_id for row in item.report.rows),
            )
            != (
                reference.realized_schedule_hash,
                reference.envelope,
                reference.full_schedule_reserve_nanos,
                reference.hard_cap_nanos,
                reference_row_ids,
            )
            for item in boundaries
        ):
            raise ValueError("budget adequacy boundary runtime frame differs")
        if reference.budget_adequacy_gate_passed is not True or (
            reference.overall_summary.any_token_terminal_rows != 0
        ):
            raise ValueError("budget adequacy public reference differs")
        if (
            reference.expected_rows,
            reference.rows_per_condition,
            reference.realized_schedule_hash,
            reference.full_schedule_reserve_nanos,
            reference.hard_cap_nanos,
            reference.settled_model_cost_nanos,
            reference.overall_summary.successes,
            reference.overall_summary.evaluator_reached_rows,
            reference.overall_summary.patch_attempts,
            reference.overall_summary.patch_rejections,
            reference.overall_summary.no_new_evidence_turns,
        ) != (
            4,
            2,
            self.reference_realized_schedule_hash,
            15_300_000_000,
            18_000_000_000,
            366_421_500,
            4,
            4,
            6,
            1,
            3,
        ):
            raise ValueError("budget adequacy public aggregates differ")
        if any(
            value != 4
            for value in (
                reference.overall_summary.patch_milestone_rows,
                reference.overall_summary.check_milestone_rows,
                reference.overall_summary.diff_milestone_rows,
                reference.overall_summary.submission_milestone_rows,
            )
        ):
            raise ValueError("budget adequacy public milestones differ")
        if (
            tuple(item.path for item in self.source_files) != SOURCE_PATHS
            or tuple(item.path for item in self.validation_files) != VALIDATION_PATHS
        ):
            raise ValueError("budget adequacy file inventory differs")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ) or self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("budget adequacy inventory hash differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("budget adequacy qualification hash differs")
        return self


def _repository_root(repository: str | Path) -> Path:
    root = Path(repository).resolve()
    if not (root / "pyproject.toml").is_file():
        raise RecoveryError("budget adequacy qualification repository is invalid")
    return root


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate budget adequacy key: {key}")
        value[key] = item
    return value


def _read_json(root: Path, binding: EvidenceBinding) -> tuple[bytes, dict[str, Any]]:
    raw = ensure_within(root, binding.path).read_bytes()
    if len(raw) != binding.file_bytes or sha256_bytes(raw) != binding.file_sha256:
        raise RecoveryError(f"budget adequacy predecessor differs: {binding.path}")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RecoveryError(f"budget adequacy predecessor is invalid: {binding.path}") from exc
    if type(value) is not dict or value.get("content_hash") != binding.content_hash:
        raise RecoveryError(f"budget adequacy predecessor content differs: {binding.path}")
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if sha256_json(body) != binding.content_hash:
        raise RecoveryError(f"budget adequacy predecessor hash differs: {binding.path}")
    return raw, value


def _file_binding(root: Path, relative: str) -> FileBinding:
    raw = ensure_within(root, relative).read_bytes()
    return FileBinding(path=relative, file_bytes=len(raw), file_sha256=sha256_bytes(raw))


def _validated_predecessors(
    root: Path,
    contract: BudgetAdequacyThresholdContract,
) -> tuple[dict[str, Any], FinalizationReserveContract, SaturationRecoveryPublicQualification]:
    _, r8 = _read_json(root, contract.r8_development_evidence)

    finalization_raw, _ = _read_json(root, contract.finalization_reserve)
    try:
        finalization = FinalizationReserveContract.model_validate_json(finalization_raw)
    except ValueError as exc:
        raise RecoveryError("budget adequacy finalization predecessor is invalid") from exc
    if finalization != r8_public_development_finalization_reserve():
        raise RecoveryError("budget adequacy finalization predecessor differs")

    thresholds_raw, _ = _read_json(root, contract.saturation_thresholds)
    try:
        thresholds = SaturationRecoveryPublicQualification.model_validate_json(thresholds_raw)
    except ValueError as exc:
        raise RecoveryError("budget adequacy threshold predecessor is invalid") from exc
    if saturation_qualification_bytes(thresholds) != thresholds_raw:
        raise RecoveryError("budget adequacy threshold predecessor is noncanonical")

    admission_raw, _ = _read_json(root, contract.admission_recovery_shadow)
    try:
        admission = SaturationRecoveryShadowPublicQualification.model_validate_json(admission_raw)
    except ValueError as exc:
        raise RecoveryError("budget adequacy admission predecessor is invalid") from exc
    if admission_shadow_qualification_bytes(admission) != admission_raw:
        raise RecoveryError("budget adequacy admission predecessor is noncanonical")
    if admission.predecessor_threshold_content_hash != thresholds.content_hash:
        raise RecoveryError("budget adequacy admission threshold binding differs")
    return r8, finalization, thresholds


def _reference_rows(
    r8: dict[str, Any],
    finalization: FinalizationReserveContract,
    thresholds: SaturationRecoveryPublicQualification,
) -> tuple[BudgetAdequacyRowObservation, ...]:
    rows = r8.get("rows")
    if type(rows) is not list or len(rows) != 4:
        raise RecoveryError("budget adequacy R8 rows are incomplete")
    threshold_by_run = {item.run_id: item for item in thresholds.observations}
    finalization_by_run = {item.run_id: item for item in finalization.observations}
    expected_frame = (
        (1, "moto-query-scanned-count", "no_memory"),
        (2, "moto-query-scanned-count", "structured"),
        (3, "babel-strict-grouped-decimal-trailing-zeroes", "structured"),
        (4, "babel-strict-grouped-decimal-trailing-zeroes", "no_memory"),
    )
    projected: list[BudgetAdequacyRowObservation] = []
    for raw_row, expected in zip(rows, expected_frame, strict=True):
        if (
            type(raw_row) is not dict
            or (raw_row.get("order"), raw_row.get("task_id"), raw_row.get("condition")) != expected
        ):
            raise RecoveryError("budget adequacy R8 schedule differs")
        if (
            raw_row.get("outcome_kind") != "resolved"
            or raw_row.get("evaluation_reached") is not True
            or raw_row.get("trace_qualified") is not True
        ):
            raise RecoveryError("budget adequacy R8 row is not resolved and eligible")
        verdicts = raw_row.get("verdicts")
        if type(verdicts) is not dict or set(verdicts.values()) != {"pass"}:
            raise RecoveryError("budget adequacy R8 verdicts differ")
        run_id = raw_row.get("run_id")
        if (
            type(run_id) is not str
            or run_id not in threshold_by_run
            or run_id not in finalization_by_run
        ):
            raise RecoveryError("budget adequacy R8 lifecycle binding differs")
        threshold = threshold_by_run[run_id]
        lifecycle = finalization_by_run[run_id]
        if (threshold.task_id, threshold.condition) != (
            raw_row["task_id"],
            raw_row["condition"],
        ) or (lifecycle.task_id, lifecycle.condition) != (
            raw_row["task_id"],
            raw_row["condition"],
        ):
            raise RecoveryError("budget adequacy R8 lifecycle projection differs")
        usage = raw_row.get("usage")
        usage_evidence = raw_row.get("usage_evidence")
        if type(usage) is not dict or type(usage_evidence) is not dict:
            raise RecoveryError("budget adequacy R8 usage is missing")
        tools = tuple(name for turn in lifecycle.turns for name in turn.tool_names)
        projected.append(
            build_budget_adequacy_row(
                order=raw_row["order"],
                task_id=raw_row["task_id"],
                condition=raw_row["condition"],
                outcome_kind="resolved",
                success=True,
                evaluator_reached=True,
                token_terminal_dimension="none",
                patch_milestone="apply_patch" in tools,
                check_milestone="run_check" in tools,
                diff_milestone="get_diff" in tools,
                submission_milestone="finish_task" in tools,
                no_new_evidence_turns=threshold.loop_detection_count,
                patch_attempts=(
                    threshold.successful_mutation_count + threshold.rejected_patch_count
                ),
                patch_rejections=threshold.rejected_patch_count,
                input_tokens=usage.get("input_tokens"),
                output_tokens=usage.get("output_tokens"),
                total_tokens=usage.get("input_tokens") + usage.get("output_tokens"),
                model_cost_nanos=usage_evidence.get("token_derived_cost_nanos"),
            )
        )
    return tuple(projected)


def _replace_row(
    row: BudgetAdequacyRowObservation,
    **updates: object,
) -> BudgetAdequacyRowObservation:
    body = row.model_dump(mode="python", exclude={"observation_id", "content_hash"})
    body.update(updates)
    return build_budget_adequacy_row(**body)


def _boundary_observations(
    reference_rows: tuple[BudgetAdequacyRowObservation, ...],
) -> tuple[BoundaryObservation, ...]:
    observations: list[BoundaryObservation] = []
    dimensions = ("input_tokens", "output_tokens", "total_tokens")
    for index, (scenario, dimension) in enumerate(
        zip(BOUNDARY_SCENARIOS[:3], dimensions, strict=True)
    ):
        rows = list(reference_rows)
        source = rows[index]
        rows[index] = _replace_row(
            source,
            outcome_kind="agent_failure",
            success=False,
            evaluator_reached=False,
            token_terminal_dimension=dimension,
            check_milestone=False,
            diff_milestone=False,
            submission_milestone=False,
        )
        report = project_budget_adequacy(
            measurement_id=f"synthetic-{scenario}",
            expected_rows=4,
            realized_schedule_hash=(
                "sha256:26026929c2992473b00ce58af760481d7406509f592b8d7674cb7ac6fa4a9a6d"
            ),
            envelope=build_budget_envelope(
                max_cumulative_input_tokens=3_000_000,
                max_cumulative_output_tokens=350_000,
                max_total_tokens=3_350_000,
            ),
            full_schedule_reserve_nanos=15_300_000_000,
            hard_cap_nanos=18_000_000_000,
            rows=tuple(rows),
        )
        identity = {"scenario": scenario, "report_hash": report.content_hash}
        observations.append(
            BoundaryObservation(
                observation_id=sha256_json(identity),
                scenario=scenario,
                expected_gate_passed=False,
                expected_terminal_dimension=dimension,
                report=report,
            )
        )

    rows = list(reference_rows)
    for index in (1, 2):
        rows[index] = _replace_row(
            rows[index],
            outcome_kind="task_failure",
            success=False,
        )
    report = project_budget_adequacy(
        measurement_id="synthetic-zero-success-cost-denominator",
        expected_rows=4,
        realized_schedule_hash=(
            "sha256:26026929c2992473b00ce58af760481d7406509f592b8d7674cb7ac6fa4a9a6d"
        ),
        envelope=build_budget_envelope(
            max_cumulative_input_tokens=3_000_000,
            max_cumulative_output_tokens=350_000,
            max_total_tokens=3_350_000,
        ),
        full_schedule_reserve_nanos=15_300_000_000,
        hard_cap_nanos=18_000_000_000,
        rows=tuple(rows),
    )
    identity = {
        "scenario": "zero-success-cost-denominator",
        "report_hash": report.content_hash,
    }
    observations.append(
        BoundaryObservation(
            observation_id=sha256_json(identity),
            scenario="zero-success-cost-denominator",
            expected_gate_passed=True,
            expected_terminal_dimension="none",
            report=report,
        )
    )
    return tuple(observations)


def build_budget_adequacy_public_qualification(
    repository: str | Path = ".",
) -> BudgetAdequacyPublicQualification:
    root = _repository_root(repository)
    contract = r8_public_budget_adequacy_contract()
    r8, finalization, thresholds = _validated_predecessors(root, contract)
    campaign = r8.get("campaign")
    expected_campaign = {
        "schedule_hash": contract.public_realized_schedule_hash,
        "full_schedule_reserve_nanos": contract.public_full_schedule_reserve_nanos,
        "hard_cap_nanos": contract.public_hard_cap_nanos,
        "accrued_cost_nanos": contract.public_settled_model_cost_nanos,
        "expected_runs": 4,
        "terminal_runs": 4,
        "not_started_runs": 0,
        "retry_or_replacement_performed": False,
    }
    if type(campaign) is not dict or any(
        campaign.get(key) != value for key, value in expected_campaign.items()
    ):
        raise RecoveryError("budget adequacy R8 campaign facts differ")
    rows = _reference_rows(r8, finalization, thresholds)
    envelope = build_budget_envelope(
        max_cumulative_input_tokens=contract.public_max_cumulative_input_tokens,
        max_cumulative_output_tokens=contract.public_max_cumulative_output_tokens,
        max_total_tokens=contract.public_max_total_tokens,
    )
    reference = project_budget_adequacy(
        measurement_id="r8-public-development-budget-adequacy-reference",
        expected_rows=4,
        realized_schedule_hash=contract.public_realized_schedule_hash,
        envelope=envelope,
        full_schedule_reserve_nanos=contract.public_full_schedule_reserve_nanos,
        hard_cap_nanos=contract.public_hard_cap_nanos,
        rows=rows,
    )
    boundaries = _boundary_observations(rows)
    source_files = tuple(_file_binding(root, path) for path in SOURCE_PATHS)
    validation_files = tuple(_file_binding(root, path) for path in VALIDATION_PATHS)
    body: dict[str, Any] = {
        "schema_version": QUALIFICATION_SCHEMA,
        "qualification_id": QUALIFICATION_ID,
        "status": "PUBLIC_NO_CALL_BUDGET_ADEQUACY_QUALIFIED_RUNTIME_CLOSED",
        "evidence_date": "2026-08-16",
        "evidence_scope": "r8-public-development-and-deterministic-synthetic-boundaries",
        "contract": contract.model_dump(mode="python"),
        "contract_hash": contract.content_hash,
        "r8_development_evidence": contract.r8_development_evidence.model_dump(mode="python"),
        "finalization_reserve": contract.finalization_reserve.model_dump(mode="python"),
        "saturation_thresholds": contract.saturation_thresholds.model_dump(mode="python"),
        "admission_recovery_shadow": contract.admission_recovery_shadow.model_dump(mode="python"),
        "reference_report": reference.model_dump(mode="python"),
        "reference_report_hash": reference.content_hash,
        "boundary_scenarios": BOUNDARY_SCENARIOS,
        "boundary_observations": tuple(item.model_dump(mode="python") for item in boundaries),
        "expected_boundary_observations": 4,
        "reference_rows": 4,
        "reference_rows_per_condition": 2,
        "reference_realized_schedule_hash": contract.public_realized_schedule_hash,
        "reference_full_schedule_reserve_nanos": contract.public_full_schedule_reserve_nanos,
        "reference_hard_cap_nanos": contract.public_hard_cap_nanos,
        "reference_settled_model_cost_nanos": contract.public_settled_model_cost_nanos,
        "reference_successes": 4,
        "reference_evaluator_reached_rows": 4,
        "reference_token_terminal_rows": 0,
        "reference_patch_attempts": 6,
        "reference_patch_rejections": 1,
        "reference_no_new_evidence_turns": 3,
        "reference_patch_check_diff_submission_rows": 4,
        "zero_terminal_criterion_exact": True,
        "all_terminal_dimensions_fail_adequacy_only": True,
        "fixed_budget_success_remains_estimable_with_token_terminal": True,
        "zero_success_cost_denominator_is_null": True,
        "equal_condition_denominator_required": True,
        "threshold_selection_uses_r16": False,
        "r16_artifact_files_read": 0,
        "trace_snapshot_files_read": 0,
        "runtime_state_files_read": 0,
        "public_task_files_read": 0,
        "private_task_files_read": 0,
        "hidden_files_read": 0,
        "reference_patches_read": 0,
        "source_files": tuple(item.model_dump(mode="python") for item in source_files),
        "validation_files": tuple(item.model_dump(mode="python") for item in validation_files),
        "source_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in source_files]
        ),
        "validation_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in validation_files]
        ),
        "bound_evidence_artifact_files_read": 4,
        "provider_transport_calls": 0,
        "provider_generation_calls": 0,
        "runner_calls": 0,
        "tool_execution_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "added_model_cost_usd": 0,
        "provider_calls_authorized": False,
        "runner_activation_authorized": False,
        "tool_policy_activation_authorized": False,
        "request_integration_authorized": False,
        "state_mutation_authorized": False,
        "fresh_panel_authorized": False,
        "paid_execution_authorized": False,
        "next_gate": (
            "preregister-versioned-lean-runtime-integration-and-fresh-development-validation"
        ),
    }
    return BudgetAdequacyPublicQualification.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def qualification_bytes(qualification: BudgetAdequacyPublicQualification) -> bytes:
    return (
        json.dumps(
            qualification.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def materialize_budget_adequacy_public_qualification(
    repository: str | Path = ".",
    output_path: str | Path = QUALIFICATION_PATH,
) -> BudgetAdequacyPublicQualification:
    root = _repository_root(repository)
    qualification = build_budget_adequacy_public_qualification(root)
    content = qualification_bytes(qualification)
    output = ensure_within(root, str(output_path))
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.read_bytes() != content:
            raise RecoveryError("existing budget adequacy qualification differs")
        return qualification
    with output.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    return qualification


def load_budget_adequacy_public_qualification(
    repository: str | Path = ".",
    path: str | Path = QUALIFICATION_PATH,
) -> BudgetAdequacyPublicQualification:
    root = _repository_root(repository)
    raw = ensure_within(root, str(path)).read_bytes()
    try:
        text = raw.decode("utf-8", errors="strict")
        json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
        qualification = BudgetAdequacyPublicQualification.model_validate_json(text)
    except (UnicodeDecodeError, ValueError) as exc:
        raise RecoveryError("budget adequacy qualification is invalid JSON") from exc
    if qualification_bytes(qualification) != raw:
        raise RecoveryError("budget adequacy qualification bytes are not canonical")
    expected = build_budget_adequacy_public_qualification(root)
    if qualification != expected:
        raise RecoveryError("budget adequacy qualification differs from source")
    return qualification


__all__ = [
    "BOUNDARY_SCENARIOS",
    "BudgetAdequacyPublicQualification",
    "QUALIFICATION_ID",
    "QUALIFICATION_PATH",
    "QUALIFICATION_SCHEMA",
    "build_budget_adequacy_public_qualification",
    "load_budget_adequacy_public_qualification",
    "materialize_budget_adequacy_public_qualification",
    "qualification_bytes",
]
