"""Public linkage audit. Mechanical provenance never certifies requirement coverage."""

from __future__ import annotations

import ast
import json
from collections import Counter

from diagnostics import probe_invocation_control as control
from diagnostics import probe_purpose_grading as purpose
from diagnostics import verification_role_grading as role
from diagnostics import verification_state_grading as common
from diagnostics.positive_verification_panel import require
from patchloop.dev import probe_invocation, reproduction
from patchloop.dev.conversation import reconstruct_state
from patchloop.util import canonical_json, sha256_json

public_index = common.public_index
KEYS = (
    "decision_sequence",
    "action_id",
    "input_hash",
    "request_sequence",
    "request_hash",
    "diff_hash",
)
SCOPE = ("caller", "arguments", "inputs", "environment", "countercondition", "expectation")
BREAKS = {
    "no_exposure",
    "not_selected_with_opportunity",
    "attempt_blocked",
    "wrong_mapping_or_conditions",
    "no_baseline",
    "delivery_loss",
    "misinterpreted",
    "applied_repair_failed",
    "unknown",
}


def has_invocation(source):
    try:
        tree = ast.parse(source or "")
    except (ValueError, SyntaxError):
        return False
    return any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "call_target"
        for n in ast.walk(tree)
    )


def opportunities(public):
    rows = []
    for event in public["events"]:
        if event["event_type"] != "provider_call_started":
            continue
        wire = event["payload"]["wire"]
        state = reconstruct_state(wire["input"], context_policy="segmented-v1")
        tool = next((t for t in wire.get("tools", []) if t["name"] == "run_probe"), None)
        description = tool.get("description", "") if tool else ""
        guidance = (
            "B"
            if reproduction.DESCRIPTION in description
            else "A"
            if control.DESCRIPTION in description
            else "UNRECOGNIZED"
            if tool
            else None
        )
        rows.append(
            {
                "request_sequence": event["sequence"],
                "request_hash": event["payload"]["actual_request_hash"],
                "offered": tool is not None,
                "guidance": guidance,
                "description_hash": sha256_json(description),
                "tool_description": description,
                "phase": state.get("verification_phase"),
                "remaining_budget": state.get("remaining_budget"),
                "action_horizon": state.get("action_horizon"),
                "environment": state.get("probe_environment"),
                "diff_hash": state["current_diff"]["patch_hash"],
            }
        )
    return rows


def inventory(public):
    catalog = {(i["decision_sequence"], i["action_id"]): i for i in common.decisions(public)}
    rows = []
    for row in purpose.inventory(public):
        item = catalog[row["decision_sequence"], row["action_id"]]
        receipt = item["receipt"]
        output = receipt["payload"]["result"].get("output", {}) if receipt else {}
        repro = output.get("reproduction") or {}
        binding, trace = repro.get("binding", {}), repro.get("call_observation", {})
        definition = binding.get("definition", {})
        calls = trace.get("calls", [])
        bound = bool(
            receipt
            and common.current_execution(receipt, item["diff_hash"])
            and trace.get("binding_method") == probe_invocation.CHANNEL
            and isinstance(trace.get("execution_environment"), dict)
            and all(
                trace["execution_environment"].get(k) is not None
                for k in (
                    "image_digest",
                    "profile_hash",
                    "dependencies",
                    "thread_environment",
                    "entrypoint",
                )
            )
            and calls
            and trace.get("incomplete") is False
            and all(probe_invocation.valid_call(c, definition.get("entrypoint")) for c in calls)
            and repro.get("comparison") in {"matched", "mismatched"}
        )
        source = item["call"]["arguments"].get("python_source")
        rows.append(
            {
                **row,
                "phase": reconstruct_state(
                    item["request"]["payload"]["wire"]["input"], context_policy="segmented-v1"
                )
                .get("verification_phase", {})
                .get("phase"),
                "invocation_expression": has_invocation(source),
                "bound": bound,
                "definition": definition,
                "program_hash": binding.get("program_hash") or output.get("source_hash"),
                "actual_calls": calls,
                "execution_environment": trace.get("execution_environment"),
                "host_environment": probe_invocation.environment(output),
                "conditions_hash": sha256_json(probe_invocation.conditions(trace))
                if bound
                else None,
                "observed_json": repro.get("observed_json"),
                "flags": {
                    k: output.get(k)
                    for k in (
                        "exit_code",
                        "timed_out",
                        "truncated",
                        "deadline_exhausted",
                        "cleanup_failed",
                        "setup_checks",
                    )
                },
            }
        )
    return rows


