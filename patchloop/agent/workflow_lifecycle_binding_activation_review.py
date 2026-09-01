"""Deterministic zero-call activation review for the Lean V28 package.

The review may find the package eligible for a later adoption decision.  It
does not adopt the runtime, create a candidate, observe provider acceptance or
authorize external execution.
"""

from __future__ import annotations

import ast
import copy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V28,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V28,
    LEAN_RUNTIME_POLICY_VERSION_V28,
    LEAN_TOOL_SCHEMA_VERSION_V28,
)
from patchloop.agent.provider_schema_admission import (
    PROVIDER_SCHEMA_POLICY,
    validate_provider_tool_schemas,
)
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import TOOL_SCHEMAS_V29
from patchloop.agent.workflow_lifecycle_binding_qualification import (
    QUALIFICATION_PATH,
    build_lifecycle_binding_qualification,
    qualification_bytes,
)
from patchloop.agent.workflow_lifecycle_binding_successor import (
    LIFECYCLE_COMPONENT_BINDING_POLICY,
    MAX_PLAN_FEEDBACK_BYTES_V3,
    PLAN_ADMISSION_FEEDBACK_POLICY_V3,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-lifecycle-component-binding-activation-review-v1"
REVIEW_PATH = Path(
    "experiments/lean-harness-lifecycle-component-binding-activation-review-20260901-v1.json"
)
QUALIFICATION_FILE_SHA256 = (
    "sha256:7ab720ed2eee560ef0d827488a4fb0e361bef44e17676234bade941bb5471b4e"
)
QUALIFICATION_CONTENT_HASH = (
    "sha256:2139df760fdc779ba2bef52dba3d2d7c4b22c389df29ee6e6757978ce44d68c5"
)
QUALIFICATION_BYTES = 6_498

EXPECTED_RUNTIME_IDENTITY = {
    "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V28,
    "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V28,
    "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V28,
    "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V28,
    "lifecycle_binding_policy_version": LIFECYCLE_COMPONENT_BINDING_POLICY,
    "feedback_policy_version": PLAN_ADMISSION_FEEDBACK_POLICY_V3,
}

SOURCE_FILES = (
    "patchloop/agent/workflow_lifecycle_binding_activation_review.py",
    "scripts/build_lean_harness_lifecycle_binding_activation_review.py",
    "tests/test_workflow_lifecycle_binding_activation_review.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"V28 activation-review input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _qualification(root: Path) -> dict[str, Any]:
    raw = ensure_within(root, QUALIFICATION_PATH.as_posix()).read_bytes()
    if len(raw) != QUALIFICATION_BYTES or sha256_bytes(raw) != QUALIFICATION_FILE_SHA256:
        raise ContractError("frozen V28 qualification bytes differ")
    rebuilt = build_lifecycle_binding_qualification(root)
    if (
        raw != qualification_bytes(rebuilt)
        or rebuilt.get("content_hash") != QUALIFICATION_CONTENT_HASH
    ):
        raise ContractError("frozen V28 qualification source binding differs")
    return rebuilt


def _mock_guarded_runtime_pair(root: Path) -> dict[str, Any]:
    path = "patchloop/contracts.py"
    tree = ast.parse(ensure_within(root, path).read_text(encoding="utf-8"))
    pairs = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Tuple)
        and [item.value if isinstance(item, ast.Constant) else None for item in node.elts]
        == [LEAN_TOOL_SCHEMA_VERSION_V28, LEAN_CONTEXT_POLICY_VERSION_V28]
    ]
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    guarded: list[bool] = []
    for pair in pairs:
        current: ast.AST = pair
        while current in parents and not (
            isinstance(current, ast.BoolOp) and isinstance(current.op, ast.And)
        ):
            current = parents[current]
        guarded.append(
            any(
                isinstance(node, ast.Compare)
                and ast.unparse(node) == "self.model.provider == 'mock'"
                for node in ast.walk(current)
            )
        )
    if len(pairs) != 1 or guarded != [True]:
        raise ContractError("V28 mock-only runtime admission boundary differs")
    return {
        "path": path,
        "kind": "static-source-observation-not-live-control-flow-proof",
        "runtime_pair_occurrences": len(pairs),
        "all_occurrences_require_mock_provider": all(guarded),
        "live_manifest_admitted": False,
    }


