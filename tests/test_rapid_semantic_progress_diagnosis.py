from __future__ import annotations

import hashlib
import json
from pathlib import Path

from patchloop.evals.rapid_semantic_progress_diagnosis import (
    build_rapid_semantic_progress_diagnosis,
    diagnosis_bytes,
)

ARTIFACT = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-semantic-progress-diagnosis-v1.json"
)


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def test_semantic_progress_diagnosis_is_deterministic_and_public_only() -> None:
    first = build_rapid_semantic_progress_diagnosis()
    second = build_rapid_semantic_progress_diagnosis()

    assert diagnosis_bytes(first) == diagnosis_bytes(second)
    assert first["diagnosis"] == {
        "failure_signature_was_model_visible": True,
        "failure_signature_was_structurally_pinned": False,
        "same_signature_repeated_across_distinct_diffs": True,
        "all_revisions_refined_prior_hypothesis": True,
        "semantic_no_progress_was_not_structured": True,
        "insufficient_failure_visibility_supported": False,
        "increase_correction_limit_supported": False,
        "task_specific_solution_policy_supported": False,
        "next_successor_scope": "bounded-public-failure-signature-and-no-progress-reset",
        "live_candidate_ready": False,
    }
    failure = first["no_progress_failure"]
    assert [row["event_sequence"] for row in failure["failed_checks"]] == [52, 80, 113, 146]
    assert len({row["failure_signature_hash"] for row in failure["failed_checks"]}) == 1
    assert failure["distinct_failed_diff_count"] == 4
    assert failure["rejected_revision_count"] == 0
    assert [row["prior_hypothesis_disposition"] for row in failure["revisions"]] == [
        "refined",
        "refined",
        "refined",
    ]
    assert all(row["failure_signature_visible"] for row in failure["request_visibility"])
    assert not any(row["catalog_has_failure_signature"] for row in failure["request_visibility"])
    boundary = first["evidence_boundary"]
    assert boundary["task_fixture_files_read"] is False
    assert boundary["reference_patch_read"] is False
    assert boundary["hidden_evaluator_content_read"] is False
    assert boundary["provider_calls"] == boundary["docker_calls"] == 0
    assert boundary["visible_check_calls"] == boundary["state_mutations"] == 0
    assert (
        first["contamination_disclosure"][
            "interactive_exploration_glob_exposed_excluded_fixture_lines"
        ]
        is True
    )
    serialized = diagnosis_bytes(first).decode("utf-8")
    assert "reference.patch" not in serialized
    assert "/hidden/" not in serialized and "\\hidden\\" not in serialized


def test_materialized_semantic_progress_diagnosis_matches_builder() -> None:
    expected = diagnosis_bytes(build_rapid_semantic_progress_diagnosis())
    actual = ARTIFACT.read_bytes()

    assert actual == expected
    document = json.loads(actual)
    assert document["content_hash"] == build_rapid_semantic_progress_diagnosis()["content_hash"]
    assert _sha256(actual) == (
        "sha256:b818f2deeda534638fda996d342059814787823c62edcf882e63685e24d81223"
    )
