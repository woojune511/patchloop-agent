"""Project a frozen saved candidate's public observations for a source-only pair."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from diagnostics import selection_observation as selection
from diagnostics.decision_sampler import require
from patchloop.dev.context import bounded_lines, source_lines
from patchloop.dev.contracts import DevToolResult
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.util import sha256_bytes

ROOT = Path("C:/pt/selection-observation-live-v2/A")
MODEL_JOURNAL_HASH = "sha256:8991603cff33fcbdd109129c7df2c22c003f37ec4d993399688f33cc41df00de"
PUBLIC_JOURNAL_HASH = "sha256:0685600a36f50bf9acdfc6d565f100a84855f308f2c070e78378fab47b4bbe24"
CANDIDATE_HASH = "sha256:93b024b3f11ef89311d9cbf5a06a56328b14f7b7d7687746e6d24a8b9fb8e3e5"
FILE_HASH = "sha256:7728b5200cd0049919dbeeb049a7fafa6f83b2063acd7d5f6044ca8f9313bb46"
SOURCE_PATH = "astroid/modutils.py"
RANGES = {"R0": ((265, 273),), "R1": ((1, 400), (401, 676))}


def bind_file(path: Path, expected: str | None = None) -> dict:
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    require(expected is None or digest == expected, "saved public input changed: " + str(path))
    return {"path": str(path.resolve()), "hash": digest, "bytes": len(raw)}


def read_receipt(ref: dict, bindings: dict, *, root: Path = ROOT / "public") -> dict:
    """Only the public host receipt CAS is a permitted receipt source."""
    path = Path(ref["path"]).resolve()
    require(path.is_relative_to((root / "artifacts/objects/sha256").resolve()),
            "receipt is outside the public evidence store")
    binding = bind_file(path, ref["content_hash"])
    require(binding["bytes"] == ref["size_bytes"], "public receipt size changed")
    bindings[binding["path"]] = binding
    return json.loads(path.read_bytes())


def changed_lines(output: dict) -> dict:
    value = output.get("public_execution", {})
    expected = "not_applicable" if value.get("diff_hash") == selection.EMPTY_DIFF else "collected"
    require(value.get("status") == expected and value.get("omitted_file_count") == 0,
            "changed-line observation incomplete")
    result = {key: copy.deepcopy(value[key]) for key in (
        "schema_version", "status", "scope", "diff_hash", "diagnostic_only",
        "deleted_line_count", "omitted_file_count", "files")}
    result["coverage_limit"] = (
        "Python line entry in the launch thread; other threads and subprocesses are "
        "unmeasured. Not observed is not proof of unexecuted code or branch coverage."
    )
    return result


def original_public(result: dict) -> dict:
    output = result["output"]
    # Deliberately omit cached judgments, authored interpretation and host prose.
    return {
        "diff_hash": result["workspace_diff_hash"],
        "call_observation": copy.deepcopy(output["reproduction"]["call_observation"]),
        "exception_diagnostics": copy.deepcopy(output.get("exception_diagnostics")),
        "changed_line_observation": changed_lines(output),
    }


def case_public(result: dict) -> dict:
    data = selection.observation(DevToolResult.model_validate(result))
    # Explicit measured-field allowlist; no arbitrary operator summary is copied.
    observed = {key: copy.deepcopy(data[key]) for key in (
        "environment", "events", "exception", "exit_code", "inputs_after", "inputs_before",
        "layout", "outcome", "overflow", "search_paths", "stderr", "stdout", "target")}
    return {"diff_hash": result["workspace_diff_hash"], "observed": observed,
            "changed_line_observation": changed_lines(result["output"])}


def make_sources(raw: bytes) -> dict:
    require(sha256_bytes(raw) == FILE_HASH, "saved candidate source changed")
    lines = source_lines(raw.decode("utf-8"))
    require(len(lines) == 676, "saved candidate line count changed")
    packets = {}
    for arm, ranges in RANGES.items():
        spans = []
        for start, end in ranges:
            content, actual_end, clipped = bounded_lines(lines, start, end)
            require(actual_end == end and not clipped, "source packet was clipped")
            spans.append({"path": SOURCE_PATH, "start_line": start, "end_line": end,
                          "content": content, "file_hash": FILE_HASH})
        packets[arm] = spans
    require("modpath.append(part)" in packets["R0"][0]["content"],
            "do not hide the source context already present in the saved diff")
    return packets


def build_packet_bundle() -> dict:
    """Read-only preparation: no credentials, provider, target or evaluator calls."""
    bindings = {}
    model = DevJournal(ROOT, "run_dev_selectionmodel")
    public = DevJournal(ROOT / "public", "run_dev_selectionpublic")
    for journal, expected in ((model, MODEL_JOURNAL_HASH), (public, PUBLIC_JOURNAL_HASH)):
        binding = bind_file(journal.path, expected)
        bindings[binding["path"]] = binding
    model_events, public_events = model.events(), public.events()
    edits = [event["payload"] for event in model_events if event["event_type"] == "action_started"
             and event["payload"]["tool"] == "replace_text"]
    require(len(edits) == 1, "saved candidate must contain exactly one model edit")
    args = edits[0]["arguments"]
    finishes = [event["payload"]["result"] for event in model_events
                if event["event_type"] == "action_finished"
                and event["payload"]["action_id"] == edits[0]["action_id"]]
    require(len(finishes) == 1 and finishes[0]["status"] == "succeeded"
            and finishes[0]["workspace_diff_hash"] == CANDIDATE_HASH,
            "saved mutation receipt does not match candidate")
    workspace = ROOT / "workspaces/base/repo"
    diff = WorkspaceManager.diff_summary(workspace)
    require(diff.patch_hash == CANDIDATE_HASH and not diff.untracked_files
            and diff.changed_files == [SOURCE_PATH], "saved candidate diff changed")
    source_file = workspace / SOURCE_PATH
    for path, expected in ((source_file, FILE_HASH), (selection.PUBLIC, None),
                           (selection.SOURCE, selection.SOURCE_HASH),
                           (selection.HELPER, None), (Path(__file__), None)):
        binding = bind_file(path, expected)
        bindings[binding["path"]] = binding
    sources = make_sources(source_file.read_bytes())
    records = [event["payload"] for event in public_events
               if event["event_type"] == "public_checks_finished"]
    require(len(records) == 1 and records[0]["candidate_hash"] == CANDIDATE_HASH,
            "public checks are not bound to the saved candidate")
    checks = records[0]
    originals = [read_receipt(checks["original_call"][key], bindings)
                 for key in ("base_receipt", "candidate_receipt")]
    require(originals[0]["workspace_diff_hash"] == selection.EMPTY_DIFF
            and originals[1]["workspace_diff_hash"] == CANDIDATE_HASH,
            "original receipt source differs")
    summary = selection.original_summary(*originals)
    require(summary["call1_same_conditions"] and not summary["call1_F0010_resolved"],
            "saved original failure no longer matches")
    original_arguments = next(event["payload"]["arguments"] for event in public_events
                              if event["event_type"] == "action_started"
                              and event["payload"]["action_id"] == "host-original")
    cases = []
    programs = selection.programs()
    for name, (layout, child) in selection.CASES.items():
        record = checks["cases"][name]
        base, candidate = [read_receipt(record[key], bindings)
                           for key in ("base_receipt", "receipt")]
        require(base["workspace_diff_hash"] == selection.EMPTY_DIFF
                and candidate["workspace_diff_hash"] == CANDIDATE_HASH,
                "supplementary receipt source differs")
        before, after = case_public(base), case_public(candidate)
        require(all(before["observed"][key] == after["observed"][key]
                    for key in ("environment", "inputs_before", "target")),
                "supplementary conditions differ")
        args_for_case = next(event["payload"]["arguments"] for event in public_events
                             if event["event_type"] == "action_started"
                             and event["payload"]["action_id"] == "host-" + name)
        require(args_for_case["python_source"] == programs[name],
                "public fixture program changed")
        cases.append({"name": name, "layout": layout, "child_source": child,
                      "base": before, "saved_candidate": after})
    regression = read_receipt(checks["regression_receipt"], bindings)
    require(regression["workspace_diff_hash"] == CANDIDATE_HASH
            and regression["status"] == "succeeded"
            and regression["output"].get("passed") is True,
            "saved registered regression is not complete")
    common = {
        "saved_candidate_diff": diff.patch,
        "previous_authored_hypothesis": {
            "status": "model_authored_unverified", "hypothesis": args["hypothesis"],
            "expected_behavior": args["expected_behavior"]},
        "public_failure_feedback": {
            "original_call": {"program": original_arguments["python_source"],
                              "purpose": copy.deepcopy(original_arguments["purpose"]),
                              "base": original_public(originals[0]),
                              "saved_candidate": original_public(originals[1]),
                              "comparison": summary},
            "supplementary_program_template": selection.HELPER.read_text("utf-8"),
            "supplementary_cases": cases,
            "registered_regression": {
                key: copy.deepcopy(regression["output"].get(key))
                for key in ("check_id", "passed", "exit_code", "stdout", "stderr")},
        },
    }
    return {"common": common, "source_packets": sources, "seed_patch": diff.patch,
            "input_bindings": sorted(bindings.values(), key=lambda row: row["path"]),
            "provenance": {
                "candidate_diff_hash": CANDIDATE_HASH, "source_file_hash": FILE_HASH,
                "public_task_path": str(selection.PUBLIC.resolve()),
                "public_hash": sha256_bytes(selection.PUBLIC.read_bytes()),
                "prepared_source_path": str(selection.SOURCE.resolve()),
                "prepared_source_hash": selection.SOURCE_HASH,
                "original_arguments": copy.deepcopy(original_arguments),
                "public_receipts": 13, "historical_model_actions_imported": False,
                "private_evaluation_opened": False, "operator_solution_projected": False}}
