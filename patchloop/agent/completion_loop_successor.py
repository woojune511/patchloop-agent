"""Public-only, offline successor policy for completion after a mutation.

The consumed Lean V7 runtime moved directly from a failed visible check to a
mutation-only tool surface.  On the harder AnyIO task that removed the
``read_file`` refresh which the phase evidence still allowed, so the model
repeated edits against stale or poorly understood source.  This module keeps
the immutable V7 behavior intact and defines an opt-in successor projection:

* run registered checks in public task order, one per response;
* after a failed check, refresh one current file before another mutation;
* use the structured edit path for correction when it is available;
* expose only the latest edit correction body once; and
* use small response ceilings for mechanical check/review/submission turns.

All functions are pure.  They perform no workspace, state, Docker, evaluator,
provider, or network action and grant no runtime authority.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.phases import EvidenceState
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json, sha256_text

COMPLETION_LOOP_SCHEMA = "completion-loop-successor-decision-v1"
COMPLETION_LOOP_POLICY = "ordered-check-refresh-structured-correction-v1"
COMPLETION_TOOL_SURFACE_SCHEMA = "completion-loop-successor-tool-surface-v1"
CORRECTION_CONTEXT_SCHEMA = "current-edit-correction-context-v1"
CORRECTION_CONTEXT_POLICY = "latest-public-edit-correction-once-v1"
PROVIDER_TERMINAL_ATTRIBUTION_SCHEMA = "provider-terminal-attribution-v1"
PROVIDER_TERMINAL_ATTRIBUTION_POLICY = "explicit-terminal-before-accounting-v1"

_EMPTY_DIFF_HASH = sha256_text("")
_MUTATION_TOOLS = frozenset({"apply_patch", "apply_structured_edit"})
_TARGET_CEILINGS = {
    "visible-check": 2_048,
    "correction-inspection": 4_096,
    "corrective-mutation": 8_192,
    "diff-review": 2_048,
    "submission": 2_048,
}

CompletionTarget = Literal[
    "phase-policy",
    "visible-check",
    "correction-inspection",
    "corrective-mutation",
    "diff-review",
    "submission",
]


class CompletionLoopDecision(BaseModel):
    """One state-derived request target with no execution authority."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["completion-loop-successor-decision-v1"]
    policy_version: Literal["ordered-check-refresh-structured-correction-v1"]
    target: CompletionTarget
    current_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mutation_event_sequence: int | None = Field(default=None, ge=1)
    expected_check_id: str | None = None
    completed_check_ids: tuple[str, ...]
    preserve_check_ids: tuple[str, ...]
    latest_failed_check_sequence: int | None = Field(default=None, ge=1)
    latest_correction_read_sequence: int | None = Field(default=None, ge=1)
    latest_edit_failure_sequence: int | None = Field(default=None, ge=1)
    fresh_read_required: bool
    allowed_tool_names: tuple[str, ...]
    configured_max_output_tokens: int = Field(ge=1)
    effective_max_output_tokens: int = Field(ge=1)
    reasoning_effort: Literal["low", "medium"]
    parallel_tool_calls: Literal[False]
    one_tool_call_per_response: Literal[True]
    one_check_per_response: Literal[True]
    public_check_order_enforced: Literal[True]
    upstream_check_gated_by_prior_pass: Literal[True]
    raw_trace_mutated: Literal[False]
    runtime_activation_authorized: Literal[False]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        if len(set(self.allowed_tool_names)) != len(self.allowed_tool_names):
            raise ValueError("completion successor tools repeat")
        if len(set(self.completed_check_ids)) != len(self.completed_check_ids):
            raise ValueError("completion successor completed checks repeat")
        if not set(self.preserve_check_ids).issubset(self.completed_check_ids):
            raise ValueError("completion successor preserves a non-passing check")
        if self.effective_max_output_tokens > self.configured_max_output_tokens:
            raise ValueError("completion successor exceeds configured output ceiling")

        expected_tools: dict[str, tuple[str, ...] | None] = {
            "phase-policy": None,
            "visible-check": ("run_check",),
            "correction-inspection": ("read_file",),
            "corrective-mutation": None,
            "diff-review": ("get_diff",),
            "submission": ("finish_task",),
        }
        exact = expected_tools[self.target]
        if exact is not None and self.allowed_tool_names != exact:
            raise ValueError("completion successor target/tool surface differs")
        if self.target == "corrective-mutation" and (
            len(self.allowed_tool_names) != 1
            or self.allowed_tool_names[0] not in _MUTATION_TOOLS
        ):
            raise ValueError("completion successor correction tool differs")
        if (
            self.target != "phase-policy"
            and self.effective_max_output_tokens > _TARGET_CEILINGS[self.target]
        ):
            raise ValueError("completion successor target ceiling differs")
        if self.target == "visible-check":
            if not self.expected_check_id or self.fresh_read_required:
                raise ValueError("visible-check target lacks one expected check")
        elif self.expected_check_id is not None and self.target not in {
            "correction-inspection",
            "corrective-mutation",
        }:
            raise ValueError("completion successor has an unexpected check binding")
        if self.target == "correction-inspection" and (
            not self.fresh_read_required or self.latest_failed_check_sequence is None
        ):
            raise ValueError("correction inspection lacks failed-check evidence")
        if self.target == "corrective-mutation" and (
            self.fresh_read_required
            or self.latest_failed_check_sequence is None
            or self.latest_correction_read_sequence is None
            or self.latest_correction_read_sequence
            <= self.latest_failed_check_sequence
        ):
            raise ValueError("corrective mutation lacks a fresh post-check read")
        if self.reasoning_effort != (
            "medium" if self.target in {"phase-policy", "corrective-mutation"} else "low"
        ):
            raise ValueError("completion successor reasoning effort differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("completion successor decision hash differs")
        return self


class CompletionToolSurface(BaseModel):
    """Exact request schemas selected by a completion decision."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["completion-loop-successor-tool-surface-v1"]
    decision_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_tool_names: tuple[str, ...]
    expected_check_id: str | None
    tool_schemas: tuple[dict[str, Any], ...]
    parallel_tool_calls: Literal[False]
    one_tool_call_per_response: Literal[True]
    runtime_activation_authorized: Literal[False]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @property
    def selected_tool_schemas(self) -> tuple[dict[str, Any], ...]:
        """Expose the common Lean request-surface interface without copying bytes."""

        return self.tool_schemas

    @model_validator(mode="after")
    def validate_surface(self) -> Self:
        names = tuple(item.get("name") for item in self.tool_schemas)
        if self.selected_tool_names != names or len(set(names)) != len(names):
            raise ValueError("completion successor selected schemas differ")
        if self.selected_tool_schema_hash != sha256_json(list(self.tool_schemas)):
            raise ValueError("completion successor schema hash differs")
        if self.expected_check_id is not None:
            if names != ("run_check",):
                raise ValueError("check binding belongs to a non-check surface")
            check_schema = self.tool_schemas[0]
            check_id = (
                check_schema.get("parameters", {})
                .get("properties", {})
                .get("check_id", {})
            )
            if check_id.get("enum") != [self.expected_check_id]:
                raise ValueError("run_check schema is not bound to one check ID")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("completion successor surface content hash differs")
        return self


class EditCorrectionReference(BaseModel):
    """Identity retained where a full correction body was removed."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    event_sequence: int | None = Field(default=None, ge=1)
    tool: str | None
    correction_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    occurrence_count: int = Field(ge=1)
    selected_current: bool


class CurrentEditCorrectionContextEvidence(BaseModel):
    """Audit evidence for a request-only latest-correction projection."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["current-edit-correction-context-v1"]
    policy_version: Literal["latest-public-edit-correction-once-v1"]
    source_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_context_bytes: int = Field(ge=1)
    projected_context_bytes: int = Field(ge=1)
    selected_event_sequence: int | None = Field(default=None, ge=1)
    selected_correction_hash: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    source_full_correction_occurrences: int = Field(ge=0)
    projected_full_correction_occurrences: int = Field(ge=0, le=1)
    removed_full_correction_occurrences: int = Field(ge=0)
    references: tuple[EditCorrectionReference, ...]
    latest_correction_only: Literal[True]
    public_agent_visible_context_only: Literal[True]
    raw_trace_mutated: Literal[False]
    state_mutation_authorized: Literal[False]
    runtime_activation_authorized: Literal[False]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        if self.removed_full_correction_occurrences != (
            self.source_full_correction_occurrences
            - self.projected_full_correction_occurrences
        ):
            raise ValueError("edit correction removal count differs")
        if (self.selected_correction_hash is None) != (self.selected_event_sequence is None):
            raise ValueError("edit correction selected identity is partial")
        expected_projected = 1 if self.selected_correction_hash is not None else 0
        if self.projected_full_correction_occurrences != expected_projected:
            raise ValueError("edit correction projected occurrence count differs")
        if sum(item.occurrence_count for item in self.references) != (
            self.source_full_correction_occurrences
        ):
            raise ValueError("edit correction source occurrence count differs")
        selected = [item for item in self.references if item.selected_current]
        if self.selected_correction_hash is None:
            if selected or self.references:
                raise ValueError("empty edit correction projection has references")
        elif len(selected) != 1 or selected[0].correction_hash != self.selected_correction_hash:
            raise ValueError("edit correction selected reference differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("edit correction projection content hash differs")
        return self


class ProviderTerminalAttribution(BaseModel):
    """Fail-closed attribution which does not discard accounting mismatch."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["provider-terminal-attribution-v1"]
    policy_version: Literal["explicit-terminal-before-accounting-v1"]
    response_status: str | None
    response_incomplete_reason: str | None
    usage_present: bool
    input_token_count_match: bool
    primary_error_code: Literal["incomplete_response", "input_token_count_mismatch"] | None
    accounting_mismatch_preserved: bool
    historical_adapter_precedence_differs: bool
    fail_closed: Literal[True]
    runtime_activation_authorized: Literal[False]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_attribution(self) -> Self:
        explicit_incomplete = bool(
            self.response_status not in {None, "completed"}
            or self.response_incomplete_reason
        )
        expected = (
            "incomplete_response"
            if explicit_incomplete
            else "input_token_count_mismatch"
            if not self.input_token_count_match
            else None
        )
        if self.primary_error_code != expected:
            raise ValueError("provider terminal primary attribution differs")
        if self.accounting_mismatch_preserved is self.input_token_count_match:
            raise ValueError("provider terminal accounting attribution differs")
        if self.historical_adapter_precedence_differs is not bool(
            explicit_incomplete and not self.input_token_count_match
        ):
            raise ValueError("provider terminal precedence comparison differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("provider terminal attribution hash differs")
        return self


@dataclass(frozen=True)
class ProjectedEditCorrectionContext:
    rendered: str
    content_hash: str
    evidence: CurrentEditCorrectionContextEvidence


def _hashed(model_type: type[BaseModel], body: dict[str, Any]) -> Any:
    return model_type.model_validate({**body, "content_hash": sha256_json(body)})


def _event_check_outcomes(
    task: PublicTask,
    events: tuple[RunEvent, ...],
    evidence: EvidenceState,
) -> dict[str, RunEvent]:
    required = {check.id for check in task.visible_checks}
    mutation_sequence = evidence.mutation_event_sequence or 0
    outcomes: dict[str, RunEvent] = {}
    for event in events:
        if (
            event.sequence > mutation_sequence
            and event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "run_check"
            and event.payload.get("check_id") in required
            and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
        ):
            outcomes[str(event.payload["check_id"])] = event
    return outcomes


def _latest_current_read(
    events: tuple[RunEvent, ...],
    *,
    after_sequence: int,
    worktree_diff_hash: str,
) -> RunEvent | None:
    return next(
        (
            event
            for event in reversed(events)
            if event.sequence > after_sequence
            and event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "read_file"
            and event.payload.get("worktree_diff_hash") == worktree_diff_hash
        ),
        None,
    )


def _latest_edit_failure(
    events: tuple[RunEvent, ...],
    *,
    after_sequence: int,
) -> RunEvent | None:
    return next(
        (
            event
            for event in reversed(events)
            if event.sequence > after_sequence
            and event.type == EventType.TOOL_FAILED
            and event.payload.get("tool") in _MUTATION_TOOLS
        ),
        None,
    )


def project_completion_loop_successor(
    *,
    task: PublicTask,
    evidence: EvidenceState,
    events: tuple[RunEvent, ...] | list[RunEvent],
    available_tool_names: tuple[str, ...],
    configured_max_output_tokens: int,
) -> CompletionLoopDecision:
    """Select one bounded next action from public current-diff evidence."""

    if type(task) is not PublicTask or type(evidence) is not EvidenceState:
        raise TypeError("completion successor requires exact public task and phase evidence")
    if type(events) not in {tuple, list} or any(type(event) is not RunEvent for event in events):
        raise TypeError("completion successor events must be exact RunEvent values")
    if type(available_tool_names) is not tuple or any(
        type(name) is not str for name in available_tool_names
    ):
        raise TypeError("completion successor available tools must be an exact tuple")
    if type(configured_max_output_tokens) is not int or configured_max_output_tokens < 1:
        raise TypeError("completion successor output ceiling must be a positive integer")
    if len(set(available_tool_names)) != len(available_tool_names):
        raise ContractError("completion successor available tools repeat")

    event_tuple = tuple(events)
    required = tuple(check.id for check in task.visible_checks)
    if not required:
        raise ContractError("completion successor requires registered public checks")
    if set(evidence.completed_checks) | set(evidence.pending_checks) != set(required):
        raise ContractError("completion successor phase/check evidence differs")

    expected_check: str | None = None
    latest_failed: RunEvent | None = None
    latest_read: RunEvent | None = None
    latest_edit_failure: RunEvent | None = None
    preserve = tuple(check_id for check_id in required if check_id in evidence.completed_checks)

    if not evidence.mutation_present or evidence.worktree_diff_hash == _EMPTY_DIFF_HASH:
        target: CompletionTarget = "phase-policy"
        allowed = tuple(
            name for name in available_tool_names if name in evidence.allowed_next_actions
        )
        if not allowed:
            raise ContractError("completion successor phase policy leaves no tool")
        effective = configured_max_output_tokens
        fresh_read_required = False
    else:
        outcomes = _event_check_outcomes(task, event_tuple, evidence)
        observed_completed = tuple(
            check_id
            for check_id in required
            if check_id in outcomes and outcomes[check_id].payload.get("passed") is True
        )
        if observed_completed != evidence.completed_checks:
            raise ContractError("completion successor current-diff check evidence differs")
        expected_check = next(
            (check_id for check_id in required if check_id not in evidence.completed_checks),
            None,
        )
        if expected_check is not None:
            outcome = outcomes.get(expected_check)
            if outcome is None:
                target = "visible-check"
                allowed = ("run_check",)
                fresh_read_required = False
            elif outcome.payload.get("passed") is not False:
                raise ContractError("completion successor check outcome lacks behavior state")
            else:
                latest_failed = outcome
                latest_read = _latest_current_read(
                    event_tuple,
                    after_sequence=outcome.sequence,
                    worktree_diff_hash=evidence.worktree_diff_hash,
                )
                latest_edit_failure = _latest_edit_failure(
                    event_tuple,
                    after_sequence=(latest_read.sequence if latest_read else outcome.sequence),
                )
                if latest_read is None or latest_edit_failure is not None:
                    target = "correction-inspection"
                    allowed = ("read_file",)
                    fresh_read_required = True
                else:
                    target = "corrective-mutation"
                    correction_tool = (
                        "apply_structured_edit"
                        if "apply_structured_edit" in available_tool_names
                        else "apply_patch"
                    )
                    allowed = (correction_tool,)
                    fresh_read_required = False
        elif evidence.review_event_sequence is None or not evidence.review_presented_to_model:
            target = "diff-review"
            allowed = ("get_diff",)
            fresh_read_required = False
        else:
            target = "submission"
            allowed = ("finish_task",)
            fresh_read_required = False

        missing = [name for name in allowed if name not in available_tool_names]
        if missing:
            raise ContractError(
                "completion successor target tool is unavailable: " + ", ".join(missing)
            )
        effective = min(configured_max_output_tokens, _TARGET_CEILINGS[target])

    body = {
        "schema_version": COMPLETION_LOOP_SCHEMA,
        "policy_version": COMPLETION_LOOP_POLICY,
        "target": target,
        "current_diff_hash": evidence.worktree_diff_hash,
        "mutation_event_sequence": evidence.mutation_event_sequence,
        "expected_check_id": expected_check,
        "completed_check_ids": evidence.completed_checks,
        "preserve_check_ids": preserve,
        "latest_failed_check_sequence": latest_failed.sequence if latest_failed else None,
        "latest_correction_read_sequence": latest_read.sequence if latest_read else None,
        "latest_edit_failure_sequence": (
            latest_edit_failure.sequence if latest_edit_failure else None
        ),
        "fresh_read_required": fresh_read_required,
        "allowed_tool_names": allowed,
        "configured_max_output_tokens": configured_max_output_tokens,
        "effective_max_output_tokens": effective,
        "reasoning_effort": (
            "medium" if target in {"phase-policy", "corrective-mutation"} else "low"
        ),
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "one_check_per_response": True,
        "public_check_order_enforced": True,
        "upstream_check_gated_by_prior_pass": True,
        "raw_trace_mutated": False,
        "runtime_activation_authorized": False,
        "provider_calls_authorized": False,
    }
    return _hashed(CompletionLoopDecision, body)


def project_completion_tool_surface(
    *,
    decision: CompletionLoopDecision,
    source_tool_schemas: tuple[dict[str, Any], ...],
) -> CompletionToolSurface:
    """Bind the ordered check ID and select only the decision's one tool."""

    if type(decision) is not CompletionLoopDecision:
        raise TypeError("completion successor surface requires an exact decision")
    if type(source_tool_schemas) is not tuple or any(
        type(schema) is not dict for schema in source_tool_schemas
    ):
        raise TypeError("completion successor source schemas must be an exact tuple")
    source_names = tuple(schema.get("name") for schema in source_tool_schemas)
    if any(type(name) is not str or not name for name in source_names):
        raise ContractError("completion successor source schema name is invalid")
    if len(set(source_names)) != len(source_names):
        raise ContractError("completion successor source schema names repeat")

    selected = tuple(
        copy.deepcopy(schema)
        for schema in source_tool_schemas
        if schema["name"] in decision.allowed_tool_names
    )
    selected_names = tuple(schema["name"] for schema in selected)
    if selected_names != decision.allowed_tool_names:
        raise ContractError("completion successor source schema order differs")
    if decision.expected_check_id is not None and decision.target == "visible-check":
        check = selected[0]
        try:
            check_id = check["parameters"]["properties"]["check_id"]
        except (KeyError, TypeError) as exc:
            raise ContractError("completion successor run_check schema differs") from exc
        if type(check_id) is not dict:
            raise ContractError("completion successor check_id schema differs")
        check_id["enum"] = [decision.expected_check_id]
        check_id["description"] = (
            "This turn is bound to the next public check in task order: "
            + decision.expected_check_id
        )

    body = {
        "schema_version": COMPLETION_TOOL_SURFACE_SCHEMA,
        "decision_hash": decision.content_hash,
        "source_tool_schema_hash": sha256_json(list(source_tool_schemas)),
        "selected_tool_schema_hash": sha256_json(list(selected)),
        "selected_tool_names": selected_names,
        "expected_check_id": (
            decision.expected_check_id if decision.target == "visible-check" else None
        ),
        "tool_schemas": selected,
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "runtime_activation_authorized": False,
        "provider_calls_authorized": False,
    }
    return _hashed(CompletionToolSurface, body)


def _take_edit_corrections(value: Any) -> list[dict[str, Any]]:
    """Remove full correction bodies recursively and return exact copies."""

    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        correction = value.pop("edit_correction", None)
        if correction is not None:
            if type(correction) is not dict:
                raise ContractError("edit correction body must be an exact object")
            found.append(copy.deepcopy(correction))
        for child in value.values():
            found.extend(_take_edit_corrections(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_take_edit_corrections(child))
    return found


def project_current_edit_correction_context(rendered: str) -> ProjectedEditCorrectionContext:
    """Keep one latest correction body and replace all request duplicates with refs."""

    if type(rendered) is not str or not rendered:
        raise TypeError("edit correction projection requires a nonempty exact string")
    try:
        source = json.loads(rendered)
    except json.JSONDecodeError as exc:
        raise ContractError("edit correction source context must be JSON") from exc
    if type(source) is not dict:
        raise ContractError("edit correction source context must be an object")
    recent = source.get("recent_events")
    if type(recent) is not list:
        raise ContractError("edit correction source lacks recent events")

    projected = copy.deepcopy(source)
    grouped: dict[tuple[int | None, str | None, str], dict[str, Any]] = {}
    order: list[tuple[int | None, str | None, str]] = []
    for event in projected["recent_events"]:
        if type(event) is not dict or type(event.get("payload")) is not dict:
            raise ContractError("edit correction recent-event shape differs")
        sequence = event.get("sequence")
        if type(sequence) is not int or sequence < 1:
            raise ContractError("edit correction recent-event sequence differs")
        payload = event["payload"]
        corrections = _take_edit_corrections(payload)
        if not corrections:
            continue
        hashes = {sha256_json(item) for item in corrections}
        if len(hashes) != 1:
            raise ContractError("one event contains conflicting edit corrections")
        digest = next(iter(hashes))
        key = (sequence, payload.get("tool"), digest)
        grouped[key] = {
            "correction": corrections[0],
            "occurrences": len(corrections),
        }
        order.append(key)
        payload["edit_correction_ref"] = {
            "schema_version": "edit-correction-ref-v1",
            "event_sequence": sequence,
            "correction_hash": digest,
        }

    retry = projected.get("rejected_mutation_retry")
    retry_corrections = _take_edit_corrections(retry) if retry is not None else []
    for correction in retry_corrections:
        digest = sha256_json(correction)
        matching = [key for key in order if key[2] == digest]
        key = matching[-1] if matching else (None, "apply_patch", digest)
        if key not in grouped:
            grouped[key] = {"correction": correction, "occurrences": 0}
            order.append(key)
        grouped[key]["occurrences"] += 1
    if retry_corrections and isinstance(retry, dict):
        digest = sha256_json(retry_corrections[-1])
        retry["edit_correction_ref"] = {
            "schema_version": "edit-correction-ref-v1",
            "event_sequence": next(
                (key[0] for key in reversed(order) if key[2] == digest),
                None,
            ),
            "correction_hash": digest,
        }

    selected_key = max(
        order,
        key=lambda key: (-1 if key[0] is None else key[0], order.index(key)),
        default=None,
    )
    if selected_key is not None:
        selected = grouped[selected_key]
        projected["current_edit_correction"] = {
            "schema_version": "current-edit-correction-v1",
            "source_event_sequence": selected_key[0],
            "tool": selected_key[1],
            "correction_hash": selected_key[2],
            "correction": selected["correction"],
            "instruction": (
                "Use only this latest public current-source correction. Ignore older "
                "correction refs and do not replay stale text."
            ),
        }

    projected_rendered = (
        canonical_json(projected)
        if selected_key is not None
        else rendered
    )
    references = tuple(
        EditCorrectionReference(
            event_sequence=key[0],
            tool=key[1],
            correction_hash=key[2],
            occurrence_count=grouped[key]["occurrences"],
            selected_current=(key == selected_key),
        )
        for key in order
    )
    source_occurrences = sum(item.occurrence_count for item in references)
    projected_occurrences = 1 if selected_key is not None else 0
    body = {
        "schema_version": CORRECTION_CONTEXT_SCHEMA,
        "policy_version": CORRECTION_CONTEXT_POLICY,
        "source_context_hash": sha256_text(rendered),
        "projected_context_hash": sha256_text(projected_rendered),
        "source_context_bytes": len(rendered.encode("utf-8")),
        "projected_context_bytes": len(projected_rendered.encode("utf-8")),
        "selected_event_sequence": selected_key[0] if selected_key else None,
        "selected_correction_hash": selected_key[2] if selected_key else None,
        "source_full_correction_occurrences": source_occurrences,
        "projected_full_correction_occurrences": projected_occurrences,
        "removed_full_correction_occurrences": source_occurrences - projected_occurrences,
        "references": tuple(item.model_dump(mode="python") for item in references),
        "latest_correction_only": True,
        "public_agent_visible_context_only": True,
        "raw_trace_mutated": False,
        "state_mutation_authorized": False,
        "runtime_activation_authorized": False,
        "provider_calls_authorized": False,
    }
    evidence = _hashed(CurrentEditCorrectionContextEvidence, body)
    return ProjectedEditCorrectionContext(
        rendered=projected_rendered,
        content_hash=sha256_text(projected_rendered),
        evidence=evidence,
    )


def project_provider_terminal_attribution(
    *,
    response_status: str | None,
    response_incomplete_reason: str | None,
    usage_present: bool,
    input_token_count_match: bool,
) -> ProviderTerminalAttribution:
    """Prefer explicit provider terminal state while retaining usage mismatch."""

    if response_status is not None and type(response_status) is not str:
        raise TypeError("provider response status must be a string or null")
    if response_incomplete_reason is not None and type(response_incomplete_reason) is not str:
        raise TypeError("provider incomplete reason must be a string or null")
    if type(usage_present) is not bool or type(input_token_count_match) is not bool:
        raise TypeError("provider terminal accounting fields must be exact booleans")
    explicit_incomplete = bool(
        response_status not in {None, "completed"} or response_incomplete_reason
    )
    primary = (
        "incomplete_response"
        if explicit_incomplete
        else "input_token_count_mismatch"
        if not input_token_count_match
        else None
    )
    body = {
        "schema_version": PROVIDER_TERMINAL_ATTRIBUTION_SCHEMA,
        "policy_version": PROVIDER_TERMINAL_ATTRIBUTION_POLICY,
        "response_status": response_status,
        "response_incomplete_reason": response_incomplete_reason,
        "usage_present": usage_present,
        "input_token_count_match": input_token_count_match,
        "primary_error_code": primary,
        "accounting_mismatch_preserved": not input_token_count_match,
        "historical_adapter_precedence_differs": bool(
            explicit_incomplete and not input_token_count_match
        ),
        "fail_closed": True,
        "runtime_activation_authorized": False,
        "provider_calls_authorized": False,
    }
    return _hashed(ProviderTerminalAttribution, body)


def completion_instruction(decision: CompletionLoopDecision) -> dict[str, Any]:
    """Render the small model-facing instruction for the selected target."""

    if type(decision) is not CompletionLoopDecision:
        raise TypeError("completion instruction requires an exact decision")
    instructions = {
        "phase-policy": "Use the phase-filtered tools to understand and implement the task.",
        "visible-check": (
            "Run exactly the bound public check. Do not call another check in this response."
        ),
        "correction-inspection": (
            "The bound public check failed. Read one current relevant source range before editing."
        ),
        "corrective-mutation": (
            "Make one smallest structured correction from the fresh read; preserve behaviors "
            "covered by already passing checks."
        ),
        "diff-review": "Review the complete current diff with get_diff.",
        "submission": "Submit the already checked and reviewed current diff.",
    }
    body = {
        "schema_version": "completion-loop-instruction-v1",
        "policy_version": COMPLETION_LOOP_POLICY,
        "decision_hash": decision.content_hash,
        "target": decision.target,
        "expected_check_id": decision.expected_check_id,
        "preserve_check_ids": list(decision.preserve_check_ids),
        "effective_max_output_tokens": decision.effective_max_output_tokens,
        "reasoning_effort": decision.reasoning_effort,
        "parallel_tool_calls": False,
        "instruction": instructions[decision.target],
        "provider_calls_authorized": False,
    }
    return {**body, "content_hash": sha256_json(body)}
