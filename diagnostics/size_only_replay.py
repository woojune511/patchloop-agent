"""Offline, fixed-trajectory segment replay; never a resumable or executable run.

Reuse actual public states, decisions, opaque continuations and tool results. Check
the original projection byte-for-byte before changing boundaries. Token estimates
are anchored to saved provider counts, not to the ciphertext's text tokenization.
Only local files are read. The CLI blocks socket connections, including tokenizer
downloads; install the optional tokenizer and populate its cache separately.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics.cleanup_information_checkpoint import ForkStore
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import disjoint
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import evidence_focus, runner, segments, working_plan
from patchloop.dev.conversation import SEGMENT_RULES, assemble_model_input, reconstruct_state
from patchloop.dev.cost import DevCostLedger, ModelPricing
from patchloop.dev.state import DevJournal
from patchloop.dev.thin_policy import system_prompt
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SEGMENT_EVENTS = {segments.EVENT, segments.PREPARED_EVENT}
JOURNAL = "run_dev_sizeonlyreplay"


@dataclass
class SavedTurn:
    row: str
    sequence: int
    prefix: list
    turn: dict
    state: dict
    wire: dict
    usage: dict
    latest: list
    exchange: list
    base: list
    handoff: dict


def load_row(row, after_sequence):
    root = Path(row["request"]["state_root"])
    journal = DevJournal(root, row["request"]["resume_run_id"])
    events = journal.events()  # Validates the complete immutable chain.
    store = ForkStore(root, events)
    reads = {str(p): sha256_bytes(p.read_bytes())
             for p in (journal.path, journal.envelope_path)}
    turns, reasoning = [], {}
    started = {e["payload"]["turn_id"]: e for e in events
               if e["event_type"] == "turn_started"}
    finished = {e["payload"]["call_id"]: e["payload"] for e in events
                if e["event_type"] == "provider_call_finished"}
    for event in events:
        if event["event_type"] != "provider_call_started" or event["sequence"] <= after_sequence:
            continue
        call = event["payload"]
        boundary = started[call["turn_id"]]
        turn = boundary["payload"]
        prefix = events[:boundary["sequence"] - 1]
        reader = SimpleNamespace(events=lambda prefix=prefix: prefix)
        state = json.loads(store.read_bytes(Artifact.model_validate(turn["context_artifact"])))
        bundle = json.loads(store.read_bytes(Artifact.model_validate(
            turn["prepared_input"]["artifact"])))
        wire = bundle["request"]
        require(sha256_json(wire) == call["counted_request_hash"], "saved count body mismatch")
        wire["max_output_tokens"] = call["output_ceiling"]
        require(sha256_json(wire) == call["request_hash"], "saved generation body mismatch")
        original = runner._load_active_model_input(turn, store, context_policy=segments.POLICY)
        require(original == wire["input"], "saved input differs from actual wire")
        latest = DevJournal.latest_tool_batch_results(reader)
        exchange = runner._build_latest_exchange(
            journal=reader, artifact_store=store, context=canonical_json(state),
            latest_tool_results=latest)[1:-1]
        handoff = reconstruct_state(original, context_policy=segments.POLICY)["segment_handoff"]
        base = segments.load_binding(turn["context_segment"]["binding"], store)["base"]
        usage = finished[call["call_id"]]
        require(usage["input_tokens"] == call["input_tokens"], "saved count/usage mismatch")
        ref = usage.get("continuation_ref")
        if ref:
            continuation = json.loads(store.read_bytes(Artifact.model_validate(ref["artifact"])))
            opaque = [i for i in continuation["output_order"] if "encrypted_content" in i]
            require(len(opaque) == 1, "reasoning usage needs one-to-one opaque attribution")
            reasoning[sha256_bytes(opaque[0]["encrypted_content"].encode())] = (
                usage["reasoning_output_tokens"])
        turns.append(SavedTurn(row["row_id"], event["sequence"], prefix, turn, state,
                               wire, usage, latest, exchange, base, handoff))
    require(turns and turns[0].handoff["review_requested"], "start at a saved fresh segment")
    # CAS reads already verify bytes/hash/size. Include remapped files, not stale old paths.
    for path, digest in store.reads.items():
        p = Path(path)
        if p.is_file():
            require(sha256_bytes(p.read_bytes()) == digest, "inherited source changed")
            reads[str(p)] = digest
    return turns, reasoning, reads


def fresh_base(turn, *, omit_optional=False):
    ids = {r.action_id for r in turn.latest}
    calls = [c for e in turn.prefix if e["event_type"] == "turn_decision_recorded"
             for c in e["payload"].get("tool_calls", []) if c["action_id"] in ids]
    base = runner._segment_public_base(system_prompt("current", "brief-v1"),
                                       turn.state, turn.latest, calls)
    optional = [] if omit_optional else evidence_focus.optional_exchanges(
        turn.state.get("working_notes", {}).get("open_question"), turn.prefix, ids,
        diff_hash=turn.state["current_diff"]["patch_hash"])
    optional_ids = {i["call_id"] for i in optional if i["type"] == "function_call_output"}
    require(len(optional_ids) <= 2, "optional reference budget exceeded")
    if optional:
        base.append(SEGMENT_RULES.archive(exchanges=optional))
    return base, sorted(optional_ids)


def compose(turn, previous, handoff, *, base=None, replay_boundary=None):
    """Mirror the runtime's public projection using only the turn's past records."""
    state = copy.deepcopy(turn.state)
    fresh = handoff["review_requested"]
    if fresh:
        previous, added = base, []
    else:
        require(previous is not None, "missing previous input")
        added = copy.deepcopy(turn.exchange)
        admissions = {e["payload"]["action_id"]: e["payload"] for e in turn.prefix
                      if e["event_type"] == "action_started"}
        for position, item in enumerate(added):
            if item.get("type") == "function_call_output":
                added[position] = {**item, "output": canonical_json(runner.project_mutation_result(
                    json.loads(item["output"]), history=[*previous[3:], *added[:position]],
                    admission=admissions.get(item["call_id"]),
                    archive_kind=runner.PUBLIC_EVIDENCE_KIND))}
    plan_events = turn.prefix
    if replay_boundary is not None:
        # Remove original transitions also from the plan review signal. Keep the
        # actual model-authored plans/receipts; their behavior is held fixed.
        plan_events = [e for e in turn.prefix if e["event_type"] not in SEGMENT_EVENTS]
        plan_events.append({"event_type": segments.PREPARED_EVENT,
                            "sequence": replay_boundary, "payload": {}})
    state["working_plan"] = working_plan.project(
        plan_events, diff_hash=state["current_diff"]["patch_hash"],
        gate=state["workflow_gate"], policy="brief-v1")
    state["segment_handoff"] = handoff
    view = runner._segment_current_view(state, [*previous[3:], *added], turn.latest)
    return assemble_model_input(system_prompt=system_prompt("current", "brief-v1"),
                                state=view, history=added, previous_input=previous,
                                context_policy=segments.POLICY)


def verify_baseline(turns):
    previous = None
    for turn in turns:
        actual = turn.wire["input"]
        rebuilt = compose(turn, previous, turn.handoff, base=turn.base)
        require(rebuilt == actual, f"baseline input mismatch: {turn.row}/{turn.sequence}")
        sizes = segments.request_sizes(turn.wire)
        require(not segments.size_reasons(sizes), "saved dispatched byte limit exceeded")
        require(turn.usage["input_tokens"] <= segments.MAX_INPUT_TOKENS, "saved token limit")
        previous = actual


class TokenEstimator:
    """Empirical delta estimate, not a provider count or guaranteed upper bound.

    Content is locally tokenized; opaque items use their saved reasoning-output
    usage. Protocol overhead is approximated by 30 per call/output pair and seven
    per developer message. Anchor every candidate to that same turn's actual count
    (same tools). The sensitivity margin covers all observed residual variation
    within an identical tool schema, with a minimum 128-token margin.
    """

    def __init__(self, encode, reasoning, all_turns):
        self.encode = encode
        self.reasoning = reasoning
        self.text_count = lru_cache(maxsize=8192)(lambda text: len(encode(text)))
        groups = defaultdict(list)
        residuals = []
        for turn in all_turns:
            measured = self.measure(turn.wire["input"])
            residual = turn.usage["input_tokens"] - measured
            groups[sha256_json(turn.wire["tools"])].append(residual)
            residuals.append({"row": turn.row, "request_sequence": turn.sequence,
                              "residual": residual})
        self.margin = max(128, max(max(v) - min(v) for v in groups.values()))
        self.calibration = {"method": "same-turn-saved-count-plus-local-feature-delta-v1",
                            "encoding": "o200k_base", "margin_tokens": self.margin,
                            "baseline_requests": len(all_turns),
                            "schema_groups": len(groups), "residuals": residuals,
                            "provider_count": False, "statistical_confidence_interval": False,
                            "ciphertext_tokenization": False,
                            "assumption": "retained opaque items count as saved reasoning usage"}

    def measure(self, items):
        value = 0
        for item in items:
            if item.get("type") == "reasoning":
                digest = sha256_bytes(item["encrypted_content"].encode())
                require(digest in self.reasoning, "opaque item has no saved usage attribution")
                value += self.reasoning[digest]
                continue
            for key in ("content", "arguments", "output"):
                if key in item:
                    value += self.text_count(item[key])
            if item.get("type") == "function_call":
                value += 30
            if item.get("role") == "developer":
                value += 7
        return value

    def estimate(self, turn, items):
        exact = items == turn.wire["input"]
        center = turn.usage["input_tokens"] + self.measure(items) - self.measure(turn.wire["input"])
        margin = 0 if exact else self.margin
        return {"lower": max(0, center - margin), "central": center,
                "upper": center + margin, "saved_exact_input": exact}


def inventory(items):
    facts, exchanges, observations = SEGMENT_RULES.inventory(items)
    outputs = {i["call_id"]: json.loads(i["output"]) for i in exchanges.values()
               if i["type"] == "function_call_output"}
    return facts, outputs, observations


def probe_catalog(turns, after_sequence):
    """Read public action records for measurement only, never for reconstruction."""
    events = turns[-1].prefix
    calls = {c["action_id"]: c for e in events if e["event_type"] == "turn_decision_recorded"
             for c in e["payload"].get("tool_calls", [])}
    return [{"sequence": e["sequence"], "action_id": r["action_id"],
             "before_checkpoint": e["sequence"] <= after_sequence,
             "python_source": calls[r["action_id"]]["arguments"]["python_source"],
             "stdout": r["output"]["stdout"], "diff_hash": r["output"]["diff_hash"],
             "question": r["output"]["question"]}
            for e in events if e["event_type"] == "action_finished"
            and (r := e["payload"]["result"])["tool"] == "run_probe"]


def probe_delivery(items, probes, sequence):
    """Require the same action's entire program and stdout, not a substring hit."""
    _, exchanges, _ = SEGMENT_RULES.inventory(items)
    calls = defaultdict(list)
    outputs = defaultdict(list)
    for item in exchanges.values():
        if item["type"] == "function_call":
            calls[item["call_id"]].append(json.loads(item["arguments"]))
        else:
            outputs[item["call_id"]].append(json.loads(item["output"]))
    result = []
    for probe in probes:
        if probe["sequence"] >= sequence:
            continue
        aid = probe["action_id"]
        result.append({"action_id": aid,
                       "program": any(c.get("python_source") == probe["python_source"]
                                      for c in calls[aid]),
                       "stdout": bool(probe["stdout"]) and any(
                           o.get("output", {}).get("stdout") == probe["stdout"]
                           for o in outputs[aid])})
    return result


