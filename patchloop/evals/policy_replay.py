"""Deterministic, public-metadata-only replay for bounded agent policies."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from patchloop.contracts import RunEvent
from patchloop.util import sha256_json

ProgressKind = Literal[
    "forward_phase",
    "patch_applied",
    "visible_check_passed",
    "submission_attempted",
    "submission_accepted",
]
PolicyKind = Literal[
    "repeated_rejection",
    "relative_context_growth",
    "absolute_context_ceiling_sensitivity",
]

PHASE_ORDER = {
    "INTAKE": 0,
    "REPRODUCE": 1,
    "PLAN": 2,
    "IMPLEMENT": 3,
    "VERIFY": 4,
    "REVIEW": 5,
    "DONE": 6,
}
DEFAULT_MIN_AFFECTED_TASKS = 3
DEFAULT_MIN_SAVINGS_PPM = 200_000
_CUMULATIVE_SPLIT_GENERATION_BLOCK_SCHEMA = "model-generation-block-v4"
_CUMULATIVE_SPLIT_TOKEN_BUDGET_SCHEMA = "cumulative-split-v1"


class PolicyReplayError(ValueError):
    """Raised when public event metadata is malformed or incomplete."""


@dataclass(frozen=True, slots=True)
class ProgressMarker:
    sequence: int
    kind: ProgressKind


@dataclass(frozen=True, slots=True)
class RejectionObservation:
    sequence: int
    fingerprint: str


@dataclass(frozen=True, slots=True)
class ContextObservation:
    sequence: int
    context_characters: int
    baseline_context_characters: int
    completed_model_calls_since_progress: int


@dataclass(frozen=True, slots=True)
class PublicTrajectory:
    run_id: str
    task_id: str
    events: tuple[RunEvent, ...]
    progress_markers: tuple[ProgressMarker, ...]
    rejections: tuple[RejectionObservation, ...]
    contexts: tuple[ContextObservation, ...]
    total_model_tokens: int
    total_model_calls: int
    total_tool_calls: int
    duration_ms: int
    public_event_projection_hash: str


@dataclass(frozen=True, slots=True)
class ObservedSuffix:
    model_tokens: int
    model_calls: int
    tool_calls: int
    wall_clock_ms: int

    def to_dict(self) -> dict[str, int]:
        return {
            "model_tokens": self.model_tokens,
            "model_calls": self.model_calls,
            "tool_calls": self.tool_calls,
            "wall_clock_ms": self.wall_clock_ms,
        }


@dataclass(frozen=True, slots=True)
class PolicyReplayResult:
    policy_id: str
    policy_kind: PolicyKind
    run_id: str
    task_id: str
    triggered: bool
    trigger_sequence: int | None
    trigger_fingerprint: str | None
    trigger_context_characters: int | None
    trigger_baseline_context_characters: int | None
    trigger_completed_model_calls_since_progress: int | None
    later_progress_sequences: tuple[int, ...]
    false_stop: bool | None
    observed_suffix: ObservedSuffix | None
    run_total_model_tokens: int
    run_duration_ms: int

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "policy_kind": self.policy_kind,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "triggered": self.triggered,
            "trigger_sequence": self.trigger_sequence,
            "trigger_fingerprint": self.trigger_fingerprint,
            "trigger_context_characters": self.trigger_context_characters,
            "trigger_baseline_context_characters": (
                self.trigger_baseline_context_characters
            ),
            "trigger_completed_model_calls_since_progress": (
                self.trigger_completed_model_calls_since_progress
            ),
            "later_progress_sequences": list(self.later_progress_sequences),
            "false_stop": self.false_stop,
            "observed_suffix": (
                self.observed_suffix.to_dict()
                if self.observed_suffix is not None
                else None
            ),
            "run_total_model_tokens": self.run_total_model_tokens,
            "run_duration_ms": self.run_duration_ms,
        }


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    policy_id: str
    policy_kind: PolicyKind
    panel_run_count: int
    triggered_run_count: int
    false_stop_run_ids: tuple[str, ...]
    safe_intercept_run_ids: tuple[str, ...]
    affected_task_ids: tuple[str, ...]
    observed_suffix_model_tokens: int
    safe_intercept_total_model_tokens: int
    observed_suffix_token_fraction_ppm: int
    observed_suffix_wall_clock_ms: int
    safe_intercept_total_wall_clock_ms: int
    observed_suffix_wall_fraction_ppm: int
    zero_false_stops_passed: bool
    minimum_task_coverage_passed: bool
    minimum_savings_passed: bool
    leave_one_task_out_passed: bool
    admission_scope: bool
    admitted: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "policy_kind": self.policy_kind,
            "panel_run_count": self.panel_run_count,
            "triggered_run_count": self.triggered_run_count,
            "false_stop_run_ids": list(self.false_stop_run_ids),
            "safe_intercept_run_ids": list(self.safe_intercept_run_ids),
            "affected_task_ids": list(self.affected_task_ids),
            "observed_suffix_model_tokens": self.observed_suffix_model_tokens,
            "safe_intercept_total_model_tokens": (
                self.safe_intercept_total_model_tokens
            ),
            "observed_suffix_token_fraction_ppm": (
                self.observed_suffix_token_fraction_ppm
            ),
            "observed_suffix_wall_clock_ms": (
                self.observed_suffix_wall_clock_ms
            ),
            "safe_intercept_total_wall_clock_ms": (
                self.safe_intercept_total_wall_clock_ms
            ),
            "observed_suffix_wall_fraction_ppm": (
                self.observed_suffix_wall_fraction_ppm
            ),
            "zero_false_stops_passed": self.zero_false_stops_passed,
            "minimum_task_coverage_passed": self.minimum_task_coverage_passed,
            "minimum_savings_passed": self.minimum_savings_passed,
            "leave_one_task_out_passed": self.leave_one_task_out_passed,
            "admission_scope": self.admission_scope,
            "admitted": self.admitted,
        }


def _strict_int(value: object, *, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise PolicyReplayError(f"{label} must be an integer >= {minimum}")
    return value


def _strict_string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PolicyReplayError(f"{label} must be a non-empty string")
    return value


def _forward_phase_marker(event: RunEvent) -> ProgressMarker | None:
    source = _strict_string(event.payload.get("from"), label="PhaseChanged.from")
    target = _strict_string(event.payload.get("to"), label="PhaseChanged.to")
    if source not in PHASE_ORDER or target not in PHASE_ORDER:
        raise PolicyReplayError("PhaseChanged contains an unknown phase")
    if PHASE_ORDER[target] <= PHASE_ORDER[source]:
        return None
    return ProgressMarker(sequence=event.sequence, kind="forward_phase")


def _apply_call_worktrees(
    events: Sequence[RunEvent],
) -> dict[str, tuple[int, str]]:
    """Index public apply-call CAS metadata by correlation ID.

    Correlation IDs are used only to join the call and failure.  They are not
    emitted in the public projection or included in a rejection fingerprint.
    """

    worktrees: dict[str, tuple[int, str]] = {}
    for event in events:
        if event.type.value != "ToolCalled" or event.payload.get("tool") != (
            "apply_patch"
        ):
            continue
        correlation_id = _strict_string(
            event.correlation_id,
            label="apply ToolCalled.correlation_id",
        )
        if correlation_id in worktrees:
            raise PolicyReplayError(
                "apply ToolCalled correlation_id must be unique within a run"
            )
        worktrees[correlation_id] = (
            event.sequence,
            _strict_string(
                event.payload.get("worktree_diff_hash"),
                label="apply ToolCalled.worktree_diff_hash",
            ),
        )
    return worktrees


def _rejection_worktree_diff_hash(
    event: RunEvent,
    apply_call_worktrees: dict[str, tuple[int, str]],
) -> str:
    correlation_id = _strict_string(
        event.correlation_id,
        label="apply ToolFailed.correlation_id",
    )
    call = apply_call_worktrees.get(correlation_id)
    if call is None:
        raise PolicyReplayError(
            "apply ToolFailed must correlate to one public apply ToolCalled"
        )
    call_sequence, worktree_diff_hash = call
    if call_sequence >= event.sequence:
        raise PolicyReplayError(
            "apply ToolFailed must follow its correlated apply ToolCalled"
        )
    return worktree_diff_hash


def _rejection_fingerprint(event: RunEvent, *, worktree_diff_hash: str) -> str:
    error_code = _strict_string(
        event.payload.get("error_code"), label="apply rejection error_code"
    )
    details = event.payload.get("error_details")
    if not isinstance(details, dict):
        raise PolicyReplayError("apply rejection error_details must be an object")
    stage = _strict_string(details.get("stage"), label="apply rejection stage")
    reason = _strict_string(details.get("reason"), label="apply rejection reason")
    return sha256_json(
        {
            "schema_version": "public-apply-rejection-fingerprint-v1",
            "tool": "apply_patch",
            "status": "rejected",
            "error_code": error_code,
            "stage": stage,
            "reason": reason,
            "worktree_diff_hash": worktree_diff_hash,
        }
    )


def _cumulative_split_generation_block_projection(
    payload: dict[str, object],
) -> dict[str, object]:
    """Validate and project the public arithmetic of a v4 token block."""

    if (
        payload.get("token_budget_schema_version")
        != _CUMULATIVE_SPLIT_TOKEN_BUDGET_SCHEMA
        or payload.get("reason_code") != "exact_request_budget_exceeded"
        or payload.get("error_code") != "MODEL_GENERATION_BUDGET_EXCEEDED"
        or payload.get("generation_started") is not False
    ):
        raise PolicyReplayError(
            "ModelGenerationBlocked v4 common fields are invalid"
        )
    integer_fields = (
        "requested_input_tokens",
        "max_output_tokens",
        "input_tokens_used",
        "output_tokens_used",
        "total_tokens_used",
        "max_cumulative_input_tokens",
        "max_cumulative_output_tokens",
        "max_total_tokens",
        "remaining_input_tokens",
        "remaining_output_tokens",
        "remaining_total_tokens",
    )
    values = {
        field: _strict_int(
            payload.get(field),
            label=f"ModelGenerationBlocked.{field}",
            minimum=(1 if field.startswith("max_") else 0),
        )
        for field in integer_fields
    }
    input_token_count_calls = _strict_int(
        payload.get("input_token_count_calls"),
        label="ModelGenerationBlocked.input_token_count_calls",
    )
    if input_token_count_calls != 1:
        raise PolicyReplayError(
            "ModelGenerationBlocked.input_token_count_calls must equal 1"
        )
    if values["total_tokens_used"] != (
        values["input_tokens_used"] + values["output_tokens_used"]
    ):
        raise PolicyReplayError(
            "ModelGenerationBlocked.total_tokens_used must equal split usage"
        )
    if not (
        values["max_cumulative_input_tokens"] <= values["max_total_tokens"]
        and values["max_cumulative_output_tokens"] <= values["max_total_tokens"]
        and values["max_total_tokens"]
        <= values["max_cumulative_input_tokens"]
        + values["max_cumulative_output_tokens"]
    ):
        raise PolicyReplayError(
            "ModelGenerationBlocked split token limits are inconsistent"
        )
    for dimension in ("input", "output", "total"):
        limit_field = (
            f"max_cumulative_{dimension}_tokens"
            if dimension != "total"
            else "max_total_tokens"
        )
        used_field = f"{dimension}_tokens_used"
        remaining_field = f"remaining_{dimension}_tokens"
        if values[remaining_field] != values[limit_field] - values[used_field]:
            raise PolicyReplayError(
                f"ModelGenerationBlocked.{remaining_field} is inconsistent"
            )

    expected_exceeded = [
        dimension
        for dimension, exceeded in (
            (
                "input_tokens",
                values["input_tokens_used"] + values["requested_input_tokens"]
                > values["max_cumulative_input_tokens"],
            ),
            (
                "output_tokens",
                values["output_tokens_used"] + values["max_output_tokens"]
                > values["max_cumulative_output_tokens"],
            ),
            (
                "total_tokens",
                values["total_tokens_used"]
                + values["requested_input_tokens"]
                + values["max_output_tokens"]
                > values["max_total_tokens"],
            ),
        )
        if exceeded
    ]
    exceeded = payload.get("exceeded_dimensions")
    binding = payload.get("binding_dimension")
    if not expected_exceeded or exceeded != expected_exceeded:
        raise PolicyReplayError(
            "ModelGenerationBlocked.exceeded_dimensions is inconsistent"
        )
    if binding != expected_exceeded[0]:
        raise PolicyReplayError(
            "ModelGenerationBlocked.binding_dimension is inconsistent"
        )
    return {
        "schema_version": _CUMULATIVE_SPLIT_GENERATION_BLOCK_SCHEMA,
        "token_budget_schema_version": _CUMULATIVE_SPLIT_TOKEN_BUDGET_SCHEMA,
        "error_code": _strict_string(
            payload.get("error_code"),
            label="ModelGenerationBlocked.error_code",
        ),
        "reason_code": _strict_string(
            payload.get("reason_code"),
            label="ModelGenerationBlocked.reason_code",
        ),
        "generation_started": payload["generation_started"],
        "input_token_count_calls": input_token_count_calls,
        **values,
        "exceeded_dimensions": expected_exceeded,
        "binding_dimension": binding,
    }


def _safe_projection_payload(
    event: RunEvent,
    *,
    apply_call_worktrees: dict[str, tuple[int, str]],
) -> dict[str, object]:
    event_type = event.type.value
    payload = event.payload
    if event_type == "PhaseChanged":
        return {
            "from": _strict_string(payload.get("from"), label="PhaseChanged.from"),
            "to": _strict_string(payload.get("to"), label="PhaseChanged.to"),
        }
    if event_type == "ContextBuilt":
        return {
            "context_characters": _strict_int(
                payload.get("context_characters"), label="ContextBuilt.context_characters"
            ),
            "included_event_count": _strict_int(
                payload.get("included_event_count"),
                label="ContextBuilt.included_event_count",
            ),
            "omitted_event_count": _strict_int(
                payload.get("omitted_event_count"),
                label="ContextBuilt.omitted_event_count",
            ),
        }
    if event_type == "ModelCalled":
        return {
            key: _strict_int(payload.get(key), label=f"ModelCalled.{key}")
            for key in (
                "requested_input_tokens",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "duration_ms",
            )
        }
    if event_type == "ToolCalled":
        return {"tool": _strict_string(payload.get("tool"), label="ToolCalled.tool")}
    if event_type in {"ToolSucceeded", "ToolFailed"} and payload.get("tool") == (
        "run_check"
    ):
        passed = payload.get("passed")
        if type(passed) is not bool:
            raise PolicyReplayError("run_check passed must be a boolean")
        return {
            "tool": "run_check",
            "passed": passed,
            "check_id": payload.get("check_id"),
            "worktree_diff_hash": payload.get("worktree_diff_hash"),
        }
    if event_type == "ToolFailed" and payload.get("tool") == "apply_patch":
        details = payload.get("error_details")
        if not isinstance(details, dict):
            raise PolicyReplayError("apply rejection error_details must be an object")
        return {
            "tool": "apply_patch",
            "error_code": _strict_string(
                payload.get("error_code"), label="apply rejection error_code"
            ),
            "stage": _strict_string(
                details.get("stage"), label="apply rejection stage"
            ),
            "reason": _strict_string(
                details.get("reason"), label="apply rejection reason"
            ),
            "worktree_diff_hash": _rejection_worktree_diff_hash(
                event,
                apply_call_worktrees,
            ),
        }
    if event_type == "ModelGenerationBlocked":
        generation_started = payload.get("generation_started")
        if type(generation_started) is not bool:
            raise PolicyReplayError(
                "ModelGenerationBlocked.generation_started must be a boolean"
            )
        if payload.get("schema_version") == _CUMULATIVE_SPLIT_GENERATION_BLOCK_SCHEMA:
            return _cumulative_split_generation_block_projection(payload)
        return {
            "error_code": _strict_string(
                payload.get("error_code"),
                label="ModelGenerationBlocked.error_code",
            ),
            "reason_code": _strict_string(
                payload.get("reason_code"),
                label="ModelGenerationBlocked.reason_code",
            ),
            "generation_started": generation_started,
            "requested_input_tokens": _strict_int(
                payload.get("requested_input_tokens"),
                label="ModelGenerationBlocked.requested_input_tokens",
            ),
            "max_output_tokens": _strict_int(
                payload.get("max_output_tokens"),
                label="ModelGenerationBlocked.max_output_tokens",
            ),
            "remaining_tokens": _strict_int(
                payload.get("remaining_tokens"),
                label="ModelGenerationBlocked.remaining_tokens",
            ),
        }
    if event_type == "RunFailed":
        return {
            "error_code": payload.get("error_code"),
            "error_type": payload.get("error_type"),
            "outcome_kind": payload.get("outcome_kind"),
        }
    return {}


def public_event_projection_hash(events: Sequence[RunEvent]) -> str:
    """Hash only allowlisted process metadata, never model/tool/patch bodies."""

    if not events:
        raise PolicyReplayError("public trajectory must contain at least one event")
    run_id = events[0].run_id
    apply_call_worktrees = _apply_call_worktrees(events)
    projected = []
    for expected_sequence, event in enumerate(events, start=1):
        if event.run_id != run_id:
            raise PolicyReplayError("public trajectory contains multiple run IDs")
        if event.sequence != expected_sequence:
            raise PolicyReplayError("public trajectory sequence is not contiguous")
        projected.append(
            {
                "sequence": event.sequence,
                "type": event.type.value,
                "timestamp": event.timestamp.isoformat(),
                "payload": _safe_projection_payload(
                    event,
                    apply_call_worktrees=apply_call_worktrees,
                ),
            }
        )
    return sha256_json(
        {
            "schema_version": "public-policy-event-projection-v1",
            "run_id": run_id,
            "events": projected,
        }
    )


def project_public_trajectory(
    events: Sequence[RunEvent], *, task_id: str
) -> PublicTrajectory:
    """Project the public event stream needed for bounded policy replay."""

    task_id = _strict_string(task_id, label="task_id")
    event_rows = tuple(events)
    projection_hash = public_event_projection_hash(event_rows)
    apply_call_worktrees = _apply_call_worktrees(event_rows)
    progress: list[ProgressMarker] = []
    rejections: list[RejectionObservation] = []
    contexts: list[ContextObservation] = []
    seen_passing_checks: set[tuple[str, str]] = set()
    baseline_context_characters: int | None = None
    completed_model_calls_since_progress = 0
    total_model_tokens = 0
    total_model_calls = 0
    total_tool_calls = 0

    prior_timestamp = event_rows[0].timestamp
    for event in event_rows:
        if event.timestamp < prior_timestamp:
            raise PolicyReplayError("public trajectory timestamps are not monotonic")
        prior_timestamp = event.timestamp
        marker: ProgressMarker | None = None
        event_type = event.type.value
        if event_type == "PhaseChanged":
            marker = _forward_phase_marker(event)
        elif event_type == "PatchApplied":
            marker = ProgressMarker(event.sequence, "patch_applied")
        elif event_type in {"ToolSucceeded", "ToolFailed"} and event.payload.get(
            "tool"
        ) == "run_check":
            passed = event.payload.get("passed")
            if type(passed) is not bool:
                raise PolicyReplayError("run_check passed must be a boolean")
            if passed:
                check_id = _strict_string(
                    event.payload.get("check_id"), label="run_check check_id"
                )
                worktree_diff_hash = _strict_string(
                    event.payload.get("worktree_diff_hash"),
                    label="run_check worktree_diff_hash",
                )
                check_key = (check_id, worktree_diff_hash)
                if check_key not in seen_passing_checks:
                    seen_passing_checks.add(check_key)
                    marker = ProgressMarker(
                        event.sequence, "visible_check_passed"
                    )
        elif event_type == "SubmissionAttempted":
            marker = ProgressMarker(event.sequence, "submission_attempted")
        elif event_type == "SubmissionAccepted":
            marker = ProgressMarker(event.sequence, "submission_accepted")

        if marker is not None:
            progress.append(marker)
            baseline_context_characters = None
            completed_model_calls_since_progress = 0

        if event_type == "ContextBuilt":
            context_characters = _strict_int(
                event.payload.get("context_characters"),
                label="ContextBuilt.context_characters",
            )
            if baseline_context_characters is None:
                baseline_context_characters = context_characters
            contexts.append(
                ContextObservation(
                    sequence=event.sequence,
                    context_characters=context_characters,
                    baseline_context_characters=baseline_context_characters,
                    completed_model_calls_since_progress=(
                        completed_model_calls_since_progress
                    ),
                )
            )
        elif event_type == "ModelCalled":
            total_model_tokens += _strict_int(
                event.payload.get("total_tokens"), label="ModelCalled.total_tokens"
            )
            total_model_calls += 1
            completed_model_calls_since_progress += 1
        elif event_type == "ToolCalled":
            total_tool_calls += 1
        elif event_type == "ToolFailed" and event.payload.get("tool") == (
            "apply_patch"
        ):
            worktree_diff_hash = _rejection_worktree_diff_hash(
                event,
                apply_call_worktrees,
            )
            rejections.append(
                RejectionObservation(
                    sequence=event.sequence,
                    fingerprint=_rejection_fingerprint(
                        event,
                        worktree_diff_hash=worktree_diff_hash,
                    ),
                )
            )

    duration_ms = round(
        (event_rows[-1].timestamp - event_rows[0].timestamp).total_seconds() * 1000
    )
    return PublicTrajectory(
        run_id=event_rows[0].run_id,
        task_id=task_id,
        events=event_rows,
        progress_markers=tuple(progress),
        rejections=tuple(rejections),
        contexts=tuple(contexts),
        total_model_tokens=total_model_tokens,
        total_model_calls=total_model_calls,
        total_tool_calls=total_tool_calls,
        duration_ms=duration_ms,
        public_event_projection_hash=projection_hash,
    )


def _observed_suffix(
    trajectory: PublicTrajectory, trigger_sequence: int
) -> tuple[tuple[int, ...], ObservedSuffix]:
    tail = [event for event in trajectory.events if event.sequence > trigger_sequence]
    trigger = next(
        event
        for event in trajectory.events
        if event.sequence == trigger_sequence
    )
    later_progress = tuple(
        marker.sequence
        for marker in trajectory.progress_markers
        if marker.sequence > trigger_sequence
    )
    return later_progress, ObservedSuffix(
        model_tokens=sum(
            _strict_int(
                event.payload.get("total_tokens"), label="ModelCalled.total_tokens"
            )
            for event in tail
            if event.type.value == "ModelCalled"
        ),
        model_calls=sum(event.type.value == "ModelCalled" for event in tail),
        tool_calls=sum(event.type.value == "ToolCalled" for event in tail),
        wall_clock_ms=round(
            (trajectory.events[-1].timestamp - trigger.timestamp).total_seconds()
            * 1000
        ),
    )


def _no_trigger_result(
    trajectory: PublicTrajectory, *, policy_id: str, policy_kind: PolicyKind
) -> PolicyReplayResult:
    return PolicyReplayResult(
        policy_id=policy_id,
        policy_kind=policy_kind,
        run_id=trajectory.run_id,
        task_id=trajectory.task_id,
        triggered=False,
        trigger_sequence=None,
        trigger_fingerprint=None,
        trigger_context_characters=None,
        trigger_baseline_context_characters=None,
        trigger_completed_model_calls_since_progress=None,
        later_progress_sequences=(),
        false_stop=None,
        observed_suffix=None,
        run_total_model_tokens=trajectory.total_model_tokens,
        run_duration_ms=trajectory.duration_ms,
    )


def replay_repeated_rejection(
    trajectory: PublicTrajectory, *, threshold: int
) -> PolicyReplayResult:
    """Replay a same-fingerprint rejected-apply streak threshold."""

    threshold = _strict_int(threshold, label="rejection threshold", minimum=2)
    policy_id = f"repeated-rejection-n{threshold}"
    progress_sequences = {item.sequence for item in trajectory.progress_markers}
    rejection_by_sequence = {item.sequence: item for item in trajectory.rejections}
    streak = 0
    prior_fingerprint: str | None = None
    for event in trajectory.events:
        if event.sequence in progress_sequences:
            streak = 0
            prior_fingerprint = None
        rejection = rejection_by_sequence.get(event.sequence)
        if rejection is None:
            continue
        if rejection.fingerprint == prior_fingerprint:
            streak += 1
        else:
            streak = 1
            prior_fingerprint = rejection.fingerprint
        if streak < threshold:
            continue
        later_progress, suffix = _observed_suffix(trajectory, event.sequence)
        return PolicyReplayResult(
            policy_id=policy_id,
            policy_kind="repeated_rejection",
            run_id=trajectory.run_id,
            task_id=trajectory.task_id,
            triggered=True,
            trigger_sequence=event.sequence,
            trigger_fingerprint=rejection.fingerprint,
            trigger_context_characters=None,
            trigger_baseline_context_characters=None,
            trigger_completed_model_calls_since_progress=None,
            later_progress_sequences=later_progress,
            false_stop=bool(later_progress),
            observed_suffix=suffix,
            run_total_model_tokens=trajectory.total_model_tokens,
            run_duration_ms=trajectory.duration_ms,
        )
    return _no_trigger_result(
        trajectory, policy_id=policy_id, policy_kind="repeated_rejection"
    )


def replay_relative_context_growth(
    trajectory: PublicTrajectory,
    *,
    multiplier: int,
    minimum_completed_model_calls: int,
) -> PolicyReplayResult:
    """Replay context growth relative to the first context after progress."""

    multiplier = _strict_int(multiplier, label="context multiplier", minimum=2)
    minimum_completed_model_calls = _strict_int(
        minimum_completed_model_calls,
        label="minimum completed model calls",
        minimum=1,
    )
    policy_id = (
        f"relative-context-x{multiplier}-calls{minimum_completed_model_calls}"
    )
    for context in trajectory.contexts:
        if (
            context.completed_model_calls_since_progress
            < minimum_completed_model_calls
            or context.context_characters
            < context.baseline_context_characters * multiplier
        ):
            continue
        later_progress, suffix = _observed_suffix(
            trajectory, context.sequence
        )
        return PolicyReplayResult(
            policy_id=policy_id,
            policy_kind="relative_context_growth",
            run_id=trajectory.run_id,
            task_id=trajectory.task_id,
            triggered=True,
            trigger_sequence=context.sequence,
            trigger_fingerprint=None,
            trigger_context_characters=context.context_characters,
            trigger_baseline_context_characters=(
                context.baseline_context_characters
            ),
            trigger_completed_model_calls_since_progress=(
                context.completed_model_calls_since_progress
            ),
            later_progress_sequences=later_progress,
            false_stop=bool(later_progress),
            observed_suffix=suffix,
            run_total_model_tokens=trajectory.total_model_tokens,
            run_duration_ms=trajectory.duration_ms,
        )
    return _no_trigger_result(
        trajectory,
        policy_id=policy_id,
        policy_kind="relative_context_growth",
    )


def replay_absolute_context_ceiling(
    trajectory: PublicTrajectory, *, maximum_context_characters: int
) -> PolicyReplayResult:
    """Replay an absolute ceiling as post-hoc sensitivity, never admission."""

    maximum_context_characters = _strict_int(
        maximum_context_characters,
        label="maximum context characters",
        minimum=1,
    )
    policy_id = f"absolute-context-{maximum_context_characters}"
    for context in trajectory.contexts:
        if context.context_characters < maximum_context_characters:
            continue
        later_progress, suffix = _observed_suffix(
            trajectory, context.sequence
        )
        return PolicyReplayResult(
            policy_id=policy_id,
            policy_kind="absolute_context_ceiling_sensitivity",
            run_id=trajectory.run_id,
            task_id=trajectory.task_id,
            triggered=True,
            trigger_sequence=context.sequence,
            trigger_fingerprint=None,
            trigger_context_characters=context.context_characters,
            trigger_baseline_context_characters=(
                context.baseline_context_characters
            ),
            trigger_completed_model_calls_since_progress=(
                context.completed_model_calls_since_progress
            ),
            later_progress_sequences=later_progress,
            false_stop=bool(later_progress),
            observed_suffix=suffix,
            run_total_model_tokens=trajectory.total_model_tokens,
            run_duration_ms=trajectory.duration_ms,
        )
    return _no_trigger_result(
        trajectory,
        policy_id=policy_id,
        policy_kind="absolute_context_ceiling_sensitivity",
    )


def _fraction_ppm(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return numerator * 1_000_000 // denominator


def _base_gate(
    results: Sequence[PolicyReplayResult],
    *,
    minimum_affected_tasks: int,
    minimum_savings_ppm: int,
) -> tuple[bool, bool, bool]:
    triggered = [item for item in results if item.triggered]
    false_stops = [item for item in triggered if item.false_stop is True]
    safe = [item for item in triggered if item.false_stop is False]
    affected_tasks = {item.task_id for item in safe}
    suffix_tokens = sum(
        item.observed_suffix.model_tokens
        for item in safe
        if item.observed_suffix is not None
    )
    total_tokens = sum(item.run_total_model_tokens for item in safe)
    suffix_wall = sum(
        item.observed_suffix.wall_clock_ms
        for item in safe
        if item.observed_suffix is not None
    )
    total_wall = sum(item.run_duration_ms for item in safe)
    zero_false_stops = not false_stops and bool(triggered)
    task_coverage = len(affected_tasks) >= minimum_affected_tasks
    savings = (
        _fraction_ppm(suffix_tokens, total_tokens) >= minimum_savings_ppm
        or _fraction_ppm(suffix_wall, total_wall) >= minimum_savings_ppm
    )
    return zero_false_stops, task_coverage, savings


def aggregate_policy_replays(
    results: Sequence[PolicyReplayResult],
    *,
    panel_task_ids: Sequence[str],
    admission_scope: bool = True,
    minimum_affected_tasks: int = DEFAULT_MIN_AFFECTED_TASKS,
    minimum_savings_ppm: int = DEFAULT_MIN_SAVINGS_PPM,
) -> PolicyEvaluation:
    """Apply the predeclared safety, generality, benefit, and LOTO gates."""

    if not results:
        raise PolicyReplayError("policy aggregation requires at least one run")
    minimum_affected_tasks = _strict_int(
        minimum_affected_tasks, label="minimum affected tasks", minimum=1
    )
    minimum_savings_ppm = _strict_int(
        minimum_savings_ppm, label="minimum savings ppm", minimum=1
    )
    if minimum_savings_ppm > 1_000_000:
        raise PolicyReplayError("minimum savings ppm cannot exceed 1000000")
    policy_ids = {item.policy_id for item in results}
    policy_kinds = {item.policy_kind for item in results}
    if len(policy_ids) != 1 or len(policy_kinds) != 1:
        raise PolicyReplayError("all replay rows must use one exact policy")
    run_ids = [item.run_id for item in results]
    if len(run_ids) != len(set(run_ids)):
        raise PolicyReplayError("policy aggregation contains duplicate run IDs")
    expected_tasks = tuple(sorted({_strict_string(x, label="panel task") for x in panel_task_ids}))
    observed_tasks = {item.task_id for item in results}
    if observed_tasks != set(expected_tasks):
        raise PolicyReplayError("panel task IDs do not match replay rows")

    triggered = [item for item in results if item.triggered]
    false_stops = [item for item in triggered if item.false_stop is True]
    safe = [item for item in triggered if item.false_stop is False]
    suffix_tokens = sum(
        item.observed_suffix.model_tokens
        for item in safe
        if item.observed_suffix is not None
    )
    total_tokens = sum(item.run_total_model_tokens for item in safe)
    suffix_wall = sum(
        item.observed_suffix.wall_clock_ms
        for item in safe
        if item.observed_suffix is not None
    )
    total_wall = sum(item.run_duration_ms for item in safe)
    zero_false_stops, task_coverage, savings = _base_gate(
        results,
        minimum_affected_tasks=minimum_affected_tasks,
        minimum_savings_ppm=minimum_savings_ppm,
    )
    leave_one_task_out = all(
        all(
            _base_gate(
                [item for item in results if item.task_id != excluded_task],
                minimum_affected_tasks=minimum_affected_tasks,
                minimum_savings_ppm=minimum_savings_ppm,
            )
        )
        for excluded_task in expected_tasks
    )
    admitted = (
        admission_scope
        and zero_false_stops
        and task_coverage
        and savings
        and leave_one_task_out
    )
    return PolicyEvaluation(
        policy_id=next(iter(policy_ids)),
        policy_kind=next(iter(policy_kinds)),
        panel_run_count=len(results),
        triggered_run_count=len(triggered),
        false_stop_run_ids=tuple(sorted(item.run_id for item in false_stops)),
        safe_intercept_run_ids=tuple(sorted(item.run_id for item in safe)),
        affected_task_ids=tuple(sorted({item.task_id for item in safe})),
        observed_suffix_model_tokens=suffix_tokens,
        safe_intercept_total_model_tokens=total_tokens,
        observed_suffix_token_fraction_ppm=_fraction_ppm(
            suffix_tokens, total_tokens
        ),
        observed_suffix_wall_clock_ms=suffix_wall,
        safe_intercept_total_wall_clock_ms=total_wall,
        observed_suffix_wall_fraction_ppm=_fraction_ppm(
            suffix_wall, total_wall
        ),
        zero_false_stops_passed=zero_false_stops,
        minimum_task_coverage_passed=task_coverage,
        minimum_savings_passed=savings,
        leave_one_task_out_passed=leave_one_task_out,
        admission_scope=admission_scope,
        admitted=admitted,
    )


def select_panel_decision(evaluations: Sequence[PolicyEvaluation]) -> str:
    """Select the bounded panel decision without changing runtime policy."""

    admitted = [item for item in evaluations if item.admitted]
    if not admitted:
        return "retain-current-policy-and-count-qualified-budget-terminal-as-agent-failure"
    kinds = {item.policy_kind for item in admitted}
    if "repeated_rejection" in kinds:
        return "admit-generic-repeated-rejection-fail-fast-for-offline-runtime-e2e"
    if "relative_context_growth" in kinds:
        return "admit-generic-relative-context-ceiling-for-offline-runtime-e2e"
    raise PolicyReplayError("sensitivity-only policy cannot be admitted")
