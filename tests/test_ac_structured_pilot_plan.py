from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from patchloop.agent.model import SYSTEM_PROMPT_V3

PLAN_PATH = Path("experiments/ac-structured-pilot.plan.yaml")
DATASET_PATH = Path("data/dataset-manifest.yaml")
PLATFORM_RENDER_SHA = "sha256:f1cd44ed10d527ff7f5c44dd0be4e6957810530cd055d3329da0d7962d3cec7c"
CONTEXT_RENDER_SHA = "sha256:ab0273b575f76efd4ca9facda9540d87f2ea85e69a333cf87e4d7ac781287c2a"
STATE_RENDER_SHA = "sha256:00ceca8ed912a48f36ab26fb50b1d7eb428fe261a83b2bd84e231f0c6e786bf7"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_ac_pilot_is_exactly_four_paired_readiness_rows() -> None:
    plan = _load_yaml(PLAN_PATH)

    assert plan["schema_version"] == "ac-structured-pilot-plan-v1"
    assert plan["status"] == "offline-suite-and-qualification-implemented-live-closed"
    assert plan["design"]["conditions"] == ["no_memory", "structured"]
    assert plan["design"]["repetitions"] == 1
    assert plan["design"]["task_count"] == 2
    assert plan["design"]["expected_runs"] == 4

    rows = plan["design"]["schedule"]
    assert [row["order"] for row in rows] == list(range(1, 5))
    for task_id in {row["task_id"] for row in rows}:
        assert [row["condition"] for row in rows if row["task_id"] == task_id] in (
            ["no_memory", "structured"],
            ["structured", "no_memory"],
        )


def test_ac_pilot_uses_the_complete_dev_validation_panel_and_no_source_task() -> None:
    plan = _load_yaml(PLAN_PATH)
    manifest = _load_yaml(DATASET_PATH)
    manifest_by_id = {row["task_id"]: row for row in manifest["tasks"]}
    source_task_ids = {
        "pyfakefs-makedirs-parent-traversal",
        "hf-hub-xet-endpoint-propagation",
        "tox-cross-section-empty-substitution",
    }

    task_rows = plan["tasks"]
    task_ids = {Path(row["path"]).parent.name for row in task_rows}
    assert task_ids == {
        "moto-query-scanned-count",
        "babel-strict-grouped-decimal-trailing-zeroes",
    }
    assert len(task_rows) == len(task_ids) == 2
    assert task_ids.isdisjoint(source_task_ids)
    for row in task_rows:
        task_id = Path(row["path"]).parent.name
        assert row["dataset_role"] == "development-validation"
        assert manifest_by_id[task_id]["role"] == "development-validation"
        assert manifest_by_id[task_id]["path"] == Path(row["path"]).parent.as_posix()

    selection = plan["selection_contract"]
    assert selection["source_task_reuse_allowed"] is False
    assert selection["heldout_task_consumed"] is False
    assert selection["heldout_issue_text_inspected_for_this_selection"] is False
    assert selection["hidden_or_private_evidence_inspected"] is False
    assert selection["outcome_based_task_selection_allowed"] is False
    assert selection["replacement_after_outcome_allowed"] is False


def test_ac_pilot_keeps_the_high_headroom_tuple_condition_neutral() -> None:
    plan = _load_yaml(PLAN_PATH)
    runtime = plan["fixed_runtime_tuple"]

    assert runtime == {
        "model": "openai",
        "model_id": "gpt-5.4-mini-2026-03-17",
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "transport_max_retries": 0,
        "max_output_tokens": 25_000,
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 3_000_000,
        "wall_clock_timeout_seconds": 3_600,
        "tool_schema_version": "v2",
        "context_policy_version": "phase-evidence-v5",
        "system_prompt_version": "SYSTEM_PROMPT_V3",
        "system_prompt_sha256": (
            "sha256:441c71fdea2defed14f06b32c3fba7a7aaa19f7a3ca749bc994e72708d8a733b"
        ),
        "memory_policy_version": "fixed-d110-bundle-v1",
    }
    assert runtime["system_prompt_sha256"] == (
        "sha256:" + hashlib.sha256(SYSTEM_PROMPT_V3.encode("utf-8")).hexdigest()
    )


