"""Shared API diagnostics through the copied child launcher, without Docker or providers."""

from __future__ import annotations

import ast
import copy
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_dev_probe_sandbox import FakeProcess, backend, mock_launch, public_repo  # noqa: F401
from test_probe_setup import request

from patchloop.dev import probe_invocation, reproduction
from patchloop.errors import ContractError
from patchloop.sandbox import probe_setup, probes
from patchloop.util import sha256_bytes


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("offline only"))


def execute(root, source, *, implementation="return True", channel=None):
    root.mkdir()
    trusted = root / "trusted"
    trusted.mkdir()
    for source_file, name in ((probes._WRAPPER, "probe_runner.py"),
                              (probes._SETUP_WRAPPER, "probe_setup.py"),
                              (probes._API_WRAPPER, "probe_api.py")):
        (trusted / name).write_bytes(source_file.read_bytes())
    (root / "public_api.py").write_text(
        "def entry():\n    " + implementation + "\n", encoding="utf-8")
    binding = {"case_id": "sha256:" + "c" * 64, "root_action_id": "fixture",
               "program_hash": sha256_bytes(source.encode()), "definition": {
                   "entrypoint": "public_api.entry", "expected_json": "true",
                   "observation_channel": channel or probe_invocation.CHANNEL}}
    wrapped = reproduction.program(source, binding)
    req = request(wrapped)
    # Only isolation installation is mocked; the copied launcher supplies the APIs.
    launcher = (
        "import runpy, sys\n"
        f"wrapper=runpy.run_path({str(trusted / 'probe_runner.py')!r})\n"
        f"setup_module=runpy.run_path({str(trusted / 'probe_setup.py')!r})\n"
        f"setup=setup_module['SetupChecks']({req!r})\n"
        "execute=wrapper['_execute_child']\n"
        "execute.__globals__['_install_process_boundary']=lambda:None\n"
        "wrapper['os'].setsid=lambda:None\n"
        f"execute(compile(sys.stdin.read(), '<patchloop-probe>', 'exec'), setup=setup, "
        f"import_paths=[{str(root)!r}])\n"
    )
    process = subprocess.run([sys.executable, "-I", "-B", "-c", launcher], cwd=root,
        input=wrapped.encode(), capture_output=True, check=False, timeout=10)
    collector = probes._OutputCollector(setup_request=req)
    collector.drain(io.BytesIO(process.stdout), "stdout")
    collector.drain(io.BytesIO(process.stderr), "stderr")
    stdout, stderr = collector.public_text()
    output = {"status": "passed" if process.returncode == 0 else "failed",
              "exit_code": process.returncode, "stdout": stdout, "stderr": stderr,
              "timed_out": False, "truncated": False, "cleanup_failed": False,
              "deadline_exhausted": False,
              "setup_checks": probe_setup.public_feedback(req, collector.setup_report)}
    return reproduction.compare(output, binding)


def test_missing_setup_arguments_are_precise_and_do_not_prove_target_absence(tmp_path):
    bad = execute(tmp_path / "bad", "check_setup('mode')\nobserved_target()()")
    feedback = bad["setup_checks"]
    assert bad["status"] == "failed" and feedback["status"] == "unknown"
    assert feedback["api_error"] == {
        "api": "check_setup", "parameter": None, "code": "missing_arguments",
        "missing_parameters": ["actual", "expected"],
    }
    assert "check_setup: missing required arguments: actual, expected" in bad["stderr"]
    trace = bad["reproduction"]["call_observation"]
    assert trace["calls"] == []
    assert trace["request_phase"] == {"settings_rejected": False, "target_entries": 0}
    assert bad["reproduction"]["comparison"] == "not_compared"
    good = execute(tmp_path / "good", """import inspect
assert list(inspect.signature(check_setup).parameters) == ['label', 'actual', 'expected']
check_setup('mode', 'chosen', 'chosen')
record_observation(observed_target()().value)
""")
    assert good["setup_checks"]["status"] == "passed"
    assert "api_error" not in good["setup_checks"]
    assert good["reproduction"]["comparison"] == "matched"


def test_dynamic_settings_report_field_and_limit_without_entering_target(tmp_path):
    bad = execute(tmp_path / "bad", """paths = [str(i) for i in range(7)]
observed_target(input_paths=paths)()
""", implementation="raise AssertionError('TARGET_REACHED')")
    assert "observed_target.input_paths: received 7 items; maximum 4" in bad["stderr"]
    assert "TARGET_REACHED" not in bad["stderr"]
    trace = bad["reproduction"]["call_observation"]
    assert trace["calls"] == [] and trace["incomplete"] is True
    assert trace["request_phase"] == {"settings_rejected": True, "target_entries": 0}
    assert bad["reproduction"]["comparison"] == "not_compared"
    good = execute(tmp_path / "good", """from pathlib import Path
root = Path(reproduction_workspace())
for i in range(7):
    (root / str(i)).write_text('input')
record_observation(observed_target(input_paths=[root])().value)
""")
    call, = good["reproduction"]["call_observation"]["calls"]
    assert call["inputs"][0]["entries"] == 8 and call["target_started"] is True
    assert good["reproduction"]["comparison"] == "matched"


