"""Offline saved-state and log-channel checks; never reclassify historical probes."""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

from diagnostics.caller_uptake import file_ref, read_ref
from diagnostics.verification_state_grading import decisions, public_index
from diagnostics.verification_state_off import legacy_review
from patchloop.contracts import PublicTask
from patchloop.dev import reproduction
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.sandbox.probes import PROBE_OUTPUT_LIMIT_BYTES, PROBE_SOURCE_LIMIT_CHARS
from patchloop.util import canonical_json, sha256_bytes, sha256_json


def transport_fixture(output, value):
    """Only execute a fixed stdlib fixture; saved programs are never executed."""
    source = (
        "import json, sys\n"
        f"print({output.get('stdout', '')!r}, end='')\n"
        f"sys.stderr.write({output.get('stderr', '')!r})\n"
        f"record_observation(json.loads({canonical_json({'observed': value})!r}))\n"
    )
    binding = {
        "case_id": sha256_json({"transport_fixture": source}),
        "program_hash": sha256_bytes(source.encode()), "root_action_id": "transport-fixture",
        "definition": {"entrypoint": "json.loads", "expected_json": '{"observed":1}',
                       "observation_channel": reproduction.OBSERVATION_CHANNEL},
    }
    execution = reproduction.program(source, binding)
    assert len(execution) <= PROBE_SOURCE_LIMIT_CHARS
    process = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", execution],
        capture_output=True, timeout=10, check=False,
    )
    assert len(process.stdout) + len(process.stderr) <= PROBE_OUTPUT_LIMIT_BYTES
    receipt = reproduction.compare({
        "source_hash": sha256_bytes(execution.encode()),
        "status": "passed" if process.returncode == 0 else "failed",
        "exit_code": process.returncode, "stdout": process.stdout.decode("utf-8"),
        "stderr": process.stderr.decode("utf-8"), "truncated": False,
        "timed_out": False, "cleanup_failed": False, "deadline_exhausted": False,
    }, binding)
    assert receipt["stdout"].replace("\r\n", "\n") == output.get("stdout", "").replace("\r\n", "\n")
    assert receipt["reproduction"]["comparison"] == ("matched" if value == 1 else "mismatched")
    return {"fixture_source_hash": binding["program_hash"], "execution_chars": len(execution),
            "comparison": receipt["reproduction"]["comparison"],
            "historical_program_executed": False, "original_requirement_verified": False}


def replay(audit, output):
    output.mkdir(exist_ok=False, parents=True)
    script = output / "executed-script.py"
    with script.open("xb") as stream:
        stream.write(Path(__file__).read_bytes())
    journal = DevJournal(output, "run_dev_probepurposereplay")
    index = json.loads((audit / "index.json").read_bytes())
    journal.append("replay_started", {
        "public_index": file_ref(audit / "index.json"), "script": file_ref(script),
        "provider_calls": 0, "evaluator_calls": 0,
    })
    rows = []
    for public_id, ref in index["files"].items():
        public = json.loads(read_ref(ref))
        public_index(public)
        prior, inputs, fixtures = [], [], []
        for event in public["events"]:
            if event["event_type"] == "provider_call_started":
                wire = event["payload"]["wire"]
                state = reconstruct_state(wire["input"], context_policy="segmented-v1")
                task = PublicTask.model_validate(state["public_task"])
                review = state["reproduction_review"]
                reader = reproduction.review if "required" in review else legacy_review
                assert reader(
                    prior, state["current_diff"]["patch_hash"], public_task=task,
                ) == review
                projected = copy.deepcopy(wire)
                for tool in projected["tools"]:
                    if tool["name"] != "run_probe":
                        continue
                    header = "For a proposed original-task reproduction, "
                    assert header in tool["description"]
                    description = tool["description"].split(header)[0]
                    assert "State the expected observation" in description
                    description = description.replace(
                        "State the expected observation",
                        "For helper probes, state the expected observation", 1,
                    )
                    tool["description"] = description + reproduction.DESCRIPTION
                    params = tool["parameters"]
                    params["properties"] = {
                        ("purpose" if key == "reproduction" else key):
                        (reproduction.purpose_schema() if key == "reproduction" else value)
                        for key, value in params["properties"].items()
                    }
                    params["required"] = [
                        "purpose" if key == "reproduction" else key for key in params["required"]]
                assert projected["input"] == wire["input"]
                inputs.append({
                    "sequence": event["sequence"],
                    "request_hash": event["payload"]["actual_request_hash"],
                    "state_unchanged": True,
                    "public_wire_byte_delta": len(canonical_json(projected).encode())
                    - len(canonical_json(wire).encode()),
                })
            prior.append(event)
        for decision in decisions(public):
            if decision["tool"] != "run_probe" or not decision["receipt"]:
                continue
            result = decision["receipt"]["payload"]["result"]
            assert decision["call"]["arguments"].get("reproduction") is None
            assert "reproduction" not in (result.get("output") or {})
            fixtures.append({
                "decision_sequence": decision["decision_sequence"],
                "receipt_hash": decision["receipt"]["event_hash"],
                "historical_classification": "unbound_unchanged",
                "transport_only": [transport_fixture(result["output"], v) for v in (0, 1)],
            })
        row = {"public_id": public_id, "public": ref, "inputs": inputs, "fixtures": fixtures}
        path = output / (public_id + ".json")
        with path.open("x", encoding="utf-8") as stream:
            stream.write(canonical_json(row) + "\n")
        journal.append("saved_run_checked", {"row": file_ref(path)})
        rows.append({"public_id": public_id, "inputs": len(inputs),
                     "unchanged_unbound_probes": len(fixtures),
                     "public_wire_byte_deltas": sorted(
                         {i["public_wire_byte_delta"] for i in inputs})})
    summary = {
        "rows": rows, "provider_calls": 0, "evaluator_calls": 0,
        "limits": "Only tool disclosure projected; actual input tokens and future trajectories "
                  "are not measured. Transport fixtures use saved log text with synthetic stdlib "
                  "observations, never historical caller executions or repair verdicts.",
    }
    path = output / "summary.json"
    with path.open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(summary) + "\n")
    journal.append("replay_closed", {"summary": file_ref(path)})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(canonical_json(replay(args.audit, args.output)))


if __name__ == "__main__":
    main()
