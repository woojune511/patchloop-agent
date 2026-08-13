from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.r8_completion_correction import (
    EXECUTION_HASH,
    OUTPUT_PATH,
    RESULT_PATH,
    validate_r8_runtime_evidence,
)


def test_r8_index_is_content_addressed_and_revalidates_external_evidence() -> None:
    external_available = RESULT_PATH.is_file()
    summary = validate_r8_runtime_evidence()
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    assert summary["status"] == "CORRECTED_COMPLETE_READINESS_MATRIX"
    assert summary["external_evidence_revalidated"] is external_available
    assert payload["campaign"]["execution_hash"] == EXECUTION_HASH
    assert payload["campaign"]["actual_model_cost_usd"] == 0.3664215
    assert payload["external_artifacts"]["final_result"]["file_sha256"] == (
        "sha256:8dbcb60a8a7f2937b00f7729561755cd9ef9b023d84ce64be4a0230ec5cc2878"
    )
    assert payload["external_artifacts"]["journal"]["file_sha256"] == (
        "sha256:f05dc041ea2196f790d7df3985d0731c0dfd2878f0c273f6e4811d81cdc0446a"
    )
    assert payload["predecessor_correction_index"]["file_sha256"] == (
        "sha256:24f942d487be1d30280a20f2a34a1bea7f3679c2756080c1d6cc7f0fdd1f7e38"
    )


def test_r8_correction_preserves_raw_gate_and_admits_exact_v2_matrix() -> None:
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    correction = payload["completion_correction"]
    original = correction["original_completion_gate"]
    corrected = correction["corrected_completion_gate"]

    assert correction["producer_schema_version"] == "trace-qualification-v2"
    assert correction["original_consumer_schema_version"] == "trace-qualification-v1"
    assert original["passed"] is False
    assert original["official_evaluator_runs"] == 0
    assert original["unclassified_runs"] == 4
    assert original["task_failures"] == -4
    assert corrected["passed"] is True
    assert corrected["analysis_ready"] is True
    assert corrected["official_evaluator_runs"] == 4
    assert corrected["unclassified_runs"] == 0
    assert corrected["task_successes"] == 4
    assert corrected["task_failures"] == 0
    assert correction["original_result_rewritten"] is False
    assert correction["provider_or_evaluator_reexecution_performed"] is False


def test_r8_rows_are_resolved_qualified_and_claims_stay_closed() -> None:
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    rows = payload["rows"]
    claims = payload["claim_authority"]

    assert [(row["task_id"], row["condition"]) for row in rows] == [
        ("moto-query-scanned-count", "no_memory"),
        ("moto-query-scanned-count", "structured"),
        ("babel-strict-grouped-decimal-trailing-zeroes", "structured"),
        ("babel-strict-grouped-decimal-trailing-zeroes", "no_memory"),
    ]
    assert all(row["outcome_kind"] == "resolved" for row in rows)
    assert all(row["trace_qualified"] is True for row in rows)
    assert all(row["evaluator_v2_completion_eligible"] is True for row in rows)
    assert sum(row["usage_evidence"]["token_derived_cost_nanos"] for row in rows) == 366_421_500
    assert claims["development_readiness_matrix_complete"] is True
    assert claims["descriptive_paired_analysis_ready"] is True
    assert claims["memory_effect_claim_authorized"] is False
    assert claims["retrieval_quality_claim_authorized"] is False
    assert claims["heldout_generalization_claim_authorized"] is False
    assert claims["core_campaign_authorized"] is False


def test_r8_descriptive_pairs_use_exact_settled_usage_without_widening_claims() -> None:
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    pairs = payload["descriptive_paired_analysis"]["pairs"]

    assert [pair["structured_minus_no_memory"] for pair in pairs] == [
        {
            "resolved_delta": 0,
            "total_tokens": -37_997,
            "model_cost_nanos": -38_622_750,
        },
        {
            "resolved_delta": 0,
            "total_tokens": -36_041,
            "model_cost_nanos": -42_540_750,
        },
    ]
    assert payload["descriptive_paired_analysis"]["success_delta_observed"] == 0
    assert (
        payload["descriptive_paired_analysis"]["inferential_memory_effect_claim_authorized"]
        is False
    )


def test_r8_index_paths_do_not_embed_private_payloads() -> None:
    text = Path(OUTPUT_PATH).read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" not in text
    assert "reference_patch" not in text
    assert "private.yaml" not in text
