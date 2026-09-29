import copy
import json

import pytest

from diagnostics import decision_sampler as shared
from diagnostics import pre_edit_issue_focus_sampler as s
from patchloop.errors import ContractError


def test_issue_only_projection_preserves_native_items(monkeypatch):
    issue = {"title": "example", "description": "Keep unrelated behavior unchanged."}
    monkeypatch.setattr(s, "reconstruct_state", lambda *a, **k: {
        "public_task": {"issue": issue}})
    original = {"input": [{"role": "system", "content": "original"},
                          {"type": "reasoning", "encrypted_content": "opaque-fixture"}],
                "tools": [{"name": "replace_text"}], "max_output_tokens": 12000}
    before = copy.deepcopy(original)
    requests = s.project(original)
    assert original == before
    assert requests["A"] == {**original, "max_output_tokens": 25000}
    assert requests["B"]["input"][:-1] == requests["A"]["input"]
    assert json.loads(requests["B"]["input"][-1]["content"])["issue"] == issue
    assert {k: v for k, v in requests["A"].items() if k != "input"} == {
        k: v for k, v in requests["B"].items() if k != "input"}
    original["tools"] = [{"name": "finish_task"}]
    with pytest.raises(ContractError, match="mutation unavailable"):
        s.project(original)


def test_frozen_scope_and_reservation():
    assert s.CALLS == {"P": 5, "H": 9, "F": 2}
    assert len(s.SCHEDULE) == 12
    for i in range(0, 12, 2):
        a, b = s.SCHEDULE[i:i+2]
        assert a[0] == b[0] and a[2] == b[2] and {a[1], b[1]} == {"A", "B"}
    pricing = shared.cell_profile(s.protocol(), "A").pricing()
    assert shared.full_reservation(60000, pricing) * 12 <= 8e9
