"""Four bounded voluntary-review continuations, separate from normal dev/resume.

Reuse the existing diagnostic dispatcher/reconciliation and the active gateway.
No default prompt, policy, task or historical diagnostic is modified.
"""
from __future__ import annotations

import argparse
import copy
import json
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from time import monotonic
from typing import Any

from diagnostics import counterexample_review as design
from diagnostics import decision_sampler as shared
from diagnostics import episode_requests as requests
from diagnostics import fresh_state_rollout as engine
from diagnostics import probe_first_rollout as recovery
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import runner as loop
from patchloop.dev.contracts import DevLimits, dev_tool_surface_hash
from patchloop.dev.conversation import history_metadata, reconstruct_state
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.environment import load_exact_openai_api_key
from patchloop.git_execution import run_git
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text, utc_now

SCHEMA = "counterexample-review-rollout-v1"
DESIGN = Path("C:/pt/analyses/counterexample-review-20260913")
DESIGN_HASH = "sha256:4203456c03746084ae6b21c957032d45deab511e1a6e05faac61eddee20baec0"
TASK = repository_root() / "tasks/dev-train/pyfakefs-makedirs-parent-traversal-v2"
ORDER = ("A1", "B1", "B2", "A2")
TOTAL_CAP = Decimal("2.00")
BRANCH_CAP = Decimal("0.50")
BOUNDARIES = engine.BOUNDARIES
INHERIT = frozenset(engine.KINDS) | {"repair_recheck_started", "repair_recheck_finished"}


def read(path: Path) -> dict:
    return json.loads(path.read_bytes())


def implementation_hashes() -> dict[str, str]:
    # Includes transitive diagnostic imports; active runtime bytes have their own identity.
    return {p.name: sha256_bytes(p.read_bytes())
            for p in sorted((repository_root() / "diagnostics").glob("*.py"))}


@dataclass(frozen=True)
class Plan:
    checkpoint: dict = field(repr=False)
    envelope: dict = field(repr=False)
    prefix: list[dict] = field(repr=False)
    initial_context: str = field(repr=False)
    arms: dict[str, dict] = field(repr=False)
    package: Any = field(repr=False)
    state: dict = field(repr=False)


def load_plan() -> Plan:
    shared.require(sha256_bytes((DESIGN / "packet.json").read_bytes()) == DESIGN_HASH,
                   "source design changed")
    design.validate(DESIGN)
    checkpoint = read(DESIGN / "checkpoint.json")
    source = Path(checkpoint["source_root"])
    journal = DevJournal(source, checkpoint["source_run_id"])
    events = journal.events()
    cutoff = events[checkpoint["cutoff_event_sequence"] - 1]
    shared.require(cutoff["event_hash"] == checkpoint["cutoff_event_hash"], "cutoff changed")
    envelope = journal.load_envelope().model_dump(mode="json")
    shared.require(envelope["limits"] == DevLimits().model_dump(mode="json")
                   and envelope["repair_recheck"] is True
                   and envelope["probe_profile_hash"] is not None,
                   "source limits/probe/recheck mismatch")
    package = load_task_package(TASK)
    arms = {arm: read(DESIGN / f"{arm}.json") for arm in ("A", "B")}
    state = reconstruct_state(arms["A"]["input"])
    shared.require(package.task_content_hash == checkpoint["task_content_hash"]
                   and package.public.model_dump(mode="json") == state["public_task"],
                   "task content mismatch")
    context = design.PublicStore(source / "artifacts").read_bytes(
        Artifact.model_validate(checkpoint["context_artifact"])).decode()
    return Plan(checkpoint, envelope, events[:checkpoint["prefix_event_count"]],
                context, arms, package, state)


