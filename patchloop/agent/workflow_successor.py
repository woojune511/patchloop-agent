"""Public-only deterministic workflow successors for Lean V9 and V10.

The outer state machine is reconstructed exclusively from durable public run
events and the current diff-bound evidence.  The functions in this module do
not execute tools, mutate state, contact a provider, or inspect evaluator data.
"""

from __future__ import annotations

import copy
import fnmatch
from collections import Counter
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.agent.phases import EvidenceState
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import ContractError
from patchloop.util import safe_relative_path, sha256_json, sha256_text

WORKFLOW_POLICY_V9 = "bounded-correction-review-repair-v1"
WORKFLOW_POLICY_V10 = "public-evidence-plan-gate-v1"
WORKFLOW_DECISION_SCHEMA = "lean-workflow-decision-v1"
WORKFLOW_SURFACE_SCHEMA = "lean-workflow-tool-surface-v1"
PUBLIC_TASK_SPEC_SCHEMA = "public-task-spec-v1"
WORK_PLAN_SCHEMA = "recorded-work-plan-v1"
PLAN_RECORDED_EVENT_SCHEMA = "plan-recorded-event-v1"
PROTOCOL_RECOVERY_POLICY = "shared-model-action-contract-recovery-v1"

_EMPTY_DIFF_HASH = sha256_text("")
_MUTATION_TOOLS = frozenset({"apply_patch", "apply_structured_edit"})
_INFO_TOOLS = frozenset({"search_files", "read_file"})
_PROTOCOL_REASON_CODES = frozenset(
    {
        "multiple_tool_calls",
        "unavailable_tool",
        "wrong_check_id",
        "actionless_response",
        "reasoning_incomplete",
    }
)

WorkflowTarget = Literal[
    "phase-policy",
    "visible-check",
    "correction-investigation",
    "corrective-mutation",
    "diff-review",
    "review-decision",
    "pre-mutation-exploration",
    "record-work-plan",
    "plan-implementation",
    "terminal",
]


