"""Offline activation review for Lean V23 self-directed exploration.

The review reads only persisted public-mock request artifacts.  It does not
alter the runtime, create a Rapid candidate, or claim that canonical JSON byte
counts are provider tokens, latency, cost, or agent-quality evidence.
"""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V23,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V23,
    LEAN_RUNTIME_POLICY_VERSION_V23,
    LEAN_SELF_DIRECTED_EXPLORATION_POLICY_VERSION_V23,
    LEAN_TOOL_SCHEMA_VERSION_V23,
    LeanHarnessRequestEvidenceV23,
    validate_persisted_lean_harness_request,
)
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-self-directed-exploration-activation-review-v1"
MEASUREMENT_SCHEMA_VERSION = "lean-v23-self-directed-request-measurement-v1"
SERIES_ASSESSMENT_SCHEMA_VERSION = "lean-v23-self-directed-request-series-assessment-v1"
RECOVERY_AUDIT_SCHEMA_VERSION = "lean-v23-self-directed-recovery-audit-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-self-directed-exploration-activation-review-20260829-v1.json"
)

# These are the already-fixed V22 activation envelopes.  V23 did not receive a
# post-observation relaxed envelope, so the review reports compatibility with
# the predecessor limits instead of inventing a larger passing threshold.
INHERITED_REQUEST_ENVELOPES = {
    "current_request_max_bytes": 65_000,
    "recovered_request_max_bytes": 90_000,
    "recovered_growth_ratio_max": 1.25,
}

EXPECTED_PRE_PLAN_SURFACES = {
    "zero_source_read": ("search_files", "read_file"),
    "source_read_available": ("search_files", "read_file", "record_work_plan"),
    "information_limit": ("record_work_plan", "declare_exploration_exhausted"),
}