def delivery(probe, item):
    """Receipt identity plus body/scope, not a caller-name substring hit."""
    receipt = probe["receipt"]
    if receipt is None or receipt["sequence"] >= item["request_sequence"]:
        return "NOT_AVAILABLE"
    result = receipt["payload"]["result"]
    wire = item["request"]["payload"]["wire"]
    state = reconstruct_state(wire["input"], context_policy="segmented-v1")
    status = "OMITTED"

    def body(node):
        if isinstance(node, str):
            try:
                parsed = json.loads(node)
            except ValueError:
                return False
            return body(parsed) if isinstance(parsed, (dict, list)) else False
        if isinstance(node, list):
            return any(body(v) for v in node)
        if isinstance(node, dict):
            keys = ("action_id", "input_hash", "workspace_diff_hash", "status", "output")
            if all(
                k in node and canonical_json(node[k]) == canonical_json(result.get(k)) for k in keys
            ):
                return True
            return any(body(v) for v in node.values())
        return False

    if body(wire["input"]):
        status = "BODY"
    else:
        repro = result.get("output", {}).get("reproduction") or {}
        for case in state.get("reproduction_review", {}).get("items", []):
            if case["case_id"] != repro.get("binding", {}).get("case_id"):
                continue
            for name in ("baseline", "latest"):
                view = case.get(name) or {}
                if view.get("action_id") == result["action_id"]:
                    # Summary only: do not claim that observed JSON or full setup survived.
                    status = "SUMMARY"
    return (
        "STALE_" + status
        if status != "OMITTED" and (result["workspace_diff_hash"] != item["diff_hash"])
        else status
    )


def _semantic(value, events, *, before=None):
    require(
        value.get("semantic_review") is True and value.get("rationale"),
        "explicit public semantic review required",
    )
    refs = value.get("evidence", [])
    require(refs, "semantic review requires public evidence")
    for ref in refs:
        common.quote(ref, events, before=before)


def delivery_inventory(public):
    """Track availability at every later request, including unused/restored receipts."""
    probes = [i for i in common.decisions(public) if i["tool"] == "run_probe" and i["receipt"]]
    result = []
    for probe in probes:
        previously_missing = False
        for event in public["events"]:
            if event["event_type"] != "provider_call_started":
                continue
            state = reconstruct_state(
                event["payload"]["wire"]["input"], context_policy="segmented-v1"
            )
            item = {
                "request": event,
                "request_sequence": event["sequence"],
                "diff_hash": state["current_diff"]["patch_hash"],
            }
            scope = delivery(probe, item)
            if scope == "NOT_AVAILABLE":
                continue
            result.append(
                {
                    "probe": [probe["decision_sequence"], probe["action_id"]],
                    "request_sequence": event["sequence"],
                    "delivery": scope,
                    "restored": previously_missing and scope != "OMITTED",
                }
            )
            previously_missing = scope == "OMITTED"
    return result


