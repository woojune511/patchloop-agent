"""Fresh helper exception contract and frozen replay bytes, without Docker/provider."""

from __future__ import annotations

import ast

import pytest
from test_probe_invocation import execute

from patchloop.dev import probe_invocation, reproduction
from patchloop.util import canonical_json, sha256_bytes

EXIT_IMPLEMENTATION = (
    "import sys; print('public-out'); print('public-err', file=sys.stderr); raise SystemExit(7)"
)
EXIT_VALUE = {
    "value": None, "stdout": "public-out\n", "stderr": "public-err\n",
    "outcome": "system_exit", "exit_code": 7, "capture_status": "complete",
}


def test_explicit_system_exit_has_same_observation_as_automatic_capture(tmp_path):
    source = '''automatic = observed_target()()
explicit = observed_target(expected_exceptions=(SystemExit,))()
def observed(call):
    return {key: getattr(call, key) for key in (
        "value", "stdout", "stderr", "outcome", "exit_code", "capture_status")}
record_observation([observed(automatic), observed(explicit)])
'''
    result = execute(
        tmp_path / "execution", source=source, implementation=EXIT_IMPLEMENTATION, parameters="",
        channel=probe_invocation.CHANNEL, expected_json=canonical_json([EXIT_VALUE, EXIT_VALUE]),
    )
    assert result["comparison"] == "matched", result
    automatic, explicit = result["call_observation"]["calls"]
    assert automatic["target_started"] is explicit["target_started"] is True
    assert automatic["capture"] == explicit["capture"]
    assert automatic["exception"] == explicit["exception"] == {
        "type": "builtins.SystemExit", "message": "7",
    }
    # Explicit configuration stays auditable; equality here is behavior, not case identity.
    assert automatic["exception_policy"] == []
    assert explicit["exception_policy"] == ["builtins.SystemExit"]


def test_system_exit_subclass_is_supported_without_broadening_other_exceptions(tmp_path):
    source = '''import public_api
class PlannedExit(SystemExit):
    pass
public_api.PlannedExit = PlannedExit
call = observed_target(expected_exceptions=(PlannedExit,))()
record_observation(call.outcome == "system_exit" and call.exit_code == 7)
'''
    result = execute(
        tmp_path / "execution", source=source, parameters="", channel=probe_invocation.CHANNEL,
        implementation="import public_api; raise public_api.PlannedExit(7)",
    )
    assert result["comparison"] == "matched", result
    call, = result["call_observation"]["calls"]
    assert call["target_started"] is True
    assert call["capture"]["status"] == "complete"
    assert call["exception"]["type"].endswith(".PlannedExit")


@pytest.mark.parametrize("settings,raised,comparison", [
    ("(ValueError,)", "ValueError", "matched"),
    ("(ValueError,)", "TypeError", "not_compared"),
    ("(Exception,)", "ValueError", "not_compared"),
])
def test_ordinary_exceptions_still_require_an_exact_declared_class(
    tmp_path, settings, raised, comparison,
):
    result = execute(
        tmp_path / "execution", parameters="", channel=probe_invocation.CHANNEL,
        source=f"observed_target(expected_exceptions={settings})()\nrecord_observation(True)",
        implementation=f"raise {raised}('target failure')",
    )
    assert result["comparison"] == comparison, result
    call, = result["call_observation"]["calls"]
    assert call["target_started"] is True
    assert call["outcome"] == "raised"
    assert result["call_observation"]["incomplete"] is (comparison == "not_compared")


@pytest.mark.parametrize("settings", [
    "(BaseException,)", "(KeyboardInterrupt,)", "(GeneratorExit,)",
    "[SystemExit]", "SystemExit", "(SystemExit(7),)", "('SystemExit',)",
    "(SystemExit,) * 5",
])
def test_invalid_exception_settings_are_rejected_before_target_entry(tmp_path, settings):
    result = execute(
        tmp_path / "execution", parameters="", channel=probe_invocation.CHANNEL,
        source=f"observed_target(expected_exceptions={settings})()\nrecord_observation(True)",
        implementation="from pathlib import Path; Path('entered').touch(); return True",
    )
    assert result["comparison"] == "not_compared", result
    assert result["call_observation"]["calls"] == []
    assert result["call_observation"]["incomplete"] is True
    assert not (tmp_path / "execution/entered").exists()


def test_saved_v7_explicit_system_exit_remains_rejected(tmp_path):
    result = execute(
        tmp_path / "execution", parameters="", channel=probe_invocation.BEHAVIOR_CHANNEL,
        source="observed_target(expected_exceptions=(SystemExit,))()\nrecord_observation(True)",
        implementation="from pathlib import Path; Path('entered').touch(); raise SystemExit(7)",
    )
    assert result["comparison"] == "not_compared", result
    assert result["call_observation"]["calls"] == []
    assert not (tmp_path / "execution/entered").exists()


def test_v1_through_v7_observer_bytes_remain_frozen():
    hashes = {
        1: "4403de14a66f4807e021ae64076e81fe4a6ac36202ef990998723f714ab6aeba",
        2: "e040de896a21492a92fe92ad69dd2317dafc3246fe8ecffe56165a81ef4c9f3d",
        3: "8c884396c60b1b7502a0ab557d63adc3b5c4a1eba28ab5de21d3a595842ac1d7",
        4: "2416bd836752828ab4d2d9d1183ecf9c6a0b7b1168fa7619b4f16fbd229ccee3",
        5: "67052927eab7f0ab6dd72b7afad7cfdb3c32bf37befad1e46e14861392a47fe4",
        6: "67052927eab7f0ab6dd72b7afad7cfdb3c32bf37befad1e46e14861392a47fe4",
        7: "6cfee49fce5e6d805db2ab15d3a18cbe704717020e4fd41305ee04da3947c684",
    }
    for version, digest in hashes.items():
        observer = probe_invocation.observer(f"invoke-declared-call-v{version}")
        assert sha256_bytes(observer.encode()) == "sha256:" + digest


def test_fresh_observer_with_long_entrypoint_and_trace_stays_within_existing_limit():
    assert probe_invocation.BEHAVIOR_CHANNEL == "invoke-declared-call-v7"
    assert probe_invocation.CHANNEL == "invoke-declared-call-v8"
    binding = {"case_id": "sha256:" + "c" * 64, "definition": {
        "entrypoint": "x." + "a" * 198, "observation_channel": probe_invocation.CHANNEL,
    }}
    source = reproduction.program("", binding, call_path=True)
    ast.parse(source)
    assert len(source) - len(repr("")) <= 8000
