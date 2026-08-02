"""V11 public coverage-rejection context recovery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    EventType,
    Phase,
    PublicReviewContract,
    RunEvent,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import (
    canonical_json,
    safe_relative_path,
    sha256_bytes,
    sha256_text,
)

REVIEW_EVIDENCE_V2_SCHEMA = "review-evidence-v2"
COVERAGE_REJECTION_FEEDBACK_SCHEMA = "coverage-rejection-feedback-v1"
COVERAGE_REJECTION_ERROR_CODE = "COVERAGE_CITATION_REJECTED"


def _context_event(*args: Any, **kwargs: Any) -> tuple[Any, Any]:
    """Resolve the shared renderer at call time without an import cycle."""

    from patchloop.agent.context import _context_event as implementation

    return implementation(*args, **kwargs)


def _v11_request_envelope(
    request_document: Any,
    *,
    expected_provider: str,
) -> tuple[bool, str | None]:
    """Return the rendered context from an exact mock or Responses request."""

    if (
        not isinstance(request_document, dict)
        or set(request_document)
        != {
            "schema_version",
            "provider",
            "endpoint",
            "request_body",
            "request_body_hash",
            "context_build",
            "worker_claim",
        }
        or request_document.get("schema_version")
        != "model-request-evidence-v1"
    ):
        return False, None
    request_body = request_document.get("request_body")
    if not isinstance(request_body, dict):
        return False, None
    provider = request_document.get("provider")
    endpoint = request_document.get("endpoint")
    if provider != expected_provider:
        return False, None
    if provider == "mock":
        rendered_context = request_body.get("context")
        return (
            bool(
                endpoint is None
                and set(request_body)
                == {"model", "system_prompt", "context", "tools"}
                and isinstance(request_body.get("model"), str)
                and isinstance(request_body.get("system_prompt"), str)
                and isinstance(rendered_context, str)
                and isinstance(request_body.get("tools"), list)
            ),
            rendered_context if isinstance(rendered_context, str) else None,
        )
    if provider != "openai" or endpoint != "/v1/responses":
        return False, None
    inputs = request_body.get("input")
    rendered_context = (
        inputs[1].get("content")
        if isinstance(inputs, list)
        and len(inputs) == 2
        and isinstance(inputs[1], dict)
        else None
    )
    valid = bool(
        set(request_body)
        == {
            "model",
            "input",
            "tools",
            "store",
            "reasoning",
            "service_tier",
            "max_output_tokens",
            "truncation",
        }
        and isinstance(request_body.get("model"), str)
        and isinstance(inputs, list)
        and len(inputs) == 2
        and isinstance(inputs[0], dict)
        and set(inputs[0]) == {"role", "content"}
        and inputs[0].get("role") == "system"
        and isinstance(inputs[0].get("content"), str)
        and isinstance(inputs[1], dict)
        and set(inputs[1]) == {"role", "content"}
        and inputs[1].get("role") == "user"
        and isinstance(rendered_context, str)
        and isinstance(request_body.get("tools"), list)
        and request_body.get("store") is False
        and isinstance(request_body.get("reasoning"), dict)
        and isinstance(request_body.get("service_tier"), str)
        and type(request_body.get("max_output_tokens")) is int
        and request_body["max_output_tokens"] > 0
        and request_body.get("truncation") == "disabled"
    )
    return valid, rendered_context if isinstance(rendered_context, str) else None


def _v11_correlated_success_call(
    events: list[RunEvent],
    outcome: RunEvent,
    *,
    artifact_store: ArtifactStore | None,
    expected_tool: str,
    worktree_diff_hash: str,
) -> tuple[RunEvent, dict[str, Any], dict[str, Any] | None]:
    """Validate one V11 tool outcome against its durable dispatched call."""

    if artifact_store is None:
        raise RecoveryError(
            "phase-evidence-v11 requires the artifact store for tool binding"
        )
    action_id = outcome.correlation_id
    calls = [
        event
        for event in events
        if event.sequence < outcome.sequence
        and event.type == EventType.TOOL_CALLED
        and event.correlation_id == action_id
        and event.payload.get("tool") == expected_tool
    ]
    outcomes = [
        event
        for event in events
        if event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
        and event.correlation_id == action_id
        and event.payload.get("tool") == expected_tool
    ]
    if (
        outcome.actor != "tool-gateway"
        or outcome.payload.get("status") != "succeeded"
        or not isinstance(action_id, str)
        or not action_id
        or len(calls) != 1
        or len(outcomes) != 1
        or outcomes[0].event_id != outcome.event_id
    ):
        raise RecoveryError(
            f"v11 {expected_tool} outcome lacks one correlated call"
        )
    call = calls[0]
    try:
        input_artifact = Artifact.model_validate(
            call.payload.get("input_artifact")
        )
        input_document = json.loads(
            artifact_store.read_bytes(input_artifact).decode(
                "utf-8",
                errors="strict",
            )
        )
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(
            f"v11 {expected_tool} call input CAS is invalid"
        ) from exc
    if not isinstance(input_document, dict):
        raise RecoveryError(
            f"v11 {expected_tool} call input must be an object"
        )
    arguments = input_document.get("input")
    expected_keys = (
        {"tool", "input", "execution_context"}
        if expected_tool == "review_task"
        else {"tool", "input"}
    )
    state_marker = None
    if expected_tool == "get_diff":
        state_marker = max(
            (
                event.sequence
                for event in events
                if event.sequence < call.sequence
                and event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "run_check"
                and event.payload.get("worktree_diff_hash")
                == worktree_diff_hash
            ),
            default=None,
        )
    expected_input_hash = (
        sha256_text(
            canonical_json({"tool": expected_tool, "input": arguments})
        )
        if isinstance(arguments, dict)
        else None
    )
    expected_normalized_hash = (
        sha256_text(
            canonical_json(
                {
                    "tool": expected_tool,
                    "input": arguments,
                    "worktree_diff_hash": worktree_diff_hash,
                    "state_marker": state_marker,
                }
            )
        )
        if isinstance(arguments, dict)
        else None
    )
    execution_context = input_document.get("execution_context")
    if (
        call.actor != "agent"
        or set(input_document) != expected_keys
        or input_document.get("tool") != expected_tool
        or not isinstance(arguments, dict)
        or call.payload.get("artifact_id") != input_artifact.artifact_id
        or call.payload.get("artifact_path") != input_artifact.path
        or call.payload.get("input_hash") != expected_input_hash
        or call.payload.get("normalized_call_hash")
        != expected_normalized_hash
        or call.payload.get("worktree_diff_hash") != worktree_diff_hash
        or call.payload.get("execution") != "dispatched"
        or (
            expected_tool == "review_task"
            and not isinstance(execution_context, dict)
        )
    ):
        raise RecoveryError(
            f"v11 {expected_tool} call binding is invalid"
        )
    return call, arguments, (
        execution_context if isinstance(execution_context, dict) else None
    )


def _validate_v11_get_diff_success(
    events: list[RunEvent],
    outcome: RunEvent,
    *,
    artifact_store: ArtifactStore | None,
    worktree_diff_hash: str,
) -> dict[str, Any]:
    """Bind a V11 get_diff outcome to its call and exact patch bytes."""

    _, arguments, _ = _v11_correlated_success_call(
        events,
        outcome,
        artifact_store=artifact_store,
        expected_tool="get_diff",
        worktree_diff_hash=worktree_diff_hash,
    )
    if arguments != {}:
        raise RecoveryError("v11 get_diff call arguments are invalid")
    assert artifact_store is not None
    try:
        result_artifact = Artifact.model_validate(
            outcome.payload.get("result_artifact")
        )
        result_document = json.loads(
            artifact_store.read_bytes(result_artifact).decode(
                "utf-8",
                errors="strict",
            )
        )
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError("v11 get_diff result CAS is invalid") from exc
    if (
        not isinstance(result_document, dict)
        or set(result_document)
        != {
            "patch",
            "patch_hash",
            "worktree_diff_hash",
            "changed_files",
            "added_lines",
            "deleted_lines",
        }
        or outcome.payload.get("artifact_id")
        != result_artifact.artifact_id
        or outcome.payload.get("artifact_path") != result_artifact.path
        or outcome.payload.get("patch_hash") != worktree_diff_hash
        or outcome.payload.get("worktree_diff_hash")
        != worktree_diff_hash
        or not isinstance(result_document.get("patch"), str)
        or sha256_text(result_document["patch"]) != worktree_diff_hash
        or result_document.get("patch_hash") != worktree_diff_hash
        or result_document.get("worktree_diff_hash")
        != worktree_diff_hash
        or not isinstance(result_document.get("changed_files"), list)
        or any(
            not isinstance(path, str) or not path
            for path in result_document.get("changed_files", [])
        )
        or type(result_document.get("added_lines")) is not int
        or result_document["added_lines"] < 0
        or type(result_document.get("deleted_lines")) is not int
        or result_document["deleted_lines"] < 0
    ):
        raise RecoveryError("v11 get_diff result binding is invalid")
    return result_document


def _validate_v11_review_arguments(
    events: list[RunEvent],
    *,
    call_sequence: int,
    arguments: dict[str, Any],
    review_evidence: dict[str, Any],
    artifact_store: ArtifactStore,
    worktree_diff_hash: str,
    public_review_contract: PublicReviewContract,
    rejection_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rebuild the public V11 review decision from durable trace evidence."""

    if set(arguments) != {
        "requirements",
        "coverage_targets",
        "targeted_validation",
        "residual_risks",
    }:
        raise RecoveryError("v11 review arguments have an invalid shape")
    expected_evidence_keys = {
        "schema_version",
        "pinning_active",
        "worktree_diff_hash",
        "mutation_event_sequence",
        "coverage_target_event_sequences",
        "passing_check_event_sequences",
        "source_get_diff_sequence",
        "citable_event_sequences",
        "incomplete_event_sequences",
        "pinned_tool_results",
    }
    if (
        set(review_evidence) != expected_evidence_keys
        or review_evidence.get("schema_version")
        != REVIEW_EVIDENCE_V2_SCHEMA
        or review_evidence.get("pinning_active") is not True
        or review_evidence.get("worktree_diff_hash")
        != worktree_diff_hash
        or type(review_evidence.get("mutation_event_sequence")) is not int
        or type(review_evidence.get("source_get_diff_sequence")) is not int
    ):
        raise RecoveryError("v11 review evidence has an invalid shape")

    contract_requirements = list(public_review_contract.requirements)
    contract_requirement_ids = [
        requirement.requirement_id
        for requirement in contract_requirements
    ]
    contract_targets = [
        (requirement.requirement_id, target)
        for requirement in contract_requirements
        for target in requirement.coverage_targets
    ]
    contract_target_ids = [
        target.coverage_target_id for _, target in contract_targets
    ]
    target_mapping = review_evidence.get(
        "coverage_target_event_sequences"
    )
    passing_sequences = review_evidence.get(
        "passing_check_event_sequences"
    )
    citable_sequences = review_evidence.get("citable_event_sequences")
    incomplete_sequences = review_evidence.get(
        "incomplete_event_sequences"
    )
    pinned_tool_results = review_evidence.get("pinned_tool_results")
    if (
        not isinstance(target_mapping, dict)
        or set(target_mapping) != set(contract_target_ids)
        or not isinstance(passing_sequences, list)
        or not isinstance(citable_sequences, list)
        or not isinstance(incomplete_sequences, list)
        or not isinstance(pinned_tool_results, list)
        or any(
            not isinstance(sequences, list)
            or sequences != sorted(set(sequences))
            or any(type(sequence) is not int or sequence < 1 for sequence in sequences)
            for sequences in target_mapping.values()
        )
        or passing_sequences != sorted(set(passing_sequences))
        or any(type(sequence) is not int or sequence < 1 for sequence in passing_sequences)
        or len(citable_sequences) != len(set(citable_sequences))
        or any(type(sequence) is not int or sequence < 1 for sequence in citable_sequences)
        or len(incomplete_sequences) != len(set(incomplete_sequences))
        or any(type(sequence) is not int or sequence < 1 for sequence in incomplete_sequences)
    ):
        raise RecoveryError("v11 review evidence mapping is invalid")

    expected_citable: list[int] = []
    for target_id in contract_target_ids:
        for sequence in target_mapping[target_id]:
            if sequence not in expected_citable:
                expected_citable.append(sequence)
    for sequence in passing_sequences:
        if sequence not in expected_citable:
            expected_citable.append(sequence)
    source_get_diff_sequence = review_evidence["source_get_diff_sequence"]
    if source_get_diff_sequence not in expected_citable:
        expected_citable.append(source_get_diff_sequence)
    if citable_sequences != expected_citable:
        raise RecoveryError("v11 review citations are not canonical")

    events_by_sequence = {event.sequence: event for event in events}
    mutation = events_by_sequence.get(
        review_evidence["mutation_event_sequence"]
    )
    source_get_diff = events_by_sequence.get(source_get_diff_sequence)
    if (
        mutation is None
        or mutation.type != EventType.PATCH_APPLIED
        or mutation.payload.get("worktree_diff_hash")
        != worktree_diff_hash
        or mutation.sequence >= call_sequence
        or source_get_diff is None
        or source_get_diff.sequence >= call_sequence
    ):
        raise RecoveryError("v11 review mutation/diff provenance is invalid")
    _validate_v11_get_diff_success(
        events,
        source_get_diff,
        artifact_store=artifact_store,
        worktree_diff_hash=worktree_diff_hash,
    )

    result_evidence_by_sequence: dict[int, dict[str, Any]] = {}
    for requirement_id, target in contract_targets:
        del requirement_id
        for sequence in target_mapping[target.coverage_target_id]:
            event = events_by_sequence.get(sequence)
            if event is None or event.sequence >= call_sequence:
                raise RecoveryError(
                    "v11 review cites unavailable target evidence"
                )
            expected_tool = (
                "read_file"
                if target.evidence_kind == "current_diff_inspection"
                else "run_check"
            )
            _v11_correlated_success_call(
                events,
                event,
                artifact_store=artifact_store,
                expected_tool=expected_tool,
                worktree_diff_hash=worktree_diff_hash,
            )
            rendered, evidence = _context_event(
                event,
                policy_version="phase-evidence-v10",
                artifact_store=artifact_store,
            )
            result = rendered["payload"].get("tool_result")
            if (
                evidence is None
                or evidence.get("available") is not True
                or evidence.get("truncated") is not False
                or not isinstance(result, dict)
                or result.get("worktree_diff_hash")
                != worktree_diff_hash
                or (
                    target.evidence_kind == "current_diff_inspection"
                    and (
                        result.get("path") != target.path
                        or not isinstance(result.get("content"), str)
                        or target.anchor not in result["content"]
                    )
                )
                or (
                    target.evidence_kind == "passing_validation"
                    and (
                        result.get("check_id") not in target.check_ids
                        or result.get("passed") is not True
                    )
                )
            ):
                raise RecoveryError(
                    "v11 review target evidence is invalid"
                )
            result_evidence_by_sequence[sequence] = evidence

    for sequence in passing_sequences:
        event = events_by_sequence.get(sequence)
        if (
            event is None
            or event.sequence >= call_sequence
            or event.type != EventType.TOOL_SUCCEEDED
            or event.payload.get("tool") not in {"run_check", "run_probe"}
            or event.payload.get("passed") is not True
            or event.payload.get("worktree_diff_hash")
            != worktree_diff_hash
        ):
            raise RecoveryError("v11 passing validation evidence is invalid")
        _v11_correlated_success_call(
            events,
            event,
            artifact_store=artifact_store,
            expected_tool=str(event.payload["tool"]),
            worktree_diff_hash=worktree_diff_hash,
        )
        rendered, evidence = _context_event(
            event,
            policy_version="phase-evidence-v10",
            artifact_store=artifact_store,
        )
        result = rendered["payload"].get("tool_result")
        if (
            evidence is None
            or evidence.get("available") is not True
            or evidence.get("truncated") is not False
            or not isinstance(result, dict)
            or result.get("passed") is not True
        ):
            raise RecoveryError("v11 passing validation result is invalid")
        result_evidence_by_sequence[sequence] = evidence
    _, source_diff_evidence = _context_event(
        source_get_diff,
        policy_version="phase-evidence-v10",
        artifact_store=artifact_store,
    )
    if source_diff_evidence is None:
        raise RecoveryError("v11 review diff evidence is unavailable")
    result_evidence_by_sequence[source_get_diff_sequence] = (
        source_diff_evidence
    )
    declared_pinned = {
        item.get("event_sequence"): item
        for item in pinned_tool_results
        if isinstance(item, dict)
    }
    if (
        len(declared_pinned) != len(pinned_tool_results)
        or set(declared_pinned)
        != set(citable_sequences) | set(incomplete_sequences)
        or any(
            declared_pinned.get(sequence)
            != result_evidence_by_sequence.get(sequence)
            for sequence in citable_sequences
        )
    ):
        raise RecoveryError("v11 pinned review evidence is invalid")

    requirements = arguments.get("requirements")
    targets = arguments.get("coverage_targets")
    targeted_validation = arguments.get("targeted_validation")
    residual_risks = arguments.get("residual_risks")
    if (
        not isinstance(requirements, list)
        or not isinstance(targets, list)
        or not isinstance(targeted_validation, list)
        or not isinstance(residual_risks, list)
        or len(requirements) != len(contract_requirements)
        or len(targets) != len(contract_targets)
    ):
        raise RecoveryError("v11 review collection cardinality is invalid")

    normalized_requirements: list[dict[str, Any]] = []
    observed_requirement_ids: list[str] = []
    for row in requirements:
        if (
            not isinstance(row, dict)
            or set(row)
            != {
                "requirement_id",
                "status",
                "evidence_event_sequences",
                "notes",
            }
        ):
            raise RecoveryError("v11 review requirement row is invalid")
        requirement_id = row.get("requirement_id")
        status = row.get("status")
        sequences = row.get("evidence_event_sequences")
        notes = row.get("notes")
        if (
            requirement_id not in contract_requirement_ids
            or requirement_id in observed_requirement_ids
            or status not in {"verified", "partially_verified", "unverified"}
            or not isinstance(sequences, list)
            or len(sequences) > 20
            or len(sequences) != len(set(sequences))
            or any(type(sequence) is not int for sequence in sequences)
            or (status != "unverified" and not sequences)
            or not isinstance(notes, str)
            or not notes.strip()
            or len(notes) > 2000
        ):
            raise RecoveryError("v11 review requirement fields are invalid")
        observed_requirement_ids.append(str(requirement_id))
        requirement = next(
            item
            for item in contract_requirements
            if item.requirement_id == requirement_id
        )
        normalized_requirements.append(
            {
                "requirement_id": requirement_id,
                "source_excerpt": requirement.source_excerpt.strip(),
                "status": status,
                "evidence_event_sequences": list(sequences),
                "notes": notes.strip(),
            }
        )
    if set(observed_requirement_ids) != set(contract_requirement_ids):
        raise RecoveryError("v11 review requirement IDs are invalid")
    requirement_rows_by_id = {
        row["requirement_id"]: row for row in normalized_requirements
    }
    normalized_requirements = [
        requirement_rows_by_id[requirement_id]
        for requirement_id in contract_requirement_ids
    ]

    normalized_targets: list[dict[str, Any]] = []
    target_statuses: dict[str, str] = {}
    submitted_by_target: dict[str, list[int]] = {}
    observed_target_ids: list[str] = []
    rejected_target_id = (
        rejection_details.get("coverage_target_id")
        if isinstance(rejection_details, dict)
        else None
    )
    rejected_reason = (
        rejection_details.get("reason")
        if isinstance(rejection_details, dict)
        else None
    )
    for row in targets:
        if (
            not isinstance(row, dict)
            or set(row)
            != {
                "coverage_target_id",
                "status",
                "evidence_event_sequences",
                "notes",
            }
        ):
            raise RecoveryError("v11 review target row is invalid")
        target_id = row.get("coverage_target_id")
        status = row.get("status")
        sequences = row.get("evidence_event_sequences")
        notes = row.get("notes")
        if (
            target_id not in contract_target_ids
            or target_id in observed_target_ids
            or status not in {"verified", "partially_verified", "unverified"}
            or not isinstance(sequences, list)
            or len(sequences) > 20
            or len(sequences) != len(set(sequences))
            or any(type(sequence) is not int for sequence in sequences)
            or not isinstance(notes, str)
            or not notes.strip()
            or len(notes) > 2000
        ):
            raise RecoveryError("v11 review target fields are invalid")
        allowed = target_mapping[str(target_id)]
        is_rejected_target = target_id == rejected_target_id
        if not is_rejected_target:
            if not set(sequences).issubset(allowed):
                raise RecoveryError("v11 review target cites unrelated evidence")
            if status == "verified" and (not allowed or sequences != allowed):
                raise RecoveryError("v11 verified target evidence is incomplete")
            if status == "partially_verified" and not sequences:
                raise RecoveryError("v11 partial target lacks evidence")
            if status == "unverified" and sequences:
                raise RecoveryError("v11 unverified target cites evidence")
        elif rejected_reason == "target_evidence_not_allowed":
            if set(sequences).issubset(allowed):
                raise RecoveryError("v11 rejection reason is not reproducible")
        elif rejected_reason == "verified_target_evidence_mismatch":
            if (
                not set(sequences).issubset(allowed)
                or status != "verified"
                or (allowed and sequences == allowed)
            ):
                raise RecoveryError("v11 rejection reason is not reproducible")
        elif rejected_reason == "fresh_target_evidence_required":
            if status != "verified" or sequences != allowed:
                raise RecoveryError("v11 rejection reason is not reproducible")
        elif rejection_details is not None:
            raise RecoveryError("v11 rejection target is not reproducible")
        observed_target_ids.append(str(target_id))
        target_statuses[str(target_id)] = str(status)
        submitted_by_target[str(target_id)] = list(sequences)
        requirement_id = next(
            requirement_id
            for requirement_id, target in contract_targets
            if target.coverage_target_id == target_id
        )
        normalized_targets.append(
            {
                "coverage_target_id": target_id,
                "requirement_id": requirement_id,
                "status": status,
                "evidence_event_sequences": list(sequences),
                "notes": notes.strip(),
            }
        )
        if is_rejected_target:
            return {
                "requirements": normalized_requirements,
                "coverage_targets": normalized_targets,
                "targeted_validation": [],
                "residual_risks": [],
                "contract_requirement_ids": contract_requirement_ids,
                "contract_target_ids": contract_target_ids,
                "verified_target_ids": [],
                "unresolved_target_ids": contract_target_ids,
                "coverage_complete": False,
            }
    if rejection_details is not None:
        raise RecoveryError("v11 source target rejection was not reproduced")
    if set(observed_target_ids) != set(contract_target_ids):
        raise RecoveryError("v11 review target IDs are invalid")
    target_rows_by_id = {
        row["coverage_target_id"]: row for row in normalized_targets
    }
    normalized_targets = [
        target_rows_by_id[target_id] for target_id in contract_target_ids
    ]

    if rejection_details is None:
        requirement_rows = {
            row["requirement_id"]: row for row in normalized_requirements
        }
        for requirement in contract_requirements:
            target_ids = [
                target.coverage_target_id
                for target in requirement.coverage_targets
            ]
            statuses = [
                target_statuses[target_id] for target_id in target_ids
            ]
            expected_status = (
                "verified"
                if all(status == "verified" for status in statuses)
                else (
                    "unverified"
                    if all(status == "unverified" for status in statuses)
                    else "partially_verified"
                )
            )
            expected_sequences: list[int] = []
            for target_id in target_ids:
                for sequence in submitted_by_target[target_id]:
                    if sequence not in expected_sequences:
                        expected_sequences.append(sequence)
            requirement_row = requirement_rows[
                requirement.requirement_id
            ]
            if (
                requirement_row["status"] != expected_status
                or requirement_row["evidence_event_sequences"]
                != expected_sequences
            ):
                raise RecoveryError(
                    "v11 review requirement roll-up is invalid"
                )

    if not 1 <= len(targeted_validation) <= 20:
        raise RecoveryError("v11 targeted validation cardinality is invalid")
    normalized_validation: list[dict[str, Any]] = []
    seen_validation: set[int] = set()
    current_validation_passed = False
    for row in targeted_validation:
        if (
            not isinstance(row, dict)
            or set(row) != {"kind", "event_sequence", "outcome", "notes"}
        ):
            raise RecoveryError("v11 targeted validation row is invalid")
        kind = row.get("kind")
        sequence = row.get("event_sequence")
        outcome = row.get("outcome")
        notes = row.get("notes")
        event = events_by_sequence.get(sequence) if type(sequence) is int else None
        expected_tools = {
            "probe": {"run_probe"},
            "registered_check": {"run_check"},
            "repository_evidence": {"read_file", "search_files", "get_diff"},
        }.get(str(kind))
        if (
            expected_tools is None
            or type(sequence) is not int
            or sequence in seen_validation
            or sequence not in citable_sequences
            or event is None
            or event.sequence >= call_sequence
            or event.payload.get("tool") not in expected_tools
            or outcome not in {"passed", "failed", "inconclusive"}
            or not isinstance(notes, str)
            or not notes.strip()
            or len(notes) > 2000
        ):
            raise RecoveryError("v11 targeted validation fields are invalid")
        actual_outcome = (
            "inconclusive"
            if event.payload.get("timed_out") is True
            else (
                "passed"
                if kind == "repository_evidence"
                or event.payload.get("passed") is True
                else "failed"
            )
        )
        if outcome != actual_outcome:
            raise RecoveryError("v11 targeted validation outcome is invalid")
        if kind in {"probe", "registered_check"} and outcome == "passed":
            current_validation_passed = True
        seen_validation.add(sequence)
        normalized_validation.append({**row, "notes": notes.strip()})
    if not current_validation_passed:
        raise RecoveryError("v11 review lacks passing validation evidence")

    if len(residual_risks) > 20:
        raise RecoveryError("v11 residual risk cardinality is invalid")
    normalized_risks: list[dict[str, Any]] = []
    risk_requirement_ids: set[str] = set()
    for row in residual_risks:
        if (
            not isinstance(row, dict)
            or set(row) != {"requirement_ids", "risk", "mitigation"}
        ):
            raise RecoveryError("v11 residual risk row is invalid")
        requirement_ids = row.get("requirement_ids")
        risk = row.get("risk")
        mitigation = row.get("mitigation")
        if (
            not isinstance(requirement_ids, list)
            or not requirement_ids
            or len(requirement_ids) > 20
            or len(requirement_ids) != len(set(requirement_ids))
            or any(item not in contract_requirement_ids for item in requirement_ids)
            or not isinstance(risk, str)
            or not risk.strip()
            or len(risk) > 1000
            or not isinstance(mitigation, str)
            or not mitigation.strip()
            or len(mitigation) > 1000
        ):
            raise RecoveryError("v11 residual risk fields are invalid")
        risk_requirement_ids.update(requirement_ids)
        normalized_risks.append(
            {
                "requirement_ids": list(requirement_ids),
                "risk": risk.strip(),
                "mitigation": mitigation.strip(),
            }
        )
    nonverified = {
        row["requirement_id"]
        for row in normalized_requirements
        if row["status"] != "verified"
    }
    if not nonverified.issubset(risk_requirement_ids):
        raise RecoveryError("v11 review residual risk coverage is invalid")

    verified_target_ids = [
        target_id
        for target_id in contract_target_ids
        if target_statuses[target_id] == "verified"
    ]
    unresolved_target_ids = [
        target_id
        for target_id in contract_target_ids
        if target_statuses[target_id] != "verified"
    ]
    return {
        "requirements": normalized_requirements,
        "coverage_targets": normalized_targets,
        "targeted_validation": normalized_validation,
        "residual_risks": normalized_risks,
        "contract_requirement_ids": contract_requirement_ids,
        "contract_target_ids": contract_target_ids,
        "verified_target_ids": verified_target_ids,
        "unresolved_target_ids": unresolved_target_ids,
        "coverage_complete": not unresolved_target_ids,
    }


