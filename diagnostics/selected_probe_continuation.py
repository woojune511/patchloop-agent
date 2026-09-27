"""Replay one already-paid response, execute its probe, freeze before another count."""
from __future__ import annotations

import copy
import json
from contextlib import suppress
from pathlib import Path
from unittest.mock import patch

from diagnostics import checkpoint_continuation as restore
from diagnostics import closure_policy_sampler as sampler
from diagnostics import expectation_review_continuation as guidance
from diagnostics.decision_sampler import require
from patchloop.agent.model import (
    EncryptedReasoningContinuationItem,
    FunctionCallContinuationRef,
    ModelTurn,
    OpenAIResponsesAdapter,
    RequestedTool,
)
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import native_compaction, runner, segments
from patchloop.dev.contracts import ProviderContinuationRef
from patchloop.dev.conversation import history_metadata
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json, sha256_bytes, sha256_json


class BoundaryCaptured(BaseException):
    """Intentional stop before input counting; not a provider failure or terminal."""


def saved_response(root, plan):
    envelope = json.loads((root / "envelope.json").read_bytes())
    require(envelope["packet_hash"] == plan.packet_hash
            and envelope["provider_free"] is False, "wrong live collection")
    result = json.loads((root / "result.json").read_bytes())
    require(result["terminal"] == "SAMPLES_COLLECTED" and result["total_cost_known"],
            "collection is not settled")
    journal = DevJournal(root, envelope["run_id"])
    events = journal.events()
    selected = [e["payload"] for e in events if e["event_type"] == "sample_recorded"
                and e["payload"]["arm"] == "B" and e["payload"]["sample_number"] == 2]
    require(len(selected) == 1, "unique B2 sample required")
    sample = selected[0]
    usage = next(e["payload"] for e in events if e["event_type"] == "provider_call_finished"
                 and e["payload"]["sample_id"] == sample["sample_id"])
    cell = next(c for c in plan.cells if c.arm == "B" and c.sample_number == 2)
    require(usage["billing_known"] and usage["request_hash"] == cell.request_hash
            and usage["response_status"] == "completed", "response identity or billing changed")
    store = ArtifactStore(root)
    public = json.loads(store.read_bytes(Artifact.model_validate(sample["public_artifact"])))
    calls = [RequestedTool(**c) for c in public["tool_calls"]]
    require(len(calls) == 1 and calls[0].name == "run_probe", "selected action is not one probe")
    continuation = runner._load_provider_continuation(
        store, ProviderContinuationRef.model_validate(sample["continuation_ref"]))
    items = tuple(EncryptedReasoningContinuationItem(
        id=x.id, encrypted_content=x.encrypted_content, status=x.status)
        if x.type == "reasoning" else FunctionCallContinuationRef(action_id=x.action_id)
        for x in continuation.output_order)
    turn = ModelTurn(tool_calls=calls, provider_continuation=items,
                     requested_input_tokens=usage["input_tokens"],
                     **{k: usage[k] for k in (
                         "input_tokens", "cached_input_tokens", "output_tokens",
                         "reasoning_output_tokens", "response_id", "response_model",
                         "response_status", "output_shape_hash")},
                     output_item_types=tuple(usage["output_item_types"]),
                     output_item_count=len(items),
                     non_tool_output_item_count=len(items) - len(calls))
    runner._validate_continuation_action_order(runner._turn_from_openai(turn).provider_continuation,
                                              runner._turn_from_openai(turn).tool_calls)
    return cell, turn, {"source_journal_hash": sha256_bytes(journal.path.read_bytes()),
                        "sample": sample, "usage": usage}


