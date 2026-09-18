"""Actual model inputs retain setup observations without changing acceptance/replay."""

from __future__ import annotations

import copy
import json

import pytest
from test_dev_probe_observation_v28 import _result
from test_dev_probes import FakeProbe, probe_call
from test_probe_setup import execute

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, DevRunRequest
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.probe_observation import project_probe_result
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root


@pytest.mark.parametrize("status", ["failed", "passed", "not_checked", "unknown"])
def test_setup_comparisons_never_change_execution_or_behavior_verdict(status):
    result = _result(status="failed", collected=False)
    result["output"]["setup_checks"] = {"status": status, "checks": []}
    before = copy.deepcopy(result)
    projected = project_probe_result(result)
    observation = projected["observation"]
    assert observation["execution_status"] == "failed"
    assert observation["behavior_verdict"] == "not_assessed"
    assert observation["setup_check_observation"]["status"] == status
    assert projected["output"]["setup_checks"] == result["output"]["setup_checks"]
    assert result == before


def test_old_receipt_without_setup_helper_does_not_invent_observations():
    result = _result(status="passed", collected=False)
    assert "setup_check_observation" not in project_probe_result(result)["observation"]


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_actual_inputs_keep_setup_receipt_task_diff_check_and_closed_replay(
    tmp_path, monkeypatch, policy,
):
    source = (
        "actual = dict(mode='chosen')\nactual.update(dict(mode='inherited'))\n"
        "check_setup('mode', actual['mode'], 'chosen')\nraise RuntimeError('must not reach')\n"
    )

    class SetupProbe(FakeProbe):
        def run_probe(self, workspace, question, python_source, **kwargs):
            assert python_source == source
            output = super().run_probe(workspace, question, python_source, **kwargs)
            _, failure, output["setup_checks"] = execute(python_source)
            assert type(failure).__name__ == "SetupMismatchError"
            return output

    backend = SetupProbe()

    class ProbeThenMock(MockDevAdapter):
        def next_turn(self, context, tools):
            if backend.calls == 0:
                description = next(t["description"] for t in tools if t["name"] == "run_probe")
                assert "check_setup(label, actual, expected)" in description
                call = probe_call()
                call.arguments["python_source"] = source
                return DevModelTurn(tool_calls=[call])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", ProbeThenMock)
    request = DevRunRequest(
        provider="mock", model="mock-dev", enable_probes=True, context_policy=policy,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml", state_root=tmp_path,
    )
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    journal = DevJournal(tmp_path, result["run_id"])
    store = ArtifactStore(tmp_path / "artifacts")
    delivered = []
    for event in journal.events():
        if event["event_type"] != "turn_started":
            continue
        turn = event["payload"]
        items = runner._load_active_model_input(turn, store, context_policy=policy)
        state = reconstruct_state(items, context_policy=policy)
        context = json.loads(store.read_bytes(Artifact.model_validate(turn["context_artifact"])))
        for field in ("public_task", "current_diff", "visible_check_status"):
            assert state[field] == context[field]
        delivered.extend(json.loads(item["output"]) for item in items
                         if item.get("type") == "function_call_output"
                         and item["call_id"] == "probe-1")
    assert delivered
    for receipt in delivered:
        assert receipt["observation"]["setup_check_observation"]["status"] == "failed"
        assert receipt["observation"]["behavior_verdict"] == "not_assessed"
        assert receipt["output"]["setup_checks"]["checks"][0] == {
            "label": "mode", "actual": "inherited", "expected": "chosen", "matched": False,
        }
    before = journal.path.read_bytes()
    assert runner.run_dev(request.model_copy(update={"resume_run_id": result["run_id"]}))[
        "runs"][0] == result
    assert journal.path.read_bytes() == before and backend.calls == 1
