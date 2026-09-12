"""Prepare and mock a bounded continuation of one collected compacted decision.

No credential loader, client constructor, Docker constructor or live CLI exists here.
The old run is read-only checkpoint evidence, not a native resume or a new approval.
An eventual collector must supply admitted backends, a client and a shared cost cap.
"""

from __future__ import annotations

import argparse
import copy
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from time import monotonic
from types import SimpleNamespace

from diagnostics import compaction_followup as followup
from diagnostics import compaction_replay as compact
from diagnostics import compaction_snapshot as snapshots
from diagnostics import count_replay as original
from diagnostics import fresh_state_rollout as engine
from diagnostics import model_state_review as review
from diagnostics.decision_sampler import read_source_artifact, require
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import runner as loop
from patchloop.dev.contracts import DevLimits, DevModelTurn, RequestedTool, dev_tool_surface_hash
from patchloop.dev.conversation import assemble_model_input
from patchloop.dev.native_sources import project_mutation_result, reference_native_sources
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas, validate_tool_batch
from patchloop.errors import RecoveryError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import runtime_content_hash
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json

KIND = "compaction-short-episode-v1"
MAX_NEW_RESPONSES = 8
BOUNDARIES = {**engine.BOUNDARIES, "hidden_evaluator": "NOT_RUN"}
INHERIT = {
    *engine.KINDS,
    "model_call_finished",
    "repair_recheck_started",
    "repair_recheck_finished",
}


@dataclass
class Plan:
    identity: dict
    source_root: Path
    collection_root: Path
    prefix: list[dict]
    envelope: dict
    request: dict = field(repr=False)
    original_input: list[dict] = field(repr=False)
    state: dict = field(repr=False)
    seed: DevModelTurn = field(repr=False)
    package: object = field(repr=False)


def implementation():
    return {
        "runtime_hash": runtime_content_hash(),
        "tool_surface_hash": dev_tool_surface_hash(),
        "modules": {
            p.name: sha256_bytes(p.read_bytes())
            for p in (
                Path(__file__),
                Path(snapshots.__file__),
                Path(followup.__file__),
                Path(engine.__file__),
                Path(review.__file__),
                Path(engine.requests.__file__),
            )
        },
    }


