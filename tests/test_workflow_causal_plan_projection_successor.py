from __future__ import annotations

import copy
import json

import pytest

from patchloop.agent.workflow_causal_plan_projection_successor import (
    CausalPlanRequestProjection,
    RecordedCausalPlanV2,
    normalize_causal_plan_request,
    project_causal_plan_request,
    project_eligible_causal_source_spans,
)
from patchloop.agent.workflow_successor_v2 import (
    CheckEvidenceProjection,
    EligiblePlanEvidence,
    EligiblePlanEvidenceCatalog,
    SearchEvidenceProjection,
    SourceEvidenceProjection,
)
from patchloop.contracts import PublicTask
from patchloop.errors import ContractError
from patchloop.util import sha256_json, sha256_text

RUN_ID = "run_causal_projection"
EMPTY_DIFF = sha256_text("")
RUNTIME_PATH = "src/package/runtime.py"
HANDLER_PATH = "src/package/handler.py"


def _task() -> PublicTask:
    return PublicTask.model_validate(
        {
            "schema_version": "task-public-v1",
            "task_id": "synthetic-causal-projection",
            "task_version": 1,
            "split": "smoke",
            "repository": {
                "url": "snapshot://synthetic-causal-projection",
                "base_commit": "sha256:" + "0" * 64,
                "language": "python",
            },
            "issue": {
                "title": "Synthetic public behavior",
                "description": "Preserve a public lifecycle behavior through a bounded edit.",
            },
            "constraints": {
                "allowed_paths": ["src/**/*.py"],
                "forbidden_paths": ["tests/**"],
                "max_changed_files": 2,
                "max_diff_lines": 100,
                "dependency_changes_allowed": False,
                "public_api_changes_allowed": False,
            },
            "visible_checks": [
                {
                    "id": "targeted",
                    "command": ["python", "-m", "synthetic_targeted"],
                    "timeout_seconds": 30,
                },
                {
                    "id": "upstream",
                    "command": ["python", "-m", "synthetic_upstream"],
                    "timeout_seconds": 30,
                },
            ],
            "tags": ["synthetic", "public"],
        }
    )


def _read(sequence: int, path: str, ranges: tuple[tuple[int, int], ...]) -> EligiblePlanEvidence:
    source = SourceEvidenceProjection(
        path=path,
        requested_range=(ranges[0][0], ranges[-1][1]),
        actual_range=(ranges[0][0], ranges[-1][1]),
        visible_ranges=ranges,
        omitted_ranges=(),
        partial_line=False,
        total_lines=400,
        file_content_hash="sha256:" + f"{sequence:064x}",
    )
    return EligiblePlanEvidence.model_validate(
        {
            "evidence_id": f"pev:{sequence}",
            "kind": "source_read",
            "role": "foundation",
            "run_id": RUN_ID,
            "worktree_diff_hash": EMPTY_DIFF,
            "canonical_event_sequence": sequence,
            "model_visible_event_sequences": (sequence,),
            "replay_alias_event_sequences": (),
            "artifact_hash": "sha256:" + f"{sequence + 100:064x}",
            "visible_projection_hash": sha256_json(source.model_dump(mode="json")),
            "source": source.model_dump(mode="python"),
            "check": None,
            "diff_review": None,
            "search": None,
        }
    )


def _failed_check(sequence: int = 13) -> EligiblePlanEvidence:
    check = CheckEvidenceProjection(
        check_id="targeted",
        check_index=0,
        invocation_status="completed",
        behavior_status="failed",
        passed=False,
        timed_out=False,
    )
    return EligiblePlanEvidence.model_validate(
        {
            "evidence_id": f"pev:{sequence}",
            "kind": "targeted_check_result",
            "role": "foundation",
            "run_id": RUN_ID,
            "worktree_diff_hash": EMPTY_DIFF,
            "canonical_event_sequence": sequence,
            "model_visible_event_sequences": (sequence,),
            "replay_alias_event_sequences": (),
            "artifact_hash": "sha256:" + f"{sequence + 100:064x}",
            "visible_projection_hash": sha256_json(check.model_dump(mode="json")),
            "source": None,
            "check": check.model_dump(mode="python"),
            "diff_review": None,
            "search": None,
        }
    )


