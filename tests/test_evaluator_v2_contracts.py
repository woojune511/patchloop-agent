from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1,
    Artifact,
    EvaluatorContractBinding,
    EvaluatorSafetyContract,
    EvaluatorV2EvaluationReceipt,
    EventType,
    EvidenceArtifactRef,
    ExperimentPurpose,
    ExperimentRunContext,
    ModelConfig,
    RunEvent,
    RunManifest,
    RunOutcomeKind,
    RunResult,
    RunStatus,
    SafetyControlKind,
    SafetyEvidenceBundle,
    SafetyEvidenceReason,
    SafetyEvidenceRecord,
    SafetyPolicyProfile,
    TaskPackage,
    Usage,
    Verdicts,
    VerdictState,
    VerifierResult,
    aggregate_v2_verdict_states,
    build_evaluator_contract_binding,
    build_safety_evidence_bundle_ref,
    docker_registered_check_policy_input_hash,
    registered_check_result_hash,
)
from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.runner import (
    DockerSandbox,
    LocalSandbox,
    SandboxResult,
    registered_check_execution_policy,
)
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json
from patchloop.verifier.core import EvaluationEngine
from patchloop.verifier.evidence import (
    RegisteredCheckResultEvidenceV2,
    ScopePolicyResultEvidenceV2,
    evaluator_v2_check_execution_id,
    evaluator_v2_event_prefix_hash,
    evaluator_v2_marker_set_hash,
    validate_evaluator_v2_artifact_chain,
)
from patchloop.verifier.policy import PolicyOutcome
from patchloop.verifier.receipt import (
    EvaluatorV2QualificationAuthority,
    issue_evaluator_v2_evaluation_receipt,
    validate_persisted_evaluator_v2_evaluation_receipt,
)
from patchloop.verifier.runtime_evidence import (
    EvaluatorV2RuntimeAuthority,
    build_evaluator_safety_contract_v2,
    build_submitted_patch_ref,
    evaluator_v2_manifest_runtime_tuple_hash,
    produce_evaluator_v2_result,
    produce_evaluator_v2_result_from_state,
    produce_registered_check_evidence_v2,
    produce_scope_policy_evidence_v2,
)

SHA_A = "sha256:" + ("a" * 64)
SHA_B = "sha256:" + ("b" * 64)
SHA_C = "sha256:" + ("c" * 64)
SHA_D = "sha256:" + ("d" * 64)
SCOPE_IDS = ("dependency", "public_api", "scope", "test_tampering")
PRIVATE_MARKERS = (b"private-marker-alpha", b"private-marker-beta")
TOOL_SCHEMA_HASH = sha256_json(TOOL_SCHEMAS_V2)


@dataclass
class V2Chain:
    package: TaskPackage
    contract: EvaluatorSafetyContract
    binding: EvaluatorContractBinding
    manifest: RunManifest
    bundle: SafetyEvidenceBundle
    result: RunResult
    manifest_bytes: bytes
    bundle_bytes: bytes
    result_bytes: bytes
    events: tuple[RunEvent, ...]
    descriptors: dict[str, Artifact]
    evidence_bytes: dict[str, bytes]


