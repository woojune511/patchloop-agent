"""The generic review adds one field without changing the agent's evidence or tools."""

import copy
import json

import pytest

from diagnostics import expectation_review_checkpoint as review
from patchloop.errors import ContractError
from patchloop.util import canonical_json


def test_exact_one_field_and_no_task_answer():
    request = {
        "model": "frozen",
        "tools": [{"name": "replace_text"}, {"name": "run_probe"}],
        "input": [
            {"role": "system", "content": "unchanged"},
            {
                "role": "developer",
                "content": canonical_json(
                    {
                        "kind": "harness_current_state",
                        "state": {
                            "working_notes": {"open_question": "disputed expectation"},
                            "completion_guidance": {"next_action": None},
                            "remaining_budget": {"cost": {"remaining": 42}},
                        },
                    }
                ),
            },
        ],
    }
    before = copy.deepcopy(request)
    selected = review.project(request)
    assert request == before
    view = json.loads(selected["input"][-1]["content"])
    assert view["state"].pop(review.FIELD) == review.CUE
    selected["input"][-1]["content"] = canonical_json(view)
    assert selected == request
    for forbidden in ("toqito", "uparrow", "downarrow", "0.562", "0.569", "Petz"):
        assert forbidden not in review.CUE
    with pytest.raises(ContractError, match="already present"):
        review.project(review.project(request))


def test_reject_noncurrent_message():
    with pytest.raises(ContractError, match="current state"):
        review.project({"input": [{"content": canonical_json({"kind": "other"})}]})