def line_ranges(facts):
    grouped = defaultdict(list)
    for path, digest, line in sorted(facts):
        ranges = grouped[path, digest]
        if ranges and ranges[-1][1] + 1 == line:
            ranges[-1][1] = line
        else:
            ranges.append([line, line])
    return [{"path": p, "file_hash": h, "ranges": r} for (p, h), r in grouped.items()]


def retention(before, after):
    old_facts, old_outputs, old_obs = inventory(before)
    new_facts, new_outputs, new_obs = inventory(after)
    old, new = set(old_facts), set(new_facts)
    old_ids, new_ids = set(old_outputs), set(new_outputs)
    return {"source_lines_before": len(old), "source_lines_after": len(new),
            "added_source_line_exposures": len(new - old),
            "lost_source_line_exposures": len(old - new),
            "added_source_ranges": line_ranges(new - old),
            "lost_source_ranges": line_ranges(old - new),
            "tool_result_ids_before": sorted(old_ids), "tool_result_ids_after": sorted(new_ids),
            "added_tool_result_ids": sorted(new_ids - old_ids),
            "lost_tool_result_ids": sorted(old_ids - new_ids),
            "added_observation_hashes": sorted(set(new_obs) - set(old_obs)),
            "lost_observation_hashes": sorted(set(old_obs) - set(new_obs)),
            "observation_hashes_before": sorted(old_obs),
            "observation_hashes_after": sorted(new_obs)}


