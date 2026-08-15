"""Strict immutable contracts for the execution-closed held-out A/C suite."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.util import sha256_json

HELDOUT_AC_SUITE_ID = "core-ac-fixed-bundle-heldout-20260814-v1"
HELDOUT_AC_PREREGISTRATION_CONTENT_HASH = (
    "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
)
HELDOUT_AC_PREREGISTRATION_FILE_SHA256 = (
    "sha256:f6d9d015329823f3f888aac5f15296b2ddefda9e45b5d5501b8d94587bb11d8f"
)


class HeldoutACFrozenModel(BaseModel):
    """Strict immutable base for the execution-closed held-out A/C suite."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class HeldoutACPreregistrationSectionHashes(HeldoutACFrozenModel):
    dataset: Literal["sha256:effac6a9e9a26b21db52e6377a078746819d95dfd6607e7db11ca5bc8dcbdfc2"]
    treatment: Literal["sha256:f3a7256fe2201d0d43c4739c973a180ba0fd4d5bfe5de4f472b21589068982b3"]
    schedule_design: Literal[
        "sha256:52f58401c3626e5d788719ff0932f3f2a2abf1dd1cb092570ad0be461ff68a72"
    ]
    schedule: Literal["sha256:e999650448975f7382d69734ff52fa8c95d912bdb01dbdf82e17d8098d3f6206"]
    runtime: Literal["sha256:907b109b07606e78ed9eacd09b91e09b49fe46d6b4a1dc7bae2b79baf772fd03"]
    cost: Literal["sha256:c1034d283fed13ddb6af0f5462d06add2df5004730d3466ae73ef2cce8d0c2bb"]
    outcomes: Literal["sha256:03ea217e0092c84b02bedd1b896c3e7c5aabd174d6147bf83ab1af6934f54bc5"]
    analysis: Literal["sha256:a044262a830b4615bf0ee9394879a22e46acce184a0894696baff2193b216a3a"]
    exclusions: Literal["sha256:055316274c9dc14bb0b0e9e67735047ba8104db275a77ef2f8edf5e055ee3ed7"]
    stopping: Literal["sha256:d8c723fd38e592c81859b7ed298c407cef3d4682077f5e96807ccd0977388c20"]
    authority: Literal["sha256:c3b416c3f1a9d039713964ba4f4b1f62dfd33c44201c1787c25048e2088ac855"]


class HeldoutACPreregistrationBinding(HeldoutACFrozenModel):
    path: Literal["experiments/heldout-ac-preregistration-20260814-v1.yaml"]
    preregistration_id: Literal["core-ac-fixed-bundle-heldout-20260814-v1"]
    content_hash: Literal["sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"]
    file_bytes: Literal[31_338]
    file_sha256: Literal["sha256:f6d9d015329823f3f888aac5f15296b2ddefda9e45b5d5501b8d94587bb11d8f"]
    section_hashes: HeldoutACPreregistrationSectionHashes


class HeldoutACDatasetBinding(HeldoutACFrozenModel):
    manifest_path: Literal["data/dataset-manifest.yaml"]
    manifest_file_bytes: Literal[47_368]
    manifest_file_sha256: Literal[
        "sha256:e8cf14ca9dabebcc03c3522e400dfcb79606541e9b11e59f49510ea5c40bebed"
    ]
    dataset_id: Literal["patchloop-benchmark-v1"]
    status: Literal["frozen"]
    selection_rule: Literal["complete-admitted-core-same-repo-and-core-cross-repo-panel"]


class HeldoutACSuiteTask(HeldoutACFrozenModel):
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    role: Literal["core-same-repo", "core-cross-repo"]


class HeldoutACNoMemoryTreatment(HeldoutACFrozenModel):
    selected_memory: None
    entry_count: Literal[0]
    bundle_bytes: Literal[0]
    bundle_sha256: None