def _artifact(
    index: int,
    role: str,
    *,
    content: bytes | None = None,
    media_type: str = "application/json; charset=utf-8",
) -> tuple[EvidenceArtifactRef, Artifact, bytes]:
    artifact_id = f"art_{index:032x}"
    body = content or json.dumps(
        {"artifact_index": index, "role": role},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    ref = EvidenceArtifactRef(
        artifact_id=artifact_id,
        content_hash=sha256_bytes(body),
        size_bytes=len(body),
        media_type=media_type,
        role=role,
    )
    descriptor = Artifact(
        artifact_id=artifact_id,
        content_hash=ref.content_hash,
        media_type=media_type,
        size_bytes=len(body),
        path=f"C:/virtual/{artifact_id}",
        created_at=datetime(2026, 8, 11, tzinfo=UTC),
    )
    return ref, descriptor, body


def _safety_contract(package: TaskPackage) -> EvaluatorSafetyContract:
    return build_evaluator_safety_contract_v2(
        package=package,
        tool_schemas=TOOL_SCHEMAS_V2,
        private_markers=PRIVATE_MARKERS,
    )


def _v1_manifest() -> RunManifest:
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    return RunManifest(
        run_id="run_golden",
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        base_commit=package.public.repository.base_commit,
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
        harness_git_commit="a" * 40,
        tool_schema_version="v2",
        context_policy_version="phase-evidence-v5",
        memory_policy_version="v1",
        model=ModelConfig(provider="mock", model_id="mock-v1"),
        sandbox_backend="local",
        created_at=datetime(2026, 8, 11, tzinfo=UTC),
    )


def _v1_result() -> RunResult:
    verifier = VerifierResult(
        verifier_result_id="vr_golden",
        run_id="run_golden",
        check_type="hidden",
        check_id="hidden",
        state=VerdictState.PASS,
        duration_ms=1,
    )
    return RunResult(
        run_id="run_golden",
        agent_submission_status="completed",
        evaluation_status="completed",
        scope_compliant_success=True,
        official=False,
        verdicts=Verdicts(
            hidden_tests=VerdictState.PASS,
            regression_tests=VerdictState.PASS,
            scope_policy=VerdictState.PASS,
            safety_policy=VerdictState.PASS,
        ),
        usage=Usage(),
        submitted_patch_artifact_id="artifact_golden",
        verifier_results=[verifier],
    )


def _manifest(
    package: TaskPackage,
    binding: EvaluatorContractBinding,
    *,
    sandbox_backend: str,
) -> RunManifest:
    return RunManifest(
        schema_version="run-manifest-v2",
        run_id="run_evaluator_v2",
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        base_commit=package.public.repository.base_commit,
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
        evaluator_contract=binding,
        harness_git_commit="b" * 40,
        tool_schema_version="v2",
        context_policy_version="phase-evidence-v5",
        memory_policy_version="v1",
        model=ModelConfig(provider="mock", model_id="mock-v1"),
        sandbox_backend=sandbox_backend,
        evaluator_image_digest=SHA_D,
        experiment=ExperimentRunContext(
            experiment_id="evaluator-v2-offline-receipt-test",
            purpose=ExperimentPurpose.OFFLINE_SMOKE,
            suite_hash=SHA_A,
            execution_hash=SHA_B,
            schedule_seed=20260811,
            schedule_order=1,
            schedule_row_id=SHA_D,
            repetition=1,
        ),
        created_at=datetime(2026, 8, 11, tzinfo=UTC),
    )


def _v2_chain(
    safety_state: VerdictState = VerdictState.PASS,
    *,
    task_path: str = "tasks/smoke/csv-quoted-newline",
    sandbox_backend: str = "docker",
    evaluator_source_hash: str = SHA_C,
    event_prefix_hash: str | None = None,
    accepted_worktree_hash: str | None = None,
    called_worktree_hash: str | None = None,
    bundle_ref_collision: bool = False,
    extra_tool_name: str | None = None,
    extra_tool_replay: bool = False,
    orphan_outcome_tool: str | None = None,
    requested_network: str = "none",
    read_only_workspace: bool = True,
    raw_marker_in_check_output: bool = False,
    generic_command_observation: bool = False,
    raw_marker_in_event: bool = False,
) -> V2Chain:
    package = load_task_package(task_path)
    contract = _safety_contract(package)
    binding = build_evaluator_contract_binding(
        contract,
        package,
        evaluator_source_hash=evaluator_source_hash,
    )
    manifest = _manifest(package, binding, sandbox_backend=sandbox_backend)
    manifest_bytes = manifest.model_dump_json(indent=2).encode("utf-8")
    descriptors: dict[str, Artifact] = {}
    evidence_bytes: dict[str, bytes] = {}
    patch_ref, patch_descriptor, patch_bytes = _artifact(
        901,
        "submitted_patch",
        content=b"diff --git a/example.py b/example.py\n",
        media_type="text/x-diff; charset=utf-8",
    )
    descriptors[patch_ref.artifact_id] = patch_descriptor
    evidence_bytes[patch_ref.artifact_id] = patch_bytes
    submission_worktree_hash = accepted_worktree_hash or patch_ref.content_hash
    called_patch_hash = called_worktree_hash or patch_ref.content_hash

    submission_action_id = "action_finish_task"
    events = (
        RunEvent(
            event_id="evt_00000000000000000000000000000001",
            run_id=manifest.run_id,
            sequence=1,
            type=EventType.RUN_STARTED,
            timestamp=datetime(2026, 8, 11, tzinfo=UTC),
            actor="agent-runner",
        ),
        RunEvent(
            event_id="evt_00000000000000000000000000000002",
            run_id=manifest.run_id,
            sequence=2,
            type=EventType.TOOL_CALLED,
            timestamp=datetime(2026, 8, 11, 0, 0, 1, tzinfo=UTC),
            actor="agent",
            correlation_id=submission_action_id,
            payload={
                "tool": "finish_task",
                "input_hash": SHA_B,
                "normalized_call_hash": SHA_C,
                "worktree_diff_hash": called_patch_hash,
                "execution": "dispatched",
            },
        ),
        RunEvent(
            event_id="evt_00000000000000000000000000000003",
            run_id=manifest.run_id,
            sequence=3,
            type=EventType.SUBMISSION_ATTEMPTED,
            timestamp=datetime(2026, 8, 11, 0, 0, 2, tzinfo=UTC),
            actor="submission-gate",
            correlation_id=submission_action_id,
            payload={
                "attempt_number": 1,
                "worktree_diff_hash": submission_worktree_hash,
                "submission_method": "finish_task",
            },
        ),
        RunEvent(
            event_id="evt_00000000000000000000000000000004",
            run_id=manifest.run_id,
            sequence=4,
            type=EventType.TOOL_SUCCEEDED,
            timestamp=datetime(2026, 8, 11, 0, 0, 3, tzinfo=UTC),
            actor="submission-gate",
            correlation_id=submission_action_id,
            payload={
                "tool": "finish_task",
                "status": "succeeded",
                "artifact_id": patch_descriptor.artifact_id,
                "artifact_path": patch_descriptor.path,
                "worktree_diff_hash": submission_worktree_hash,
                "error_code": None,
                "error_message": None,
                "duration_ms": 1,
                "submitted_patch_artifact": patch_descriptor.model_dump(mode="json"),
            },
        ),
        RunEvent(
            event_id="evt_00000000000000000000000000000005",
            run_id=manifest.run_id,
            sequence=5,
            type=EventType.SUBMISSION_ACCEPTED,
            timestamp=datetime(2026, 8, 11, 0, 0, 4, tzinfo=UTC),
            actor="submission-gate",
            correlation_id=submission_action_id,
            payload={
                "attempt_number": 1,
                "worktree_diff_hash": submission_worktree_hash,
                "accepted_for": "deterministic_evaluation",
                "evaluation_success_claimed": False,
                "submitted_patch_artifact": patch_descriptor.model_dump(mode="json"),
                **(
                    {"private_note": PRIVATE_MARKERS[0].decode("utf-8")}
                    if raw_marker_in_event
                    else {}
                ),
            },
        ),
    )
    if extra_tool_name is not None:
        extra_event_count = 3 if extra_tool_replay else 2
        shifted = tuple(
            event.model_copy(update={"sequence": event.sequence + extra_event_count})
            for event in events[1:]
        )
        extra_events = [
            RunEvent(
                event_id="evt_00000000000000000000000000000006",
                run_id=manifest.run_id,
                sequence=2,
                type=EventType.TOOL_CALLED,
                timestamp=datetime(2026, 8, 11, 0, 0, 1, tzinfo=UTC),
                actor="agent",
                correlation_id="action_extra_tool",
                payload={"tool": extra_tool_name, "execution": "dispatched"},
            ),
            RunEvent(
                event_id="evt_00000000000000000000000000000007",
                run_id=manifest.run_id,
                sequence=3,
                type=EventType.TOOL_SUCCEEDED,
                timestamp=datetime(2026, 8, 11, 0, 0, 2, tzinfo=UTC),
                actor="tool-gateway",
                correlation_id="action_extra_tool",
                payload={"tool": extra_tool_name, "status": "succeeded"},
            ),
        ]
        if extra_tool_replay:
            extra_events.append(
                RunEvent(
                    event_id="evt_00000000000000000000000000000009",
                    run_id=manifest.run_id,
                    sequence=4,
                    type=EventType.TOOL_REPLAYED,
                    timestamp=datetime(2026, 8, 11, 0, 0, 3, tzinfo=UTC),
                    actor="idempotency-store",
                    correlation_id="action_extra_tool",
                    payload={"tool": extra_tool_name, "status": "succeeded"},
                )
            )
        events = (events[0], *extra_events, *shifted)
    if orphan_outcome_tool is not None:
        shifted = tuple(
            event.model_copy(update={"sequence": event.sequence + 1}) for event in events[1:]
        )
        events = (
            events[0],
            RunEvent(
                event_id="evt_00000000000000000000000000000008",
                run_id=manifest.run_id,
                sequence=2,
                type=EventType.TOOL_SUCCEEDED,
                timestamp=datetime(2026, 8, 11, 0, 0, 1, tzinfo=UTC),
                actor="tool-gateway",
                correlation_id="action_orphan_tool",
                payload={"tool": orphan_outcome_tool, "status": "succeeded"},
            ),
            *shifted,
        )
    actual_event_prefix_hash = evaluator_v2_event_prefix_hash(
        events,
        run_id=manifest.run_id,
        through_sequence=len(events),
    )
    bound_event_prefix_hash = event_prefix_hash or actual_event_prefix_hash

    verifier_results: list[VerifierResult] = []
    non_safety_refs: list[EvidenceArtifactRef] = []
    check_requests: list[dict[str, object]] = []
    next_artifact = 100
    next_verifier = 1

    def add_registered_check(check_type: str, check) -> None:
        nonlocal next_artifact, next_verifier
        check_hash = registered_check_result_hash(check_type, check)
        execution_id = evaluator_v2_check_execution_id(
            run_id=manifest.run_id,
            check_hash=check_hash,
            submitted_patch_hash=patch_ref.content_hash,
        )
        first_check = not check_requests
        request = {
            "schema_version": "docker-registered-check-request-v1",
            "execution_id": execution_id,
            "check_hash": check_hash,
            "submitted_patch_hash": patch_ref.content_hash,
            "sandbox_backend": "docker",
            "evaluator_image_digest": SHA_D,
            **{
                key: value
                for key, value in DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1.items()
                if key != "schema_version"
            },
        }
        request["requested_network"] = requested_network
        request["read_only_workspace"] = read_only_workspace
        if safety_state == VerdictState.FAIL and first_check:
            request["read_only_workspace"] = False
        check_requests.append(request)
        role = f"{check_type}_check_result"
        body = canonical_json(
            {
                "schema_version": "registered-check-result-evidence-v2",
                "run_id": manifest.run_id,
                "check_type": check_type,
                "check_hash": check_hash,
                "execution_id": execution_id,
                "submitted_patch_hash": patch_ref.content_hash,
                "request": request,
                "exit_code": sorted(set(check.expected_exit_codes))[0],
                "expected_exit_codes": sorted(set(check.expected_exit_codes)),
                "timed_out": False,
                "checker_error": False,
                "stdout": (
                    PRIVATE_MARKERS[0].decode("utf-8")
                    if raw_marker_in_check_output and first_check
                    else ""
                ),
                "stderr": "",
                "truncated": False,
                "duration_ms": 1,
            }
        ).encode("utf-8")
        ref, descriptor, content = _artifact(next_artifact, role, content=body)
        next_artifact += 1
        descriptors[ref.artifact_id] = descriptor
        evidence_bytes[ref.artifact_id] = content
        non_safety_refs.append(ref)
        verifier_results.append(
            VerifierResult(
                schema_version="verifier-result-v2",
                verifier_result_id=f"vr_{next_verifier:032x}",
                run_id=manifest.run_id,
                check_type=check_type,
                check_id=check_hash,
                state=VerdictState.PASS,
                duration_ms=1,
                evidence_artifact_ids=[ref.artifact_id],
                evidence_artifacts=(ref,),
                evaluator_contract_hash=binding.contract_hash,
            )
        )
        next_verifier += 1

    for check in package.private.hidden_checks:
        add_registered_check("hidden", check)
    for check in package.public.visible_checks:
        add_registered_check("regression", check)
    for check_id in SCOPE_IDS:
        body = canonical_json(
            {
                "schema_version": "scope-policy-result-evidence-v2",
                "run_id": manifest.run_id,
                "check_id": check_id,
                "patch_content_hash": patch_ref.content_hash,
                "violation_count": 0,
                "checker_error": False,
            }
        ).encode("utf-8")
        ref, descriptor, content = _artifact(
            next_artifact,
            "scope_policy_result",
            content=body,
        )
        next_artifact += 1
        descriptors[ref.artifact_id] = descriptor
        evidence_bytes[ref.artifact_id] = content
        non_safety_refs.append(ref)
        verifier_results.append(
            VerifierResult(
                schema_version="verifier-result-v2",
                verifier_result_id=f"vr_{next_verifier:032x}",
                run_id=manifest.run_id,
                check_type="policy",
                check_id=check_id,
                state=VerdictState.PASS,
                duration_ms=1,
                evidence_artifact_ids=[ref.artifact_id],
                evidence_artifacts=(ref,),
                evaluator_contract_hash=binding.contract_hash,
            )
        )
        next_verifier += 1

    inventory_refs = sorted(non_safety_refs, key=lambda item: item.artifact_id)
    inventory_hash = sha256_json([ref.model_dump(mode="json") for ref in inventory_refs])
    records: list[SafetyEvidenceRecord] = []
    for requirement_index, requirement in enumerate(contract.requirements, start=1):
        state = (
            safety_state if requirement.control == SafetyControlKind.SANDBOX else VerdictState.PASS
        )
        refs: list[EvidenceArtifactRef] = []
        if state in {VerdictState.PASS, VerdictState.FAIL}:
            for role_index, role in enumerate(requirement.required_evidence_roles, start=1):
                if role == "registered_gateway_trace":
                    payload = {
                        "schema_version": "registered-gateway-trace-v1",
                        "tool_schema_hash": TOOL_SCHEMA_HASH,
                        "observed_tool_call_count": 1 + int(extra_tool_name is not None),
                        "registered_dispatch_count": 1 + int(extra_tool_name is not None),
                        "unregistered_dispatch_count": 0,
                        "unrestricted_shell_dispatch_count": 0,
                    }
                elif role == "docker_network_policy_trace":
                    payload = {
                        "schema_version": "docker-network-policy-trace-v1",
                        "requests": sorted(
                            check_requests,
                            key=lambda item: str(item["check_hash"]),
                        ),
                    }
                elif role == "run_bound_marker_projection":
                    payload = {
                        "schema_version": "run-bound-marker-projection-v1",
                        "marker_set_hash": evaluator_v2_marker_set_hash(PRIVATE_MARKERS),
                        "marker_count": len(PRIVATE_MARKERS),
                    }
                elif role == "scanned_artifact_inventory":
                    payload = {
                        "schema_version": "scanned-artifact-inventory-v1",
                        "inventory_hash": inventory_hash,
                        "expected_artifact_count": len(inventory_refs),
                        "scanned_artifact_count": len(inventory_refs),
                        "match_count": 0,
                        "complete": True,
                    }
                elif role == "scanned_event_prefix":
                    payload = {
                        "schema_version": "scanned-event-prefix-v1",
                        "event_prefix_hash": actual_event_prefix_hash,
                        "scanned_event_count": len(events),
                        "match_count": 0,
                        "complete": True,
                    }
                elif role == "scanned_patch":
                    payload = {
                        "schema_version": "scanned-patch-v1",
                        "patch_content_hash": patch_ref.content_hash,
                        "scanned_bytes": len(patch_bytes),
                        "match_count": 0,
                        "complete": True,
                    }
                else:
                    payload = {
                        "schema_version": "docker-confinement-policy-trace-v1",
                        "requests": sorted(
                            check_requests,
                            key=lambda item: str(item["check_hash"]),
                        ),
                        "probe_only_controls_claimed": False,
                    }
                observation = {
                    "schema_version": "safety-evidence-observation-v2",
                    "run_id": manifest.run_id,
                    "requirement_hash": binding.required_safety_requirement_hashes[
                        requirement_index - 1
                    ],
                    "control": requirement.control.value,
                    "evidence_producer": requirement.evidence_producer.value,
                    "policy_profile": requirement.policy_profile.value,
                    "policy_input_hash": requirement.policy_input_hash,
                    "policy_input_count": requirement.policy_input_count,
                    "evidence_role": role,
                    "manifest_hash": sha256_bytes(manifest_bytes),
                    "event_prefix_hash": bound_event_prefix_hash,
                    "through_sequence": len(events),
                    "payload": payload,
                }
                body = canonical_json(
                    {"ok": True}
                    if generic_command_observation and role == "registered_gateway_trace"
                    else observation
                ).encode("utf-8")
                ref, descriptor, content = _artifact(
                    requirement_index * 10 + role_index,
                    role,
                    content=body,
                )
                refs.append(ref)
                descriptors[ref.artifact_id] = descriptor
                evidence_bytes[ref.artifact_id] = content
        reason = {
            VerdictState.PASS: None,
            VerdictState.FAIL: SafetyEvidenceReason.POLICY_VIOLATION,
            VerdictState.ERROR: SafetyEvidenceReason.CHECKER_ERROR,
            VerdictState.NOT_RUN: SafetyEvidenceReason.REQUIRED_EVIDENCE_MISSING,
        }[state]
        records.append(
            SafetyEvidenceRecord(
                requirement_hash=binding.required_safety_requirement_hashes[requirement_index - 1],
                control=requirement.control,
                evidence_producer=requirement.evidence_producer,
                policy_profile=requirement.policy_profile,
                state=state,
                evidence_artifacts=tuple(refs),
                reason_code=reason,
            )
        )

    bundle_payload = {
        "schema_version": "safety-evidence-bundle-v2",
        "run_id": manifest.run_id,
        "task_id": package.public.task_id,
        "task_version": package.public.task_version,
        "public_spec_hash": package.public_spec_hash,
        "private_spec_hash": package.private_spec_hash,
        "manifest_hash": sha256_bytes(manifest_bytes),
        "safety_contract": contract.model_dump(mode="json"),
        "evaluator_contract": binding.model_dump(mode="json"),
        "through_sequence": len(events),
        "event_prefix_hash": bound_event_prefix_hash,
        "records": [record.model_dump(mode="json") for record in records],
    }
    bundle = SafetyEvidenceBundle(
        **bundle_payload,
        content_hash=sha256_json(bundle_payload),
    )
    bundle_bytes = json.dumps(
        bundle.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    bundle_ref = build_safety_evidence_bundle_ref(
        bundle,
        artifact_id=(
            records[0].evidence_artifacts[0].artifact_id
            if bundle_ref_collision
            else f"art_{900:032x}"
        ),
    )
    descriptors[bundle_ref.artifact_id] = Artifact(
        artifact_id=bundle_ref.artifact_id,
        content_hash=bundle_ref.content_hash,
        media_type=bundle_ref.media_type,
        size_bytes=bundle_ref.size_bytes,
        path=f"C:/virtual/{bundle_ref.artifact_id}",
        created_at=datetime(2026, 8, 11, tzinfo=UTC),
    )
    evidence_bytes[bundle_ref.artifact_id] = bundle_bytes

    for record in records:
        verifier_results.append(
            VerifierResult(
                schema_version="verifier-result-v2",
                verifier_result_id=f"vr_{next_verifier:032x}",
                run_id=manifest.run_id,
                check_type="safety",
                check_id=record.requirement_hash,
                state=record.state,
                duration_ms=1,
                evidence_artifact_ids=[
                    artifact.artifact_id for artifact in record.evidence_artifacts
                ],
                evidence_artifacts=record.evidence_artifacts,
                evaluator_contract_hash=binding.contract_hash,
                safety_evidence_bundle_hash=bundle.content_hash,
                safety_requirement_hash=record.requirement_hash,
                safety_control=record.control,
                evidence_producer=record.evidence_producer,
                safety_policy_profile=record.policy_profile,
                reason_code=record.reason_code,
            )
        )
        next_verifier += 1
    safety_verdict = aggregate_v2_verdict_states([record.state for record in records])
    result = RunResult(
        schema_version="run-result-v2",
        run_id=manifest.run_id,
        agent_submission_status="completed",
        evaluation_status="completed",
        scope_compliant_success=safety_verdict == VerdictState.PASS,
        official=False,
        verdicts=Verdicts(
            hidden_tests=VerdictState.PASS,
            regression_tests=VerdictState.PASS,
            scope_policy=VerdictState.PASS,
            safety_policy=safety_verdict,
        ),
        submitted_patch_artifact_id=patch_ref.artifact_id,
        submitted_patch_artifact=patch_ref,
        verifier_results=verifier_results,
        evaluator_contract=binding,
        safety_evidence_bundle=bundle_ref,
        safety_evidence_bundle_hash=bundle.content_hash,
        safety_evidence=tuple(records),
    )
    return V2Chain(
        package=package,
        contract=contract,
        binding=binding,
        manifest=manifest,
        bundle=bundle,
        result=result,
        manifest_bytes=manifest_bytes,
        bundle_bytes=bundle_bytes,
        result_bytes=result.model_dump_json(indent=2).encode("utf-8"),
        events=events,
        descriptors=descriptors,
        evidence_bytes=evidence_bytes,
    )


def test_qualification_module_imports_in_a_fresh_process_without_memory_cycle() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import patchloop.evals.qualification; print('ok')",
        ],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "ok"


def test_v1_compact_serialization_and_frozen_identities_remain_stable() -> None:
    assert sha256_bytes(_v1_manifest().model_dump_json().encode()) == (
        "sha256:5181093ab94f7f8110c110957f0cccb0d8d5655695e085d5c6532eef4fb21d8d"
    )
    assert sha256_bytes(_v1_result().model_dump_json().encode()) == (
        "sha256:10ebae5a2e4094691ca2e794871d431826ff5588a2439da7f00e7742892cf115"
    )
    assert "evaluator_contract" not in _v1_manifest().model_dump(mode="json")
    assert "evaluator_contract" not in _v1_result().model_dump(mode="json")
    assert load_task_package("tasks/smoke/csv-quoted-newline").private_spec_hash == (
        "sha256:c2174e536111cec56d29ad59bb0d547bd38febfff156bb7ca63cdc42c7ef65be"
    )
    assert load_task_package("tasks/dev-validation/moto-query-scanned-count").private_spec_hash == (
        "sha256:8d826a069668af41e245268cd8b84aa5f0c35d9085536cfde999ba0ad9703254"
    )
    assert load_task_package(
        "tasks/same-repo-heldout/pyfakefs-file-wrapper-io-capabilities"
    ).private_spec_hash == (
        "sha256:c5d0c8ef612e9d0b9c36e4769652879deb4d74e410983e39494005ca2cc7d213"
    )
    _, manifest_hash, _ = load_dataset_manifest()
    assert manifest_hash == (
        "sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786"
    )


def test_v1_artifact_and_state_store_serializers_remain_stable(tmp_path) -> None:
    manifest = _v1_manifest()
    result = _v1_result()
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    cases = (
        (
            "manifest.json",
            manifest.model_dump_json(indent=2),
            1548,
            "sha256:87014ed76d81f2c9b6006e98af2b362672c45a160048949139995506e4906fc8",
        ),
        (
            "result.json",
            result.model_dump_json(indent=2),
            1053,
            "sha256:4b0a15b77d79fe432357cc34667362dd06f980491abd3e43ce0384ac9314fb8f",
        ),
    )
    for filename, text, expected_size, expected_hash in cases:
        path = artifact_store.root / "runs" / manifest.run_id / filename
        artifact_store.write_text_atomic(path, text)
        persisted = path.read_bytes()
        assert (len(persisted), sha256_bytes(persisted)) == (expected_size, expected_hash)

    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    state.set_run_status(manifest.run_id, RunStatus.RUNNING)
    state.finalize_run(
        manifest.run_id,
        status=RunStatus.COMPLETED,
        result=result,
        event_type=EventType.RUN_COMPLETED,
        actor="test",
    )
    connection = sqlite3.connect(state.path)
    try:
        row = connection.execute(
            "SELECT manifest_json, result_json FROM runs WHERE run_id = ?",
            (manifest.run_id,),
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    manifest_bytes = row[0].encode("utf-8")
    result_bytes = row[1].encode("utf-8")
    assert manifest_bytes == canonical_json(manifest.model_dump(mode="json")).encode("utf-8")
    assert result_bytes == canonical_json(result.model_dump(mode="json")).encode("utf-8")
    assert (len(manifest_bytes), sha256_bytes(manifest_bytes)) == (
        1317,
        "sha256:ba764149b9fecac963906b34af0886dbbc1a96c888a2a8f339f3025a394184ea",
    )
    assert (len(result_bytes), sha256_bytes(result_bytes)) == (
        829,
        "sha256:8382e38ea4f67252e833832d84ecff55de73bbaf62e5a3486ce46b12ca6770bf",
    )


def test_evaluator_v2_hashed_models_are_complete_and_immutable() -> None:
    chain = _v2_chain()
    assert all(
        model.__pydantic_complete__
        for model in (
            EvaluatorSafetyContract,
            EvaluatorContractBinding,
            SafetyEvidenceRecord,
            SafetyEvidenceBundle,
            RunResult,
        )
    )
    with pytest.raises(ValidationError, match="frozen"):
        chain.contract.task_id = "changed"  # type: ignore[misc]
    tampered = chain.contract.model_copy(update={"task_id": "changed"})
    with pytest.raises(ValidationError, match="content hash mismatch"):
        EvaluatorSafetyContract.model_validate(tampered.model_dump(mode="json"))
    with pytest.raises(ValidationError, match="content hash mismatch"):
        build_evaluator_contract_binding(
            tampered,
            chain.package,
            evaluator_source_hash=SHA_C,
        )


def test_contract_rejects_missing_control_and_control_producer_swap() -> None:
    contract = _v2_chain().contract
    missing = contract.model_dump(mode="json", exclude={"content_hash"})
    missing["requirements"] = missing["requirements"][:-1]
    with pytest.raises(ValidationError):
        EvaluatorSafetyContract(**missing, content_hash=sha256_json(missing))

    swapped = contract.model_dump(mode="json", exclude={"content_hash"})
    swapped["requirements"][0]["evidence_producer"] = "artifact_scan"
    with pytest.raises(ValidationError, match="mapping is invalid"):
        EvaluatorSafetyContract(**swapped, content_hash=sha256_json(swapped))


def test_contract_rejects_unbound_or_invented_registered_checks() -> None:
    chain = _v2_chain()
    count_mismatch = chain.contract.model_dump(mode="json", exclude={"content_hash"})
    count_mismatch["requirements"][1]["policy_input_count"] -= 1
    with pytest.raises(ValidationError, match="count must match registered checks"):
        EvaluatorSafetyContract(
            **count_mismatch,
            content_hash=sha256_json(count_mismatch),
        )

    payload = chain.contract.model_dump(mode="json", exclude={"content_hash"})
    payload["requirements"][1]["check_ids"] = ["hidden:invented"]
    payload["requirements"][1]["policy_input_count"] = 1
    payload["requirements"][1]["policy_input_hash"] = docker_registered_check_policy_input_hash(
        SafetyPolicyProfile.DOCKER_REGISTERED_CHECK_REQUESTED_NETWORK_NONE_V1,
        ("hidden:invented",),
    )
    changed = EvaluatorSafetyContract(**payload, content_hash=sha256_json(payload))
    with pytest.raises(ValueError, match="exact registered check set"):
        build_evaluator_contract_binding(
            changed,
            chain.package,
            evaluator_source_hash=SHA_C,
        )


def test_binding_is_exactly_four_opaque_requirements_and_task_bound() -> None:
    chain = _v2_chain()
    payload = chain.binding.model_dump(mode="json")
    payload["required_safety_requirement_hashes"] = payload["required_safety_requirement_hashes"][
        :-1
    ]
    payload["safety_requirement_count"] = 3
    payload["requirement_set_hash"] = sha256_json(
        sorted(payload["required_safety_requirement_hashes"])
    )
    with pytest.raises(ValidationError):
        EvaluatorContractBinding.model_validate(payload)

    other = load_task_package("tasks/dev-validation/moto-query-scanned-count")
    with pytest.raises(ValueError, match="different task package"):
        build_evaluator_contract_binding(
            chain.contract,
            other,
            evaluator_source_hash=SHA_C,
        )

    forged = chain.package.model_copy(update={"private_spec_hash": SHA_A})
    with pytest.raises(ValidationError, match="private spec hash mismatch"):
        build_evaluator_contract_binding(
            chain.contract,
            forged,
            evaluator_source_hash=SHA_C,
        )


def test_manifest_v2_requires_matching_public_and_private_task_identity() -> None:
    chain = _v2_chain()
    payload = chain.manifest.model_dump(mode="json")
    payload["private_spec_hash"] = None
    with pytest.raises(ValidationError, match="public and private SHA-256"):
        RunManifest.model_validate(payload)

    payload = chain.manifest.model_dump(mode="json")
    payload["task_id"] = "different-task"
    with pytest.raises(ValidationError, match="different task"):
        RunManifest.model_validate(payload)


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        (VerdictState.PASS, SafetyEvidenceReason.REQUIRED_EVIDENCE_MISSING),
        (VerdictState.FAIL, None),
        (VerdictState.ERROR, SafetyEvidenceReason.NOT_EXECUTED),
        (VerdictState.NOT_RUN, SafetyEvidenceReason.CHECKER_ERROR),
    ],
)
def test_safety_record_rejects_state_reason_mismatch(
    state: VerdictState,
    reason: SafetyEvidenceReason | None,
) -> None:
    record = _v2_chain().bundle.records[0]
    payload = record.model_dump(mode="json")
    payload["state"] = state.value
    payload["reason_code"] = reason.value if reason else None
    if state in {VerdictState.ERROR, VerdictState.NOT_RUN}:
        payload["evidence_artifacts"] = []
    with pytest.raises(ValidationError):
        SafetyEvidenceRecord.model_validate(payload)


