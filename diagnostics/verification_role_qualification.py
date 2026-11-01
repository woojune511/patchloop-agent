"""Provider-free, fixed-trajectory qualification; never a resumable experiment.

Historical decisions are held fixed only to locate opportunities and counterfactual
admission failures. They are not predictions of behavior under a new instruction.
No historical program, provider request or evaluator is executed.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import socket
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics import size_only_replay as replay
from diagnostics import verification_role as role
from diagnostics import verification_role_panel as panel
from diagnostics.caller_uptake import file_ref
from diagnostics.cleanup_information_checkpoint import ForkStore
from diagnostics.evidence_handoff_replay import inventory, ranges
from diagnostics.positive_verification_panel import require
from patchloop import prepared_probe_dependencies as deps
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import PublicTask
from patchloop.dev import runner, segments
from patchloop.dev.conversation import SEGMENT_RULES, reconstruct_state
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.repository import DiffSummary
from patchloop.runtime import git_commit, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json


def save(root, name, value):
    path = root / name
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(value) + "\n")
    return file_ref(path)


def floor_cost(tokens):
    return tokens * 750 + 128 * 4500


def settled(prefix):
    return sum(e["payload"]["cost_nanos"] for e in prefix
               if e["event_type"] == "provider_call_finished")


def safe_prefix(turn):
    # Remove preparation for the historical next request, which must be rebuilt
    # after the phase/tool mask changes. Preserve completed corrections and notes.
    last = max(e["sequence"] for e in turn.prefix if e["event_type"] in {
        "tool_batch_finished", "protocol_correction", "repair_recheck_finished"})
    return turn.prefix[:last]


def admission_replay(turns):
    """Earliest counterfactual divergence, plus the nominal phase-entry snapshot."""
    rows, selected = [], None
    for index, turn in enumerate(turns):
        ledger = DevCostLedger(Decimal("0.48"), pricing_for_model(panel.MODEL))
        ledger.spent_nanos = settled(turn.prefix)
        admission = ledger.admit(turn.usage["input_tokens"])
        ready = turn.state["workflow_gate"] == "ready_to_submit"
        trigger = ("candidate_ready" if ready else "initial_calls" if index >= 28 else
                   "initial_cost" if admission is None else None)
        row = {"sequence": turn.sequence, "completed_model_calls": index,
               "candidate_present": bool(turn.state["current_diff"]["patch"]),
               "gate": turn.state["workflow_gate"], "settled_nanos": ledger.spent_nanos,
               "saved_input_tokens": turn.usage["input_tokens"],
               "saved_output_tokens": turn.usage["output_tokens"],
               "output_ceiling": admission.output_ceiling if admission else None,
               "saved_output_fits": bool(admission and
                                         admission.output_ceiling >= turn.usage["output_tokens"]),
               "trigger": trigger}
        rows.append(row)
        if trigger:
            selected = turn
            break
    require(selected is not None, "no observable phase entry in saved trajectory")
    first_divergence = next((r for r in rows if r["trigger"] or not r["saved_output_fits"]), None)
    return selected, {"requests": rows, "first_divergence": first_divergence,
                      "nominal_entry": rows[-1], "new_trajectory_predicted": False}


class ReplayStore(ArtifactStore):
    def __init__(self, root, inherited):
        super().__init__(root / "artifacts")
        self.inherited = inherited

    def read_bytes(self, artifact):
        if Path(artifact.path).resolve().is_relative_to(self.root.resolve()):
            return super().read_bytes(artifact)
        return self.inherited.read_bytes(artifact)


class SavedGateway(DevToolGateway):
    """No workspace: validate the observed-source projection against the saved one."""

    def __init__(self, state, **kwargs):
        self.saved_diff = DiffSummary(**{k: state["current_diff"][k] for k in
            ("changed_files", "added_lines", "deleted_lines", "patch", "untracked_files")})
        super().__init__(**kwargs)
        self._working_findings = copy.deepcopy(state["working_notes"]["findings"])
        self._working_open_question = copy.deepcopy(state["working_notes"]["open_question"])

    @property
    def current_diff(self):
        return self.saved_diff

    def _refresh_working_source_notes(self):
        # The saved context already refreshed them on this exact diff. Never
        # compare historical source with a later workspace, or invent gap bytes.
        pass

    def _validated_source_spans(self):
        latest = {}
        for span in self.spans.values():
            old = latest.get(span["path"])
            if old is None or old["last_observed_seq"] < span["last_observed_seq"]:
                latest[span["path"]] = span
        return [s for s in self.spans.values()
                if s["file_hash"] == latest[s["path"]]["file_hash"]]

    def execute(self, call):
        raise AssertionError("qualification cannot execute historical tools")


def capture_checkpoint(root, turn, source, request, arm, environment):
    root.mkdir(parents=True, exist_ok=False)
    prefix = safe_prefix(turn)
    journal = DevJournal(root, source.run_id)
    journal.path.parent.mkdir(parents=True, exist_ok=True)
    # An exact immutable prefix with a new diagnostic tail, without a run envelope.
    with journal.path.open("xb") as stream:
        stream.write(b"\n".join(source.path.read_bytes().split(b"\n")[:len(prefix)]) + b"\n")
    require(journal.events() == prefix, "copied public checkpoint changed")
    inherited = ForkStore(source.root, source.events())
    store = ReplayStore(root, inherited)
    public = PublicTask.model_validate(turn.state["public_task"])
    gateway = SavedGateway(turn.state, workspace=root / "unmaterialized", public_task=public,
        sandbox=None, journal=journal, limits=request.limits,
        probe_sandbox=SimpleNamespace(environment=environment), history_search_policy="public-v1")
    latest = journal.latest_tool_batch_results()
    baseline = gateway.prepare_context_projection(latest)
    require(inventory(baseline.source_spans) == inventory(turn.state["source_spans"]),
            "observed-source hydration differs from the historical checkpoint")
    controller = role.VerificationRun(gateway, arm)
    gateway.run_extension = controller
    counters = runner._restore_counters(journal)
    ledger = DevCostLedger(Decimal("0.88"), pricing_for_model(panel.MODEL))
    ledger.spent_nanos = settled(prefix)
    controller.request, controller.counters = request, counters
    controller.ledger, controller.store, controller.row_cost_start = ledger, store, 0
    controller.entry = {k: 0 for k in controller.usage()}
    with journal.execution_lock():
        journal.append("qualification_fork", {"source": file_ref(source.path),
            "source_sequence": len(prefix), "dispatch_sequence": turn.sequence,
            "mode": "input-only; not resumable; no historical actions executed"})
        controller._start("verify", "fixed_snapshot_projection")
        projection = gateway.prepare_context_projection(latest)
        snapshot = gateway.state_snapshot(projection=projection)
        with patch.object(runner, "_tool_policy", role._policy):
            policy = role._policy(gateway, counters, request.limits,
                snapshot=snapshot, repair_inspection_policy=request.repair_inspection_policy,
                repair_recheck=request.repair_recheck, cost_ledger=ledger,
                completion_cost_policy=request.completion_cost_policy)
        elapsed = (request.limits.wall_time_seconds -
                   turn.state["remaining_budget"]["total_active_wall_time_seconds"])
        context = runner._build_context(package=SimpleNamespace(public=public), gateway=gateway,
            journal=journal, correction=None, latest_tool_results=latest, counters=counters,
            elapsed_seconds=elapsed, limits=request.limits, policy=policy, snapshot=snapshot,
            tool_policy_transition=runner._tool_policy_transition(journal, policy),
            projection=projection, repair_recheck=request.repair_recheck,
            planning_policy=request.planning_policy, evaluation_reserve_seconds=330)
        context = controller.context(context)
        state = json.loads(context)
        state["remaining_budget"]["cost"] = {
            "currency": "USD", "unit": "nanodollar", "invocation_cap": ledger.cap_nanos,
            "settled_usage": ledger.spent_nanos, "remaining": ledger.remaining_nanos,
            "provider": "openai", **runner._completion_cost_payload(policy)}
        context = canonical_json(state)
        items = runner._build_model_input(journal=controller.input_journal, artifact_store=store,
            context=context,
            latest_tool_results=controller.input_journal.latest_tool_batch_results(),
            context_policy=request.context_policy, planning_policy=request.planning_policy,
            history_search_policy=request.history_search_policy)
        schemas = controller.schemas(role._schemas(finish_enabled=False, check_ids=policy.check_ids,
            test_suite_ids=[s.id for s in public.test_suites], allowed_tools=policy.allowed_tools,
            read_paths=policy.targeted_read_paths, planning_policy=request.planning_policy,
            probe_environment=environment, history_search_policy=request.history_search_policy))
        wire = {**turn.wire, "input": items, "tools": schemas, "max_output_tokens": 25_000}
        delivered = reconstruct_state(items, context_policy="segmented-v1")
        require(delivered["verification_phase"] == state["verification_phase"]
                and delivered["public_task"] == public.model_dump(mode="json"),
                "actual packet lost its common phase or public task")
        require(arm == "A" or not any(i.get("type") in {"reasoning", "function_call",
                                                       "function_call_output"} for i in items),
                "independent entry copied native history")
        ref = save(root, "wire.json", wire)
        journal.append("qualification_input_captured", {"wire": ref,
            "common_context_hash": sha256_json(state), "provider_calls": 0, "input_count_calls": 0})
    return wire, state, inherited.reads


def exposed(wire):
    facts, exchanges, _ = SEGMENT_RULES.inventory(wire["input"])
    outputs = {v["call_id"] for v in exchanges.values() if v["type"] == "function_call_output"}
    return {(*k, v) for k, v in facts.items()}, outputs


def funding(tokens, state):
    # Existing completion forecasts are lower bounds on registered paths, not
    # evidence that 128 output tokens yield a useful decision.
    horizon = state["action_horizon"]
    final_calls = horizon["mutation_completion_horizon"]["minimum_calls"]
    unit = floor_cost(tokens)
    first_max = tokens * 750 + 25_000 * 4500
    return {"verification": {"minimum_calls": 2, "purpose": "one observation then report",
            "minimum_cost_nanos": 2 * floor_cost(tokens), "envelope_nanos": 200_000_000,
            "funded": 2 * unit <= 200_000_000,
            "funded_after_max_first_output": first_max + unit <= 200_000_000},
            "final": {"minimum_calls": final_calls, "purpose": "existing mutation forecast",
            "minimum_cost_nanos": final_calls * unit,
            "reserved_nanos": 200_000_000,
            "funded": final_calls * unit <= 200_000_000,
            "funded_after_max_first_output": first_max + (final_calls - 1) * unit
            <= 200_000_000},
            "maximum_calls_at_floor": min(6, 200_000_000 // unit),
            "six_full_outputs_cost_nanos": 6 * (tokens * 750 + 25_000 * 4500),
            "useful_output_guaranteed": False}


def qualification_receipts(root, summary, initial, returns):
    """Bind failed gates too. A passing unit test must not erase a failed delivery."""
    identity = {k: summary[k] for k in (
        "head", "runtime_hash", "implementation", "contract_hash",
        "provider_calls", "input_count_calls")}
    initial_result = panel.initial_pair(initial)
    comparison = all(r["common_context_equal"] and r["schemas_equal"]
                     and r["contrast_present"] for r in summary["rows"])
    delivery = (set(returns) == {"A", "B"}
                and all(r["passed"] is True for r in returns.values()))
    bounded = all(not segments.size_reasons(a["sizes"])
                  and a["tokens"]["upper"] <= 60_000
                  for r in summary["rows"] for a in r["arms"].values())
    funding_ok = all(a["funding"][p]["funded"] for r in summary["rows"]
                     for a in r["arms"].values() for p in ("verification", "final"))
    initial_ref = save(root, "initial-comparison.json", initial_result)
    return_ref = save(root, "return-delivery.json", returns)
    common_evidence = [file_ref(root / "summary.json"), initial_ref, return_ref]
    outcomes = {
        "same_snapshot_capture": (comparison and delivery and bounded,
            "Common entry state/schema and contrast pass; selected return evidence must pass too."),
        "historical_packet_replay": (summary["baseline_exact_requests"] > 0,
            "Exact original projections; enumerated intended native/source displacement."),
        "resource_feasibility": (funding_ok and bounded,
            "Minimum paths only; output-ceiling divergence and starvation remain risks."),
    }
    gates = {"contract_hash": identity["contract_hash"]}
    for gate, (passed, explanation) in outcomes.items():
        gates[gate] = save(root, gate + ".json", {**identity, "gate": gate, "passed": passed,
            "explanation": explanation, "evidence": common_evidence})
    return gates


def run(manifest, output, encoder):
    output.mkdir(parents=True, exist_ok=False)
    journal = DevJournal(output, "run_dev_rolequalification49")
    identity = {"head": git_commit(), "runtime_hash": runtime_content_hash(),
                "implementation": panel.bindings(), "contract_hash": sha256_json(role.contract()),
                "provider_calls": 0, "input_count_calls": 0}
    save(output, "executed-source.json", {"source": Path(__file__).read_text(encoding="utf-8")})
    journal.append("qualification_started", {**identity, "manifest": file_ref(manifest)})
    source_rows = json.loads(manifest.read_bytes())["rows"]
    all_turns, reasoning, rows, reads = [], {}, [], {str(manifest): file_ref(manifest)["hash"]}
    for row in source_rows:
        root = Path(row["request"]["state_root"])
        paths = list((root / "runs").glob("*.jsonl"))
        if not paths:
            continue
        require(len(paths) == 1, "ambiguous saved run")
        request = copy.deepcopy(row)
        request["request"]["resume_run_id"] = paths[0].stem
        turns, opaque_usage, bound_reads = replay.load_row(request, 0)
        replay.verify_baseline(turns)
        all_turns.extend(turns)
        reasoning.update(opaque_usage)
        reads.update(bound_reads)
        rows.append((row, turns, DevJournal(root, paths[0].stem)))
    estimator = replay.TokenEstimator(encoder, reasoning, all_turns)
    results = []
    for row, turns, source in rows:
        selected, admission = admission_replay(turns)
        request = panel.request(output / "not-executable", row["row_id"])
        public = PublicTask.model_validate(selected.state["public_task"])
        dependencies = deps.load_dependencies(panel.common.DEPENDENCIES, public,
                                               deps.admit(panel.common.DEPENDENCIES))
        wires, states, details = {}, {}, {}
        for arm in "AB":
            wires[arm], states[arm], bound_reads = capture_checkpoint(
                output / row["row_id"] / arm, selected, source, request, arm,
                dependencies.environment)
            reads.update(bound_reads)
            estimate = estimator.estimate(selected, wires[arm]["input"])
            delta = len(encoder(canonical_json(wires[arm]["tools"]))) - len(
                encoder(canonical_json(selected.wire["tools"])))
            for key in ("lower", "central", "upper"):
                estimate[key] = max(0, estimate[key] + delta)
            details[arm] = {"sizes": segments.request_sizes(wires[arm]), "tokens": estimate,
                "native_items": sum(i.get("type") == "reasoning" for i in wires[arm]["input"]),
                "native_calls": sum(i.get("type") == "function_call"
                                    for i in wires[arm]["input"]),
                "segment": reconstruct_state(wires[arm]["input"],
                                              context_policy="segmented-v1")["segment_handoff"],
                "funding": funding(estimate["upper"], states[arm])}
        facts_a, receipts_a = exposed(wires["A"])
        facts_b, receipts_b = exposed(wires["B"])
        facts_old, receipts_old = exposed(selected.wire)
        displacement = {"A_minus_B": ranges(facts_a - facts_b),
            "B_minus_A": ranges(facts_b - facts_a),
            "A_receipts_missing_from_B": sorted(receipts_a - receipts_b),
            "original_minus_A": ranges(facts_old - facts_a),
            "original_minus_B": ranges(facts_old - facts_b),
            "new_in_A": ranges(facts_a - facts_old), "new_in_B": ranges(facts_b - facts_old),
            "original_receipts_missing_from_A": sorted(receipts_old - receipts_a),
            "original_receipts_missing_from_B": sorted(receipts_old - receipts_b)}
        result = {"row": row["row_id"], "baseline_exact_requests": len(turns),
            "checkpoint": selected.sequence, "admission": admission, "arms": details,
            "common_context_equal": states["A"] == states["B"],
            "schemas_equal": wires["A"]["tools"] == wires["B"]["tools"],
            "contrast_present": bool(details["A"]["native_items"] or facts_a != facts_b),
            "source_lines": {"original": len(facts_old), "A": len(facts_a), "B": len(facts_b),
                "A_minus_B": len(facts_a - facts_b), "B_minus_A": len(facts_b - facts_a),
                "original_minus_A": len(facts_old - facts_a),
                "original_minus_B": len(facts_old - facts_b)},
            "displacement": displacement}
        ref = save(output, row["row_id"] + ".json", result)
        journal.append("checkpoint_compared", {"result": ref})
        results.append(result)
    for path, digest in reads.items():
        require(sha256_bytes(Path(path).read_bytes()) == digest, "historical evidence changed")
    summary = {**identity, "rows": results, "baseline_exact_requests": len(all_turns),
        "calibration": estimator.calibration, "historical_files_unchanged": len(reads),
        "worst_input_funding": funding(60_000, states["A"]),
        "paid_authorized": False, "frozen": False,
        "limitations": ["No new model behavior, useful output or repair measured.",
            "Token estimates are saved-count anchored; no provider count.",
            "Minimum-output funding is not useful reasoning capacity.",
            "Nominal entry after first output-ceiling divergence is a diagnostic snapshot only."]}
    ref = save(output, "summary.json", summary)
    save(output, "source-reads.json", reads)
    journal.append("qualification_finished", {"summary": ref, "frozen": False})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tokenizer-package", type=Path, required=True)
    parser.add_argument("--tokenizer-cache", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.tokenizer_package))
    os.environ["TIKTOKEN_CACHE_DIR"] = str(args.tokenizer_cache)
    import tiktoken

    with patch.object(socket.socket, "connect", side_effect=AssertionError("offline only")):
        value = run(args.manifest, args.output, tiktoken.get_encoding("o200k_base").encode)
    print(canonical_json({k: value[k] for k in
                          ("baseline_exact_requests", "provider_calls", "frozen")}))


if __name__ == "__main__":
    main()
