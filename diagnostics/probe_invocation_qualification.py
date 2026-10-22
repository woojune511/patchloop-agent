"""Provider-free packet comparison and saved-log qualification. No saved tools run."""

from __future__ import annotations

import argparse
import copy
import json
import os
import socket
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from diagnostics import probe_invocation_control as control
from diagnostics import probe_invocation_grading as linkage
from diagnostics import probe_invocation_panel as panel
from diagnostics import probe_invocation_replay as replay
from diagnostics import size_only_replay as saved
from diagnostics import verification_role_grading as grading
from diagnostics import verification_role_qualification as phase
from diagnostics.caller_uptake import file_ref, read_ref
from diagnostics.positive_verification_panel import require
from patchloop import prepared_probe_dependencies as deps
from patchloop.contracts import PublicTask
from patchloop.dev import reproduction, segments
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.runtime import git_commit, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

save = phase.save


def normalized(value):
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            return value
        return normalized(parsed) if isinstance(parsed, (dict, list)) else value
    if isinstance(value, list):
        return [normalized(v) for v in value]
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in value.items()}
    return value


def compare_inputs(wires, *, initial=False):
    values = {a: normalized(w) for a, w in wires.items()}
    for arm, value in values.items():
        expected = control.DESCRIPTION if arm == "A" else reproduction.DESCRIPTION
        for tool in value["tools"]:
            if tool["name"] == "run_probe":
                require(tool["description"].endswith(expected), "wrong invocation description")
                tool["description"] = tool["description"][: -len(expected)] + control.DESCRIPTION

        def visit(node, arm=arm):
            if isinstance(node, list):
                for item in node:
                    visit(item)
            elif isinstance(node, dict):
                if "reproduction_review" in node:
                    old = control.previous_view(node["reproduction_review"])
                    require(arm != "A" or old == node["reproduction_review"], "OFF review leaked")
                    node["reproduction_review"] = old
                if "segment_handoff" in node:
                    node["segment_handoff"]["segment_id"] = "<derived-segment-id>"
                for item in node.values():
                    visit(item)

        visit(value)
    require(
        values["A"] == values["B"], "difference outside guidance/review/derived segment identity"
    )
    facts, receipts = {}, {}
    for arm, wire in wires.items():
        facts[arm], receipts[arm] = phase.exposed(wire)
        state = reconstruct_state(wire["input"], context_policy="segmented-v1")
        require(not initial or not state["current_diff"]["patch"], "initial capture has a patch")
    return {
        "allowed_paths": [
            "tools.run_probe.description",
            "reproduction_review.*.execution_link",
            "reproduction_review.*.replay_action_id",
            "segment_handoff.segment_id",
        ],
        "contrast_present": wires["A"] != wires["B"],
        "common_state_and_schemas_equal": True,
        "tools_equal": wires["A"]["tools"] == wires["B"]["tools"],
        "derived_segment_ids_checked": True,
        "wire_bytes": {a: len(canonical_json(w).encode()) for a, w in wires.items()},
        "displacement": {
            "A_minus_B": phase.ranges(facts["A"] - facts["B"]),
            "B_minus_A": phase.ranges(facts["B"] - facts["A"]),
            "A_receipts_missing_from_B": sorted(receipts["A"] - receipts["B"]),
            "B_receipts_missing_from_A": sorted(receipts["B"] - receipts["A"]),
        },
    }


def bounded_estimate(turn, wire, estimator):
    value = estimator.estimate(turn, wire["input"])
    delta = estimator.text_count(canonical_json(wire["tools"])) - estimator.text_count(
        canonical_json(turn.wire["tools"])
    )
    for key in ("lower", "central", "upper"):
        value[key] = max(0, value[key] + delta)
    if delta and value["saved_exact_input"]:
        value["lower"] = max(0, value["lower"] - estimator.margin)
        value["upper"] += estimator.margin
    return {**value, "schema_token_delta": delta, "provider_count": False}


