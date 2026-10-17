"""Replay frozen public states through each arm's selector and presentation, without a model."""
from __future__ import annotations

import argparse
import ast
import copy
import inspect
import json
from pathlib import Path

from diagnostics.evidence_handoff_replay import Inputs, digest, inventory
from diagnostics.question_priority_replay import RULES, SavedGateway
from diagnostics.repair_mechanisms import ARMS, arm_sources
from patchloop.dev import runner
from patchloop.dev.context import build_observed_source_index
from patchloop.dev.contracts import DevToolResult
from patchloop.dev.conversation import assemble_model_input
from patchloop.dev.evidence_focus import bind_question
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges
from patchloop.dev.state import DevJournal
from patchloop.dev.thin_policy import system_prompt
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_json

AUDIT = Path("C:/pt/analyses/segment-boundary-audit-20261016-v1")
PREVIOUS = Path("C:/pt/analyses/question-call-support-20261017-v4")


def optional_from_runtime(state, prefix, latest, *, omit=False):
    """Execute the actual pure selection expression, not an arm label or a duplicate policy.

    Full runner recovery/count/commit is covered by test_evidence_handoff. This
    saved-state projection intentionally does not load/rewrite encrypted continuations.
    """
    tree = ast.parse(inspect.getsource(runner._build_segmented_model_input))
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == "optional" for t in n.targets)]
    assert len(nodes) == 1
    expression = ast.Expression(nodes[0].value)
    return eval(compile(expression, "<frozen-runtime-optional-selection>", "eval"),
                runner.__dict__, {"state": state, "events": prefix,
                                  "ids": {r.action_id for r in latest}, "replace_pending": omit})


def compose(state, gateway, latest, prefix, *, omit=False):
    projection = gateway.prepare_context_projection(latest)
    candidate = copy.deepcopy(state)
    candidate["source_spans"] = list(projection.source_spans)
    candidate["working_notes"]["open_question"] = copy.deepcopy(gateway._working_open_question)
    candidate["observed_source_index"] = build_observed_source_index(
        projection.delivered_spans, editable_paths=projection.editable_paths)
    candidate["context_projection"].update(
        retained_content_chars=projection.retained_content_chars,
        omitted_observed_line_count=projection.omitted_observed_line_count,
        omitted_pinned_ranges=list(projection.omitted_pinned_ranges),
        omitted_observed_ranges=list(projection.omitted_observed_ranges),
        omitted_observed_range_count=projection.omitted_observed_range_count,
        delivered_source_hash=sha256_json(projection.delivered_spans))
    ids = {r.action_id for r in latest}
    calls = [c for e in prefix if e["event_type"] == "turn_decision_recorded"
             for c in e["payload"].get("tool_calls", []) if c["action_id"] in ids]
    prompt = system_prompt("current", "brief-v1")
    base = runner._segment_public_base(prompt, candidate, latest, calls)
    optional = optional_from_runtime(candidate, prefix, latest, omit=omit)
    if optional:
        base.append(runner.SEGMENT_RULES.archive(exchanges=optional))
    view = runner._segment_current_view(candidate, base[3:], latest)
    model_input = assemble_model_input(system_prompt=prompt, state=view, history=[],
                                       previous_input=base, context_policy="segmented-v1")
    facts, _, _ = RULES.inventory(model_input)
    delivered = {(*key, value) for key, value in facts.items()}
    assert inventory(projection.delivered_spans) <= delivered
    assert projection.retained_content_chars <= 24000
    assert not any(item.get("type") == "reasoning" for item in model_input)
    exchanges = list(public_exchanges(model_input, archive_kind=PUBLIC_EVIDENCE_KIND))
    return projection, view, model_input, delivered, exchanges, optional


def rebind(raw, gateway, results):
    if not isinstance(raw, dict):
        return raw
    wire = {"text": raw["text"], "evidence": [
        {k: r[k] for k in ("kind", "path", "start_line", "end_line", "role", "action_id")
         if k in r} for r in raw["evidence"]]}
    question, error = bind_question(wire, gateway._snapshot_spans, results,
                                    diff_hash=raw.get("declared_diff_hash"))
    assert error is None, error
    return question