def source_observations(root: Path) -> dict[str, Any]:
    manifest = SimpleNamespace(
        tool_schema_version=LEAN_TOOL_SCHEMA_VERSION_V28,
        context_policy_version=LEAN_CONTEXT_POLICY_VERSION_V28,
    )
    _prompt, schemas = AgentRunner._runtime_contract(manifest)
    schema_receipt = validate_provider_tool_schemas({"tools": copy.deepcopy(schemas)})
    if schemas is not TOOL_SCHEMAS_V29:
        raise ContractError("V28 runtime contract does not select tool schema V29")
    return {
        "runtime_contract": {
            "tool_schema_version": manifest.tool_schema_version,
            "context_policy_version": manifest.context_policy_version,
            "selects_tool_schemas_v29": True,
            "tool_count": len(schemas),
            "tool_schema_hash": sha256_json(schemas),
        },
        "static_provider_schema_admission": {
            "policy_version": schema_receipt["policy_version"],
            "tool_schema_hash": schema_receipt["tool_schema_hash"],
            "tool_count": len(schema_receipt["tool_names"]),
            "provider_acceptance_observed": False,
        },
        "manifest_admission": _mock_guarded_runtime_pair(root),
    }


def activation_criteria(
    qualification: dict[str, Any], observations: dict[str, Any]
) -> dict[str, bool]:
    scenarios = qualification.get("scenarios", {})
    registry = scenarios.get("single_component_registry_request", {})
    record = scenarios.get("bound_public_plan_record", {})
    feedback = scenarios.get("exact_relation_mismatch_feedback", {})
    r24 = scenarios.get("r24_public_mismatch_shape", {})
    tests = qualification.get("validated_test_surfaces", {})
    boundary = qualification.get("evidence_boundary", {})
    runtime = observations.get("runtime_contract", {})
    provider = observations.get("static_provider_schema_admission", {})
    admission = observations.get("manifest_admission", {})
    return {
        "runtime_identity_exact": qualification.get("runtime_identity")
        == EXPECTED_RUNTIME_IDENTITY,
        "component_registry_removes_repeated_free_form_relations": (
            registry.get("owners_field_absent") is True
            and registry.get("states_field_absent") is True
            and registry.get("free_form_affected_components_absent") is True
            and registry.get("integer_component_references")
            == {"type": "integer", "minimum": 0, "maximum": 7}
            and registry.get("semantic_truth_verified") is False
        ),
        "normalized_record_is_public_plan_bound_not_semantic_oracle": (
            record.get("component_count") == 2
            and record.get("transition_component_indices") == [0, 1]
            and record.get("mutation_owner_component_index") == 0
            and record.get("public_current_diff_source_only") is True
            and record.get("private_or_hidden_material_used") is False
        ),
        "exact_feedback_is_bounded_deterministic_and_tamper_closed": (
            feedback.get("deterministic") is True
            and feedback.get("projected_exact_mismatch") is True
            and feedback.get("tampered_relation_hash_rejected") is True
            and feedback.get("private_or_hidden_material_included") is False
            and feedback.get("raw_reasoning_included") is False
            and isinstance(feedback.get("latest_feedback_bytes"), int)
            and feedback["latest_feedback_bytes"] <= MAX_PLAN_FEEDBACK_BYTES_V3
        ),
        "one_retry_repeated_rejection_and_restart_are_qualified": (
            tests.get("one_retry_exact_feedback") is True
            and tests.get("second_rejection_stops_before_third_plan_dispatch") is True
            and tests.get("feedback_restart_recovery") is True
            and tests.get("durable_component_registry_record") is True
        ),
        "r24_shape_is_public_and_diagnostic_not_semantic_proof": (
            r24.get("classification") == "cross-field-lifecycle-component-binding-friction"
            and r24.get("affected_started_rows") == 2
            and r24.get("rejected_plan_attempts") == 3
            and r24.get("exact_mismatch_feedback_was_absent") is True
            and r24.get("semantic_fix_correctness_established") is False
            and r24.get("official") is False
            and r24.get("raw_reasoning_read") is False
            and r24.get("private_or_hidden_material_read") is False
        ),
        "runtime_routes_v29_and_static_schema_is_locally_admitted": (
            runtime.get("selects_tool_schemas_v29") is True
            and runtime.get("tool_count") == provider.get("tool_count")
            and provider.get("policy_version") == PROVIDER_SCHEMA_POLICY
            and provider.get("provider_acceptance_observed") is False
        ),
        "live_manifest_and_external_authority_stay_closed": (
            admission.get("runtime_pair_occurrences") == 1
            and admission.get("all_occurrences_require_mock_provider") is True
            and admission.get("live_manifest_admitted") is False
            and qualification.get("candidate_created") is False
            and qualification.get("paid_execution_authorized") is False
        ),
        "qualification_is_zero_call_noncreating_and_source_bound": (
            qualification.get("status") == "offline-qualified"
            and qualification.get("external_calls") == 0
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
            and len(qualification.get("source_files", [])) == 10
            and len(qualification.get("immutable_inputs", [])) == 5
        ),
    }