def qualify(manifest, audit, annotations, output, encode):
    output.mkdir(parents=True, exist_ok=False)
    journal = DevJournal(output, "run_dev_probeinvocationqualification53")
    identity = {
        "head": git_commit(),
        "runtime_hash": runtime_content_hash(),
        "implementation": panel.bindings(),
        "contract_hash": sha256_json(control.contract()),
        "provider_calls": 0,
        "input_count_calls": 0,
    }
    journal.append(
        "qualification_started",
        {
            **identity,
            "manifest": file_ref(manifest),
            "public_index": file_ref(audit / "index.json"),
            "annotations": file_ref(annotations),
        },
    )
    historical = replay.replay(audit, output / "legacy")
    index = json.loads((audit / "index.json").read_bytes())["files"]
    old_reviews = json.loads(annotations.read_bytes())["rows"]
    grades = {
        r["public_id"]: grading.validate_annotation(r, json.loads(read_ref(index[r["public_id"]])))
        for r in old_reviews
    }
    save(output, "unchanged-public-judgments.json", grades)
    inventories = {}
    for public_id, ref in index.items():
        public = json.loads(read_ref(ref))
        inventories[public_id] = {
            "probes": linkage.inventory(public),
            "opportunities": linkage.opportunities(public),
            "delivery": linkage.delivery_inventory(public),
            "classification": "historical public observation; no new treatment or outcomes",
        }
    save(output, "historical-linkage-inventory.json", inventories)
    all_inputs, checkpoints, reads = [], [], {}
    loaded, all_turns, reasoning = [], [], {}
    for row in json.loads(manifest.read_bytes())["rows"]:
        state_root = Path(row["request"]["state_root"])
        (path,) = (state_root / "runs").glob("*.jsonl")
        historical_row = copy.deepcopy(row)
        historical_row["request"]["resume_run_id"] = path.stem
        turns, opaque_usage, bound_reads = saved.load_row(historical_row, 0)
        reads.update(bound_reads)
        loaded.append((row, path, turns))
        all_turns.extend(turns)
        reasoning.update(opaque_usage)
    estimator = saved.TokenEstimator(encode, reasoning, all_turns)
    for row, path, turns in loaded:
        state_root = Path(row["request"]["state_root"])
        public = json.loads(read_ref(index[row["public_id"]]))
        events = public["events"]
        by_sequence = {
            e["sequence"]: e for e in events if e["event_type"] == "provider_call_started"
        }
        for turn in turns:
            wire = by_sequence[turn.sequence]["payload"]["wire"]
            # Public export redacts opaque bytes. Restore only the exact saved opaque
            # items to measure limits; they are never interpreted or displayed.
            public_wire = copy.deepcopy(wire)
            opaque = iter(i for i in turn.wire["input"] if i.get("type") == "reasoning")
            public_wire["input"] = [
                next(opaque) if i.get("type") == "reasoning_redacted" else i
                for i in public_wire["input"]
            ]
            require(
                public_wire == turn.wire, "public capture differs from saved dispatched request"
            )
            prior = [e for e in events if e["sequence"] < turn.sequence]
            review = reproduction.review(
                prior,
                turn.state["current_diff"]["patch_hash"],
                public_task=PublicTask.model_validate(turn.state["public_task"]),
            )
            wires = {"A": turn.wire, "B": replay.project(turn.wire, review)}
            comparison = compare_inputs(wires)
            details = {
                a: {
                    "sizes": segments.request_sizes(w),
                    "tokens": bounded_estimate(turn, w, estimator),
                }
                for a, w in wires.items()
            }
            for arm, detail in details.items():
                if detail["tokens"]["upper"] <= 60_000:
                    continue
                base, optional = saved.fresh_base(turn)
                handoff = {**turn.handoff, "reason": "input_tokens", "review_requested": True}
                fresh = {
                    **turn.wire,
                    "input": saved.compose(
                        turn,
                        None,
                        handoff,
                        base=base,
                        replay_boundary=turn.prefix[-1]["sequence"] + 1,
                    ),
                }
                fresh_review = control.previous_view(review) if arm == "A" else review
                with control.assigned(arm):
                    fresh = replay.project(fresh, fresh_review)
                old_facts, old_receipts = phase.exposed(wires[arm])
                new_facts, new_receipts = phase.exposed(fresh)
                detail["size_transition_sensitivity"] = {
                    "sizes": segments.request_sizes(fresh),
                    "tokens": bounded_estimate(turn, fresh, estimator),
                    "optional_reference_ids": optional,
                    "lost_lines": phase.ranges(old_facts - new_facts),
                    "gained_lines": phase.ranges(new_facts - old_facts),
                    "lost_receipts": sorted(old_receipts - new_receipts),
                    "gained_receipts": sorted(new_receipts - old_receipts),
                    "scope": "Estimated-bound checkpoint sensitivity; not a live transition.",
                }
            all_inputs.append(
                {
                    "row": row["row_id"],
                    "sequence": turn.sequence,
                    "phase": turn.state["verification_phase"]["phase"],
                    "handoff": turn.handoff,
                    "comparison": comparison,
                    "arms": details,
                }
            )
        # Same public checkpoint before the first verify request, both same-context.
        selected = next(t for t in turns if t.state["verification_phase"]["phase"] == "verify")
        req = panel.request(output / "not-executable", row["row_id"])
        task = PublicTask.model_validate(selected.state["public_task"])
        environment = deps.load_dependencies(
            panel.common.DEPENDENCIES, task, deps.admit(panel.common.DEPENDENCIES)
        ).environment
        wires, states = {}, {}
        for arm in "AB":
            with control.assigned(arm):
                wires[arm], states[arm], more_reads = phase.capture_checkpoint(
                    output / row["row_id"] / arm,
                    selected,
                    DevJournal(state_root, path.stem),
                    req,
                    "A",
                    environment,
                )
            reads.update(more_reads)
        checkpoints.append(
            {
                "row": row["row_id"],
                "sequence": selected.sequence,
                "comparison": compare_inputs(wires),
                "arms": {
                    a: {
                        "sizes": segments.request_sizes(w),
                        "tokens": bounded_estimate(selected, w, estimator),
                        "funding": phase.funding(60_000, states[a]),
                    }
                    for a, w in wires.items()
                },
            }
        )
    for path, digest in reads.items():
        require(sha256_bytes(Path(path).read_bytes()) == digest, "historical bytes changed")
    all_bounded = all(
        not segments.size_reasons(v.get("size_transition_sensitivity", v)["sizes"])
        and v.get("size_transition_sensitivity", v)["tokens"]["upper"] <= 60_000
        for r in all_inputs + checkpoints
        for v in r["arms"].values()
    )
    funding = all(
        v["funding"][p]["funded"]
        for r in checkpoints
        for v in r["arms"].values()
        for p in ("verification", "final")
    )
    summary = {
        **identity,
        "historical_inputs": len(all_inputs),
        "public_audits": len(grades),
        "historical_programs_executed": 0,
        "historical_files_unchanged": len(reads),
        "legacy": historical,
        "all_bounded": all_bounded,
        "minimum_funding": funding,
        "calibration": estimator.calibration,
        "checkpoints": checkpoints,
        "limitations": [
            "Fixed past trajectories; new behavior, uptake, judgment and repair are unmeasured.",
            "Saved-count anchored tokenizer delta with empirical margin; no provider count.",
            "Floor funding is not useful reasoning capacity; maximum output can consume reserve.",
        ],
    }
    save(output, "input-comparisons.json", all_inputs)
    save(output, "source-reads.json", reads)
    ref = save(output, "summary.json", summary)
    journal.append("qualification_finished", {"summary": ref})
    return summary