def limits_hold(items):
    state = reconstruct_state(items, context_policy=segments.POLICY)
    projection = state["context_projection"]
    require(projection["retained_content_limit"] == 24_000
            and projection["retained_content_chars"] <= 24_000, "source projection budget")
    question = state.get("working_notes", {}).get("open_question")
    refs = len(question.get("evidence", [])) if question else 0
    require(refs <= 2, "question reference budget")
    return {"retained_source_chars": projection["retained_content_chars"],
            "question_references": refs}


def replay(turns, estimator, level, *, save_input=None, probes=()):
    previous, handoff, boundary = None, None, None
    rows = []
    for index, turn in enumerate(turns):
        optional_ids, attempts = [], []
        if index == 0:
            # Common saved checkpoint: do not recover pre-checkpoint discarded history.
            candidate = copy.deepcopy(turn.wire["input"])
            handoff = copy.deepcopy(turn.handoff)
            boundary = turn.turn["context_segment"]["binding"]["reviewed_through_sequence"] + 1
        else:
            handoff = {**handoff, "review_requested": False}
            candidate = compose(turn, previous, handoff, replay_boundary=boundary)
        estimate = estimator.estimate(turn, candidate)
        wire = {**turn.wire, "input": candidate, "max_output_tokens": 25_000}
        sizes = segments.request_sizes(wire)
        reasons = segments.size_reasons(sizes)
        if estimate[level] > segments.MAX_INPUT_TOKENS:
            reasons.append("input_tokens_estimate")
        if reasons:
            attempts.append({"sizes": sizes, "tokens": estimate, "reasons": reasons})
            base, optional_ids = fresh_base(turn)
            boundary = turn.prefix[-1]["sequence"] + 1
            handoff = {**handoff, "reason": "+".join(reasons), "review_requested": True,
                       "segment_id": "segment_" + sha256_json({
                           "diagnostic": "size-only-v1", "row": turn.row,
                           "source_request_sequence": turn.sequence,
                           "base_hash": sha256_json(base)})[7:]}
            candidate = compose(turn, None, handoff, base=base, replay_boundary=boundary)
            estimate = estimator.estimate(turn, candidate)
            wire = {**wire, "input": candidate}
            sizes = segments.request_sizes(wire)
            if (segments.size_reasons(sizes) or estimate[level] > segments.MAX_INPUT_TOKENS
                    ) and optional_ids:
                attempts.append({"sizes": sizes, "tokens": estimate,
                                 "reasons": ["omit_optional_evidence"]})
                base, optional_ids = fresh_base(turn, omit_optional=True)
                candidate = compose(turn, None, handoff, base=base, replay_boundary=boundary)
                estimate = estimator.estimate(turn, candidate)
                wire = {**wire, "input": candidate}
                sizes = segments.request_sizes(wire)
        failed = bool(segments.size_reasons(sizes) or estimate[level] > segments.MAX_INPUT_TOKENS)
        row = {"request_sequence": turn.sequence, "baseline_tokens": turn.usage["input_tokens"],
               "baseline_bytes": segments.request_sizes(turn.wire),
               "baseline_fresh": turn.handoff["review_requested"],
               "baseline_reason": turn.handoff["reason"],
               "estimated_tokens": estimate, "selected_token_scenario": estimate[level],
               "token_limit_uncertain": estimate["lower"] <= segments.MAX_INPUT_TOKENS
               < estimate["upper"],
               "sizes": sizes, "fresh": handoff["review_requested"],
               "reason": handoff["reason"], "attempts": attempts,
               "optional_handoff_result_ids": optional_ids,
               "limits": limits_hold(candidate), "input_hash": sha256_json(candidate),
               "retention": retention(turn.wire["input"], candidate),
               "probe_delivery_before": probe_delivery(turn.wire["input"], probes, turn.sequence),
               "probe_delivery_after": probe_delivery(candidate, probes, turn.sequence),
               "status": "FRESH_SIZE_LIMIT" if failed else "RECONSTRUCTED",
               "output_tokens_held_fixed": turn.usage["output_tokens"],
               "baseline_cached_tokens": turn.usage["cached_input_tokens"],
               "baseline_output_ceiling": turn.wire["max_output_tokens"]}
        if save_input:
            row["input_artifact"] = save_input(candidate)
        rows.append(row)
        if failed:
            break
        previous = candidate
    return rows


