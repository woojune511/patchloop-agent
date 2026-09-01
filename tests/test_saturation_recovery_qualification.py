from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

import patchloop.agent.saturation_recovery_qualification as subject
from patchloop.agent.saturation_recovery_qualification import (
    RUN_FRAME,
    SOURCE_PATHS,
    VALIDATION_PATHS,
    SaturationRecoveryPublicQualification,
    build_saturation_recovery_public_qualification,
    load_saturation_recovery_public_qualification,
    materialize_saturation_recovery_public_qualification,
    qualification_bytes,
)
from patchloop.errors import RecoveryError
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def qualification() -> SaturationRecoveryPublicQualification:
    return build_saturation_recovery_public_qualification(REPOSITORY)


def _rehash(body: dict[str, object]) -> dict[str, object]:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_public_r8_projection_freezes_condition_neutral_thresholds(
    qualification: SaturationRecoveryPublicQualification,
) -> None:
    assert qualification.status == "PUBLIC_THRESHOLDS_FROZEN_RUNTIME_CLOSED"
    assert qualification.evidence_scope == (
        "r8-public-development-agent-visible-lifecycle-metadata"
    )
    assert (
        tuple((item.run_id, item.task_id, item.condition) for item in qualification.observations)
        == RUN_FRAME
    )
    assert [item.event_count for item in qualification.observations] == [92, 65, 54, 85]
    assert qualification.total_event_rows_read == 296
    assert qualification.selected_event_projection_rows == 53
    assert qualification.runs_with_semantic_replay == 1
    assert qualification.runs_with_patch_rejection == 1
    assert qualification.observed_max_semantic_replays_per_mutation_epoch == 3
    assert qualification.observed_max_no_progress_streak == 2
    assert qualification.observed_max_consecutive_patch_rejections == 1
    assert qualification.observed_max_recovery_model_turns == 1
    assert qualification.source_semantic_replay_saturation_threshold == 6
    assert qualification.source_tool_gateway_saturation_threshold == 6
    assert qualification.candidate_semantic_replay_saturation_threshold == 4
    assert qualification.candidate_no_progress_strategy_threshold == 2
    assert qualification.candidate_structured_edit_escalation_rejections == 2
    assert qualification.direct_corrective_patch_retries_before_escalation == 1
    assert qualification.saturation_blocks_tools == ("read_file", "search_files")
    assert qualification.condition_neutral_thresholds is True
    assert qualification.observed_success_prefix_preserved is True


def test_moto_no_memory_projection_binds_observed_recovery(
    qualification: SaturationRecoveryPublicQualification,
) -> None:
    observed = qualification.observations[0]
    assert observed.semantic_replay_sequences == (40, 51, 55)
    assert observed.semantic_replay_tools == (
        "search_files",
        "read_file",
        "read_file",
    )
    assert observed.loop_detection_count == 3
    assert observed.max_no_progress_streak == 2
    assert observed.strategy_change_required_count == 1
    assert observed.rejected_patch_sequences == (60,)
    assert observed.first_recovery_mutation_sequence == 67
    assert observed.model_turns_from_rejection_to_recovery == 1
    assert all(
        item.semantic_replay_count == 0
        and item.rejected_patch_count == 0
        and item.first_recovery_mutation_sequence is None
        for item in qualification.observations[1:]
    )


def test_threshold_claim_and_authority_boundaries_are_closed(
    qualification: SaturationRecoveryPublicQualification,
) -> None:
    assert qualification.r16_outcomes_used_for_threshold_selection is False
    assert qualification.heldout_task_files_read == 0
    assert qualification.private_task_files_read == 0
    assert qualification.hidden_files_read == 0
    assert qualification.reference_patches_read == 0
    assert qualification.trace_snapshot.checked_in is False
    assert qualification.trace_snapshot.wal_bytes_at_projection == 0
    assert qualification.trace_snapshot_replayable_from_checked_in_files is False
    assert qualification.threshold_optimality_established is False
    assert qualification.provider_token_savings_verified is False
    assert qualification.success_effect_verified is False
    assert qualification.provider_transport_calls == 0
    assert qualification.provider_generation_calls == 0
    assert qualification.runner_calls == 0
    assert qualification.docker_calls == 0
    assert qualification.evaluator_calls == 0
    assert qualification.added_model_cost_usd == 0
    assert qualification.provider_calls_authorized is False
    assert qualification.runner_activation_authorized is False
    assert qualification.tool_policy_activation_authorized is False
    assert qualification.state_mutation_authorized is False
    assert qualification.paid_execution_authorized is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_semantic_replay_saturation_threshold", 5),
        ("candidate_no_progress_strategy_threshold", 3),
        ("candidate_structured_edit_escalation_rejections", 3),
        ("condition_neutral_thresholds", False),
        ("r16_outcomes_used_for_threshold_selection", True),
        ("provider_calls_authorized", True),
        ("runner_activation_authorized", True),
    ],
)
def test_rehashed_threshold_or_authority_drift_is_rejected(
    qualification: SaturationRecoveryPublicQualification,
    field: str,
    value: object,
) -> None:
    body = qualification.model_dump(mode="python")
    body[field] = value
    with pytest.raises(ValidationError):
        SaturationRecoveryPublicQualification.model_validate(_rehash(body))


