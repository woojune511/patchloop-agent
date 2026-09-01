from __future__ import annotations

import inspect
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import patchloop.agent.saturation_recovery_shadow as subject
from patchloop.agent.finalization import (
    project_phase_tool_surface,
    r8_public_development_finalization_reserve,
)
from patchloop.agent.phases import EvidenceState
from patchloop.agent.saturation_recovery_qualification import (
    QUALIFICATION_PATH,
    SaturationRecoveryPublicQualification,
)
from patchloop.agent.saturation_recovery_shadow import (
    SaturationRecoveryAdmissionShadow,
    project_saturation_recovery_admission_shadow,
)
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.contracts import EventType, RunEvent
from patchloop.util import sha256_json, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]
FIXED_TIME = datetime(2026, 8, 16, tzinfo=UTC)


@pytest.fixture(scope="module")
def thresholds() -> SaturationRecoveryPublicQualification:
    return SaturationRecoveryPublicQualification.model_validate_json(
        (REPOSITORY / QUALIFICATION_PATH).read_bytes()
    )


def _phase_surface():
    evidence = EvidenceState(
        worktree_diff_hash=sha256_text("synthetic-current-diff"),
        mutation_event_sequence=1,
        mutation_present=True,
        completed_checks=(),
        pending_checks=("public-check",),
        current_diff_check_event_sequences=(),
        latest_check_sequence=None,
        review_event_sequence=None,
        review_presented_to_model=False,
        task_review_event_sequence=None,
        task_review_presented_to_model=False,
        task_review_coverage_complete=None,
        unresolved_coverage_target_ids=(),
        submission_ready=False,
        missing_evidence=("visible_checks_current_diff",),
        allowed_next_actions=(
            "run_check",
            "apply_patch",
            "read_file",
            "search_files",
        ),
    )
    return project_phase_tool_surface(
        reserve=r8_public_development_finalization_reserve(),
        tool_schemas=TOOL_SCHEMAS_V2,
        phase_evidence=evidence,
        mode="exploration",
    )


def _event(
    sequence: int,
    event_type: EventType,
    payload: dict[str, Any],
) -> RunEvent:
    return RunEvent(
        event_id=f"evt_shadow_{sequence:03d}",
        run_id="run_saturation_recovery_shadow",
        sequence=sequence,
        type=event_type,
        timestamp=FIXED_TIME,
        actor="synthetic-public-fixture",
        payload=payload,
    )


def _replays(count: int, *, start: int = 1) -> list[RunEvent]:
    events: list[RunEvent] = []
    sequence = start
    for index in range(count):
        tool = "read_file" if index % 2 == 0 else "search_files"
        events.extend(
            (
                _event(
                    sequence,
                    EventType.LOOP_DETECTED,
                    {
                        "schema_version": "investigation-loop-v1",
                        "tool": tool,
                    },
                ),
                _event(
                    sequence + 1,
                    EventType.TOOL_REPLAYED,
                    {"tool": tool, "semantic_replay": True},
                ),
                _event(
                    sequence + 2,
                    EventType.TOOL_SUCCEEDED,
                    {"tool": "run_check", "status": "succeeded"},
                ),
            )
        )
        sequence += 3
    return events


def _seen_only(count: int, *, start: int = 1) -> list[RunEvent]:
    return [
        _event(
            start + index,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "read_file" if index % 2 == 0 else "search_files",
                "status": "succeeded",
                "novelty": {"classification": "seen_only"},
            },
        )
        for index in range(count)
    ]


def _rejections(count: int, *, start: int = 1) -> list[RunEvent]:
    return [
        _event(
            start + index,
            EventType.TOOL_FAILED,
            {
                "tool": "apply_patch",
                "status": "rejected",
                "error_code": "PATCH_REJECTED",
            },
        )
        for index in range(count)
    ]


def _project(
    thresholds: SaturationRecoveryPublicQualification,
    events: list[RunEvent],
) -> SaturationRecoveryAdmissionShadow:
    return project_saturation_recovery_admission_shadow(
        thresholds=thresholds,
        events=events,
        phase_tool_surface=_phase_surface(),
    )


def _rehash(body: dict[str, Any]) -> dict[str, Any]:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_normal_prefix_preserves_current_phase_surface(
    thresholds: SaturationRecoveryPublicQualification,
) -> None:
    shadow = _project(thresholds, [])

    assert shadow.admission_mode == "normal"
    assert shadow.reason_codes == ()
    assert shadow.selected_tool_names == shadow.source_phase_tool_names
    assert shadow.selected_tool_names == (
        "search_files",
        "read_file",
        "apply_patch",
        "run_check",
    )
    assert shadow.request_rebuild_required is False
    assert shadow.tool_surface_changed is False


def test_fourth_semantic_replay_blocks_only_read_and_search(
    thresholds: SaturationRecoveryPublicQualification,
) -> None:
    admitted = _project(thresholds, _replays(3))
    blocked = _project(thresholds, _replays(4))

    assert admitted.semantic_replay_count == 3
    assert admitted.evidence_saturated is False
    assert admitted.selected_tool_names == admitted.source_phase_tool_names
    assert blocked.semantic_replay_count == 4
    assert blocked.evidence_saturated is True
    assert blocked.reason_codes == ("semantic_replay_limit_reached",)
    assert blocked.removed_tool_names == ("search_files", "read_file")
    assert blocked.selected_tool_names == ("apply_patch", "run_check")
    assert blocked.freeform_patch_admitted is True


