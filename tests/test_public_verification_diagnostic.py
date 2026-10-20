"""Synthetic controls validate judgment distinctions, not model repair quality."""
import json
from pathlib import Path

import pytest

from diagnostics import public_verification_diagnostic as diagnostic
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    root = tmp_path_factory.mktemp("publicjudgment") / "diagnostic"
    return root, diagnostic.run(root)


def test_independent_contract_detects_base_and_wrong_repairs_and_accepts_correct(result):
    _, report = result
    correct = report["controls"]["correct"]
    assert correct["comparison"]["status"] == "OBSERVED_FAIL_THEN_PASS"
    before, after = correct["phases"]
    assert before["judgment"] == {
        "execution": "COMPLETED", "readiness": "READY", "behavior": "FAIL",
    }
    assert after["judgment"] == {
        "execution": "COMPLETED", "readiness": "READY", "behavior": "PASS",
    }
    for name in ("raw_value", "constant"):
        for row in report["controls"][name]["phases"]:
            assert row["judgment"]["readiness"] == "READY"
            assert row["judgment"]["behavior"] == "FAIL"


@pytest.mark.parametrize("name,reason", [
    ("self_confirming", "EXPECTATION_MISMATCH"),
    ("wrong_entry", "ENTRY_POINT_MISMATCH"),
    ("caught_setup", "SETUP_ERROR"),
])
def test_passing_process_and_pytest_do_not_prove_behavior_when_check_is_unfit(result, name, reason):
    _, report = result
    control = report["controls"][name]
    assert control["comparison"]["status"] == "PASSED_BOTH"
    for row in control["phases"]:
        raw = json.loads(Path(row["receipt"]["path"]).read_text(encoding="utf-8"))
        assert raw["exit_code"] == 0
        assert row["judgment"] == {
            "execution": "COMPLETED", "readiness": reason, "behavior": "NOT_ASSESSED",
        }


def test_same_frozen_tests_and_pair_inputs_have_provenance_and_no_quality_claim(result):
    root, report = result
    test_hash = sha256_bytes(diagnostic.TEST_SOURCE.encode())
    for control in report["controls"].values():
        before, after = control["phases"]
        assert before["test_source_hash"] == after["test_source_hash"] == test_hash
        assert before["plan_hash"] == after["plan_hash"]
    events = DevJournal(root, "run_dev_publicjudgment").events()
    assert events[0]["event_type"] == "public_judgment_frozen"
    assert events[-1]["event_type"] == "public_judgment_closed"
    assert sum(e["event_type"] == "public_judgment_finished" for e in events) == 12
    freeze = events[0]["payload"]["artifact"]
    assert freeze["content_hash"] == report["freeze_hash"]
    assert sha256_bytes(Path(freeze["path"]).read_bytes()) == report["freeze_hash"]
    assert report["model_behavior_improvement"] == report["acceptance"] == "NOT_RUN"
    assert report["model_calls"] == 0 and not report["claim_eligible"]
    with pytest.raises(ContractError, match="fresh external root"):
        diagnostic.run(root)


def test_incomplete_execution_or_unusable_observation_is_never_pass():
    assert diagnostic.judge({"status": "TIMEOUT"}, "")["behavior"] == "NOT_ASSESSED"
    assert diagnostic.judge({"status": "COMPLETED"}, "") == {
        "execution": "COMPLETED", "readiness": "INVALID_OBSERVATION",
        "behavior": "NOT_ASSESSED",
    }