def _validate_v11_model_tool_call(
    model_event: RunEvent,
    call: RunEvent,
    *,
    expected_tool: str,
    expected_arguments: dict[str, Any],
    artifact_store: ArtifactStore,
    label: str,
) -> None:
    """Bind a dispatched tool call to the content-addressed model response."""

    try:
        response_path = Path(
            str(model_event.payload["artifact_path"])
        ).resolve()
        relative = response_path.relative_to(artifact_store.root.resolve())
        response_bytes = response_path.read_bytes()
        response_document = json.loads(
            response_bytes.decode("utf-8", errors="strict")
        )
    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RecoveryError(
            f"v11 {label} model response CAS is invalid"
        ) from exc
    parts = relative.parts
    declared_calls = (
        response_document.get("tool_calls")
        if isinstance(response_document, dict)
        else None
    )
    expected_call = {
        "name": expected_tool,
        "action_id": call.correlation_id,
        "arguments": expected_arguments,
    }
    matching_calls = (
        [item for item in declared_calls if item == expected_call]
        if isinstance(declared_calls, list)
        else []
    )
    if (
        model_event.type != EventType.MODEL_CALLED
        or model_event.actor != "model-adapter"
        or not model_event.sequence < call.sequence
        or len(parts) != 4
        or parts[0:2] != ("objects", "sha256")
        or len(parts[2]) != 2
        or len(parts[3]) != 62
        or sha256_bytes(response_bytes) != f"sha256:{parts[2]}{parts[3]}"
        or not isinstance(model_event.payload.get("artifact_id"), str)
        or not model_event.payload["artifact_id"]
        or model_event.payload.get("artifact_path") != str(response_path)
        or not isinstance(declared_calls, list)
        or any(
            not isinstance(item, dict)
            or set(item) != {"name", "action_id", "arguments"}
            for item in declared_calls
        )
        or len(matching_calls) != 1
    ):
        raise RecoveryError(
            f"v11 {label} tool call is not model-response-bound"
        )


