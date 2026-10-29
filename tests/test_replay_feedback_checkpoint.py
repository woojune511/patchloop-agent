"""One synthetic registered replay; attachment must never execute it again."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import test_observation_exposure as fixtures

from diagnostics import replay_feedback_checkpoint as diagnostic
from diagnostics.checkpoint_continuation import inherited_reads
from diagnostics.observation_exposure import SyntheticProbe
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import sha256_json

source = fixtures.source


def branch_for(source, root):
    root.mkdir()
    return fixtures.branch_for(source, root, "B")


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    def forbidden(*_, **__):
        pytest.fail("provider, network or Docker execution is forbidden")
    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(runner, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", forbidden)
    monkeypatch.setattr(runner, "DockerProbeSandbox", forbidden)


@pytest.fixture
def captured(source, tmp_path):
    branch = branch_for(source, tmp_path / "capture")
    target = next(e["payload"]["action_id"] for e in branch.journal.events()
                  if e["event_type"] == "action_started" and e["payload"]["tool"] == "run_probe")
    probe = SyntheticProbe(branch.envelope, {diagnostic.ACTION_ID: "passed"})
    packet = diagnostic.capture(branch, target, probe_sandbox=probe)
    return branch, packet, probe


def test_capture_and_attach_preserve_raw_feedback_and_charge_only_one_action(
    source, tmp_path, captured,
):
    capture_branch, packet, probe = captured
    branch = branch_for(source, tmp_path / "attached")
    before = diagnostic._counters(branch)
    receipt = diagnostic.attach(branch, packet)
    assert probe.calls == [diagnostic.ACTION_ID]
    assert (receipt["target_executions"] == receipt["model_calls"]
            == receipt["accepted_mutations"] == 0)
    assert diagnostic._counters(branch) == (before[0], before[1] + 1, before[2])
    assert branch.journal.latest_active_elapsed_ms() == (
        packet["binding"]["original_active_elapsed_ms"] + packet["elapsed_ms"])
    assert branch.journal.latest_tool_batch_results()[0].model_dump(mode="json") == (
        diagnostic.packet_result(packet))
    assert diagnostic.packet_result(packet)["output"]["stdout"] == "SYNTHETIC_PROBE_ONLY"
    assert capture_branch.journal.events()[-1]["event_type"] == diagnostic.CAPTURED
    with pytest.raises(ContractError, match="unused checkpoint"):
        diagnostic.attach(branch, packet)
    with pytest.raises(ContractError, match="unused checkpoint"):
        diagnostic.capture(capture_branch, packet["binding"]["target_action_id"],
                           probe_sandbox=probe)
    assert probe.calls == [diagnostic.ACTION_ID]


def test_host_handoff_validates_old_calls_without_rewriting_host_feedback(
    source, tmp_path, captured, monkeypatch,
):
    _, packet, _ = captured
    branch = branch_for(source, tmp_path / "handoff")
    diagnostic.attach(branch, packet)
    events = branch.journal.events()
    before = branch.journal.path.read_bytes()
    inherited_cursor = runner.segments.cursor(events[:branch.inherited_events])
    assert runner.segments.cursor(events) != inherited_cursor
    # This fixture is not a completion checkpoint. Supply the compact-stage gate
    # and fresh binding explicitly while testing the real old-exchange validator.
    parent = DevJournal(source.root, source.run_id)
    cut = [e for e in parent.events() if e["event_type"] == "model_input_prepared"][-1]
    bundle = json.loads(Path(cut["payload"]["artifact"]["path"]).read_bytes())
    context = json.loads(Path(bundle["turn"]["context_artifact"]["path"]).read_bytes())
    context.update(workflow_gate="ready_to_submit", latest_tool_results=[
        diagnostic.packet_result(packet)])
    monkeypatch.setattr(runner.segments, "active", lambda *a, **k: (
        {"cursor": inherited_cursor}, None))
    original = runner._build_latest_exchange
    received = []

    def checked(**kwargs):
        received.append([r.action_id for r in kwargs["latest_tool_results"]])
        assert json.loads(kwargs["context"])["latest_tool_results"] == [
            diagnostic.packet_result(packet)]
        return original(**kwargs)

    with patch.object(runner, "_build_latest_exchange", checked), inherited_reads(branch), \
            diagnostic.host_handoff(branch, packet):
        assert runner.segments.cursor(events) == inherited_cursor
        runner._build_latest_exchange(journal=branch.journal, artifact_store=branch.store,
            context=json.dumps(context),
            latest_tool_results=branch.journal.latest_tool_batch_results())
        with pytest.raises(ContractError, match="compact completion"):
            runner._build_latest_exchange(journal=branch.journal, artifact_store=branch.store,
                context=json.dumps({**context, "workflow_gate": "needs_work"}),
                latest_tool_results=branch.journal.latest_tool_batch_results())
        newer = [*events, {"sequence": len(events) + 1,
                          "event_type": "turn_decision_recorded", "event_hash": "new",
                          "payload": {"turn_id": "new"}}]
        assert runner.segments.cursor(newer) == "new"
    assert received == [[packet["binding"]["target_action_id"]]]
    assert branch.journal.path.read_bytes() == before


def test_attach_rejects_wrong_candidate_before_adding_events(source, tmp_path, captured):
    _, packet, _ = captured
    branch = branch_for(source, tmp_path / "wrong")
    target = Path(branch.workspace) / "mini_data_utils/csvlite.py"
    target.write_text(target.read_text(encoding="utf-8") + "\n# Different candidate\n",
                      encoding="utf-8")
    before = branch.journal.path.read_bytes()
    with pytest.raises(ContractError, match="candidate/prefix/program"):
        diagnostic.attach(branch, packet)
    assert branch.journal.path.read_bytes() == before


def test_missing_execution_receipt_cannot_be_attached(source, tmp_path, captured):
    _, packet, _ = captured
    changed = copy.deepcopy(packet)
    changed["events"] = [e for e in changed["events"]
                         if e["event_type"] != "probe_execution_finished"]
    with pytest.raises(ContractError, match="unique execution receipt"):
        diagnostic._completed(changed["events"], changed["binding"],
                              diagnostic.RequestedTool.model_validate(changed["call"]))
    changed["packet_hash"] = sha256_json({k: v for k, v in changed.items()
                                         if k not in {"packet_hash", "capture_receipt_hash"}})
    branch = branch_for(source, tmp_path / "missing")
    with pytest.raises(ContractError, match="capture receipt"):
        diagnostic.attach(branch, changed)


def test_capture_rejects_incomplete_cleanup_and_cannot_retry(source, tmp_path):
    branch = branch_for(source, tmp_path / "uncertain")
    target = next(e["payload"]["action_id"] for e in branch.journal.events()
                  if e["event_type"] == "action_started" and e["payload"]["tool"] == "run_probe")

    class UncertainProbe(SyntheticProbe):
        def run_probe(self, *args, **kwargs):
            result = super().run_probe(*args, **kwargs)
            result["cleanup_failed"] = True
            return result

    probe = UncertainProbe(branch.envelope, {diagnostic.ACTION_ID: "passed"})
    with pytest.raises(ContractError, match="complete|cleanup"):
        diagnostic.capture(branch, target, probe_sandbox=probe)
    assert not any(e["event_type"] == diagnostic.CAPTURED for e in branch.journal.events())
    with pytest.raises(ContractError, match="unused checkpoint"):
        diagnostic.capture(branch, target, probe_sandbox=probe)
    assert probe.calls == [diagnostic.ACTION_ID]