def envelope_for(plan: Plan) -> dict:
    return {
        **BOUNDARIES, "schema_version": SCHEMA, "collector_implemented": True,
        "paid_execution_authorized": False, "source_design_hash": DESIGN_HASH,
        "implementation_hashes": implementation_hashes(), "runtime_hash": runtime_content_hash(),
        "tool_surface_hash": dev_tool_surface_hash(),
        "checkpoint": {k: plan.checkpoint[k] for k in (
            "source_run_id", "turn_id", "cutoff_event_hash", "original_request_hash")},
        "request_hashes": {arm: sha256_bytes(design.wire(r)) for arm, r in plan.arms.items()},
        "task_id": plan.package.public.task_id, "task_version": plan.package.public.task_version,
        "task_content_hash": plan.package.task_content_hash,
        "model": design.MODEL, "reasoning": "medium", "max_output_tokens": 25000,
        "context_policy": "append-v1", "compaction": False, "repair_recheck": True,
        "probe": {k: plan.envelope[k] for k in ("probe_image_digest", "probe_profile_hash")},
        "evaluator_image_digest": plan.envelope["evaluator_image_digest"],
        "credential_file": str((repository_root() / ".env").resolve()),
        "credential_path_hash": sha256_text(str((repository_root() / ".env").resolve())),
        "branch_order": list(ORDER), "samples_per_arm": 2, "new_calls_each": 8,
        "cap_usd_each": str(BRANCH_CAP), "cap_usd_total": str(TOTAL_CAP), "budget_transfer": False,
        "inherited_remaining_budget": plan.state["remaining_budget"],
        "maximum_experiment_wall_seconds": 1800, "request_waits": requests.WAITS.contract(),
        "pricing": design.protocol({"remaining_budget": plan.state["remaining_budget"]})["pricing"],
        "treatment": "one initial system suffix, retained unchanged; normal voluntary tools",
        "scheduler": "round-robin; branch cost/turn bounds censor only that branch; "
                     "uncertainty, unconfirmed cleanup and experiment deadline stop all",
    }


def fresh_root(root: Path, *protected: Path) -> Path:
    shared.require(root.is_absolute(), "absolute external root required")
    root = root.resolve()
    shared.require(not root.exists() and root.parent.is_dir()
                   and all(not root.is_relative_to(p.resolve())
                           and not p.resolve().is_relative_to(root) for p in protected),
                   "fresh disjoint external root required")
    return root


def prepare(root: Path) -> dict:
    plan = load_plan()
    root = fresh_root(root, repository_root(), DESIGN, Path(plan.checkpoint["source_root"]))
    envelope = envelope_for(plan)
    store = ArtifactStore(root)
    for arm, request in plan.arms.items():
        store.write_text_immutable(root / f"{arm}.json", design.wire(request).decode())
    store.write_text_immutable(root / "plan.json", canonical_json(envelope))
    return envelope


def validate(root: Path) -> tuple[Plan, dict]:
    plan = load_plan()
    expected = envelope_for(plan)
    shared.require(read(root / "plan.json") == expected, "executable packet changed")
    shared.require(all((root / f"{a}.json").read_bytes() == design.wire(r)
                       for a, r in plan.arms.items()), "executable request changed")
    return plan, expected


