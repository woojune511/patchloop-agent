"""Judgment provenance, negative controls and fixed-allocation execution guards."""
from __future__ import annotations

import copy
from datetime import UTC, datetime

import pytest

from diagnostics import verification_state_execution as execution
from diagnostics import verification_state_grading as grading
from diagnostics import verification_state_panel as panel
from patchloop.dev.conversation import assemble_model_input
from patchloop.errors import ContractError
from patchloop.util import sha256_json


def event(sequence, kind, payload):
    return {"sequence": sequence, "event_type": kind, "payload": payload,
            "event_hash": sha256_json({"sequence": sequence, "kind": kind, "payload": payload})}


def reviewed_row(label="CONTRADICTED"):
    observation = "Original caller still fails on current diff D1 with the public setup."
    claim = "The original issue is fixed."
    raw = {"action_id": "finish", "name": "finish_task", "arguments": {"assessment": claim}}
    state = {"public_task": {"issue": {"title": "Original issue"}},
             "current_diff": {"patch_hash": "D1"}, "observed": observation}
    wire = {"input": assemble_model_input(system_prompt="fixed", state=state, history=[],
                                          context_policy="segmented-v1")}
    events = [
        event(1, "action_finished", {"result": {
            "action_id": "probe", "input_hash": "probe-input", "tool": "run_probe",
            "workspace_diff_hash": "D1", "status": "succeeded", "output": {
                "stdout": observation, "exit_code": 0, "timed_out": False,
                "truncated": False, "deadline_exhausted": False, "cleanup_failed": False}}}),
        event(2, "provider_call_started", {"turn_id": "t1", "wire": wire,
                                           "actual_request_hash": sha256_json(wire)}),
        event(3, "turn_decision_recorded", {"turn_id": "t1", "tool_calls": [raw]}),
        event(4, "action_finished", {"result": {
            "action_id": "finish", "input_hash": grading.input_hash(raw),
            "tool": "finish_task", "status": "succeeded", "workspace_diff_hash": "D1"}}),
    ]
    public = {"public_id": "masked-1", "events": events}
    ref = {"sequence": 1, "event_hash": events[0]["event_hash"], "text": observation,
           "delivered": True}
    reason = {
        "CONTRADICTED": "current_original_path_refutation", "UNSUPPORTED": "helper_to_task",
        "SUPPORTED_DIRECT": "current_original_path_and_control",
        "SUPPORTED_INFERENCE": "current_source_mapping", "UNKNOWN": "ambiguous_mapping",
        "NO_CLAIM": "discussion_only",
    }[label]
    row = {
        "public_id": "masked-1", "public_hash": sha256_json(public), "reviewed_decisions": [3],
        "reviewer": "fixture", "rationale": "Explicit scope review.",
        "alternatives": "Fixture labels validate structure, not semantic accuracy.",
        "displacement_review": "No loss in this bounded fixture.",
        "fresh_grade_exposure": [], "started": True,
        **{axis: "NO_OBSERVED" for axis in grading.AXES},
        "evidence": {},
        "claims": [{
            "decision_sequence": 3, "action_id": "finish", "input_hash": grading.input_hash(raw),
            "request_sequence": 2, "request_hash": sha256_json(wire), "diff_hash": "D1",
            "text": claim, "receipt_hash": events[3]["event_hash"], "finish_admitted": True,
            "label": label, "is_completion_claim": label != "NO_CLAIM",
            "rationale": "Independent semantic reviewer checked original setup.",
            "scope_rationale": "Input, environment and outcome mapped to public issue.",
            "evidence": [ref], "reason_kind": reason, "semantic_review": True,
        }],
    }
    return row, public


def test_judgment_states_are_independent_of_runtime_unknown_and_actual_grade():
    for label in grading.LABELS:
        row, public = reviewed_row(label)
        result = grading.validate_annotation(row, public)
        assert result["bad_claim"] is (label in grading.BAD)
        assert result["unknown_claim"] is (label == "UNKNOWN")
        assert result["claiming"] is (label != "NO_CLAIM")
    row, public = reviewed_row()
    # A rejected finish can still contain a false completion assertion.
    public["events"][-1]["payload"]["result"]["status"] = "failed"
    row["public_hash"] = sha256_json(public)
    row["claims"][0]["finish_admitted"] = False
    assert grading.validate_annotation(row, public)["bad_claim"]


