"""Separate probe intent, execution scope, binding, delivered comparison and repair."""
from __future__ import annotations

import copy

from diagnostics import verification_state_grading as common
from diagnostics.positive_verification_panel import require

public_index = common.public_index


def inventory(public):
    rows, seen = [], set()
    for item in common.decisions(public):
        identity = (item["action_id"], item["input_hash"])
        if item["tool"] != "run_probe" or identity in seen:
            continue
        seen.add(identity)
        arguments = item["call"]["arguments"]
        purpose = arguments.get("purpose")
        receipt = item["receipt"]
        result = receipt["payload"]["result"] if receipt else {}
        repro = (result.get("output") or {}).get("reproduction") or {}
        rows.append({
            **{k: item[k] for k in ("decision_sequence", "action_id", "input_hash",
                                    "request_sequence", "request_hash", "diff_hash")},
            "receipt_hash": receipt["event_hash"] if receipt else None,
            "selected_kind": (purpose.get("kind") if isinstance(purpose, dict) else None)
            or ("legacy_original" if arguments.get("reproduction") else
                "replay" if arguments.get("replay_action_id") else "unbound"),
            "admitted": result.get("status") == "succeeded",
            "bound": bool(repro), "comparison": repro.get("comparison", "not_bound"),
            "reason": repro.get("reason"),
        })
    return rows


def validate_annotation(row, public):
    summary = common.validate_annotation(row, public)
    catalog = common.decisions(public)
    by_id = {(i["decision_sequence"], i["action_id"]): i for i in catalog}
    expected = inventory(public)
    annotations = row["probes"]
    require(len(annotations) == len(expected), "review every unique probe attempt")
    used = 0
    for actual, item in zip(annotations, expected, strict=True):
        require(actual["mechanical"] == item, "probe identity or mechanical result differs")
        require(actual["intent_scope"] in {"ORIGINAL", "HELPER", "UNKNOWN"}
                and actual["execution_scope"] in {"ORIGINAL", "HELPER", "UNKNOWN", "UNOBSERVED"}
                and actual["scope_rationale"] and actual["evidence"],
                "probe semantic scope required")
        events = common.public_index(public)
        for ref in actual["evidence"]:
            cited = common.quote(ref, events)
            require(cited["sequence"] in {item["decision_sequence"],
                    by_id[item["decision_sequence"], item["action_id"]]["receipt"]["sequence"]
                    if item["receipt_hash"] else None}, "scope must cite this probe")
        if not item["admitted"]:
            require(actual["execution_scope"] == "UNOBSERVED", "unexecuted scope cannot pass")
        use = actual.get("use")
        if use is None:
            continue
        subsequent = by_id.get((use.get("decision_sequence"), use.get("action_id")))
        original = by_id[item["decision_sequence"], item["action_id"]]
        receipt = original["receipt"]
        repro = receipt["payload"]["result"]["output"]["reproduction"] if item["bound"] else {}
        require(item["bound"] and item["comparison"] in {"matched", "mismatched"}
                and actual["execution_scope"] == "ORIGINAL" and subsequent is not None,
                "comparison use requires a bound compared original-path probe")
        require(subsequent["request_sequence"] > receipt["sequence"]
                and subsequent["diff_hash"] == item["diff_hash"]
                and all(use.get(k) == subsequent[k] for k in (
                    "input_hash", "request_sequence", "request_hash", "diff_hash")),
                "use must follow this receipt in its bound input")
        wire = subsequent["request"]["payload"]["wire"]["input"]
        require(common.contains(wire, repro["binding"]["case_id"])
                and common.contains(wire, repro["observed_json"])
                and common.contains(subsequent["call"], use.get("text"))
                and use.get("rationale") and use.get("semantic_review") is True,
                "delivered observation and explicit subsequent use required")
        used += 1
    require(row["changed_mechanism_applied"] != "YES" or used > 0,
            "package-use credit requires an observed comparison application")
    return {**summary, "probe_inventory": copy.deepcopy(expected),
            "probes_reviewed": len(expected), "bound_comparison_uses": used,
            "original_intent_count": sum(a["intent_scope"] == "ORIGINAL" for a in annotations),
            "original_execution_count": sum(
                a["execution_scope"] == "ORIGINAL" for a in annotations),
            "bound_probe_count": sum(i["bound"] for i in expected),
            "compared_probe_count": sum(
                i["comparison"] in {"matched", "mismatched"} for i in expected),
            "rejected_probe_attempts": sum(not i["admitted"] for i in expected)}


def aggregate(rows, order):
    result = common.aggregate(rows, order)
    for arm, summary in result["arms"].items():
        audits = [r.get("audit", {}).get("judgment", {}) for r in result["rows"]
                  if r["row_id"].startswith(arm)]
        for field in ("probes_reviewed", "original_intent_count", "original_execution_count",
                      "bound_probe_count", "compared_probe_count", "bound_comparison_uses",
                      "rejected_probe_attempts"):
            summary[field] = sum(a.get(field, 0) for a in audits)
    return result
