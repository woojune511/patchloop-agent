"""Zero-call adoption decision for the frozen Lean V28 package.

The decision selects V28 only as a future ``official=false`` Rapid treatment.
It does not promote a default runtime, create a candidate or rehearsal, or
authorize provider, Docker, evaluator, visible-check, network, or paid work.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from patchloop.agent.workflow_lifecycle_binding_activation_review import (
    REVIEW_PATH as ACTIVATION_REVIEW_PATH,
)
from patchloop.agent.workflow_lifecycle_binding_activation_review import (
    build_lifecycle_binding_activation_review,
)
from patchloop.agent.workflow_lifecycle_binding_activation_review import (
    review_bytes as activation_review_bytes,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-lifecycle-component-binding-adoption-decision-v1"
DECISION_PATH = Path(
    "experiments/lean-harness-lifecycle-component-binding-adoption-decision-20260901-v1.json"
)
ACTIVATION_REVIEW_BYTES = 8_517
ACTIVATION_REVIEW_FILE_SHA256 = (
    "sha256:12b5e11c2aecd453cfdcf6a909f30b7fdc6cd41a3b4bb20fb87371d34dfc16ed"
)
ACTIVATION_REVIEW_CONTENT_HASH = (
    "sha256:119a40b5c8e80c13e2e2fc2bf5b2f73e2bddfd2c0f452b1d8a3d9a56646980c3"
)

EXPECTED_ACTIVATION_CRITERIA = {
    "component_registry_removes_repeated_free_form_relations",
    "exact_feedback_is_bounded_deterministic_and_tamper_closed",
    "live_manifest_and_external_authority_stay_closed",
    "normalized_record_is_public_plan_bound_not_semantic_oracle",
    "one_retry_repeated_rejection_and_restart_are_qualified",
    "qualification_is_zero_call_noncreating_and_source_bound",
    "r24_shape_is_public_and_diagnostic_not_semantic_proof",
    "runtime_identity_exact",
    "runtime_routes_v29_and_static_schema_is_locally_admitted",
}

EXPECTED_RESIDUAL_RISKS = (
    "Integer references can still bind the wrong semantic component.",
    "Structural admission does not prove lifecycle atomicity or task correctness.",
    "Exact feedback can still lead to one bad retry before the bounded terminal.",
    "R24's targeted-check semantic failure is not repaired by this contract change.",
    "R24's provider timeout and continuation gap are outside this package.",
    "Local strict-schema admission is not live provider acceptance.",
    "Mock completion establishes no quality, cost or generalization improvement.",
)

SOURCE_FILES = (
    "patchloop/agent/workflow_lifecycle_binding_adoption_decision.py",
    "scripts/build_lean_harness_lifecycle_binding_adoption_decision.py",
    "tests/test_workflow_lifecycle_binding_adoption_decision.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"V28 adoption-decision input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _activation_review(root: Path) -> dict[str, Any]:
    path = ensure_within(root, ACTIVATION_REVIEW_PATH.as_posix())
    if path.is_symlink() or not path.is_file():
        raise ContractError("frozen V28 activation review is unavailable")
    raw = path.read_bytes()
    if len(raw) != ACTIVATION_REVIEW_BYTES or sha256_bytes(raw) != ACTIVATION_REVIEW_FILE_SHA256:
        raise ContractError("frozen V28 activation-review bytes differ")
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("frozen V28 activation review is not canonical JSON") from exc
    if (
        document.get("content_hash") != ACTIVATION_REVIEW_CONTENT_HASH
        or activation_review_bytes(document) != raw
    ):
        raise ContractError("frozen V28 activation-review content differs")
    rebuilt = build_lifecycle_binding_activation_review(root)
    if activation_review_bytes(rebuilt) != raw:
        raise ContractError("frozen V28 activation-review source binding differs")
    return document


def adoption_criteria(review: dict[str, Any]) -> dict[str, bool]:
    decision = review.get("decision", {})
    package = review.get("package_assessment", {})
    constraints = review.get("future_candidate_constraints", {})
    boundary = review.get("evidence_boundary", {})
    activation = review.get("activation_criteria", {})
    return {
        "activation_review_is_ready_and_unadopted": (
            review.get("status") == "activation-reviewed-candidate-decision-ready"
            and decision.get("adoption_status") == "eligible-not-adopted"
            and decision.get("eligible_for_separate_adoption_decision") is True
            and decision.get("candidate_design_authorized_by_review") is False
            and set(activation) == EXPECTED_ACTIVATION_CRITERIA
            and all(activation.values())
        ),
        "observed_contract_friction_is_directly_addressed": (
            package.get("acceptable_variable") == "single-versioned-lifecycle-plan-feedback-package"
            and package.get("observed_public_failure_class_addressed")
            == "cross-field-lifecycle-component-binding-friction"
        ),
        "semantic_and_infrastructure_unknowns_are_not_reclassified": (
            package.get("semantic_task_failure_addressed") is False
            and package.get("provider_timeout_addressed") is False
            and package.get("quality_effect_established") is False
            and package.get("generalization_established") is False
            and package.get("single_mechanism_attribution_allowed") is False
        ),
        "comparison_variable_and_scope_are_bounded": (
            constraints.get("eligible_scope") == "official-false-rapid-public-development-only"
            and constraints.get("recommended_control_runtime") == "lean-harness-v27"
            and constraints.get("recommended_treatment_runtime") == "lean-harness-v28"
            and constraints.get("package_is_single_comparison_variable") is True
            and constraints.get("official") is False
        ),
        "fair_comparison_inputs_remain_fixed": (
            constraints.get("same_task_image_model_memory_budget_evaluator_required") is True
            and constraints.get("task_version_change_allowed") is False
            and constraints.get("runner_continuity_check_allowed") is False
            and constraints.get("historical_retry_or_resume_allowed") is False
        ),
        "candidate_and_external_gates_remain_separate": (
            constraints.get("exact_candidate_and_two_byte_identical_rehearsals_required") is True
            and constraints.get("fresh_one_use_cost_approval_required") is True
            and constraints.get("schedule_and_cost_not_selected_by_review") is True
            and review.get("candidate_created") is False
            and review.get("rehearsal_created") is False
            and review.get("paid_execution_authorized") is False
            and review.get("external_activation_performed") is False
        ),
        "residual_risks_are_preserved_exactly": (
            tuple(review.get("residual_risks", ())) == EXPECTED_RESIDUAL_RISKS
        ),
        "evidence_boundary_is_public_and_zero_call": (
            review.get("external_calls") == 0
            and all(
                boundary.get(key) == 0
                for key in (
                    "provider_calls",
                    "docker_calls",
                    "evaluator_calls",
                    "visible_check_calls",
                    "network_calls",
                )
            )
            and boundary.get("added_cost_usd") == "0"
            and boundary.get("raw_reasoning_read") is False
            and boundary.get("private_task_spec_read") is False
            and boundary.get("hidden_evaluator_content_read") is False
            and boundary.get("reference_patch_read") is False
        ),
    }


def build_lifecycle_binding_adoption_decision(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    review = _activation_review(root)
    criteria = adoption_criteria(review)
    adopted = all(criteria.values())
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": "2026-09-01T00:00:00+00:00",
        "status": "package-adoption-recorded" if adopted else "package-adoption-blocked",
        "scope": "future-official-false-rapid-treatment-selection-only",
        "activation_review": {
            **_identity(root, ACTIVATION_REVIEW_PATH.as_posix()),
            "content_hash": review["content_hash"],
            "status": review["status"],
        },
        "runtime_identity": review["runtime_identity"],
        "adoption_criteria": criteria,
        "decision": {
            "adoption_status": ("adopted-for-future-rapid-treatment" if adopted else "not-adopted"),
            "selected_control_runtime": "lean-harness-v27",
            "selected_treatment_runtime": "lean-harness-v28",
            "eligible_for_separate_candidate_preparation": adopted,
            "candidate_preparation_authorized_in_this_work_item": False,
            "default_runtime_changed": False,
            "quality_or_generalization_promotion": False,
            "live_execution_ready": False,
            "reason": (
                "V28 is selected only as the next Rapid treatment because it directly "
                "addresses R24's public lifecycle-binding contract friction as one "
                "versioned package. Provider acceptance, semantic task success and "
                "performance remain questions for a later approved comparison."
            ),
        },
        "comparison_contract": {
            "official": False,
            "control_runtime": "lean-harness-v27",
            "treatment_runtime": "lean-harness-v28",
            "declared_comparison_variable": "lifecycle-plan-feedback-package",
            "recommended_rows_per_arm": 3,
            "balanced_interleaved_schedule_required": True,
            "same_task_image_model_memory_budget_evaluator_required": True,
            "task_version_change_allowed": False,
            "runner_continuity_check_allowed": False,
            "semantic_or_timeout_fix_may_be_bundled": False,
            "exact_schedule_selected": False,
            "cost_reserve_or_cap_selected": False,
        },
        "precommitted_interpretation": {
            "primary_development_question": (
                "Does V28 remove repeated lifecycle-component binding admission loops "
                "without adding a new workflow-contract terminal?"
            ),
            "legacy_unbound_terminal_count_max": 0,
            "admission_loop_budget_terminal_count_max": 0,
            "harness_admission_infrastructure_failure_count_max": 0,
            "treatment_evaluator_reach_floor": "2/3",
            "treatment_reach_submission_success_not_lower_than_control": True,
            "treatment_mean_settled_row_cost_ratio_max": "1.25",
            "incomplete_schedule_is_noncomparative": True,
            "passing_selects_public_development_default_only": True,
            "quality_or_generalization_claim_allowed": False,
        },
        "residual_risks": list(EXPECTED_RESIDUAL_RISKS),
        "source_files": [_identity(root, relative) for relative in SOURCE_FILES],
        "evidence_boundary": {
            "frozen_public_activation_review_only": True,
            "raw_reasoning_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "network_calls": 0,
            "added_cost_usd": "0",
        },
        "historical_retry_or_resume_allowed": False,
        "runtime_source_modified": False,
        "candidate_created": False,
        "rehearsal_created": False,
        "external_calls": 0,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
        "next_gate": "separate-v27-v28-rapid-candidate-and-rehearsal-preparation",
    }
    if not adopted:
        raise ContractError("V28 package-adoption criteria are incomplete")
    return {**body, "content_hash": sha256_json(body)}


def decision_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("V28 adoption-decision content hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_lifecycle_binding_adoption_decision(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    first = build_lifecycle_binding_adoption_decision(root)
    raw = decision_bytes(first)
    if raw != decision_bytes(build_lifecycle_binding_adoption_decision(root)):
        raise ContractError("V28 adoption decisions are not byte-identical")
    target = ensure_within(root, DECISION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != raw:
            raise ContractError("existing V28 adoption decision differs; never overwrite evidence")
    else:
        with target.open("xb") as stream:
            stream.write(raw)
    return first


__all__ = [
    "ACTIVATION_REVIEW_BYTES",
    "ACTIVATION_REVIEW_CONTENT_HASH",
    "ACTIVATION_REVIEW_FILE_SHA256",
    "DECISION_PATH",
    "EXPECTED_ACTIVATION_CRITERIA",
    "EXPECTED_RESIDUAL_RISKS",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "adoption_criteria",
    "build_lifecycle_binding_adoption_decision",
    "decision_bytes",
    "materialize_lifecycle_binding_adoption_decision",
]