@pytest.mark.parametrize("source,implementation", [
    ("observed_target()()", "raise TypeError('missing actual and expected')"),
    ("observed_target()()\ncheck_setup('mode')", "return True"),
])
def test_target_entry_is_not_erased_by_target_typeerror_or_later_setup_error(
    tmp_path, source, implementation,
):
    result = execute(tmp_path / "run", source, implementation=implementation)
    trace = result["reproduction"]["call_observation"]
    assert trace["request_phase"] == {"settings_rejected": False, "target_entries": 1}
    assert trace["calls"][0]["target_started"] is True
    assert result["reproduction"]["comparison"] == "not_compared"
    if source.endswith("()"):
        assert "api_error" not in result["setup_checks"]


def test_setup_error_report_is_bounded_and_malformed_details_remain_unknown():
    req = request()
    checker = probe_setup.SetupChecks(req)
    for i in range(16):
        checker.check(str(i), "x" * 200, "x" * 200)
    with pytest.raises(ValueError):
        checker.invoke("label")
    report = checker._report(checker.checks)
    assert len(json.dumps(report).encode()) <= probe_setup.MAX_REPORT_BYTES
    assert probe_setup.public_feedback(req, report)["status"] == "unknown"
    malformed = copy.deepcopy(report)
    malformed["api_error"]["missing_parameters"] = ["x" * 65]
    feedback = probe_setup.public_feedback(req, malformed)
    assert feedback["status"] == "unknown" and "api_error" not in feedback


@pytest.mark.parametrize("change", [
    {"error": []}, {"error": {}}, {"request_hash": "another-request"},
    {"checks": [{"wrong": "shape"}]},
])
def test_invalid_setup_envelopes_do_not_raise_or_deliver_unbound_api_errors(change):
    req = request()
    report = {"request_hash": req["request_hash"], "checks": [], "error": "api_usage",
              "api_error": {"api": "check_setup", "parameter": None,
                            "code": "missing_arguments", "missing_parameters": ["actual"]}}
    feedback = probe_setup.public_feedback(req, report | change)
    assert feedback["status"] == "unknown"
    assert feedback["reason"] == "missing_or_invalid_report"
    assert "api_error" not in feedback


def test_v10_bytes_stay_frozen_and_v11_optional_hooks_fit_8k():
    assert sha256_bytes(probe_invocation.observer(probe_invocation.CONSTRUCTION_CHANNEL)
                        .encode()) == (
        "sha256:879bba8fa12a28f3fd91818d810022f84e62eaf276aa99de426ed4064e568a30")
    for channel in probe_invocation.CONSTRUCTION_CHANNELS:
        binding = {"case_id": "sha256:" + "c" * 64, "definition": {
            "entrypoint": "x." + "a" * 198, "observation_channel": channel}}
        wrapped = reproduction.program("", binding, call_path=True)
        ast.parse(wrapped)
        assert len(wrapped) - len(repr("")) <= 8000


def test_api_contract_is_copied_and_hash_bound_in_sandbox_profile(
    monkeypatch, public_repo,  # noqa: F811
):
    sandbox = backend(monkeypatch)
    seen = []

    def launch(command, **kwargs):
        mount = next(arg for arg in command if "target=/opt/patchloop," in arg)
        trusted = Path(mount.split("source=", 1)[1].split(",target=", 1)[0])
        seen.append(sha256_bytes((trusted / "probe_api.py").read_bytes()))
        return FakeProcess()

    mock_launch(monkeypatch, launch)
    sandbox.run_probe(public_repo, "observe", "print(1)", deadline=None,
                      execution_identity={"run_id": "r", "action_id": "a"})
    assert seen == [sandbox.current_profile()["helper_api_hash"]]


def test_api_contract_drift_after_preflight_never_launches(
    monkeypatch, public_repo, tmp_path,  # noqa: F811
):
    copied = tmp_path / "probe_api.py"
    copied.write_bytes(probes._API_WRAPPER.read_bytes())
    monkeypatch.setattr(probes, "_API_WRAPPER", copied)
    sandbox = backend(monkeypatch)
    copied.write_bytes(copied.read_bytes() + b"\n# changed\n")
    monkeypatch.setattr(probes.subprocess, "Popen", lambda *a, **k: pytest.fail("launched"))
    with pytest.raises(ContractError, match="changed after preflight"):
        sandbox.run_probe(public_repo, "observe", "print(1)", deadline=None,
                          execution_identity={"run_id": "r", "action_id": "a"})