def _validate_v11_feedback_tool_generation(
    events: list[RunEvent],
    call: RunEvent,
    *,
    expected_tool: str,
    expected_arguments: dict[str, Any],
    expected_feedback: dict[str, Any],
    expected_feedback_build: dict[str, Any],
    artifact_store: ArtifactStore,
    label: str,
    expected_provider: str,
) -> tuple[RunEvent, RunEvent]:
    """Bind a recovery call to a model request carrying active feedback."""

    prior_models = [
        event
        for event in events
        if event.type == EventType.MODEL_CALLED
        and event.sequence < call.sequence
    ]
    if not prior_models:
        raise RecoveryError(f"v11 {label} lacks a source generation")
    model_event = prior_models[-1]
    request_contexts = [
        event
        for event in events
        if event.type == EventType.CONTEXT_BUILT
        and event.sequence < model_event.sequence
        and event.payload.get("artifact_id")
        == model_event.payload.get("request_artifact_id")
    ]
    if len(request_contexts) != 1:
        raise RecoveryError(f"v11 {label} request context is ambiguous")
    request_context = request_contexts[0]
    try:
        request_path = Path(
            str(request_context.payload["artifact_path"])
        ).resolve()
        relative = request_path.relative_to(artifact_store.root.resolve())
        request_bytes = request_path.read_bytes()
        request_document = json.loads(
            request_bytes.decode("utf-8", errors="strict")
        )
    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RecoveryError(f"v11 {label} request CAS is invalid") from exc
    parts = relative.parts
    request_body = (
        request_document.get("request_body")
        if isinstance(request_document, dict)
        else None
    )
    context_build = (
        request_document.get("context_build")
        if isinstance(request_document, dict)
        else None
    )
    worker_claim = (
        request_document.get("worker_claim")
        if isinstance(request_document, dict)
        else None
    )
    request_envelope_valid, rendered_context = _v11_request_envelope(
        request_document,
        expected_provider=expected_provider,
    )
    try:
        rendered_payload = json.loads(rendered_context or "")
    except json.JSONDecodeError as exc:
        raise RecoveryError(
            f"v11 {label} rendered context is invalid"
        ) from exc
    request_body_hash = (
        sha256_text(canonical_json(request_body))
        if isinstance(request_body, dict)
        else None
    )
    expected_build = {
        **expected_feedback_build,
        "source_through_sequence": request_context.sequence - 1,
    }
    if (
        request_context.actor != "context-builder"
        or not request_context.sequence < model_event.sequence < call.sequence
        or len(parts) != 4
        or parts[0:2] != ("objects", "sha256")
        or len(parts[2]) != 2
        or len(parts[3]) != 62
        or sha256_bytes(request_bytes) != f"sha256:{parts[2]}{parts[3]}"
        or not request_envelope_valid
        or not isinstance(rendered_payload, dict)
        or not isinstance(context_build, dict)
        or context_build.get("schema_version")
        != "context-build-evidence-v11"
        or not isinstance(worker_claim, dict)
        or worker_claim.get("schema_version")
        != "worker-claim-evidence-v1"
        or request_document.get("request_body_hash") != request_body_hash
        or request_context.payload.get("request_body_hash")
        != request_body_hash
        or request_context.payload.get("context_hash")
        != sha256_text(rendered_context)
        or model_event.payload.get("request_artifact_id")
        != request_context.payload.get("artifact_id")
        or model_event.payload.get("request_artifact_path")
        != request_context.payload.get("artifact_path")
        or model_event.payload.get("request_artifact_hash")
        != sha256_bytes(request_bytes)
        or model_event.payload.get("request_body_hash") != request_body_hash
        or rendered_payload.get("coverage_rejection_feedback")
        != expected_feedback
        or context_build.get("coverage_rejection_feedback")
        != expected_build
        or request_context.payload.get("coverage_rejection_feedback")
        != expected_build
        or request_context.payload.get("worker_claim")
        != worker_claim
    ):
        raise RecoveryError(f"v11 {label} request binding is invalid")
    _validate_v11_model_tool_call(
        model_event,
        call,
        expected_tool=expected_tool,
        expected_arguments=expected_arguments,
        artifact_store=artifact_store,
        label=label,
    )
    return request_context, model_event