@dataclass
class Branch(recovery.Branch):
    inherited_accepted_mutations: int = 0
    diagnostic_schema = SCHEMA
    run_id_prefix = "run_dev_review_"

    def _forced_turn(self, turn_id):
        return False  # Reuse reconciliation, never the predecessor's forced-probe mask.

    def _sync_accounting(self):
        super()._sync_accounting()
        self.new_tools += len(self._new_events("repair_recheck_started"))

    def finish(self, code, message="", **details):
        if self.terminal is not None:
            return self.terminal
        # Finalization is read-only even after the execution deadline. A pending mutation
        # can make the actual worktree uncertain; never label this last receipt current.
        results = [e["payload"]["result"] for e in self.journal.events()
                   if e["event_type"] == "action_finished"]
        recorded_hash = next((r["workspace_diff_hash"] for r in reversed(results)
                              if r.get("workspace_diff_hash")), None)
        self.terminal = {
            **BOUNDARIES, "branch": self.label, "terminal": str(code), "message": message,
            "provider_calls": self.new_provider_calls, "tool_actions": self.new_tools,
            "cost_nanos": self.new_cost_nanos, "branch_active_ms": int(self.clock() * 1000),
            "accepted_mutations_since_checkpoint": (
                self.gateway.accepted_mutations - self.inherited_accepted_mutations),
            "last_recorded_diff_hash": recorded_hash,
            "recorded_visible_checks": self.gateway.visible_check_status(diff_hash=recorded_hash)
            if recorded_hash else [], **details,
        }
        self.journal.append("terminal", self.terminal)
        return self.terminal

    def _finish_batch(self):
        abort, _ = loop._batch_execution_abort(self.latest)
        if abort is not None:
            cleanup = any(r.output.get("cleanup_failed") for r in self.latest)
            raise engine.AbortExperiment("SANDBOX_CLEANUP_FAILED" if cleanup else str(abort))
        for result in self.latest:
            if result.status != "succeeded":
                continue
            if result.tool == "stop_task":
                self.finish("AGENT_STOPPED", result.output["summary"])
            elif result.tool == "finish_task":
                artifact = self.store.put_text(result.output["patch"], "text/x-diff")
                shared.require(artifact.content_hash == result.output["patch_hash"],
                               "submission identity mismatch")
                self.finish("PUBLIC_CHECKS_SUBMITTED",
                            submitted_artifact=artifact.model_dump(mode="json"))

    def project_request(self, request, context):
        """Diagnostic-only intervention before both artifacts are recorded."""
        suffix_count = request["input"][0]["content"].count(design.PROMPT_SUFFIX)
        if self.label.startswith("B") and suffix_count == 0:
            request["input"][0]["content"] += design.PROMPT_SUFFIX
            suffix_count = 1
        shared.require(suffix_count == int(self.label.startswith("B")), "instruction drift")
        return request, context, "review_instruction_recorded", {
            "arm": self.label[0], "suffix_count": suffix_count,
        }

    def prepare_request(self, package, adapter):
        self.reconcile()  # Recorded work first; uncertain provider calls are never retried.
        if self.terminal is not None:
            return None
        self.gateway.deadline.check()
        code, message = loop._run_repair_recheck(
            journal=self.journal, gateway=self.gateway, latest_results=self.latest,
            counters=self.counters, active_elapsed_ms=self.elapsed_ms)
        self._sync_accounting()
        if code is not None:
            raise engine.AbortExperiment(str(code))
        if self.new_provider_calls >= 8:
            self.finish("LIMIT_REACHED", "eight-response diagnostic bound", censored=True)
            return None
        projection = self.gateway.prepare_context_projection(latest_results=self.latest)
        snapshot = self.gateway.state_snapshot(projection=projection)
        policy = loop._tool_policy(self.gateway, self.counters, self.gateway.limits,
                                   snapshot=snapshot)
        if not policy.completion_possible:
            self.finish("LIMIT_REACHED", "completion horizon exhausted before provider dispatch",
                        completion_horizon=loop._completion_horizon_payload(
                            self.gateway, self.counters, self.gateway.limits, policy),
                        censored=True)
            return None
        transition = loop._tool_policy_transition(self.journal, policy)
        if self.initial_request is not None:
            request, context = copy.deepcopy(self.initial_request), self.initial_context
            expected = dev_tool_schemas(
                finish_enabled="finish_task" in policy.allowed_tools, check_ids=policy.check_ids,
                allowed_tools=policy.allowed_tools, read_paths=policy.targeted_read_paths)
            shared.require(request["tools"] == expected, "frozen policy/schema mismatch")
            self.initial_request = None
        else:
            context = loop._build_context(
                package=package, gateway=self.gateway, journal=self.journal,
                correction=self.correction, latest_tool_results=self.latest,
                counters=self.counters, elapsed_seconds=self.elapsed_ms() / 1000,
                limits=self.gateway.limits, policy=policy, snapshot=snapshot,
                projection=projection, tool_policy_transition=transition, repair_recheck=True)
            items = loop._build_model_input(journal=self.journal, artifact_store=self.store,
                                           context=context, latest_tool_results=self.latest)
            schemas = dev_tool_schemas(
                finish_enabled="finish_task" in policy.allowed_tools, check_ids=policy.check_ids,
                allowed_tools=policy.allowed_tools, read_paths=policy.targeted_read_paths)
            request = adapter.request_payload(items, schemas, system_prompt=loop.DEV_SYSTEM_PROMPT)
        request, context, event_kind, event_details = self.project_request(request, context)
        for key, value in shared.SETTINGS.items():
            shared.require(request.get(key) == value, "dispatch settings drift")
        shared.require(request["reasoning"] == {"effort": "medium"}, "reasoning drift")
        turn_id = "turn_" + uuid.uuid4().hex
        input_ref = self.store.put_text(design.wire(request["input"]).decode(), "application/json")
        context_ref = self.store.put_text(context, "application/json")
        self.journal.append("turn_started", {
            "turn_id": turn_id, "context_artifact": context_ref.model_dump(mode="json"),
            "context_hash": context_ref.content_hash,
            "model_input_artifact": input_ref.model_dump(mode="json"),
            "model_input_hash": input_ref.content_hash, "native_history": history_metadata(
                request["input"]), "available_tool_names": sorted(policy.allowed_tools),
            "workflow_gate": policy.workflow_gate, "max_parallel_reads": policy.max_parallel_reads,
            "targeted_read_paths": list(policy.targeted_read_paths),
            "active_elapsed_ms": self.elapsed_ms(),
        })
        self.journal.append(event_kind, {
            "turn_id": turn_id, **event_details,
            "request_hash": sha256_bytes(design.wire(request)),
            "tools_hash": sha256_bytes(design.wire(request["tools"])),
        })
        if transition:
            self.journal.append("tool_policy_transition", {"turn_id": turn_id, **transition})
        self.correction = None
        return turn_id, request, policy