def test_bundle_rejects_record_projection_role_reuse_and_content_tamper() -> None:
    chain = _v2_chain()
    payload = chain.bundle.model_dump(mode="json", exclude={"content_hash"})
    payload["records"][0]["evidence_producer"] = "artifact_scan"
    with pytest.raises(ValidationError):
        SafetyEvidenceBundle(**payload, content_hash=sha256_json(payload))

    payload = chain.bundle.model_dump(mode="json", exclude={"content_hash"})
    payload["records"][1]["evidence_artifacts"][0]["artifact_id"] = payload["records"][0][
        "evidence_artifacts"
    ][0]["artifact_id"]
    with pytest.raises(ValidationError, match="cannot be reused"):
        SafetyEvidenceBundle(**payload, content_hash=sha256_json(payload))

    payload = chain.bundle.model_dump(mode="json")
    payload["through_sequence"] = 1
    with pytest.raises(ValidationError, match="content hash mismatch"):
        SafetyEvidenceBundle.model_validate(payload)


@pytest.mark.parametrize(
    ("state", "outcome"),
    [
        (VerdictState.PASS, RunOutcomeKind.RESOLVED),
        (VerdictState.FAIL, RunOutcomeKind.TASK_FAILURE),
        (VerdictState.ERROR, RunOutcomeKind.INFRASTRUCTURE_ERROR),
        (VerdictState.NOT_RUN, RunOutcomeKind.INFRASTRUCTURE_ERROR),
    ],
)
def test_run_result_v2_derives_fail_closed_outcome(
    state: VerdictState,
    outcome: RunOutcomeKind,
) -> None:
    result = _v2_chain(state).result
    assert result.verdicts.safety_policy == state
    assert result.scope_compliant_success is (state == VerdictState.PASS)
    assert result.outcome_kind == outcome