def _search(sequence: int = 14) -> EligiblePlanEvidence:
    search = SearchEvidenceProjection(
        query_hash="sha256:" + "e" * 64,
        path_glob="src/**/*.py",
        match_count=2,
        truncated=False,
    )
    return EligiblePlanEvidence.model_validate(
        {
            "evidence_id": f"pev:{sequence}",
            "kind": "search_support",
            "role": "support",
            "run_id": RUN_ID,
            "worktree_diff_hash": EMPTY_DIFF,
            "canonical_event_sequence": sequence,
            "model_visible_event_sequences": (sequence,),
            "replay_alias_event_sequences": (),
            "artifact_hash": "sha256:" + f"{sequence + 100:064x}",
            "visible_projection_hash": sha256_json(search.model_dump(mode="json")),
            "source": None,
            "check": None,
            "diff_review": None,
            "search": search.model_dump(mode="python"),
        }
    )


def _catalog(*, include_failed_check: bool = False) -> EligiblePlanEvidenceCatalog:
    task = _task()
    items = [
        _read(10, RUNTIME_PATH, ((20, 57), (90, 118))),
        _read(11, HANDLER_PATH, ((120, 170),)),
    ]
    if include_failed_check:
        items.append(_failed_check())
    items.append(_search())
    body = {
        "schema_version": "eligible-plan-evidence-catalog-v1",
        "run_id": RUN_ID,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": sha256_json(task.model_dump(mode="json")),
        "worktree_diff_hash": EMPTY_DIFF,
        "model_visible_context_hash": "sha256:" + "c" * 64,
        "model_visible_recent_event_sequences": tuple(
            item.canonical_event_sequence for item in items
        ),
        "items": tuple(item.model_dump(mode="python") for item in items),
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return EligiblePlanEvidenceCatalog.model_validate({**body, "content_hash": sha256_json(body)})


def _linked(span_id: str, name: str) -> dict:
    return {
        "source_span_id": span_id,
        "symbol": name,
        "observation": f"The public source at {name} controls the visible lifecycle step.",
        "relationship_to_next": "This state is forwarded to the next public source boundary.",
    }


def _arguments(*, same_boundary_and_mutation: bool = True) -> dict:
    mutation_span = "cspan:10:0" if same_boundary_and_mutation else "cspan:11:0"
    return {
        "hypothesis": (
            "The public boundary and final state transition jointly control the behavior."
        ),
        "supporting_evidence_ids": ["pev:14"],
        "candidate_source_span_ids": [mutation_span],
        "intended_change": "Adjust only the evidence-bound state transition.",
        "expected_behavior": "The targeted and upstream public checks pass in order.",
        "unknowns": ["A later public check may reveal another lifecycle boundary."],
        "prior_hypothesis_disposition": None,
        "causal_mechanism": {
            "summary": (
                "The entry boundary propagates state through the handler to the mutation site."
            ),
            "causal_boundary": _linked("cspan:10:0", "entry_boundary"),
            "intermediate_steps": [_linked("cspan:11:0", "handler")],
            "mutation_site": {
                "source_span_id": mutation_span,
                "symbol": "state_transition",
                "observation": "This public source span commits the externally visible state.",
            },
            "mutation_site_rationale": "The bounded edit changes the observed transition.",
            "expected_observable_effect": "The targeted check observes one completed transition.",
            "falsification_condition": "The same public failure persists after the edit.",
        },
    }


def _normalize(arguments: dict | None = None):
    return normalize_causal_plan_request(
        task=_task(),
        catalog=_catalog(),
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
        raw_arguments=_arguments() if arguments is None else arguments,
    )


def test_request_surface_uses_exact_span_ids_and_omits_server_invariants() -> None:
    projection = project_causal_plan_request(task=_task(), catalog=_catalog(), trigger="initial")
    parameters = json.dumps(projection.parameters, sort_keys=True)

    assert [item.source_span_id for item in projection.source_span_catalog.spans] == [
        "cspan:10:0",
        "cspan:10:1",
        "cspan:11:0",
    ]
    assert projection.observation_status == "static_source"
    assert projection.observation_evidence_id is None
    for forbidden in (
        '"observation_status"',
        '"foundation_evidence_ids"',
        '"candidate_files"',
        '"planned_check_ids"',
        '"role"',
        '"path"',
        '"start_line"',
        '"end_line"',
        '"read_evidence_id"',
    ):
        assert forbidden not in parameters


def test_server_assigns_roles_final_null_and_static_observation() -> None:
    plan = _normalize()

    assert plan.observation_status == "static_source"
    assert tuple(step.role for step in plan.causal_mechanism.causal_path) == (
        "causal_boundary",
        "intermediate",
        "mutation_site",
    )
    assert tuple(step.ordinal for step in plan.causal_mechanism.causal_path) == (0, 1, 2)
    assert plan.causal_mechanism.causal_path[-1].relationship_to_next is None
    assert plan.planned_check_ids == ("targeted", "upstream")
    assert {item.evidence_id for item in plan.foundation_evidence} == {"pev:10", "pev:11"}


def test_repeated_boundary_and_mutation_location_is_valid_and_deterministic() -> None:
    first = _normalize()
    second = _normalize()

    assert first == second
    keys = first.causal_mechanism.source_coverage_keys
    assert keys[0] == keys[-1]
    assert first.causal_mechanism.repeated_source_locations_allowed is True


def test_model_cannot_supply_old_role_final_relationship_or_observation_status() -> None:
    arguments = _arguments()
    arguments["observation_status"] = "targeted_check_failed"
    arguments["causal_mechanism"]["mutation_site"]["role"] = "mutation_site"
    arguments["causal_mechanism"]["mutation_site"]["relationship_to_next"] = "extra"

    with pytest.raises(ContractError) as exc_info:
        _normalize(arguments)

    assert exc_info.value.details["reason_codes"] == ["causal_plan_input_shape_invalid"]


def test_forged_or_foreign_span_id_fails_closed() -> None:
    arguments = _arguments()
    arguments["causal_mechanism"]["mutation_site"]["source_span_id"] = "cspan:84:0"

    with pytest.raises(ContractError) as exc_info:
        _normalize(arguments)

    assert exc_info.value.details["reason_codes"] == ["causal_source_span_ineligible"]


def test_candidate_must_be_one_of_the_bound_mechanism_spans() -> None:
    arguments = _arguments(same_boundary_and_mutation=False)
    arguments["candidate_source_span_ids"] = ["cspan:10:1"]

    with pytest.raises(ContractError) as exc_info:
        _normalize(arguments)

    assert exc_info.value.details["reason_codes"] == ["causal_candidate_not_in_mechanism"]


def test_failed_check_revision_derives_observation_and_pins_trigger() -> None:
    arguments = _arguments()
    arguments["prior_hypothesis_disposition"] = "rejected"
    plan = normalize_causal_plan_request(
        task=_task(),
        catalog=_catalog(include_failed_check=True),
        trigger="check_failure",
        revision_index=1,
        parent_plan_hash="sha256:" + "a" * 64,
        trigger_check_id="targeted",
        trigger_event_sequence=13,
        raw_arguments=arguments,
    )

    assert plan.observation_status == "visible_check_failed"
    assert plan.observation_evidence is not None
    assert plan.observation_evidence.evidence_id == "pev:13"
    assert "pev:13" in {item.evidence_id for item in plan.foundation_evidence}


def test_wrong_revision_trigger_and_initial_disposition_fail_closed() -> None:
    arguments = _arguments()
    arguments["prior_hypothesis_disposition"] = "rejected"
    with pytest.raises(ContractError) as trigger_error:
        normalize_causal_plan_request(
            task=_task(),
            catalog=_catalog(include_failed_check=True),
            trigger="check_failure",
            revision_index=1,
            parent_plan_hash="sha256:" + "a" * 64,
            trigger_check_id="upstream",
            trigger_event_sequence=13,
            raw_arguments=arguments,
        )
    assert trigger_error.value.details["reason_codes"] == ["causal_observation_trigger_invalid"]

    with pytest.raises(ContractError) as initial_error:
        _normalize(arguments)
    assert initial_error.value.details["reason_codes"] == ["causal_plan_revision_binding_invalid"]


def test_span_catalog_preserves_only_visible_ranges_and_exact_artifact_binding() -> None:
    spans = project_eligible_causal_source_spans(task=_task(), catalog=_catalog())

    first, second, third = spans.spans
    assert (first.start_line, first.end_line) == (20, 57)
    assert (second.start_line, second.end_line) == (90, 118)
    assert first.read_evidence_id == second.read_evidence_id == "pev:10"
    assert third.read_evidence_id == "pev:11"
    assert first.artifact_hash != third.artifact_hash


def test_tampered_catalog_hash_is_rejected_before_projection() -> None:
    catalog = _catalog().model_dump(mode="python")
    catalog["items"][0]["worktree_diff_hash"] = "sha256:" + "f" * 64

    with pytest.raises(ValueError):
        EligiblePlanEvidenceCatalog.model_validate(catalog)


def test_normalization_does_not_mutate_model_arguments() -> None:
    arguments = _arguments()
    before = copy.deepcopy(arguments)

    _normalize(arguments)

    assert arguments == before


def test_request_and_recorded_plan_round_trip_for_durable_restart() -> None:
    projection = project_causal_plan_request(task=_task(), catalog=_catalog(), trigger="initial")
    plan = _normalize()

    assert (
        CausalPlanRequestProjection.model_validate(projection.model_dump(mode="python"))
        == projection
    )
    assert RecordedCausalPlanV2.model_validate(plan.model_dump(mode="python")) == plan