def test_annotation_rejects_wrong_diff_input_receipt_quotes_and_omissions():
    changes = [
        ("diff_hash", "wrong-patch"), ("input_hash", "wrong-action"),
        ("request_hash", "wrong-input"), ("receipt_hash", "wrong-receipt"),
        ("reason_kind", "derived_UNKNOWN"), ("semantic_review", False),
    ]
    for field, value in changes:
        row, public = reviewed_row()
        row["claims"][0][field] = value
        with pytest.raises(ContractError):
            grading.validate_annotation(row, public)
    for change in ("omit_finish", "omit_turn", "no_evidence", "not_delivered", "future", "private"):
        row, public = reviewed_row()
        if change == "omit_finish":
            row["claims"] = []
        elif change == "omit_turn":
            row["reviewed_decisions"] = []
        elif change == "no_evidence":
            row["claims"][0]["evidence"] = []
        elif change == "not_delivered":
            row["claims"][0]["evidence"][0]["delivered"] = False
        elif change == "future":
            row["claims"][0]["evidence"][0].update(
                sequence=4, event_hash=public["events"][-1]["event_hash"], text="finish")
        else:
            public["events"].append(event(5, "evaluation_finished", {"hidden": True}))
            row["public_hash"] = sha256_json(public)
        with pytest.raises(ContractError):
            grading.validate_annotation(row, public)


def test_mechanism_use_cannot_be_awarded_for_unbound_or_earlier_actions():
    row, public = reviewed_row("UNKNOWN")
    for axis in ("separation_exposure", "supported_application", "actionable_contrast",
                 "changed_mechanism_applied"):
        row[axis] = "YES"
        row["evidence"][axis] = row["claims"][0]["evidence"]
    with pytest.raises(ContractError, match="bound dispatched"):
        grading.validate_annotation(row, public)
    item, = grading.decisions(public)
    row["mechanism_application"] = {
        **{k: item[k] for k in ("decision_sequence", "action_id", "input_hash",
                                "request_sequence", "request_hash", "diff_hash")},
        "exposure_text": "Original caller", "use_text": "original issue",
        "rationale": "A structural validation fixture, not semantic proof of use.",
    }
    with pytest.raises(ContractError, match="separated state"):
        grading.validate_annotation(row, public)
    row["mechanism_application"]["request_sequence"] += 1
    with pytest.raises(ContractError, match="bound dispatched"):
        grading.validate_annotation(row, public)


def test_direct_judgment_rejects_stale_nonexecution_and_unhealthy_witnesses():
    for label in ("CONTRADICTED", "SUPPORTED_DIRECT"):
        row, public = reviewed_row(label)
        public["events"][0]["payload"]["result"]["output"]["exit_code"] = 1
        row["public_hash"] = sha256_json(public)
        assert grading.validate_annotation(row, public)["last_claim"] == label
        for variant in ("old_diff", "output_diff", "not_executed", "notes", "no_exit",
                        "timed_out", "truncated", "deadline_exhausted", "cleanup_failed",
                        "setup_failed", "incomplete_call"):
            row, public = reviewed_row(label)
            witness = public["events"][0]
            result = witness["payload"]["result"]
            output = result["output"]
            if variant == "old_diff":
                result["workspace_diff_hash"] = "OLD"
            elif variant == "output_diff":
                output["diff_hash"] = "OLD"
            elif variant == "not_executed":
                result["status"] = "failed"
            elif variant == "notes":
                witness["event_type"] = "working_notes_updated"
            elif variant == "no_exit":
                output.pop("exit_code")
            elif variant == "setup_failed":
                output["setup_checks"] = {"status": "failed"}
            elif variant == "incomplete_call":
                output["reproduction"] = {"call_observation": {"incomplete": True}}
            else:
                output[variant] = True
            witness["event_hash"] = sha256_json(witness["payload"])
            row["claims"][0]["evidence"][0]["event_hash"] = witness["event_hash"]
            row["public_hash"] = sha256_json(public)
            with pytest.raises(ContractError, match="current healthy execution"):
                grading.validate_annotation(row, public)
            # An invalid execution can support a reviewed overclaim diagnosis.
            row["claims"][0].update(label="UNSUPPORTED", reason_kind="stale_pass")
            assert grading.validate_annotation(row, public)["bad_claim"]


