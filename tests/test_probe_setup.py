"""Separate supplied setup comparisons from behavior, without supplying an oracle."""

from __future__ import annotations

import copy
import io
import json
import threading
from pathlib import Path

import pytest
from test_dev_probe_sandbox import FakeProcess, backend, mock_launch, public_repo  # noqa: F401

from patchloop.sandbox import probe_setup, probes
from patchloop.sandbox.execution_feedback import marker as line_marker
from patchloop.util import sha256_bytes, sha256_json


def request(source="fixture"):
    value = {"source_hash": sha256_bytes(source.encode()),
             "execution_identity_hash": sha256_json({"run_id": "run", "action_id": "check"})}
    return {**value, "request_hash": sha256_json(value)}


def frame(req, checks, *, error=None):
    return probe_setup.marker(req) + json.dumps({
        "request_hash": req["request_hash"], "checks": checks, "error": error,
    }).encode() + b"\n"


def execute(source):
    req = request(source)
    checker = probe_setup.SetupChecks(req)
    stderr = []
    checker.write = lambda fd, block: stderr.append(block)
    namespace = {"check_setup": checker.check}
    failure = None
    try:
        exec(source, namespace)
    except Exception as exc:
        failure = exc
    finally:
        checker.finish()
    output = probes._OutputCollector(setup_request=req)
    output.drain(io.BytesIO(b"".join(stderr)), "stderr")
    return namespace, failure, probe_setup.public_feedback(req, output.setup_report)


def test_actual_construction_mismatch_stops_following_behavior():
    namespace, failure, feedback = execute(
        "settings = dict(mode='chosen')\n"
        "settings.update(dict(mode='inherited'))\n"
        "check_setup('mode', settings['mode'], 'chosen')\n"
        "behavior_reached = True\n"
    )
    assert isinstance(failure, probe_setup.SetupMismatchError)
    assert "behavior_reached" not in namespace
    assert feedback["status"] == "failed"
    assert feedback["checks"] == [{"label": "mode", "actual": "inherited",
                                   "expected": "chosen", "matched": False}]
    assert feedback["selection"] == "model_authored" and feedback["diagnostic_only"]


@pytest.mark.parametrize("source,expected,exception", [
    ("check_setup('mode', 'chosen', 'chosen')\nassert False, 'behavior'", "passed", AssertionError),
    ("assert False, 'ordinary assertion'", "not_checked", AssertionError),
    ("pass", "not_checked", type(None)),
    ("try:\n check_setup('mode', 'actual', 'intended')\nexcept AssertionError:\n pass\n"
     "behavior_reached = True", "failed", type(None)),
    ("check_setup('typed', True, 1)", "failed", probe_setup.SetupMismatchError),
    ("check_setup('typed', 1, 1.0)", "failed", probe_setup.SetupMismatchError),
])
def test_setup_status_does_not_classify_behavior_or_uncaught_exception(source, expected, exception):
    namespace, failure, feedback = execute(source)
    assert isinstance(failure, exception)
    assert feedback["status"] == expected
    if "behavior_reached" in source:
        assert namespace["behavior_reached"] is True


@pytest.mark.parametrize("value", [None, False, 17, 0.25, "setting"])
def test_plain_scalars_round_trip(value):
    _, failure, feedback = execute(f"check_setup('value', {value!r}, {value!r})")
    assert failure is None and feedback["status"] == "passed"
    assert feedback["checks"][0]["actual"] == value


@pytest.mark.parametrize("source,reason", [
    ("check_setup('', 1, 1)", "invalid_label"),
    ("check_setup('x' * 121, 1, 1)", "invalid_label"),
    ("check_setup('x', float('nan'), 1)", "unsupported_value"),
    ("check_setup('x', float('inf'), 1)", "unsupported_value"),
    ("check_setup('x', 1 << 256, 1)", "unsupported_value"),
    ("check_setup('x', 'x' * 257, 1)", "unsupported_value"),
    ("check_setup('x', [], [])", "unsupported_value"),
    ("class Unsafe:\n def __eq__(self, other):\n  raise RuntimeError('must not invoke')\n"
     "check_setup('object', Unsafe(), Unsafe())", "unsupported_value"),
    ("for i in range(17):\n check_setup(str(i), i, i)", "check_limit"),
    ("for i in range(16):\n check_setup('한' * 120, '글' * 256, '글' * 256)", "report_limit"),
    ("try:\n check_setup('', 1, 1)\nexcept ValueError:\n pass\n"
     "check_setup('valid later', 1, 1)", "invalid_label"),
])
def test_invalid_or_excessive_checks_are_unknown_even_when_error_caught(source, reason):
    _, failure, feedback = execute(source)
    assert failure is None or isinstance(failure, ValueError)
    assert feedback["status"] == "unknown" and feedback["reason"] == reason
    assert len(json.dumps(feedback).encode()) < 12_000


