"""Executable caller linkage and before/after scope, using trusted local fixtures only."""
from __future__ import annotations

import copy
import os
import subprocess
import sys

import pytest

from patchloop.dev import probe_invocation, reproduction
from patchloop.probe_limits import EXECUTION_LIMIT_CHARS
from patchloop.util import sha256_bytes

SOURCE = '''import os, json
from pathlib import Path
p = str(Path("input.txt").resolve())
value = call_target(args=[p, json.loads(os.environ["FLAG"])],
                    input_paths=[p], environment_keys=["MODE"])
print("progress, not a verdict")
record_observation(value)
'''


def execute(root, *, implementation="return False", source=SOURCE, entrypoint="public_api.entry",
            content="fixture", flag="1", mode="stable", channel=probe_invocation.ARGV_CHANNEL,
            parameters="path, flag"):
    root.mkdir(parents=True)
    (root / "input.txt").write_text(content, encoding="utf-8")
    (root / "_impl.py").write_text(
        f"def actual({parameters}):\n    " + implementation + "\n", encoding="utf-8")
    (root / "public_api.py").write_text(
        "from _impl import actual as entry\n"
        "class Public:\n    def __init__(self, value):\n        self.value = value\n",
        encoding="utf-8")
    binding = {
        "case_id": "sha256:" + "c" * 64, "program_hash": sha256_bytes(source.encode()),
        "root_action_id": "before", "definition": {"entrypoint": entrypoint,
        "expected_json": "true", "observation_channel": channel},
    }
    wrapped = reproduction.program(source, binding)
    assert len(wrapped) <= EXECUTION_LIMIT_CHARS
    process = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", wrapped], cwd=root,
        env={**os.environ, "MODE": mode, "FLAG": flag, "PYTHONPATH": str(root)},
        capture_output=True, encoding="utf-8", timeout=10, check=False,
    )
    result = reproduction.compare({
        "status": "passed" if process.returncode == 0 else "failed",
        "exit_code": process.returncode, "stdout": process.stdout, "stderr": process.stderr,
        "truncated": False, "timed_out": False, "cleanup_failed": False,
        "deadline_exhausted": False, "execution_policy": {
            "image_digest": "fixture-image", "profile_hash": "fixture-profile",
            "dependencies": {"manifest_hash": "dependency-lock"},
            "thread_environment": {"OMP_NUM_THREADS": "1"}, "entrypoint": ["python"]},
    }, binding)
    return result["reproduction"]


def review(before, after):
    events = [{"event_type": "action_finished", "payload": {"result": {
        "tool": "run_probe", "action_id": action, "workspace_diff_hash": diff,
        "output": {"reproduction": value}}}}
        for action, diff, value in (("before", "D0", before), ("after", "D1", after))]
    return reproduction.review(events, "D1")["items"][0]


def test_public_alias_and_same_conditions_pair_across_scratch_paths(tmp_path):
    before = execute(tmp_path / "before")
    after = execute(tmp_path / "after", implementation="return True")
    assert before["comparison"] == "mismatched", before
    assert after["comparison"] == "matched", after
    actual = before["call_observation"]["calls"][0]
    assert actual["entrypoint"] == "public_api.entry"
    assert actual["resolved_entrypoint"] == "_impl.actual"
    assert actual["inputs"][0]["entries"] == 1
    linked = review(before, after)
    assert linked["comparison_status"] == "mismatch_to_match"
    assert linked["evidence"]["status"] == "SUPPORTED"
    assert linked["repair_success"] == "not_assessed"
    assert linked["baseline"]["execution_link"] == linked["latest"]["execution_link"]


@pytest.mark.parametrize("change", [{"content": "different"}, {"flag": "true"},
                                   {"flag": "1.0"}, {"mode": "different"}])
def test_changed_input_contents_argument_types_or_environment_cannot_pair(tmp_path, change):
    before = execute(tmp_path / "before")
    after = execute(tmp_path / "after", implementation="return True", **change)
    assert after["comparison"] == "matched"  # One observation, not a same-condition repair.
    linked = review(before, after)
    assert linked["comparison_status"] == "observed_call_or_setup_changed"
    assert linked["evidence"]["status"] == "UNKNOWN"


def test_environment_policy_and_relative_cwd_changes_cannot_pair(tmp_path):
    before = execute(tmp_path / "before")
    after = execute(tmp_path / "after", implementation="return True")
    for key in ("image_digest", "profile_hash", "dependencies", "thread_environment", "entrypoint"):
        changed = copy.deepcopy(after)
        changed["call_observation"]["execution_environment"][key] = "changed"
        assert review(before, changed)["evidence"]["status"] == "UNKNOWN"
    changed = copy.deepcopy(after)
    changed["call_observation"]["calls"][0]["cwd"] += "/subdirectory"
    assert review(before, changed)["comparison_status"] == "observed_call_or_setup_changed"


def test_public_constructor_and_caught_target_exception_are_observed(tmp_path):
    constructor = execute(tmp_path / "constructor", entrypoint="public_api.Public",
                          source="record_observation(call_target(args=[True]).value)")
    assert constructor["comparison"] == "matched", constructor
    source = '''try:
    call_target(args=["input.txt", 1], input_paths=["input.txt"])
except ValueError:
    record_observation(False)
else:
    record_observation(True)
'''
    before = execute(tmp_path / "before", source=source, implementation="raise ValueError('bug')")
    after = execute(tmp_path / "after", source=source, implementation="return True")
    assert before["call_observation"]["calls"][0]["outcome"] == "raised"
    assert review(before, after)["comparison_status"] == "mismatch_to_match"


def test_fixture_tree_absence_is_part_of_the_conditions(tmp_path):
    source = '''import os
from pathlib import Path
p = Path("fixture")
p.mkdir()
(p / "data").write_text("stable")
if os.environ["MODE"] == "present":
    (p / "optional").write_text("extra")
record_observation(call_target(args=[str(p.resolve()), 1], input_paths=[str(p.resolve())]))
'''
    before = execute(tmp_path / "before", source=source)
    same = execute(tmp_path / "same", source=source, implementation="return True")
    changed = execute(tmp_path / "changed", source=source, implementation="return True",
                      mode="present")
    assert review(before, same)["comparison_status"] == "mismatch_to_match"
    assert review(before, changed)["evidence"]["status"] == "UNKNOWN"
    assert before["call_observation"]["calls"][0]["inputs"][0]["entries"] == 2
    assert changed["call_observation"]["calls"][0]["inputs"][0]["entries"] == 3


@pytest.mark.parametrize(("source", "reason"), [
    ("from public_api import entry\nrecord_observation(entry('input.txt', 1))",
     "declared_call_unobserved_or_incomplete"),
    ("record_observation(True)\ncall_target(args=['input.txt', 1])",
     "observation_not_after_target_calls"),
    ("record_observation(call_target(args=['input.txt', object()]))",
     "declared_call_unobserved_or_incomplete"),
    ("record_observation(call_target(args=['input.txt', (1,)]))",
     "declared_call_unobserved_or_incomplete"),
    ("from pathlib import Path\nPath('input.txt').write_bytes(b'x'*1048577)\n"
     "record_observation(call_target(args=['input.txt', 1], input_paths=['input.txt']))",
     "declared_call_unobserved_or_incomplete"),
])
def test_missing_link_early_observation_and_large_input_remain_unknown(tmp_path, source, reason):
    result = execute(tmp_path / "run", source=source, implementation="return True")
    assert result["comparison"] == "not_compared", result
    assert result["reason"] == reason
