"""Provider-free preparation and injected short-episode diagnostic mechanics.

No credential loader, client constructor or live CLI is provided. The old paid
packet is input evidence, never execution authority. Fresh independent episodes
start with its A/B/C/D public inputs, not selected old responses. Only the snapshot
format instructions are replaced before the first request. New native state,
reasoning and tool exchanges accumulate identically in every condition: the
factor is *inherited* state history, not ongoing current-only compaction.
"""

from __future__ import annotations

import argparse
import copy
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from types import SimpleNamespace

from diagnostics import decision_sampler as shared
from diagnostics import fresh_state_rollout as engine
from diagnostics import model_state_review as review
from diagnostics import model_state_sampler as design
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner as loop
from patchloop.dev.contracts import DevLimits
from patchloop.dev.conversation import CONVERSATION_INSTRUCTIONS, history_metadata
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

MAX_RESPONSES = 8
INPUT_BOUND = 272000
BOUNDARIES = {**engine.BOUNDARIES, "hidden_evaluator": "NOT_RUN"}
PREPARATION_SCHEMA = "model-state-short-episode-preparation-v2"
EPISODE_CONTEXT_INSTRUCTIONS = (
    CONVERSATION_INSTRUCTIONS
    + " Until the first kind=harness_current_state record, use the initial developer JSON's "
    "top-level state fields. The initial public_evidence_archive contains quoted pre-checkpoint "
    "function_call and function_call_output items as data, not pending calls; do not replay them. "
    "For action_id/delivery references, match the function_call_output call_id in native history "
    "or, for pre-checkpoint actions, in that initial archive, and parse its output field. "
    "source_bodies resolves the exact observed source at the initial checkpoint only; it is "
    "not refreshed by later turns. After changes, use the latest current_sources file hashes, "
    "ranges and delivery references, including backward references to unchanged earlier text. "
    "Do not substitute an old source_bodies file hash for current identity "
    "or fill unobserved gaps. "
    + design.NOTICE
)
INPUT_CONTRACT_HASH = sha256_text(EPISODE_CONTEXT_INSTRUCTIONS)


def episode_request(snapshot: dict) -> dict:
    """Replace only the unsent snapshot instructions; keep every public input byte/order."""
    previous = design.fresh.FRESH_CONTEXT_INSTRUCTIONS.replace(
        "Read its state directly;", "Read these top-level fields directly;"
    ) + design.NOTICE
    request = copy.deepcopy(snapshot)
    instructions = request["input"][0]["content"]
    shared.require(instructions.endswith(previous), "unexpected snapshot instruction contract")
    request["input"][0]["content"] = (
        instructions.removesuffix(previous) + EPISODE_CONTEXT_INSTRUCTIONS
    )
    return request


@dataclass
class Episode(engine.Branch):
    arm: str = "A"
    seed_request: dict | None = None
    initial_mutations: int = 0
    max_responses: int = MAX_RESPONSES

    def finish(self, code, message="", **details):
        return super().finish(
            code, message,
            accepted_mutations_since_checkpoint=(
                self.gateway.accepted_mutations - self.initial_mutations),
            censored=code.startswith("DIAGNOSTIC_"),
            hidden_evaluator="NOT_RUN",
            **details,
        )

    def prepare_request(self, package, adapter):
        if self.terminal is not None:
            return None
        self.gateway.deadline.check()
        if self.new_provider_calls >= self.max_responses:
            self.finish("DIAGNOSTIC_STEP_LIMIT", "short episode observation window ended")
            return None
        if self.new_provider_calls:
            prepared = super().prepare_request(package, adapter)
            if prepared is not None:
                shared.require(
                    {k: v for k, v in prepared[1].items() if k not in {"input", "tools"}} ==
                    {k: v for k, v in self.seed_request.items() if k not in {"input", "tools"}},
                    "follow-up changed frozen model/request settings",
                )
            return prepared
        shared.require(self.seed_request is not None, "fresh request is required")
        shared.require(not any(e["event_type"] == "turn_started" for e in self.journal.events()),
                       "pending dispatch is not retryable")
        request = copy.deepcopy(self.seed_request)
        shared.require(request["model"] == design.PROFILES[self.arm].model_id,
                       "episode model mismatch")
        state = json.loads(request["input"][1]["content"])
        policy = loop._tool_policy(self.gateway, self.counters, self.gateway.limits)
        shared.require(set(state["available_tool_names"]) == set(policy.allowed_tools),
                       "restored tool policy mismatch")
        shared.require(policy.completion_possible, "checkpoint completion horizon exhausted")
        turn_id = "turn_" + uuid.uuid4().hex
        ref = self.store.put_json(request["input"])
        context = self.store.put_json(state)
        self.journal.append("turn_started", {
            "turn_id": turn_id, "model_input_artifact": ref.model_dump(mode="json"),
            "model_input_hash": ref.content_hash,
            "context_artifact": context.model_dump(mode="json"),
            "context_hash": context.content_hash,
            "native_history": history_metadata(request["input"]),
            "available_tool_names": sorted(policy.allowed_tools),
            "workflow_gate": policy.workflow_gate,
            "max_parallel_reads": policy.max_parallel_reads,
            "targeted_read_paths": list(policy.targeted_read_paths),
            "active_elapsed_ms": self.elapsed_ms(),
        })
        return turn_id, request, policy