def prepare(plan_path, plan_hash, live_root, output):
    plan = sampler.load_plan(plan_path, plan_hash)
    cell, saved, binding = saved_response(live_root, plan)
    extension_path = Path("C:/pt/analyses/time-extension-checkpoint-20260928-v1/packet.json")
    branch = restore.restore(extension_path, sha256_bytes(extension_path.read_bytes()), output, "A",
                             review_new_cap_nanos=3_000_000_000)
    selected = json.loads(cell.request_json)
    expected = copy.deepcopy(branch.selected)
    expected["input"][0]["content"] = expected["input"][0]["content"].replace(
        sampler.REMOVED, "", 1)
    require(expected == selected, "restored checkpoint does not match B2 request")
    branch.selected = selected
    prepared = next(e["payload"] for e in reversed(branch.journal.events())
                    if e["event_type"] == "model_input_prepared")
    bundle = json.loads(branch.store.read_bytes(Artifact.model_validate(prepared["artifact"])))
    bundle["request"] = selected
    bundle["turn"]["model_input_artifact"] = native_compaction.put_json(
        branch.store, selected["input"])
    bundle["turn"]["model_input_hash"] = bundle["turn"]["model_input_artifact"]["content_hash"]
    bundle["turn"]["native_history"] = history_metadata(
        selected["input"], context_policy="segmented-v1")
    bundle["turn"]["context_request_sizes"] = segments.request_sizes(selected)
    branch.journal.append("model_input_prepared", {
        **prepared, "artifact": native_compaction.put_json(branch.store, bundle),
        "request_hash": cell.request_hash})
    branch.journal.append("diagnostic_saved_response_replay", {
        "official": False, "source": binding, "new_provider_calls": 0,
        "new_billed_cost_nanos": 0, "replayed_usage_is_historical": True,
        "budget_is_bookkeeping_not_authorization": True,
        "following_policy": "ordinary runtime; current-input ablation ends after saved response"})
    counted, dispatched, captured = [], [], []

    class ReplayAdapter(OpenAIResponsesAdapter):
        def __init__(self, config, **kwargs):
            self.config = config

        def count_input_tokens_v2(self, request, **kwargs):
            require(not counted and request == selected, "unexpected replay count")
            counted.append(True)
            return saved.input_tokens

        def execute_request(self, request, **kwargs):
            require(len(counted) == 1 and not dispatched and request == selected,
                    "unexpected replay dispatch")
            dispatched.append(True)
            return saved

    original_prepare = native_compaction.prepared_input
    original_binding = segments.validate_input_binding

    def validate_overlay(items, binding, store):
        # The sampler changed only the system text, not the inherited segment seed.
        # Verify that exact overlay against its original seed; all other inputs use
        # the unmodified validator. Do not rewrite the source seed or segment ID.
        if items == selected["input"]:
            normalized = copy.deepcopy(items)
            normalized[0] = copy.deepcopy(branch.original["input"][0])
            return original_binding(normalized, binding, store)
        return original_binding(items, binding, store)

    def capture(journal, store, turn, request, transition):
        boundary, next_bundle = original_prepare(journal, store, turn, request, transition)
        if dispatched:
            captured.append((boundary, next_bundle))
            raise BoundaryCaptured()
        return boundary, next_bundle

    def no_network(*args, **kwargs):
        raise RuntimeError("provider network forbidden during replay preparation")

    with (restore.inherited_reads(branch), guidance.inputs(branch),
          patch.object(segments, "validate_input_binding", validate_overlay),
          patch.object(native_compaction, "prepared_input", capture),
          patch.object(runner, "OpenAIResponsesAdapter", ReplayAdapter),
          patch.object(runner, "load_exact_openai_api_key", lambda _: "replay-no-credential"),
          patch("socket.socket.connect", no_network), branch.journal.execution_lock(),
          suppress(BoundaryCaptured)):
        runner._run_one_locked(
            request=branch.request, task_dir=branch.task_dir, package=branch.package,
            state_root=branch.root, pricing=branch.pricing, cost_ledger=branch.ledger,
            runtime_hash=branch.envelope.runtime_hash, model_hash=branch.envelope.model_hash,
            run_id=branch.journal.run_id, journal=branch.journal, envelope=branch.envelope,
            resuming=True)
    require(len(captured) == 1 and len(dispatched) == 1, "next boundary was not captured")
    require(branch.journal.unresolved_provider_call() is None
            and branch.journal.unresolved_input_count() is None
            and branch.journal.terminal() is None, "boundary has pending operation or terminal")
    boundary, next_bundle = captured[0]
    receipt = {"official": False, "new_provider_calls": 0, "new_billed_cost_nanos": 0,
               "historical_response_replays": 1, "paid_execution_authorized": False,
               "boundary": boundary, "next_request_hash": sha256_json(next_bundle["request"]),
               "source_binding": binding, "branch_root": str(output),
               "followup_collection": "NOT_IMPLEMENTED", "task_acceptance": "NOT_RUN"}
    branch.journal.append("diagnostic_probe_boundary_captured", receipt)
    (output / "prepared-boundary.json").write_text(canonical_json(receipt), encoding="utf-8")
    return receipt
