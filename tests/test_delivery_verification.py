"""Delivery classification survives evaluation/recovery without becoming acceptance."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from test_dev_evaluation_resume import _completed_run, _forbid_execution
from test_repair import request_file as request_file

from patchloop import repair
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.contracts import DevTerminal
from patchloop.errors import RecoveryError


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("delivery verification tests must not access the network")
    monkeypatch.setattr("socket.socket.connect", forbidden)


def metadata(*, verified=False, case_status=None):
    return {
        "delivery_state": "cases_verified_delivery" if verified else "unverified_delivery",
        "original_verification": {
            "policy": "original-obligation-v1", "obligation_id": "public-obligation",
            "task_hash": "public-task-hash", "status": "verified" if verified else "unverified",
            "acquisition_status": "acquired" if verified else "not_attempted",
        },
        "submission_verification": {
            "status": case_status or ("cases_verified" if verified else "unverified"),
            "requirement_mapping": "model_authored_unverified", "repair_success": "not_assessed",
        },
    }


class Journal:
    """In-memory public-event fixture for receipt identity tests."""

    run_id = "run_dev_deliveryfixture"

    def __init__(self):
        self.records = []

    def events(self):
        return self.records

    def append(self, event_type, payload):
        event = {"sequence": len(self.records) + 1, "event_type": event_type, "payload": payload}
        self.records.append(event)
        return event

    def terminal(self):
        return next((event for event in self.records if event["event_type"] == "terminal"), None)

    def load_envelope(self):
        return SimpleNamespace(compaction_contract=None)


def delivery_fixture(tmp_path, *, verified=False, legacy=False):
    journal = Journal()
    store = ArtifactStore(tmp_path)
    patch = store.put_text("public candidate diff", "text/x-diff")
    envelope = SimpleNamespace(model_dump=lambda **kwargs: {"run_id": journal.run_id})
    finish = {"patch_hash": patch.content_hash, "changed_files": ["public.py"]}
    if not legacy:
        finish.update(metadata(verified=verified))
    journal.append("action_finished", {"result": {
        "tool": "finish_task", "action_id": "public-finish", "status": "succeeded",
        "workspace_diff_hash": patch.content_hash, "output": finish,
    }})
    journal.append("submission_recorded", {
        "patch_hash": patch.content_hash, "visible_check_diff_hash": patch.content_hash,
        "changed_files": finish["changed_files"],
    })
    return journal, store, envelope, patch, finish


@pytest.mark.parametrize("verified", [False, True])
def test_repair_receipt_and_recovery_keep_explicit_finish_delivery(tmp_path, verified):
    journal, store, envelope, patch, finish = delivery_fixture(tmp_path, verified=verified)
    delivered = repair.record_delivery(journal, store, envelope, patch, finish, 123)
    assert delivered["acceptance"] == "NOT_RUN"
    assert repair.delivery_metadata(delivered) == repair.delivery_metadata(finish)
    assert repair.load_delivery(journal, store, envelope) == delivered
    reference = Artifact.model_validate(delivered["public_verification"])
    receipt = json.loads(store.read_bytes(reference))
    assert repair.delivery_metadata(receipt) == repair.delivery_metadata(finish)
    assert receipt["finish"] == finish


def test_legacy_finish_and_delivery_keep_their_existing_absent_field_shape(tmp_path):
    journal, store, envelope, patch, finish = delivery_fixture(tmp_path, legacy=True)
    assert repair.delivery_metadata(finish) == {}
    delivered = repair.record_delivery(journal, store, envelope, patch, finish, 123)
    assert "delivery_state" not in delivered
    assert "original_verification" not in delivered
    assert repair.load_delivery(journal, store, envelope) == delivered


@pytest.mark.parametrize("field", ["delivery_state", "original_verification"])
def test_incomplete_explicit_delivery_metadata_is_not_treated_as_legacy(field):
    value = metadata()
    del value[field]
    with pytest.raises(RecoveryError, match="explicit delivery"):
        repair.delivery_metadata(value)


def test_case_success_without_acquired_original_obligation_stays_unverified():
    value = metadata(case_status="cases_verified")
    assert repair.delivery_metadata(value)["delivery_state"] == "unverified_delivery"
    value["delivery_state"] = "cases_verified_delivery"
    with pytest.raises(RecoveryError, match="differs from recorded"):
        repair.delivery_metadata(value)


def test_delivery_receipt_cannot_change_the_recorded_original_verification(tmp_path):
    journal, store, envelope, patch, finish = delivery_fixture(tmp_path)
    delivered = repair.record_delivery(journal, store, envelope, patch, finish, 123)
    data = json.loads(store.read_bytes(Artifact.model_validate(delivered["public_verification"])))
    data["original_verification"]["acquisition_status"] = "setup_blocked"
    replacement = store.put_json(data)
    journal.records[-1]["payload"]["receipt"] = replacement.model_dump(mode="json")
    with pytest.raises(RecoveryError, match="invalid public repair delivery"):
        repair.load_delivery(journal, store, envelope)


@pytest.mark.parametrize("mismatch", ["patch", "workspace", "multiple_finishes"])
def test_recorded_delivery_is_bound_to_one_successful_candidate(tmp_path, mismatch):
    journal, _, _, patch, _ = delivery_fixture(tmp_path)
    selected_hash = patch.content_hash
    if mismatch == "patch":
        selected_hash = "another-candidate"
    elif mismatch == "workspace":
        journal.records[0]["payload"]["result"]["workspace_diff_hash"] = "another-candidate"
    else:
        journal.records.append(copy.deepcopy(journal.records[0]))
    with pytest.raises(RecoveryError, match="finish"):
        repair.recorded_delivery_metadata(journal.events(), patch_hash=selected_hash)


@pytest.mark.parametrize("acceptance", ["PASS", "FAIL"])
@pytest.mark.parametrize("verified", [False, True])
def test_public_result_does_not_replace_delivery_with_evaluator_acceptance(acceptance, verified):
    terminal = {
        "terminal": f"EVALUATOR_{acceptance}", "call_counts": {"model": 1, "tool": 1},
        "accepted_mutations": 1, "cost_nanos": 0, "evaluator": {"task_acceptance": acceptance},
        **metadata(verified=verified),
    }
    result = runner._public_result("run_dev_public", terminal)
    assert result["terminal"] == f"EVALUATOR_{acceptance}"
    assert result["evaluator"]["task_acceptance"] == acceptance
    assert repair.delivery_metadata(result) == repair.delivery_metadata(terminal)
    result["original_verification"]["status"] = "changed copy"
    assert terminal["original_verification"]["status"] != "changed copy"


def test_delivery_metadata_cannot_override_the_independent_terminal_or_acceptance():
    terminal = runner._terminal(
        journal=Journal(), terminal=DevTerminal.EVALUATOR_PASS, counters=runner._RunCounters(),
        cost_ledger=None, cost_start_nanos=0, hashes={},
        evaluator={"task_acceptance": "PASS"}, run_age_seconds=0, active_elapsed_ms=0,
        verification_metadata={**metadata(), "terminal": "EVALUATOR_FAIL",
                               "evaluator": {"task_acceptance": "FAIL"}},
    )
    assert terminal["terminal"] == "EVALUATOR_PASS"
    assert terminal["evaluator"] == {"task_acceptance": "PASS"}
    assert terminal["delivery_state"] == "unverified_delivery"


def test_evaluator_metadata_only_resume_keeps_unverified_delivery_even_when_acceptance_passes(
    tmp_path, monkeypatch,
):
    request, journal, _ = _completed_run(tmp_path, monkeypatch, outcome="pass")
    finish = next(e["payload"]["result"]["output"] for e in journal.events()
                  if e["event_type"] == "action_finished"
                  and e["payload"]["result"]["tool"] == "finish_task"
                  and e["payload"]["result"]["status"] == "succeeded")
    assert finish["delivery_state"] == "unverified_delivery"
    monkeypatch.setattr(runner, "_run_one_locked", _forbid_execution)
    monkeypatch.setattr(runner.EvaluationEngine, "evaluate", _forbid_execution)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["evaluator"]["task_acceptance"] == "PASS"
    assert result["delivery_state"] == "unverified_delivery"
    assert repair.delivery_metadata(result) == repair.delivery_metadata(finish)
    assert repair.delivery_metadata(journal.terminal()["payload"]) == (
        repair.delivery_metadata(finish)
    )
    before = journal.path.read_bytes()
    assert runner.run_dev(request)["runs"][0] == result
    assert journal.path.read_bytes() == before


def test_public_repair_result_exposes_unverified_delivery_without_acceptance(request_file):
    request = repair.load_repair_request(request_file)
    result = repair.run_repair(request)["runs"][0]
    assert result["terminal"] == "PATCH_READY"
    assert result["acceptance"] == "NOT_RUN" and result["evaluator"] is None
    assert result["delivery_state"] == "unverified_delivery"
    assert repair.delivery_metadata(result["delivery"]) == repair.delivery_metadata(result)
