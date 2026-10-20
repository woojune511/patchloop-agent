"""Frozen provider-free displacement comparison against the previous paired selector."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from diagnostics.evidence_handoff_replay import Inputs, digest, inventory, surrogate
from diagnostics.question_priority_replay import RULES, SavedGateway, compose, write_case
from patchloop.dev.contracts import DevToolResult
from patchloop.dev.evidence_focus import bind_question
from patchloop.dev.question_support import question_support
from patchloop.dev.state import DevJournal
from patchloop.runtime import runtime_content_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.output
    journal = DevJournal(root, "run_dev_callsupport")
    planned = journal.events()[0]
    assert planned["event_type"] == "analysis_planned"
    assert not (root / "results.json").exists(), "Use a fresh planned evidence directory"
    protocol = planned["payload"]
    reader = Inputs()
    audit = Path(protocol["saved_boundaries"])
    prior = Path(protocol["baseline_inputs"])
    journal.append("replay_started", {"runtime_hash": runtime_content_hash(),
                                      "script_hash": digest(Path(__file__).read_bytes())})
    boundaries = reader.read(audit / "boundaries-v2.json")
    # Outcome columns and future events never select a source line or a declaration.
    journals = {r["row"]: r["journal"] for r in reader.read(audit / "rows-v2.json")}
    baseline = {r["id"]: r for r in reader.read(prior / "results.json")}
    results, cache, linebook = [], {}, ["# Source displacement against the paired selector", ""]
    for boundary in boundaries:
        row, seq = boundary["row"], boundary["segment_sequence"]
        if row not in cache:
            cache[row] = reader.events(journals[row])
        prefix = [e for e in cache[row] if e["sequence"] < seq]
        state = reader.artifact(boundary["handoff_artifact"])["state"]
        gateway = SavedGateway(state, prefix, root)
        prior_results = {e["payload"]["result"]["action_id"]: e["payload"]["result"]
                         for e in prefix if e["event_type"] == "action_finished"}
        latest = [DevToolResult.model_validate(prior_results[r["action_id"]])
                  for r in state["latest_tool_results"]]
        facts, _, _ = RULES.inventory(reader.artifact(boundary["after_input_artifact"]))
        original = {(*k, v) for k, v in facts.items()}
        priorities = gateway._source_projection_priorities()
        protected = {x for x in original if any(x[0] == p and lo <= x[2] <= hi and rank <= 1
                                                for p, lo, hi, rank in priorities)}
        questions = {"actual_legacy": state["working_notes"].get("open_question")}
        questions["unscoped_surrogate"], error = bind_question({
            "text": "Legacy surrogate; roles NOT_EXPOSED", "evidence": surrogate(state),
        }, gateway._snapshot_spans, prior_results)
        assert error is None
        if row == 13 and str(seq) in protocol["fixed_declarations"]:
            questions["paired_current"], error = bind_question({
                "text": "Which observed open raises the missing-file error?" if seq == 303 else
                "Does the directory guard reach the namespace route, and which branch "
                "raises the observed file error?",
                "evidence": protocol["fixed_declarations"][str(seq)],
            }, gateway._snapshot_spans, prior_results, diff_hash=gateway.current_diff_hash)
            assert error is None
            if seq == 476:
                questions["pre_edit_question"], error = bind_question({
                    "text": state["working_notes"]["open_question"],
                    "evidence": [{**r, "role": "primary"} for r in surrogate(state)],
                }, gateway._snapshot_spans, prior_results,
                    diff_hash=state["working_notes"]["last_update_result"]["diff_hash_at_update"])
                assert error is None
        for variant, question in questions.items():
            name = f"row{row:02}-boundary{seq}-{variant}"
            previous = baseline[name]
            facts, _, _ = RULES.inventory(reader.artifact({
                "path": previous["input_artifact"]["path"],
                "content_hash": previous["input_artifact"]["sha256"],
            }))
            previous_lines = {(*k, v) for k, v in facts.items()}
            gateway.set_question(question)
            projection, view, model_input, actual = compose(state, gateway, latest, prefix)
            if variant != "paired_current":
                assert actual == original == previous_lines
            else:
                assert view["working_notes"]["open_question"]["evidence_delivery"] == "complete"
            result = write_case(root, name, model_input, view, projection, actual,
                                original, previous_lines, protected)
            observed = {key[:3]: (key[3], 0, 0) for key in inventory(gateway._snapshot_spans)}
            support = question_support(observed, gateway.focus_source_references())
            actual_keys = {key[:3] for key in actual}
            result.update(row=row, boundary=seq, variant=variant,
                          original_reason=boundary["reason"],
                          prior_retained_chars=previous["retained_chars"],
                          prior_input_bytes=previous["input_bytes"],
                          syntax_support_lines=len(support),
                          delivered_support_lines=len(support & actual_keys),
                          missing_support_keys=sorted(support - actual_keys))
            results.append(result)
            if variant == "paired_current":
                linebook += [f"## {name}", ""]
                for label, field in [("Newly omitted", "lost_from_prior_text"),
                                     ("Newly retained", "gained_from_prior_text")]:
                    linebook += [f"### {label}", "", "```text"]
                    linebook += [f"{x['path']}:{x['line']} | {x['text']}" for x in result[field]]
                    linebook += ["```", ""]
    summary = {}
    for variant in sorted({r["variant"] for r in results}):
        selected = [r for r in results if r["variant"] == variant]
        summary[variant] = {"cases": len(selected), **{
            k: sum(r[k] for r in selected) for k in (
                "gained_prior_count", "lost_prior_count", "syntax_support_lines",
                "delivered_support_lines")},
            "max_retained_chars": max(r["retained_chars"] for r in selected),
            "max_input_bytes": max(r["input_bytes"] for r in selected)}
    for name, data in [("results.json", results), ("summary.json", summary),
                       ("read-manifest.json", list(reader.files.values()))]:
        (root / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "linebook.md").write_text("\n".join(linebook), encoding="utf-8")
    assert all(digest(Path(x["path"]).read_bytes()) == x["sha256"] for x in reader.files.values())
    journal.append("replay_completed", {
        "runtime_hash": runtime_content_hash(), "summary": summary,
        "original_files_unchanged": len(reader.files),
        "artifacts": {p.name: digest(p.read_bytes()) for p in root.iterdir() if p.is_file()},
        "provider_calls": 0, "count_calls": 0, "task_executions": 0,
        "model_exposure": "NOT_EXPOSED", "quality_claim": False,
        "exact_token_counts_and_full_request_admission": "NOT_RUN",
    })
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