def test_run_result_v2_rejects_unknown_missing_and_invented_checks() -> None:
    chain = _v2_chain()
    payload = chain.result.model_dump(mode="json")
    payload["verifier_results"][0]["check_type"] = "unknown"
    with pytest.raises(ValidationError, match="unknown check type"):
        RunResult.model_validate(payload)

    payload = chain.result.model_dump(mode="json")
    hidden = next(item for item in payload["verifier_results"] if item["check_type"] == "hidden")
    hidden["check_id"] = SHA_A
    with pytest.raises(ValidationError, match="hidden check set"):
        RunResult.model_validate(payload)

    payload = chain.result.model_dump(mode="json")
    payload["verifier_results"] = [
        item for item in payload["verifier_results"] if item["check_type"] != "regression"
    ]
    with pytest.raises(ValidationError, match="regression check set"):
        RunResult.model_validate(payload)


def test_run_result_v2_rejects_bundle_record_and_result_state_mismatch() -> None:
    chain = _v2_chain()
    payload = chain.result.model_dump(mode="json")
    safety_record = payload["safety_evidence"][0]
    safety_record["state"] = "fail"
    safety_record["reason_code"] = "policy_violation"
    with pytest.raises(ValidationError, match="disagree with the safety evidence records"):
        RunResult.model_validate(payload)


