"""Offline saved-boundary selector replay. No provider, workspace execution or grades."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from patchloop.contracts import PublicTask
from patchloop.dev.context import build_observed_source_index, project_observed_sources
from patchloop.dev.contracts import DevLimits, DevToolResult
from patchloop.dev.conversation import assemble_model_input
from patchloop.dev.evidence_focus import bind_question, optional_exchanges
from patchloop.dev.path_policy import mutation_path_allowed
from patchloop.dev.public_history import SnapshotRules
from patchloop.dev.runner import SEGMENT_RULES, _segment_current_view, _segment_public_base
from patchloop.dev.state import DevJournal
from patchloop.dev.thin_policy import system_prompt
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json


def digest(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class Inputs:
    def __init__(self):
        self.files = {}

    def read(self, path):
        path = Path(path)
        raw = path.read_bytes()
        entry = {"path": str(path.resolve()), "sha256": digest(raw), "bytes": len(raw)}
        if str(path.resolve()) in self.files:
            assert self.files[str(path.resolve())] == entry
        self.files[str(path.resolve())] = entry
        return json.loads(raw)

    def artifact(self, ref):
        result = self.read(ref["path"])
        assert self.files[str(Path(ref["path"]).resolve())]["sha256"] == ref["content_hash"]
        return result

    def events(self, path):
        raw = Path(path).read_bytes()
        assert raw.endswith(b"\n")
        self.files[str(Path(path).resolve())] = {
            "path": str(Path(path).resolve()), "sha256": digest(raw), "bytes": len(raw),
        }
        events, previous = [], None
        for number, line in enumerate(raw.splitlines(), 1):
            event = json.loads(line)
            assert event["sequence"] == number and event["previous_event_hash"] == previous
            assert event["event_hash"] == sha256_json({k: v for k, v in event.items()
                                                      if k != "event_hash"})
            previous = event["event_hash"]
            events.append(event)
        return events


def inventory(spans):
    return {(s["path"], s["file_hash"], s["start_line"] + i, line)
            for s in spans for i, line in enumerate(s["content"].split("\n"))}


def ranges(lines):
    groups = {}
    for path, file_hash, number, _ in sorted(lines):
        pieces = groups.setdefault((path, file_hash), [])
        if pieces and pieces[-1][1] + 1 == number:
            pieces[-1][1] = number
        else:
            pieces.append([number, number])
    return [{"path": p, "file_hash": h, "ranges": r} for (p, h), r in groups.items()]


def surrogate(state):
    """Frozen before replay: latest current note citations, at most two; no hindsight."""
    refs = []
    for note in reversed(state.get("working_notes", {}).get("findings", [])):
        if note.get("status") != "current":
            continue
        for ref in note.get("evidence", []):
            if ref["kind"] != "source":
                continue
            wire = {k: ref[k] for k in ("kind", "path", "start_line", "end_line")}
            if wire not in refs:
                refs.append(wire)
            if len(refs) == 2:
                return refs
    return refs


def replay(boundary, events, inputs, root):
    handoff = inputs.artifact(boundary["handoff_artifact"])
    state = handoff["state"]
    prefix = [e for e in events if e["sequence"] < boundary["segment_sequence"]]
    # Hydrate immutable public observations only. No executor or filesystem source read.
    gateway = DevToolGateway(
        workspace=root / "unmaterialized",
        public_task=PublicTask.model_validate(state["public_task"]),
        sandbox=None, journal=SimpleNamespace(events=lambda: prefix), limits=DevLimits(),
    )
    gateway._working_findings = copy.deepcopy(state["working_notes"]["findings"])
    spans = list(gateway.spans.values())
    current_versions = {}
    for s in spans:
        old = current_versions.get(s["path"])
        if old is None or old[0] < s.get("last_observed_seq", 0):
            current_versions[s["path"]] = s.get("last_observed_seq", 0), s["file_hash"]
    spans = [s for s in spans if s["file_hash"] == current_versions[s["path"]][1]]

    def tracked(path, **_):
        selected = [s for s in spans if s["path"] == path]
        if not selected:
            raise ContractError("no observed public body")
        lines = {s["start_line"] + i: v for s in selected
                 for i, v in enumerate(s["content"].split("\n"))}
        # Only for locating an already-observed failed mutation anchor. Gap sentinels
        # never enter spans, selector output, source hashes, or any model input.
        body = "\n".join(lines.get(n, "\x00unobserved") for n in range(1, max(lines) + 1))
        return path, SimpleNamespace(read_bytes=lambda: body.encode())

    gateway._tracked_path = tracked
    priorities = gateway._source_projection_priorities()
    prior_results = {e["payload"]["result"]["action_id"]: e["payload"]["result"]
                     for e in prefix if e["event_type"] == "action_finished"}
    latest = [DevToolResult.model_validate(prior_results[r["action_id"]])
              for r in state["latest_tool_results"]]
    native_ids = {s["span_id"] for r in latest for s in [
        *r.output.get("spans", []), r.output.get("mutation_evidence"),
        *r.output.get("revalidated_spans", []),
    ] if isinstance(s, dict)}
    native = [s for s in spans if s["span_id"] in native_ids]
    editable = {s["path"] for s in spans if mutation_path_allowed(
        s["path"], allowed_paths=state["public_task"]["constraints"]["allowed_paths"],
        forbidden_paths=state["public_task"]["constraints"]["forbidden_paths"])}
    kwargs = dict(native_spans=native, priorities=priorities, editable_paths=editable,
                  max_chars=24_000)
    baseline = project_observed_sources(spans, **kwargs)
    original = inventory(state["source_spans"])
    assert inventory(baseline.source_spans) == original, (
        "baseline reconstruction differs", boundary["row"], boundary["segment_sequence"],
        ranges(original - inventory(baseline.source_spans)),
        ranges(inventory(baseline.source_spans) - original))
    selected = surrogate(state)
    question, error = bind_question({"text": "Offline surrogate; model focus NOT_EXPOSED",
                                     "evidence": selected}, spans, {})
    assert error is None, error
    changed = project_observed_sources(spans, **kwargs, focus_references=question["evidence"])
    before, after = inventory(baseline.delivered_spans), inventory(changed.delivered_spans)
    wanted = {line for line in inventory(spans) if any(
        line[0] == r["path"] and line[1] == r["file_hash"] and
        r["start_line"] <= line[2] <= r["end_line"] for r in question["evidence"])}
    assert changed.retained_content_chars <= 24_000
    assert not (after - inventory(spans))
    protected = {line for line in before if any(
        line[0] == p and lo <= line[2] <= hi and rank <= 1 for p, lo, hi, rank in priorities)}
    assert protected <= after
    candidate = copy.deepcopy(state)
    candidate["source_spans"] = list(changed.source_spans)
    candidate["working_notes"]["open_question"] = question
    candidate["observed_source_index"] = build_observed_source_index(
        changed.delivered_spans, editable_paths=changed.editable_paths)
    candidate["context_projection"].update(
        retained_content_chars=changed.retained_content_chars,
        omitted_observed_line_count=changed.omitted_observed_line_count,
        omitted_pinned_ranges=list(changed.omitted_pinned_ranges),
        omitted_observed_ranges=list(changed.omitted_observed_ranges),
        omitted_observed_range_count=changed.omitted_observed_range_count,
        delivered_source_hash=sha256_json(changed.delivered_spans),
    )
    ids = {r.action_id for r in latest}
    calls = [c for e in prefix if e["event_type"] == "turn_decision_recorded"
             for c in e["payload"].get("tool_calls", []) if c["action_id"] in ids]
    prompt = system_prompt("current", "brief-v1")
    base = _segment_public_base(prompt, candidate, latest, calls)
    view = _segment_current_view(candidate, base[3:], latest)
    model_input = assemble_model_input(system_prompt=prompt, state=view, history=[],
                                       previous_input=base, context_policy="segmented-v1")
    note_projection = []
    for old, new in zip(state["working_notes"]["findings"],
                        view["working_notes"]["findings"], strict=True):
        assert old["statement"] == new["model_interpretation"]
        assert "statement" not in new and "status" not in new
        assert new["evidence_currency"] == old["status"]
        note_projection.append({k: new[k] for k in (
            "note_id", "model_interpretation", "evidence_currency", "evidence_delivery", "evidence",
        )})
    facts, _, _ = SnapshotRules("harness_current_state",
                                "harness_historical_public_evidence_v1", "",
                                initial_state_index=1).inventory(model_input)
    delivered = {(*k, v) for k, v in facts.items()}
    assert after <= delivered
    assert not any(i.get("type") == "reasoning" for i in model_input)
    # Separate fixed surrogate for the older-result route, never combined with the
    # two source references or selected from later actions/grades.
    tool_refs = []
    for note in reversed(state["working_notes"]["findings"]):
        for ref in note.get("evidence", []):
            if ref["kind"] != "tool_result" or prior_results[ref["action_id"]]["tool"] not in {
                "run_check", "run_tests", "run_probe",
            }:
                continue
            wire = {"kind": "tool_result", "action_id": ref["action_id"]}
            if wire not in tool_refs:
                tool_refs.append(wire)
    tool_refs = tool_refs[:2]
    tool_candidate = copy.deepcopy(state)
    tool_question, error = bind_question({"text": "Offline tool surrogate; NOT_EXPOSED",
                                         "evidence": tool_refs}, [], prior_results)
    assert error is None
    tool_candidate["working_notes"]["open_question"] = tool_question
    tool_base = _segment_public_base(prompt, tool_candidate, latest, calls)
    added = optional_exchanges(tool_question, prefix, ids)
    if added:
        tool_base.append(SEGMENT_RULES.archive(exchanges=added))
    tool_view = _segment_current_view(tool_candidate, tool_base[3:], latest)
    tool_input = assemble_model_input(system_prompt=prompt, state=tool_view, history=[],
                                      previous_input=tool_base, context_policy="segmented-v1")
    resolved_tool_refs = tool_view["working_notes"]["open_question"]["evidence"]
    assert all(r["evidence_delivery"] == "complete" for r in resolved_tool_refs)
    assert all(r["behavior_coverage"] == "not_assessed" for r in resolved_tool_refs)
    identifier = f"row{boundary['row']:02}-boundary{boundary['segment_sequence']}"
    return {
        "id": identifier, "row": boundary["row"], "sequence": boundary["segment_sequence"],
        "original_reason": boundary["reason"], "baseline_exact": True,
        "surrogate_references": question["evidence"], "model_focus_exposure": "NOT_EXPOSED",
        "declared_lines": len(wanted), "before_declared_lines": len(wanted & before),
        "after_declared_lines": len(wanted & after),
        "gained_lines": len(after - before), "displaced_lines": len(before - after),
        "gained_ranges": ranges(after - before), "displaced_ranges": ranges(before - after),
        "missing_declared_ranges": ranges(wanted - after),
        "before_retained_chars": baseline.retained_content_chars,
        "after_retained_chars": changed.retained_content_chars,
        "protected_lines_preserved": len(protected),
        "note_projection": note_projection,
        "closed_by_model_count": sum(
            c["status"] == "closed_by_model"
            for c in view["working_notes"].get("verification", {}).get("items", [])),
        "new_input_bytes": len(canonical_json(model_input).encode()),
        "exact_token_count": "NOT_RUN", "behavior_effect": "NOT_ASSESSED",
        "tool_surrogate": {"references": resolved_tool_refs,
                           "additional_bodies": len(added) // 2,
                           "new_input_bytes": len(canonical_json(tool_input).encode()),
                           "full_request_admission": "NOT_RUN; offline body delivery only"},
        "tool_input": tool_input if tool_refs else None,
        "input": model_input,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    inputs = Inputs()
    journal = DevJournal(args.output, "run_dev_handoffreplay")
    source_hashes = {str(p): digest(p.read_bytes()) for p in [
        Path(__file__), *Path("patchloop/dev").glob("*.py"),
    ]}
    protocol = {
        "question": "Declared source retention and displaced public information at fixed handoffs",
        "baseline_commit": "ffe11a0", "implementation_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_hashes": source_hashes, "scope": "all75 saved plmini20live02 handoffs",
        "selection": "latest current notes in reverse retained order, first2 distinct source refs",
        "secondary_selection": "separate first2 retained-note verification refs; "
                               "reverse note order, historical refs eligible, no combined focus",
        "selection_excludes": "future actions, future probes, grade/evaluator information",
        "model_focus_exposure": "NOT_EXPOSED; deterministic surrogate selector test only",
        "limits": {"retained_source_chars": 24_000, "new_provider_calls": 0,
                   "new_count_calls": 0, "new_solver_runs": 0, "docker_calls": 0},
        "stop": "baseline mismatch, unseen source, protected source displacement or budget breach",
        "quality_claim": False,
    }
    journal.append("analysis_started", protocol)
    try:
        boundaries = inputs.read(args.audit_root / "boundaries-v2.json")
        rows = inputs.read(args.audit_root / "rows-v2.json")
        events = {r["row"]: inputs.events(r["journal"]) for r in rows}
        results = []
        for boundary in boundaries:
            result = replay(boundary, events[boundary["row"]], inputs, args.output)
            model_input = result.pop("input")
            tool_input = result.pop("tool_input")
            path = args.output / f"{result['id']}.json"
            path.write_text(canonical_json(model_input), encoding="utf-8")
            result["input_artifact"] = {"path": str(path), "sha256": digest(path.read_bytes())}
            if tool_input is not None:
                tool_path = args.output / f"{result['id']}-tool-focus.json"
                tool_path.write_text(canonical_json(tool_input), encoding="utf-8")
                result["tool_surrogate"]["input_artifact"] = {
                    "path": str(tool_path), "sha256": digest(tool_path.read_bytes()),
                }
            results.append(result)
        summary = {
            "boundaries": len(results), "baseline_exact": sum(r["baseline_exact"] for r in results),
            **{k: sum(r[k] for r in results) for k in (
                "declared_lines", "before_declared_lines", "after_declared_lines",
                "gained_lines", "displaced_lines")},
            "changed_boundaries": sum(r["gained_lines"] > 0 for r in results),
            "reason_counts": dict(Counter(r["original_reason"] for r in results)),
            "maximum_retained_chars": max(r["after_retained_chars"] for r in results),
            "notes_preserved_as_interpretations": sum(len(r["note_projection"]) for r in results),
            "note_delivery": dict(Counter(n["evidence_delivery"] for r in results
                                           for n in r["note_projection"])),
            "model_closure_occurrences": sum(r["closed_by_model_count"] for r in results),
            "tool_focus_boundaries": sum(bool(r["tool_surrogate"]["references"]) for r in results),
            "tool_references_delivered": sum(
                len(r["tool_surrogate"]["references"]) for r in results),
            "additional_tool_bodies": sum(
                r["tool_surrogate"]["additional_bodies"] for r in results),
            "model_focus_exposure": "NOT_EXPOSED", "behavior_effect": "NOT_ASSESSED",
            "token_counts": "NOT_RUN; no remote calls", "provider_calls": 0,
        }
        reports = []
        for name, value in [("results.json", results), ("summary.json", summary),
                            ("read-manifest.json", list(inputs.files.values()))]:
            path = args.output / name
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
            reports.append({"path": str(path), "sha256": digest(path.read_bytes())})
        assert all(digest(Path(x["path"]).read_bytes()) == x["sha256"]
                   for x in inputs.files.values())
        journal.append("analysis_completed", {
            **summary, "original_files_unchanged": len(inputs.files),
            "reports": reports,
        })
        print(json.dumps(summary))
    except Exception as exc:
        journal.append("analysis_failed", {"exception": type(exc).__name__, "message": str(exc)})
        raise


if __name__ == "__main__":
    main()