class HeldoutACStructuredTreatment(HeldoutACFrozenModel):
    delivery: Literal["exact-d110-three-entry-bundle-every-request"]
    entry_count: Literal[3]
    bundle_bytes: Literal[3_528]
    bundle_sha256: Literal[
        "sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf"
    ]
    d110_index_version: Literal[
        "idxgrp_563976c4443a725e287225cef1e718daf134fbb96574921cb9e020049ea52064"
    ]
    d110_index_content_hash: Literal[
        "sha256:3a99e6c190672d1676bc4d13604de989899de9ddac85d282cc90c4d56f426c56"
    ]


class HeldoutACTreatment(HeldoutACFrozenModel):
    conditions: tuple[Literal["no_memory"], Literal["structured"]]
    memory_policy_version: Literal["fixed-d110-bundle-v1"]
    no_memory: HeldoutACNoMemoryTreatment
    structured: HeldoutACStructuredTreatment
    query_embedding_or_similarity_used: Literal[False]
    threshold_or_reranking_used: Literal[False]
    only_treatment_difference: Literal["selected-memory-content-and-derived-evidence"]

    @field_validator("conditions", mode="before")
    @classmethod
    def freeze_yaml_conditions(cls, value: Any) -> Any:
        if type(value) not in {list, tuple}:
            raise ValueError("held-out A/C conditions must be a sequence")
        return tuple(value)


class HeldoutACScheduleBinding(HeldoutACFrozenModel):
    seed: Literal[20_260_814]
    repetitions: Literal[2]
    expected_runs: Literal[48]
    task_condition_pairs: Literal[24]
    waves: Literal[4]
    rows_per_wave: Literal[12]
    pair_adjacency_required: Literal[True]
    condition_order_reversed_in_repetition_2: Literal[True]
    replacement_allowed: Literal[False]
    retry_allowed: Literal[False]
    projection_bytes: Literal[6_128]
    projection_sha256: Literal[
        "sha256:26ddf0c7123a8fb17e27e1b7229f4aa9d01f6ad3162f29b2463aa71a79451c51"
    ]


class HeldoutACSuiteScheduleRow(HeldoutACFrozenModel):
    order: int = Field(ge=1, le=48)
    wave: int = Field(ge=1, le=4)
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    role: Literal["core-same-repo", "core-cross-repo"]
    condition: Literal["no_memory", "structured"]
    repetition: Literal[1, 2]


class HeldoutACRuntime(HeldoutACFrozenModel):
    evaluator_version: Literal["v2"]
    safety_contract_schema: Literal["evaluator-safety-contract-v2"]
    receipt_schema: Literal["evaluator-v2-evaluation-receipt-v1"]
    raw_result_official: Literal[False]
    model: Literal["openai"]
    model_id: Literal["gpt-5.4-mini-2026-03-17"]
    reasoning_effort: Literal["medium"]
    reasoning_mode: Literal["standard"]
    service_tier: Literal["default"]
    transport_max_retries: Literal[0]
    store: Literal[False]
    system_prompt_version: Literal["SYSTEM_PROMPT_V3"]
    tool_schema_version: Literal["v2"]
    context_policy_version: Literal["phase-evidence-v5"]
    memory_policy_version: Literal["fixed-d110-bundle-v1"]
    sandbox_backend: Literal["docker"]
    marker_profile: Literal["task-private-plus-run-secret-exact-v1"]
    call_guard_policy: Literal["model-tool-bounded-enforcement-v1"]
    max_output_tokens: Literal[25_000]
    token_budget_schema_version: Literal["cumulative-split-v1"]
    max_cumulative_input_tokens: Literal[4_000_000]
    max_cumulative_output_tokens: Literal[500_000]
    max_total_tokens: Literal[4_500_000]
    max_model_calls: Literal[240]
    max_tool_calls: Literal[400]
    wall_clock_timeout_seconds: Literal[3_600]


