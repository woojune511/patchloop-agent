from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from test_caller_uptake_followup import saved_fixture
from test_checkpoint_comparison import install_sdk
from test_checkpoint_continuation import stop_steps
from test_mutation_advice_checkpoint import source as source  # noqa: F401
from test_saved_caller_checkpoint import saved_packet as saved_packet  # noqa: F401

from diagnostics import caller_evidence_execution as execution
from diagnostics import caller_evidence_grading as grading
from diagnostics import caller_uptake_execution, caller_uptake_followup
from diagnostics import checkpoint_comparison as comparison
from diagnostics import checkpoint_continuation as continuation
from diagnostics.caller_uptake import file_ref
from diagnostics.positive_verification_panel import save
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.repository import WorkspaceManager
from patchloop.util import sha256_bytes


@pytest.fixture
def execution_packet(saved_packet, source, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "_require_tracked_clean_paths", lambda *a: None)
    monkeypatch.setattr(comparison, "check_environment", lambda *a: {"status": "READY"})
    prepared = comparison.prepare(Path(saved_packet["packet"]), saved_packet["packet_hash"],
        source.root.parent / "absent.env", tmp_path / "live", tmp_path / "comparison")
    plan = json.loads(Path(prepared["manifest"]).read_bytes())
    root = tmp_path / "execution"
    root.mkdir()
    save(root, "continuation-manifest.json", plan)
    packet = {"controls": plan, "rows": execution.rows_for(plan)}
    save(root, "native-fixture.json", {"instance_id": "fixture"})
    packet["native_input"] = {"instance_id": "fixture",
                              "rows": file_ref(root / "native-fixture.json")}
    monkeypatch.setattr(execution, "validate", lambda *a: packet)
    authorization = {"approved": True, "manifest_hash": "test", "task": plan["task"],
        "model": plan["model"], "credential_file": plan["env_file"], "repeat_per_arm": 6,
        "new_cap_nanos": plan["new_cap_nanos"], "human_message": "synthetic test only"}
    pricing = {"verified_on": datetime.now(UTC).date().isoformat(),
               "source": plan["pricing_source"], "prices": plan["pricing"]}
    return root, packet, authorization, pricing


def test_twelve_serial_branches_sealed_and_public_audit_excludes_inherited_decisions(
    execution_packet, source, monkeypatch,
):
    root, packet, auth, price = execution_packet
    clients = [continuation.ScriptedClient(stop_steps()) for _ in range(12)]
    install_sdk(monkeypatch, source, clients)
    result = execution.collect(root, "test", auth, price)
    assert result["started"] == 12 and result["stop_reason"] is None
    assert result["grades"] == "SEALED" and "rows" not in result
    plan = packet["controls"]
    assert plan["new_cap_nanos"] == 12 * plan["row_new_cap_nanos"]
    assert result["new_cost_nanos"] < plan["new_cap_nanos"]
    allowed = execution.export_audit(root, "test")
    assert len(allowed) == 12
    annotations = []
    for label, client in zip(plan["order"], clients, strict=True):
        value = json.loads((root / "audit-public" / (label + ".json")).read_bytes())
        assert value["first_delivery"] == "COMPLETE"
        assert sum(e["event_type"] == "turn_decision_recorded" for e in value["events"]) == 1
        text = json.dumps(value)
        assert "task_acceptance" not in text
        for event in value["events"]:
            if event["event_type"] == "provider_call_started":
                assert all(item.get("type") != "reasoning" and "encrypted_content" not in item
                           for item in event["payload"]["wire"]["input"])
        assert len(client.created) == len(client.counted) == 1
        decision = next(e for e in value["events"] if e["event_type"] == "turn_decision_recorded")
        audit = file_ref(root / "audit-public" / (label + ".json"))
        annotations.append({"row_id": label, "audit": audit, "G": "NOT_ACQUIRED",
            "D": "COMPLETE" if label.startswith("B") else "NOT_ACQUIRED_OR_SUPPLIED",
            "J": "NO_EXPLICIT_JUDGMENT", "action_use": "NONE", "acquisition_origin": "none",
            "reviewer": "fixture", "rationale": "Synthetic stop, no semantic assertion.",
            "alternatives": "No model judgment measured.", "evidence": [], "inventory": [],
            "first_decision": {**audit, "sequence": decision["sequence"],
                               "event_hash": decision["event_hash"]}})
    save(root, "annotations.json", {"rows": annotations, "fresh_grade_exposure": []})
    sealed = execution.seal_audit(root, "test", root / "annotations.json")
    assert len(sealed) == 12
    assessed = execution.assess(root, "test")
    assert assessed["complete"] and assessed["arms"]["B"]["Q"] == 0
    assert assessed["arms"]["B"]["J"] == {"NO_EXPLICIT_JUDGMENT": 6}
    with pytest.raises(ContractError, match="no assessment retry"):
        execution.assess(root, "test")
    with pytest.raises(ContractError, match="no resume"):
        execution.collect(root, "test", auth, price)


