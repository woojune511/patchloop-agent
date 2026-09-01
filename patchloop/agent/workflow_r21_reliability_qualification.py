"""Deterministic zero-call qualification for the Lean V26 R21 successor."""

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
from patchloop.agent.investigation import InspectionRecord
from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V26,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V26,
    LEAN_RUNTIME_POLICY_VERSION_V26,
    LEAN_TOOL_SCHEMA_VERSION_V26,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    _task,
)
from patchloop.agent.workflow_plan_admission_feedback_successor_qualification import (
    _feedback_details,
)
from patchloop.agent.workflow_plan_contract_compatibility_successor import (
    project_trigger_bound_self_directed_plan_request,
)
from patchloop.agent.workflow_r21_reliability_successor import (
    ANCHORED_READ_POLICY,
    GENERATION_INCOMPLETE_RECOVERY_POLICY,
    LIFECYCLE_PLAN_POLICY,
    MAX_PLAN_FEEDBACK_BYTES,
    PLAN_ADMISSION_FEEDBACK_POLICY_V2,
    normalize_lifecycle_bound_plan,
    project_compact_plan_admission_feedback_v2,
    project_generation_incomplete_recovery,
    project_lifecycle_bound_plan_request,
    resolve_anchored_read,
)
from patchloop.agent.workflow_self_directed_exploration_successor_qualification import (
    _catalog_v4,
    _plan_arguments,
    _request,
)
from patchloop.contracts import Artifact, EventType, RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.evals.anyio_runner_continuity_public_check import (
    QUALIFICATION_PATH as RUNNER_CONTINUITY_QUALIFICATION_PATH,
)
from patchloop.evals.anyio_runner_continuity_public_check import (
    build_qualification as build_runner_continuity_qualification,
)
from patchloop.evals.anyio_runner_continuity_public_check import (
    qualification_bytes as runner_continuity_qualification_bytes,
)
from patchloop.util import (
    canonical_json,
    ensure_within,
    sha256_bytes,
    sha256_json,
    sha256_text,
)

SCHEMA_VERSION = "lean-r21-reliability-successor-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-r21-reliability-public-qualification-20260831-v1.json"
)