def cost_projection(rows, *, pricing, row_cap, historical_debit, cache_mode, baseline=False):
    """Admission is uncached, even in cache scenarios. Never settle an unfittable output."""
    ledger = DevCostLedger(Decimal(row_cap) / 1_000_000_000, pricing)
    ledger.spent_nanos = historical_debit
    admitted, stopped, full_trace_cost = [], None, 0
    for row in rows:
        tokens = row["baseline_tokens"] if baseline else row["selected_token_scenario"]
        cached = (min(tokens, row["baseline_cached_tokens"]) if cache_mode == "saved-cache-count"
                  else 0)
        output = row["output_tokens_held_fixed"]
        cost = DevCostLedger(Decimal(1), pricing).settle(
            input_tokens=tokens, cached_input_tokens=cached, output_tokens=output)
        full_trace_cost += cost
        if stopped:
            continue
        admission = ledger.admit(tokens, desired_output_ceiling=25_000)
        if row["status"] != "RECONSTRUCTED" or admission is None:
            stopped = {"request_sequence": row["request_sequence"],
                       "reason": "SIZE_LIMIT" if row["status"] != "RECONSTRUCTED" else "COST_CAP"}
        elif output > admission.output_ceiling:
            stopped = {"request_sequence": row["request_sequence"],
                       "reason": "SAVED_OUTPUT_EXCEEDS_AFFORDABLE_CEILING",
                       "saved_output_tokens": output,
                       "affordable_output_ceiling": admission.output_ceiling}
        else:
            if baseline and cache_mode == "saved-cache-count":
                require(admission.output_ceiling == row["baseline_output_ceiling"],
                        "baseline cost admission mismatch")
            cost = ledger.settle(input_tokens=tokens, cached_input_tokens=cached,
                                 output_tokens=output)
            admitted.append({"request_sequence": row["request_sequence"], "cost_nanos": cost,
                             "output_ceiling": admission.output_ceiling})
    return {"cache_scenario": cache_mode, "admitted_saved_outputs": len(admitted),
            "conditional_prefix_cost_nanos": ledger.spent_nanos - historical_debit,
            "full_trace_estimate_nanos_ignoring_early_stop": full_trace_cost,
            "stopped_before_saved_output": stopped, "admissions": admitted}


