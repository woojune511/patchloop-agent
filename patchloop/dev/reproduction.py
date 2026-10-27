"""Frozen public reproduction evidence, separate from helper/process success.

Identity and JSON comparison are mechanical. The declared connection to the public
requirement remains model-authored; no host-certified task-success verdict is made.
"""

from __future__ import annotations

import copy
import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from patchloop import probe_limits
from patchloop.dev import (
    probe_call_capture,
    probe_comparison,
    probe_invocation,
    probe_judgment,
    probe_requests,
)
from patchloop.dev.probe_cases import observation_json
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_bytes, sha256_json

REPLAY_DESCRIPTION = (
    "After an edit, use replay_action_id with purpose=null to keep the exact program, "
    "purpose and expected value."
)

DESCRIPTION = (
    "Choose purpose for each new probe: {kind: helper} explores a helper or uncertain path; "
    "kind=original_requirement binds the complete current public issue automatically; "
    "do not copy a requirement quote. Include a fully qualified Python entrypoint, "
    "input_conditions, "
    "environment_conditions, reported_failure_json and expected_json in that same object. "
    "reported_failure_json is the reported buggy result; expected_json is the desired result "
    "after repair. Both must be strict JSON and must differ. Choose observable properties "
    "that distinguish the reported failure from the desired behavior. Use one extractor for "
    "the failing input and a normal-input control, before and after repair. Check both error "
    "absence and positive evidence that the intended input was processed; an empty result "
    "can hide skipped work. Select a public output marker, processed item or returned data "
    "that would distinguish a no-op from the required behavior. "
    "Keep raw logs and call metadata in the separate call receipt, not in comparison values "
    "unless the requirement concerns them. "
    "Require a clean exit or absence of all diagnostics only when the public requirement "
    "requires it; keep unrelated diagnostics in logs. Derive each value from completed, "
    "interpretable target results. Missing output or an unexpected invocation/setup/parse "
    "failure must not become a false/no-error value: leave the observation incomplete. "
    "Observing an arbitrary mismatch does not reproduce the declared failure. No separate "
    "declaration step is needed. For original_requirement execute the declared entrypoint "
    "by creating target=observed_target(input_paths=[...], environment_keys=[...]), "
    "then calling it with ordinary Python arguments: call=target(['path']). "
    "Use only arguments supported by the inspected public signature; this example adds "
    "no target-specific keyword. "
    "A list argument is passed once, without an adapter args=[...] container. It "
    "resolves public aliases and constructors; do not replace it with a helper call. Select "
    "fixture files/directories in input_paths, not candidate implementation files; select "
    "relevant environment variable names in environment_keys. In original_requirement use "
    "root=Path(reproduction_workspace()) for fixtures, and "
    "outputs=Path(reproduction_outputs()) for generated files and HOME/cache children. "
    "These are separate stable roots in the fresh sandbox. Select actual fixture paths; "
    "generated output paths and ancestors containing them cannot be selected inputs. "
    "Declare cold/warm cache setup explicitly: a cache intentionally read by the target "
    "is an input fixture, not an ignored output. Create children and set environment "
    "variables explicitly. Avoid random temporary paths. "
    "The target starts with sys.argv=['<patchloop-reproduction>']; set explicit CLI argv "
    "before calling a CLI that reads it. Host tracing options are not target arguments. "
    "Empty lists mean no selected "
    "external inputs/variables, not complete environment coverage. call.value is the return "
    "value; call.stdout/stderr are bounded per-call Python streams, not repr(value). "
    "Choose the diagnostic channel from public behavior and inspect both captured streams; "
    "For diagnostic-presence booleans, include diagnostic_rules in purpose: "
    "Each rule has field, call_id, code and role ('failure' or 'processing'). "
    "Select the stable public diagnostic code, not its changing explanatory message. "
    "Each selected call must pair a failure rule expected false with a processing rule "
    "expected true. Choose the processing code from the intended fixture's public behavior, "
    "not an unrelated warning. A target that emits neither code must fail this conjunction. "
    "Each field is computed only by the host from that call's complete stdout AND stderr. "
    "The failure/desired objects must have exactly those boolean fields. With diagnostic_rules, "
    "only execute the target calls; do not write an extractor or call record_observation. "
    "The host uses the same rules before and after edits, so changed text with the same code "
    "remains a failure. Code selection and requirement mapping are still unverified. "
    "Use null rules for silent targets: record actual processed items/returned data together "
    "with the failure observation. Do not invent diagnostic output to satisfy a rule. "
    "do not assume stderr. call.outcome='returned' means the callable returned, not task success. "
    "call.exit_code is the observed SystemExit code; null means no exit code, never zero. "
    "capture_status='complete' means both streams were collected. With null rules, "
    "inspect capture_status and exception before extracting values. "
    + probe_call_capture.EXCEPTION_DESCRIPTION + " "
    "Direct fd/subprocess output is unobserved. "
    "Only with null diagnostic_rules, call "
    "record_observation(value) exactly once "
    "with the actual JSON-compatible observation (at most 2048 UTF-8 bytes). Print progress "
    "normally: probe logs are not auto-parsed; explicitly derive the observation from "
    "the target's return value, captured diagnostics or intended exception. Report an observed bug "
    "as a value, not an assertion against expected behavior; the host compares it. Setup "
    "failures, crashes and incomplete observations remain unverified. "
    "On preflight rejection, correct the named invalid_fields in the actual arguments with a "
    "new action_id. A changed explanation is not a correction; full preflight must pass. "
    "The harness records actual arguments, input-content fingerprints and execution environment "
    "at the call, and compares the recorded value with both frozen declarations. "
    "comparison_feedback lists bounded JSON Pointer differences (missing/extra/type/value); "
    "values remain in binding.definition and observed_json. It never changes declarations "
    "or certifies the selected channel, control or public-requirement mapping. "
    + REPLAY_DESCRIPTION + " Changing them creates a different experiment, not resolution "
    "of the old one. reproduction_review separates helpers, unobserved calls, changed setup "
    "and same-reproduction comparisons. At finish the host replays stale invocation-bound "
    "cases; current comparable mismatch/conflict blocks submission. Unknown remains unverified."
)