IMMUTABLE_INPUTS = {
    "patchloop/agent/workflow_plan_contract_compatibility_successor.py": {
        "bytes": 9_952,
        "file_sha256": "sha256:d49329cbd4bb1f313e9612679cc7a97b450c5bc6fcf0bc5721f6b2b3cf259d8c",
    },
    "experiments/lean-harness-plan-contract-compatibility-public-qualification-20260830-v1.json": {
        "bytes": 5_493,
        "file_sha256": "sha256:b22700a13fe823a270c439c9972e21d21eb8d1d53ae6a0431452fc77f8cbc4a9",
        "content_hash": "sha256:c6c075746ef7557a620860acaedb9fc202f674a32be11e9cb49e2507172a8453",
    },
    (
        "reports/rapid-development/rapid-public-dev-anyio-v5-v25-mechanical-"
        "activation-20260830-r21-590bbd602a34.jsonl"
    ): {
        "bytes": 21_394,
        "file_sha256": "sha256:54ae5e99226ec8a2d6635e6ece104c87b3ae1ba0e6aca675e20c7d7d339a749a",
    },
    "reports/rapid-development/rapid-workflow-diagnosis-r21-590bbd602a34.json": {
        "bytes": 11_731,
        "file_sha256": "sha256:14663e2ed74a684c3c9d017a8e3c6812b3187b09938cea703a0735b920f4a884",
        "content_hash": "sha256:4893b30ff24c9d95ad844569fe5831497400893784e3a99ef663db4016adc601",
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_r21_reliability_successor.py",
    "patchloop/agent/workflow_r21_reliability_qualification.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/investigation.py",
    "patchloop/contracts.py",
    "patchloop/errors.py",
    "scripts/build_lean_harness_r21_reliability_qualification.py",
    "tests/test_workflow_r21_reliability_successor.py",
    "tests/test_workflow_r21_reliability_runner.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"R21 reliability input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _immutable_identity(root: Path, relative: str) -> dict[str, Any]:
    identity = _identity(root, relative)
    expected = IMMUTABLE_INPUTS[relative]
    if "content_hash" in expected:
        try:
            document = json.loads(ensure_within(root, relative).read_bytes())
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("R21 reliability immutable JSON is invalid") from exc
        content_hash = document.get("content_hash")
        if content_hash != sha256_json(
            {key: value for key, value in document.items() if key != "content_hash"}
        ):
            raise ContractError("R21 reliability immutable content hash differs")
        identity["content_hash"] = content_hash
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"R21 reliability immutable input differs: {relative}")
    return identity


def _runner_continuity_identity(root: Path) -> dict[str, Any]:
    relative = RUNNER_CONTINUITY_QUALIFICATION_PATH.as_posix()
    identity = _identity(root, relative)
    raw = ensure_within(root, relative).read_bytes()
    expected = runner_continuity_qualification_bytes(build_runner_continuity_qualification(root))
    if raw != expected:
        raise ContractError("runner-continuity source qualification differs")
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError("runner-continuity source qualification is invalid") from exc
    if (
        document.get("status") != "offline-source-qualified-proposal"
        or document.get("activation_authorized") is not False
        or document.get("task_successor_created") is not False
        or document.get("behavior_observed") is not False
    ):
        raise ContractError("runner-continuity proposal boundary differs")
    return {
        **identity,
        "content_hash": document["content_hash"],
        "status": document["status"],
        "task_successor_created": False,
        "behavior_observed": False,
        "activation_authorized": False,
    }


def _generation_scenario() -> dict[str, Any]:
    timestamp = datetime(2026, 8, 31, tzinfo=UTC)

    def blocked(sequence: int, policy: str = GENERATION_INCOMPLETE_RECOVERY_POLICY) -> RunEvent:
        return RunEvent(
            event_id=f"evt-generation-{sequence}",
            run_id="run-v26-qualification",
            sequence=sequence,
            type=EventType.TOOL_ADMISSION_BLOCKED,
            timestamp=timestamp,
            actor="workflow-state-machine",
            payload={
                "policy_version": policy,
                "reason_code": "reasoning_incomplete",
                "execution": "not_dispatched",
            },
        )

    available = project_generation_incomplete_recovery((blocked(1, "other-policy"),))
    consumed = project_generation_incomplete_recovery((blocked(2),))
    repeated_rejected = False
    try:
        project_generation_incomplete_recovery((blocked(2), blocked(3)))
    except RecoveryError:
        repeated_rejected = True
    return {
        "available_remaining": available.remaining,
        "consumed_remaining": consumed.remaining,
        "consumed_source_event_sequence": consumed.source_event_sequence,
        "other_policy_consumed": available.used,
        "second_incomplete_rejected": repeated_rejected,
        "shared_action_recovery_slot_consumed": False,
    }


def _feedback_context(details: dict[str, Any]) -> BuiltContext:
    events = []
    for sequence in (16, 17):
        events.append(
            {
                "sequence": sequence,
                "type": "ToolFailed",
                "actor": "tool-gateway",
                "payload": {
                    "tool": "record_work_plan",
                    "status": "rejected",
                    "error_code": "WORK_PLAN_ADMISSION_REJECTED",
                    "error_message": "public plan is incomplete",
                    "error_details": copy.deepcopy(details),
                    "admission_blocked": True,
                },
            }
        )
    payload = {
        "public_task": {"task_id": "r21-reliability-qualification"},
        "phase": "PLAN",
        "checkpoint": None,
        "phase_contract": {"current_phase": "PLAN"},
        "recent_events": events,
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


def _feedback_scenario() -> dict[str, Any]:
    details = _feedback_details()
    details["policy_version"] = "bounded-self-directed-exploration-v1"
    details["eligible_plan_evidence_catalog"] = {
        **details["eligible_plan_evidence_catalog"],
        "items": [{"evidence_id": "pev:17"}, {"evidence_id": "pev:19"}],
    }
    catalog_body = {
        key: value
        for key, value in details["eligible_plan_evidence_catalog"].items()
        if key != "content_hash"
    }
    details["eligible_plan_evidence_catalog"]["content_hash"] = sha256_json(catalog_body)
    details["eligible_catalog_hash"] = details["eligible_plan_evidence_catalog"]["content_hash"]
    details["activated_exploration_plan_request"]["source_span_catalog"] = {
        "spans": [{"source_span_id": "cspan:21:0"}, {"source_span_id": "cspan:22:0"}]
    }
    activated_body = {
        key: value
        for key, value in details["activated_exploration_plan_request"].items()
        if key != "content_hash"
    }
    details["activated_exploration_plan_request"]["content_hash"] = sha256_json(activated_body)
    details["activated_exploration_plan_request_hash"] = details[
        "activated_exploration_plan_request"
    ]["content_hash"]
    compacted = project_lean_context_event_descriptors_v2(_feedback_context(details))
    first = project_compact_plan_admission_feedback_v2(compacted)
    second = project_compact_plan_admission_feedback_v2(compacted)
    events = json.loads(first.rendered)["recent_events"]
    latest = events[-1]["payload"]["error_details"]
    return {
        "deterministic": first == second,
        "rejection_count": first.evidence.rejection_count,
        "latest_feedback_bytes": first.evidence.latest_feedback_bytes,
        "byte_ceiling": MAX_PLAN_FEEDBACK_BYTES,
        "older_rejection_hash_only": (
            events[0]["payload"]["error_details"]["schema_version"]
            == "superseded-plan-admission-feedback-v2"
        ),
        "latest_evidence_ids": latest["eligible_evidence_ids"],
        "latest_source_span_ids": latest["eligible_source_span_ids"],
        "durable_event_changed": first.evidence.durable_event_changed,
    }


def _anchor_scenario() -> dict[str, Any]:
    timestamp = datetime(2026, 8, 31, tzinfo=UTC)
    result = {
        "matches": [
            {"path": "src/pkg/example.py", "line": 41, "text": "def target():"},
            {"path": "src/pkg/example.py", "line": 88, "text": "return state"},
        ]
    }
    record = InspectionRecord(
        tool="search_files",
        arguments={"query": "target", "path_glob": "src/**/*.py"},
        input_hash=sha256_text("input"),
        normalized_call_hash=sha256_text("call"),
        worktree_diff_hash=sha256_text("diff"),
        mutation_epoch_sequence=None,
        call_sequence=6,
        outcome_sequence=7,
        action_id="search-target",
        result=result,
        result_artifact=Artifact(
            artifact_id="art-search",
            content_hash=sha256_json(result),
            media_type="application/json",
            size_bytes=len(canonical_json(result).encode("utf-8")),
            path="objects/search.json",
            created_at=timestamp,
        ),
    )
    resolved = resolve_anchored_read(
        run_id="run-v26-qualification",
        task=_task(),
        worktree_diff_hash=record.worktree_diff_hash,
        records=(record,),
        raw_anchor={
            "search_event_sequence": 7,
            "match_index": 1,
            "before_lines": 8,
            "after_lines": 12,
        },
    )
    stale_rejected = False
    try:
        resolve_anchored_read(
            run_id="run-v26-qualification",
            task=_task(),
            worktree_diff_hash=sha256_text("stale"),
            records=(record,),
            raw_anchor={"search_event_sequence": 7, "match_index": 1},
        )
    except ContractError:
        stale_rejected = True
    return {
        "policy_version": ANCHORED_READ_POLICY,
        "resolved_path": resolved.path,
        "resolved_range": [resolved.start_line, resolved.end_line],
        "match_line": resolved.match_line,
        "selected_match_covered": resolved.start_line <= resolved.match_line <= resolved.end_line,
        "stale_diff_rejected": stale_rejected,
        "search_result_hash_bound": (
            resolved.search_result_hash == record.result_artifact.content_hash
        ),
    }


def _lifecycle_arguments() -> dict[str, Any]:
    arguments = _plan_arguments(co_located=False)
    mutation_span = arguments["causal_mechanism"]["mutation_site"]["source_span_id"]
    execution_span = arguments["readiness_assessment"]["basis_source_span_ids"][-1]
    arguments["lifecycle_state_transition"] = {
        "owners": [
            {
                "component": "runner",
                "owner_source_span_id": mutation_span,
                "responsibility": "Own the public lifecycle state transition.",
            },
            {
                "component": "lease",
                "owner_source_span_id": execution_span,
                "responsibility": "Preserve the public execution lease.",
            },
        ],
        "states": [
            {"component": "runner", "before": "active", "after": "interrupted"},
            {"component": "lease", "before": "held", "after": "released"},
        ],
        "transitions": [
            {
                "trigger": "The public interrupt path is observed.",
                "affected_components": ["runner", "lease"],
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


def _lifecycle_scenario() -> dict[str, Any]:
    catalog = _catalog_v4(source_count=2)
    self_directed = _request(catalog)
    trigger_bound = project_trigger_bound_self_directed_plan_request(
        self_directed.source_request.base_request
    )
    request = project_lifecycle_bound_plan_request(trigger_bound)
    arguments = _lifecycle_arguments()
    plan, closure, record = normalize_lifecycle_bound_plan(
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
    tampered = copy.deepcopy(arguments)
    tampered["lifecycle_state_transition"]["owners"][0]["owner_source_span_id"] = arguments[
        "readiness_assessment"
    ]["basis_source_span_ids"][-1]
    mutation_owner_missing_rejected = False
    try:
        normalize_lifecycle_bound_plan(
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
            raw_arguments=tampered,
        )
    except ContractError:
        mutation_owner_missing_rejected = True
    return {
        "policy_version": LIFECYCLE_PLAN_POLICY,
        "request_hash": request.content_hash,
        "plan_hash": plan.content_hash,
        "closure_hash": closure.content_hash,
        "record_hash": record.content_hash,
        "semantic_truth_verified": request.semantic_truth_verified,
        "public_current_diff_source_only": record.public_current_diff_source_only,
        "components": sorted(item.component for item in record.lifecycle.owners),
        "mutation_owner_missing_rejected": mutation_owner_missing_rejected,
        "atomic_postconditions": len(record.lifecycle.atomic_postconditions),
    }


def build_r21_reliability_qualification(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    scenarios = {
        "dedicated_generation_incomplete_recovery": _generation_scenario(),
        "compact_plan_admission_feedback": _feedback_scenario(),
        "anchored_source_read": _anchor_scenario(),
        "generic_lifecycle_state_transition": _lifecycle_scenario(),
    }
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 31, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "lean-v26-r21-public-agent-reliability-successor",
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V26,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V26,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V26,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V26,
            "generation_recovery_policy_version": GENERATION_INCOMPLETE_RECOVERY_POLICY,
            "feedback_policy_version": PLAN_ADMISSION_FEEDBACK_POLICY_V2,
            "anchor_policy_version": ANCHORED_READ_POLICY,
            "lifecycle_plan_policy_version": LIFECYCLE_PLAN_POLICY,
        },
        "scenarios": scenarios,
        "validated_test_surfaces": {
            "focused_unit": True,
            "real_shaped_mocked_runner": True,
            "generation_retry_restart": True,
            "plan_feedback_retry": True,
            "anchored_search_read_dispatch": True,
            "lifecycle_plan_recording": True,
            "v19_v25_regression": True,
            "repeated_public_failure_causal_reset_preserved": True,
            "second_incomplete_stops_before_third_provider_mock_dispatch": True,
        },
        "separate_public_check_proposal": _runner_continuity_identity(root),
        "source_files": [_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_inputs": [_immutable_identity(root, relative) for relative in IMMUTABLE_INPUTS],
        "evidence_boundary": {
            "public_synthetic_and_public_mock_inputs_only": True,
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
        "next_gate": "separate-lean-v26-activation-review-if-requested",
    }
    if (
        scenarios["dedicated_generation_incomplete_recovery"]["consumed_remaining"] != 0
        or scenarios["compact_plan_admission_feedback"]["latest_feedback_bytes"]
        > MAX_PLAN_FEEDBACK_BYTES
        or not scenarios["anchored_source_read"]["selected_match_covered"]
        or scenarios["generic_lifecycle_state_transition"]["semantic_truth_verified"] is not False
    ):
        raise ContractError("R21 reliability qualification criteria are incomplete")
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("R21 reliability qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_r21_reliability_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_r21_reliability_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


__all__ = [
    "IMMUTABLE_INPUTS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_r21_reliability_qualification",
    "materialize_r21_reliability_qualification",
    "qualification_bytes",
]
