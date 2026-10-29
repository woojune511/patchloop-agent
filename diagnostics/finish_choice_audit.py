"""Read-only public decision/delivery audit and conditional resource comparisons.

No provider, sandbox, evaluator or workspace execution. Results explain recorded
choices and minimum slots; they do not infer model motives or repair correctness.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev.completion_budget import (
    CompletionState,
    action_budget_explanations,
    mutation_attempt_budget,
)
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges
from patchloop.dev.state import DevJournal
from patchloop.util import sha256_bytes, sha256_json


def slot_comparison(*, calls, corrections, actions, used_edits, check_count, caps=(3, 4, 12)):
    """Hold response/action slots fixed while changing only accepted-edit capacity."""
    if min(calls, corrections, actions, used_edits, check_count) < 0 or corrections > calls:
        raise ValueError("invalid resource snapshot")
    rows = []
    for cap in caps:
        if cap < used_edits:
            raise ValueError("counterfactual cap is below already accepted edits")
        state = CompletionState(
            check_count=check_count, remaining_check_count=0, unused_check_count=0,
            unrun_recoverable_check=False, requires_mutation=True, anchor_available=True,
            remaining_mutations=cap - used_edits, mutation_retry_available=False,
        )
        route = mutation_attempt_budget(state)
        forecast = action_budget_explanations(
            state, offered_tools=frozenset({"run_probe"}), total_model_calls=calls,
            correction_model_calls=corrections, remaining_tool_actions=actions,
            max_parallel_reads=0, test_comparison_enabled=False,
        )
        rows.append({
            "edit_cap": cap, "edits_remaining": cap - used_edits,
            "ordinary_calls": calls - corrections,
            "edit_route_minimum": {"calls": route.minimum,
                                   "actions": route.minimum_tool_actions},
            "immediate_shortfalls": [key for key, available, required in (
                ("model_calls", calls - corrections, route.minimum),
                ("tool_actions", actions, route.minimum_tool_actions),
                ("accepted_mutations", cap - used_edits, 1),
            ) if available < required],
            "after_one_probe_shortfalls": forecast["after_exploration"]["run_probe"][0][
                "edit_route_shortfalls"],
        })
    return {
        "kind": "minimum_slot_counterfactual", "rows": rows,
        "assumptions": (
            "Current editable source anchor, successful edit, the specified required-check "
            "count and finish; no automatic recheck or original replay. All other response/action "
            "slots and correction reservations stay fixed. Cost/time, scope, changed evidence, "
            "failed edits/checks and actual future admission require reassessment. "
            "No model choice, patch quality or causal repair benefit is predicted."
        ),
    }


def _read_json(store, reference):
    return json.loads(store.read_bytes(Artifact.model_validate(reference)))


def _evidence(rows, items, state, action_id, before_sequence):
    event = next((row for row in rows if row["event_type"] == "action_finished"
                  and row["sequence"] < before_sequence
                  and row["payload"]["result"]["action_id"] == action_id), None)
    if event is None:
        raise ValueError("evidence must name an earlier public action result")
    original = event["payload"]["result"]
    if original["tool"] not in {"run_probe", "run_check", "run_tests", "read_file", "search_files"}:
        raise ValueError("unsupported public evidence tool")
    delivered = [("current_state", value) for value in state.get("latest_tool_results", [])]
    delivered += [("native_or_public_archive", json.loads(item["output"]))
                  for item in public_exchanges(items, archive_kind=PUBLIC_EVIDENCE_KIND)
                  if item.get("type") == "function_call_output"]
    selected = [(channel, value) for channel, value in delivered
                if value.get("action_id") == action_id]
    original_output = original.get("output", {})
    return {
        "action_id": action_id, "sequence": event["sequence"], "event_hash": event["event_hash"],
        "input_hash": original["input_hash"], "tool": original["tool"],
        "execution_status": original["status"],
        "current_candidate": original["workspace_diff_hash"] == state["current_diff"]["patch_hash"],
        "delivered_channels": sorted({channel for channel, _ in selected}),
        "text_fields": {key: {
            "characters": len(original_output[key]),
            "sha256": sha256_bytes(original_output[key].encode("utf-8")),
            "exact_body_delivered": any(
                value.get("output", {}).get(key) == original_output[key] for _, value in selected),
        } for key in ("stdout", "stderr") if isinstance(original_output.get(key), str)},
        "source_spans": [{
            "path": span["path"], "start_line": span["start_line"],
            "end_line": span["end_line"], "file_hash": span["file_hash"],
            "characters": len(span["content"]),
            "exact_body_delivered": any(
                candidate == span for _, value in selected
                for candidate in value.get("output", {}).get("spans", [])),
        } for span in original_output.get("spans", []) if "content" in span],
        "interpretation": "Execution success and delivery do not classify the observed behavior.",
    }


def audit_saved_turn(root: Path, run_id: str, sequence: int, *, evidence_ids=(), check_count=1):
    root = root.resolve()
    if (not (root / "runs" / f"{run_id}.jsonl").is_file()
            or not (root / "artifacts/objects/sha256").is_dir()):
        raise ValueError("existing journal and artifact store required")
    journal = DevJournal(root, run_id)
    rows = journal.events()  # Verify the chain; never export unrelated payloads.
    event = next((row for row in rows if row["sequence"] == sequence), None)
    if event is None or event["event_type"] != "turn_started":
        raise ValueError("selection must be a saved public turn")
    turn = event["payload"]
    store = ArtifactStore(root / "artifacts")
    items = _read_json(store, turn["model_input_artifact"])
    prepared = _read_json(store, turn["prepared_input"]["artifact"])["request"]
    request_hash = sha256_json(prepared)
    if (prepared["input"] != items
            or request_hash != turn["prepared_input"]["request_hash"]
            or turn["model_input_hash"] != turn["model_input_artifact"]["content_hash"]):
        raise ValueError("saved input differs from its prepared request")
    dispatch = [row for row in rows if row["event_type"] == "provider_call_started"
                and row["payload"]["turn_id"] == turn["turn_id"]]
    if (len(dispatch) != 1 or dispatch[0]["payload"]["request_hash"] != request_hash
            or dispatch[0]["payload"]["counted_request_hash"] != request_hash):
        raise ValueError("counted/dispatched request identity is not established")
    state = reconstruct_state(items, context_policy="segmented-v1")
    if state["completion_guidance"].get("verification_policy") != "public-checks-v1":
        raise ValueError("this comparison requires the public-checks-v1 diagnostic-only policy")
    tools = sorted(tool["name"] for tool in prepared["tools"])
    if tools != sorted(state["available_tool_names"]):
        raise ValueError("delivered tools disagree with the public state")
    decisions = [row for row in rows if row["event_type"] == "turn_decision_recorded"
                 and row["payload"]["turn_id"] == turn["turn_id"]]
    budget = state["remaining_budget"]
    cost = budget["cost"]
    original_cap = journal.load_envelope().limits.max_accepted_mutations
    comparison = slot_comparison(
        calls=budget["model_calls"],
        corrections=cost["completion_cost"]["correction_model_calls_reserved"],
        actions=budget["tool_actions"], used_edits=original_cap - budget["accepted_mutations"],
        check_count=check_count,
    )
    recorded_route = state["action_horizon"]["mutation_completion_horizon"]
    minimum = comparison["rows"][0]["edit_route_minimum"]
    if (minimum["calls"] != recorded_route["minimum_calls"]
            or minimum["actions"] != recorded_route["minimum_tool_actions"]):
        raise ValueError("specified simple edit route does not match the recorded minimum")
    return {
        "schema": "public-finish-choice-audit-v1", "run_id": run_id,
        "turn": {"sequence": sequence, "event_hash": event["event_hash"],
                 "turn_id": turn["turn_id"], "request_hash": request_hash,
                 "dispatch_sequence": dispatch[0]["sequence"]},
        "candidate_diff_hash": state["current_diff"]["patch_hash"],
        "workflow_gate": state["workflow_gate"], "offered_tools": tools,
        "chosen_actions": [{"sequence": row["sequence"], "event_hash": row["event_hash"],
                            "names": [call["name"] for call in row["payload"]["tool_calls"]]}
                           for row in decisions],
        "original_edit_cap": original_cap,
        "remaining": {key: budget[key] for key in (
            "model_calls", "tool_actions", "accepted_mutations", "active_wall_time_seconds")},
        "remaining_cost_nanos": cost["remaining"],
        "legacy_action_forecast_present": "action_budget" in state["action_horizon"],
        "recorded_mutation_minimum_possible": recorded_route["minimum_possible"],
        "evidence": [_evidence(rows, items, state, action_id, sequence)
                     for action_id in evidence_ids],
        "local_resource_comparison": comparison,
        "limits": "No evaluator data, source bodies, reasoning or inferred model motives exported.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_root", type=Path)
    parser.add_argument("run_id")
    parser.add_argument("turn_sequence", type=int)
    parser.add_argument("--evidence-action-id", action="append", default=[])
    parser.add_argument("--required-check-count", type=int, default=1)
    args = parser.parse_args()
    print(json.dumps(audit_saved_turn(
        args.state_root, args.run_id, args.turn_sequence,
        evidence_ids=args.evidence_action_id, check_count=args.required_check_count,
    ), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
