"""Public task obligation and a bounded, recoverable acquisition opportunity."""

from __future__ import annotations

from patchloop.errors import RecoveryError
from patchloop.util import sha256_bytes, sha256_json

POLICY = "original-obligation-v1"
ACQUISITION = "bounded-v1"
MAX_ATTEMPTS = 2
MAX_ACTIONS = 6
MAX_REQUEST_ERRORS = 2
PROBE_STAGES = "probe-stages-v1"
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
    legacy = {**definition(public_task), "acquisition_policy": acquisition,
              "max_original_attempts": MAX_ATTEMPTS, "max_investigation_actions": MAX_ACTIONS}
    expected = {**legacy, "accounting_policy": PROBE_STAGES,
                "max_request_errors": MAX_REQUEST_ERRORS}
    records = [e["payload"] for e in journal.events()
               if e["event_type"] == "original_obligation_registered"]
    if records:
        if records not in ([expected], [legacy]):
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
    starts, results, dispatched, returned, releases = {}, {}, {}, {}, []
    for event in events:
        payload = event["payload"]
        if event["event_type"] == "action_started":
            starts[payload["action_id"]] = payload
        elif event["event_type"] == "action_finished":
            result = payload["result"]
            results[result["action_id"]] = result
        elif event["event_type"] == "probe_execution_started":
            dispatched[payload["action_id"]] = payload
        elif event["event_type"] == "probe_execution_finished":
            returned[payload["action_id"]] = payload
        elif event["event_type"] == "original_acquisition_released":
            releases.append(payload)
    if any(row.get("obligation_id") != identity["obligation_id"] for row in releases):
        raise RecoveryError("original acquisition release refers to another task")
    baseline_probes = {key: row for key, row in starts.items()
                       if row.get("tool") == "run_probe"
                       and row.get("baseline_diff_hash") == EMPTY_DIFF}
    originals = {key: row for key, row in baseline_probes.items()
                 if request_kind(row.get("arguments", {}), row.get("reproduction_binding"))
                 == "original_requirement"}
    # A rejected request never reaches dispatch. Old receipts cannot establish
    # that distinction, so reserve their old slots without calling them executions.
    legacy = [key for key, row in originals.items()
              if "probe_request" not in row and key not in dispatched]
    attempts = [key for key in originals if key in dispatched]
    request_errors = [key for key, row in baseline_probes.items()
                      if row.get("probe_request", {}).get("status") == "rejected"
                      and row["probe_request"].get("kind") != "helper"]
    pending_requests = [key for key, row in originals.items()
                        if key not in dispatched and key not in results
                        and row.get("probe_request", {}).get("status") == "accepted"]
    pending_dispatches = [key for key in attempts if key not in returned and key not in results]
    pending_results = [key for key in attempts if key in returned and key not in results]
    uncertain_dispatches = [key for key in attempts if key not in returned
                            and results.get(key, {}).get("output", {}).get("probe_stage")
                            == "dispatch_pending"]
    pending = bool(pending_requests or pending_dispatches or pending_results
                   or any(key not in results for key in legacy))
    reserved = len(attempts) + len(legacy)
    setup_failures = sum(
        results.get(key, {}).get("output", {}).get("reproduction", {}).get("comparison")
        == "not_compared"
        and results[key]["output"].get("status") != "passed" for key in attempts)
    actions = sum(row.get("tool") in INVESTIGATION_TOOLS
                  and row.get("baseline_diff_hash") == EMPTY_DIFF for row in starts.values())
    roots = completion.get("baseline_failure_case_ids", [])
    matched = completion.get("baseline_matched_count", 0)
    observed = completion.get("baseline_observed_count", 0)
    acquisition_status = ("acquired" if roots else "setup_blocked" if not probe_available
                          else "not_reproduced" if matched or observed
                          else "setup_blocked" if attempts or legacy
                          else "request_blocked" if request_errors else "not_attempted")
    reason = ("baseline_failure_observed" if roots else releases[0]["reason"] if releases
              else "probe_unavailable" if not probe_available else "attempt_pending" if pending
              else "request_error_limit" if len(request_errors) >= MAX_REQUEST_ERRORS
              else "original_attempt_limit" if reserved >= MAX_ATTEMPTS
              else "investigation_action_limit" if actions >= MAX_ACTIONS else "awaiting_original")
    stage = ("acquired" if roots else "disabled" if acquisition == "none" else "released"
             if releases or not probe_available else "pending" if pending else "released"
             if reserved >= MAX_ATTEMPTS or actions >= MAX_ACTIONS
             or len(request_errors) >= MAX_REQUEST_ERRORS else "pending")
    status = ("refuted" if completion["status"] == "refuted" else "verified"
              if roots and completion["status"] == "cases_verified" else "unverified")
    return {
        **identity, "status": status, "acquisition_policy": acquisition,
        "acquisition_status": acquisition_status, "stage": stage, "reason": reason,
        "original_attempts": len(attempts), "investigation_actions": actions,
        "accounting_policy": PROBE_STAGES, "request_errors": len(request_errors),
        "max_request_errors": MAX_REQUEST_ERRORS,
        "original_attempts_reserved": reserved,
        "legacy_uncertain_original_attempts": len(legacy),
        "pending_original_requests": len(pending_requests),
        "pending_original_dispatches": len(pending_dispatches),
        "pending_original_results": len(pending_results),
        "uncertain_original_dispatches": len(uncertain_dispatches),
        "original_execution_results": sum(key in returned for key in attempts),
        "original_setup_failures": setup_failures,
        "max_original_attempts": MAX_ATTEMPTS, "max_investigation_actions": MAX_ACTIONS,
        "baseline_failure_case_ids": roots, "current_diff_hash": completion["current_diff_hash"],
        "interpretation": "Only selected public cases; issue-to-caller mapping is unverified. "
        "Releasing acquisition, helper/check PASS and independent acceptance do not discharge "
        "missing original evidence.",
    }


def request_kind(arguments, binding=None):
    """Classify declared intent without granting rejected/untyped requests evidence."""
    if binding is not None or arguments.get("reproduction") is not None:
        return "original_requirement"
    purpose = arguments.get("purpose")
    if isinstance(purpose, dict) and purpose.get("kind") in ("original_requirement", "helper"):
        return purpose["kind"]
    return "unclassified" if "purpose" in arguments else "helper"