def load_source(collection_root: Path, result_hash: str, task_dir: Path) -> Plan:
    """Verify the seed and healthy cutoff; never import the later failed response."""
    collection_root = collection_root.resolve()
    raw = (collection_root / "result.json").read_bytes()
    require(sha256_bytes(raw) == result_hash, "seed result hash mismatch")
    result = followup.inspect_result(collection_root)
    binding = json.loads((collection_root / "execution.json").read_bytes())
    require(
        canonical_json(result).encode() == raw
        and result["result"] == "RESPONSE_COLLECTED"
        and result["failure"] is None
        and result["cleanup"]["status"] == "CLOSED"
        and result["count_attempts"] == result["generation_attempts"] == 1
        and result["execution_plan_hash"] == binding["execution_plan_hash"],
        "seed is not a complete bound response",
    )
    bound = binding["plan"]
    require(
        bound["runtime_hash"] == runtime_content_hash()
        and bound["implementation"]
        == {
            p.name: sha256_bytes(p.read_bytes())
            for p in (
                Path(followup.__file__),
                Path(followup.prices.__file__),
                Path(followup.transport.__file__),
            )
        },
        "seed implementation mismatch",
    )
    source_identity, request, _ = followup.source(
        Path(bound["source"]["collection_root"]), bound["source"]["result_hash"]
    )
    require(source_identity == bound["source"], "seed input/source binding mismatch")
    public = json.loads(
        read_source_artifact(collection_root, result["assessment"]["public_artifact"])
    )
    require(
        public["response_status"] == "completed"
        and public["error_code"] is None
        and public["tool_batch_contract"] == "PASS_SHAPE_ONLY"
        and public["continuation_ref"] == result["assessment"]["continuation_ref"],
        "seed is not a completed public tool decision",
    )
    seed = DevModelTurn(
        tool_calls=[RequestedTool.model_validate(c) for c in public["tool_calls"]],
        response_status="completed",
        output_item_types=public["output_item_types"],
        continuation_ref=public["continuation_ref"],
    )
    continuation = loop._load_provider_continuation(
        engine.readonly_store(collection_root / "artifacts"), seed.continuation_ref
    )
    loop._validate_continuation_action_order(continuation, seed.tool_calls)
    state = json.loads(request["input"][-1]["content"])["state"]
    validate_tool_batch(seed.tool_calls, allowed_tools=set(state["available_tool_names"]))
    require(
        len(seed.tool_calls) == 1
        and seed.tool_calls[0].name == "run_check"
        and seed.tool_calls[0].arguments == {"check_id": state["remaining_visible_check_ids"][0]},
        "expected the collected remaining-check proposal",
    )
    source_root = Path(source_identity["source_state_root"])
    events, envelope = original.source_events(source_root)
    _, cutoff = original.cutoff_request(events, envelope, source_root, original.TURNS[0])
    started = next(
        e
        for e in events
        if e["event_type"] == "turn_started" and e["payload"]["turn_id"] == cutoff["turn_id"]
    )
    prefix = events[: started["sequence"] - 1]
    original_input = json.loads(
        read_source_artifact(source_root, started["payload"]["model_input_artifact"])
    )
    package = load_task_package(task_dir)
    require(
        package.public.model_dump(mode="json") == state["public_task"]
        and package.task_content_hash == envelope["task_content_hash"],
        "task content mismatch",
    )
    require(
        (source_root / "workspaces" / envelope["run_id"] / "repo").is_dir(),
        "source repository unavailable",
    )
    seed_journal = DevJournal(collection_root, binding["run_id"])
    seed_events = seed_journal.events()
    elapsed = (
        datetime.fromisoformat(seed_events[-1]["timestamp"])
        - datetime.fromisoformat(seed_events[0]["timestamp"])
    ).total_seconds()
    require(
        elapsed >= 0 and result["usage"]["input_tokens"] == result["input_tokens"],
        "seed usage/time mismatch",
    )
    identity = {
        "collection_root": str(collection_root),
        "result_hash": result_hash,
        "collection_journal_hash": sha256_bytes(seed_journal.path.read_bytes()),
        "execution_hash": sha256_bytes((collection_root / "execution.json").read_bytes()),
        "source_run_id": envelope["run_id"],
        "source_root": str(source_root),
        "source_prefix_last_hash": prefix[-1]["event_hash"],
        "cutoff_event_hash": started["event_hash"],
        "original_source_hashes": original.SOURCE_HASHES,
        "source_runtime_hash": envelope["runtime_hash"],
        "task_dir": str(task_dir.resolve()),
        "task_content_hash": package.task_content_hash,
        "credential_file_path_hash": envelope["credential_file_path_hash"],
        "request_hash": sha256_json(request),
        "original_input_hash": sha256_json(original_input),
        "seed_turn_hash": sha256_json(seed.model_dump(mode="json")),
        "seed_active_seconds": elapsed,
        "seed_prior_usage": result["usage"],
        "seed_prior_generation_cost_nanos": result["generation_model_rate_cost_nanos"],
        "repair_recheck": envelope.get("repair_recheck", False),
        "evaluator_image_digest": envelope["evaluator_image_digest"],
        "probe_image_digest": envelope.get("probe_image_digest"),
        "probe_profile_hash": envelope.get("probe_profile_hash"),
    }
    return Plan(
        identity,
        source_root,
        collection_root,
        prefix,
        envelope,
        request,
        original_input,
        state,
        seed,
        package,
    )


