"""Deterministic zero-call activation review for the Lean V26 package.

The review treats the four V26 mechanisms as one public-development product
package.  It does not attribute an effect to any individual mechanism, create
a candidate, execute the proposed runner-continuity check, or authorize an
external call.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V26,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V26,
    LEAN_RUNTIME_POLICY_VERSION_V26,
    LEAN_TOOL_SCHEMA_VERSION_V26,
)
from patchloop.agent.workflow_r21_reliability_qualification import (
    build_r21_reliability_qualification,
    qualification_bytes,
)
from patchloop.agent.workflow_r21_reliability_successor import (
    ANCHORED_READ_POLICY,
    GENERATION_INCOMPLETE_RECOVERY_POLICY,
    LIFECYCLE_PLAN_POLICY,
    MAX_PLAN_FEEDBACK_BYTES,
    PLAN_ADMISSION_FEEDBACK_POLICY_V2,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-r21-reliability-activation-review-v1"
REVIEW_PATH = Path("experiments/lean-harness-r21-reliability-activation-review-20260831-v1.json")

V26_QUALIFICATION_PATH = (
    "experiments/lean-harness-r21-reliability-public-qualification-20260831-v1.json"
)
R21_DIAGNOSIS_PATH = "reports/rapid-development/rapid-workflow-diagnosis-r21-590bbd602a34.json"
R21_BUNDLE_PATH = (
    "reports/rapid-development/"
    "rapid-public-dev-anyio-v5-v25-mechanical-activation-20260830-r21-590bbd602a34.jsonl"
)
RUNNER_CONTINUITY_PROPOSAL_PATH = (
    "experiments/anyio-runner-continuity-public-check-source-qualification-20260831-v1.json"
)

IMMUTABLE_INPUTS = {
    V26_QUALIFICATION_PATH: {
        "bytes": 6_253,
        "file_sha256": ("sha256:6b0f753f26c7e7d2d303c9b82bc192396bc1fbd312c709534927b7b39a4d38df"),
        "content_hash": ("sha256:4f07dd47a2d7d81580d135018b8400476880d7ce93f1c280d5b9c8f8c97f9275"),
    },
    R21_DIAGNOSIS_PATH: {
        "bytes": 11_731,
        "file_sha256": ("sha256:14663e2ed74a684c3c9d017a8e3c6812b3187b09938cea703a0735b920f4a884"),
        "content_hash": ("sha256:4893b30ff24c9d95ad844569fe5831497400893784e3a99ef663db4016adc601"),
    },
    R21_BUNDLE_PATH: {
        "bytes": 21_394,
        "file_sha256": ("sha256:54ae5e99226ec8a2d6635e6ece104c87b3ae1ba0e6aca675e20c7d7d339a749a"),
    },
    RUNNER_CONTINUITY_PROPOSAL_PATH: {
        "bytes": 7_159,
        "file_sha256": ("sha256:afaea6f091497e03219a47496c9f27f177a99061d9329af6a5793d188366d6b5"),
        "content_hash": ("sha256:ccb2cab859d71641fbb33416ca7c5cbf31512f2e9b590c4dc97de595101d8c13"),
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_r21_reliability_activation_review.py",
    "patchloop/agent/workflow_r21_reliability_qualification.py",
    "patchloop/agent/workflow_r21_reliability_successor.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/investigation.py",
    "patchloop/contracts.py",
    "patchloop/errors.py",
    "scripts/build_lean_harness_r21_reliability_activation_review.py",
    "scripts/build_lean_harness_r21_reliability_qualification.py",
    "tests/test_workflow_r21_reliability_activation_review.py",
    "tests/test_workflow_r21_reliability_qualification.py",
    "tests/test_workflow_r21_reliability_runner.py",
    "tests/test_workflow_r21_reliability_successor.py",
)

EXPECTED_RUNTIME_IDENTITY = {
    "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V26,
    "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V26,
    "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V26,
    "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V26,
    "generation_recovery_policy_version": GENERATION_INCOMPLETE_RECOVERY_POLICY,
    "feedback_policy_version": PLAN_ADMISSION_FEEDBACK_POLICY_V2,
    "anchor_policy_version": ANCHORED_READ_POLICY,
    "lifecycle_plan_policy_version": LIFECYCLE_PLAN_POLICY,
}


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"V26 activation-review input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _json_document(root: Path, relative: str, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(ensure_within(root, relative).read_bytes())
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError(f"{label} is invalid") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{label} is not an object")
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError(f"{label} content hash differs")
    return value


def _immutable_identity(root: Path, relative: str) -> dict[str, Any]:
    identity = _identity(root, relative)
    expected = IMMUTABLE_INPUTS[relative]
    if "content_hash" in expected:
        identity["content_hash"] = _json_document(
            root, relative, label="V26 activation-review immutable JSON"
        )["content_hash"]
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"V26 activation-review input differs: {relative}")
    return identity


def _qualification(root: Path) -> dict[str, Any]:
    _immutable_identity(root, V26_QUALIFICATION_PATH)
    stored = ensure_within(root, V26_QUALIFICATION_PATH).read_bytes()
    rebuilt = build_r21_reliability_qualification(root)
    if stored != qualification_bytes(rebuilt):
        raise ContractError("V26 qualification source binding differs")
    if (
        rebuilt.get("status") != "offline-qualified"
        or rebuilt.get("candidate_created") is not False
        or rebuilt.get("external_calls") != 0
    ):
        raise ContractError("V26 qualification boundary differs")
    return rebuilt


def _public_r21_rows(root: Path) -> list[dict[str, Any]]:
    _immutable_identity(root, R21_DIAGNOSIS_PATH)
    diagnosis = _json_document(root, R21_DIAGNOSIS_PATH, label="R21 public diagnosis")
    rows: list[dict[str, Any]] = []
    for row in diagnosis.get("rows", []):
        first_mutation = row.get("first_mutation_evidence", {})
        terminal = row.get("terminal_attribution", {})
        rows.append(
            {
                "order": row.get("order"),
                "run_id": row.get("run_id"),
                "terminal_classification": terminal.get("classification"),
                "terminal_error_code": terminal.get("error_code"),
                "first_mutation_observed": first_mutation.get("event_sequence") is not None,
                "evaluator_reached": row.get("evaluator_reached"),
                "submission_completed": row.get("submission_completed"),
                "success_at_budget": row.get("success_at_budget"),
            }
        )
    expected = [
        {
            "order": 1,
            "run_id": "run_rapid_v29_590bbd602a34_01",
            "terminal_classification": "agent_execution_terminal",
            "terminal_error_code": "SELF_DIRECTED_EXPLORATION_EXHAUSTED",
            "first_mutation_observed": True,
            "evaluator_reached": False,
            "submission_completed": False,
            "success_at_budget": False,
        },
        {
            "order": 2,
            "run_id": "run_rapid_v29_590bbd602a34_02",
            "terminal_classification": "completed",
            "terminal_error_code": None,
            "first_mutation_observed": True,
            "evaluator_reached": True,
            "submission_completed": True,
            "success_at_budget": False,
        },
        {
            "order": 3,
            "run_id": "run_rapid_v29_590bbd602a34_03",
            "terminal_classification": "agent_execution_terminal",
            "terminal_error_code": "MODEL_ACTION_CONTRACT_REPEATED",
            "first_mutation_observed": False,
            "evaluator_reached": False,
            "submission_completed": False,
            "success_at_budget": False,
        },
    ]
    if rows != expected:
        raise ContractError("R21 public activation-review row projection differs")
    return rows


def activation_criteria(qualification: dict[str, Any]) -> dict[str, bool]:
    """Return the fail-closed product-package decision criteria."""

    scenarios = qualification.get("scenarios", {})
    generation = scenarios.get("dedicated_generation_incomplete_recovery", {})
    feedback = scenarios.get("compact_plan_admission_feedback", {})
    anchor = scenarios.get("anchored_source_read", {})
    lifecycle = scenarios.get("generic_lifecycle_state_transition", {})
    tests = qualification.get("validated_test_surfaces", {})
    proposal = qualification.get("separate_public_check_proposal", {})
    boundary = qualification.get("evidence_boundary", {})
    zero_call_keys = (
        "provider_calls",
        "docker_calls",
        "evaluator_calls",
        "visible_check_calls",
        "network_calls",
    )
    return {
        "runtime_identity_exact": qualification.get("runtime_identity")
        == EXPECTED_RUNTIME_IDENTITY,
        "four_mechanisms_present": set(scenarios)
        == {
            "dedicated_generation_incomplete_recovery",
            "compact_plan_admission_feedback",
            "anchored_source_read",
            "generic_lifecycle_state_transition",
        },
        "generation_retry_is_one_use_and_independent": (
            generation.get("available_remaining") == 1
            and generation.get("consumed_remaining") == 0
            and generation.get("second_incomplete_rejected") is True
            and generation.get("shared_action_recovery_slot_consumed") is False
        ),
        "feedback_is_bounded_deterministic_and_nonmutating": (
            feedback.get("deterministic") is True
            and feedback.get("older_rejection_hash_only") is True
            and isinstance(feedback.get("latest_feedback_bytes"), int)
            and feedback["latest_feedback_bytes"] <= MAX_PLAN_FEEDBACK_BYTES
            and feedback.get("durable_event_changed") is False
        ),
        "anchored_read_is_current_diff_hash_bound": (
            anchor.get("selected_match_covered") is True
            and anchor.get("stale_diff_rejected") is True
            and anchor.get("search_result_hash_bound") is True
        ),
        "lifecycle_contract_is_public_provenance_not_semantic_oracle": (
            lifecycle.get("public_current_diff_source_only") is True
            and lifecycle.get("semantic_truth_verified") is False
            and lifecycle.get("mutation_owner_missing_rejected") is True
            and lifecycle.get("atomic_postconditions", 0) >= 1
        ),
        "focused_and_predecessor_surfaces_qualified": bool(tests)
        and all(value is True for value in tests.values()),
        "repeated_failure_causal_reset_preserved": tests.get(
            "repeated_public_failure_causal_reset_preserved"
        )
        is True,
        "runner_continuity_remains_unobserved_and_excluded": (
            proposal.get("status") == "offline-source-qualified-proposal"
            and proposal.get("behavior_observed") is False
            and proposal.get("task_successor_created") is False
            and proposal.get("activation_authorized") is False
        ),
        "qualification_is_zero_call_and_noncreating": (
            qualification.get("status") == "offline-qualified"
            and qualification.get("external_calls") == 0
            and qualification.get("candidate_created") is False
            and all(boundary.get(key) == 0 for key in zero_call_keys)
            and boundary.get("added_cost_usd") == "0"
        ),
    }


def build_r21_reliability_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    qualification = _qualification(root)
    public_rows = _public_r21_rows(root)
    criteria = activation_criteria(qualification)
    ready = all(criteria.values())
    proposal = qualification["separate_public_check_proposal"]
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 31, tzinfo=UTC).isoformat(),
        "status": "activation-reviewed-candidate-decision-ready",
        "scope": "lean-v26-four-mechanism-product-package-review",
        "runtime_identity": qualification["runtime_identity"],
        "qualification": {
            "path": V26_QUALIFICATION_PATH,
            "bytes": IMMUTABLE_INPUTS[V26_QUALIFICATION_PATH]["bytes"],
            "file_sha256": IMMUTABLE_INPUTS[V26_QUALIFICATION_PATH]["file_sha256"],
            "content_hash": qualification["content_hash"],
            "status": qualification["status"],
        },
        "runtime_source_binding": qualification["source_files"],
        "historical_public_observations": {
            "source": R21_DIAGNOSIS_PATH,
            "rows": public_rows,
            "mechanism_causality_established": False,
            "row_2_hidden_cause_inferred": False,
            "raw_trace_replayed": False,
            "reasoning_or_response_text_read": False,
        },
        "package_assessment": {
            "mechanism_count": 4,
            "mechanisms": [
                {
                    "policy_version": GENERATION_INCOMPLETE_RECOVERY_POLICY,
                    "falsifiable_boundary": (
                        "one incomplete generation may retry without consuming action recovery; "
                        "a second stops before a third dispatch"
                    ),
                },
                {
                    "policy_version": PLAN_ADMISSION_FEEDBACK_POLICY_V2,
                    "falsifiable_boundary": (
                        "superseded feedback is hash-only and the latest public card stays "
                        "within the fixed byte ceiling"
                    ),
                },
                {
                    "policy_version": ANCHORED_READ_POLICY,
                    "falsifiable_boundary": (
                        "a current-diff search result selects the exact dispatched read range"
                    ),
                },
                {
                    "policy_version": LIFECYCLE_PLAN_POLICY,
                    "falsifiable_boundary": (
                        "plan provenance binds lifecycle owners, transitions and public "
                        "postconditions without certifying semantic truth"
                    ),
                },
            ],
            "acceptable_variable": "single-versioned-product-package",
            "single_mechanism_attribution_allowed": False,
            "quality_effect_established": False,
            "generalization_established": False,
        },
        "activation_criteria": criteria,
        "residual_risks": {
            "dedicated_retry_may_repeat_bad_reasoning": True,
            "anchored_match_may_be_irrelevant": True,
            "lifecycle_schema_does_not_prove_runtime_atomicity": True,
            "four_mechanisms_cannot_be_individually_attributed": True,
            "r21_row_2_hidden_cause_remains_unknown": True,
            "runner_continuity_behavior_unobserved": True,
        },
        "runner_continuity_separation": {
            "proposal_path": proposal["path"],
            "file_sha256": proposal["file_sha256"],
            "content_hash": proposal["content_hash"],
            "behavior_observed": False,
            "task_successor_created": False,
            "include_in_future_v25_v26_comparison": False,
            "required_before_task_successor": "separate-base-reference-behavior-qualification",
        },
        "future_candidate_constraints": {
            "eligible_scope": "official-false-rapid-public-development-only",
            "recommended_control_runtime": "lean-harness-v25",
            "recommended_treatment_runtime": LEAN_RUNTIME_POLICY_VERSION_V26,
            "package_is_single_comparison_variable": True,
            "same_task_image_model_memory_budget_evaluator_required": True,
            "task_successor_allowed": False,
            "runner_continuity_check_allowed": False,
            "exact_candidate_and_two_byte_identical_rehearsals_required": True,
            "fresh_one_use_cost_approval_required": True,
            "candidate_design_authorized_by_review": False,
        },
        "decision": {
            "suitable_for_future_rapid_candidate": ready,
            "candidate_preparation_ready": ready,
            "adoption_status": "eligible-not-adopted",
            "runtime_offline_qualified": True,
            "candidate_created": False,
            "rehearsal_executed": False,
            "next_work": "separate-v25-v26-rapid-package-adoption-decision",
            "reason": (
                "The four V26 mechanisms are versioned, public, bounded and fail closed, "
                "so they are acceptable only as one non-attributable product-package "
                "variable. The unexecuted runner-continuity check remains outside the task."
            ),
        },
        "review_source_files": [_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_inputs": [_immutable_identity(root, relative) for relative in IMMUTABLE_INPUTS],
        "evidence_boundary": {
            "public_qualification_and_public_diagnosis_only": True,
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
        "external_activation_performed": False,
        "external_calls": 0,
        "candidate_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    if not ready:
        raise ContractError("V26 activation-review criteria are incomplete")
    return {**body, "content_hash": sha256_json(body)}


def review_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("V26 activation-review content hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_r21_reliability_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_r21_reliability_activation_review(root)
    target = ensure_within(root, REVIEW_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(review_bytes(value))
    return value


def load_r21_reliability_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, REVIEW_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("V26 activation review is unavailable") from exc
    if review_bytes(value) != raw:
        raise ContractError("V26 activation-review bytes differ")
    if value != build_r21_reliability_activation_review(root):
        raise ContractError("V26 activation-review source binding differs")
    return value


__all__ = [
    "EXPECTED_RUNTIME_IDENTITY",
    "IMMUTABLE_INPUTS",
    "REVIEW_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "activation_criteria",
    "build_r21_reliability_activation_review",
    "load_r21_reliability_activation_review",
    "materialize_r21_reliability_activation_review",
    "review_bytes",
]
