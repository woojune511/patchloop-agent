"""Run the frozen probe-first repair comparison, without changing normal dev-head.

The first B probe is model authored. Its real native feedback releases the phase;
all later input projection, tools and budgets use the ordinary loop. No paid resume,
operator repair hints, private evaluation, or automatic Docker startup/pull/build.
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from diagnostics import current_source_rollout as source
from diagnostics import probe_first_view as view
from patchloop.dev.contracts import DevModelTurn
from patchloop.dev.tools import validate_tool_batch
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes

common, shared, loop = source.common, source.shared, source.loop
DESIGN = Path("C:/pt/pl43-probe-first-design-a")
SCHEMA = "probe-first-short-rollout-v1"


def load_plan() -> source.Plan:
    manifest = view.validate(DESIGN)
    plan = source.load_plan()
    raw = view.wire(plan.requests["A"])
    shared.require(sha256_bytes(raw) == manifest["source_hash"]
                   and raw == (DESIGN / "A.json").read_bytes(), "probe seed mismatch")
    return replace(plan, requests={"A": plan.requests["A"],
                                   "B": json.loads((DESIGN / "B.json").read_bytes())},
                   metrics=manifest)


def envelope_for(plan: source.Plan) -> dict:
    envelope = source.envelope_for(plan)
    envelope.pop("source_metrics")
    return {
        **envelope, "kind": SCHEMA,
        "design_manifest_hash": sha256_bytes((DESIGN / "manifest.json").read_bytes()),
        "probe_first_metrics": plan.metrics,
        "treatment": "B forces one model-authored probe attempt, then ordinary loop",
        "collector_implemented": True,
        "source_design_protocol": view.design_contract(plan.metrics),
    }


def _fresh_root(root: Path, *protected: Path) -> Path:
    root = root.resolve()
    shared.require(not root.exists() and root.parent.is_dir() and all(
        not root.is_relative_to(p.resolve()) and not p.resolve().is_relative_to(root)
        for p in (source.repository_root(), source.SOURCE, source.AUDIT,
                  source.PROTOTYPE, source.REQUEST.parents[3], DESIGN, *protected)),
        "fresh disjoint external root required")
    return root


def prepare(root: Path) -> dict:
    root = _fresh_root(root)
    plan = load_plan()
    envelope = envelope_for(plan)
    store = source.ArtifactStore(root)
    for arm, request in plan.requests.items():
        store.write_text_immutable(root / f"{arm}.json", view.wire(request).decode())
    store.write_text_immutable(root / "plan.json", canonical_json(envelope))
    return envelope


class Branch(source.Branch):
    def _new_events(self, kind: str) -> list[dict]:
        return [e["payload"] for e in self.journal.events()
                if e["event_type"] == kind and not e["payload"].get("diagnostic_inherited")]

    def _probe_batch(self) -> dict | None:
        probes = {e["action_id"] for e in self._new_events("action_finished")
                  if e["result"]["tool"] == "run_probe"}
        return next((b for b in self._new_events("tool_batch_finished")
                     if probes.intersection(b["action_ids"])), None)

    def _forced_turn(self, turn_id: str) -> bool:
        return next((e["forced_probe"] for e in self._new_events("probe_choice_recorded")
                     if e["turn_id"] == turn_id), False)

    def transform_request(self, request: dict, policy: Any) -> tuple[dict, str, dict]:
        shared.require(request.get("tool_choice") == "required", "ordinary choice drift")
        forced = self.label.startswith("B") and self._probe_batch() is None
        original = request
        if forced:
            shared.require("run_probe" in policy.allowed_tools, "probe phase no longer viable")
            request = copy.deepcopy(request)
            request["tool_choice"] = dict(view.FORCED_PROBE)
        return request, "probe_choice_recorded", {
            "arm": self.label[0], "forced_probe": forced,
            "tool_choice": request["tool_choice"],
            "ordinary_request_hash": sha256_bytes(view.wire(original)),
            "dispatched_request_hash": sha256_bytes(view.wire(request)),
            "unchanged_input_hash": sha256_bytes(view.wire(request["input"])),
            "unchanged_tools_hash": sha256_bytes(view.wire(request["tools"])),
        }

    def _sync_accounting(self) -> None:
        self.counters = loop._restore_counters(self.journal)
        self.new_provider_calls = len(self._new_events("provider_call_started"))
        self.new_tools = sum(len(e["tool_calls"]) for e in self._new_events("tool_batch_started"))
        self.new_cost_nanos = sum(e.get("cost_nanos") or 0
                                 for e in self._new_events("provider_call_finished"))
        self.latest = self.journal.latest_tool_batch_results()
        self.correction = loop._pending_protocol_correction(self.journal)

    def _finish_batch(self) -> None:
        abort, _ = loop._batch_execution_abort(self.latest)
        if abort is not None:
            code = ("SANDBOX_CLEANUP_FAILED" if any(r.output.get("cleanup_failed")
                                                  for r in self.latest)
                    else "LIMIT_REACHED" if str(abort) == "LIMIT_REACHED"
                    else "TOOL_RECOVERY_ERROR")
            raise common.AbortExperiment(code)
        batch = self._probe_batch()
        if self.label.startswith("B") and batch and not self._new_events("probe_phase_released"):
            self.journal.append("probe_phase_released", {
                "turn_id": batch["turn_id"], "action_ids": batch["action_ids"],
                "reason": "first probe batch has durable native feedback",
            })
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

    def accept(self, turn_id: str, turn: DevModelTurn, policy: Any, checkpoint=lambda _: None):
        """Admit the recorded action mask; replay only the same durable decision/batch."""
        payload = {"turn_id": turn_id, **turn.model_dump(mode="json")}
        previous = next((e for e in self._new_events("turn_decision_recorded")
                         if e["turn_id"] == turn_id), None)
        if previous is None:
            self.journal.append("turn_decision_recorded", payload)
        else:
            shared.require(previous == payload, "decision replay mismatch")
        checkpoint("decision_recorded")
        if turn.error_code == "provider_continuation_error":
            raise common.AbortExperiment("PROVIDER_CONTINUATION_ERROR")
        if self._forced_turn(turn_id):
            policy = replace(policy, allowed_tools=frozenset({"run_probe"}))
        issue = (loop._model_error_issue(turn.error_code, turn.incomplete_reason,
                                         turn.tool_contract_failure) if turn.error_code else None)
        if issue is None:
            try:
                validate_tool_batch(turn.tool_calls, max_parallel_reads=policy.max_parallel_reads,
                                    allowed_tools=policy.allowed_tools,
                                    allowed_read_paths=policy.targeted_read_paths)
            except ContractError as exc:
                issue = str(exc)
        if issue is not None:
            if self.counters.protocol_recoveries >= self.gateway.limits.max_protocol_recoveries:
                return self.finish("PROTOCOL_VIOLATION", issue)
            self.counters.protocol_recoveries += 1
            self.correction = loop._protocol_correction(
                turn_id=turn_id, code=turn.error_code or "INVALID_TOOL_BATCH", issue=issue,
                gateway=self.gateway, policy=policy,
                tool_contract_failure=turn.tool_contract_failure)
            self.journal.append("protocol_correction", self.correction)
            return None
        started = next((e for e in self._new_events("tool_batch_started")
                        if e["turn_id"] == turn_id), None)
        calls = [c.model_dump(mode="json") for c in turn.tool_calls]
        if started is None:
            shared.require(self.counters.tool_actions + len(calls)
                           <= self.gateway.limits.max_tool_actions, "tool budget exceeded")
            self.journal.append("tool_batch_started", {
                "turn_id": turn_id, "tool_calls": calls, "active_elapsed_ms": self.elapsed_ms(),
            })
            self.counters.tool_actions += len(calls)
            self.new_tools += len(calls)
        else:
            shared.require(started["tool_calls"] == calls, "batch replay mismatch")
        self.gateway.record_working_notes_update(turn.tool_calls, turn_id=turn_id)
        self.latest = self.gateway.execute_batch(turn.tool_calls)
        checkpoint("actions_finished")
        _, self.correction = loop._record_tool_batch(
            journal=self.journal, gateway=self.gateway, turn_id=turn_id,
            calls=turn.tool_calls, results=self.latest, active_elapsed_ms=self.elapsed_ms())
        checkpoint("batch_finished")
        loop._update_inspection_counters(self.counters, self.latest, self.gateway)
        self.counters.protocol_recoveries = 0
        self._finish_batch()
        return self.terminal

    def reconcile(self) -> None:
        """Resolve recorded work before a new dispatch; never retry an uncertain request."""
        if self.terminal is not None:
            return
        terminals = self._new_events("terminal")
        if terminals:
            self.terminal = terminals[-1]
            return
        completed_counts = {e["count_id"] for e in self._new_events("input_count_finished")}
        if any(e["count_id"] not in completed_counts
               for e in self._new_events("input_count_started")):
            raise common.AbortExperiment("COUNT_TIMEOUT_OR_UNKNOWN")
        if self.journal.unresolved_provider_call() is not None:
            raise common.AbortExperiment("PROVIDER_TIMEOUT_OR_UNKNOWN")
        recorded = {e["turn_id"] for e in self._new_events("turn_decision_recorded")}
        if any(not e.get("billing_known", False)
               for e in self._new_events("provider_call_finished")):
            raise common.AbortExperiment("PROVIDER_TIMEOUT_OR_UNKNOWN")
        if any(e["turn_id"] not in recorded for e in self._new_events("provider_call_finished")):
            raise common.AbortExperiment("PROVIDER_CONTINUATION_ERROR")
        pending = loop._unresolved_decision(self.journal)
        self._sync_accounting()
        if pending is not None:
            turn_id, names, maximum, paths = pending[0], pending[6], pending[7], pending[8]
            finished_ids = {e["action_id"] for e in self._new_events("action_finished")}
            if any(e["tool"] in {"run_check", "run_probe"} and e["action_id"] not in finished_ids
                   for e in self._new_events("action_started")):
                raise common.AbortExperiment("TOOL_EXECUTION_UNKNOWN")
            started = next(e for e in self._new_events("turn_started")
                           if e["turn_id"] == turn_id)
            try:
                loop._load_active_model_input(started, self.store)
                loop._validate_recorded_continuations(self.journal.events(), self.store)
            except loop._ProviderContinuationError as exc:
                raise common.AbortExperiment("PROVIDER_CONTINUATION_ERROR") from exc
            loop._validate_resumed_workspace(self.gateway.workspace, self.journal,
                                             deadline=self.gateway.deadline)
            policy = replace(loop._tool_policy(self.gateway, self.counters, self.gateway.limits),
                             allowed_tools=names, max_parallel_reads=maximum,
                             targeted_read_paths=paths)
            payload = next(e for e in self._new_events("turn_decision_recorded")
                           if e["turn_id"] == turn_id)
            turn = DevModelTurn.model_validate({k: v for k, v in payload.items() if k != "turn_id"})
            self.accept(turn_id, turn, policy)
        self.latest = self.journal.latest_tool_batch_results()
        self.correction = loop._pending_protocol_correction(self.journal)
        self._finish_batch()

    def prepare_request(self, package: Any, adapter: Any):
        self.reconcile()
        if self.terminal is not None:
            return None
        # A correction can use the probe's last available slack. Do not dispatch a
        # forced call if the ordinary budget no longer offers that action.
        policy = loop._tool_policy(self.gateway, self.counters, self.gateway.limits)
        if (self.label.startswith("B") and self._probe_batch() is None
                and "run_probe" not in policy.allowed_tools):
            self.finish("LIMIT_REACHED", "probe phase has no remaining completion slack",
                        censored=True)
            return None
        return super().prepare_request(package, adapter)


def initialize_branch(plan, label, root, sandbox, probe, deadline) -> Branch:
    return source.initialize_branch(plan, label, root, sandbox, probe, deadline,
                                    branch_type=Branch, kind=SCHEMA)


def run(plan_root: Path, root: Path, **kwargs) -> dict:
    _fresh_root(root, plan_root)
    return source.run(plan_root, root, plan_loader=load_plan, envelope_builder=envelope_for,
                      branch_initializer=initialize_branch, **kwargs)


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
