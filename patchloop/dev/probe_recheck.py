"""Opt-in saved-program feedback after edits; model-authored tests are not gates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from patchloop.dev import probe_cases
from patchloop.dev.contracts import DevToolResult, RequestedTool
from patchloop.errors import RecoveryError
from patchloop.util import sha256_json

POLICY = "saved-program-v1"
TOOL_DESCRIPTION = (
    "Cases never block finish. This run automatically reruns the last completed retained "
    "save_program=true program after edits when the existing probe budget permits; "
    "a new save replaces the active program and manual reruns do not."
)


def contract() -> dict[str, str]:
    return {
        "policy": POLICY,
        "selection": "last-completed-reference-free-save-before-mutation-v1",
        "execution": "one-retained-program-after-required-recheck-before-inference-v1",
        "admission": "existing-probe-budget-policy-or-durable-skip-v1",
        "interpretation": "model-authored-unverified-no-finish-gate-v1",
        "tool_description": TOOL_DESCRIPTION,
    }


def active_program(events: list[dict]) -> dict | None:
    starts = {}
    selected = None
    for event in events:
        payload = event["payload"]
        if event["event_type"] == "action_started":
            starts[payload["action_id"]] = payload
        elif event["event_type"] == "action_finished" and "probe_case" in payload:
            result = payload["result"]
            if (result["status"] == "succeeded"
                    and starts.get(result["action_id"], {}).get("arguments", {}).get(
                        "save_program") is True):
                selected = payload["probe_case"]["case_id"]
    # Eviction does not reactivate another old program.
    return probe_cases.saved_cases(events).get(selected)


@dataclass(frozen=True)
class ProbeRecheck:
    parent_action_id: str
    case_id: str
    definition_hash: str
    baseline_diff_hash: str
    candidate_diff_hash: str

    def call(self, run_id: str) -> RequestedTool:
        identity = sha256_json({"run_id": run_id, **asdict(self)})[7:39]
        return RequestedTool(name="run_probe", action_id=f"harness_probe_{identity}", arguments={
            "question": None, "python_source": None, "reference_action_id": None,
            "case_id": self.case_id, "save_program": False,
        })

    def payload(self, run_id: str) -> dict[str, Any]:
        return {"origin": "harness", "action_id": self.call(run_id).action_id, **asdict(self)}


def select(journal, latest_results: list[DevToolResult]) -> ProbeRecheck | None:
    if len(latest_results) != 1:
        return None
    mutation = latest_results[0]
    if mutation.tool != "replace_text" or mutation.status != "succeeded":
        return None
    baseline = mutation.output.get("baseline_diff_hash")
    candidate = mutation.output.get("worktree_diff_hash")
    if not isinstance(baseline, str) or not isinstance(candidate, str):
        raise RecoveryError("probe recheck requires durable mutation diff identities")
    if baseline == candidate:
        return None
    prefix = []
    for event in journal.events():
        if (event["event_type"] == "action_started"
                and event["payload"]["action_id"] == mutation.action_id):
            break
        prefix.append(event)
    else:
        raise RecoveryError("probe recheck mutation admission is missing")
    saved = active_program(prefix)
    if saved is None:
        return None
    return ProbeRecheck(mutation.action_id, saved["definition"]["case_id"],
                        saved["last_result"]["definition_hash"], baseline, candidate)


def context(journal, diff_hash: str) -> dict:
    events = journal.events()
    active = active_program(events)
    last = next((dict(e["payload"]) for e in reversed(events)
                 if e["event_type"] in {"probe_recheck_finished", "probe_recheck_skipped"}), None)
    if last is not None:
        last["currency"] = "current" if last["candidate_diff_hash"] == diff_hash else "historical"
    return {
        "policy": POLICY,
        "active_case_id": active["definition"]["case_id"] if active else None,
        "program_authorship": "model_authored_unverified",
        "behavior_verdict": "not_assessed",
        "instruction": "After edits the harness reruns the last retained saved program when "
                       "the existing probe budget permits. Inspect its observed output before "
                       "deciding the next action. A failed assertion may mean an invalid test; "
                       "exit zero does not prove correctness. New saves replace the active "
                       "program; manual reruns do not. This never blocks submission.",
        "last_result": last,
    }