def build_lifecycle_binding_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    qualification = _qualification(root)
    observations = source_observations(root)
    criteria = activation_criteria(qualification, observations)
    eligible = all(criteria.values())
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": "2026-09-01T00:00:00+00:00",
        "status": (
            "activation-reviewed-candidate-decision-ready"
            if eligible
            else "activation-review-blocked"
        ),
        "scope": "frozen-lean-v28-offline-package-not-live-activation",
        "runtime_identity": qualification["runtime_identity"],
        "qualification": {
            **_identity(root, QUALIFICATION_PATH.as_posix()),
            "content_hash": qualification["content_hash"],
            "status": qualification["status"],
        },
        "runtime_source_binding": qualification["source_files"],
        "predecessor_preservation": qualification["immutable_inputs"],
        "source_observations": observations,
        "activation_criteria": criteria,
        "package_assessment": {
            "acceptable_variable": "single-versioned-lifecycle-plan-feedback-package",
            "single_mechanism_attribution_allowed": False,
            "observed_public_failure_class_addressed": (
                "cross-field-lifecycle-component-binding-friction"
            ),
            "semantic_task_failure_addressed": False,
            "provider_timeout_addressed": False,
            "quality_effect_established": False,
            "generalization_established": False,
        },
        "decision": {
            "adoption_status": "eligible-not-adopted" if eligible else "blocked",
            "eligible_for_separate_adoption_decision": eligible,
            "candidate_design_authorized_by_review": False,
            "live_execution_ready": False,
            "provider_acceptance_observed": False,
            "candidate_created": False,
            "next_work": "separate-v27-v28-rapid-package-adoption-decision",
            "reason": (
                "V28 removes the observed repeated-string relation and returns exact bounded "
                "public feedback while preserving fail-closed recovery. It remains unadopted "
                "because no live manifest, candidate rehearsal, provider acceptance or AnyIO "
                "performance has been observed."
            ),
        },
        "future_candidate_constraints": {
            "eligible_scope": "official-false-rapid-public-development-only",
            "recommended_control_runtime": "lean-harness-v27",
            "recommended_treatment_runtime": LEAN_RUNTIME_POLICY_VERSION_V28,
            "package_is_single_comparison_variable": True,
            "same_task_image_model_memory_budget_evaluator_required": True,
            "task_version_change_allowed": False,
            "runner_continuity_check_allowed": False,
            "historical_retry_or_resume_allowed": False,
            "candidate_design_authorized_by_review": False,
            "exact_candidate_and_two_byte_identical_rehearsals_required": True,
            "fresh_one_use_cost_approval_required": True,
            "schedule_and_cost_not_selected_by_review": True,
            "official": False,
        },
        "residual_risks": [
            "Integer references can still bind the wrong semantic component.",
            "Structural admission does not prove lifecycle atomicity or task correctness.",
            "Exact feedback can still lead to one bad retry before the bounded terminal.",
            "R24's targeted-check semantic failure is not repaired by this contract change.",
            "R24's provider timeout and continuation gap are outside this package.",
            "Local strict-schema admission is not live provider acceptance.",
            "Mock completion establishes no quality, cost or generalization improvement.",
        ],
        "review_source_files": [_identity(root, relative) for relative in SOURCE_FILES],
        "evidence_boundary": {
            "public_qualification_and_static_source_only": True,
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
        "runtime_source_modified": False,
        "external_activation_performed": False,
        "external_calls": 0,
        "candidate_created": False,
        "rehearsal_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
        "next_gate": "separate-v27-v28-rapid-package-adoption-decision",
    }
    if not eligible:
        raise ContractError("V28 activation-review criteria are incomplete")
    return {**body, "content_hash": sha256_json(body)}


def review_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("V28 activation-review content hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_lifecycle_binding_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    first = build_lifecycle_binding_activation_review(root)
    raw = review_bytes(first)
    if raw != review_bytes(build_lifecycle_binding_activation_review(root)):
        raise ContractError("V28 activation reviews are not byte-identical")
    target = ensure_within(root, REVIEW_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != raw:
            raise ContractError("existing V28 review differs; never overwrite evidence")
    else:
        with target.open("xb") as stream:
            stream.write(raw)
    return first


__all__ = [
    "EXPECTED_RUNTIME_IDENTITY",
    "QUALIFICATION_BYTES",
    "QUALIFICATION_CONTENT_HASH",
    "QUALIFICATION_FILE_SHA256",
    "REVIEW_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "activation_criteria",
    "build_lifecycle_binding_activation_review",
    "materialize_lifecycle_binding_activation_review",
    "review_bytes",
    "source_observations",
]
