"""Host-registered public obligations, separate from model notes and task identity."""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from patchloop.contracts import RegisteredCheck
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_json


@dataclass(frozen=True)
class RequiredPublicCheck:
    """A trusted public check and optional already measured failure.

    Binding contains the executor/program, interpretation and source-receipt
    identities. This is host configuration, never a model-writable registration.
    Imported observations are evidence, not newly executed or charged actions.
    """

    check: RegisteredCheck
    binding: dict[str, Any]
    observation: dict[str, Any] | None = None

    def descriptor(self) -> dict[str, Any]:
        return copy.deepcopy({
            "check": self.check.model_dump(mode="json"),
            "binding": self.binding, "observation": self.observation,
        })

    @property
    def binding_hash(self) -> str:
        return sha256_json(self.descriptor())

    @property
    def observation_id(self) -> str:
        return "public_observation_" + self.binding_hash[7:39]


def registered_checks(gateway: Any) -> tuple[RegisteredCheck, ...]:
    """One registry for execution, finish, context and resource forecasts."""
    checks = getattr(gateway, "registered_checks", None)
    return tuple(checks if checks is not None else gateway.public_task.visible_checks)


def bind_checks(
    journal: DevJournal, checks: tuple[RequiredPublicCheck, ...],
    *, task_check_ids: set[str], current_diff_hash: Callable[[], str],
) -> None:
    """Freeze a run's supplement, including removal and observation provenance."""
    ids = [entry.check.id for entry in checks]
    if len(set(ids)) != len(ids) or set(ids) & task_check_ids:
        raise ContractError("supplemental public check IDs must be unique")
    for entry in checks:
        if not entry.binding:
            raise ContractError("supplemental public checks require a host evidence binding")
        observation = entry.observation
        if observation is not None and (
                observation.get("check_id") != entry.check.id
                    or observation.get("passed") is not False
                    or not isinstance(observation.get("diff_hash"), str)
                    or any(observation.get(flag) is not False for flag in (
                        "timed_out", "truncated", "deadline_exhausted", "cleanup_failed"))):
            raise ContractError("imported public observation must be a complete bound failure")
    descriptors = [entry.descriptor() for entry in checks]
    payload = {
        "schema": "required-public-checks-v1", "checks": descriptors,
        "binding_hash": sha256_json(descriptors),
    }
    existing = [event["payload"] for event in journal.events()
                if event["event_type"] == "public_checks_registered"]
    if existing:
        if len(existing) != 1 or existing[0] != payload:
            raise RecoveryError("registered public checks or imported evidence changed")
        return
    if not checks:
        return  # Preserve ordinary task-only run identities and journal bytes.
    measured_diff = current_diff_hash()
    for entry in checks:
        if entry.observation and entry.observation["diff_hash"] != measured_diff:
            raise ContractError("initial public observation does not match the current diff")
    journal.append("public_checks_registered", payload)


def public_context(checks: tuple[RequiredPublicCheck, ...]) -> list[dict[str, Any]]:
    return [{
        "check": entry.check.model_dump(mode="json"),
        "binding_hash": entry.binding_hash, "origin": "host_registered_public_check",
        "observation_id": entry.observation_id if entry.observation is not None else None,
        "measured_diff_hash": (entry.observation or {}).get("diff_hash"),
    } for entry in checks]
