"""Execution observations are not answers to the model's experimental question."""

from __future__ import annotations

import copy
from typing import Any

MAX_OBSERVATION_FILES = 4
MAX_OBSERVATION_RANGES = 3


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
    return {
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


def project_probe_result(result: dict[str, Any]) -> dict[str, Any]:
    """Relabel only the model view; durable execution receipts and their hashes stay exact."""
    if result.get("tool") != "run_probe":
        return result
    projected = copy.deepcopy(result)
    projected["observation"] = probe_observation(result)
    # In canonical JSON 'observation' precedes the detailed 'output'. The original
    # sandbox status stays in the journal, not as an ambiguous model-facing PASS.
    projected["output"].pop("status", None)
    return projected
