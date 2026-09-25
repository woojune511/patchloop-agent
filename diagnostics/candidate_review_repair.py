"""Opt-in candidate reconsideration using the unchanged dev runner and evaluator.

An external experiment owns sampling, reviewer dispatch, budget and freeze checks.
This seam installs one saved public candidate before the first gateway is created.
It never resumes a source run, invents tool receipts, or supplies old evaluation data.
Run in a dedicated sequential process: the scoped hooks are process-local.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest.mock import patch

from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.errors import ContractError
from patchloop.repository import WorkspaceManager
from patchloop.util import canonical_json, sha256_json, sha256_text

FIELD = "candidate_reconsideration"
NOTICE = (
    "The workspace starts from a previously model-authored candidate for this same public task. "
    "Independently assess it, make any justified repair, verify the current candidate and submit "
    "using the normal tools. No previous check verdict or plan is inherited. The reference "
    "source is an exact-base snapshot, not current editable-source evidence; use registered "
    "reads for current code. An optional external model review is unverified advice about the "
    "initial candidate, not a test result or an instruction that must be followed. After edits "
    "its claims still concern that older candidate; validate your actual changes."
)
REVIEW_FIELDS = frozenset({
    "assessment", "evidence", "proposed_check", "recommended_change", "limitations",
})


def require(condition, message):
    if not condition:
        raise ContractError(message)


def validate_review(review):
    if review is not None:
        require(isinstance(review, dict) and set(review) == REVIEW_FIELDS,
                "review must contain only the public report fields")
        require(all(isinstance(v, str) and len(v) <= 20_000 for v in review.values()),
                "review fields must be bounded text")


def overlay(state, *, seed_hash, base_commit, source_code, review):
    validate_review(review)
    return {
        "instruction": NOTICE,
        "initial_candidate_hash": seed_hash,
        "reference_source": {"base_commit": base_commit, "source_code": source_code},
        "review": None if review is None else {
            "origin": "external_model_authored_unverified",
            "subject_patch_hash": seed_hash,
            "currency": ("matches_current_diff" if state["current_diff"]["patch_hash"] == seed_hash
                         else "older_candidate"),
            "report": review,
        },
    }


def run_seeded(request: DevRunRequest, *, seed_patch: str, seed_hash: str,
               base_commit: str, source_code: list, review: dict | None,
               experiment_hash: str, source_run_id: str, branch: str):
    """One fresh run; only supplemental review differs between comparison branches.

    The imported candidate consumes one of the usual four mutation slots. The normal
    result's accepted_mutations counts *new* accepted tool edits only; the seed is a
    separate diagnostic receipt. The evaluator still creates its own clean workspace.
    """
    require(request.repeat == 1 and request.resume_run_id is None,
            "diagnostic branches forbid repetition and resume")
    require(request.state_root is not None and not request.state_root.exists(),
            "diagnostic branch requires a new state root")
    require(bool(seed_patch) and sha256_text(seed_patch) == seed_hash, "seed hash mismatch")
    require(request.limits.max_accepted_mutations >= 1, "seed requires one mutation slot")
    validate_review(review)
    source_code, review = copy.deepcopy(source_code), copy.deepcopy(review)
    original_gateway, original_context = runner.DevToolGateway, runner._build_context
    initialized = []

    class SeededGateway(original_gateway):
        def __init__(self, **kwargs):
            require(not initialized, "only one agent gateway is allowed")
            workspace, journal = kwargs["workspace"], kwargs["journal"]
            deadline = kwargs.get("deadline")
            require(kwargs["public_task"].repository.base_commit == base_commit,
                    "seed base differs from public task")
            clean = WorkspaceManager.diff_summary(workspace, deadline=deadline)
            require(not clean.patch and not clean.untracked_files, "seed workspace is not clean")
            store = ArtifactStore(Path(request.state_root) / "artifacts")
            artifact = store.put_text(seed_patch, "text/x-diff")
            WorkspaceManager.apply_patch(workspace, Path(artifact.path), deadline=deadline)
            summary = WorkspaceManager.diff_summary(workspace, deadline=deadline)
            require(summary.patch_hash == seed_hash and not summary.untracked_files,
                    "installed candidate identity mismatch")
            super().__init__(**kwargs)
            require(self.accepted_mutations == 0 and not self.checks_by_diff,
                    "old mutation/check state was inherited")
            self.accepted_mutations = 1
            journal.append("diagnostic_candidate_seeded", {
                "official": False, "experiment_hash": experiment_hash, "branch": branch,
                "source_run_id": source_run_id, "seed_artifact": artifact.model_dump(mode="json"),
                "seed_hash": seed_hash, "base_commit": base_commit,
                "source_code_hash": sha256_json(source_code), "review_hash": sha256_json(review),
                "seed_mutation_slots": 1, "historical_actions_or_verdicts_imported": False,
                "resume_allowed": False,
            })
            initialized.append(journal.run_id)

    def context(**kwargs):
        state = json.loads(original_context(**kwargs))
        state[FIELD] = overlay(state, seed_hash=seed_hash, base_commit=base_commit,
                               source_code=source_code, review=review)
        return canonical_json(state)

    with patch.object(runner, "DevToolGateway", SeededGateway), \
            patch.object(runner, "_build_context", context):
        return runner.run_dev(request)
