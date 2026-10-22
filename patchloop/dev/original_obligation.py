"""Public task obligation and a bounded, recoverable acquisition opportunity."""

from __future__ import annotations

from patchloop.errors import RecoveryError
from patchloop.util import sha256_bytes, sha256_json

POLICY = "original-obligation-v1"
ACQUISITION = "bounded-v1"
MAX_ATTEMPTS = 2
MAX_ACTIONS = 6
EMPTY_DIFF = sha256_bytes(b"")
INVESTIGATION_TOOLS = frozenset({"read_file", "search_files", "search_history", "run_probe"})


def definition(public_task):
    task_hash = sha256_json(public_task.model_dump(mode="json"))
    return {
        "policy": POLICY, "obligation_id": sha256_json({"policy": POLICY, "task": task_hash}),
        "public_task_hash": task_hash,
        "requirement": "Reproduce the public report on the unchanged base and replay its caller, "
        "inputs, setup and expected behavior on the submitted candidate.",
        "requirement_mapping": "model_authored_unverified",
    }


def ensure(journal, public_task, acquisition):
    expected = {**definition(public_task), "acquisition_policy": acquisition,
                "max_original_attempts": MAX_ATTEMPTS, "max_investigation_actions": MAX_ACTIONS}
    records = [e["payload"] for e in journal.events()
               if e["event_type"] == "original_obligation_registered"]
    if records:
        if records != [expected]:
            raise RecoveryError("original public obligation identity changed")
    elif acquisition != "none":
        journal.append("original_obligation_registered", expected)


def release(journal, public_task, reason):
    if reason not in {"completion_budget", "probe_unavailable"}:
        raise ValueError("unknown acquisition release reason")
    identity = definition(public_task)["obligation_id"]
    previous = [e["payload"] for e in journal.events()
                if e["event_type"] == "original_acquisition_released"]
    if previous:
        if len(previous) != 1 or previous[0].get("obligation_id") != identity:
            raise RecoveryError("original acquisition release identity changed")
        return
    journal.append("original_acquisition_released", {
        "obligation_id": identity, "reason": reason,
    })


def review(events, public_task, completion, *, acquisition="none", probe_available=True):
    """Derive truth from receipts; plans, helper passes and releases confer no credit."""
    identity = definition(public_task)
    starts, results, releases = {}, {}, []
    for event in events:
        payload = event["payload"]
        if event["event_type"] == "action_started":
            starts[payload["action_id"]] = payload
        elif event["event_type"] == "action_finished":
            result = payload["result"]
            results[result["action_id"]] = result
        elif event["event_type"] == "original_acquisition_released":
            releases.append(payload)
    if any(row.get("obligation_id") != identity["obligation_id"] for row in releases):
        raise RecoveryError("original acquisition release refers to another task")
    # Count attempts once at durable admission, including invalid setup, but never
    # turn rejected edits or duplicate replay into acquisition budget consumption.
    attempts = [key for key, row in starts.items() if row.get("tool") == "run_probe"
                and row.get("baseline_diff_hash") == EMPTY_DIFF
                and isinstance(row.get("arguments", {}).get("purpose"), dict)
                and row["arguments"]["purpose"].get("kind")
                == "original_requirement"]
    actions = sum(row.get("tool") in INVESTIGATION_TOOLS
                  and row.get("baseline_diff_hash") == EMPTY_DIFF for row in starts.values())
    pending = any(key not in results for key in attempts)
    roots = completion.get("baseline_failure_case_ids", [])
    matched = completion.get("baseline_matched_count", 0)
    acquisition_status = ("acquired" if roots else "setup_blocked" if not probe_available
                          else "not_reproduced" if matched
                          else "setup_blocked" if attempts else "not_attempted")
    reason = ("baseline_failure_observed" if roots else releases[0]["reason"] if releases
              else "probe_unavailable" if not probe_available else "attempt_pending" if pending
              else "original_attempt_limit" if len(attempts) >= MAX_ATTEMPTS
              else "investigation_action_limit" if actions >= MAX_ACTIONS else "awaiting_original")
    stage = ("acquired" if roots else "disabled" if acquisition == "none" else "released"
             if releases or not probe_available else "pending" if pending else "released"
             if len(attempts) >= MAX_ATTEMPTS or actions >= MAX_ACTIONS else "pending")
    status = ("refuted" if completion["status"] == "refuted" else "verified"
              if roots and completion["status"] == "cases_verified" else "unverified")
    return {
        **identity, "status": status, "acquisition_policy": acquisition,
        "acquisition_status": acquisition_status, "stage": stage, "reason": reason,
        "original_attempts": len(attempts), "investigation_actions": actions,
        "max_original_attempts": MAX_ATTEMPTS, "max_investigation_actions": MAX_ACTIONS,
        "baseline_failure_case_ids": roots, "current_diff_hash": completion["current_diff_hash"],
        "interpretation": "Only selected public cases; issue-to-caller mapping is unverified. "
        "Releasing acquisition, helper/check PASS and independent acceptance do not discharge "
        "missing original evidence.",
    }
