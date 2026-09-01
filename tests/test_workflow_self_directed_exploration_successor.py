from __future__ import annotations

import copy

import pytest

from patchloop.agent.tools import TOOL_SCHEMAS_V26
from patchloop.agent.workflow_causal_plan_projection_activation import (
    project_activated_causal_plan_request,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    HANDLER_PATH,
    RUNTIME_PATH,
    _arguments,
    _catalog,
    _task,
)
from patchloop.agent.workflow_plan_contract_compatibility_successor import (
    TriggerBoundSelfDirectedPlanRequest,
    normalize_trigger_bound_self_directed_plan,
    project_trigger_bound_self_directed_plan_request,
)
from patchloop.agent.workflow_self_directed_exploration_successor import (
    EligiblePlanEvidenceCatalogV4,
    InvestigationIntentInput,
    normalize_self_directed_plan,
    project_episode_investigation_target_hashes,
    project_investigation_target,
    project_self_directed_evidence_catalog,
    project_self_directed_exploration_state,
    project_self_directed_plan_request,
    project_self_directed_tool_surface,
    project_self_directed_workflow_decision,
    validate_exploration_stop,
    validate_investigation_action,
)
from patchloop.agent.workflow_semantic_progress_successor import (
    WORKFLOW_POLICY_V15,
    WorkflowDecisionV3,
)
from patchloop.agent.workflow_successor_v2 import EligiblePlanEvidenceCatalogV2
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError
from patchloop.util import sha256_json, utc_now


def _catalog_v2(*, source_count: int = 2) -> EligiblePlanEvidenceCatalogV2:
    source = _catalog(include_failed_check=False)
    source_items = [item for item in source.items if item.kind == "source_read"]
    support_items = [item for item in source.items if item.kind != "source_read"]
    items = tuple(source_items[:source_count] + support_items)
    body = {
        **source.model_dump(mode="python", exclude={"schema_version", "content_hash", "items"}),
        "schema_version": "eligible-plan-evidence-catalog-v2",
        "items": tuple(item.model_dump(mode="python") for item in items),
        "required_trigger_status": "not_required",
        "required_trigger_event_sequence": None,
        "required_trigger_evidence_id": None,
        "model_visible_pinned_event_sequences": (),
        "unavailable_reason": None,
    }
    return EligiblePlanEvidenceCatalogV2.model_validate({**body, "content_hash": sha256_json(body)})


def _decision(*, used: int = 1) -> WorkflowDecisionV3:
    catalog = _catalog_v2()
    body = {
        "schema_version": "lean-workflow-decision-v3",
        "runtime_policy_version": "lean-harness-v15",
        "policy_version": WORKFLOW_POLICY_V15,
        "target": "pre-mutation-exploration",
        "current_diff_hash": catalog.worktree_diff_hash,
        "expected_check_id": None,
        "allowed_tool_names": ("search_files", "read_file", "record_work_plan"),
        "information_actions_in_episode": 0,
        "fresh_current_read": False,
        "corrective_mutations_for_check": 0,
        "review_corrections_used": 0,
        "pre_mutation_actions_used": used,
        "active_plan_hash": None,
        "plan_gate_id": "sha256:" + "4" * 64,
        "plan_admission_recovery_used": False,
        "plan_admission_recovery_remaining": 1,
        "required_trigger_evidence_id": None,
        "revision_trigger": None,
        "terminal_reason": None,
        "configured_max_output_tokens": 12_288,
        "effective_max_output_tokens": 4_096,
        "reasoning_effort": "medium",
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "provider_calls_authorized": False,
        "semantic_progress_state_hash": None,
        "semantic_reset_required": False,
        "required_prior_hypothesis_disposition": None,
    }
    return WorkflowDecisionV3.model_validate({**body, "content_hash": sha256_json(body)})


def _v4_catalog(*, source_count: int = 2) -> EligiblePlanEvidenceCatalogV4:
    return project_self_directed_evidence_catalog(
        base=_catalog_v2(source_count=source_count),
        pin=None,
    )


def _state(*, source_count: int = 2, used: int = 1):
    decision = _decision(used=used)
    catalog = _v4_catalog(source_count=source_count)
    return project_self_directed_exploration_state(
        task=_task(),
        decision=decision,
        catalog=catalog,
        events=(),
        active_work_state=None,
    )