class HeldoutACCompletionCampaignAuthority(HeldoutACFrozenModel):
    """Execution-free projection of one validated candidate's completion controls."""

    schema_version: Literal["heldout-ac-completion-campaign-authority-v1"]
    candidate_schema_version: Literal[
        "heldout-ac-execution-candidate-v1",
        "heldout-ac-execution-candidate-v2",
        "heldout-ac-execution-candidate-v3",
    ]
    suite_id: Literal[HELDOUT_AC_SUITE_ID]
    suite_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    realized_schedule_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    schedule_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    schedule_row_ids: tuple[str, ...] = Field(min_length=48, max_length=48)
    runtime_tuple_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    pricing_binding_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    max_cumulative_input_tokens: int = Field(gt=0)
    max_cumulative_output_tokens: int = Field(gt=0)
    max_total_tokens: int = Field(gt=0)
    max_model_calls: int = Field(gt=0)
    max_tool_calls: int = Field(gt=0)
    wall_clock_timeout_seconds: int = Field(gt=0)
    campaign_cost_control_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    per_run_reserve_nanos: int = Field(gt=0)
    full_schedule_reserve_nanos: int = Field(gt=0)
    hard_cap_nanos: int = Field(gt=0)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_authority(self) -> HeldoutACCompletionCampaignAuthority:
        if self.candidate_schema_version == "heldout-ac-execution-candidate-v3":
            if self.realized_schedule_hash is None:
                raise ValueError("held-out completion authority realized schedule is absent")
        elif self.realized_schedule_hash is not None:
            raise ValueError("held-out historical completion authority has a realized schedule")
        expected_limits = (
            (4_000_000, 500_000, 4_500_000, 5_250_000_000, 252_000_000_000, 275_000_000_000)
            if self.candidate_schema_version == "heldout-ac-execution-candidate-v1"
            else (1_000_000, 100_000, 1_100_000, 1_200_000_000, 57_600_000_000, 60_000_000_000)
        )
        observed_limits = (
            self.max_cumulative_input_tokens,
            self.max_cumulative_output_tokens,
            self.max_total_tokens,
            self.per_run_reserve_nanos,
            self.full_schedule_reserve_nanos,
            self.hard_cap_nanos,
        )
        if observed_limits != expected_limits or (
            self.max_model_calls,
            self.max_tool_calls,
            self.wall_clock_timeout_seconds,
        ) != (240, 400, 3_600):
            raise ValueError("held-out completion authority budget or cost boundary differs")
        if len(set(self.schedule_row_ids)) != 48:
            raise ValueError("held-out completion authority schedule identities are not unique")
        cost_body = {
            "schema_version": (
                "heldout-ac-full-schedule-cost-control-v1"
                if self.candidate_schema_version == "heldout-ac-execution-candidate-v1"
                else "heldout-ac-full-schedule-cost-control-v2"
            ),
            "suite_id": self.suite_id,
            "suite_content_hash": self.suite_content_hash,
            "execution_hash": self.execution_hash,
            "schedule_hash": self.schedule_hash,
            "scheduled_run_count": 48,
            "per_run_reserve_nanos": self.per_run_reserve_nanos,
            "full_schedule_reserve_nanos": self.full_schedule_reserve_nanos,
            "hard_cap_nanos": self.hard_cap_nanos,
            "cost_censoring_allowed": False,
            "live_resume_supported": False,
        }
        if self.campaign_cost_control_hash != sha256_json(cost_body):
            raise ValueError("held-out completion authority cost-control hash differs")
        expected_hash = sha256_json(
            self.model_dump(mode="json", exclude={"content_hash"}, exclude_none=True)
        )
        if self.content_hash != expected_hash:
            raise ValueError("held-out completion authority content hash differs")
        return self


