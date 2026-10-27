"""Bound a small next-step prediction to refutation, never judge prose as proof."""

from __future__ import annotations

import copy

from patchloop.dev import probe_judgment
from patchloop.errors import ContractError
from patchloop.util import sha256_json

POLICY = "refuted-repair-prediction-v1"
EVENTS = ("entered", "not_entered", "raised", "not_raised", "original_failure_absent")
IDENTITY = ("origin", "path", "function", "file_hash")


def decorate(path):
    """Number host-observed functions; the model never authors hashes or call IDs."""
    if path.get("status") != "diagnosed":
        return path
    observation = path.get("diagnosis_observation", {})
    targets = {}
    for row in [observation.get("focus", {}), *observation.get("watches", [])]:
        if all(key in row for key in IDENTITY):
            key = tuple(row[name] for name in IDENTITY[:3])
            targets[key] = row
    return {**path, "prediction_targets": [
        {"target": index, **{key: row[key] for key in IDENTITY},
         "event_counts": copy.deepcopy(row.get("event_counts")),
         "observed_lines": row.get("observed_lines", []),
         "not_observed_lines": row.get("not_observed_lines", [])}
        for index, row in enumerate(list(targets.values())[:5])],
        "prediction_guidance": (
            "State how the refutation changes your hypothesis. Select a changed observable "
            "on the same original call: target -1/original_failure_absent, or a listed function. "
            "not_raised requires function entry and zero exception events. Trace events are "
            "not normal-return or escaped-exception proofs. A prediction is not repair evidence.")}


def schema(path, *, test_enabled=False, suite_ids=()):
    variants = [{"type": "object", "additionalProperties": False,
        "properties": {
            "kind": {"type": "string", "enum": ["source"]},
            "target": {"type": "integer", "enum": [-1, *[
                row["target"] for row in path.get("prediction_targets", [])]]},
            "event": {"type": "string", "enum": list(EVENTS)},
        }, "required": ["kind", "target", "event"]}]
    if test_enabled and suite_ids:
        variants.append({"type": "object", "additionalProperties": False,
            "properties": {
                "kind": {"type": "string", "enum": ["test"]},
                "suite_id": {"type": "string", "enum": list(suite_ids)},
                "targets": {"type": "array", "minItems": 1, "maxItems": 1,
                            "description": "The added/extended test function or method node ID "
                                           "without parameters; e.g. tests/test_x.py::test_x.",
                            "items": {"type": "string", "minLength": 1, "maxLength": 500}},
            }, "required": ["kind", "suite_id", "targets"]})
    return {"anyOf": variants, "description": (
        "One next observation after the refuted repair. Source edits predict original-call "
        "behavior; a test addition reserves the same selected test on before/after source. "
        "The host binds the diagnosis and implementation attempt.")}


def _invalid(message):
    return ContractError(message, details={"invalid_fields": [
        {"path": "/repair_prediction", "requirement": message}]})


def _key(path):
    return {key: path.get(key) for key in ("mutation_action_id", "diagnosis_action_id")}


def review(events, current_diff, path):
    """One test comparison per diagnosed source attempt, independent of test diffs."""
    starts = [e["payload"] for e in events if e["event_type"] == "action_started"]
    results = {e["payload"]["result"]["action_id"]: e["payload"]["result"]
               for e in events if e["event_type"] == "action_finished"}
    tests = [s for s in starts if s.get("repair_prediction", {}).get("kind") == "test"
             and s.get("mutation_admitted") is True]
    pending = next((s for s in reversed(tests)
                    if (r := results.get(s["action_id"])) and r["status"] == "succeeded"
                    and r["workspace_diff_hash"] == current_diff), None)
    identity = _key(path)
    if pending is not None:
        identity = _key(pending["repair_prediction"])
    linked = [s for s in starts if s.get("repair_test_link") == identity]
    source_tests = [s for s in tests if _key(s["repair_prediction"]) == identity]
    completed = next((results[s["action_id"]] for s in reversed(linked)
                      if s["action_id"] in results), None)
    available = path.get("status") == "diagnosed" and not linked and not source_tests
    status = "available" if available else "not_needed"
    selection = None
    if pending is not None:
        selection = pending["repair_prediction"]["selection"]
        status = "needs_test_comparison"
    if completed:
        status = ("observed" if completed["status"] == "succeeded"
                  and completed.get("output", {}).get("comparison", {}).get("status")
                  in {"OBSERVED_FAIL_THEN_PASS", "PASSED_BOTH"}
                  else "unverified")
    return {"policy": POLICY, "status": status, "test_available": available,
            "pending_test": copy.deepcopy(selection) if status == "needs_test_comparison" else None,
            "test_link": identity,
            "test_mutation_action_id": pending["action_id"] if pending else None,
            "comparison_action_id": completed["action_id"] if completed else None,
            "comparison": copy.deepcopy(completed.get("output", {}).get("comparison"))
            if completed else None,
            "original_requirement_credit": False}


