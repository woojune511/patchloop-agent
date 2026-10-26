"""One optional, original-call observation before the first successful edit.

This module projects public receipts and constructs a frozen replay request. It
does not execute targets, require an observation before editing, or judge repairs.
"""

from __future__ import annotations

import copy
import json

from patchloop.dev import completion_reproduction, probe_invocation, probe_judgment, reproduction
from patchloop.errors import ContractError
from patchloop.sandbox import call_path_trace
from patchloop.util import sha256_bytes, sha256_json

POLICY = "first-original-observation-v1"
TOOL_NAME = "observe_original"
MAX_REJECTED_REQUESTS = 2
EMPTY_DIFF = sha256_bytes(b"")
PREDICTIONS = ("entered", "not_entered", "returned", "raised")
LINK_FIELDS = ("policy", "candidate_diff_hash", "case_id", "replay_action_id", "call_id")
IDENTITY = ("origin", "path", "function", "file_hash")


def schema():
    identity = call_path_trace.schema()["properties"]["focus"]["properties"]
    return {
        "type": "function", "name": TOOL_NAME, "strict": True,
        "description": (
            "Optionally test a first-repair hypothesis on the acquired original call. "
            "Select one or two public functions and predict their trace events. The host "
            "replays the unchanged caller, fixtures and controls once, deriving parameters "
            "and executable lines from source. returned means a return trace event; raised "
            "means an exception trace event, which may be caught. Neither proves a normal "
            "return or escaping exception. Unknown is not no-hit. Direct editing remains "
            "available; no plan or memory annotation is accepted."
        ),
        "parameters": {
            "type": "object", "additionalProperties": False,
            "required": ["hypothesis", "candidates"], "properties": {
                "hypothesis": {"type": "string", "minLength": 1, "maxLength": 1000},
                "candidates": {"type": "array", "minItems": 1, "maxItems": 2,
                               "items": {"type": "object", "additionalProperties": False,
                                         "required": [*identity, "prediction"],
                                         "properties": {**identity, "prediction": {
                                             "type": "string", "enum": list(PREDICTIONS)}}}},
            },
        },
    }


def _invalid(path, requirement):
    return ContractError(f"{path}: {requirement}", details={"invalid_fields": [
        {"path": path, "requirement": requirement}]})


def validate_selection(arguments):
    """Validate only model-owned selections; never accept replay/trace identities."""
    if type(arguments) is not dict or set(arguments) != {"hypothesis", "candidates"}:
        raise _invalid("/", "select only hypothesis and candidates")
    hypothesis, candidates = arguments["hypothesis"], arguments["candidates"]
    if type(hypothesis) is not str or not hypothesis.strip() or len(hypothesis) > 1000:
        raise _invalid("/hypothesis", "use 1-1000 characters")
    if type(candidates) is not list or not 1 <= len(candidates) <= 2:
        raise _invalid("/candidates", "select one or two public functions")
    seen = set()
    for index, candidate in enumerate(candidates):
        path = f"/candidates/{index}"
        if type(candidate) is not dict or set(candidate) != {
                "origin", "path", "function", "prediction"}:
            raise _invalid(path, "select origin, path, function and prediction only")
        if candidate["prediction"] not in PREDICTIONS:
            raise _invalid(path + "/prediction", "use entered, not_entered, returned or raised")
        target = {key: candidate[key] for key in ("origin", "path", "function")}
        try:
            call_path_trace.selection_request({"focus": target,
                "watches": [{**target, "fields": []}]}, "call-1")
        except ValueError as exc:
            raise _invalid(path, str(exc)) from exc
        identity = tuple(target.values())
        if identity in seen:
            raise _invalid(path, "select each function only once")
        seen.add(identity)
    return copy.deepcopy(arguments)


def link(state):
    """Stable original/diff identity shared by rejection, execution and recovery."""
    return {key: state[key] for key in LINK_FIELDS}


def prepare(arguments, state, workspace, source_preflight, *, deadline=None):
    selection = validate_selection(arguments)
    if state.get("status") != "available" or not state.get("available"):
        raise ContractError("first original-call observation is not available")
    if not callable(source_preflight):
        raise ContractError("public source binding is unavailable")
    targets = [{key: row[key] for key in ("origin", "path", "function")}
               for row in selection["candidates"]]
    request = {**call_path_trace.selection_request({"focus": targets[0],
        "watches": [{**target, "fields": []} for target in targets]}, state["call_id"]),
        "scope": "selected_call"}
    try:
        bound = source_preflight(workspace, request, deadline=deadline, line_changes=[])
    except (OSError, ValueError, SyntaxError) as exc:
        raise _invalid("/candidates", f"public source binding failed: {exc}") from exc
    # The preflight AST supplies parameters even though the model selected no fields.
    resolved = {"call_id": state["call_id"], "scope": "selected_call",
                "focus": {key: bound["focus"][key] for key in IDENTITY},
                "watches": [{**{key: watch[key] for key in (*IDENTITY, "lines")},
                             "fields": list(watch["parameters"])}
                            for watch in bound["watches"]]}
    return {**link(state), **selection, "selection_hash": sha256_json(selection),
            "call_path": resolved,
            "line_selection": [{"path": watch["path"], "function": watch["function"],
                                **watch["line_selection"]} for watch in bound["watches"]]}


