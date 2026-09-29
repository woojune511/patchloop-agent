import copy
import json
from decimal import Decimal

import pytest

from diagnostics import decision_sampler as shared
from diagnostics import public_check_focus_sampler as s
from patchloop.errors import ContractError


def test_projection_only_repeats_available_checks(monkeypatch):
    checks = [{"id": "public", "command": ["python", "-c", "assert True"]}]
    state = {"public_task": {"visible_checks": checks},
             "visible_check_status": [{"status": "PASS"}]}
    monkeypatch.setattr(s, "reconstruct_state", lambda *a, **k: state)
    original = {"input": [{"role": "user", "content": "unchanged"}],
                "max_output_tokens": 18000, "tools": [{"name": "finish_task"}]}
    before = copy.deepcopy(original)
    r = s.project(original)
    assert original == before
    assert r["A"] == {**original, "max_output_tokens": 25000}
    assert r["B"]["input"][:-1] == r["A"]["input"]
    assert json.loads(r["B"]["input"][-1]["content"])["visible_checks"] == checks
    assert {k: v for k, v in r["B"].items() if k != "input"} == {
        k: v for k, v in r["A"].items() if k != "input"}
    state["visible_check_status"][0]["status"] = "FAIL"
    with pytest.raises(ContractError):
        s.project(original)


def test_balanced_order_and_total_reservation():
    assert len(s.SCHEDULE) == 12
    for i in range(0, 12, 2):
        a, b = s.SCHEDULE[i:i+2]
        assert a[0] == b[0] and a[2] == b[2] and {a[1], b[1]} == {"A", "B"}
    profile = shared.cell_profile(s.protocol(), "A")
    assert shared.full_reservation(60000, profile.pricing()) * 12 <= int(Decimal(8)*10**9)
