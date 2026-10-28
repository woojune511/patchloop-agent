"""Bounded diagnosis after a refuted repair misses its changed Python branch.

This is a projection of public receipts, not a second task-success judge. A
complete trace explains one invocation; it does not prove a repair hypothesis.
"""

from __future__ import annotations

import copy
import json

from patchloop.dev import completion_reproduction, probe_invocation, probe_judgment, reproduction
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes, sha256_json
from patchloop.verifier.policy import _is_test_path

POLICY = "repair-call-path-v1"
MAX_REJECTED_REQUESTS = 2  # Original request and one correction, not two executions.
READ_TOOLS = {"read_file", "search_files"}


def _mutation_receipt(start, result):
    """Require the durable admission and completed full-diff receipt to agree."""
    output = result.get("output", {})
    mutation = output.get("mutation", {})
    evidence = output.get("mutation_evidence") or {}
    arguments = start.get("arguments", {})
    path = start.get("mutation_target_path")
    patch = start.get("mutation_generated_patch")
    diff = start.get("mutation_expected_worktree_diff_hash")
    return bool(
        start.get("mutation_admitted") is True and path and patch and diff
        and start.get("baseline_diff_hash") and start.get("mutation_preimage_file_hash")
        and start.get("mutation_expected_postimage_file_hash")
        and start.get("input_hash") and start["input_hash"] == result.get("input_hash")
        and start["action_id"] == result.get("action_id")
        and result.get("tool") == "replace_text" and result.get("status") == "succeeded"
        and arguments.get("path") == path and output.get("changed_files") == [path]
        and result.get("workspace_diff_hash") == diff == output.get("worktree_diff_hash")
        and mutation.get("diff_hash") == diff and mutation.get("changed_hunk") == patch
        and output.get("patch_hash") == sha256_bytes(patch.encode("utf-8"))
        and mutation.get("replacement_hash") == sha256_json({
            key: arguments.get(key) for key in ("path", "old_text", "new_text", "occurrence")})
        and evidence.get("path") == path and evidence.get("source_diff_hash") == diff
        and evidence.get("file_hash") == start["mutation_expected_postimage_file_hash"]
    )


def _test_only_chain(events, mutation_id, current_diff, results):
    """Prove unchanged implementation through host-certified additive test edits.

    This grants no fresh trace or check credit. Missing legacy metadata keeps the
    old, exact-candidate rule; an admitted mutation without a result is uncertain.
    """
    chain, hashes, seen = [], {}, set()
    for event in events:
        start = event["payload"]
        if event["event_type"] != "action_started" or start.get("tool") != "replace_text":
            continue
        if not chain and start["action_id"] != mutation_id:
            continue
        if start.get("mutation_admitted") is False:
            continue
        if start["action_id"] in seen:
            return None
        seen.add(start["action_id"])
        if not _mutation_receipt(start, results.get(start["action_id"], {})):
            return None
        path = start["mutation_target_path"]
        if chain and (
            start.get("mutation_test_only") is not True
            or not _is_test_path(path) or not path.endswith(".py")
            or path.rsplit("/", 1)[-1] in {"conftest.py", "setup.py", "__init__.py"}
            or start["baseline_diff_hash"] != chain[-1]["mutation_expected_worktree_diff_hash"]
            or (path in hashes and start["mutation_preimage_file_hash"] != hashes[path])
        ):
            return None
        chain.append(start)
        hashes[path] = start["mutation_expected_postimage_file_hash"]
    if not chain or chain[-1]["mutation_expected_worktree_diff_hash"] != current_diff:
        return None
    return chain


def _same_failure(before, after):
    """Require the same public inputs, environment and captured failure, not a label."""
    old, new = before.get("output", {}), after.get("output", {})
    if any(not old.get(key) or old[key] != new.get(key)
           for key in ("image_digest", "profile_hash")):
        return False
    a, b = old.get("reproduction", {}), new.get("reproduction", {})
    if a.get("binding") != b.get("binding") or a.get("observed_json") != b.get("observed_json"):
        return False
    if reproduction.call_identity(a["call_observation"]) != reproduction.call_identity(
        b["call_observation"]
    ):
        return False
    def outputs(observation):
        return [{key: call.get(key) for key in (
            "call_id", "capture", "exception", "outcome", "exit_code")}
                for call in observation["call_observation"]["calls"]]
    return sha256_json(outputs(a)) == sha256_json(outputs(b))


def _historical_links(starts, results, chain, link, failure, base, *, ruleless=False):
    if not chain:
        return {}
    histories = {}
    for start in starts.values():
        prior = start.get("repair_path_link") or {}
        keys = ("policy", "case_id", "replay_action_id", "mutation_action_id")
        if prior == link or any(prior.get(key) != link[key]
                                for key in keys + (() if ruleless else ("call_id",))):
            continue
        position = next((i for i, step in enumerate(chain[:-1])
                         if step["mutation_expected_worktree_diff_hash"]
                         == prior.get("candidate_diff_hash")), None)
        old_failure = results.get(prior.get("failure_action_id"), {})
        if (position is not None
                and _unchanged_failure(old_failure, base, link["case_id"],
                                       prior["candidate_diff_hash"])
                and _same_failure(old_failure, failure)):
            histories[start["action_id"]] = {
                "observed_diff_hash": prior["candidate_diff_hash"],
                "test_only_mutation_action_ids": [s["action_id"] for s in chain[position + 1:]],
            }
    return histories


