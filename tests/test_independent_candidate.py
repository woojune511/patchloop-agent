from __future__ import annotations

import copy

import pytest
from test_candidate_review_repair import REPORT, request

from diagnostics import candidate_review_repair as seam
from diagnostics import independent_candidate as candidate
from patchloop.dev import runner
from patchloop.errors import ContractError
from patchloop.util import sha256_text


def arguments():
    return dict(seed_patch="seed", seed_hash=sha256_text("seed"), base_commit="a" * 40,
                source_code=[], review=None, experiment_hash="sha256:" + "b" * 64,
                source_run_id="run_dev_saved", branch="B",
                alternative={"patch": "alternative", "patch_hash": sha256_text("alternative"),
                             "base_commit": "a" * 40})


@pytest.mark.parametrize("kind", ["hash", "base", "empty", "verdict", "review",
                                  "completion", "comparison", "change", "feedback"])
def test_invalid_alternative_fails_before_model(tmp_path, monkeypatch, kind):
    kwargs = arguments()
    if kind == "hash":
        kwargs["alternative"]["patch_hash"] = sha256_text("tampered")
    elif kind == "base":
        kwargs["alternative"]["base_commit"] = "c" * 40
    elif kind == "empty":
        kwargs["alternative"] = {}
    elif kind == "verdict":
        kwargs["alternative"]["acceptance"] = "PASS"
    elif kind == "review":
        kwargs["review"] = REPORT
    elif kind == "completion":
        kwargs["completion_guidance_policy"] = "status-only-v1"
    elif kind == "comparison":
        kwargs["comparison_policy"] = "paired-observation-v1"
    elif kind == "change":
        kwargs["change_review_policy"] = "change-review-v1"
    else:
        kwargs["public_feedback"] = {key: "public" for key in seam.FEEDBACK_FIELDS}
        kwargs["public_feedback"]["observed_on_diff_hash"] = kwargs["seed_hash"]
    monkeypatch.setattr(runner, "run_dev", lambda _: pytest.fail("model must not start"))
    root = tmp_path / "run"
    with pytest.raises((ValueError, ContractError)):
        seam.run_seeded(request(root), **kwargs)
    assert not root.exists()


def test_overlay_follows_current_diff_without_mutating_prior_input():
    other = candidate.Candidate.model_validate(arguments()["alternative"])
    state = {"current_diff": {"patch_hash": sha256_text("seed")}}
    original = copy.deepcopy(state)
    value = candidate.overlay(state, other)
    assert state == original and not value["matches_current_diff"]
    state["current_diff"]["patch_hash"] = other.patch_hash
    assert candidate.overlay(state, other)["matches_current_diff"]
    assert not value["matches_current_diff"]