def arguments(raw, admission):
    """The persisted small request keeps its own action hash; only execution uses this."""
    if sha256_json(validate_selection(raw)) != admission["selection_hash"]:
        raise ContractError("first observation selection differs from its admission")
    return {"question": None, "python_source": None, "purpose": None,
            "replay_action_id": admission["replay_action_id"],
            "call_path": copy.deepcopy(admission["call_path"])}


def _same_failure(result, baseline, identity):
    try:
        observed = result["output"]["reproduction"]
        return bool(
            result.get("workspace_diff_hash") == identity["candidate_diff_hash"]
            and observed["binding"] == baseline["binding"]
            and observed["binding"]["case_id"] == identity["case_id"]
            and observed["comparison"] == "mismatched"
            and observed.get("declared_failure_comparison") == "matched"
            and observed.get("judgment", {}).get("status") == "consistent"
            and baseline.get("judgment", {}).get("status") == "consistent"
            and json.loads(observed["observed_json"]) == json.loads(baseline["observed_json"])
            and completion_reproduction._healthy(result, observed)
            and probe_judgment.evaluate(observed["binding"]["definition"]["diagnostic_rules"],
                observed["call_observation"], observed["observed_json"])["status"] == "consistent"
            and reproduction.call_identity(observed["call_observation"])
            == reproduction.call_identity(baseline["call_observation"])
            and probe_invocation.conditions(observed["call_observation"])
            == probe_invocation.conditions(baseline["call_observation"]))
    except (KeyError, TypeError, ValueError):
        return False


def _failing_call(observation):
    try:
        definition = observation["binding"]["definition"]
        expected = json.loads(definition["expected_json"])
        actual = json.loads(observation["observed_json"])
        rules = definition.get("diagnostic_rules", [])
        controls = {rule["call_id"] for rule in rules
                    if actual[rule["field"]] is False and expected[rule["field"]] is False}
        return next((rule["call_id"] for rule in rules
                     if actual[rule["field"]] is True and expected[rule["field"]] is False
                     and controls - {rule["call_id"]}), None)
    except (KeyError, TypeError, ValueError):
        return None


def _trace_complete(result, start, dispatch, baseline, identity):
    admission = start.get("first_observation") or {}
    request = admission.get("call_path") or {}
    output = result.get("output") or {}
    trace = output.get("call_path") or {}
    if not (admission.get("selection_hash") == sha256_json(start.get("arguments"))
            and all(admission.get(key) == value for key, value in identity.items())
            and request.get("scope") == "selected_call"
            and trace.get("status") == "complete" and trace.get("reason") is None
            and trace.get("scope") == "selected_call_launch_thread"
            and trace.get("call_id") == request.get("call_id") == identity["call_id"]
            and trace.get("candidate_diff_hash") == identity["candidate_diff_hash"]
            and trace.get("snapshot_hash") is not None
            and trace["snapshot_hash"] == output.get("snapshot_hash")
            and trace.get("request_hash")
            and start.get("execution_identity") is not None
            and trace.get("execution_identity_hash") == sha256_json(start["execution_identity"])
            and trace.get("raw_request_hash") == sha256_json(request)
            and dispatch.get("call_path_request_hash") == sha256_json(request)
            and dispatch.get("execution_source_hash") is not None
            and dispatch["execution_source_hash"] == output.get("execution_source_hash")
            and _failing_call(baseline) == identity["call_id"]
            and _same_failure(result, baseline, identity)):
        return False
    requested = [request.get("focus", {}), *request.get("watches", [])]
    observed = [trace.get("focus", {}), *trace.get("watches", [])]
    if len(requested) != len(observed) or len(requested) != len(admission["candidates"]) + 1:
        return False
    for index, (target, row) in enumerate(zip(requested, observed, strict=True)):
        if (any(row.get(key) != target.get(key) for key in IDENTITY)
                or type(row.get("entries")) is not int or row["entries"] < 0
                or row.get("observation") != ("observed" if row["entries"] else "not_observed")
                or type(row.get("events")) is not list):
            return False
        if "event_counts" in row:
            counts = row["event_counts"]
            if (type(counts) is not dict
                    or set(counts) != {"call", "line", "return", "exception"}
                    or any(type(value) is not int or value < 0 for value in counts.values())
                    or counts["call"] != row["entries"]):
                return False
        if index and (row.get("fields") != target["fields"]
                      or row.get("not_observed_lines") is None
                      or set(row.get("observed_lines", [])) | set(row["not_observed_lines"])
                      != set(target["lines"])):
            return False
    return True


