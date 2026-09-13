"""One supplied public program's execution history, never a semantic oracle.

Pure diagnostic projections. No task-specific paths, provider, filesystem reads,
tool admission, model-authored case IDs, or default-runtime imports of this module.
"""

from __future__ import annotations

import copy
import json

from patchloop.dev.conversation import (
    STATE_KIND,
    history_metadata,
    reconstruct_state,
    validate_model_input,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_json

DEFINITION = "supplied_public_case"
STATUS = "public_case_status"
SCHEMA = "supplied-public-case-v1"


def require(condition, message):
    if not condition:
        raise ContractError(message)


def define_case(
    *,
    purpose,
    inputs,
    initial_state,
    expected_observables,
    question,
    python_source,
    provenance,
    execution_context,
):
    """Called by the operator's sealed preparer, never on model-supplied metadata."""
    require(
        isinstance(python_source, str)
        and 0 < len(python_source) <= 8000
        and len(python_source.encode("utf-8")) <= 32000,
        "public case source exceeds limits",
    )
    require(isinstance(question, str) and 0 < len(question) <= 500, "invalid case question")
    body = {
        "schema_version": SCHEMA,
        "origin": "operator_supplied_public_reproduction",
        "purpose": purpose,
        "input": inputs,
        "initial_state": initial_state,
        "expected_observables": expected_observables,
        "question": question,
        "python_source": python_source,
        "source_hash": sha256_bytes(python_source.encode("utf-8")),
        "provenance": provenance,
        "execution_context": execution_context,
        "interpretation": "Supplied public program, not a new tool or a current execution result. "
        "Its output needs interpretation; normal exit is not semantic success.",
    }
    require(
        len(canonical_json({k: v for k, v in body.items() if k != "python_source"})) <= 8000,
        "public case metadata exceeds bound",
    )
    return {**body, "case_id": "case_" + sha256_json(body)[7:31]}


def validate_case(case):
    keys = (
        "purpose",
        "initial_state",
        "question",
        "python_source",
        "provenance",
        "execution_context",
    )
    expected = define_case(
        **{k: case[k] for k in keys},
        inputs=case["input"],
        expected_observables=case["expected_observables"],
    )
    require(case == expected, "public case definition identity mismatch")


def observations(case, events):
    """Reduce verified journal events, including inherited receipts, in durable order.

    An action start binds the task-scoped input and execution identity; its finished
    receipt binds the raw program, baseline/full diff, snapshot and sandbox policy.
    The caller supplies a case bound to the branch's validated task/environment.
    """
    validate_case(case)
    started, rows = {}, []
    environment = case["execution_context"]
    for event in events:
        payload = event["payload"]
        if event["event_type"] == "action_started" and payload["tool"] == "run_probe":
            action_input = {k: payload[k] for k in ("tool", "arguments")}
            if payload.get("turn_decision") is not None:
                action_input["turn_decision"] = payload["turn_decision"]
            require(sha256_json(action_input) == payload["input_hash"], "probe input hash mismatch")
            require(payload["action_id"] not in started, "duplicate probe start")
            started[payload["action_id"]] = payload
        elif event["event_type"] == "action_finished" and payload["result"]["tool"] == "run_probe":
            result = payload["result"]
            start = started.get(result["action_id"])
            require(
                start is not None
                and payload["action_id"] == result["action_id"]
                and payload["input_hash"] == result["input_hash"] == start["input_hash"],
                "probe result/action mismatch",
            )
            source = start["arguments"].get("python_source")
            if not isinstance(source, str) or sha256_bytes(source.encode()) != case["source_hash"]:
                continue  # A different program is still a valid probe, not this case.
            identity = start["execution_identity"]
            require(
                identity["action_id"] == result["action_id"] and identity.get("run_id"),
                "probe execution identity mismatch",
            )
            output = result["output"]
            diff = start["baseline_diff_hash"]
            require(result["workspace_diff_hash"] == diff, "probe result diff mismatch")
            if result["status"] == "succeeded" or "source_hash" in output:
                require(
                    output["source_hash"] == case["source_hash"]
                    and output["diff_hash"] == output["workspace_diff_hash"] == diff
                    and output["image_digest"] == environment["probe_image_digest"]
                    and output["profile_hash"] == environment["probe_profile_hash"]
                    and output["execution_policy_hash"] == sha256_json(output["execution_policy"])
                    and output["execution_policy"]["profile_hash"] == output["profile_hash"],
                    "probe receipt identity mismatch",
                )
            complete = (
                result["status"] == "succeeded"
                and output.get("status") == "passed"
                and output.get("exit_code") == 0
                and bool(output.get("snapshot_hash"))
                and output.get("execution_policy", {}).get("cleanup_status") == "confirmed"
                and not any(
                    output.get(k, False)
                    for k in ("truncated", "timed_out", "cleanup_failed", "deadline_exhausted")
                )
            )
            ref = {
                "action_id": result["action_id"],
                "input_hash": result["input_hash"],
                "diff_hash": diff,
                "source_hash": case["source_hash"],
                "execution_context_hash": sha256_json(environment),
                "execution_identity": identity,
                "receipt_hash": sha256_json(result),
                "event_hash": event["event_hash"],
                "snapshot_hash": output.get("snapshot_hash"),
                "execution_policy_hash": output.get("execution_policy_hash"),
                "execution_status": "completed" if complete else "incomplete",
                "exit_code": output.get("exit_code"),
                "execution_issue": None if complete else output.get("status", "tool_result_error"),
            }
            require(
                not any(r["reference"]["action_id"] == result["action_id"] for r in rows),
                "duplicate case receipt",
            )
            rows.append({"reference": ref, "result": result})
    return rows


def status(case, rows, current_diff_hash):
    current = next(
        (
            r["reference"]
            for r in reversed(rows)
            if r["reference"]["diff_hash"] == current_diff_hash
        ),
        None,
    )
    historical = next(
        (
            r["reference"]
            for r in reversed(rows)
            if r["reference"]["diff_hash"] != current_diff_hash
        ),
        None,
    )
    return {
        "case_id": case["case_id"],
        "definition_ref": DEFINITION,
        "current_diff_hash": current_diff_hash,
        "state": (
            "no_current_result"
            if current is None
            else "current_result_available"
            if current["execution_status"] == "completed"
            else "execution_incomplete"
        ),
        "current_result": copy.deepcopy(current),
        "last_historical_result": copy.deepcopy(historical),
        "behavior_verdict": "NOT_ASSESSED",
        "interpretation": "Only exact program execution is tracked, not semantic equivalence or "
        "correctness. Compare expected observables with actual output. Edits, "
        "registered-check PASS and model concern resolution do not observe this case.",
    }


def completion_guidance(state, issue):
    guidance = copy.deepcopy(state["completion_guidance"])
    if not guidance["submission_ready"]:
        return guidance  # Preserve required mutation/check priority and all existing budgets.
    allowed = state["available_tool_names"]
    if issue["state"] == "current_result_available":
        message = (
            "Current exact-program output is available. Compare it with the supplied expected "
        )
        message += (
            "observables before completion; execution completion alone does not confirm repair. "
        )
        # Do not inherit the default suggestion to run another probe after it already ran.
        if "finish_task" in allowed:
            guidance["next_action"] = {"tool": "finish_task"}
    elif "run_probe" in allowed:
        guidance["next_action"] = {"tool": "run_probe"}
        message = (
            "No complete current result for the supplied program is recorded. Consider "
            "run_probe with supplied_public_case.question and its exact python_source, "
            "then compare actual and expected observables. "
        )
    else:
        message = "No complete current case result is recorded; no new diagnostic is offered. "
    if "finish_task" in allowed:
        message += "finish_task remains available; keep unverified behavior explicit. "
    guidance["message"] = message + "This is advice, not a submission gate or an automatic verdict."
    return guidance


def definition_delivery(case, items, *, previously_projected=False):
    """Reference an actual earlier inline body, never a reference to a reference."""
    for index, item in enumerate(items[:-1]):
        if item.get("role") != "developer":
            continue
        view = json.loads(item["content"])
        body = view.get("state", view).get(DEFINITION)
        if body == case:
            return {
                "case_id": case["case_id"],
                "definition_hash": sha256_json(case),
                "source_hash": case["source_hash"],
                "delivery": {
                    "input_item_index": index,
                    "item_hash": sha256_json(item),
                    "field": f"state.{DEFINITION}" if "state" in view else DEFINITION,
                },
            }, None
    return copy.deepcopy(case), "definition_delivery_not_restored" if previously_projected else None


def add_case(request, case, rows, *, treatment, previously_projected=False):
    """Change only the unsent state; leave the entire native/opaque prefix exact."""
    validate_case(case)
    items = request["input"]
    validate_model_input(items, history_metadata(items))
    require(items[-1].get("role") == "developer", "unsent state required")
    view = json.loads(items[-1]["content"])
    require(view["kind"] == STATE_KIND, "unsent state required")
    original = reconstruct_state(items)
    delivered, diagnostic = definition_delivery(
        case, items, previously_projected=previously_projected
    )
    overlay = {DEFINITION: delivered}
    if treatment:
        issue = status(case, rows, original["current_diff"]["patch_hash"])
        # Only claim a native delivery if that actual public output exists in this input.
        outputs = {}
        for item in items:
            if item.get("type") == "function_call_output":
                value = json.loads(item["output"])
                if isinstance(value, dict) and value.get("action_id"):
                    outputs[value["action_id"]] = (item["call_id"], value)
        for key in ("current_result", "last_historical_result"):
            ref = issue[key]
            if ref is None:
                continue
            delivered_result = outputs.get(ref["action_id"])
            if delivered_result:
                _, value = delivered_result
                require(
                    value.get("input_hash") == ref["input_hash"]
                    and value.get("workspace_diff_hash") == ref["diff_hash"],
                    "case native result reference mismatch",
                )
            ref["delivery"] = (
                {"kind": "native_function_call_output", "call_id": delivered_result[0]}
                if delivered_result
                else {"kind": "receipt_only_not_in_native_input"}
            )
        overlay.update({STATUS: issue, "completion_guidance": completion_guidance(original, issue)})
    else:
        require(STATUS not in original, "case treatment leaked into control")
    view["state"].update(overlay)
    changed = copy.deepcopy(request)
    changed["input"][-1]["content"] = canonical_json(view)
    require(changed["input"][:-1] == items[:-1], "sent case history changed")
    require(
        reconstruct_state(changed["input"]) == {**original, **overlay}, "unrelated state changed"
    )
    validate_model_input(changed["input"], history_metadata(changed["input"]))
    return changed, overlay, diagnostic
