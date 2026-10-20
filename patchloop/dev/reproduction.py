"""Frozen public reproduction evidence, separate from helper/process success.

Identity and JSON comparison are mechanical. The declared connection to the public
requirement remains model-authored; no host-certified task-success verdict is made.
"""

from __future__ import annotations

import copy
import json

from pydantic import BaseModel, ConfigDict, Field

from patchloop.dev.probe_cases import observation_json
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_bytes, sha256_json

DESCRIPTION = (
    "For a proposed original-task reproduction, set reproduction before execution: quote "
    "the public requirement, name the fully qualified Python entrypoint actually called, "
    "describe inputs/environment, and freeze expected_json. Print exactly one JSON value "
    "computed from the observed behavior. A helper experiment uses reproduction=null. "
    "The harness observes the declared Python call and compares stdout with the frozen "
    "expectation; neither proves that your chosen call represents the public requirement. "
    "After an edit, use replay_action_id with reproduction=null to keep the exact program, "
    "purpose and expected value. Changing them creates a different experiment, not resolution "
    "of the old one. reproduction_review separates helpers, unobserved calls, changed setup "
    "and same-reproduction comparisons. No extra probe or submission gate is imposed."
)


class Intent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    requirement_quote: str = Field(min_length=1, max_length=600)
    entrypoint: str = Field(
        min_length=3, max_length=200, pattern=r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$"
    )
    input_conditions: str = Field(min_length=1, max_length=400)
    environment_conditions: str = Field(min_length=1, max_length=400)
    expected_json: str = Field(min_length=1, max_length=2048)


def schema():
    result = Intent.model_json_schema()
    result.pop("title", None)
    for item in result["properties"].values():
        item.pop("title", None)
    return {"anyOf": [result, {"type": "null"}]}


def bind(raw, public_task, source, action_id, *, replay=None, events=()):
    if replay is not None:
        if raw is not None:
            raise ContractError("replay preserves reproduction; use reproduction=null")
        started = next(
            (
                e["payload"]
                for e in events
                if e["event_type"] == "action_started" and e["payload"]["action_id"] == replay
            ),
            {},
        )
        binding = started.get("reproduction_binding")
        if binding is None:
            return None
        prior = next(
            (
                e["payload"]["result"]
                for e in events
                if e["event_type"] == "action_finished"
                and e["payload"]["result"]["action_id"] == replay
            ),
            {},
        )
        observed = prior.get("output", {}).get("reproduction", {})
        if observed.get("binding") != binding or binding["program_hash"] != sha256_bytes(
            source.encode("utf-8")
        ):
            raise RecoveryError("reproduction replay identity mismatch")
        return copy.deepcopy(binding)
    if raw is None:
        return None
    if not isinstance(source, str) or not 1 <= len(source) <= 8_000:
        raise ContractError("probe source must contain 1-8000 characters")
    intent = Intent.model_validate(raw)
    task = public_task.model_dump(mode="json")
    if not any(intent.requirement_quote in task["issue"][key] for key in ("title", "description")):
        raise ContractError("reproduction requirement_quote must occur in the public issue")
    expected, reason = observation_json(
        {"status": "passed", "exit_code": 0, "stdout": intent.expected_json}
    )
    if expected is None:
        raise ContractError(
            "reproduction expected_json must be bounded strict JSON: " + str(reason)
        )
    definition = {
        **intent.model_dump(),
        "expected_json": expected,
        "public_task_hash": sha256_json(task),
    }
    program_hash = sha256_bytes(source.encode("utf-8"))
    identity = sha256_json({"definition": definition, "program_hash": program_hash})
    for event in events:
        if event["event_type"] == "action_finished":
            old = (
                (event["payload"]["result"].get("output") or {})
                .get("reproduction", {})
                .get("binding")
            )
            if old is not None and old["case_id"] == identity:
                return copy.deepcopy(old)
    return {
        "case_id": identity,
        "definition": definition,
        "program_hash": program_hash,
        "root_action_id": action_id,
    }


