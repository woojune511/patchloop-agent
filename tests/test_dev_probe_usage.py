"""Real helper/pipe execution with mocked Linux isolation and Docker launch only."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest
from test_dev_probe_sandbox import backend, mock_launch, public_repo  # noqa: F401
from test_dev_probes import probe_call

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, DevRunRequest
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.sandbox import probes

# Execute the actual copied child wrapper/helper in a fresh Python process. Only
# Linux session/seccomp isolation is stubbed; this is not a Docker isolation test.
CHILD = """
import json
import runpy
import sys
from pathlib import Path

trusted, snapshot = map(Path, sys.argv[1:])
wrapper = runpy.run_path(str(trusted / 'probe_runner.py'))
setup_module = runpy.run_path(str(trusted / 'probe_setup.py'))
setup = setup_module['SetupChecks'](
    json.loads((trusted / 'setup_request.json').read_bytes()))
execute = wrapper['_execute_child']
execute.__globals__['_install_process_boundary'] = lambda: None
wrapper['os'].setsid = lambda: None
code = compile(sys.stdin.read(), '<patchloop-probe>', 'exec')
execute(code, import_paths=[str(snapshot)], setup=setup)
"""

PARTIAL_SOURCE = (
    "import time\n"
    "from types import SimpleNamespace\n"
    "settings = SimpleNamespace(mode='chosen')\n"
    "expected_mode = 'chosen'\n"
    "check_setup('mode', settings.mode, expected_mode)\n"
    "actual_value = settings.mode\n"
    "print({'stage': 'before_call', 'value': actual_value}, flush=True)\n"
    "time.sleep(60)\n"
    "print('AFTER_BLOCKING_CALL', flush=True)\n"
)
PARTIAL_STDOUT = "{'stage': 'before_call', 'value': 'chosen'}" + os.linesep


@pytest.fixture
def pipe_backend(monkeypatch):
    # A real timeout and real OS pipes, without waiting the production 30 seconds.
    monkeypatch.setattr(probes, "PROBE_TIMEOUT_SECONDS", 2)
    sandbox = backend(monkeypatch)
    popen = subprocess.Popen
    processes = []

    def launch(command, **kwargs):
        mounts = {}
        for i, arg in enumerate(command):
            if arg == "--mount":
                fields = dict(item.split("=", 1) for item in command[i + 1].split(",")
                              if "=" in item)
                mounts[fields["target"]] = fields["source"]
        # Deliberately omit -u: the example's flush=True must reach the OS pipe
        # before the child is killed, even with ordinary Python output buffering.
        process = popen(
            [sys.executable, "-I", "-B", "-c", CHILD,
             mounts["/opt/patchloop"], mounts["/workspace"]],
            **kwargs,
        )
        processes.append(process)
        return process

    mock_launch(monkeypatch, launch)
    yield sandbox, processes
    for process in processes:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=2)


@pytest.mark.parametrize("expected", [2, 1])
def test_injected_helper_uses_actual_source_and_stops_on_mismatch(
    pipe_backend, public_repo, expected,  # noqa: F811
):
    sandbox, processes = pipe_backend
    source = (
        "import module\n"
        f"check_setup('value', module.VALUE, {expected})\n"
        "print('AFTER_SETUP', flush=True)\n"
    )
    result = sandbox.run_probe(
        public_repo, "Does the constructed public value match?", source, deadline=None,
        execution_identity={"run_id": "run", "action_id": "helper"},
    )
    matched = expected == 2
    assert result["status"] == ("passed" if matched else "failed")
    assert result["exit_code"] == (0 if matched else 1)
    assert result["stdout"] == ("AFTER_SETUP" + os.linesep if matched else "")
    assert result["setup_checks"]["checks"] == [{
        "label": "value", "actual": 2, "expected": expected, "matched": matched,
    }]
    assert result["setup_checks"]["status"] == ("passed" if matched else "failed")
    assert len(processes) == 1 and processes[0].poll() is not None
    assert not result["cleanup_failed"]


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_timeout_keeps_emitted_observation_in_actual_inputs_and_closed_replay(
    tmp_path, monkeypatch, pipe_backend, policy,
):
    sandbox, processes = pipe_backend

    class ProbeThenMock(MockDevAdapter):
        def next_turn(self, context, tools):
            if not processes:
                description = next(t["description"] for t in tools if t["name"] == "run_probe")
                assert "without importing or redefining it" in description
                assert "check_setup('mode', settings.mode, expected_mode)" in description
                assert "print({'stage': 'before_call', 'value': actual_value}, flush=True)" in (
                    description)
                call = probe_call()
                call.arguments["python_source"] = PARTIAL_SOURCE
                return DevModelTurn(tool_calls=[call])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: sandbox)
    monkeypatch.setattr(runner, "MockDevAdapter", ProbeThenMock)
    request = DevRunRequest(
        provider="mock", model="mock-dev", enable_probes=True, context_policy=policy,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml", state_root=tmp_path,
    )
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["official"] is False
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
        output = receipt["output"]
        assert output["stdout"] == PARTIAL_STDOUT
        assert output["captured_output_bytes"] == len(PARTIAL_STDOUT.encode())
        assert output["timed_out"] and not output["truncated"]
        assert not output["cleanup_failed"] and not output["deadline_exhausted"]
        assert output["setup_checks"]["status"] == "unknown"
        # This probe precedes the first edit, so there are no changed-line targets.
        assert output["public_execution"]["status"] == "not_applicable"
        assert output["execution_policy"]["cleanup_status"] == "confirmed"
        assert receipt["observation"]["execution_status"] == "timeout"
        assert receipt["observation"]["behavior_verdict"] == "not_assessed"
    assert len(processes) == 1 and processes[0].poll() is not None
    before = journal.path.read_bytes()
    assert runner.run_dev(request.model_copy(update={"resume_run_id": result["run_id"]}))[
        "runs"][0] == result
    assert journal.path.read_bytes() == before and len(processes) == 1
