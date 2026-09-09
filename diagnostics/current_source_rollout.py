"""Bounded current-source presentation A/B, not normal dev resume or evaluation.

A preserves current native source references; B inlines exactly those selected
bodies in each new current-state view. Both retain the complete native prefix.
Four fresh branches share one cost ledger; no paid retry or resume exists.
"""

from __future__ import annotations

import argparse
import copy
import json
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from time import monotonic
from typing import Any

from diagnostics import current_source_view as view
from diagnostics import decision_sampler as shared
from diagnostics import failure_order_sampler as frozen
from diagnostics import fresh_state_rollout as common
from patchloop.agent.model import OpenAIResponsesAdapter, create_openai_client
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import runner as loop
from patchloop.dev.contracts import DevLimits, dev_tool_surface_hash
from patchloop.dev.conversation import (
    CONVERSATION_INSTRUCTIONS,
    history_metadata,
    reconstruct_state,
    validate_model_input,
)
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.git_execution import run_git
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text, utc_now

SOURCE = Path("C:/patchloop-state")
AUDIT = Path("C:/pt/pl43-decision-a")
PROTOTYPE = Path("C:/pt/pl-fix-source-view-a")
REQUEST = Path("C:/pt/pl43-order-design-a/objects/sha256/b3/"
               "5803e978909bb0369f34a91637b29a086435b5208869bf04742f0e36e55fc0")
REQUEST_HASH = "sha256:b35803e978909bb0369f34a91637b29a086435b5208869bf04742f0e36e55fc0"
EXECUTING_RUNTIME = "sha256:a3d7f3c00ffc7d534b434eb197366da241228d4906d997084b9d8094c39526f1"
TASK = repository_root() / "tasks/dev-train/pyfakefs-makedirs-parent-traversal-v2"
SCHEMA = "current-source-short-rollout-v1"
ORDER = ("A1", "B1", "B2", "A2")
BOUNDARIES = common.BOUNDARIES


def implementation_files() -> list[Path]:
    # Bind every imported diagnostic dependency, in addition to the runtime hash.
    return sorted((repository_root() / "diagnostics").glob("*.py"))


def implementation_hash() -> str:
    return sha256_json({p.name: sha256_bytes(p.read_bytes()) for p in implementation_files()})


@dataclass(frozen=True)
class Plan:
    manifest: dict = field(repr=False)
    envelope: dict = field(repr=False)
    prefix: list[dict] = field(repr=False)
    started: dict = field(repr=False)
    requests: dict = field(repr=False)
    context: str = field(repr=False)
    public_state: dict = field(repr=False)
    package: Any = field(repr=False)
    metrics: dict


