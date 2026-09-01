from __future__ import annotations

import copy
import json

import pytest

from patchloop.agent.context_event_compaction import (
    project_lean_context_event_descriptors_v2,
)
from patchloop.agent.investigation import InspectionRecord
from patchloop.agent.workflow_plan_contract_compatibility_successor import (
    project_trigger_bound_self_directed_plan_request,
)
from patchloop.agent.workflow_r21_reliability_successor import (
    GENERATION_INCOMPLETE_RECOVERY_POLICY,
    PLAN_ADMISSION_FEEDBACK_POLICY_V2,
    LifecycleBoundPlanRequest,
    normalize_lifecycle_bound_plan,
    project_compact_plan_admission_feedback_v2,
    project_generation_incomplete_recovery,
    project_lifecycle_bound_plan_request,
    resolve_anchored_read,
)
from patchloop.contracts import Artifact, EventType, RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_json, sha256_text, utc_now
from tests.test_workflow_plan_admission_feedback_successor import _context, _details
from tests.test_workflow_self_directed_exploration_successor import (
    _plan_arguments,
    _request,
    _task,
    _v4_catalog,
)


def _event(sequence: int, *, policy: str = GENERATION_INCOMPLETE_RECOVERY_POLICY) -> RunEvent:
    return RunEvent(
        event_id=f"evt-{sequence}",
        run_id="run-v26",
        sequence=sequence,
        type=EventType.TOOL_ADMISSION_BLOCKED,
        timestamp=utc_now(),
        actor="workflow-state-machine",
        payload={
            "policy_version": policy,
            "reason_code": "reasoning_incomplete",
            "execution": "not_dispatched",
        },
    )


def _search_record() -> InspectionRecord:
    result = {
        "matches": [
            {"path": "src/pkg/example.py", "line": 41, "text": "def target():"},
            {"path": "src/pkg/example.py", "line": 88, "text": "return state"},
        ]
    }
    return InspectionRecord(
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
            size_bytes=len(json.dumps(result).encode("utf-8")),
            path="objects/search.json",
            created_at=utc_now(),
        ),
    )


def _lifecycle_arguments() -> dict:
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


def _lifecycle_request() -> tuple[object, LifecycleBoundPlanRequest]:
    catalog = _v4_catalog()
    self_directed = _request(catalog)
    trigger_bound = project_trigger_bound_self_directed_plan_request(
        self_directed.source_request.base_request
    )
    return catalog, project_lifecycle_bound_plan_request(trigger_bound)


def test_generation_incomplete_recovery_is_one_use_and_separate_by_policy() -> None:
    available = project_generation_incomplete_recovery((_event(1, policy="other-policy"),))
    consumed = project_generation_incomplete_recovery((_event(2),))

    assert available.used is False and available.remaining == 1
    assert consumed.used is True and consumed.remaining == 0
    assert consumed.source_event_sequence == 2
    with pytest.raises(RecoveryError, match="more than once"):
        project_generation_incomplete_recovery((_event(2), _event(3)))


def test_compact_feedback_keeps_latest_public_ids_and_hashes_older_rejections() -> None:
    details = _details()
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
    source = _context(details)
    payload = json.loads(source.rendered)
    older = copy.deepcopy(payload["recent_events"][0])
    older["sequence"] = 16
    payload["recent_events"].insert(0, older)
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    source = copy.copy(source)
    object.__setattr__(source, "rendered", rendered)
    object.__setattr__(source, "content_hash", sha256_text(rendered))
    source.evidence["rendered_characters"] = len(rendered)
    source.evidence["rendered_bytes"] = len(rendered.encode("utf-8"))
    compacted = project_lean_context_event_descriptors_v2(source)

    first = project_compact_plan_admission_feedback_v2(compacted)
    second = project_compact_plan_admission_feedback_v2(compacted)
    projected = json.loads(first.rendered)["recent_events"]

    assert first == second
    assert first.evidence.policy_version == PLAN_ADMISSION_FEEDBACK_POLICY_V2
    assert projected[0]["payload"]["error_details"]["schema_version"] == (
        "superseded-plan-admission-feedback-v2"
    )
    latest = projected[1]["payload"]["error_details"]
    assert latest["eligible_evidence_ids"] == ["pev:17", "pev:19"]
    assert latest["eligible_source_span_ids"] == ["cspan:21:0", "cspan:22:0"]
    assert "eligible_plan_evidence_catalog" not in latest
    assert first.evidence.projected_context_bytes <= 90_000


def test_anchored_read_resolves_exact_match_and_rejects_stale_or_foreign_scope() -> None:
    record = _search_record()
    resolved = resolve_anchored_read(
        run_id="run-v26",
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

    assert resolved.path == "src/pkg/example.py"
    assert (resolved.start_line, resolved.match_line, resolved.end_line) == (80, 88, 100)
    with pytest.raises(ContractError, match="stale or unavailable"):
        resolve_anchored_read(
            run_id="run-v26",
            task=_task(),
            worktree_diff_hash=sha256_text("other-diff"),
            records=(record,),
            raw_anchor={"search_event_sequence": 7, "match_index": 0},
        )


def test_lifecycle_plan_records_atomic_transition_and_fails_closed_on_owner_tamper() -> None:
    catalog, request = _lifecycle_request()
    arguments = _lifecycle_arguments()
    plan, closure, lifecycle = normalize_lifecycle_bound_plan(
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

    assert lifecycle.plan_hash == plan.content_hash
    assert lifecycle.mutation_site_span_id in lifecycle.cited_source_span_ids
    assert closure.request_projection_hash == request.source_request.content_hash

    tampered = copy.deepcopy(arguments)
    tampered["lifecycle_state_transition"]["owners"][0]["owner_source_span_id"] = tampered[
        "readiness_assessment"
    ]["basis_source_span_ids"][-1]
    with pytest.raises(ContractError, match="mutation site"):
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
