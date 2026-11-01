"""Opt-in repair feedback using a registered check, not a fabricated model call."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from patchloop.dev.contracts import DevToolResult, RequestedTool
from patchloop.dev.mutation_tools import MUTATION_TOOLS
from patchloop.dev.state import DevJournal
from patchloop.errors import RecoveryError
from patchloop.util import sha256_json


@dataclass(frozen=True)
class CheckObservation:
    """A check execution or a cited prior public observation, never a fake action."""

    action_id: str
    output: dict[str, Any]
    origin: str | None = None


def check_observations(events):
    for event in events:
        if event["event_type"] == "public_check_imported":
            payload = event["payload"]
            output = payload.get("output")
            if (not isinstance(payload.get("observation_id"), str)
                    or not isinstance(output, dict)
                    or output.get("origin") != "imported_public_observation"):
                raise RecoveryError("imported public check observation is invalid")
            yield event["sequence"], CheckObservation(
                payload["observation_id"], output, "imported_public_observation")
        elif event["event_type"] == "action_finished":
            result = DevToolResult.model_validate(event["payload"]["result"])
            if result.tool == "run_check" and result.status == "succeeded":
                yield event["sequence"], CheckObservation(result.action_id, result.output)


@dataclass(frozen=True)
class RepairRecheck:
    parent_action_id: str
    previous_check_action_id: str
    check_id: str
    baseline_diff_hash: str
    candidate_diff_hash: str
    previous_check_origin: str | None = None

    def _identity(self) -> dict[str, Any]:
        # Preserve the exact existing action hash/payload for ordinary check parents.
        return {key: value for key, value in asdict(self).items() if value is not None}

    def call(self, run_id: str) -> RequestedTool:
        identity = sha256_json({"run_id": run_id, **self._identity()})[7:39]
        return RequestedTool(
            name="run_check", action_id=f"harness_recheck_{identity}",
            arguments={"check_id": self.check_id},
        )

    def payload(self, run_id: str) -> dict[str, Any]:
        return {"origin": "harness", "action_id": self.call(run_id).action_id, **self._identity()}


def latest_repair_check(
    events: list[dict[str, Any]], *, baseline: str, registered_checks: set[str],
) -> CheckObservation | None:
    """Return the current registered failure eligible for an accepted repair's child."""
    checks: dict[str, tuple[int, CheckObservation]] = {}
    for sequence, result in check_observations(events):
        check_id = result.output.get("check_id")
        if check_id in registered_checks and result.output.get("diff_hash") == baseline:
            checks[check_id] = (sequence, result)
    failed = [row for row in checks.values() if row[1].output.get("passed") is False
              and not row[1].output.get("deadline_exhausted")
              and not row[1].output.get("cleanup_failed")]
    return max(failed, key=lambda row: row[0])[1] if failed else None


def select_repair_recheck(
    journal: DevJournal, latest_results: list[DevToolResult], *, registered_checks: set[str],
) -> RepairRecheck | None:
    """Select the latest still-failing check at this accepted mutation's admission.

    Selection is based on durable pre-mutation evidence, so a crash after applying
    the edit or after completing the check cannot erase or change the trigger.
    No historical error from another diff, hypothesis, probe or private input is used.
    """
    if len(latest_results) != 1:
        return None
    mutation = latest_results[0]
    if mutation.tool not in MUTATION_TOOLS or mutation.status != "succeeded":
        return None
    baseline = mutation.output.get("baseline_diff_hash")
    candidate = mutation.output.get("worktree_diff_hash")
    if not isinstance(baseline, str) or not isinstance(candidate, str):
        raise RecoveryError("repair recheck requires durable mutation diff identities")
    if candidate == baseline:
        return None
    before_mutation = []
    for event in journal.events():
        if (event["event_type"] == "action_started"
                and event["payload"].get("action_id") == mutation.action_id):
            break
        before_mutation.append(event)
    else:
        raise RecoveryError("repair recheck mutation admission is missing")
    previous = latest_repair_check(
        before_mutation, baseline=baseline, registered_checks=registered_checks,
    )
    if previous is None:
        return None
    return RepairRecheck(
        parent_action_id=mutation.action_id, previous_check_action_id=previous.action_id,
        check_id=previous.output["check_id"], baseline_diff_hash=baseline,
        candidate_diff_hash=candidate, previous_check_origin=previous.origin,
    )


def repair_recheck_context(journal: DevJournal, diff_hash: str) -> dict[str, Any]:
    finished = next((event["payload"] for event in reversed(journal.events())
                     if event["event_type"] == "repair_recheck_finished"), None)
    last = None
    if finished is not None:
        last = {key: finished[key] for key in (
            "origin", "action_id", "parent_action_id", "previous_check_action_id",
            "check_id", "baseline_diff_hash", "candidate_diff_hash", "status", "passed",
        )}
        if finished.get("previous_check_origin") is not None:
            last["previous_check_origin"] = finished["previous_check_origin"]
        last["evidence_currency"] = (
            "current" if finished["candidate_diff_hash"] == diff_hash else "historical"
        )
        last["details_delivery"] = "recent_checks matched by action_id, check_id and diff_hash"
    return {
        "enabled": True,
        "policy": (
            "After an accepted repair of a current public failure, the harness reruns the "
            "latest failing registered check before inference. This uses one tool action, "
            "not a model call. Other checks still require run_check; a repair is not a PASS."
        ),
        "last_result": last,
    }