def load_plan() -> Plan:
    """Validate historical input separately from the current executing runtime."""
    shared.require(runtime_content_hash() == EXECUTING_RUNTIME, "execution runtime changed")
    for name, digest in frozen.AUDIT_HASHES.items():
        shared.require(sha256_bytes((AUDIT / name).read_bytes()) == digest, "audit changed")
    manifest = json.loads((AUDIT / "checkpoint-manifest.json").read_bytes())
    for name, suffix in (("journal", ".jsonl"), ("envelope", ".envelope.json")):
        path = SOURCE / "runs" / (manifest["run_id"] + suffix)
        shared.require(path.resolve() == Path(manifest[name]["path"]).resolve(),
                       "source path mismatch")
        shared.require(sha256_bytes(path.read_bytes()) == manifest[name]["content_hash"],
                       "historical evidence changed")
    envelope = json.loads(Path(manifest["envelope"]["path"]).read_bytes())
    shared.require(manifest["runtime_hash"] == envelope["runtime_hash"]
                   and manifest["model_hash"] == envelope["model_hash"], "source envelope mismatch")
    events = DevJournal(SOURCE, manifest["run_id"]).events()
    cutoff = events[manifest["cutoff_event_sequence"] - 1]
    started = cutoff["payload"]
    shared.require(cutoff["event_type"] == "turn_started"
                   and cutoff["event_hash"] == manifest["cutoff_event_hash"]
                   and started["turn_id"] == manifest["turn_id"], "cutoff mismatch")
    raw = REQUEST.read_bytes()
    shared.require(sha256_bytes(raw) == REQUEST_HASH, "frozen request changed")
    request = json.loads(raw)
    shared.require(view.wire(request) == raw, "request wire order changed")
    items = json.loads(shared.read_source_artifact(SOURCE, manifest["native_input_artifact"]))
    validate_model_input(items, started["native_history"])
    shared.require(request["input"] == items, "request is not the selected native checkpoint")
    shared.require(items[0]["content"] == loop.DEV_SYSTEM_PROMPT + "\n" + CONVERSATION_INSTRUCTIONS,
                   "system prompt changed")
    for key, value in shared.SETTINGS.items():
        shared.require(request.get(key) == value, "model request settings changed")
    shared.require(request["reasoning"] == {"effort": "medium"}, "reasoning setting changed")
    state = reconstruct_state(items)
    context = shared.read_source_artifact(SOURCE, manifest["context_artifact"]).decode()
    original_context = json.loads(context)
    for key in ("public_task", "current_diff", "remaining_budget", "visible_check_status",
                "current_public_failure", "available_tool_names"):
        shared.require(state[key] == original_context[key], "source state mismatch")
    shared.require(state["current_diff"]["patch_hash"] == manifest["current_diff_hash"],
                   "checkpoint diff mismatch")
    schemas = dev_tool_schemas(
        finish_enabled="finish_task" in started["available_tool_names"],
        check_ids=[c["check_id"] for c in state["visible_check_status"]
                   if c["status"] == "NOT_RUN"],
        allowed_tools=started["available_tool_names"], read_paths=started["targeted_read_paths"],
    )
    shared.require(request["tools"] == schemas, "tool schema or order changed")
    metrics = view.validate(PROTOTYPE)
    alternate, actual_metrics = view.inline_current_sources(request)
    shared.require(actual_metrics == metrics, "prototype differs from frozen treatment")
    prefix = events[: cutoff["sequence"] - 1]
    prior_ids = [e["payload"]["action_id"] for e in prefix
                 if e["event_type"] == "action_finished"]
    call_ids = [i["call_id"] for i in items if i.get("type") == "function_call"]
    shared.require(call_ids == prior_ids == started["transcript_action_ids"],
                   "native action order crosses cutoff")
    package = load_task_package(TASK)
    shared.require(package.task_content_hash == envelope["task_content_hash"]
                   and package.public.model_dump(mode="json") == state["public_task"],
                   "task content mismatch")
    shared.require(envelope["model"] == shared.MODEL
                   and envelope["reasoning_effort"] == "medium"
                   and envelope["limits"] == DevLimits().model_dump(mode="json"),
                   "source model or limits mismatch")
    shared.require(state["remaining_budget"]["model_calls"] == 20
                   and state["remaining_budget"]["tool_actions"] == 80
                   and state["remaining_budget"]["accepted_mutations"] == 1,
                   "unexpected checkpoint budget")
    return Plan(manifest, envelope, prefix, started, {"A": request, "B": alternate},
                context, state, package, metrics)


def clone_checkpoint(plan: Plan, destination: Path, store: ArtifactStore,
                     deadline: ExecutionDeadline) -> None:
    source = SOURCE / "workspaces" / plan.manifest["run_id"] / "repo"
    shared.require(source.is_dir() and not destination.exists(), "checkpoint workspace missing")
    destination.parent.mkdir(parents=True, exist_ok=True)
    run_git(destination.parent, "clone", "--quiet", "--no-hardlinks", "--no-checkout",
            str(source), str(destination), deadline=deadline)
    run_git(destination, "config", "core.longpaths", "true", deadline=deadline)
    run_git(destination, "checkout", "--quiet", "--detach", plan.envelope["base_commit"],
            deadline=deadline)
    patch = store.put_text(plan.public_state["current_diff"]["patch"], "text/x-diff")
    WorkspaceManager.apply_patch(destination, patch.path, deadline=deadline)
    summary = WorkspaceManager.diff_summary(destination, deadline=deadline)
    shared.require(summary.patch_hash == plan.manifest["current_diff_hash"]
                   and not summary.untracked_files, "isolated checkpoint differs")
    for group in plan.public_state["current_sources"]:
        shared.require(sha256_bytes((destination / group["path"]).read_bytes())
                       == group["file_hash"], "checkpoint source bytes differ")