def proposal(plan: Plan, max_new_responses: int = MAX_NEW_RESPONSES, *,
             context_policy: str = snapshots.APPEND) -> dict:
    require(context_policy in snapshots.POLICIES, "unknown compaction context policy")
    remaining = plan.state["remaining_budget"]
    require(
        type(max_new_responses) is int and 1 <= max_new_responses <= remaining["model_calls"] - 1,
        "new response observation bound exceeds inherited budget",
    )
    return {
        **BOUNDARIES,
        "kind": KIND,
        "source": plan.identity,
        "implementation": implementation(),
        "status": "PREPARED_NOT_EXECUTABLE",
        "paid_execution_authorized": False,
        "seed_proposals_reused": 1,
        "seed_generation_repeated": False,
        "max_new_responses": max_new_responses,
        "max_new_input_counts": max_new_responses,
        "initial_tool_batch": [c.model_dump(mode="json") for c in plan.seed.tool_calls],
        "remaining_budget_before_seed_response": remaining,
        "seed_response_consumes_inherited_model_calls": 1,
        "seed_response_active_seconds": plan.identity["seed_active_seconds"],
        "global_limits": plan.envelope["limits"],
        "step_limit_changes_tool_policy": False,
        "step_limit_is_censoring": True,
        "count_billing": "UNCONFIRMED_SEPARATE_ACKNOWLEDGEMENT_REQUIRED",
        "generation_cap_usd": None,
        "total_invoice_cost_usd": None,
        "input_limit": 272000,
        "output_ceiling": 25000,
        "new_compactions": 0,
        "continuation_reset": False,
        "waits": engine.requests.WAITS.contract(),
        "automatic_retry_or_resume": False,
        "current_state": "native projection, selected observed sources and exact public reentry",
        "context_policy": context_policy,
        "before_live": [
            "exact new grant and positive generation cap with count billing disclosure",
            "official price review and JIT unchanged-25k output reservation",
            "bound collector lifetime lock, client cleanup and partial-result receipts",
            "existing Docker/image/probe identity preflight; no start/pull/build",
        ],
    }


def prepare(
    collection_root: Path,
    result_hash: str,
    task_dir: Path,
    output: Path,
    max_new_responses: int = MAX_NEW_RESPONSES,
    context_policy: str = snapshots.APPEND,
) -> dict:
    plan = load_source(collection_root, result_hash, task_dir)
    output = compact.new_external_root(output, collection_root, plan.source_root)
    packet = proposal(plan, max_new_responses, context_policy=context_policy)
    store = ArtifactStore(output)
    store.write_text_immutable(output / "packet.json", canonical_json(packet))
    digest = sha256_json(packet)
    store.write_text_immutable(output / "packet.sha256", digest + "\n")
    return {
        "packet_hash": digest,
        "max_new_responses": max_new_responses,
        "context_policy": context_policy,
        "status": packet["status"],
        "api_requests": 0,
        "tool_executions": 0,
        "official": False,
    }


def verify(packet_root: Path, packet_hash: str) -> tuple[Plan, dict]:
    packet = json.loads((packet_root / "packet.json").read_bytes())
    require(sha256_json(packet) == packet_hash, "packet hash mismatch")
    source = packet["source"]
    plan = load_source(
        Path(source["collection_root"]), source["result_hash"], Path(source["task_dir"])
    )
    require(packet == proposal(plan, packet["max_new_responses"],
                               context_policy=packet.get("context_policy", snapshots.APPEND)),
            "episode contract changed")
    return plan, packet


