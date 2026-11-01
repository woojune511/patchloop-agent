from __future__ import annotations

import copy
import json

import pytest

from diagnostics import segmented_input_audit as audit
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import completion_context, repair_context, runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import history_metadata, reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import canonical_json


@pytest.fixture(scope="module", params=["current", "thin"])
def recorded(tmp_path_factory, request):
    root = tmp_path_factory.mktemp("projected-audit")
    result = runner.run_dev(DevRunRequest(
        provider="mock", model="mock", state_root=root,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        context_policy="segmented-v1", repair_recheck=True,
        planning_policy="none" if request.param == "thin" else "brief-v1",
        agent_policy=request.param))
    assert result["runs"][0]["terminal"] == "EVALUATOR_PASS"
    journal = DevJournal(root, result["runs"][0]["run_id"])
    return journal.events(), ArtifactStore(root / "artifacts")


def test_actual_mock_inputs_verify_handoffs_and_receipt_references(recorded):
    events, store = recorded
    turns = [e for e in events if e["event_type"] == "turn_started"]
    receipts = [audit.verify_turn(e, events, store) for e in turns]
    assert len(receipts) == 4 and all(r["verified"] for r in receipts)
    if turns[0]["payload"]["context_segment"]["binding"].get("agent_policy") == "thin":
        assert all(r["plan_matches_before_projection"] for r in receipts)
    else:
        assert any(not r["plan_matches_before_projection"] for r in receipts)
    states = [reconstruct_state(runner._load_active_model_input(
        e["payload"], store, context_policy="segmented-v1"), context_policy="segmented-v1")
        for e in turns]
    assert any(repair_context.pending(state) for state in states)
    assert any(completion_context.active(state) for state in states)


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
        if field in view["state"]:
            view["state"].pop(field)
        else:
            view["state"][field] = {"injected": True}
        changed[-1]["content"] = json.dumps(view)
    monkeypatch.setattr(runner, "_load_active_model_input", lambda *a, **kw: changed)
    with pytest.raises(ValueError, match="projected public state differs"):
        audit.verify_turn(event, events, store)


def test_actual_wire_mismatch_is_not_normalized(recorded):
    events, store = recorded
    event = next(e for e in events if e["event_type"] == "turn_started")
    with pytest.raises(ValueError, match="actual input differs"):
        audit.verify_turn(event, events, store, actual_input=[])


@pytest.mark.parametrize("damage", ["input_hash", "native_seed", "handoff_state"])
def test_audit_preserves_native_and_segment_binding_validation(recorded, damage):
    events, store = recorded
    event = copy.deepcopy(next(e for e in events if e["event_type"] == "turn_started"))
    turn = event["payload"]
    if damage == "input_hash":
        turn["model_input_hash"] = "sha256:" + "0" * 64
    elif damage == "native_seed":
        turn["native_history"]["seed_hash"] = "sha256:" + "0" * 64
    else:
        turn["context_segment"]["binding"]["state_hash"] = "sha256:" + "0" * 64
    with pytest.raises(runner._ProviderContinuationError, match="unavailable or invalid"):
        audit.verify_turn(event, events, store)


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


def test_diagnosis_input_is_verified_without_inventing_check_table(recorded, tmp_path):
    events, source_store = recorded
    first = next(e for e in events if e["event_type"] == "turn_started")["payload"]
    state = json.loads(source_store.read_bytes(Artifact.model_validate(first["context_artifact"])))
    state.update(workflow_gate="needs_path_diagnosis",
                 available_tool_names=["read_file", "stop_task"],
                 diagnosis_stage={"policy": "focus-only-diagnosis-v1", "observations": []})
    agent_policy = first["context_segment"]["binding"].get("agent_policy", "current")
    journal = DevJournal(tmp_path, "run_dev_diagnosisaudit")
    store = ArtifactStore(tmp_path / "artifacts")
    context = store.put_text(canonical_json(state), "application/json")
    with journal.execution_lock():
        items = runner._build_model_input(
            journal=journal, artifact_store=store, context=canonical_json(state),
            latest_tool_results=[], context_policy="segmented-v1",
            planning_policy="none" if agent_policy == "thin" else "brief-v1",
            agent_policy=agent_policy,
        )
        saved = store.put_text(canonical_json(items), "application/json")
        journal.append("turn_started", {
            "turn_id": "diagnosis", "context_artifact": context.model_dump(mode="json"),
            "model_input_artifact": saved.model_dump(mode="json"),
            "model_input_hash": saved.content_hash,
            "native_history": history_metadata(items, context_policy="segmented-v1"),
            "context_segment": runner._segment_input_binding(journal, store),
        })
    rows = journal.events()
    assert audit.verify_turn(rows[-1], rows, store, actual_input=items)["verified"]
    delivered = reconstruct_state(items, context_policy="segmented-v1")
    assert "visible_check_status" not in delivered
    assert delivered["segment_handoff"]["interpretation"] == "public original-call diagnosis only"


@pytest.mark.parametrize("damage", ["missing_findings", "inherited_finding", "null_plan"])
def test_fresh_signature_requires_explicit_empty_phase_state(recorded, damage):
    events, store = recorded
    first = next(e for e in events if e["event_type"] == "turn_started")["payload"]
    items = runner._load_active_model_input(first, store, context_policy="segmented-v1")
    view = json.loads(items[-1]["content"])
    state = view["state"]
    notes = state["working_notes"]
    if damage == "missing_findings":
        notes.pop("findings")
    elif damage == "inherited_finding":
        notes["findings"] = [{"statement": "old conclusion"}]
    else:
        state["working_plan"] = None
    items[-1]["content"] = canonical_json(view)
    with pytest.raises(ValueError, match="fresh solve"):
        audit.initial_signature({"input": items})
