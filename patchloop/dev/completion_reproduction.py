"""Pure completion projection for durable public invocation-bound reproductions.

Every first binding survives plan changes and bounded context display. This judges
the selected cases only: their mapping to the task and repair success stay unverified.
"""

from __future__ import annotations

import copy

from patchloop.dev import (
    observation_correction,
    probe_comparison,
    probe_invocation,
    probe_replay,
    reproduction,
)
from patchloop.dev.contracts import RequestedTool
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_json

POLICY = "completion-reproduction-v1"
DISPLAY_LIMIT = 3


def replay_call(run_id, case_id, root_action_id, diff_hash):
    """Use one recoverable ordinary probe action per run, original case and diff."""
    identity = sha256_json({
        "policy": POLICY, "run_id": run_id, "case_id": case_id,
        "root_action_id": root_action_id, "candidate_diff_hash": diff_hash,
    })
    return RequestedTool(
        name="run_probe", action_id="completion-reproduction-" + identity.split(":", 1)[-1],
        arguments={"question": None, "python_source": None,
                   "replay_action_id": root_action_id, "purpose": None},
    )


def _healthy(result, observation):
    output = result.get("output") or {}
    trace = observation["call_observation"]
    return (
        result.get("status") == "succeeded" and output.get("status") == "passed"
        and type(output.get("exit_code")) is int and output["exit_code"] == 0
        and not any(output.get(key) for key in (
            "timed_out", "truncated", "cleanup_failed", "deadline_exhausted"))
        and output.get("execution_policy", {}).get("cleanup_status") == "confirmed"
        and output.get("setup_checks", {}).get("status") != "failed"
        and observation["comparison"] in {"matched", "mismatched"}
        and observation.get("reason") is None
        and probe_invocation.supports(trace.get("binding_method"))
        and trace["calls"] and not trace["incomplete"]
        and all(probe_invocation.valid_call(call, observation["binding"]["definition"][
            "entrypoint"], channel=trace.get("binding_method")) for call in trace["calls"])
    )


def _compact(row, *, include_observation=False):
    if row is None:
        return None
    result, observation = row
    trace = observation["call_observation"]
    return {
        "action_id": result["action_id"], "diff_hash": result["workspace_diff_hash"],
        "comparison": observation["comparison"], "reason": observation["reason"],
        **({"observed_json": observation.get("observed_json")} if include_observation else {}),
        "execution_status": result.get("output", {}).get("status"),
        **({"declared_failure_comparison": observation["declared_failure_comparison"]}
           if "declared_failure_comparison" in observation else {}),
        "execution_link": probe_invocation.summary(trace) if probe_invocation.supports(trace.get(
            "binding_method")) else {"status": "unbound_invocation"},
    }


def _comparability(root, current, eligible):
    if not eligible or current is None or not _healthy(*current):
        return {"status": "unavailable", "differences": [], "omitted_count": 0}
    baseline = probe_invocation.conditions(root[1]["call_observation"])
    candidate = probe_invocation.conditions(current[1]["call_observation"])
    feedback = probe_comparison.differences(canonical_json(baseline), canonical_json(candidate))
    return {"status": "changed" if feedback["differences"] else "same", **feedback}


def _failure_diagnostic(events, current_diff, failure_actions):
    """One model diagnostic per refuted candidate, derived from durable starts.

    Host replays do not spend this opportunity. A rejected model request does;
    neither another replay nor restart can replenish it on the same diff.
    """
    first_failure = next((event for event in events
                          if event["event_type"] == "action_finished"
                          and event["payload"]["result"]["action_id"] in failure_actions), None)
    if first_failure is None:
        return None
    # A batch start spends the slot even when its action is a cached replay or
    # execution is interrupted before action_started. Only accepted candidates
    # change the workspace; serial batches observe the last completed diff.
    observed_diff, spent = None, None
    for event in events:
        if event["event_type"] == "action_finished":
            observed_diff = event["payload"]["result"].get("workspace_diff_hash", observed_diff)
        elif (event["event_type"] == "tool_batch_started"
              and event["sequence"] > first_failure["sequence"]
              and observed_diff == current_diff):
            spent = next((call["action_id"] for call in event["payload"]["tool_calls"]
                          if call["name"] in {"read_file", "search_files", "run_probe"}), None)
            if spent is not None:
                break
    return {
        "candidate_diff_hash": current_diff,
        "failure_action_id": first_failure["payload"]["result"]["action_id"],
        "status": "spent" if spent else "available", "spent_action_id": spent,
    }


