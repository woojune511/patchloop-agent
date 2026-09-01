"""Deterministic zero-call qualification for the Lean V28 lifecycle binding."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.context import BuiltContext
from patchloop.agent.context_event_compaction import (
    project_lean_context_event_descriptors_v2,
)
from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V28,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V28,
    LEAN_RUNTIME_POLICY_VERSION_V28,
    LEAN_TOOL_SCHEMA_VERSION_V28,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    _task,
)
from patchloop.agent.workflow_lifecycle_binding_successor import (
    LIFECYCLE_COMPONENT_BINDING_POLICY,
    MAX_PLAN_FEEDBACK_BYTES_V3,
    PLAN_ADMISSION_FEEDBACK_POLICY_V3,
    LifecycleRelationMismatch,
    normalize_lifecycle_component_bound_plan,
    project_lifecycle_component_bound_plan_request,
    project_lifecycle_plan_admission_feedback_v3,
)
from patchloop.agent.workflow_plan_admission_feedback_successor_qualification import (
    _feedback_details,
)
from patchloop.agent.workflow_plan_contract_compatibility_successor import (
    project_trigger_bound_self_directed_plan_request,
)
from patchloop.agent.workflow_self_directed_exploration_successor_qualification import (
    _catalog_v4,
    _plan_arguments,
    _request,
)
from patchloop.errors import ContractError
from patchloop.util import (
    canonical_json,
    ensure_within,
    sha256_bytes,
    sha256_json,
    sha256_text,
)

SCHEMA_VERSION = "lean-lifecycle-component-binding-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-lifecycle-component-binding-public-qualification-20260901-v1.json"
)

IMMUTABLE_INPUTS = {
    "patchloop/agent/workflow_r21_reliability_successor.py": {
        "bytes": 35_629,
        "file_sha256": "sha256:45e204a4f082a84ac00cceca75ef0be13f2341d5118eeb9c7f23e3967024b5d6",
    },
    "experiments/lean-harness-r21-reliability-public-qualification-20260831-v1.json": {
        "bytes": 6_253,
        "file_sha256": "sha256:6b0f753f26c7e7d2d303c9b82bc192396bc1fbd312c709534927b7b39a4d38df",
        "content_hash": "sha256:4f07dd47a2d7d81580d135018b8400476880d7ce93f1c280d5b9c8f8c97f9275",
    },
    (
        "experiments/rapid-candidate-v33-v25-v27-provider-schema-ab-public-"
        "qualification-20260901-v1.json"
    ): {
        "bytes": 34_163,
        "file_sha256": "sha256:e30991a90e615fbf1b9861bda3b133aedca6296aa47016fb0ec863b462363066",
        "content_hash": "sha256:d2c14105ab67dc1784ce53aa21a2e7e3b1d6f95a1b6a8e5baea4ce7ae7f5394d",
    },
    (
        "reports/rapid-development/artifacts/rapid-public-dev-anyio-v5-provider-"
        "schema-ab-20260901-r24-candidate-v33-halted-public-audit-v1.json"
    ): {
        "bytes": 29_718,
        "file_sha256": "sha256:78c1b54aa2de9c06927c31753dd293b2ddf1fe0b1376f56e0b3ce7870abf2155",
        "content_hash": "sha256:0e6e94aaec6c803a9377ba46e1b25390ef1219871b8ec382e2d53b659bf7c457",
    },
    (
        "reports/rapid-development/rapid-public-dev-anyio-v5-provider-schema-ab-"
        "20260901-r24-a4a8e75dfa0f.jsonl"
    ): {
        "bytes": 26_043,
        "file_sha256": "sha256:604583a194479b7ce6712488604dd75bfe0fa9f65bebfd89d3ba8233479e5746",
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_lifecycle_binding_successor.py",
    "patchloop/agent/workflow_lifecycle_binding_qualification.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_lifecycle_binding_qualification.py",
    "tests/test_workflow_lifecycle_binding_successor.py",
    "tests/test_workflow_lifecycle_binding_runner.py",
    "tests/test_workflow_lifecycle_binding_qualification.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"lifecycle-binding input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _immutable_identity(root: Path, relative: str) -> dict[str, Any]:
    identity = _identity(root, relative)
    expected = IMMUTABLE_INPUTS[relative]
    if "content_hash" in expected:
        try:
            document = json.loads(ensure_within(root, relative).read_bytes())
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("lifecycle-binding immutable JSON is invalid") from exc
        content_hash = document.get("content_hash")
        if content_hash != sha256_json(
            {key: value for key, value in document.items() if key != "content_hash"}
        ):
            raise ContractError("lifecycle-binding immutable content hash differs")
        identity["content_hash"] = content_hash
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"lifecycle-binding immutable input differs: {relative}")
    return identity


def _request_projection():
    catalog = _catalog_v4(source_count=2)
    self_directed = _request(catalog)
    trigger_bound = project_trigger_bound_self_directed_plan_request(
        self_directed.source_request.base_request
    )
    return catalog, project_lifecycle_component_bound_plan_request(trigger_bound)


def _lifecycle_arguments() -> dict[str, Any]:
    arguments = _plan_arguments(co_located=False)
    mutation_span = arguments["causal_mechanism"]["mutation_site"]["source_span_id"]
    execution_span = arguments["readiness_assessment"]["basis_source_span_ids"][-1]
    arguments["lifecycle_component_binding"] = {
        "components": [
            {
                "name": "runner",
                "owner_source_span_id": mutation_span,
                "responsibility": "Own the public lifecycle state transition.",
                "before": "active",
                "after": "interrupted",
            },
            {
                "name": "lease",
                "owner_source_span_id": execution_span,
                "responsibility": "Preserve the public execution lease.",
                "before": "held",
                "after": "released",
            },
        ],
        "transitions": [
            {
                "trigger": "The public interrupt path is observed.",
                "affected_component_indices": [0, 1],
                "evidence_source_span_ids": [mutation_span, execution_span],
                "atomic": True,
            }
        ],
        "atomic_postconditions": [
            {
                "condition": "Runner and lease expose one consistent public state.",
                "evidence_source_span_ids": [mutation_span, execution_span],
                "falsification_observation": "A later public operation sees a stale lease.",
            }
        ],
    }
    return arguments


def _normalize(arguments: dict[str, Any]):
    catalog, request = _request_projection()
    return normalize_lifecycle_component_bound_plan(
        task=_task(),
        catalog=catalog,
        request_projection=request,
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
        history=(),
        raw_arguments=arguments,
    )


def _relation_mismatch(arguments: dict[str, Any]) -> LifecycleRelationMismatch:
    try:
        _normalize(arguments)
    except ContractError as exc:
        raw = exc.details.get("lifecycle_relation_mismatch")
        if raw is None:
            raise ContractError("lifecycle-binding mismatch details are absent") from exc
        return LifecycleRelationMismatch.model_validate_json(canonical_json(raw))
    raise ContractError("lifecycle-binding negative scenario did not reject")


def _feedback_context(details: dict[str, Any]) -> BuiltContext:
    payload = {
        "public_task": {"task_id": "lifecycle-binding-qualification"},
        "phase": "PLAN",
        "checkpoint": None,
        "phase_contract": {"current_phase": "PLAN"},
        "recent_events": [
            {
                "sequence": 17,
                "type": "ToolFailed",
                "actor": "tool-gateway",
                "payload": {
                    "tool": "record_work_plan",
                    "status": "rejected",
                    "error_code": "WORK_PLAN_ADMISSION_REJECTED",
                    "error_message": "public plan is incomplete",
                    "error_details": details,
                    "admission_blocked": True,
                },
            }
        ],
        "execution_signals": {"repeated_calls": []},
        "selected_memory": None,
        "rules": {"private_evaluator_data_unavailable": True},
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    return BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            "schema_version": "context-build-evidence-v11",
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
        },
    )


def _registry_scenario() -> dict[str, Any]:
    _catalog, request = _request_projection()
    lifecycle = request.parameters["properties"]["lifecycle_component_binding"]
    properties = lifecycle["properties"]
    transition = properties["transitions"]["items"]["properties"]
    return {
        "request_hash": request.content_hash,
        "component_fields": sorted(properties["components"]["items"]["properties"]),
        "relation_fields": sorted(properties),
        "owners_field_absent": "owners" not in properties,
        "states_field_absent": "states" not in properties,
        "free_form_affected_components_absent": "affected_components" not in transition,
        "integer_component_references": transition["affected_component_indices"]["items"],
        "semantic_truth_verified": request.semantic_truth_verified,
    }


def _normalization_scenario() -> dict[str, Any]:
    plan, closure, record = _normalize(_lifecycle_arguments())
    return {
        "policy_version": record.policy_version,
        "plan_hash": plan.content_hash,
        "closure_hash": closure.content_hash,
        "record_hash": record.content_hash,
        "component_count": len(record.lifecycle.components),
        "transition_component_indices": list(
            record.lifecycle.transitions[0].affected_component_indices
        ),
        "mutation_owner_component_index": record.mutation_owner_component_index,
        "public_current_diff_source_only": record.public_current_diff_source_only,
        "private_or_hidden_material_used": any(
            (
                record.private_evidence_used,
                record.hidden_evaluator_used,
                record.reference_patch_used,
                record.reasoning_text_used,
            )
        ),
    }


def _exact_feedback_scenario() -> dict[str, Any]:
    arguments = _lifecycle_arguments()
    binding = arguments["lifecycle_component_binding"]
    binding["components"][1]["name"] = "runner"
    binding["components"][1]["after"] = "held"
    binding["transitions"][0]["affected_component_indices"] = [0, 0, 4]
    mismatch = _relation_mismatch(arguments)
    details = _feedback_details()
    details["policy_version"] = "bounded-self-directed-exploration-v1"
    details["reason_codes"] = ["lifecycle_component_relation_invalid"]
    details["lifecycle_relation_mismatch"] = mismatch.model_dump(mode="json")
    compacted = project_lean_context_event_descriptors_v2(_feedback_context(details))
    first = project_lifecycle_plan_admission_feedback_v3(compacted)
    second = project_lifecycle_plan_admission_feedback_v3(compacted)
    projected = json.loads(first.rendered)["recent_events"][0]["payload"]["error_details"][
        "lifecycle_relation_mismatch"
    ]
    tampered = copy.deepcopy(details)
    tampered["lifecycle_relation_mismatch"]["component_count"] = 3
    tamper_rejected = False
    try:
        project_lifecycle_plan_admission_feedback_v3(
            project_lean_context_event_descriptors_v2(_feedback_context(tampered))
        )
    except ContractError:
        tamper_rejected = True
    violation = mismatch.transition_reference_violations[0]
    return {
        "mismatch_hash": mismatch.content_hash,
        "component_count": mismatch.component_count,
        "collision_indices": list(mismatch.component_name_collisions[0].component_indices),
        "unchanged_state_indices": list(mismatch.unchanged_state_component_indices),
        "duplicate_transition_indices": list(violation.duplicate_component_indices),
        "out_of_range_transition_indices": list(violation.out_of_range_component_indices),
        "deterministic": first == second,
        "projected_exact_mismatch": projected == mismatch.model_dump(mode="json"),
        "latest_feedback_bytes": first.evidence.latest_feedback_bytes,
        "feedback_byte_ceiling": MAX_PLAN_FEEDBACK_BYTES_V3,
        "tampered_relation_hash_rejected": tamper_rejected,
        "private_or_hidden_material_included": (first.evidence.private_or_hidden_material_included),
        "raw_reasoning_included": first.evidence.raw_reasoning_included,
    }


def _r24_public_shape(root: Path) -> dict[str, Any]:
    relative = next(
        path for path in IMMUTABLE_INPUTS if path.endswith("halted-public-audit-v1.json")
    )
    document = json.loads(ensure_within(root, relative).read_bytes())
    diagnosis = document["failure_diagnosis"]["v27_lifecycle_plan_admission"]
    boundary = document["evidence_boundary"]
    shape = {
        "status": document["status"],
        "official": document["official"],
        "classification": diagnosis["classification"],
        "affected_started_rows": diagnosis["affected_started_rows"],
        "rejected_plan_attempts": diagnosis["rejected_plan_attempts"],
        "all_owner_state_sets_mismatched": diagnosis["all_owner_state_sets_mismatched"],
        "all_transition_sets_escape_owners": diagnosis["all_transition_sets_escape_owners"],
        "exact_mismatch_feedback_was_absent": not diagnosis[
            "feedback_component_mismatch_projection_present"
        ],
        "semantic_fix_correctness_established": diagnosis["semantic_fix_correctness_established"],
        "public_agent_visible_only": boundary["public_task_and_agent_visible_events_only"],
        "raw_reasoning_read": boundary["raw_reasoning_read"],
        "private_or_hidden_material_read": any(
            (
                boundary["private_task_spec_read"],
                boundary["hidden_evaluator_content_read"],
                boundary["reference_patch_read"],
            )
        ),
    }
    if (
        shape["classification"] != "cross-field-lifecycle-component-binding-friction"
        or shape["affected_started_rows"] != 2
        or shape["rejected_plan_attempts"] != 3
        or not shape["all_owner_state_sets_mismatched"]
        or not shape["all_transition_sets_escape_owners"]
        or not shape["exact_mismatch_feedback_was_absent"]
        or shape["raw_reasoning_read"]
        or shape["private_or_hidden_material_read"]
    ):
        raise ContractError("R24 public lifecycle mismatch shape differs")
    return shape


def build_lifecycle_binding_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    scenarios = {
        "single_component_registry_request": _registry_scenario(),
        "bound_public_plan_record": _normalization_scenario(),
        "exact_relation_mismatch_feedback": _exact_feedback_scenario(),
        "r24_public_mismatch_shape": _r24_public_shape(root),
    }
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 9, 1, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "lean-v28-lifecycle-component-binding-successor",
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V28,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V28,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V28,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V28,
            "lifecycle_binding_policy_version": LIFECYCLE_COMPONENT_BINDING_POLICY,
            "feedback_policy_version": PLAN_ADMISSION_FEEDBACK_POLICY_V3,
        },
        "scenarios": scenarios,
        "validated_test_surfaces": {
            "focused_unit": True,
            "real_shaped_mocked_runner": True,
            "one_retry_exact_feedback": True,
            "second_rejection_stops_before_third_plan_dispatch": True,
            "feedback_restart_recovery": True,
            "durable_component_registry_record": True,
            "v27_predecessor_regression": True,
            "strict_provider_schema_regression": True,
        },
        "source_files": [_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_inputs": [_immutable_identity(root, relative) for relative in IMMUTABLE_INPUTS],
        "evidence_boundary": {
            "public_synthetic_and_sanitized_public_audit_inputs_only": True,
            "raw_reasoning_read_by_builder": False,
            "private_task_spec_read_by_builder": False,
            "hidden_evaluator_content_read_by_builder": False,
            "reference_patch_read_by_builder": False,
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
        "next_gate": "separate-lean-v28-activation-review-if-requested",
    }
    registry = scenarios["single_component_registry_request"]
    feedback = scenarios["exact_relation_mismatch_feedback"]
    if (
        not registry["owners_field_absent"]
        or not registry["states_field_absent"]
        or not registry["free_form_affected_components_absent"]
        or registry["semantic_truth_verified"] is not False
        or not feedback["deterministic"]
        or not feedback["projected_exact_mismatch"]
        or not feedback["tampered_relation_hash_rejected"]
        or feedback["latest_feedback_bytes"] > MAX_PLAN_FEEDBACK_BYTES_V3
    ):
        raise ContractError("lifecycle-binding qualification criteria are incomplete")
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("lifecycle-binding qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_lifecycle_binding_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_lifecycle_binding_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


__all__ = [
    "IMMUTABLE_INPUTS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_lifecycle_binding_qualification",
    "materialize_lifecycle_binding_qualification",
    "qualification_bytes",
]
