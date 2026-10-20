"""Instruction delivery, unchanged actions, and bounded experiment execution."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from diagnostics import positive_verification_panel as panel
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner, working_plan
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import sha256_json


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("local panel verification must not contact a provider")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def test_same_request_and_distinct_instruction_identity_restored_on_error():
    req = panel.request("1733", Path("C:/pt/not-run"))
    base = working_plan.instructions("brief-v1")
    original_hash = runner._model_hash(req, None)
    with pytest.raises(RuntimeError), panel.arm_instructions("B"):
        assert working_plan.instructions() == base.replace(panel.REPLACED, panel.GUIDANCE)
        assert runner._model_hash(req, None) != original_hash
        assert req == panel.request("1733", Path("C:/pt/not-run"))
        raise RuntimeError("interrupted turn")
    assert working_plan.instructions() == base
    assert runner._model_hash(req, None) == original_hash
    assert len(panel.ORDER) == 8
    assert len(panel.ORDER) * panel.ROW_CAP == panel.CAP
    for case in panel.TASKS:
        rows = [(a, n) for c, a, n in panel.ORDER if c == case]
        assert sorted(rows) == [("A", 1), ("A", 2), ("B", 1), ("B", 2)]
        assert rows[0][0] != rows[2][0]


@pytest.mark.parametrize("arm", ["A", "B"])
def test_mock_reaches_evaluation_and_every_segment_gets_only_selected_guidance(
    tmp_path, monkeypatch, arm,
):
    monkeypatch.setattr(runner.DockerProbeSandbox, "preflight", lambda self, **kw: self.identity)
    root = tmp_path / arm
    req = panel.request("1733", root, mock=True)
    with panel.arm_instructions(arm):
        result = runner.run_dev(req)
    run = result["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["evaluator"]["safety_state"] == "NOT_RUN"
    journal = DevJournal(root, run["run_id"])
    store = ArtifactStore(root / "artifacts")
    turns = [e["payload"] for e in journal.events() if e["event_type"] == "turn_started"]
    assert turns
    for turn in turns:
        items = runner._load_active_model_input(turn, store, context_policy="segmented-v1")
        system = items[0]["content"]
        assert (panel.GUIDANCE in system) == (arm == "B")
        assert (panel.REPLACED in system) == (arm == "A")
    actions = [e["payload"]["result"]["tool"] for e in journal.events()
               if e["event_type"] == "action_finished"]
    assert "replace_text" in actions and "run_check" in actions and "finish_task" in actions


def prepared(tmp_path, monkeypatch):
    root = tmp_path / "panel"
    root.mkdir()
    monkeypatch.setattr(panel, "LIVE", tmp_path / "live")
    monkeypatch.setattr(panel, "validate", lambda *args: {})
    monkeypatch.setattr(runner, "_require_tracked_clean_paths", lambda *args: None)
    panel.save(root, "authorization.json", {"approved": True, "human_message": "unit fixture",
                                             "packet_hash": "frozen"})
    receipt = {"test": "preflight"}
    panel.save(root, "preflight.json", receipt)
    DevJournal(root, "run_dev_positivepanel").append("preflight_passed", {
        "packet_hash": "frozen", "receipt_hash": sha256_json(receipt)})
    return root


def test_missing_exact_approval_cannot_dispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(panel, "validate", lambda *args: {})
    monkeypatch.setattr(runner, "run_dev", lambda *args: pytest.fail("dispatch"))
    with pytest.raises(ContractError, match="approval required"):
        panel.run(tmp_path, "frozen")


def test_uncertainty_stops_all_rows_and_disallows_restart(tmp_path, monkeypatch):
    root = prepared(tmp_path, monkeypatch)
    seen = []

    def uncertain(req):
        seen.append(req)
        return {"cost_nanos": 0, "runs": [{"terminal": "PROVIDER_TIMEOUT_OR_UNKNOWN"}]}

    monkeypatch.setattr(runner, "run_dev", uncertain)
    monkeypatch.setattr(panel, "settled", lambda *args: False)
    result = panel.run(root, "frozen")
    assert len(seen) == result["completed"] == 1
    assert len(result["not_run"]) == 7 and not result["total_cost_known"]
    with pytest.raises(ContractError, match="no restart"):
        panel.run(root, "frozen")


def test_exact_row_caps_bound_invocation_and_order(tmp_path, monkeypatch):
    root = prepared(tmp_path, monkeypatch)
    seen = []

    def completed(req):
        seen.append((req.task.parent.name, req.max_cost_usd, working_plan.instructions()))
        return {"cost_nanos": panel.usd_to_nanos(panel.ROW_CAP)}

    monkeypatch.setattr(runner, "run_dev", completed)
    monkeypatch.setattr(panel, "settled", lambda *args: True)
    result = panel.run(root, "frozen")
    assert result["completed"] == 8 and result["not_run"] == []
    assert result["recorded_cost_nanos"] == panel.usd_to_nanos(panel.CAP)
    for actual, (case, arm, _) in zip(seen, panel.ORDER, strict=True):
        assert actual[0].endswith(case) and actual[1] == panel.ROW_CAP
        assert (panel.GUIDANCE in actual[2]) == (arm == "B")


def test_packet_tamper_rejected_before_source_checks(tmp_path):
    panel.save(tmp_path, "packet.json", {"scope": "tampered"})
    with pytest.raises(ContractError, match="packet changed"):
        panel.validate(tmp_path, "sha256:" + "0" * 64)


def test_authorization_for_other_packet_rejected(tmp_path, monkeypatch):
    root = prepared(tmp_path, monkeypatch)
    path = root / "authorization.json"
    approval = json.loads(path.read_bytes())
    approval["packet_hash"] = "other"
    path.write_text(json.dumps(approval), encoding="utf-8")
    with pytest.raises(ContractError, match="approval does not bind"):
        panel.run(root, "frozen")
