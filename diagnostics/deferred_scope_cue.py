"""Deliver the frozen scope cue at the first submission-eligible decision only."""
from __future__ import annotations

import copy
import json

from diagnostics.decision_sampler import require
from diagnostics.post_edit_budget_checkpoint import SCOPE_CUE, SCOPE_FIELD
from patchloop.contracts import Artifact
from patchloop.dev import native_compaction, segments
from patchloop.dev.conversation import history_metadata
from patchloop.util import canonical_json, sha256_json


def prepare_at_readiness(original_prepare, branch, turn, request, transition):
    journal, store = branch.journal, branch.store
    events = journal.events()[branch.inherited_events:]
    delivered_turns = {e["payload"]["boundary_id"] for e in events
                       if e["event_type"] == "diagnostic_scope_cue_prepared"}
    dispatched = any(e["event_type"] == "provider_call_started"
                     and e["payload"]["turn_id"] in delivered_turns for e in events)
    state = json.loads(request["input"][-1]["content"])["state"]
    ready = state["completion_guidance"]["submission_ready"]
    if dispatched or not ready:
        return original_prepare(journal, store, turn, request, transition)
    require(branch.packet.get(SCOPE_FIELD) == SCOPE_CUE, "frozen scope cue required")
    selected = copy.deepcopy(request)
    view = json.loads(selected["input"][-1]["content"])
    require(SCOPE_FIELD not in view["state"], "scope cue already present")
    view["state"][SCOPE_FIELD] = SCOPE_CUE
    selected["input"][-1]["content"] = canonical_json(view)
    sizes = segments.request_sizes(selected)
    require(not segments.size_reasons(sizes), "cued request exceeds byte limits")
    updated = copy.deepcopy(turn)
    canonical = json.loads(store.read_bytes(Artifact.model_validate(turn["context_artifact"])))
    canonical[SCOPE_FIELD] = SCOPE_CUE
    updated["context_artifact"] = native_compaction.put_json(store, canonical)
    updated["context_hash"] = updated["context_artifact"]["content_hash"]
    updated["model_input_artifact"] = native_compaction.put_json(store, selected["input"])
    updated["model_input_hash"] = updated["model_input_artifact"]["content_hash"]
    updated["native_history"] = history_metadata(selected["input"], context_policy="segmented-v1")
    updated["context_request_sizes"] = sizes
    boundary, bundle = original_prepare(journal, store, updated, selected, transition)
    require(json.loads(bundle["request"]["input"][-1]["content"])["state"].get(SCOPE_FIELD)
            == SCOPE_CUE, "prepared request lost scope cue")
    if boundary["boundary_id"] not in delivered_turns:
        require(bundle["request"] == selected, "new cue boundary differs from projection")
        journal.append("diagnostic_scope_cue_prepared", {
            "boundary_id": boundary["boundary_id"], "timing": "ready-to-submit",
            "baseline_request": native_compaction.put_json(store, request),
            "selected_request_hash": sha256_json(selected), "field": SCOPE_FIELD,
        })
    # Count-driven segmentation may prepare another input before any dispatch.
    # Keep applying there; a real dispatch, not preparation/counting, consumes the cue.
    return boundary, bundle
