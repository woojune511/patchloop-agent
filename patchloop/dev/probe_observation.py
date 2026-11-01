"""Execution observations are not answers to the model's experimental question."""

from __future__ import annotations

import copy
from typing import Any

from patchloop.util import sha256_bytes, sha256_json

MAX_OBSERVATION_FILES = 4
MAX_OBSERVATION_RANGES = 3


def bound_probe_program(result: dict[str, Any], started: dict[str, Any]) -> dict[str, str] | None:
    """Expose the exact executed public helper, including its input and assertions.

    Replay/case requests bind their resolved program at admission. The program is
    experimental setup, not public-task coverage or a successful behavior verdict.
    Missing/inconsistent receipts cannot supply a guessed program.
    """
    output = result.get("output", {})
    if (result.get("tool") != "run_probe" or started.get("tool") != "run_probe"
            or result.get("status") != "succeeded"
            or not result.get("input_hash") or not result.get("workspace_diff_hash")
            or result.get("action_id") != started.get("action_id")
            or result["input_hash"] != started.get("input_hash")
            or result["workspace_diff_hash"] != started.get("baseline_diff_hash")
            or result["workspace_diff_hash"] != output.get("diff_hash")):
        return None
    request = (started.get("probe_replay_request") or started.get("probe_case_request")
               or started.get("arguments", {}))
    action_input = {"tool": started["tool"], "arguments": started.get("arguments", {})}
    if started.get("turn_decision") is not None:
        action_input["turn_decision"] = started["turn_decision"]
    if "memory_update" in started:
        action_input["memory_update"] = started["memory_update"]
    source, question = request.get("python_source"), request.get("question")
    if (not isinstance(source, str) or not 1 <= len(source) <= 8_000
            or not isinstance(question, str) or not 1 <= len(question) <= 500
            or result["input_hash"] != sha256_json(action_input)
            or output.get("question") != question
            or output.get("source_hash") != sha256_bytes(source.encode("utf-8"))):
        return None
    return {"python_source": source, "source_hash": output["source_hash"]}


def probe_observation(result: dict[str, Any]) -> dict[str, Any]:
    """Summarize an already public receipt; never infer behavior from exit or line entry."""
    output = result.get("output", {})
    status = output.get("status", "not_run" if result.get("status") == "failed" else "unknown")
    feedback = output.get("public_execution") or {}
    source_files = feedback.get("files", [])
    files = []
    for source in source_files[:MAX_OBSERVATION_FILES]:
        row = {key: source[key] for key in ("path", "file_hash", "status", "reason")
               if key in source}
        for prefix, field in (("observed", "executed_changed_ranges"),
                              ("not_observed", "not_observed_changed_ranges")):
            ranges = source.get(field) if source.get("status") == "collected" else None
            row[f"{prefix}_changed_line_count"] = (
                sum(end - start + 1 for start, end in ranges) if ranges is not None else None
            )
            row[f"{prefix}_ranges"] = (
                copy.deepcopy(ranges[:MAX_OBSERVATION_RANGES]) if ranges is not None else None
            )
            row[f"{prefix}_omitted_range_count"] = (
                max(0, len(ranges) - MAX_OBSERVATION_RANGES) if ranges is not None else None
            )
        files.append(row)
    observation = {
        "execution_status": "completed" if status == "passed" else status,
        "behavior_verdict": "not_assessed",
        "line_entry_observation": {
            "status": feedback.get("status", "unknown"),
            "scope": "python_launch_thread",
            "files": files,
            "omitted_file_count": feedback.get("omitted_file_count", 0)
            + max(0, len(source_files) - MAX_OBSERVATION_FILES),
        },
        "interpretation": (
            "Execution completed does not mean the question was verified. Line entry is not "
            "branch/assertion coverage; unmeasured threads and inputs remain unknown. "
            "Compare the actual input, output and relevant ranges before drawing a conclusion."
        ),
    }
    setup = output.get("setup_checks")
    if isinstance(setup, dict):
        setup_status = setup.get("status", "unknown")
        observation["setup_check_observation"] = {
            "status": setup_status, "check_count": len(setup.get("checks", [])),
            "interpretation": (
                "Actual supplied setup values differ from expectations. Check construction "
                "and the expectation before attributing this mismatch to candidate behavior. "
                if setup_status == "failed" else
                "Only the program's selected setup comparisons are observed. "
            ) + "Setup checks do not assess behavior correctness or public applicability.",
        }
    if status == "failed" and any(
        line.startswith(("ModuleNotFoundError:", "ImportError:"))
        for line in output.get("stderr", "").splitlines()
    ):
        environment_message = (
            "Only /workspace is added to sys.path; "
            "a src layout may need its observed source root added explicitly. Project "
            "dependencies are not installed and cannot be installed in this probe. "
        )
        if output.get("execution_policy", {}).get("dependencies") is not None:
            environment_message = (
                "Prepared public dependencies and source import roots are available, but "
                "additional packages cannot be installed in this probe. "
            )
        observation["environment_guidance"] = {
            "basis": "reported_import_error",
            "message": (
                "Stderr reports an import error. " + environment_message +
                "Use the traceback to distinguish path, dependency and API errors. If imports "
                "remain unavailable, isolate the relevant mechanism with the standard library, "
                "print or assert the expected observation, and state the reduction's limits. "
                "An import error alone does not test the intended behavior; a reduced experiment "
                "does not verify the project implementation."
            ),
        }
    return observation


def project_probe_result(result: dict[str, Any]) -> dict[str, Any]:
    """Relabel only the model view; durable execution receipts and their hashes stay exact."""
    if result.get("tool") not in {"run_probe", "observe_original"}:
        return result
    projected = copy.deepcopy(result)
    projected["observation"] = probe_observation(result)
    # In canonical JSON 'observation' precedes the detailed 'output'. The original
    # sandbox status stays in the journal, not as an ambiguous model-facing PASS.
    projected["output"].pop("status", None)
    return projected
