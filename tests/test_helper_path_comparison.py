import copy
import json
from types import SimpleNamespace

import pytest

from diagnostics import helper_path_comparison as comparison
from patchloop.errors import ContractError
from patchloop.util import canonical_json


def request():
    return {"model": comparison.MODEL, "input": [{"role": "developer",
        "content": canonical_json({"kind": "harness_current_state", "state": {
            "remaining_budget": {"model_calls": 16}, "common": "keep"}})}]}


def test_only_permitted_observation_diff_and_no_mutation_of_baseline():
    original = request()
    saved = copy.deepcopy(original)
    a = comparison.attach(original, {comparison.FIELD: {"caller": "fixed"}})
    b = comparison.attach(a, {comparison.EXTRA: {"helper": "new"}})
    view = json.loads(b["input"][-1]["content"])
    del view["state"][comparison.EXTRA]
    b["input"][-1]["content"] = canonical_json(view)
    assert a == b and original == saved
    with pytest.raises(ContractError, match="collision"):
        comparison.attach(a, {comparison.FIELD: {"caller": "changed"}})


def test_supplement_is_canonical_and_first_dispatch_only(monkeypatch):
    events = [{"event_type": "historical"}, {"event_type": "observation_exposure_fork"}]
    branch = SimpleNamespace(inherited_events=1, journal=SimpleNamespace(events=lambda: events))
    monkeypatch.setattr(comparison.runner, "_build_context", lambda **_: '{"common":true}')
    monkeypatch.setattr(comparison.runner, "_build_model_input", lambda **_: request()["input"])
    additions = {comparison.FIELD: {"caller": "fixed"}, comparison.EXTRA: {"helper": "new"}}
    with comparison.first_observation(branch, additions):
        assert json.loads(comparison.runner._build_context())[comparison.EXTRA] == {"helper": "new"}
        assert comparison.EXTRA in json.loads(comparison.runner._build_model_input()[
            -1]["content"])["state"]
        events.append({"event_type": "provider_call_started"})
        assert comparison.EXTRA not in json.loads(comparison.runner._build_context())
        assert comparison.runner._build_model_input() == request()["input"]


def test_fixed_order_and_no_inherited_budget_refill():
    assert comparison.ORDER == ("A1", "B1", "B2", "A2", "A3", "B3")
    assert comparison.ROW_CAP * len(comparison.ORDER) == comparison.CAP
    from decimal import Decimal

    assert comparison.ROW_CAP + Decimal("0.37263270") == Decimal("0.88")
