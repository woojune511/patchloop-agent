"""Deterministic zero-call qualification for the public exploration gate."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.workflow_causal_plan_projection_activation import (
    project_activated_causal_plan_request,
    standard_plan_from_projected_causal_plan,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    _arguments,
    _catalog,
    _task,
)
from patchloop.agent.workflow_exploration_gate_successor import (
    EXPLORATION_GATE_POLICY,
    build_exploration_work_plan_binding,
    normalize_exploration_gated_causal_plan,
    project_exploration_gated_causal_plan_request,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-public-exploration-gate-successor-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-exploration-gate-public-qualification-20260827-v1.json"
)

SOURCE_FILES = (
    "patchloop/agent/workflow_exploration_gate_successor.py",
    "patchloop/agent/workflow_exploration_gate_successor_qualification.py",
    "scripts/build_lean_harness_exploration_gate_qualification.py",
    "tests/test_workflow_exploration_gate_successor.py",
    "tests/test_workflow_exploration_gate_successor_qualification.py",
)

IMMUTABLE_PUBLIC_INPUTS = {
    (
        "experiments/"
        "lean-harness-causal-plan-projection-activation-public-qualification-20260826-v1.json"
    ): {
        "bytes": 5_438,
        "file_sha256": "sha256:7f4b75a80c8085cdcf3beca1f9693077f97596ba719f3bdece5c9d5553cefa8b",
        "content_hash": "sha256:359b3bc8b2067bcd9b42f3c8dbbc5d8894d04a0611948c44a1d83d2995979754",
    },
    (
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-causal-plan-projection-ab-20260826-r14-"
        "workflow-diagnosis-v1.json"
    ): {
        "bytes": 16_969,
        "file_sha256": "sha256:42cedd83a425ef5beca6d0a597d7fcfe7d7243eb2890515ccc5386bca1d5cca5",
        "content_hash": "sha256:fa7497f94aa5854cb28b3ca48ca16d45d2d39db59b0c71da3efa2beec96e3695",
    },
    ("experiments/anyio-ordinary-failure-public-check-source-qualification-20260827-v1.json"): {
        "bytes": 6_970,
        "file_sha256": "sha256:f92590a5dd1ae8d5baf68541c3013dd24dd76bd43ab298b9299ed5f8e381b369",
        "content_hash": "sha256:dbd9b94fbe1ca3aadf34f59bd5045c05d234ac907c192368abef42a973ca4307",
    },
}


def _identity(root: Path, relative: str, *, canonical_document: bool) -> dict[str, Any]:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise ContractError(f"exploration-gate input is unavailable: {relative}")
    raw = path.read_bytes()
    result: dict[str, Any] = {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }
    if canonical_document:
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("exploration-gate input is not canonical JSON") from exc
        body = {key: value for key, value in document.items() if key != "content_hash"}
        if document.get("content_hash") != sha256_json(body):
            raise ContractError("exploration-gate input content hash differs")
        result["content_hash"] = document["content_hash"]
    return result


def _base_request():
    return project_activated_causal_plan_request(
        task=_task(),
        catalog=_catalog(include_failed_check=False),
        trigger="initial",
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
    )


def _exploration_state() -> dict[str, Any]:
    unknown = _arguments()["unknowns"][0]
    return {
        "boundary_coverage": {
            "ownership_boundary_span_ids": ["cspan:10:0"],
            "execution_boundary_span_ids": ["cspan:11:0"],
            "mutation_boundary_span_ids": ["cspan:10:0"],
        },
        "invariants": [
            {
                "subject": "Public lifecycle ownership",
                "claim": "The entry and handler ranges jointly own the transition.",
                "evidence_source_span_ids": ["cspan:10:0", "cspan:11:0"],
            }
        ],
        "preservation_obligations": [
            {
                "public_requirement": "Preserve the later public lifecycle behavior.",
                "expected_behavior": "The public checks continue in their registered order.",
                "evidence_source_span_ids": ["cspan:11:0"],
            }
        ],
        "unknown_dispositions": [
            {
                "question": unknown,
                "disposition": "non_blocking",
                "explanation": (
                    "The later observation does not alter this evidence-bound current transition."
                ),
                "evidence_source_span_ids": ["cspan:11:0"],
            }
        ],
        "open_blocking_unknowns": [],
    }


def _valid_arguments() -> dict[str, Any]:
    arguments = _arguments()
    arguments["exploration_state"] = _exploration_state()
    return arguments


def _normalize(arguments: dict[str, Any]):
    request = project_exploration_gated_causal_plan_request(_base_request())
    return normalize_exploration_gated_causal_plan(
        task=_task(),
        catalog=_catalog(include_failed_check=False),
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


def _reason_code(call: Callable[[], Any]) -> str:
    try:
        call()
    except ContractError as exc:
        reasons = exc.details.get("reason_codes")
        if isinstance(reasons, list) and len(reasons) == 1 and isinstance(reasons[0], str):
            return reasons[0]
        raise ContractError("exploration-gate rejection lacks one typed reason") from exc
    raise ContractError("exploration-gate negative scenario did not reject")


def _scenarios() -> dict[str, Any]:
    request = project_exploration_gated_causal_plan_request(_base_request())
    first_plan, first_receipt = _normalize(_valid_arguments())
    second_plan, second_receipt = _normalize(_valid_arguments())
    standard = standard_plan_from_projected_causal_plan(
        task=_task(),
        catalog=_catalog(include_failed_check=False),
        projected=first_plan,
    )
    binding = build_exploration_work_plan_binding(
        plan=standard,
        plan_event_sequence=30,
        projected=first_plan,
        receipt=first_receipt,
    )

    one_span = _valid_arguments()
    one_span["candidate_source_span_ids"] = ["cspan:10:0"]
    one_span["causal_mechanism"] = {
        "summary": "One source range appears to own the complete transition.",
        "causal_boundary": {
            "source_span_id": "cspan:10:0",
            "symbol": "entry",
            "observation": "The range receives the transition.",
            "relationship_to_next": "The same range commits it.",
        },
        "intermediate_steps": [],
        "mutation_site": {
            "source_span_id": "cspan:10:0",
            "symbol": "mutation",
            "observation": "The range commits the transition.",
        },
        "mutation_site_rationale": "The single range appears sufficient.",
        "expected_observable_effect": "The public transition changes.",
        "falsification_condition": "The same public failure remains.",
    }
    coverage = one_span["exploration_state"]["boundary_coverage"]
    for key in tuple(coverage):
        coverage[key] = ["cspan:10:0"]
    for item in (
        *one_span["exploration_state"]["invariants"],
        *one_span["exploration_state"]["preservation_obligations"],
        *one_span["exploration_state"]["unknown_dispositions"],
    ):
        item["evidence_source_span_ids"] = ["cspan:10:0"]

    missing_disposition = _valid_arguments()
    missing_disposition["exploration_state"]["unknown_dispositions"] = []
    open_blocker = _valid_arguments()
    open_blocker["exploration_state"]["open_blocking_unknowns"] = [
        "Which public source range owns the remaining transition?"
    ]
    unbound_mutation = _valid_arguments()
    unbound_mutation["exploration_state"]["boundary_coverage"]["mutation_boundary_span_ids"] = [
        "cspan:11:0"
    ]

    tampered_parameters = copy.deepcopy(request.parameters)
    tampered_parameters["properties"]["exploration_state"]["properties"]["open_blocking_unknowns"][
        "maxItems"
    ] = 1
    tampered = request.model_copy(update={"parameters": tampered_parameters})
    tamper_failed_closed = False
    try:
        normalize_exploration_gated_causal_plan(
            task=_task(),
            catalog=_catalog(include_failed_check=False),
            request_projection=tampered,
            trigger="initial",
            revision_index=0,
            parent_plan_hash=None,
            trigger_check_id=None,
            trigger_event_sequence=None,
            cross_reset_trigger=None,
            history=(),
            raw_arguments=_valid_arguments(),
        )
    except RecoveryError:
        tamper_failed_closed = True

    return {
        "dynamic_request": {
            "request_hash": request.content_hash,
            "parameter_schema_hash": request.parameter_schema_hash,
            "eligible_span_ids": [
                item.source_span_id
                for item in request.base_request.source_projection.source_span_catalog.spans
            ],
            "open_blocking_unknowns_max_items": request.parameters["properties"][
                "exploration_state"
            ]["properties"]["open_blocking_unknowns"]["maxItems"],
            "runtime_surface_activated": request.runtime_surface_activated,
        },
        "valid_closure": {
            "projected_plan_hash": first_plan.content_hash,
            "receipt_hash": first_receipt.content_hash,
            "active_plan_hash": standard.content_hash,
            "binding_hash": binding.content_hash,
            "distinct_source_coverage_keys": len(first_receipt.selected_source_coverage_keys),
            "declared_unknowns_closed": first_receipt.declared_unknowns_closed,
            "same_input_same_plan": first_plan == second_plan,
            "same_input_same_receipt": first_receipt == second_receipt,
        },
        "typed_rejections": {
            "one_range_for_all_boundaries": _reason_code(lambda: _normalize(one_span)),
            "missing_unknown_disposition": _reason_code(lambda: _normalize(missing_disposition)),
            "open_blocking_unknown": _reason_code(lambda: _normalize(open_blocker)),
            "unbound_mutation_boundary": _reason_code(lambda: _normalize(unbound_mutation)),
            "tampered_request_failed_closed": tamper_failed_closed,
        },
    }


def _r14_public_binding(root: Path) -> dict[str, Any]:
    relative = tuple(IMMUTABLE_PUBLIC_INPUTS)[1]
    diagnosis = json.loads((root / relative).read_bytes())
    boundary = diagnosis.get("evidence_boundary", {})
    rows = [row for row in diagnosis.get("rows", []) if row.get("variant") == "lean-harness-v18"]
    if (
        diagnosis.get("official") is not False
        or diagnosis.get("source_bundle", {}).get("execution_hash")
        != "sha256:f077496605d0776d7d2f2e677391cc2ae9135550077486126258429917986c1b"
        or len(rows) != 3
        or [row.get("first_mutation_evidence", {}).get("read_calls") for row in rows] != [3, 3, 1]
        or any(row.get("first_mutation_evidence", {}).get("check_calls") != 0 for row in rows)
        or sum(row.get("submission_completed") is True for row in rows) != 2
        or any(row.get("success_at_budget") is not False for row in rows)
        or any(
            boundary.get(key) is not False
            for key in (
                "private_task_spec_read",
                "hidden_evaluator_content_read",
                "reference_patch_read",
                "reasoning_text_read",
            )
        )
    ):
        raise ContractError("R14 public exploration tuple differs")
    return {
        "execution_hash": diagnosis["source_bundle"]["execution_hash"],
        "official": diagnosis["official"],
        "v18_rows": len(rows),
        "first_mutation_read_calls_in_order": [3, 3, 1],
        "first_mutation_check_calls_in_order": [0, 0, 0],
        "submissions": 2,
        "successes": 0,
        "raw_plan_payloads_replayed": False,
        "coding_quality_inferred": False,
        "r14_retry_allowed": False,
    }


def build_workflow_exploration_gate_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    public_inputs: list[dict[str, Any]] = []
    for relative, expected in IMMUTABLE_PUBLIC_INPUTS.items():
        observed = _identity(root, relative, canonical_document=True)
        if any(observed.get(key) != value for key, value in expected.items()):
            raise ContractError(f"immutable exploration-gate input differs: {relative}")
        public_inputs.append(observed)

    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "generic-public-boundary-and-unknown-closure-contract",
        "policy_version": EXPLORATION_GATE_POLICY,
        "runtime_version": None,
        "tool_schema_version": None,
        "context_policy_version": None,
        "runtime_surface_activated": False,
        "runtime_activation_authorized": False,
        "scenarios": _scenarios(),
        "r14_public_binding": _r14_public_binding(root),
        "source_files": [
            _identity(root, relative, canonical_document=False) for relative in SOURCE_FILES
        ],
        "immutable_public_inputs": public_inputs,
        "contract_limits": {
            "does_not_prove_semantic_correctness": True,
            "does_not_detect_omitted_unstated_unknowns": True,
            "does_not_require_more_reads_by_count_alone": True,
            "requires_two_distinct_boundary_coverage_keys": True,
            "requires_declared_unknown_dispositions": True,
            "requires_mutation_boundary_binding": True,
            "later_runtime_activation_required": True,
        },
        "evidence_boundary": {
            "public_synthetic_source_only": True,
            "r14_public_diagnosis_identity_and_aggregate_only": True,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "workspace_task_mutations": 0,
            "added_cost_usd": "0",
        },
        "paid_execution_authorized": False,
        "rapid_candidate_created": False,
        "quality_improvement_established": False,
        "runtime_behavior_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("exploration-gate qualification hash differs")
    return (canonical_json(value) + "\n").encode()


def materialize_workflow_exploration_gate_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_exploration_gate_successor_qualification(root)
    target = (root / QUALIFICATION_PATH).resolve()
    if not target.is_relative_to(root):
        raise ContractError("exploration-gate qualification output escapes repository")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_workflow_exploration_gate_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = (root / QUALIFICATION_PATH).resolve()
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("exploration-gate qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("exploration-gate qualification bytes differ")
    if value != build_workflow_exploration_gate_successor_qualification(root):
        raise ContractError("exploration-gate qualification source binding differs")
    return value


__all__ = [
    "IMMUTABLE_PUBLIC_INPUTS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_exploration_gate_successor_qualification",
    "load_workflow_exploration_gate_successor_qualification",
    "materialize_workflow_exploration_gate_successor_qualification",
    "qualification_bytes",
]
