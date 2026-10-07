"""Operator-only classifiers for the frozen four-task current/thin comparison."""

from __future__ import annotations

import ast
import json

from diagnostics import probe_recheck_public, source_retention_comparison


def classify_public(case: str, result: dict, spec: dict) -> dict:
    """Keep execution uncertainty separate from the scoped public behavior verdict."""
    if (
        result.get("exit_code") != 0
        or any(result.get(key) for key in (
            "timed_out", "cleanup_failed", "truncated", "deadline_exhausted",
        ))
        or result.get("execution_policy", {}).get("cleanup_status") != "confirmed"
    ):
        return {"status": "UNASSESSED", "reason": "execution_uncertainty"}
    setup = result.get("setup_checks", {}).get("status")
    if setup in {"failed", "error"} or (case in {"1733", "2419"} and setup != "passed"):
        return {"status": "UNASSESSED", "reason": "setup_incomplete"}
    if spec.get("case") != case:
        return {"status": "UNASSESSED", "reason": "case_mismatch"}
    if case == "1072":
        return source_retention_comparison.classify(result, spec)
    if case == "1694":
        return probe_recheck_public.classify(result, spec)
    try:
        if case == "1733":
            rows = [ast.literal_eval(line) for line in result["stdout"].splitlines()]
            if (
                len(rows) != 3 or not all(type(row) is dict for row in rows)
                or rows[0] != {"stage": "before_fix", "cte_sql": spec["cte_input"],
                               "top_sql": spec["top_input"]}
                or rows[1]["stage"] != "after_fix"
            ):
                raise ValueError("invalid input observation")
            matched = rows[1]["cte_fixed"].splitlines() == spec["expected_lines"]
            preserved = rows[1]["top_fixed"].splitlines() == spec["ordinary_expected_lines"]
            return {"status": "PASS" if matched and preserved else "FAIL",
                    "issue_output_matches": matched, "ordinary_preserved": preserved,
                    "observed": rows, "scope": "public WITH output and plain SELECT only"}
        if case != "2419":
            raise ValueError("unsupported case")
        rows = json.loads(result["stdout"])
        if not isinstance(rows, list) or len(rows) != 3:
            raise ValueError("invalid observation")
        matches = []
        for row, name in zip(rows, ("IFNULL", "NVL", "COALESCE"), strict=True):
            if (
                not isinstance(row, dict) or row["name"] != name
                or row["sql"] != "SELECT " + name + "(a, b) FROM t;"
                or not isinstance(row["violations"], list)
                or any(not isinstance(item, dict) or not isinstance(item["code"], str)
                       or not isinstance(item["description"], str) for item in row["violations"])
            ):
                raise ValueError("invalid observation")
            expected = ([] if name == "COALESCE" else
                        [{"code": "L060", "description": spec["expected_messages"][name]}])
            matches.append(row["violations"] == expected)
        return {"status": "PASS" if all(matches) else "FAIL", "case_matches": matches,
                "observed": rows, "scope": "public IFNULL/NVL text and COALESCE control only"}
    except (ValueError, KeyError, TypeError, SyntaxError, AttributeError):
        return {"status": "UNASSESSED", "reason": "invalid_observation"}
