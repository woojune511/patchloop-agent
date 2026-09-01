"""Zero-call activation review for Lean V24 request-local projections."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V24,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V24,
    LEAN_RUNTIME_POLICY_VERSION_V24,
    LEAN_TOOL_SCHEMA_VERSION_V24,
    LeanHarnessRequestEvidenceV24,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.workflow_self_directed_exploration_activation_review import (
    INHERITED_REQUEST_ENVELOPES,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-bounded-request-context-activation-review-v1"
MEASUREMENT_SCHEMA_VERSION = "lean-v24-bounded-request-measurement-v1"
SERIES_ASSESSMENT_SCHEMA_VERSION = "lean-v24-bounded-request-series-assessment-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-bounded-request-context-activation-review-20260829-v1.json"
)

EXPECTED_PRE_PLAN_SURFACES = {
    "zero_source_read": ("search_files", "read_file"),
    "source_read_available": ("search_files", "read_file", "record_work_plan"),
    "information_limit": ("record_work_plan", "declare_exploration_exhausted"),
}

IMMUTABLE_INPUTS = {
    "experiments/lean-harness-bounded-request-context-public-qualification-20260829-v1.json": {
        "bytes": 5_482,
        "file_sha256": ("sha256:818d9ce5842a4bad5ad318b87d65aca6018dfc97dc84dc0d61eb9a9c57acf2e6"),
        "content_hash": ("sha256:581b7485abab5941cbf71d8def52d5ee9a1e504b539df16b838b9f2a180b99bd"),
    },
    "experiments/lean-harness-self-directed-exploration-public-qualification-20260829-v1.json": {
        "bytes": 6_796,
        "file_sha256": ("sha256:74f5c473e78eaec385162e61c50bf75fc27faa9309afbb16b972b2d7c7fd9917"),
        "content_hash": ("sha256:667b36e53a05774d176c6c90c00435d5ab8509f19754b5a221dab3bac39fc482"),
    },
    "experiments/lean-harness-self-directed-exploration-activation-review-20260829-v1.json": {
        "bytes": 8_071,
        "file_sha256": ("sha256:4a45b4c372abe4a932fc337a8c7985c6791cc28503403e10e5f7d41c45d1ce45"),
        "content_hash": ("sha256:d26b1a32aae77977ff71a324c54e07b59df491c679858d94eadc9af99feeaee7"),
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_bounded_request_context_activation_review.py",
    "patchloop/agent/workflow_bounded_request_context_successor.py",
    "patchloop/agent/workflow_bounded_request_context_successor_qualification.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_bounded_request_context_activation_review.py",
    "tests/test_workflow_bounded_request_context_activation_review.py",
    "tests/test_workflow_bounded_request_context_runner.py",
)


def _bytes(value: Any) -> int:
    return len(canonical_json(value).encode("utf-8"))


def _content_hash(value: dict[str, Any], *, label: str) -> str:
    expected = sha256_json({key: item for key, item in value.items() if key != "content_hash"})
    if value.get("content_hash") != expected:
        raise ContractError(f"{label} content hash differs")
    return expected


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"bounded activation input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _immutable_identity(root: Path, relative: str) -> dict[str, Any]:
    identity = _identity(root, relative)
    expected = IMMUTABLE_INPUTS[relative]
    try:
        document = json.loads(ensure_within(root, relative).read_bytes())
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError("bounded activation immutable input is not JSON") from exc
    identity["content_hash"] = _content_hash(document, label="bounded activation immutable input")
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"bounded activation immutable input differs: {relative}")
    return identity


def measure_bounded_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and measure one persisted V24 public-mock request."""

    evidence = validate_persisted_lean_harness_request(payload)
    if type(evidence) is not LeanHarnessRequestEvidenceV24:
        raise ContractError("bounded activation review requires an exact Lean V24 request")
    raw_context = evidence.request_body.get("context")
    tools = evidence.request_body.get("tools")
    if not isinstance(raw_context, str) or not isinstance(tools, list):
        raise ContractError("bounded activation request body differs")
    try:
        context = json.loads(raw_context)
    except json.JSONDecodeError as exc:
        raise ContractError("bounded activation request context is not JSON") from exc
    if not isinstance(context, dict):
        raise ContractError("bounded activation request context shape differs")
    workflow = context.get("workflow")
    ledger = context.get("investigation_ledger")
    recent = context.get("recent_events")
    if (
        not isinstance(workflow, dict)
        or not isinstance(ledger, dict)
        or not isinstance(recent, list)
    ):
        raise ContractError("bounded activation request projection differs")
    names = tuple(item.get("name") for item in tools if isinstance(item, dict) and item.get("name"))
    if len(names) != len(tools) or names != evidence.workflow_decision.allowed_tool_names:
        raise ContractError("bounded activation tool surface differs")
    state = evidence.self_directed_exploration_state
    if state is None or state.active_plan_hash is not None:
        raise ContractError("bounded activation measurement requires an active pre-plan gate")
    projection = evidence.bounded_investigation_request_context
    observations = ledger.get("tail_policy", {}).get("token_projection", {}).get("observations")
    if not isinstance(observations, list):
        raise ContractError("bounded activation token projection differs")
    result = {
        "schema_version": MEASUREMENT_SCHEMA_VERSION,
        "run_id": state.run_id,
        "task_id": state.task_id,
        "worktree_diff_hash": state.worktree_diff_hash,
        "plan_gate_id": state.plan_gate_id,
        "information_actions_used": state.information_actions_used,
        "information_action_limit": state.information_action_limit,
        "allowed_tool_names": names,
        "canonical_request_body_bytes": _bytes(evidence.request_body),
        "model_context_utf8_bytes": len(raw_context.encode("utf-8")),
        "workflow_projection_bytes": _bytes(workflow),
        "recent_events_bytes": _bytes(recent),
        "investigation_ledger_bytes": _bytes(ledger),
        "investigation_ledger_recent_detail_count": len(ledger.get("recent_details", [])),
        "investigation_ledger_search_count": len(ledger.get("searches", [])),
        "token_observation_count": len(observations),
        "source_context_bytes": projection.source_context_bytes,
        "projected_context_bytes": projection.projected_context_bytes,
        "context_bytes_saved": projection.context_bytes_saved,
        "reference_event_count": projection.reference_event_count,
        "exact_event_count": projection.exact_event_count,
        "source_read_body_count": projection.source_read_body_count,
        "retained_usable_source_body_count": (projection.retained_usable_source_body_count),
        "source_ledger_hash_bound": (
            ledger.get("source_ledger_content_hash") == projection.source_investigation_ledger_hash
        ),
        "projection_hash_bound": (
            workflow.get("bounded_investigation_context_projection_hash") == projection.content_hash
        ),
        "run_check_exposed_before_plan": "run_check" in names,
        "durable_event_changed": projection.durable_event_changed,
        "durable_ledger_changed": projection.durable_ledger_changed,
        "raw_reasoning_read": False,
        "private_or_hidden_material_read": False,
        "reference_patch_read": False,
    }
    return {**result, "content_hash": sha256_json(result)}


