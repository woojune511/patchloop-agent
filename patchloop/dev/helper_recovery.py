"""One same-question correction for a proved pre-target request failure.

Host preflight or fresh explicit invocation markers must prove the phase. A
returned target exception is not a setup failure; correction is not verification.
"""

from __future__ import annotations

import copy

from patchloop.dev import probe_invocation
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes, sha256_json

POLICY = "helper-program-correction-v1"
ARGUMENT_POLICY = "original-argument-correction-v1"
ARGUMENT_CHANNEL = "invoke-declared-call-v9"


def _original_calls(start, result, execution_starts, execution_returns):
    """Accept only the exact, settled fresh original execution's valid call rows."""
    arguments = start.get("arguments", {})
    purpose = arguments.get("purpose")
    binding = start.get("reproduction_binding") or {}
    definition = binding.get("definition", {})
    output = result.get("output") or {}
    observed = output.get("reproduction") or {}
    trace = observed.get("call_observation") or {}
    calls = trace.get("calls")
    started = execution_starts.get(start.get("action_id"), [])
    returned = execution_returns.get(start.get("action_id"), [])
    source = arguments.get("python_source")
    if (start.get("tool") != "run_probe" or result.get("tool") != "run_probe"
            or start.get("probe_request", {}).get("status") != "accepted"
            or not isinstance(purpose, dict) or purpose.get("kind") != "original_requirement"
            or arguments.get("replay_action_id") is not None
            or result.get("status") != "succeeded"
            or not start.get("input_hash") or result.get("input_hash") != start["input_hash"]
            or result.get("action_id") != start.get("action_id")
            or binding.get("root_action_id") != start.get("action_id")
            or not isinstance(source, str)
            or binding.get("program_hash") != sha256_bytes(source.encode("utf-8"))
            or observed.get("binding") != binding
            or definition.get("observation_channel") != ARGUMENT_CHANNEL
            or trace.get("binding_method") != ARGUMENT_CHANNEL
            or result.get("workspace_diff_hash") != start.get("baseline_diff_hash")
            or output.get("diff_hash") != start.get("baseline_diff_hash")
            or output.get("probe_stage") != "execution_returned"
            or len(started) != 1 or len(returned) != 1
            or not isinstance(calls, list) or not 1 <= len(calls) <= 4
            or type(trace.get("incomplete")) is not bool
            or not all(probe_invocation.valid_call(
                call, definition.get("entrypoint"), channel=ARGUMENT_CHANNEL) for call in calls)
            or len({call["call_id"] for call in calls}) != len(calls)):
        return None
    identity = started[0]
    if (not identity.get("execution_source_hash")
            or identity.get("input_hash") != start["input_hash"]
            or identity.get("baseline_diff_hash") != start["baseline_diff_hash"]
            or {key: returned[0].get(key) for key in identity} != identity
            or returned[0].get("output", {}).get("source_hash")
            != identity["execution_source_hash"]
            or output.get("execution_source_hash") != identity["execution_source_hash"]):
        return None
    for receipt in (output, returned[0].get("output", {})):
        if (receipt.get("status") not in {"passed", "failed"}
                or type(receipt.get("exit_code")) is not int or receipt["exit_code"] < 0
                or any(receipt.get(key) is not False for key in (
                    "timed_out", "truncated", "cleanup_failed", "deadline_exhausted"))
                or receipt.get("execution_policy", {}).get("cleanup_status") != "confirmed"):
            return None
    return calls


def _binding_error(start, result, execution_starts, execution_returns):
    calls = _original_calls(start, result, execution_starts, execution_returns)
    if not calls or any(call.get("target_started") is not False for call in calls):
        return None
    failures = [call for call in calls if call.get("binding_error") is True
                and isinstance(call.get("signature"), str) and call["signature"]
                and len(call["signature"]) <= 256
                and (call.get("exception") or {}).get("type") == "builtins.TypeError"]
    if not failures:
        return None
    return {
        "kind": "argument_binding", "phase": "before_target",
        "source_hash": sha256_bytes(start["arguments"]["python_source"].encode("utf-8")),
        "calls": [{key: copy.deepcopy(call[key]) for key in (
            "call_id", "entrypoint", "signature", "arguments", "argv", "exception")}
            for call in failures],
    }


