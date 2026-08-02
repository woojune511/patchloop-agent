"""Independent V11 coverage-rejection trace qualification."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    EventType,
    ExperimentPurpose,
    RunManifest,
    RunStatus,
    TaskPackage,
)
from patchloop.errors import RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_text


def _qualification_helper(name: str) -> Any:
    """Resolve shared V10/runtime helpers only after qualification is loaded."""

    from patchloop.evals import qualification

    return getattr(qualification, name)


def _nested_cas_artifact_evidence(*args: Any, **kwargs: Any) -> Any:
    return _qualification_helper("_nested_cas_artifact_evidence")(*args, **kwargs)


def _request_context(*args: Any, **kwargs: Any) -> Any:
    return _qualification_helper("_request_context")(*args, **kwargs)


def _request_evidence_payload(*args: Any, **kwargs: Any) -> Any:
    return _qualification_helper("_request_evidence_payload")(*args, **kwargs)


def _request_runtime_contract_valid(*args: Any, **kwargs: Any) -> Any:
    return _qualification_helper("_request_runtime_contract_valid")(*args, **kwargs)


def _v10_coverage_decision_evidence(*args: Any, **kwargs: Any) -> Any:
    return _qualification_helper("_v10_coverage_decision_evidence")(*args, **kwargs)


def _v10_recompute_review_anchor(*args: Any, **kwargs: Any) -> Any:
    return _qualification_helper("_v10_recompute_review_anchor")(*args, **kwargs)


def _v11_correlated_success_call_evidence(
    *,
    artifact_root: Path,
    events: list[Any],
    outcome: Any,
    expected_tool: str,
    worktree_diff_hash: str,
) -> tuple[Any, dict[str, Any]]:
    """Bind one V11 success outcome to its exact dispatched call and input."""

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
    input_valid, input_item, input_bytes = _nested_cas_artifact_evidence(
        artifact_root=artifact_root,
        event_id=call.event_id,
        role=f"v11-{expected_tool}-input",
        raw_artifact=call.payload.get("input_artifact"),
    )
    if not input_valid or input_bytes is None:
        raise RecoveryError(f"v11 {expected_tool} input CAS is invalid")
    input_document = json.loads(input_bytes.decode("utf-8"))
    arguments = (
        input_document.get("input")
        if isinstance(input_document, dict)
        else None
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
    if (
        call.actor != "agent"
        or not isinstance(input_document, dict)
        or set(input_document) != {"tool", "input"}
        or input_document.get("tool") != expected_tool
        or not isinstance(arguments, dict)
        or call.payload.get("artifact_id") != input_item.get("artifact_id")
        or call.payload.get("artifact_path")
        != input_item.get("declared_path")
        or call.payload.get("input_hash") != expected_input_hash
        or call.payload.get("normalized_call_hash")
        != expected_normalized_hash
        or call.payload.get("worktree_diff_hash") != worktree_diff_hash
        or call.payload.get("execution") != "dispatched"
    ):
        raise RecoveryError(f"v11 {expected_tool} call binding is invalid")
    return call, arguments


def _v11_get_diff_result_evidence(
    *,
    artifact_root: Path,
    artifact_store: ArtifactStore,
    events: list[Any],
    outcome: Any,
    worktree_diff_hash: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind V11 get_diff call, result CAS, and exact patch bytes."""

    _, arguments = _v11_correlated_success_call_evidence(
        artifact_root=artifact_root,
        events=events,
        outcome=outcome,
        expected_tool="get_diff",
        worktree_diff_hash=worktree_diff_hash,
    )
    if arguments != {}:
        raise RecoveryError("v11 get_diff call arguments are invalid")
    rendered, result_evidence = _v10_recompute_review_anchor(
        outcome,
        artifact_store=artifact_store,
    )
    result_document = rendered.get("payload", {}).get("tool_result")
    if (
        outcome.type != EventType.TOOL_SUCCEEDED
        or outcome.payload.get("tool") != "get_diff"
        or outcome.payload.get("patch_hash") != worktree_diff_hash
        or outcome.payload.get("worktree_diff_hash")
        != worktree_diff_hash
        or not isinstance(result_document, dict)
        or set(result_document)
        != {
            "patch",
            "patch_hash",
            "worktree_diff_hash",
            "changed_files",
            "added_lines",
            "deleted_lines",
        }
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
        or result_evidence.get("available") is not True
        or result_evidence.get("truncated") is True
    ):
        raise RecoveryError("v11 get_diff result binding is invalid")
    return result_document, result_evidence


def _v11_latest_worker_claim(
    *,
    worker_claims: list[dict[str, Any]],
    claim_evidence: Any,
    context_timestamp: datetime,
    label: str,
) -> tuple[dict[str, Any], datetime]:
    """Resolve one request claim by durable SQLite row order at build time."""

    if (
        not isinstance(claim_evidence, dict)
        or claim_evidence.get("schema_version")
        != "worker-claim-evidence-v1"
    ):
        raise RecoveryError(f"v11 {label} worker claim evidence is invalid")
    matching_claims = [
        claim
        for claim in worker_claims
        if claim_evidence
        == {
            "schema_version": "worker-claim-evidence-v1",
            **claim,
        }
    ]
    try:
        matching_time = datetime.fromisoformat(
            str(matching_claims[0].get("claimed_at"))
        )
        parsed_claims = [
            (datetime.fromisoformat(str(claim.get("claimed_at"))), claim)
            for claim in worker_claims
        ]
    except (IndexError, TypeError, ValueError) as exc:
        raise RecoveryError(f"v11 {label} worker claim is malformed") from exc
    if any(
        current[0] < previous[0]
        for previous, current in zip(
            parsed_claims,
            parsed_claims[1:],
            strict=False,
        )
    ):
        raise RecoveryError(
            f"v11 {label} worker claims conflict with durable row order"
        )
    prior_claims = [
        claim
        for claimed_at, claim in parsed_claims
        if claimed_at <= context_timestamp
    ]
    if (
        len(matching_claims) != 1
        or matching_time > context_timestamp
        or not prior_claims
        or prior_claims[-1] != matching_claims[0]
    ):
        raise RecoveryError(
            f"v11 {label} worker claim is not the active durable claim"
        )
    return matching_claims[0], matching_time


def _v11_bind_model_request(
    *,
    artifact_root: Path,
    context_event: Any,
    model_event: Any,
    label: str,
    expected_call: Any | None = None,
    expected_tool: str | None = None,
    expected_arguments: dict[str, Any] | None = None,
) -> None:
    """Bind one request and optional tool call to exact model CAS objects."""

    try:
        request_path = Path(
            str(context_event.payload["artifact_path"])
        ).resolve()
        request_path.relative_to(artifact_root.resolve())
        content_hash = sha256_bytes(request_path.read_bytes())
        response_path = Path(
            str(model_event.payload["artifact_path"])
        ).resolve()
        relative = response_path.relative_to(artifact_root.resolve())
        response_bytes = response_path.read_bytes()
        response_document = json.loads(response_bytes.decode("utf-8"))
    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RecoveryError(
            f"v11 {label} request artifact cannot be rebound"
        ) from exc
    parts = relative.parts
    declared_calls = (
        response_document.get("tool_calls")
        if isinstance(response_document, dict)
        else None
    )
    expected_tool_call = (
        {
            "name": expected_tool,
            "action_id": expected_call.correlation_id,
            "arguments": expected_arguments,
        }
        if expected_call is not None
        and isinstance(expected_tool, str)
        and isinstance(expected_arguments, dict)
        else None
    )
    matching_calls = (
        [item for item in declared_calls if item == expected_tool_call]
        if expected_tool_call is not None
        and isinstance(declared_calls, list)
        else []
    )
    if (
        context_event.type != EventType.CONTEXT_BUILT
        or context_event.actor != "context-builder"
        or model_event.type != EventType.MODEL_CALLED
        or model_event.actor != "model-adapter"
        or context_event.sequence >= model_event.sequence
        or model_event.payload.get("request_artifact_id")
        != context_event.payload.get("artifact_id")
        or model_event.payload.get("request_artifact_path")
        != context_event.payload.get("artifact_path")
        or model_event.payload.get("request_artifact_hash") != content_hash
        or model_event.payload.get("request_body_hash")
        != context_event.payload.get("request_body_hash")
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
        or (
            expected_call is not None
            and (
                expected_tool_call is None
                or len(matching_calls) != 1
                or not model_event.sequence < expected_call.sequence
            )
        )
    ):
        raise RecoveryError(
            f"v11 {label} context was not consumed by its model request"
        )


