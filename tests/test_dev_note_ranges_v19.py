from __future__ import annotations

import json

import pytest
from test_dev_context_v12 import note_call, observe, source_note
from test_dev_context_v12 import source_gateway as source_gateway
from test_dev_notes_v14 import restore

from patchloop.dev.contracts import DevToolResult
from patchloop.dev.working_notes import (
    SourceNoteEvidence,
    note_feedback,
    source_note_range_details,
)
from patchloop.util import sha256_bytes, sha256_json


def _span(start, end, *, path="src.py", content=None):
    return {
        "path": path, "start_line": start, "end_line": end, "file_hash": "observed-hash",
        "content": content if content is not None else "\n".join(
            f"PUBLIC_SOURCE_BODY_{line}" for line in range(start, end + 1)
        ),
    }


def test_pending_read_range_is_never_observed_and_does_not_block_the_read(source_gateway):
    gateway, _, _ = source_gateway
    observe(gateway, "src.py", 1, 1, action_id="first")
    call = note_call("next-read", source_note("A premature whole-range claim.", 1, 4))
    payload = gateway.record_working_notes_update([call], turn_id="next")
    finding = payload["receipt"]["findings"][0]
    assert finding["code"] == "unobserved_source_range"
    assert finding["reason"] == "never_observed"
    assert finding["range_details"]["requested_range"] == {
        "path": "src.py", "start_line": 1, "end_line": 4,
    }
    assert finding["range_details"]["current_observed_ranges"] == [
        {"start_line": 1, "end_line": 1},
    ]
    assert finding["range_details"]["missing_ranges"] == [
        {"start_line": 2, "end_line": 4},
    ]
    assert "Pending reads are not evidence" in finding["message"]
    assert payload["findings"] == []
    assert gateway.execute(call).status == "succeeded"
    assert gateway.working_notes()["last_update_result"] == payload["receipt"]


def test_stale_range_detail_is_durable_and_rejects_whole_finding_not_valid_action(source_gateway):
    gateway, sources, tracked = source_gateway
    observe(gateway, "src.py", 1, 4, action_id="prior-source")
    sources["src.py"] = b"first\nchanged\nthird\nfourth\n"
    observe(gateway, "src.py", 1, 2, action_id="current-source")
    update = source_note("This whole-range finding must not be partially admitted.", 1, 4)
    update["findings"].append(source_note("This shorter observation is current.", 1, 2)[
        "findings"
    ][0])
    call = note_call("read-after-stale-note", update)
    payload = gateway.record_working_notes_update([call], turn_id="stale-note")
    failed, accepted = payload["receipt"]["findings"]
    assert failed["code"] == "unobserved_source_range"
    assert failed["reason"] == "stale_current_range"
    assert failed["range_details"]["missing_ranges"] == [
        {"start_line": 3, "end_line": 4},
    ]
    assert "not bound as current source evidence" in failed["message"]
    assert "Historical coordinates" in failed["message"]
    assert accepted["status"] == "created"
    assert payload["findings"][0]["statement"] == "This shorter observation is current."
    assert len(payload["findings"]) == 1
    assert payload["receipt"]["status"] == "partially_applied"
    assert payload["diagnostics"] == ["unobserved_public_evidence"]
    before = gateway.journal.path.read_bytes()
    restarted = restore(gateway, tracked)
    assert restarted.record_working_notes_update([call], turn_id="stale-note") == payload
    assert gateway.journal.path.read_bytes() == before
    assert gateway.execute(call).status == "succeeded"
    assert gateway.working_notes()["last_update_result"] == payload["receipt"]


@pytest.mark.parametrize("field", ["mutation_evidence", "revalidated_spans"])
def test_prior_successful_mutation_observations_are_historical_evidence(source_gateway, field):
    gateway, sources, _ = source_gateway
    span = _span(1, 4, content=sources["src.py"].decode().rstrip("\n"))
    span["file_hash"] = sha256_bytes(sources["src.py"])
    result = DevToolResult(
        action_id="prior-mutation", input_hash=sha256_json(field),
        tool="replace_text", status="succeeded",
        output={field: [span] if field == "revalidated_spans" else span},
    )
    gateway.journal.append("action_finished", {"result": result.model_dump(mode="json")})
    sources["src.py"] = b"first\nchanged\nthird\nfourth\n"
    observe(gateway, "src.py", 1, 2, action_id="current")
    payload = gateway.record_working_notes_update(
        [note_call("note", source_note("Prior source lacks a current binding.", 1, 4))],
        turn_id="note",
    )
    assert payload["receipt"]["findings"][0]["reason"] == "stale_current_range"


