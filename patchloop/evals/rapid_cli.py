"""Shared credential-safe CLI dispatch for future Rapid development scripts."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from patchloop.environment import exact_openai_api_key_environment
from patchloop.errors import ContractError

RapidRehearsal = Callable[..., dict[str, Any]]
RapidExecution = Callable[..., dict[str, Any]]
_EXECUTION_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")


def dispatch_rapid_public_development_cli(
    *,
    mode: Literal["rehearse", "execute"],
    repository: str | Path,
    env_file: str | Path | None,
    approve_live_cost: bool,
    approved_execution_hash: str | None,
    rehearse: RapidRehearsal,
    execute: RapidExecution,
) -> dict[str, Any]:
    """Run one statically imported Rapid entry with an exact credential boundary.

    Rehearsal is guaranteed not to read or export the credential.  Execution
    requires an explicit env file and exposes only ``OPENAI_API_KEY`` for the
    duration of the exact execution callback.  Candidate/hash/cost admission
    remains the responsibility of that callback's production dispatcher.
    """

    if mode == "rehearse":
        if approve_live_cost or approved_execution_hash is not None:
            raise ContractError("Rapid rehearsal must not carry paid execution authority")
        return rehearse(repository=repository)
    if mode != "execute":
        raise ContractError("Rapid CLI mode differs")
    if (
        approve_live_cost is not True
        or not isinstance(approved_execution_hash, str)
        or not _EXECUTION_HASH.fullmatch(approved_execution_hash)
    ):
        raise ContractError(
            "Rapid execution requires explicit cost approval and an exact execution hash"
        )
    if env_file is None:
        raise ContractError("Rapid execution requires an explicit --env-file")
    with exact_openai_api_key_environment(env_file):
        return execute(
            repository=repository,
            approve_live_cost=approve_live_cost,
            approved_execution_hash=approved_execution_hash,
        )


__all__ = ["dispatch_rapid_public_development_cli"]
