"""Project caller linkage onto saved public inputs without running saved programs."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from diagnostics.caller_uptake import file_ref, read_ref
from diagnostics.verification_role_qualification import save
from diagnostics.verification_state_grading import decisions, public_index
from patchloop.contracts import PublicTask
from patchloop.dev import reproduction
from patchloop.dev.conversation import STATE_KIND, reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json, sha256_bytes, sha256_json


def previous_view(review):
    """Remove only the new disclosure; preserve every prior classification and witness."""
    result = copy.deepcopy(review)
    for case in result["items"]:
        case.pop("replay_action_id")
        for phase in ("baseline", "latest"):
            if case[phase] is not None:
                case[phase].pop("execution_link")
    return result


def project(wire, review):
    result = copy.deepcopy(wire)
    for item in reversed(result["input"]):
        if item.get("role") != "developer":
            continue
        value = json.loads(item["content"])
        if value.get("kind") == STATE_KIND:
            value["state"]["reproduction_review"] = review
            item["content"] = canonical_json(value)
            break
    else:
        initial = json.loads(result["input"][1]["content"])
        initial["reproduction_review"] = review
        result["input"][1]["content"] = canonical_json(initial)
    for tool in result["tools"]:
        if tool["name"] == "run_probe":
            before, marker, _ = tool["description"].partition("Choose purpose for each new probe")
            assert marker, "unexpected historical probe description"
            tool["description"] = before + reproduction.DESCRIPTION
    return result


def replay(audit, output):
    output.mkdir(parents=True, exist_ok=False)
    (output / "executed-script.py").write_bytes(Path(__file__).read_bytes())
    journal = DevJournal(output, "run_dev_probeinvocationreplay")
    index_path = audit / "index.json"
    index = json.loads(index_path.read_bytes())
    journal.append("replay_started", {"public_index": file_ref(index_path),
        "script": file_ref(output / "executed-script.py"), "provider_calls": 0,
        "input_count_calls": 0, "historical_programs_executed": 0})
    rows = []
    for public_id, ref in index["files"].items():
        public = json.loads(read_ref(ref))
        public_index(public)
        prior, inputs, probes = [], [], []
        for event in public["events"]:
            if event["event_type"] == "provider_call_started":
                wire = event["payload"]["wire"]
                state = reconstruct_state(wire["input"], context_policy="segmented-v1")
                review = reproduction.review(prior, state["current_diff"]["patch_hash"],
                    public_task=PublicTask.model_validate(state["public_task"]))
                assert previous_view(review) == state["reproduction_review"]
                projected = project(wire, review)
                expected = {**state, "reproduction_review": review}
                assert reconstruct_state(
                    projected["input"], context_policy="segmented-v1") == expected
                # No source, notes, native evidence, limits, schema field or verdict is evicted.
                def native(items):
                    return [v for v in items if v.get("type") in {
                        "reasoning", "function_call", "function_call_output"}]
                assert native(wire["input"]) == native(projected["input"])
                for old, new in zip(wire["tools"], projected["tools"], strict=True):
                    assert {k: v for k, v in old.items() if k != "description"} == {
                        k: v for k, v in new.items() if k != "description"}
                    if old["name"] != "run_probe":
                        assert old == new
                inputs.append({"sequence": event["sequence"],
                    "request_hash": event["payload"]["actual_request_hash"],
                    "prior_view_hash": sha256_json(state["reproduction_review"]),
                    "new_view_hash": sha256_json(review), "bound_cases": len(review["items"]),
                    "prior_classifications_unchanged": True,
                    "other_state_and_native_unchanged": True,
                    "view_byte_delta": len(canonical_json(review).encode()) -
                                       len(canonical_json(state["reproduction_review"]).encode()),
                    "public_wire_byte_delta": len(canonical_json(projected).encode()) -
                                              len(canonical_json(wire).encode()),
                    "execution_links": [c["latest"]["execution_link"] for c in review["items"]],
                })
            prior.append(event)
        for decision in decisions(public):
            if decision["tool"] != "run_probe" or not decision["receipt"]:
                continue
            output_value = decision["receipt"]["payload"]["result"].get("output") or {}
            evidence = output_value.get("reproduction")
            if evidence:
                source = decision["call"]["arguments"]["python_source"]
                execution = reproduction.program(source, evidence["binding"])
                assert sha256_bytes(execution.encode()) == output_value["execution_source_hash"]
            probes.append({"decision_sequence": decision["decision_sequence"],
                "receipt_hash": decision["receipt"]["event_hash"],
                "classification": evidence["comparison"] if evidence else "unbound_unchanged",
                "reason": evidence["reason"] if evidence else None,
                "declared_entrypoint": evidence["binding"]["definition"]["entrypoint"]
                                       if evidence else None,
                "observed_calls": len(evidence["call_observation"]["calls"]) if evidence else None,
                "legacy_execution_bytes_preserved": True if evidence else None,
                "historical_program_executed": False})
        row = {"public_id": public_id, "public": ref, "inputs": inputs, "probes": probes}
        journal.append("public_run_checked", {"row": save(output, public_id + ".json", row)})
        rows.append({"public_id": public_id, "inputs": len(inputs), "probes": probes,
            "bound_case_inputs": sum(bool(i["bound_cases"]) for i in inputs),
            "view_byte_deltas": sorted({i["view_byte_delta"] for i in inputs}),
            "public_wire_byte_deltas": sorted({i["public_wire_byte_delta"] for i in inputs})})
    summary = {"rows": rows, "provider_calls": 0, "input_count_calls": 0,
        "historical_programs_executed": 0, "evaluator_calls": 0,
        "scope": "Saved public inputs only. Previous grades and programs are unchanged; "
                 "adding linkage disclosure evicts no existing field in this projection. "
                 "Encrypted bodies are redacted, so full input tokens, future size handoffs, "
                 "model uptake and repair success are not measured."}
    journal.append("replay_closed", {"summary": save(output, "summary.json", summary)})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(canonical_json(replay(args.audit, args.output)))


if __name__ == "__main__":
    main()
