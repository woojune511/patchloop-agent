"""Positive selected-call failure evidence, separate from whole-case comparability."""
from __future__ import annotations

from patchloop.dev import probe_invocation
from patchloop.util import sha256_json


def summaries(trace):
    calls = trace.get("calls", [])
    return {
        "calls": [_outcome(call) for call in calls[:4]],
        "omitted_call_count": max(0, len(calls) - 4),
        "observation_incomplete": trace.get("incomplete", True),
        "verification_credit": False,
    }


def _outcome(call):
    exception = call.get("exception") or {}
    return {
        "call_id": call.get("call_id"), "outcome": call.get("outcome"),
        "capture_status": (call.get("capture") or {}).get("status", "unavailable"),
        "exception": ({"type": exception.get("type"),
                       "message": str(exception.get("message", ""))[:256]}
                      if exception else None),
        "exit_code": call.get("exit_code"),
        "unexpected_exception": (
            call.get("outcome") == "raised" and bool(exception)
            and exception.get("type") not in call.get("exception_policy", [])
            and exception.get("type") not in {"SystemExit", "builtins.SystemExit"}
        ),
    }


def _selected_conditions(trace, call):
    conditions = probe_invocation.conditions({**trace, "calls": [call]})
    # Global incomplete concerns all calls; it must remain in the public packet,
    # but does not erase positive evidence about this one fully captured call.
    return {key: conditions[key] for key in ("calls", "execution_environment")}


def bound_failure(root, candidate):
    """Require a qualified root at the caller; never grant equality/PASS credit."""
    result, observation = candidate
    trace = observation["call_observation"]
    baseline = root[1]["call_observation"]
    output = result.get("output") or {}
    # A settled helper failure does not erase an earlier complete target capture.
    # Keep the outer receipt intact; only selected negative evidence qualifies here.
    exit_code = output.get("exit_code")
    if (trace.get("binding_method") not in probe_invocation.CAPTURE_CHANNELS
            or observation["binding"] != root[1]["binding"]
            or result.get("status") != "succeeded" or type(exit_code) is not int
            or output.get("status") != ("passed" if exit_code == 0 else "failed")
            or any(output.get(key) for key in (
                "timed_out", "truncated", "cleanup_failed", "deadline_exhausted"))
            or output.get("execution_policy", {}).get("cleanup_status") != "confirmed"
            or output.get("setup_checks", {}).get("status") == "failed"):
        return None
    calls, base_calls = trace["calls"], baseline["calls"]
    if (len({call.get("call_id") for call in calls}) != len(calls)
            or len({call.get("call_id") for call in base_calls}) != len(base_calls)):
        return None
    for call in calls:
        outcome = _outcome(call)
        if (not outcome["unexpected_exception"] or outcome["capture_status"] != "complete"
                or not probe_invocation.valid_call(call, observation["binding"]["definition"][
                    "entrypoint"], channel=trace["binding_method"])):
            continue
        base_call = next((row for row in base_calls if row.get("call_id") == call["call_id"]), None)
        if base_call is None or sha256_json(_selected_conditions(trace, call)) != sha256_json(
            _selected_conditions(baseline, base_call)
        ):
            continue
        return {
            "kind": "original_target_exception", "action_id": result["action_id"],
            "diff_hash": result["workspace_diff_hash"],
            "case_id": observation["binding"]["case_id"],
            "root_action_id": observation["binding"]["root_action_id"],
            **outcome, "condition_match": "same_selected_call_inputs_and_environment",
            "observation_incomplete": trace["incomplete"],
            "whole_case_comparison": observation["comparison"],
            "original_verification_credit": False,
            "interpretation": "Positive failure of the selected call under the original "
            "inputs and environment. Whole-case comparison and task correctness remain unverified.",
        }
    return None