def test_rehashed_observation_aggregate_and_predecessor_drift_is_rejected(
    qualification: SaturationRecoveryPublicQualification,
) -> None:
    observation = qualification.model_dump(mode="python")
    observation["observations"][0]["semantic_replay_count"] = 2
    with pytest.raises(ValidationError, match="semantic replay observation differs"):
        SaturationRecoveryPublicQualification.model_validate(_rehash(observation))

    projection = qualification.model_dump(mode="python")
    projection["observations"][0]["selected_event_projection_hash"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="selected-event projection frame differs"):
        SaturationRecoveryPublicQualification.model_validate(_rehash(projection))

    aggregate = qualification.model_dump(mode="python")
    aggregate["selected_event_projection_rows"] += 1
    with pytest.raises(ValidationError, match="selected event-row total differs"):
        SaturationRecoveryPublicQualification.model_validate(_rehash(aggregate))

    predecessor = qualification.model_dump(mode="python")
    predecessor["predecessor_compacted_shadow"]["file_bytes"] += 1
    with pytest.raises(ValidationError, match="compacted-shadow predecessor differs"):
        SaturationRecoveryPublicQualification.model_validate(_rehash(predecessor))


def test_source_and_validation_inventories_bind_current_bytes(
    qualification: SaturationRecoveryPublicQualification,
) -> None:
    assert tuple(item.path for item in qualification.source_files) == SOURCE_PATHS
    assert tuple(item.path for item in qualification.validation_files) == VALIDATION_PATHS
    for item in (*qualification.source_files, *qualification.validation_files):
        raw = (REPOSITORY / item.path).read_bytes()
        assert item.file_bytes == len(raw)
        assert item.file_sha256 == sha256_bytes(raw)


def test_build_uses_immutable_sqlite_and_never_reads_heldout_or_private_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[str] = []
    uris: list[str] = []
    original_read_bytes = Path.read_bytes
    original_connect = subject.sqlite3.connect

    def tracked_read_bytes(path: Path) -> bytes:
        opened.append(str(path.resolve(strict=False)).replace("\\", "/"))
        return original_read_bytes(path)

    def tracked_connect(database, *args, **kwargs):
        uris.append(str(database))
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", tracked_read_bytes)
    monkeypatch.setattr(subject.sqlite3, "connect", tracked_connect)
    built = build_saturation_recovery_public_qualification(REPOSITORY)

    assert built.sqlite_queries == 4
    assert len(uris) == 1
    assert "mode=ro&immutable=1" in uris[0]
    normalized = tuple(item.lower() for item in opened)
    assert not any("/heldout-ac/" in item for item in normalized)
    assert not any("/tasks/" in item for item in normalized)
    assert not any(
        token in item
        for item in normalized
        for token in ("private.yaml", "/hidden", "reference.patch", "r16")
    )


def test_trace_snapshot_hash_or_wal_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "R8_TRACE_SNAPSHOT_FILE_SHA256",
        "sha256:" + "0" * 64,
    )
    with pytest.raises(RecoveryError, match="trace snapshot differs"):
        build_saturation_recovery_public_qualification(REPOSITORY)


def test_materialization_is_append_only_canonical_and_replayable(tmp_path: Path) -> None:
    output = tmp_path / "thresholds.json"
    first = materialize_saturation_recovery_public_qualification(REPOSITORY, output)
    first_bytes = output.read_bytes()
    first_mtime = output.stat().st_mtime_ns
    second = materialize_saturation_recovery_public_qualification(REPOSITORY, output)

    assert first == second
    assert output.read_bytes() == first_bytes == qualification_bytes(first)
    assert output.stat().st_mtime_ns == first_mtime
    assert load_saturation_recovery_public_qualification(REPOSITORY, output) == first

    output.write_bytes(first_bytes + b" ")
    with pytest.raises(RecoveryError, match="existing.*differs"):
        materialize_saturation_recovery_public_qualification(REPOSITORY, output)


def test_qualification_has_no_runner_generation_or_runtime_policy_surface() -> None:
    source = inspect.getsource(subject)
    runner = (REPOSITORY / "patchloop/agent/runner.py").read_text(encoding="utf-8")

    assert "StateStore" not in source
    assert "load_task_package" not in source
    assert ".execute_request(" not in source
    assert "saturation_recovery_qualification" not in runner
    assert "build_saturation_recovery_public_qualification" not in runner
