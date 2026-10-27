"""Bound diagnostic-presence observations to complete per-call public captures.

The selected literals and caller-to-requirement mapping remain model-authored.
This checks extraction consistency, not semantic task coverage or repair quality.
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from patchloop.dev import probe_requests
from patchloop.util import canonical_json, sha256_json

POLICY = "captured-diagnostic-v1"
CANONICAL_POLICY = "captured-diagnostic-v2"


class DiagnosticRule(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    field: str = Field(min_length=1, max_length=64)
    call_id: Literal["call-1", "call-2", "call-3", "call-4"]
    contains: str = Field(min_length=1, max_length=160)


class DiagnosticCodeRule(BaseModel):
    """Fresh diagnostic identity, independent of changing explanatory text."""

    model_config = ConfigDict(extra="forbid", strict=True)

    field: str = Field(min_length=1, max_length=64)
    call_id: Literal["call-1", "call-2", "call-3", "call-4"]
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Z]+[0-9]+[A-Z0-9_-]*$")


class BehaviorDiagnosticRule(DiagnosticCodeRule):
    """A selected failure signal or positive evidence of intended processing."""

    role: Literal["failure", "processing"]


def is_canonical(rules):
    return bool(rules) and all(isinstance(rule, DiagnosticCodeRule)
                              or isinstance(rule, dict) and "code" in rule for rule in rules)


def is_usable(judgment):
    """Legacy agreement and fresh host computation are distinct usable evidence."""
    return isinstance(judgment, dict) and (
        judgment.get("policy", POLICY) == POLICY and judgment.get("status") == "consistent"
        or judgment.get("policy") == CANONICAL_POLICY and judgment.get("status") == "computed")


def rules_schema():
    item = BehaviorDiagnosticRule.model_json_schema()
    item.pop("title", None)
    for value in item["properties"].values():
        value.pop("title", None)
    item["properties"]["code"].pop("pattern", None)
    return {"anyOf": [
        {"type": "array", "items": item, "minItems": 1, "maxItems": 4},
        {"type": "null"},
    ], "description": "Declare each field's call_id and stable diagnostic code, e.g. F0010. "
                         "Codes are uppercase letters followed by digits (up to 32 characters). "
                         "The host computes booleans from complete per-call stdout and stderr; "
                         "do not reimplement extraction or call record_observation. "
                         "Pair failure absence with a positive processing code on the same call. "
                         "For silent processing use null and observe actual returned/output data."}


def validate(rules, expected_json, reported_failure_json):
    """Validate declaration shape without inferring whether its literal is correct."""
    if rules is None:
        return
    fields = [rule.field if isinstance(rule, BaseModel) else rule["field"]
              for rule in rules]
    if len(set(fields)) != len(fields):
        raise probe_requests.error("diagnostic_rules must have distinct field keys",
                                   "/purpose/diagnostic_rules")
    for key, text in (("expected_json", expected_json),
                      ("reported_failure_json", reported_failure_json)):
        value = json.loads(text)
        if (not isinstance(value, dict) or set(value) != set(fields)
                or any(type(item) is not bool for item in value.values())):
            raise probe_requests.error(
                "diagnostic declarations must be boolean objects with exactly the rule fields",
                "/purpose/" + key, "/purpose/diagnostic_rules")
    normalized = [rule.model_dump() if isinstance(rule, BaseModel) else rule for rule in rules]
    if any("role" in rule for rule in normalized):
        desired = json.loads(expected_json)
        failures = {rule["call_id"] for rule in normalized if rule.get("role") == "failure"}
        processing = {rule["call_id"] for rule in normalized
                      if rule.get("role") == "processing"}
        if not failures or failures != processing or any(
            rule.get("role") not in {"failure", "processing"}
            or desired[rule["field"]] != (rule["role"] == "processing")
            for rule in normalized
        ):
            raise probe_requests.error(
                "Each diagnostic call needs failure=false and processing=true in expected_json; "
                "select positive public processing evidence from that same call. "
                "For a silent target use null rules and actual processed results instead.",
                "/purpose/diagnostic_rules", "/purpose/expected_json")
        signals = {}
        for rule in normalized:
            key = (rule["call_id"], rule["code"])
            if key in signals and signals[key] != rule["role"]:
                raise probe_requests.error(
                    "The same call/code cannot be both absent failure and present processing",
                    "/purpose/diagnostic_rules")
            signals[key] = rule["role"]


def evaluate(rules, trace, authored_json, *, reason=None):
    """Compute field values independently per stream; incomplete is never absent."""
    normalized = [rule.model_dump() if isinstance(rule, BaseModel) else rule
                  for rule in rules]
    canonical = is_canonical(normalized)
    result = {"policy": CANONICAL_POLICY if canonical else POLICY, "status": "unknown",
              "rules_hash": sha256_json(normalized),
              "host_json": None, "authored_json": authored_json, "witnesses": [],
              "reason": reason, **({"source": "host"} if canonical else {})}
    if reason is not None:
        return result
    calls = trace.get("calls", [])
    by_id = {call.get("call_id"): call for call in calls}
    if trace.get("incomplete") is not False or len(by_id) != len(calls):
        result["reason"] = "diagnostic_capture_unavailable"
        return result
    values = {}
    witnesses = []
    for rule in normalized:
        call = by_id.get(rule["call_id"], {})
        capture = call.get("capture", {})
        if (capture.get("scope") != "python-streams" or capture.get("status") != "complete"
                or call.get("outcome") not in {"returned", "system_exit", "raised"}
                or (call.get("outcome") == "raised" and (
                    not call.get("exception")
                    or call["exception"].get("type") not in call.get("exception_policy", [])))
                or not all(isinstance(capture.get(channel), str)
                           for channel in ("stdout", "stderr"))):
            result["reason"] = "diagnostic_capture_unavailable"
            return result
        matches = []
        for channel in ("stdout", "stderr"):
            text = capture[channel]
            token = rule["code"] if canonical else rule["contains"]
            match = (re.search(r"(?<![A-Za-z0-9_-])" + re.escape(token)
                               + r"(?![A-Za-z0-9_-])", text) if canonical else None)
            offset = ((match.start() if match else -1) if canonical else text.find(token))
            if offset >= 0:
                matches.append({"channel": channel, "character_offset": offset,
                                "text": token})
        values[rule["field"]] = bool(matches)
        witnesses.append({"field": rule["field"], "call_id": rule["call_id"],
                          "capture_status": "complete", "channels": ["stdout", "stderr"],
                          "matches": matches})
    result.update(host_json=canonical_json(values), witnesses=witnesses)
    result["status"] = ("computed" if canonical else "consistent"
                        if result["host_json"] == authored_json else "conflict")
    result["reason"] = None if is_usable(result) else "observation_conflict"
    return result
