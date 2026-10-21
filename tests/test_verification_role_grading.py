"""Judgment and report-use controls do not borrow independent acceptance grades."""
from __future__ import annotations

import copy
import json

import pytest
from test_verification_state_grading import event, reviewed_row

from diagnostics import verification_role_execution as execution
from diagnostics import verification_role_grading as grading
from diagnostics import verification_role_panel as panel
from diagnostics import verification_state_grading as common
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.errors import ContractError
from patchloop.util import sha256_json


def annotated(label="CONTRADICTED"):
    row, public = reviewed_row(label)
    entry = public["events"][1]
    wire = entry["payload"]["wire"]
    state = reconstruct_state(wire["input"], context_policy="segmented-v1")
    state["verification_phase"] = {"phase": "final", "report": None}
    state["current_diff"]["patch"] = "public candidate"
    wire["input"] = assemble_model_input(system_prompt="fixed", state=state, history=[],
                                         context_policy="segmented-v1")
    entry["payload"]["actual_request_hash"] = sha256_json(wire)
    row["claims"][0]["request_hash"] = sha256_json(wire)
    row["public_hash"] = sha256_json(public)
    row["verification_reports"] = []
    row["verification_chain"] = {
        key: {"status": "NO_OBSERVED", "evidence": [], "rationale": "Bounded public fixture."}
        for key in grading.CHAIN}
    return row, public


def test_final_judgment_labels_are_independent_of_repair_outcomes():
    for label in common.LABELS:
        row, public = annotated(label)
        result = grading.validate_annotation(row, public)
        assert result["J_final"] is (label in common.BAD)
        assert result["J_any"] is (label in common.BAD)
        assert result["final_assessable"] is (label not in {"UNKNOWN", "NO_CLAIM"})
        assert not result["supported_report_use"]


def test_absent_phase_or_report_cannot_receive_credit_and_private_grades_are_rejected():
    for axis in ("phase_reached", "feedback_delivery", "application"):
        row, public = annotated()
        row["verification_chain"][axis].update(
            status="YES", evidence=row["claims"][0]["evidence"])
        with pytest.raises(ContractError):
            grading.validate_annotation(row, public)
    row, public = annotated()
    public["events"].append(event(5, "evaluation_finished", {"private_grade": "PASS"}))
    row["public_hash"] = sha256_json(public)
    with pytest.raises(ContractError, match="nonpublic"):
        grading.validate_annotation(row, public)


def two_claims(*, initial_phase="initial", final_label="SUPPORTED_DIRECT"):
    row, public = annotated(final_label)
    initial = copy.deepcopy(public["events"][1:4])
    original_claim = copy.deepcopy(row["claims"][0])
    # Place a distinct early completion assertion before the final decision.
    for e in public["events"][1:]:
        e["sequence"] += 3
    for e in initial:
        payload = e["payload"]
        if "turn_id" in payload:
            payload["turn_id"] = "initial-turn"
        if e["event_type"] == "provider_call_started":
            state = reconstruct_state(payload["wire"]["input"], context_policy="segmented-v1")
            state["verification_phase"]["phase"] = initial_phase
            payload["wire"]["input"] = assemble_model_input(
                system_prompt="fixed", state=state, history=[], context_policy="segmented-v1")
            payload["actual_request_hash"] = sha256_json(payload["wire"])
        elif e["event_type"] == "turn_decision_recorded":
            payload["tool_calls"][0]["action_id"] = "early-finish"
        else:
            payload["result"]["action_id"] = "early-finish"
    early_raw = initial[1]["payload"]["tool_calls"][0]
    initial[2]["payload"]["result"]["input_hash"] = common.input_hash(early_raw)
    public["events"] = [public["events"][0], *initial, *public["events"][1:]]
    original_claim.update(action_id="early-finish", input_hash=common.input_hash(early_raw),
        request_hash=initial[0]["payload"]["actual_request_hash"], label="UNSUPPORTED",
        is_completion_claim=True, reason_kind="helper_to_task")
    row["claims"][0].update(decision_sequence=6, request_sequence=5)
    row["claims"].insert(0, original_claim)
    row["reviewed_decisions"] = [3, 6]
    row["public_hash"] = sha256_json(public)
    return row, public


