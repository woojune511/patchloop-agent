"""Public, provenance-bound judgment audit; independent repair grades stay separate."""
from __future__ import annotations

from collections import Counter

from diagnostics import verification_role as role
from diagnostics import verification_state_grading as common
from diagnostics.positive_verification_panel import require
from patchloop.dev.conversation import reconstruct_state

public_index = common.public_index
CHAIN = ("phase_reached", "acquisition", "delivery", "interpretation", "feedback_delivery",
         "application")


def catalog(public):
    result = common.decisions(public)
    for item in result:
        state = reconstruct_state(item["request"]["payload"]["wire"]["input"],
                                  context_policy="segmented-v1")
        phase = state.get("verification_phase")
        require(isinstance(phase, dict) and phase.get("phase") in role.LIMITS,
                "decision has no bound verification phase")
        item.update(phase=phase["phase"], phase_state=phase,
                    candidate_present=bool(state["current_diff"].get("patch")))
    return result


def report_inventory(public):
    seen, reports = set(), []
    for item in catalog(public):
        identity = item["action_id"], item["input_hash"]
        if item["tool"] != role.REPORT_TOOL or identity in seen:
            continue
        seen.add(identity)
        reports.append({**{k: item[k] for k in (
            "decision_sequence", "action_id", "input_hash", "request_sequence", "request_hash",
            "diff_hash", "phase")}, "receipt_hash": (
                item["receipt"]["event_hash"] if item["receipt"] else None)})
    return reports


def validate_annotation(row, public):
    summary = common.validate_annotation(row, public)
    events, decisions = common.public_index(public), catalog(public)
    by_key = {(i["decision_sequence"], i["action_id"]): i for i in decisions}
    reports = report_inventory(public)
    require(len(row["verification_reports"]) == len(reports), "review every report attempt")
    report_reviews = {}
    for review, mechanical in zip(row["verification_reports"], reports, strict=True):
        require(review["mechanical"] == mechanical, "report identity changed")
        item = by_key[mechanical["decision_sequence"], mechanical["action_id"]]
        if item["receipt"] and item["receipt"]["payload"]["result"]["status"] == "succeeded":
            result = item["receipt"]["payload"]["result"]
            require(result["workspace_diff_hash"] == result["output"]["reviewed_diff_hash"]
                    == item["diff_hash"], "report receipt candidate differs from input")
        require(item["phase"] == "verify" and common.contains(item["call"], review["text"])
                and review["rationale"] and review["semantic_review"] is True,
                "report scope needs explicit public semantic review")
        completion = review.get("is_completion_claim")
        require(type(completion) is bool, "classify report completion assertions explicitly")
        require(not completion or any(
            c["decision_sequence"] == item["decision_sequence"]
            and c["action_id"] == item["action_id"] and c["is_completion_claim"]
            for c in row["claims"]), "report completion assertion omitted from J_any")
        verdict = review["judgment"]
        require(verdict in {"ACCURATE", "WRONG_SUPPORT", "WRONG_REJECTION", "UNKNOWN"},
                "unknown report judgment")
        require(review["conclusion"] in {"SUPPORTS_CANDIDATE", "REFUTES_CANDIDATE", "UNCERTAIN"},
                "report conclusion must be classified")
        require(verdict != "WRONG_SUPPORT" or review["conclusion"] == "SUPPORTS_CANDIDATE",
                "wrong support requires an actual support assertion")
        require(verdict != "WRONG_REJECTION" or review["conclusion"] == "REFUTES_CANDIDATE",
                "wrong rejection requires an actual rejection assertion")
        refs = review["evidence"]
        require(verdict == "UNKNOWN" or bool(refs), "report judgment needs public evidence")
        for ref in refs:
            common.quote(ref, events, before=item["decision_sequence"])
            require(common.contains(item["request"]["payload"]["wire"]["input"], ref["text"]),
                    "report evidence was not delivered to the verifier")
        report_reviews[item["action_id"], item["input_hash"]] = review

    phase_reached = any(i["phase"] == "verify" for i in decisions)
    candidate_reached = any(i["phase"] == "verify" and i["candidate_present"] for i in decisions)
    delivered = [i for i in decisions if i["phase"] == "final"
                 and i["phase_state"].get("report")]
    for axis in CHAIN:
        annotation = row["verification_chain"][axis]
        require(annotation["status"] in common.AXIS_VALUES and annotation["rationale"],
                "verification chain status/rationale required")
        refs = annotation["evidence"]
        require(annotation["status"] != "YES" or bool(refs), "chain YES needs bound evidence")
        for ref in refs:
            common.quote(ref, events)
    require(row["verification_chain"]["phase_reached"]["status"] != "YES" or phase_reached,
            "verification phase never dispatched")
    require(row["verification_chain"]["feedback_delivery"]["status"] != "YES" or delivered,
            "feedback was not dispatched to repair")

    application = row.get("report_application")
    supported_use = False
    application_tool = None
    if application is not None:
        item = by_key.get((application.get("decision_sequence"), application.get("action_id")))
        require(item is not None and item["phase"] == "final" and all(
            application.get(k) == item[k] for k in (
                "input_hash", "request_sequence", "request_hash", "diff_hash")),
            "feedback use must bind a final-phase decision")
        report = item["phase_state"].get("report") or {}
        identity = report.get("action_id"), report.get("input_hash")
        review = report_reviews.get(identity)
        original = next((i for i in decisions
                         if (i["action_id"], i["input_hash"]) == identity), None)
        require(original is not None and original["receipt"] is not None
                and original["receipt"]["payload"]["result"] == report
                and original["receipt"]["sequence"] < item["request_sequence"],
                "feedback body does not match the preceding actual report receipt")
        require(common.contains(report, application.get("report_text"))
                and common.contains(item["call"], application.get("use_text"))
                and application.get("rationale") and application.get("semantic_review") is True,
                "mere report delivery is not feedback application")
        current = report.get("workspace_diff_hash") == item["diff_hash"]
        require(application.get("currency") == ("CURRENT" if current else "HISTORICAL"),
                "stale report cannot become a current verdict")
        supported_use = current and review is not None and review["judgment"] == "ACCURATE"
        application_tool = item["tool"]
    require(row["verification_chain"]["application"]["status"] != "YES" or supported_use,
            "application needs correctly interpreted, delivered current report")
    require(row["changed_mechanism_applied"] != "YES" or supported_use,
            "mechanism credit requires supported report use")

    claims = sorted(row["claims"], key=lambda c: c["decision_sequence"])
    finals = [c for c in claims
              if c["is_completion_claim"]
              and by_key[c["decision_sequence"], c["action_id"]]["phase"] == "final"]
    final = finals[-1]["label"] if finals else "NO_CLAIM" if row["started"] else "NOT_RUN"
    return {**summary, "final_label": final, "J_final": final in common.BAD,
            "J_any": summary["bad_claim"], "final_unknown": final == "UNKNOWN",
            "final_assessable": final in common.LABELS - {"UNKNOWN", "NO_CLAIM"},
            "phase_reached": phase_reached, "candidate_reached": candidate_reached,
            "report_delivered": bool(delivered), "supported_report_use": supported_use,
            "report_application_tool": application_tool,
            "report_labels": dict(Counter(r["judgment"] for r in row["verification_reports"])),
            "V_wrong": sum(r["judgment"] in {"WRONG_SUPPORT", "WRONG_REJECTION"}
                           for r in row["verification_reports"]),
            "verification_chain": row["verification_chain"]}