def replay(root: Path, arm: str, *, max_boundaries: int | None = None):
    assert not root.exists(), "Use a fresh immutable replay directory"
    expected = arm_sources(repository_root(), arm)
    assert all((repository_root() / p).read_bytes() == s.encode() for p, s in expected.items())
    root.mkdir(parents=True)
    journal = DevJournal(root, "run_dev_repairreplay")
    journal.append("replay_planned", {
        "arm": arm, "runtime_hash": runtime_content_hash(), "script_hash": digest(
            Path(__file__).read_bytes()), "prior": str(PREVIOUS), "audit": str(AUDIT),
        "scope": "same-state public projection; no continuation or token-count replay",
        "provider_calls_allowed": 0, "input_count_calls_allowed": 0,
        "tool_surrogate": "latest two observed check/test/probe results outside latest batch",
        "max_boundaries": max_boundaries,
    })
    reader = Inputs()
    boundaries = reader.read(AUDIT / "boundaries-v2.json")
    paths = {row["row"]: row["journal"] for row in reader.read(AUDIT / "rows-v2.json")}
    previous = reader.read(PREVIOUS / "results.json")
    events, results = {}, []
    for boundary in boundaries[:max_boundaries]:
        row, seq = boundary["row"], boundary["segment_sequence"]
        if row not in events:
            events[row] = reader.events(paths[row])
        prefix = [e for e in events[row] if e["sequence"] < seq]
        state = reader.artifact(boundary["handoff_artifact"])["state"]
        gateway = SavedGateway(state, prefix, root)
        observed = {e["payload"]["result"]["action_id"]: e["payload"]["result"]
                    for e in prefix if e["event_type"] == "action_finished"}
        latest = [DevToolResult.model_validate(observed[r["action_id"]])
                  for r in state["latest_tool_results"]]
        fixed = [r for r in previous if r["row"] == row and r["boundary"] == seq]
        cases = [(r["id"], rebind(r["question"], gateway, observed), r) for r in fixed]
        latest_ids = {r.action_id for r in latest}
        older = [r for r in reversed(list(observed.values())) if r["action_id"] not in latest_ids
                 and r["tool"] in {"run_check", "run_tests", "run_probe"}][:2]
        if older:
            question, error = bind_question({"text": "Which observed result addresses the purpose?",
                "evidence": [{"kind": "tool_result", "action_id": r["action_id"], "role": role}
                             for r, role in zip(older, ("primary", "countercheck"), strict=False)]},
                gateway._snapshot_spans, observed, diff_hash=gateway.current_diff_hash)
            assert error is None
            cases.append((f"row{row:02}-boundary{seq}-tool_surrogate", question, None))
        for name, question, old in cases:
            gateway.set_question(question)
            variants = (False, True) if old is None else (False,)
            for omit in variants:
                projection, view, model_input, delivered, exchanges, optional = compose(
                    state, gateway, latest, prefix, omit=omit)
                identifier = name + ("-omit" if omit else "")
                raw = canonical_json(model_input).encode()
                (root / f"{identifier}.json").write_bytes(raw)
                original = reader.artifact({"path": old["input_artifact"]["path"],
                    "content_hash": old["input_artifact"]["sha256"]}) if old else None
                old_facts = RULES.inventory(original)[0] if original else {}
                old_lines = {(*k, v) for k, v in old_facts.items()}
                if arm == "E1J1" and old:
                    assert raw == canonical_json(original).encode(), identifier
                priorities = gateway._source_projection_priorities()
                protected = {x for x in old_lines if any(
                    x[0] == p and lo <= x[2] <= hi and rank <= 1
                    for p, lo, hi, rank in priorities)}
                assert protected <= delivered
                results.append({"id": identifier, "row": row, "boundary": seq, "arm": arm,
                    "variant": old["variant"] if old else "tool_surrogate",
                    "operator_declared": not old or old["variant"] != "actual_legacy",
                    "input_sha256": digest(raw), "input_bytes": len(raw),
                    "retained_chars": projection.retained_content_chars,
                    "source_lines": [list(x) for x in sorted(delivered)],
                    "source_sha256": sha256_json(sorted(delivered)),
                    "exchange_sha256": sha256_json(exchanges),
                    "optional_ids": sorted({i["call_id"] for i in optional}),
                    "omitted_optional": omit, "protected_lines": len(protected),
                    "gained_from_current": [list(x) for x in sorted(delivered - old_lines)],
                    "lost_from_current": [list(x) for x in sorted(old_lines - delivered)],
                    "question": view["working_notes"].get("open_question"),
                    "notes": view["working_notes"].get("findings", []),
                    "original_reason": boundary["reason"]})
    artifacts = (("results.json", results), ("read-manifest.json", list(reader.files.values())))
    for filename, data in artifacts:
        (root / filename).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    assert all(digest(Path(x["path"]).read_bytes()) == x["sha256"] for x in reader.files.values())
    summary = {"arm": arm, "cases": len(results), "boundaries": len(boundaries[:max_boundaries]),
               "max_retained_chars": max(r["retained_chars"] for r in results),
               "max_input_bytes": max(r["input_bytes"] for r in results),
               "original_files_unchanged": len(reader.files), "provider_calls": 0,
               "input_count_calls": 0, "paid_cost_usd": "0", "repair_quality": "NOT_RUN",
               "exact_token_counts_and_full_request_admission": "NOT_RUN"}
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    journal.append("replay_completed", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--max-boundaries", type=int)
    args = parser.parse_args()
    print(json.dumps(replay(args.output, args.arm, max_boundaries=args.max_boundaries), indent=2))


if __name__ == "__main__":
    main()