def test_corrected_final_claim_does_not_erase_initial_error():
    row, public = two_claims()
    summary = grading.validate_annotation(row, public)
    assert summary["J_any"] is True and summary["J_final"] is False
    row, public = two_claims(initial_phase="final", final_label="NO_CLAIM")
    summary = grading.validate_annotation(row, public)
    assert summary["J_final"] and summary["final_label"] == "UNSUPPORTED"


def test_screen_uses_final_judgments_and_cannot_reward_silence_or_missing_repairs():
    order = panel.allocation(3)["order"]
    rows = []
    for label in order:
        is_b = label.startswith("B")
        audit = {"started": True, "J_any": True, "bad_claim": True,
                 "J_final": not is_b, "final_label": "SUPPORTED_DIRECT" if is_b else "UNSUPPORTED",
                 "final_assessable": True, "candidate_reached": True,
                 "supported_report_use": is_b}
        rows.append({"row_id": label, "submitted": True, "completed": True, "settled": True,
                     "cleanup": True, "native": "PASS" if is_b else "FAIL",
                     "registered": "PASS" if is_b else "FAIL", "missing": "PASS", "present": "PASS",
                     "audit": {"judgment": audit}})
    result = grading.aggregate(rows, order)
    assert result["favorable_local_signal"]
    assert result["arms"]["B"]["J_any"] == 3 and result["arms"]["B"]["J_final"] == 0
    for change in ("silence", "no_repair", "no_report_use"):
        altered = copy.deepcopy(rows)
        for r in altered:
            if not r["row_id"].startswith("B"):
                continue
            if change == "silence":
                r["audit"]["judgment"].update(final_assessable=False, final_label="NO_CLAIM")
            elif change == "no_repair":
                r.update(native="FAIL", registered="FAIL")
            else:
                r["audit"]["judgment"]["supported_report_use"] = False
        assert not grading.aggregate(altered, order)["favorable_local_signal"]


def test_execution_requires_fresh_exact_approval_and_initializes_both_roles(tmp_path):
    with pytest.raises(ContractError):
        execution.collect(tmp_path, "unfrozen", {"repeat_per_arm": 3}, {})
    assert execution.initializer("A").__name__ == "initialize_worker_a"
    assert execution.initializer("B").__name__ == "initialize_worker_b"
    with pytest.raises(ContractError):
        panel.allocation(6)


def with_report():
    row, public = annotated("NO_CLAIM")
    observation = public["events"][0]["payload"]["result"]["output"]["stdout"]
    raw = {"action_id": "report", "name": grading.role.REPORT_TOOL,
           "arguments": {"assessment": observation}}
    wire = copy.deepcopy(public["events"][1]["payload"]["wire"])
    state = reconstruct_state(wire["input"], context_policy="segmented-v1")
    state["verification_phase"]["phase"] = "verify"
    wire["input"] = assemble_model_input(system_prompt="fixed", state=state, history=[],
                                         context_policy="segmented-v1")
    receipt = {"tool": grading.role.REPORT_TOOL, "action_id": "report",
               "input_hash": common.input_hash(raw), "workspace_diff_hash": "D1",
               "status": "succeeded", "output": {
                   "assessment": observation, "reviewed_diff_hash": "D1"}}
    added = [event(2, "provider_call_started", {"turn_id": "verify", "wire": wire,
                 "actual_request_hash": sha256_json(wire)}),
             event(3, "turn_decision_recorded", {"turn_id": "verify", "tool_calls": [raw]}),
             event(4, "action_finished", {"result": receipt})]
    for item in public["events"][1:]:
        item["sequence"] += 3
    final = public["events"][1]["payload"]
    state["verification_phase"] = {"phase": "final", "report": receipt}
    final["wire"]["input"] = assemble_model_input(system_prompt="fixed", state=state, history=[],
                                                 context_policy="segmented-v1")
    final["actual_request_hash"] = sha256_json(final["wire"])
    public["events"] = [public["events"][0], *added, *public["events"][1:]]
    row["public_hash"] = sha256_json(public)
    row["reviewed_decisions"] = [3, 6]
    row["claims"][0].update(decision_sequence=6, request_sequence=5,
                            request_hash=final["actual_request_hash"])
    row["verification_reports"] = [{"mechanical": grading.report_inventory(public)[0],
        "text": observation, "rationale": "Reviewed original public failure.",
        "semantic_review": True, "is_completion_claim": False, "judgment": "ACCURATE",
        "conclusion": "REFUTES_CANDIDATE", "evidence": row["claims"][0]["evidence"]}]
    item = grading.catalog(public)[-1]
    row["report_application"] = {
        **{k: item[k] for k in ("decision_sequence", "action_id", "input_hash",
                                "request_sequence", "request_hash", "diff_hash")},
        "report_text": observation, "use_text": "original issue", "currency": "CURRENT",
        "semantic_review": True, "rationale": "Structural fixture of reviewed report use."}
    row["verification_chain"]["application"].update(
        status="YES", evidence=row["claims"][0]["evidence"])
    return row, public