def _observation(start, result, complete):
    admission = start.get("first_observation") or {}
    trace = (result or {}).get("output", {}).get("call_path") or {}
    candidates = []
    for index, selected in enumerate(admission.get("candidates", [])):
        row = trace.get("watches", [])[index] if complete else {}
        events = row.get("events", [])
        counts = row.get("event_counts")
        outcomes = {"entered": bool(row.get("entries")),
                    "not_entered": row.get("entries") == 0,
                    "returned": counts["return"] > 0 if counts is not None
                    else any(e["event"] == "return" for e in events),
                    "raised": counts["exception"] > 0 if counts is not None
                    else any(e["event"] == "exception" for e in events)}
        exits = [event for event in events if event["event"] != "line"]
        status = ("prediction_matched" if outcomes[selected["prediction"]]
                  else "prediction_contradicted") if complete else "insufficient"
        candidates.append({**selected, "file_hash": admission["call_path"]["watches"][index][
            "file_hash"], "status": status,
            "entries": row.get("entries"), "observed_lines": row.get("observed_lines"),
            "not_observed_lines": row.get("not_observed_lines"),
            **({"event_counts": copy.deepcopy(counts)} if counts is not None else {}),
            "entry_exit_events": exits if len(exits) <= 4 else [*exits[:2], *exits[-2:]],
            "omitted_event_count": max(0, len(exits) - 4)})
    return {"action_id": start["action_id"], "input_hash": start.get("input_hash"),
            "hypothesis": admission.get("hypothesis"),
            "selection_hash": admission.get("selection_hash"), "candidates": candidates,
            "status": "observed" if complete else "insufficient",
            **({"collection": copy.deepcopy(trace["collection"])}
               if "collection" in trace else {}),
            "trace_identity": {key: trace.get(key) for key in (
                "request_hash", "raw_request_hash", "snapshot_hash", "execution_identity_hash")},
            "interpretation": "Predictions concern bounded trace events in the original call. "
            "Exceptions may be caught and return events may be unwinding; repair correctness "
            "and the model-authored hypothesis remain unverified."}


def review(events, current_diff, completion):
    """Never block edits; preserve a spent observation across recovery and later edits."""
    inactive = {"policy": POLICY, "status": "not_needed", "blocked": False, "available": False}
    starts = {e["payload"]["action_id"]: e["payload"] for e in events
              if e["event_type"] == "action_started"}
    results = {e["payload"]["result"]["action_id"]: e["payload"]["result"] for e in events
               if e["event_type"] == "action_finished"}
    dispatches = {e["payload"]["action_id"]: e["payload"] for e in events
                  if e["event_type"] == "probe_execution_started"}
    attempts = [s for s in starts.values() if s.get("tool") == TOOL_NAME
                and s.get("first_observation_link", {}).get("policy") == POLICY]
    edited = any(r.get("tool") == "replace_text" and r.get("status") == "succeeded"
                 for r in results.values())
    identity = copy.deepcopy(attempts[0]["first_observation_link"]) if attempts else None
    if identity is None:
        if edited or current_diff != EMPTY_DIFF or completion.get(
                "observation_correction", {}).get("blocked"):
            return inactive
        for case in completion.get("cases", []):
            if (case["case_id"] not in completion.get("baseline_failure_case_ids", [])
                    or not case.get("replayable") or case.get("evidence", {}).get(
                        "status") != "REFUTED"):
                continue
            baseline = results.get(case["root_action_id"], {}).get("output", {}).get(
                "reproduction", {})
            call_id = _failing_call(baseline)
            candidate = {"policy": POLICY, "candidate_diff_hash": current_diff,
                         "case_id": case["case_id"], "replay_action_id": case["root_action_id"],
                         "call_id": call_id}
            if call_id and _same_failure(results[case["root_action_id"]], baseline, candidate):
                identity = candidate
                break
    if identity is None:
        return inactive
    attempts = [s for s in attempts if s["first_observation_link"] == identity]
    rejected = [s for s in attempts if s.get("probe_request", {}).get("status") == "rejected"]
    reserved = [s for s in attempts if s not in rejected]
    eligible = (identity["case_id"] in completion.get("baseline_failure_case_ids", [])
                and not completion.get("observation_correction", {}).get("blocked"))
    stale = edited or current_diff != identity["candidate_diff_hash"] or not eligible
    spent = bool(reserved) or len(rejected) >= MAX_REJECTED_REQUESTS
    observation = None
    complete = False
    if reserved:
        start = reserved[0]
        result = results.get(start["action_id"])
        baseline = results.get(identity["replay_action_id"], {}).get("output", {}).get(
            "reproduction", {})
        complete = bool(result and _trace_complete(
            result, start, dispatches.get(start["action_id"], {}), baseline, identity))
        observation = _observation(start, result, complete)
    return {**identity, "status": "observed" if complete else "incomplete" if spent
            else "not_needed" if stale else "available", "blocked": False,
            "available": not spent and not stale, "stale": stale,
            "evidence_currency": "historical" if stale else "current",
            "rejected_requests": len(rejected), "max_rejected_requests": MAX_REJECTED_REQUESTS,
            "execution_reserved": bool(reserved),
            "execution_attempted": any(s["action_id"] in dispatches for s in attempts),
            "attempt_action_ids": [s["action_id"] for s in attempts],
            "observation": observation, "repair_correctness": "unverified"}