@pytest.mark.parametrize("invalid_kind", ["pending", "failed", "check", "malformed_span"])
def test_unobserved_payloads_do_not_create_historical_coverage(source_gateway, invalid_kind):
    gateway, _, _ = source_gateway
    span = _span(1, 4)
    if invalid_kind == "pending":
        gateway.journal.append("action_started", {"mutation_evidence": span})
    else:
        if invalid_kind == "malformed_span":
            span["content"] = "Only one line was returned"
        result = DevToolResult(
            action_id="not-source-evidence", input_hash=sha256_json(invalid_kind),
            tool="run_check" if invalid_kind == "check" else "replace_text",
            status="failed" if invalid_kind == "failed" else "succeeded",
            output={"mutation_evidence": span, "spans": [span]},
        )
        gateway.journal.append("action_finished", {"result": result.model_dump(mode="json")})
    observe(gateway, "src.py", 1, 1, action_id="current")
    payload = gateway.record_working_notes_update(
        [note_call("note", source_note("No completed source supports this range.", 1, 4))],
        turn_id="note",
    )
    assert payload["receipt"]["findings"][0]["reason"] == "never_observed"


def test_range_details_are_bounded_and_nearby_current_ranges_come_first():
    current = [_span(line, line) for line in range(1, 60, 2)]
    historical = [_span(1, 100)]
    evidence = SourceNoteEvidence(kind="source", path="src.py", start_line=45, end_line=100)
    diagnostic = source_note_range_details(evidence, current, historical)
    detail = diagnostic["range_details"]
    assert diagnostic["reason"] == "stale_current_range"
    assert detail["range_limit"] == 8
    assert len(detail["current_observed_ranges"]) == 8
    assert detail["current_observed_ranges"][0] == {"start_line": 45, "end_line": 45}
    assert len(detail["missing_ranges"]) == 8
    assert detail["current_observed_range_count"] == 30
    assert detail["missing_range_count"] == 8
    assert detail["ranges_truncated"] == {
        "current_observed_ranges": True, "missing_ranges": False,
    }
    assert "PUBLIC_SOURCE_BODY" not in json.dumps(diagnostic)


def test_many_missing_subranges_preserve_total_count_without_unbounded_output():
    evidence = SourceNoteEvidence(kind="source", path="src.py", start_line=1, end_line=10**9)
    current = [_span(line, line) for line in range(1, 60, 2)]
    diagnostic = source_note_range_details(evidence, current, [])
    detail = diagnostic["range_details"]
    assert diagnostic["reason"] == "never_observed"
    assert detail["missing_range_count"] == 30
    assert len(detail["missing_ranges"]) == 8
    assert detail["ranges_truncated"]["missing_ranges"] is True
    assert len(json.dumps(diagnostic)) < 2_000


def test_partial_history_does_not_label_an_entire_unseen_gap_as_stale():
    evidence = SourceNoteEvidence(kind="source", path="src.py", start_line=1, end_line=8)
    diagnostic = source_note_range_details(evidence, [_span(1, 2)], [_span(1, 5)])
    assert diagnostic["reason"] == "never_observed"
    assert diagnostic["range_details"]["missing_ranges"] == [{"start_line": 3, "end_line": 8}]


def test_unknown_paths_and_source_bodies_are_not_echoed():
    path = ".patchloop-hidden/PRIVATE_REFERENCE_SENTINEL.py"
    evidence = SourceNoteEvidence(kind="source", path=path, start_line=1, end_line=3)
    diagnostic = source_note_range_details(evidence, [_span(1, 3)], [_span(1, 3)])
    assert diagnostic["range_details"]["requested_range"]["path"] is None
    assert path not in json.dumps(diagnostic)
    assert "PUBLIC_SOURCE_BODY" not in json.dumps(diagnostic)
    assert diagnostic["reason"] == "never_observed"


def test_reversed_range_remains_invalid_and_non_admitting():
    evidence = SourceNoteEvidence(kind="source", path="src.py", start_line=3, end_line=1)
    diagnostic = source_note_range_details(evidence, [_span(1, 4)], [_span(1, 4)])
    assert diagnostic["reason"] == "never_observed"
    assert diagnostic["range_details"]["requested_range_valid"] is False
    assert diagnostic["range_details"]["missing_ranges"] == []
    assert note_feedback("unobserved_source_range")["code"] == "unobserved_source_range"