@dataclass
class Episode(engine.Branch):
    seed: DevModelTurn | None = None
    seed_request: dict = field(default_factory=dict, repr=False)
    original_history: list[dict] = field(default_factory=list, repr=False)
    initial_mutations: int = 0
    repair_recheck: bool = False
    context_policy: str = snapshots.APPEND

    def finish(self, code, message="", **details):
        if self.terminal is None:
            # Read-only provenance is allowed after expiry, never another task action.
            summary, metadata_error = None, None
            try:
                summary = WorkspaceManager.diff_summary(
                    self.gateway.workspace, deadline=ExecutionDeadline.from_remaining(5)
                )
            except Exception as exc:
                metadata_error = engine.requests.exception_evidence(exc)
            digest = summary.patch_hash if summary is not None else None
            self.terminal = {
                **BOUNDARIES,
                "branch": self.label,
                "context_policy": self.context_policy,
                "terminal": code,
                "message": message,
                "provider_calls": self.new_provider_calls,
                "tool_actions": self.new_tools,
                "cost_nanos": self.new_cost_nanos,
                "branch_active_ms": int(self.clock() * 1000),
                "accepted_mutations_since_checkpoint": (
                    self.gateway.accepted_mutations - self.initial_mutations
                ),
                "current_diff_hash": digest,
                "visible_checks": self.gateway.visible_check_status(diff_hash=digest)
                if digest
                else [],
                "metadata_error": metadata_error,
                "censored": code.startswith("DIAGNOSTIC_"),
                **details,
            }
            self.journal.append("terminal", self.terminal)
        return self.terminal

    def accept(self, turn_id, turn, policy, checkpoint=lambda _: None):
        try:
            result = super().accept(turn_id, turn, policy, checkpoint)
        except RecoveryError as exc:
            terminal, _ = loop._batch_execution_abort(self.latest)
            if terminal is not None:
                raise engine.AbortExperiment(str(terminal), {"phase": "tool_execution"}) from exc
            raise
        if result is None and self.repair_recheck:
            before = self.counters.tool_actions
            terminal, message = loop._run_repair_recheck(
                journal=self.journal,
                gateway=self.gateway,
                latest_results=self.latest,
                counters=self.counters,
                active_elapsed_ms=self.elapsed_ms,
            )
            self.new_tools += self.counters.tool_actions - before
            if terminal is not None:
                raise engine.AbortExperiment(str(terminal), {"phase": "repair_recheck"})
        return result

    def prepare_request(self, package, adapter):
        if self.terminal is not None:
            return None
        self.gateway.deadline.check()
        events = self.journal.events()
        require(
            any(e["event_type"] == "compacted_seed_finished" for e in events),
            "execute the collected seed before requesting another decision",
        )
        started = [e for e in events if e["event_type"] == "turn_started"]
        decided = {
            e["payload"]["turn_id"] for e in events if e["event_type"] == "turn_decision_recorded"
        }
        require(
            all(e["payload"]["turn_id"] in decided for e in started),
            "pending request is not retryable",
        )
        if self.new_provider_calls >= self.max_responses:
            self.finish("DIAGNOSTIC_STEP_LIMIT", "bounded observation window ended")
            return None
        projection = self.gateway.prepare_context_projection(latest_results=self.latest)
        snapshot = self.gateway.state_snapshot(projection=projection)
        policy = loop._tool_policy(
            self.gateway, self.counters, self.gateway.limits, snapshot=snapshot
        )
        if not policy.completion_possible:
            self.finish(
                "LIMIT_REACHED",
                "completion horizon exhausted before provider dispatch",
                completion_horizon=loop._completion_horizon_payload(
                    self.gateway, self.counters, self.gateway.limits, policy
                ),
            )
            return None
        transition = loop._tool_policy_transition(self.journal, policy)
        context = loop._build_context(
            package=package,
            gateway=self.gateway,
            journal=self.journal,
            correction=self.correction,
            latest_tool_results=self.latest,
            counters=self.counters,
            elapsed_seconds=self.elapsed_ms() / 1000,
            limits=self.gateway.limits,
            policy=policy,
            snapshot=snapshot,
            projection=projection,
            tool_policy_transition=transition,
            repair_recheck=self.repair_recheck,
        )
        last = next(e for e in reversed(events) if e["event_type"] == "turn_started")
        saved_raw = read_source_artifact(self.journal.root, last["payload"]["model_input_artifact"])
        saved = json.loads(saved_raw)
        require(
            sha256_bytes(saved_raw) == last["payload"]["model_input_hash"]
            and saved[: len(self.seed_request["input"])] == self.seed_request["input"],
            "compacted input prefix changed",
        )
        exchange = loop._build_latest_exchange(
            journal=self.journal,
            artifact_store=self.store,
            context=context,
            latest_tool_results=self.latest,
        )
        added = exchange[1:-1]
        # The retained source index is local reconstruction data, never another model input.
        history = [*self.original_history, *saved[len(self.seed_request["input"]) :]]
        admissions = {
            e["payload"]["action_id"]: e["payload"]
            for e in events
            if e["event_type"] == "action_started"
        }
        for n, item in enumerate(added):
            if item.get("type") == "function_call_output":
                added[n] = {
                    **item,
                    "output": canonical_json(
                        project_mutation_result(
                            json.loads(item["output"]),
                            history=[*history, *added[:n]],
                            admission=admissions.get(item["call_id"]),
                        )
                    ),
                }
        history.extend(added)
        # Reuse native derived-state projection, then the already-tested public reentry.
        state = reference_native_sources(json.loads(exchange[-1]["content"]), history)
        state = loop.compact_model_state(state, history)
        projection_input = assemble_model_input(
            system_prompt=loop.DEV_SYSTEM_PROMPT,
            state=state,
            history=[
                i
                for i in history
                if i.get("type") in {"reasoning", "function_call", "function_call_output"}
            ],
        )
        reentry, metrics = compact.public_reentry(projection_input)
        items, lifecycle = snapshots.compose(
            seed=self.seed_request["input"], saved=saved, added=added,
            reentry=reentry[-1], policy=self.context_policy,
        )
        request = {
            **copy.deepcopy(self.seed_request),
            "input": items,
            "tools": dev_tool_schemas(
                finish_enabled="finish_task" in policy.allowed_tools,
                check_ids=policy.check_ids,
                allowed_tools=policy.allowed_tools,
                read_paths=policy.targeted_read_paths,
            ),
        }
        require(
            adapter.config == followup.model_config("medium") and adapter.client.max_retries == 0,
            "adapter/model settings changed",
        )
        turn_id = "turn_" + uuid.uuid4().hex
        ref, context_ref = (
            self.store.put_text(
                json.dumps(items, ensure_ascii=False, separators=(",", ":")), "application/json"
            ),
            self.store.put_text(context, "application/json"),
        )
        self.journal.append(
            "turn_started",
            {
                "turn_id": turn_id,
                "context_artifact": context_ref.model_dump(mode="json"),
                "context_hash": context_ref.content_hash,
                "model_input_artifact": ref.model_dump(mode="json"),
                "model_input_hash": ref.content_hash,
                "state_lifecycle": lifecycle,
                "available_tool_names": sorted(policy.allowed_tools),
                "workflow_gate": policy.workflow_gate,
                "max_parallel_reads": policy.max_parallel_reads,
                "targeted_read_paths": list(policy.targeted_read_paths),
                "active_elapsed_ms": self.elapsed_ms(),
            },
        )
        self.journal.append(
            "compacted_context_appended" if self.context_policy == snapshots.APPEND
            else "compacted_context_projected",
            {
                "turn_id": turn_id,
                "seed_input_hash": sha256_json(self.seed_request["input"]),
                **({"prefix_item_count": len(saved)} if self.context_policy == snapshots.APPEND
                   else {"previous_input_item_count": len(saved),
                         "preserved_seed_item_count": len(self.seed_request["input"])}),
                "added_exchange_items": len(added),
                "state_lifecycle": lifecycle,
                **metrics,
            },
        )
        if transition:
            self.journal.append("tool_policy_transition", {"turn_id": turn_id, **transition})
        self.correction = None
        return turn_id, request, policy