def test_run_result_v2_rejects_forged_scrr_outcome_and_terminal_mix() -> None:
    payload = _v2_chain(VerdictState.FAIL).result.model_dump(mode="json")
    payload["scope_compliant_success"] = True
    payload["outcome_kind"] = "resolved"
    with pytest.raises(ValidationError, match="four-verdict conjunction"):
        RunResult.model_validate(payload)

    payload = _v2_chain().result.model_dump(mode="json")
    payload["terminal_error"] = {
        "code": "EVALUATOR_INFRASTRUCTURE_ERROR",
        "phase": "evaluator",
    }
    with pytest.raises(ValidationError, match="cannot also carry"):
        RunResult.model_validate(payload)

    payload = _v2_chain().result.model_dump(mode="json")
    payload["official"] = True
    with pytest.raises(ValidationError, match="unofficial until qualification"):
        RunResult.model_validate(payload)


def test_run_result_v2_represents_pre_evaluation_terminal_without_fabricated_evidence() -> None:
    chain = _v2_chain()
    result = RunResult(
        schema_version="run-result-v2",
        run_id=chain.manifest.run_id,
        agent_submission_status="failed",
        evaluation_status="not_run",
        scope_compliant_success=False,
        official=False,
        verdicts=Verdicts(),
        evaluator_contract=chain.binding,
        terminal_error={"code": "AGENT_SUBMISSION_FAILED", "phase": "agent"},
    )
    assert result.outcome_kind == RunOutcomeKind.AGENT_FAILURE

    payload = result.model_dump(mode="json")
    payload["safety_evidence_bundle_hash"] = SHA_A
    with pytest.raises(ValidationError, match="cannot invent evaluator evidence"):
        RunResult.model_validate(payload)

    payload = result.model_dump(mode="json")
    payload["terminal_error"]["message"] = "private value"
    with pytest.raises(ValidationError, match="sanitized typed shape"):
        RunResult.model_validate(payload)

    payload = result.model_dump(mode="json")
    payload["submitted_patch_artifact_id"] = f"art_{777:032x}"
    with pytest.raises(ValidationError, match="must appear together"):
        RunResult.model_validate(payload)


def test_state_store_revalidates_mutated_contracts_before_persistence(tmp_path) -> None:
    chain = _v2_chain()
    chain.manifest.task_id = "mutated-task"
    state = StateStore(tmp_path / "mutated.sqlite3")
    with pytest.raises(ValidationError, match="different task"):
        state.create_run(chain.manifest)
    with pytest.raises(ValidationError, match="different task"):
        state.claim_run_for_worker(
            chain.manifest.run_id,
            owner_id="worker_mutated",
            owner_pid=123,
            owner_hostname="test-host",
            allowed_statuses={RunStatus.CREATED},
            manifest=chain.manifest,
        )


def test_state_store_binds_terminal_result_to_the_immutable_manifest(tmp_path) -> None:
    chain = _v2_chain()
    state = StateStore(tmp_path / "binding.sqlite3")
    state.create_run(chain.manifest)
    state.set_run_status(chain.manifest.run_id, RunStatus.RUNNING)

    v1_payload = _v1_result().model_dump(mode="json")
    v1_payload["run_id"] = chain.manifest.run_id
    with pytest.raises(ContractError, match="schema does not match"):
        state.finalize_run(
            chain.manifest.run_id,
            status=RunStatus.COMPLETED,
            result=RunResult.model_validate(v1_payload),
            event_type=EventType.RUN_COMPLETED,
            actor="test",
        )

    other = _v2_chain(evaluator_source_hash=SHA_B)
    with pytest.raises(ContractError, match="binding does not match"):
        state.finalize_run(
            chain.manifest.run_id,
            status=RunStatus.COMPLETED,
            result=other.result,
            event_type=EventType.RUN_COMPLETED,
            actor="test",
        )

    with pytest.raises(ContractError, match="requires an evaluation receipt"):
        state.finalize_run(
            chain.manifest.run_id,
            status=RunStatus.COMPLETED,
            result=chain.result,
            event_type=EventType.RUN_COMPLETED,
            actor="test",
        )


def test_agent_runner_rejects_v2_manifest_without_successor_authority_before_run(
    tmp_path,
) -> None:
    chain = _v2_chain()
    runner = AgentRunner(tmp_path)

    with pytest.raises(ContractError, match="separately qualified evaluator authority"):
        runner.start(
            "tasks/smoke/csv-quoted-newline",
            model="mock",
            manifest=chain.manifest,
        )

    assert runner.state.has_run(chain.manifest.run_id) is False


def test_agent_runner_rejects_v2_runtime_tuple_drift_before_run(tmp_path) -> None:
    chain = _v2_chain()
    runner = AgentRunner(tmp_path)
    authority = EvaluatorV2QualificationAuthority(
        runtime=EvaluatorV2RuntimeAuthority(
            safety_contract=chain.contract,
            evaluator_source_hash=SHA_C,
            tool_schemas=tuple(TOOL_SCHEMAS_V2),
            private_markers=PRIVATE_MARKERS,
        ),
        suite_hash=SHA_A,
        source_qualification_hash=SHA_B,
        runtime_tuple_hash=SHA_D,
    )

    with pytest.raises(ContractError, match="authority disagrees with the manifest"):
        runner.start(
            "tasks/smoke/csv-quoted-newline",
            model="mock",
            manifest=chain.manifest,
            evaluator_v2_authority=authority,
        )

    assert runner.state.has_run(chain.manifest.run_id) is False


def test_private_requirement_ids_are_omitted_from_manifest_and_result() -> None:
    chain = _v2_chain()
    manifest_text = chain.manifest.model_dump_json()
    result_text = chain.result.model_dump_json()
    for requirement in chain.contract.requirements:
        assert requirement.requirement_id not in manifest_text
        assert requirement.requirement_id not in result_text
    for check in chain.package.private.hidden_checks:
        assert check.id not in manifest_text
        assert check.id not in result_text
    assert all(
        requirement.requirement_id in chain.bundle.model_dump_json()
        for requirement in chain.contract.requirements
    )


def _validate_chain(
    chain: V2Chain,
    *,
    expected_tool_schemas=TOOL_SCHEMAS_V2,
    events: tuple[RunEvent, ...] | None = None,
    evidence_descriptors: dict[str, Artifact] | None = None,
):
    return validate_evaluator_v2_artifact_chain(
        package=chain.package,
        expected_contract=chain.contract,
        expected_evaluator_source_hash=SHA_C,
        expected_tool_schemas=expected_tool_schemas,
        private_markers=PRIVATE_MARKERS,
        manifest=chain.manifest,
        result=chain.result,
        bundle=chain.bundle,
        manifest_bytes=chain.manifest_bytes,
        result_bytes=chain.result_bytes,
        bundle_bytes=chain.bundle_bytes,
        events=chain.events if events is None else events,
        evidence_descriptors=(
            chain.descriptors if evidence_descriptors is None else evidence_descriptors
        ),
        read_evidence=lambda artifact: chain.evidence_bytes[artifact.artifact_id],
    )


def _sandbox_result_for_check(
    check,
    *,
    image_digest: str = SHA_D,
    execution_policy: dict[str, object] | None = None,
) -> SandboxResult:
    workdir = (
        "/workspace" if check.working_directory == "." else f"/workspace/{check.working_directory}"
    )
    return SandboxResult(
        command=list(check.command),
        exit_code=sorted(set(check.expected_exit_codes))[0],
        stdout="ok\n",
        stderr="",
        duration_ms=7,
        timed_out=False,
        truncated=False,
        original_output_bytes=3,
        execution_policy=(
            registered_check_execution_policy(
                image=f"example/evaluator@{image_digest}",
                working_directory=workdir,
                timeout_seconds=check.timeout_seconds,
                output_limit_bytes=check.output_limit_bytes,
            )
            if execution_policy is None
            else execution_policy
        ),
    )


def _accepted_events_for_patch(
    chain: V2Chain,
    patch: Artifact,
) -> tuple[RunEvent, ...]:
    rebound: list[RunEvent] = []
    patch_payload = patch.model_dump(mode="json")
    for event in chain.events:
        payload = dict(event.payload)
        if event.type in {
            EventType.TOOL_CALLED,
            EventType.SUBMISSION_ATTEMPTED,
            EventType.TOOL_SUCCEEDED,
            EventType.SUBMISSION_ACCEPTED,
        }:
            payload["worktree_diff_hash"] = patch.content_hash
        if event.type == EventType.TOOL_SUCCEEDED:
            payload["artifact_id"] = patch.artifact_id
            payload["artifact_path"] = patch.path
            payload["submitted_patch_artifact"] = patch_payload
        if event.type == EventType.SUBMISSION_ACCEPTED:
            payload["submitted_patch_artifact"] = patch_payload
        rebound.append(
            RunEvent.model_validate({**event.model_dump(mode="json"), "payload": payload})
        )
    return tuple(rebound)


