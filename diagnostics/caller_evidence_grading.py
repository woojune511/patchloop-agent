"""Bound public annotations and repair outcomes, without a paid or semantic auto-judge."""
from __future__ import annotations

import json
from collections import Counter

from diagnostics.caller_uptake import read_ref
from diagnostics.decision_sampler import require
from patchloop.util import canonical_json

G = {"ACQUIRED_SOURCE", "ACQUIRED_EXECUTION", "ATTEMPT_FAILED", "NOT_ACQUIRED", "UNKNOWN"}
D = {"COMPLETE", "PARTIAL_OR_TRUNCATED", "LOST_AT_HANDOFF", "STALE_AFTER_EDIT",
     "NOT_ACQUIRED_OR_SUPPLIED", "UNKNOWN"}
J = {"SUPPORTED", "OVERCLAIM", "NO_EXPLICIT_JUDGMENT", "UNKNOWN", "NO_DECISION_OPPORTUNITY"}
ACTIONS = {"SUPPORTED", "UNSUPPORTED", "NONE", "UNKNOWN"}


def event(ref, allowed, row_id):
    require(ref["path"] in allowed and allowed[ref["path"]] == ref["hash"],
            "unbound public evidence")
    audit = json.loads(read_ref({k: ref[k] for k in ("path", "hash")}))
    require(audit["row_id"] == row_id, "evidence belongs to another row")
    matches = [e for e in audit["events"] if e["sequence"] == ref["sequence"]
               and e["event_hash"] == ref["event_hash"]]
    require(len(matches) == 1, "public event identity mismatch")
    return matches[0], audit


def material(ref, allowed, row_id):
    bound, _ = event(ref, allowed, row_id)
    value = bound
    # Explicit JSON path can traverse a serialized current-state content field.
    for key in ref["keys"]:
        if isinstance(value, str):
            value = json.loads(value)
        value = value[key]
    text = value if isinstance(value, str) else canonical_json(value)
    quote = ref["quote"]
    require(isinstance(quote, str) and quote and quote in text, "material quote missing")
    return bound, quote


def contains(wire, quote):
    if isinstance(wire, str):
        if quote in wire:
            return True
        try:
            return contains(json.loads(wire), quote)
        except (ValueError, TypeError):
            return False
    if isinstance(wire, dict):
        return quote in canonical_json(wire) or any(contains(v, quote) for v in wire.values())
    if isinstance(wire, list):
        return any(contains(v, quote) for v in wire)
    return False


def validate_annotation(row, allowed):
    """Check mechanical lineage; a human still owns relevance and semantic judgment."""
    label = row["row_id"]
    require(row["G"] in G and row["D"] in D and row["J"] in J
            and row["action_use"] in ACTIONS, "unknown audit label")
    require(all(row.get(k) for k in ("reviewer", "rationale", "alternatives")),
            "human scope review required")
    audit_ref = row["audit"]
    require(audit_ref["path"] in allowed and allowed[audit_ref["path"]] == audit_ref["hash"],
            "unbound row audit")
    audit = json.loads(read_ref(audit_ref))
    require(audit["row_id"] == label, "audit belongs to another row")
    complete = [e for e in audit["events"] if e["event_type"] == "turn_decision_recorded"
                and not e["payload"].get("error_code")
                and not e["payload"].get("incomplete_reason") and e["payload"].get("tool_calls")]
    require(row["acquisition_origin"] in {"autonomous", "prompted_verification", "none"},
            "unknown acquisition origin")
    if row["G"].startswith("ACQUIRED"):
        require(row["acquisition_origin"] == "autonomous" and row.get("acquisition"),
                "supplied/copied evidence is not autonomous acquisition")
    for ref in row.get("acquisition", []):
        bound, _ = material(ref, allowed, label)
        require(bound["event_type"] == "action_finished"
                and bound["payload"]["result"]["tool"] in
                {"read_file", "search_files", "run_probe"}, "acquisition requires a public action")
    if row["J"] in {"SUPPORTED", "OVERCLAIM"} or row["action_use"] == "SUPPORTED":
        require(row["D"] == "COMPLETE" and row.get("evidence"),
                "adequate delivered evidence required for evidence-present judgment")
    decision_ref = row.get("first_decision")
    if decision_ref:
        decision, audit = event(decision_ref, allowed, label)
        require(complete and decision == complete[0], "first complete decision must be assessed")
        require(row["J"] != "NO_DECISION_OPPORTUNITY", "decision opportunity exists")
    else:
        require(row["J"] in {"NO_DECISION_OPPORTUNITY", "UNKNOWN"}, "decision reference required")
        require(row["J"] != "NO_DECISION_OPPORTUNITY" or not complete,
                "decision opportunity exists")
    first_linked = False
    for item in row.get("evidence", []):
        observed, quote = material(item["material"], allowed, label)
        request, _ = event(item["request"], allowed, label)
        decision, _ = event(item["decision"], allowed, label)
        require(request["event_type"] == "provider_call_started"
                and decision["event_type"] == "turn_decision_recorded"
                and observed["sequence"] <= request["sequence"] < decision["sequence"]
                and request["payload"]["turn_id"] == decision["payload"]["turn_id"]
                and contains(request["payload"]["wire"], quote)
                and item["scope_rationale"], "evidence/decision delivery mismatch")
        first_linked |= bool(decision_ref and decision["sequence"] == decision_ref["sequence"])
        require(item["origin"] in {"operator_supplied", "autonomous", "prompted_verification"},
                "evidence origin required")
        require(item["currency"] in {"current", "historical_acknowledged", "stale_unacknowledged"},
                "evidence currency required")
        if item["currency"] == "current":
            require(item["material_diff"] == item["decision_diff"], "stale failure called current")
        if row["J"] == "OVERCLAIM":
            require(item["currency"] == "current", "overclaim requires current contrary evidence")
    if row["J"] in {"SUPPORTED", "OVERCLAIM"} or row["action_use"] == "SUPPORTED":
        require(first_linked, "first judgment cannot borrow a later decision's evidence")
    for item in row.get("inventory", []):
        require(item["status"] in D and item["rationale"], "invalid evidence inventory")
        if item["status"] == "LOST_AT_HANDOFF":
            _, quote = material(item["material"], allowed, label)
            before, _ = event(item["before"], allowed, label)
            after, _ = event(item["after"], allowed, label)
            require(before["event_type"] == after["event_type"] == "provider_call_started"
                    and before["sequence"] < after["sequence"]
                    and contains(before["payload"]["wire"], quote)
                    and not contains(after["payload"]["wire"], quote)
                    and item["all_routes_reviewed"] is True, "retention loss not established")
    return {k: row[k] for k in ("G", "D", "J", "action_use", "acquisition_origin")}


