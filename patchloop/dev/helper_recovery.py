"""One same-question correction for a helper program rejected before dispatch.

Only a host preflight proves that no target ran. A returned runtime exception is
not classified as a setup failure, and a corrected execution is not verification.
"""

from __future__ import annotations

import copy

from patchloop.errors import ContractError
from patchloop.util import sha256_bytes, sha256_json

POLICY = "helper-program-correction-v1"


def review(events, current_diff):
    """Derive a run-wide ticket from durable admission/result identities."""
    inactive = {"policy": POLICY, "status": "not_needed", "blocked": False}
    starts = {e["payload"]["action_id"]: e["payload"] for e in events
              if e["event_type"] == "action_started"}
    results = {e["payload"]["result"]["action_id"]: e["payload"]["result"] for e in events
               if e["event_type"] == "action_finished"}
    dispatched = {e["payload"]["action_id"] for e in events
                  if e["event_type"] == "probe_execution_started"}
    root = None
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
            break
    if root is None:
        return inactive
    binding = {
        "policy": POLICY, "root_action_id": root["action_id"],
        "root_input_hash": root["input_hash"], "diff_hash": root["baseline_diff_hash"],
        "question_hash": sha256_json(root["arguments"]["question"]),
        "source_hash": root["helper_program_error"]["source_hash"],
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
        status = "execution_returned" if healthy else "verification_incomplete"
    elif current_diff != binding["diff_hash"]:
        status = "verification_incomplete"
    return {
        **binding, "status": status, "blocked": status != "execution_returned",
        "question": root["arguments"]["question"],
        "python_source": root["arguments"]["python_source"] if not attempt else None,
        "error": copy.deepcopy(root["helper_program_error"]),
        "correction_action_id": attempt["action_id"] if attempt else None,
        "execution_status": (returned or {}).get("output", {}).get("status"),
        "behavior_verdict": "not_assessed", "remaining_attempts": int(not attempt),
        "interpretation": (
            "The original helper program was rejected before any execution. Correct its source "
            "for the exact same question with a new action_id, or stop. One correction request "
            "is allowed in this run; no unrelated inspection can spend it. A returned execution "
            "settles program correction only; inspect its output before drawing conclusions."
        ),
    }


def link(state):
    return {key: state[key] for key in ("policy", "root_action_id", "root_input_hash",
                                       "diff_hash", "question_hash", "source_hash")}


def validate(state, tool, arguments):
    if not state.get("blocked") or tool == "stop_task":
        return None
    source = arguments.get("python_source")
    if (state["status"] == "pending" and tool == "run_probe"
            and arguments.get("purpose") == {"kind": "helper"}
            and arguments.get("replay_action_id") is None
            and arguments.get("call_path") is None
            and arguments.get("question") == state["question"]
            and isinstance(source, str)
            and sha256_bytes(source.encode("utf-8")) != state["source_hash"]):
        return link(state)
    raise ContractError(
        "Correct the rejected helper source for the same question with a new action_id, "
        "or stop; its one correction cannot be replaced by exploration or source mutation.",
        details={"helper_correction": copy.deepcopy(state)},
    )
