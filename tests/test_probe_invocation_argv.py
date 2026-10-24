"""Bind a CLI caller's actual argv while preserving saved invocation-v1 replays."""
from __future__ import annotations

import copy
import json

import pytest
from test_probe_invocation import execute, review

from patchloop.dev import probe_invocation, reproduction
from patchloop.util import sha256_bytes

CLI_SOURCE = '''import json, os, sys
sys.argv = json.loads(os.environ["FLAG"])
try:
    call_target(input_paths=["input.txt"])
except SystemExit as error:
    record_observation(error.code == 0)
'''


def cli(root, *, argv=("pylint", "src/project"), code=1, **kwargs):
    return execute(root, source=CLI_SOURCE, parameters="", flag=json.dumps(argv),
                   implementation=f"raise SystemExit({code})", **kwargs)


def test_same_cli_argv_and_caught_system_exit_preserve_the_case(tmp_path):
    before = cli(tmp_path / "before")
    after = cli(tmp_path / "after", code=0)
    assert before["comparison"] == "mismatched", before
    assert after["comparison"] == "matched", after
    for observation in (before, after):
        trace = observation["call_observation"]
        assert trace["binding_method"] == probe_invocation.ARGV_CHANNEL
        call = trace["calls"][0]
        assert call["argv"] == ["pylint", "src/project"]
        assert call["arguments"] == {"args": [], "kwargs": {}}
        assert call["outcome"] == "raised"
    assert review(before, after)["comparison_status"] == "mismatch_to_match"
    assert review(before, after)["evidence"]["status"] == "SUPPORTED"


@pytest.mark.parametrize("argv", [
    ["pylint", "src"],
    ["another-cli", "src/project"],
    ["pylint", "src/project", "--errors-only"],
])
def test_changed_actual_argv_is_not_same_case_support(tmp_path, argv):
    before = cli(tmp_path / "before")
    after = cli(tmp_path / "after", argv=argv, code=0)
    assert before["binding"] == after["binding"]  # Same program, purpose and expectation.
    assert after["comparison"] == "matched", after
    linked = review(before, after)
    assert linked["comparison_status"] == "observed_call_or_setup_changed"
    assert linked["evidence"]["status"] == "UNKNOWN"
    assert linked["evidence"]["reason"] == "no_comparable_current_observation"


def test_argv_is_copied_before_the_target_mutates_it(tmp_path):
    result = execute(
        tmp_path / "run", source=CLI_SOURCE, parameters="",
        flag=json.dumps(["pylint", "src/project"]),
        implementation="import sys; sys.argv[:] = ['changed']; raise SystemExit(0)",
    )
    assert result["comparison"] == "matched", result
    assert result["call_observation"]["calls"][0]["argv"] == ["pylint", "src/project"]


@pytest.mark.parametrize("argv", [["pylint"] * 17, ["pylint", "x" * 257], ["pylint", 1]])
def test_incomplete_or_non_string_argv_cannot_receive_comparison_credit(tmp_path, argv):
    result = cli(tmp_path / "run", argv=argv, code=0)
    assert result["comparison"] == "not_compared", result
    assert result["reason"] == "declared_call_unobserved_or_incomplete"


def test_v2_requires_argv_and_v1_shape_stays_readable(tmp_path):
    result = cli(tmp_path / "run", code=0)
    call = result["call_observation"]["calls"][0]
    assert probe_invocation.valid_call(
        call, "public_api.entry", channel=probe_invocation.ARGV_CHANNEL)
    legacy = copy.deepcopy(call)
    legacy.pop("argv")
    assert probe_invocation.valid_call(legacy, "public_api.entry")
    assert probe_invocation.valid_call(
        legacy, "public_api.entry", channel=probe_invocation.LEGACY_CHANNEL)
    assert not probe_invocation.valid_call(
        legacy, "public_api.entry", channel=probe_invocation.ARGV_CHANNEL)
    assert not probe_invocation.valid_call(
        call, "public_api.entry", channel=probe_invocation.LEGACY_CHANNEL)


def test_legacy_channel_keeps_saved_observer_bytes_and_replay_semantics(tmp_path):
    assert sha256_bytes(probe_invocation.OBSERVER.encode()) == (
        "sha256:4403de14a66f4807e021ae64076e81fe4a6ac36202ef990998723f714ab6aeba")
    before = cli(tmp_path / "before", channel=probe_invocation.LEGACY_CHANNEL)
    after = cli(tmp_path / "after", channel=probe_invocation.LEGACY_CHANNEL, code=0)
    for observation in (before, after):
        trace = observation["call_observation"]
        assert trace["binding_method"] == probe_invocation.LEGACY_CHANNEL
        assert "argv" not in trace["calls"][0]
        assert probe_invocation.valid_call(trace["calls"][0], "public_api.entry")
    assert review(before, after)["comparison_status"] == "mismatch_to_match"
    assert review(before, after)["evidence"]["status"] == "SUPPORTED"
    saved = reproduction.program(CLI_SOURCE, before["binding"])
    assert sha256_bytes(saved.encode()) == (
        "sha256:fc995e369e859fa641847a336d4ea5f03ce3cd5315484f868dd8d3c657899412")
    assert saved.endswith(probe_invocation.OBSERVER)
    assert saved == reproduction.program(CLI_SOURCE, after["binding"])