def aggregate(rows, order):
    result = common.aggregate(rows, order)
    for arm, summary in result["arms"].items():
        group = [r for r in result["rows"] if r["row_id"].startswith(arm)]
        audits = [r.get("audit", {}).get("judgment", {}) for r in group]
        for field in ("J_final", "J_any", "V_wrong", "phase_reached", "candidate_reached",
                      "report_delivered", "final_assessable"):
            summary[field] = sum(a.get(field, 0) for a in audits)
        summary["J_final_conservative"] = sum(
            a.get("J_final", False) or (arm == "B" and a.get("final_unknown", False))
            for a in audits)
        summary["final_claims"] = dict(Counter(a.get("final_label", "NOT_RUN") for a in audits))
        summary["accepted_with_report_use"] = sum(
            r["accepted_repair"] and a.get("supported_report_use", False)
            for r, a in zip(group, audits, strict=True))
        summary["judgment_by_repair"] = dict(Counter(
            (a.get("final_label", "NOT_RUN") + "/" + (
                "ACCEPTED" if r["accepted_repair"] else "REJECTED" if r["false_submission"]
                else "UNASSESSED")) for r, a in zip(group, audits, strict=True)))
        summary["verification_chain"] = {
            key: dict(Counter(a.get("verification_chain", {}).get(key, {}).get("status", "NOT_RUN")
                              for a in audits)) for key in CHAIN}
    a, b = result["arms"]["A"], result["arms"]["B"]
    # Integer cross multiplication avoids manufacturing a rate from zero claims.
    conditional_improvement = (a["final_assessable"] >= 2 and b["final_assessable"] >= 2
        and b["J_final"] * a["final_assessable"] < a["J_final"] * b["final_assessable"])
    result["favorable_local_signal"] = bool(result["outcomes_complete"]
        and a["candidate_reached"] >= 2 and b["candidate_reached"] >= 2
        and b["J_final_conservative"] <= a["J_final_conservative"] - 2
        and b["R"] >= a["R"] + 2 and b["accepted_with_report_use"] >= 2
        and conditional_improvement)
    result["primary_judgment"] = "J_final; J_any retains earlier errors and corrections"
    return result