def test_threaded_comparisons_keep_each_row():
    checker = probe_setup.SetupChecks(request())
    threads = [threading.Thread(target=checker.check, args=(str(i), i, i)) for i in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=1)
        assert not thread.is_alive()
    assert len(checker.checks) == 6 and checker.error is None


@pytest.mark.parametrize("case", ["missing", "wrong_request", "duplicate", "partial", "large",
                                  "invalid_json", "invalid_row", "invalid_error", "extra_verdict"])
def test_frame_interference_and_malformed_payload_are_unknown(case):
    req = request()
    rows = [{"label": "x", "actual": 1, "expected": 1}]
    valid = frame(req, rows)
    raw = {
        "missing": b"ordinary stderr\n", "wrong_request": frame(request("other"), rows),
        "duplicate": valid + valid, "partial": valid[:-1],
        "large": probe_setup.marker(req) + b"x" * (probe_setup.MAX_REPORT_BYTES + 1) + b"\n",
        "invalid_json": probe_setup.marker(req) + b"{invalid}\n",
        "invalid_row": frame(req, [{"label": "x", "actual": [], "expected": []}]),
        "invalid_error": frame(req, rows, error={"bad": True}),
        "extra_verdict": frame(req, [{**rows[0], "matched": True}]),
    }[case]
    output = probes._OutputCollector(setup_request=req)
    output.drain(io.BytesIO(raw), "stderr")
    feedback = probe_setup.public_feedback(req, output.setup_report)
    assert feedback["status"] == "unknown" and not feedback["checks"]


def test_both_report_channels_keep_public_stderr_and_arbitrary_chunk_boundaries():
    req = request()
    line_req = {"request_hash": sha256_json("lines")}
    line_report = {"request_hash": line_req["request_hash"], "files": []}
    line_frame = line_marker(line_req) + json.dumps(line_report).encode() + b"\n"
    raw = b"before\n" + line_frame + b"middle\n" + frame(req, []) + b"after\n"

    class SmallChunks(io.BytesIO):
        def read(self, size=-1):
            return super().read(min(7, size))

    output = probes._OutputCollector(line_req, req)
    output.drain(SmallChunks(raw), "stderr")
    assert output.report == line_report
    assert probe_setup.public_feedback(req, output.setup_report)["status"] == "not_checked"
    assert output.public_text() == ("", "before\nmiddle\nafter\n")
    assert output.observed == 20 and not output.limit_hit.is_set()


@pytest.mark.parametrize("exit_code,flood,cleanup,expected", [
    (0, False, True, "failed"), (1, False, True, "failed"),
    (124, False, True, "unknown"), (0, True, True, "unknown"),
    (0, False, False, "unknown"),
])
def test_sandbox_binds_raw_source_and_disregards_incomplete_execution_reports(
    monkeypatch, public_repo, exit_code, flood, cleanup, expected,  # noqa: F811
):
    sandbox = backend(monkeypatch)
    source = "check_setup('mode', 'actual', 'expected')\n"
    seen = []

    def launch(command, **kwargs):
        mount = next(arg for arg in command if "target=/opt/patchloop," in arg)
        trusted = Path(mount.split("source=", 1)[1].split(",target=", 1)[0])
        req = json.loads((trusted / "setup_request.json").read_bytes())
        assert req["source_hash"] == sha256_bytes(source.encode())
        assert sha256_bytes((trusted / "probe_setup.py").read_bytes()) == (
            sandbox.current_profile()["setup_helper_hash"])
        rows = [{"label": "mode", "actual": "actual", "expected": "expected"}]
        process = FakeProcess(stdout=b"x" * 12_001 if flood else b"", stderr=frame(req, rows))
        process.returncode = exit_code
        seen.append(copy.deepcopy(req))
        return process

    mock_launch(monkeypatch, launch)
    cleanups = iter((True, cleanup))
    monkeypatch.setattr(sandbox, "_cleanup", lambda *args: next(cleanups))
    result = sandbox.run_probe(public_repo, "setup", source, deadline=None,
                               execution_identity={"run_id": "run", "action_id": "check"})
    assert len(seen) == 1 and result["source_hash"] == sha256_bytes(source.encode())
    assert result["setup_checks"]["status"] == expected
    assert result["setup_checks"]["request_hash"] == seen[0]["request_hash"]


def test_setup_helper_drift_after_preflight_prevents_launch(monkeypatch, public_repo, tmp_path):  # noqa: F811
    sandbox = backend(monkeypatch)
    changed = tmp_path / "changed-helper.py"
    changed.write_text("changed", encoding="utf-8")
    monkeypatch.setattr(probes, "_SETUP_WRAPPER", changed)
    with pytest.raises(probes.ContractError, match="trusted profile changed"):
        sandbox.run_probe(public_repo, "setup", "pass", deadline=None,
                          execution_identity={"run_id": "run", "action_id": "check"})