def test_runtime_producer_persists_typed_registered_check_and_scope_evidence(
    tmp_path,
) -> None:
    chain = _v2_chain()
    store = ArtifactStore(tmp_path / "artifacts")
    patch = store.put_text(
        "diff --git a/example.py b/example.py\n",
        "text/x-diff",
    )
    patch_ref = build_submitted_patch_ref(store, patch)
    hidden_check = chain.package.private.hidden_checks[0]

    produced = produce_registered_check_evidence_v2(
        artifact_store=store,
        manifest=chain.manifest,
        submitted_patch=patch_ref,
        check_type="hidden",
        check=hidden_check,
        outcome=_sandbox_result_for_check(hidden_check),
        private_markers=PRIVATE_MARKERS,
    )
    persisted = RegisteredCheckResultEvidenceV2.model_validate_json(
        store.read_bytes(produced.artifact)
    )

    assert persisted == produced.observation
    assert produced.verifier_result.state == VerdictState.PASS
    assert produced.request.requested_network == "none"
    assert produced.request.read_only_workspace is True
    assert produced.request.evaluator_image_digest == SHA_D
    assert produced.artifact_ref.role == "hidden_check_result"
    assert produced.artifact.path not in produced.verifier_result.model_dump_json()

    leaky_outcome = _sandbox_result_for_check(hidden_check)
    leaky_outcome = SandboxResult(
        **{
            **leaky_outcome.__dict__,
            "stdout": f"before {PRIVATE_MARKERS[0].decode()} after",
        }
    )
    redacted = produce_registered_check_evidence_v2(
        artifact_store=store,
        manifest=chain.manifest,
        submitted_patch=patch_ref,
        check_type="hidden",
        check=hidden_check,
        outcome=leaky_outcome,
        private_markers=PRIVATE_MARKERS,
    )
    redacted_bytes = store.read_bytes(redacted.artifact)
    assert PRIVATE_MARKERS[0] not in redacted_bytes
    assert redacted.observation.redacted_private_marker_match_count == 1

    scope = produce_scope_policy_evidence_v2(
        artifact_store=store,
        manifest=chain.manifest,
        submitted_patch=patch_ref,
        check_id="scope",
        outcome=PolicyOutcome(passed=False, violations=["outside allowed path"]),
    )
    persisted_scope = ScopePolicyResultEvidenceV2.model_validate_json(
        store.read_bytes(scope.artifact)
    )
    assert persisted_scope == scope.observation
    assert scope.verifier_result.state == VerdictState.FAIL
    assert scope.observation.violation_count == 1


def test_runtime_producer_fails_closed_on_untyped_or_misbound_sandbox_policy(
    tmp_path,
) -> None:
    chain = _v2_chain()
    store = ArtifactStore(tmp_path / "artifacts")
    patch_ref = build_submitted_patch_ref(
        store,
        store.put_text("diff --git a/a b/a\n", "text/x-diff"),
    )
    check = chain.package.private.hidden_checks[0]
    valid_policy = registered_check_execution_policy(
        image=f"example/evaluator@{SHA_D}",
        working_directory="/workspace",
        timeout_seconds=check.timeout_seconds,
        output_limit_bytes=check.output_limit_bytes,
    )

    for outcome in (
        _sandbox_result_for_check(check, execution_policy=None),
        _sandbox_result_for_check(
            check,
            execution_policy={**valid_policy, "requested_network": "bridge"},
        ),
        _sandbox_result_for_check(check, image_digest=SHA_A),
    ):
        if outcome.execution_policy is not None and outcome.execution_policy == valid_policy:
            outcome = SandboxResult(
                **{
                    **outcome.__dict__,
                    "execution_policy": None,
                }
            )
        with pytest.raises(ContractError, match="requested-policy|requested policy"):
            produce_registered_check_evidence_v2(
                artifact_store=store,
                manifest=chain.manifest,
                submitted_patch=patch_ref,
                check_type="hidden",
                check=check,
                outcome=outcome,
                private_markers=PRIVATE_MARKERS,
            )

    with pytest.raises(ContractError, match="scope policy observation"):
        produce_scope_policy_evidence_v2(
            artifact_store=store,
            manifest=chain.manifest,
            submitted_patch=patch_ref,
            check_id="scope",
            outcome=PolicyOutcome(passed=False, violations=[]),
        )


@pytest.mark.parametrize(
    ("marker_in_output", "expected_safety", "expected_success"),
    [
        (False, VerdictState.PASS, True),
        (True, VerdictState.FAIL, False),
    ],
)
def test_runtime_result_producer_builds_a_self_validating_unofficial_chain(
    tmp_path,
    marker_in_output: bool,
    expected_safety: VerdictState,
    expected_success: bool,
) -> None:
    chain = _v2_chain()
    store = ArtifactStore(tmp_path / "artifacts")
    patch = store.put_text(
        "diff --git a/example.py b/example.py\n",
        "text/x-diff",
    )
    patch_ref = build_submitted_patch_ref(store, patch)
    registered = []
    for check_type, checks in (
        ("hidden", chain.package.private.hidden_checks),
        ("regression", chain.package.public.visible_checks),
    ):
        for check in checks:
            outcome = _sandbox_result_for_check(check)
            if marker_in_output and not registered:
                outcome = SandboxResult(
                    **{
                        **outcome.__dict__,
                        "stdout": PRIVATE_MARKERS[0].decode("utf-8"),
                    }
                )
            registered.append(
                produce_registered_check_evidence_v2(
                    artifact_store=store,
                    manifest=chain.manifest,
                    submitted_patch=patch_ref,
                    check_type=check_type,
                    check=check,
                    outcome=outcome,
                    private_markers=PRIVATE_MARKERS,
                )
            )
    policies = [
        produce_scope_policy_evidence_v2(
            artifact_store=store,
            manifest=chain.manifest,
            submitted_patch=patch_ref,
            check_id=check_id,
            outcome=PolicyOutcome(passed=True),
        )
        for check_id in SCOPE_IDS
    ]

    produced = produce_evaluator_v2_result(
        artifact_store=store,
        package=chain.package,
        manifest=chain.manifest,
        expected_contract=chain.contract,
        expected_evaluator_source_hash=SHA_C,
        expected_tool_schemas=TOOL_SCHEMAS_V2,
        private_markers=PRIVATE_MARKERS,
        events=_accepted_events_for_patch(chain, patch),
        submitted_patch=patch,
        registered_checks=registered,
        scope_policies=policies,
    )

    assert produced.result.verdicts.safety_policy == expected_safety
    assert produced.result.scope_compliant_success is expected_success
    assert produced.result.official is False
    assert produced.validation.runtime_authenticated is False
    assert produced.validation.qualification_eligible is False
    assert store.read_bytes(produced.bundle_artifact)
    if marker_in_output:
        assert all(
            PRIVATE_MARKERS[0] not in store.read_bytes(artifact)
            for artifact in produced.evidence_artifacts
        )


def test_store_bound_runtime_producer_uses_the_exact_durable_event_prefix(
    tmp_path,
) -> None:
    chain = _v2_chain()
    store = ArtifactStore(tmp_path / "artifacts")
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(chain.manifest)
    patch = store.put_text(
        "diff --git a/example.py b/example.py\n",
        "text/x-diff",
    )
    for event in _accepted_events_for_patch(chain, patch):
        state.append_event(
            chain.manifest.run_id,
            event.type,
            actor=event.actor,
            payload=event.payload,
            correlation_id=event.correlation_id,
        )
    patch_ref = build_submitted_patch_ref(store, patch)
    registered = [
        produce_registered_check_evidence_v2(
            artifact_store=store,
            manifest=chain.manifest,
            submitted_patch=patch_ref,
            check_type=check_type,
            check=check,
            outcome=_sandbox_result_for_check(check),
            private_markers=PRIVATE_MARKERS,
        )
        for check_type, checks in (
            ("hidden", chain.package.private.hidden_checks),
            ("regression", chain.package.public.visible_checks),
        )
        for check in checks
    ]
    policies = [
        produce_scope_policy_evidence_v2(
            artifact_store=store,
            manifest=chain.manifest,
            submitted_patch=patch_ref,
            check_id=check_id,
            outcome=PolicyOutcome(passed=True),
        )
        for check_id in SCOPE_IDS
    ]
    inputs = {
        "state_store": state,
        "artifact_store": store,
        "run_id": chain.manifest.run_id,
        "package": chain.package,
        "expected_contract": chain.contract,
        "expected_evaluator_source_hash": SHA_C,
        "expected_tool_schemas": TOOL_SCHEMAS_V2,
        "private_markers": PRIVATE_MARKERS,
        "submitted_patch": patch,
        "registered_checks": registered,
        "scope_policies": policies,
    }

    store_bound = produce_evaluator_v2_result_from_state(**inputs)

    assert store_bound.durable_event_prefix is True
    assert store_bound.cas_verified is True
    assert store_bound.runtime_authenticated is False
    assert store_bound.qualification_eligible is False
    assert store_bound.production.result.scope_compliant_success is True

    state.append_event(
        chain.manifest.run_id,
        EventType.CHECK_FINISHED,
        actor="evaluator",
        payload={"note": "unbound tail"},
    )
    with pytest.raises(ContractError, match="preterminal bookkeeping tail"):
        produce_evaluator_v2_result_from_state(**inputs)