def test_structured_arm_is_fixed_bundle_not_selective_retrieval() -> None:
    plan = _load_yaml(PLAN_PATH)
    structured = plan["structured_condition"]
    index_path = Path(structured["frozen_index"]["path"])
    frozen_index = _load_yaml(index_path)

    assert structured["mode"] == "fixed-approved-three-entry-bundle"
    assert structured["delivery_cadence"] == "every-model-request"
    assert structured["query_embedding_or_similarity_used"] is False
    assert structured["threshold_or_reranking_used"] is False
    assert structured["entry_count"] == 3
    assert structured["order_contract"] == "frozen-d110-group-provenance-order"
    assert structured["ordered_entries"] == [
        {
            "order": 1,
            "memory_id": "memgrp_649483b80292fea26e4009ebdb72df31",
            "semantic_group_id": "platform-emulation-matrix-gap",
            "render_file_sha256": PLATFORM_RENDER_SHA,
        },
        {
            "order": 2,
            "memory_id": "memgrp_b421547d481faabf9be3511217258de5",
            "semantic_group_id": "request-context-propagation-gap",
            "render_file_sha256": CONTEXT_RENDER_SHA,
        },
        {
            "order": 3,
            "memory_id": "memgrp_5a23f463cba43bf3ba395f67cf976047",
            "semantic_group_id": "exception-origin-state-conflation",
            "render_file_sha256": STATE_RENDER_SHA,
        },
    ]
    assert structured["ordered_entries"] == [
        {key: row[key] for key in ("order", "memory_id", "semantic_group_id", "render_file_sha256")}
        for row in frozen_index["group_provenance"]
    ]
    assert structured["token_budget"] == 2_000
    assert structured["render_contract"] == {
        "separator": "\n\n---\n\n",
        "trailing_newline": True,
        "bundle_bytes": 3_528,
        "bundle_sha256": (
            "sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf"
        ),
    }
    assert structured["observed_provider_input_delta_tokens"] == 702
    assert index_path.exists()
    assert _sha256(index_path) == structured["frozen_index"]["file_sha256"]
    marker_path = Path(structured["frozen_index"]["marker_path"])
    assert marker_path.read_text(encoding="utf-8") == (
        structured["frozen_index"]["marker_content_hash"] + "\n"
    )
    assert _sha256(marker_path) == structured["frozen_index"]["marker_file_sha256"]


def test_ac_pilot_is_non_executable_and_non_headline() -> None:
    plan = _load_yaml(PLAN_PATH)
    analysis = plan["analysis_contract"]
    authority = plan["execution_boundary"]

    assert analysis["diagnostic_only"] is True
    assert analysis["confidence_interval_claim_allowed"] is False
    assert analysis["statistical_significance_claim_allowed"] is False
    assert analysis["portfolio_headline_allowed"] is False
    assert analysis["full_four_condition_conclusion_allowed"] is False
    assert analysis["heldout_memory_effect_claim_allowed"] is False
    assert analysis["cross_repository_generalization_claim_allowed"] is False

    assert authority["runtime_fixed_bundle_injection_implemented"] is True
    assert authority["runtime_fixed_bundle_mock_path_verified"] is True
    assert authority["fixed_request_artifact_replay_validator_implemented"] is True
    assert authority["runtime_fixed_bundle_injection_qualified"] is False
    assert authority["experiment_suite_exact_policy_binding_implemented"] is True
    assert authority["structured_trace_qualifier_implemented"] is True
    assert authority["offline_source_qualification_ready_for_materialization"] is True
    assert authority["exact_four_row_cost_reservation_implemented"] is False
    assert authority["exact_four_row_completion_gate_implemented"] is False
    assert authority["execution_authorization_candidate_prepared"] is False
    assert authority["retrieval_experiment_authorized"] is False
    assert authority["runtime_memory_injection_authorized"] is False
    assert authority["provider_execution_authorized"] is False
    assert authority["evaluator_execution_authorized"] is False
    assert authority["live_cost_approved"] is False
    assert authority["approved_execution_hash"] is None
    assert authority["automatic_retry_allowed"] is False
    assert authority["full_four_condition_campaign_deferred"] is True
    assert authority["heldout_ac_comparison_deferred"] is True
    assert authority["d121_successor_execution_required_for_this_pilot"] is False
    assert authority["d121_successor_execution_deferred"] is True
