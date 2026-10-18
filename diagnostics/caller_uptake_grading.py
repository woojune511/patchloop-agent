"""Public caller receipts and human evidence-use annotations; never a paid judge.

The task-specific oracle belongs to this frozen diagnostic, not the coding agent.
Receipt validity, public behavior, evidence use and independent repair acceptance
are separate axes. A schema-valid annotation is not a semantic proof.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from diagnostics.positive_verification_panel import require
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes, sha256_json

PROGRAMS = {
    "missing": "sha256:6e8c94f7ba40b28dffdf22442d772678b23ce4a1ea1f87f02bed4625a0ee3278",
    "present": "sha256:8227ee2f9c9092341de61fefea2b310e9e4e638000eba7261e21ab0a78ef5f4b",
}
LABELS = {"YES", "NO_OBSERVED", "UNKNOWN", "NOT_RUN"}
EVIDENCE_STATES = {"NOT_ACQUIRED", "ACQUISITION_FAILED", "PRESENT", "LOST_AT_HANDOFF",
                   "STALE_AFTER_EDIT", "TRUNCATED", "UNCERTAIN"}


def caller_grade(receipt, *, case, dependency_hash, diff_hash, expected_diff, cleanup):
    """Classify only the two frozen programs, preserving uncertain receipts as ERROR."""
    result = {"status": "ERROR", "case": case, "diff_hash": diff_hash,
              "receipt_hash": sha256_json(receipt), "reason": "receipt_or_identity"}
    policy = receipt.get("execution_policy", {})
    setup = receipt.get("setup_checks", {})
    if (case not in PROGRAMS or diff_hash != expected_diff or cleanup is not True
            or receipt.get("source_hash") != PROGRAMS[case]
            or policy.get("dependencies", {}).get("manifest_hash") != dependency_hash
            or receipt.get("status") != "passed" or receipt.get("exit_code") != 0
            or setup.get("status") != "passed" or setup.get("source_hash") != PROGRAMS[case]
            or policy.get("cleanup_status") != "confirmed"
            or any(receipt.get(k) for k in
                   ("timed_out", "truncated", "cleanup_failed", "deadline_exhausted"))):
        return result
    try:
        before, outcome = [json.loads(line) for line in receipt["stdout"].splitlines()]
        initial, present = before["input"], case == "present"
        cwd = initial["cwd"]
        layout = ["src/__init__.py", "src/project/file.py"]
        if present:
            layout.insert(1, "src/project/__init__.py")
        checks = setup["checks"]
        expected_checks = {"caller version": "2.12.2", "current project": True,
            "public caller": True, "cwd": cwd, "relative argument": "src/project",
            "src initializer": True, "project initializer": present, "empty public input": "",
            "console entry": "pylint:run_pylint"}
        check_values = {c["label"]: c["actual"] for c in checks}
        require(len(checks) == len(expected_checks) and check_values == expected_checks
                and all(c["matched"] is True and type(c["actual"]) is type(c["expected"])
                        and c["actual"] == c["expected"] for c in checks), "setup")
        require(before["stage"] == "before_call" and outcome["stage"] == "result"
                and outcome["present"] is present and outcome["overflow"] == 0, "framing")
        require(cwd.startswith("/tmp/public-caller-") and initial["argv"] ==
                ["pylint", "src/project"] and initial["layout"] == layout, "input")
        require(initial["sys_path"][:2] == ["/workspace", "/opt/patchloop-dependencies"]
                and initial["environment"] == {"HOME": cwd + "/home",
                    "PYLINTHOME": cwd + "/cache", "PYTHONPATH": None}, "environment")
        require(outcome["entry_point"] == "pylint:run_pylint"
                and outcome["origins"] == {
                    "pylint": "/opt/patchloop-dependencies/pylint/__init__.py",
                    "astroid": "/workspace/astroid/__init__.py"}
                and outcome["python"].startswith("3.9.25 "), "origins")
        require(outcome["configuration"]["jobs"] == 1
                and outcome["configuration"]["rcfile"] is None, "configuration")
        calls = outcome["calls"]
        require(isinstance(calls, list) and len(calls) <= 24, "calls")
        def observed(function, file, arguments):
            return any(c["function"] == function and c["file"] == file and c["cwd"] == cwd
                       and all(c["arguments"].get(k) == v for k, v in arguments.items())
                       for c in calls)
        require(observed("run_pylint", "/opt/patchloop-dependencies/pylint/__init__.py", {})
                and observed("__init__", "/opt/patchloop-dependencies/pylint/lint/run.py",
                             {"args": ["src/project"]}), "entry not observed")
        target = observed("get_ast", "/opt/patchloop-dependencies/pylint/lint/pylinter.py",
                          {"filepath": "src/project/file.py"})
        exit_code = outcome["pylint_exit_code"]
        require(type(exit_code) is int and 0 <= exit_code <= 63, "invalid caller exit")
        text = outcome["pylint_stdout"] + outcome["pylint_stderr"]
        require(isinstance(text, str), "invalid output")
    except (KeyError, ValueError, TypeError, ContractError, AttributeError):
        return {**result, "reason": "incomplete_or_inapplicable_observation"}
    passed = exit_code == 0 and "F0010" not in text and target
    return {**result, "status": "PASS" if passed else "FAIL",
            "reason": "completed_public_behavior", "caller_exit": exit_code,
            "child_analyzed": target, "f0010": "F0010" in text}


def span_text(ref, allowed):
    """Resolve exact public evidence bytes; no paths outside the sealed export."""
    require(ref["path"] in allowed and allowed[ref["path"]] == ref["hash"], "unbound evidence")
    raw = Path(ref["path"]).read_bytes()
    require(sha256_bytes(raw) == ref["hash"], "evidence changed")
    start, end = ref["start"], ref["end"]
    require(type(start) is int and type(end) is int and 0 <= start < end <= len(raw),
            "invalid byte span")
    return raw[start:end]


def validate_annotation(row, allowed):
    """Validate audit lineage, not whether the human's interpretation is correct."""
    require(row["U_source"] in LABELS and row["U_exec"] in LABELS, "unknown uptake label")
    require(row["reviewer"] and row["rationale"] and row["alternatives"], "human review required")
    for axis in ("availability", "disclosure", "inspection", "relevant_execution",
                 "base_failure", "normal_control", "candidate_test", "delivery", "interpretation"):
        require(row[axis] in LABELS, "missing independent audit axis")
    for component in ("source", "exec"):
        evidence = row.get(component + "_evidence", [])
        if row["U_" + component] == "YES":
            require(bool(evidence), "uptake needs linked evidence and decision")
        for item in evidence:
            material = span_text(item["material"], allowed)
            request = span_text(item["request"], allowed)
            span_text(item["decision"], allowed)
            require(material in request and item["scope_rationale"], "delivery or scope unbound")
            require(item["material_sequence"] < item["request_sequence"]
                    < item["decision_sequence"], "decision must follow delivery")
            if component == "exec":
                require(all(item.get(k) for k in ("action_id", "input_hash", "diff_hash",
                    "program_hash", "entry_setup_rationale")), "execution lineage missing")
            if item.get("counterexample"):
                require(item["decision_opportunity"] is True
                        and item["diff_hash"] == item["decision_diff_hash"],
                        "stale failure or no decision opportunity")
    for item in row["evidence_inventory"]:
        require(item["state"] in EVIDENCE_STATES and item["rationale"], "evidence state missing")
        if item["state"] == "LOST_AT_HANDOFF":
            material = span_text(item["material"], allowed)
            require(material in span_text(item["earlier_full_request"], allowed)
                    and material not in span_text(item["later_full_request"], allowed)
                    and item["all_routes_reviewed"] is True, "loss not established")
    labels = (row["U_source"], row["U_exec"])
    return "YES" if "YES" in labels else "UNKNOWN" if "UNKNOWN" in labels else (
        "NOT_RUN" if labels == ("NOT_RUN", "NOT_RUN") else "NO_OBSERVED")