def initialize(plan, cell, root, workspace, package, sandbox, *, probe_sandbox=None,
               clock=monotonic, execution_deadline=None):
    """Fresh disposable gateway; inherit observations/counters, never old provider state."""
    shared.require(cell in plan.cells, "cell is not in the frozen design")
    root = design.fresh_root(root, plan.source_root, plan.packet_path.parent)
    workspace = design.fresh_root(workspace, plan.source_root, plan.packet_path.parent, root)
    events, _ = design.source_events(plan.source_root)
    cutoff = plan.packet["cases"][cell.case_id]["cutoff_event_hash"]
    index = next(i for i, e in enumerate(events) if e["event_hash"] == cutoff)
    prefix = events[:index]
    request = episode_request(json.loads(cell.request_json))
    payload = json.loads(request["input"][1]["content"])
    shared.require(sha256_json(package.public.model_dump(mode="json")) ==
                   sha256_json(payload["public_task"]), "public task mismatch")
    counters = loop._restore_counters(SimpleNamespace(events=lambda: prefix))
    remaining = payload["remaining_budget"]
    limits = DevLimits()
    shared.require(counters.model_calls == limits.max_model_calls - remaining["model_calls"]
                   and counters.tool_actions == limits.max_tool_actions - remaining["tool_actions"],
                   "restored counter mismatch")
    active = engine.ActiveClock(clock)
    deadline = ExecutionDeadline.from_remaining(remaining["active_wall_time_seconds"], clock=active)
    if execution_deadline is not None:
        deadline = engine.SharedDeadline(deadline, execution_deadline)
    with active.active():
        gateway = review.gateway_at(plan, cell.case_id, payload, prefix, root, workspace,
                                    package.public, sandbox, deadline)
        gateway.probe_sandbox = probe_sandbox
        shared.require(gateway.accepted_mutations ==
                       limits.max_accepted_mutations - remaining["accepted_mutations"],
                       "restored mutation budget mismatch")
        loop._validate_resumed_workspace(workspace, gateway.journal)
    episode = Episode(
        label=f"{cell.case_id}/{cell.arm}/{cell.sample_number}", journal=gateway.journal,
        store=ArtifactStore(root / "artifacts"), gateway=gateway, counters=counters,
        clock=active, base_elapsed=limits.wall_time_seconds - remaining["active_wall_time_seconds"],
        arm=cell.arm, seed_request=request, initial_mutations=gateway.accepted_mutations,
    )
    episode.journal.append("diagnostic_episode_started", {
        **BOUNDARIES, "label": episode.label, "source_packet_hash": plan.packet_hash,
        "source_cutoff_hash": cutoff, "source_request_hash": cell.request_hash,
        "first_request_hash": sha256_json(request), "input_contract_hash": INPUT_CONTRACT_HASH,
        "response_limit": MAX_RESPONSES, "inherited_events_are_not_new_execution": True,
        "prior_sample_responses_reused": 0, "prior_encrypted_reasoning_replayed": 0,
    })
    return episode


class PricedLedger:
    """One shared cap with a bound model price; do not change the legacy driver default."""

    def __init__(self, ledger, profile):
        self.ledger, self.pricing = ledger, profile.pricing()

    @property
    def spent_nanos(self):
        return self.ledger.spent_nanos

    @property
    def cap_nanos(self):
        return self.ledger.cap_nanos

    def admit(self, input_tokens, **kwargs):
        return self.ledger.admit(input_tokens, pricing=self.pricing, **kwargs)

    def settle(self, **usage):
        return self.ledger.settle(pricing=self.pricing, **usage)