def _v11_bind_tool_call_generation(
    *,
    artifact_root: Path,
    events: list[Any],
    context_events: list[Any],
    call: Any,
    expected_tool: str,
    expected_arguments: dict[str, Any],
    label: str,
) -> tuple[Any, Any]:
    """Bind a tool call to the immediately preceding model generation."""

    prior_models = [
        event
        for event in events
        if event.type == EventType.MODEL_CALLED
        and event.sequence < call.sequence
    ]
    if not prior_models:
        raise RecoveryError(f"v11 {label} lacks a source generation")
    model_event = prior_models[-1]
    matching_contexts = [
        event
        for event in context_events
        if event.sequence < model_event.sequence
        and event.payload.get("artifact_id")
        == model_event.payload.get("request_artifact_id")
    ]
    intervening_contexts = [
        event
        for event in context_events
        if matching_contexts
        and matching_contexts[0].sequence
        < event.sequence
        < model_event.sequence
    ]
    if len(matching_contexts) != 1 or intervening_contexts:
        raise RecoveryError(f"v11 {label} request context is ambiguous")
    context_event = matching_contexts[0]
    _v11_bind_model_request(
        artifact_root=artifact_root,
        context_event=context_event,
        model_event=model_event,
        label=label,
        expected_call=call,
        expected_tool=expected_tool,
        expected_arguments=expected_arguments,
    )
    return context_event, model_event


def _v11_validate_rejected_review_arguments(
    *,
    contract: Any,
    arguments: dict[str, Any],
    review_evidence: dict[str, Any],
    execution_context: dict[str, Any],
    events: list[Any],
    artifact_store: ArtifactStore,
    call_sequence: int,
    worktree_diff_hash: str,
    rejected_target_id: str,
    expected_rejection_reason: str,
) -> None:
    """Rebuild the complete V11 source request before trusting its rejection."""

    expected_argument_keys = {
        "requirements",
        "coverage_targets",
        "targeted_validation",
        "residual_risks",
    }
    if (
        set(arguments) != expected_argument_keys
        or len(canonical_json(arguments).encode("utf-8")) > 16_000
    ):
        raise RecoveryError("v11 rejected review argument envelope is invalid")

    requirements = list(contract.requirements)
    requirement_ids = [item.requirement_id for item in requirements]
    requirement_by_id = {
        item.requirement_id: item for item in requirements
    }
    targets = [
        target
        for requirement in requirements
        for target in requirement.coverage_targets
    ]
    target_ids = [target.coverage_target_id for target in targets]
    target_by_id = {target.coverage_target_id: target for target in targets}
    raw_requirements = arguments.get("requirements")
    raw_targets = arguments.get("coverage_targets")
    if (
        not isinstance(raw_requirements, list)
        or len(raw_requirements) != len(requirement_ids)
        or not isinstance(raw_targets, list)
        or len(raw_targets) != len(target_ids)
    ):
        raise RecoveryError("v11 rejected review row cardinality is invalid")

    target_mapping = review_evidence.get(
        "coverage_target_event_sequences"
    )
    citable = review_evidence.get("citable_event_sequences")
    passing = review_evidence.get("passing_check_event_sequences")
    mutation_sequence = review_evidence.get("mutation_event_sequence")
    source_diff_sequence = review_evidence.get("source_get_diff_sequence")
    presented = execution_context.get("presented_tool_results")
    if (
        review_evidence.get("schema_version") != "review-evidence-v2"
        or review_evidence.get("pinning_active") is not True
        or review_evidence.get("worktree_diff_hash") != worktree_diff_hash
        or type(mutation_sequence) is not int
        or type(source_diff_sequence) is not int
        or not mutation_sequence < source_diff_sequence < call_sequence
        or not isinstance(target_mapping, dict)
        or set(target_mapping) != set(target_ids)
        or not isinstance(citable, list)
        or any(type(sequence) is not int for sequence in citable)
        or len(citable) != len(set(citable))
        or not isinstance(passing, list)
        or any(type(sequence) is not int for sequence in passing)
        or len(passing) != len(set(passing))
        or not isinstance(presented, list)
    ):
        raise RecoveryError("v11 rejected review evidence authority is invalid")
    for sequences in target_mapping.values():
        if (
            not isinstance(sequences, list)
            or any(type(sequence) is not int for sequence in sequences)
            or sequences != sorted(set(sequences))
        ):
            raise RecoveryError(
                "v11 rejected review target evidence mapping is invalid"
            )
    expected_citable: list[int] = []
    for target_id in target_ids:
        for sequence in target_mapping[target_id]:
            if sequence not in expected_citable:
                expected_citable.append(sequence)
    for sequence in passing:
        if sequence not in expected_citable:
            expected_citable.append(sequence)
    if source_diff_sequence not in expected_citable:
        expected_citable.append(source_diff_sequence)
    if citable != expected_citable:
        raise RecoveryError(
            "v11 rejected review citable evidence is not canonical"
        )

    complete_presented = {
        item["event_sequence"]
        for item in presented
        if (
            isinstance(item, dict)
            and type(item.get("event_sequence")) is int
            and item.get("available") is True
            and item.get("truncated") is False
        )
    }
    events_by_sequence = {event.sequence: event for event in events}
    for target_id, target in target_by_id.items():
        for sequence in target_mapping[target_id]:
            event = events_by_sequence.get(sequence)
            if (
                sequence <= mutation_sequence
                or sequence >= call_sequence
                or sequence not in complete_presented
                or sequence not in citable
                or event is None
                or event.type != EventType.TOOL_SUCCEEDED
                or event.payload.get("worktree_diff_hash")
                != worktree_diff_hash
            ):
                raise RecoveryError(
                    "v11 rejected review advertises invalid target evidence"
                )
            rendered_anchor, anchor_evidence = _v10_recompute_review_anchor(
                event,
                artifact_store=artifact_store,
            )
            tool_result = rendered_anchor.get("payload", {}).get(
                "tool_result"
            )
            if (
                anchor_evidence.get("available") is not True
                or anchor_evidence.get("truncated") is not False
                or not isinstance(tool_result, dict)
                or tool_result.get("worktree_diff_hash")
                != worktree_diff_hash
                or (
                    target.evidence_kind == "current_diff_inspection"
                    and (
                        event.payload.get("tool") != "read_file"
                        or tool_result.get("path") != target.path
                        or target.anchor
                        not in tool_result.get("content", "")
                    )
                )
                or (
                    target.evidence_kind == "passing_validation"
                    and (
                        event.payload.get("tool") != "run_check"
                        or tool_result.get("check_id")
                        not in target.check_ids
                        or tool_result.get("passed") is not True
                        or tool_result.get("timed_out") is not False
                    )
                )
            ):
                raise RecoveryError(
                    "v11 rejected review target evidence is not public-bound"
                )

    observed_requirement_ids: set[str] = set()
    for row in raw_requirements:
        if not isinstance(row, dict) or set(row) != {
            "requirement_id",
            "status",
            "evidence_event_sequences",
            "notes",
        }:
            raise RecoveryError("v11 rejected requirement row is invalid")
        requirement_id = row.get("requirement_id")
        status = row.get("status")
        sequences = row.get("evidence_event_sequences")
        notes = row.get("notes")
        if (
            requirement_id not in requirement_by_id
            or requirement_id in observed_requirement_ids
            or status
            not in {"verified", "partially_verified", "unverified"}
            or not isinstance(sequences, list)
            or len(sequences) > 20
            or any(
                type(sequence) is not int or sequence < 1
                for sequence in sequences
            )
            or len(sequences) != len(set(sequences))
            or not isinstance(notes, str)
            or not notes.strip()
            or len(notes) > 2_000
            or (status != "unverified" and not sequences)
        ):
            raise RecoveryError("v11 rejected requirement fields are invalid")
        observed_requirement_ids.add(requirement_id)
    if observed_requirement_ids != set(requirement_ids):
        raise RecoveryError(
            "v11 rejected review requirement IDs are invalid"
        )
    active_feedback = execution_context.get("coverage_rejection_feedback")
    if active_feedback is not None and (
        not isinstance(active_feedback, dict)
        or active_feedback.get("schema_version")
        != "coverage-rejection-feedback-v1"
        or active_feedback.get("coverage_target_id") not in target_by_id
        or type(active_feedback.get("source_failure_sequence")) is not int
        or active_feedback.get("source_failure_sequence", 0) < 1
        or active_feedback.get("worktree_diff_hash") != worktree_diff_hash
    ):
        raise RecoveryError("v11 rejected review active feedback is invalid")

    reproduced_target_id: str | None = None
    observed_target_ids: set[str] = set()
    for row in raw_targets:
        if reproduced_target_id is not None:
            break
        if not isinstance(row, dict) or set(row) != {
            "coverage_target_id",
            "status",
            "evidence_event_sequences",
            "notes",
        }:
            raise RecoveryError("v11 rejected coverage target row is invalid")
        target_id = row.get("coverage_target_id")
        status = row.get("status")
        sequences = row.get("evidence_event_sequences")
        notes = row.get("notes")
        if (
            target_id not in target_by_id
            or target_id in observed_target_ids
            or status
            not in {"verified", "partially_verified", "unverified"}
            or not isinstance(sequences, list)
            or len(sequences) > 20
            or any(
                type(sequence) is not int or sequence < 1
                for sequence in sequences
            )
            or len(sequences) != len(set(sequences))
            or not isinstance(notes, str)
            or not notes.strip()
            or len(notes) > 2_000
        ):
            raise RecoveryError(
                "v11 rejected coverage target fields are invalid"
            )
        observed_target_ids.add(target_id)
        advertised = target_mapping[target_id]
        reason: str | None = None
        if not set(sequences).issubset(advertised):
            reason = "target_evidence_not_allowed"
        elif status == "verified" and (
            not advertised or sequences != advertised
        ):
            reason = "verified_target_evidence_mismatch"
        elif (
            isinstance(active_feedback, dict)
            and active_feedback.get("coverage_target_id") == target_id
            and (
                status != "verified"
                or not any(
                    sequence > active_feedback["source_failure_sequence"]
                    for sequence in sequences
                )
            )
        ):
            reason = "fresh_target_evidence_required"
        if reason is not None:
            if (
                target_id != rejected_target_id
                or reason != expected_rejection_reason
                or reproduced_target_id is not None
            ):
                raise RecoveryError(
                    "v11 rejected review has another target citation failure"
                )
            reproduced_target_id = target_id
        elif (
            (status == "partially_verified" and not sequences)
            or (status == "unverified" and sequences)
        ):
            raise RecoveryError(
                "v11 rejected coverage target status is invalid"
            )
    if reproduced_target_id != rejected_target_id:
        raise RecoveryError("v11 source target rejection was not reproduced")