def admit(path, state, arguments, *, public_task):
    raw = arguments.get("repair_prediction")
    if path.get("status") != "diagnosed":
        if raw is not None:
            raise _invalid("repair_prediction requires a completed original-call diagnosis")
        return None
    if not isinstance(raw, dict):
        raise _invalid("after diagnosis provide one source prediction or a bounded test addition")
    base = {"policy": POLICY, **_key(path), "case_id": path["case_id"],
            "call_id": path["call_id"], "replay_action_id": path["replay_action_id"],
            "observed_diff_hash": path.get("diagnosis_evidence", {}).get(
                "observed_diff_hash", path["candidate_diff_hash"]),
            "refutation": copy.deepcopy(path.get("factual_refutation", {})),
            "hypothesis": arguments.get("hypothesis"),
            "expected_behavior": arguments.get("expected_behavior")}
    if raw.get("kind") == "source":
        if (set(raw) != {"kind", "target", "event"} or type(raw.get("target")) is not int
                or raw.get("event") not in EVENTS):
            raise _invalid("source prediction needs kind, integer target and a listed event")
        target = next((r for r in path.get("prediction_targets", [])
                       if r["target"] == raw["target"]), None)
        if (raw["target"] == -1) != (raw["event"] == "original_failure_absent"):
            raise _invalid("target -1 is reserved for original_failure_absent")
        if raw["target"] != -1 and target is None:
            raise _invalid("target must name a host-observed function")
        if target is not None and _event_matches(target, raw["event"]):
            raise _invalid("select a changed observable; this event was already true "
                           "in the failed run")
        return {**base, **raw, "function": copy.deepcopy(target)}
    if raw.get("kind") == "test":
        if (set(raw) != {"kind", "suite_id", "targets"}
                or not state.get("test_available")
                or raw.get("suite_id") not in {s.id for s in public_task.test_suites}
                or not isinstance(raw.get("targets"), list) or len(raw["targets"]) != 1
                or not isinstance(raw["targets"][0], str) or not 1 <= len(raw["targets"][0]) <= 500
                or raw["targets"][0].partition("::")[0] != arguments.get("path")):
            raise _invalid("select one available test comparison in the edited file "
                           "and registered suite")
        return {**base, "kind": "test", "selection": {
            "suite_id": raw["suite_id"], "targets": list(raw["targets"]),
            "comparison": {"baseline": "before_mutation",
                           "mutation_action_id": path["mutation_action_id"]}}}
    raise _invalid("repair_prediction.kind must be source or test")


def validate_test(state, path, arguments):
    if state.get("status") == "needs_test_comparison":
        if arguments != state["pending_test"]:
            raise ContractError("run the frozen before/after selection for this test addition")
        return state["test_link"]
    if path.get("status") != "diagnosed":
        return None
    if not state.get("test_available"):
        raise ContractError("the diagnosed implementation's selected-test comparison is spent")
    comparison = arguments.get("comparison")
    expected = {"baseline": "before_mutation", "mutation_action_id": path["mutation_action_id"]}
    if comparison != expected:
        raise ContractError("compare identical tests before the diagnosed implementation edit")
    if not isinstance(arguments.get("targets"), list) or len(arguments["targets"]) != 1:
        raise ContractError("the bounded diagnosis comparison selects exactly one test")
    return _key(path)


def validate_addition(path, before, after, selection):
    """The reserved comparison must collect a test introduced by this edit."""
    from patchloop.test_additions import added_tests

    additions = added_tests(before, after, path, suite_additions=True)
    target = selection["targets"][0]
    filename, _, node = target.partition("::")
    # Select the complete added function/method, including any newly added parameters.
    if filename != path or node not in {item["function"] for item in additions}:
        raise _invalid("select the full new or extended test function/method from this edit")


def _event_matches(row, event):
    counts = row.get("event_counts")
    if not isinstance(counts, dict) or any(type(counts.get(k)) is not int
                                           for k in ("call", "exception")):
        return None
    return {"entered": counts["call"] > 0, "not_entered": counts["call"] == 0,
            "raised": counts["exception"] > 0,
            "not_raised": counts["call"] > 0 and counts["exception"] == 0}.get(event)


def _invocation_fingerprint(output):
    from patchloop.dev import probe_invocation, reproduction

    observed = output.get("reproduction", {})
    trace = observed.get("call_observation")
    if not trace or not output.get("image_digest") or not output.get("profile_hash"):
        return None
    return sha256_json({
        "binding": observed["binding"], "calls": reproduction.call_identity(trace),
        "conditions": probe_invocation.conditions(trace),
        "image_digest": output["image_digest"], "profile_hash": output["profile_hash"],
    })


