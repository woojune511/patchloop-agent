from __future__ import annotations

import copy
import json

import pytest

from patchloop.agent.context import BuiltContext
from patchloop.agent.context_event_compaction import (
    project_lean_context_event_descriptors_v2,
)
from patchloop.agent.workflow_plan_admission_feedback_successor import (
    PLAN_ADMISSION_FEEDBACK_PROJECTION_POLICY,
    PROJECTED_FEEDBACK_SCHEMA,
    BoundedWorkPlanAdmissionFeedback,
    CompatibleBoundedWorkPlanAdmissionFeedback,
    project_bounded_plan_admission_feedback,
    project_compatible_bounded_plan_admission_feedback,
)
from patchloop.errors import ContractError
from patchloop.util import sha256_json, sha256_text


def _document(schema: str, payload: str) -> dict:
    body = {"schema_version": schema, "payload": payload}
    return {**body, "content_hash": sha256_json(body)}


def _details() -> dict:
    catalog = _document("eligible-plan-evidence-catalog-v3", "c" * 2_000)
    causal = _document("activated-causal-plan-request-v1", "p" * 8_000)
    activated_body = {
        "schema_version": "pinned-exploration-plan-request-v1",
        "source_request": {"base_request": causal},
        "payload": "a" * 18_000,
    }
    activated = {
        **activated_body,
        "content_hash": sha256_json(activated_body),
    }
    return {
        "schema_version": "work-plan-admission-feedback-v1",
        "policy_version": "work-plan-admission-recovery-v1",
        "plan_gate_id": sha256_text("gate"),
        "attempt": 1,
        "reason_codes": ["exploration_blocking_unknowns_open"],
        "eligible_catalog_hash": catalog["content_hash"],
        "eligible_plan_evidence_catalog": catalog,
        "activated_exploration_plan_request": activated,
        "activated_exploration_plan_request_hash": activated["content_hash"],
        "causal_plan_request_projection": causal,
        "causal_plan_request_projection_hash": causal["content_hash"],
        "semantic_progress_state": None,
        "required_prior_hypothesis_disposition": None,
        "worktree_diff_hash": sha256_text(""),
        "request_artifact_id": "art_request",
        "request_body_hash": sha256_text("request"),
        "execution": "not_dispatched",
        "guidance": (
            "Retry once using only the exact cspan and support IDs in "
            "causal_plan_request_projection. Do not supply paths, ranges, roles, "
            "evidence bindings, observation status, or check order."
        ),
    }


def _context(details: dict | None = None) -> BuiltContext:
    payload = {
        "public_task": {"task_id": "bounded-plan-feedback"},
        "phase": "PLAN",
        "checkpoint": None,
        "phase_contract": {"current_phase": "PLAN"},
        "recent_events": (
            [
                {
                    "sequence": 17,
                    "type": "ToolFailed",
                    "actor": "tool-gateway",
                    "payload": {
                        "tool": "record_work_plan",
                        "status": "rejected",
                        "error_code": "WORK_PLAN_ADMISSION_REJECTED",
                        "error_message": "public plan is incomplete",
                        "error_details": details,
                        "admission_blocked": True,
                        "artifact_id": "art_result",
                        "artifact_path": "objects/result.json",
                    },
                }
            ]
            if details is not None
            else []
        ),
        "execution_signals": {"repeated_calls": []},
        "selected_memory": None,
        "rules": {"private_evaluator_data_unavailable": True},
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    return BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            "schema_version": "context-build-evidence-v11",
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
        },
    )


def _project(details: dict | None = None):
    compacted = project_lean_context_event_descriptors_v2(
        _context(_details() if details is None else details)
    )
    return compacted, project_bounded_plan_admission_feedback(compacted)


def test_projection_bounds_only_model_visible_plan_feedback() -> None:
    source_details = _details()
    durable_copy = copy.deepcopy(source_details)
    compacted, projected = _project(source_details)
    payload = json.loads(projected.rendered)
    feedback = payload["recent_events"][0]["payload"]["error_details"]
    record = projected.evidence.event_projections[0]

    assert source_details == durable_copy
    assert feedback["schema_version"] == PROJECTED_FEEDBACK_SCHEMA
    assert feedback["projection_policy_version"] == (PLAN_ADMISSION_FEEDBACK_PROJECTION_POLICY)
    assert feedback["reason_codes"] == ["exploration_blocking_unknowns_open"]
    assert "eligible_plan_evidence_catalog" not in feedback
    assert "activated_exploration_plan_request" not in feedback
    assert "causal_plan_request_projection" not in feedback
    assert {item["field"] for item in feedback["omitted_details"]} >= {
        "eligible_plan_evidence_catalog",
        "activated_exploration_plan_request",
        "causal_plan_request_projection",
        "semantic_progress_state",
    }
    assert projected.evidence.source_context_hash == compacted.content_hash
    assert projected.evidence.context_bytes_saved > 25_000
    assert record.source_error_details_bytes > 25_000
    assert record.projected_error_details_bytes <= 4_096
    assert projected.evidence.durable_event_changed is False
    assert projected.evidence.durable_result_artifact_changed is False

    tampered_feedback = copy.deepcopy(feedback)
    tampered_feedback["unversioned_field"] = "not allowed"
    with pytest.raises(ValueError):
        BoundedWorkPlanAdmissionFeedback.model_validate_json(
            json.dumps(tampered_feedback, separators=(",", ":"))
        )


def test_projection_is_deterministic_and_empty_context_is_exact_noop() -> None:
    compacted, first = _project()
    second = project_bounded_plan_admission_feedback(compacted)
    empty = project_lean_context_event_descriptors_v2(_context())
    empty_projected = project_bounded_plan_admission_feedback(empty)

    assert first == second
    assert empty_projected.rendered == empty.rendered
    assert empty_projected.evidence.projected_event_count == 0
    assert empty_projected.evidence.context_bytes_saved == 0


def test_self_directed_feedback_is_opt_in_and_preserves_v24_fail_closed() -> None:
    details = _details()
    details["policy_version"] = "bounded-self-directed-exploration-v1"
    compacted = project_lean_context_event_descriptors_v2(_context(details))

    with pytest.raises(ContractError, match="source contract differs"):
        project_bounded_plan_admission_feedback(compacted)

    projected = project_compatible_bounded_plan_admission_feedback(compacted)
    feedback = json.loads(projected.rendered)["recent_events"][0]["payload"]["error_details"]
    parsed = CompatibleBoundedWorkPlanAdmissionFeedback.model_validate_json(
        json.dumps(feedback, separators=(",", ":"))
    )
    assert parsed.policy_version == "bounded-self-directed-exploration-v1"
    assert projected.evidence.projected_event_count == 1


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value.__setitem__("unexpected_nested_plan", {"large": "x"}),
            "source fields differ",
        ),
        (
            lambda value: value.__setitem__(
                "eligible_catalog_hash",
                sha256_text("tampered"),
            ),
            "nested binding differs",
        ),
        (
            lambda value: value.__setitem__(
                "cross_reset_failure_trigger",
                _document("cross-reset-trigger-v1", "trigger"),
            ),
            "cross-reset fields are incomplete",
        ),
    ],
)
def test_projection_fails_closed_on_unversioned_or_tampered_feedback(
    mutate,
    message: str,
) -> None:
    details = _details()
    mutate(details)
    compacted = project_lean_context_event_descriptors_v2(_context(details))

    with pytest.raises(ContractError, match=message):
        project_bounded_plan_admission_feedback(compacted)