OBSERVATION_CHANNEL = "record-observation-v1"


class CallIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    entrypoint: str = Field(
        min_length=3, max_length=200, pattern=r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$"
    )
    input_conditions: str = Field(min_length=1, max_length=400)
    environment_conditions: str = Field(min_length=1, max_length=400)
    expected_json: str = Field(min_length=1, max_length=2048)


class Intent(CallIntent):
    """Legacy quotation-bearing binding; retained for exact recovery/replay."""

    requirement_quote: str = Field(min_length=1, max_length=600)


class OriginalIntent(CallIntent):
    """Fresh purposes distinguish the reported bug from the desired repaired result."""

    expected_json: str = Field(min_length=1, max_length=2048,
                               description="Desired observed result after the repair.")
    reported_failure_json: str = Field(
        min_length=1, max_length=2048,
        description="Reported buggy observed result before the repair; differs from expected_json.",
    )
    diagnostic_rules: list[probe_judgment.DiagnosticRule] | None = Field(
        default=None, min_length=1, max_length=4,
    )
    corrects_action_id: str | None = Field(default=None, min_length=1, max_length=500)


class LegacyOriginalIntent(OriginalIntent):
    requirement_quote: str = Field(min_length=1, max_length=600)


class CanonicalOriginalIntent(OriginalIntent):
    diagnostic_rules: list[probe_judgment.DiagnosticCodeRule] | None = Field(
        default=None, min_length=1, max_length=4,
    )


class BehaviorOriginalIntent(OriginalIntent):
    diagnostic_rules: list[probe_judgment.BehaviorDiagnosticRule] | None = Field(
        default=None, min_length=1, max_length=4,
    )


def schema():
    result = Intent.model_json_schema()
    result.pop("title", None)
    for item in result["properties"].values():
        item.pop("title", None)
    # Enforce this regex locally without adding it to the provider's output grammar.
    del result["properties"]["entrypoint"]["pattern"]
    return {"anyOf": [result, {"type": "null"}]}