def test_v2_receipt_revalidates_state_and_cas_before_terminal_persistence(
    tmp_path,
) -> None:
    chain = _v2_chain()
    store = ArtifactStore(tmp_path / "artifacts")
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(chain.manifest)
    state.set_run_status(chain.manifest.run_id, RunStatus.RUNNING)
    patch = store.put_text(
        "diff --git a/example.py b/example.py\n",
        "text/x-diff",
    )
    for event in _accepted_events_for_patch(chain, patch):
        state.append_event(
            chain.manifest.run_id,
            event.type,
            actor=event.actor,
            payload=event.payload,
            correlation_id=event.correlation_id,
        )
    patch_ref = build_submitted_patch_ref(store, patch)
    registered = [
        produce_registered_check_evidence_v2(
            artifact_store=store,
            manifest=chain.manifest,
            submitted_patch=patch_ref,
            check_type=check_type,
            check=check,
            outcome=_sandbox_result_for_check(check),
            private_markers=PRIVATE_MARKERS,
        )
        for check_type, checks in (
            ("hidden", chain.package.private.hidden_checks),
            ("regression", chain.package.public.visible_checks),
        )
        for check in checks
    ]
    policies = [
        produce_scope_policy_evidence_v2(
            artifact_store=store,
            manifest=chain.manifest,
            submitted_patch=patch_ref,
            check_id=check_id,
            outcome=PolicyOutcome(passed=True),
        )
        for check_id in SCOPE_IDS
    ]
    runtime_authority = EvaluatorV2RuntimeAuthority(
        safety_contract=chain.contract,
        evaluator_source_hash=SHA_C,
        tool_schemas=tuple(TOOL_SCHEMAS_V2),
        private_markers=PRIVATE_MARKERS,
    )
    authority = EvaluatorV2QualificationAuthority(
        runtime=runtime_authority,
        suite_hash=SHA_A,
        source_qualification_hash=SHA_B,
        runtime_tuple_hash=evaluator_v2_manifest_runtime_tuple_hash(chain.manifest),
    )
    production = produce_evaluator_v2_result_from_state(
        state_store=state,
        artifact_store=store,
        run_id=chain.manifest.run_id,
        package=chain.package,
        expected_contract=chain.contract,
        expected_evaluator_source_hash=SHA_C,
        expected_tool_schemas=TOOL_SCHEMAS_V2,
        private_markers=PRIVATE_MARKERS,
        submitted_patch=patch,
        registered_checks=registered,
        scope_policies=policies,
    )

    validated = issue_evaluator_v2_evaluation_receipt(
        state_store=state,
        artifact_store=store,
        package=chain.package,
        production=production,
        authority=authority,
        evaluator_duration_ms=17,
    )

    assert validated.receipt.runtime_authenticated is True
    assert validated.receipt.qualification_eligible is True
    assert validated.result.official is False
    assert validated.receipt.source_qualification_hash == SHA_B
    assert (
        validate_persisted_evaluator_v2_evaluation_receipt(
            state_store=state,
            artifact_store=store,
            run_id=chain.manifest.run_id,
            package=chain.package,
            authority=authority,
        ).receipt
        == validated.receipt
    )
    state.finalize_run(
        chain.manifest.run_id,
        status=RunStatus.COMPLETED,
        result=validated.result,
        event_type=EventType.RUN_COMPLETED,
        actor="evaluator",
        evaluator_v2_receipt=validated.receipt,
    )
    terminal = state.list_events(chain.manifest.run_id)[-1]
    assert terminal.payload["evaluator_v2_receipt_hash"] == validated.receipt.content_hash
    assert terminal.payload["evaluator_v2_source_qualification_hash"] == SHA_B
    assert (
        validate_persisted_evaluator_v2_evaluation_receipt(
            state_store=state,
            artifact_store=store,
            run_id=chain.manifest.run_id,
            package=chain.package,
            authority=authority,
        ).receipt
        == validated.receipt
    )

    from patchloop.evals.qualification import _evaluation_receipt_evidence

    receipt_ok, receipt_evidence = _evaluation_receipt_evidence(
        root=tmp_path,
        run_id=chain.manifest.run_id,
        manifest=chain.manifest,
        result=validated.result,
        package=chain.package,
        state=state,
        evaluator_v2_authority=authority,
    )
    assert receipt_ok is True
    assert receipt_evidence["runtime_authenticated"] is True
    assert receipt_evidence["qualification_eligible"] is True
    wrong_authority = EvaluatorV2QualificationAuthority(
        runtime=runtime_authority,
        suite_hash=SHA_A,
        source_qualification_hash=SHA_D,
        runtime_tuple_hash=evaluator_v2_manifest_runtime_tuple_hash(chain.manifest),
    )
    assert (
        _evaluation_receipt_evidence(
            root=tmp_path,
            run_id=chain.manifest.run_id,
            manifest=chain.manifest,
            result=validated.result,
            package=chain.package,
            state=state,
            evaluator_v2_authority=wrong_authority,
        )[0]
        is False
    )

    tampered = validated.receipt.model_copy(update={"suite_hash": SHA_D})
    with pytest.raises(ValidationError, match="content hash mismatch"):
        EvaluatorV2EvaluationReceipt.model_validate(tampered.model_dump(mode="json"))


class _OfflineRequestedPolicySandbox:
    """Execute local fixtures while emitting the Docker request shape under test."""

    official = True

    def image_identity(self) -> str:
        return SHA_D

    def probe_image_identity(self) -> None:
        return None

    def run_check(self, workspace, check) -> SandboxResult:
        local = LocalSandbox().run_check(workspace, check)
        workdir = (
            "/workspace"
            if check.working_directory == "."
            else f"/workspace/{check.working_directory}"
        )
        return SandboxResult(
            **{
                **local.__dict__,
                "execution_policy": registered_check_execution_policy(
                    image=f"example/evaluator@{SHA_D}",
                    working_directory=workdir,
                    timeout_seconds=check.timeout_seconds,
                    output_limit_bytes=check.output_limit_bytes,
                ),
            }
        )


def test_evaluation_engine_v2_candidate_uses_real_local_producers_but_stays_unofficial(
    tmp_path,
) -> None:
    chain = _v2_chain()
    store = ArtifactStore(tmp_path / "artifacts")
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(chain.manifest)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    prepared = manager.create(
        "prepare-v2-patch",
        chain.package.public.repository.url,
        chain.package.public.repository.base_commit,
    )
    manager.apply_patch(
        prepared,
        Path("tasks/smoke/csv-quoted-newline/reference.patch"),
    )
    patch_text = manager.diff_summary(prepared).patch
    patch = store.put_text(patch_text, "text/x-diff")
    for event in _accepted_events_for_patch(chain, patch):
        state.append_event(
            chain.manifest.run_id,
            event.type,
            actor=event.actor,
            payload=event.payload,
            correlation_id=event.correlation_id,
        )
    engine = EvaluationEngine(
        manager,
        _OfflineRequestedPolicySandbox(),
        store,
        state,
    )
    authority = EvaluatorV2RuntimeAuthority(
        safety_contract=chain.contract,
        evaluator_source_hash=SHA_C,
        tool_schemas=tuple(TOOL_SCHEMAS_V2),
        private_markers=PRIVATE_MARKERS,
    )

    produced = engine.evaluate_v2_candidate(
        "tasks/smoke/csv-quoted-newline",
        patch.path,
        chain.manifest,
        submitted_patch_artifact=patch,
        authority=authority,
    )

    assert produced.production.result.scope_compliant_success is True
    assert produced.production.result.official is False
    assert produced.runtime_authenticated is False
    assert produced.qualification_eligible is False


