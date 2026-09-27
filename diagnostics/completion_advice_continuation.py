"""Scoped, offline-only rehearsal of advice removal before every input count."""
from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from unittest.mock import patch

from diagnostics import checkpoint_continuation as continuation
from diagnostics.completion_advice_checkpoint import project
from diagnostics.decision_sampler import require
from patchloop.contracts import Artifact
from patchloop.dev import native_compaction, segments
from patchloop.dev.conversation import history_metadata
from patchloop.util import sha256_json


@contextmanager
def advice_inputs(branch):
    """Rebind frozen and newly prepared inputs, including count-driven segments."""
    original = native_compaction.prepared_input

    def prepare(journal, store, turn, request, transition):
        require(journal is branch.journal, "unexpected diagnostic journal")
        boundary, bundle = original(journal, store, turn, request, transition)
        markers = [e["payload"] for e in journal.events()[branch.inherited_events:]
                   if e["event_type"] == "diagnostic_advice_removed"]
        if any(m["selected_request_hash"] == boundary["request_hash"] for m in markers):
            return boundary, bundle
        # The saved first boundary is authoritative, including its frozen elapsed time.
        baseline = bundle["request"]
        selected = project(baseline)
        sizes = segments.request_sizes(selected)
        require(not segments.size_reasons(sizes), "advice input exceeds byte limits")
        updated = copy.deepcopy(bundle)
        updated["request"] = selected
        prepared_turn = updated["turn"]
        canonical = json.loads(store.read_bytes(
            Artifact.model_validate(prepared_turn["context_artifact"])))
        canonical["completion_guidance"] = json.loads(
            selected["input"][-1]["content"])["state"]["completion_guidance"]
        prepared_turn["context_artifact"] = native_compaction.put_json(store, canonical)
        prepared_turn["context_hash"] = prepared_turn["context_artifact"]["content_hash"]
        prepared_turn["model_input_artifact"] = native_compaction.put_json(store, selected["input"])
        prepared_turn["model_input_hash"] = prepared_turn["model_input_artifact"]["content_hash"]
        prepared_turn["native_history"] = history_metadata(
            selected["input"], context_policy="segmented-v1")
        prepared_turn["context_request_sizes"] = sizes
        replacement = {**boundary, "artifact": native_compaction.put_json(store, updated),
                       "request_hash": sha256_json(selected)}
        journal.append("model_input_prepared", replacement)
        journal.append("diagnostic_advice_removed", {
            "boundary_id": boundary["boundary_id"],
            "baseline_request": native_compaction.put_json(store, baseline),
            "selected_request_hash": replacement["request_hash"],
        })
        return replacement, updated

    with patch.object(native_compaction, "prepared_input", prepare):
        yield


def rehearse(branch, client):
    """Finite scripted SDK only; no live dispatch or normal resume integration."""
    require(type(client) is continuation.ScriptedClient, "finite offline client required")
    require(branch.packet["schema"] == "post-edit-budget-checkpoint-v1"
            and "verification_scope_cue" not in branch.packet, "unhinted budget fork required")
    branch.journal.append("diagnostic_advice_rehearsal_configured", {
        "official": False, "live_model_calls": 0,
        "unsupported_stage_policy": "stop before count; no baseline fallback",
    })
    with advice_inputs(branch):
        return continuation.rehearse(branch, client)
