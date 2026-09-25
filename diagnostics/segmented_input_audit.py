"""Verify saved segmented input against its projected public state, without execution."""
from __future__ import annotations

import copy
import json
from types import SimpleNamespace

from patchloop.contracts import Artifact
from patchloop.dev import runner, segments, working_plan
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.util import sha256_json


def verify_turn(event, events, store, *, actual_input=None):
    """Rebuild the display transformation at this boundary, using public records only.

    Canonical gateway state precedes the segment event and native deduplication.
    Comparing that raw object to the delivered plan/notes would reject valid input.
    This checks delivery consistency, not semantic completeness or model uptake.
    """
    turn = event["payload"]
    items = runner._load_active_model_input(turn, store, context_policy=segments.POLICY)
    if actual_input is not None and items != actual_input:
        raise ValueError("actual input differs from saved native input")
    canonical = json.loads(store.read_bytes(Artifact.model_validate(turn["context_artifact"])))
    prefix = [row for row in events if row["sequence"] < event["sequence"]]
    journal = SimpleNamespace(events=lambda: prefix)
    latest = DevJournal.latest_tool_batch_results(journal)
    binding = turn["context_segment"]["binding"]
    expected = copy.deepcopy(canonical)
    policy = expected.get("working_plan", {}).get("policy", "none")
    if policy != "none":
        expected["working_plan"] = working_plan.project(
            prefix, diff_hash=expected["current_diff"]["patch_hash"],
            gate=expected["workflow_gate"], policy=policy)
    expected["segment_handoff"] = {
        "segment_id": binding["segment_id"], "reason": binding["reason"],
        "review_requested": segments.is_fresh(journal, binding),
        "previous_reasoning_available": False,
        "interpretation": "public execution facts and unverified model-authored notes/plan",
    }
    expected = runner._segment_current_view(expected, items[3:], latest)
    delivered = reconstruct_state(items, context_policy=segments.POLICY)
    if delivered != expected:
        changed = sorted(k for k in set(delivered) | set(expected)
                         if delivered.get(k) != expected.get(k))
        raise ValueError("projected public state differs: " + ", ".join(changed))
    for key in ("public_task", "current_diff", "visible_check_status"):
        if delivered[key] != canonical[key]:
            raise ValueError("public authority differs: " + key)
    return {"turn_id": turn["turn_id"], "input_hash": sha256_json(items),
            "projected_state_hash": sha256_json(delivered),
            "plan_matches_before_projection": canonical.get("working_plan") ==
            delivered.get("working_plan"), "verified": True}


def initial_signature(wire):
    """Compare fresh starts, excluding model and measured/derived run identities."""
    state = reconstruct_state(wire["input"], context_policy=segments.POLICY)
    if (state["current_diff"]["patch"] or state["working_plan"]["plan"] is not None
            or state["working_notes"]["findings"]
            or any(row["status"] != "NOT_RUN" for row in state["visible_check_status"])
            or "candidate_reconsideration" in state):
        raise ValueError("fresh solve contains previous candidate or memory")
    state = copy.deepcopy(state)
    state["remaining_budget"].pop("active_wall_time_seconds")
    # The hash binds canonical state, including the measured preparation time.
    # Its validity is checked through the saved input binding before pair comparison.
    state["segment_handoff"].pop("segment_id")
    return {"state": state, "system": wire["input"][0],
            "flags_and_tools": {k: v for k, v in wire.items() if k not in {"input", "model"}}}
