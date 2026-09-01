"""Request/dispatch parity for post-restore semantic-progress evidence.

Lean V20 is intentionally opt-in.  Earlier runtimes keep their historical
event-domain behavior, while V20 projects one typed descriptor and requires
the tool gateway to reconstruct that exact descriptor before plan admission.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.contracts import EventType, RunEvent
from patchloop.errors import RecoveryError
from patchloop.util import sha256_json

SEMANTIC_PROGRESS_EPOCH_PARITY_POLICY = "post-restore-semantic-progress-epoch-parity-v1"
SEMANTIC_PROGRESS_EVENT_DOMAIN_SCHEMA = "semantic-progress-event-domain-v1"


class SemanticProgressEventDomain(BaseModel):
    """Public event-sequence boundary shared by request and dispatch."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["semantic-progress-event-domain-v1"]
    policy_version: Literal["post-restore-semantic-progress-epoch-parity-v1"]
    run_id: str
    source_event_count: int = Field(ge=0)
    source_last_event_sequence: int | None = Field(default=None, ge=1)
    latest_restore_event_sequence: int | None = Field(default=None, ge=1)
    epoch_event_sequences: tuple[int, ...]
    event_type_sequence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_event_envelope_only: Literal[True]
    event_payloads_projected: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_domain(self) -> Self:
        if self.source_event_count == 0 and (
            self.source_last_event_sequence is not None
            or self.latest_restore_event_sequence is not None
            or self.epoch_event_sequences
        ):
            raise ValueError("empty semantic event domain differs")
        if self.source_event_count > 0 and self.source_last_event_sequence is None:
            raise ValueError("semantic event domain lacks its source tail")
        if tuple(sorted(set(self.epoch_event_sequences))) != self.epoch_event_sequences:
            raise ValueError("semantic event-domain sequence order differs")
        if self.latest_restore_event_sequence is not None and any(
            sequence <= self.latest_restore_event_sequence
            for sequence in self.epoch_event_sequences
        ):
            raise ValueError("semantic event domain crosses its restore boundary")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("semantic event-domain hash differs")
        return self


def project_semantic_progress_event_domain(
    *,
    run_id: str,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> SemanticProgressEventDomain:
    """Project the exact append-only suffix after the latest completed restore."""

    event_tuple = tuple(events)
    sequences = tuple(event.sequence for event in event_tuple)
    if any(event.run_id != run_id for event in event_tuple):
        raise RecoveryError("semantic event domain contains a foreign run")
    if tuple(sorted(set(sequences))) != sequences:
        raise RecoveryError("semantic event domain sequence order differs")
    restore_sequences = tuple(
        event.sequence
        for event in event_tuple
        if event.type == EventType.MUTATION_BASELINE_RESTORED
    )
    latest_restore = restore_sequences[-1] if restore_sequences else None
    epoch = tuple(
        event for event in event_tuple if latest_restore is None or event.sequence > latest_restore
    )
    body = {
        "schema_version": SEMANTIC_PROGRESS_EVENT_DOMAIN_SCHEMA,
        "policy_version": SEMANTIC_PROGRESS_EPOCH_PARITY_POLICY,
        "run_id": run_id,
        "source_event_count": len(event_tuple),
        "source_last_event_sequence": sequences[-1] if sequences else None,
        "latest_restore_event_sequence": latest_restore,
        "epoch_event_sequences": tuple(event.sequence for event in epoch),
        "event_type_sequence_hash": sha256_json(
            [(event.sequence, event.type.value) for event in epoch]
        ),
        "public_event_envelope_only": True,
        "event_payloads_projected": False,
    }
    return SemanticProgressEventDomain(**body, content_hash=sha256_json(body))


def select_semantic_progress_epoch_events(
    *,
    domain: SemanticProgressEventDomain,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> tuple[RunEvent, ...]:
    """Reconstruct and select the exact domain, failing closed on drift."""

    event_tuple = tuple(events)
    sequences = tuple(event.sequence for event in event_tuple)
    if any(event.run_id != domain.run_id for event in event_tuple):
        raise RecoveryError("semantic event domain contains a foreign run")
    if tuple(sorted(set(sequences))) != sequences:
        raise RecoveryError("semantic event domain sequence order differs")
    request_prefix = tuple(
        event
        for event in event_tuple
        if domain.source_last_event_sequence is not None
        and event.sequence <= domain.source_last_event_sequence
    )
    if len(request_prefix) != domain.source_event_count:
        raise RecoveryError("semantic progress event domain prefix differs")
    exact = project_semantic_progress_event_domain(
        run_id=domain.run_id,
        events=request_prefix,
    )
    if exact != domain:
        raise RecoveryError("semantic progress event domain differs")
    by_sequence = {event.sequence: event for event in request_prefix}
    try:
        return tuple(by_sequence[sequence] for sequence in domain.epoch_event_sequences)
    except KeyError as exc:  # defensive: exact projection should make this unreachable
        raise RecoveryError("semantic progress event domain is incomplete") from exc


__all__ = [
    "SEMANTIC_PROGRESS_EPOCH_PARITY_POLICY",
    "SEMANTIC_PROGRESS_EVENT_DOMAIN_SCHEMA",
    "SemanticProgressEventDomain",
    "project_semantic_progress_event_domain",
    "select_semantic_progress_epoch_events",
]