def initialize(
    plan: Plan,
    packet: dict,
    root: Path,
    sandbox,
    *,
    probe_sandbox=None,
    clock=monotonic,
    execution_deadline=None,
) -> Episode:
    """New isolated checkpoint only; backends are explicit, seed execution is separate."""
    require(
        packet == proposal(plan, packet["max_new_responses"],
                           context_policy=packet.get("context_policy", snapshots.APPEND)),
        "changed initialization contract"
    )
    require(
        sha256_json(plan.request) == plan.identity["request_hash"]
        and sha256_json(plan.seed.model_dump(mode="json")) == plan.identity["seed_turn_hash"],
        "in-memory seed changed",
    )
    require(
        sha256_json(plan.original_input) == plan.identity["original_input_hash"]
        and plan.state == json.loads(plan.request["input"][-1]["content"])["state"],
        "checkpoint projection inputs changed",
    )
    root = compact.new_external_root(root, plan.source_root, plan.collection_root)
    require(
        sandbox is not None
        and (plan.identity["probe_image_digest"] is None or probe_sandbox is not None),
        "registered backends required",
    )
    remaining = plan.state["remaining_budget"]
    limits = DevLimits.model_validate(packet["global_limits"])
    counters = loop._restore_counters(SimpleNamespace(events=lambda: plan.prefix))
    require(
        counters.model_calls == limits.max_model_calls - remaining["model_calls"]
        and counters.tool_actions == limits.max_tool_actions - remaining["tool_actions"],
        "checkpoint counters differ",
    )
    active = engine.ActiveClock(clock)
    seed_time = plan.identity["seed_active_seconds"]
    require(seed_time < remaining["active_wall_time_seconds"], "seed exhausted active budget")
    deadline = ExecutionDeadline.from_remaining(
        remaining["active_wall_time_seconds"] - seed_time, clock=active
    )
    if execution_deadline is not None:
        deadline = engine.SharedDeadline(deadline, execution_deadline)
    store = ArtifactStore(root / "artifacts")
    journal = DevJournal(root, "run_dev_compactepisode_" + uuid.uuid4().hex[:16])
    binding = {
        "kind": KIND,
        "run_id": journal.run_id,
        "packet_hash": sha256_json(packet),
        "packet": packet,
        "native_resume": False,
    }
    ArtifactStore(root).write_text_immutable(root / "execution.json", canonical_json(binding))
    sources = [
        engine.readonly_store(plan.source_root / "artifacts"),
        engine.readonly_store(plan.collection_root / "artifacts"),
    ]
    with active.active(), journal.execution_lock():
        journal.append(
            "compacted_episode_initialized",
            {
                **BOUNDARIES,
                "packet_hash": sha256_json(packet),
                "source": plan.identity,
                "inherited_events_are_not_new_execution": True,
            },
        )
        for event in plan.prefix:
            if event["event_type"] in INHERIT:
                journal.append(
                    event["event_type"],
                    {
                        **engine.import_artifacts(event["payload"], store, sources),
                        "diagnostic_inherited": True,
                        "source_event_hash": event["event_hash"],
                    },
                )
        workspace = root / "workspaces" / journal.run_id / "repo"
        review.clone_checkpoint(
            SimpleNamespace(
                source_root=plan.source_root,
                packet={"source_run_id": plan.identity["source_run_id"]},
            ),
            {**plan.state, "source_bodies": plan.state.get("current_sources", [])},
            workspace,
            store,
            deadline,
        )
        gateway = DevToolGateway(
            workspace=workspace,
            public_task=plan.package.public,
            sandbox=sandbox,
            probe_sandbox=probe_sandbox,
            journal=journal,
            limits=limits,
            deadline=deadline,
        )
        require(
            gateway.accepted_mutations
            == limits.max_accepted_mutations - remaining["accepted_mutations"],
            "checkpoint mutation count differs",
        )
        loop._validate_resumed_workspace(workspace, journal, deadline=deadline)
        seed = DevModelTurn.model_validate(
            engine.import_artifacts(plan.seed.model_dump(mode="json"), store, sources)
        )
    return Episode(
        "compacted",
        journal,
        store,
        gateway,
        counters,
        active,
        limits.wall_time_seconds - remaining["active_wall_time_seconds"] + seed_time,
        latest=journal.latest_tool_batch_results(),
        seed=seed,
        seed_request=copy.deepcopy(plan.request),
        original_history=copy.deepcopy(plan.original_input),
        initial_mutations=gateway.accepted_mutations,
        repair_recheck=plan.identity["repair_recheck"],
        max_responses=packet["max_new_responses"],
        context_policy=packet["context_policy"],
    )