def prepare_replay(events, call, current_diff, run_id, workspace, preflight, *, deadline=None):
    """Add host tracing to the already-required replay; preserve its raw action identity."""
    from patchloop.dev import completion_reproduction
    from patchloop.sandbox import call_path_trace

    starts = {e["payload"]["action_id"]: e["payload"] for e in events
              if e["event_type"] == "action_started"}
    for event in reversed(events):
        if event["event_type"] != "action_finished":
            continue
        result = event["payload"]["result"]
        if (result["tool"] != "replace_text" or result["status"] != "succeeded"
                or result["workspace_diff_hash"] != current_diff):
            continue
        start = starts[result["action_id"]]
        prediction = start.get("repair_prediction", {})
        if prediction.get("kind") != "source":
            return None
        expected = completion_reproduction.replay_call(
            run_id, prediction["case_id"], prediction["replay_action_id"], current_diff)
        if call.action_id != expected.action_id or call.arguments != expected.arguments:
            return None
        root = next((e["payload"]["result"]["output"] for e in events
                     if e["event_type"] == "action_finished"
                     and e["payload"]["result"]["action_id"] == prediction["replay_action_id"]), {})
        admission = {"policy": POLICY, "mutation_action_id": result["action_id"],
                     "candidate_diff_hash": current_diff, "prediction": copy.deepcopy(prediction),
                     "invocation_fingerprint": _invocation_fingerprint(root),
                     "status": "ready", "call_path": None}
        if prediction["event"] == "original_failure_absent":
            return admission
        target = {key: prediction["function"][key] for key in IDENTITY[:3]}
        try:
            if not callable(preflight):
                raise ValueError("source trace binding unavailable")
            request = {**call_path_trace.selection_request({"focus": target,
                "watches": [{**target, "fields": []}]}, prediction["call_id"]),
                "scope": "selected_call"}
            bound = preflight(workspace, request, deadline=deadline, line_changes=[])
            admission["call_path"] = {
                "call_id": prediction["call_id"], "scope": "selected_call",
                "focus": {key: bound["focus"][key] for key in IDENTITY},
                "watches": [{**{key: w[key] for key in (*IDENTITY, "lines")},
                             "fields": list(w["parameters"])} for w in bound["watches"]]}
        except (ContractError, OSError, SyntaxError, ValueError) as exc:
            # Failure to observe a prediction must not prevent the original check.
            admission.update(status="unavailable", reason=str(exc))
        return admission
    return None


def assess(admission, result, execution_identity):
    """Separate prediction support from original-call effect on this exact diff."""
    from patchloop.dev import completion_reproduction

    prediction = admission["prediction"]
    reproduction = result.get("reproduction") or {}
    healthy = (admission["candidate_diff_hash"] == result.get("diff_hash")
               and reproduction.get("binding", {}).get("case_id") == prediction["case_id"]
               and probe_judgment.is_usable(reproduction.get("judgment"))
               and admission.get("invocation_fingerprint") is not None
               and admission["invocation_fingerprint"] == _invocation_fingerprint(result)
               and bool(reproduction) and completion_reproduction._healthy(
                   {"status": "succeeded", "output": result}, reproduction))
    original_effect = ("supported" if reproduction.get("comparison") == "matched" else "refuted")
    outcome = None
    if healthy and admission["status"] == "ready":
        if prediction["event"] == "original_failure_absent":
            outcome = reproduction["comparison"] == "matched"
        else:
            trace = result.get("call_path", {})
            request = admission["call_path"]
            if (trace.get("status") == "complete"
                    and trace.get("scope") == "selected_call_launch_thread"
                    and trace.get("call_id") == prediction["call_id"]
                    and trace.get("candidate_diff_hash") == admission["candidate_diff_hash"]
                    and trace.get("snapshot_hash") is not None
                    and trace.get("snapshot_hash") == result.get("snapshot_hash")
                    and trace.get("execution_identity_hash") == sha256_json(execution_identity)
                    and trace.get("raw_request_hash") == sha256_json(request)):
                row = trace.get("focus", {})
                if all(row.get(key) == request["focus"][key] for key in IDENTITY):
                    outcome = _event_matches(row, prediction["event"])
    return {"policy": POLICY, "mutation_action_id": admission["mutation_action_id"],
            "candidate_diff_hash": admission["candidate_diff_hash"],
            "diagnosis_action_id": prediction["diagnosis_action_id"],
            "prediction": {key: prediction[key] for key in ("target", "event")},
            "status": "unverified" if outcome is None else "matched" if outcome else "contradicted",
            "original_effect": original_effect if healthy else "unverified",
            "semantic_correctness": "unverified", "counts_toward_required_checks": False}
