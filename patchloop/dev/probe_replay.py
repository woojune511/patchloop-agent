"""Explicit reuse of a completed public probe's program on the current diff."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_bytes, sha256_json

DESCRIPTION = (
    "To rerun an earlier completed public probe on the current diff, set replay_action_id "
    "to its action_id and question/python_source to null; otherwise set replay_action_id "
    "null. This reuses the exact question and program, including assertions, without "
    "requiring an earlier save. Do not combine action replay with saving or selecting "
    "a case. A completed assertion or import failure can "
    "be rerun; an incomplete or uncertain execution cannot. The new result tests the "
    "current diff, not the old snapshot, and grants no required-check credit."
)


class ReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    replay_action_id: str = Field(min_length=1, max_length=500)
    question: None = None
    python_source: None = None
    case_id: None = None
    reference_action_id: None = None
    save_program: Literal[False] = False


def prepare(arguments: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Resolve only this run's completed, identity-bound public executions."""
    intent = ReplayRequest.model_validate(arguments)
    started = None
    result = None
    for event in events:
        payload = event["payload"]
        if payload.get("action_id") != intent.replay_action_id:
            continue
        if event["event_type"] == "action_started":
            started = payload
        elif event["event_type"] == "action_finished" and started is not None:
            result = payload["result"]
            break
    if (started is None or result is None or started.get("tool") != "run_probe"
            or result.get("tool") != "run_probe" or result.get("status") != "succeeded"):
        raise ContractError("replay_action_id must name a completed public probe in this run")
    output = result["output"]
    if (output.get("status") not in {"passed", "failed", "timeout", "output_limit"}
            or output.get("cleanup_failed")
            or output.get("execution_policy", {}).get("cleanup_status") != "confirmed"):
        raise ContractError("replay requires a completed probe with confirmed cleanup")
    program = (started.get("probe_replay_request") or started.get("probe_case_request")
               or started["arguments"])
    question, source = program.get("question"), program.get("python_source")
    if (not isinstance(question, str) or not 1 <= len(question) <= 500
            or not isinstance(source, str) or not 1 <= len(source) <= 8_000):
        raise RecoveryError("prior probe has no bound question and program")
    action_input = {"tool": started["tool"], "arguments": started["arguments"]}
    if started.get("turn_decision") is not None:
        action_input["turn_decision"] = started["turn_decision"]
    source_hash = sha256_bytes(source.encode("utf-8"))
    if (started["input_hash"] != result["input_hash"]
            or started["input_hash"] != sha256_json(action_input)
            or result["action_id"] != intent.replay_action_id
            or output.get("source_hash") != source_hash
            or output.get("question") != question
            or not isinstance(result.get("workspace_diff_hash"), str)
            or result["workspace_diff_hash"] != output.get("diff_hash")
            or result["workspace_diff_hash"] != started.get("baseline_diff_hash")):
        raise RecoveryError("prior probe program or execution identity is inconsistent")
    return {
        "question": question, "python_source": source, "case": None,
        "replayed_from": {
            "action_id": intent.replay_action_id, "input_hash": result["input_hash"],
            "diff_hash": result["workspace_diff_hash"], "source_hash": source_hash,
        },
    }
