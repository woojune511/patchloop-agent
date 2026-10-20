from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from diagnostics import caller_evidence_grading as grading
from diagnostics.caller_uptake import file_ref
from patchloop.errors import ContractError
from patchloop.util import canonical_json

ORDER = [f"{a}{n}" for n in range(1, 7) for a in ("AB" if n % 2 else "BA")]


@pytest.fixture
def annotation(tmp_path):
    events = [
        {"sequence": 1, "event_hash": "action", "event_type": "action_finished", "payload": {
            "result": {"tool": "run_probe", "output": "caller failure"}}},
        {"sequence": 2, "event_hash": "request", "event_type": "provider_call_started",
         "payload": {"turn_id": "turn", "wire": {"input": [{"content": canonical_json({
             "state": {"operator_caller_observation": "caller failure"}})}]}}},
        {"sequence": 3, "event_hash": "decision", "event_type": "turn_decision_recorded",
         "payload": {"turn_id": "turn", "tool_calls": [{"name": "read_file"}]}},
        {"sequence": 4, "event_hash": "after", "event_type": "provider_call_started",
         "payload": {"turn_id": "later", "wire": {"input": []}}}]
    path = tmp_path / "B1.json"
    path.write_text(canonical_json({"row_id": "B1", "events": events}), encoding="utf-8")
    audit = file_ref(path)
    def ref(n):
        return {**audit, "sequence": n, "event_hash": events[n - 1]["event_hash"]}
    supplied = {**ref(2), "keys": ["payload", "wire", "input", 0, "content", "state",
                                   "operator_caller_observation"], "quote": "caller failure"}
    row = {"row_id": "B1", "audit": audit, "G": "NOT_ACQUIRED", "D": "COMPLETE",
           "J": "SUPPORTED", "action_use": "SUPPORTED", "acquisition_origin": "none",
           "reviewer": "fixture", "rationale": "scope checked", "alternatives": "budget",
           "first_decision": ref(3), "acquisition": [], "inventory": [], "evidence": [{
               "material": supplied, "request": ref(2), "decision": ref(3),
               "origin": "operator_supplied", "currency": "current", "material_diff": "base",
               "decision_diff": "base", "scope_rationale": "same input and caller"}]}
    return row, {audit["path"]: audit["hash"]}, ref


def test_supplied_use_does_not_become_autonomous_acquisition(annotation):
    row, allowed, _ = annotation
    result = grading.validate_annotation(row, allowed)
    assert result["G"] == "NOT_ACQUIRED" and result["J"] == "SUPPORTED"
    row.update(G="ACQUIRED_EXECUTION", acquisition_origin="prompted_verification")
    with pytest.raises(ContractError, match="autonomous acquisition"):
        grading.validate_annotation(row, allowed)


@pytest.mark.parametrize("field,value", [
    ("D", "NOT_ACQUIRED_OR_SUPPLIED"), ("D", "PARTIAL_OR_TRUNCATED"),
    ("first_decision", None), ("J", "NO_DECISION_OPPORTUNITY"), ("evidence", []),
])
def test_evidence_present_claim_requires_delivery_and_opportunity(annotation, field, value):
    row, allowed, _ = annotation
    row[field] = value
    with pytest.raises(ContractError):
        grading.validate_annotation(row, allowed)


def test_stale_failure_cannot_be_current_counterevidence(annotation):
    row, allowed, _ = annotation
    row["J"] = "OVERCLAIM"
    row["evidence"][0]["decision_diff"] = "edited"
    with pytest.raises(ContractError, match="stale"):
        grading.validate_annotation(row, allowed)
    row["J"] = "SUPPORTED"
    row["evidence"][0]["currency"] = "historical_acknowledged"
    assert grading.validate_annotation(row, allowed)["J"] == "SUPPORTED"


@pytest.mark.parametrize("change", ["wrong_row", "wrong_event", "wrong_quote", "wrong_turn"])
def test_annotations_bind_actual_public_events(annotation, change):
    row, allowed, _ = annotation
    if change == "wrong_row":
        row["row_id"] = "A1"
    elif change == "wrong_event":
        row["evidence"][0]["material"]["sequence"] = 999
    elif change == "wrong_quote":
        row["evidence"][0]["material"]["quote"] = "never delivered"
    else:
        row["evidence"][0]["request"]["sequence"] = 4
        row["evidence"][0]["request"]["event_hash"] = "after"
    with pytest.raises(ContractError):
        grading.validate_annotation(row, allowed)