def _linked(span_id: str, symbol: str) -> dict:
    return {
        "source_span_id": span_id,
        "symbol": symbol,
        "observation": "The public source controls one visible lifecycle step.",
        "relationship_to_next": "The current state reaches the next public boundary.",
    }


def _plan_arguments(*, co_located: bool) -> dict:
    arguments = _arguments()
    question = arguments.pop("unknowns")[0]
    if co_located:
        ownership = execution = mutation = "cspan:10:0"
        basis = [mutation]
        intermediate_steps: list[dict] = []
    else:
        ownership = mutation = "cspan:10:0"
        execution = "cspan:11:0"
        basis = [mutation, execution]
        intermediate_steps = [_linked(execution, "handler")]
    arguments["causal_mechanism"]["causal_boundary"] = _linked(ownership, "entry_boundary")
    arguments["causal_mechanism"]["intermediate_steps"] = intermediate_steps
    arguments["causal_mechanism"]["mutation_site"]["source_span_id"] = mutation
    arguments["candidate_source_span_ids"] = [mutation]
    arguments["exploration_state"] = {
        "boundary_coverage": {
            "ownership_boundary_span_ids": [ownership],
            "execution_boundary_span_ids": [execution],
            "mutation_boundary_span_ids": [mutation],
        },
        "invariants": [
            {
                "subject": "Public lifecycle ownership",
                "claim": "The cited source controls the bounded transition.",
                "evidence_source_span_ids": list(dict.fromkeys(basis)),
            }
        ],
        "preservation_obligations": [
            {
                "public_requirement": "Preserve the later visible lifecycle step.",
                "expected_behavior": "Visible checks remain ordered after the edit.",
                "evidence_source_span_ids": [mutation if co_located else execution],
            }
        ],
        "unknown_dispositions": [
            {
                "question": question,
                "disposition": "non_blocking",
                "explanation": "The bounded transition does not depend on this question.",
                "evidence_source_span_ids": [mutation],
            }
        ],
        "open_blocking_unknowns": [],
    }
    arguments["readiness_assessment"] = {
        "readiness_status": "ready_to_plan",
        "sufficiency_mode": "co_located_boundary" if co_located else "multi_range",
        "basis_source_span_ids": basis,
        "sufficiency_rationale": "The current public ranges bind the proposed change.",
        "remaining_unknowns_non_blocking": True,
    }
    return arguments


def _request(catalog: EligiblePlanEvidenceCatalogV4):
    base = project_activated_causal_plan_request(
        task=_task(),
        catalog=catalog,
        trigger="initial",
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
    )
    return project_self_directed_plan_request(base)


def test_trigger_bound_plan_schema_matches_initial_and_revision_admission() -> None:
    initial_source = _request(_v4_catalog())
    initial = project_trigger_bound_self_directed_plan_request(
        initial_source.source_request.base_request
    )
    assert initial.parameters["properties"]["prior_hypothesis_disposition"] == {
        "type": "null",
        "enum": [None],
    }

    revision_base = project_activated_causal_plan_request(
        task=_task(),
        catalog=_catalog(include_failed_check=True),
        trigger="check_failure",
        trigger_check_id="targeted",
        trigger_event_sequence=13,
        cross_reset_trigger=None,
    )
    revision = project_trigger_bound_self_directed_plan_request(revision_base)
    assert revision.parameters["properties"]["prior_hypothesis_disposition"] == {
        "type": "string",
        "enum": ["retained", "refined", "rejected"],
    }


def test_trigger_bound_initial_plan_normalizes_and_tamper_fails_closed() -> None:
    catalog = _v4_catalog()
    source = _request(catalog)
    request = project_trigger_bound_self_directed_plan_request(source.source_request.base_request)
    projected, receipt = normalize_trigger_bound_self_directed_plan(
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
        raw_arguments=_plan_arguments(co_located=False),
    )
    assert projected.prior_hypothesis_disposition is None
    assert receipt.request_projection_hash == request.content_hash

    tampered = request.model_dump(mode="python")
    tampered["parameters"]["properties"]["prior_hypothesis_disposition"] = {
        "type": ["string", "null"],
        "enum": ["retained", "refined", "rejected", None],
    }
    tampered["parameter_schema_hash"] = sha256_json(tampered["parameters"])
    tampered["content_hash"] = sha256_json(
        {key: value for key, value in tampered.items() if key != "content_hash"}
    )
    with pytest.raises(ValueError, match="trigger-bound plan request differs"):
        TriggerBoundSelfDirectedPlanRequest.model_validate(tampered)