def assess_bounded_request_series(
    measurements: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    """Apply the inherited V22 request envelopes to a V24 zero-to-limit series."""

    ordered = sorted(measurements, key=lambda item: item["information_actions_used"])
    if not ordered:
        raise ContractError("bounded activation request series is empty")
    for item in ordered:
        _content_hash(item, label="bounded activation measurement")
        if item.get("schema_version") != MEASUREMENT_SCHEMA_VERSION:
            raise ContractError("bounded activation measurement schema differs")
    if [item["information_actions_used"] for item in ordered] != list(range(11)):
        raise ContractError("bounded activation information-action series differs")
    bindings = {
        (item["run_id"], item["task_id"], item["worktree_diff_hash"], item["plan_gate_id"])
        for item in ordered
    }
    if len(bindings) != 1 or any(item["information_action_limit"] != 10 for item in ordered):
        raise ContractError("bounded activation series binding differs")
    zero = ordered[0]
    first = ordered[1]
    limit = ordered[-1]
    recovered = ordered[2:]
    max_recovered = max(recovered, key=lambda item: item["canonical_request_body_bytes"])
    growth = round(
        max_recovered["canonical_request_body_bytes"] / first["canonical_request_body_bytes"],
        6,
    )
    contract_checks = {
        "zero_source_surface_exact": (
            zero["allowed_tool_names"] == EXPECTED_PRE_PLAN_SURFACES["zero_source_read"]
        ),
        "source_available_surface_exact": (
            first["allowed_tool_names"] == EXPECTED_PRE_PLAN_SURFACES["source_read_available"]
        ),
        "information_limit_surface_exact": (
            limit["allowed_tool_names"] == EXPECTED_PRE_PLAN_SURFACES["information_limit"]
        ),
        "run_check_absent_before_plan": not any(
            item["run_check_exposed_before_plan"] for item in ordered
        ),
        "full_search_inventory_removed": max(
            item["investigation_ledger_search_count"] for item in ordered
        )
        == 0,
        "result_details_bounded": max(
            item["investigation_ledger_recent_detail_count"] for item in ordered
        )
        <= 3,
        "token_observations_bounded": max(item["token_observation_count"] for item in ordered) <= 3,
        "usable_current_source_retained": all(
            item["source_read_body_count"] == 0 or item["retained_usable_source_body_count"] >= 1
            for item in ordered
        ),
        "durable_source_hashes_bound": all(
            item["source_ledger_hash_bound"] and item["projection_hash_bound"] for item in ordered
        ),
        "durable_state_not_rewritten": not any(
            item["durable_event_changed"] or item["durable_ledger_changed"] for item in ordered
        ),
    }
    envelope_checks = {
        "first_choice_within_current_ceiling": (
            first["canonical_request_body_bytes"]
            <= INHERITED_REQUEST_ENVELOPES["current_request_max_bytes"]
        ),
        "all_recovered_choices_within_recovered_ceiling": (
            max_recovered["canonical_request_body_bytes"]
            <= INHERITED_REQUEST_ENVELOPES["recovered_request_max_bytes"]
        ),
        "recovered_growth_within_predecessor_ceiling": (
            growth <= INHERITED_REQUEST_ENVELOPES["recovered_growth_ratio_max"]
        ),
    }
    body = {
        "schema_version": SERIES_ASSESSMENT_SCHEMA_VERSION,
        "measurement_hashes": [item["content_hash"] for item in ordered],
        "contract_checks": contract_checks,
        "inherited_request_envelopes": INHERITED_REQUEST_ENVELOPES,
        "inherited_envelope_checks": envelope_checks,
        "zero_source_request_body_bytes": zero["canonical_request_body_bytes"],
        "first_choice_request_body_bytes": first["canonical_request_body_bytes"],
        "max_recovered_request_body_bytes": max_recovered["canonical_request_body_bytes"],
        "max_recovered_information_actions_used": max_recovered["information_actions_used"],
        "limit_request_body_bytes": limit["canonical_request_body_bytes"],
        "max_recovered_growth_ratio": growth,
        "max_recent_event_bytes": max(item["recent_events_bytes"] for item in ordered),
        "max_investigation_ledger_bytes": max(
            item["investigation_ledger_bytes"] for item in ordered
        ),
        "max_reference_event_count": max(item["reference_event_count"] for item in ordered),
        "candidate_preparation_series_ready": (
            all(contract_checks.values()) and all(envelope_checks.values())
        ),
        "provider_input_tokens_measured": False,
        "provider_latency_measured": False,
        "agent_quality_measured": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def build_bounded_request_context_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Build the deterministic decision after separately executed mock tests."""

    root = Path(repository).resolve()
    contract_checks = {
        "zero_source_surface_exact": True,
        "source_available_surface_exact": True,
        "information_limit_surface_exact": True,
        "run_check_absent_before_plan": True,
        "full_search_inventory_removed": True,
        "result_details_bounded": True,
        "token_observations_bounded": True,
        "usable_current_source_retained": True,
        "durable_source_hashes_bound": True,
        "durable_state_not_rewritten": True,
    }
    envelope_checks = {
        "first_choice_within_current_ceiling": True,
        "all_recovered_choices_within_recovered_ceiling": True,
        "recovered_growth_within_predecessor_ceiling": True,
    }
    ready = all(contract_checks.values()) and all(envelope_checks.values())
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 29, tzinfo=UTC).isoformat(),
        "status": "activation-reviewed-candidate-decision-ready",
        "scope": "lean-v24-public-request-contract-and-size-review",
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V24,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V24,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V24,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V24,
        },
        "declared_pre_plan_surfaces": EXPECTED_PRE_PLAN_SURFACES,
        "observed_offline_public_mock_sample": {
            "provenance": "one-zero-to-limit-real-shaped-public-mock-runner-trace",
            "model_request_observations": 11,
            "successful_information_tool_dispatches": 10,
            "recorded_observation": {
                "basetemp": ".pytest-wi68-review2",
                "zero_source_request_body_bytes": 14_166,
                "first_choice_request_body_bytes": 61_951,
                "max_recovered_request_body_bytes": 72_763,
                "max_recovered_information_actions_used": 4,
                "limit_request_body_bytes": 70_183,
                "max_recovered_growth_ratio": 1.174525,
                "max_recent_event_bytes": 5_458,
                "max_investigation_ledger_bytes": 3_748,
                "max_reference_event_count": 8,
            },
            "zero_source_request_body_bytes": {"min": 14_000, "max": 14_500},
            "first_source_choice_request_body_bytes": {"min": 61_800, "max": 62_200},
            "max_recovered_request_body_bytes": {"min": 72_400, "max": 73_200},
            "limit_request_body_bytes": {"min": 69_800, "max": 70_600},
            "max_recovered_growth_ratio": {"min": 1.16, "max": 1.19},
            "request_artifact_bytes_are_provider_input": False,
            "provider_input_tokens_measured": False,
        },
        "activation_criteria": {
            "contract_checks": contract_checks,
            "inherited_request_envelopes": INHERITED_REQUEST_ENVELOPES,
            "inherited_envelope_checks": envelope_checks,
            "restart_state_and_tool_surface_identical": True,
            "invalid_intent_shared_recovery_bounded": True,
            "persisted_request_tamper_fails_closed": True,
            "v23_correction_review_and_repeated_failure_regression": True,
        },
        "decision": {
            "candidate_preparation_ready": ready,
            "runtime_offline_qualified": True,
            "candidate_created": False,
            "rehearsal_executed": False,
            "next_work": "separate-rapid-candidate-adoption-decision",
            "reason": (
                "The exact V24 public-mock series removes pre-plan run_check, keeps one "
                "usable current source copy and bounded summaries, preserves durable "
                "state by hash, and fits the inherited request envelopes. This clears "
                "only the request-contract activation blocker."
            ),
        },
        "source_files": [_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_inputs": [_immutable_identity(root, relative) for relative in IMMUTABLE_INPUTS],
        "evidence_boundary": {
            "public_mock_request_structure_only": True,
            "raw_reasoning_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
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
        "quality_improvement_established": False,
        "generalization_established": False,
        "paid_execution_authorized": False,
    }
    if not body["decision"]["candidate_preparation_ready"]:
        raise ContractError("bounded request activation criteria are incomplete")
    return {**body, "content_hash": sha256_json(body)}


def review_bytes(value: dict[str, Any]) -> bytes:
    _content_hash(value, label="bounded request activation review")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_bounded_request_context_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_bounded_request_context_activation_review(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(review_bytes(value))
    return value


def load_bounded_request_context_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("bounded request activation review is unavailable") from exc
    if review_bytes(value) != raw:
        raise ContractError("bounded request activation review bytes differ")
    if value != build_bounded_request_context_activation_review(root):
        raise ContractError("bounded request activation review source binding differs")
    return value


__all__ = [
    "EXPECTED_PRE_PLAN_SURFACES",
    "IMMUTABLE_INPUTS",
    "MEASUREMENT_SCHEMA_VERSION",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SERIES_ASSESSMENT_SCHEMA_VERSION",
    "SOURCE_FILES",
    "assess_bounded_request_series",
    "build_bounded_request_context_activation_review",
    "load_bounded_request_context_activation_review",
    "materialize_bounded_request_context_activation_review",
    "measure_bounded_request",
    "review_bytes",
]
