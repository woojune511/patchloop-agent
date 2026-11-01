"""Actual callable shape and bounded binding failures, without providers or Docker."""

from __future__ import annotations

import ast
import copy

import pytest
from test_probe_invocation import execute

from patchloop.dev import probe_invocation, reproduction
from patchloop.util import sha256_bytes


def run(root, source, *, parameters="", implementation="return True", **kwargs):
    return execute(root, source=source, parameters=parameters, implementation=implementation,
                   channel=probe_invocation.SIGNATURE_CHANNEL, **kwargs)


def test_signature_is_actual_and_lazy_before_zero_argument_cli_call(tmp_path):
    result = run(tmp_path / "run", '''import sys
from pathlib import Path
target = observed_target()
assert target.signature() == "()"
assert not Path("entered").exists()
sys.argv = ["public-cli", "fixture.py"]
call = target()
record_observation(call.value == ["fixture.py"])
''', implementation="import sys; from pathlib import Path; Path('entered').touch(); "
                        "return sys.argv[1:]")
    assert result["comparison"] == "matched", result
    call, = result["call_observation"]["calls"]
    assert call["signature"] == "()" and call["bound_parameters"] == {}
    assert call["target_started"] is True and call["binding_error"] is False


@pytest.mark.parametrize("parameters,signature,good,bad", [
    ("", "()", "target()", "target(['fixture.py'])"),
    ("path, *, enabled=False", "(path, *, enabled=False)",
     "target('fixture.py', enabled=True)", "target('fixture.py', True)"),
])
def test_argument_binding_failure_is_pre_target_and_correct_call_can_execute(
    tmp_path, parameters, signature, good, bad,
):
    prefix = f"target = observed_target()\nassert target.signature() == {signature!r}\n"
    bad_result = run(
        tmp_path / "bad", prefix + bad, parameters=parameters,
        implementation="from pathlib import Path; Path('entered').touch(); return True",
    )
    call, = bad_result["call_observation"]["calls"]
    assert bad_result["comparison"] == "not_compared"
    assert call["signature"] == signature and call["binding_error"] is True
    assert call["target_started"] is False and call["bound_parameters"] is None
    assert call["exception"]["type"] == "builtins.TypeError"
    assert not (tmp_path / "bad/entered").exists()
    assert probe_invocation.valid_call(call, "public_api.entry")
    good_result = run(tmp_path / "good", prefix + f"record_observation({good}.value)",
                      parameters=parameters)
    assert good_result["comparison"] == "matched", good_result
    assert good_result["call_observation"]["calls"][0]["binding_error"] is False


def test_type_error_inside_target_is_not_a_binding_failure(tmp_path):
    result = run(tmp_path / "run", "observed_target()()",
                 implementation="raise TypeError('too many positional arguments')")
    call, = result["call_observation"]["calls"]
    assert call["signature"] == "()" and call["binding_error"] is False
    assert call["target_started"] is True and call["outcome"] == "raised"
    assert call["capture"]["status"] == "complete"


@pytest.mark.parametrize("unknown", ["unavailable", "oversized"])
def test_unavailable_or_oversized_signature_cannot_certify_binding_failure(tmp_path, unknown):
    parameters = "" if unknown == "unavailable" else "path='" + "x" * 300 + "'"
    setup = ("import public_api\npublic_api.entry.__signature__ = object()\n"
             if unknown == "unavailable" else "")
    result = run(tmp_path / "run", setup + '''target = observed_target()
assert target.signature() is None
target(1, 2)
''', parameters=parameters)
    call, = result["call_observation"]["calls"]
    assert call["signature"] is None and call["binding_error"] is False
    assert call["target_started"] is (unknown == "unavailable")
    assert result["comparison"] == "not_compared"


def test_snapshot_failure_is_not_a_binding_error_and_metadata_is_not_input_identity(tmp_path):
    result = run(tmp_path / "run", '''from pathlib import Path
output = reproduction_outputs()
target = observed_target(input_paths=[output])
assert target.signature() == "()"
target()
''')
    call, = result["call_observation"]["calls"]
    assert call["target_started"] is False and call["binding_error"] is False
    assert call["exception"]["type"] == "builtins.ValueError"
    before = probe_invocation.conditions(result["call_observation"])
    changed = copy.deepcopy(result["call_observation"])
    changed["calls"][0].update(signature="(new_shape)", binding_error=True)
    assert probe_invocation.conditions(changed) == before


def test_signature_marker_requires_well_formed_pre_target_typeerror(tmp_path):
    result = run(tmp_path / "run", "observed_target()(1)")
    call, = result["call_observation"]["calls"]
    for change in ({"signature": None}, {"signature": ""}, {"signature": "x" * 257},
                   {"binding_error": 1}, {"target_started": True},
                   {"bound_parameters": {}}, {"exception": None}):
        assert not probe_invocation.valid_call({**call, **change}, "public_api.entry")


def test_saved_v8_is_frozen_and_fresh_hooks_fit_the_same_allowance(tmp_path):
    old = probe_invocation.observer(probe_invocation.EXCEPTION_CHANNEL)
    assert sha256_bytes(old.encode()) == (
        "sha256:0be715b7add04b0b7ef125c1011b724f8a230c91550033dcd29295566a178583")
    legacy = execute(tmp_path / "legacy", source="observed_target()(1)", parameters="",
                     channel=probe_invocation.EXCEPTION_CHANNEL)
    call, = legacy["call_observation"]["calls"]
    assert "signature" not in call and "binding_error" not in call
    assert probe_invocation.valid_call(call, "public_api.entry")
    binding = {"case_id": "sha256:" + "c" * 64, "definition": {
        "entrypoint": "x." + "a" * 198,
        "observation_channel": probe_invocation.SIGNATURE_CHANNEL,
    }}
    source = reproduction.program("", binding, call_path=True)
    ast.parse(source)
    assert len(source) - len(repr("")) <= 8000