def _exception_sites(trace):
    sites = []
    for row in [trace["focus"], *trace["watches"]]:
        for event in row["events"]:
            if event.get("event") != "exception":
                continue
            site = {**{key: row[key] for key in ("origin", "path", "function", "file_hash")},
                    "line": event["line"], "exception_type": event["exception_type"]}
            if site not in sites:
                sites.append(site)
    return sites[:4], max(0, len(sites) - 4)


def _unchanged_failure(result, baseline, case_id, current_diff):
    observation = result.get("output", {}).get("reproduction", {})
    if (result.get("workspace_diff_hash") != current_diff
            or observation.get("binding", {}).get("case_id") != case_id
            or observation.get("comparison") != "mismatched"
            or observation.get("declared_failure_comparison") != "matched"):
        return False
    rules = observation.get("binding", {}).get("definition", {}).get("diagnostic_rules")
    if rules is not None:
        if not probe_judgment.is_usable(observation.get("judgment")):
            return False
    elif (observation.get("binding") != baseline.get("binding")
          or observation.get("observed_json") != baseline.get("observed_json")
          or not _paired_capture(observation, baseline)):
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
    return next((rule["call_id"] for rule in (definition.get("diagnostic_rules") or [])
                 if actual.get(rule["field"]) != expected.get(rule["field"])), None)


def _paired_capture(observation, baseline):
    """Equal captured outcomes permit diagnosis, never authored-judgment promotion."""
    traces = [value.get("call_observation", {}) for value in (observation, baseline)]
    if any(trace.get("binding_method") not in probe_invocation.CAPTURE_CHANNELS
           or trace.get("incomplete") is not False or not trace.get("calls")
           or any(call.get("capture", {}).get("status") != "complete"
                  or call.get("target_started") is False for call in trace["calls"])
           for trace in traces):
        return False
    fields = ("call_id", "capture", "exception", "outcome", "exit_code")
    return [{key: row.get(key) for key in fields} for row in traces[0]["calls"]] == [
        {key: row.get(key) for key in fields} for row in traces[1]["calls"]]


def _call_choices(observation):
    return [{key: copy.deepcopy(call.get(key)) for key in (
        "call_id", "argv", "arguments", "outcome", "exit_code")}
        for call in observation["call_observation"]["calls"]
        if call.get("capture", {}).get("status") == "complete"
        and call.get("target_started") is not False][:4]


