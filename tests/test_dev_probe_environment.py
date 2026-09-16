"""Import guidance describes the real limits without claiming a behavior verdict."""

from __future__ import annotations

import copy
import json
import subprocess
import sys

import pytest
from test_dev_probe_observation_v28 import _result
from test_dev_probes import FakeProbe, probe_call

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, DevRunRequest
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.probe_observation import project_probe_result
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import canonical_json


def test_src_layout_and_missing_dependency_are_distinct_observed_failures(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "public_fixture.py").write_text(
        "import patchloop_probe_missing_dependency\n", encoding="utf-8",
    )
    for path, missing in ((tmp_path, "public_fixture"),
                          (source, "patchloop_probe_missing_dependency")):
        process = subprocess.run(
            [sys.executable, "-I", "-S", "-B", "-c",
             f"import sys; sys.path.insert(0, {str(path)!r}); import public_fixture"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        assert process.returncode == 1 and f"No module named '{missing}'" in process.stderr
        result = _result(status="failed", collected=False)
        result["output"]["stderr"] = process.stderr
        before = copy.deepcopy(result)
        observed = project_probe_result(result)["observation"]
        assert observed["environment_guidance"]["basis"] == "reported_import_error"
        assert observed["behavior_verdict"] == "not_assessed"
        assert missing not in canonical_json(observed)
        assert result == before


@pytest.mark.parametrize("status,stderr,stdout,expected", [
    ("failed", "ImportError: cannot import name 'value' from 'public_module'\n", "", True),
    ("failed", "ModuleNotFoundError: No module named 'module'\n", "", True),
    ("failed", "AssertionError: mismatch\n", "", False),
    ("failed", "  ImportError: quoted source\n", "", False),
    ("failed", "", "ModuleNotFoundError: printed example\n", False),
    ("passed", "ImportError: caught error\n", "", False),
    ("timeout", "ImportError: partial output\n", "", False),
    ("cleanup_failed", "ImportError: partial output\n", "", False),
])
def test_guidance_is_conditional_and_does_not_reclassify_the_receipt(
    status, stderr, stdout, expected,
):
    result = _result(status=status, collected=False)
    result["output"].update(stderr=stderr, stdout=stdout)
    projected = project_probe_result(result)
    assert ("environment_guidance" in projected["observation"]) is expected
    assert projected["observation"]["execution_status"] == (
        "completed" if status == "passed" else status)
    assert projected["observation"]["behavior_verdict"] == "not_assessed"
    assert projected["output"]["stderr"] == stderr
    assert projected["output"]["stdout"] == stdout


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_real_model_inputs_receive_guidance_and_keep_public_state_and_replay(
    tmp_path, monkeypatch, policy,
):
    class ImportFailure(FakeProbe):
        def run_probe(self, *args, **kwargs):
            output = super().run_probe(*args, **kwargs)
            output["stderr"] = "ModuleNotFoundError: No module named 'public_dependency'\n"
            return output

    backend = ImportFailure()

    class ProbeThenMock(MockDevAdapter):
        def next_turn(self, context, tools):
            if backend.calls == 0:
                description = next(t["description"] for t in tools if t["name"] == "run_probe")
                assert "sys.path.insert(0, '/workspace/src')" in description
                return DevModelTurn(tool_calls=[probe_call()])
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
    assert delivered and all(r["observation"]["environment_guidance"]["basis"] ==
                             "reported_import_error" for r in delivered)
    before = journal.path.read_bytes()
    assert runner.run_dev(request.model_copy(update={"resume_run_id": result["run_id"]}))[
        "runs"][0] == result
    assert journal.path.read_bytes() == before and backend.calls == 1
