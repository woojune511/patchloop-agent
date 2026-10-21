"""Capture, freeze and validate a new shared-budget verification-role allocation."""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from diagnostics import caller_uptake as prior
from diagnostics import portfolio_dev20, probe_recheck_panel
from diagnostics import verification_role as role
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
from patchloop.util import canonical_json, sha256_json

SPEC = ".agent/plans/verification-role-comparison.md"
MODEL, TASK, ROW_CAP = prior.MODEL, prior.TASK, prior.ROW_CAP
JOURNAL = "run_dev_verificationrole49"
SCHEMA = "verification-role-comparison-v1"
request, xml_receipt = common.request, common.xml_receipt
_ALLOCATION = common.allocation
_FREEZE, _VALIDATE = common.freeze, common.validate


def allocation(repeat_per_arm):
    require(type(repeat_per_arm) is int and repeat_per_arm == 3,
            "verification-role comparison is exactly three per arm")
    return _ALLOCATION(repeat_per_arm)


def bindings():
    repo = repository_root()
    names = [SPEC, "tests/test_verification_role.py", "tests/test_verification_role_grading.py",
             "tests/test_verification_state_grading.py", "tests/quick.txt"]
    names += [p.relative_to(repo).as_posix() for p in (repo / "diagnostics").rglob("*.py")]
    return {name: prior.file_ref(repo / name)["hash"] for name in sorted(names)}


def identity(live):
    repo = repository_root()
    runner._require_tracked_clean_paths(repo, runtime_content_paths() + list(bindings()))
    req = request(live, prior.ORDER[0])
    package, _, _, environment = probe_recheck_panel.environment(req)
    runner._live_source_preflight(req.task.parent, package)
    require(prior.invariants()["references"] == 2, "reference limit changed")
    return {
        "comparison": "verification-role-v1", "head": git_commit(),
        "runtime_hash": runtime_content_hash(), "implementation": bindings(),
        "role_contract": role.contract(), "invariants": prior.invariants(),
        "environment": environment, "public_hash": package.public_spec_hash,
        "task_hash": package.task_content_hash, "source": prior.file_ref(prior.SOURCE),
        "dependencies": prior.file_ref(common.DEPENDENCIES),
        "native_identity": portfolio_dev20.native_identity(), "native_input": prior.native_input(),
        "pricing": portfolio_dev20.price(),
        "prompts": {a: sha256_json(DEV_SYSTEM_PROMPT) for a in "AB"},
    }


def initial_pair(wires):
    left, right = (common.normalize_initial(wires[a]) for a in "AB")
    require(left == right, "initial repair requests must be identical except derived identities")
    return {"allowed_paths": [], "derived_segment_ids_checked": True, "tools_equal": True,
            "wire_bytes": {a: len(canonical_json(w).encode()) for a, w in wires.items()}}


@contextmanager
def configured():
    with (patch.object(common, "off", role), patch.object(common, "SPEC", SPEC),
          patch.object(common, "REDUCED_SPEC", SPEC), patch.object(common, "JOURNAL", JOURNAL),
          patch.object(common, "SCHEMA", SCHEMA),
          patch.object(common, "__doc__", __doc__),
          patch.object(common, "identity", identity),
          patch.object(common, "allocation", allocation),
          patch.object(common, "initial_pair", initial_pair),
          patch.object(common, "freeze", freeze), patch.object(common, "validate", validate)):
        yield


def capture(root, arm):
    with configured():
        return common.capture(root, arm)


def freeze(root, live, validation, *, repeat_per_arm=3):
    qualification(validation)
    with configured():
        return _FREEZE(root, live, validation, repeat_per_arm=repeat_per_arm)


def validate(root, digest):
    with configured():
        packet = _VALIDATE(root, digest)
    qualification(Path(packet["validation"]["path"]))
    return packet


def qualification(validation):
    """Never let generic panel validation omit the additional phase freeze gates."""
    value = json.loads(validation.read_bytes())
    gates = value.get("verification_role", {})
    require(gates.get("contract_hash") == sha256_json(role.contract()),
            "missing or changed verification-role qualification")
    for name in ("same_snapshot_capture", "historical_packet_replay", "resource_feasibility"):
        ref = gates.get(name)
        require(isinstance(ref, dict), "missing qualification: " + name)
        receipt = json.loads(prior.read_ref(ref))
        require(receipt.get("gate") == name and receipt.get("passed") is True
                and receipt.get("contract_hash") == gates["contract_hash"]
                and all(receipt.get(k) == value.get(k) and value.get(k) is not None
                        for k in ("head", "runtime_hash", "implementation"))
                and receipt.get("provider_calls") == receipt.get("input_count_calls") == 0,
                "qualification failed: " + name)
        require(receipt.get("evidence"), "qualification requires bound evidence: " + name)
        for evidence in receipt["evidence"]:
            prior.read_ref(evidence)
    return gates


if __name__ == "__main__":
    with configured():
        common.main(default_repeat=3, repeat_choices=(3,))