@dataclass
class Branch(common.Branch):
    initial_request: dict | None = field(default=None, repr=False)
    initial_context: str = field(default="", repr=False)

    def prepare_request(self, package: Any, adapter: Any):
        self.gateway.deadline.check()
        if self.new_provider_calls >= 8:
            self.finish("LIMIT_REACHED", "eight-response diagnostic bound reached", censored=True)
            return None
        projection = self.gateway.prepare_context_projection(latest_results=self.latest)
        snapshot = self.gateway.state_snapshot(projection=projection)
        policy = loop._tool_policy(self.gateway, self.counters, self.gateway.limits,
                                   snapshot=snapshot)
        if not policy.completion_possible:
            self.finish("LIMIT_REACHED", "completion horizon exhausted before provider dispatch",
                        completion_horizon=loop._completion_horizon_payload(
                            self.gateway, self.counters, self.gateway.limits, policy))
            return None
        transition = loop._tool_policy_transition(self.journal, policy)
        if self.initial_request is not None:
            request = copy.deepcopy(self.initial_request)
            context = self.initial_context
            shared.require({s["name"] for s in request["tools"]} == set(policy.allowed_tools),
                           "current policy differs at frozen first dispatch")
            self.initial_request = None
        else:
            context = loop._build_context(
                package=package, gateway=self.gateway, journal=self.journal,
                correction=self.correction, latest_tool_results=self.latest,
                counters=self.counters, elapsed_seconds=self.elapsed_ms() / 1000,
                limits=self.gateway.limits, policy=policy, snapshot=snapshot,
                projection=projection, tool_policy_transition=transition,
            )
            items = loop._build_model_input(journal=self.journal, artifact_store=self.store,
                                           context=context, latest_tool_results=self.latest)
            schemas = dev_tool_schemas(
                finish_enabled="finish_task" in policy.allowed_tools, check_ids=policy.check_ids,
                allowed_tools=policy.allowed_tools, read_paths=policy.targeted_read_paths,
            )
            request = adapter.request_payload(items, schemas, system_prompt=loop.DEV_SYSTEM_PROMPT)
            request["parallel_tool_calls"], request["tool_choice"] = True, "required"
        # The first request is frozen A for both arms; subsequent A follows normal
        # projection. B changes only this new state's selected source presentation.
        alternate, metrics = view.inline_current_sources(request)
        if self.label.startswith("B"):
            request = alternate
        for key, value in shared.SETTINGS.items():
            shared.require(request.get(key) == value, "dispatch settings drift")
        shared.require(request.get("reasoning") == {"effort": "medium"}, "effort drift")
        turn_id = "turn_" + uuid.uuid4().hex
        input_ref = self.store.put_text(view.wire(request["input"]).decode(), "application/json")
        context_ref = self.store.put_text(context, "application/json")
        self.journal.append("turn_started", {
            "turn_id": turn_id, "context_artifact": context_ref.model_dump(mode="json"),
            "context_hash": context_ref.content_hash,
            "model_input_artifact": input_ref.model_dump(mode="json"),
            "model_input_hash": input_ref.content_hash,
            "native_history": history_metadata(request["input"]),
            "available_tool_names": sorted(policy.allowed_tools),
            "workflow_gate": policy.workflow_gate, "max_parallel_reads": policy.max_parallel_reads,
            "targeted_read_paths": list(policy.targeted_read_paths),
            "active_elapsed_ms": self.elapsed_ms(),
        })
        self.journal.append("source_presentation_recorded", {
            "turn_id": turn_id, "arm": self.label[0], "treatment_applied": self.label[0] == "B",
            "input_hash": input_ref.content_hash, "context_is_pre_treatment": True, **metrics,
        })
        if transition:
            self.journal.append("tool_policy_transition", {"turn_id": turn_id, **transition})
        self.correction = None
        return turn_id, request, policy


def initialize_branch(plan: Plan, label: str, root: Path, sandbox: Any, probe: Any,
                      deadline: ExecutionDeadline) -> Branch:
    branch_root = root / label
    store = ArtifactStore(branch_root / "artifacts")
    journal = DevJournal(branch_root, "run_dev_source_" + uuid.uuid4().hex[:16])
    journal.append("diagnostic_branch_started", {
        **BOUNDARIES, "kind": SCHEMA, "label": label,
        "source_run_id": plan.manifest["run_id"],
        "source_prefix_last_event_hash": plan.prefix[-1]["event_hash"],
        "source_runtime_hash": plan.envelope["runtime_hash"],
        "executing_runtime_hash": EXECUTING_RUNTIME,
        "inherited_events_are_not_new_execution": True,
    })
    sources = [common.readonly_store(SOURCE / "artifacts")]
    for event in plan.prefix:
        if event["event_type"] in common.KINDS:
            journal.append(event["event_type"], {
                **common.import_artifacts(event["payload"], store, sources),
                "diagnostic_inherited": True, "source_event_hash": event["event_hash"],
            })
    workspace = branch_root / "workspaces" / journal.run_id / "repo"
    clone_checkpoint(plan, workspace, store, deadline)
    active = common.ActiveClock()
    remaining = plan.public_state["remaining_budget"]["active_wall_time_seconds"]
    gateway = DevToolGateway(
        workspace=workspace, public_task=plan.package.public, sandbox=sandbox, journal=journal,
        limits=DevLimits(), probe_sandbox=probe,
        deadline=common.SharedDeadline(ExecutionDeadline.from_remaining(remaining, clock=active),
                                       deadline),
    )
    counters = loop._restore_counters(journal)
    shared.require(counters.model_calls == 20 and counters.tool_actions == 20
                   and gateway.accepted_mutations == 3, "checkpoint counters differ")
    loop._validate_resumed_workspace(workspace, journal, deadline=deadline)
    loop._validate_recorded_continuations(journal.events(), store)
    return Branch(label, journal, store, gateway, counters, active, 1800 - remaining,
                  latest=journal.latest_tool_batch_results(),
                  initial_request=plan.requests["A"], initial_context=plan.context)