def test_report_use_needs_exact_prior_receipt_current_diff_and_correct_interpretation():
    row, public = with_report()
    assert grading.validate_annotation(row, public)["supported_report_use"]
    for defect in ("stale", "unknown", "wrong_rejection", "omitted", "false_currency",
                   "undelivered", "unreviewed_completion"):
        row, public = with_report()
        if defect == "stale":
            row["report_application"]["diff_hash"] = "NEXT"
        elif defect in {"unknown", "wrong_rejection"}:
            row["verification_reports"][0]["judgment"] = (
                "UNKNOWN" if defect == "unknown" else "WRONG_REJECTION")
        elif defect == "omitted":
            row["verification_reports"] = []
        elif defect == "false_currency":
            row["report_application"]["currency"] = "HISTORICAL"
        elif defect == "undelivered":
            row["report_application"]["report_text"] = "Unseen correct answer"
        else:
            row["verification_reports"][0]["is_completion_claim"] = True
        with pytest.raises(ContractError):
            grading.validate_annotation(row, public)
    row, public = with_report()
    row["verification_reports"][0]["judgment"] = "WRONG_REJECTION"
    row["verification_chain"]["application"]["status"] = "NO_OBSERVED"
    result = grading.validate_annotation(row, public)
    assert result["V_wrong"] == 1 and not result["supported_report_use"]


def test_role_packet_discriminator_and_additional_freeze_gates(tmp_path):
    from diagnostics import verification_state_panel as old

    with panel.configured():
        assert old.SCHEMA == "verification-role-comparison-v1"
        assert old.freeze is panel.freeze and old.validate is panel.validate
    assert old.SCHEMA == "verification-state-comparison-v2"
    validation = tmp_path / "validation.json"
    for value in ({}, {"verification_role": {
        "contract_hash": sha256_json(grading.role.contract())}}):
        validation.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises(ContractError):
            panel.freeze(tmp_path, tmp_path / "live", validation)
    identity = {"head": "fixture", "runtime_hash": "runtime", "implementation": {"code": "H"}}
    value = {**identity, "verification_role": {
        "contract_hash": sha256_json(grading.role.contract())}}
    witness = tmp_path / "witness.json"
    witness.write_text("{}", encoding="utf-8")
    for name in ("same_snapshot_capture", "historical_packet_replay", "resource_feasibility"):
        receipt = {**identity, "contract_hash": value["verification_role"]["contract_hash"],
                   "gate": name, "passed": True, "provider_calls": 0, "input_count_calls": 0,
                   "evidence": [panel.prior.file_ref(witness)]}
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(receipt), encoding="utf-8")
        value["verification_role"][name] = panel.prior.file_ref(path)
    validation.write_text(json.dumps(value), encoding="utf-8")
    assert panel.qualification(validation) == value["verification_role"]
    value["head"] = "different-commit"
    validation.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ContractError, match="qualification failed"):
        panel.qualification(validation)