def test_first_source_read_exposes_plan_and_optional_further_exploration() -> None:
    catalog = _v4_catalog(source_count=1)
    state = _state(source_count=1)
    assert state is not None
    decision = project_self_directed_workflow_decision(
        base_decision=_decision(),
        state=state,
        source_tool_schemas=tuple(TOOL_SCHEMAS_V26),
        events=(),
    )
    assert set(decision.allowed_tool_names) == {
        "search_files",
        "read_file",
        "record_work_plan",
    }
    assert decision.investigation_intent_required is True
    surface, request = project_self_directed_tool_surface(
        task=_task(),
        decision=decision,
        catalog=catalog,
        state=state,
        source_tool_schemas=tuple(TOOL_SCHEMAS_V26),
        cross_reset_trigger=None,
    )
    assert request is not None
    read_schema = next(
        item for item in surface.selected_tool_schemas if item["name"] == "read_file"
    )
    assert "investigation_intent" in read_schema["parameters"]["required"]


def test_no_source_read_keeps_initial_inspection_free_of_unusable_intent() -> None:
    catalog = _v4_catalog(source_count=0)
    state = _state(source_count=0, used=0)
    assert state is not None and not state.source_spans
    decision = project_self_directed_workflow_decision(
        base_decision=_decision(used=0),
        state=state,
        source_tool_schemas=tuple(TOOL_SCHEMAS_V26),
        events=(),
    )
    assert set(decision.allowed_tool_names) == {"search_files", "read_file"}
    assert decision.investigation_intent_required is False
    surface, request = project_self_directed_tool_surface(
        task=_task(),
        decision=decision,
        catalog=catalog,
        state=state,
        source_tool_schemas=tuple(TOOL_SCHEMAS_V26),
        cross_reset_trigger=None,
    )
    assert request is None
    read_schema = next(
        item for item in surface.selected_tool_schemas if item["name"] == "read_file"
    )
    assert "investigation_intent" not in read_schema["parameters"]["properties"]


@pytest.mark.parametrize("co_located", [False, True])
def test_multi_range_and_co_located_readiness_are_admitted(co_located: bool) -> None:
    catalog = _v4_catalog()
    projected, receipt = normalize_self_directed_plan(
        task=_task(),
        catalog=catalog,
        request_projection=_request(catalog),
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
        history=(),
        raw_arguments=_plan_arguments(co_located=co_located),
    )
    assert tuple(item.source_span_id for item in projected.candidate_source_spans) == (
        "cspan:10:0",
    )
    assert receipt.readiness_assessment.sufficiency_mode == (
        "co_located_boundary" if co_located else "multi_range"
    )


def test_co_located_readiness_requires_preservation_and_falsification() -> None:
    catalog = _v4_catalog()
    missing_preservation = _plan_arguments(co_located=True)
    missing_preservation["exploration_state"]["preservation_obligations"][0][
        "evidence_source_span_ids"
    ] = ["cspan:11:0"]
    with pytest.raises(ContractError) as preservation_error:
        normalize_self_directed_plan(
            task=_task(),
            catalog=catalog,
            request_projection=_request(catalog),
            trigger="initial",
            revision_index=0,
            parent_plan_hash=None,
            trigger_check_id=None,
            trigger_event_sequence=None,
            cross_reset_trigger=None,
            history=(),
            raw_arguments=missing_preservation,
        )
    assert (
        "self_directed_colocated_boundary_invalid"
        in preservation_error.value.details["reason_codes"]
    )

    missing_falsification = _plan_arguments(co_located=True)
    missing_falsification["causal_mechanism"]["falsification_condition"] = ""
    with pytest.raises(ContractError):
        normalize_self_directed_plan(
            task=_task(),
            catalog=catalog,
            request_projection=_request(catalog),
            trigger="initial",
            revision_index=0,
            parent_plan_hash=None,
            trigger_check_id=None,
            trigger_event_sequence=None,
            cross_reset_trigger=None,
            history=(),
            raw_arguments=missing_falsification,
        )