def _v11_coverage_rejection_recovery_evidence(
    *,
    root: Path,
    manifest: RunManifest,
    package: TaskPackage,
    events: list[Any],
    context_events: list[Any],
    worker_claims: list[dict[str, Any]],
) -> tuple[bool, dict[str, Any]]:
    """Bind a V11 target rejection to restart, fresh evidence, and retry."""

    live_pilot = bool(
        manifest.experiment is not None
        and manifest.experiment.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT
        and manifest.model.provider == "openai"
    )
    offline_validation = bool(
        manifest.model.provider == "mock" and manifest.experiment is None
    )
    selector_valid = bool(
        manifest.tool_schema_version == "v6"
        and manifest.context_policy_version == "phase-evidence-v11"
        and (offline_validation or live_pilot)
    )
    restart_required = not live_pilot
    contract = manifest.public_review_contract
    targets = (
        {
            target.coverage_target_id: (requirement.requirement_id, target)
            for requirement in contract.requirements
            for target in requirement.coverage_targets
        }
        if contract is not None
        and contract.schema_version == "public-review-contract-v2"
        else {}
    )
    artifact_root = (root / "artifacts").resolve()
    artifact_store = ArtifactStore(artifact_root)
    events_by_sequence = {event.sequence: event for event in events}
    rejections = [
        event
        for event in events
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("tool") == "review_task"
        and event.payload.get("error_code")
        == "COVERAGE_CITATION_REJECTED"
    ]
    failed_sequences: list[int] = []
    failure_reasons: list[dict[str, Any]] = []
    verified_rejection_sequences: list[int] = []
    restart_rejection_sequences: list[int] = []
    rehydrated_context_sequences: list[int] = []
    recovery_evidence_sequences: list[int] = []
    refreshed_diff_sequences: list[int] = []
    complete_review_sequences: list[int] = []
    cleared_context_sequences: list[int] = []

    for failure in rejections:
        try:
            action_id = failure.correlation_id
            calls = [
                event
                for event in events
                if event.type == EventType.TOOL_CALLED
                and event.payload.get("tool") == "review_task"
                and event.correlation_id == action_id
                and event.sequence < failure.sequence
            ]
            outcomes = [
                event
                for event in events
                if event.type
                in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
                and event.payload.get("tool") == "review_task"
                and event.correlation_id == action_id
            ]
            if (
                failure.actor != "tool-gateway"
                or failure.payload.get("status") != "rejected"
                or not isinstance(action_id, str)
                or not action_id
                or len(calls) != 1
                or outcomes != [failure]
            ):
                raise RecoveryError(
                    "v11 rejected review lifecycle is ambiguous"
                )
            call = calls[0]

            input_valid, input_item, input_bytes = (
                _nested_cas_artifact_evidence(
                    artifact_root=artifact_root,
                    event_id=call.event_id,
                    role="v11-rejected-review-input",
                    raw_artifact=call.payload.get("input_artifact"),
                )
            )
            if not input_valid or input_bytes is None:
                raise RecoveryError("v11 rejected review input CAS is invalid")
            input_document = json.loads(input_bytes.decode("utf-8"))
            arguments = (
                input_document.get("input")
                if isinstance(input_document, dict)
                else None
            )
            execution_context = (
                input_document.get("execution_context")
                if isinstance(input_document, dict)
                else None
            )
            expected_input_hash = (
                sha256_text(
                    canonical_json(
                        {"tool": "review_task", "input": arguments}
                    )
                )
                if isinstance(arguments, dict)
                else None
            )
            diff_hash = call.payload.get("worktree_diff_hash")
            expected_normalized_hash = (
                sha256_text(
                    canonical_json(
                        {
                            "tool": "review_task",
                            "input": arguments,
                            "worktree_diff_hash": diff_hash,
                            "state_marker": None,
                        }
                    )
                )
                if isinstance(arguments, dict)
                and isinstance(diff_hash, str)
                else None
            )
            if (
                call.actor != "agent"
                or not isinstance(input_document, dict)
                or set(input_document)
                != {"tool", "input", "execution_context"}
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
                or execution_context.get("phase") != "REVIEW"
                or call.payload.get("artifact_id")
                != input_item.get("artifact_id")
                or call.payload.get("artifact_path")
                != input_item.get("declared_path")
                or call.payload.get("input_hash") != expected_input_hash
                or call.payload.get("normalized_call_hash")
                != expected_normalized_hash
                or call.payload.get("execution") != "dispatched"
                or call.payload.get("request_artifact_id")
                != execution_context.get("request_artifact_id")
                or call.payload.get("request_phase") != "REVIEW"
            ):
                raise RecoveryError(
                    "v11 rejected review input binding is invalid"
                )

            source_contexts = [
                event
                for event in context_events
                if event.sequence < call.sequence
                and event.actor == "context-builder"
                and event.payload.get("artifact_id")
                == execution_context.get("request_artifact_id")
            ]
            if len(source_contexts) != 1:
                raise RecoveryError(
                    "v11 rejected review request context is ambiguous"
                )
            source_context = source_contexts[0]
            request_valid, request_evidence = _request_evidence_payload(
                source_context,
                artifact_root=artifact_root,
                expected_provider=manifest.model.provider,
            )
            context_build = (
                request_evidence.get("context_build")
                if isinstance(request_evidence, dict)
                else None
            )
            source_claim_evidence = (
                request_evidence.get("worker_claim")
                if isinstance(request_evidence, dict)
                else None
            )
            source_rendered_context = _request_context(
                request_evidence.get("request_body")
                if isinstance(request_evidence, dict)
                else None,
                allow_direct_context=True,
            )
            source_rendered_payload = json.loads(
                source_rendered_context or ""
            )
            review_evidence = (
                context_build.get("review_evidence")
                if isinstance(context_build, dict)
                else None
            )
            if (
                not request_valid
                or not isinstance(request_evidence, dict)
                or not _request_runtime_contract_valid(
                    request_evidence.get("request_body"), manifest
                )
                or not isinstance(context_build, dict)
                or context_build.get("schema_version")
                != "context-build-evidence-v11"
                or not isinstance(review_evidence, dict)
                or review_evidence.get("schema_version")
                != "review-evidence-v2"
                or execution_context.get("review_evidence")
                != review_evidence
                or execution_context.get("presented_tool_results")
                != context_build.get("tool_results")
                or not isinstance(source_rendered_payload, dict)
                or source_rendered_payload.get(
                    "coverage_rejection_feedback"
                )
                != execution_context.get(
                    "coverage_rejection_feedback"
                )
                or not isinstance(source_claim_evidence, dict)
                or source_claim_evidence.get("schema_version")
                != "worker-claim-evidence-v1"
                or source_context.payload.get("worker_claim")
                != source_claim_evidence
            ):
                raise RecoveryError(
                    "v11 rejected review source context is invalid"
                )
            source_models = [
                event
                for event in events
                if event.type == EventType.MODEL_CALLED
                and source_context.sequence < event.sequence < call.sequence
            ]
            if len(source_models) != 1:
                raise RecoveryError(
                    "v11 rejected review source generation is ambiguous"
                )
            _v11_bind_model_request(
                artifact_root=artifact_root,
                context_event=source_context,
                model_event=source_models[0],
                label="rejected review source",
                expected_call=call,
                expected_tool="review_task",
                expected_arguments=arguments,
            )
            source_claim, source_claim_time = _v11_latest_worker_claim(
                worker_claims=worker_claims,
                claim_evidence=source_claim_evidence,
                context_timestamp=source_context.timestamp,
                label="rejected review source",
            )

            result_valid, result_item, result_bytes = (
                _nested_cas_artifact_evidence(
                    artifact_root=artifact_root,
                    event_id=failure.event_id,
                    role="v11-coverage-rejection-result",
                    raw_artifact=failure.payload.get("result_artifact"),
                )
            )
            if not result_valid or result_bytes is None:
                raise RecoveryError(
                    "v11 coverage rejection result CAS is invalid"
                )
            result_document = json.loads(result_bytes.decode("utf-8"))
            details = (
                result_document.get("error_details")
                if isinstance(result_document, dict)
                else None
            )
            target_id = (
                details.get("coverage_target_id")
                if isinstance(details, dict)
                else None
            )
            target_binding = targets.get(target_id)
            target_rows = arguments.get("coverage_targets")
            submitted_rows = (
                [
                    row
                    for row in target_rows
                    if isinstance(row, dict)
                    and row.get("coverage_target_id") == target_id
                ]
                if isinstance(target_rows, list)
                else []
            )
            allowed_mapping = review_evidence.get(
                "coverage_target_event_sequences"
            )
            if (
                target_binding is None
                or len(submitted_rows) != 1
                or not isinstance(allowed_mapping, dict)
            ):
                raise RecoveryError(
                    "v11 coverage rejection target is not public-bound"
                )
            requirement_id, target = target_binding
            submitted_row = submitted_rows[0]
            submitted_sequences = submitted_row.get(
                "evidence_event_sequences"
            )
            allowed_sequences = allowed_mapping.get(target_id)
            if (
                not isinstance(submitted_sequences, list)
                or any(type(item) is not int for item in submitted_sequences)
                or not isinstance(allowed_sequences, list)
                or any(type(item) is not int for item in allowed_sequences)
            ):
                raise RecoveryError(
                    "v11 coverage rejection sequences are invalid"
                )
            invalid_sequences = [
                sequence
                for sequence in submitted_sequences
                if sequence not in allowed_sequences
            ]
            active_feedback = execution_context.get(
                "coverage_rejection_feedback"
            )
            if not set(submitted_sequences).issubset(allowed_sequences):
                expected_reason = "target_evidence_not_allowed"
            elif (
                submitted_row.get("status") == "verified"
                and (
                    not allowed_sequences
                    or submitted_sequences != allowed_sequences
                )
            ):
                expected_reason = "verified_target_evidence_mismatch"
            elif (
                isinstance(active_feedback, dict)
                and active_feedback.get("schema_version")
                == "coverage-rejection-feedback-v1"
                and active_feedback.get("coverage_target_id")
                == target_id
                and (
                    submitted_row.get("status") != "verified"
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
            ):
                expected_reason = "fresh_target_evidence_required"
            else:
                raise RecoveryError(
                    "v11 rejection reason cannot be reproduced"
                )
            _v11_validate_rejected_review_arguments(
                contract=contract,
                arguments=arguments,
                review_evidence=review_evidence,
                execution_context=execution_context,
                events=events,
                artifact_store=artifact_store,
                call_sequence=call.sequence,
                worktree_diff_hash=diff_hash,
                rejected_target_id=target_id,
                expected_rejection_reason=expected_reason,
            )
            if target.evidence_kind == "current_diff_inspection":
                required_evidence: dict[str, Any] = {
                    "tool": "read_file",
                    "path": target.path,
                    "anchor": target.anchor,
                }
                guidance = (
                    "Locate the exact public anchor if needed, then use "
                    "read_file to obtain a complete current-diff result "
                    "containing it. Retry with only the refreshed "
                    "target-specific advertised sequences."
                )
            else:
                required_evidence = {
                    "tool": "run_check",
                    "check_ids": list(target.check_ids),
                }
                guidance = (
                    "Run an allowed registered check for this target on the "
                    "current diff, then retry with only the refreshed "
                    "target-specific advertised sequences."
                )
            expected_details = {
                "schema_version": "coverage-citation-error-v1",
                "stage": "review",
                "reason": expected_reason,
                "coverage_target_id": target_id,
                "requirement_id": requirement_id,
                "submitted_event_sequences": submitted_sequences,
                "allowed_event_sequences": allowed_sequences,
                "invalid_event_sequences": invalid_sequences,
                "evidence_kind": target.evidence_kind,
                "required_evidence": required_evidence,
                "mutation_event_sequence": review_evidence.get(
                    "mutation_event_sequence"
                ),
                "worktree_diff_hash": review_evidence.get(
                    "worktree_diff_hash"
                ),
                "source_get_diff_sequence": review_evidence.get(
                    "source_get_diff_sequence"
                ),
                "guidance": guidance,
            }
            expected_message = (
                "review_task coverage target citation was rejected"
            )
            expected_result = {
                "tool": "review_task",
                "status": "rejected",
                "error_code": "COVERAGE_CITATION_REJECTED",
                "error_message": expected_message,
                "error_details": expected_details,
            }
            source_diff = events_by_sequence.get(
                expected_details["source_get_diff_sequence"]
            )
            mutation = events_by_sequence.get(
                expected_details["mutation_event_sequence"]
            )
            if (
                result_document != expected_result
                or failure.payload.get("artifact_id")
                != result_item.get("artifact_id")
                or failure.payload.get("artifact_path")
                != result_item.get("declared_path")
                or failure.payload.get("error_message") != expected_message
                or failure.payload.get("error_details") != expected_details
                or diff_hash != expected_details["worktree_diff_hash"]
                or mutation is None
                or mutation.type != EventType.PATCH_APPLIED
                or mutation.payload.get("worktree_diff_hash") != diff_hash
                or source_diff is None
                or source_diff.type != EventType.TOOL_SUCCEEDED
                or source_diff.payload.get("tool") != "get_diff"
                or not mutation.sequence < source_diff.sequence < call.sequence
            ):
                raise RecoveryError(
                    "v11 coverage rejection result is not independently reproducible"
                )

            from patchloop.agent.context import (
                _coverage_rejection_feedback_v11,
            )

            prior_events = [
                event
                for event in events
                if event.sequence < source_context.sequence
            ]
            (
                expected_active_feedback,
                expected_active_feedback_build,
                _,
            ) = _coverage_rejection_feedback_v11(
                prior_events,
                worktree_diff_hash=diff_hash,
                artifact_store=artifact_store,
                public_review_contract=contract,
                model_provider=manifest.model.provider,
            )
            if (
                expected_active_feedback_build.get(
                    "source_through_sequence"
                )
                != source_context.sequence - 1
                or execution_context.get("coverage_rejection_feedback")
                != expected_active_feedback
                or source_rendered_payload.get(
                    "coverage_rejection_feedback"
                )
                != expected_active_feedback
                or context_build.get("coverage_rejection_feedback")
                != expected_active_feedback_build
                or source_context.payload.get(
                    "coverage_rejection_feedback"
                )
                != expected_active_feedback_build
            ):
                raise RecoveryError(
                    "v11 rejected review active feedback is not predecessor-bound"
                )
            _v11_get_diff_result_evidence(
                artifact_root=artifact_root,
                artifact_store=artifact_store,
                events=events,
                outcome=source_diff,
                worktree_diff_hash=diff_hash,
            )
            for sequence in allowed_sequences:
                anchor_event = events_by_sequence.get(sequence)
                if anchor_event is None or anchor_event.sequence >= call.sequence:
                    raise RecoveryError(
                        "v11 rejection advertises unavailable evidence"
                    )
                rendered_anchor, anchor_evidence = (
                    _v10_recompute_review_anchor(
                        anchor_event,
                        artifact_store=artifact_store,
                    )
                )
                tool_result = rendered_anchor.get("payload", {}).get(
                    "tool_result"
                )
                if (
                    anchor_evidence.get("truncated") is True
                    or not isinstance(tool_result, dict)
                    or tool_result.get("worktree_diff_hash") != diff_hash
                    or (
                        target.evidence_kind == "current_diff_inspection"
                        and (
                            anchor_event.payload.get("tool") != "read_file"
                            or tool_result.get("path") != target.path
                            or target.anchor not in tool_result.get("content", "")
                        )
                    )
                    or (
                        target.evidence_kind == "passing_validation"
                        and (
                            anchor_event.payload.get("tool") != "run_check"
                            or tool_result.get("check_id")
                            not in target.check_ids
                            or tool_result.get("passed") is not True
                        )
                    )
                ):
                    raise RecoveryError(
                        "v11 rejection allowed evidence is invalid"
                    )

            next_models = [
                event
                for event in events
                if event.type == EventType.MODEL_CALLED
                and event.sequence > failure.sequence
            ]
            if not next_models:
                raise RecoveryError(
                    "v11 rejection has no post-failure model request"
                )
            next_model = next_models[0]
            later_contexts = [
                event
                for event in context_events
                if failure.sequence < event.sequence < next_model.sequence
            ]
            if len(later_contexts) != 1:
                raise RecoveryError(
                    "v11 rejection rehydrated request context is ambiguous"
                )
            rehydrated = later_contexts[0]
            if (
                restart_required
                and failure.event_id == rejections[0].event_id
            ):
                restart_boundary_events = [
                    event
                    for event in events
                    if failure.sequence
                    < event.sequence
                    < rehydrated.sequence
                ]
                if (
                    not restart_boundary_events
                    or any(
                        event.type != EventType.CHECKPOINT_SAVED
                        or event.actor != "state-store"
                        for event in restart_boundary_events
                    )
                ):
                    raise RecoveryError(
                        "v11 designated rejection did not stop at the durable "
                        "restart boundary"
                    )
            _v11_bind_model_request(
                artifact_root=artifact_root,
                context_event=rehydrated,
                model_event=next_model,
                label="rehydrated rejection",
            )
            rehydrated_valid, rehydrated_request = (
                _request_evidence_payload(
                    rehydrated,
                    artifact_root=artifact_root,
                    expected_provider=manifest.model.provider,
                )
            )
            rendered_context = _request_context(
                rehydrated_request.get("request_body")
                if isinstance(rehydrated_request, dict)
                else None,
                allow_direct_context=True,
            )
            rendered_payload = json.loads(rendered_context or "")
            rehydrated_build = (
                rehydrated_request.get("context_build")
                if isinstance(rehydrated_request, dict)
                else None
            )
            feedback_build = (
                rehydrated_build.get("coverage_rejection_feedback")
                if isinstance(rehydrated_build, dict)
                else None
            )
            rehydrated_claim_evidence = (
                rehydrated_request.get("worker_claim")
                if isinstance(rehydrated_request, dict)
                else None
            )
            expected_visible = {
                "schema_version": "coverage-rejection-feedback-v1",
                "source_call_sequence": call.sequence,
                "source_failure_sequence": failure.sequence,
                "action_id": action_id,
                "error_code": "COVERAGE_CITATION_REJECTED",
                **{
                    key: expected_details[key]
                    for key in (
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
                    )
                },
            }
            recent_sequences = {
                item.get("sequence")
                for item in rendered_payload.get("recent_events", [])
                if isinstance(item, dict)
            }
            build_result_artifact = (
                {
                    "artifact_id": result_item.get("artifact_id"),
                    "content_hash": result_item.get(
                        "declared_content_hash"
                    ),
                    "size_bytes": result_item.get("declared_size_bytes"),
                }
            )
            build_input_artifact = {
                "artifact_id": input_item.get("artifact_id"),
                "content_hash": input_item.get("declared_content_hash"),
                "size_bytes": input_item.get("declared_size_bytes"),
            }
            expected_feedback_build = {
                "schema_version": "coverage-rejection-feedback-v1",
                "included": True,
                "source_call_sequence": call.sequence,
                "source_failure_sequence": failure.sequence,
                "action_id": action_id,
                "content_hash": sha256_text(canonical_json(expected_visible)),
                "input_artifact": build_input_artifact,
                "result_artifact": build_result_artifact,
                "source_through_sequence": rehydrated.sequence - 1,
            }
            if (
                not rehydrated_valid
                or rehydrated.actor != "context-builder"
                or not isinstance(rendered_payload, dict)
                or not isinstance(rehydrated_build, dict)
                or rehydrated_build.get("schema_version")
                != "context-build-evidence-v11"
                or rendered_payload.get("coverage_rejection_feedback")
                != expected_visible
                or feedback_build != expected_feedback_build
                or rehydrated.payload.get("coverage_rejection_feedback")
                != expected_feedback_build
                or not isinstance(rehydrated_claim_evidence, dict)
                or rehydrated_claim_evidence.get("schema_version")
                != "worker-claim-evidence-v1"
                or rehydrated.payload.get("worker_claim")
                != rehydrated_claim_evidence
                or failure.sequence in recent_sequences
            ):
                raise RecoveryError(
                    "v11 coverage rejection feedback rehydration is invalid"
                )

            rehydrated_claim, rehydrated_claim_time = (
                _v11_latest_worker_claim(
                    worker_claims=worker_claims,
                    claim_evidence=rehydrated_claim_evidence,
                    context_timestamp=rehydrated.timestamp,
                    label="rehydrated rejection",
                )
            )
            same_claim = bool(
                rehydrated_claim.get("claim_id")
                == source_claim.get("claim_id")
                and rehydrated_claim.get("owner_id")
                == source_claim.get("owner_id")
            )
            if same_claim:
                if (
                    rehydrated_claim != source_claim
                    or rehydrated_claim_time != source_claim_time
                    or not failure.timestamp < rehydrated.timestamp
                ):
                    raise RecoveryError(
                        "v11 rejection continuing worker claim is invalid"
                    )
            else:
                if (
                    rehydrated_claim.get("prior_status")
                    != RunStatus.RUNNING.value
                    or rehydrated_claim.get("reclaimed") is not True
                    or rehydrated_claim.get("claim_id")
                    == source_claim.get("claim_id")
                    or rehydrated_claim.get("owner_id")
                    == source_claim.get("owner_id")
                    or not failure.timestamp
                    < rehydrated_claim_time
                    <= rehydrated.timestamp
                ):
                    raise RecoveryError(
                        "v11 rejection post-failure worker claim is invalid"
                    )
                restart_rejection_sequences.append(failure.sequence)

            later_mutations = [
                event
                for event in events
                if event.type == EventType.PATCH_APPLIED
                and event.sequence > failure.sequence
            ]
            if later_mutations:
                raise RecoveryError(
                    "v11 rejection recovery crossed a mutation boundary"
                )
            recovery_candidates = []
            recovery_tool = (
                "read_file"
                if target.evidence_kind == "current_diff_inspection"
                else "run_check"
            )
            for event in events:
                if (
                    event.sequence <= next_model.sequence
                    or event.type != EventType.TOOL_SUCCEEDED
                    or event.payload.get("tool") != recovery_tool
                    or event.payload.get("worktree_diff_hash") != diff_hash
                ):
                    continue
                _, recovery_arguments = (
                    _v11_correlated_success_call_evidence(
                        artifact_root=artifact_root,
                        events=events,
                        outcome=event,
                        expected_tool=recovery_tool,
                        worktree_diff_hash=diff_hash,
                    )
                )
                rendered_anchor, anchor_evidence = (
                    _v10_recompute_review_anchor(
                        event,
                        artifact_store=artifact_store,
                    )
                )
                tool_result = rendered_anchor.get("payload", {}).get(
                    "tool_result"
                )
                if not isinstance(tool_result, dict) or anchor_evidence.get(
                    "truncated"
                ) is True:
                    continue
                if target.evidence_kind == "current_diff_inspection":
                    matches = bool(
                        event.payload.get("tool") == "read_file"
                        and recovery_arguments.get("path") == target.path
                        and tool_result.get("path") == target.path
                        and target.anchor in tool_result.get("content", "")
                    )
                else:
                    matches = bool(
                        event.payload.get("tool") == "run_check"
                        and recovery_arguments.get("check_id")
                        == tool_result.get("check_id")
                        and tool_result.get("check_id") in target.check_ids
                        and tool_result.get("passed") is True
                    )
                if matches:
                    recovery_candidates.append(event)
            if not recovery_candidates:
                raise RecoveryError(
                    "v11 rejection lacks fresh exact target evidence"
                )
            successful_reviews = [
                event
                for event in events
                if event.sequence > rehydrated.sequence
                and event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "review_task"
                and event.payload.get("coverage_complete") is True
                and event.payload.get("unresolved_coverage_target_ids") == []
            ]
            if not successful_reviews:
                raise RecoveryError(
                    "v11 rejection lacks a complete retry review"
                )
            complete_review = successful_reviews[0]
            clearing_review_valid, clearing_review_details = (
                _v10_coverage_decision_evidence(
                    root=root,
                    manifest=manifest,
                    package=package,
                    events=events,
                    context_events=context_events,
                )
            )
            if (
                not clearing_review_valid
                or complete_review.sequence
                not in clearing_review_details.get(
                    "verified_review_sequences",
                    [],
                )
                or complete_review.sequence
                not in clearing_review_details.get(
                    "coverage_complete_review_sequences",
                    [],
                )
            ):
                raise RecoveryError(
                    "v11 clearing review failed independent reconstruction"
                )

            clearing_calls = [
                event
                for event in events
                if event.type == EventType.TOOL_CALLED
                and event.payload.get("tool") == "review_task"
                and event.correlation_id == complete_review.correlation_id
                and event.sequence < complete_review.sequence
            ]
            if len(clearing_calls) != 1:
                raise RecoveryError(
                    "v11 clearing review call is ambiguous"
                )
            clearing_call = clearing_calls[0]
            (
                clearing_input_valid,
                clearing_input_item,
                clearing_input_bytes,
            ) = _nested_cas_artifact_evidence(
                artifact_root=artifact_root,
                event_id=clearing_call.event_id,
                role="v11-clearing-review-input",
                raw_artifact=clearing_call.payload.get("input_artifact"),
            )
            clearing_input_document = (
                json.loads(clearing_input_bytes.decode("utf-8"))
                if clearing_input_bytes is not None
                else None
            )
            clearing_execution_context = (
                clearing_input_document.get("execution_context")
                if isinstance(clearing_input_document, dict)
                else None
            )
            clearing_request_id = (
                clearing_execution_context.get("request_artifact_id")
                if isinstance(clearing_execution_context, dict)
                else None
            )
            clearing_contexts = [
                event
                for event in context_events
                if event.actor == "context-builder"
                and event.sequence < clearing_call.sequence
                and event.payload.get("artifact_id") == clearing_request_id
            ]
            if len(clearing_contexts) != 1:
                raise RecoveryError(
                    "v11 clearing review request context is ambiguous"
                )
            clearing_context = clearing_contexts[0]
            clearing_request_valid, clearing_request = (
                _request_evidence_payload(
                    clearing_context,
                    artifact_root=artifact_root,
                    expected_provider=manifest.model.provider,
                )
            )
            clearing_rendered = _request_context(
                clearing_request.get("request_body")
                if isinstance(clearing_request, dict)
                else None,
                allow_direct_context=True,
            )
            clearing_rendered_payload = json.loads(clearing_rendered or "")
            clearing_build = (
                clearing_request.get("context_build")
                if isinstance(clearing_request, dict)
                else None
            )
            clearing_models = [
                event
                for event in events
                if event.type == EventType.MODEL_CALLED
                and clearing_context.sequence
                < event.sequence
                < clearing_call.sequence
            ]
            if len(clearing_models) != 1:
                raise RecoveryError(
                    "v11 clearing review generation is ambiguous"
                )
            _v11_bind_model_request(
                artifact_root=artifact_root,
                context_event=clearing_context,
                model_event=clearing_models[0],
                label="clearing review",
                expected_call=clearing_call,
                expected_tool="review_task",
                expected_arguments=(
                    clearing_input_document.get("input")
                    if isinstance(clearing_input_document, dict)
                    else None
                ),
            )
            clearing_prefix = [
                event
                for event in events
                if event.sequence < clearing_context.sequence
            ]
            (
                expected_clearing_feedback,
                expected_clearing_feedback_build,
                _,
            ) = _coverage_rejection_feedback_v11(
                clearing_prefix,
                worktree_diff_hash=diff_hash,
                artifact_store=artifact_store,
                public_review_contract=contract,
                model_provider=manifest.model.provider,
            )
            if (
                not clearing_input_valid
                or not isinstance(clearing_input_document, dict)
                or set(clearing_input_document)
                != {"tool", "input", "execution_context"}
                or clearing_input_document.get("tool") != "review_task"
                or not isinstance(clearing_execution_context, dict)
                or clearing_call.payload.get("artifact_id")
                != clearing_input_item.get("artifact_id")
                or clearing_call.payload.get("artifact_path")
                != clearing_input_item.get("declared_path")
                or clearing_call.payload.get("request_artifact_id")
                != clearing_request_id
                or not clearing_request_valid
                or not isinstance(clearing_rendered_payload, dict)
                or not isinstance(clearing_build, dict)
                or expected_clearing_feedback is None
                or expected_clearing_feedback_build.get(
                    "source_through_sequence"
                )
                != clearing_context.sequence - 1
                or clearing_execution_context.get(
                    "coverage_rejection_feedback"
                )
                != expected_clearing_feedback
                or clearing_rendered_payload.get(
                    "coverage_rejection_feedback"
                )
                != expected_clearing_feedback
                or clearing_build.get("coverage_rejection_feedback")
                != expected_clearing_feedback_build
                or clearing_context.payload.get(
                    "coverage_rejection_feedback"
                )
                != expected_clearing_feedback_build
            ):
                raise RecoveryError(
                    "v11 clearing review did not consume exact active feedback"
                )
            review_valid, _, review_bytes = _nested_cas_artifact_evidence(
                artifact_root=artifact_root,
                event_id=complete_review.event_id,
                role="v11-recovery-task-review",
                raw_artifact=complete_review.payload.get("review_artifact"),
            )
            review_document = (
                json.loads(review_bytes.decode("utf-8"))
                if review_bytes is not None
                else None
            )
            recovery_diff_sequence = (
                review_document.get("source_get_diff_sequence")
                if isinstance(review_document, dict)
                else None
            )
            recovery_diff = events_by_sequence.get(recovery_diff_sequence)
            recovery_diff_evidence: dict[str, Any] | None = None
            recovery_diff_result: dict[str, Any] | None = None
            if recovery_diff is not None:
                recovery_diff_result, recovery_diff_evidence = (
                    _v11_get_diff_result_evidence(
                        artifact_root=artifact_root,
                        artifact_store=artifact_store,
                        events=events,
                        outcome=recovery_diff,
                        worktree_diff_hash=diff_hash,
                    )
                )
            recovered_rows = (
                [
                    row
                    for row in review_document.get("coverage_targets", [])
                    if isinstance(row, dict)
                    and row.get("coverage_target_id") == target_id
                ]
                if isinstance(review_document, dict)
                else []
            )
            fresh_recovery_sequences = (
                [
                    sequence
                    for sequence in recovered_rows[0].get(
                        "evidence_event_sequences",
                        [],
                    )
                    if type(sequence) is int
                    and sequence > failure.sequence
                ]
                if len(recovered_rows) == 1
                else []
            )
            recovery_candidates_by_sequence = {
                event.sequence: event
                for event in recovery_candidates
                if event.sequence < complete_review.sequence
            }
            if (
                not fresh_recovery_sequences
                or any(
                    sequence not in recovery_candidates_by_sequence
                    for sequence in fresh_recovery_sequences
                )
            ):
                raise RecoveryError(
                    "v11 complete retry does not resolve every fresh target "
                    "evidence event"
                )
            cited_recovery_candidates = [
                recovery_candidates_by_sequence[sequence]
                for sequence in fresh_recovery_sequences
            ]
            recovery_bindings: list[
                tuple[Any, Any, Any, Any]
            ] = []
            for recovery in cited_recovery_candidates:
                recovery_call, recovery_arguments = (
                    _v11_correlated_success_call_evidence(
                        artifact_root=artifact_root,
                        events=events,
                        outcome=recovery,
                        expected_tool=recovery_tool,
                        worktree_diff_hash=diff_hash,
                    )
                )
                (
                    recovery_request_context,
                    recovery_request_model,
                ) = _v11_bind_tool_call_generation(
                    artifact_root=artifact_root,
                    events=events,
                    context_events=context_events,
                    call=recovery_call,
                    expected_tool=recovery_tool,
                    expected_arguments=recovery_arguments,
                    label="fresh target recovery",
                )
                recovery_bindings.append(
                    (
                        recovery_request_context,
                        recovery_request_model,
                        recovery_call,
                        recovery,
                    )
                )
            recovery_diff_call, recovery_diff_arguments = (
                _v11_correlated_success_call_evidence(
                    artifact_root=artifact_root,
                    events=events,
                    outcome=recovery_diff,
                    expected_tool="get_diff",
                    worktree_diff_hash=diff_hash,
                )
                if recovery_diff is not None
                else (None, None)
            )
            if (
                recovery_diff_call is None
                or not isinstance(recovery_diff_arguments, dict)
            ):
                raise RecoveryError(
                    "v11 refreshed diff lacks its dispatched call"
                )
            (
                recovery_diff_context,
                recovery_diff_model,
            ) = _v11_bind_tool_call_generation(
                artifact_root=artifact_root,
                events=events,
                context_events=context_events,
                call=recovery_diff_call,
                expected_tool="get_diff",
                expected_arguments=recovery_diff_arguments,
                label="refreshed diff",
            )
            recovery_outcome_sequences = [
                binding[3].sequence for binding in recovery_bindings
            ]
            causal_valid = bool(
                failure.sequence < rehydrated.sequence
                and recovery_bindings
                and recovery_outcome_sequences
                == sorted(set(recovery_outcome_sequences))
                and all(
                    rehydrated.sequence
                    <= recovery_request_context.sequence
                    < recovery_request_model.sequence
                    < recovery_call.sequence
                    < recovery.sequence
                    < recovery_diff_context.sequence
                    for (
                        recovery_request_context,
                        recovery_request_model,
                        recovery_call,
                        recovery,
                    ) in recovery_bindings
                )
                and recovery_outcome_sequences[-1]
                < recovery_diff_context.sequence
                < recovery_diff_model.sequence
                < recovery_diff_call.sequence
                < recovery_diff.sequence
                < clearing_context.sequence
                < clearing_models[0].sequence
                < clearing_call.sequence
                < complete_review.sequence
            )
            if not causal_valid:
                raise RecoveryError(
                    "v11 recovery evidence causal order is invalid"
                )
            feedback_contexts = [
                (binding[0], "fresh target recovery")
                for binding in recovery_bindings
            ]
            feedback_contexts.append(
                (recovery_diff_context, "refreshed diff")
            )
            for feedback_context, feedback_label in feedback_contexts:
                feedback_valid, feedback_request = (
                    _request_evidence_payload(
                        feedback_context,
                        artifact_root=artifact_root,
                        expected_provider=manifest.model.provider,
                    )
                )
                feedback_rendered = _request_context(
                    feedback_request.get("request_body")
                    if isinstance(feedback_request, dict)
                    else None,
                    allow_direct_context=True,
                )
                feedback_rendered_payload = json.loads(
                    feedback_rendered or ""
                )
                feedback_context_build = (
                    feedback_request.get("context_build")
                    if isinstance(feedback_request, dict)
                    else None
                )
                feedback_claim = (
                    feedback_request.get("worker_claim")
                    if isinstance(feedback_request, dict)
                    else None
                )
                feedback_prefix = [
                    event
                    for event in events
                    if event.sequence < feedback_context.sequence
                ]
                (
                    expected_persistent_feedback,
                    expected_persistent_build,
                    _,
                ) = _coverage_rejection_feedback_v11(
                    feedback_prefix,
                    worktree_diff_hash=diff_hash,
                    artifact_store=artifact_store,
                    public_review_contract=contract,
                    model_provider=manifest.model.provider,
                )
                _v11_latest_worker_claim(
                    worker_claims=worker_claims,
                    claim_evidence=feedback_claim,
                    context_timestamp=feedback_context.timestamp,
                    label=feedback_label,
                )
                if (
                    not feedback_valid
                    or expected_persistent_feedback is None
                    or expected_persistent_build.get(
                        "source_through_sequence"
                    )
                    != feedback_context.sequence - 1
                    or feedback_rendered_payload.get(
                        "coverage_rejection_feedback"
                    )
                    != expected_persistent_feedback
                    or not isinstance(feedback_context_build, dict)
                    or feedback_context_build.get(
                        "coverage_rejection_feedback"
                    )
                    != expected_persistent_build
                    or feedback_context.payload.get(
                        "coverage_rejection_feedback"
                    )
                    != expected_persistent_build
                    or feedback_context.payload.get("worker_claim")
                    != feedback_claim
                ):
                    raise RecoveryError(
                        f"v11 {feedback_label} lost active rejection feedback"
                    )
            if (
                not review_valid
                or recovery_diff is None
                or recovery_diff.type != EventType.TOOL_SUCCEEDED
                or recovery_diff.actor != "tool-gateway"
                or recovery_diff.payload.get("tool") != "get_diff"
                or recovery_diff.payload.get("status") != "succeeded"
                or recovery_diff.payload.get("worktree_diff_hash")
                != diff_hash
                or recovery_diff.payload.get("patch_hash") != diff_hash
                or not isinstance(recovery_diff_result, dict)
                or not isinstance(recovery_diff_evidence, dict)
                or recovery_diff_evidence.get("available") is not True
                or recovery_diff_evidence.get("truncated") is True
                or not all(
                    recovery.sequence < recovery_diff.sequence
                    for recovery in cited_recovery_candidates
                )
                or not recovery_diff.sequence < complete_review.sequence
                or complete_review.payload.get("source_get_diff_sequence")
                != recovery_diff.sequence
                or len(recovered_rows) != 1
                or recovered_rows[0].get("status") != "verified"
                or any(
                    recovery.sequence
                    not in recovered_rows[0].get(
                        "evidence_event_sequences",
                        [],
                    )
                    for recovery in cited_recovery_candidates
                )
                or review_document.get("worktree_diff_hash") != diff_hash
            ):
                raise RecoveryError(
                    "v11 complete retry does not cite fresh target evidence"
                )

            clear_models = [
                event
                for event in events
                if event.type == EventType.MODEL_CALLED
                and event.sequence > complete_review.sequence
            ]
            if not clear_models:
                raise RecoveryError(
                    "v11 successful review has no cleared model request"
                )
            clear_model = clear_models[0]
            clear_contexts = [
                event
                for event in context_events
                if complete_review.sequence
                < event.sequence
                < clear_model.sequence
            ]
            if len(clear_contexts) != 1:
                raise RecoveryError(
                    "v11 successful review cleared request is ambiguous"
                )
            clear_context = clear_contexts[0]
            _v11_bind_model_request(
                artifact_root=artifact_root,
                context_event=clear_context,
                model_event=clear_model,
                label="cleared feedback",
            )
            clear_valid, clear_request = _request_evidence_payload(
                clear_context,
                artifact_root=artifact_root,
                expected_provider=manifest.model.provider,
            )
            clear_rendered = _request_context(
                clear_request.get("request_body")
                if isinstance(clear_request, dict)
                else None,
                allow_direct_context=True,
            )
            clear_payload = json.loads(clear_rendered or "")
            clear_build = (
                clear_request.get("context_build")
                if isinstance(clear_request, dict)
                else None
            )
            clear_feedback = (
                clear_build.get("coverage_rejection_feedback")
                if isinstance(clear_build, dict)
                else None
            )
            clear_claim_evidence = (
                clear_request.get("worker_claim")
                if isinstance(clear_request, dict)
                else None
            )
            _v11_latest_worker_claim(
                worker_claims=worker_claims,
                claim_evidence=clear_claim_evidence,
                context_timestamp=clear_context.timestamp,
                label="cleared context",
            )
            expected_clear_feedback = {
                "schema_version": "coverage-rejection-feedback-v1",
                "included": False,
                "source_through_sequence": clear_context.sequence - 1,
            }
            if (
                not clear_valid
                or clear_context.actor != "context-builder"
                or clear_payload.get("coverage_rejection_feedback") is not None
                or clear_feedback != expected_clear_feedback
                or clear_context.payload.get("coverage_rejection_feedback")
                != expected_clear_feedback
                or clear_context.payload.get("worker_claim")
                != clear_claim_evidence
            ):
                raise RecoveryError(
                    "v11 rejection feedback did not clear after review"
                )

            verified_rejection_sequences.append(failure.sequence)
            rehydrated_context_sequences.append(rehydrated.sequence)
            recovery_evidence_sequences.extend(
                recovery.sequence
                for recovery in cited_recovery_candidates
            )
            refreshed_diff_sequences.append(recovery_diff.sequence)
            complete_review_sequences.append(complete_review.sequence)
            cleared_context_sequences.append(clear_context.sequence)
        except (
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            RecoveryError,
        ) as exc:
            failed_sequences.append(failure.sequence)
            failure_reasons.append(
                {"sequence": failure.sequence, "reason": str(exc)}
            )

    mutation_sequences = [
        event.sequence
        for event in events
        if event.type == EventType.PATCH_APPLIED
    ]
    nonvacuous = bool(rejections)
    exercise_required = bool(not live_pilot or nonvacuous)
    designated_restart_rejection_sequence = (
        rejections[0].sequence if rejections else None
    )
    rejection_integrity_valid = bool(
        len(verified_rejection_sequences) == len(rejections)
        and not failed_sequences
        and (
            not restart_required
            or designated_restart_rejection_sequence
            in restart_rejection_sequences
        )
    )
    passed = bool(
        selector_valid
        and targets
        and (nonvacuous or not exercise_required)
        and rejection_integrity_valid
        and len(mutation_sequences) == 1
    )
    exercise_status = (
        "failed"
        if not passed
        else "passed"
        if nonvacuous
        else "inconclusive"
    )
    return passed, {
        "selector_valid": selector_valid,
        "live_pilot": live_pilot,
        "exercise_required": exercise_required,
        "restart_required": restart_required,
        "exercise_status": exercise_status,
        "exercise_reason": (
            "rejection_not_observed"
            if exercise_status == "inconclusive"
            else None
        ),
        "public_target_count": len(targets),
        "rejection_count": len(rejections),
        "nonvacuous": nonvacuous,
        "verified_rejection_sequences": verified_rejection_sequences,
        "restart_rejection_sequences": restart_rejection_sequences,
        "restart_observed": bool(restart_rejection_sequences),
        "designated_restart_rejection_sequence": (
            designated_restart_rejection_sequence
        ),
        "rehydrated_context_sequences": rehydrated_context_sequences,
        "recovery_evidence_sequences": recovery_evidence_sequences,
        "refreshed_diff_sequences": refreshed_diff_sequences,
        "complete_review_sequences": complete_review_sequences,
        "cleared_context_sequences": cleared_context_sequences,
        "patch_applied_sequences": mutation_sequences,
        "worker_claim_count": len(worker_claims),
        "running_reclaim_count": sum(
            claim.get("reclaimed") is True for claim in worker_claims
        ),
        "failed_rejection_sequences": failed_sequences,
        "failure_reasons": failure_reasons,
    }