def review(events, current_diff):
    """Derive a run-wide ticket from durable admission/result identities."""
    inactive = {"policy": POLICY, "status": "not_needed", "blocked": False}
    starts = {e["payload"]["action_id"]: e["payload"] for e in events
              if e["event_type"] == "action_started"}
    results = {e["payload"]["result"]["action_id"]: e["payload"]["result"] for e in events
               if e["event_type"] == "action_finished"}
    dispatched = {e["payload"]["action_id"] for e in events
                  if e["event_type"] == "probe_execution_started"}
    execution_starts, execution_returns = {}, {}
    for event in events:
        target = (execution_starts if event["event_type"] == "probe_execution_started" else
                  execution_returns if event["event_type"] == "probe_execution_finished" else None)
        if target is not None:
            target.setdefault(event["payload"]["action_id"], []).append(event["payload"])
    root, root_error, policy = None, None, POLICY
    for event in events:
        if event["event_type"] != "action_finished":
            continue
        result = event["payload"]["result"]
        if result["tool"] == "replace_text" and result["status"] == "succeeded":
            break  # This correction addresses reaching the first repair only.
        start = starts.get(result["action_id"], {})
        error = start.get("helper_program_error")
        if (result["tool"] == "run_probe" and result["status"] == "failed"
                and error and start.get("arguments", {}).get("purpose") == {"kind": "helper"}
                and start.get("probe_request", {}).get("status") == "rejected"
                and result["action_id"] not in dispatched
                and result.get("output", {}).get("helper_program_error") == error):
            root = start
            root_error = error
            break
        error = _binding_error(start, result, execution_starts, execution_returns)
        if error is not None:
            root, root_error, policy = start, error, ARGUMENT_POLICY
            break
    if root is None:
        return inactive
    binding = {
        "policy": policy, "root_action_id": root["action_id"],
        "root_input_hash": root["input_hash"], "diff_hash": root["baseline_diff_hash"],
        "question_hash": sha256_json(root["arguments"]["question"]),
        "source_hash": root_error["source_hash"],
    }
    attempts = [s for s in starts.values() if s.get("helper_recovery_link") == binding]
    attempt = attempts[0] if attempts else None
    returned = results.get(attempt["action_id"]) if attempt else None
    status = "pending"
    if attempt:
        # A target exception/assertion may be useful evidence. A known returned
        # execution settles this program correction, never the diagnostic question.
        output = (returned or {}).get("output", {})
        healthy = (returned is not None and returned["status"] == "succeeded"
                   and attempt["action_id"] in dispatched
                   and output.get("probe_stage") == "execution_returned"
                   and output.get("status") in {"passed", "failed"}
                   and not output.get("cleanup_failed")
                   and not output.get("deadline_exhausted"))
        if policy == ARGUMENT_POLICY:
            calls = _original_calls(
                attempt, returned or {}, execution_starts, execution_returns)
            healthy = bool(calls and all(call["target_started"]
                           and not call["binding_error"]
                           and call["capture"]["status"] == "complete" for call in calls))
        healthy &= len(attempts) == 1
        status = "execution_returned" if healthy else "verification_incomplete"
    elif current_diff != binding["diff_hash"]:
        status = "verification_incomplete"
    return {
        **binding, "status": status, "blocked": status != "execution_returned",
        "question": root["arguments"]["question"],
        "python_source": root["arguments"]["python_source"] if not attempt else None,
        "error": copy.deepcopy(root_error),
        **({"purpose": copy.deepcopy(root["arguments"]["purpose"]),
            "call_path": copy.deepcopy(root["arguments"].get("call_path"))}
           if policy == ARGUMENT_POLICY else {}),
        "correction_action_id": attempt["action_id"] if attempt else None,
        "execution_status": (returned or {}).get("output", {}).get("status"),
        "behavior_verdict": "not_assessed", "remaining_attempts": int(not attempt),
        "interpretation": (
            "Argument binding failed before any declared target entered. Inspect the actual "
            "signature and arguments, then submit changed source with the same question, "
            "purpose and call-path request using a new action_id, or stop. This run permits "
            "one correction request; rejection or another pre-target failure cannot renew it. "
            "Actual target entry settles argument correction only, not original reproduction."
        ) if policy == ARGUMENT_POLICY else (
            "The original helper program was rejected before any execution. Correct its source "
            "for the exact same question with a new action_id, or stop. One correction request "
            "is allowed in this run; no unrelated inspection can spend it. A returned execution "
            "settles program correction only; inspect its output before drawing conclusions."
        ),
    }


def link(state):
    return {key: state[key] for key in ("policy", "root_action_id", "root_input_hash",
                                       "diff_hash", "question_hash", "source_hash")}


def correction_available(state, obligation=None):
    """A correction consumes existing acquisition slots, including disabled gates."""
    if state.get("status") != "pending":
        return False
    if state.get("policy") != ARGUMENT_POLICY:
        return True
    if not obligation or obligation.get("stage") not in {"pending", "disabled"}:
        return False
    if obligation.get("reason") not in {"awaiting_original", "preparation_action_limit"}:
        return False
    for count, maximum in (("original_attempts_reserved", "max_original_attempts"),
                           ("request_errors", "max_request_errors")):
        value, ceiling = obligation.get(count), obligation.get(maximum)
        if type(value) is not int or type(ceiling) is not int or not 0 <= value < ceiling:
            return False
    return all(obligation.get(key) == 0 for key in (
        "pending_original_requests", "pending_original_dispatches", "pending_original_results",
        "uncertain_original_dispatches"))


def validate(state, tool, arguments, *, original_obligation=None):
    if not state.get("blocked") or tool == "stop_task":
        return None
    source = arguments.get("python_source")
    if (correction_available(state, original_obligation) and tool == "run_probe"
            and arguments.get("purpose") == state.get("purpose", {"kind": "helper"})
            and arguments.get("replay_action_id") is None
            and arguments.get("call_path") == state.get("call_path")
            and arguments.get("question") == state["question"]
            and isinstance(source, str)
            and sha256_bytes(source.encode("utf-8")) != state["source_hash"]):
        return link(state)
    raise ContractError(
        "Correct the pre-target source for the same question and purpose with a new action_id, "
        "or stop; its one correction cannot be replaced by exploration or source mutation.",
        details={"helper_correction": copy.deepcopy(state)},
    )
