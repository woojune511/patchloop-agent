"""Bounded pre-edit helper observations and optional current-diff replay guidance."""

from __future__ import annotations

import copy
from typing import Any

from patchloop.dev import probe_replay
from patchloop.dev.mutation_tools import MUTATION_TOOLS
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_bytes

PREVIEW_CHARS = 1_000
GUIDANCE = (
    "This is the latest completed helper before the latest edit; its relevance to the "
    "public requirement is not assessed. Compare its question and observations with the "
    "current required checks. If its outcome on this patch remains important, use the "
    "offered replay reference or inspect relevant caller/test code. If the behavior is "
    "unchanged, reconsider whether the changed branch ran, changed the intermediate "
    "result, or was followed by another transformation. Execution and check PASS alone "
    "do not answer this question. No automatic execution, extra budget or finish gate."
)


def _record(result: dict[str, Any]) -> dict[str, Any]:
    output = result["output"]
    observation = {key: output[key] for key in (
        "status", "exit_code", "timed_out", "truncated", "deadline_exhausted",
        "cleanup_failed", "execution_uncertain", "profile_hash", "image_digest",
    ) if key in output}
    for channel in ("stdout", "stderr"):
        value = output.get(channel, "")
        observation[channel] = value[:PREVIEW_CHARS]
        observation[channel + "_omitted_chars"] = max(0, len(value) - PREVIEW_CHARS)
    return {"action_id": result["action_id"], "input_hash": result["input_hash"],
            "diff_hash": result["workspace_diff_hash"],
            "source_hash": output["source_hash"], "observation": observation}


def _complete(output: dict[str, Any]) -> bool:
    return (output.get("status") in {"passed", "failed"}
            and type(output.get("exit_code")) is int
            and not any(output.get(key) for key in (
                "timed_out", "truncated", "deadline_exhausted", "cleanup_failed",
                "execution_uncertain"))
            and output.get("execution_policy", {}).get("cleanup_status") == "confirmed")


def _reference_valid(action_id: str, events: list[dict]) -> bool:
    try:
        probe_replay.prepare({"replay_action_id": action_id}, events)
    except (ContractError, RecoveryError):
        return False
    return True


def review(events: list[dict], current_diff: str) -> dict[str, Any] | None:
    """Derive one card from durable public actions; never execute or interpret a test."""
    mutations = [(i, event["payload"]["result"]) for i, event in enumerate(events)
                 if event["event_type"] == "action_finished"
                 and event["payload"]["result"].get("tool") in MUTATION_TOOLS
                 and event["payload"]["result"].get("status") == "succeeded"]
    if not mutations:
        return None
    mutation_index, mutation = mutations[-1]
    if mutation["output"].get("worktree_diff_hash") != current_diff:
        return None
    probes = [(i, event["payload"]["result"]) for i, event in enumerate(events)
              if event["event_type"] == "action_finished"
              and event["payload"]["result"].get("tool") == "run_probe"
              and event["payload"]["result"].get("status") == "succeeded"
              and isinstance(event["payload"]["result"].get("output", {}).get("source_hash"), str)
              and not event["payload"]["result"]["output"].get("reproduction")]
    prior = [(i, result) for i, result in probes if i < mutation_index]
    if not prior:
        return None
    baseline_index, baseline = prior[-1]
    question = baseline["output"].get("question")
    if not isinstance(question, str):
        return None
    reference_valid = _reference_valid(baseline["action_id"], events)
    source_hash = baseline["output"]["source_hash"]
    current = [(i, row) for i, row in probes if i > baseline_index
               and row["workspace_diff_hash"] == current_diff
               and row["output"].get("source_hash") == source_hash
               and row["output"].get("question") == question]
    candidate: dict[str, Any] = {"status": "not_run", "observation": None}
    if current:
        row = current[-1][1]
        identity_valid = _reference_valid(row["action_id"], events)
        candidate = {"status": ("unresolved" if not identity_valid else
                                "observed" if _complete(row["output"]) else "partial"),
                     "observation": _record(row)}
    finished = {event["payload"]["result"]["action_id"] for event in events
                if event["event_type"] == "action_finished"}
    for event in events[mutation_index + 1:]:
        if event["event_type"] != "action_started":
            continue
        start = event["payload"]
        if (start.get("tool") != "run_probe" or start["action_id"] in finished
                or start.get("baseline_diff_hash") != current_diff):
            continue
        program = (start.get("probe_replay_request") or start.get("probe_case_request")
                   or start["arguments"])
        source = program.get("python_source")
        if (start["arguments"].get("replay_action_id") == baseline["action_id"]
                or (isinstance(source, str) and sha256_bytes(source.encode()) == source_hash
                    and program.get("question") == question)):
            candidate = {"status": "unresolved", "action_id": start["action_id"],
                         "observation": None}
            break
    return {
        "selection": "latest_completed_helper_before_latest_edit",
        "mutation_action_id": mutation["action_id"], "current_diff_hash": current_diff,
        "question": question[:500], "question_authorship": "model",
        "baseline": _record(baseline), "candidate": candidate,
        "requirement_coverage": "not_assessed", "behavior_verdict": "not_assessed",
        "comparison_scope": "Same question/program only; inspect execution conditions and "
                            "completeness. Previews are not full-output comparisons.",
        "replay": {"reference_valid": reference_valid, "available": False,
                   "arguments": None, "reason": "tool_policy_not_projected",
                   "argument_scope": "Tool fields only; supply the usual turn_decision or "
                                     "memory_update only as required by the offered schema."},
        "guidance": GUIDANCE,
    }


def with_guidance(card: dict[str, Any], *, offered: bool, restricted: bool,
                  probe_policy: str) -> dict[str, Any]:
    """Use the existing admission policy; this card grants no tool permission."""
    card = copy.deepcopy(card)
    replay = card["replay"]
    reason = ("reference_unavailable" if not replay["reference_valid"] else
              "execution_unresolved" if card["candidate"]["status"] == "unresolved" else
              "run_probe_not_offered" if not offered else
              "specialized_diagnostic_stage" if restricted else None)
    replay.update(available=reason is None, reason=reason, arguments=None)
    if reason is None:
        arguments = {"replay_action_id": card["baseline"]["action_id"],
                     "question": None, "python_source": None, "purpose": None,
                     "call_path": None}
        if probe_policy in {"cases-v1", "reference-cases-v1"}:
            arguments.update(case_id=None, reference_action_id=None)
        if probe_policy == "cases-v1":
            arguments["save_program"] = False
        replay["arguments"] = arguments
    return card
