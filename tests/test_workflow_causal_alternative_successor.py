from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from patchloop.agent.workflow_causal_alternative_successor import (
    CAUSAL_ALTERNATIVE_POLICY,
    CausalAlternativeAdmissionCheckpoint,
    CausalMechanismHistoryEntry,
    RecordedCausalAlternativePlan,
    initial_causal_alternative_checkpoint,
    project_causal_alternative_input_contract,
    project_mutation_baseline,
    record_causal_alternative_acceptance,
    record_causal_alternative_rejection,
    record_mutation_baseline_restore,
    validate_causal_alternative_plan,
    validate_public_causal_mechanism,
)
from patchloop.agent.workflow_semantic_progress_successor import PublicSemanticProgressState
from patchloop.agent.workflow_successor_v2 import (
    EligiblePlanEvidence,
    EligiblePlanEvidenceCatalog,
    SourceEvidenceProjection,
)
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_json, sha256_text

RUN_ID = "run_causal_alternative"
EMPTY_DIFF = sha256_text("")
DIFF_A = "sha256:" + "a" * 64
DIFF_B = "sha256:" + "b" * 64
FAILURE = "AssertionError: PUBLIC_CASE:synthetic:unchanged"
PRIOR_PATH = "src/package/inner.py"
ALTERNATIVE_PATH = "src/package/outer.py"
MUTATION_PATH = "src/package/handler.py"


