"""Bounded diagnosis after a refuted repair misses its changed Python branch.

This is a projection of public receipts, not a second task-success judge. A
complete trace explains one invocation; it does not prove a repair hypothesis.
"""

from __future__ import annotations

import copy
import json

from patchloop.dev import completion_reproduction, probe_invocation, reproduction
from patchloop.errors import ContractError
from patchloop.util import sha256_json
from patchloop.verifier.policy import _is_test_path

POLICY = "repair-call-path-v1"
MAX_REJECTED_REQUESTS = 2  # Original request and one correction, not two executions.
READ_TOOLS = {"read_file", "search_files"}


def _unchanged_failure(result, baseline, case_id, current_diff):
    observation = result.get("output", {}).get("reproduction", {})
    if (result.get("workspace_diff_hash") != current_diff
            or observation.get("binding", {}).get("case_id") != case_id
            or observation.get("comparison") != "mismatched"
            or observation.get("declared_failure_comparison") != "matched"
            or observation.get("judgment", {}).get("status") != "consistent"):
        return False
    return (completion_reproduction._healthy(result, observation)
            and reproduction.call_identity(observation["call_observation"])
            == reproduction.call_identity(baseline["call_observation"])
            and probe_invocation.conditions(observation["call_observation"])
            == probe_invocation.conditions(baseline["call_observation"]))


def _call_id(observation):
    definition = observation["binding"]["definition"]
    expected = json.loads(definition["expected_json"])
    actual = json.loads(observation["observed_json"])
    return next((rule["call_id"] for rule in definition.get("diagnostic_rules", [])
                 if actual.get(rule["field"]) != expected.get(rule["field"])), None)


def _watched_changes(request, changes):
    return any(watch.get("origin") == "workspace" and watch.get("path") == row["path"]
               and any(start <= line <= end for start, end in row["ranges"]
                       for line in watch.get("lines", []))
               for watch in request.get("watches", []) for row in changes)


def _summary(trace):
    """Keep bounded entry/exit evidence after native results leave recent context."""
    rows = []
    for row in [trace["focus"], *trace["watches"]]:
        events = row["events"]
        selected = events if len(events) <= 2 else [events[0], events[-1]]
        rows.append({**{key: row[key] for key in ("origin", "path", "function", "file_hash",
                      "entries", "observed_lines", "not_observed_lines", "observation")},
                     **({"event_counts": copy.deepcopy(row["event_counts"])}
                        if "event_counts" in row else {}),
                     "entry_exit_events": selected,
                     "omitted_event_count": len(events) - len(selected)})
    return {"scope": trace["scope"], "focus": rows[0], "watches": rows[1:],
            **({"collection": copy.deepcopy(trace["collection"])}
               if "collection" in trace else {}),
            "details_field": "output.call_path", "semantic_correctness": "unverified"}


