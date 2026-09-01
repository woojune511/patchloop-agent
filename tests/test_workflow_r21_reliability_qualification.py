from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_r21_reliability_qualification import (
    IMMUTABLE_INPUTS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_r21_reliability_qualification,
    qualification_bytes,
)
from patchloop.evals.rapid_v26_batch_image_binding import validate_v26_batch_image_binding
from patchloop.evals.rapid_v26_package_binding import (
    V26_QUALIFICATION_FILE_SHA256,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_v26_qualification_is_deterministic_source_bound_and_zero_call() -> None:
    first = build_r21_reliability_qualification(ROOT)
    second = build_r21_reliability_qualification(ROOT)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
    assert first["candidate_created"] is False
    assert first["external_calls"] == 0
    assert [item["path"] for item in first["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in first["immutable_inputs"]] == list(IMMUTABLE_INPUTS)
    for key in (
        "provider_calls",
        "docker_calls",
        "evaluator_calls",
        "visible_check_calls",
        "network_calls",
    ):
        assert first["evidence_boundary"][key] == 0


def test_v26_qualification_covers_all_four_r21_successor_mechanisms() -> None:
    scenarios = build_r21_reliability_qualification(ROOT)["scenarios"]
    generation = scenarios["dedicated_generation_incomplete_recovery"]
    feedback = scenarios["compact_plan_admission_feedback"]
    anchor = scenarios["anchored_source_read"]
    lifecycle = scenarios["generic_lifecycle_state_transition"]

    assert generation["other_policy_consumed"] is False
    assert generation["second_incomplete_rejected"] is True
    assert generation["shared_action_recovery_slot_consumed"] is False
    assert feedback["deterministic"] is True
    assert feedback["older_rejection_hash_only"] is True
    assert feedback["latest_feedback_bytes"] <= feedback["byte_ceiling"]
    assert feedback["latest_evidence_ids"] == ["pev:17", "pev:19"]
    assert anchor["selected_match_covered"] is True
    assert anchor["stale_diff_rejected"] is True
    assert anchor["search_result_hash_bound"] is True
    assert lifecycle["semantic_truth_verified"] is False
    assert lifecycle["mutation_owner_missing_rejected"] is True
    assert lifecycle["atomic_postconditions"] == 1


def test_v26_qualification_keeps_check_proposal_unactivated() -> None:
    proposal = build_r21_reliability_qualification(ROOT)["separate_public_check_proposal"]

    assert proposal["task_successor_created"] is False
    assert proposal["behavior_observed"] is False
    assert proposal["activation_authorized"] is False


def test_stored_v26_qualification_is_an_exact_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()

    assert raw == qualification_bytes(json.loads(raw))
    assert sha256_bytes(raw) == V26_QUALIFICATION_FILE_SHA256
    # R22 adds only experiment admission. Never rewrite the reviewed artifact.
    assert json.loads(raw)["scenarios"] == build_r21_reliability_qualification(ROOT)["scenarios"]
    binding = validate_v26_batch_image_binding(ROOT)
    assert all(d["frozen_bytes_recovered"] for d in binding["batch_image_source_deltas"])
