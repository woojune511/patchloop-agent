"""Audit saved public inspections against the exact input, without executing tools."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from diagnostics import model_state_review as review
from diagnostics import model_state_sampler as design
from patchloop.artifacts import ArtifactStore
from patchloop.dev.native_sources import _lines
from patchloop.dev.state import DevJournal
from patchloop.util import sha256_json


def delivered_lines(payload: dict) -> dict:
    """Only materialized source actually present in this request; no filesystem reads."""
    observed = {}
    for group in payload["source_bodies"]:
        for span in group["spans"]:
            lines = _lines({**group, **span})
            design.shared.require(lines is not None, "incomplete delivered source")
            for number, line in enumerate(lines, span["start_line"]):
                key = (group["path"], group["file_hash"], number)
                design.shared.require(key not in observed or observed[key] == line,
                                      "conflicting delivered source")
                observed[key] = line
    return observed


def inspect_result(payload: dict, result: dict) -> dict:
    """Coverage is a byte/range observation, never a semantic necessity verdict."""
    before = delivered_lines(payload)
    returned = {}
    ranges = []
    for span in result["output"].get("spans", []):
        lines = _lines(span)
        design.shared.require(lines is not None, "incomplete saved inspection")
        ranges.append({key: span[key] for key in ("path", "file_hash", "start_line", "end_line")})
        for number, line in enumerate(lines, span["start_line"]):
            key = (span["path"], span["file_hash"], number)
            design.shared.require(key not in returned or returned[key] == line,
                                  "conflicting inspection source")
            design.shared.require(key not in before or before[key] == line,
                                  "same source identity has different bytes")
            returned[key] = line
    covered = sum(key in before for key in returned)
    new = len(returned) - covered
    outcome = (
        "new_coverage" if new else "covered_only" if returned else
        "zero_match" if result["tool"] == "search_files" else "no_source_returned"
    )
    return {
        "result_status": result["status"],
        "outcome": outcome,
        "returned_unique_lines": len(returned),
        "already_delivered_lines": covered,
        "new_to_request_lines": new,
        "ranges": ranges,
        "ranges_hash": sha256_json(ranges),
        "original_gateway_gain": result["output"].get("evidence_gain"),
        "semantic_necessity": "NOT_INFERRED_FROM_COVERAGE",
    }


def audit(plan, collection_root: Path, assessment_root: Path) -> dict:
    source, receipt, samples, _ = review.collection(plan, collection_root)
    report = review.report(plan, collection_root, assessment_root)
    assessed = design.readonly_store(assessment_root)
    public_by_id = {s["anonymous_sample_id"]: review.read_json(source, s["public_artifact"])
                    for s in samples}
    rows = []
    batches = 0
    for row in report["rows"]:
        if not row.get("inspection_results"):
            continue
        batches += 1
        cell = next(c for c in plan.cells if (c.case_id, c.arm, c.sample_number) ==
                    (row["case_id"], row["condition"], row["repetition"]))
        payload = json.loads(json.loads(cell.request_json)["input"][1]["content"])
        calls = public_by_id[row["anonymous_sample_id"]]["tool_calls"]
        for index, (call, ref) in enumerate(zip(calls, row["inspection_results"], strict=True)):
            result = review.read_json(assessed, ref)
            design.shared.require(call["name"] == result["tool"], "inspection order mismatch")
            arguments = dict(call["arguments"])
            decision = arguments.pop("turn_decision", {})
            rows.append({
                "sample_id": row["anonymous_sample_id"], "case_id": row["case_id"],
                "condition": row["condition"], "repetition": row["repetition"],
                "batch_index": index, "tool": call["name"], "arguments": arguments,
                "public_basis": decision.get("basis"),
                "evidence_goal": decision.get("evidence_goal"),
                "request_hash": cell.request_hash, "saved_result_artifact": ref,
                **inspect_result(payload, result),
            })
    return {
        **review.BOUNDARIES,
        "kind": "model-state-inspection-audit-v1",
        "status": "READ_ONLY_EVIDENCE_AUDIT",
        "packet_hash": plan.packet_hash, "collection_result_hash": sha256_json(receipt),
        "assessment_result_hash": sha256_json(json.loads((assessment_root / "result.json")
                                                       .read_bytes())),
        "new_tool_executions": 0, "new_provider_calls": 0,
        "inspection_batches": batches, "inspection_actions": len(rows),
        "outcome_counts": dict(Counter(r["outcome"] for r in rows)),
        "by_case": {case: dict(Counter(r["outcome"] for r in rows if r["case_id"] == case))
                    for case in design.CASE_TURNS},
        "rows": rows,
        "limits": [
            "Counts compare each response with its frozen request, not later batch discoveries.",
            "A new source range need not be useful; a repeated range need not be pointless.",
            "Error messages may already convey behavior without conveying full source lines.",
            "No saved inspection outcome was delivered to the original one-response sample.",
        ],
    }


def save_audit(plan, collection_root: Path, assessment_root: Path, root: Path) -> dict:
    result = audit(plan, collection_root, assessment_root)
    root = design.fresh_root(root, plan.source_root, plan.packet_path.parent,
                             collection_root, assessment_root)
    store = ArtifactStore(root)
    ref = store.put_json(result)
    (root / "result.json").write_bytes(store.read_bytes(ref))
    journal = DevJournal(root, "run_dev_inspection_audit")
    journal.append("terminal", {"result_artifact": ref.model_dump(mode="json"),
                                "result_hash": ref.content_hash})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("packet", "source-root", "collection-root", "assessment-root", "output-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--packet-hash", required=True)
    args = parser.parse_args(argv)
    plan = design.load_plan(args.packet, args.source_root, args.packet_hash)
    result = save_audit(plan, args.collection_root, args.assessment_root, args.output_root)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