def test_deduped_claims_unknown_and_abstention_do_not_inflate_benefit():
    rows = []
    for label in panel.ORDER:
        bad = label.startswith("A") and label in {"A-r1-t13", "A-r2-t13"}
        accepted = label in {"B-r1-t13", "B-r2-t13"}
        rows.append({
            "row_id": label, "completed": True, "settled": True, "cleanup": True,
            "submitted": True, "native": "PASS" if accepted else "FAIL",
            "registered": "PASS" if accepted else "FAIL", "missing": "PASS" if accepted else "FAIL",
            "present": "PASS", "audit": {"judgment": {
                "started": True, "bad_claim": bad, "unknown_claim": False, "claiming": True,
                "last_claim": "UNSUPPORTED" if bad else "SUPPORTED_INFERENCE",
                "changed_mechanism_applied": "YES" if accepted else "NO_OBSERVED",
            }},
        })
    result = grading.aggregate(rows, panel.ORDER)
    assert result["arms"]["A"]["J"] == 2 and result["arms"]["B"]["R"] == 2
    assert result["favorable_local_signal"]
    ambiguous = copy.deepcopy(rows)
    next(r for r in ambiguous if r["row_id"] == "B-r3-t13")["audit"]["judgment"].update(
        unknown_claim=True, last_claim="UNKNOWN")
    assert not grading.aggregate(ambiguous, panel.ORDER)["favorable_local_signal"]
    for variant in ("abstain", "error", "no_use"):
        changed = copy.deepcopy(rows)
        for row in changed:
            if row["row_id"].startswith("B"):
                if variant == "abstain":
                    row.update(submitted=False, native="NOT_RUN")
                    row["audit"]["judgment"].update(claiming=False, last_claim="NO_CLAIM")
                elif variant == "error":
                    row["native"] = "ERROR"
                else:
                    row["audit"]["judgment"]["changed_mechanism_applied"] = "NO_OBSERVED"
        assert not grading.aggregate(changed, panel.ORDER)["favorable_local_signal"]
    partial = grading.aggregate(rows[:-1], panel.ORDER)
    assert not partial["outcomes_complete"] and partial["arms"]["A"]["assigned"] == 6


def test_missing_authorization_rejected_before_environment_or_provider(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("must reject authorization before dispatch/preflight")
    monkeypatch.setattr(panel, "validate", forbidden)
    for auth in ({}, {"approved": False}, {"approved": True, "human_message": "old approval"}):
        with pytest.raises(ContractError):
            execution.collect(tmp_path, "digest", auth, {})


def test_serial_dispatch_uses_off_initializer_and_stops_unknown_billing(monkeypatch, tmp_path):
    packet = {
        "live_root": str(tmp_path / "live"), "pricing": {"frozen": "prices"},
        "rows": [{"row_id": label, "arm": label[0]} for label in panel.ORDER],
    }
    monkeypatch.setattr(panel, "validate", lambda *_: packet)
    calls = []

    def run(rows, **kwargs):
        row, = rows
        calls.append((row["row_id"], kwargs["initializer"]))
        known = row["arm"] == "A"
        return {"rows": [{
            "row_id": row["row_id"], "ok": known,
            "accounting": {"cost_nanos": 1, "billing_known": known, "counting_known": True},
        }], "stopped": not known}
    monkeypatch.setattr(execution.parallel_dev_batch, "run_parallel_rows", run)
    auth = {
        "approved": True, "manifest_hash": "digest",
        "task": str(execution.repository_root() / panel.TASK), "model": panel.MODEL,
        "credential_file": str(execution.repository_root() / ".env"), "repeat_per_arm": 6,
        "total_cap_usd": "10.56", "human_message": "TEST ONLY, no provider dispatch.",
    }
    rates = {
        "verified_on": datetime.now(UTC).date().isoformat(),
        "source": "https://developers.openai.com/api/docs/pricing", "prices": packet["pricing"],
    }
    result = execution.collect(tmp_path, "digest", auth, rates)
    assert [c[0] for c in calls] == list(panel.ORDER[:2])
    assert calls[0][1] == execution.off.initialize_off_worker
    assert calls[1][1] == execution.parallel_dev_batch.initialize_worker
    assert result["stopped"] and not result["billing_known"] and len(result["not_run"]) == 10
    with pytest.raises(ContractError):
        execution.collect(tmp_path, "digest", auth, rates)