class HeldoutACCost(HeldoutACFrozenModel):
    schema_version: Literal["heldout-ac-split-token-full-schedule-reserve-v1"]
    accounting_scope: Literal["campaign-local"]
    accounting_basis: Literal["split-token-ceiling-standard-list-price"]
    scheduled_run_count: Literal[48]
    input_reserve_rate_per_million_usd: Literal[0.75]
    output_reserve_rate_per_million_usd: Literal[4.5]
    cache_discount_assumed: Literal[False]
    per_run_reserve_usd: Literal[5.25]
    full_schedule_reserve_usd: Literal[252.0]
    hard_cap_usd: Literal[275.0]
    hard_cap_slack_usd: Literal[23.0]
    money_scale: Literal["nano-usd"]
    per_run_reserve_nanos: Literal[5_250_000_000]
    full_schedule_reserve_nanos: Literal[252_000_000_000]
    hard_cap_nanos: Literal[275_000_000_000]
    hard_cap_slack_nanos: Literal[23_000_000_000]
    reservation_mode: Literal["row-bound-full-schedule-up-front"]
    initial_reservation_boundary: Literal["before-first-provider-call"]
    row_reserve_count: Literal[48]
    cost_censoring_allowed: Literal[False]
    not_started_due_to_cost_allowed: Literal[False]
    automatic_retry_or_replacement_allowed: Literal[False]
    settlement_basis: Literal["durable-token-derived-standard-list-price"]
    live_resume_policy: Literal["disabled"]
    completion_guaranteed: Literal[False]
    invoice_or_free_tier_claimed: Literal[False]
    pricing_basis_observed_at: Literal["2026-08-13T12:05:26Z"]
    pricing_source_url: Literal["https://developers.openai.com/api/docs/pricing"]
    pricing_refresh_required_before_candidate: Literal[True]
    pricing_drift_disposition: Literal["block-and-create-successor-cost-binding"]

    @field_validator(
        "input_reserve_rate_per_million_usd",
        "output_reserve_rate_per_million_usd",
        "per_run_reserve_usd",
        "full_schedule_reserve_usd",
        "hard_cap_usd",
        "hard_cap_slack_usd",
        mode="before",
    )
    @classmethod
    def validate_float_cost_fields(cls, value: Any) -> Any:
        if type(value) is not float:
            raise ValueError("held-out A/C USD amounts and rates must be YAML floats")
        return value


class HeldoutACExecutionGate(HeldoutACFrozenModel):
    source_qualification_present: Literal[False]
    exact_execution_candidate_present: Literal[False]
    explicit_paid_approval_present: Literal[False]
    pricing_refreshed_for_candidate: Literal[False]
    heldout_task_spec_or_outcome_access_authorized: Literal[False]
    provider_execution_authorized: Literal[False]
    evaluator_execution_authorized: Literal[False]
    agent_execution_authorized: Literal[False]
    docker_observation_authorized: Literal[False]
    sdk_observation_authorized: Literal[False]
    runtime_memory_injection_authorized: Literal[False]
    cost_reservation_authorized: Literal[False]
    spend_authorized: Literal[False]
    authorized_provider_calls: Literal[0]
    authorized_evaluator_calls: Literal[0]
    authorized_agent_runs: Literal[0]
    authorized_docker_calls: Literal[0]
    authorized_sdk_calls: Literal[0]
    authorized_cost_usd: Literal[0.0]

    @field_validator("authorized_cost_usd", mode="before")
    @classmethod
    def validate_authorized_cost_float(cls, value: Any) -> Any:
        if type(value) is not float:
            raise ValueError("held-out A/C authorized_cost_usd must be a YAML float")
        return value