def envelope_for(plan: Plan) -> dict:
    return {
        **BOUNDARIES, "kind": SCHEMA, "implementation_hash": implementation_hash(),
        "executing_runtime_hash": EXECUTING_RUNTIME, "tool_surface_hash": dev_tool_surface_hash(),
        "source_runtime_hash": plan.envelope["runtime_hash"],
        "source_journal_hash": plan.manifest["journal"]["content_hash"],
        "source_envelope_hash": plan.manifest["envelope"]["content_hash"],
        "evaluator_image_digest": plan.envelope["evaluator_image_digest"],
        "probe_image_digest": plan.envelope["probe_image_digest"],
        "probe_profile_hash": plan.envelope["probe_profile_hash"],
        "cutoff_event_hash": plan.manifest["cutoff_event_hash"],
        "request_hashes": {a: sha256_bytes(view.wire(r)) for a, r in plan.requests.items()},
        "task_id": plan.package.public.task_id, "task_version": plan.package.public.task_version,
        "task_content_hash": plan.package.task_content_hash,
        "model": shared.MODEL, "reasoning": "medium", "store": False,
        "credential_path_hash": sha256_text(str((repository_root() / ".env").resolve())),
        "cap_nanos": 1_200_000_000, "pricing": shared.price_identity(), "output_ceiling": 25000,
        "branches": list(ORDER), "maximum_new_responses_each": 8,
        "remaining_budget": plan.public_state["remaining_budget"],
        "experiment_wall_time_seconds": 1800,
        "schedule": "round-robin A1 B1 B2 A2; skip terminal branches",
        "cap_policy": "shared JIT full-25k-ceiling admission; no guaranteed completion reserve",
        "treatment": "B inlines selected current_sources in each new view; native prefix unchanged",
        "source_metrics": plan.metrics,
    }


def prepare(root: Path) -> dict:
    root = root.resolve()
    shared.require(root.parent.is_dir() and not root.exists()
                   and not root.is_relative_to(repository_root())
                   and not root.is_relative_to(SOURCE), "fresh external preparation root required")
    plan = load_plan()
    envelope = envelope_for(plan)
    store = ArtifactStore(root)
    for arm, request in plan.requests.items():
        store.write_text_immutable(root / f"{arm}.json", view.wire(request).decode())
    store.write_text_immutable(root / "plan.json", canonical_json(envelope))
    return envelope


