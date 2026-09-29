"""Public unsuccessful executions, derived from durable actions, not bug verdicts."""

from __future__ import annotations

from typing import Any


def verification_observation(result: dict[str, Any]) -> dict[str, Any] | None:
    tool = result.get("tool")
    if tool not in {"run_check", "run_probe"}:
        return None
    output = result.get("output", {})
    unhealthy = any(output.get(k, False) for k in (
        "timed_out", "deadline_exhausted", "cleanup_failed", "truncated",
    ))
    failed = (result.get("status") != "succeeded" or unhealthy
              or (tool == "run_check" and output.get("passed") is False)
              or (tool == "run_probe" and (
                  output.get("status") == "failed"
                  or (type(output.get("exit_code")) is int and output["exit_code"] != 0))))
    if not failed:
        return None
    return {
        "action_id": result["action_id"], "input_hash": result["input_hash"],
        "origin": "registered_check" if tool == "run_check" else "agent_probe",
        "tool": tool, "diff_hash": result.get("workspace_diff_hash"),
        "action_status": result.get("status"),
        "error_code": result.get("error_code"),
        "execution": {k: output[k] for k in (
            "passed", "status", "exit_code", "timed_out", "deadline_exhausted",
            "cleanup_failed", "truncated",
        ) if k in output},
        "subject": str(output.get("check_id") or output.get("question") or tool)[:400],
        "behavior_verdict": "not_assessed",
    }


def project_verification_observations(
    results: list[dict[str, Any]], concerns: list[dict[str, Any]], *, diff_hash: str,
) -> dict[str, Any]:
    observations = {}
    for result in results:
        item = verification_observation(result)
        if item is not None:
            observations[item["action_id"]] = item
    items = list(observations.values())
    for item in items:
        item["currency"] = (
            "unknown" if item["diff_hash"] is None else
            "current" if item["diff_hash"] == diff_hash else "historical"
        )
        item["concern_ids"] = [c["concern_id"] for c in concerns
                               if c.get("observation", {}).get("action_id") == item["action_id"]]
    return {
        "items": items[-6:], "omitted_count": max(0, len(items) - 6),
        "interpretation": "Unsuccessful public executions, not confirmed bugs. Invalid probes "
        "and candidate failures are not distinguished without interpretation. Later PASS does "
        "not erase an observation. Full records remain in the action journal; linking a concern "
        "does not resolve it. This catalog never blocks submission.",
    }