def validate_annotation(row, public):
    summary = role.validate_annotation(row, public)
    events, catalog = public_index(public), common.decisions(public)
    by_key = {(i["decision_sequence"], i["action_id"]): i for i in catalog}
    link = row["invocation"]
    actual_opportunities, probes = opportunities(public), inventory(public)
    require(
        link["opportunities"] == actual_opportunities, "dispatched opportunity inventory differs"
    )
    require(link["arm"] in {"A", "B"}, "invocation assignment required")
    require(
        all(o["guidance"] == link["arm"] for o in actual_opportunities if o["offered"]),
        "guidance does not match assignment",
    )
    feasibility = link["feasibility"]
    require(len(feasibility) == len(actual_opportunities), "review every opportunity")
    for review, opportunity in zip(feasibility, actual_opportunities, strict=True):
        require(
            review["request_sequence"] == opportunity["request_sequence"]
            and review["status"] in {"FEASIBLE", "UNAVAILABLE", "UNKNOWN"}
            and review["rationale"],
            "opportunity feasibility needs reasons",
        )
        require(review["status"] != "FEASIBLE" or opportunity["offered"], "tool not offered")
        if review["status"] == "FEASIBLE":
            require(
                all(review.get(k) for k in ("environment", "time", "actions", "cost", "source")),
                "feasible opportunity needs all resource dimensions",
            )
            _semantic(review, events, before=opportunity["request_sequence"] + 1)
    require(len(link["probes"]) == len(probes), "review every probe including rejections")
    scopes, items = {}, {}
    for review, mechanical in zip(link["probes"], probes, strict=True):
        require(review["mechanical"] == mechanical, "probe identity or actual observation differs")
        key = mechanical["decision_sequence"], mechanical["action_id"]
        item = by_key[key]
        items[key] = item
        status = review["original_scope"]
        require(status in common.AXIS_VALUES and review["rationale"], "explicit original scope")
        if status == "YES":
            require(
                item["receipt"] is not None
                and common.current_execution(item["receipt"], item["diff_hash"]),
                "faithful scope requires actual healthy execution",
            )
            _semantic(review, events)
            require(
                any(ref["sequence"] == item["receipt"]["sequence"] for ref in review["evidence"]),
                "scope must cite this execution",
            )
            require(
                all(review.get("mapping", {}).get(k) for k in SCOPE),
                "original scope requires caller, inputs, environment, control and expectation",
            )
            # Legacy name tracing can miss a valid alias/constructor. B-only fields are
            # deliberately not a prerequisite for this common semantic standard.
        scopes[key] = status

    pairs = []
    seen = set()
    for pair in link["pairs"]:
        left, right = tuple(pair["before"]), tuple(pair["after"])
        require(
            left in items and right in items and (left, right) not in seen,
            "pair requires two unique actual probes",
        )
        seen.add((left, right))
        first, last = items[left], items[right]
        a, b = (
            next(p for p in probes if (p["decision_sequence"], p["action_id"]) == key)
            for key in (left, right)
        )
        require(
            pair["status"] in {"IMPROVED", "STILL_FAIL", "CONFLICT", "INCOMPARABLE", "UNKNOWN"},
            "unknown before/after status",
        )
        _semantic(pair, events)
        if pair["status"] in {"IMPROVED", "STILL_FAIL"}:
            require(
                scopes[left] == scopes[right] == "YES"
                and first["receipt"]["sequence"] < last["request_sequence"]
                and first["diff_hash"] != last["diff_hash"]
                and a["program_hash"] is not None
                and a["program_hash"] == b["program_hash"]
                and a["definition"] == b["definition"],
                "pair program/purpose/diff differs",
            )
            if link["arm"] == "B":
                require(
                    a["bound"] and b["bound"] and a["conditions_hash"] == b["conditions_hash"],
                    "changed or incomplete call conditions",
                )
                require(
                    a["comparison"] == "mismatched"
                    and b["comparison"]
                    == ("matched" if pair["status"] == "IMPROVED" else "mismatched"),
                    "pair needs a measured failing baseline and actual later outcome",
                )
                if pair["status"] == "IMPROVED":
                    require(
                        not any(
                            p["bound"]
                            and p["diff_hash"] == b["diff_hash"]
                            and p["program_hash"] == b["program_hash"]
                            and p["definition"] == b["definition"]
                            and p["conditions_hash"] == b["conditions_hash"]
                            and p["comparison"] == "mismatched"
                            for p in probes
                        ),
                        "conflicting current observations cannot establish improvement",
                    )
            else:
                # Same semantic bar without granting missing legacy metadata a free pass.
                require(
                    a["host_environment"] == b["host_environment"],
                    "legacy execution environment changed",
                )
                if a["actual_calls"] and b["actual_calls"]:
                    require(
                        sha256_json(
                            reproduction.call_identity(
                                {"calls": a["actual_calls"], "incomplete": False}
                            )
                        )
                        == sha256_json(
                            reproduction.call_identity(
                                {"calls": b["actual_calls"], "incomplete": False}
                            )
                        ),
                        "legacy observed call conditions changed",
                    )
                require(
                    all(
                        pair.get(k)
                        for k in (
                            "explicit_expectation",
                            "failed_baseline",
                            "later_observation",
                            "same_arguments",
                            "same_inputs",
                            "same_environment",
                        )
                    ),
                    "legacy pair needs explicit public program/setup/outcome provenance",
                )
            require(
                {first["receipt"]["sequence"], last["receipt"]["sequence"]}
                <= {r["sequence"] for r in pair["evidence"]},
                "pair must cite both executions",
            )
            require(
                any(
                    i["tool"] in {"replace_text", "create_file", "delete_file"}
                    and first["receipt"]["sequence"]
                    < i["decision_sequence"]
                    < last["request_sequence"]
                    and i["receipt"] is not None
                    and i["receipt"]["payload"]["result"]["status"] == "succeeded"
                    for i in catalog
                ),
                "pair has no intervening accepted edit",
            )
        pairs.append(pair["status"])

    applications, delivered = [], []
    for use in link["applications"]:
        key = tuple(use["probe"])
        item = by_key.get((use.get("decision_sequence"), use.get("action_id")))
        require(
            key in items and item is not None and all(use.get(k) == item[k] for k in KEYS),
            "application decision/probe identity differs",
        )
        state = delivery(items[key], item)
        require(use["delivery"] == state, "delivery scope/currency differs")
        require(
            use["judgment"] in {"SUPPORTED", "SUPPORTED_LIMITATION", "MISINTERPRETED", "UNKNOWN"},
            "application judgment required",
        )
        _semantic(use, events, before=item["decision_sequence"])
        require(common.contains(item["call"], use["use_text"]), "use is not an actual decision")
        require(
            state not in {"OMITTED", "NOT_AVAILABLE"}
            and common.contains(item["request"]["payload"]["wire"]["input"], use["exposure_text"]),
            "use requires receipt/scope actually delivered before decision",
        )
        if use["judgment"] == "SUPPORTED":
            require(
                scopes[key] == "YES" and use.get("scope_rationale"),
                "name/hash repetition or wrong mapping is not supported use",
            )
            require(
                not state.startswith("STALE_") or use.get("historical_only") is True,
                "stale receipt cannot prove current task success",
            )
        elif use["judgment"] == "SUPPORTED_LIMITATION":
            require(
                use.get("scope_rationale") and use.get("not_task_success_evidence") is True,
                "limitation use needs explicit scope and cannot certify task success",
            )
            require(
                any(
                    ref["sequence"] == items[key]["receipt"]["sequence"] for ref in use["evidence"]
                ),
                "limitation use must cite the actual receipt",
            )
        applications.append((key, use["judgment"]))
        delivered.append(state)
    for finding in link["breaks"]:
        require(finding["kind"] in BREAKS, "unknown causal boundary")
        _semantic(finding, events)
    require(
        [b["sequence"] for b in link["breaks"]] == sorted(b["sequence"] for b in link["breaks"]),
        "earliest and later breaks must remain ordered",
    )
    bound_keys = {(p["decision_sequence"], p["action_id"]) for p in probes if p["bound"]}
    faithful_use = any(
        k in bound_keys and scopes[k] == "YES" and v == "SUPPORTED" for k, v in applications
    )
    trace = delivery_inventory(public)
    started = summary["started"]
    return {
        **summary,
        "invocation": {
            "E": "YES"
            if any(f["status"] == "FEASIBLE" for f in feasibility)
            else "UNKNOWN"
            if started
            else "NOT_RUN",
            "U_attempt": "YES"
            if any(
                p["invocation_expression"]
                or p["bound"]
                or (
                    p["selected_kind"] in {"original_requirement", "legacy_original", "replay"}
                    or scopes[p["decision_sequence"], p["action_id"]] == "YES"
                )
                for p in probes
            )
            else "NO_OBSERVED"
            if started
            else "NOT_RUN",
            "U_bound": "NOT_APPLICABLE"
            if link["arm"] == "A"
            else "YES"
            if bound_keys
            else "NO_OBSERVED"
            if started
            else "NOT_RUN",
            "V_original": "YES"
            if "YES" in scopes.values()
            else "UNKNOWN"
            if "UNKNOWN" in scopes.values()
            else "NO_OBSERVED"
            if started
            else "NOT_RUN",
            "P_pair": "YES"
            if set(pairs) & {"IMPROVED", "STILL_FAIL"}
            else "UNKNOWN"
            if "UNKNOWN" in pairs
            else "NO_OBSERVED"
            if started
            else "NOT_RUN",
            "D": dict(Counter(v["delivery"] for v in trace)),
            "delivery_inventory": trace,
            "application_delivery": dict(Counter(delivered)),
            "pairs": dict(Counter(pairs)),
            "U_applied": "YES"
            if any(v in {"SUPPORTED", "SUPPORTED_LIMITATION"} for _, v in applications)
            else "UNKNOWN"
            if any(v == "UNKNOWN" for _, v in applications)
            else "NO_OBSERVED"
            if started
            else "NOT_RUN",
            "faithful_linkage_use": faithful_use,
            "supported_limitation_use": any(v == "SUPPORTED_LIMITATION" for _, v in applications),
            "breaks": link["breaks"],
            "probe_attempts": len(probes),
            "opportunities": len(feasibility),
        },
    }