def _task() -> PublicTask:
    return PublicTask.model_validate(
        {
            "schema_version": "task-public-v1",
            "task_id": "synthetic-causal-alternative",
            "task_version": 1,
            "split": "smoke",
            "repository": {
                "url": "snapshot://synthetic-causal-alternative",
                "base_commit": "sha256:" + "0" * 64,
                "language": "python",
            },
            "issue": {
                "title": "Synthetic public behavior",
                "description": "Preserve one public behavior through a bounded source change.",
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


def _state() -> PublicSemanticProgressState:
    body = {
        "schema_version": "public-semantic-progress-state-v1",
        "run_id": RUN_ID,
        "worktree_diff_hash": DIFF_B,
        "check_id": "targeted",
        "current_failure_event_sequence": 6,
        "failure_signature": FAILURE,
        "failure_signature_hash": sha256_text(FAILURE),
        "same_signature_failed_diff_count": 2,
        "failure_event_sequences": (3, 6),
        "failed_diff_hashes": (DIFF_A, DIFF_B),
        "semantic_reset_required": True,
        "public_check_output_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return PublicSemanticProgressState.model_validate({**body, "content_hash": sha256_json(body)})


def _event(
    sequence: int,
    event_type: EventType,
    *,
    correlation_id: str | None = None,
    payload: dict | None = None,
) -> RunEvent:
    return RunEvent(
        event_id=f"evt_causal_{sequence}",
        run_id=RUN_ID,
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 26, tzinfo=UTC),
        actor="test",
        correlation_id=correlation_id,
        payload=payload or {},
    )


def _events() -> tuple[RunEvent, ...]:
    return (
        _event(
            1,
            EventType.PATCH_PREPARED,
            correlation_id="mutation-1",
            payload={
                "schema_version": "patch-mutation-intent-v1",
                "content_hash": "sha256:" + "3" * 64,
                "baseline_worktree_diff_hash": EMPTY_DIFF,
                "expected_worktree_diff_hash": DIFF_A,
            },
        ),
        _event(
            2,
            EventType.PATCH_APPLIED,
            correlation_id="mutation-1",
            payload={"patch_hash": "sha256:" + "1" * 64, "worktree_diff_hash": DIFF_A},
        ),
        _event(3, EventType.TOOL_SUCCEEDED, payload={"tool": "run_check"}),
        _event(
            4,
            EventType.PATCH_PREPARED,
            correlation_id="mutation-2",
            payload={
                "schema_version": "patch-mutation-intent-v1",
                "content_hash": "sha256:" + "4" * 64,
                "baseline_worktree_diff_hash": DIFF_A,
                "expected_worktree_diff_hash": DIFF_B,
            },
        ),
        _event(
            5,
            EventType.PATCH_APPLIED,
            correlation_id="mutation-2",
            payload={"patch_hash": "sha256:" + "2" * 64, "worktree_diff_hash": DIFF_B},
        ),
        _event(6, EventType.TOOL_SUCCEEDED, payload={"tool": "run_check"}),
    )


def _read(sequence: int, path: str, start: int, end: int) -> EligiblePlanEvidence:
    source = SourceEvidenceProjection(
        path=path,
        requested_range=(start, end),
        actual_range=(start, end),
        visible_ranges=((start, end),),
        omitted_ranges=(),
        partial_line=False,
        total_lines=300,
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


def _catalog() -> EligiblePlanEvidenceCatalog:
    task = _task()
    items = (
        _read(10, PRIOR_PATH, 10, 20),
        _read(11, ALTERNATIVE_PATH, 30, 40),
        _read(12, MUTATION_PATH, 50, 60),
    )
    body = {
        "schema_version": "eligible-plan-evidence-catalog-v1",
        "run_id": RUN_ID,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": sha256_json(task.model_dump(mode="json")),
        "worktree_diff_hash": EMPTY_DIFF,
        "model_visible_context_hash": "sha256:" + "c" * 64,
        "model_visible_recent_event_sequences": (10, 11, 12),
        "items": tuple(item.model_dump(mode="python") for item in items),
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return EligiblePlanEvidenceCatalog.model_validate({**body, "content_hash": sha256_json(body)})


def _location(path: str, evidence_id: str, start: int, end: int, symbol: str) -> dict:
    return {
        "path": path,
        "start_line": start,
        "end_line": end,
        "read_evidence_id": evidence_id,
        "symbol": symbol,
    }


def _prior_raw(*, summary: str = "The inner boundary controls the behavior.") -> dict:
    location = _location(PRIOR_PATH, "pev:10", 10, 20, "inner_boundary")
    return {
        "summary": summary,
        "causal_path": [
            {
                "role": "boundary_and_mutation_site",
                "location": location,
                "observation": "The visible source makes the inner boundary the decision site.",
                "relationship_to_next": None,
            }
        ],
        "mutation_site_rationale": "Changing this decision site should alter the public behavior.",
        "expected_observable_effect": "The targeted public check should change outcome.",
        "falsification_condition": "The same public failure persists after the bounded edit.",
    }


def _alternative_raw() -> dict:
    boundary = _location(ALTERNATIVE_PATH, "pev:11", 30, 40, "outer_boundary")
    mutation = _location(MUTATION_PATH, "pev:12", 50, 60, "handler_boundary")
    return {
        "summary": "The outer boundary controls whether the handler reaches the expected state.",
        "causal_path": [
            {
                "role": "causal_boundary",
                "location": boundary,
                "observation": "The outer source owns the entry and exit ordering.",
                "relationship_to_next": "Its branch determines when the handler is invoked.",
            },
            {
                "role": "mutation_site",
                "location": mutation,
                "observation": "The handler commits the externally visible state.",
                "relationship_to_next": None,
            },
        ],
        "mutation_site_rationale": (
            "Editing the handler boundary changes the state observed by the public check."
        ),
        "expected_observable_effect": "The targeted check observes the completed state once.",
        "falsification_condition": "The targeted check retains the same bounded failure signature.",
    }


def _history():
    task = _task()
    catalog = _catalog()
    mechanism = validate_public_causal_mechanism(
        task=task,
        catalog=catalog,
        foundation_evidence_ids=["pev:10"],
        raw_mechanism=_prior_raw(),
    )
    return (
        CausalMechanismHistoryEntry(
            revision_index=0,
            plan_hash="sha256:" + "1" * 64,
            parent_plan_hash=None,
            trigger="initial",
            mechanism=mechanism,
        ),
        CausalMechanismHistoryEntry(
            revision_index=1,
            plan_hash="sha256:" + "2" * 64,
            parent_plan_hash="sha256:" + "1" * 64,
            trigger="check_failure",
            mechanism=mechanism,
        ),
    )


def _baseline_and_receipt():
    baseline = project_mutation_baseline(
        semantic_progress_state=_state(),
        events=_events(),
    )
    receipt = record_mutation_baseline_restore(
        baseline=baseline,
        observed_before_diff_hash=DIFF_B,
        observed_after_diff_hash=EMPTY_DIFF,
        restored_action_ids=("mutation-2", "mutation-1"),
        restored_intent_hashes=("sha256:" + "4" * 64, "sha256:" + "3" * 64),
    )
    return baseline, receipt


def _arguments(raw_mechanism: dict, *, candidate_path=MUTATION_PATH, evidence_id="pev:12"):
    history = _history()
    return {
        "observation_status": "visible_check_failed",
        "hypothesis": "A different public causal boundary controls the failed behavior.",
        "foundation_evidence_ids": ["pev:11", "pev:12"],
        "supporting_evidence_ids": [],
        "candidate_files": [{"path": candidate_path, "read_evidence_id": evidence_id}],
        "intended_change": "Change only the newly evidenced mutation boundary.",
        "expected_behavior": "Targeted then upstream public checks pass in order.",
        "unknowns": ["The public check may expose another boundary after this edit."],
        "prior_causal_mechanism_hash": history[-1].mechanism.content_hash,
        "alternative_causal_mechanism": raw_mechanism,
    }


def _validate(arguments: dict):
    baseline, receipt = _baseline_and_receipt()
    return validate_causal_alternative_plan(
        task=_task(),
        catalog=_catalog(),
        semantic_progress_state=_state(),
        baseline=baseline,
        restore_receipt=receipt,
        history=_history(),
        parent_plan_hash="sha256:" + "2" * 64,
        arguments=arguments,
    )


def test_schema_uses_generic_causal_path_and_mutation_site_rationale() -> None:
    raw = _alternative_raw()

    mechanism = validate_public_causal_mechanism(
        task=_task(),
        catalog=_catalog(),
        foundation_evidence_ids=["pev:11", "pev:12"],
        raw_mechanism=raw,
    )

    assert "mutation_site_rationale" in raw
    assert "causal_path" in raw
    assert "why_exception_reaches_mutation_site" not in json.dumps(raw)
    assert mechanism.symbol_text_used_for_admission is False
    assert mechanism.prose_used_for_distinctness is False

    contract = project_causal_alternative_input_contract(
        catalog=_catalog(),
        prior_causal_mechanism_hash=_history()[-1].mechanism.content_hash,
    )
    serialized = json.dumps(contract.parameters, sort_keys=True)
    mechanism_properties = contract.parameters["properties"]["alternative_causal_mechanism"][
        "properties"
    ]
    assert "mutation_site_rationale" in mechanism_properties
    assert "why_exception_reaches_mutation_site" not in serialized
    assert contract.task_specific_field_names == ()
    assert contract.runtime_surface_activated is False


def test_exact_mutation_chain_projects_and_restores_in_reverse_without_erasing_trace() -> None:
    baseline, receipt = _baseline_and_receipt()

    assert baseline.baseline_diff_hash == EMPTY_DIFF
    assert baseline.current_failed_diff_hash == DIFF_B
    assert baseline.forward_action_ids == ("mutation-1", "mutation-2")
    assert baseline.restore_action_ids == ("mutation-2", "mutation-1")
    assert receipt.exact_restore_verified is True
    assert receipt.preserved_failure_event_sequences == (3, 6)
    assert receipt.append_only_events_deleted is False

    with pytest.raises(ContractError) as exc_info:
        record_mutation_baseline_restore(
            baseline=baseline,
            observed_before_diff_hash=DIFF_B,
            observed_after_diff_hash=DIFF_A,
            restored_action_ids=("mutation-2", "mutation-1"),
            restored_intent_hashes=("sha256:" + "4" * 64, "sha256:" + "3" * 64),
        )
    assert exc_info.value.details["reason_codes"] == ["mutation_baseline_restore_mismatch"]


def test_prose_or_symbol_relabel_cannot_reuse_an_exhausted_causal_boundary() -> None:
    relabeled = _prior_raw(summary="A completely different prose label.")
    relabeled["causal_path"][0]["location"]["symbol"] = "renamed_boundary"
    arguments = _arguments(relabeled, candidate_path=PRIOR_PATH, evidence_id="pev:10")
    arguments["foundation_evidence_ids"] = ["pev:10"]

    with pytest.raises(ContractError) as exc_info:
        _validate(arguments)

    assert exc_info.value.details["reason_codes"] == ["causal_boundary_already_exhausted"]


def test_non_exhausted_public_boundary_admits_one_general_causal_alternative() -> None:
    plan, normalization = _validate(_arguments(_alternative_raw()))

    assert plan.policy_version == CAUSAL_ALTERNATIVE_POLICY
    assert plan.prior_hypothesis_disposition == "rejected"
    assert plan.causal_contrast.alternative_boundary_is_non_exhausted is True
    assert plan.causal_contrast.mechanism_family_changed is True
    assert plan.causal_contrast.prose_only_relabel_accepted is False
    assert plan.alternative_causal_mechanism.mutation_site_rationale.startswith("Editing")
    assert plan.candidate_files[0].path == MUTATION_PATH
    assert plan.planned_check_ids == ("targeted", "upstream")
    assert normalization.canonical_candidate_count == 1


def test_unseen_or_partially_unseen_source_location_fails_closed() -> None:
    raw = _alternative_raw()
    raw["causal_path"][0]["location"]["end_line"] = 41

    with pytest.raises(ContractError) as exc_info:
        _validate(_arguments(raw))

    assert exc_info.value.details["reason_codes"] == ["causal_source_range_not_visible"]


def test_one_recovery_slot_survives_restart_and_second_relabel_terminates() -> None:
    baseline, receipt = _baseline_and_receipt()
    checkpoint = initial_causal_alternative_checkpoint(
        semantic_progress_state_hash=_state().content_hash,
        restore_receipt_hash=receipt.content_hash,
        parent_plan_hash="sha256:" + "2" * 64,
    )
    first = record_causal_alternative_rejection(
        checkpoint,
        reason_codes=("causal_boundary_already_exhausted",),
    )
    restored = CausalAlternativeAdmissionCheckpoint.model_validate_json(first.model_dump_json())
    second = record_causal_alternative_rejection(
        restored,
        reason_codes=("causal_boundary_already_exhausted",),
    )

    assert restored == first
    assert first.status == "active"
    assert first.recovery_remaining == 0
    assert second.status == "terminal"
    assert second.terminal_reason == "causal_alternative_admission_repeated"
    assert second.provider_dispatch_after_terminal is False
    with pytest.raises(RecoveryError):
        record_causal_alternative_rejection(
            second,
            reason_codes=("causal_boundary_already_exhausted",),
        )


def test_valid_alternative_acceptance_is_durable_and_idempotent_by_hash() -> None:
    plan, _ = _validate(_arguments(_alternative_raw()))
    _, receipt = _baseline_and_receipt()
    checkpoint = initial_causal_alternative_checkpoint(
        semantic_progress_state_hash=_state().content_hash,
        restore_receipt_hash=receipt.content_hash,
        parent_plan_hash="sha256:" + "2" * 64,
    )

    accepted = record_causal_alternative_acceptance(checkpoint, plan_hash=plan.content_hash)
    replayed = CausalAlternativeAdmissionCheckpoint.model_validate_json(accepted.model_dump_json())

    assert accepted.status == "accepted"
    assert accepted.accepted_plan_hash == plan.content_hash
    assert replayed == accepted
    with pytest.raises(RecoveryError):
        record_causal_alternative_acceptance(accepted, plan_hash=plan.content_hash)


def test_tampered_history_and_recorded_candidate_binding_fail_closed() -> None:
    baseline, receipt = _baseline_and_receipt()
    history = _history()
    tampered_history = (
        history[0],
        CausalMechanismHistoryEntry(
            revision_index=1,
            plan_hash=history[1].plan_hash,
            parent_plan_hash="sha256:" + "9" * 64,
            trigger="check_failure",
            mechanism=history[1].mechanism,
        ),
    )
    with pytest.raises(ContractError) as exc_info:
        validate_causal_alternative_plan(
            task=_task(),
            catalog=_catalog(),
            semantic_progress_state=_state(),
            baseline=baseline,
            restore_receipt=receipt,
            history=tampered_history,
            parent_plan_hash=history[1].plan_hash,
            arguments=_arguments(_alternative_raw()),
        )
    assert exc_info.value.details["reason_codes"] == ["causal_history_invalid"]

    plan, _ = _validate(_arguments(_alternative_raw()))
    raw = plan.model_dump(mode="python", exclude={"content_hash"})
    raw["candidate_files"][0]["read_evidence_id"] = "pev:11"
    with pytest.raises(ValueError, match="binding differs"):
        RecordedCausalAlternativePlan.model_validate({**raw, "content_hash": sha256_json(raw)})