def review(events, current_diff, *, public_task=None, run_id):
    """Project all bindings; only the display, never obligations, is bounded.

    ``case_count`` includes unestablished/legacy bindings. ``replayable_case_count``
    counts healthy invocation-bound roots; ``pending_cases`` is the complete internal
    replay plan. A durable automatic attempt settles UNKNOWN for this diff without
    retrying. A new diff makes that case pending again.
    """
    cases, completed_actions, attempts = {}, {}, {}
    rejected = {event["payload"]["action_id"] for event in events
                if event["event_type"] == "action_started"
                and event["payload"].get("tool") == "run_probe"
                and event["payload"].get("probe_request", {}).get("status") == "rejected"}
    for event in events:
        kind, payload = event["event_type"], event["payload"]
        if kind in {"completion_reproduction_finished", "completion_reproduction_skipped"}:
            attempts.setdefault(payload["action_id"], []).append({"kind": kind, **payload})
        if kind == "action_started" and payload.get("tool") == "run_probe":
            if payload["action_id"] in rejected:
                continue
            binding = payload.get("reproduction_binding")
            if binding is not None:
                cases.setdefault(binding["case_id"], {"binding": binding, "rows": []})
        elif kind == "action_finished":
            result = payload["result"]
            completed_actions[result["action_id"]] = result
            if result["action_id"] in rejected:
                continue
            observation = (result.get("output") or {}).get("reproduction")
            if result.get("tool") != "run_probe" or observation is None:
                continue
            binding = observation["binding"]
            case = cases.setdefault(binding["case_id"], {"binding": binding, "rows": []})
            # A later declaration/replay cannot revise the first case's conditions.
            if case["binding"] == binding:
                case["rows"].append((result, observation))

    task_hash = sha256_json(public_task.model_dump(mode="json")) if public_task else None
    items, pending, failure_actions = [], [], set()
    diagnostic_eligible = False
    for case_id, case in cases.items():
        binding, rows = case["binding"], case["rows"]
        root_id = binding["root_action_id"]
        root = next((row for row in rows if row[0]["action_id"] == root_id), None)
        root_reason = "baseline_not_observed"
        eligible = False
        if root is not None:
            root_reason = "baseline_not_healthy_invocation"
            eligible = (probe_invocation.supports(binding["definition"].get("observation_channel"))
                        and _healthy(*root))
            if eligible:
                # Reuse the existing public program/receipt identity checks. Corrupt
                # execution identities raise RecoveryError rather than receive credit.
                try:
                    probe_replay.prepare({"replay_action_id": root_id}, events)
                except ContractError:
                    eligible = False
                    root_reason = "baseline_not_replayable"
        if task_hash is not None and binding["definition"].get("public_task_hash") != task_hash:
            eligible = False
            root_reason = "public_task_changed"

        comparable = [row for row in rows if eligible
                      and row[0]["workspace_diff_hash"] == current_diff
                      and _healthy(*row)
                      and reproduction.call_identity(row[1]["call_observation"])
                      == reproduction.call_identity(root[1]["call_observation"])]
        outcomes = {row[1]["comparison"] for row in comparable}
        evidence = ("CONFLICT" if len(outcomes) > 1 else "REFUTED"
                    if "mismatched" in outcomes else "SUPPORTED"
                    if "matched" in outcomes else "UNKNOWN")
        call = replay_call(run_id, case_id, root_id, current_diff)
        identity = {"action_id": call.action_id, "case_id": case_id,
                    "root_action_id": root_id, "candidate_diff_hash": current_diff}
        attempt = next((item for item in attempts.get(call.action_id, ())
                        if all(item.get(k) == v for k, v in identity.items())), None)
        completed = completed_actions.get(call.action_id)
        if completed is not None and (
                completed.get("tool") != call.name or completed.get("input_hash")
                != sha256_json({"tool": call.name, "arguments": call.arguments})):
            raise RecoveryError("completion reproduction action identity mismatch")
        settled = completed is not None or attempt is not None
        is_pending = eligible and evidence == "UNKNOWN" and not settled
        if is_pending:
            pending.append({"case_id": case_id, "root_action_id": root_id,
                            "auto_action_id": call.action_id, "current_diff": current_diff})
        state = ("refuted" if evidence in {"REFUTED", "CONFLICT"} else "verified"
                 if evidence == "SUPPORTED" else "pending" if is_pending else "unverified")
        reason = ("same_case_conflicting_observations" if evidence == "CONFLICT"
                  else "frozen_expectation_comparison" if comparable
                  else root_reason if not eligible else "automatic_attempt_unverified"
                  if settled else "no_comparable_current_observation")
        witnesses = {row[1]["comparison"]: row[0]["action_id"] for row in comparable}
        paired = "reported_failure_json" in binding["definition"]
        original_failure = bool(
            eligible and root[0]["workspace_diff_hash"] == sha256_bytes(b"")
            and root[1]["comparison"] == "mismatched"
            and (not paired or root[1].get("declared_failure_comparison") == "matched"))
        current = next((row for row in reversed(rows)
                        if row[0]["workspace_diff_hash"] == current_diff), None)
        comparability = _comparability(root, current, eligible)
        if original_failure and current_diff != sha256_bytes(b""):
            failure_actions.update(row[0]["action_id"] for row in comparable
                                   if row[1]["comparison"] == "mismatched")
            diagnostic_eligible |= evidence == "REFUTED" and comparability["status"] == "same"
        items.append({
            "case_id": case_id, "root_action_id": root_id,
            "purpose": copy.deepcopy(binding["definition"]),
            "baseline": _compact(root), "latest": _compact(rows[-1] if rows else None),
            "current": _compact(current, include_observation=True),
            "comparability": comparability,
            "status": state, "replayable": bool(eligible), "auto_action_id": call.action_id,
            **({"baseline_acquisition": {
                "status": "qualified" if original_failure else "unverified",
                "reason": "matched_declared_failure_on_unchanged_base" if original_failure
                else "reported_failure_not_established_on_unchanged_base",
                "requirement_mapping": "model_authored_unverified",
            }} if paired else {}),
            "evidence": {"status": evidence, "reason": reason,
                         "evidence_action_ids": list(witnesses.values())},
            "automatic_attempt": {
                "status": "skipped" if attempt is not None and attempt["kind"]
                == "completion_reproduction_skipped" else "finished" if settled
                else "pending" if is_pending else "not_needed",
                "reason": attempt.get("reason") if attempt is not None else None,
            },
            "requirement_mapping": "model_authored_unverified", "repair_success": "not_assessed",
        })
    correction = observation_correction.review(events, current_diff)
    superseded = set(correction["superseded_case_ids"])
    superseded_items = [item for item in items if item["case_id"] in superseded]
    items = [item for item in items if item["case_id"] not in superseded]
    failed = sum(item["status"] == "refuted" for item in items)
    unverified = sum(item["status"] == "unverified" for item in items)
    priority = {"refuted": 0, "pending": 1, "unverified": 2, "verified": 3}
    items.sort(key=lambda item: priority[item["status"]])
    acquired = [item["case_id"] for item in items
                if item["replayable"] and item["baseline"]["diff_hash"] == sha256_bytes(b"")
                and item["baseline"]["comparison"] == "mismatched"
                and ("baseline_acquisition" not in item
                     or item["baseline_acquisition"]["status"] == "qualified")]
    return {
        "policy": POLICY,
        "status": "refuted" if failed else "pending" if pending else "unverified"
        if unverified or not items else "cases_verified",
        "current_diff_hash": current_diff, "case_count": len(items),
        "observation_correction": correction,
        "superseded_case_count": len(superseded_items),
        "superseded_cases": [{"case_id": item["case_id"],
                              "root_action_id": item["root_action_id"],
                              "status": "superseded_judgment"}
                             for item in superseded_items[:DISPLAY_LIMIT]],
        "replayable_case_count": sum(item["replayable"] for item in items),
        "baseline_failure_case_ids": acquired,
        "early_replay_reusable": bool(items) and len(acquired) == len(items) and all(
            item["status"] in {"refuted", "verified"}
            and item["evidence"]["status"] != "CONFLICT"
            and item["comparability"]["status"] == "same" for item in items
        ),
        "baseline_matched_count": sum(item["replayable"] and item["baseline"]["diff_hash"]
                                      == sha256_bytes(b"") and item["baseline"]["comparison"]
                                      == "matched" for item in items),
        "baseline_observed_count": sum(item["replayable"] and item["baseline"]["diff_hash"]
                                       == sha256_bytes(b"") for item in items),
        "pending_count": len(pending), "failed_count": failed,
        "unestablished_count": sum(not item["replayable"] for item in items),
        "unverified_count": unverified, "pending_cases": pending,
        "original_failure_diagnostic": (
            _failure_diagnostic(events, current_diff, failure_actions)
            if diagnostic_eligible else None
        ),
        "cases": items[:DISPLAY_LIMIT], "omitted_count": max(0, len(items) - DISPLAY_LIMIT),
        "requirement_mapping": "model_authored_unverified", "repair_success": "not_assessed",
        "interpretation": "Frozen public case evidence, not task correctness. Helper/check PASS, "
        "plan replacement and assessment text cannot resolve an original case. Automatic replay "
        "attempts are bounded per case and candidate; unavailable observations remain unverified.",
    }