def initialize_branch(plan, label, root, sandbox, probe, deadline, *, branch_class=Branch):
    branch_root = root / label
    store = ArtifactStore(branch_root / "artifacts")
    journal = DevJournal(branch_root, branch_class.run_id_prefix + uuid.uuid4().hex[:16])
    journal.append("diagnostic_branch_started", {
        **BOUNDARIES, "kind": branch_class.diagnostic_schema, "label": label,
        "source_run_id": plan.checkpoint["source_run_id"],
        "source_cutoff_event_hash": plan.checkpoint["cutoff_event_hash"],
        "inherited_events_are_not_new_execution": True,
    })
    sources = [design.PublicStore(Path(plan.checkpoint["source_root"]) / "artifacts")]
    for event in plan.prefix:
        if event["event_type"] in INHERIT:
            journal.append(event["event_type"], {
                **engine.import_artifacts(event["payload"], store, sources),
                "diagnostic_inherited": True, "source_event_hash": event["event_hash"],
            })
    workspace = branch_root / "workspaces" / journal.run_id / "repo"
    source = (Path(plan.checkpoint["source_root"]) / "workspaces"
              / plan.checkpoint["source_run_id"] / "repo")
    active = engine.ActiveClock()
    remaining = plan.state["remaining_budget"]["active_wall_time_seconds"]
    branch_deadline = engine.SharedDeadline(
        ExecutionDeadline.from_remaining(remaining, clock=active), deadline)
    with active.active():
        workspace.parent.mkdir(parents=True)
        run_git(workspace.parent, "clone", "--quiet", "--no-hardlinks", "--no-checkout",
                str(source), str(workspace), deadline=branch_deadline)
        run_git(workspace, "config", "core.longpaths", "true", deadline=branch_deadline)
        run_git(workspace, "checkout", "--quiet", "--detach", plan.envelope["base_commit"],
                deadline=branch_deadline)
        patch = store.put_text(plan.state["current_diff"]["patch"], "text/x-diff")
        WorkspaceManager.apply_patch(workspace, patch.path, deadline=branch_deadline)
        summary = WorkspaceManager.diff_summary(workspace, deadline=branch_deadline)
        shared.require(summary.patch_hash == plan.state["current_diff"]["patch_hash"]
                       and not summary.untracked_files, "isolated checkpoint differs")
        gateway = DevToolGateway(
            workspace=workspace, public_task=plan.package.public, sandbox=sandbox, journal=journal,
            limits=DevLimits(), probe_sandbox=probe, deadline=branch_deadline)
        counters = loop._restore_counters(journal)
        budget = plan.state["remaining_budget"]
        shared.require(counters.model_calls == gateway.limits.max_model_calls
                       - budget["model_calls"]
                       and counters.tool_actions == gateway.limits.max_tool_actions
                       - budget["tool_actions"] and gateway.accepted_mutations
                       == gateway.limits.max_accepted_mutations - budget["accepted_mutations"],
                       "inherited counters differ")
        shared.require(gateway.visible_check_status() == plan.state["visible_check_status"],
                       "inherited current checks differ")
        loop._validate_resumed_workspace(workspace, journal, deadline=branch_deadline)
        loop._validate_recorded_continuations(journal.events(), store)
    return branch_class(label, journal, store, gateway, counters, active, 1800 - remaining,
                        latest=journal.latest_tool_batch_results(),
                        initial_request=plan.arms[label[0]], initial_context=plan.initial_context,
                        inherited_accepted_mutations=gateway.accepted_mutations)


