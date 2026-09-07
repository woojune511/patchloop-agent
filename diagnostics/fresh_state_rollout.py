"""Continue the four collected C3 decisions in independent diagnostic workspaces.

Not dev resume, new sampling, a default context change, or private evaluation.
The source prefix is explicitly inherited evidence, never newly executed usage.
Each seed uses its original request/response; subsequent exchanges use the current
gateway, projection, action policy and correction logic. All new native reasoning
and calls/results are retained in both arms. No restart or automatic retry exists.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import uuid
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from typing import Any

from diagnostics import decision_sampler as shared
from diagnostics import fresh_state_design as design
from diagnostics import fresh_state_sampler as sampler
from patchloop.agent.model import OpenAIResponsesAdapter, create_openai_client
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import runner as loop
from patchloop.dev.contracts import DevLimits, DevModelTurn
from patchloop.dev.conversation import history_metadata, reconstruct_state
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas, validate_tool_batch
from patchloop.errors import ContractError, RecoveryError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text, utc_now

FRESH_PACKET_HASH = "sha256:1839a26def6adea31a288ccf2c084d8a77b80b166039e3491dffd141cbb1d8d7"
SEED_JOURNAL_HASH = "sha256:2c5fc7d654b354a9879ed2f7d49e7e7c19e7ce3c20b76fe263be81f8d6f08295"
SOURCE = Path("C:/patchloop-state")
DESIGN = Path("C:/pt/pl39-fresh-state-design-a/packet.json")
PARENT = Path("C:/pt/pl39-decision-design-a/packet.json")
SEEDS = Path("C:/pt/pl39-fresh-state-live-a")
TASK = repository_root() / "tasks/dev-train/pyfakefs-makedirs-parent-traversal-v2"
KINDS = (
    "action_started",
    "action_finished",
    "tool_batch_started",
    "tool_batch_finished",
    "working_notes_updated",
    "protocol_correction",
    "attempt_card",
    "turn_started",
    "turn_decision_recorded",
    "provider_call_started",
    "provider_call_finished",
    "input_count_started",
    "input_count_finished",
    "tool_policy_transition",
)
BOUNDARIES = {
    "official": False,
    "claim_eligible": False,
    "task_acceptance": "NOT_RUN",
    "safety_state": "NOT_RUN",
    "private_evaluation": "NOT_RUN",
    "resume_allowed": False,
}
STATE_NOTICE = (
    "For subsequent turns, the latest developer record with kind=harness_current_state "
    "contains the complete current state under state. Earlier records and the frozen "
    "public archive remain historical evidence, not current source/check/budget authority. "
    "The immutable public_task remains in the initial developer record."
)


def implementation_hash() -> str:
    return sha256_json(
        {
            **sampler.implementation_hashes(),
            "diagnostics/fresh_state_rollout.py": sha256_bytes(Path(__file__).read_bytes()),
        }
    )


def readonly_store(root: Path) -> ArtifactStore:
    shared.require((root / "objects/sha256").is_dir(), "source CAS missing")
    store = object.__new__(ArtifactStore)
    store.root, store.objects = root, root / "objects/sha256"
    return store


def import_artifacts(value: Any, destination: ArtifactStore, sources: list[ArtifactStore]) -> Any:
    if isinstance(value, list):
        return [import_artifacts(v, destination, sources) for v in value]
    if not isinstance(value, dict):
        return value
    if {
        "artifact_id",
        "content_hash",
        "size_bytes",
        "media_type",
        "path",
        "created_at",
    } <= value.keys():
        artifact = Artifact.model_validate(value)
        source = next(
            (
                s
                for s in sources
                if Path(artifact.path).resolve().is_relative_to(s.objects.resolve())
            ),
            None,
        )
        shared.require(source is not None, "unregistered inherited artifact root")
        imported = destination.put_bytes(source.read_bytes(artifact), artifact.media_type)
        return artifact.model_copy(update={"path": imported.path}).model_dump(mode="json")
    return {k: import_artifacts(v, destination, sources) for k, v in value.items()}


@dataclass
class Plan:
    frozen: sampler.FreshPlan
    prefix: list[dict]
    started: dict
    samples: list[dict]
    public_state: dict
    package: Any
    source_workspace: Path


def load_plan() -> Plan:
    frozen = sampler.load_plan(DESIGN, PARENT, SOURCE, FRESH_PACKET_HASH)
    source = DevJournal(SOURCE, frozen.packet["source_run_id"])
    events = source.events()
    start = next(
        e
        for e in events
        if e["event_type"] == "turn_started"
        and e["payload"]["turn_id"] == frozen.packet["source_turn_id"]
    )
    prefix = events[: events.index(start)]
    seed_result = json.loads((SEEDS / "result.json").read_bytes())
    seed_journal = DevJournal(SEEDS, seed_result["run_id"])
    shared.require(
        sha256_bytes(seed_journal.path.read_bytes()) == SEED_JOURNAL_HASH,
        "collected seed journal mismatch",
    )
    shared.require(
        seed_result["terminal"] == "SAMPLES_COLLECTED"
        and seed_result["provider_calls"] == 4
        and seed_result["tool_executions"] == 0,
        "four independent completed seeds required",
    )
    records = [e["payload"] for e in seed_journal.events() if e["event_type"] == "sample_recorded"]
    shared.require(
        [(r["arm"], r["sample_number"]) for r in records] == list(sampler.PROTOCOL.sampling_order),
        "seed schedule mismatch",
    )
    store = readonly_store(SEEDS)
    samples = []
    for cell, record in zip(frozen.cells, records, strict=True):
        shared.require(
            record["request_hash"] == cell.request_hash
            and record["ordered_request_hash"] == sha256_text(cell.request_json),
            "seed did not use the exact frozen request",
        )
        public = json.loads(store.read_bytes(Artifact.model_validate(record["public_artifact"])))
        calls = [
            loop._requested_tool_from_openai(SimpleNamespace(**c)) for c in public["tool_calls"]
        ]
        shared.require(
            public["response_status"] == "completed" and public["error_code"] is None,
            "seed is not a completed decision",
        )
        ref = loop._continuation_ref_from_payload(record)
        shared.require(ref is not None, "seed continuation missing")
        continuation = loop._load_provider_continuation(store, ref)
        loop._validate_continuation_action_order(continuation, calls)
        samples.append({"cell": cell, "record": record, "calls": calls})
    package = load_task_package(TASK)
    loop._live_source_preflight(TASK, package)
    shared.require(package.task_content_hash == frozen.packet["task_content_hash"], "task mismatch")
    state = reconstruct_state(json.loads(frozen.cells[0].request_json)["input"])
    shared.require(
        state["public_task"] == package.public.model_dump(mode="json"), "public mismatch"
    )
    shared.require(
        state["remaining_budget"]["model_calls"] == 9
        and state["remaining_budget"]["tool_actions"] == 68
        and state["remaining_budget"]["accepted_mutations"] == 1,
        "checkpoint budget drift",
    )
    return Plan(
        frozen,
        prefix,
        start["payload"],
        samples,
        state,
        package,
        SOURCE / "workspaces" / source.run_id / "repo",
    )


class ActiveClock:
    def __init__(self, clock=monotonic):
        self.clock, self.elapsed, self.started = clock, 0.0, None

    def __call__(self):
        return self.elapsed + (self.clock() - self.started if self.started is not None else 0.0)

    @contextmanager
    def active(self):
        shared.require(self.started is None, "nested branch clock")
        self.started = self.clock()
        try:
            yield
        finally:
            self.elapsed += self.clock() - self.started
            self.started = None


class SharedDeadline:
    """Use the tighter branch-active and whole-experiment deadline."""

    def __init__(self, *deadlines):
        self.deadlines = deadlines

    def remaining_seconds(self):
        return min(deadline.remaining_seconds() for deadline in self.deadlines)

    check = ExecutionDeadline.check
    bounded_timeout = ExecutionDeadline.bounded_timeout


def clone_checkpoint(source: Path, destination: Path, state: dict, store: ArtifactStore) -> None:
    shared.require(not destination.exists(), "checkpoint destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    commands = [
        [
            "git",
            "clone",
            "--quiet",
            "--no-hardlinks",
            "--no-checkout",
            str(source),
            str(destination),
        ],
        ["git", "-C", str(destination), "config", "core.longpaths", "true"],
        [
            "git",
            "-C",
            str(destination),
            "checkout",
            "--quiet",
            "--detach",
            state["public_task"]["repository"]["base_commit"],
        ],
    ]
    for command in commands:
        result = subprocess.run(command, capture_output=True, check=False)
        shared.require(result.returncode == 0, "isolated checkpoint Git operation failed")
    patch = store.put_text(state["current_diff"]["patch"], "text/x-diff")
    WorkspaceManager.apply_patch(destination, patch.path)
    summary = WorkspaceManager.diff_summary(destination)
    shared.require(
        summary.patch_hash == state["current_diff"]["patch_hash"] and not summary.untracked_files,
        "cloned checkpoint differs from the cutoff",
    )
    for group in state.get("current_sources", []):
        shared.require(
            sha256_bytes((destination / group["path"]).read_bytes()) == group["file_hash"],
            "checkpoint source raw bytes mismatch",
        )


@dataclass
class Branch:
    label: str
    journal: DevJournal
    store: ArtifactStore
    gateway: DevToolGateway
    counters: Any
    clock: ActiveClock
    base_elapsed: float
    latest: list = field(default_factory=list)
    correction: dict | None = None
    terminal: dict | None = None
    new_provider_calls: int = 0
    new_tools: int = 0
    new_cost_nanos: int = 0

    def elapsed_ms(self):
        return int((self.base_elapsed + self.clock()) * 1000)

    def finish(self, code: str, message: str = "", **details):
        if self.terminal is None:
            self.terminal = {
                **BOUNDARIES,
                "branch": self.label,
                "terminal": code,
                "message": message,
                "provider_calls": self.new_provider_calls,
                "tool_actions": self.new_tools,
                "cost_nanos": self.new_cost_nanos,
                "branch_active_ms": int(self.clock() * 1000),
                "accepted_mutations_since_checkpoint": self.gateway.accepted_mutations - 3,
                "current_diff_hash": self.gateway.current_diff_hash,
                "visible_checks": self.gateway.visible_check_status(),
                **details,
            }
            self.journal.append("terminal", self.terminal)
        return self.terminal

    def accept(self, turn_id: str, turn: DevModelTurn, policy: Any, checkpoint=lambda _: None):
        self.journal.append(
            "turn_decision_recorded",
            {
                "turn_id": turn_id,
                **turn.model_dump(mode="json"),
            },
        )
        checkpoint("decision_recorded")
        if turn.error_code == "provider_continuation_error":
            raise RecoveryError("provider continuation unavailable")
        issue = None
        if turn.error_code:
            issue = loop._model_error_issue(
                turn.error_code, turn.incomplete_reason, turn.tool_contract_failure
            )
        else:
            try:
                validate_tool_batch(
                    turn.tool_calls,
                    max_parallel_reads=policy.max_parallel_reads,
                    allowed_tools=policy.allowed_tools,
                    allowed_read_paths=policy.targeted_read_paths,
                )
            except ContractError as exc:
                issue = str(exc)
        if issue is not None:
            if self.counters.protocol_recoveries >= self.gateway.limits.max_protocol_recoveries:
                return self.finish("PROTOCOL_VIOLATION", issue)
            self.counters.protocol_recoveries += 1
            self.correction = loop._protocol_correction(
                turn_id=turn_id,
                code=turn.error_code or "INVALID_TOOL_BATCH",
                issue=issue,
                gateway=self.gateway,
                policy=loop._tool_policy(self.gateway, self.counters, self.gateway.limits),
                tool_contract_failure=turn.tool_contract_failure,
            )
            self.journal.append("protocol_correction", self.correction)
            return None
        shared.require(
            self.counters.tool_actions + len(turn.tool_calls)
            <= self.gateway.limits.max_tool_actions,
            "tool batch budget exceeded",
        )
        self.journal.append(
            "tool_batch_started",
            {
                "turn_id": turn_id,
                "tool_calls": [c.model_dump(mode="json") for c in turn.tool_calls],
                "active_elapsed_ms": self.elapsed_ms(),
            },
        )
        self.counters.tool_actions += len(turn.tool_calls)
        self.new_tools += len(turn.tool_calls)
        self.gateway.record_working_notes_update(turn.tool_calls, turn_id=turn_id)
        self.latest = self.gateway.execute_batch(turn.tool_calls)
        checkpoint("actions_finished")
        completed, self.correction = loop._record_tool_batch(
            journal=self.journal,
            gateway=self.gateway,
            turn_id=turn_id,
            calls=turn.tool_calls,
            results=self.latest,
            active_elapsed_ms=self.elapsed_ms(),
        )
        checkpoint("batch_finished")
        loop._update_inspection_counters(self.counters, self.latest, self.gateway)
        self.counters.protocol_recoveries = 0
        abort, message = loop._batch_execution_abort(self.latest)
        if abort is not None:
            # Cleanup uncertainty and deadline failures stop the whole experiment.
            raise RecoveryError(message or str(abort))
        if completed is not None:
            if completed.tool == "stop_task":
                return self.finish("AGENT_STOPPED", completed.output["summary"])
            artifact = self.store.put_text(completed.output["patch"], "text/x-diff")
            shared.require(
                artifact.content_hash == completed.output["patch_hash"],
                "submission identity mismatch",
            )
            return self.finish(
                "PUBLIC_CHECKS_SUBMITTED", submitted_artifact=artifact.model_dump(mode="json")
            )
        return None

    def prepare_request(self, package: Any, adapter: Any):
        self.gateway.deadline.check()
        if self.new_provider_calls >= 8:
            self.finish("LIMIT_REACHED", "eight-response follow-up bound reached")
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
        )
        # The identical format notice makes the original three-message B packet's
        # subsequent native state records explicit without rewriting any seed item.
        state = json.loads(context)
        state["followup_state_contract"] = STATE_NOTICE
        context = canonical_json(state)
        model_input = loop._build_model_input(
            journal=self.journal,
            artifact_store=self.store,
            context=context,
            latest_tool_results=self.latest,
        )
        schemas = dev_tool_schemas(
            finish_enabled="finish_task" in policy.allowed_tools,
            check_ids=policy.check_ids,
            allowed_tools=policy.allowed_tools,
            read_paths=policy.targeted_read_paths,
        )
        request = adapter.request_payload(
            model_input, schemas, system_prompt=loop.DEV_SYSTEM_PROMPT
        )
        request["parallel_tool_calls"], request["tool_choice"] = True, "required"
        turn_id = "turn_" + uuid.uuid4().hex
        input_ref = self.store.put_text(canonical_json(model_input), "application/json")
        context_ref = self.store.put_text(context, "application/json")
        self.journal.append(
            "turn_started",
            {
                "turn_id": turn_id,
                "context_artifact": context_ref.model_dump(mode="json"),
                "context_hash": context_ref.content_hash,
                "model_input_artifact": input_ref.model_dump(mode="json"),
                "model_input_hash": input_ref.content_hash,
                "native_history": history_metadata(model_input),
                "available_tool_names": sorted(policy.allowed_tools),
                "workflow_gate": policy.workflow_gate,
                "max_parallel_reads": policy.max_parallel_reads,
                "targeted_read_paths": list(policy.targeted_read_paths),
                "active_elapsed_ms": self.elapsed_ms(),
            },
        )
        if transition:
            self.journal.append("tool_policy_transition", {"turn_id": turn_id, **transition})
        self.correction = None
        return turn_id, request, policy


def initialize(
    plan: Plan, root: Path, sandbox: Any, probe: Any, *, clock=monotonic
) -> list[Branch]:
    branches = []
    limits = DevLimits()
    for sample in plan.samples:
        cell, record = sample["cell"], sample["record"]
        label = f"{cell.arm}{cell.sample_number}"
        branch_root = root / label
        store = ArtifactStore(branch_root / "artifacts")
        journal = DevJournal(branch_root, "run_dev_branch_" + uuid.uuid4().hex[:16])
        journal.append(
            "diagnostic_branch_started",
            {
                "kind": "fresh-state-short-rollout-v1",
                **BOUNDARIES,
                "label": label,
                "source_run_id": plan.frozen.packet["source_run_id"],
                "source_prefix_last_event_hash": plan.prefix[-1]["event_hash"],
                "reused_sample_id": record["sample_id"],
                "inherited_events_are_not_new_execution": True,
            },
        )
        sources = [readonly_store(SOURCE / "artifacts"), readonly_store(SEEDS)]
        for event in plan.prefix:
            if event["event_type"] in KINDS:
                journal.append(
                    event["event_type"],
                    {
                        **import_artifacts(event["payload"], store, sources),
                        "diagnostic_inherited": True,
                        "source_event_hash": event["event_hash"],
                    },
                )
        workspace = branch_root / "workspaces" / journal.run_id / "repo"
        clone_checkpoint(plan.source_workspace, workspace, plan.public_state, store)
        active = ActiveClock(clock)
        remaining = plan.public_state["remaining_budget"]["active_wall_time_seconds"]
        gateway = DevToolGateway(
            workspace=workspace,
            public_task=plan.package.public,
            sandbox=sandbox,
            journal=journal,
            limits=limits,
            deadline=ExecutionDeadline.from_remaining(remaining, clock=active),
            probe_sandbox=probe,
        )
        counters = loop._restore_counters(journal)
        shared.require(
            counters.model_calls == 31
            and counters.tool_actions == 32
            and gateway.accepted_mutations == 3,
            "hydrated checkpoint budget mismatch",
        )
        loop._validate_resumed_workspace(workspace, journal)
        input_items = json.loads(cell.request_json)["input"]
        input_ref = store.put_text(canonical_json(input_items), "application/json")
        started = import_artifacts(copy.deepcopy(plan.started), store, sources)
        seed_turn = "turn_seed_" + uuid.uuid4().hex
        started.update(
            turn_id=seed_turn,
            model_input_artifact=input_ref.model_dump(mode="json"),
            model_input_hash=input_ref.content_hash,
            native_history=history_metadata(input_items),
        )
        journal.append("turn_started", started)
        branch = Branch(
            label, journal, store, gateway, counters, active, limits.wall_time_seconds - remaining
        )
        branch._seed = (
            seed_turn,
            DevModelTurn(
                tool_calls=sample["calls"],
                output_item_types=["reasoning", "function_call"],
                continuation_ref=loop._continuation_ref_from_payload(
                    import_artifacts(record, store, sources)
                ),
            ),
            SimpleNamespace(
                allowed_tools=frozenset(started["available_tool_names"]),
                max_parallel_reads=cell.max_parallel_reads,
                targeted_read_paths=cell.read_paths,
            ),
        )
        branches.append(branch)
    return branches


class AbortExperiment(Exception):
    def __init__(self, code: str):
        self.code = code


def dispatch(
    branch: Branch,
    adapter: Any,
    ledger: DevCostLedger,
    prepared: tuple,
    *,
    checkpoint=lambda _: None,
):
    turn_id, request, policy = prepared
    wire = design.wire_json(request)
    request_ref = branch.store.put_text(wire, "application/json")
    count_id, call_id = "count_" + uuid.uuid4().hex, "call_" + uuid.uuid4().hex
    common = {
        "turn_id": turn_id,
        "request_hash": sha256_json(request),
        "ordered_request_hash": sha256_text(wire),
    }
    branch.journal.append(
        "input_count_started",
        {
            **common,
            "count_id": count_id,
            "request_artifact": request_ref.model_dump(mode="json"),
            "active_elapsed_ms": branch.elapsed_ms(),
        },
    )
    try:
        count = adapter.count_input_tokens_v2(
            request, timeout_seconds=branch.gateway.deadline.check()
        )
        shared.require(type(count) is int and count > 0, "invalid count")
    except Exception as exc:
        raise AbortExperiment("COUNT_TIMEOUT_OR_UNKNOWN") from exc
    branch.journal.append(
        "input_count_finished", {"turn_id": turn_id, "count_id": count_id, "input_tokens": count}
    )
    if count > sampler.INPUT_TOKEN_LIMIT:
        raise AbortExperiment("INPUT_LIMIT_EXCEEDED")
    admission = ledger.admit(count, desired_output_ceiling=25000, minimum_output_ceiling=25000)
    if admission is None:
        raise AbortExperiment("COST_CAP_REACHED")
    shared.require(design.wire_json(request) == wire, "count altered exact request")
    timeout = branch.gateway.deadline.check()
    branch.journal.append(
        "provider_call_started",
        {
            **common,
            "call_id": call_id,
            "input_tokens": count,
            "output_ceiling": 25000,
            "reserved_cost_nanos": admission.reserved_cost_nanos,
            "active_elapsed_ms": branch.elapsed_ms(),
        },
    )
    branch.counters.model_calls += 1
    branch.new_provider_calls += 1
    checkpoint("dispatch_recorded")
    try:
        raw = adapter.execute_request(
            request, requested_input_tokens=count, timeout_seconds=timeout
        )
    except Exception as exc:
        raise AbortExperiment("PROVIDER_TIMEOUT_OR_UNKNOWN") from exc
    checkpoint("provider_returned")
    valid = (
        raw.input_tokens == count
        and 0 <= raw.cached_input_tokens <= count
        and 0 <= raw.reasoning_output_tokens <= raw.output_tokens <= 25000
        and raw.response_model == shared.MODEL
        and bool(raw.response_id)
        and raw.response_status in {"completed", "incomplete"}
        and not (raw.error and raw.error.code == "input_token_count_mismatch")
    )
    cost = (
        ledger.settle(
            input_tokens=raw.input_tokens,
            cached_input_tokens=raw.cached_input_tokens,
            output_tokens=raw.output_tokens,
        )
        if valid
        else None
    )
    branch.journal.append(
        "provider_call_finished",
        {
            **common,
            "call_id": call_id,
            "response_id": raw.response_id,
            "response_model": raw.response_model,
            "response_status": raw.response_status,
            "input_tokens": raw.input_tokens,
            "cached_input_tokens": raw.cached_input_tokens,
            "output_tokens": raw.output_tokens,
            "reasoning_output_tokens": raw.reasoning_output_tokens,
            "cost_nanos": cost,
            "billing_known": valid,
            "active_elapsed_ms": branch.elapsed_ms(),
        },
    )
    checkpoint("usage_recorded")
    if not valid or ledger.spent_nanos > ledger.cap_nanos:
        raise AbortExperiment("PROVIDER_TIMEOUT_OR_UNKNOWN")
    branch.new_cost_nanos += cost
    turn = loop._turn_from_openai(raw)
    if turn.error_code == "provider_continuation_error":
        raise AbortExperiment("PROVIDER_CONTINUATION_ERROR")
    if "reasoning" in turn.output_item_types:
        if turn.provider_continuation is None:
            raise AbortExperiment("PROVIDER_CONTINUATION_ERROR")
        try:
            loop._validate_continuation_action_order(turn.provider_continuation, turn.tool_calls)
            ref = loop._store_provider_continuation(branch.store, turn.provider_continuation)
            loop._load_provider_continuation(branch.store, ref)
            turn = turn.model_copy(update={"continuation_ref": ref})
        except Exception as exc:
            raise AbortExperiment("PROVIDER_CONTINUATION_ERROR") from exc
    branch.accept(turn_id, turn, policy, checkpoint)


def run(
    plan: Plan,
    root: Path,
    *,
    credential_file: Path,
    cap: Decimal,
    pricing_verified_on: str,
    approved_hash: str,
    sandbox=None,
    probe=None,
    adapter_factory=None,
    checkpoint=lambda _: None,
):
    shared.require(approved_hash == implementation_hash(), "rollout implementation mismatch")
    shared.require(cap == Decimal("1.20"), "this protocol uses one shared $1.20 cap")
    shared.require(
        pricing_verified_on == utc_now().date().isoformat(), "price review date mismatch"
    )
    root = root.resolve()
    protected = [
        SOURCE,
        DESIGN.parent,
        PARENT.parent,
        SEEDS,
        Path("C:/pt/pl39-fresh-state-review-a"),
        repository_root(),
    ]
    shared.require(
        root.is_absolute()
        and not root.exists()
        and all(
            not root.is_relative_to(p.resolve()) and not p.resolve().is_relative_to(root)
            for p in protected
        ),
        "new external result root required",
    )
    shared.require(
        credential_file.resolve() == repository_root() / ".env",
        "exact root credential path required",
    )
    if adapter_factory is None:
        plan = load_plan()  # Recheck all frozen/runtime/task identities before execution.
        sandbox = loop._live_sandbox_preflight(plan.package)
        probe = DockerProbeSandbox()
        probe.preflight()
    shared.require(sandbox is not None, "registered sandbox required")
    root.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(root)
    ledger = DevCostLedger(cap, pricing_for_model(shared.MODEL))
    envelope = {
        **BOUNDARIES,
        "kind": "fresh-state-short-rollout-v1",
        "implementation_hash": approved_hash,
        "runtime_hash": runtime_content_hash(),
        "seed_journal_hash": SEED_JOURNAL_HASH,
        "packet_hash": FRESH_PACKET_HASH,
        "task_content_hash": plan.package.task_content_hash,
        "task_id": plan.package.public.task_id,
        "model": shared.MODEL,
        "reasoning": "medium",
        "output_ceiling": 25000,
        "credential_path_hash": sha256_text(str(credential_file.resolve())),
        "cap_nanos": ledger.cap_nanos,
        "pricing": shared.price_identity(),
        "pricing_verified_on": pricing_verified_on,
        "branches": ["A1", "B1", "B2", "A2"],
        "seed_executions_each": 1,
        "maximum_new_responses_each": 8,
        "maximum_new_responses_total": 32,
        "experiment_wall_time_seconds": 1800,
        "remaining_budget_before_seed": plan.public_state["remaining_budget"],
        "schedule": "round-robin A1 B1 B2 A2; skip terminal branches",
        "cap_policy": (
            "JIT full-ceiling admission; stop all on cap or uncertainty; no reserved success"
        ),
        "followup_state_contract": STATE_NOTICE,
        "provider_free": adapter_factory is not None,
    }
    store.write_text_immutable(root / "envelope.json", canonical_json(envelope))
    branches, client, terminal = [], None, "ROLLOUTS_COMPLETED"
    started = monotonic()
    experiment_deadline = ExecutionDeadline.from_remaining(1800)
    try:
        branches = initialize(plan, root, sandbox, probe)
        for branch in branches:
            branch.gateway.deadline = SharedDeadline(branch.gateway.deadline, experiment_deadline)
        # Each already billed seed consumes the checkpoint's next model step, not
        # this invocation's provider-call or cost ledger. No seed is regenerated.
        for branch in branches:
            with branch.clock.active(), branch.journal.execution_lock():
                turn_id, turn, policy = branch._seed
                branch.journal.append(
                    "model_call_finished",
                    {
                        "turn_id": turn_id,
                        "provider": "reused_collected_sample",
                        "new_provider_dispatch": False,
                    },
                )
                branch.counters.model_calls += 1
                branch.accept(turn_id, turn, policy, checkpoint)
        config = shared.model_config("medium")
        while any(b.terminal is None for b in branches):
            for branch in branches:
                if branch.terminal is not None:
                    continue
                with branch.clock.active(), branch.journal.execution_lock():
                    if adapter_factory is None:
                        if client is None:
                            from patchloop.environment import load_exact_openai_api_key

                            key = load_exact_openai_api_key(credential_file)
                            client = create_openai_client(config, api_key=key)
                            del key
                        adapter = OpenAIResponsesAdapter(config, api_key="", client=client)
                    else:
                        adapter = adapter_factory(config)
                    shared.require(
                        adapter.config == config and adapter.client.max_retries == 0,
                        "adapter settings drift",
                    )
                    prepared = branch.prepare_request(plan.package, adapter)
                    if prepared is not None:
                        dispatch(branch, adapter, ledger, prepared, checkpoint=checkpoint)
    except AbortExperiment as exc:
        terminal = exc.code
    except ExecutionDeadlineExceeded:
        terminal = "LIMIT_REACHED"
    except (KeyboardInterrupt, SystemExit):
        terminal = "INTERRUPTED"
    except Exception as exc:
        terminal = "ROLLOUT_ERROR"
        store.put_json({"error_type": type(exc).__name__})  # Never serialize raw SDK errors.
    finally:
        if client is not None:
            with suppress(Exception):
                client.close()
    unknown = any(
        b.journal.unresolved_provider_call() is not None
        or any(
            e["event_type"] == "provider_call_finished"
            and e["payload"].get("billing_known") is False
            for e in b.journal.events()
        )
        for b in branches
    )
    if unknown:
        terminal = "PROVIDER_TIMEOUT_OR_UNKNOWN"
    for branch in branches:
        if branch.terminal is None:
            branch.finish(terminal, "experiment stopped; outcome censored", censored=True)
    result = {
        **BOUNDARIES,
        "terminal": terminal,
        "branches": [b.terminal for b in branches],
        "new_provider_calls": sum(b.new_provider_calls for b in branches),
        "new_input_count_calls": sum(
            e["event_type"] == "input_count_started"
            and not e["payload"].get("diagnostic_inherited")
            for b in branches
            for e in b.journal.events()
        ),
        "new_tool_actions": sum(b.new_tools for b in branches),
        "recorded_cost_nanos": ledger.spent_nanos,
        "total_cost_known": not unknown,
        "elapsed_ms": int((monotonic() - started) * 1000),
    }
    store.write_text_immutable(root / "result.json", canonical_json(result))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "run"])
    parser.add_argument("--result-root", type=Path)
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--max-cost-usd", type=Decimal)
    parser.add_argument("--pricing-verified-on")
    parser.add_argument("--implementation-hash")
    parser.add_argument("--approve-four-short-rollouts", action="store_true")
    args = parser.parse_args(argv)
    plan = load_plan()
    if args.command == "validate":
        print(
            canonical_json(
                {
                    **BOUNDARIES,
                    "status": "VALIDATED_NOT_EXECUTED",
                    "implementation_hash": implementation_hash(),
                    "remaining_budget": plan.public_state["remaining_budget"],
                    "seeds": len(plan.samples),
                    "source_prefix_events": len(plan.prefix),
                }
            )
        )
        return 0
    shared.require(
        args.approve_four_short_rollouts
        and all(
            (
                args.result_root,
                args.credential_file,
                args.max_cost_usd,
                args.pricing_verified_on,
                args.implementation_hash,
            )
        ),
        "exact four-short-rollout approval is required",
    )
    print(
        canonical_json(
            run(
                plan,
                args.result_root,
                credential_file=args.credential_file,
                cap=args.max_cost_usd,
                pricing_verified_on=args.pricing_verified_on,
                approved_hash=args.implementation_hash,
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