def aggregate(rows, order):
    """Intended-row denominators; outcomes never select which uptake rows to count."""
    require(len(order) == 12 and len(set(order)) == 12, "twelve assigned rows required")
    require(len({r["row_id"] for r in rows}) == len(rows)
            and all(r["row_id"] in order for r in rows), "invalid row roster")
    by_id = {r["row_id"]: r for r in rows}
    records = []
    for label in order:
        r = by_id.get(label, {})
        s = r.get("submitted") is True and r.get("registered") == r.get("native") == "PASS"
        t = r.get("submitted") is True and r.get("missing") == r.get("present") == "PASS"
        if s or t:
            require(r.get("submitted_diff") and r["submitted_diff"] == r.get("assessed_from_diff")
                    and r.get("source_only_diff") and r["source_only_diff"] == r.get("caller_diff")
                    == r.get("native_diff"), "assessment diff lineage mismatch")
        records.append({"row_id": label, "arm": label[0], "S": bool(s), "T": bool(t),
                        "Q": bool(s and t), "U": r.get("U", "NOT_RUN"), "raw": r})
    arms = {arm: {"intended": 6, **{k: sum(r[k] for r in records if r["arm"] == arm)
                                   for k in ("S", "T", "Q")},
                  "uptake": dict(Counter(r["U"] for r in records if r["arm"] == arm))}
            for arm in "AB"}
    complete = all(r["raw"].get("completed") and r["raw"].get("settled")
                   and r["raw"].get("cleanup") and (
                       not r["raw"].get("submitted") or (
                           r["raw"].get("registered") == r["raw"].get("native")
                           and r["raw"].get("native") in {"PASS", "FAIL"}
                           and all(r["raw"].get(k) in {"PASS", "FAIL"}
                                   for k in ("missing", "present"))
                           and r["raw"].get("safety") == "PASS")) for r in records)
    signal = (complete and arms["B"]["Q"] > arms["A"]["Q"]
              and sum(r["arm"] == "B" and r["Q"] and r["U"] == "YES" for r in records) >= 2
              and all(r["raw"].get("present") != "FAIL" for r in records))
    return {"rows": records, "arms": arms, "Q_B_minus_A": arms["B"]["Q"] - arms["A"]["Q"],
            "S_B_minus_A": arms["B"]["S"] - arms["A"]["S"], "complete": complete,
            "favorable_local_signal": signal, "automatic_followup": False,
            "official": False, "claim_eligible": False}
