"""One bounded baseline-judgment correction, derived from immutable public receipts.

A correction replaces only a proved conflicting or structurally invalid observation. It cannot
retire a healthy failure, change a caller or weaken the frozen expected outcome.
"""

from __future__ import annotations

import copy

from patchloop.dev import probe_call_capture, probe_comparison, probe_invocation, probe_requests
from patchloop.util import sha256_bytes

POLICY = "observation-correction-v1"
JUDGMENT_POLICY = "captured-diagnostic-v1"
EMPTY_DIFF = sha256_bytes(b"")
MAX_ATTEMPTS = 1


def shape_error(observation):
    """Recompute narrow v11 observation validity from public values, not model labels."""
    definition = observation.get("binding", {}).get("definition", {})
    if (definition.get("observation_channel") != probe_invocation.API_CHANNEL
            or definition.get("diagnostic_rules")
            or observation.get("reason") not in {None, "observation_shape_mismatch"}):
        return None
    return probe_comparison.object_field_mismatch(definition, observation.get("observed_json"))


def _reproduction(result):
    return (result.get("output") or {}).get("reproduction") or {}


def _target(start):
    # Count the request, even when preflight rejects it before binding/dispatch.
    purpose = start.get("arguments", {}).get("purpose")
    return purpose.get("corrects_action_id") if isinstance(purpose, dict) else None


def _definition(binding):
    return {key: value for key, value in binding["definition"].items()
            if key != "corrects_action_id"}


def _complete(result):
    output = result.get("output") or {}
    reproduction = _reproduction(result)
    trace = reproduction.get("call_observation", {})
    definition = reproduction.get("binding", {}).get("definition", {})
    calls = trace.get("calls", [])
    return bool(
        result.get("status") == "succeeded" and output.get("status") == "passed"
        and type(output.get("exit_code")) is int and output["exit_code"] == 0
        and not any(output.get(key) for key in (
            "timed_out", "truncated", "cleanup_failed", "deadline_exhausted"))
        and output.get("execution_policy", {}).get("cleanup_status") == "confirmed"
        and output.get("setup_checks", {}).get("status") != "failed"
        and trace.get("binding_method") in probe_invocation.CAPTURE_CHANNELS
        and calls and trace.get("incomplete") is False
        and all(probe_invocation.valid_call(call, definition.get("entrypoint"),
                                           channel=trace["binding_method"]) for call in calls)
        and not probe_call_capture.incomplete(calls)
    )


def _is_conflict(result):
    reproduction = _reproduction(result)
    judgment = reproduction.get("judgment", {})
    return (judgment.get("policy") == JUDGMENT_POLICY
            and judgment.get("status") == "conflict"
            and reproduction.get("reason") == "observation_conflict") or bool(
                shape_error(reproduction)
                and result.get("workspace_diff_hash") == EMPTY_DIFF
                and reproduction.get("binding", {}).get("root_action_id")
                == result.get("action_id"))


def _baseline_conflict(result):
    reproduction = _reproduction(result)
    binding = reproduction.get("binding", {})
    return (_is_conflict(result) and _complete(result)
            and result.get("workspace_diff_hash") == EMPTY_DIFF
            and binding.get("root_action_id") == result.get("action_id")
            and (bool(binding.get("definition", {}).get("diagnostic_rules"))
                 or bool(shape_error(reproduction))))


def _correction_reason(previous, current, start):
    """Return a failure reason, or None for a fresh same-condition baseline proof."""
    before, after = _reproduction(previous), _reproduction(current)
    old, new = before.get("binding", {}), after.get("binding", {})
    if not _baseline_conflict(previous):
        return "target_not_baseline_conflict"
    if not new or new.get("root_action_id") != start["action_id"]:
        return "correction_not_fresh"
    if (current.get("workspace_diff_hash") != EMPTY_DIFF
            or start.get("baseline_diff_hash") != EMPTY_DIFF):
        return "correction_not_on_base"
    if (_target(start) != previous["action_id"]
            or new["definition"].get("corrects_action_id") != previous["action_id"]):
        return "correction_link_changed"
    if _definition(old) != _definition(new):
        return "correction_declarations_changed"
    if old.get("program_hash") == new.get("program_hash"):
        return "correction_program_unchanged"
    if not _complete(current):
        return "correction_execution_incomplete"
    judgment = after.get("judgment", {})
    object_fields = shape_error(before) is not None
    if (after.get("reason") is not None or (not object_fields and (
            judgment.get("policy") != JUDGMENT_POLICY
            or judgment.get("status") != "consistent"))):
        return "correction_judgment_unresolved"
    if (after.get("comparison") != "mismatched"
            or after.get("declared_failure_comparison") != "matched"
            or after.get("observed_json") != new["definition"].get("reported_failure_json")
            or (not object_fields and after.get("observed_json") != judgment.get("host_json"))):
        return "correction_failure_not_reproduced"
    if probe_invocation.conditions(before["call_observation"]) != (
            probe_invocation.conditions(after["call_observation"])):
        return "correction_conditions_changed"
    return None