def _validate_v11_feedback_clearing_review(
    events: list[RunEvent],
    outcome: RunEvent,
    *,
    artifact_store: ArtifactStore | None,
    worktree_diff_hash: str,
    expected_feedback: dict[str, Any],
    expected_feedback_build: dict[str, Any],
    public_review_contract: PublicReviewContract,
    expected_provider: str,
) -> bool:
    """Validate a same-diff review and return whether it may clear feedback."""

    call, arguments, execution_context = _v11_correlated_success_call(
        events,
        outcome,
        artifact_store=artifact_store,
        expected_tool="review_task",
        worktree_diff_hash=worktree_diff_hash,
    )
    if artifact_store is None:
        raise RecoveryError(
            "phase-evidence-v11 requires the artifact store for review binding"
        )
    if (
        not isinstance(execution_context, dict)
        or set(execution_context)
        != {
            "request_artifact_id",
            "phase",
            "presented_tool_results",
            "review_evidence",
            "coverage_rejection_feedback",
        }
        or execution_context.get("phase") != Phase.REVIEW.value
        or call.payload.get("request_phase") != Phase.REVIEW.value
        or call.payload.get("request_artifact_id")
        != execution_context.get("request_artifact_id")
    ):
        raise RecoveryError(
            "v11 feedback-clearing review request identity is invalid"
        )
    request_contexts = [
        event
        for event in events
        if event.sequence < call.sequence
        and event.type == EventType.CONTEXT_BUILT
        and event.actor == "context-builder"
        and event.payload.get("artifact_id")
        == execution_context["request_artifact_id"]
    ]
    if len(request_contexts) != 1:
        raise RecoveryError(
            "v11 feedback-clearing review request context is ambiguous"
        )
    request_context = request_contexts[0]
    try:
        request_path = Path(
            str(request_context.payload["artifact_path"])
        ).resolve()
        relative = request_path.relative_to(artifact_store.root.resolve())
        request_bytes = request_path.read_bytes()
        parts = relative.parts
        request_document = json.loads(
            request_bytes.decode("utf-8", errors="strict")
        )
    except (
        KeyError,
        OSError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RecoveryError(
            "v11 feedback-clearing review request CAS is invalid"
        ) from exc
    request_body = (
        request_document.get("request_body")
        if isinstance(request_document, dict)
        else None
    )
    context_build = (
        request_document.get("context_build")
        if isinstance(request_document, dict)
        else None
    )
    worker_claim = (
        request_document.get("worker_claim")
        if isinstance(request_document, dict)
        else None
    )
    request_envelope_valid, rendered_context = _v11_request_envelope(
        request_document,
        expected_provider=expected_provider,
    )
    try:
        rendered_payload = json.loads(rendered_context or "")
    except json.JSONDecodeError as exc:
        raise RecoveryError(
            "v11 feedback-clearing review context is invalid JSON"
        ) from exc
    request_body_hash = (
        sha256_text(canonical_json(request_body))
        if isinstance(request_body, dict)
        else None
    )
    expected_request_feedback_build = {
        **expected_feedback_build,
        "source_through_sequence": request_context.sequence - 1,
    }
    if (
        len(parts) != 4
        or parts[0:2] != ("objects", "sha256")
        or len(parts[2]) != 2
        or len(parts[3]) != 62
        or sha256_bytes(request_bytes) != f"sha256:{parts[2]}{parts[3]}"
        or not request_envelope_valid
        or not isinstance(rendered_payload, dict)
        or not isinstance(context_build, dict)
        or context_build.get("schema_version")
        != "context-build-evidence-v11"
        or not isinstance(worker_claim, dict)
        or worker_claim.get("schema_version")
        != "worker-claim-evidence-v1"
        or request_context.payload.get("worker_claim") != worker_claim
        or request_document.get("request_body_hash") != request_body_hash
        or request_context.payload.get("request_body_hash")
        != request_body_hash
        or request_context.payload.get("context_hash")
        != sha256_text(rendered_context)
        or rendered_payload.get("phase") != Phase.REVIEW.value
        or rendered_payload.get("coverage_rejection_feedback")
        != expected_feedback
        or execution_context.get("coverage_rejection_feedback")
        != expected_feedback
        or context_build.get("coverage_rejection_feedback")
        != expected_request_feedback_build
        or request_context.payload.get("coverage_rejection_feedback")
        != expected_request_feedback_build
        or context_build.get("review_evidence")
        != execution_context.get("review_evidence")
        or context_build.get("tool_results")
        != execution_context.get("presented_tool_results")
    ):
        raise RecoveryError(
            "v11 feedback-clearing review request binding is invalid"
        )
    request_models = [
        event
        for event in events
        if request_context.sequence < event.sequence < call.sequence
        and event.type == EventType.MODEL_CALLED
    ]
    if (
        len(request_models) != 1
        or request_models[0].actor != "model-adapter"
        or request_models[0].payload.get("request_artifact_id")
        != request_context.payload.get("artifact_id")
        or request_models[0].payload.get("request_artifact_path")
        != request_context.payload.get("artifact_path")
        or request_models[0].payload.get("request_artifact_hash")
        != sha256_bytes(request_bytes)
        or request_models[0].payload.get("request_body_hash")
        != request_body_hash
    ):
        raise RecoveryError(
            "v11 feedback-clearing review request was not dispatched"
        )
    _validate_v11_model_tool_call(
        request_models[0],
        call,
        expected_tool="review_task",
        expected_arguments=arguments,
        artifact_store=artifact_store,
        label="feedback-clearing review",
    )
    if not (
        type(expected_feedback.get("source_failure_sequence")) is int
        and expected_feedback["source_failure_sequence"]
        < request_context.sequence
        < request_models[0].sequence
        < call.sequence
        < outcome.sequence
    ):
        raise RecoveryError(
            "v11 feedback-clearing review causal order is invalid"
        )
    try:
        result_artifact = Artifact.model_validate(
            outcome.payload.get("result_artifact")
        )
        result_document = json.loads(
            artifact_store.read_bytes(result_artifact).decode(
                "utf-8",
                errors="strict",
            )
        )
        review_artifact = Artifact.model_validate(
            result_document.get("review_artifact")
            if isinstance(result_document, dict)
            else None
        )
        review_document = json.loads(
            artifact_store.read_bytes(review_artifact).decode(
                "utf-8",
                errors="strict",
            )
        )
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(
            "v11 feedback-clearing review CAS is invalid"
        ) from exc
    contract_requirement_ids = [
        requirement.requirement_id
        for requirement in public_review_contract.requirements
    ]
    contract_targets = [
        (requirement.requirement_id, target.coverage_target_id)
        for requirement in public_review_contract.requirements
        for target in requirement.coverage_targets
    ]
    contract_target_ids = [target_id for _, target_id in contract_targets]
    try:
        if set(arguments) != {
            "requirements",
            "coverage_targets",
            "targeted_validation",
            "residual_risks",
        }:
            raise ValueError("review arguments have an invalid shape")
        submitted_requirements = arguments["requirements"]
        submitted_targets = arguments["coverage_targets"]
        submitted_validation = arguments["targeted_validation"]
        submitted_risks = arguments["residual_risks"]
        if (
            not isinstance(submitted_requirements, list)
            or not isinstance(submitted_targets, list)
            or not isinstance(submitted_validation, list)
            or not isinstance(submitted_risks, list)
        ):
            raise ValueError("review argument collections are invalid")
        if any(
            not isinstance(row, dict)
            or set(row)
            != {
                "requirement_id",
                "status",
                "evidence_event_sequences",
                "notes",
            }
            for row in submitted_requirements
        ):
            raise ValueError("review requirement arguments are invalid")
        requirement_arguments = {
            row["requirement_id"]: row for row in submitted_requirements
        }
        if (
            len(requirement_arguments) != len(submitted_requirements)
            or set(requirement_arguments) != set(contract_requirement_ids)
        ):
            raise ValueError("review requirement IDs are invalid")
        expected_requirements = [
            {
                "requirement_id": requirement.requirement_id,
                "source_excerpt": requirement.source_excerpt.strip(),
                "status": requirement_arguments[
                    requirement.requirement_id
                ]["status"],
                "evidence_event_sequences": list(
                    requirement_arguments[requirement.requirement_id][
                        "evidence_event_sequences"
                    ]
                ),
                "notes": requirement_arguments[
                    requirement.requirement_id
                ]["notes"].strip(),
            }
            for requirement in public_review_contract.requirements
        ]
        if any(
            not isinstance(row, dict)
            or set(row)
            != {
                "coverage_target_id",
                "status",
                "evidence_event_sequences",
                "notes",
            }
            for row in submitted_targets
        ):
            raise ValueError("review target arguments are invalid")
        target_arguments = {
            row["coverage_target_id"]: row for row in submitted_targets
        }
        if (
            len(target_arguments) != len(submitted_targets)
            or set(target_arguments) != set(contract_target_ids)
        ):
            raise ValueError("review target IDs are invalid")
        expected_targets = [
            {
                "coverage_target_id": target_id,
                "requirement_id": requirement_id,
                "status": target_arguments[target_id]["status"],
                "evidence_event_sequences": list(
                    target_arguments[target_id][
                        "evidence_event_sequences"
                    ]
                ),
                "notes": target_arguments[target_id]["notes"].strip(),
            }
            for requirement_id, target_id in contract_targets
        ]
        if any(
            not isinstance(row, dict)
            or set(row) != {"kind", "event_sequence", "outcome", "notes"}
            for row in submitted_validation
        ):
            raise ValueError("review validation arguments are invalid")
        expected_validation = [
            {**row, "notes": row["notes"].strip()}
            for row in submitted_validation
        ]
        if any(
            not isinstance(row, dict)
            or set(row) != {"requirement_ids", "risk", "mitigation"}
            for row in submitted_risks
        ):
            raise ValueError("review risk arguments are invalid")
        expected_risks = [
            {
                "requirement_ids": list(row["requirement_ids"]),
                "risk": row["risk"].strip(),
                "mitigation": row["mitigation"].strip(),
            }
            for row in submitted_risks
        ]
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise RecoveryError(
            "v11 feedback-clearing review arguments are invalid"
        ) from exc
    coverage = (
        result_document.get("public_review_coverage")
        if isinstance(result_document, dict)
        else None
    )
    target_rows = (
        review_document.get("coverage_targets")
        if isinstance(review_document, dict)
        else None
    )
    authoritative_target_ids = (
        coverage.get("authoritative_coverage_target_ids")
        if isinstance(coverage, dict)
        else None
    )
    verified_target_ids = (
        [
            row.get("coverage_target_id")
            for row in target_rows
            if isinstance(row, dict) and row.get("status") == "verified"
        ]
        if isinstance(target_rows, list)
        else None
    )
    observed_target_ids = (
        [
            row.get("coverage_target_id")
            for row in target_rows
            if isinstance(row, dict)
        ]
        if isinstance(target_rows, list)
        else None
    )
    unresolved_target_ids = (
        [
            target_id
            for target_id in authoritative_target_ids
            if target_id not in set(verified_target_ids)
        ]
        if isinstance(authoritative_target_ids, list)
        and isinstance(verified_target_ids, list)
        else None
    )
    coverage_complete = unresolved_target_ids == []
    review_evidence = execution_context.get("review_evidence")
    if not isinstance(review_evidence, dict):
        raise RecoveryError(
            "v11 feedback-clearing review evidence is invalid"
        )
    reconstructed = _validate_v11_review_arguments(
        events,
        call_sequence=call.sequence,
        arguments=arguments,
        review_evidence=review_evidence,
        artifact_store=artifact_store,
        worktree_diff_hash=worktree_diff_hash,
        public_review_contract=public_review_contract,
    )
    recovered_target_rows = [
        row
        for row in reconstructed["coverage_targets"]
        if row.get("coverage_target_id")
        == expected_feedback.get("coverage_target_id")
    ]
    source_failure_sequence = expected_feedback.get(
        "source_failure_sequence"
    )
    fresh_target_sequences = (
        [
            sequence
            for sequence in recovered_target_rows[0].get(
                "evidence_event_sequences",
                [],
            )
            if type(sequence) is int
            and type(source_failure_sequence) is int
            and sequence > source_failure_sequence
        ]
        if len(recovered_target_rows) == 1
        else []
    )
    if coverage_complete and (
        len(recovered_target_rows) != 1
        or recovered_target_rows[0].get("status") != "verified"
        or not fresh_target_sequences
    ):
        raise RecoveryError(
            "v11 feedback-clearing review lacks fresh target citations"
        )
    events_by_sequence = {event.sequence: event for event in events}
    recovery_tool = (
        "read_file"
        if expected_feedback.get("evidence_kind")
        == "current_diff_inspection"
        else "run_check"
    )
    recovery_bindings: list[
        tuple[RunEvent, RunEvent, RunEvent, RunEvent]
    ] = []
    if coverage_complete:
        for recovery_sequence in fresh_target_sequences:
            recovery_outcome = events_by_sequence.get(recovery_sequence)
            if (
                recovery_outcome is None
                or recovery_outcome.type != EventType.TOOL_SUCCEEDED
                or recovery_outcome.payload.get("tool") != recovery_tool
            ):
                raise RecoveryError(
                    "v11 feedback-clearing target citation is invalid"
                )
            recovery_call, recovery_arguments, _ = (
                _v11_correlated_success_call(
                    events,
                    recovery_outcome,
                    artifact_store=artifact_store,
                    expected_tool=recovery_tool,
                    worktree_diff_hash=worktree_diff_hash,
                )
            )
            recovery_context, recovery_model = (
                _validate_v11_feedback_tool_generation(
                    events,
                    recovery_call,
                    expected_tool=recovery_tool,
                    expected_arguments=recovery_arguments,
                    expected_feedback=expected_feedback,
                    expected_feedback_build=expected_feedback_build,
                    artifact_store=artifact_store,
                    label="fresh target recovery",
                    expected_provider=expected_provider,
                )
            )
            recovery_bindings.append(
                (
                    recovery_context,
                    recovery_model,
                    recovery_call,
                    recovery_outcome,
                )
            )
    recovery_diff = (
        events_by_sequence.get(
            review_evidence.get("source_get_diff_sequence")
        )
        if coverage_complete
        else None
    )
    if coverage_complete and (
        recovery_diff is None
        or recovery_diff.type != EventType.TOOL_SUCCEEDED
        or recovery_diff.payload.get("tool") != "get_diff"
    ):
        raise RecoveryError(
            "v11 feedback-clearing review lacks a refreshed diff"
        )
    diff_call, diff_arguments, _ = (
        _v11_correlated_success_call(
            events,
            recovery_diff,
            artifact_store=artifact_store,
            expected_tool="get_diff",
            worktree_diff_hash=worktree_diff_hash,
        )
        if coverage_complete and recovery_diff is not None
        else (None, None, None)
    )
    diff_context, diff_model = (
        _validate_v11_feedback_tool_generation(
            events,
            diff_call,
            expected_tool="get_diff",
            expected_arguments=diff_arguments,
            expected_feedback=expected_feedback,
            expected_feedback_build=expected_feedback_build,
            artifact_store=artifact_store,
            label="refreshed diff",
            expected_provider=expected_provider,
        )
        if coverage_complete
        and diff_call is not None
        and isinstance(diff_arguments, dict)
        else (None, None)
    )
    if coverage_complete:
        recovery_outcome_sequences = [
            binding[3].sequence for binding in recovery_bindings
        ]
        causal_valid = bool(
            type(source_failure_sequence) is int
            and recovery_bindings
            and recovery_outcome_sequences
            == sorted(set(recovery_outcome_sequences))
            and all(
                source_failure_sequence
                < recovery_context.sequence
                < recovery_model.sequence
                < recovery_call.sequence
                < recovery_outcome.sequence
                < diff_context.sequence
                for (
                    recovery_context,
                    recovery_model,
                    recovery_call,
                    recovery_outcome,
                ) in recovery_bindings
            )
        )
        causal_valid = bool(
            causal_valid
            and recovery_outcome_sequences[-1]
            < diff_context.sequence
            < diff_model.sequence
            < diff_call.sequence
            < recovery_diff.sequence
            < request_context.sequence
            < request_models[0].sequence
            < call.sequence
            < outcome.sequence
        )
        if not causal_valid:
            raise RecoveryError(
                "v11 feedback-clearing recovery causal order is invalid"
            )
    if (
        reconstructed["requirements"] != expected_requirements
        or reconstructed["coverage_targets"] != expected_targets
        or reconstructed["targeted_validation"] != expected_validation
        or reconstructed["residual_risks"] != expected_risks
        or reconstructed["contract_requirement_ids"]
        != contract_requirement_ids
        or reconstructed["contract_target_ids"] != contract_target_ids
        or reconstructed["verified_target_ids"] != verified_target_ids
        or reconstructed["unresolved_target_ids"]
        != unresolved_target_ids
        or reconstructed["coverage_complete"] is not coverage_complete
    ):
        raise RecoveryError(
            "v11 feedback-clearing review reconstruction is invalid"
        )
    if (
        not isinstance(result_document, dict)
        or set(result_document)
        != {
            "schema_version",
            "review_schema_version",
            "review_artifact",
            "review_content_hash",
            "review",
            "request_artifact_id",
            "worktree_diff_hash",
            "mutation_event_sequence",
            "source_get_diff_sequence",
            "requirement_count",
            "coverage_target_count",
            "coverage_complete",
            "verified_coverage_target_ids",
            "unresolved_coverage_target_ids",
            "public_review_coverage",
            "targeted_validation_count",
            "residual_risk_count",
            "self_attestation",
            "deterministic_correctness_claimed",
            "public_review_contract_hash",
        }
        or result_document.get("schema_version")
        != "task-review-result-v3"
        or not isinstance(review_document, dict)
        or set(review_document)
        != {
            "schema_version",
            "run_id",
            "request_artifact_id",
            "worktree_diff_hash",
            "mutation_event_sequence",
            "source_get_diff_sequence",
            "requirements",
            "coverage_targets",
            "public_review_coverage",
            "targeted_validation",
            "residual_risks",
            "deterministic_correctness_claimed",
            "public_review_contract_hash",
            "public_review_contract_schema_version",
            "authoritative_requirement_ids",
        }
        or review_document.get("schema_version") != "task-review-v3"
        or result_document.get("review_schema_version")
        != "task-review-v3"
        or result_document.get("review") != review_document
        or result_document.get("review_content_hash")
        != review_artifact.content_hash
        or outcome.payload.get("artifact_id")
        != result_artifact.artifact_id
        or outcome.payload.get("artifact_path") != result_artifact.path
        or outcome.payload.get("review_artifact")
        != review_artifact.model_dump(mode="json")
        or outcome.payload.get("review_content_hash")
        != review_artifact.content_hash
        or result_document.get("worktree_diff_hash")
        != worktree_diff_hash
        or review_document.get("worktree_diff_hash")
        != worktree_diff_hash
        or outcome.payload.get("worktree_diff_hash")
        != worktree_diff_hash
        or review_document.get("run_id") != outcome.run_id
        or review_document.get("request_artifact_id")
        != execution_context.get("request_artifact_id")
        or result_document.get("request_artifact_id")
        != execution_context.get("request_artifact_id")
        or not isinstance(review_evidence, dict)
        or review_document.get("mutation_event_sequence")
        != review_evidence.get("mutation_event_sequence")
        or result_document.get("mutation_event_sequence")
        != review_evidence.get("mutation_event_sequence")
        or review_document.get("source_get_diff_sequence")
        != review_evidence.get("source_get_diff_sequence")
        or result_document.get("source_get_diff_sequence")
        != review_evidence.get("source_get_diff_sequence")
        or review_document.get("requirements") != expected_requirements
        or review_document.get("coverage_targets") != expected_targets
        or review_document.get("targeted_validation")
        != expected_validation
        or review_document.get("residual_risks") != expected_risks
        or review_document.get("authoritative_requirement_ids")
        != contract_requirement_ids
        or review_document.get("public_review_contract_hash")
        != public_review_contract.content_hash
        or result_document.get("public_review_contract_hash")
        != public_review_contract.content_hash
        or review_document.get("public_review_contract_schema_version")
        != public_review_contract.schema_version
        or review_document.get("deterministic_correctness_claimed")
        is not False
        or result_document.get("deterministic_correctness_claimed")
        is not False
        or result_document.get("self_attestation") is not True
        or not isinstance(coverage, dict)
        or set(coverage)
        != {
            "schema_version",
            "authoritative_coverage_target_ids",
            "verified_coverage_target_ids",
            "unresolved_coverage_target_ids",
            "coverage_complete",
            "ready_for_submission",
            "deterministic_correctness_claimed",
        }
        or coverage.get("schema_version") != "public-review-coverage-v1"
        or coverage.get("deterministic_correctness_claimed") is not False
        or not isinstance(authoritative_target_ids, list)
        or authoritative_target_ids != contract_target_ids
        or observed_target_ids != authoritative_target_ids
        or coverage.get("verified_coverage_target_ids")
        != verified_target_ids
        or coverage.get("unresolved_coverage_target_ids")
        != unresolved_target_ids
        or coverage.get("coverage_complete") is not coverage_complete
        or coverage.get("ready_for_submission") is not coverage_complete
        or review_document.get("public_review_coverage") != coverage
        or result_document.get("coverage_complete") is not coverage_complete
        or result_document.get("unresolved_coverage_target_ids")
        != unresolved_target_ids
        or result_document.get("verified_coverage_target_ids")
        != verified_target_ids
        or result_document.get("requirement_count")
        != len(expected_requirements)
        or result_document.get("coverage_target_count")
        != len(expected_targets)
        or result_document.get("targeted_validation_count")
        != len(expected_validation)
        or result_document.get("residual_risk_count")
        != len(expected_risks)
        or outcome.payload.get("review_schema_version") != "task-review-v3"
        or outcome.payload.get("requirement_count")
        != len(expected_requirements)
        or outcome.payload.get("coverage_target_count")
        != len(expected_targets)
        or outcome.payload.get("targeted_validation_count")
        != len(expected_validation)
        or outcome.payload.get("residual_risk_count")
        != len(expected_risks)
        or outcome.payload.get("coverage_complete") is not coverage_complete
        or outcome.payload.get("unresolved_coverage_target_ids")
        != unresolved_target_ids
        or outcome.payload.get("verified_coverage_target_ids")
        != verified_target_ids
    ):
        raise RecoveryError(
            "v11 feedback-clearing review binding is invalid"
        )
    return coverage_complete


def _validate_v11_feedback_clearing_mutation(
    events: list[RunEvent],
    mutation: RunEvent,
    *,
    artifact_store: ArtifactStore | None,
    worktree_diff_hash: str,
    expected_baseline_diff_hash: str,
    source_failure_sequence: int,
    expected_feedback: dict[str, Any],
    expected_feedback_build: dict[str, Any],
    expected_provider: str,
) -> None:
    """Require the complete prepared-patch lifecycle before clearing feedback."""

    if artifact_store is None:
        raise RecoveryError(
            "phase-evidence-v11 requires the artifact store for mutation binding"
        )
    action_id = mutation.correlation_id
    calls = [
        event
        for event in events
        if event.type == EventType.TOOL_CALLED
        and event.correlation_id == action_id
        and event.payload.get("tool") == "apply_patch"
    ]
    outcomes = [
        event
        for event in events
        if event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
        and event.correlation_id == action_id
        and event.payload.get("tool") == "apply_patch"
    ]
    prepared_events = [
        event
        for event in events
        if event.type == EventType.PATCH_PREPARED
        and event.correlation_id == action_id
    ]
    applications = [
        event
        for event in events
        if event.type == EventType.PATCH_APPLIED
        and event.correlation_id == action_id
    ]
    if (
        mutation.actor != "tool-gateway"
        or not isinstance(action_id, str)
        or not action_id
        or len(calls) != 1
        or len(prepared_events) != 1
        or len(outcomes) != 1
        or len(applications) != 1
        or applications[0].event_id != mutation.event_id
    ):
        raise RecoveryError(
            "v11 feedback-clearing mutation lifecycle is ambiguous"
        )
    call = calls[0]
    prepared = prepared_events[0]
    outcome = outcomes[0]
    try:
        patch_artifact = Artifact.model_validate(
            call.payload.get("patch_artifact")
        )
        patch = artifact_store.read_bytes(patch_artifact).decode(
            "utf-8",
            errors="strict",
        )
    except (ValueError, UnicodeDecodeError) as exc:
        raise RecoveryError(
            "v11 feedback-clearing mutation patch CAS is invalid"
        ) from exc
    mutation_context, mutation_model = _validate_v11_feedback_tool_generation(
        events,
        call,
        expected_tool="apply_patch",
        expected_arguments={"patch": patch},
        expected_feedback=expected_feedback,
        expected_feedback_build=expected_feedback_build,
        artifact_store=artifact_store,
        label="feedback-clearing mutation",
        expected_provider=expected_provider,
    )
    try:
        intent_artifact = Artifact.model_validate(
            prepared.payload.get("intent_artifact")
        )
        intent_document = json.loads(
            artifact_store.read_bytes(intent_artifact).decode(
                "utf-8",
                errors="strict",
            )
        )
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(
            "v11 feedback-clearing mutation intent CAS is invalid"
        ) from exc
    expected_input_hash = sha256_text(
        canonical_json({"tool": "apply_patch", "input": {"patch": patch}})
    )
    baseline_diff_hash = call.payload.get("worktree_diff_hash")
    expected_normalized_hash = (
        sha256_text(
            canonical_json(
                {
                    "tool": "apply_patch",
                    "input": {"patch": patch},
                    "worktree_diff_hash": baseline_diff_hash,
                    "state_marker": None,
                }
            )
        )
        if isinstance(baseline_diff_hash, str)
        else None
    )
    patch_hash = patch_artifact.content_hash
    files = (
        intent_document.get("files")
        if isinstance(intent_document, dict)
        else None
    )
    intent_paths: list[str] = []
    if not isinstance(files, list) or not files:
        raise RecoveryError(
            "v11 feedback-clearing mutation intent has no file images"
        )
    try:
        from patchloop.agent.tools import _patch_paths

        for entry in files:
            if (
                not isinstance(entry, dict)
                or set(entry)
                != {
                    "path",
                    "mode",
                    "git_mode",
                    "preimage_artifact",
                    "postimage_artifact",
                }
                or type(entry.get("mode")) is not int
                or not 0 <= entry["mode"] <= 0o7777
                or entry.get("git_mode") not in {"100644", "100755"}
            ):
                raise ValueError("invalid file image entry")
            path = safe_relative_path(
                str(entry["path"]),
                field_name="prepared patch path",
            )
            if path in intent_paths:
                raise ValueError("duplicate file image path")
            intent_paths.append(path)
            preimage = Artifact.model_validate(
                entry["preimage_artifact"]
            )
            artifact_store.read_bytes(preimage)
            postimage_raw = entry["postimage_artifact"]
            if postimage_raw is not None:
                postimage = Artifact.model_validate(postimage_raw)
                artifact_store.read_bytes(postimage)
        patch_paths = _patch_paths(patch)
    except (ContractError, KeyError, TypeError, ValueError) as exc:
        raise RecoveryError(
            "v11 feedback-clearing mutation file images are invalid"
        ) from exc
    if intent_paths != patch_paths:
        raise RecoveryError(
            "v11 feedback-clearing mutation file images do not match the patch"
        )

    try:
        result_path = Path(str(outcome.payload["artifact_path"])).resolve()
        relative = result_path.relative_to(artifact_store.root.resolve())
        result_bytes = result_path.read_bytes()
        parts = relative.parts
        result_document = json.loads(
            result_bytes.decode("utf-8", errors="strict")
        )
    except (
        KeyError,
        OSError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RecoveryError(
            "v11 feedback-clearing mutation result CAS is invalid"
        ) from exc
    result_changed_files = (
        result_document.get("changed_files")
        if isinstance(result_document, dict)
        else None
    )
    try:
        result_paths_valid = bool(
            isinstance(result_changed_files, list)
            and all(
                isinstance(path, str)
                and safe_relative_path(
                    path,
                    field_name="applied patch result path",
                )
                == path
                for path in result_changed_files
            )
        )
    except ContractError as exc:
        raise RecoveryError(
            "v11 feedback-clearing mutation result paths are invalid"
        ) from exc
    if (
        call.actor != "agent"
        or call.payload.get("artifact_id") != patch_artifact.artifact_id
        or call.payload.get("artifact_path") != patch_artifact.path
        or call.payload.get("input_hash") != expected_input_hash
        or call.payload.get("normalized_call_hash")
        != expected_normalized_hash
        or baseline_diff_hash != expected_baseline_diff_hash
        or call.payload.get("execution") != "dispatched"
        or prepared.actor != "tool-gateway"
        or set(prepared.payload)
        != {
            "schema_version",
            "artifact_id",
            "artifact_path",
            "content_hash",
            "size_bytes",
            "intent_artifact",
            "baseline_worktree_diff_hash",
            "expected_worktree_diff_hash",
        }
        or prepared.payload.get("schema_version")
        != "patch-mutation-intent-v1"
        or prepared.payload.get("artifact_id")
        != intent_artifact.artifact_id
        or prepared.payload.get("artifact_path") != intent_artifact.path
        or prepared.payload.get("content_hash")
        != intent_artifact.content_hash
        or prepared.payload.get("size_bytes") != intent_artifact.size_bytes
        or not isinstance(intent_document, dict)
        or set(intent_document)
        != {
            "schema_version",
            "run_id",
            "action_id",
            "input_hash",
            "patch_artifact",
            "baseline_worktree_diff_hash",
            "expected_worktree_diff_hash",
            "files",
        }
        or intent_document.get("schema_version")
        != "patch-mutation-intent-v1"
        or intent_document.get("run_id") != mutation.run_id
        or intent_document.get("action_id") != action_id
        or intent_document.get("input_hash") != expected_input_hash
        or intent_document.get("patch_artifact")
        != patch_artifact.model_dump(mode="json")
        or intent_document.get("baseline_worktree_diff_hash")
        != expected_baseline_diff_hash
        or intent_document.get("expected_worktree_diff_hash")
        != worktree_diff_hash
        or prepared.payload.get("baseline_worktree_diff_hash")
        != expected_baseline_diff_hash
        or prepared.payload.get("expected_worktree_diff_hash")
        != worktree_diff_hash
        or outcome.actor != "tool-gateway"
        or outcome.type != EventType.TOOL_SUCCEEDED
        or outcome.payload.get("status") != "succeeded"
        or outcome.payload.get("patch_hash") != patch_hash
        or mutation.payload.get("patch_hash") != patch_hash
        or outcome.payload.get("worktree_diff_hash")
        != worktree_diff_hash
        or mutation.payload.get("worktree_diff_hash")
        != worktree_diff_hash
        or len(parts) != 4
        or parts[0:2] != ("objects", "sha256")
        or len(parts[2]) != 2
        or len(parts[3]) != 62
        or sha256_bytes(result_bytes) != f"sha256:{parts[2]}{parts[3]}"
        or not isinstance(outcome.payload.get("artifact_id"), str)
        or not outcome.payload["artifact_id"]
        or outcome.payload.get("result_artifact") is not None
        or not isinstance(result_document, dict)
        or set(result_document)
        != {
            "patch_hash",
            "worktree_diff_hash",
            "changed_files",
            "diff_lines",
        }
        or result_document.get("patch_hash") != patch_hash
        or result_document.get("worktree_diff_hash")
        != worktree_diff_hash
        or not isinstance(result_changed_files, list)
        or not result_paths_valid
        or len(result_changed_files) != len(intent_paths)
        or set(result_changed_files) != set(intent_paths)
        or type(result_document.get("diff_lines")) is not int
        or result_document["diff_lines"] < 1
        or not source_failure_sequence
        < mutation_context.sequence
        < mutation_model.sequence
        < call.sequence
        < prepared.sequence
        < outcome.sequence
        < mutation.sequence
    ):
        raise RecoveryError(
            "v11 feedback-clearing mutation binding is invalid"
        )


def _coverage_rejection_feedback_v11(
    events: list[RunEvent],
    *,
    worktree_diff_hash: str,
    artifact_store: ArtifactStore | None,
    public_review_contract: PublicReviewContract,
    model_provider: str = "mock",
) -> tuple[dict[str, Any] | None, dict[str, Any], int | None]:
    """Rehydrate the active V11 coverage rejection from durable CAS data.

    A complete later review or a new mutation resolves the feedback.  A valid
    partial review does not. Until then, the exact gateway rejection is
    rendered outside the bounded recent event window so a fresh worker receives
    the same public recovery contract.
    """

    source_failure = next(
        (
            event
            for event in reversed(events)
            if event.type == EventType.TOOL_FAILED
            and event.payload.get("tool") == "review_task"
            and (
                event.payload.get("error_code")
                == COVERAGE_REJECTION_ERROR_CODE
                or (
                    isinstance(event.payload.get("error_details"), dict)
                    and event.payload["error_details"].get("schema_version")
                    == "coverage-citation-error-v1"
                )
            )
        ),
        None,
    )

    inactive_evidence = {
        "schema_version": COVERAGE_REJECTION_FEEDBACK_SCHEMA,
        "included": False,
        "source_through_sequence": events[-1].sequence if events else 0,
    }
    if source_failure is None:
        return None, inactive_evidence, None
    if artifact_store is None:
        raise RecoveryError(
            "phase-evidence-v11 requires the artifact store to rehydrate "
            "coverage rejection feedback"
        )
    if (
        source_failure.actor != "tool-gateway"
        or source_failure.payload.get("status") != "rejected"
    ):
        raise RecoveryError(
            "v11 coverage rejection has an invalid tool outcome identity"
        )
    action_id = source_failure.correlation_id
    if not isinstance(action_id, str) or not action_id:
        raise RecoveryError(
            "v11 coverage rejection lacks an action identity"
        )

    source_calls = [
        event
        for event in events
        if event.sequence < source_failure.sequence
        and event.type == EventType.TOOL_CALLED
        and event.actor == "agent"
        and event.correlation_id == action_id
        and event.payload.get("tool") == "review_task"
    ]
    source_outcomes = [
        event
        for event in events
        if event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
        and event.correlation_id == action_id
        and event.payload.get("tool") == "review_task"
    ]
    if (
        len(source_calls) != 1
        or len(source_outcomes) != 1
        or source_outcomes[0].event_id != source_failure.event_id
    ):
        raise RecoveryError(
            "v11 coverage rejection does not have one exact call/outcome pair"
        )
    source_call = source_calls[0]

    try:
        input_artifact = Artifact.model_validate(
            source_call.payload.get("input_artifact")
        )
    except ValueError as exc:
        raise RecoveryError(
            "v11 rejected review call lacks a valid input artifact"
        ) from exc
    if (
        source_call.payload.get("artifact_id")
        != input_artifact.artifact_id
        or source_call.payload.get("artifact_path") != input_artifact.path
    ):
        raise RecoveryError(
            "v11 rejected review call conflicts with its input artifact"
        )
    try:
        input_document = json.loads(
            artifact_store.read_bytes(input_artifact).decode(
                "utf-8",
                errors="strict",
            )
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(
            "v11 rejected review input artifact is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(input_document, dict):
        raise RecoveryError(
            "v11 rejected review input artifact must be an object"
        )
    arguments = input_document.get("input")
    execution_context = input_document.get("execution_context")
    source_diff_hash = source_call.payload.get("worktree_diff_hash")
    expected_source_normalized_hash = (
        sha256_text(
            canonical_json(
                {
                    "tool": "review_task",
                    "input": arguments,
                    "worktree_diff_hash": source_diff_hash,
                    "state_marker": None,
                }
            )
        )
        if isinstance(arguments, dict)
        and isinstance(source_diff_hash, str)
        else None
    )
    if (
        set(input_document) != {"tool", "input", "execution_context"}
        or input_document.get("tool") != "review_task"
        or not isinstance(arguments, dict)
        or not isinstance(execution_context, dict)
        or set(execution_context)
        != {
            "request_artifact_id",
            "phase",
            "presented_tool_results",
            "review_evidence",
            "coverage_rejection_feedback",
        }
        or execution_context.get("phase") != Phase.REVIEW.value
        or source_call.payload.get("request_phase") != Phase.REVIEW.value
        or source_call.payload.get("request_artifact_id")
        != execution_context.get("request_artifact_id")
        or source_call.payload.get("input_hash")
        != sha256_text(
            canonical_json({"tool": "review_task", "input": arguments})
        )
        or source_call.payload.get("normalized_call_hash")
        != expected_source_normalized_hash
        or source_call.payload.get("execution") != "dispatched"
    ):
        raise RecoveryError(
            "v11 rejected review call conflicts with its durable input"
        )

    request_artifact_id = execution_context.get("request_artifact_id")
    source_contexts = [
        event
        for event in events
        if event.sequence < source_call.sequence
        and event.type == EventType.CONTEXT_BUILT
        and event.actor == "context-builder"
        and event.payload.get("artifact_id") == request_artifact_id
    ]
    if len(source_contexts) != 1:
        raise RecoveryError(
            "v11 rejected review lacks one prior request context"
        )
    source_context = source_contexts[0]
    try:
        request_path = Path(
            str(source_context.payload["artifact_path"])
        ).resolve()
        relative = request_path.relative_to(
            artifact_store.root.resolve()
        )
        request_bytes = request_path.read_bytes()
        parts = relative.parts
        request_document = json.loads(
            request_bytes.decode("utf-8", errors="strict")
        )
    except (
        KeyError,
        OSError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RecoveryError(
            "v11 rejected review request context artifact is invalid"
        ) from exc
    if (
        len(parts) != 4
        or parts[0:2] != ("objects", "sha256")
        or len(parts[2]) != 2
        or len(parts[3]) != 62
        or sha256_bytes(request_bytes)
        != f"sha256:{parts[2]}{parts[3]}"
        or not isinstance(request_document, dict)
    ):
        raise RecoveryError(
            "v11 rejected review request context is not content-addressed"
        )
    request_body = request_document.get("request_body")
    context_build = request_document.get("context_build")
    worker_claim = request_document.get("worker_claim")
    request_envelope_valid, rendered_context = _v11_request_envelope(
        request_document,
        expected_provider=model_provider,
    )
    try:
        rendered_payload = json.loads(rendered_context or "")
    except json.JSONDecodeError as exc:
        raise RecoveryError(
            "v11 rejected review request context is not valid JSON"
        ) from exc
    calculated_request_hash = (
        sha256_text(canonical_json(request_body))
        if isinstance(request_body, dict)
        else None
    )
    if (
        not request_envelope_valid
        or not isinstance(rendered_payload, dict)
        or not isinstance(context_build, dict)
        or context_build.get("schema_version")
        != "context-build-evidence-v11"
        or not isinstance(worker_claim, dict)
        or worker_claim.get("schema_version")
        != "worker-claim-evidence-v1"
        or source_context.payload.get("worker_claim") != worker_claim
        or request_document.get("request_body_hash")
        != calculated_request_hash
        or source_context.payload.get("request_body_hash")
        != calculated_request_hash
        or source_context.payload.get("context_hash")
        != sha256_text(rendered_context)
        or rendered_payload.get("phase") != Phase.REVIEW.value
        or rendered_payload.get("coverage_rejection_feedback")
        != execution_context.get("coverage_rejection_feedback")
        or context_build.get("review_evidence")
        != execution_context.get("review_evidence")
        or context_build.get("tool_results")
        != execution_context.get("presented_tool_results")
    ):
        raise RecoveryError(
            "v11 rejected review conflicts with its prior request context"
        )

    source_model_events = [
        event
        for event in events
        if source_context.sequence < event.sequence < source_call.sequence
        and event.type == EventType.MODEL_CALLED
    ]
    request_content_hash = sha256_bytes(request_bytes)
    if (
        len(source_model_events) != 1
        or source_model_events[0].actor != "model-adapter"
        or source_model_events[0].payload.get("request_artifact_id")
        != request_artifact_id
        or source_model_events[0].payload.get("request_artifact_path")
        != source_context.payload.get("artifact_path")
        or source_model_events[0].payload.get("request_artifact_hash")
        != request_content_hash
        or source_model_events[0].payload.get("request_body_hash")
        != calculated_request_hash
    ):
        raise RecoveryError(
            "v11 rejected review request was not the sole dispatched generation"
        )
    _validate_v11_model_tool_call(
        source_model_events[0],
        source_call,
        expected_tool="review_task",
        expected_arguments=arguments,
        artifact_store=artifact_store,
        label="rejected review source",
    )

    try:
        result_artifact = Artifact.model_validate(
            source_failure.payload.get("result_artifact")
        )
    except ValueError as exc:
        raise RecoveryError(
            "v11 coverage rejection lacks a valid result artifact"
        ) from exc
    if (
        source_failure.payload.get("artifact_id")
        != result_artifact.artifact_id
        or source_failure.payload.get("artifact_path")
        != result_artifact.path
    ):
        raise RecoveryError(
            "v11 coverage rejection conflicts with its result artifact"
        )
    try:
        result_document = json.loads(
            artifact_store.read_bytes(result_artifact).decode(
                "utf-8",
                errors="strict",
            )
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(
            "v11 coverage rejection artifact is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(result_document, dict):
        raise RecoveryError(
            "v11 coverage rejection artifact must be an object"
        )
    details = result_document.get("error_details")
    event_message = source_failure.payload.get("error_message")
    if (
        set(result_document)
        != {
            "tool",
            "status",
            "error_code",
            "error_message",
            "error_details",
        }
        or result_document.get("tool") != "review_task"
        or result_document.get("status") != "rejected"
        or result_document.get("error_code")
        != COVERAGE_REJECTION_ERROR_CODE
        or result_document.get("error_message")
        != "review_task coverage target citation was rejected"
        or not isinstance(details, dict)
        or source_failure.payload.get("error_code")
        != result_document.get("error_code")
        or source_failure.payload.get("error_details") != details
        or event_message != result_document["error_message"]
    ):
        raise RecoveryError(
            "v11 coverage rejection event conflicts with its structured result"
        )

    required_detail_fields = {
        "schema_version",
        "stage",
        "reason",
        "coverage_target_id",
        "requirement_id",
        "submitted_event_sequences",
        "allowed_event_sequences",
        "invalid_event_sequences",
        "evidence_kind",
        "required_evidence",
        "mutation_event_sequence",
        "worktree_diff_hash",
        "source_get_diff_sequence",
        "guidance",
    }
    if (
        set(details) != required_detail_fields
        or details.get("schema_version") != "coverage-citation-error-v1"
        or details.get("stage") != "review"
        or details.get("reason")
        not in {
            "target_evidence_not_allowed",
            "verified_target_evidence_mismatch",
            "fresh_target_evidence_required",
        }
        or not isinstance(details.get("coverage_target_id"), str)
        or not isinstance(details.get("requirement_id"), str)
        or details.get("evidence_kind")
        not in {"current_diff_inspection", "passing_validation"}
        or not isinstance(details.get("required_evidence"), dict)
        or type(details.get("mutation_event_sequence")) is not int
        or not isinstance(details.get("worktree_diff_hash"), str)
        or type(details.get("source_get_diff_sequence")) is not int
        or not isinstance(details.get("guidance"), str)
        or not details["guidance"]
    ):
        raise RecoveryError(
            "v11 coverage rejection details have an invalid shape"
        )
    sequence_fields = (
        "submitted_event_sequences",
        "allowed_event_sequences",
        "invalid_event_sequences",
    )
    for field in sequence_fields:
        sequences = details.get(field)
        if (
            not isinstance(sequences, list)
            or any(type(sequence) is not int or sequence < 1 for sequence in sequences)
            or len(sequences) != len(set(sequences))
        ):
            raise RecoveryError(
                "v11 coverage rejection has invalid event sequences"
            )

    target_id = details["coverage_target_id"]
    contract_target = None
    contract_requirement_id = None
    for requirement in public_review_contract.requirements:
        for target in requirement.coverage_targets:
            if target.coverage_target_id == target_id:
                contract_target = target
                contract_requirement_id = requirement.requirement_id
                break
        if contract_target is not None:
            break
    if contract_target is None or contract_requirement_id is None:
        raise RecoveryError(
            "v11 coverage rejection references an unknown public target"
        )
    expected_required_evidence = (
        {
            "tool": "read_file",
            "path": contract_target.path,
            "anchor": contract_target.anchor,
        }
        if contract_target.evidence_kind == "current_diff_inspection"
        else {
            "tool": "run_check",
            "check_ids": list(contract_target.check_ids),
        }
    )
    expected_guidance = (
        "Locate the exact public anchor if needed, then use read_file to "
        "obtain a complete current-diff result containing it. Retry with "
        "only the refreshed target-specific advertised sequences."
        if contract_target.evidence_kind == "current_diff_inspection"
        else (
            "Run an allowed registered check for this target on the current "
            "diff, then retry with only the refreshed target-specific "
            "advertised sequences."
        )
    )
    if (
        details["requirement_id"] != contract_requirement_id
        or details["evidence_kind"] != contract_target.evidence_kind
        or details["required_evidence"] != expected_required_evidence
    ):
        raise RecoveryError(
            "v11 coverage rejection conflicts with the public review contract"
        )

    prior_events = [
        event for event in events if event.sequence < source_context.sequence
    ]
    (
        expected_active_feedback,
        expected_active_feedback_build,
        _,
    ) = _coverage_rejection_feedback_v11(
        prior_events,
        worktree_diff_hash=details["worktree_diff_hash"],
        artifact_store=artifact_store,
        public_review_contract=public_review_contract,
        model_provider=model_provider,
    )
    if (
        expected_active_feedback_build.get("source_through_sequence")
        != source_context.sequence - 1
        or execution_context.get("coverage_rejection_feedback")
        != expected_active_feedback
        or rendered_payload.get("coverage_rejection_feedback")
        != expected_active_feedback
        or context_build.get("coverage_rejection_feedback")
        != expected_active_feedback_build
        or source_context.payload.get("coverage_rejection_feedback")
        != expected_active_feedback_build
    ):
        raise RecoveryError(
            "v11 rejected review active feedback lacks durable predecessor provenance"
        )

    review_evidence = execution_context.get("review_evidence")
    target_sequences = (
        review_evidence.get("coverage_target_event_sequences")
        if isinstance(review_evidence, dict)
        else None
    )
    allowed_sequences = details["allowed_event_sequences"]
    submitted_sequences = details["submitted_event_sequences"]
    invalid_sequences = details["invalid_event_sequences"]
    coverage_rows = arguments.get("coverage_targets")
    submitted_rows = (
        [
            row
            for row in coverage_rows
            if isinstance(row, dict)
            and row.get("coverage_target_id") == target_id
        ]
        if isinstance(coverage_rows, list)
        else []
    )
    submitted_status = (
        submitted_rows[0].get("status")
        if len(submitted_rows) == 1
        else None
    )
    active_feedback = execution_context.get(
        "coverage_rejection_feedback"
    )
    expected_reason = (
        "target_evidence_not_allowed"
        if not set(submitted_sequences).issubset(allowed_sequences)
        else (
            "verified_target_evidence_mismatch"
            if submitted_status == "verified"
            and (
                not allowed_sequences
                or submitted_sequences != allowed_sequences
            )
            else (
                "fresh_target_evidence_required"
                if isinstance(active_feedback, dict)
                and active_feedback.get("schema_version")
                == COVERAGE_REJECTION_FEEDBACK_SCHEMA
                and active_feedback.get("coverage_target_id")
                == target_id
                and (
                    submitted_status != "verified"
                    or type(
                        active_feedback.get(
                            "source_failure_sequence"
                        )
                    )
                    is not int
                    or not any(
                        sequence
                        > active_feedback[
                            "source_failure_sequence"
                        ]
                        for sequence in submitted_sequences
                    )
                )
                else None
            )
        )
    )
    if (
        not isinstance(review_evidence, dict)
        or review_evidence.get("schema_version")
        != REVIEW_EVIDENCE_V2_SCHEMA
        or not isinstance(target_sequences, dict)
        or target_sequences.get(target_id) != allowed_sequences
        or len(submitted_rows) != 1
        or submitted_rows[0].get("evidence_event_sequences")
        != submitted_sequences
        or expected_reason is None
        or details["reason"] != expected_reason
        or details["guidance"] != expected_guidance
        or invalid_sequences
        != [
            sequence
            for sequence in submitted_sequences
            if sequence not in set(allowed_sequences)
        ]
        or review_evidence.get("mutation_event_sequence")
        != details["mutation_event_sequence"]
        or review_evidence.get("worktree_diff_hash")
        != details["worktree_diff_hash"]
        or review_evidence.get("source_get_diff_sequence")
        != details["source_get_diff_sequence"]
    ):
        raise RecoveryError(
            "v11 coverage rejection conflicts with its request evidence"
        )
    _validate_v11_review_arguments(
        events,
        call_sequence=source_call.sequence,
        arguments=arguments,
        review_evidence=review_evidence,
        artifact_store=artifact_store,
        worktree_diff_hash=details["worktree_diff_hash"],
        public_review_contract=public_review_contract,
        rejection_details=details,
    )

    mutation_events = [
        event
        for event in events
        if event.sequence < source_failure.sequence
        and event.type == EventType.PATCH_APPLIED
    ]
    latest_mutation = mutation_events[-1] if mutation_events else None
    source_worktree_diff_hash = details["worktree_diff_hash"]
    if (
        latest_mutation is None
        or details["mutation_event_sequence"] != latest_mutation.sequence
        or latest_mutation.payload.get("worktree_diff_hash")
        != source_worktree_diff_hash
        or source_call.payload.get("worktree_diff_hash")
        != source_worktree_diff_hash
    ):
        raise RecoveryError(
            "v11 coverage rejection is not bound to the active mutation"
        )

    events_by_sequence = {event.sequence: event for event in events}
    source_get_diff = events_by_sequence.get(
        details["source_get_diff_sequence"]
    )
    if (
        source_get_diff is None
        or source_get_diff.sequence >= source_call.sequence
        or source_get_diff.type != EventType.TOOL_SUCCEEDED
        or source_get_diff.payload.get("tool") != "get_diff"
    ):
        raise RecoveryError(
            "v11 coverage rejection lacks its current-diff review source"
        )
    _validate_v11_get_diff_success(
        events,
        source_get_diff,
        artifact_store=artifact_store,
        worktree_diff_hash=source_worktree_diff_hash,
    )

    for sequence in allowed_sequences:
        event = events_by_sequence.get(sequence)
        if event is None or event.sequence >= source_call.sequence:
            raise RecoveryError(
                "v11 coverage rejection allows unavailable evidence"
            )
        rendered_event, result_evidence = _context_event(
            event,
            policy_version="phase-evidence-v10",
            artifact_store=artifact_store,
        )
        tool_result = rendered_event["payload"].get("tool_result")
        if (
            result_evidence is None
            or result_evidence.get("available") is not True
            or result_evidence.get("truncated") is not False
            or not isinstance(tool_result, dict)
            or tool_result.get("worktree_diff_hash")
            != source_worktree_diff_hash
        ):
            raise RecoveryError(
                "v11 coverage rejection allows incomplete evidence"
            )
        if contract_target.evidence_kind == "current_diff_inspection":
            if (
                rendered_event["payload"].get("tool") != "read_file"
                or tool_result.get("path") != contract_target.path
                or not isinstance(tool_result.get("content"), str)
                or contract_target.anchor not in tool_result["content"]
            ):
                raise RecoveryError(
                    "v11 coverage rejection allows the wrong inspection evidence"
                )
        elif (
            rendered_event["payload"].get("tool") != "run_check"
            or tool_result.get("check_id") not in contract_target.check_ids
            or tool_result.get("passed") is not True
        ):
            raise RecoveryError(
                "v11 coverage rejection allows the wrong validation evidence"
            )

    visible = {
        "schema_version": COVERAGE_REJECTION_FEEDBACK_SCHEMA,
        "source_call_sequence": source_call.sequence,
        "source_failure_sequence": source_failure.sequence,
        "action_id": action_id,
        "error_code": COVERAGE_REJECTION_ERROR_CODE,
        "reason": details["reason"],
        "coverage_target_id": target_id,
        "requirement_id": details["requirement_id"],
        "submitted_event_sequences": submitted_sequences,
        "allowed_event_sequences": allowed_sequences,
        "invalid_event_sequences": invalid_sequences,
        "evidence_kind": details["evidence_kind"],
        "required_evidence": details["required_evidence"],
        "mutation_event_sequence": details["mutation_event_sequence"],
        "worktree_diff_hash": details["worktree_diff_hash"],
        "source_get_diff_sequence": details["source_get_diff_sequence"],
        "guidance": details["guidance"],
    }
    evidence_base = {
        "schema_version": COVERAGE_REJECTION_FEEDBACK_SCHEMA,
        "included": True,
        "source_call_sequence": source_call.sequence,
        "source_failure_sequence": source_failure.sequence,
        "action_id": action_id,
        "content_hash": sha256_text(canonical_json(visible)),
        "input_artifact": {
            "artifact_id": input_artifact.artifact_id,
            "content_hash": input_artifact.content_hash,
            "size_bytes": input_artifact.size_bytes,
        },
        "result_artifact": {
            "artifact_id": result_artifact.artifact_id,
            "content_hash": result_artifact.content_hash,
            "size_bytes": result_artifact.size_bytes,
        },
    }
    clearing_events = [
        event
        for event in events
        if event.sequence > source_failure.sequence
        and (
            event.type == EventType.PATCH_APPLIED
            or (
                event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "review_task"
            )
        )
    ]
    for clearing_event in clearing_events:
        if clearing_event.type == EventType.PATCH_APPLIED:
            clearing_diff_hash = clearing_event.payload.get(
                "worktree_diff_hash"
            )
            if not isinstance(clearing_diff_hash, str):
                raise RecoveryError(
                    "v11 feedback-clearing mutation lacks a diff identity"
                )
            _validate_v11_feedback_clearing_mutation(
                events,
                clearing_event,
                artifact_store=artifact_store,
                worktree_diff_hash=clearing_diff_hash,
                expected_baseline_diff_hash=source_worktree_diff_hash,
                source_failure_sequence=source_failure.sequence,
                expected_feedback=visible,
                expected_feedback_build=evidence_base,
                expected_provider=model_provider,
            )
            return None, inactive_evidence, None
        complete = _validate_v11_feedback_clearing_review(
            events,
            clearing_event,
            artifact_store=artifact_store,
            worktree_diff_hash=source_worktree_diff_hash,
            expected_feedback=visible,
            expected_feedback_build=evidence_base,
            public_review_contract=public_review_contract,
            expected_provider=model_provider,
        )
        if complete:
            return None, inactive_evidence, None
    if worktree_diff_hash != source_worktree_diff_hash:
        raise RecoveryError(
            "v11 active coverage rejection conflicts with the current diff"
        )
    evidence = {
        **evidence_base,
        "source_through_sequence": events[-1].sequence,
    }
    return visible, evidence, source_failure.sequence
