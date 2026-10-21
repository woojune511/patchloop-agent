"""Reuse the validated packet format for a distinct purpose/channel comparison."""
from __future__ import annotations

import copy
import subprocess
from contextlib import contextmanager
from unittest.mock import patch

from diagnostics import caller_uptake as prior
from diagnostics import portfolio_dev20, probe_recheck_panel
from diagnostics import probe_purpose_control as control
from diagnostics import verification_state_panel as common
from diagnostics.positive_verification_panel import require
from patchloop.dev import runner
from patchloop.dev.model import DEV_SYSTEM_PROMPT
from patchloop.runtime import (
    git_commit,
    repository_root,
    runtime_content_hash,
    runtime_content_paths,
)
from patchloop.util import canonical_json, sha256_bytes

SPEC = ".agent/plans/probe-purpose-comparison.md"
MODEL, TASK, ROW_CAP = prior.MODEL, prior.TASK, prior.ROW_CAP
JOURNAL = "run_dev_probepurpose46"
request = common.request
xml_receipt = common.xml_receipt
_ALLOCATION = common.allocation


def allocation(repeat_per_arm):
    require(type(repeat_per_arm) is int and repeat_per_arm == 3,
            "purpose comparison is exactly three per arm")
    return _ALLOCATION(repeat_per_arm)


def bindings():
    repo = repository_root()
    names = [SPEC, "tests/test_probe_purpose_comparison.py", "tests/test_probe_purpose.py",
             "tests/test_verification_state_grading.py", "tests/quick.txt"]
    names += [p.relative_to(repo).as_posix() for p in (repo / "diagnostics").rglob("*.py")]
    return {name: prior.file_ref(repo / name)["hash"] for name in sorted(names)}


def identity(live):
    repo = repository_root()
    runner._require_tracked_clean_paths(repo, runtime_content_paths() + list(bindings()))
    require(not subprocess.check_output(
        ["git", "diff", control.BASE, "--name-only", "--", "patchloop", "tasks",
         "pyproject.toml", "uv.lock", "docker"], cwd=repo, text=True).strip(),
        "common product runtime changed")
    req = request(live, prior.ORDER[0])
    package, _, _, environment = probe_recheck_panel.environment(req)
    runner._live_source_preflight(req.task.parent, package)
    prompt = sha256_bytes(DEV_SYSTEM_PROMPT.encode())
    return {
        "comparison": "probe-purpose-v1", "head": git_commit(),
        "runtime_hash": runtime_content_hash(), "implementation": bindings(),
        "invariants": prior.invariants(), "environment": environment,
        "public_hash": package.public_spec_hash, "task_hash": package.task_content_hash,
        "source": prior.file_ref(prior.SOURCE),
        "dependencies": prior.file_ref(common.DEPENDENCIES),
        "native_identity": portfolio_dev20.native_identity(), "native_input": prior.native_input(),
        "pricing": portfolio_dev20.price(), "prompts": {a: prompt for a in "AB"},
    }


def initial_pair(wires):
    left, right = (common.normalize_initial(wires[a]) for a in "AB")
    expected = copy.deepcopy(right)
    expected["tools"] = control.project_tools(right["tools"], "A")
    require(left == expected, "difference outside assigned probe schema/guidance")
    return {"allowed_paths": ["/tools/run_probe"], "derived_segment_ids_checked": True,
            "input_equal_after_segment_normalization": left["input"] == right["input"],
            "wire_bytes": {a: len(canonical_json(w).encode()) for a, w in wires.items()},
            "tools_equal": False}


@contextmanager
def configured():
    # Reuse the v2 envelope, receipts, skip-set check and immutable admission;
    # the explicit comparison discriminator binds this initializer and specification.
    with (patch.object(common, "off", control), patch.object(common, "SPEC", SPEC),
          patch.object(common, "REDUCED_SPEC", SPEC), patch.object(common, "JOURNAL", JOURNAL),
          patch.object(common, "identity", identity),
          patch.object(common, "allocation", allocation),
          patch.object(common, "initial_pair", initial_pair)):
        yield


def capture(root, arm):
    with configured():
        return common.capture(root, arm)


def freeze(root, live, validation, *, repeat_per_arm=3):
    with configured():
        return common.freeze(root, live, validation, repeat_per_arm=repeat_per_arm)


def validate(root, digest):
    with configured():
        return common.validate(root, digest)


if __name__ == "__main__":
    with configured():
        common.main()
