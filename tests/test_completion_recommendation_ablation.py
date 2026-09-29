import copy
import json
from decimal import Decimal

import pytest

from diagnostics import completion_recommendation_ablation as s
from diagnostics import decision_sampler as shared
from patchloop.errors import ContractError
from patchloop.util import canonical_json


def request():
    state = {
        "completion_guidance": {"stage": "needs_visible_checks", "message": s.ORIGINAL_MESSAGE,
                                "next_action": {"tool": "run_check",
                                                "check_id": "upstream-xet-regression"}},
        "remaining_visible_check_ids": ["upstream-xet-regression"],
        "operator_public_feedback": {"currency": "current_candidate", "stdout": "counterexample"},
        "remaining_budget": {"model_calls": 39},
    }
    return {"input": [{"role": "system", "content": "system"},
                      {"role": "developer", "content": canonical_json({"public_task": {}})},
                      {"role": "user", "content": "task"},
                      {"type": "reasoning", "encrypted_content": "opaque"},
                      {"role": "developer", "content": canonical_json({
                          "kind": "harness_current_state", "state": state})}],
            "tools": [{"name": "run_probe"}], "max_output_tokens": 25000}


def test_only_latest_recommendation_changes_and_history_is_identical():
    original = request()
    before = copy.deepcopy(original)
    pair = s.project(original)
    assert pair["A"] == original == before
    assert pair["B"]["input"][:-1] == original["input"][:-1]
    assert pair["B"]["tools"] == original["tools"]
    after = copy.deepcopy(pair["B"])
    view = json.loads(after["input"][-1]["content"])
    view["state"]["completion_guidance"]["message"] = s.ORIGINAL_MESSAGE
    view["state"]["completion_guidance"]["next_action"] = {
        "tool": "run_check", "check_id": "upstream-xet-regression"}
    after["input"][-1]["content"] = canonical_json(view)
    assert after == original


@pytest.mark.parametrize("field,value", [
    ("message", "changed guidance"), ("stage", "ready_to_submit")])
def test_wrong_checkpoint_rejected(field, value):
    original = request()
    view = json.loads(original["input"][-1]["content"])
    view["state"]["completion_guidance"][field] = value
    original["input"][-1]["content"] = canonical_json(view)
    with pytest.raises(ContractError, match="wrong post-contract"):
        s.project(original)


def test_schedule_and_cap_cover_full_ceiling():
    assert [a for _, a, _ in s.SCHEDULE] == list("ABBAAB")
    price = shared.cell_profile(s.protocol(), "A").pricing()
    assert shared.full_reservation(60000, pricing=price) * 6 == int(Decimal("3.15") * 10**9)
    assert shared.ACTIVE_SECONDS == 1800
