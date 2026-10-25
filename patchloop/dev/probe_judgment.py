"""Bound diagnostic-presence observations to complete per-call public captures.

The selected literals and caller-to-requirement mapping remain model-authored.
This checks extraction consistency, not semantic task coverage or repair quality.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from patchloop.dev import probe_requests
from patchloop.util import canonical_json, sha256_json

POLICY = "captured-diagnostic-v1"


class DiagnosticRule(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    field: str = Field(min_length=1, max_length=64)
    call_id: Literal["call-1", "call-2", "call-3", "call-4"]
    contains: str = Field(min_length=1, max_length=160)


def rules_schema():
    item = DiagnosticRule.model_json_schema()
    item.pop("title", None)
    for value in item["properties"].values():
        value.pop("title", None)
    return {"anyOf": [
        {"type": "array", "items": item, "minItems": 1, "maxItems": 4},
        {"type": "null"},
    ], "description": "For diagnostic-presence booleans, declare each field's call_id and literal. "
                         "The host searches both complete per-call stdout and stderr. "
                         "Use null only for observations outside this diagnostic contract."}


def validate(rules, expected_json, reported_failure_json):
    """Validate declaration shape without inferring whether its literal is correct."""
    if rules is None:
        return
    fields = [rule.field if isinstance(rule, DiagnosticRule) else rule["field"]
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


def evaluate(rules, trace, authored_json, *, reason=None):
    """Compute field values independently per stream; incomplete is never absent."""
    normalized = [rule.model_dump() if isinstance(rule, DiagnosticRule) else rule
                  for rule in rules]
    result = {"policy": POLICY, "status": "unknown", "rules_hash": sha256_json(normalized),
              "host_json": None, "authored_json": authored_json, "witnesses": [],
              "reason": reason}
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
            offset = text.find(rule["contains"])
            if offset >= 0:
                matches.append({"channel": channel, "character_offset": offset,
                                "text": rule["contains"]})
        values[rule["field"]] = bool(matches)
        witnesses.append({"field": rule["field"], "call_id": rule["call_id"],
                          "capture_status": "complete", "channels": ["stdout", "stderr"],
                          "matches": matches})
    result.update(host_json=canonical_json(values), witnesses=witnesses)
    result["status"] = "consistent" if result["host_json"] == authored_json else "conflict"
    result["reason"] = None if result["status"] == "consistent" else "observation_conflict"
    return result