class HeldoutACSuite(HeldoutACFrozenModel):
    """Metadata-only 48-row A/C suite; it is intentionally not executable."""

    schema_version: Literal["heldout-ac-suite-v1"]
    suite_id: Literal["core-ac-fixed-bundle-heldout-20260814-v1"]
    status: Literal["execution-closed"]
    created_date: Literal["2026-08-14"]
    preregistration: HeldoutACPreregistrationBinding
    dataset: HeldoutACDatasetBinding
    tasks: tuple[HeldoutACSuiteTask, ...] = Field(min_length=12, max_length=12)
    treatment: HeldoutACTreatment
    schedule_binding: HeldoutACScheduleBinding
    schedule: tuple[HeldoutACSuiteScheduleRow, ...] = Field(min_length=48, max_length=48)
    runtime: HeldoutACRuntime
    cost: HeldoutACCost
    execution_gate: HeldoutACExecutionGate
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_closed_matrix(self) -> HeldoutACSuite:
        if self.treatment.conditions != ("no_memory", "structured"):
            raise ValueError("held-out A/C conditions require canonical A then C order")
        if len(self.tasks) != 12 or len({task.task_id for task in self.tasks}) != 12:
            raise ValueError("held-out A/C suite requires 12 unique tasks")
        role_counts = {
            role: sum(task.role == role for task in self.tasks)
            for role in ("core-same-repo", "core-cross-repo")
        }
        if role_counts != {"core-same-repo": 6, "core-cross-repo": 6}:
            raise ValueError("held-out A/C suite requires six tasks per core role")
        if len(self.schedule) != 48:
            raise ValueError("held-out A/C suite requires exactly 48 scheduled rows")
        if [row.order for row in self.schedule] != list(range(1, 49)):
            raise ValueError("held-out A/C schedule order must be contiguous from 1 through 48")
        tasks_by_id = {task.task_id: task.role for task in self.tasks}
        observed_cells: set[tuple[str, str, int]] = set()
        for row in self.schedule:
            if tasks_by_id.get(row.task_id) != row.role:
                raise ValueError("held-out A/C schedule task role differs from task binding")
            observed_cells.add((row.task_id, row.condition, row.repetition))
        expected_cells = {
            (task_id, condition, repetition)
            for task_id in tasks_by_id
            for condition in ("no_memory", "structured")
            for repetition in (1, 2)
        }
        if observed_cells != expected_cells:
            raise ValueError("held-out A/C schedule is not the 12 by A/C by two matrix")
        for first, second in zip(self.schedule[::2], self.schedule[1::2], strict=True):
            if (
                first.task_id != second.task_id
                or first.role != second.role
                or first.repetition != second.repetition
                or {first.condition, second.condition} != {"no_memory", "structured"}
            ):
                raise ValueError("held-out A/C task-condition pairs must remain adjacent")
        return self

    @field_validator("tasks", "schedule", mode="before")
    @classmethod
    def freeze_yaml_rows(cls, value: Any) -> Any:
        if type(value) not in {list, tuple}:
            raise ValueError("held-out A/C task and schedule rows must be sequences")
        return tuple(value)


class HeldoutACSuiteFileBinding(HeldoutACFrozenModel):
    path: Literal["experiments/heldout-ac-suite-20260814-v1.yaml"]
    suite_id: Literal["core-ac-fixed-bundle-heldout-20260814-v1"]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    file_bytes: int = Field(gt=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class HeldoutACQualificationRequirements(HeldoutACFrozenModel):
    dedicated_source_qualification_required: Literal[True]
    refreshed_pricing_binding_required: Literal[True]
    exact_execution_candidate_required: Literal[True]
    separate_explicit_paid_approval_required: Literal[True]
    typed_agent_failure_completion_adapter_required: Literal[True]
    complete_panel_analysis_required: Literal[True]
    may_open_heldout_task_specs_or_outcomes: Literal[False]
    may_make_provider_evaluator_agent_docker_or_sdk_calls: Literal[False]
    may_reserve_or_spend_cost: Literal[False]


class HeldoutACSuitePlan(HeldoutACFrozenModel):
    schema_version: Literal["heldout-ac-suite-plan-v1"]
    plan_id: Literal["core-ac-fixed-bundle-heldout-20260814-v1-offline-plan"]
    status: Literal["offline-contract-only"]
    suite: HeldoutACSuiteFileBinding
    preregistration: HeldoutACPreregistrationBinding
    requirements: HeldoutACQualificationRequirements
    grants_execution_authority: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