def summarize(rows):
    def distribution(values):
        return {"min": min(values), "median": statistics.median(values),
                "max": max(values), "sum": sum(values)}
    return {"requests": len(rows), "transitions_after_start": sum(r["fresh"] for r in rows[1:]),
            "tokens": distribution([r["selected_token_scenario"] for r in rows]),
            "request_bytes": distribution([r["sizes"]["request_bytes"] for r in rows]),
            "largest_encrypted_item_bytes": max(r["sizes"]["largest_encrypted_item_bytes"]
                                                for r in rows),
            "extra_source_line_exposures": sum(r["retention"]["added_source_line_exposures"]
                                                for r in rows),
            "lost_source_line_exposures": sum(r["retention"]["lost_source_line_exposures"]
                                               for r in rows),
            "extra_tool_result_exposures": sum(len(r["retention"]["added_tool_result_ids"])
                                                for r in rows),
            "lost_tool_result_exposures": sum(len(r["retention"]["lost_tool_result_ids"])
                                               for r in rows)}


def run(manifest_path, output, after_sequence, encode, tokenizer_metadata):
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    controls = manifest["controls"]
    source_roots = [Path(r["request"]["state_root"]) for r in manifest["rows"]]
    disjoint(output, [repository_root(), manifest_path.parent, *source_roots])
    require(manifest["invariants"]["references"] == 2
            and manifest["invariants"]["retained_source_chars"] == 24_000,
            "unsupported source budget")
    require(all(r["request"]["segment_boundary_policy"] == segments.DEFAULT_BOUNDARY_POLICY
                for r in manifest["rows"]), "source boundary policy")
    require(manifest["runtime_hash"] == runtime_content_hash(), "source runtime differs")
    output.mkdir()
    journal, store = DevJournal(output, JOURNAL), ArtifactStore(output / "artifacts")
    contract = {"schema": "size-only-offline-replay-v1", "official": False,
                "source_manifest_hash": sha256_bytes(raw), "after_sequence": after_sequence,
                "runtime_hash": runtime_content_hash(), "tokenizer": tokenizer_metadata,
                "implementation_hash": sha256_bytes(Path(__file__).read_bytes()),
                "intervention": "size-only-v1 from common saved fresh segment",
                "invariants": manifest["invariants"],
                "source_model": controls["model"], "source_order": controls["order"],
                "row_cap_nanos": controls["original_row_cap_nanos"],
                "historical_debit_nanos": controls["historical_spent_nanos"],
                "group_new_cap_nanos": controls["new_cap_nanos"],
                "pricing": controls["pricing"],
                "provider_requests": 0, "provider_token_counts": 0, "new_spend_nanos": 0,
                "tools_executed": 0, "credentials_read": False,
                "held_fixed": ["public states except derived segment/plan review projections",
                               "model responses, tool outcomes, schemas, output tokens",
                               "source limits, two question refs, call/action/edit/time limits"],
                "not_established": ["model evidence uptake", "repair success", "new latency",
                                    "actual caching", "exact counterfactual token counts"],
                "token_scenarios": ["lower", "central", "upper"],
                "request_bytes_scope": "serialized request before output-ceiling cost adjustment",
                "cache_scenarios": ["saved-cache-count", "uncached"],
                "budget_stop": "stop saved trajectory when its output cannot fit admission"}
    journal.append("replay_specification_frozen", contract)
    cases, opaque, inputs = {}, {}, {str(manifest_path): sha256_bytes(raw)}
    for row in manifest["rows"]:
        turns, reasoning, reads = load_row(row, after_sequence)
        verify_baseline(turns)
        cases[row["row_id"]] = turns
        opaque.update(reasoning)
        inputs.update(reads)
        journal.append("baseline_reconstructed", {"row": row["row_id"], "requests": len(turns),
                                                  "exact_input_hashes": [
                                                      sha256_json(t.wire["input"]) for t in turns]})
    estimator = TokenEstimator(encode, opaque, [t for turns in cases.values() for t in turns])
    journal.append("token_estimator_calibrated", estimator.calibration)
    pricing = ModelPricing(**{k: Decimal(v) for k, v in controls["pricing"].items()})
    results = []
    for label in controls["order"]:
        turns = cases[label]
        # Track every first-request observation by exact record hash, not a keyword
        # or a later outcome-selected quote. This includes the supplied caller packet.
        _, _, first_observations = inventory(turns[0].wire["input"])
        tracked = [{"hash": h, "field": r["field"]} for h, r in first_observations.items()]
        probes = probe_catalog(turns, after_sequence)
        row_result = {"row": label, "tracked_first_observations": tracked,
                      "probes": probes, "scenarios": {}}
        for level in ("lower", "central", "upper"):
            save = (lambda items: store.put_json(items).model_dump(mode="json")) if (
                level == "central") else None
            rows = replay(turns, estimator, level, save_input=save, probes=probes)
            costs = [cost_projection(rows, pricing=pricing,
                                    row_cap=controls["original_row_cap_nanos"],
                                    historical_debit=controls["historical_spent_nanos"],
                                    cache_mode=mode) for mode in contract["cache_scenarios"]]
            scenario = {"summary": summarize(rows), "costs": costs, "requests": rows}
            if level == "central":
                scenario["baseline_cost"] = cost_projection(
                    rows, pricing=pricing, row_cap=controls["original_row_cap_nanos"],
                    historical_debit=controls["historical_spent_nanos"],
                    cache_mode="saved-cache-count", baseline=True)
                require(scenario["baseline_cost"]["conditional_prefix_cost_nanos"]
                        == sum(t.usage["cost_nanos"] for t in turns), "baseline billing mismatch")
            row_result["scenarios"][level] = scenario
            journal.append("row_scenario_reconstructed", {"row": label, "level": level,
                                                          "result": store.put_json(scenario)
                                                          .model_dump(mode="json")})
        results.append(row_result)
        print(json.dumps({"row": label, "central": row_result["scenarios"]["central"]["summary"]}),
              flush=True)
    # No row borrows unused funds. Their maximum allocations sum to the group cap.
    require(len(results) * (controls["original_row_cap_nanos"] - controls["historical_spent_nanos"])
            <= controls["new_cap_nanos"], "source row caps exceed group allocation")
    require(all(sha256_bytes(Path(p).read_bytes()) == h for p, h in inputs.items()),
            "source bytes changed during replay")
    result = {"contract": contract, "calibration": estimator.calibration, "rows": results,
              "source_files": inputs, "source_files_unchanged": True}
    path = output / "result.json"
    with path.open("x", encoding="utf-8") as f:
        f.write(canonical_json(result) + "\n")
    journal.append("replay_completed", {"result_path": str(path),
                                        "result_hash": sha256_bytes(path.read_bytes()),
                                        "source_files_verified": len(inputs), "new_spend_nanos": 0})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--after-sequence", type=int, required=True)
    parser.add_argument("--tokenizer-package", type=Path, required=True)
    parser.add_argument("--tokenizer-cache", type=Path, required=True)
    args = parser.parse_args()
    require(args.tokenizer_package.is_dir() and args.tokenizer_cache.is_dir(),
            "local tokenizer package and cache required; no automatic downloads")
    sys.path.insert(0, str(args.tokenizer_package.resolve()))
    os.environ["TIKTOKEN_CACHE_DIR"] = str(args.tokenizer_cache.resolve())
    import tiktoken

    def forbidden(*args, **kwargs):
        raise RuntimeError("offline replay forbids network connections")

    with patch("socket.socket.connect", forbidden), patch("socket.socket.connect_ex", forbidden):
        encoding = tiktoken.get_encoding("o200k_base")
        metadata = {"package": "tiktoken", "version": tiktoken.__version__,
                    "encoding": encoding.name,
                    "cache_files": {str(p): sha256_bytes(p.read_bytes())
                                    for p in args.tokenizer_cache.iterdir() if p.is_file()}}
        run(args.manifest.resolve(), args.output.resolve(), args.after_sequence,
            lambda text: encoding.encode(text, disallowed_special=()), metadata)


if __name__ == "__main__":
    main()
