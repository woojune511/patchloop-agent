"""Deterministic zero-call qualification for the opt-in Lean V19 gate."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V19,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V19,
    LEAN_RUNTIME_POLICY_VERSION_V19,
    LEAN_TOOL_SCHEMA_VERSION_V19,
)
from patchloop.agent.tools import TOOL_SCHEMAS_V23
from patchloop.agent.workflow_causal_plan_projection_activation import (
    standard_plan_from_projected_causal_plan,
)
from patchloop.agent.workflow_causal_plan_projection_activation_qualification import (
    _catalog_v2,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    EMPTY_DIFF,
    RUN_ID,
    RUNTIME_PATH,
    _read,
    _support,
    _task,
)
from patchloop.agent.workflow_exploration_gate_activation import (
    EXPLORATION_GATE_ACTIVATION_POLICY,
    exploration_binding_for_hash,
    exploration_closure_event_payload,
    normalize_activated_exploration_plan,
    project_exploration_readiness_decision,
    project_exploration_workflow_tool_surface,
)
from patchloop.agent.workflow_exploration_gate_successor import (
    build_exploration_work_plan_binding,
)
from patchloop.agent.workflow_exploration_gate_successor_qualification import (
    QUALIFICATION_PATH as SOURCE_QUALIFICATION_PATH,
)
from patchloop.agent.workflow_semantic_progress_successor import WorkflowDecisionV3
from patchloop.agent.workflow_successor_v2 import EligiblePlanEvidenceCatalogV2
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError
from patchloop.util import (
    canonical_json,
    ensure_within,
    sha256_bytes,
    sha256_json,
)

SCHEMA_VERSION = "lean-exploration-gate-activation-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-exploration-gate-activation-public-qualification-20260827-v1.json"
)

IMMUTABLE_PREDECESSORS = {
    SOURCE_QUALIFICATION_PATH.as_posix(): {
        "bytes": 4_742,
        "file_sha256": ("sha256:9fe9342514fa58f995e6c261370b9fedc0a3063999ab43e7fba8983da7bafc09"),
        "content_hash": ("sha256:bb2891ea57635a2f51012320ee563d4d2d9d9496daede590c2d48ba9bcc605b2"),
    },
    (
        "experiments/"
        "lean-harness-causal-plan-projection-activation-public-qualification-20260826-v1.json"
    ): {
        "bytes": 5_438,
        "file_sha256": ("sha256:7f4b75a80c8085cdcf3beca1f9693077f97596ba719f3bdece5c9d5553cefa8b"),
        "content_hash": ("sha256:359b3bc8b2067bcd9b42f3c8dbbc5d8894d04a0611948c44a1d83d2995979754"),
    },
    (
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-causal-plan-projection-ab-20260826-r14-"
        "workflow-diagnosis-v1.json"
    ): {
        "bytes": 16_969,
        "file_sha256": ("sha256:42cedd83a425ef5beca6d0a597d7fcfe7d7243eb2890515ccc5386bca1d5cca5"),
        "content_hash": ("sha256:fa7497f94aa5854cb28b3ca48ca16d45d2d39db59b0c71da3efa2beec96e3695"),
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_exploration_gate_activation.py",
    "patchloop/agent/workflow_exploration_gate_activation_qualification.py",
    "patchloop/agent/workflow_exploration_gate_successor.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/runner.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_exploration_gate_activation_qualification.py",
    "tests/test_workflow_exploration_gate_activation.py",
    "tests/test_workflow_exploration_gate_activation_qualification.py",
    "tests/test_workflow_successor_v2_runner.py",
)


def _identity(root: Path, relative: str, *, canonical_document: bool) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"exploration activation input is unavailable: {relative}")
    raw = selected.read_bytes()
    value: dict[str, Any] = {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }
    if canonical_document:
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("exploration activation predecessor is not JSON") from exc
        content_hash = document.get("content_hash")
        if content_hash != sha256_json(
            {key: item for key, item in document.items() if key != "content_hash"}
        ):
            raise ContractError("exploration activation predecessor content hash differs")
        value["content_hash"] = content_hash
    return value


def _single_range_catalog() -> EligiblePlanEvidenceCatalogV2:
    task = _task()
    items = (
        _read(20, RUNTIME_PATH, ((20, 57),)),
        _support(24),
    )
    body = {
        "schema_version": "eligible-plan-evidence-catalog-v2",
        "run_id": RUN_ID,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": sha256_json(task.model_dump(mode="json")),
        "worktree_diff_hash": EMPTY_DIFF,
        "model_visible_context_hash": "sha256:" + "d" * 64,
        "model_visible_recent_event_sequences": tuple(
            item.canonical_event_sequence for item in items
        ),
        "items": tuple(item.model_dump(mode="python") for item in items),
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
        "required_trigger_status": "not_required",
        "required_trigger_event_sequence": None,
        "required_trigger_evidence_id": None,
        "model_visible_pinned_event_sequences": (),
        "unavailable_reason": None,
    }
    return EligiblePlanEvidenceCatalogV2.model_validate({**body, "content_hash": sha256_json(body)})


def _initial_decision() -> WorkflowDecisionV3:
    body = {
        "schema_version": "lean-workflow-decision-v3",
        "runtime_policy_version": "lean-harness-v15",
        "policy_version": "public-failure-signature-no-progress-reset-v1",
        "target": "pre-mutation-exploration",
        "current_diff_hash": EMPTY_DIFF,
        "expected_check_id": None,
        "allowed_tool_names": (
            "search_files",
            "read_file",
            "run_check",
            "record_work_plan",
        ),
        "information_actions_in_episode": 0,
        "fresh_current_read": True,
        "corrective_mutations_for_check": 0,
        "review_corrections_used": 0,
        "pre_mutation_actions_used": 1,
        "active_plan_hash": None,
        "plan_gate_id": None,
        "plan_admission_recovery_used": False,
        "plan_admission_recovery_remaining": 1,
        "required_trigger_evidence_id": None,
        "revision_trigger": None,
        "terminal_reason": None,
        "configured_max_output_tokens": 12_288,
        "effective_max_output_tokens": 8_192,
        "reasoning_effort": "medium",
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "provider_calls_authorized": False,
        "semantic_progress_state_hash": None,
        "semantic_reset_required": False,
        "required_prior_hypothesis_disposition": None,
    }
    return WorkflowDecisionV3.model_validate({**body, "content_hash": sha256_json(body)})


def _arguments() -> dict[str, Any]:
    return {
        "hypothesis": "A bounded public source path owns the visible transition.",
        "supporting_evidence_ids": ["pev:24"],
        "candidate_source_span_ids": ["cspan:21:0"],
        "intended_change": "Adjust only the evidence-bound mutation boundary.",
        "expected_behavior": "The public targeted behavior is preserved.",
        "unknowns": [],
        "prior_hypothesis_disposition": None,
        "causal_mechanism": {
            "summary": "The public entry reaches an execution boundary and mutation site.",
            "causal_boundary": {
                "source_span_id": "cspan:20:0",
                "symbol": "entry_boundary",
                "observation": "This range owns the public entry transition.",
                "relationship_to_next": "The transition reaches the execution boundary.",
            },
            "intermediate_steps": [
                {
                    "source_span_id": "cspan:20:1",
                    "symbol": "execution_boundary",
                    "observation": "This range executes the public transition.",
                    "relationship_to_next": "Execution reaches the mutation site.",
                }
            ],
            "mutation_site": {
                "source_span_id": "cspan:21:0",
                "symbol": "mutation_boundary",
                "observation": "This range commits the visible state.",
            },
            "mutation_site_rationale": "The final boundary is the minimal edit site.",
            "expected_observable_effect": "The targeted check observes the preserved state.",
            "falsification_condition": "The same public failure remains after the edit.",
        },
        "exploration_state": {
            "boundary_coverage": {
                "ownership_boundary_span_ids": ["cspan:20:0"],
                "execution_boundary_span_ids": ["cspan:20:1"],
                "mutation_boundary_span_ids": ["cspan:21:0"],
            },
            "invariants": [
                {
                    "subject": "Public transition ownership",
                    "claim": "Ownership and execution precede the mutation boundary.",
                    "evidence_source_span_ids": ["cspan:20:0", "cspan:20:1"],
                }
            ],
            "preservation_obligations": [
                {
                    "public_requirement": "Preserve the ordinary execution path.",
                    "expected_behavior": "The visible transition remains ordered.",
                    "evidence_source_span_ids": ["cspan:20:1", "cspan:21:0"],
                }
            ],
            "unknown_dispositions": [],
            "open_blocking_unknowns": [],
        },
    }


def _event(sequence: int, event_type: EventType, payload: dict[str, Any]) -> RunEvent:
    return RunEvent(
        event_id=f"evt_exploration_activation_{sequence}",
        run_id=RUN_ID,
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 27, tzinfo=UTC),
        actor="qualification",
        correlation_id=None,
        payload=payload,
    )


def _reason_code(callable_: Any) -> str:
    try:
        callable_()
    except ContractError as exc:
        codes = exc.details.get("reason_codes", [])
        if isinstance(codes, list) and len(codes) == 1 and isinstance(codes[0], str):
            return codes[0]
        raise ContractError("exploration activation rejection code differs") from exc
    raise ContractError("exploration activation expected rejection")


def _scenarios() -> dict[str, Any]:
    task = _task()
    decision = _initial_decision()
    single_catalog = _single_range_catalog()
    full_catalog = _catalog_v2()
    schemas = tuple(copy.deepcopy(item) for item in TOOL_SCHEMAS_V23)

    restricted = project_exploration_readiness_decision(
        task=task,
        decision=decision,
        catalog=single_catalog,
        source_tool_schemas=schemas,
        cross_reset_trigger=None,
    )
    restricted_surface, restricted_request = project_exploration_workflow_tool_surface(
        task=task,
        decision=restricted,
        catalog=single_catalog,
        source_tool_schemas=schemas,
        cross_reset_trigger=None,
    )
    ready = project_exploration_readiness_decision(
        task=task,
        decision=decision,
        catalog=full_catalog,
        source_tool_schemas=schemas,
        cross_reset_trigger=None,
    )
    ready_surface, request = project_exploration_workflow_tool_surface(
        task=task,
        decision=ready,
        catalog=full_catalog,
        source_tool_schemas=schemas,
        cross_reset_trigger=None,
    )
    if request is None:
        raise ContractError("exploration activation did not expose its qualified request")

    arguments = _arguments()
    projected, receipt = normalize_activated_exploration_plan(
        task=task,
        catalog=full_catalog,
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
    plan = standard_plan_from_projected_causal_plan(
        task=task,
        catalog=full_catalog,
        projected=projected,
    )
    binding = build_exploration_work_plan_binding(
        plan=plan,
        plan_event_sequence=60,
        projected=projected,
        receipt=receipt,
    )
    plan_event = _event(
        60,
        EventType.PLAN_RECORDED,
        {
            "plan_hash": plan.content_hash,
            "revision_index": plan.revision_index,
            "parent_plan_hash": plan.parent_plan_hash,
            "trigger": plan.trigger,
            "exploration_closure_receipt_hash": receipt.content_hash,
            "activated_exploration_request_hash": request.content_hash,
        },
    )
    closure_event = _event(
        61,
        EventType.EXPLORATION_CLOSURE_RECORDED,
        exploration_closure_event_payload(binding=binding, request_projection=request),
    )
    recovered = exploration_binding_for_hash(
        run_id=RUN_ID,
        plan_hash=plan.content_hash,
        events=(plan_event, closure_event),
    )
    blocked_arguments = copy.deepcopy(arguments)
    blocked_arguments["exploration_state"]["open_blocking_unknowns"] = [
        "The mutation owner is unresolved."
    ]

    return {
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V19,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V19,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V19,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V19,
            "activation_policy_version": EXPLORATION_GATE_ACTIVATION_POLICY,
        },
        "bounded_readiness": {
            "single_range_target": restricted.target,
            "single_range_tools": list(restricted_surface.selected_tool_names),
            "single_range_plan_request": restricted_request is not None,
            "ready_target_preserved": ready.target == decision.target,
            "ready_plan_schema_present": any(
                item.get("name") == "record_work_plan"
                for item in ready_surface.selected_tool_schemas
            ),
            "minimum_distinct_coverage_keys": (
                request.source_request.minimum_distinct_source_coverage_keys
            ),
        },
        "dynamic_plan_surface": {
            "runtime_surface_activated": request.runtime_surface_activated,
            "source_surface_remains_unactivated": (
                not request.source_request.runtime_surface_activated
            ),
            "request_parameters_match_surface": next(
                item["parameters"]
                for item in ready_surface.selected_tool_schemas
                if item.get("name") == "record_work_plan"
            )
            == request.parameters,
            "open_blocker_rejection": _reason_code(
                lambda: normalize_activated_exploration_plan(
                    task=task,
                    catalog=full_catalog,
                    request_projection=request,
                    trigger="initial",
                    revision_index=0,
                    parent_plan_hash=None,
                    trigger_check_id=None,
                    trigger_event_sequence=None,
                    cross_reset_trigger=None,
                    history=(),
                    raw_arguments=blocked_arguments,
                )
            ),
        },
        "durable_closure": {
            "binding_round_trip_exact": recovered == binding,
            "plan_hash": plan.content_hash,
            "receipt_hash": receipt.content_hash,
            "selected_source_coverage_key_count": len(receipt.selected_source_coverage_keys),
            "closure_event_type": EventType.EXPLORATION_CLOSURE_RECORDED.value,
        },
        "preserved_limits": {
            "work_plan_admission_recovery_slots": 1,
            "third_dispatch_after_second_rejection": False,
            "mutation_without_closure": False,
            "targeted_first_changed": False,
            "v18_runtime_modified": False,
        },
    }


def build_workflow_exploration_gate_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    predecessors: list[dict[str, Any]] = []
    for relative, expected in IMMUTABLE_PREDECESSORS.items():
        observed = _identity(root, relative, canonical_document=True)
        if any(observed.get(key) != value for key, value in expected.items()):
            raise ContractError(f"immutable exploration predecessor differs: {relative}")
        predecessors.append(observed)

    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "lean-v19-public-exploration-closure-activation",
        "scenarios": _scenarios(),
        "source_files": [
            _identity(root, relative, canonical_document=False) for relative in SOURCE_FILES
        ],
        "immutable_predecessors": predecessors,
        "preservation_boundary": {
            "lean_v18_behavior_modified": False,
            "r14_retry_allowed": False,
            "source_contract_requalified": False,
            "activation_is_opt_in": True,
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
        "runtime_surface_activated": True,
        "rapid_candidate_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("exploration activation qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_exploration_gate_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_exploration_gate_activation_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_workflow_exploration_gate_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("exploration activation qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("exploration activation qualification bytes differ")
    if value != build_workflow_exploration_gate_activation_qualification(root):
        raise ContractError("exploration activation qualification source binding differs")
    return value


__all__ = [
    "IMMUTABLE_PREDECESSORS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_exploration_gate_activation_qualification",
    "load_workflow_exploration_gate_activation_qualification",
    "materialize_workflow_exploration_gate_activation_qualification",
    "qualification_bytes",
]