def purpose_schema():
    original = BehaviorOriginalIntent.model_json_schema()
    original.pop("title", None)
    original.pop("$defs", None)
    for item in original["properties"].values():
        item.pop("title", None)
    del original["properties"]["entrypoint"]["pattern"]
    original["properties"]["diagnostic_rules"] = probe_judgment.rules_schema()
    original["properties"]["corrects_action_id"].pop("default", None)
    original["properties"] = {
        "kind": {"type": "string", "enum": ["original_requirement"]},
        **original["properties"],
    }
    original["required"] = ["kind", *original["required"],
                            "diagnostic_rules", "corrects_action_id"]
    return {"anyOf": [
        {"type": "object", "additionalProperties": False,
         "properties": {"kind": {"type": "string", "enum": ["helper"]}},
         "required": ["kind"]},
        original, {"type": "null"},
    ], "description": "Select helper or original_requirement; null only when replaying."}


def selection(arguments, *, allow_legacy=False):
    """Fresh purposes bind in the same action; old arguments keep their recovery identity."""
    if "purpose" not in arguments:
        return arguments.get("reproduction"), None
    if "reproduction" in arguments:
        raise probe_requests.error("use purpose, not both purpose and legacy reproduction",
                                   "/reproduction")
    purpose = arguments["purpose"]
    if purpose is None:
        if not (arguments.get("replay_action_id") or arguments.get("case_id")):
            raise probe_requests.error(
                "a new probe must select helper or original_requirement purpose", "/purpose")
        return None, None
    if purpose == {"kind": "helper"}:
        return None, None
    if not isinstance(purpose, dict) or purpose.get("kind") != "original_requirement":
        raise probe_requests.error("probe purpose must be helper or original_requirement",
                                   "/purpose")
    if not allow_legacy and "reported_failure_json" not in purpose:
        raise probe_requests.error(
            "original_requirement requires reported_failure_json for the reported "
            "bug and expected_json for the desired repaired result",
            "/purpose/reported_failure_json")
    if not allow_legacy and "requirement_quote" in purpose:
        raise probe_requests.error(
            "omit requirement_quote; the host binds the complete public issue",
            "/purpose/requirement_quote")
    return {k: v for k, v in purpose.items() if k != "kind"}, probe_invocation.CHANNEL