def uncertainty(branches):
    for branch in branches:
        if branch.journal.unresolved_provider_call() is not None or any(
            not e.get("billing_known", False) for e in branch._new_events("provider_call_finished")
        ):
            return "PROVIDER_TIMEOUT_OR_UNKNOWN"
    for branch in branches:
        finished = {e["count_id"] for e in branch._new_events("input_count_finished")}
        if any(e["count_id"] not in finished for e in branch._new_events("input_count_started")):
            return "COUNT_TIMEOUT_OR_UNKNOWN"
    return None


def drive(plan, branches, adapter_factory, *, checkpoint=lambda _: None, progress=lambda _: None,
          branch_cap=BRANCH_CAP, total_cap=TOTAL_CAP):
    """Same action space, isolated non-transferable ledgers, one sequential dispatch."""
    shared.require(branch_cap > 0 and branch_cap * len(branches) <= total_cap,
                   "non-transferable branch caps exceed the total")
    ledgers = {b.label: DevCostLedger(branch_cap, pricing_for_model(design.MODEL))
               for b in branches}
    terminal = "ROLLOUTS_COMPLETED"
    try:
        while any(b.terminal is None for b in branches):
            for branch in branches:
                if branch.terminal is not None:
                    continue
                with branch.clock.active(), branch.journal.execution_lock():
                    adapter = adapter_factory(shared.model_config("medium"))
                    shared.require(adapter.config == shared.model_config("medium")
                                   and adapter.client.max_retries == 0, "adapter contract drift")
                    prepared = branch.prepare_request(plan.package, adapter)
                    if prepared is not None:
                        ledgers[branch.label].spent_nanos = branch.new_cost_nanos
                        try:
                            engine.dispatch(branch, adapter, ledgers[branch.label], prepared,
                                            checkpoint=checkpoint, request_waits=requests.WAITS)
                        except engine.AbortExperiment as exc:
                            if exc.code != "COST_CAP_REACHED":
                                raise
                            branch.finish(exc.code, "branch cap exhausted; no budget transfer",
                                          censored=True)
                    progress({"branch": branch.label, "responses": branch.new_provider_calls,
                              "tools": branch.new_tools, "cost_nanos": branch.new_cost_nanos,
                              "terminal": branch.terminal and branch.terminal["terminal"]})
    except engine.AbortExperiment as exc:
        terminal = exc.code
    except ExecutionDeadlineExceeded:
        terminal = "LIMIT_REACHED"
    except (KeyboardInterrupt, SystemExit):
        terminal = "INTERRUPTED"
    except Exception:
        terminal = "ROLLOUT_ERROR"  # Never persist SDK exception text or raw reasoning.
    terminal = uncertainty(branches) or terminal
    for branch in branches:
        branch._sync_accounting()
        if branch.terminal is None:
            branch.finish(terminal, "experiment stopped; outcome censored", censored=True)
    spent = sum(b.new_cost_nanos for b in branches)
    shared.require(spent <= int(total_cap * 1_000_000_000), "shared cap violated")
    return {
        **BOUNDARIES, "terminal": terminal, "branches": [b.terminal for b in branches],
        "new_provider_calls": sum(b.new_provider_calls for b in branches),
        "new_input_count_calls": sum(len(b._new_events("input_count_started")) for b in branches),
        "new_tool_actions": sum(b.new_tools for b in branches), "recorded_cost_nanos": spent,
        "provider_cost_known": uncertainty(branches) != "PROVIDER_TIMEOUT_OR_UNKNOWN",
        "count_billing_and_invoice": "UNVERIFIED",
    }