def _same_link(prior, current, *, ruleless=False):
    # Selection cannot create another preparation, rejection or execution allowance.
    if not ruleless:
        return prior == current
    return isinstance(prior, dict) and all(prior.get(key) == value
        for key, value in current.items() if key != "call_id")


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
            observation = result["output"]["reproduction"]
            call_id = _call_id(observation)
            ruleless = observation["binding"]["definition"].get("diagnostic_rules") is None
            choices = _call_choices(observation) if ruleless else []
            if feedback.get("diff_hash") == current_diff and changes and (call_id or choices):
                trigger = (case, result, changes, call_id, choices, ruleless)
                break
        if trigger:
            break
    if trigger is None:
        return inactive
    case, failure, changes, call_id, choices, ruleless = trigger
    link = {"policy": POLICY, "candidate_diff_hash": current_diff,
            "case_id": case["case_id"], "replay_action_id": case["root_action_id"],
            "failure_action_id": failure["action_id"], "mutation_action_id": mutation["action_id"],
            "call_id": call_id}
    history = _historical_links(starts, results, _test_only_chain(
        events, mutation["action_id"], current_diff, results), link, failure, base,
        ruleless=ruleless)
    linked = [start for start in starts.values() if _same_link(
        start.get("repair_path_link"), link, ruleless=ruleless)
              or start["action_id"] in history]
    if ruleless:
        allowed = {row["call_id"] for row in choices}
        call_id = next((selected for start in linked
                        if start.get("tool") == "run_probe"
                        and start.get("probe_request", {}).get("status") != "rejected"
                        and (selected := (start.get("diagnosis_request") or {}).get(
                            "call_path", {}).get("call_id")) in allowed
                        and start["repair_path_link"].get("call_id") == selected), None)
        link["call_id"] = call_id
    preparations = [s["action_id"] for s in linked if s["tool"] in READ_TOOLS]
    attempts = [s for s in linked if s["tool"] == "run_probe"]
    dispatched = {e["payload"]["action_id"] for e in events
                  if e["event_type"] == "probe_execution_started"}
    executed = [s for s in attempts if s["action_id"] in dispatched]
    rejected = [s for s in attempts if s.get("probe_request", {}).get("status") == "rejected"]
    diagnosis = next((results[s["action_id"]] for s in executed
                      if s["action_id"] in results), None)
    complete = False
    trace = {}
    observed_diff = current_diff
    if diagnosis:
        trace = diagnosis.get("output", {}).get("call_path", {})
        admission = starts[diagnosis["action_id"]]
        historical = history.get(diagnosis["action_id"])
        observed_diff = historical["observed_diff_hash"] if historical else current_diff
        request = (admission.get("diagnosis_request", {}).get("call_path")
                   or admission["arguments"].get("call_path", {}))
        expected_scope = ("selected_call_launch_thread" if request.get("scope") == "selected_call"
                          else "selected_call_focus_launch_thread" if "scope" not in request
                          else None)
        watched_hashes = {(w.get("path"), w.get("file_hash")) for w in trace.get("watches", [])}
        complete = bool(
            trace.get("status") == "complete" and trace.get("call_id") == call_id
            and expected_scope is not None and trace.get("scope") == expected_scope
            and trace.get("candidate_diff_hash") == observed_diff
            and trace.get("snapshot_hash") is not None
            and trace.get("snapshot_hash") == diagnosis["output"].get("snapshot_hash")
            and trace.get("execution_identity_hash") == sha256_json(
                starts[diagnosis["action_id"]].get("execution_identity"))
            and trace.get("raw_request_hash") == sha256_json(request)
            and _watched_changes(request, changes)
            and any((c["path"], c["file_hash"]) in watched_hashes for c in changes)
            and _unchanged_failure(diagnosis, base, case["case_id"], observed_diff)
            and (not historical or (
                admission.get("input_hash")
                and admission["input_hash"] == diagnosis.get("input_hash")
                and _same_failure(diagnosis, failure)))
        )
    exhausted = bool(executed or len(rejected) >= MAX_REJECTED_REQUESTS)
    collection_status = "complete" if complete else "unknown" if executed else "not_collected"
    sites, omitted_sites = _exception_sites(trace) if complete else ([], 0)
    origin = diagnosis or (executed[0] if executed else None)
    evidence = None
    if origin:
        historical = history.get(origin["action_id"])
        attempted_diff = historical["observed_diff_hash"] if historical else current_diff
        evidence = {
            "relation": "historical_test_only" if historical else "current_candidate",
            "source_action_id": origin["action_id"],
            "observed_diff_hash": attempted_diff if complete else None,
            "attempted_diff_hash": attempted_diff, "current_diff_hash": current_diff,
            "snapshot_hash": trace.get("snapshot_hash") if complete else None,
            "test_only_mutation_action_ids": (
                historical["test_only_mutation_action_ids"] if historical else []),
            "current_snapshot_trace": bool(complete and not historical),
        }
    return {
        **link, "status": "diagnosed" if complete else "verification_incomplete" if exhausted
        else "needs_path_diagnosis", "blocked": not complete,
        **({"call_mapping": "model_selected_unverified", "call_choices": choices,
            "call_selection_required": call_id is None} if ruleless else {}),
        "diagnosis_action_id": diagnosis["action_id"] if complete else None,
        "diagnosis_collection_status": collection_status,
        "original_effect_status": "original_effect_refuted",
        **({"diagnosis_evidence": evidence} if evidence else {}),
        **({"diagnosis_observation": _summary(diagnosis["output"]["call_path"])}
           if complete else {}),
        "preparation_available": not preparations, "preparation_action_ids": preparations,
        "rejected_requests": len(rejected), "execution_attempted": bool(executed),
        "unobserved_changes": changes,
        "factual_refutation": {
            "failure_action_id": failure["action_id"], "case_id": case["case_id"],
            "call_id": call_id, "candidate_diff_hash": current_diff,
            "original_failure": "unchanged", "unobserved_changes": copy.deepcopy(changes),
            "exception_sites": sites, "omitted_exception_site_count": omitted_sites,
            "exception_evidence_action_id": diagnosis["action_id"] if complete else None,
            "exception_evidence_diff_hash": observed_diff if complete else None,
            "interpretation": "Captured original failure and measured line absence refute the "
                "predicted original-call effect. Exception sites are observed samples; exceptions "
                "may be caught and a return event may be exception unwinding. No alternative "
                "repair mechanism or semantic correctness is established.",
        },
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
                and (request.get("call_id") in {row["call_id"]
                     for row in state.get("call_choices", [])}
                     if state.get("call_selection_required")
                     else request.get("call_id") == state["call_id"])
                and _watched_changes(request, state["unobserved_changes"])):
            return {**link(state), "call_id": request["call_id"]}
    raise ContractError(
        "Resolve the bounded original-call path diagnosis before another repair or verification "
        "action.", details={"repair_path": copy.deepcopy(state)},
    )
