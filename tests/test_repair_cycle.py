"""Original-call feedback and completed reuse without provider or target execution."""
from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_exception_frame_repair import result as original_result

from diagnostics import repair_cycle as d
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import DevToolResult
from patchloop.errors import ContractError
from patchloop.util import sha256_json


class RecordedGateway:
    def __init__(self, journal, diff, *, failed=True, cleanup=True):
        self.journal, self.current_diff_hash = journal, diff
        self.failed, self.cleanup, self.dispatches = failed, cleanup, 0

    def execute(self, call):
        digest = sha256_json({"tool": call.name, "arguments": call.arguments})
        self.journal.append("action_started", {"action_id": call.action_id,
                            "input_hash": digest, "tool": call.name})
        self.dispatches += 1
        raw = original_result()
        raw.update(action_id=call.action_id, input_hash=digest, tool=call.name,
                   workspace_diff_hash=self.current_diff_hash)
        if self.failed:
            calls = raw["output"]["reproduction"]["call_observation"]["calls"]
            calls[0]["capture"]["stdout"] = "F0010"
        if not self.cleanup:
            raw["output"]["cleanup_failed"] = True
        raw["output"]["operator_advice"] = "PRIVATE_SENTINEL"
        value = DevToolResult.model_validate(raw)
        self.journal.append("action_finished", {"action_id": call.action_id,
                            "input_hash": digest, "result": value.model_dump(mode="json")})
        return value


def checker(tmp_path, monkeypatch, smoke_package, *, diff="one"):
    model = SimpleNamespace(current_diff_hash=diff, workspace=tmp_path / "candidate",
                            deadline=ExecutionDeadline.from_remaining(600))
    loaded = SimpleNamespace(original_arguments={"python_source": "original caller",
        "purpose": {"kind": "helper"}}, public=smoke_package.public)
    check = d.OriginalCallRecheck(loaded, model, tmp_path / "checks")
    baseline = RecordedGateway(check.base_journal, d.host.EMPTY_DIFF)
    candidate = RecordedGateway(check.journal, diff)
    monkeypatch.setattr(check, "_baseline_gateway", lambda: baseline)
    monkeypatch.setattr(check, "_gateway", lambda *_: candidate)
    return check, model, baseline, candidate


def test_failed_capture_reaches_feedback_and_exact_diff_reuses_at_finish(
    tmp_path, monkeypatch, smoke_package,
):
    check, _, base, candidate = checker(tmp_path, monkeypatch, smoke_package)
    assert check.needed_actions() == 2 and check.needed_original_seconds() == 120
    feedback = check.check()
    assert feedback["status"] == "failed" and feedback["candidate_diff_hash"] == "one"
    assert feedback["observed"]["calls"][0]["capture"]["stdout"] == "F0010"
    assert "PRIVATE_SENTINEL" not in str(feedback)
    assert check.needed_original_seconds() == 0
    assert check.needed_original_seconds(for_new_diff=True) == 60
    assert check.check()["candidate_receipt_reused"]
    assert check.current_receipts()[1]["workspace_diff_hash"] == "one"
    assert check.host_actions == 2 and base.dispatches == candidate.dispatches == 1


def test_new_diff_invalidates_success_and_retreat_to_clean_base_is_still_failure(
    tmp_path, monkeypatch, smoke_package,
):
    check, model, base, candidate = checker(tmp_path, monkeypatch, smoke_package)
    candidate.failed = False
    assert check.check()["status"] == "supported"
    model.current_diff_hash = candidate.current_diff_hash = "two"
    candidate.failed = True
    assert check.current_receipts() is None and check.needed_actions() == 1
    assert check.check()["status"] == "failed"
    model.current_diff_hash = d.host.EMPTY_DIFF
    assert check.check()["status"] == "failed"
    assert check.needed_actions() == 0 and base.dispatches == 1 and candidate.dispatches == 2


def test_completed_receipts_survive_controller_reconstruction(tmp_path, monkeypatch, smoke_package):
    check, model, _, _ = checker(tmp_path, monkeypatch, smoke_package)
    first = check.check()
    recovered = d.OriginalCallRecheck(check.loaded, model, check.root)
    monkeypatch.setattr(recovered, "_gateway", lambda *_: pytest.fail("action redispatched"))
    monkeypatch.setattr(recovered, "_baseline_gateway", lambda: pytest.fail("base redispatched"))
    assert (recovered.check()["candidate_receipt"]["content_hash"]
            == first["candidate_receipt"]["content_hash"])
    assert recovered.host_actions == 2


def test_pending_replay_or_cleanup_failure_never_retries(tmp_path, monkeypatch, smoke_package):
    check, _, _, candidate = checker(tmp_path, monkeypatch, smoke_package)
    candidate.cleanup = False
    with pytest.raises(ContractError, match="execution aborted"):
        check.check()
    with pytest.raises(ContractError, match="capture incomplete"):
        check.check()
    assert candidate.dispatches == 1
    pending = check._call("pending")
    check.journal.append("action_started", {"action_id": pending.action_id,
                                           "input_hash": "unknown"})
    with pytest.raises(ContractError, match="unfinished action"):
        check.needed_actions(for_new_diff=True)


def test_recheck_quota_does_not_reset_per_edit(tmp_path, monkeypatch, smoke_package):
    check, model, _, candidate = checker(tmp_path, monkeypatch, smoke_package)
    for diff in ("one", "two", "three"):
        model.current_diff_hash = candidate.current_diff_hash = diff
        check.check()
    assert check.host_actions == 4
    model.current_diff_hash = candidate.current_diff_hash = "four"
    with pytest.raises(ContractError, match="allowance exhausted"):
        check.check()
    assert candidate.dispatches == 3


@pytest.mark.parametrize("changed", [False, True])
def test_final_public_checks_reuse_only_matching_original_input_and_diff(
    tmp_path, monkeypatch, smoke_package, changed,
):
    check, model, _, _ = checker(tmp_path, monkeypatch, smoke_package)
    check.check()
    pair = copy.deepcopy(check.current_receipts())
    if changed:
        pair[1]["input_hash"] = "different original program"
    model.public_task = smoke_package.public
    model.sandbox = model.probe_sandbox = None
    seen = []

    class HostGateway:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.current_diff_hash = "one"

        def execute(self, call):
            seen.append(call.name)
            assert call.name == "run_check"
            return DevToolResult(action_id=call.action_id, input_hash="check", tool=call.name,
                status="succeeded", workspace_diff_hash="one", output={"passed": True})

    class Manager:
        def __init__(self, *_, **__):
            pass

        def create(self, *_, **__):
            return Path(tmp_path / "base")

        @staticmethod
        def diff_summary(_):
            return SimpleNamespace(patch_hash=d.host.EMPTY_DIFF)

    monkeypatch.setattr(d.host, "DevToolGateway", HostGateway)
    monkeypatch.setattr(d.host, "WorkspaceManager", Manager)
    monkeypatch.setattr(d.host, "programs", lambda: {})
    if changed:
        with pytest.raises(ContractError, match="request changed"):
            d.host.public_checks(check.loaded, model, tmp_path / "final", original_receipts=pair)
        assert seen == []
    else:
        result = d.host.public_checks(check.loaded, model, tmp_path / "final",
                                      original_receipts=pair)
        assert not result["original_call"]["call1_F0010_resolved"]
        assert result["regression_passed"] and seen == ["run_check"]
