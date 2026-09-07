"""A readable current view, separate from the complete public audit context.

No model summarization or source access occurs here. Native calls/results remain
exact; only redundant harness accounting and already delivered bodies are omitted.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from patchloop.dev.path_policy import mutation_path_allowed


def _select(value: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: value[key] for key in keys if key in value}


def _source_catalog(view: dict[str, Any]) -> None:
    """Group exact deliveries by file/action, preserving gaps and inline fallbacks."""
    if "source_spans" not in view and "observed_source_index" not in view:
        return
    files: dict[tuple[str, str], dict[str, Any]] = {}
    constraints = view.get("public_task", {}).get("constraints")

    def group_for(row: dict[str, Any]) -> dict[str, Any]:
        identity = row["path"], row["file_hash"]
        return files.setdefault(identity, {
            "path": identity[0], "file_hash": identity[1],
            "content_delivery": {}, "inline_spans": [], "headers": [],
        })

    for span in view.pop("source_spans", []):
        group = group_for(span)
        references = span.get("content_delivery")
        if not references:
            group["inline_spans"].append(_select(span, ("start_line", "end_line", "content")))
            continue
        for ref in references:
            fields = group["content_delivery"].setdefault(ref["action_id"], {})
            fields.setdefault(ref["field"], []).append([ref["start_line"], ref["end_line"]])
    index = view.pop("observed_source_index", {})
    for header in index.get("entries", []):
        group_for(header)["headers"].append(_select(header, ("kind", "name", "start_line")))
    for group in files.values():
        if isinstance(constraints, dict):
            group["edit_permission"] = "allowed" if mutation_path_allowed(
                group["path"], allowed_paths=constraints.get("allowed_paths", []),
                forbidden_paths=constraints.get("forbidden_paths", []),
            ) else "read_only"
        for fields in group["content_delivery"].values():
            for field, ranges in fields.items():
                merged: list[list[int]] = []
                for start, end in sorted(ranges):
                    if merged and start <= merged[-1][1] + 1:
                        merged[-1][1] = max(merged[-1][1], end)
                    else:
                        merged.append([start, end])
                fields[field] = merged
        for key in ("inline_spans", "headers"):
            if not group[key]:
                del group[key]
    view["current_sources"] = list(files.values())
    view["source_index_omitted_count"] = index.get("omitted_count", 0)


def compact_model_state(
    state: dict[str, Any], history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Project an already public, source-validated state without changing authority."""
    view = copy.deepcopy(state)
    # Omit redundant historical cards, not the separately derived current
    # completion_guidance. Retain protocol cards for unsatisfied corrections.
    if "recent_attempt_result_next_question" in view:
        view["recent_attempt_result_next_question"] = [
            card for card in view["recent_attempt_result_next_question"]
            if card.get("attempt") == "protocol"
        ]
    if "evidence_ledger" in view:
        view["evidence_ledger"] = _select(view["evidence_ledger"], ("search_summary",))
    if "action_horizon" in view:
        view["action_horizon"] = _select(view["action_horizon"], (
            "minimum_completion_calls", "completion_budget_calls", "completion_possible",
            "protected_completion_possible", "mutation_completion_horizon", "exploration_state",
            "model_turns_available_for_exploration", "tool_actions_available_for_exploration",
            "closure_reason", "tools_closing_after_this_turn", "tool_closure_prediction_basis",
            "tool_policy_transition", "max_parallel_reads_this_turn",
        ))
    if "mutation_readiness" in view:
        view["mutation_readiness"] = _select(view["mutation_readiness"], (
            "state", "current_anchor_evidence_paths",
        ))
    if "context_projection" in view:
        view["context_projection"].pop("delivered_source_hash", None)
        view["context_projection"].pop("mutation_readiness_basis", None)
    _source_catalog(view)
    notes = view.get("working_notes")
    if isinstance(notes, dict):
        # These constant explanations already appear in the fixed system prompt.
        notes.pop("interpretation", None)
        verification = notes.get("verification", {})
        verification.pop("interpretation", None)
        for item in verification.get("items", []):
            item.pop("created_turn_id", None)
            item.pop("updated_turn_id", None)

    results: dict[str, dict[str, Any]] = {}
    for item in history:
        if item.get("type") != "function_call_output":
            continue
        result = json.loads(item["output"])
        if (isinstance(result, dict) and result.get("action_id") == item.get("call_id")
                and isinstance(result.get("output"), dict)):
            results[item["call_id"]] = result

    if isinstance(notes, dict):
        receipt = notes.get("last_update_result")
        if isinstance(receipt, dict) and isinstance(receipt.get("turn_id"), str):
            delivered = results.get(receipt.get("action_id"), {}).get("memory_update_result")
            if delivered == receipt:
                # Match the full durable receipt, not just its formerly allocated IDs.
                # It may belong to any earlier exchange, including before a mutation.
                notes["last_update_result"] = {
                    **_select(receipt, ("turn_id", "action_id")),
                    "delivery": "preceding_function_call_output",
                }
                notes.pop("last_update_diagnostics", None)

    for key, tool in (("recent_checks", "run_check"), ("recent_probes", "run_probe")):
        for record in view.get(key, []):
            result = results.get(record.get("action_id"), {})
            if (result.get("tool") != tool or not isinstance(record.get("diff_hash"), str)
                    or result["output"].get("diff_hash") != record["diff_hash"]
                    or (tool == "run_check"
                        and result["output"].get("check_id") != record.get("check_id"))):
                continue
            for field in ("stdout", "stderr", "execution_policy", "public_check_failure"):
                record.pop(field, None)
            record["delivery"] = "preceding_function_call_output"
            if (tool == "run_probe" and isinstance(record.get("observation"), dict)
                    and result.get("observation") == record["observation"]):
                # Keep the distinction salient, without repeating range excerpts
                # already delivered at the front of this native probe result.
                record["observation"] = {
                    **_select(record["observation"], ("execution_status", "behavior_verdict")),
                    "details_delivery": "preceding_function_call_output.observation",
                }

    failed = view.get("last_failed_mutation")
    if isinstance(failed, dict):
        result = results.get(failed.get("action_id"), {})
        if result.get("tool") == "replace_text" and result.get("status") == "failed":
            view["last_failed_mutation"] = {
                **_select(failed, (
                    "action_id", "baseline_diff_hash", "error_code", "error_location",
                )),
                "error_message": result.get("message"),
                "mutation_failure": copy.deepcopy(result["output"].get("mutation_failure")),
                "delivery": "preceding_function_call_output",
                "replacement_delivery": "preceding_function_call_arguments",
            }
    successful = view.get("last_successful_mutation")
    if isinstance(successful, dict) and "diff_hash" in successful:
        result = next((r for r in reversed(list(results.values()))
                       if r.get("tool") == "replace_text" and r.get("status") == "succeeded"
                       and r["output"].get("worktree_diff_hash") == successful["diff_hash"]), None)
        if result is not None:
            view["last_successful_mutation"] = {
                **_select(successful, (
                    "diff_hash", "changed_files", "hypothesis", "expected_behavior",
                    "postimage_evidence_available",
                )),
                "action_id": result["action_id"], "delivery": "preceding_function_call_output",
            }
    return view
