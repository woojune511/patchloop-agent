"""Process-local experimental control; product defaults and execution stay unchanged."""
from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import patch

from diagnostics.positive_verification_panel import require
from patchloop.dev import evidence_focus, model, model_state, reproduction, runner
from patchloop.dev.reproduction import call_identity
from patchloop.util import sha256_bytes

BASE = "5bd4c26c44b7edf1991178f1e58ac8240fac7875"
LEGACY = "5f2da9aecd9bcd988ad309832784ac144890b464"
PROMPT_HASHES = {
    "A": "sha256:490886aa27bed74b722ccb28de083d88a1cd5b5e5c9709487867eef4c7c78087",
    "B": "sha256:eb206661a18e29fed1eb4e7b9ef92ef485c890ac202f4b4d51482de97d8c882a",
}
CONTROL = """Use reproduction for a proposed original-caller experiment, keeping its public purpose,
input/setup and expected JSON fixed; use replay_action_id after edits. Ordinary helper
results do not resolve a reproduction. Its comparisons do not certify the experiment's
connection to the original task: account for that connection in the final assessment.
"""
_ON_PROMPT = model.DEV_SYSTEM_PROMPT
_ON_PROJECT = evidence_focus.project_interpretations
_ON_CONTEXT = runner._build_context
_ACTIVE = False


def prompt(arm):
    require(arm in {"A", "B"}, "unknown verification arm")
    require(sha256_bytes(_ON_PROMPT.encode()) == PROMPT_HASHES["B"], "base prompt changed")
    start = _ON_PROMPT.index("Bind reproduction's public purpose")
    end = _ON_PROMPT.index("behavior_verdict=not_assessed", start)
    result = _ON_PROMPT if arm == "B" else _ON_PROMPT[:start] + CONTROL + _ON_PROMPT[end:]
    require(len(result) == 8000 and sha256_bytes(result.encode()) == PROMPT_HASHES[arm],
            "assigned prompt changed")
    return result


def legacy_review(events, current_diff, *, public_task=None):
    cases, helper_count = {}, 0
    for event in events:
        if event["event_type"] != "action_finished":
            continue
        result = event["payload"]["result"]
        if result["tool"] != "run_probe":
            continue
        repro = (result.get("output") or {}).get("reproduction")
        if repro is None:
            # Rejected declarations/replays are actions, not executed helpers.
            helper_count += isinstance((result.get("output") or {}).get("source_hash"), str)
            continue
        binding = repro["binding"]
        row = {
            "action_id": result["action_id"],
            "diff_hash": result["workspace_diff_hash"],
            "comparison": repro["comparison"],
            "reason": repro["reason"],
            "call_observation": repro["call_observation"],
        }
        case = cases.setdefault(
            binding["case_id"], {"binding": binding, "baseline": None, "latest": None}
        )
        # A new declaration is a new baseline; it cannot resolve a previous case.
        if result["action_id"] == binding["root_action_id"]:
            case["baseline"] = row
        case["latest"] = row
    items = []
    for case in cases.values():
        base, latest = case["baseline"], case["latest"]
        progress = "baseline_not_observed"
        if base is not None:
            if latest["diff_hash"] != current_diff:
                progress = "current_diff_not_observed"
            elif latest["diff_hash"] == base["diff_hash"]:
                progress = "no_modified_diff_comparison"
            elif base["comparison"] != "mismatched":
                progress = "baseline_not_different"
            elif latest["comparison"] == "not_compared":
                progress = "current_observation_incomplete"
            elif call_identity(base["call_observation"]) != call_identity(
                latest["call_observation"]
            ):
                progress = "observed_call_or_setup_changed"
            else:
                progress = (
                    "mismatch_to_match" if latest["comparison"] == "matched" else "still_mismatched"
                )

        def compact(row):
            return (
                None if row is None else {k: v for k, v in row.items() if k != "call_observation"}
            )

        items.append(
            {
                "case_id": case["binding"]["case_id"],
                "purpose": case["binding"]["definition"],
                "baseline": compact(base),
                "latest": compact(latest),
                "comparison_status": progress,
                "requirement_mapping": "model_authored_unverified",
                "repair_success": "not_assessed",
            }
        )
    return {
        "original_task_verification": "mapping_unverified" if items else "no_bound_reproduction",
        "helper_or_unbound_executions": helper_count,
        "items": items[:3],
        "omitted_count": max(0, len(items) - 3),
        "interpretation": "Helper results and suite PASS cannot resolve a reproduction. "
        "Replay the original action on the current diff, preserving its purpose and predicate. "
        "Even mismatch_to_match verifies only that declared experiment; assess its connection "
        "to the reported caller/input/failure separately. Submission eligibility is unchanged.",
    }


def legacy_interpretations(view, history, *, archive_kind=None):
    # Preserve every common annotation, reversing only the model-facing name hunk.
    before = view.get("working_notes", {}).get("verification", {})
    had_ids = "unresolved_ids" in before or "model_open_concern_ids" in before
    _ON_PROJECT(view, history, archive_kind=archive_kind)
    verification = view.get("working_notes", {}).get("verification")
    if isinstance(verification, dict):
        identifiers = verification.pop("model_open_concern_ids", [])
        if had_ids:
            verification["unresolved_ids"] = identifiers
        for concern in verification.get("items", []):
            concern["status"] = concern.pop("model_position")


def legacy_context(**kwargs):
    value = _ON_CONTEXT(**kwargs)
    if getattr(kwargs["gateway"], "probe_sandbox", None) is None:
        data = json.loads(value)
        data.pop("reproduction_review", None)
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return value


@contextmanager
def assigned(arm):
    """One arm per process; all patches restore on exit, including exceptional exits."""
    global _ACTIVE
    require(not _ACTIVE, "verification arms cannot be nested or shared across threads")
    assigned_prompt = prompt(arm)
    _ACTIVE = True
    try:
        if arm == "B":
            yield
        else:
            with (patch.object(model, "DEV_SYSTEM_PROMPT", assigned_prompt),
                  patch.object(runner, "DEV_SYSTEM_PROMPT", assigned_prompt),
                  patch.object(reproduction, "review", legacy_review),
                  patch.object(evidence_focus, "project_interpretations", legacy_interpretations),
                  patch.object(model_state, "project_interpretations", legacy_interpretations),
                  patch.object(runner, "_build_context", legacy_context)):
                yield
    finally:
        _ACTIVE = False


def initialize_off_worker(stop, admission):
    """Spawn-safe initializer for the existing serial allocation worker."""
    from diagnostics.parallel_dev_batch import initialize_worker

    initialize_worker(stop, admission)
    global _WORKER_SCOPE
    _WORKER_SCOPE = assigned("A")
    _WORKER_SCOPE.__enter__()