# Executed within the existing probe sandbox, with its unchanged source/output/time
# limits. Like setup/line feedback, this in-process observation is not an attestation.
_TRACE = """import sys as _pr_sys, os as _pr_os, json as _pr_json
_pr_rows = []
_pr_more = [False]
def _pr_value(v, depth=0):
    if v is None or type(v) in (bool, int, float, str):
        if type(v) is str and len(v) > 256:
            _pr_more[0] = True
            return {"omitted": "long_string"}
        return v
    if depth < 2 and type(v) in (list, tuple) and len(v) <= 16:
        return [_pr_value(x, depth+1) for x in v]
    if depth < 2 and type(v) is dict and len(v) <= 16 and all(type(k) is str for k in v):
        return {k: _pr_value(x, depth+1) for k, x in v.items()}
    _pr_more[0] = True
    return {"omitted_type": type(v).__module__ + "." + type(v).__name__}
def _pr_trace(frame, event, arg):
    if event != "call":
        return
    code = frame.f_code
    name = getattr(code, "co_qualname", code.co_name)
    if not hasattr(code, "co_qualname") and "self" in frame.f_locals:
        name = type(frame.f_locals["self"]).__qualname__ + "." + code.co_name
    target = frame.f_globals.get("__name__", "") + "." + name
    if target != _pr_target:
        return
    if len(_pr_rows) >= 4:
        _pr_more[0] = True
        return
    count = code.co_argcount + code.co_kwonlyargcount
    count += bool(code.co_flags & 4) + bool(code.co_flags & 8)
    values = {k: _pr_value(frame.f_locals[k]) for k in code.co_varnames[:count]
              if k in frame.f_locals and k not in ("self", "cls")}
    _pr_rows.append({"entrypoint": target, "arguments": values,
                     "cwd": _pr_os.getcwd(), "sys_path": list(_pr_sys.path)})
_pr_old = _pr_sys.getprofile()
_pr_sys.setprofile(_pr_trace)
try:
    exec(compile(_pr_source, "<patchloop-reproduction>", "exec"), globals())
finally:
    _pr_sys.setprofile(_pr_old)
    try:
        _pr_report = _pr_json.dumps({"calls": _pr_rows, "incomplete": _pr_more[0]},
                                    ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        if len(_pr_report) > 6000:
            _pr_report = '{"calls":[],"incomplete":true}'
        _pr_os.write(2, ("\\n" + _pr_marker + _pr_report + "\\n").encode())
    except (ValueError, OverflowError, OSError):
        pass
"""


def marker(binding):
    return "\x1ePATCHLOOP-REPRODUCTION:" + binding["case_id"] + ":"


def program(source, binding):
    return (
        f"_pr_target = {binding['definition']['entrypoint']!r}\n"
        f"_pr_marker = {marker(binding)!r}\n_pr_source = {source!r}\n" + _TRACE
    )


def compare(output, binding):
    result = copy.deepcopy(output)
    # Keep raw execution and authored-program identities distinct.
    result["execution_source_hash"] = result.get("source_hash")
    result["source_hash"] = binding["program_hash"]
    prefix = marker(binding)
    stderr = result.get("stderr", "")
    frames = [part for part in stderr.split("\n") if part.startswith(prefix)]
    result["stderr"] = "\n".join(part for part in stderr.split("\n") if not part.startswith(prefix))
    trace = {"calls": [], "incomplete": True}
    if len(frames) == 1:
        try:
            candidate = json.loads(frames[0][len(prefix) :])
            if (
                isinstance(candidate, dict)
                and set(candidate) == {"calls", "incomplete"}
                and type(candidate["incomplete"]) is bool
                and isinstance(candidate["calls"], list)
                and len(candidate["calls"]) <= 4
                and all(
                    isinstance(c, dict)
                    and set(c) == {"entrypoint", "arguments", "cwd", "sys_path"}
                    and c["entrypoint"] == binding["definition"]["entrypoint"]
                    and isinstance(c["arguments"], dict)
                    and isinstance(c["cwd"], str)
                    and isinstance(c["sys_path"], list)
                    and all(isinstance(p, str) for p in c["sys_path"])
                    for c in candidate["calls"]
                )
            ):
                trace = candidate
        except (ValueError, TypeError):
            pass
    actual, reason = observation_json(result)
    if not trace["calls"] or trace["incomplete"]:
        reason = "declared_call_unobserved_or_incomplete"
    result["reproduction"] = {
        "binding": binding,
        "call_observation": trace,
        "observed_json": actual,
        "comparison": (
            "not_compared"
            if reason
            else "matched"
            if actual == binding["definition"]["expected_json"]
            else "mismatched"
        ),
        "reason": reason,
        "requirement_mapping": "model_authored_unverified",
        "reported_failure_match": "not_assessed",
        "repair_success": "not_assessed",
        "interpretation": "Frozen expectation comparison and observed Python calls only. "
        "A baseline mismatch is not automatically the reported failure. Declared setup/entrypoint "
        "may not represent the public task; in-process feedback is not an attestation.",
    }
    return result