def run(plan_root, result_root, *, approval_packet_hash, credential_file, cap,
        pricing_verified_on, adapter_factory=None, sandbox=None, probe=None,
        checkpoint=lambda _: None, progress=lambda _: None):
    plan, envelope = validate(plan_root)
    shared.require(approval_packet_hash == sha256_bytes((plan_root / "plan.json").read_bytes()),
                   "exact executable packet approval required")
    shared.require(cap == TOTAL_CAP and credential_file.resolve() == repository_root() / ".env",
                   "exact cap/credential path required")
    shared.require(pricing_verified_on == utc_now().date().isoformat(),
                   "price review date mismatch")
    root = fresh_root(result_root, repository_root(), DESIGN, plan_root,
                      Path(plan.checkpoint["source_root"]))
    root.mkdir()  # Exclusive one-shot admission; no resume or reuse of this result directory.
    store = ArtifactStore(root)
    observer = DevJournal(root, "run_dev_review_observer")
    deadline = ExecutionDeadline.from_remaining(1800)
    client, branches, result = None, [], None
    started = monotonic()
    with observer.execution_lock():
        store.write_text_immutable(root / "envelope.json", canonical_json({
            **envelope, "approval_packet_hash": approval_packet_hash,
            "pricing_verified_on": pricing_verified_on,
            "provider_free": adapter_factory is not None,
        }))
        observer.append("diagnostic_execution_started", {
            "packet_hash": approval_packet_hash, "provider_free": adapter_factory is not None,
        })
        try:
            if adapter_factory is None:
                loop._live_source_preflight(TASK, plan.package, deadline=deadline)
                loop._require_tracked_clean_paths(repository_root(),
                    ["diagnostics/" + name for name in implementation_hashes()], deadline=deadline)
                sandbox = loop._live_sandbox_preflight(plan.package, deadline=deadline)
                probe = DockerProbeSandbox()
                identity = probe.preflight(deadline=deadline)
                shared.require(identity["image_digest"] == plan.envelope["probe_image_digest"]
                               and identity["profile_hash"] == plan.envelope["probe_profile_hash"],
                               "probe identity mismatch")
            shared.require(sandbox is not None and probe is not None,
                           "registered backends required")
            for label in ORDER:
                branches.append(initialize_branch(plan, label, root, sandbox, probe, deadline))

            def adapter(config):
                nonlocal client
                if adapter_factory is not None:
                    return adapter_factory(config)
                if client is None:
                    key = load_exact_openai_api_key(credential_file)
                    client = requests.DiagnosticClient(api_key=key)
                    del key
                return OpenAIResponsesAdapter(config, api_key="", client=client)

            def progress_record(value):
                observer.append("diagnostic_branch_progress", value)
                progress(value)

            result = drive(plan, branches, adapter, checkpoint=checkpoint, progress=progress_record)
        except (Exception, KeyboardInterrupt, SystemExit):
            code = uncertainty(branches) or (
                "ROLLOUT_ERROR" if any(b.new_provider_calls for b in branches)
                else "PREFLIGHT_OR_INITIALIZATION_FAILED")
            for branch in branches:
                branch.finish(code, censored=True)
            result = {**BOUNDARIES, "terminal": code,
                      "branches": [b.terminal for b in branches],
                      "recorded_cost_nanos": sum(b.new_cost_nanos for b in branches),
                      "provider_cost_known": code != "PROVIDER_TIMEOUT_OR_UNKNOWN"}
        finally:
            if client is not None:
                try:
                    client.close(timeout=requests.WAITS.client_cleanup_seconds)
                except (Exception, KeyboardInterrupt, SystemExit):
                    if result["terminal"] not in {
                        "PROVIDER_TIMEOUT_OR_UNKNOWN", "COUNT_TIMEOUT_OR_UNKNOWN",
                    }:
                        result["terminal"] = "CLIENT_CLEANUP_UNCONFIRMED"
        result["elapsed_ms"] = int((monotonic() - started) * 1000)
        result["provider_free"] = adapter_factory is not None
        observer.append("diagnostic_execution_finished", result)
        store.write_text_immutable(root / "result.json", canonical_json(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "validate", "run"])
    parser.add_argument("--plan-root", type=Path, required=True)
    parser.add_argument("--result-root", type=Path)
    parser.add_argument("--approval-packet-hash")
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--max-cost-usd", type=Decimal)
    parser.add_argument("--pricing-verified-on")
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.plan_root)
    elif args.command == "validate":
        result = validate(args.plan_root)[1]
    else:
        shared.require(all((args.result_root, args.approval_packet_hash, args.credential_file,
                            args.max_cost_usd, args.pricing_verified_on)),
                       "exact run inputs required")
        result = run(args.plan_root, args.result_root,
                     approval_packet_hash=args.approval_packet_hash,
                     credential_file=args.credential_file, cap=args.max_cost_usd,
                     pricing_verified_on=args.pricing_verified_on,
                     progress=lambda p: print(canonical_json(p), flush=True))
    print(canonical_json(result))


if __name__ == "__main__":
    main()
