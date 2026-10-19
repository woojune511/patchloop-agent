"""Provider-free retrieval/packing experiment over immutable dispatched inputs.

Each saved decision is an independent opportunity, not an augmented executable
trajectory. A synthetic quoted search result measures packing only. No model
choice, new reasoning item, judgment, tool execution or repair grade is invented.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics.cleanup_information_checkpoint import ForkStore
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import disjoint
from diagnostics.size_only_replay import TokenEstimator, inventory, load_row, verify_baseline
from patchloop.artifacts import ArtifactStore
from patchloop.dev import evidence_focus, runner, segments, working_plan
from patchloop.dev import history_search as search
from patchloop.dev.contracts import DevToolResult, RequestedTool
from patchloop.dev.conversation import SEGMENT_RULES, assemble_model_input
from patchloop.dev.state import DevJournal
from patchloop.dev.thin_policy import system_prompt
from patchloop.dev.tools import dev_tool_schemas
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json


def query_for(state):
    question = state.get("working_notes", {}).get("open_question")
    text = question.get("text") if isinstance(question, dict) else question
    if isinstance(text, str) and text.strip():
        return text[:search.MAX_QUERY_CHARS], "open_question"
    plan = state.get("working_plan", {}).get("plan")
    text = plan.get("text") if isinstance(plan, dict) else plan
    if isinstance(text, str) and text.strip():
        return text[:search.MAX_QUERY_CHARS], "working_plan"
    text = state.get("public_task", {}).get("issue", {}).get("description")
    if isinstance(text, str) and text.strip():
        return text[:search.MAX_QUERY_CHARS], "public_task"
    return None, "empty"


def search_available(turn, *, spent_calls=0, spent_actions=0):
    remaining = turn.state["remaining_budget"]
    return (bool({"read_file", "search_files"} & set(turn.turn["available_tool_names"]))
            and remaining["model_calls"] - spent_calls - 1
            >= turn.turn["completion_budget_calls"]
            and remaining["tool_actions"] - spent_actions - 1
            >= turn.turn["completion_budget_tool_actions"])


def after_search_events(turn):
    """A public hypothetical completed follow-up, never appended to the source journal."""
    events = list(turn.prefix)
    turn_id = turn.turn["turn_id"]
    for kind, payload in (
        ("turn_started", {"turn_id": turn_id}),
        ("turn_decision_recorded", {"turn_id": turn_id, "error_code": None,
                                    "incomplete_reason": None}),
        ("tool_batch_finished", {"turn_id": turn_id}),
    ):
        event = {"event_type": kind, "payload": payload, "sequence": len(events) + 1}
        events.append({**event, "event_hash": sha256_json(event)})
    return events


def pack_result(turn, result, estimator, *, level="central"):
    """Same-segment and normal size-handoff packing, excluding unknown new reasoning."""
    state = copy.deepcopy(turn.state)
    state["segment_handoff"] = copy.deepcopy(turn.handoff)
    events = after_search_events(turn)
    required_boundary = segments.boundary_reason(
        SimpleNamespace(events=lambda: events), turn.turn["context_segment"]["binding"])
    call = RequestedTool(name=search.TOOL, action_id=f"offline-history-{turn.sequence}",
                         arguments={"query": result["query"]}, turn_decision={
                             "mode": "inspect", "basis": "Recover original public conditions.",
                             "evidence_goal": result["query"][:500], "memory_update": None,
                             "plan_update": None, "plan_update_reason": None})
    tool_result = DevToolResult(action_id=call.action_id, tool=search.TOOL, status="succeeded",
                               input_hash=sha256_json(call.model_dump(mode="json")),
                               workspace_diff_hash=state["current_diff"]["patch_hash"],
                               output=result)
    state["remaining_budget"]["model_calls"] -= 1
    state["remaining_budget"]["tool_actions"] -= 1
    state["latest_tool_results"] = [tool_result.model_dump(mode="json")]
    state["recent_attempt_result_next_question"] = [runner._batch_attempt_card(
        turn_id=call.action_id, calls=[call], results=[tool_result], gateway=None)]
    prompt = system_prompt("current", "brief-v1", search.POLICY)
    quoted_base = runner._segment_public_base(
        prompt, state, [tool_result], [call.model_dump(mode="json")])
    optional = evidence_focus.optional_exchanges(
        state.get("working_notes", {}).get("open_question"), turn.prefix, {call.action_id},
        diff_hash=state["current_diff"]["patch_hash"])
    require(sum(i["type"] == "function_call_output" for i in optional) <= 2,
            "question reference bound changed")
    tools = copy.deepcopy(turn.wire["tools"])
    if search_available(turn, spent_calls=1, spent_actions=1):
        tools.extend(dev_tool_schemas(finish_enabled=False, allowed_tools={search.TOOL},
                                     history_search_policy=search.POLICY,
                                     planning_policy="brief-v1"))
    schema_delta = (estimator.text_count(canonical_json(tools))
                    - estimator.text_count(canonical_json(turn.wire["tools"])))
    attempts = []
    handoff_mode = "major_result_handoff" if required_boundary else "size_handoff"
    for mode in ("same_segment", handoff_mode, handoff_mode + "_without_optional"):
        if mode == "same_segment":
            previous = copy.deepcopy(turn.wire["input"])
            previous[0]["content"] += "\n\n" + search.INSTRUCTIONS
            added = quoted_base[3:]
            state["segment_handoff"]["review_requested"] = False
        else:
            previous = copy.deepcopy(quoted_base)
            if mode == handoff_mode and optional:
                previous.append(SEGMENT_RULES.archive(exchanges=optional))
            added = []
            state["segment_handoff"] = {**state["segment_handoff"],
                                        "reason": required_boundary or "offline_size_projection",
                                        "review_requested": True}
        plan_events = events if mode == "same_segment" else [*events, {
            "event_type": segments.PREPARED_EVENT, "sequence": len(events) + 1, "payload": {}}]
        state["working_plan"] = working_plan.project(
            plan_events, diff_hash=state["current_diff"]["patch_hash"],
            gate=state["workflow_gate"], policy="brief-v1")
        view = runner._segment_current_view(copy.deepcopy(state),
                                           [*previous[3:], *added], [tool_result])
        items = assemble_model_input(system_prompt=prompt, state=view, history=added,
                                     previous_input=previous, context_policy=segments.POLICY)
        counts = estimator.estimate(turn, items)
        counts = {k: counts[k] + schema_delta for k in ("lower", "central", "upper")}
        sizes = segments.request_sizes({**turn.wire, "input": items, "tools": tools})
        reasons = segments.size_reasons(sizes)
        if counts[level] > segments.MAX_INPUT_TOKENS:
            reasons.append("input_tokens")
        if mode == "same_segment" and required_boundary:
            reasons.append(required_boundary)
        attempts.append({"mode": mode, "counts_before_unknown_search_reasoning": counts,
                         "sizes": sizes, "reasons": reasons})
        if not reasons:
            break
    before_facts, before_outputs, before_obs = inventory(turn.wire["input"])
    after_facts, after_outputs, after_obs = inventory(items)
    # Retrieved records are nested quoted data, not promoted native source anchors.
    missing_facts = set(before_facts) - set(after_facts)
    lost_sources = [{"path": p, "file_hash": h, "line": line,
                     "content": before_facts[p, h, line]} for p, h, line in sorted(missing_facts)]
    lost_outputs = {key: before_outputs[key]
                    for key in before_outputs.keys() - after_outputs.keys()}
    lost_observations = {key: before_obs[key] for key in before_obs.keys() - after_obs.keys()}
    require(len(canonical_json(result)) <= search.MAX_RESULT_CHARS, "result bound exceeded")
    require(len(result["records"]) <= 2, "retrieval reference bound exceeded")
    serialized = canonical_json(items)
    for record in result["records"]:
        if record["delivery"] == "complete":
            require(sha256_json(record["body"]) == record["record_id"], "partial retrieved body")
    # The actual tool result must survive public projection without altered content.
    require(after_outputs[call.action_id]["output"] == result, "retrieval delivery changed")
    return {"attempts": attempts, "mode": mode, "fits_known_content": not reasons,
            "already_due_result_boundary": required_boundary,
            "input_hash": sha256_json(items), "visible_chars": len(serialized),
            "lost_sources": lost_sources, "lost_outputs": lost_outputs,
            "lost_observations": lost_observations,
            "selected_source_chars_unchanged": turn.state.get("context_projection"),
            "unknowns": ["search_decision_reasoning", "model_output_cost", "new_decisions",
                         "tool_time_and_later_trajectory"]}, items


def run(manifest_path, output, after_sequence, target_hash, encode, tokenizer):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(not output.exists(), "use a fresh output directory")
    disjoint(output, [repository_root(), manifest_path.parent,
                     *(Path(r["request"]["state_root"]) for r in manifest["rows"])])
    require(manifest["invariants"]["references"] == 2
            and manifest["invariants"]["retained_source_chars"] == 24_000,
            "source reference/source budget differs")
    require(all(r["request"]["segment_boundary_policy"] == segments.DEFAULT_BOUNDARY_POLICY
                for r in manifest["rows"]), "source boundary differs")
    output.mkdir(parents=True)
    journal = DevJournal(output, "run_dev_historysearchreplay")
    store = ArtifactStore(output / "artifacts")
    protocol_path = Path(__file__).parents[1] / "docs/history/2026-10-19-run-history-search.md"
    contract = {"official": False, "new_spend_nanos": 0, "provider_calls": 0,
                "baseline_manifest_hash": sha256_bytes(manifest_path.read_bytes()),
                "source_runtime_hash": manifest["runtime_hash"],
                "investigation_runtime_hash": runtime_content_hash(),
                "implementation_hash": sha256_bytes(Path(__file__).read_bytes()),
                "protocol_hash": sha256_bytes(protocol_path.read_bytes()),
                "search_contract": search.contract(), "after_sequence": after_sequence,
                "target_observation_hash": target_hash, "tokenizer": tokenizer,
                "query": "question-else-plan-text-else-task-statement-first-800-chars",
                "ranking_tuning_after_results": False, "counterfactual": "independent-packing-only",
                "model_query_choice": "NOT_RUN", "evidence_uptake": "NOT_RUN",
                "repair_success": "NOT_RUN", "boundary": segments.DEFAULT_BOUNDARY_POLICY}
    # Freeze the protocol before loading the corpus or obtaining retrieval scores.
    (output / "manifest.json").write_text(canonical_json(contract) + "\n", encoding="utf-8")
    journal.append("experiment_frozen", contract)
    cases, opaque, sources = {}, {}, {str(manifest_path): contract["baseline_manifest_hash"]}
    for row in manifest["rows"]:
        turns, reasoning, reads = load_row(row, after_sequence)
        verify_baseline(turns)
        cases[row["row_id"]] = turns
        opaque.update(reasoning)
        sources.update(reads)
    estimator = TokenEstimator(encode, opaque, [t for turns in cases.values() for t in turns])
    results = []
    for row in manifest["rows"]:
        root = Path(row["request"]["state_root"])
        original = DevJournal(root, row["request"]["resume_run_id"])
        events = original.events()
        source_store = ForkStore(root, events)
        corpus = search.PublicHistory()
        requests = []
        for turn in cases[row["row_id"]]:
            corpus.sync(events, source_store, before_sequence=turn.sequence + 1)
            query, query_source = query_for(turn.state)
            visible = inventory(turn.wire["input"])[2]
            retrieval = (corpus.search(
                query, current_diff_hash=turn.state["current_diff"]["patch_hash"])
                         if query else None)
            complete = {r["record_id"] for r in retrieval["records"]
                        if r["delivery"] == "complete"} if retrieval else set()
            record = {"request_sequence": turn.sequence, "query_source": query_source,
                      "query": query, "corpus_records": len(corpus.records),
                      "target_acquired": target_hash in corpus.records,
                      "target_already_visible": target_hash in visible,
                      "target_retrieved_complete": target_hash in complete,
                      "search_available": search_available(turn), "retrieval": retrieval,
                      "baseline_tokens": turn.usage["input_tokens"], "packing": {}}
            if retrieval:
                for level in ("lower", "central", "upper"):
                    packed, projected = pack_result(turn, retrieval, estimator, level=level)
                    if level == "central":
                        packed["input_artifact"] = store.put_json(projected).model_dump(mode="json")
                    record["packing"][level] = packed
            requests.append(record)
        source_files = {p: digest for p, digest in source_store.reads.items() if Path(p).is_file()}
        sources.update(source_files)
        summary = {
            "requests": len(requests),
            "target_acquired": sum(r["target_acquired"] for r in requests),
            "target_visible": sum(r["target_already_visible"] for r in requests),
            "target_retrieved": sum(r["target_retrieved_complete"] for r in requests),
            "newly_retrievable": sum(r["target_retrieved_complete"]
                                     and not r["target_already_visible"] for r in requests),
            "newly_retrievable_when_available": sum(r["target_retrieved_complete"]
                and not r["target_already_visible"] and r["search_available"] for r in requests),
            "search_available": sum(r["search_available"] for r in requests),
            "packing_modes": dict(Counter(r["packing"]["central"]["mode"] for r in requests
                                          if r["packing"])),
        }
        row_result = {"row": row["row_id"], "summary": summary, "requests": requests}
        results.append(row_result)
        journal.append("row_replayed", {"row": row["row_id"], "summary": summary,
            "result": store.put_json(row_result).model_dump(mode="json")})
        print(canonical_json({"row": row["row_id"], **summary}), flush=True)
    require(all(sha256_bytes(Path(p).read_bytes()) == digest for p, digest in sources.items()),
            "immutable source changed")
    result = {"contract": contract, "rows": results, "calibration": estimator.calibration,
              "source_files": sources, "source_files_unchanged": True}
    path = output / "result.json"
    path.write_text(canonical_json(result) + "\n", encoding="utf-8")
    journal.append("experiment_completed", {"result_path": str(path),
                                           "result_hash": sha256_bytes(path.read_bytes()),
                                           "source_files_verified": len(sources)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--after-sequence", type=int, required=True)
    parser.add_argument("--target-observation-hash", required=True)
    parser.add_argument("--tokenizer-package", type=Path, required=True)
    parser.add_argument("--tokenizer-cache", type=Path, required=True)
    args = parser.parse_args()
    require(args.tokenizer_package.is_dir() and args.tokenizer_cache.is_dir(),
            "local tokenizer required; downloads forbidden")
    sys.path.insert(0, str(args.tokenizer_package.resolve()))
    os.environ["TIKTOKEN_CACHE_DIR"] = str(args.tokenizer_cache.resolve())
    import tiktoken

    def forbidden(*args, **kwargs):
        raise RuntimeError("offline history replay forbids network connections")

    with patch("socket.socket.connect", forbidden), patch("socket.socket.connect_ex", forbidden):
        encoding = tiktoken.get_encoding("o200k_base")
        metadata = {"package": "tiktoken", "version": tiktoken.__version__,
                    "encoding": encoding.name, "cache_files": {
                        str(p): sha256_bytes(p.read_bytes())
                        for p in args.tokenizer_cache.iterdir() if p.is_file()}}
        run(args.manifest.resolve(), args.output.resolve(), args.after_sequence,
            args.target_observation_hash,
            lambda value: encoding.encode(value, disallowed_special=()), metadata)


if __name__ == "__main__":
    main()
