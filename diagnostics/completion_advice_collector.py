"""Manifest-bound advice ablation using the existing single-use cost collector."""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from diagnostics import post_edit_budget_continuation as base
from diagnostics.completion_advice_checkpoint import project
from diagnostics.completion_advice_continuation import advice_inputs
from diagnostics.decision_sampler import require
from patchloop.contracts import Artifact
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_json

IMPLEMENTATION = (
    "diagnostics/completion_advice_collector.py",
    "diagnostics/completion_advice_checkpoint.py",
    "diagnostics/completion_advice_continuation.py",
    ".agent/completion-advice-checkpoint.md",
)


@contextmanager
def configured():
    original_controls, original_run = base.controls, base.live.run_branch

    def controls(*args):
        plan = original_controls(*args)
        require(plan["verification_scope_cue"] is None, "scope cue would confound ablation")
        packet_path = Path(plan["packet"])
        packet = json.loads(packet_path.read_bytes())
        request = json.loads(base.ArtifactStore(packet_path.parent / "artifacts").read_bytes(
            Artifact.model_validate(packet["request"])))
        return {**plan, "schema": "completion-advice-continuation-v1",
                "intervention": "continuous-local-completion-advice-removal-v1",
                "treatment_first_request_hash": sha256_json(project(request)),
                "advice_implementation": {
                    p: sha256_bytes((repository_root() / p).read_bytes()) for p in IMPLEMENTATION}}

    def run(branch, *args):
        branch.selected = project(branch.selected)
        with advice_inputs(branch):
            return original_run(branch, *args)

    with patch.object(base, "controls", controls), patch.object(base.live, "run_branch", run):
        yield


def prepare(packet_path, packet_hash, env_file, result_root, output):
    base.runner._require_tracked_clean_paths(repository_root(), list(IMPLEMENTATION))
    with configured():
        return base.prepare(packet_path, packet_hash, env_file, result_root, output)


def collect(manifest_path, approved_hash, approved_cap_usd):
    base.runner._require_tracked_clean_paths(repository_root(), list(IMPLEMENTATION))
    with configured():
        return base.collect(manifest_path, approved_hash, approved_cap_usd)
