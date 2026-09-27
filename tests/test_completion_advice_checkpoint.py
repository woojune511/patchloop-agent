"""The ablation must preserve eligibility, public evidence and available actions."""
import copy
import json
from types import SimpleNamespace

import pytest

from diagnostics import completion_advice_checkpoint as advice
from patchloop.dev.runner import _completion_guidance
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
        "completion_guidance": {"stage": "unknown"}}})}]}
    with pytest.raises(ContractError, match="unsupported completion stage"):
        advice.project(request)


@pytest.mark.parametrize("tools,gate,ready,status", [
    (["replace_text"], "needs_mutation", False, "FAIL"),
    (["read_file"], "needs_mutation", False, "FAIL"),
    (["search_files"], "needs_mutation", False, "FAIL"),
    (["finish_task"], "ready_to_submit", True, "PASS"),
    ([], "needs_visible_checks", False, "NOT_RUN"),
])
def test_all_runtime_guidance_shapes(tools, gate, ready, status):
    snapshot = SimpleNamespace(ready_to_submit=ready,
        visible_check_status=[{"status": status}], diff=SimpleNamespace(patch_hash="same"))
    policy = SimpleNamespace(allowed_tools=tools, workflow_gate=gate, check_ids=[])
    guidance = _completion_guidance(snapshot, policy)
    request = {"tools": [{"name": t} for t in tools], "input": [
        {"content": canonical_json({"state": {"completion_guidance": guidance}})}]}
    selected = advice.project(request)
    after = json.loads(selected["input"][-1]["content"])["state"]["completion_guidance"]
    assert after["next_action"] is None
    for key in ("stage", "submission_ready", "diff_hash"):
        assert after[key] == guidance[key]
    assert selected["tools"] == request["tools"]