def receipts(root, summary, initial, local):
    identity = {
        k: summary[k]
        for k in (
            "head",
            "runtime_hash",
            "implementation",
            "contract_hash",
            "provider_calls",
            "input_count_calls",
        )
    }
    initial_ref = save(root, "initial-comparison.json", panel.initial_pair(initial))
    require(
        set(local) == {"A", "B"} and all(v["passed"] for v in local.values()),
        "both local before/after and return paths required",
    )
    for value in local.values():
        calls = Counter(item["phase"] for item in value["inputs"])
        value["minimum_path_funding"] = {
            name: {
                "calls": count,
                "nanos_at_60k_input_128_output": count * phase.floor_cost(60_000),
                "phase_nanos": phase.role.LIMITS[name]["cost_nanos"],
            }
            for name, count in calls.items()
        }
        require(
            value["wrapped_chars"] <= 8_000
            and value["model_calls"] <= 40
            and all(
                count <= phase.role.LIMITS[name]["model_calls"]
                and count * phase.floor_cost(60_000) <= phase.role.LIMITS[name]["cost_nanos"]
                for name, count in calls.items()
            ),
            "measured minimum local path not funded",
        )
    local_ref = save(root, "local-paths.json", local)
    outcomes = {
        "same_snapshot_capture": summary["all_bounded"] and len(summary["checkpoints"]) == 6,
        "historical_packet_replay": summary["historical_inputs"] == 149
        and summary["public_audits"] == 6,
        "resource_feasibility": summary["all_bounded"] and summary["minimum_funding"],
    }
    gates = {"contract_hash": identity["contract_hash"]}
    for gate, passed in outcomes.items():
        gates[gate] = save(
            root,
            gate + ".json",
            {
                **identity,
                "gate": gate,
                "passed": passed,
                "evidence": [
                    file_ref(root / "summary.json"),
                    file_ref(root / "input-comparisons.json"),
                    initial_ref,
                    local_ref,
                ],
            },
        )
    return gates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "audit", "annotations", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--tokenizer-package", type=Path, required=True)
    parser.add_argument("--tokenizer-cache", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.tokenizer_package))
    os.environ["TIKTOKEN_CACHE_DIR"] = str(args.tokenizer_cache)
    import tiktoken

    with patch.object(socket.socket, "connect", side_effect=AssertionError("offline only")):
        result = qualify(
            args.manifest,
            args.audit,
            args.annotations,
            args.output,
            tiktoken.get_encoding("o200k_base").encode,
        )
    print(
        canonical_json(
            {k: result[k] for k in ("historical_inputs", "all_bounded", "minimum_funding")}
        )
    )


if __name__ == "__main__":
    main()