def review(events, current_diff):
    cases, helper_count = {}, 0
    for event in events:
        if event["event_type"] != "action_finished":
            continue
        result = event["payload"]["result"]
        if result["tool"] != "run_probe":
            continue
        repro = (result.get("output") or {}).get("reproduction")
        if repro is None:
            # Rejected declarations/replays are actions, not executed helpers.
            helper_count += isinstance((result.get("output") or {}).get("source_hash"), str)
            continue
        binding = repro["binding"]
        row = {
            "action_id": result["action_id"],
            "diff_hash": result["workspace_diff_hash"],
            "comparison": repro["comparison"],
            "reason": repro["reason"],
            "call_observation": repro["call_observation"],
        }
        case = cases.setdefault(
            binding["case_id"], {"binding": binding, "baseline": None, "latest": None}
        )
        # A new declaration is a new baseline; it cannot resolve a previous case.
        if result["action_id"] == binding["root_action_id"]:
            case["baseline"] = row
        case["latest"] = row
    items = []
    for case in cases.values():
        base, latest = case["baseline"], case["latest"]
        progress = "baseline_not_observed"
        if base is not None:
            if latest["diff_hash"] != current_diff:
                progress = "current_diff_not_observed"
            elif latest["diff_hash"] == base["diff_hash"]:
                progress = "no_modified_diff_comparison"
            elif base["comparison"] != "mismatched":
                progress = "baseline_not_different"
            elif latest["comparison"] == "not_compared":
                progress = "current_observation_incomplete"
            elif call_identity(base["call_observation"]) != call_identity(
                latest["call_observation"]
            ):
                progress = "observed_call_or_setup_changed"
            else:
                progress = (
                    "mismatch_to_match" if latest["comparison"] == "matched" else "still_mismatched"
                )

        def compact(row):
            return (
                None if row is None else {k: v for k, v in row.items() if k != "call_observation"}
            )

        items.append(
            {
                "case_id": case["binding"]["case_id"],
                "purpose": case["binding"]["definition"],
                "baseline": compact(base),
                "latest": compact(latest),
                "comparison_status": progress,
                "requirement_mapping": "model_authored_unverified",
                "repair_success": "not_assessed",
            }
        )
    return {
        "original_task_verification": "mapping_unverified" if items else "no_bound_reproduction",
        "helper_or_unbound_executions": helper_count,
        "items": items[:3],
        "omitted_count": max(0, len(items) - 3),
        "interpretation": "Helper results and suite PASS cannot resolve a reproduction. "
        "Replay the original action on the current diff, preserving its purpose and predicate. "
        "Even mismatch_to_match verifies only that declared experiment; assess its connection "
        "to the reported caller/input/failure separately. Submission eligibility is unchanged.",
    }


def call_identity(trace):
    """Allow a fresh scratch cwd, preserving path relationships and all observed values."""

    def relative(value, cwd):
        if isinstance(value, str) and (
            value == cwd or value.startswith(cwd + "/") or value.startswith(cwd + "\\")
        ):
            return "$CWD" + value[len(cwd) :]
        if isinstance(value, list):
            return [relative(v, cwd) for v in value]
        if isinstance(value, dict):
            return {k: relative(v, cwd) for k, v in value.items()}
        return value

    return {
        "incomplete": trace["incomplete"],
        "calls": [relative(row, row["cwd"]) for row in trace["calls"]],
    }