def run(plan_root: Path, root: Path, *, credential_file: Path, cap: Decimal,
        pricing_verified_on: str, adapter_factory=None, sandbox=None, probe=None,
        checkpoint=lambda _: None, progress=lambda _: None) -> dict:
    plan = load_plan()
    expected = envelope_for(plan)
    shared.require(json.loads((plan_root / "plan.json").read_bytes()) == expected,
                   "prepared experiment changed")
    for arm, request in plan.requests.items():
        shared.require((plan_root / f"{arm}.json").read_bytes() == view.wire(request),
                       "prepared request changed")
    shared.require(cap == Decimal("1.20"), "one shared $1.20 cap required")
    shared.require(pricing_verified_on == utc_now().date().isoformat(),
                   "price review date mismatch")
    shared.require(credential_file.resolve() == repository_root() / ".env", "credential path drift")
    root = root.resolve()
    protected = [SOURCE, AUDIT, PROTOTYPE, REQUEST.parents[3], repository_root(), plan_root]
    shared.require(not root.exists() and root.parent.is_dir()
                   and all(not root.is_relative_to(p.resolve())
                           and not p.resolve().is_relative_to(root) for p in protected),
                   "new disjoint external result root required")
    deadline = ExecutionDeadline.from_remaining(1800)
    if adapter_factory is None:
        loop._live_source_preflight(TASK, plan.package, deadline=deadline)
        loop._require_tracked_clean_paths(repository_root(),
                                         [p.relative_to(repository_root()).as_posix()
                                          for p in implementation_files()], deadline=deadline)
        sandbox = loop._live_sandbox_preflight(plan.package, deadline=deadline)
        probe = DockerProbeSandbox()
        identity = probe.preflight(deadline=deadline)
        shared.require(identity["image_digest"] == plan.envelope["probe_image_digest"]
                       and identity["profile_hash"] == plan.envelope["probe_profile_hash"],
                       "probe identity mismatch")
    shared.require(sandbox is not None and probe is not None, "registered backends required")
    store = ArtifactStore(root)
    ledger = DevCostLedger(cap, pricing_for_model(shared.MODEL))
    store.write_text_immutable(root / "envelope.json", canonical_json({
        **expected, "pricing_verified_on": pricing_verified_on,
        "provider_free": adapter_factory is not None,
    }))
    branches, client, terminal = [], None, "ROLLOUTS_COMPLETED"
    started = monotonic()
    try:
        for label in ORDER:
            branches.append(initialize_branch(plan, label, root, sandbox, probe, deadline))
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
                    shared.require(adapter.config == config and adapter.client.max_retries == 0,
                                   "adapter contract drift")
                    prepared = branch.prepare_request(plan.package, adapter)
                    if prepared is not None:
                        common.dispatch(branch, adapter, ledger, prepared, checkpoint=checkpoint)
                    progress({"branch": branch.label, "responses": branch.new_provider_calls,
                              "tools": branch.new_tools, "cost_nanos": ledger.spent_nanos,
                              "terminal": branch.terminal and branch.terminal["terminal"]})
    except common.AbortExperiment as exc:
        terminal = exc.code
    except ExecutionDeadlineExceeded:
        terminal = "LIMIT_REACHED"
    except (KeyboardInterrupt, SystemExit):
        terminal = "INTERRUPTED"
    except Exception as exc:
        terminal = "ROLLOUT_ERROR"
        store.write_text_immutable(root / "error.json", canonical_json({
            "error_type": type(exc).__name__,
        }))  # Never serialize provider exception text or raw reasoning.
    finally:
        if client is not None:
            with suppress(Exception):
                client.close()
    unknown = any(b.journal.unresolved_provider_call() is not None or any(
        e["event_type"] == "provider_call_finished" and e["payload"].get("billing_known") is False
        for e in b.journal.events()) for b in branches)
    if unknown:
        terminal = "PROVIDER_TIMEOUT_OR_UNKNOWN"
    for branch in branches:
        if branch.terminal is None:
            branch.finish(terminal, "experiment stopped; outcome censored", censored=True)
    result = {
        **BOUNDARIES, "terminal": terminal, "branches": [b.terminal for b in branches],
        "new_provider_calls": sum(b.new_provider_calls for b in branches),
        "new_input_count_calls": sum(e["event_type"] == "input_count_started"
                                     and not e["payload"].get("diagnostic_inherited")
                                     for b in branches for e in b.journal.events()),
        "new_tool_actions": sum(b.new_tools for b in branches),
        "recorded_cost_nanos": ledger.spent_nanos, "total_cost_known": not unknown,
        "elapsed_ms": int((monotonic() - started) * 1000),
    }
    store.write_text_immutable(root / "result.json", canonical_json(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "prepare", "run"])
    parser.add_argument("--plan-root", type=Path)
    parser.add_argument("--result-root", type=Path)
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--max-cost-usd", type=Decimal)
    parser.add_argument("--pricing-verified-on")
    args = parser.parse_args()
    if args.command == "validate":
        result = envelope_for(load_plan())
    elif args.command == "prepare":
        shared.require(args.plan_root is not None, "plan root required")
        result = prepare(args.plan_root)
    else:
        shared.require(all((args.plan_root, args.result_root, args.credential_file,
                            args.max_cost_usd, args.pricing_verified_on)), "exact inputs required")
        result = run(args.plan_root, args.result_root, credential_file=args.credential_file,
                     cap=args.max_cost_usd, pricing_verified_on=args.pricing_verified_on,
                     progress=lambda p: print(canonical_json(p), flush=True))
    print(canonical_json(result))


if __name__ == "__main__":
    main()
