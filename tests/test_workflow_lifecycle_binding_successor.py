from __future__ import annotations

import copy
import json

import pytest

from patchloop.agent.context_event_compaction import (
    project_lean_context_event_descriptors_v2,
)
from patchloop.agent.workflow_lifecycle_binding_successor import (
    LIFECYCLE_COMPONENT_BINDING_POLICY,
    LifecycleRelationMismatch,
    normalize_lifecycle_component_bound_plan,
    project_lifecycle_component_bound_plan_request,
    project_lifecycle_plan_admission_feedback_v3,
)
from patchloop.agent.workflow_plan_contract_compatibility_successor import (
    project_trigger_bound_self_directed_plan_request,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json
from tests.test_workflow_plan_admission_feedback_successor import _context, _details
from tests.test_workflow_self_directed_exploration_successor import (
    _plan_arguments,
    _request,
    _task,
    _v4_catalog,
)


def _lifecycle_request():
    catalog = _v4_catalog()
    self_directed = _request(catalog)
    trigger_bound = project_trigger_bound_self_directed_plan_request(
        self_directed.source_request.base_request
    )
    return catalog, project_lifecycle_component_bound_plan_request(trigger_bound)


def _lifecycle_arguments() -> dict:
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


def _normalize(arguments: dict):
    catalog, request = _lifecycle_request()
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


def _relation_error(arguments: dict) -> ContractError:
    with pytest.raises(ContractError) as caught:
        _normalize(arguments)
    assert caught.value.details["reason_codes"] == ["lifecycle_component_relation_invalid"]
    return caught.value


def test_component_registry_schema_defines_names_once_and_uses_integer_refs() -> None:
    _catalog, request = _lifecycle_request()
    lifecycle = request.parameters["properties"]["lifecycle_component_binding"]

    assert set(lifecycle["properties"]) == {
        "components",
        "transitions",
        "atomic_postconditions",
    }
    assert "owners" not in lifecycle["properties"]
    assert "states" not in lifecycle["properties"]
    transition = lifecycle["properties"]["transitions"]["items"]
    assert "affected_components" not in transition["properties"]
    assert transition["properties"]["affected_component_indices"]["items"] == {
        "type": "integer",
        "minimum": 0,
        "maximum": 7,
    }


def test_component_registry_normalizes_to_one_bound_public_record() -> None:
    plan, closure, lifecycle = _normalize(_lifecycle_arguments())

    assert lifecycle.policy_version == LIFECYCLE_COMPONENT_BINDING_POLICY
    assert lifecycle.plan_hash == plan.content_hash
    assert lifecycle.mutation_owner_component_index == 0
    assert lifecycle.lifecycle.transitions[0].affected_component_indices == (0, 1)
    assert lifecycle.mutation_site_span_id in lifecycle.cited_source_span_ids
    assert closure.request_projection_hash != lifecycle.content_hash


def test_relation_rejection_reports_exact_transition_and_component_mismatch() -> None:
    arguments = _lifecycle_arguments()
    arguments["lifecycle_component_binding"]["components"][1]["name"] = "runner"
    arguments["lifecycle_component_binding"]["components"][1]["after"] = "held"
    arguments["lifecycle_component_binding"]["transitions"][0]["affected_component_indices"] = [
        0,
        0,
        4,
    ]

    error = _relation_error(arguments)
    mismatch = LifecycleRelationMismatch.model_validate_json(
        canonical_json(error.details["lifecycle_relation_mismatch"])
    )

    assert mismatch.component_count == 2
    assert mismatch.component_name_collisions[0].component_indices == (0, 1)
    assert mismatch.unchanged_state_component_indices == (1,)
    violation = mismatch.transition_reference_violations[0]
    assert violation.transition_index == 0
    assert violation.duplicate_component_indices == (0,)
    assert violation.out_of_range_component_indices == (4,)


def test_relation_rejection_reports_exact_missing_mutation_owner() -> None:
    arguments = _lifecycle_arguments()
    mutation_span = arguments["causal_mechanism"]["mutation_site"]["source_span_id"]
    execution_span = arguments["readiness_assessment"]["basis_source_span_ids"][-1]
    arguments["lifecycle_component_binding"]["components"][0]["owner_source_span_id"] = (
        execution_span
    )

    error = _relation_error(arguments)
    mismatch = LifecycleRelationMismatch.model_validate_json(
        canonical_json(error.details["lifecycle_relation_mismatch"])
    )

    assert mismatch.mutation_owner_missing is True
    assert mismatch.mutation_site_span_id == mutation_span
    assert mismatch.owner_source_span_ids == (execution_span, execution_span)


def _feedback_details(mismatch: dict) -> dict:
    details = _details()
    details["policy_version"] = "bounded-self-directed-exploration-v1"
    details["reason_codes"] = ["lifecycle_component_relation_invalid"]
    details["lifecycle_relation_mismatch"] = mismatch
    return details


def test_feedback_keeps_latest_exact_public_relation_and_is_deterministic() -> None:
    arguments = _lifecycle_arguments()
    arguments["lifecycle_component_binding"]["transitions"][0]["affected_component_indices"] = [
        0,
        3,
    ]
    mismatch = _relation_error(arguments).details["lifecycle_relation_mismatch"]
    compacted = project_lean_context_event_descriptors_v2(_context(_feedback_details(mismatch)))

    first = project_lifecycle_plan_admission_feedback_v3(compacted)
    second = project_lifecycle_plan_admission_feedback_v3(compacted)
    feedback = json.loads(first.rendered)["recent_events"][0]["payload"]["error_details"]

    assert first == second
    assert feedback["lifecycle_relation_mismatch"] == mismatch
    assert feedback["lifecycle_relation_mismatch"]["component_count"] == 2
    assert feedback["lifecycle_relation_mismatch"]["transition_reference_violations"][0][
        "out_of_range_component_indices"
    ] == [3]
    assert first.evidence.latest_relation_mismatch_hash == mismatch["content_hash"]
    assert first.evidence.private_or_hidden_material_included is False
    assert first.evidence.raw_reasoning_included is False


def test_feedback_fails_closed_on_tampered_relation_hash() -> None:
    arguments = _lifecycle_arguments()
    arguments["lifecycle_component_binding"]["transitions"][0]["affected_component_indices"] = [
        0,
        3,
    ]
    mismatch = copy.deepcopy(_relation_error(arguments).details["lifecycle_relation_mismatch"])
    mismatch["component_count"] = 3
    details = _feedback_details(mismatch)
    compacted = project_lean_context_event_descriptors_v2(_context(details))

    with pytest.raises(ContractError, match="relation feedback is invalid"):
        project_lifecycle_plan_admission_feedback_v3(compacted)


def test_relation_mismatch_hash_covers_exact_machine_readable_details() -> None:
    arguments = _lifecycle_arguments()
    arguments["lifecycle_component_binding"]["transitions"][0]["affected_component_indices"] = [
        0,
        3,
    ]
    mismatch = _relation_error(arguments).details["lifecycle_relation_mismatch"]

    assert mismatch["content_hash"] == sha256_json(
        {key: value for key, value in mismatch.items() if key != "content_hash"}
    )
