from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.rapid_r18_exploration_diagnosis import (
    DIAGNOSIS_PATH,
    V20_RUN_IDS,
    build_rapid_r18_exploration_diagnosis,
    diagnosis_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_r18_exploration_diagnosis_is_deterministic_and_zero_call() -> None:
    first = build_rapid_r18_exploration_diagnosis(ROOT)
    second = build_rapid_r18_exploration_diagnosis(ROOT)

    assert diagnosis_bytes(first) == diagnosis_bytes(second)
    assert first["official"] is False
    assert [row["run_id"] for row in first["rows"]] == list(V20_RUN_IDS)
    assert first["consumed_r18_modified"] is False
    assert first["consumed_r18_retry_allowed"] is False
    assert first["paid_execution_authorized"] is False
    assert all(
        first["evidence_boundary"][key] == 0
        for key in (
            "provider_calls",
            "docker_calls",
            "agent_calls",
            "evaluator_calls",
            "visible_check_calls",
            "network_calls",
            "state_mutations",
        )
    )


def test_r18_exploration_diagnosis_separates_observation_and_attribution() -> None:
    value = build_rapid_r18_exploration_diagnosis(ROOT)
    rows = value["rows"]
    findings = value["system_findings"]

    assert [row["plan_attempt_count"] for row in rows] == [0, 1, 1]
    assert all(row["mutation_count"] == 0 for row in rows)
    assert all(row["coverage_shrank_without_mutation"] for row in rows)
    assert all(row["terminal"]["error_code"] == "PRE_MUTATION_EVIDENCE_EXHAUSTED" for row in rows)
    assert findings["observed"]["exact_ordered_text_equality_was_false"] is True
    assert findings["observed"]["recovery_retry_was_not_forced"] is True
    assert findings["causal_attribution"]["task_semantic_difficulty_measured"] is False
    assert findings["next_successor_seam"]["name"] == "pinned-plan-gate-liveness-v1"
    assert findings["next_successor_seam"]["new_paid_candidate_allowed"] is False


def test_r18_exploration_diagnosis_preserves_public_only_detail() -> None:
    value = build_rapid_r18_exploration_diagnosis(ROOT)

    assert value["evidence_boundary"]["raw_reasoning_read"] is False
    assert value["evidence_boundary"]["llm_response_text_read"] is False
    assert value["evidence_boundary"]["private_task_spec_read"] is False
    assert value["evidence_boundary"]["hidden_evaluator_content_read"] is False
    assert value["evidence_boundary"]["reference_patch_read"] is False
    assert value["rows"][1]["plan_attempts"][0]["arguments"]["exact_ordered_unknown_match"] is False
    assert value["rows"][2]["plan_attempts"][0]["arguments"]["exact_ordered_unknown_match"] is False


def test_stored_r18_exploration_diagnosis_is_a_byte_audit() -> None:
    raw = (ROOT / DIAGNOSIS_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == diagnosis_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
