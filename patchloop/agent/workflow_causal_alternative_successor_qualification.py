"""Deterministic zero-call qualification for the public causal-alternative gate."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.workflow_causal_alternative_successor import (
    CAUSAL_ALTERNATIVE_POLICY,
    CausalAlternativeAdmissionCheckpoint,
    CausalMechanismHistoryEntry,
    MutationBaselineProjection,
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
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

SCHEMA_VERSION = "lean-causal-alternative-successor-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-causal-alternative-public-qualification-20260826-v1.json"
)
RUN_ID = "run_causal_alternative_qualification"
EMPTY_DIFF = sha256_text("")
DIFF_A = "sha256:" + "a" * 64
DIFF_B = "sha256:" + "b" * 64
FAILURE = "AssertionError: PUBLIC_CASE:synthetic:unchanged"
PRIOR_PATH = "src/package/inner.py"
ALTERNATIVE_PATH = "src/package/outer.py"
MUTATION_PATH = "src/package/handler.py"

SOURCE_FILES = (
    "patchloop/agent/workflow_causal_alternative_successor.py",
    "patchloop/agent/workflow_causal_alternative_successor_qualification.py",
    "scripts/build_lean_harness_causal_alternative_qualification.py",
    "tests/test_workflow_causal_alternative_successor.py",
    "tests/test_workflow_causal_alternative_successor_qualification.py",
)

IMMUTABLE_PREDECESSORS = {
    "experiments/lean-harness-candidate-binding-public-qualification-20260825-v1.json": {
        "bytes": 5_218,
        "file_sha256": ("sha256:55038c7be91138c1863e59f37169276974960255978c87ad94b1b574acf0a2d1"),
        "content_hash": ("sha256:9e973d1b7976148861af71399d5cfe6e43d436eaff713f3ed171dbb94fc88b4c"),
    },
    (
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-semantic-progress-ab-20260825-r12-terminal-diagnosis-v1.json"
    ): {
        "bytes": 17_022,
        "file_sha256": ("sha256:633154b9e505a7bf436caf17502a8364782798bc5cbb557f09f6fc69e3814d45"),
        "content_hash": ("sha256:20b2601bd6a92ab4e982deb2ef079712dba46817859fb18d1d960ae5e8a27b49"),
    },
}


def _identity(root: Path, relative: str, *, json_content: bool = False) -> dict[str, Any]:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise ContractError(f"causal-alternative qualification input is unavailable: {relative}")
    raw = path.read_bytes()
    result: dict[str, Any] = {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }
    if json_content:
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("causal-alternative predecessor is not canonical JSON") from exc
        content_hash = document.get("content_hash")
        if content_hash != sha256_json(
            {key: value for key, value in document.items() if key != "content_hash"}
        ):
            raise ContractError("causal-alternative predecessor content hash differs")
        result["content_hash"] = content_hash
    return result


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
    payload: dict[str, Any] | None = None,
) -> RunEvent:
    return RunEvent(
        event_id=f"evt_qualification_{sequence}",
        run_id=RUN_ID,
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 26, tzinfo=UTC),
        actor="qualification",
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


def _catalog(task: PublicTask) -> EligiblePlanEvidenceCatalog:
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


def _location(path: str, evidence_id: str, start: int, end: int, symbol: str) -> dict[str, Any]:
    return {
        "path": path,
        "start_line": start,
        "end_line": end,
        "read_evidence_id": evidence_id,
        "symbol": symbol,
    }


def _prior_raw(*, summary: str = "The inner boundary controls the behavior.") -> dict[str, Any]:
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
        "mutation_site_rationale": "Changing this site should alter the public behavior.",
        "expected_observable_effect": "The targeted public check should change outcome.",
        "falsification_condition": "The same public failure persists after the bounded edit.",
    }


def _alternative_raw() -> dict[str, Any]:
    boundary = _location(ALTERNATIVE_PATH, "pev:11", 30, 40, "outer_boundary")
    mutation = _location(MUTATION_PATH, "pev:12", 50, 60, "handler_boundary")
    return {
        "summary": "The outer boundary controls whether the handler reaches the expected state.",
        "causal_path": [
            {
                "role": "causal_boundary",
                "location": boundary,
                "observation": "The outer source owns entry and exit ordering.",
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
        "falsification_condition": "The targeted check retains the same failure signature.",
    }


def _history(task: PublicTask, catalog: EligiblePlanEvidenceCatalog):
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


def _arguments(prior_hash: str, mechanism: dict[str, Any]) -> dict[str, Any]:
    return {
        "observation_status": "visible_check_failed",
        "hypothesis": "A different public causal boundary controls the failed behavior.",
        "foundation_evidence_ids": ["pev:11", "pev:12"],
        "supporting_evidence_ids": [],
        "candidate_files": [{"path": MUTATION_PATH, "read_evidence_id": "pev:12"}],
        "intended_change": "Change only the newly evidenced mutation boundary.",
        "expected_behavior": "Targeted then upstream public checks pass in order.",
        "unknowns": ["Another public boundary may be exposed after this edit."],
        "prior_causal_mechanism_hash": prior_hash,
        "alternative_causal_mechanism": mechanism,
    }


def _reason_codes(exc: ContractError) -> list[str]:
    values = exc.details.get("reason_codes", [])
    return list(values) if isinstance(values, list) else []


def _scenarios() -> dict[str, Any]:
    task = _task()
    state = _state()
    catalog = _catalog(task)
    history = _history(task, catalog)
    parent_hash = history[-1].plan_hash
    input_contract = project_causal_alternative_input_contract(
        catalog=catalog,
        prior_causal_mechanism_hash=history[-1].mechanism.content_hash,
    )
    baseline = project_mutation_baseline(semantic_progress_state=state, events=_events())
    receipt = record_mutation_baseline_restore(
        baseline=baseline,
        observed_before_diff_hash=DIFF_B,
        observed_after_diff_hash=EMPTY_DIFF,
        restored_action_ids=("mutation-2", "mutation-1"),
        restored_intent_hashes=("sha256:" + "4" * 64, "sha256:" + "3" * 64),
    )

    relabeled = _prior_raw(summary="Different prose for the same source boundary.")
    relabeled["causal_path"][0]["location"]["symbol"] = "renamed_boundary"
    same_family_arguments = _arguments(history[-1].mechanism.content_hash, relabeled)
    same_family_arguments["foundation_evidence_ids"] = ["pev:10"]
    same_family_arguments["candidate_files"] = [{"path": PRIOR_PATH, "read_evidence_id": "pev:10"}]
    try:
        validate_causal_alternative_plan(
            task=task,
            catalog=catalog,
            semantic_progress_state=state,
            baseline=baseline,
            restore_receipt=receipt,
            history=history,
            parent_plan_hash=parent_hash,
            arguments=same_family_arguments,
        )
    except ContractError as exc:
        same_family_reason_codes = _reason_codes(exc)
    else:
        raise ContractError("same-family causal relabel was accepted")

    alternative, normalization = validate_causal_alternative_plan(
        task=task,
        catalog=catalog,
        semantic_progress_state=state,
        baseline=baseline,
        restore_receipt=receipt,
        history=history,
        parent_plan_hash=parent_hash,
        arguments=_arguments(history[-1].mechanism.content_hash, _alternative_raw()),
    )

    checkpoint = initial_causal_alternative_checkpoint(
        semantic_progress_state_hash=state.content_hash,
        restore_receipt_hash=receipt.content_hash,
        parent_plan_hash=parent_hash,
    )
    first_rejection = record_causal_alternative_rejection(
        checkpoint,
        reason_codes=("causal_boundary_already_exhausted",),
    )
    restored_checkpoint = CausalAlternativeAdmissionCheckpoint.model_validate_json(
        canonical_json(first_rejection.model_dump(mode="json"))
    )
    second_rejection = record_causal_alternative_rejection(
        restored_checkpoint,
        reason_codes=("causal_boundary_already_exhausted",),
    )
    accepted = record_causal_alternative_acceptance(
        checkpoint,
        plan_hash=alternative.content_hash,
    )

    tampered_restore_reason_codes: list[str] = []
    try:
        record_mutation_baseline_restore(
            baseline=baseline,
            observed_before_diff_hash=DIFF_B,
            observed_after_diff_hash=DIFF_A,
            restored_action_ids=("mutation-2", "mutation-1"),
            restored_intent_hashes=("sha256:" + "4" * 64, "sha256:" + "3" * 64),
        )
    except ContractError as exc:
        tampered_restore_reason_codes = _reason_codes(exc)
    if tampered_restore_reason_codes != ["mutation_baseline_restore_mismatch"]:
        raise ContractError("tampered baseline restore did not fail closed")
    try:
        record_causal_alternative_rejection(
            second_rejection,
            reason_codes=("causal_boundary_already_exhausted",),
        )
    except RecoveryError:
        post_terminal_dispatch_blocked = True
    else:
        post_terminal_dispatch_blocked = False
    if not post_terminal_dispatch_blocked:
        raise ContractError("terminal causal admission accepted another attempt")

    restored_baseline = MutationBaselineProjection.model_validate_json(
        canonical_json(baseline.model_dump(mode="json"))
    )
    restored_plan = RecordedCausalAlternativePlan.model_validate_json(
        canonical_json(alternative.model_dump(mode="json"))
    )
    if restored_baseline != baseline or restored_plan != alternative:
        raise ContractError("causal alternative restart state differs")

    return {
        "generic_schema": {
            "input_contract_hash": input_contract.content_hash,
            "parameter_schema_hash": input_contract.parameter_schema_hash,
            "model_facing_keys": list(
                input_contract.parameters["properties"]["alternative_causal_mechanism"][
                    "properties"
                ]
            ),
            "causal_path_role_enum": input_contract.parameters["properties"][
                "alternative_causal_mechanism"
            ]["properties"]["causal_path"]["items"]["properties"]["role"]["enum"],
            "exception_specific_key_present": False,
            "symbol_text_used_for_admission": False,
            "prose_used_for_distinctness": False,
        },
        "mutation_baseline_restore": {
            "projection_hash": baseline.content_hash,
            "baseline_diff_hash": baseline.baseline_diff_hash,
            "current_failed_diff_hash": baseline.current_failed_diff_hash,
            "forward_action_ids": list(baseline.forward_action_ids),
            "restore_action_ids": list(baseline.restore_action_ids),
            "restore_receipt_hash": receipt.content_hash,
            "failure_history_preserved": True,
            "tampered_restore_reason_codes": tampered_restore_reason_codes,
        },
        "same_family_relabel": {
            "reason_codes": same_family_reason_codes,
            "prose_and_symbol_changed": True,
            "source_coverage_changed": False,
            "mutation_admitted": False,
        },
        "non_exhausted_alternative": {
            "plan_hash": alternative.content_hash,
            "prior_mechanism_hash": alternative.prior_causal_mechanism.content_hash,
            "alternative_mechanism_hash": alternative.alternative_causal_mechanism.content_hash,
            "prior_boundary_coverage_key": (
                alternative.causal_contrast.prior_boundary_coverage_key
            ),
            "alternative_boundary_coverage_key": (
                alternative.causal_contrast.alternative_boundary_coverage_key
            ),
            "alternative_boundary_is_non_exhausted": True,
            "candidate_binding_normalization_hash": normalization.content_hash,
            "visible_check_order": list(alternative.planned_check_ids),
        },
        "admission_recovery": {
            "first_rejection_status": first_rejection.status,
            "first_rejection_recovery_remaining": first_rejection.recovery_remaining,
            "restart_exact": restored_checkpoint == first_rejection,
            "second_rejection_status": second_rejection.status,
            "terminal_reason": second_rejection.terminal_reason,
            "post_terminal_dispatch_blocked": post_terminal_dispatch_blocked,
            "accepted_plan_hash": accepted.accepted_plan_hash,
        },
        "restart_and_limits": {
            "baseline_round_trip_exact": restored_baseline == baseline,
            "plan_round_trip_exact": restored_plan == alternative,
            "initial_plus_corrective_mutation_limit": "1+3",
            "correction_limit_changed": False,
            "review_correction_limit_changed": False,
        },
    }


def build_workflow_causal_alternative_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    predecessors = []
    for relative, expected in IMMUTABLE_PREDECESSORS.items():
        observed = _identity(root, relative, json_content=True)
        if any(observed.get(key) != value for key, value in expected.items()):
            raise ContractError(f"immutable causal-alternative predecessor differs: {relative}")
        predecessors.append(observed)
    diagnosis_path = tuple(IMMUTABLE_PREDECESSORS)[-1]
    diagnosis = json.loads((root / diagnosis_path).read_text(encoding="utf-8"))
    selected = diagnosis.get("selected_failure_class", {})
    if (
        selected.get("id") != "semantic-reset-without-alternative-causal-mechanism"
        or selected.get("next_successor_scope") != "bounded-public-causal-alternative-gate"
        or selected.get("candidate_ready") is not False
        or diagnosis.get("interpretation_limits", {}).get("r12_retry_allowed") is not False
    ):
        raise ContractError("R12 causal-alternative diagnosis boundary differs")
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 26, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "generic-public-causal-alternative-and-exact-mutation-baseline-restore",
        "policy_version": CAUSAL_ALTERNATIVE_POLICY,
        "runtime_version": None,
        "tool_schema_version": None,
        "context_policy_version": None,
        "runtime_activation_authorized": False,
        "scenarios": _scenarios(),
        "source_files": tuple(_identity(root, relative) for relative in SOURCE_FILES),
        "immutable_predecessors": tuple(predecessors),
        "diagnosis_binding": {
            "selected_failure_class": selected["id"],
            "affected_orders": selected["affected_orders"],
            "same_family_relabel_must_fail": True,
            "non_exhausted_current_source_required": True,
            "task_specific_solution_policy_added": False,
            "r12_retry_allowed": False,
        },
        "evidence_boundary": {
            "public_synthetic_source_only": True,
            "task_fixture_files_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "workspace_mutations": 0,
            "added_cost_usd": "0",
        },
        "paid_execution_authorized": False,
        "rapid_candidate_created": False,
        "quality_improvement_established": False,
        "semantic_distinctness_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("causal-alternative qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_causal_alternative_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_causal_alternative_successor_qualification(root)
    target = (root / QUALIFICATION_PATH).resolve()
    if not target.is_relative_to(root):
        raise ContractError("causal-alternative qualification output escapes repository")
    raw = qualification_bytes(value)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return value


def load_workflow_causal_alternative_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = (root / QUALIFICATION_PATH).resolve()
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("causal-alternative qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("causal-alternative qualification bytes differ")
    if value != build_workflow_causal_alternative_successor_qualification(root):
        raise ContractError("causal-alternative qualification source binding differs")
    return value


__all__ = [
    "IMMUTABLE_PREDECESSORS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_causal_alternative_successor_qualification",
    "load_workflow_causal_alternative_successor_qualification",
    "materialize_workflow_causal_alternative_successor_qualification",
    "qualification_bytes",
]
