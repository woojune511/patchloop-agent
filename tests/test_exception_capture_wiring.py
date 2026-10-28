"""Trusted exception side channel keeps original observations and legacy bytes intact."""
from __future__ import annotations

import copy
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_dev_probe_sandbox import FakeProcess, backend, mock_launch, public_repo  # noqa: F401
from test_probe_invocation import inject_api

from patchloop.dev import probe_invocation, reproduction
from patchloop.sandbox import exception_frames, probes
from patchloop.util import sha256_bytes, sha256_json


def request(source="fixture", root=None):
    value = {
        "action_id": "probe", "source_hash": sha256_bytes(source.encode()),
        "execution_identity_hash": sha256_json({"run_id": "run", "action_id": "probe"}),
        "snapshot_hash": sha256_json("public snapshot"),
        "roots": {"workspace": str(root or "/workspace")}, "dependency_files": None,
        "report_limit_bytes": probes.EXCEPTION_REPORT_LIMIT_BYTES,
    }
    return {**value, "request_hash": sha256_json(value)}


def frame(req, *, calls=None, error=None):
    return probes.exception_marker(req) + json.dumps({
        "request_hash": req["request_hash"], "calls": calls or [], "error": error,
    }).encode() + b"\n"


def execute(root, *, broken=False):
    root.mkdir()
    (root / "public_api.py").write_text(
        "def entry():\n"
        "    try:\n"
        "        raise AttributeError('__enter__')\n"
        "    except AttributeError:\n"
        "        raise FileNotFoundError('missing initializer')\n", encoding="utf-8")
    source = "record_observation(observed_target()().value)"
    binding = {"case_id": "sha256:" + "c" * 64, "program_hash": sha256_bytes(source.encode()),
               "definition": {"entrypoint": "public_api.entry", "expected_json": "true",
                              "reported_failure_json": "false",
                              "observation_channel": probe_invocation.CHANNEL}}
    program = reproduction.program(source, binding)
    req = request(program, root)
    launcher = (
        "import runpy\n"
        f"module=runpy.run_path({str(Path(probes._WRAPPER))!r})\n"
        f"frames=runpy.run_path({str(Path(exception_frames.__file__))!r})\n"
        f"capture=module['ExceptionCapture']({req!r},frames)\n"
        + ("capture.frames.capture=lambda error: 1/0\n" if broken else "")
        + "try:\n"
        f" exec({inject_api(program)!r},{{'__name__':'__main__',"
        "'_patchloop_exception_capture':capture.capture})\n"
        "finally:\n"
        " capture.finish()\n"
    )
    process = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", launcher], cwd=root,
        env={**os.environ, "PYTHONPATH": str(root)}, capture_output=True, timeout=10, check=False)
    assert process.returncode == 0
    collector = probes._OutputCollector()
    collector.enable_exception_frames(req)
    collector.drain(io.BytesIO(process.stdout), "stdout")
    collector.drain(io.BytesIO(process.stderr), "stderr")
    stdout, stderr = collector.public_text()
    core = reproduction.compare({"status": "passed", "exit_code": 0,
                                  "stdout": stdout, "stderr": stderr,
                                  "truncated": False, "timed_out": False,
                                  "cleanup_failed": False, "deadline_exhausted": False}, binding)
    return core, probes.exception_feedback(req, collector.exception_report)


@pytest.mark.parametrize("broken", [False, True])
def test_real_chained_exception_hook_preserves_core_failure(tmp_path, broken):
    core, diagnostic = execute(tmp_path / "case", broken=broken)
    call = core["reproduction"]["call_observation"]["calls"][0]
    assert call["exception"] == {
        "type": "builtins.FileNotFoundError", "message": "missing initializer"}
    assert call["outcome"] == "raised" and call["capture"]["status"] == "complete"
    assert core["reproduction"]["comparison"] == "not_compared"
    if broken:
        assert diagnostic["status"] == "unavailable" and diagnostic["calls"] == []
    else:
        assert diagnostic["status"] == "collected"
        assert diagnostic["calls"][0]["exception"] == call["exception"]
        text = json.dumps(diagnostic["calls"][0]["details"])
        assert "AttributeError" in text and "FileNotFoundError" in text
        assert "public_api.py" in text and "file_hash" in text