def _abort(episode, exc):
    if isinstance(exc, engine.AbortExperiment):
        code = exc.code
    elif isinstance(exc, ExecutionDeadlineExceeded):
        code = "LIMIT_REACHED"
    elif isinstance(exc, loop._ProviderContinuationError):
        code = "PROVIDER_CONTINUATION_ERROR"
    else:
        code = "EXECUTION_ERROR"
    if episode.journal.unresolved_provider_call() is not None:
        code = "PROVIDER_TIMEOUT_OR_UNKNOWN"
    episode.finish(
        code,
        "diagnostic stopped; no retry or resume",
        failure=engine.requests.exception_evidence(exc),
    )


def execute_seed(episode: Episode, *, checkpoint=lambda _: None):
    """Execute the saved check once, without asking the provider to repeat its choice."""
    if episode.terminal is not None:
        return episode.terminal
    with episode.clock.active(), episode.journal.execution_lock():
        events = episode.journal.events()
        if any(e["event_type"] == "compacted_seed_finished" for e in events):
            return None
        try:
            require(
                not any(e["event_type"] == "compacted_seed_started" for e in events),
                "interrupted seed cannot be restarted",
            )
            episode.gateway.deadline.check()
            seed = episode.seed
            continuation = loop._load_provider_continuation(episode.store, seed.continuation_ref)
            loop._validate_continuation_action_order(continuation, seed.tool_calls)
            policy = loop._tool_policy(episode.gateway, episode.counters, episode.gateway.limits)
            require(
                set(policy.allowed_tools) == {t["name"] for t in episode.seed_request["tools"]},
                "checkpoint tool policy differs",
            )
            ref = episode.store.put_text(
                json.dumps(
                    episode.seed_request["input"], ensure_ascii=False, separators=(",", ":")
                ),
                "application/json",
            )
            turn_id = "turn_seed_" + uuid.uuid4().hex
            episode.journal.append(
                "compacted_seed_started",
                {"turn_id": turn_id, "seed_hash": sha256_json(seed.model_dump(mode="json"))},
            )
            episode.journal.append(
                "turn_started",
                {
                    "turn_id": turn_id,
                    "model_input_artifact": ref.model_dump(mode="json"),
                    "model_input_hash": ref.content_hash,
                    "available_tool_names": sorted(policy.allowed_tools),
                    "workflow_gate": policy.workflow_gate,
                    "diagnostic_inherited": True,
                },
            )
            episode.counters.model_calls += 1  # Historical paid seed; never charged to a new cap.
            episode.journal.append("compacted_seed_usage_inherited", {"model_calls": 1})
            episode.journal.append(
                "model_call_finished",
                {
                    "turn_id": turn_id,
                    "diagnostic_inherited": True,
                    "origin": "previously_collected_seed",
                    "new_provider_dispatch": False,
                },
            )
            episode.accept(turn_id, seed, policy, checkpoint)
            episode.journal.append(
                "compacted_seed_finished",
                {"turn_id": turn_id, "active_elapsed_ms": episode.elapsed_ms()},
            )
        except (Exception, KeyboardInterrupt, SystemExit) as exc:
            _abort(episode, exc)
            raise
    return episode.terminal