def aggregate(rows, order):
    require(len(order) == len(set(order)) == 12
            and all(sum(label.startswith(a) for label in order) == 6 for a in "AB"),
            "twelve assigned rows required")
    require(len({r["row_id"] for r in rows}) == len(rows)
            and all(r["row_id"] in order for r in rows), "invalid row roster")
    by_id = {r["row_id"]: r for r in rows}
    records = []
    for label in order:
        raw = by_id.get(label, {})
        s = raw.get("submitted") is True and raw.get("registered") == raw.get("native") == "PASS"
        t = raw.get("submitted") is True and raw.get("missing") == raw.get("present") == "PASS"
        if s or t:
            require(raw.get("submitted_diff") == raw.get("assessed_from_diff")
                    == raw.get("native_diff") and bool(raw.get("submitted_diff"))
                    and raw.get("source_only_diff") == raw.get("caller_diff")
                    and bool(raw.get("source_only_diff")), "assessment diff lineage mismatch")
        records.append({"row_id": label, "arm": label[0], "S": bool(s), "T": bool(t),
                        "Q": bool(s and t), "audit": raw.get("audit", {}), "raw": raw})
    arms = {a: {"intended": 6, **{k: sum(r[k] for r in records if r["arm"] == a)
                                for k in ("S", "T", "Q")},
                **{k: dict(Counter(r["audit"].get(k, "NOT_RUN") for r in records
                                  if r["arm"] == a)) for k in ("G", "D", "J", "action_use")}}
            for a in "AB"}
    complete = all(r["raw"].get("completed") and r["raw"].get("settled")
                   and r["raw"].get("cleanup") and (not r["raw"].get("submitted") or (
                       r["raw"].get("registered") == r["raw"].get("native")
                       and r["raw"].get("native") in {"PASS", "FAIL"}
                       and all(r["raw"].get(k) in {"PASS", "FAIL"} for k in ("missing", "present"))
                       and r["raw"].get("safety") == "PASS")) for r in records)
    signal = (complete and arms["B"]["Q"] > arms["A"]["Q"]
              and sum(r["arm"] == "B" and r["Q"] and r["audit"].get("J") == "SUPPORTED"
                      and r["audit"].get("action_use") == "SUPPORTED" for r in records) >= 2
              and all(r["raw"].get("present") != "FAIL" for r in records))
    return {"rows": records, "arms": arms, "complete": complete,
            **{k + "_B_minus_A": arms["B"][k] - arms["A"][k] for k in ("S", "T", "Q")},
            "favorable_local_signal": signal, "automatic_followup": False,
            "official": False, "claim_eligible": False}