def test_agent_runner_v2_path_issues_receipt_and_finalizes_only_with_authority(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chain = _v2_chain()
    runner = AgentRunner(tmp_path)
    sandbox = _OfflineRequestedPolicySandbox()
    monkeypatch.setattr(DockerSandbox, "available", staticmethod(lambda: True))
    monkeypatch.setattr(runner, "_docker_sandbox", lambda _package: sandbox)
    authority = EvaluatorV2QualificationAuthority(
        runtime=EvaluatorV2RuntimeAuthority(
            safety_contract=chain.contract,
            evaluator_source_hash=SHA_C,
            tool_schemas=tuple(TOOL_SCHEMAS_V2),
            private_markers=PRIVATE_MARKERS,
        ),
        suite_hash=SHA_A,
        source_qualification_hash=SHA_B,
        runtime_tuple_hash=evaluator_v2_manifest_runtime_tuple_hash(chain.manifest),
    )

    result = runner.start(
        "tasks/smoke/csv-quoted-newline",
        model="mock",
        manifest=chain.manifest,
        evaluator_v2_authority=authority,
    )

    assert result["schema_version"] == "run-result-v2"
    assert result["official"] is False
    assert result["evaluation_status"] == "completed"
    assert runner.state.get_run_status(chain.manifest.run_id) == RunStatus.COMPLETED
    receipt = validate_persisted_evaluator_v2_evaluation_receipt(
        state_store=runner.state,
        artifact_store=runner.artifacts,
        run_id=chain.manifest.run_id,
        package=chain.package,
        authority=authority,
    ).receipt
    assert receipt.runtime_authenticated is True
    assert (
        runner.state.list_events(chain.manifest.run_id)[-1].payload["evaluator_v2_receipt_hash"]
        == receipt.content_hash
    )


def test_cross_artifact_validator_accepts_exact_task_files_events_and_cas() -> None:
    chain = _v2_chain()
    validated = validate_evaluator_v2_artifact_chain(
        package=chain.package,
        expected_contract=chain.contract,
        expected_evaluator_source_hash=SHA_C,
        expected_tool_schemas=TOOL_SCHEMAS_V2,
        private_markers=PRIVATE_MARKERS,
        manifest=chain.manifest,
        result=chain.result,
        bundle=chain.bundle,
        manifest_bytes=chain.manifest_bytes,
        result_bytes=chain.result_bytes,
        bundle_bytes=chain.bundle_bytes,
        events=chain.events,
        evidence_descriptors=chain.descriptors,
        read_evidence=lambda artifact: chain.evidence_bytes[artifact.artifact_id],
    )
    assert validated.safety_state == VerdictState.PASS
    assert validated.runtime_authenticated is False
    assert validated.qualification_eligible is False
    assert validated.safety_bundle_semantic_hash == chain.bundle.content_hash
    assert validated.safety_bundle_artifact_hash == chain.result.safety_evidence_bundle.content_hash

    replayed = _validate_chain(_v2_chain(extra_tool_name="read_file", extra_tool_replay=True))
    assert replayed.safety_state == VerdictState.PASS


@pytest.mark.parametrize(
    ("chain", "message"),
    [
        (_v2_chain(bundle_ref_collision=True), "conflicting typed projections"),
        (_v2_chain(accepted_worktree_hash=SHA_A), "patch disagrees"),
        (_v2_chain(called_worktree_hash=SHA_A), "lifecycle fields are invalid"),
        (_v2_chain(extra_tool_name="powershell"), "gateway trace disagrees"),
        (
            _v2_chain(orphan_outcome_tool="powershell"),
            "no valid registered lifecycle",
        ),
        (_v2_chain(requested_network="bridge"), "safety state disagrees"),
        (_v2_chain(read_only_workspace=False), "safety state disagrees"),
        (_v2_chain(raw_marker_in_check_output=True), "private marker escaped"),
    ],
)
def test_cross_artifact_validator_rejects_semantic_self_attestation(
    chain: V2Chain,
    message: str,
) -> None:
    with pytest.raises(ContractError, match=message):
        _validate_chain(chain)


def test_cross_artifact_validator_rejects_unbound_event_tail_and_descriptor_metadata() -> None:
    chain = _v2_chain()
    tail = RunEvent(
        event_id="evt_00000000000000000000000000000008",
        run_id=chain.manifest.run_id,
        sequence=len(chain.events) + 1,
        type=EventType.CHECK_FINISHED,
        timestamp=datetime(2026, 8, 11, 0, 0, 9, tzinfo=UTC),
        actor="evaluator",
        payload={"note": "after accepted submission"},
    )
    with pytest.raises(ContractError, match="events must equal the bound prefix"):
        _validate_chain(chain, events=(*chain.events, tail))

    descriptors = dict(chain.descriptors)
    evidence_id = chain.bundle.records[0].evidence_artifacts[0].artifact_id
    descriptor = descriptors[evidence_id]
    descriptors[evidence_id] = descriptor.model_copy(
        update={"path": f"C:/virtual/{PRIVATE_MARKERS[0].decode('utf-8')}"}
    )
    with pytest.raises(ContractError, match="private marker escaped"):
        _validate_chain(chain, evidence_descriptors=descriptors)

    untrusted_tools = [{"type": "function", "name": "shell"}]
    with pytest.raises(ContractError, match="unrestricted capability"):
        _validate_chain(chain, expected_tool_schemas=untrusted_tools)

    aliased_tools = json.loads(json.dumps(TOOL_SCHEMAS_V2))
    aliased_tools[0]["name"] = "pwsh"
    with pytest.raises(ContractError, match="exact constrained v2 set"):
        _validate_chain(chain, expected_tool_schemas=aliased_tools)


def test_cross_artifact_validator_rejects_wrong_files_prefix_and_cas() -> None:
    chain = _v2_chain()
    common = {
        "package": chain.package,
        "expected_contract": chain.contract,
        "expected_evaluator_source_hash": SHA_C,
        "expected_tool_schemas": TOOL_SCHEMAS_V2,
        "private_markers": PRIVATE_MARKERS,
        "manifest": chain.manifest,
        "result": chain.result,
        "bundle": chain.bundle,
        "manifest_bytes": chain.manifest_bytes,
        "result_bytes": chain.result_bytes,
        "bundle_bytes": chain.bundle_bytes,
        "events": chain.events,
        "evidence_descriptors": chain.descriptors,
        "read_evidence": lambda artifact: chain.evidence_bytes[artifact.artifact_id],
    }
    with pytest.raises(ContractError, match="unexpected serializer"):
        validate_evaluator_v2_artifact_chain(
            **{**common, "manifest_bytes": chain.manifest_bytes + b"\n"}
        )

    missing = dict(chain.descriptors)
    missing.pop(chain.result.safety_evidence_bundle.artifact_id)
    with pytest.raises(ContractError, match="inventory is not exact"):
        validate_evaluator_v2_artifact_chain(**{**common, "evidence_descriptors": missing})

    wrong_bytes = dict(chain.evidence_bytes)
    first_evidence_id = chain.bundle.records[0].evidence_artifacts[0].artifact_id
    wrong_bytes[first_evidence_id] = b"tampered"
    with pytest.raises(ContractError, match="integrity verification"):
        validate_evaluator_v2_artifact_chain(
            **{
                **common,
                "read_evidence": lambda artifact: wrong_bytes[artifact.artifact_id],
            }
        )

    wrong_prefix = _v2_chain(event_prefix_hash=SHA_A)
    with pytest.raises(ContractError, match="event prefix hash mismatch"):
        validate_evaluator_v2_artifact_chain(
            package=wrong_prefix.package,
            expected_contract=wrong_prefix.contract,
            expected_evaluator_source_hash=SHA_C,
            expected_tool_schemas=TOOL_SCHEMAS_V2,
            private_markers=PRIVATE_MARKERS,
            manifest=wrong_prefix.manifest,
            result=wrong_prefix.result,
            bundle=wrong_prefix.bundle,
            manifest_bytes=wrong_prefix.manifest_bytes,
            result_bytes=wrong_prefix.result_bytes,
            bundle_bytes=wrong_prefix.bundle_bytes,
            events=wrong_prefix.events,
            evidence_descriptors=wrong_prefix.descriptors,
            read_evidence=lambda artifact: wrong_prefix.evidence_bytes[artifact.artifact_id],
        )


@pytest.mark.parametrize(
    ("chain", "message"),
    [
        (_v2_chain(generic_command_observation=True), "evidence payload is invalid"),
        (_v2_chain(raw_marker_in_event=True), "private marker escaped"),
    ],
)
def test_cross_artifact_validator_rejects_generic_payload_and_raw_private_marker(
    chain: V2Chain,
    message: str,
) -> None:
    with pytest.raises(ContractError, match=message):
        validate_evaluator_v2_artifact_chain(
            package=chain.package,
            expected_contract=chain.contract,
            expected_evaluator_source_hash=SHA_C,
            expected_tool_schemas=TOOL_SCHEMAS_V2,
            private_markers=PRIVATE_MARKERS,
            manifest=chain.manifest,
            result=chain.result,
            bundle=chain.bundle,
            manifest_bytes=chain.manifest_bytes,
            result_bytes=chain.result_bytes,
            bundle_bytes=chain.bundle_bytes,
            events=chain.events,
            evidence_descriptors=chain.descriptors,
            read_evidence=lambda artifact: chain.evidence_bytes[artifact.artifact_id],
        )


def test_cross_artifact_validator_requires_trusted_contract_source_and_base() -> None:
    chain = _v2_chain()
    common = {
        "package": chain.package,
        "expected_contract": chain.contract,
        "expected_evaluator_source_hash": SHA_C,
        "expected_tool_schemas": TOOL_SCHEMAS_V2,
        "private_markers": PRIVATE_MARKERS,
        "manifest": chain.manifest,
        "result": chain.result,
        "bundle": chain.bundle,
        "manifest_bytes": chain.manifest_bytes,
        "result_bytes": chain.result_bytes,
        "bundle_bytes": chain.bundle_bytes,
        "events": chain.events,
        "evidence_descriptors": chain.descriptors,
        "read_evidence": lambda artifact: chain.evidence_bytes[artifact.artifact_id],
    }
    with pytest.raises(ContractError, match="trusted offline authority"):
        validate_evaluator_v2_artifact_chain(**{**common, "expected_evaluator_source_hash": SHA_A})

    contract_payload = chain.contract.model_dump(mode="json", exclude={"content_hash"})
    contract_payload["requirements"][0]["policy_input_hash"] = SHA_A
    other_contract = EvaluatorSafetyContract(
        **contract_payload,
        content_hash=sha256_json(contract_payload),
    )
    with pytest.raises(ContractError, match="trusted safety contract"):
        validate_evaluator_v2_artifact_chain(**{**common, "expected_contract": other_contract})

    manifest_payload = chain.manifest.model_dump(mode="json")
    manifest_payload["base_commit"] = "f" * 40
    other_manifest = RunManifest.model_validate(manifest_payload)
    with pytest.raises(ContractError, match="base commit"):
        validate_evaluator_v2_artifact_chain(
            **{
                **common,
                "manifest": other_manifest,
                "manifest_bytes": other_manifest.model_dump_json(indent=2).encode("utf-8"),
            }
        )


def test_cross_artifact_validator_rejects_local_sandbox_policy_pass() -> None:
    chain = _v2_chain(sandbox_backend="local")
    with pytest.raises(ContractError, match="digest-bound Docker evaluator"):
        validate_evaluator_v2_artifact_chain(
            package=chain.package,
            expected_contract=chain.contract,
            expected_evaluator_source_hash=SHA_C,
            expected_tool_schemas=TOOL_SCHEMAS_V2,
            private_markers=PRIVATE_MARKERS,
            manifest=chain.manifest,
            result=chain.result,
            bundle=chain.bundle,
            manifest_bytes=chain.manifest_bytes,
            result_bytes=chain.result_bytes,
            bundle_bytes=chain.bundle_bytes,
            events=chain.events,
            evidence_descriptors=chain.descriptors,
            read_evidence=lambda artifact: chain.evidence_bytes[artifact.artifact_id],
        )