def review(events, current_diff):
    """Project correction capacity and lineage; never mutate or re-execute a receipt."""
    starts, results, attempts, conflicts = {}, {}, [], []
    result_positions = {}
    for position, event in enumerate(events):
        payload = event["payload"]
        if event["event_type"] == "action_started" and payload.get("tool") in {
                "run_probe", "observe_original"}:
            starts[payload["action_id"]] = payload
            if _target(payload):
                attempts.append((position, payload))
        elif event["event_type"] == "action_finished":
            result = payload["result"]
            if result.get("tool") in {"run_probe", "observe_original"}:
                results[result["action_id"]] = result
                result_positions[result["action_id"]] = position
                if _is_conflict(result):
                    conflicts.append(result)

    corrections, superseded = [], []
    attempt_reason = None
    if attempts:
        position, start = attempts[0]
        previous, current = results.get(_target(start)), results.get(start["action_id"])
        if previous is None or result_positions.get(_target(start), position) >= position:
            attempt_reason = "correction_target_unobserved"
        elif current is not None:
            attempt_reason = _correction_reason(previous, current, start)
            if attempt_reason is None:
                old, new = _reproduction(previous)["binding"], _reproduction(current)["binding"]
                corrections.append({"previous_action_id": previous["action_id"],
                                    "corrected_action_id": current["action_id"],
                                    "previous_case_id": old["case_id"],
                                    "corrected_case_id": new["case_id"]})
                superseded.append(old["case_id"])

    unresolved = [result for result in conflicts
                  if _reproduction(result).get("binding", {}).get("case_id") not in superseded]
    target = unresolved[0] if unresolved else None
    attempt = attempts[0][1] if attempts else None
    pending_started = bool(attempt and attempt["action_id"] not in results)
    if target is None:
        status, reason = ("corrected", "same_condition_baseline_confirmed") if corrections else (
            "none", None)
    elif not _baseline_conflict(target):
        status, reason = "failed", "target_not_baseline_conflict"
    elif current_diff != EMPTY_DIFF:
        status, reason = "failed", "baseline_changed_before_correction"
    elif attempt is None:
        status, reason = "pending", "awaiting_observation_correction"
    elif pending_started and _target(attempt) == target["action_id"]:
        status, reason = "pending", "correction_attempt_pending"
    else:
        status, reason = "failed", attempt_reason or "correction_allowance_spent"
    if unresolved and len(attempts) > MAX_ATTEMPTS:
        status, reason = "failed", "correction_allowance_spent"
    target_arguments = (starts.get(target["action_id"], {}).get("arguments", {})
                        if target is not None else {})
    target_error = shape_error(_reproduction(target)) if target is not None else None
    return {
        "policy": POLICY, "status": status, "reason": reason,
        **({"kind": target_error["kind"], "target_observation_error": target_error}
           if target_error is not None else {}),
        "blocked": bool(unresolved), "pending_started": pending_started,
        "attempts_used": len(attempts), "max_attempts": MAX_ATTEMPTS,
        "target_action_id": target["action_id"] if target else None,
        "target_case_id": _reproduction(target)["binding"]["case_id"] if target else None,
        "target_judgment": copy.deepcopy(_reproduction(target).get("judgment")) if target else None,
        "target_request": (copy.deepcopy({key: target_arguments[key]
                                         for key in ("question", "python_source", "purpose")
                                         if key in target_arguments}) if target else None),
        "target_action_ids": [result["action_id"] for result in unresolved],
        "attempt_action_id": attempt["action_id"] if attempt else None,
        "superseded_case_ids": superseded, "corrections": corrections,
    }


def note_updates(state):
    """Action-linked interpretations need review; their raw statements stay intact."""
    updates = {row["previous_action_id"]: row for row in state["corrections"]}
    for action_id in state["target_action_ids"]:
        updates.setdefault(action_id, {
            "previous_action_id": action_id, "corrected_action_id": None,
            "reason": ("observation_fields_conflict_with_declarations"
                       if state.get("kind") == "object_field_mismatch"
                       else "captured_output_conflicts_with_authored_judgment"),
        })
    return updates


def validate(binding, source, events, *, current_diff, action_id, replay=False,
             require_correction=True):
    """Admit only the one explicit fresh correction; completed-ID recovery is external."""
    # A persisted in-flight action owns its spent allowance. Its binding/source
    # identity is checked by the gateway before resuming its durable execution.
    prior = [event for event in events if not (
        event["event_type"] == "action_started"
        and event["payload"].get("action_id") == action_id)]
    state = review(prior, current_diff)
    corrects = (binding or {}).get("definition", {}).get("corrects_action_id")
    if replay:
        if require_correction and state["blocked"]:
            raise probe_requests.error("Correct the conflicting observation with a fresh probe",
                                       "/replay_action_id", "/purpose/corrects_action_id")
        return
    if not corrects:
        if require_correction and state["blocked"]:
            raise probe_requests.error("The unresolved observation requires corrects_action_id",
                                       "/purpose/corrects_action_id")
        return
    if state["attempts_used"] >= MAX_ATTEMPTS:
        raise probe_requests.error("The one observation correction attempt is already spent",
                                   "/purpose/corrects_action_id")
    if state["status"] != "pending" or state["target_action_id"] != corrects:
        raise probe_requests.error("Correction must reference the pending baseline conflict",
                                   "/purpose/corrects_action_id")
    previous = next(event["payload"]["result"] for event in events
                    if event["event_type"] == "action_finished"
                    and event["payload"]["result"].get("action_id") == corrects)
    old = _reproduction(previous)["binding"]
    if _definition(old) != _definition(binding):
        raise probe_requests.error("Correction preserves caller, rules, failure and desired values",
                                   "/purpose")
    if (not isinstance(source, str) or binding.get("program_hash") != sha256_bytes(source.encode())
            or old["program_hash"] == binding["program_hash"]
            or binding.get("root_action_id") != action_id):
        raise probe_requests.error("Correction requires a fresh changed observation program",
                                   "/python_source")
