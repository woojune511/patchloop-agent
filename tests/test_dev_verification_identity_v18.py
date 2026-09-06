from __future__ import annotations

import copy
import json

import pytest

from patchloop.dev.verification_concerns import (
    empty_verification_state,
    project_verification_concerns,
    update_verification_concerns,
    verification_updates_schema,
)

ORIGINAL = "Does the candidate preserve publicly documented branch behavior?"
PROGRESS = "One public branch passed; the other still needs verification."


def update(operation="upsert", concern_id=None, *, statement=ORIGINAL, reason=None, evidence=None):
    return {
        "operation": operation, "concern_id": concern_id, "statement": statement,
        "evidence_action_id": evidence, "reason": reason,
    }


def apply(state, updates, *, turn="t1", diff="candidate", prior=None):
    return update_verification_concerns(
        state, updates, diff_hash=diff, turn_id=turn, prior_results=prior or {},
    )


def created():
    return apply(empty_verification_state(), [update()])[0]


def decided(state, operation):
    return apply(state, [update(
        operation, "v1", statement=None, reason="The public result addresses this concern.",
        evidence="check" if operation == "resolve" else None,
    )], turn="decision", prior={"check": {
        "action_id": "check", "input_hash": "sha256:input", "tool": "run_check",
        "status": "succeeded", "workspace_diff_hash": "candidate",
        "output": {"diff_hash": "candidate", "passed": True},
    }})[0]


def test_progress_retains_original_and_distinct_concerns_need_new_ids():
    initial = created()
    state, receipt = apply(initial, [
        update(concern_id="v1", statement=PROGRESS),
        update(statement="Is a different public behavior preserved?"),
    ], turn="t2")
    assert initial["items"][0]["progress_note"] is None
    assert state["items"][0]["statement"] == ORIGINAL
    assert state["items"][0]["progress_note"] == PROGRESS
    assert state["items"][0]["created_turn_id"] == "t1"
    assert state["items"][0]["updated_turn_id"] == "t2"
    assert state["items"][1]["concern_id"] == "v2"
    assert state["items"][1]["progress_note"] is None
    assert receipt["available_concern_ids"] == ["v1", "v2"]


@pytest.mark.parametrize("statement", [ORIGINAL, PROGRESS])
@pytest.mark.parametrize("operation", [None, "resolve", "dismiss"])
def test_repeated_original_or_progress_is_an_exact_noop_even_after_decision(statement, operation):
    state, _ = apply(created(), [update(concern_id="v1", statement=PROGRESS)], turn="progress")
    if operation:
        state = decided(state, operation)
    snapshot = copy.deepcopy(state)
    unchanged, receipt = apply(state, [update(concern_id="v1", statement=statement)], turn="later")
    assert state == snapshot
    assert unchanged == snapshot
    assert receipt["status"] == "applied"
    assert receipt["updates"][0]["status"] == "applied"
    assert receipt["updates"][0]["code"] == "unchanged"
    assert "Use []" in receipt["updates"][0]["message"]


@pytest.mark.parametrize("operation", ["resolve", "dismiss"])
def test_new_progress_reopens_decision_without_replacing_original(operation):
    state = decided(created(), operation)
    updated, receipt = apply(state, [update(concern_id="v1", statement=PROGRESS)], turn="new")
    assert receipt["updates"][0]["code"] is None
    assert updated["items"][0]["statement"] == ORIGINAL
    assert updated["items"][0]["progress_note"] == PROGRESS
    assert updated["items"][0]["decision"] is None
    assert updated["items"][0]["updated_turn_id"] == "new"
    assert receipt["unresolved_ids"] == ["v1"]


def test_latest_progress_is_bounded_and_replaces_only_progress():
    state = created()
    for index in range(5):
        state, _ = apply(state, [update(concern_id="v1", statement=f"Progress {index}")])
    assert state["items"][0]["statement"] == ORIGINAL
    assert state["items"][0]["progress_note"] == "Progress 4"
    snapshot = copy.deepcopy(state)
    invalid, receipt = apply(state, [update(concern_id="v1", statement="x" * 401)])
    assert invalid == snapshot
    assert receipt["updates"][0]["code"] == "invalid_verification_update"
    assert "Progress 0" not in json.dumps(state)


@pytest.mark.parametrize("operation", ["resolve", "dismiss"])
def test_noop_on_later_diff_keeps_historical_decision_and_reopens_by_currency(operation):
    state, _ = apply(created(), [update(concern_id="v1", statement=PROGRESS)], turn="progress")
    state = decided(state, operation)
    updated, receipt = apply(state, [update(concern_id="v1", statement=PROGRESS)], diff="later")
    assert updated == state
    assert receipt["updates"][0]["code"] == "unchanged"
    assert receipt["unresolved_ids"] == ["v1"]
    projected = project_verification_concerns(updated, diff_hash="later")
    item = projected["items"][0]
    assert item["statement"] == ORIGINAL
    assert item["progress_note"] == PROGRESS
    assert item["status"] == "unresolved"
    assert item["decision"]["currency"] == "historical"


def test_journal_snapshot_roundtrip_preserves_original_progress_noop_and_allocator():
    updates = [
        update(concern_id="v1", statement=PROGRESS),
        update(concern_id="v1", statement=PROGRESS),
        update(statement="Another public concern."),
    ]
    state = decided(created(), "resolve")
    restored = json.loads(json.dumps(state))
    expected = apply(state, updates, turn="resumed", diff="new-diff")
    actual = apply(restored, updates, turn="resumed", diff="new-diff")
    assert actual == expected
    projected = project_verification_concerns(actual[0], diff_hash="new-diff")
    assert projected["items"][0]["statement"] == ORIGINAL
    assert projected["items"][0]["progress_note"] == PROGRESS
    assert actual[1]["updates"][1]["code"] == "unchanged"
    assert actual[0]["next_id"] == 3


def test_capacity_preserves_original_questions_and_noop_does_not_occupy_new_slot():
    state, _ = apply(created(), [
        update(statement="Second public concern."), update(statement="Third public concern."),
    ])
    state, receipt = apply(state, [
        update(concern_id="v1", statement=ORIGINAL),
        update(concern_id="v1", statement=PROGRESS),
        update(statement="Fourth public concern."),
    ], turn="full")
    assert receipt["status"] == "partially_applied"
    assert [entry["code"] for entry in receipt["updates"]] == [
        "unchanged", None, "concern_capacity",
    ]
    assert [item["statement"] for item in state["items"]] == [
        ORIGINAL, "Second public concern.", "Third public concern.",
    ]
    assert state["next_id"] == 4


def test_noop_does_not_reopen_resolved_item_and_prevent_capacity_eviction():
    state, _ = apply(created(), [
        update(statement="Second public concern."), update(statement="Third public concern."),
    ])
    state = decided(state, "resolve")
    updated, receipt = apply(state, [
        update(concern_id="v1", statement=ORIGINAL),
        update(statement="Fourth public concern."),
    ])
    assert receipt["evicted_concern_ids"] == ["v1"]
    assert [item["concern_id"] for item in updated["items"]] == ["v2", "v3", "v4"]
    assert updated["next_id"] == 5


def test_schema_keeps_five_fields_in_order_and_explains_statement_semantics():
    schema = verification_updates_schema()
    properties = schema["items"]["properties"]
    assert list(properties) == [
        "operation", "concern_id", "statement", "evidence_action_id", "reason",
    ]
    assert schema["items"]["required"] == list(properties)
    assert "immutable original" in properties["statement"]["description"]
    assert "New concerns need null IDs" in schema["description"]
    assert "progress_note" not in properties
