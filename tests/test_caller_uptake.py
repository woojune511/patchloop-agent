"""No provider calls: caller oracle, exact scope, audit separation and fixed allocations."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from diagnostics import caller_uptake as panel
from diagnostics import caller_uptake_execution as execution
from diagnostics import caller_uptake_grading as grading
from diagnostics import caller_uptake_prepare as preparation
from patchloop.artifacts import ArtifactStore
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_json


def public_receipt(case="missing"):
    cwd, present = "/tmp/public-caller-fixture", case == "present"
    expected = {"caller version": "2.12.2", "current project": True, "public caller": True,
        "cwd": cwd, "relative argument": "src/project", "src initializer": True,
        "project initializer": present, "empty public input": "",
        "console entry": "pylint:run_pylint"}
    layout = ["src/__init__.py", "src/project/file.py"]
    if present:
        layout.insert(1, "src/project/__init__.py")
    before = {"stage": "before_call", "input": {"cwd": cwd,
        "argv": ["pylint", "src/project"], "layout": layout,
        "sys_path": ["/workspace", "/opt/patchloop-dependencies"],
        "environment": {"HOME": cwd + "/home", "PYLINTHOME": cwd + "/cache", "PYTHONPATH": None}}}
    calls = [{"function": function, "file": "/opt/patchloop-dependencies/" + file,
              "cwd": cwd, "arguments": args, "path_exists": True}
             for function, file, args in (
        ("run_pylint", "pylint/__init__.py", {}),
        ("__init__", "pylint/lint/run.py", {"args": ["src/project"]}),
        ("get_ast", "pylint/lint/pylinter.py", {"filepath": "src/project/file.py"}))]
    outcome = {"stage": "result", "present": present, "overflow": 0,
        "entry_point": "pylint:run_pylint", "origins": {
            "pylint": "/opt/patchloop-dependencies/pylint/__init__.py",
            "astroid": "/workspace/astroid/__init__.py"}, "python": "3.9.25 fixture",
        "configuration": {"jobs": 1, "rcfile": None}, "calls": calls,
        "pylint_exit_code": 0, "pylint_stdout": "", "pylint_stderr": ""}
    return {"source_hash": grading.PROGRAMS[case], "status": "passed", "exit_code": 0,
        "execution_policy": {"dependencies": {"manifest_hash": "deps"},
                             "cleanup_status": "confirmed"},
        "setup_checks": {"source_hash": grading.PROGRAMS[case], "status": "passed",
            "checks": [{"label": k, "actual": v, "expected": v, "matched": True}
                       for k, v in expected.items()]},
        "stdout": json.dumps(before) + "\n" + json.dumps(outcome)}


def change_outcome(receipt, **changes):
    lines = [json.loads(line) for line in receipt["stdout"].splitlines()]
    lines[1].update(changes)
    receipt["stdout"] = "\n".join(json.dumps(line) for line in lines)
    return receipt


def grade(receipt, case="missing", **kwargs):
    return grading.caller_grade(receipt, **{"case": case, "dependency_hash": "deps",
        "diff_hash": "patch", "expected_diff": "patch", "cleanup": True, **kwargs})


@pytest.mark.parametrize("case", ["missing", "present"])
def test_positive_parser_fixture_requires_real_target_without_old_internal_route(case):
    receipt = public_receipt(case)
    assert grade(receipt, case)["status"] == "PASS"
    # No astroid manager/builder call is required: a legitimate route may change.
    assert all("astroid/" not in c["file"] for c in
               json.loads(receipt["stdout"].splitlines()[1])["calls"])


@pytest.mark.parametrize("changes", [
    {"pylint_exit_code": 1, "pylint_stdout": "F0010 old failure"},
    {"pylint_exit_code": 0, "pylint_stdout": "F0010"},
    {"pylint_exit_code": 2},
])
def test_probe_success_is_not_public_success(changes):
    assert grade(change_outcome(public_receipt(), **changes))["status"] == "FAIL"


def test_empty_output_skip_is_fail_even_when_caller_exits_zero():
    receipt = public_receipt()
    calls = json.loads(receipt["stdout"].splitlines()[1])["calls"][:2]
    assert grade(change_outcome(receipt, calls=calls))["status"] == "FAIL"


@pytest.mark.parametrize("path", ["./src/project/file.py",
    "/tmp/public-caller-fixture/src/project/file.py"])
def test_same_existing_child_accepts_equivalent_relative_or_absolute_paths(path):
    receipt = public_receipt()
    calls = json.loads(receipt["stdout"].splitlines()[1])["calls"]
    calls[-1]["arguments"]["filepath"] = path
    assert grade(change_outcome(receipt, calls=calls))["status"] == "PASS"


@pytest.mark.parametrize("path,exists", [
    ("src/project/other.py", True), ("/elsewhere/src/project/file.py", True),
    ("../src/project/file.py", True), ("src/project/file.py", False),
])
def test_other_or_nonexistent_child_does_not_receive_analysis_credit(path, exists):
    receipt = public_receipt()
    calls = json.loads(receipt["stdout"].splitlines()[1])["calls"]
    calls[-1]["arguments"]["filepath"], calls[-1]["path_exists"] = path, exists
    assert grade(change_outcome(receipt, calls=calls))["status"] == "FAIL"


@pytest.mark.parametrize("changes", [
    {"overflow": 1}, {"pylint_exit_code": None}, {"pylint_exit_code": True},
    {"entry_point": "copied:helper"}, {"origins": {"astroid": "/installed/astroid.py"}},
    {"configuration": {"jobs": 2, "rcfile": None}}, {"calls": []}, {"present": True},
])
def test_incomplete_or_wrong_scope_is_error_not_semantic_failure(changes):
    assert grade(change_outcome(public_receipt(), **changes))["status"] == "ERROR"


@pytest.mark.parametrize("key,value", [
    ("truncated", True), ("timed_out", True), ("cleanup_failed", True),
    ("deadline_exhausted", True), ("source_hash", "other program"), ("exit_code", 1),
    ("stdout", "not json"), ("stdout", ""), ("status", "failed"),
])
def test_bad_receipts_never_pass(key, value):
    receipt = public_receipt()
    receipt[key] = value
    assert grade(receipt)["status"] == "ERROR"


@pytest.mark.parametrize("changes", [{"diff_hash": "stale"}, {"cleanup": False},
                                      {"dependency_hash": "wrong arm"}])
def test_oracle_binds_candidate_environment_cleanup(changes):
    assert grade(public_receipt(), **changes)["status"] == "ERROR"


def test_input_layout_and_setup_are_required():
    receipt = public_receipt()
    lines = [json.loads(line) for line in receipt["stdout"].splitlines()]
    lines[0]["input"]["argv"] = ["pylint", "src/project/file.py"]
    receipt["stdout"] = "\n".join(json.dumps(line) for line in lines)
    assert grade(receipt)["status"] == "ERROR"
    receipt = public_receipt()
    receipt["setup_checks"]["checks"].pop()
    assert grade(receipt)["status"] == "ERROR"


def test_requests_keep_exact_budget_order_and_only_dependency_location_differs(tmp_path):
    requests = [panel.request(tmp_path / "deps", tmp_path / "live", row) for row in panel.ORDER]
    assert panel.ORDER[:4] == ("A-r1-t13", "B-r1-t13", "B-r2-t13", "A-r2-t13")
    assert len(requests) == 12 and sum(r.max_cost_usd for r in requests) == panel.CAP
    data = [r.model_dump(exclude={"state_root", "prepared_probe_dependencies"}) for r in requests]
    assert all(r == data[0] for r in data)
    assert panel.invariants()["references"] == 2
    assert requests[0].evaluation_reserve_seconds == 330


def settled(cost=880000000, **updates):
    value = {"ok": True, "accounting": {"billing_known": True, "counting_known": True,
                                        "cost_nanos": cost}}
    value["accounting"].update(updates)
    return value


def test_full_reservations_no_transfer_and_known_row_caps_stay_local():
    ledger = execution.Allocation()
    for label in panel.ORDER:
        assert ledger.settle(label, settled())
    assert ledger.cost == {"A": 5280000000, "B": 5280000000}
    with pytest.raises(ContractError):
        ledger.settle(panel.ORDER[0], settled(0))


@pytest.mark.parametrize("updates", [{"billing_known": False}, {"counting_known": False},
    {"cost_nanos": None}, {"cost_nanos": -1}, {"cost_nanos": 880000001}])
def test_uncertainty_or_extra_spending_stops_all_remaining_rows(updates):
    ledger = execution.Allocation()
    assert not ledger.settle(panel.ORDER[0], settled(**updates))
    with pytest.raises(ContractError, match="stopped"):
        ledger.settle(panel.ORDER[1], settled())


def test_unsettled_worker_and_changed_row_order_stop():
    ledger = execution.Allocation()
    with pytest.raises(ContractError):
        ledger.settle(panel.ORDER[1], settled())
    assert not ledger.settle(panel.ORDER[0], {**settled(), "ok": False})


def test_shared_host_budget_does_not_reset_between_assessments():
    assert 59 <= execution.assessment_deadline(10, clock=lambda: 550).remaining_seconds() <= 60
    with pytest.raises(ContractError, match="exhausted"):
        execution.assessment_deadline(10, clock=lambda: 610)


def test_audit_exports_dispatched_request_not_proposal_and_omits_private_grades(tmp_path):
    store = ArtifactStore(tmp_path)
    wire = {"input": [{"role": "user", "content": "public evidence"},
                      {"type": "reasoning", "encrypted_content": "secret-ciphertext"}],
            "max_output_tokens": 25000}
    bundle = {"request": wire, "turn": {"turn_id": "t1"}}
    artifact = store.put_json(bundle).model_dump(mode="json")
    sent = {**wire, "max_output_tokens": 1234}
    events = [
        ("model_input_prepared", {"artifact": artifact, "request_hash": sha256_json(wire)}),
        ("provider_call_started", {"turn_id": "t1", "output_ceiling": 1234,
                                  "request_hash": sha256_json(sent), "active_elapsed_ms": 500}),
        ("turn_decision_recorded", {"turn_id": "t1", "tool_calls": [],
                                    "continuation_ref": "secret-ciphertext"}),
        ("evaluator_finished", {"private": "private-grading-output"}),
        ("terminal", {"terminal": "EVALUATOR_FAIL", "private": "private-grading-output"}),
    ]
    events = [{"sequence": i, "event_hash": str(i), "event_type": k, "payload": p}
              for i, (k, p) in enumerate(events)]
    exported = execution.public_events(events, store)
    text = canonical_json(exported)
    assert "private-grading-output" not in text and "EVALUATOR_FAIL" not in text
    assert "secret-ciphertext" not in text and "reasoning_redacted" in text
    assert exported[0]["payload"]["wire"]["max_output_tokens"] == 1234
    events[1]["payload"]["request_hash"] = "wrong"
    with pytest.raises(ContractError, match="mismatch"):
        execution.public_events(events, store)


def annotation(tmp_path):
    path = tmp_path / "public.json"
    path.write_bytes(b"caller material; decision respects caller scope")
    ref = {"path": str(path), "hash": sha256_bytes(path.read_bytes()),
           "start": 0, "end": len(path.read_bytes())}
    row = {k: "YES" for k in ("availability", "disclosure", "inspection", "delivery",
                              "interpretation")}
    row.update({k: "NO_OBSERVED" for k in ("relevant_execution", "base_failure", "normal_control",
                                          "candidate_test")})
    row.update(U_source="YES", U_exec="NO_OBSERVED", reviewer="public-only reviewer",
        rationale="explicit source-supported decision", alternatives="helper does not reach caller",
        evidence_inventory=[], source_evidence=[{"material": {**ref, "end": 15}, "request": ref,
            "decision": ref, "material_sequence": 1, "request_sequence": 2,
            "decision_sequence": 3, "scope_rationale": "caller source, not executed result"}])
    return row, {str(path): ref["hash"]}


def test_source_use_is_not_execution_use_and_a_mention_is_not_uptake(tmp_path):
    row, allowed = annotation(tmp_path)
    assert grading.validate_annotation(row, allowed) == "YES"
    row["source_evidence"] = []
    with pytest.raises(ContractError, match="linked evidence"):
        grading.validate_annotation(row, allowed)


@pytest.mark.parametrize("change", ["no_opportunity", "stale", "not_delivered", "bad_hash"])
def test_counterexample_claim_needs_current_delivered_evidence_and_opportunity(tmp_path, change):
    row, allowed = annotation(tmp_path)
    item = copy.deepcopy(row["source_evidence"][0])
    item.update(action_id="a", input_hash="i", diff_hash="d", decision_diff_hash="d",
        program_hash="p", entry_setup_rationale="real installed entry and public input",
        counterexample=True, decision_opportunity=True)
    row.update(U_exec="YES", exec_evidence=[item])
    if change == "no_opportunity":
        item["decision_opportunity"] = False
    elif change == "stale":
        item["decision_diff_hash"] = "edited"
    elif change == "not_delivered":
        item["request"] = {**item["request"], "start": 16}
    else:
        item["material"]["hash"] = "wrong"
    with pytest.raises(ContractError):
        grading.validate_annotation(row, allowed)


def quality_row(label, *, use="NO_OBSERVED"):
    return {"row_id": label, "submitted": True, "registered": "PASS", "native": "PASS",
        "missing": "PASS", "present": "PASS", "submitted_diff": "submitted",
        "assessed_from_diff": "submitted", "source_only_diff": "source", "caller_diff": "source",
        "native_diff": "source", "completed": True, "settled": True, "cleanup": True,
        "safety": "PASS", "U": use}


def test_primary_outcomes_include_nonusers_and_all_twelve_intended_rows():
    result = grading.aggregate([quality_row(panel.ORDER[0])], panel.ORDER)
    assert result["arms"]["A"]["intended"] == result["arms"]["B"]["intended"] == 6
    assert result["arms"]["A"]["Q"] == 1 and result["Q_B_minus_A"] == -1
    assert result["rows"][0]["U"] == "NO_OBSERVED"
    assert len(result["rows"]) == 12 and not result["favorable_local_signal"]


def test_public_acceptance_and_lineage_are_separate():
    row = quality_row(panel.ORDER[0], use="YES")
    row["missing"] = "FAIL"
    result = grading.aggregate([row], panel.ORDER)
    assert result["arms"]["A"]["S"] == 1 and result["arms"]["A"]["Q"] == 0
    row["caller_diff"] = "different patch"
    with pytest.raises(ContractError, match="lineage"):
        grading.aggregate([row], panel.ORDER)


def test_assessment_refuses_unsealed_audit_without_opening_grades(tmp_path, monkeypatch):
    monkeypatch.setattr(panel, "validate", lambda *a: {})
    with pytest.raises(ContractError, match="seal all"):
        execution.assess(tmp_path, "digest")
    assert not (tmp_path / "assessments").exists()


def test_collection_needs_exact_approval_before_any_worker(tmp_path, monkeypatch):
    monkeypatch.setattr(panel, "validate", lambda *a: {})
    with pytest.raises(ContractError, match="authorization"):
        execution.collect(tmp_path, "digest", {"approved": False}, pricing_review={})


def test_native_uses_remainder_not_new_six_hundred_seconds(tmp_path, monkeypatch):
    seen = []
    def fake_run(argv, **kwargs):
        seen.append(kwargs["timeout"])
        output = Path(argv[argv.index("--output") + 1])
        output.mkdir()
        (output / "cleanup.json").write_text('{"remaining": []}')
        (output / "control-1.json").write_text(json.dumps({
            "instance_id": "fixture", "complete": True, "missing_count": 0, "resolved": False}))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(execution.subprocess, "run", fake_run)
    status = execution.native_assessment(tmp_path / "native", SimpleNamespace(model="fixture"),
        b"patch", {"instance_id": "fixture", "native_row": "private-only"},
        execution.assessment_deadline(10, clock=lambda: 590))
    assert status == "FAIL" and 0 < seen[0] <= 20


def test_first_request_comparison_rejects_unrelated_tool_or_policy_difference(monkeypatch):
    state = {"current_diff": {"patch": ""}, "working_plan": {"plan": None},
        "working_notes": {"findings": []}, "visible_check_status": [],
        "segment_handoff": {"segment_id": "derived"}, "remaining_budget": {"calls": 40}}
    monkeypatch.setattr(preparation, "reconstruct_state", lambda *a, **kw: copy.deepcopy(state))
    a = {"input": [{"role": "system", "content": "fixed prompt"}],
         "tools": [{"name": "run_probe", "description": "prefix suffix"}], "model": "same"}
    b = copy.deepcopy(a)
    b["tools"][0]["description"] = (
        "prefix " + preparation.description(["pylint==2.12.2"]) + "suffix")
    assert preparation.compare_initial(a, b)["passed"]
    b["tools"][0]["description"] += " extra instruction"
    with pytest.raises(ContractError, match="outside"):
        preparation.compare_initial(a, b)


@pytest.mark.parametrize("stop_at", [None, 2])
def test_serial_collection_closes_or_stops_without_grade_exposure(tmp_path, monkeypatch, stop_at):
    root = tmp_path / "packet"
    root.mkdir()
    packet = {"live_root": str(tmp_path / "live"), "pricing": {"input": "fixture"},
        "rows": [{"row_id": label, "arm": label[0], "request":
                  panel.request(tmp_path / "deps", tmp_path / "live", label).model_dump(
                      mode="json")}
                 for label in panel.ORDER]}
    monkeypatch.setattr(panel, "validate", lambda *a: packet)
    seen = []
    def wave(rows, **kwargs):
        assert kwargs["workers"] == 1 and kwargs["total_cap"] == panel.ROW_CAP
        assert kwargs["after_row"] is execution.due_receipts
        seen.append(rows[0]["row_id"])
        value = {**settled(20), "result": {"runs": [{"terminal": "EVALUATOR_PASS"}]}}
        stopped = len(seen) == stop_at
        if stopped:
            value["accounting"]["counting_known"] = False
        return {"rows": [value], "stopped": stopped}
    monkeypatch.setattr(execution.parallel_dev_batch, "run_parallel_rows", wave)
    auth = {"approved": True, "packet_hash": "digest",
        "task": str(panel.repository_root() / panel.TASK),
        "model": panel.MODEL, "credential_file": str(panel.repository_root() / ".env"),
        "repeat_per_arm": 6, "total_cap_usd": str(panel.CAP), "human_message": "fixture approval"}
    prices = {"verified_on": execution.datetime.now(execution.UTC).date().isoformat(),
              "source": "https://developers.openai.com/api/docs/pricing",
              "prices": packet["pricing"]}
    result = execution.collect(root, "digest", auth, pricing_review=prices)
    assert seen == list(panel.ORDER[:stop_at] if stop_at else panel.ORDER)
    assert result["grades"] == "SEALED" and "EVALUATOR_PASS" not in canonical_json(result)
    with pytest.raises(ContractError, match="no resume"):
        execution.collect(root, "digest", auth, pricing_review=prices)


def test_due_registered_receipt_blocks_next_row_but_native_is_deferred(tmp_path, monkeypatch):
    monkeypatch.setattr(execution, "DevJournal", lambda *a: SimpleNamespace(
        load_envelope=lambda: None, events=lambda: []))
    monkeypatch.setattr(execution, "load_evaluation_completion", lambda *a: None)
    value = {"result": {"runs": [{"run_id": "run_dev_fixture",
                                  "artifact_hashes": {"submitted_patch": "hash"}}]}}
    req = SimpleNamespace(state_root=tmp_path)
    with pytest.raises(ContractError, match="registered receipt"):
        execution.due_receipts(0, value, req)
    value["result"]["runs"][0]["artifact_hashes"] = {}
    assert execution.due_receipts(0, value, req)["native"] == "DEFERRED_UNTIL_AUDIT"
