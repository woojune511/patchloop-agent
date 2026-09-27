"""The ablation must preserve eligibility, public evidence and available actions."""
import copy
import json

import pytest

from diagnostics import completion_advice_checkpoint as advice
from patchloop.errors import ContractError
from patchloop.util import canonical_json


@pytest.mark.parametrize("ready", [False, True])
def test_only_recommendation_changes(ready):
    guidance = {
        "diff_hash": "same-patch", "submission_ready": ready,
        "stage": "ready_to_submit" if ready else "needs_visible_checks",
        "next_action": {"tool": "finish_task"} if ready else
        {"tool": "run_check", "check_id": "regression"},
        "message": advice.READY_FACT + advice.READY_ADVICE if ready else (
            "Run one remaining visible check for the current diff: regression. "
            "Use run_check; PASS on a different diff does not count toward completion. "
            "Submission becomes available when all required checks pass on this scoped patch."),
    }
    request = {"model": "unchanged", "tools": [{"name": "run_probe"}], "input": [
        {"role": "system", "content": "Retain system guidance"},
        {"role": "developer", "content": canonical_json({"state": {
            "completion_guidance": guidance, "working_notes": {"open_question": "new behavior?"},
            "remaining_budget": {"calls": 32}, "current_diff": {"patch": "unchanged"}}})}]}
    original = copy.deepcopy(request)
    selected = advice.project(request)
    assert request == original
    view = json.loads(selected["input"][-1]["content"])
    changed = view["state"]["completion_guidance"]
    assert changed["next_action"] is None
    assert changed["submission_ready"] is ready
    assert changed["message"] != guidance["message"]
    view["state"]["completion_guidance"] = guidance
    selected["input"][-1]["content"] = canonical_json(view)
    assert selected == original
    bad = copy.deepcopy(request)
    view["state"]["completion_guidance"]["message"] += " Changed upstream"
    bad["input"][-1]["content"] = canonical_json(view)
    with pytest.raises(ContractError, match="wording changed"):
        advice.project(bad)


def test_unsupported_stage_rejected():
    request = {"input": [{"content": canonical_json({"state": {
        "completion_guidance": {"stage": "needs_mutation"}}})}]}
    with pytest.raises(ContractError, match="only check and ready"):
        advice.project(request)