IMMUTABLE_INPUTS = {
    "experiments/lean-harness-self-directed-exploration-public-qualification-20260829-v1.json": {
        "bytes": 6_796,
        "file_sha256": ("sha256:74f5c473e78eaec385162e61c50bf75fc27faa9309afbb16b972b2d7c7fd9917"),
        "content_hash": ("sha256:667b36e53a05774d176c6c90c00435d5ab8509f19754b5a221dab3bac39fc482"),
    },
    "experiments/lean-harness-plan-admission-feedback-activation-review-20260827-v1.json": {
        "bytes": 6_574,
        "file_sha256": ("sha256:897204b88e598db7ecb156922f1a98659e49e60d93a273139e977d189e9270d2"),
        "content_hash": ("sha256:d1194a9cbdc55cbe9b07c813ea032b0ecae6cf28fe5b55fea03c6e5b9871a18d"),
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_self_directed_exploration_activation_review.py",
    "patchloop/agent/workflow_self_directed_exploration_successor.py",
    "patchloop/agent/workflow_self_directed_exploration_successor_qualification.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/context.py",
    "patchloop/agent/investigation.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_self_directed_exploration_activation_review.py",
    "tests/test_workflow_self_directed_exploration_activation_review.py",
    "tests/test_workflow_self_directed_exploration_runner.py",
)


def _bytes(value: Any) -> int:
    return len(canonical_json(value).encode("utf-8"))


def _content_hash(value: dict[str, Any], *, label: str) -> str:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    expected = sha256_json(body)
    if value.get("content_hash") != expected:
        raise ContractError(f"{label} content hash differs")
    return expected


def _request_context(evidence: LeanHarnessRequestEvidenceV23) -> dict[str, Any]:
    raw = evidence.request_body.get("context")
    if not isinstance(raw, str):
        raise ContractError("activation review request lacks string context")
    try:
        context = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ContractError("activation review request context is not JSON") from exc
    if not isinstance(context, dict):
        raise ContractError("activation review request context differs")
    if not isinstance(context.get("workflow"), dict):
        raise ContractError("activation review workflow projection differs")
    if not isinstance(context.get("investigation_ledger"), dict):
        raise ContractError("activation review investigation ledger differs")
    if not isinstance(context.get("recent_events"), list):
        raise ContractError("activation review recent-event projection differs")
    return context


def _tool_names(body: dict[str, Any]) -> tuple[str, ...]:
    tools = body.get("tools")
    if not isinstance(tools, list):
        raise ContractError("activation review request tool schema differs")
    names: list[str] = []
    for item in tools:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ContractError("activation review request tool name differs")
        names.append(item["name"])
    return tuple(names)


def measure_self_directed_exploration_request(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Measure one persisted V23 public-mock request and verify its bindings."""

    evidence = validate_persisted_lean_harness_request(payload)
    if not isinstance(evidence, LeanHarnessRequestEvidenceV23):
        raise ContractError("activation review requires a Lean V23 request")
    body = evidence.request_body
    context = _request_context(evidence)
    workflow = context["workflow"]
    ledger = context["investigation_ledger"]
    tool_names = _tool_names(body)
    if tool_names != evidence.workflow_decision.allowed_tool_names:
        raise ContractError("activation review tool surface binding differs")

    state = evidence.self_directed_exploration_state
    projected_state = workflow.get("self_directed_exploration_state")
    if state is None:
        raise ContractError("activation review requires an active self-directed gate")
    expected_state = state.model_dump(mode="json")
    if projected_state != expected_state:
        raise ContractError("activation review self-directed state binding differs")

    details = ledger.get("recent_details")
    searches = ledger.get("searches")
    reads = ledger.get("reads")
    omitted = ledger.get("omitted")
    if not (
        isinstance(details, list)
        and isinstance(searches, list)
        and isinstance(reads, list)
        and isinstance(omitted, dict)
    ):
        raise ContractError("activation review investigation ledger inventory differs")
    raw_source_values = [
        item["content"]
        for item in details
        if isinstance(item, dict) and isinstance(item.get("content"), str)
    ]

    information_actions_used = state.information_actions_used
    information_action_limit = state.information_action_limit
    source_span_count = len(state.source_spans)
    coverage_count = len(state.distinct_source_coverage_keys)
    recent_card_count = len(state.recent_investigations)
    omitted_card_count = state.omitted_investigation_count
    available_choices = state.available_choices
    run_id = state.run_id
    task_id = state.task_id
    worktree_diff_hash = state.worktree_diff_hash
    plan_gate_id = state.plan_gate_id

    result = {
        "schema_version": MEASUREMENT_SCHEMA_VERSION,
        "request_evidence_schema": evidence.schema_version,
        "run_id": run_id,
        "task_id": task_id,
        "worktree_diff_hash": worktree_diff_hash,
        "plan_gate_id": plan_gate_id,
        "readiness_source": evidence.plan_gate_readiness_source,
        "input_count_method": evidence.input_count_method,
        "allowed_tool_names": tool_names,
        "canonical_request_body_bytes": _bytes(body),
        "model_context_utf8_bytes": len(body["context"].encode("utf-8")),
        "workflow_projection_bytes": _bytes(workflow),
        "recent_events_bytes": _bytes(context["recent_events"]),
        "tool_schema_bytes": _bytes(body.get("tools", [])),
        "self_directed_state_bytes": _bytes(projected_state),
        "information_actions_used": information_actions_used,
        "information_action_limit": information_action_limit,
        "source_span_count": source_span_count,
        "distinct_source_coverage_count": coverage_count,
        "recent_investigation_card_count": recent_card_count,
        "omitted_investigation_card_count": omitted_card_count,
        "available_choices": available_choices,
        "investigation_ledger_bytes": _bytes(ledger),
        "investigation_ledger_read_count": len(reads),
        "investigation_ledger_search_count": len(searches),
        "investigation_ledger_recent_detail_count": len(details),
        "investigation_ledger_omitted": omitted,
        "model_visible_raw_source_content_count": len(raw_source_values),
        "model_visible_raw_source_content_utf8_bytes": sum(
            len(item.encode("utf-8")) for item in raw_source_values
        ),
        "run_check_exposed_before_plan": (
            state.active_plan_hash is None and "run_check" in tool_names
        ),
        "raw_reasoning_read": False,
        "private_task_material_read": False,
        "hidden_evaluator_material_read": False,
        "reference_patch_read": False,
    }
    return {**result, "content_hash": sha256_json(result)}


def assess_self_directed_exploration_request_series(
    measurements: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    """Assess one zero-to-limit V23 exploration request series."""

    ordered = sorted(measurements, key=lambda item: item["information_actions_used"])
    if not ordered:
        raise ContractError("activation review request series is empty")
    for item in ordered:
        _content_hash(item, label="activation review request measurement")
        if item.get("schema_version") != MEASUREMENT_SCHEMA_VERSION:
            raise ContractError("activation review request measurement schema differs")
    bindings = {
        (item["run_id"], item["task_id"], item["worktree_diff_hash"], item["plan_gate_id"])
        for item in ordered
    }
    if len(bindings) != 1:
        raise ContractError("activation review request series binding differs")
    if [item["information_actions_used"] for item in ordered] != list(range(11)):
        raise ContractError("activation review request series action inventory differs")
    if any(item["information_action_limit"] != 10 for item in ordered):
        raise ContractError("activation review information-action limit differs")

    zero = ordered[0]
    first = ordered[1]
    limit = ordered[-1]
    recovered = ordered[2:]
    max_recovered = max(recovered, key=lambda item: item["canonical_request_body_bytes"])
    growth_ratio = round(
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
        "run_check_absent_before_plan": not any(
            item["run_check_exposed_before_plan"] for item in ordered
        ),
        "information_limit_surface_exact": (
            limit["allowed_tool_names"] == EXPECTED_PRE_PLAN_SURFACES["information_limit"]
        ),
        "recent_investigation_cards_bounded_to_three": (
            max(item["recent_investigation_card_count"] for item in ordered) <= 3
        ),
        "omitted_card_count_reaches_six": (limit["omitted_investigation_card_count"] == 6),
        "explicit_stop_remains_available": (
            limit["available_choices"] == ("ready_to_plan", "stop_not_ready")
        ),
    }
    inherited_envelope_checks = {
        "first_choice_within_current_ceiling": (
            first["canonical_request_body_bytes"]
            <= INHERITED_REQUEST_ENVELOPES["current_request_max_bytes"]
        ),
        "all_recovered_choices_within_recovered_ceiling": (
            max_recovered["canonical_request_body_bytes"]
            <= INHERITED_REQUEST_ENVELOPES["recovered_request_max_bytes"]
        ),
        "recovered_growth_within_predecessor_ceiling": (
            growth_ratio <= INHERITED_REQUEST_ENVELOPES["recovered_growth_ratio_max"]
        ),
    }
    body = {
        "schema_version": SERIES_ASSESSMENT_SCHEMA_VERSION,
        "measurement_hashes": [item["content_hash"] for item in ordered],
        "inherited_request_envelopes": INHERITED_REQUEST_ENVELOPES,
        "contract_checks": contract_checks,
        "inherited_envelope_checks": inherited_envelope_checks,
        "first_choice_request_body_bytes": first["canonical_request_body_bytes"],
        "max_recovered_request_body_bytes": max_recovered["canonical_request_body_bytes"],
        "max_recovered_information_actions_used": max_recovered["information_actions_used"],
        "limit_request_body_bytes": limit["canonical_request_body_bytes"],
        "max_recovered_growth_ratio": growth_ratio,
        "max_self_directed_state_bytes": max(item["self_directed_state_bytes"] for item in ordered),
        "max_recent_investigation_card_count": max(
            item["recent_investigation_card_count"] for item in ordered
        ),
        "max_investigation_ledger_bytes": max(
            item["investigation_ledger_bytes"] for item in ordered
        ),
        "max_investigation_ledger_recent_detail_count": max(
            item["investigation_ledger_recent_detail_count"] for item in ordered
        ),
        "model_visible_raw_source_content_count_at_limit": limit[
            "model_visible_raw_source_content_count"
        ],
        "candidate_preparation_series_ready": (
            all(contract_checks.values()) and all(inherited_envelope_checks.values())
        ),
        "provider_input_tokens_measured": False,
        "provider_latency_measured": False,
        "agent_quality_measured": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def audit_invalid_intent_recovery(events: tuple[RunEvent, ...] | list[RunEvent]) -> dict[str, Any]:
    """Audit the public event shape for one repeated invalid-intent terminal."""

    event_tuple = tuple(events)
    model_calls = [event for event in event_tuple if event.type == EventType.MODEL_CALLED]
    read_calls = [
        event
        for event in event_tuple
        if event.type == EventType.TOOL_CALLED and event.payload.get("tool") == "read_file"
    ]
    blocked = [event for event in event_tuple if event.type == EventType.TOOL_ADMISSION_BLOCKED]
    terminals = [event for event in event_tuple if event.type == EventType.RUN_FAILED]
    patches = [event for event in event_tuple if event.type == EventType.PATCH_APPLIED]
    submissions = [event for event in event_tuple if event.type == EventType.SUBMISSION_ACCEPTED]
    if len(terminals) != 1:
        raise ContractError("activation review invalid-intent terminal inventory differs")
    checks = {
        "one_shared_recovery_block": (
            len(blocked) == 1
            and blocked[0].payload.get("reason_code")
            == "self_directed_investigation_basis_ineligible"
            and blocked[0].payload.get("execution") == "not_dispatched"
        ),
        "one_read_dispatched_before_repeated_violation": len(read_calls) == 1,
        "three_model_calls_total": len(model_calls) == 3,
        "second_violation_stops_without_tool_dispatch": (
            not any(event.sequence > blocked[0].sequence for event in read_calls)
            if blocked
            else False
        ),
        "typed_repeated_terminal": (
            terminals[0].payload.get("error_code") == "MODEL_ACTION_CONTRACT_REPEATED"
        ),
        "no_patch_or_submission": not patches and not submissions,
    }
    body = {
        "schema_version": RECOVERY_AUDIT_SCHEMA_VERSION,
        "checks": checks,
        "model_call_count": len(model_calls),
        "read_dispatch_count": len(read_calls),
        "admission_block_count": len(blocked),
        "candidate_recovery_ready": all(checks.values()),
        "provider_calls": 0,
        "visible_check_calls": 0,
    }
    return {**body, "content_hash": sha256_json(body)}


def project_bounded_context_counterfactual(payload: dict[str, Any]) -> dict[str, Any]:
    """Measure one unimplemented bounded-ledger/recent-event projection.

    The projection retains the latest visible source body plus two later detail
    cards, omits the duplicate search inventory, and retains only the last three
    token observations and last three event triplets.  It is a design probe,
    not a valid V23 request or an implemented successor result.
    """

    evidence = validate_persisted_lean_harness_request(payload)
    if not isinstance(evidence, LeanHarnessRequestEvidenceV23):
        raise ContractError("bounded projection requires a Lean V23 request")
    measurement = measure_self_directed_exploration_request(payload)
    if measurement["information_actions_used"] != measurement["information_action_limit"]:
        raise ContractError("bounded projection requires the exploration-limit request")

    body = copy.deepcopy(evidence.request_body)
    context = json.loads(body["context"])
    ledger = context["investigation_ledger"]
    details = ledger["recent_details"]
    read_details = [
        item for item in details if isinstance(item, dict) and item.get("tool") == "read_file"
    ]
    non_read_details = [
        item for item in details if not (isinstance(item, dict) and item.get("tool") == "read_file")
    ]
    retained_details = (read_details[-1:] + non_read_details[-2:])[-3:]
    omitted = ledger["omitted"]
    omitted["details"] += len(details) - len(retained_details)
    omitted["searches"] += len(ledger["searches"])
    ledger["recent_details"] = retained_details
    ledger["searches"] = []
    token_projection = ledger.get("tail_policy", {}).get("token_projection", {})
    observations = token_projection.get("observations")
    if not isinstance(observations, list):
        raise ContractError("bounded projection token observations differ")
    token_projection["observations"] = observations[-3:]
    token_projection["omitted_observation_count"] = max(0, len(observations) - 3)
    ledger["content_hash"] = sha256_json(
        {key: item for key, item in ledger.items() if key != "content_hash"}
    )
    context["recent_events"] = context["recent_events"][-9:]
    body["context"] = canonical_json(context)
    projected_bytes = _bytes(body)
    original_bytes = measurement["canonical_request_body_bytes"]
    retained_raw_source_count = sum(
        isinstance(item, dict) and isinstance(item.get("content"), str) for item in retained_details
    )
    result = {
        "schema_version": "lean-v23-bounded-context-counterfactual-v1",
        "implemented": False,
        "valid_v23_request_claimed": False,
        "durable_events_changed": False,
        "durable_result_artifacts_changed": False,
        "original_request_body_bytes": original_bytes,
        "projected_request_body_bytes": projected_bytes,
        "projected_saved_bytes": original_bytes - projected_bytes,
        "projected_saved_ratio": round((original_bytes - projected_bytes) / original_bytes, 6),
        "projected_investigation_ledger_bytes": _bytes(ledger),
        "projected_recent_events_bytes": _bytes(context["recent_events"]),
        "retained_detail_count": len(retained_details),
        "retained_raw_source_content_count": retained_raw_source_count,
        "provider_input_tokens_measured": False,
    }
    return {**result, "content_hash": sha256_json(result)}


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"activation review source is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _immutable_identity(root: Path, relative: str) -> dict[str, Any]:
    identity = _identity(root, relative)
    expected = IMMUTABLE_INPUTS[relative]
    try:
        document = json.loads(ensure_within(root, relative).read_bytes())
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError("activation review input is not JSON") from exc
    identity["content_hash"] = _content_hash(document, label="activation review input")
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"immutable activation review input differs: {relative}")
    return identity


def build_self_directed_exploration_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Build the deterministic blocked decision without running the mock runner."""

    root = Path(repository).resolve()
    contract_checks = {
        "zero_source_surface_exact": False,
        "source_available_surface_exact": False,
        "run_check_absent_before_plan": False,
        "information_limit_surface_exact": True,
        "recent_investigation_cards_bounded_to_three": True,
        "omitted_card_count_reaches_six": True,
        "explicit_stop_remains_available": True,
    }
    envelope_checks = {
        "first_choice_within_current_ceiling": True,
        "all_recovered_choices_within_recovered_ceiling": False,
        "recovered_growth_within_predecessor_ceiling": False,
    }
    candidate_ready = all(contract_checks.values()) and all(envelope_checks.values())
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 29, tzinfo=UTC).isoformat(),
        "status": "candidate-preparation-blocked",
        "scope": "lean-v23-public-self-directed-exploration-activation-review",
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V23,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V23,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V23,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V23,
            "self_directed_exploration_policy_version": (
                LEAN_SELF_DIRECTED_EXPLORATION_POLICY_VERSION_V23
            ),
        },
        "declared_pre_plan_surfaces": EXPECTED_PRE_PLAN_SURFACES,
        "observed_pre_plan_surfaces": {
            "zero_source_read": ("search_files", "read_file", "run_check"),
            "source_read_available": (
                "search_files",
                "read_file",
                "run_check",
                "record_work_plan",
            ),
            "information_limit": ("record_work_plan", "declare_exploration_exhausted"),
        },
        "observed_offline_public_mock_sample": {
            "provenance": "one-zero-to-limit-real-shaped-public-mock-runner-trace",
            "canonical_raw_trace": False,
            "model_request_observations": 11,
            "successful_information_tool_dispatches": 10,
            "visible_check_calls": 0,
            "patches": 0,
            "submissions": 0,
            "zero_source_request_body_bytes": {"min": 14_011, "max": 14_047},
            "first_source_choice_request_body_bytes": {"min": 62_720, "max": 62_756},
            "first_source_choice_tool_schema_bytes": 8_722,
            "max_recovered_request_body_bytes": {"min": 98_613, "max": 98_686},
            "max_recovered_information_actions_used": 9,
            "limit_request_body_bytes": {"min": 97_085, "max": 97_157},
            "max_recovered_growth_ratio": {"min": 1.572274, "max": 1.572535},
            "limit_self_directed_state_bytes": 5_406,
            "limit_recent_investigation_cards": 3,
            "limit_omitted_investigation_cards": 6,
            "limit_investigation_ledger_bytes": 8_762,
            "limit_investigation_ledger_recent_details": 10,
            "limit_investigation_ledger_searches": 9,
            "limit_model_visible_raw_source_content_count": 1,
            "limit_model_visible_raw_source_content_utf8_bytes": 236,
            "request_artifact_bytes_are_provider_input": False,
            "provider_input_tokens_measured": False,
        },
        "inherited_request_envelope_audit": {
            "source": "immutable-v22-activation-review",
            "envelopes": INHERITED_REQUEST_ENVELOPES,
            "checks": envelope_checks,
            "v23_specific_relaxed_envelope_preregistered": False,
        },
        "state_bound_audit": {
            "information_action_limit": 10,
            "recent_investigation_card_limit": 3,
            "observed_recent_investigation_card_max": 3,
            "observed_omitted_card_count_at_limit": 6,
            "explicit_no_patch_stop_at_limit": True,
            "restart_state_and_tool_surface_identical": True,
            "duplicate_action_count_after_restart": 0,
            "full_model_visible_investigation_ledger_is_three_card_bounded": False,
        },
        "recovery_audit": {
            "invalid_intent_first_violation_uses_shared_slot": True,
            "invalid_intent_second_violation_stops_before_tool_dispatch": True,
            "model_calls": 3,
            "read_dispatches": 1,
            "admission_blocks": 1,
            "terminal": "MODEL_ACTION_CONTRACT_REPEATED",
            "patch_or_submission": False,
        },
        "counterfactual_bounded_context_probe": {
            "implemented": False,
            "original_request_body_bytes": {"min": 97_085, "max": 97_157},
            "projected_request_body_bytes": {"min": 85_133, "max": 85_187},
            "projected_saved_bytes": {"min": 11_952, "max": 11_970},
            "projected_saved_ratio": {"min": 0.123109, "max": 0.123205},
            "projected_investigation_ledger_bytes": 2_996,
            "projected_recent_events_bytes": 15_907,
            "retained_detail_count": 3,
            "retained_raw_source_content_count": 1,
            "durable_event_or_result_changed": False,
            "provider_tokens_or_agent_quality_measured": False,
        },
        "activation_criteria": {
            "contract_checks": contract_checks,
            "inherited_envelope_checks": envelope_checks,
            "restart_recovery_exact": True,
            "invalid_intent_recovery_bounded": True,
            "persisted_request_tamper_fails_closed": True,
        },
        "decision": {
            "candidate_preparation_ready": candidate_ready,
            "blocking_failure_class": "self-directed-pre-plan-request-contract-mismatch",
            "reason": (
                "V23 exposes run_check before a work plan even though the qualified state "
                "machine declares search/read-only and plan/search/read surfaces. Its "
                "bounded three-card state also coexists with a growing full investigation "
                "ledger, and the limit path exceeds the inherited V22 recovered-request "
                "envelope. A paid comparison would therefore include avoidable request-"
                "contract and input-overhead confounds."
            ),
            "next_work": (
                "versioned-pre-plan-tool-surface-and-bounded-investigation-context-successor"
            ),
            "runtime_source_change_in_this_review": False,
            "rapid_candidate_created": False,
            "rehearsal_executed": False,
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
        "provider_efficiency_established": False,
        "quality_improvement_established": False,
        "generalization_established": False,
        "paid_execution_authorized": False,
    }
    if body["decision"]["candidate_preparation_ready"]:
        raise ContractError("V23 activation blocker was not reproduced")
    return {**body, "content_hash": sha256_json(body)}


def review_bytes(value: dict[str, Any]) -> bytes:
    _content_hash(value, label="activation review")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_self_directed_exploration_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_self_directed_exploration_activation_review(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(review_bytes(value))
    return value


def load_self_directed_exploration_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("activation review is unavailable") from exc
    if review_bytes(value) != raw:
        raise ContractError("activation review bytes differ")
    if value != build_self_directed_exploration_activation_review(root):
        raise ContractError("activation review source binding differs")
    return value


__all__ = [
    "EXPECTED_PRE_PLAN_SURFACES",
    "IMMUTABLE_INPUTS",
    "INHERITED_REQUEST_ENVELOPES",
    "MEASUREMENT_SCHEMA_VERSION",
    "QUALIFICATION_PATH",
    "RECOVERY_AUDIT_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "SERIES_ASSESSMENT_SCHEMA_VERSION",
    "SOURCE_FILES",
    "assess_self_directed_exploration_request_series",
    "audit_invalid_intent_recovery",
    "build_self_directed_exploration_activation_review",
    "load_self_directed_exploration_activation_review",
    "materialize_self_directed_exploration_activation_review",
    "measure_self_directed_exploration_request",
    "project_bounded_context_counterfactual",
    "review_bytes",
]
