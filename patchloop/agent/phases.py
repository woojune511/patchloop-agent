"""Explicit, validated agent phase transitions."""

from __future__ import annotations

from patchloop.contracts import Phase
from patchloop.errors import ContractError

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