@pytest.mark.parametrize("failure", ["count", "transport", "usage"])
def test_uncertainty_stops_all_twelve_without_replacement(
    execution_packet, source, monkeypatch, failure,
):
    root, packet, auth, price = execution_packet
    client = continuation.ScriptedClient(stop_steps(), failure=failure)
    install_sdk(monkeypatch, source, [client])
    result = execution.collect(root, "test", auth, price)
    raw = json.loads((Path(packet["controls"]["result_root"]) / "result.json").read_bytes())
    assert all(r["status"] == "NOT_RUN" for r in raw["rows"][1:])
    assert result["billing_known"] == (failure == "count")
    assert result["new_cost_nanos"] == (0 if failure == "count" else None)


def test_authorization_and_current_rates_required_before_dispatch(execution_packet, monkeypatch):
    root, _, auth, price = execution_packet
    monkeypatch.setattr(comparison, "collect", lambda *a, **k: pytest.fail("dispatch forbidden"))
    with pytest.raises(ContractError, match="authorization"):
        execution.collect(root, "test", {**auth, "new_cap_nanos": 1}, price)
    with pytest.raises(ContractError, match="fresh official"):
        execution.collect(root, "test", auth, {**price, "verified_on": "2000-01-01"})


def test_assessment_requires_sealed_audit(execution_packet):
    root, _, _, _ = execution_packet
    with pytest.raises(ContractError, match="seal public"):
        execution.assess(root, "test")


def test_post_row_failure_keeps_submission_receipt_and_stops(execution_packet, source, monkeypatch):
    root, packet, _, _ = execution_packet
    install_sdk(monkeypatch, source, [continuation.ScriptedClient(stop_steps())])
    def fail(*args):
        raise ContractError("synthetic due receipt error")
    path = root / "continuation-manifest.json"
    result = comparison.collect(path, sha256_bytes(path.read_bytes()),
        Decimal(packet["controls"]["new_cap_nanos"]) / 10**9, after_row=fail)
    assert result["rows"][0]["status"] == "COLLECTOR_FAILED"
    assert result["rows"][0]["result"]["terminal"] == "AGENT_STOPPED"
    assert all(r["status"] == "NOT_RUN" for r in result["rows"][1:])


@pytest.mark.parametrize("tests_only", [False, True])
def test_native_full_patch_and_caller_source_projection_are_separate(
    tmp_path, monkeypatch, tests_only,
):
    source, output, _ = saved_fixture(tmp_path, monkeypatch, tests_only=tests_only)
    packet, seal, *_ = caller_uptake_followup.validate_source(source, "unused")
    order = [r["row_id"] for r in packet["rows"]]
    seal["axes"] = {label: {"G": "NOT_ACQUIRED", "D": "COMPLETE", "J": "SUPPORTED",
                            "action_use": "SUPPORTED"} for label in order}
    seen = []
    def native(folder, req, patch, entry, deadline, *, patch_scope):
        workspace = tmp_path / "live/workspaces/run_dev_fixture/repo"
        assert patch == WorkspaceManager.diff_summary(workspace).patch.encode()
        assert patch and b"test_addition" in patch and patch_scope == "submitted"
        projected = (folder.parent / "source-only.patch").read_bytes()
        assert (projected == b"") is tests_only
        assert b"test_addition" not in projected
        seen.append(patch)
        folder.mkdir()
        save(folder, "receipt.json", {"submitted_diff": sha256_bytes(patch)})
        return "FAIL"
    monkeypatch.setattr(caller_uptake_execution, "native_assessment", native)
    output.mkdir()
    result = caller_uptake_execution._assess_rows(source, output, packet,
        DevJournal(output, caller_uptake_followup.JOURNAL), seal, order=order,
        aggregate=grading.aggregate, native_full_patch=True)
    assert len(seen) == 2 and result["complete"]
    assert result["arms"]["A"]["Q"] == result["arms"]["B"]["Q"] == 0