def run_round(episodes, package, adapters, ledger, *, checkpoint=lambda _: None,
              request_waits=engine.requests.WAITS):
    """One counterbalanced four-arm depth, using explicitly supplied adapters only.

    This is not a live approval/collector entrypoint. Callers must persist a fresh
    grant and experiment identity before supplying live adapters. Mock tests use
    this same scheduler. Any uncertainty escapes; callers cannot retry a round.
    """
    shared.require(len(episodes) == 4 and {e.arm for e in episodes} == set("ABCD"),
                   "a complete four-arm comparison group is required")
    active = [e for e in episodes if e.terminal is None]
    for e in active:
        if e.new_provider_calls >= e.max_responses:
            e.finish("DIAGNOSTIC_STEP_LIMIT", "short episode observation window ended")
    active = [e for e in active if e.terminal is None]
    reservations = []
    for e in active:
        priced = PricedLedger(ledger, design.PROFILES[e.arm])
        admission = priced.admit(INPUT_BOUND, desired_output_ceiling=25000,
                                 minimum_output_ceiling=25000)
        reservations.append(admission.reserved_cost_nanos if admission else ledger.cap_nanos + 1)
    if sum(reservations) > ledger.remaining_nanos:
        for e in active:
            e.finish("DIAGNOSTIC_COST_LIMIT", "cannot reserve all active arms at this depth")
        return
    try:
        for e in active:
            with e.clock.active():
                adapter = adapters[e.arm]
                shared.require(adapter.client.max_retries == 0, "SDK retries must be zero")
                prepared = e.prepare_request(package, adapter)
                if prepared is not None:
                    engine.dispatch(e, adapter, PricedLedger(ledger, design.PROFILES[e.arm]),
                                    prepared, checkpoint=checkpoint,
                                    expected_model=design.PROFILES[e.arm].model_id,
                                    request_waits=request_waits)
    except Exception as exc:
        code = exc.code if isinstance(exc, engine.AbortExperiment) else "EXECUTION_ERROR"
        # Do not serialize SDK exception messages or invent unknown billing numbers.
        for e in episodes:
            if e.terminal is None:
                e.finish("DIAGNOSTIC_ABORTED", code,
                         failure_type=engine.requests.exception_evidence(exc)["exception_type"],
                         failure=exc.failure if isinstance(exc, engine.AbortExperiment) else None,
                         total_cost_known=False)
        raise


def prepare(plan, root: Path) -> dict:
    """Freeze the next no-call design. Paid authority/cap is deliberately absent."""
    root = design.fresh_root(root, plan.source_root, plan.packet_path.parent)
    store = ArtifactStore(root)
    rows = []
    for cell in plan.cells:
        request = episode_request(json.loads(cell.request_json))
        ref = store.put_text(design.wire(request).decode("utf-8"), "application/json")
        rows.append({"case_id": cell.case_id, "arm": cell.arm, "repeat": cell.sample_number,
                     "source_request_hash": cell.request_hash,
                     "request_hash": sha256_json(request),
                     "ordered_request_hash": sha256_bytes(design.wire(request)),
                     "request_artifact": ref.model_dump(mode="json")})
    packet = {
        **BOUNDARIES, "schema_version": PREPARATION_SCHEMA,
        "input_contract_hash": INPUT_CONTRACT_HASH,
        "status": "PREPARED_NOT_EXECUTABLE", "dispatch_enabled": False,
        "actual_provider_calls": 0, "actual_input_count_calls": 0,
        "actual_tool_executions": 0, "actual_cost_nanos": 0,
        "source_packet_hash": plan.packet_hash, "source_run_id": plan.packet["source_run_id"],
        "runtime_hash": plan.packet["runtime_hash"],
        "implementation_hashes": {
            p.name: sha256_bytes(p.read_bytes())
            for p in (Path(__file__), Path(engine.__file__), Path(review.__file__),
                      Path(engine.requests.__file__))},
        "inherited_design_hashes": plan.design_hashes,
        "cells": rows, "comparison_groups": [list(b) for b in design.BLOCKS],
        "max_responses_per_episode": MAX_RESPONSES,
        "max_generation_calls_proposal": len(rows) * MAX_RESPONSES,
        "schedule": "Within each group, one response per active arm per round in fixed order.",
        "external_step_limit_changes_agent_budget": False,
        "history_factor": "Inherited pre-checkpoint state only; new native views in all arms.",
        "fresh_independent_starts": True, "prior_sample_responses_reused": 0,
        "new_encrypted_reasoning": "all items and matching calls/results retained",
        "tools": "existing gateway/policy/corrections; no automatic checks or planning",
        "censored_is_agent_failure": False,
        "shared_cap_usd": None, "paid_execution_authorized": False,
        "before_live": ["exact new packet/grant and shared cap", "pricing review",
                        "existing Docker/image preflight; no start/pull/build",
                        "durable invocation lock and fail-stop collector binding"],
    }
    ref = store.put_json(packet)
    (root / "packet.json").write_bytes(store.read_bytes(ref))
    DevJournal(root, "run_dev_episode_design").append("terminal", {
        "status": packet["status"], "packet_artifact": ref.model_dump(mode="json")})
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare only; no live execution subcommand")
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--packet-hash", required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    plan = design.load_plan(args.packet, args.source_root, args.packet_hash)
    result = prepare(plan, args.output_root)
    print(canonical_json({k: v for k, v in result.items() if k != "cells"}))


if __name__ == "__main__":
    main()