class PublicTaskSpec(BaseModel):
    """Request-only projection of fields already present in ``PublicTask``."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["public-task-spec-v1"]
    task_id: str
    task_version: int = Field(ge=1)
    public_task_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    issue: dict[str, str]
    allowed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    max_changed_files: int = Field(ge=1)
    max_diff_lines: int = Field(ge=1)
    dependency_changes_allowed: bool
    public_api_changes_allowed: bool
    visible_check_ids: tuple[str, ...] = Field(min_length=1)
    source_public_task_only: Literal[True]
    hidden_acceptance_used: Literal[False]
    private_spec_used: Literal[False]
    reference_patch_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        if len(set(self.visible_check_ids)) != len(self.visible_check_ids):
            raise ValueError("public task spec visible checks repeat")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("public task spec content hash differs")
        return self


class RecordedWorkPlan(BaseModel):
    """Validated, durable plan bound to one run/task/current diff."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["recorded-work-plan-v1"]
    run_id: str = Field(min_length=1)
    task_id: str
    task_version: int = Field(ge=1)
    public_task_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    reproduction_status: Literal[
        "confirmed_failure",
        "not_reproduced",
        "static_evidence",
    ]
    hypothesis: str = Field(min_length=1, max_length=2_000)
    evidence_event_sequences: tuple[int, ...] = Field(min_length=1, max_length=20)
    candidate_files: tuple[str, ...] = Field(min_length=1, max_length=20)
    planned_check_ids: tuple[str, ...] = Field(min_length=1, max_length=20)
    unknowns: tuple[str, ...] = Field(max_length=20)
    public_evidence_only: Literal[True]
    hidden_evidence_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("hypothesis")
    @classmethod
    def normalized_hypothesis(cls, value: str) -> str:
        if value != value.strip() or "\x00" in value:
            raise ValueError("work plan hypothesis must be trimmed public text")
        return value

    @field_validator("candidate_files")
    @classmethod
    def normalized_candidate_files(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(
            safe_relative_path(value, field_name="candidate file") for value in values
        )
        if normalized != values or len(set(values)) != len(values):
            raise ValueError("work plan candidate files differ")
        return values

    @field_validator("evidence_event_sequences")
    @classmethod
    def ordered_sequences(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if values != tuple(sorted(set(values))) or any(value < 1 for value in values):
            raise ValueError("work plan evidence sequences must be unique and ordered")
        return values

    @field_validator("unknowns")
    @classmethod
    def bounded_unknowns(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(
            not value.strip() or value != value.strip() or len(value) > 1_000 for value in values
        ):
            raise ValueError("work plan unknowns must be bounded trimmed text")
        return values

    @model_validator(mode="after")
    def validate_hash(self) -> Self:
        if len(set(self.planned_check_ids)) != len(self.planned_check_ids):
            raise ValueError("work plan check IDs repeat")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("work plan content hash differs")
        return self


class WorkflowDecision(BaseModel):
    """One provider-free projection of the next bounded workflow action."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-workflow-decision-v1"]
    runtime_policy_version: Literal["lean-harness-v9", "lean-harness-v10"]
    policy_version: Literal[
        "bounded-correction-review-repair-v1",
        "public-evidence-plan-gate-v1",
    ]
    target: WorkflowTarget
    current_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expected_check_id: str | None
    allowed_tool_names: tuple[str, ...]
    information_actions_in_episode: int = Field(ge=0, le=3)
    fresh_current_read: bool
    corrective_mutations_for_check: int = Field(ge=0, le=3)
    review_corrections_used: int = Field(ge=0, le=1)
    pre_mutation_actions_used: int = Field(ge=0, le=10)
    plan_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    shared_recovery_used: bool
    shared_recovery_remaining: int = Field(ge=0, le=1)
    terminal_reason: (
        Literal[
            "correction_attempt_limit",
            "pre_mutation_evidence_exhausted",
        ]
        | None
    )
    configured_max_output_tokens: int = Field(ge=1)
    effective_max_output_tokens: int = Field(ge=1)
    reasoning_effort: Literal["low", "medium"]
    parallel_tool_calls: Literal[False]
    one_tool_call_per_response: Literal[True]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        if len(set(self.allowed_tool_names)) != len(self.allowed_tool_names):
            raise ValueError("workflow tool names repeat")
        if self.target == "terminal":
            if self.allowed_tool_names or self.terminal_reason is None:
                raise ValueError("workflow terminal surface differs")
        elif self.terminal_reason is not None or not self.allowed_tool_names:
            raise ValueError("active workflow decision lacks tools")
        if self.target == "visible-check" and (
            self.allowed_tool_names != ("run_check",) or self.expected_check_id is None
        ):
            raise ValueError("workflow visible-check binding differs")
        if self.target == "corrective-mutation" and self.allowed_tool_names != (
            "apply_structured_edit",
        ):
            raise ValueError("workflow corrective mutation surface differs")
        if self.target == "diff-review" and self.allowed_tool_names != ("get_diff",):
            raise ValueError("workflow diff-review surface differs")
        if self.target == "record-work-plan" and self.allowed_tool_names != ("record_work_plan",):
            raise ValueError("workflow plan-recording surface differs")
        if self.effective_max_output_tokens > self.configured_max_output_tokens:
            raise ValueError("workflow output ceiling exceeds the configured limit")
        if self.shared_recovery_remaining != (0 if self.shared_recovery_used else 1):
            raise ValueError("workflow shared recovery accounting differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("workflow decision hash differs")
        return self


class WorkflowToolSurface(BaseModel):
    """Exact request tool schemas selected by one workflow decision."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-workflow-tool-surface-v1"]
    decision_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_tool_names: tuple[str, ...]
    expected_check_id: str | None
    selected_tool_schemas: tuple[dict[str, Any], ...]
    parallel_tool_calls: Literal[False]
    one_tool_call_per_response: Literal[True]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_surface(self) -> Self:
        names = tuple(schema.get("name") for schema in self.selected_tool_schemas)
        if names != self.selected_tool_names or len(set(names)) != len(names):
            raise ValueError("workflow selected schemas differ")
        if self.selected_tool_schema_hash != sha256_json(list(self.selected_tool_schemas)):
            raise ValueError("workflow selected schema hash differs")
        if self.expected_check_id is not None:
            run_check = next(
                (
                    schema
                    for schema in self.selected_tool_schemas
                    if schema.get("name") == "run_check"
                ),
                None,
            )
            enum = (
                run_check.get("parameters", {})
                .get("properties", {})
                .get("check_id", {})
                .get("enum")
                if isinstance(run_check, dict)
                else None
            )
            if enum != [self.expected_check_id]:
                raise ValueError("workflow run_check schema is not bound")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("workflow surface content hash differs")
        return self


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


def project_public_task_spec(task: PublicTask) -> PublicTaskSpec:
    if type(task) is not PublicTask:
        raise TypeError("public task spec requires an exact PublicTask")
    body = {
        "schema_version": PUBLIC_TASK_SPEC_SCHEMA,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": sha256_json(task.model_dump(mode="json")),
        "issue": task.issue.model_dump(mode="python"),
        "allowed_paths": tuple(task.constraints.allowed_paths),
        "forbidden_paths": tuple(task.constraints.forbidden_paths),
        "max_changed_files": task.constraints.max_changed_files,
        "max_diff_lines": task.constraints.max_diff_lines,
        "dependency_changes_allowed": task.constraints.dependency_changes_allowed,
        "public_api_changes_allowed": task.constraints.public_api_changes_allowed,
        "visible_check_ids": tuple(check.id for check in task.visible_checks),
        "source_public_task_only": True,
        "hidden_acceptance_used": False,
        "private_spec_used": False,
        "reference_patch_used": False,
    }
    if not body["visible_check_ids"]:
        raise ContractError("public task spec requires registered visible checks")
    return _hashed(PublicTaskSpec, body)


def _path_allowed(task: PublicTask, path: str) -> bool:
    return any(
        fnmatch.fnmatch(path, pattern) for pattern in task.constraints.allowed_paths
    ) and not any(fnmatch.fnmatch(path, pattern) for pattern in task.constraints.forbidden_paths)


def validate_record_work_plan(
    *,
    run_id: str,
    task: PublicTask,
    worktree_diff_hash: str,
    events: tuple[RunEvent, ...] | list[RunEvent],
    read_paths_by_sequence: dict[int, str],
    arguments: dict[str, Any],
) -> RecordedWorkPlan:
    """Validate a model plan against public current-run/current-diff evidence."""

    if type(task) is not PublicTask or type(arguments) is not dict:
        raise TypeError("record_work_plan requires exact public inputs")
    required = {
        "reproduction_status",
        "hypothesis",
        "evidence_event_sequences",
        "candidate_files",
        "planned_check_ids",
        "unknowns",
    }
    if set(arguments) != required:
        raise ContractError("record_work_plan arguments differ")
    event_list = tuple(events)
    if any(type(event) is not RunEvent or event.run_id != run_id for event in event_list):
        raise ContractError("record_work_plan event run binding differs")
    sequences = arguments.get("evidence_event_sequences")
    candidate_files = arguments.get("candidate_files")
    planned_checks = arguments.get("planned_check_ids")
    unknowns = arguments.get("unknowns")
    if (
        type(sequences) is not list
        or type(candidate_files) is not list
        or type(planned_checks) is not list
        or type(unknowns) is not list
    ):
        raise ContractError("record_work_plan collection shape differs")
    by_sequence = {event.sequence: event for event in event_list}
    cited: list[RunEvent] = []
    for sequence in sequences:
        if type(sequence) is not int or sequence not in by_sequence:
            raise ContractError("record_work_plan cites another or missing run event")
        event = by_sequence[sequence]
        if (
            event.type != EventType.TOOL_SUCCEEDED
            or event.payload.get("tool") not in {"read_file", "run_check"}
            or event.payload.get("worktree_diff_hash") != worktree_diff_hash
        ):
            raise ContractError("record_work_plan cites stale or non-public evidence")
        cited.append(event)
    if not cited:
        raise ContractError("record_work_plan requires public evidence")

    current_reads = {
        path
        for sequence, path in read_paths_by_sequence.items()
        if sequence in by_sequence
        and by_sequence[sequence].type == EventType.TOOL_SUCCEEDED
        and by_sequence[sequence].payload.get("tool") == "read_file"
        and by_sequence[sequence].payload.get("worktree_diff_hash") == worktree_diff_hash
    }
    normalized_candidates: list[str] = []
    for raw_path in candidate_files:
        if type(raw_path) is not str:
            raise ContractError("record_work_plan candidate file must be text")
        path = safe_relative_path(raw_path, field_name="candidate file")
        if not _path_allowed(task, path) or path not in current_reads:
            raise ContractError("record_work_plan candidate file is unread or outside scope")
        normalized_candidates.append(path)
    expected_checks = [check.id for check in task.visible_checks]
    if planned_checks != expected_checks:
        raise ContractError("record_work_plan visible-check order differs")

    status = arguments.get("reproduction_status")
    cited_reads = [event for event in cited if event.payload.get("tool") == "read_file"]
    cited_checks = [event for event in cited if event.payload.get("tool") == "run_check"]
    if status == "confirmed_failure":
        if not any(event.payload.get("passed") is False for event in cited_checks):
            raise ContractError("confirmed_failure requires a failed current-diff check")
    elif status == "not_reproduced":
        if not any(event.payload.get("passed") is True for event in cited_checks):
            raise ContractError("not_reproduced requires a completed passing public check")
    elif status == "static_evidence":
        if not cited_reads:
            raise ContractError("static_evidence requires a current source read")
    else:
        raise ContractError("record_work_plan reproduction status differs")

    task_hash = sha256_json(task.model_dump(mode="json"))
    body = {
        "schema_version": WORK_PLAN_SCHEMA,
        "run_id": run_id,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": task_hash,
        "worktree_diff_hash": worktree_diff_hash,
        "reproduction_status": status,
        "hypothesis": arguments.get("hypothesis"),
        "evidence_event_sequences": tuple(sequences),
        "candidate_files": tuple(normalized_candidates),
        "planned_check_ids": tuple(planned_checks),
        "unknowns": tuple(unknowns),
        "public_evidence_only": True,
        "hidden_evidence_used": False,
    }
    try:
        return _hashed(RecordedWorkPlan, body)
    except ValueError as exc:
        raise ContractError("record_work_plan failed its public schema") from exc


def _shared_recovery_used(events: tuple[RunEvent, ...]) -> bool:
    recoveries = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == PROTOCOL_RECOVERY_POLICY
        and event.payload.get("reason_code") in _PROTOCOL_REASON_CODES
    ]
    if len(recoveries) > 1:
        raise ContractError("shared model-action recovery was consumed more than once")
    return bool(recoveries)


def _current_check_outcomes(
    task: PublicTask,
    evidence: EvidenceState,
    events: tuple[RunEvent, ...],
) -> dict[str, RunEvent]:
    check_ids = {check.id for check in task.visible_checks}
    mutation_sequence = evidence.mutation_event_sequence or 0
    outcomes: dict[str, RunEvent] = {}
    for event in events:
        if (
            event.sequence > mutation_sequence
            and event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "run_check"
            and event.payload.get("check_id") in check_ids
            and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
            and event.payload.get("passed") in {True, False}
        ):
            outcomes[str(event.payload["check_id"])] = event
    return outcomes


def _correction_mutations_by_check(events: tuple[RunEvent, ...]) -> Counter[str]:
    counts: Counter[str] = Counter()
    latest_failed: str | None = None
    for event in events:
        if (
            event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "run_check"
            and event.payload.get("passed") is False
            and isinstance(event.payload.get("check_id"), str)
        ):
            latest_failed = str(event.payload["check_id"])
        elif event.type == EventType.PATCH_APPLIED:
            if latest_failed is not None:
                counts[latest_failed] += 1
            latest_failed = None
    return counts


def _review_corrections(events: tuple[RunEvent, ...]) -> int:
    pending_review = False
    count = 0
    for event in events:
        if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "get_diff":
            pending_review = True
        elif event.type == EventType.PATCH_APPLIED:
            if pending_review:
                count += 1
            pending_review = False
    return count


def _latest_plan(
    *,
    task: PublicTask,
    evidence: EvidenceState,
    events: tuple[RunEvent, ...],
) -> RunEvent | None:
    task_hash = sha256_json(task.model_dump(mode="json"))
    plans = [
        event
        for event in events
        if event.type.value == "PlanRecorded"
        and event.payload.get("schema_version") == PLAN_RECORDED_EVENT_SCHEMA
        and event.payload.get("task_id") == task.task_id
        and event.payload.get("task_version") == task.task_version
        and event.payload.get("public_task_hash") == task_hash
    ]
    direct = [
        event
        for event in plans
        if event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
    ]
    linked_patch = next(
        (
            event
            for event in reversed(events)
            if event.type == EventType.PATCH_APPLIED
            and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
            and isinstance(event.payload.get("plan_hash"), str)
        ),
        None,
    )
    active = direct
    if not active and linked_patch is not None:
        active = [
            event
            for event in plans
            if event.payload.get("plan_hash") == linked_patch.payload.get("plan_hash")
        ]
    if len(active) > 1 and len({event.payload.get("plan_hash") for event in active}) > 1:
        raise ContractError("current-diff work plans conflict")
    return active[-1] if active else None


def _decision(
    *,
    runtime: Literal["lean-harness-v9", "lean-harness-v10"],
    target: WorkflowTarget,
    evidence: EvidenceState,
    expected_check_id: str | None,
    allowed: tuple[str, ...],
    info_count: int,
    fresh_read: bool,
    corrective_count: int,
    review_count: int,
    pre_mutation_count: int,
    plan_hash: str | None,
    recovery_used: bool,
    terminal_reason: Literal["correction_attempt_limit", "pre_mutation_evidence_exhausted"] | None,
    configured_max_output_tokens: int,
) -> WorkflowDecision:
    ceilings = {
        "phase-policy": configured_max_output_tokens,
        "visible-check": 4_096,
        "correction-investigation": 4_096,
        "corrective-mutation": 12_288,
        "diff-review": 4_096,
        "review-decision": 8_192,
        "pre-mutation-exploration": 4_096,
        "record-work-plan": 8_192,
        "plan-implementation": 12_288,
        "terminal": 1,
    }
    reasoning = (
        "medium"
        if target
        in {
            "phase-policy",
            "corrective-mutation",
            "record-work-plan",
            "plan-implementation",
            "review-decision",
        }
        else "low"
    )
    body = {
        "schema_version": WORKFLOW_DECISION_SCHEMA,
        "runtime_policy_version": runtime,
        "policy_version": WORKFLOW_POLICY_V10
        if runtime == "lean-harness-v10"
        else WORKFLOW_POLICY_V9,
        "target": target,
        "current_diff_hash": evidence.worktree_diff_hash,
        "expected_check_id": expected_check_id,
        "allowed_tool_names": allowed,
        "information_actions_in_episode": min(info_count, 3),
        "fresh_current_read": fresh_read,
        "corrective_mutations_for_check": min(corrective_count, 3),
        "review_corrections_used": min(review_count, 1),
        "pre_mutation_actions_used": min(pre_mutation_count, 10),
        "plan_hash": plan_hash,
        "shared_recovery_used": recovery_used,
        "shared_recovery_remaining": 0 if recovery_used else 1,
        "terminal_reason": terminal_reason,
        "configured_max_output_tokens": configured_max_output_tokens,
        "effective_max_output_tokens": min(configured_max_output_tokens, ceilings[target]),
        "reasoning_effort": reasoning,
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "provider_calls_authorized": False,
    }
    return _hashed(WorkflowDecision, body)


def project_workflow_successor(
    *,
    runtime_policy_version: Literal["lean-harness-v9", "lean-harness-v10"],
    task: PublicTask,
    evidence: EvidenceState,
    events: tuple[RunEvent, ...] | list[RunEvent],
    available_tool_names: tuple[str, ...],
    configured_max_output_tokens: int,
) -> WorkflowDecision:
    """Project V9 correction/review or V10 pre-mutation plan gating."""

    if runtime_policy_version not in {"lean-harness-v9", "lean-harness-v10"}:
        raise ContractError("unsupported workflow successor runtime")
    if type(task) is not PublicTask or type(evidence) is not EvidenceState:
        raise TypeError("workflow successor requires exact public evidence")
    event_tuple = tuple(events)
    if any(type(event) is not RunEvent for event in event_tuple):
        raise TypeError("workflow successor events must be exact RunEvent values")
    if len(set(available_tool_names)) != len(available_tool_names):
        raise ContractError("workflow successor available tools repeat")
    check_order = tuple(check.id for check in task.visible_checks)
    if not check_order:
        raise ContractError("workflow successor requires public visible checks")
    recovery_used = _shared_recovery_used(event_tuple)
    review_count = _review_corrections(event_tuple)
    if review_count > 1:
        raise ContractError("review correction limit was bypassed")

    plan_event = _latest_plan(task=task, evidence=evidence, events=event_tuple)
    plan_hash = str(plan_event.payload["plan_hash"]) if plan_event else None
    pre_mutation_calls = [
        event
        for event in event_tuple
        if event.type == EventType.TOOL_CALLED
        and event.payload.get("tool") in {"search_files", "read_file", "run_check"}
        and not any(
            mutation.type == EventType.PATCH_APPLIED and mutation.sequence < event.sequence
            for mutation in event_tuple
        )
    ]
    pre_mutation_count = len(pre_mutation_calls)

    if (
        runtime_policy_version == "lean-harness-v10"
        and not evidence.mutation_present
        and plan_event is None
    ):
        current_results = [
            event
            for event in event_tuple
            if event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") in {"read_file", "run_check"}
            and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
        ]
        if pre_mutation_count >= 10:
            if current_results:
                return _decision(
                    runtime=runtime_policy_version,
                    target="record-work-plan",
                    evidence=evidence,
                    expected_check_id=None,
                    allowed=("record_work_plan",),
                    info_count=0,
                    fresh_read=False,
                    corrective_count=0,
                    review_count=review_count,
                    pre_mutation_count=pre_mutation_count,
                    plan_hash=None,
                    recovery_used=recovery_used,
                    terminal_reason=None,
                    configured_max_output_tokens=configured_max_output_tokens,
                )
            return _decision(
                runtime=runtime_policy_version,
                target="terminal",
                evidence=evidence,
                expected_check_id=None,
                allowed=(),
                info_count=0,
                fresh_read=False,
                corrective_count=0,
                review_count=review_count,
                pre_mutation_count=pre_mutation_count,
                plan_hash=None,
                recovery_used=recovery_used,
                terminal_reason="pre_mutation_evidence_exhausted",
                configured_max_output_tokens=configured_max_output_tokens,
            )
        completed_check_ids = {
            str(event.payload["check_id"])
            for event in current_results
            if event.payload.get("tool") == "run_check"
            and isinstance(event.payload.get("check_id"), str)
        }
        expected = next((item for item in check_order if item not in completed_check_ids), None)
        allowed = ["search_files", "read_file"]
        if expected is not None:
            allowed.append("run_check")
        if current_results:
            allowed.append("record_work_plan")
        return _decision(
            runtime=runtime_policy_version,
            target="pre-mutation-exploration",
            evidence=evidence,
            expected_check_id=expected,
            allowed=tuple(allowed),
            info_count=0,
            fresh_read=False,
            corrective_count=0,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            plan_hash=None,
            recovery_used=recovery_used,
            terminal_reason=None,
            configured_max_output_tokens=configured_max_output_tokens,
        )

    if (
        runtime_policy_version == "lean-harness-v10"
        and not evidence.mutation_present
        and plan_event is not None
    ):
        allowed = (
            ("apply_structured_edit",)
            if pre_mutation_count >= 10
            else ("search_files", "read_file", "apply_structured_edit")
        )
        return _decision(
            runtime=runtime_policy_version,
            target="plan-implementation",
            evidence=evidence,
            expected_check_id=None,
            allowed=allowed,
            info_count=0,
            fresh_read=True,
            corrective_count=0,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            plan_hash=plan_hash,
            recovery_used=recovery_used,
            terminal_reason=None,
            configured_max_output_tokens=configured_max_output_tokens,
        )

    if not evidence.mutation_present or evidence.worktree_diff_hash == _EMPTY_DIFF_HASH:
        allowed = tuple(
            name for name in available_tool_names if name in evidence.allowed_next_actions
        )
        if not allowed:
            raise ContractError("workflow phase policy leaves no tool")
        return _decision(
            runtime=runtime_policy_version,
            target="phase-policy",
            evidence=evidence,
            expected_check_id=None,
            allowed=allowed,
            info_count=0,
            fresh_read=False,
            corrective_count=0,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            plan_hash=plan_hash,
            recovery_used=recovery_used,
            terminal_reason=None,
            configured_max_output_tokens=configured_max_output_tokens,
        )

    outcomes = _current_check_outcomes(task, evidence, event_tuple)
    expected_check = next(
        (check_id for check_id in check_order if check_id not in evidence.completed_checks),
        None,
    )
    if expected_check is not None:
        outcome = outcomes.get(expected_check)
        if outcome is None:
            return _decision(
                runtime=runtime_policy_version,
                target="visible-check",
                evidence=evidence,
                expected_check_id=expected_check,
                allowed=("run_check",),
                info_count=0,
                fresh_read=False,
                corrective_count=_correction_mutations_by_check(event_tuple)[expected_check],
                review_count=review_count,
                pre_mutation_count=pre_mutation_count,
                plan_hash=plan_hash,
                recovery_used=recovery_used,
                terminal_reason=None,
                configured_max_output_tokens=configured_max_output_tokens,
            )
        if outcome.payload.get("passed") is not False:
            raise ContractError("workflow current check outcome differs")
        correction_count = _correction_mutations_by_check(event_tuple)[expected_check]
        if correction_count >= 3:
            return _decision(
                runtime=runtime_policy_version,
                target="terminal",
                evidence=evidence,
                expected_check_id=expected_check,
                allowed=(),
                info_count=0,
                fresh_read=False,
                corrective_count=correction_count,
                review_count=review_count,
                pre_mutation_count=pre_mutation_count,
                plan_hash=plan_hash,
                recovery_used=recovery_used,
                terminal_reason="correction_attempt_limit",
                configured_max_output_tokens=configured_max_output_tokens,
            )
        episode_events = [event for event in event_tuple if event.sequence > outcome.sequence]
        latest_rejection = next(
            (
                event
                for event in reversed(episode_events)
                if event.type == EventType.TOOL_FAILED
                and event.payload.get("tool") in _MUTATION_TOOLS
            ),
            None,
        )
        current_reads = [
            event
            for event in episode_events
            if event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "read_file"
            and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
            and (latest_rejection is None or event.sequence > latest_rejection.sequence)
        ]
        info_events = [
            event
            for event in episode_events
            if event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") in _INFO_TOOLS
            and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
        ]
        info_count = len(info_events)
        fresh_read = bool(current_reads)
        if latest_rejection is not None and not fresh_read:
            allowed = ("read_file",)
            target: WorkflowTarget = "correction-investigation"
        elif info_count >= 3:
            if not fresh_read:
                raise ContractError("workflow third investigation lacked a current read")
            allowed = ("apply_structured_edit",)
            target = "corrective-mutation"
        elif info_count == 2 and not fresh_read:
            allowed = ("read_file",)
            target = "correction-investigation"
        elif fresh_read:
            allowed = ("search_files", "read_file", "apply_structured_edit")
            target = "correction-investigation"
        else:
            allowed = ("search_files", "read_file")
            target = "correction-investigation"
        return _decision(
            runtime=runtime_policy_version,
            target=target,
            evidence=evidence,
            expected_check_id=expected_check,
            allowed=allowed,
            info_count=info_count,
            fresh_read=fresh_read,
            corrective_count=correction_count,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            plan_hash=plan_hash,
            recovery_used=recovery_used,
            terminal_reason=None,
            configured_max_output_tokens=configured_max_output_tokens,
        )

    if evidence.review_event_sequence is None or not evidence.review_presented_to_model:
        return _decision(
            runtime=runtime_policy_version,
            target="diff-review",
            evidence=evidence,
            expected_check_id=None,
            allowed=("get_diff",),
            info_count=0,
            fresh_read=False,
            corrective_count=0,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            plan_hash=plan_hash,
            recovery_used=recovery_used,
            terminal_reason=None,
            configured_max_output_tokens=configured_max_output_tokens,
        )
    return _decision(
        runtime=runtime_policy_version,
        target="review-decision",
        evidence=evidence,
        expected_check_id=None,
        allowed=("finish_task", "read_file", "search_files", "apply_structured_edit"),
        info_count=0,
        fresh_read=False,
        corrective_count=0,
        review_count=review_count,
        pre_mutation_count=pre_mutation_count,
        plan_hash=plan_hash,
        recovery_used=recovery_used,
        terminal_reason=None,
        configured_max_output_tokens=configured_max_output_tokens,
    )


def project_workflow_tool_surface(
    *,
    decision: WorkflowDecision,
    source_tool_schemas: tuple[dict[str, Any], ...],
) -> WorkflowToolSurface:
    if type(decision) is not WorkflowDecision:
        raise TypeError("workflow surface requires an exact decision")
    source = {schema.get("name"): schema for schema in source_tool_schemas}
    if len(source) != len(source_tool_schemas) or any(type(name) is not str for name in source):
        raise ContractError("workflow source schemas differ")
    missing = [name for name in decision.allowed_tool_names if name not in source]
    if missing:
        raise ContractError("workflow target tool is unavailable: " + ", ".join(missing))
    selected = tuple(copy.deepcopy(source[name]) for name in decision.allowed_tool_names)
    if decision.expected_check_id is not None and "run_check" in decision.allowed_tool_names:
        index = decision.allowed_tool_names.index("run_check")
        check_id = selected[index]["parameters"]["properties"]["check_id"]
        check_id["enum"] = [decision.expected_check_id]
        check_id["description"] = (
            "This request is bound to the next public check: " + decision.expected_check_id
        )
    body = {
        "schema_version": WORKFLOW_SURFACE_SCHEMA,
        "decision_hash": decision.content_hash,
        "source_tool_schema_hash": sha256_json(list(source_tool_schemas)),
        "selected_tool_schema_hash": sha256_json(list(selected)),
        "selected_tool_names": decision.allowed_tool_names,
        "expected_check_id": (
            decision.expected_check_id if "run_check" in decision.allowed_tool_names else None
        ),
        "selected_tool_schemas": selected,
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "provider_calls_authorized": False,
    }
    return _hashed(WorkflowToolSurface, body)


def workflow_instruction(
    decision: WorkflowDecision,
    *,
    task_spec: PublicTaskSpec | None = None,
) -> dict[str, Any]:
    instructions = {
        "phase-policy": "Use one phase-filtered public tool action.",
        "visible-check": "Run exactly the bound public check and inspect its behavior result.",
        "correction-investigation": (
            "Investigate the failed check within the bounded surface. A current read is required "
            "before the next structured edit."
        ),
        "corrective-mutation": (
            "Apply one smallest structured correction from the fresh current read."
        ),
        "diff-review": "Obtain and review the complete current diff.",
        "review-decision": (
            "Either submit the checked diff or make the single permitted review correction."
        ),
        "pre-mutation-exploration": (
            "Collect public reproduction or current-source evidence, then record a "
            "bounded work plan."
        ),
        "record-work-plan": (
            "Record the work plan now using only cited public current-diff evidence."
        ),
        "plan-implementation": (
            "Follow the recorded plan and make one smallest structured mutation."
        ),
        "terminal": "No provider request is authorized for this terminal state.",
    }
    body = {
        "schema_version": "lean-workflow-instruction-v1",
        "policy_version": decision.policy_version,
        "decision_hash": decision.content_hash,
        "target": decision.target,
        "expected_check_id": decision.expected_check_id,
        "available_tool_names": list(decision.allowed_tool_names),
        "shared_recovery_used": decision.shared_recovery_used,
        "instruction": instructions[decision.target],
        "public_task_spec": task_spec.model_dump(mode="json") if task_spec else None,
        "provider_calls_authorized": False,
    }
    return {**body, "content_hash": sha256_json(body)}
