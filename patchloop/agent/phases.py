"""Explicit, validated agent phase transitions."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from patchloop.contracts import EventType, Phase, PublicTask, RunEvent
from patchloop.errors import ContractError
from patchloop.util import sha256_text

ALLOWED_TRANSITIONS: dict[Phase, set[Phase]] = {
    Phase.INTAKE: {Phase.REPRODUCE},
    Phase.REPRODUCE: {Phase.PLAN},
    Phase.PLAN: {Phase.IMPLEMENT},
    Phase.IMPLEMENT: {Phase.VERIFY, Phase.PLAN},
    Phase.VERIFY: {Phase.REVIEW, Phase.IMPLEMENT},
    Phase.REVIEW: {Phase.DONE, Phase.IMPLEMENT},
    Phase.DONE: set(),
}


def validate_transition(current: Phase, target: Phase) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ContractError(f"invalid phase transition: {current.value} -> {target.value}")


@dataclass(frozen=True)
class EvidenceState:
    """Public orchestration evidence bound to one exact worktree diff."""

    worktree_diff_hash: str
    mutation_event_sequence: int | None
    mutation_present: bool
    completed_checks: tuple[str, ...]
    pending_checks: tuple[str, ...]
    latest_check_sequence: int | None
    review_event_sequence: int | None
    review_presented_to_model: bool
    submission_ready: bool
    missing_evidence: tuple[str, ...]
    allowed_next_actions: tuple[str, ...]


def diff_bound_evidence(
    task: PublicTask,
    events: Iterable[RunEvent],
    worktree_diff_hash: str,
    *,
    presented_tool_results: Iterable[dict[str, Any]] = (),
    phase: Phase | None = None,
) -> EvidenceState:
    """Derive latest-check and final-review readiness without private data."""

    required = tuple(check.id for check in task.visible_checks)
    event_list = tuple(events)
    latest_mutation = next(
        (
            event
            for event in reversed(event_list)
            if event.type == EventType.PATCH_APPLIED
        ),
        None,
    )
    mutation_epoch = latest_mutation.sequence if latest_mutation else 0
    mutation_present = bool(
        latest_mutation is not None
        and worktree_diff_hash != sha256_text("")
        and latest_mutation.payload.get("worktree_diff_hash")
        == worktree_diff_hash
    )
    latest_checks: dict[str, RunEvent] = {}
    review_candidates: list[RunEvent] = []
    for event in event_list:
        if (
            event.sequence > mutation_epoch
            and event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("worktree_diff_hash") == worktree_diff_hash
        ):
            if (
                event.payload.get("tool") == "run_check"
                and event.payload.get("check_id") in required
            ):
                latest_checks[str(event.payload["check_id"])] = event
            elif event.payload.get("tool") == "get_diff":
                review_candidates.append(event)

    completed = tuple(
        check_id
        for check_id in required
        if (
            check_id in latest_checks
            and latest_checks[check_id].payload.get("passed") is True
        )
    )
    pending = tuple(check_id for check_id in required if check_id not in completed)
    latest_check_sequence = (
        max(event.sequence for event in latest_checks.values())
        if latest_checks
        else None
    )
    review_event = next(
        (
            event
            for event in reversed(review_candidates)
            if not pending
            and (
                latest_check_sequence is None
                or event.sequence > latest_check_sequence
            )
        ),
        None,
    )
    presented_sequences = {
        int(item["event_sequence"])
        for item in presented_tool_results
        if (
            isinstance(item.get("event_sequence"), int)
            and item.get("available") is True
            and item.get("truncated") is False
        )
    }
    review_presented = bool(
        review_event is not None and review_event.sequence in presented_sequences
    )
    missing: list[str] = []
    if not mutation_present:
        missing.append("successful_mutation_current_diff")
    if pending:
        missing.append("visible_checks_current_diff")
    if review_event is None:
        missing.append("final_diff_review_current_diff")
    elif not review_presented:
        missing.append("final_diff_review_not_presented")
    if phase is not None and phase != Phase.REVIEW:
        missing.append("review_phase")

    if not mutation_present:
        allowed = ("apply_patch", "run_check", "read_file", "search_files")
    elif pending:
        allowed = ("run_check", "apply_patch", "read_file", "search_files")
    elif review_event is None or not review_presented:
        allowed = ("get_diff", "apply_patch", "read_file", "search_files")
    else:
        allowed = ("finish_task", "apply_patch")
    return EvidenceState(
        worktree_diff_hash=worktree_diff_hash,
        mutation_event_sequence=(
            latest_mutation.sequence if latest_mutation is not None else None
        ),
        mutation_present=mutation_present,
        completed_checks=completed,
        pending_checks=pending,
        latest_check_sequence=latest_check_sequence,
        review_event_sequence=review_event.sequence if review_event else None,
        review_presented_to_model=review_presented,
        submission_ready=not missing,
        missing_evidence=tuple(missing),
        allowed_next_actions=allowed,
    )
