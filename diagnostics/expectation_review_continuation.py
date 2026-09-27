"""Offline matched continuation retaining advice removal in both arms."""
from __future__ import annotations

import copy
import json
from unittest.mock import patch

from diagnostics import checkpoint_continuation as continuation
from diagnostics import completion_advice_checkpoint as advice
from diagnostics import expectation_review_checkpoint as review
from diagnostics.decision_sampler import require
from patchloop.contracts import Artifact
from patchloop.dev import native_compaction, runner, segments
from patchloop.dev.conversation import history_metadata
from patchloop.util import sha256_json


def rehearse(branch, client):
    require(type(client) is continuation.ScriptedClient, "finite offline client required")
    require(branch.packet["schema"] == review.SCHEMA, "review checkpoint required")
    guidance_original = runner._completion_guidance
    prepare_original = native_compaction.prepared_input
    treatment = review.FIELD in json.loads(branch.selected["input"][-1]["content"])["state"]

    def guidance(snapshot, policy):
        raw = guidance_original(snapshot, policy)
        request = {"tools": [{"name": t} for t in policy.allowed_tools], "input": [
            {"content": json.dumps({"state": {"completion_guidance": raw}})}]}
        return json.loads(advice.project(request)["input"][-1]["content"])["state"][
            "completion_guidance"]

    def prepare(journal, store, turn, request, transition):
        boundary, bundle = prepare_original(journal, store, turn, request, transition)
        dispatched = any(e["event_type"] == "provider_call_started"
                         for e in journal.events()[branch.inherited_events:])
        view = json.loads(bundle["request"]["input"][-1]["content"])
        if not treatment or dispatched or review.FIELD in view["state"]:
            return boundary, bundle
        selected = review.project(bundle["request"])
        updated = copy.deepcopy(bundle)
        updated["request"] = selected
        t = updated["turn"]
        canonical = json.loads(store.read_bytes(Artifact.model_validate(t["context_artifact"])))
        canonical[review.FIELD] = review.CUE
        t["context_artifact"] = native_compaction.put_json(store, canonical)
        t["context_hash"] = t["context_artifact"]["content_hash"]
        t["model_input_artifact"] = native_compaction.put_json(store, selected["input"])
        t["model_input_hash"] = t["model_input_artifact"]["content_hash"]
        t["native_history"] = history_metadata(selected["input"], context_policy="segmented-v1")
        t["context_request_sizes"] = segments.request_sizes(selected)
        require(not segments.size_reasons(t["context_request_sizes"]), "review exceeds byte limits")
        boundary = {**boundary, "artifact": native_compaction.put_json(store, updated),
                    "request_hash": sha256_json(selected)}
        journal.append("model_input_prepared", boundary)
        return boundary, updated

    with patch.object(runner, "_completion_guidance", guidance), patch.object(
        native_compaction, "prepared_input", prepare
    ):
        return continuation.rehearse(branch, client)
