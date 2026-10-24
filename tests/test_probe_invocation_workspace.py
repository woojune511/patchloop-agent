"""Fresh launch identity controls using the real line collector, without Docker."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_probe_invocation import review

from patchloop.dev import probe_invocation, reproduction
from patchloop.sandbox import line_trace
from patchloop.util import sha256_bytes

SOURCE = "record_observation(observed_target()().value)"
WORKSPACE_SOURCE = '''import json, os, sys
from pathlib import Path
root = Path(reproduction_workspace())
assert reproduction_workspace() == str(root)
home = root / "home"
home.mkdir()
assert not (home / "cache").exists()
(root / "input.txt").write_text(os.environ["CONTENT"], encoding="utf-8")
os.environ["HOME"] = str(home)
os.environ["PYLINTHOME"] = str(home / os.environ["CACHE_NAME"])
if os.environ["CLI_ARGV"]:
    sys.argv = json.loads(os.environ["CLI_ARGV"])
target = observed_target(input_paths=[str(root / "input.txt")],
                         environment_keys=["HOME", "PYLINTHOME", "MODE"])
record_observation(target().value)
'''


def execute(root, *, source=SOURCE, fixed=False, traced=False,
            channel=probe_invocation.CHANNEL, environment=None):
    root.mkdir(parents=True, exist_ok=True)
    implementation = (
        "import os, sys\n"
        "def entry():\n"
        "    print(repr(sys.argv))\n"
        f"    return {fixed!r}\n"
    )
    (root / "public_api.py").write_bytes(implementation.encode())
    binding = {
        "case_id": "sha256:" + "c" * 64, "program_hash": sha256_bytes(source.encode()),
        "root_action_id": "before", "definition": {
            "entrypoint": "public_api.entry", "expected_json": "true",
            "reported_failure_json": "false", "observation_channel": channel,
        },
    }
    request = {"request_hash": "a" * 64, "files": [{
        "path": "public_api.py", "file_hash": sha256_bytes(implementation.encode()),
        "changed_lines": [3, 4],
    }]}
    host_argv = ["/opt/patchloop/probe_runner.py", "30"]
    if traced:
        host_argv.append("/opt/patchloop/line_request.json")
    # Match the wrapper's order: prepare collector, install host argv, start
    # tracing, then execute the same reproduction program in a fresh process.
    launcher = (
        "import runpy, sys\n"
        f"module=runpy.run_path({str(Path(line_trace.__file__).resolve())!r})\n"
        f"collector=module['LineTrace']({request!r}, {str(root)!r}) if {traced!r} else None\n"
        f"sys.argv={host_argv!r}\n"
        "if collector: collector.start()\n"
        "try:\n"
        f" exec({reproduction.program(source, binding)!r}, {{'__name__': '__main__'}})\n"
        "finally:\n"
        " if collector: collector.finish()\n"
    )
    process = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", "-c", launcher], cwd=root,
        env={**os.environ, "PYTHONPATH": str(root), "CONTENT": "original fixture",
             "MODE": "strict", "CACHE_NAME": "cache", "CLI_ARGV": "",
             **(environment or {})},
        capture_output=True, text=True, encoding="utf-8", timeout=10, check=False,
    )
    if traced:
        prefix = line_trace.marker(request).decode()
        reports = [json.loads(row[len(prefix):]) for row in process.stderr.split("\n")
                   if row.startswith(prefix)]
        assert len(reports) == 1
        assert reports[0]["files"][0]["status"] == "collected"
        assert reports[0]["files"][0]["executed"] == [3, 4]
    return reproduction.compare({
        "status": "passed" if process.returncode == 0 else "failed",
        "exit_code": process.returncode, "stdout": process.stdout, "stderr": process.stderr,
        "truncated": False, "timed_out": False, "cleanup_failed": False,
        "deadline_exhausted": False,
    }, binding)["reproduction"]


def remove_fixture(root):
    # Model a new sandbox at the same path by removing only this test's known
    # empty tree. Production never removes or reuses a prior execution's tree.
    workspace = root / "patchloop-case"
    (workspace / "input.txt").unlink()
    (workspace / "home").rmdir()
    workspace.rmdir()


@pytest.mark.parametrize("channel", [probe_invocation.CAPTURE_CHANNEL, probe_invocation.CHANNEL])
def test_tracing_toggle_changes_legacy_identity_but_not_fresh_target_argv(tmp_path, channel):
    before = execute(tmp_path, channel=channel)
    after = execute(tmp_path, channel=channel, fixed=True, traced=True)
    assert before["comparison"] == "mismatched"
    assert after["comparison"] == "matched"
    linked = review(before, after)
    if channel == probe_invocation.CHANNEL:
        assert linked["comparison_status"] == "mismatch_to_match"
        assert linked["evidence"]["status"] == "SUPPORTED"
        for value in (before, after):
            call = value["call_observation"]["calls"][0]
            assert call["argv"] == ["<patchloop-reproduction>"]
            assert call["capture"]["stdout"].strip() == repr(call["argv"])
    else:
        assert linked["comparison_status"] == "observed_call_or_setup_changed"
        assert linked["evidence"]["status"] == "UNKNOWN"
        assert len(before["call_observation"]["calls"][0]["argv"]) == 2
        assert len(after["call_observation"]["calls"][0]["argv"]) == 3


@pytest.mark.parametrize("argv", ["", '["pylint", "src/project"]'])
def test_stable_workspace_and_selected_home_survive_fresh_traced_replay(tmp_path, argv):
    before = execute(tmp_path, source=WORKSPACE_SOURCE, environment={"CLI_ARGV": argv})
    assert before["comparison"] == "mismatched", before
    root = tmp_path / "patchloop-case"
    assert (root / "input.txt").read_text() == "original fixture"
    variables = before["call_observation"]["calls"][0]["environment"]["variables"]
    assert variables["HOME"] == sha256_bytes(str(root / "home").encode())[7:]
    assert variables["PYLINTHOME"] == sha256_bytes(str(root / "home/cache").encode())[7:]
    remove_fixture(tmp_path)
    after = execute(tmp_path, source=WORKSPACE_SOURCE, fixed=True, traced=True,
                    environment={"CLI_ARGV": argv})
    assert after["comparison"] == "matched", after
    assert review(before, after)["comparison_status"] == "mismatch_to_match"
    assert probe_invocation.conditions(before["call_observation"]) == (
        probe_invocation.conditions(after["call_observation"]))
    assert after["call_observation"]["calls"][0]["argv"] == (
        json.loads(argv) if argv else ["<patchloop-reproduction>"])


@pytest.mark.parametrize("changed", [
    {"CONTENT": "changed fixture"}, {"MODE": "relaxed"}, {"CACHE_NAME": "another-cache"},
    {"CLI_ARGV": '["pylint", "other-target"]'},
])
def test_real_input_environment_and_authored_argv_drift_remain_visible(tmp_path, changed):
    before = execute(tmp_path, source=WORKSPACE_SOURCE,
                     environment={"CLI_ARGV": '["pylint", "original-target"]'})
    remove_fixture(tmp_path)
    after = execute(tmp_path, source=WORKSPACE_SOURCE, fixed=True, traced=True,
                    environment={"CLI_ARGV": '["pylint", "original-target"]', **changed})
    assert before["comparison"] == "mismatched" and after["comparison"] == "matched"
    linked = review(before, after)
    assert linked["comparison_status"] == "observed_call_or_setup_changed"
    assert linked["evidence"]["status"] == "UNKNOWN"
    if "CLI_ARGV" in changed:
        call = after["call_observation"]["calls"][0]
        assert call["argv"] == ["pylint", "other-target"]
        assert call["capture"]["stdout"].strip() == repr(call["argv"])


@pytest.mark.parametrize("occupied", ["file", "directory"])
def test_workspace_never_reuses_or_deletes_existing_contents(tmp_path, occupied):
    workspace = tmp_path / "patchloop-case"
    if occupied == "directory":
        workspace.mkdir()
        sentinel = workspace / "keep.txt"
    else:
        sentinel = workspace
    sentinel.write_text("preserve", encoding="utf-8")
    result = execute(tmp_path, source=WORKSPACE_SOURCE, fixed=True)
    assert result["comparison"] == "not_compared"
    assert not result["call_observation"]["calls"]
    assert sentinel.read_text() == "preserve"


@pytest.mark.parametrize("channel,digest", [
    (probe_invocation.LEGACY_CHANNEL,
     "4403de14a66f4807e021ae64076e81fe4a6ac36202ef990998723f714ab6aeba"),
    (probe_invocation.ARGV_CHANNEL,
     "e040de896a21492a92fe92ad69dd2317dafc3246fe8ecffe56165a81ef4c9f3d"),
    (probe_invocation.CAPTURE_CHANNEL,
     "8c884396c60b1b7502a0ab557d63adc3b5c4a1eba28ab5de21d3a595842ac1d7"),
])
def test_legacy_observer_bytes_remain_frozen(channel, digest):
    assert sha256_bytes(probe_invocation.observer(channel).encode()) == "sha256:" + digest
    assert "def reproduction_workspace" not in probe_invocation.observer(channel)