def bind(raw, public_task, source, action_id, *, replay=None, events=(),
         observation_channel=None):
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
    if not isinstance(source, str) or not 1 <= len(source) <= probe_limits.SOURCE_LIMIT_CHARS:
        raise probe_requests.error("probe source must contain 1-8000 characters", "/python_source")
    paired = isinstance(raw, dict) and "reported_failure_json" in raw
    legacy = isinstance(raw, dict) and "requirement_quote" in raw
    intent_type = (LegacyOriginalIntent if legacy else OriginalIntent) if paired else Intent
    if paired and not legacy:
        if observation_channel == probe_invocation.CANONICAL_CHANNEL:
            intent_type = CanonicalOriginalIntent
        elif observation_channel in probe_invocation.BEHAVIOR_CHANNELS:
            intent_type = BehaviorOriginalIntent
    try:
        intent = intent_type.model_validate(raw)
    except ValidationError as exc:
        if observation_channel not in (probe_invocation.DIAGNOSTIC_CHANNEL,
                                       probe_invocation.CANONICAL_CHANNEL,
                                       *probe_invocation.BEHAVIOR_CHANNELS):
            raise
        invalid = probe_requests.fields(exc, prefix="/purpose")
        for field in invalid:
            if field["path"].startswith("/purpose/diagnostic_rules/"):
                # The request correction tracker compares named argument fields;
                # point at the real rule list, not a type branch or list traversal.
                field["path"] = "/purpose/diagnostic_rules"
        raise ContractError("invalid original_requirement fields",
                            details={"invalid_fields": invalid}) from exc
    task = public_task.model_dump(mode="json")
    if legacy and not any(intent.requirement_quote in task["issue"][key]
                          for key in ("title", "description")):
        raise ContractError("reproduction requirement_quote must occur in the public issue")
    expected, reason = observation_json(
        {"status": "passed", "exit_code": 0, "stdout": intent.expected_json}
    )
    if expected is None:
        raise probe_requests.error(
            "reproduction expected_json must be bounded strict JSON: " + str(reason),
            "/purpose/expected_json" if observation_channel in (
                probe_invocation.DIAGNOSTIC_CHANNEL, probe_invocation.CANONICAL_CHANNEL,
                *probe_invocation.BEHAVIOR_CHANNELS)
            else "/reproduction/expected_json",
        )
    failure = None
    if paired:
        failure, reason = observation_json(
            {"status": "passed", "exit_code": 0, "stdout": intent.reported_failure_json})
        if failure is None:
            raise probe_requests.error(
                "reproduction reported_failure_json must be bounded strict JSON: " + str(reason),
                "/purpose/reported_failure_json")
        if failure == expected:
            raise probe_requests.error(
                "reported_failure_json and desired expected_json must differ",
                "/purpose/reported_failure_json", "/purpose/expected_json")
        probe_judgment.validate(intent.diagnostic_rules, expected, failure)
        if intent.diagnostic_rules:
            canonical = probe_judgment.is_canonical(intent.diagnostic_rules)
            canonical_channels = (probe_invocation.CANONICAL_CHANNEL,
                                  *probe_invocation.BEHAVIOR_CHANNELS)
            if ((observation_channel in canonical_channels and not canonical)
                    or (observation_channel not in canonical_channels and any(
                        isinstance(rule, probe_judgment.DiagnosticCodeRule)
                        for rule in intent.diagnostic_rules))):
                raise probe_requests.error(
                    "Fresh diagnostic_rules require stable code fields; contains is legacy-only",
                    "/purpose/diagnostic_rules")
    definition = {
        **intent.model_dump(exclude_none=True),
        "expected_json": expected,
        **({"reported_failure_json": failure} if paired else {}),
        "public_task_hash": sha256_json(task),
        **({"requirement_source": {"field": "issue", "issue_hash": sha256_json(task["issue"])}}
           if not legacy else {}),
        **({"observation_channel": observation_channel} if observation_channel else {}),
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

_RECORD = """_pr_observation = {"count": 0, "json": None, "error": None}
def record_observation(value):
    _pr_observation["count"] += 1
    if _pr_observation["count"] != 1:
        _pr_observation["error"] = "multiple_observations"
        raise ValueError("record_observation requires exactly one value")
    try:
        text = _pr_json.dumps(value, ensure_ascii=True, allow_nan=False,
                              separators=(",", ":"))
        if len(text.encode("utf-8")) > 2048:
            raise ValueError("observation exceeds 2048 bytes")
        _pr_observation["json"] = text
    except (ValueError, TypeError, OverflowError, RecursionError):
        _pr_observation["error"] = "invalid_observation"
        raise
"""


def marker(binding):
    return "\x1ePATCHLOOP-REPRODUCTION:" + binding["case_id"] + ":"


def program(source, binding, call_path=False):
    trace = _TRACE
    channel = binding["definition"].get("observation_channel")
    if probe_invocation.supports(channel):
        trace = probe_invocation.observer(channel)
    elif channel == OBSERVATION_CHANNEL:
        # Keep the legacy wrapper byte-for-byte for old declaration/action replays.
        trace = trace.replace("_pr_rows = []", _RECORD + "\n_pr_rows = []", 1).replace(
            '{"calls": _pr_rows, "incomplete": _pr_more[0]}',
            '{"calls": _pr_rows, "incomplete": _pr_more[0], "observation": _pr_observation}', 1)
    if call_path:
        if channel not in probe_invocation.CAPTURE_CHANNELS:
            raise ContractError("call-path diagnosis requires a captured original invocation")
        # These optional hooks surround only the actual invocation, after adapter
        # setup and before the existing capture finally. Default observer bytes stay exact.
        old = "   value = target(*args, **kwargs)"
        new = ("   _patchloop_call_path_begin(row['call_id'])\n"
               "   try:\n"
               "    value = target(*args, **kwargs)\n"
               "   finally:\n"
               "    _patchloop_call_path_end(row['call_id'])")
        if channel in probe_invocation.BEHAVIOR_CHANNELS:
            old = '   row["target_started"] = True\n' + old
            new = new.replace("    value = target(*args, **kwargs)",
                              '    row["target_started"] = True\n'
                              "    value = target(*args, **kwargs)")
        if trace.count(old) != 1:
            raise ContractError("call-path observer hook location is unavailable")
        trace = trace.replace(old, new, 1)
    prefix = (
        f"_pr_target = {binding['definition']['entrypoint']!r}\n"
        f"_pr_marker = {marker(binding)!r}\n_pr_source = "
    )
    suffix = "\n" + trace
    observer = prefix + suffix
    if (len(observer) > probe_limits.OBSERVER_LIMIT_CHARS
            or len(observer.encode("utf-8")) > probe_limits.OBSERVER_LIMIT_BYTES):
        raise ContractError("host reproduction observer exceeds its separate size limit")
    # Preserve rendered bytes and execution hashes for existing bindings/replays.
    return prefix + repr(source) + suffix


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
    channel = binding["definition"].get("observation_channel")
    rules = binding["definition"].get("diagnostic_rules")
    canonical = (
        channel in (probe_invocation.CANONICAL_CHANNEL, *probe_invocation.BEHAVIOR_CHANNELS)
        and probe_judgment.is_canonical(rules)
    )
    invoked = probe_invocation.supports(channel)
    recorded = invoked or channel == OBSERVATION_CHANNEL
    if len(frames) == 1:
        try:
            candidate = json.loads(frames[0][len(prefix) :])
            if (
                isinstance(candidate, dict)
                and set(candidate) == (
                    {"calls", "incomplete", "observation"} if recorded else {"calls", "incomplete"})
                and type(candidate["incomplete"]) is bool
                and isinstance(candidate["calls"], list)
                and len(candidate["calls"]) <= 4
                and all(
                    probe_invocation.valid_call(c, binding["definition"]["entrypoint"],
                                                channel=channel)
                    if invoked else isinstance(c, dict)
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
    actual, reason = observation_json(result) if not recorded else (None, "missing_observation")
    if recorded and canonical:
        # Diagnostic observations come from final complete call captures, not a
        # second model-written extractor. Preserve a supplied value as information
        # only; it cannot replace captures or turn a failed execution into credit.
        value = trace.get("observation")
        if isinstance(value, dict) and value.get("count") == 1 and isinstance(
                value.get("json"), str):
            actual, _ = observation_json(
                {"status": "passed", "exit_code": 0, "stdout": value["json"]})
        _, reason = observation_json({**result, "stdout": "null"})
        if result.get("setup_checks", {}).get("status") == "failed":
            reason = "setup_check_failed"
        trace = {key: trace[key] for key in ("calls", "incomplete")}
    elif recorded:
        value = trace.get("observation")
        fields = {"count", "json", "error"} | ({"call_count"} if invoked else set())
        if isinstance(value, dict) and set(value) == fields:
            if (value["error"] or type(value["count"]) is not int
                    or value["count"] not in (0, 1)):
                reason = "invalid_or_multiple_observations"
            elif value["count"] == 1 and isinstance(value["json"], str):
                # Preserve a recorded observation even if a later assertion/crash
                # fails the process. It cannot acquire matched/mismatched credit.
                actual, reason = observation_json(
                    {"status": "passed", "exit_code": 0, "stdout": value["json"]})
                if reason is None:
                    _, reason = observation_json({**result, "stdout": value["json"]})
            elif value["count"] == 1:
                reason = "invalid_or_multiple_observations"
            if invoked and value["count"] == 1 and not value["error"] and (
                    type(value["call_count"]) is not int
                    or value["call_count"] != len(trace["calls"])):
                reason = "observation_not_after_target_calls"
        if result.get("setup_checks", {}).get("status") == "failed":
            reason = "setup_check_failed"
        trace = {key: trace[key] for key in ("calls", "incomplete")}
    if not trace["calls"] or trace["incomplete"]:
        reason = "declared_call_unobserved_or_incomplete"
    if (channel in probe_invocation.CAPTURE_CHANNELS
            and probe_call_capture.incomplete(trace["calls"])):
        trace["incomplete"] = True
        reason = "declared_call_unobserved_or_incomplete"
    if invoked:
        trace.update(binding_method=channel,
                     execution_environment=probe_invocation.environment(result))
    judgment = (probe_judgment.evaluate(rules, trace, actual, reason=reason)
                if rules is not None else None)
    if judgment is not None:
        if probe_judgment.is_usable(judgment):
            actual = judgment["host_json"]
        else:
            reason = judgment["reason"]
    result["reproduction"] = {
        "binding": binding,
        "call_observation": trace,
        "observed_json": actual,
        **({"judgment": judgment} if judgment is not None else {}),
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
    if "reported_failure_json" in binding["definition"]:
        result["reproduction"]["declared_failure_comparison"] = (
            "not_compared" if reason else "matched"
            if actual == binding["definition"]["reported_failure_json"] else "mismatched")
    if reason is None and channel in probe_invocation.CAPTURE_CHANNELS:
        result["reproduction"]["comparison_feedback"] = {
            role: probe_comparison.differences(binding["definition"][field], actual)
            for role, field in (("desired", "expected_json"),
                                ("declared_failure", "reported_failure_json"))
            if field in binding["definition"]
        }
    return result


def _case_evidence(case, current_diff):
    """Judge a declared experiment, never the model's requirement mapping."""
    base = case["baseline"]
    current = [row for row in case["observations"] if row["diff_hash"] == current_diff]
    comparable = [
        row for row in current
        if base is not None and row["comparison"] in {"matched", "mismatched"}
        and not row["call_observation"]["incomplete"] and row["call_observation"]["calls"]
        and call_identity(row["call_observation"]) == call_identity(base["call_observation"])
    ]
    outcomes = {row["comparison"] for row in comparable}
    status = (
        "CONFLICT" if len(outcomes) == 2 else "REFUTED" if "mismatched" in outcomes
        else "SUPPORTED" if "matched" in outcomes else "UNKNOWN"
    )
    # One witness per outcome keeps a contradictory observation visible even if a
    # later execution succeeds. Different snapshots and observed setups do not pair.
    witnesses = {
        row["comparison"]: row["action_id"] for row in comparable
    }
    return {
        "status": status,
        "currency": "current" if current else "historical",
        "reason": "same_case_conflicting_observations" if status == "CONFLICT"
        else "frozen_expectation_comparison" if comparable
        else "no_comparable_current_observation",
        "evidence_action_ids": list(witnesses.values()),
    }


def _unbound_execution(result, current_diff):
    output = result.get("output") or {}
    diff = result.get("workspace_diff_hash")
    return {
        "action_id": result["action_id"], "tool": result["tool"], "diff_hash": diff,
        "currency": "unknown" if diff is None else "current" if diff == current_diff
        else "historical",
        "scope": "helper_or_unbound_diagnostic"
        if result["tool"] in {"run_probe", "observe_original"}
        else "registered_check" if result["tool"] == "run_check" else "selected_tests",
        "subject": str(output.get("question") or output.get("check_id")
                       or output.get("targets") or result["tool"])[:400],
        "subject_role": "model_authored_question"
        if result["tool"] in {"run_probe", "observe_original"}
        else "executed_check_identifier",
        "execution": {
            "action_status": result.get("status"),
            **{key: output[key] for key in (
                "status", "passed", "exit_code", "timed_out", "truncated",
                "deadline_exhausted", "cleanup_failed",
            ) if key in output},
        },
        "requirement_coverage": "not_assessed",
    }


def review(events, current_diff, *, public_task=None):
    cases, helper_count, other_executions = {}, 0, []
    for event in events:
        if event["event_type"] != "action_finished":
            continue
        result = event["payload"]["result"]
        if result["tool"] not in {"run_probe", "observe_original", "run_check", "run_tests"}:
            continue
        repro = (result.get("output") or {}).get("reproduction")
        if repro is None:
            # Rejected declarations/replays are actions, not executed helpers.
            helper_count += result["tool"] in {"run_probe", "observe_original"} and isinstance(
                (result.get("output") or {}).get("source_hash"), str)
            other_executions.append(_unbound_execution(result, current_diff))
            continue
        binding = repro["binding"]
        row = {
            "action_id": result["action_id"],
            "diff_hash": result["workspace_diff_hash"],
            "comparison": repro["comparison"],
            "reason": repro["reason"],
            "call_observation": repro["call_observation"],
            **({"declared_failure_comparison": repro["declared_failure_comparison"]}
               if "declared_failure_comparison" in repro else {}),
        }
        case = cases.setdefault(
            binding["case_id"], {
                "binding": binding, "baseline": None, "latest": None, "observations": [],
            },
        )
        # A new declaration is a new baseline; it cannot resolve a previous case.
        if result["action_id"] == binding["root_action_id"]:
            case["baseline"] = row
        case["latest"] = row
        case["observations"].append(row)
    items = []
    for case in cases.values():
        base, latest = case["baseline"], case["latest"]
        progress = "baseline_not_observed"
        if base is not None:
            if latest["diff_hash"] != current_diff:
                progress = "current_diff_not_observed"
            elif latest["comparison"] == "not_compared":
                progress = "current_observation_incomplete"
            elif call_identity(base["call_observation"]) != call_identity(
                latest["call_observation"]
            ):
                progress = "observed_call_or_setup_changed"
            elif latest["diff_hash"] == base["diff_hash"]:
                progress = "no_modified_diff_comparison"
            elif base["comparison"] != "mismatched":
                progress = "baseline_not_different"
            else:
                progress = (
                    "mismatch_to_match" if latest["comparison"] == "matched" else "still_mismatched"
                )

        def compact(row):
            if row is None:
                return None
            trace = row["call_observation"]
            link = (probe_invocation.summary(trace)
                    if probe_invocation.supports(trace.get("binding_method")) else {
                        "status": "incomplete" if trace["incomplete"] else
                        "called" if trace["calls"] else "not_called",
                        "call_count": len(trace["calls"]), "binding_method": "legacy_name_trace",
                    })
            return {**{k: v for k, v in row.items() if k != "call_observation"},
                    "execution_link": link}

        evidence = _case_evidence(case, current_diff)
        if evidence["status"] == "CONFLICT":
            progress = "conflicting_current_observations"
        items.append(
            {
                "case_id": case["binding"]["case_id"],
                "purpose": case["binding"]["definition"],
                "baseline": compact(base),
                "latest": compact(latest),
                "comparison_status": progress,
                "replay_action_id": case["binding"]["root_action_id"],
                "evidence": evidence,
                "requirement_mapping": "model_authored_unverified",
                "unverified_scope": [
                    "issue_to_entrypoint_mapping", "expectation_matches_requirement",
                    "reported_failure_match",
                    "unobserved_environment",
                ],
                "repair_success": "not_assessed",
            }
        )
    # Show material counterevidence first without losing the counts of omitted cases.
    priority = {"CONFLICT": 0, "REFUTED": 1, "UNKNOWN": 2, "SUPPORTED": 3}
    items.sort(key=lambda item: priority[item["evidence"]["status"]])
    return {
        "original_task_verification": "mapping_unverified" if items else "no_bound_reproduction",
        "required": {
            "source": "public_task.issue",
            "public_task_hash": (
                sha256_json(public_task.model_dump(mode="json"))
                if public_task is not None else None
            ),
            "status": "UNKNOWN",
            "reason": "requirement_mapping_unverified" if items else "no_bound_reproduction",
        },
        "current_diff_hash": current_diff,
        "helper_or_unbound_executions": helper_count,
        "items": items[:3],
        "omitted_count": max(0, len(items) - 3),
        "case_status_counts": {
            status: sum(item["evidence"]["status"] == status for item in items)
            for status in priority
        },
        "other_executions": other_executions[-3:],
        "other_executions_omitted_count": max(0, len(other_executions) - 3),
        "interpretation": "Code-derived evidence state, independent of notes and plan decisions. "
        "SUPPORTED/REFUTED concern a declared experiment, not the original task. UNKNOWN scope "
        "requires connecting the public issue to actual inputs, setup and observations. "
        "Helper/suite PASS and model dismissal cannot close it. "
        "The separate completion projection controls replay and comparable-case failure at finish.",
    }


def call_identity(trace):
    """Allow a fresh scratch cwd, preserving path relationships and all observed values."""

    if probe_invocation.supports(trace.get("binding_method")):
        # Python equality merges True/1/1.0; those are different call inputs.
        return sha256_json(probe_invocation.conditions(trace))

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
