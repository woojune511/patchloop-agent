"""Bounded rejected test text, not an applied change or verification obligation."""

from __future__ import annotations

from typing import Any

from patchloop.dev.mutation_tools import MUTATION_TOOLS

MAX_TEST_PROPOSAL_CHARS = 8_000
MAX_TEST_PROPOSAL_EDITS = 4


def rejected_test_proposal(
    events: list[dict[str, Any]], *, roots: list[str], diff_hash: str,
) -> dict[str, Any] | None:
    """Keep the latest rolled-back test proposal through later successful repairs.

    Read only paired public receipts. No filesystem reads, inferred test oracle,
    semantic resolution, or execution credit. Source-only recovery must not erase
    an earlier proposed assertion merely because mutation admission now succeeds.
    """
    started = {}
    latest = None
    for event in events:
        payload = event["payload"]
        if event["event_type"] == "action_started" and payload.get("tool") in MUTATION_TOOLS:
            started[(payload["action_id"], payload["input_hash"])] = payload
        elif event["event_type"] == "action_finished":
            result = payload["result"]
            failure = result.get("output", {}).get("mutation_failure")
            if (result.get("tool") not in MUTATION_TOOLS or result.get("status") != "failed"
                    or not isinstance(failure, dict) or failure.get("rolled_back") is not True):
                continue
            request = started.get((result["action_id"], result["input_hash"]))
            if request is None or request["tool"] != result["tool"]:
                continue
            arguments = request["arguments"]
            edits = arguments.get("edits") if result["tool"] == "edit_files" else [arguments]
            if not isinstance(edits, list):
                continue
            selected = [edit for edit in edits if isinstance(edit, dict)
                        and isinstance(edit.get("path"), str)
                        and any(edit["path"].startswith(root + "/") for root in roots)
                        and not any(part in {"", ".", ".."} for part in edit["path"].split("/"))
                        and "\\" not in edit["path"] and ":" not in edit["path"]
                        and isinstance(edit.get("new_text"), str)
                        and (edit.get("old_text") is None
                             or isinstance(edit.get("old_text"), str))]
            if selected:
                latest = request, result, selected
    if latest is None:
        return None
    request, result, selected = latest
    remaining = MAX_TEST_PROPOSAL_CHARS
    excerpts = []
    for edit in selected[:MAX_TEST_PROPOSAL_EDITS]:
        excerpt = {"path": edit["path"][:1_000]}
        # Keep the proposed observation/assertion before spending space on its anchor.
        for field in ("new_text", "old_text"):
            value = edit.get(field)
            excerpt[field] = value[:remaining] if value is not None else None
            retained = len(excerpt[field] or "")
            remaining -= retained
            excerpt[field + "_omitted_chars"] = len(value or "") - retained
        excerpts.append(excerpt)
    return {
        "action_id": result["action_id"], "input_hash": result["input_hash"],
        "baseline_diff_hash": request.get("baseline_diff_hash"),
        "current_diff_hash": diff_hash,
        "proposal_status": "rejected_not_applied",
        "interpretation_status": "model_authored_unverified",
        "error_code": result.get("error_code"),
        "error_message": (result.get("message") or "")[:2_000],
        **{field: value[:1_500] if isinstance(value, str) else None
           for field in ("hypothesis", "expected_behavior")
           for value in [request["arguments"].get(field)]},
        "edits": excerpts, "omitted_edit_count": max(0, len(selected) - len(excerpts)),
        "interpretation": (
            "This attempt was rolled back; later edits are separate. Historical rejected "
            "test proposal, not current source or executed evidence. "
            "When correcting its construction, compare its input/caller/assertions with the "
            "replacement test and public task. Admission, another test or suite PASS does not "
            "establish that the same behavior was checked. This record imposes no test or gate."
        ),
    }