def test_intent_is_provenance_bound_scope_checked_and_duplicate_rejected() -> None:
    state = _state(source_count=1)
    assert state is not None
    span_id = state.source_spans[0].source_span_id
    arguments = {
        "path": RUNTIME_PATH,
        "start_line": 58,
        "end_line": 89,
        "investigation_intent": {
            "status": "need_more_evidence",
            "blocking_question": "Where is the public transition completed?",
            "basis_source_span_ids": [span_id],
            "target_role": "execution_path",
            "expected_information_gain": "This read can locate the completion boundary.",
        },
    }
    intent, target = validate_investigation_action(
        task=_task(),
        state=state,
        tool="read_file",
        arguments=arguments,
    )
    assert isinstance(intent, InvestigationIntentInput)
    with pytest.raises(ContractError) as duplicate:
        validate_investigation_action(
            task=_task(),
            state=state,
            tool="read_file",
            arguments=arguments,
            prior_target_hashes=(target.target_hash,),
        )
    assert duplicate.value.details["reason_codes"] == [
        "self_directed_investigation_target_repeated"
    ]

    outside = copy.deepcopy(arguments)
    outside["path"] = "tests/private.py"
    with pytest.raises(ContractError) as scope:
        validate_investigation_action(
            task=_task(), state=state, tool="read_file", arguments=outside
        )
    assert scope.value.details["reason_codes"] == [
        "self_directed_investigation_target_outside_scope"
    ]


def test_search_event_never_adds_source_coverage() -> None:
    catalog = _v4_catalog(source_count=1)
    state = _state(source_count=1)
    assert state is not None
    before = state.distinct_source_coverage_keys
    assert all(
        item.kind != "source_read" for item in catalog.items if item.kind == "search_support"
    )
    assert before == tuple(item.coverage_key for item in state.source_spans)


def test_limit_offers_plan_or_explicit_stop_and_stop_is_deterministic() -> None:
    state = _state(source_count=1, used=10)
    assert state is not None
    decision = project_self_directed_workflow_decision(
        base_decision=_decision(used=10),
        state=state,
        source_tool_schemas=tuple(TOOL_SCHEMAS_V26),
        events=(),
    )
    assert decision.allowed_tool_names == (
        "record_work_plan",
        "declare_exploration_exhausted",
    )
    arguments = {
        "status": "not_ready",
        "blocking_question": "Which public boundary owns the state transition?",
        "basis_source_span_ids": [state.source_spans[0].source_span_id],
        "reason": "evidence_budget_exhausted",
    }
    assert validate_exploration_stop(state=state, arguments=arguments) == (
        validate_exploration_stop(state=state, arguments=arguments)
    )


def test_investigation_target_inventory_is_idempotent_by_succeeded_event() -> None:
    state = _state(source_count=1)
    assert state is not None
    intent = {
        "status": "need_more_evidence",
        "blocking_question": "Where is the public transition completed?",
        "basis_source_span_ids": [state.source_spans[0].source_span_id],
        "target_role": "execution_path",
        "expected_information_gain": "This read can locate the completion boundary.",
    }
    target = project_investigation_target(
        tool="read_file",
        arguments={"path": HANDLER_PATH, "start_line": 1, "end_line": 20},
    )
    event = RunEvent(
        event_id="evt_intent",
        run_id=state.run_id,
        sequence=12,
        type=EventType.TOOL_SUCCEEDED,
        timestamp=utc_now(),
        actor="tool-gateway",
        correlation_id="action_intent",
        payload={
            "tool": "read_file",
            "status": "succeeded",
            "worktree_diff_hash": state.worktree_diff_hash,
            "self_directed_exploration_policy_version": state.policy_version,
            "investigation_intent": intent,
            "investigation_intent_hash": sha256_json(intent),
            "investigation_target": target.model_dump(mode="json"),
            "investigation_target_hash": target.target_hash,
            "result_artifact": {
                "artifact_id": "artifact_intent",
                "path": "objects/aa/test",
                "media_type": "application/json",
                "bytes": 10,
                "content_hash": "sha256:" + "8" * 64,
            },
        },
    )
    first = project_episode_investigation_target_hashes(
        events=(event,),
        decision=_decision(),
        worktree_diff_hash=state.worktree_diff_hash,
    )
    replay = event.model_copy(
        update={
            "event_id": "evt_intent_replay",
            "sequence": 13,
            "type": EventType.TOOL_REPLAYED,
        }
    )
    recovered = project_episode_investigation_target_hashes(
        events=(event, replay),
        decision=_decision(),
        worktree_diff_hash=state.worktree_diff_hash,
    )
    assert first == recovered == (target.target_hash,)