def review(events, current_diff, completion):
    """Keep one stable trigger per candidate; replays/restarts cannot refill it."""
    inactive = {"policy": POLICY, "status": "not_needed", "blocked": False}
    if completion.get("observation_correction", {}).get("blocked"):
        return inactive
    starts = {e["payload"]["action_id"]: e["payload"] for e in events
              if e["event_type"] == "action_started"}
    rows = [e["payload"]["result"] for e in events if e["event_type"] == "action_finished"]
    results = {r["action_id"]: r for r in rows}
    mutations = [r for r in rows if r.get("tool") == "replace_text"
                 and r.get("status") == "succeeded"
                 and (path := starts.get(r["action_id"], {}).get("mutation_target_path"))
                 and path.endswith(".py") and not _is_test_path(path)]
    if not mutations:
        return inactive
    mutation = mutations[-1]
    mutation_start = starts.get(mutation["action_id"], {})
    target_path = mutation_start.get("mutation_target_path")
    target_hash = mutation_start.get("mutation_expected_postimage_file_hash")
    if not target_path or not target_hash:
        return inactive
    trigger = None
    for case in completion.get("cases", []):
        if (case["case_id"] not in completion.get("baseline_failure_case_ids", [])
                or case.get("evidence", {}).get("status") != "REFUTED"):
            continue
        base = results.get(case["root_action_id"], {}).get("output", {}).get("reproduction")
        if base is None:
            continue
        for result in rows:
            start = starts.get(result["action_id"], {})
            if start.get("diagnosis_request") or start.get("arguments", {}).get("call_path"):
                continue
            if not _unchanged_failure(result, base, case["case_id"], current_diff):
                continue
            feedback = result["output"].get("public_execution", {})
            changes = [{"path": row["path"], "file_hash": row["file_hash"],
                        "ranges": row["not_observed_changed_ranges"]}
                       for row in feedback.get("files", [])
                       if row.get("path") == target_path and row.get("file_hash") == target_hash
                       and row.get("status") == "collected"
                       and row.get("not_observed_changed_ranges")]
            call_id = _call_id(result["output"]["reproduction"])
            if feedback.get("diff_hash") == current_diff and changes and call_id:
                trigger = (case, result, changes, call_id)
                break
        if trigger:
            break
    if trigger is None:
        return inactive
    case, failure, changes, call_id = trigger
    link = {"policy": POLICY, "candidate_diff_hash": current_diff,
            "case_id": case["case_id"], "replay_action_id": case["root_action_id"],
            "failure_action_id": failure["action_id"], "mutation_action_id": mutation["action_id"],
            "call_id": call_id}
    linked = [start for start in starts.values() if start.get("repair_path_link") == link]
    preparations = [s["action_id"] for s in linked if s["tool"] in READ_TOOLS]
    attempts = [s for s in linked if s["tool"] == "run_probe"]
    dispatched = {e["payload"]["action_id"] for e in events
                  if e["event_type"] == "probe_execution_started"}
    executed = [s for s in attempts if s["action_id"] in dispatched]
    rejected = [s for s in attempts if s.get("probe_request", {}).get("status") == "rejected"]
    diagnosis = next((results[s["action_id"]] for s in executed
                      if s["action_id"] in results), None)
    complete = False
    if diagnosis:
        trace = diagnosis.get("output", {}).get("call_path", {})
        admission = starts[diagnosis["action_id"]]
        request = (admission.get("diagnosis_request", {}).get("call_path")
                   or admission["arguments"].get("call_path", {}))
        expected_scope = ("selected_call_launch_thread" if request.get("scope") == "selected_call"
                          else "selected_call_focus_launch_thread" if "scope" not in request
                          else None)
        watched_hashes = {(w.get("path"), w.get("file_hash")) for w in trace.get("watches", [])}
        complete = bool(
            trace.get("status") == "complete" and trace.get("call_id") == call_id
            and expected_scope is not None and trace.get("scope") == expected_scope
            and trace.get("candidate_diff_hash") == current_diff
            and trace.get("snapshot_hash") is not None
            and trace.get("snapshot_hash") == diagnosis["output"].get("snapshot_hash")
            and trace.get("execution_identity_hash") == sha256_json(
                starts[diagnosis["action_id"]].get("execution_identity"))
            and trace.get("raw_request_hash") == sha256_json(request)
            and _watched_changes(request, changes)
            and any((c["path"], c["file_hash"]) in watched_hashes for c in changes)
            and _unchanged_failure(diagnosis, base, case["case_id"], current_diff)
        )
    exhausted = bool(executed or len(rejected) >= MAX_REJECTED_REQUESTS)
    return {
        **link, "status": "diagnosed" if complete else "verification_incomplete" if exhausted
        else "needs_path_diagnosis", "blocked": not complete,
        "diagnosis_action_id": diagnosis["action_id"] if complete else None,
        **({"diagnosis_observation": _summary(diagnosis["output"]["call_path"])}
           if complete else {}),
        "preparation_available": not preparations, "preparation_action_ids": preparations,
        "rejected_requests": len(rejected), "execution_attempted": bool(executed),
        "unobserved_changes": changes,
        "prior_prediction": {"hypothesis": mutation_start.get("arguments", {}).get("hypothesis"),
                             "expected_behavior": mutation_start.get("arguments", {}).get(
                                 "expected_behavior"),
                             "status": "original_effect_refuted"},
        "interpretation": "The same original failure persists and changed lines were not "
        "observed. Diagnose the failing call path before another edit. Function entry, branch "
        "execution and repair correctness are separate claims.",
    }


def link(state):
    return {key: state[key] for key in ("policy", "candidate_diff_hash", "case_id",
            "replay_action_id", "failure_action_id", "mutation_action_id", "call_id")}


def validate(state, tool, arguments):
    """Bind the offered diagnostic/next repair to receipts, never narrative alone."""
    request = arguments.get("call_path") if tool == "run_probe" else None
    if not state.get("blocked"):
        if request is not None:
            raise ContractError("call_path requires a pending original-failure path diagnosis")
        if state.get("status") == "diagnosed" and tool == "replace_text":
            if not arguments.get("hypothesis"):
                raise ContractError("Revise the prior repair hypothesis using the completed "
                                    "call-path diagnosis; provide hypothesis.")
            return {**link(state), "diagnosis_action_id": state["diagnosis_action_id"]}
        return None
    if tool == "stop_task":
        return None
    if state["status"] == "needs_path_diagnosis":
        if tool in READ_TOOLS and state["preparation_available"]:
            return link(state)
        if (tool == "run_probe" and isinstance(request, dict)
                and arguments.get("replay_action_id") == state["replay_action_id"]
                and request.get("call_id") == state["call_id"]
                and _watched_changes(request, state["unobserved_changes"])):
            return link(state)
    raise ContractError(
        "Resolve the bounded original-call path diagnosis before another repair or verification "
        "action.", details={"repair_path": copy.deepcopy(state)},
    )
