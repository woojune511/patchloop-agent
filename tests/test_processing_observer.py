"""Small v7 fixture/output and target-entry controls, without Docker or a model."""

from __future__ import annotations

import ast

import pytest
from test_probe_invocation import execute

from patchloop.dev import probe_call_capture, probe_invocation, reproduction
from patchloop.util import sha256_bytes


def run(root, source, implementation="return True", **kwargs):
    return execute(root / "execution", source=source, implementation=implementation,
                   parameters="", channel=probe_invocation.CHANNEL, **kwargs)


def test_generated_cache_growth_does_not_change_fixture_identity(tmp_path):
    source = '''import os
from pathlib import Path
root = Path(reproduction_workspace())
outputs = Path(reproduction_outputs())
assert root.parent == outputs.parent and root != outputs
assert reproduction_workspace() == str(root)
assert reproduction_outputs() == str(outputs)
(root / "input.py").write_text("import os\\n")
(outputs / "home").mkdir()
os.environ["HOME"] = str(outputs / "home")
os.environ["XDG_CACHE_HOME"] = str(outputs / "cache")
target = observed_target(input_paths=[str(root)], environment_keys=["HOME", "XDG_CACHE_HOME"])
first, second = target(), target()
record_observation(first.value and second.value)
'''
    result = run(tmp_path, source, 'import os; from pathlib import Path; '
                 'p = Path(os.environ["XDG_CACHE_HOME"]); p.mkdir(exist_ok=True); '
                 '(p / "project.stats").write_text("generated"); return True')
    assert result["comparison"] == "matched", result
    first, second = result["call_observation"]["calls"]
    assert first["inputs"] == second["inputs"]
    assert first["inputs"][0]["entries"] == 2
    assert first["environment"] == second["environment"]
    assert first["target_started"] is second["target_started"] is True
    assert (tmp_path / "execution/patchloop-outputs/cache/project.stats").read_text() == "generated"


@pytest.mark.parametrize("selected", [
    "outputs", "outputs / 'missing-child'", "outputs.parent", "outputs / 'child' / '..'",
])
def test_output_overlap_is_rejected_before_target_not_silently_filtered(tmp_path, selected):
    source = f'''from pathlib import Path
outputs = Path.cwd() / "patchloop-outputs"
try:
    observed_target(input_paths=[str({selected})])()
except ValueError:
    record_observation(True)
'''
    result = run(tmp_path, source, "raise AssertionError('must not execute')")
    assert result["comparison"] == "not_compared", result
    trace = result["call_observation"]
    call, = trace["calls"]
    assert trace["incomplete"] and call["target_started"] is False
    assert call["outcome"] == call["capture"]["status"] == "incomplete"
    assert call["exception"] == {
        "type": "builtins.ValueError", "message": "input path overlaps reproduction_outputs",
    }
    assert probe_invocation.valid_call(call, "public_api.entry", channel=probe_invocation.CHANNEL)


@pytest.mark.parametrize("directory", ["cache", "home"])
def test_legitimate_cache_and_home_input_mutations_remain_visible(tmp_path, directory):
    source = f'''import os
from pathlib import Path
root = Path(reproduction_workspace())
reproduction_outputs()
home = root / {directory!r}
home.mkdir()
(home / ".config").write_text("original")
os.environ["HOME"] = str(home)
target = observed_target(input_paths=[str(root)], environment_keys=["HOME"])
target()
target()
record_observation(True)
'''
    result = run(tmp_path, source, 'import os; from pathlib import Path; '
                 '(Path(os.environ["HOME"]) / ".config").write_text("changed"); return True')
    assert result["comparison"] == "matched", result
    first, second = result["call_observation"]["calls"]
    assert first["inputs"][0]["entries"] == second["inputs"][0]["entries"] == 3
    assert first["inputs"][0]["hash"] != second["inputs"][0]["hash"]
    assert first["environment"] == second["environment"]


@pytest.mark.parametrize("phase", ["signature", "snapshot", "resolution"])
def test_pretarget_failure_preserves_complete_row_with_false_entry(tmp_path, phase):
    setup = ''
    invocation = 'observed_target()(wrong=True)'
    options = {}
    if phase == "snapshot":
        setup = '''from pathlib import Path
root = Path(reproduction_workspace())
for i in range(65):
    (root / str(i)).touch()
'''
        invocation = 'observed_target(input_paths=[str(root)])()'
    elif phase == "resolution":
        invocation = 'observed_target()()'
        options["entrypoint"] = "public_api.missing"
    source = setup + f'''try:
    {invocation}
except (TypeError, ValueError, AttributeError):
    record_observation(True)
'''
    result = run(tmp_path, source, "raise AssertionError('must not execute')", **options)
    assert result["comparison"] == "not_compared", result
    trace = result["call_observation"]
    call, = trace["calls"]
    assert trace["incomplete"] and call["target_started"] is False
    assert call["outcome"] == call["capture"]["status"] == "incomplete"
    assert call["exception"]["type"] in {
        "builtins.TypeError", "builtins.ValueError", "builtins.AttributeError",
    }
    assert probe_invocation.valid_call(call, options.get("entrypoint", "public_api.entry"),
                                      channel=probe_invocation.CHANNEL)


@pytest.mark.parametrize("exception", ["ValueError('target failure')", "SystemExit(7)"])
def test_entered_exception_is_distinct_from_adapter_failure(tmp_path, exception):
    result = run(tmp_path, "observed_target()()\nrecord_observation(True)", f"raise {exception}")
    call, = result["call_observation"]["calls"]
    assert call["target_started"] is True
    assert call["outcome"] == ("system_exit" if exception.startswith("SystemExit") else "raised")
    assert call["capture"]["status"] == "complete"
    assert probe_invocation.valid_call(call, "public_api.entry", channel=probe_invocation.CHANNEL)


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_outputs_helper_never_reuses_or_deletes_existing_contents(tmp_path, kind):
    setup = ('p.mkdir(); (p / "keep.txt").write_text("keep")' if kind == "directory"
             else 'p.write_text("keep")')
    source = f'''from pathlib import Path
p = Path("patchloop-outputs")
{setup}
reproduction_outputs()
'''
    result = run(tmp_path, source)
    assert result["comparison"] == "not_compared"
    assert result["call_observation"]["calls"] == []
    sentinel = tmp_path / "execution/patchloop-outputs"
    if kind == "directory":
        sentinel /= "keep.txt"
    assert sentinel.read_text() == "keep"


def test_v7_size_with_optional_hooks_and_frozen_v5_v6_bytes():
    frozen = "sha256:67052927eab7f0ab6dd72b7afad7cfdb3c32bf37befad1e46e14861392a47fe4"
    for channel in (probe_invocation.DIAGNOSTIC_CHANNEL, probe_invocation.CANONICAL_CHANNEL):
        assert sha256_bytes(probe_invocation.observer(channel).encode()) == frozen
    assert probe_call_capture.behavior_observer(probe_invocation.OBSERVER_V2) == (
        probe_invocation.observer(probe_invocation.BEHAVIOR_CHANNEL))
    binding = {"case_id": "sha256:" + "c" * 64, "definition": {
        "entrypoint": "x." + "a" * 198, "observation_channel": probe_invocation.BEHAVIOR_CHANNEL,
    }}
    for call_path in (False, True):
        source = reproduction.program("", binding, call_path=call_path)
        ast.parse(source)
        assert len(source) - len(repr("")) <= 8000