def test_lost_material_needs_before_and_after_inputs(annotation):
    row, allowed, ref = annotation
    item = {"status": "LOST_AT_HANDOFF", "rationale": "all routes reviewed",
            "material": row["evidence"][0]["material"], "before": ref(2), "after": ref(4),
            "all_routes_reviewed": True}
    row["inventory"] = [item]
    grading.validate_annotation(row, allowed)
    item["after"] = ref(2)
    with pytest.raises(ContractError, match="retention loss"):
        grading.validate_annotation(row, allowed)


def test_later_uptake_cannot_relabel_the_first_judgment(annotation):
    row, _, _ = annotation
    path = Path(row["audit"]["path"])
    audit = json.loads(path.read_bytes())
    audit["events"][3]["payload"]["wire"] = audit["events"][1]["payload"]["wire"]
    audit["events"].append({"sequence": 5, "event_hash": "later-decision",
        "event_type": "turn_decision_recorded", "payload": {
            "turn_id": "later", "tool_calls": [{"name": "read_file"}]}})
    path.write_text(canonical_json(audit), encoding="utf-8")
    updated = file_ref(path)
    def rebind(value):
        if isinstance(value, dict):
            if "path" in value and "hash" in value:
                value.update(updated)
            for child in value.values():
                rebind(child)
        elif isinstance(value, list):
            for child in value:
                rebind(child)
    rebind(row)
    row["evidence"][0]["request"].update(sequence=4, event_hash="after")
    row["evidence"][0]["decision"].update(sequence=5, event_hash="later-decision")
    with pytest.raises(ContractError, match="borrow a later"):
        grading.validate_annotation(row, {updated["path"]: updated["hash"]})


def successful(label, *, judgment="SUPPORTED", acquired="NOT_ACQUIRED"):
    return {"row_id": label, "completed": True, "settled": True, "cleanup": True,
            "submitted": True, "submitted_diff": "full", "assessed_from_diff": "full",
            "native_diff": "full", "source_only_diff": "source", "caller_diff": "source",
            "registered": "PASS", "native": "PASS", "safety": "PASS",
            "missing": "PASS", "present": "PASS", "audit": {
                "G": acquired, "D": "COMPLETE", "J": judgment, "action_use": judgment}}


def test_judgment_gain_is_not_repair_gain_and_nonusers_are_not_dropped():
    rows = [successful(label) for label in ORDER]
    for row in rows:
        if row["row_id"].startswith("B"):
            row["native"] = row["registered"] = "FAIL"
    result = grading.aggregate(rows, ORDER)
    assert result["arms"]["B"]["J"] == {"SUPPORTED": 6}
    assert result["arms"]["B"]["Q"] == 0 and result["arms"]["A"]["Q"] == 6
    assert result["favorable_local_signal"] is False
    assert len(result["rows"]) == 12


def test_positive_local_signal_needs_supported_use_in_two_repairs_and_complete_grades():
    rows = [successful(label) for label in ORDER]
    for row in rows:
        if row["row_id"].startswith("A"):
            row["missing"] = "FAIL"
    assert grading.aggregate(rows, ORDER)["favorable_local_signal"]
    unknown = copy.deepcopy(rows)
    unknown[0]["native"] = "ERROR"
    assert not grading.aggregate(unknown, ORDER)["favorable_local_signal"]
    no_use = copy.deepcopy(rows)
    for row in no_use:
        row["audit"]["J"] = "UNKNOWN"
    assert not grading.aggregate(no_use, ORDER)["favorable_local_signal"]


def test_full_submission_and_source_projection_are_distinct():
    row = successful("B1")
    assert grading.aggregate([row], ORDER)["arms"]["B"]["Q"] == 1
    row["native_diff"] = row["source_only_diff"]
    with pytest.raises(ContractError, match="lineage"):
        grading.aggregate([row], ORDER)
    empty = grading.aggregate([], ORDER)
    assert empty["arms"]["A"]["intended"] == 6 and not empty["complete"]
