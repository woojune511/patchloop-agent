from __future__ import annotations

import copy
import json

import pytest

from diagnostics import segmented_input_audit as audit
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root


@pytest.fixture(scope="module")
def recorded(tmp_path_factory):
    root = tmp_path_factory.mktemp("projected-audit")
    result = runner.run_dev(DevRunRequest(
        provider="mock", model="mock", state_root=root,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        context_policy="segmented-v1", planning_policy="brief-v1", repair_recheck=True))
    assert result["runs"][0]["terminal"] == "EVALUATOR_PASS"
    journal = DevJournal(root, result["runs"][0]["run_id"])
    return journal.events(), ArtifactStore(root / "artifacts")


def test_actual_mock_inputs_verify_handoffs_and_receipt_references(recorded):
    events, store = recorded
    turns = [e for e in events if e["event_type"] == "turn_started"]
    receipts = [audit.verify_turn(e, events, store) for e in turns]
    assert len(receipts) == 4 and all(r["verified"] for r in receipts)
    assert any(not r["plan_matches_before_projection"] for r in receipts)


@pytest.mark.parametrize("field", ["public_task", "current_diff", "visible_check_status",
                                   "working_plan", "working_notes", "segment_handoff"])
def test_projected_audit_rejects_changed_delivered_state(recorded, monkeypatch, field):
    events, store = recorded
    event = [e for e in events if e["event_type"] == "turn_started"][-1]
    items = runner._load_active_model_input(event["payload"], store,
                                            context_policy="segmented-v1")
    changed = copy.deepcopy(items)
    if field == "public_task":
        initial = json.loads(changed[1]["content"])
        initial["public_task"]["issue"]["title"] = "changed requirement"
        changed[1]["content"] = json.dumps(initial)
    else:
        view = json.loads(changed[-1]["content"])
        view["state"].pop(field)
        changed[-1]["content"] = json.dumps(view)
    monkeypatch.setattr(runner, "_load_active_model_input", lambda *a, **kw: changed)
    with pytest.raises(ValueError, match="projected public state differs"):
        audit.verify_turn(event, events, store)


def test_actual_wire_mismatch_is_not_normalized(recorded):
    events, store = recorded
    event = next(e for e in events if e["event_type"] == "turn_started")
    with pytest.raises(ValueError, match="actual input differs"):
        audit.verify_turn(event, events, store, actual_input=[])


def test_initial_pair_excludes_clock_and_derived_segment_id_only(recorded):
    events, store = recorded
    event = next(e for e in events if e["event_type"] == "turn_started")
    items = runner._load_active_model_input(event["payload"], store,
                                            context_policy="segmented-v1")
    a = {"model": "mini", "input": items, "tools": [], "max_output_tokens": 25_000}
    b = copy.deepcopy(a)
    b["model"] = "full"
    view = json.loads(b["input"][-1]["content"])
    view["state"]["remaining_budget"]["active_wall_time_seconds"] -= 10
    view["state"]["segment_handoff"]["segment_id"] = "different-derived-hash"
    b["input"][-1]["content"] = json.dumps(view)
    assert audit.initial_signature(a) == audit.initial_signature(b)
    view["state"]["remaining_budget"]["accepted_mutations"] -= 1
    b["input"][-1]["content"] = json.dumps(view)
    assert audit.initial_signature(a) != audit.initial_signature(b)
    view["state"]["current_diff"]["patch"] = "inherited patch"
    b["input"][-1]["content"] = json.dumps(view)
    with pytest.raises(ValueError, match="previous candidate"):
        audit.initial_signature(b)
