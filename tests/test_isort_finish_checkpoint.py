"""Advice subtraction never changes tools, eligibility, plans or historical inputs."""

from __future__ import annotations

import copy
import json

import pytest

from diagnostics import isort_finish_checkpoint as checkpoint
from patchloop.errors import ContractError
from patchloop.util import canonical_json


def items(prefix, stage="ready_to_submit"):
    return [
        {"role": "system", "content": "Use finish_task when appropriate."},
        {"role": "developer", "content": "Historical finish_task advice stays byte-identical."},
        {
            "role": "developer",
            "content": canonical_json(
                {
                    "kind": "harness_current_state",
                    "state": {
                        "completion_guidance": {
                            "stage": stage,
                            "diff_hash": "seed",
                            "submission_ready": True,
                            "next_action": {"tool": "finish_task"},
                            "message": prefix,
                        },
                        "working_plan": {"text": "Keep the old plan.", "revision": 15},
                        "operator_public_observation": {
                            "program": "unchanged",
                            "result": "negative",
                        },
                        "available_tool_names": ["finish_task", "replace_text", "run_probe"],
                        "workflow_gate": "ready_to_submit",
                    },
                }
            ),
        },
    ]


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("suffix", ["", " Remaining solver time includes finish_task."])
def test_both_frozen_message_forms_only_remove_advice_and_preserve_suffix(index, suffix):
    prefix = checkpoint.MESSAGE_PREFIXES[index]
    before = items(prefix["before"] + suffix)
    saved = copy.deepcopy(before)
    after = checkpoint.remove_finish_advice(before)
    assert before == saved and after[:-1] == before[:-1]
    view = json.loads(after[-1]["content"])
    guidance = view["state"]["completion_guidance"]
    assert guidance["message"] == prefix["after"] + suffix
    assert guidance["next_action"] is None
    assert guidance["submission_ready"] is True and guidance["stage"] == "ready_to_submit"
    original = json.loads(before[-1]["content"])["state"]["completion_guidance"]
    for key in ("message", "next_action"):
        guidance[key] = original[key]
    after[-1]["content"] = canonical_json(view)
    assert after == before


@pytest.mark.parametrize(
    "stage", ["needs_mutation", "needs_visible_checks", "needs_source_evidence", "blocked"]
)
def test_non_ready_advice_is_completely_unchanged(stage):
    before = items("Non-ready next action remains unchanged.", stage)
    assert checkpoint.remove_finish_advice(before) == before


def test_unknown_form_cannot_silently_leave_or_rewrite_recommendation():
    with pytest.raises(ContractError, match="unknown ready message"):
        checkpoint.remove_finish_advice(items("Some new finish recommendation"))


def test_double_application_is_rejected_instead_of_masking_pipeline_drift():
    first = checkpoint.remove_finish_advice(items(checkpoint.MESSAGE_PREFIXES[0]["before"]))
    with pytest.raises(ContractError, match="unknown ready next action"):
        checkpoint.remove_finish_advice(first)