def step(episode: Episode, package, adapter, ledger, *, checkpoint=lambda _: None):
    """One explicitly injected, bounded step; never construct a provider client here."""
    if episode.terminal is not None:
        return episode.terminal
    with episode.clock.active(), episode.journal.execution_lock():
        try:
            prepared = episode.prepare_request(package, adapter)
            if prepared is not None:
                engine.dispatch(
                    episode,
                    adapter,
                    ledger,
                    prepared,
                    checkpoint=checkpoint,
                    request_waits=engine.requests.WAITS,
                )
        except (Exception, KeyboardInterrupt, SystemExit) as exc:
            _abort(episode, exc)
            raise
    return episode.terminal


def main():
    parser = argparse.ArgumentParser(
        description="Provider-free preparation only; no live subcommand"
    )
    modes = parser.add_subparsers(dest="mode", required=True)
    p = modes.add_parser("prepare")
    for key in ("collection-root", "task-dir", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    p.add_argument("--result-hash", required=True)
    p.add_argument("--max-new-responses", type=int, default=MAX_NEW_RESPONSES)
    p.add_argument("--context-policy", choices=snapshots.POLICIES, default=snapshots.APPEND)
    p = modes.add_parser("verify")
    p.add_argument("--packet-root", type=Path, required=True)
    p.add_argument("--packet-hash", required=True)
    args = vars(parser.parse_args())
    mode = args.pop("mode")
    if mode == "prepare":
        result = prepare(**args)
    else:
        _, packet = verify(**args)
        result = {
            "packet_hash": sha256_json(packet),
            "status": packet["status"],
            "api_requests": 0,
            "tool_executions": 0,
            "official": False,
        }
    print(canonical_json(result))


if __name__ == "__main__":
    main()