def test_second_no_progress_increment_requires_strategy_change_not_terminal(
    thresholds: SaturationRecoveryPublicQualification,
) -> None:
    one = _project(thresholds, _seen_only(1))
    two = _project(thresholds, _seen_only(2))

    assert one.no_progress_streak == 1
    assert one.strategy_change_required is False
    assert two.no_progress_streak == 2
    assert two.strategy_change_required is True
    assert two.admission_mode == "strategy-change-required"
    assert two.selected_tool_names == two.source_phase_tool_names
    assert two.tool_surface_changed is False
    assert two.request_rebuild_required is True
    assert two.strategy_change_is_required_not_terminal is True


def test_second_patch_rejection_replaces_freeform_with_structured_edit(
    thresholds: SaturationRecoveryPublicQualification,
) -> None:
    corrective = _project(thresholds, _rejections(1))
    recovery = _project(thresholds, _rejections(2))

    assert corrective.patch_rejection_count == 1
    assert corrective.direct_corrective_patch_retries_remaining == 0
    assert corrective.freeform_patch_admitted is True
    assert corrective.structured_edit_admitted is False
    assert recovery.patch_rejection_count == 2
    assert recovery.structured_edit_required is True
    assert recovery.removed_tool_names == ("apply_patch",)
    assert recovery.added_tool_names == ("apply_structured_edit",)
    assert recovery.selected_tool_names == (
        "search_files",
        "read_file",
        "apply_structured_edit",
        "run_check",
    )
    assert recovery.freeform_patch_admitted is False
    assert recovery.structured_edit_admitted is True
    assert recovery.structured_edit_runtime_registered is False


def test_combined_restriction_preserves_validation_and_structured_recovery(
    thresholds: SaturationRecoveryPublicQualification,
) -> None:
    events = _replays(4)
    events.extend(_rejections(2, start=events[-1].sequence + 1))
    shadow = _project(thresholds, events)

    assert shadow.admission_mode == "saturated-structured-edit-recovery"
    assert shadow.reason_codes == (
        "semantic_replay_limit_reached",
        "structured_edit_recovery_required",
    )
    assert shadow.selected_tool_names == ("apply_structured_edit", "run_check")
    assert shadow.removed_tool_names == (
        "search_files",
        "read_file",
        "apply_patch",
    )
    assert shadow.added_tool_names == ("apply_structured_edit",)


def test_patch_applied_resets_all_candidate_counters(
    thresholds: SaturationRecoveryPublicQualification,
) -> None:
    events = _replays(4)
    events.extend(_seen_only(2, start=events[-1].sequence + 1))
    events.extend(_rejections(2, start=events[-1].sequence + 1))
    mutation_sequence = events[-1].sequence + 1
    events.append(
        _event(
            mutation_sequence,
            EventType.PATCH_APPLIED,
            {"tool": "apply_patch", "status": "succeeded"},
        )
    )
    shadow = _project(thresholds, events)

    assert shadow.mutation_epoch_sequence == mutation_sequence
    assert (
        shadow.semantic_replay_count,
        shadow.no_progress_streak,
        shadow.patch_rejection_count,
    ) == (0, 0, 0)
    assert shadow.admission_mode == "normal"
    assert shadow.selected_tool_names == shadow.source_phase_tool_names


def test_source_prefix_must_be_ordered_single_run_and_exact_types(
    thresholds: SaturationRecoveryPublicQualification,
) -> None:
    ordered = _seen_only(2)
    with pytest.raises(ValueError, match="ordered and unique"):
        _project(thresholds, list(reversed(ordered)))

    other = ordered[1].model_copy(update={"run_id": "run_other"})
    with pytest.raises(ValueError, match="one run"):
        _project(thresholds, [ordered[0], other])

    with pytest.raises(TypeError, match="exact RunEvent"):
        project_saturation_recovery_admission_shadow(
            thresholds=thresholds,
            events=[ordered[0].model_dump(mode="python")],  # type: ignore[list-item]
            phase_tool_surface=_phase_surface(),
        )


def test_rehashed_decision_tool_and_event_drift_is_rejected(
    thresholds: SaturationRecoveryPublicQualification,
) -> None:
    original = _project(thresholds, _rejections(2))

    decision = original.model_dump(mode="python")
    decision["structured_edit_required"] = False
    with pytest.raises(ValidationError, match="policy decision differs"):
        SaturationRecoveryAdmissionShadow.model_validate(_rehash(decision))

    tools = original.model_dump(mode="python")
    tools["selected_tool_names"] = ("apply_patch", "run_check")
    with pytest.raises(ValidationError, match="selected tool names differ"):
        SaturationRecoveryAdmissionShadow.model_validate(_rehash(tools))

    events = original.model_dump(mode="python")
    events["event_projections"][0]["effect"] = "progress-reset"
    with pytest.raises(ValidationError):
        SaturationRecoveryAdmissionShadow.model_validate(_rehash(events))


def test_shadow_has_no_runner_state_gateway_or_provider_surface() -> None:
    source = inspect.getsource(subject)
    runner = (REPOSITORY / "patchloop/agent/runner.py").read_text(encoding="utf-8")

    assert "StateStore" not in source
    assert "ToolGateway" not in source
    assert "OpenAIResponsesAdapter" not in source
    assert ".execute(" not in source
    assert "saturation_recovery_shadow" not in runner
    assert "project_saturation_recovery_admission_shadow" not in runner