def test_v4_observer_is_frozen_and_v5_fits_existing_observer_budget():
    old = probe_invocation.observer(probe_invocation.STABLE_CHANNEL)
    assert sha256_bytes(old.encode()) == (
        "sha256:2416bd836752828ab4d2d9d1183ecf9c6a0b7b1168fa7619b4f16fbd229ccee3")
    new = probe_invocation.observer(probe_invocation.CHANNEL)
    assert len(new) < 8_000 and "_patchloop_exception_capture" in new
    assert "_patchloop_exception_capture" not in old
    compile(new, "<observer>", "exec")
    binding = {"case_id": "sha256:" + "c" * 64, "definition": {
        "entrypoint": "a." + "b" * 198, "observation_channel": probe_invocation.CHANNEL}}
    compile(reproduction.program("pass", binding), "<bounded-observer>", "exec")


@pytest.mark.parametrize("payload", [b"x" * 40_000, b"not-json", b"{}"],
                         ids=["overflow", "invalid-json", "invalid-envelope"])
def test_diagnostic_overflow_or_invalid_payload_cannot_consume_core_output_budget(payload):
    req = request()
    collector = probes._OutputCollector()
    collector.enable_exception_frames(req)
    wire = b"before\n" + probes.exception_marker(req) + payload + b"\nafter\n"
    collector.drain(io.BytesIO(wire), "stderr")
    assert collector.public_text() == ("", "before\nafter\n")
    assert not collector.limit_hit.is_set()
    assert probes.exception_feedback(req, collector.exception_report)["status"] == "unavailable"


@pytest.mark.parametrize("change", ["request", "duplicate", "call_id", "exception", "error"])
def test_unbound_or_malformed_side_report_is_unavailable(change):
    req = request()
    row = {"call_id": "call-1", "exception": {"type": "ValueError", "message": "bad"},
           "details": None}
    report = {"request_hash": req["request_hash"], "calls": [row], "error": None}
    if change == "request":
        report["request_hash"] = sha256_json("another action")
    elif change == "duplicate":
        report["calls"].append(copy.deepcopy(row))
    elif change == "call_id":
        row["call_id"] = []
    elif change == "exception":
        row["exception"] = {"message": "bad"}
    else:
        report["error"] = "collector_error"
    assert probes.exception_feedback(req, report)["status"] == "unavailable"


def test_sandbox_binds_diagnostic_helper_and_returns_separate_report(monkeypatch, public_repo):  # noqa: F811
    sandbox = backend(monkeypatch)
    source = "print('core')"
    seen = []

    def launch(command, **kwargs):
        mount = next(arg for arg in command if "target=/opt/patchloop," in arg)
        trusted = Path(mount.split("source=", 1)[1].split(",target=", 1)[0])
        req = json.loads((trusted / "exception_frames_request.json").read_bytes())
        assert req["source_hash"] == sha256_bytes(source.encode())
        assert req["action_id"] == "probe"
        assert sha256_bytes((trusted / "exception_frames.py").read_bytes()) == (
            sandbox.current_profile()["exception_frames_hash"])
        seen.append(req)
        return FakeProcess(stdout=b"core\n", stderr=frame(req))

    mock_launch(monkeypatch, launch)
    output = sandbox.run_probe(public_repo, "observe", source, deadline=None,
                               execution_identity={"run_id": "run", "action_id": "probe"})
    assert len(seen) == 1 and output["status"] == "passed"
    assert output["stdout"] == "core\n" and output["stderr"] == ""
    assert output["exception_diagnostics"]["status"] == "collected"
    assert output["exception_diagnostics"]["snapshot_hash"] == output["snapshot_hash"]
