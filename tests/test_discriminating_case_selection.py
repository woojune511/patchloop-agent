import copy
from decimal import Decimal

import pytest

from diagnostics import decision_sampler as shared
from diagnostics import discriminating_case_selection as s
from patchloop.errors import ContractError


def test_projection_preserves_actual_input_and_changes_only_instruction(monkeypatch):
    monkeypatch.setattr(s, "reconstruct_state", lambda *a, **k: {
        "current_diff": {"patch": "public candidate"}})
    original = {"input": [{"role": "system", "content": "original"},
                          {"type": "reasoning", "encrypted_content": "opaque"}],
                "tools": [{"name": "run_probe"}], "max_output_tokens": 1000}
    before = copy.deepcopy(original)
    requests = s.project(original)
    assert original == before
    assert requests["A"]["input"][:-1] == original["input"]
    assert requests["B"]["input"][:-1] == requests["A"]["input"]
    assert requests["B"]["input"][-1]["content"] == s.TREATMENT
    assert requests["A"]["tools"] == requests["B"]["tools"] == original["tools"]
    original["tools"] = [{"name": "finish_task"}]
    with pytest.raises(ContractError, match="probe unavailable"):
        s.project(original)


def test_empty_candidate_rejected(monkeypatch):
    monkeypatch.setattr(s, "reconstruct_state", lambda *a, **k: {
        "current_diff": {"patch": ""}})
    with pytest.raises(ContractError, match="candidate patch"):
        s.project({"input": [], "tools": [{"name": "run_probe"}]})


def test_balanced_schedule_and_full_reservation():
    assert len(s.SCHEDULE) == 24
    for i in range(0, 24, 2):
        a, b = s.SCHEDULE[i:i + 2]
        assert a[0] == b[0] and a[2] == b[2] and {a[1], b[1]} == {"A", "B"}
    price = shared.cell_profile(s.protocol(), "A").pricing()
    assert shared.full_reservation(60000, pricing=price) * 24 == int(Decimal("12.60") * 10**9)