def aggregate(rows, order):
    result = role.aggregate(rows, order)
    for arm, summary in result["arms"].items():
        group = [r for r in result["rows"] if r["row_id"].startswith(arm)]
        audits = [r.get("audit", {}).get("judgment", {}) for r in group]
        links = [a.get("invocation", {}) for a in audits]
        summary["invocation"] = {
            k: dict(Counter(v.get(k, "NOT_RUN") for v in links))
            for k in ("E", "U_attempt", "U_bound", "V_original", "P_pair", "U_applied")
        }
        summary["faithful_linkage_use"] = sum(v.get("faithful_linkage_use", False) for v in links)
        summary["supported_limitation_use"] = sum(
            v.get("supported_limitation_use", False) for v in links
        )
        summary["accepted_with_linkage_use"] = sum(
            r["accepted_repair"] and v.get("faithful_linkage_use", False)
            for r, v in zip(group, links, strict=True)
        )
        summary["application_judgment_repair"] = dict(
            Counter(
                v.get("U_applied", "NOT_RUN")
                + "/"
                + a.get("final_label", "NOT_RUN")
                + "/"
                + (
                    "ACCEPTED"
                    if r["accepted_repair"]
                    else "REJECTED"
                    if r["false_submission"]
                    else "UNASSESSED"
                )
                for r, a, v in zip(group, audits, links, strict=True)
            )
        )
        for component in ("missing", "present"):
            summary[component] = dict(Counter(r.get(component, "NOT_RUN") for r in group))
    a, b = (result["arms"][k] for k in "AB")
    result["mechanism_signal"] = b["faithful_linkage_use"] >= 2
    result["favorable_local_signal"] = bool(
        result["outcomes_complete"]
        and a["final_assessable"] >= 2
        and b["final_assessable"] >= 2
        and b["J_final_conservative"] <= a["J_final_conservative"] - 2
        and b["J_final_conservative"] * a["final_assessable"]
        < a["J_final_conservative"] * b["final_assessable"]
        and b["R"] >= a["R"] + 2
        and b["accepted_with_linkage_use"] >= 2
    )
    return result
