from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import patchloop.agent.saturation_recovery_shadow_qualification as subject
from patchloop.agent.saturation_recovery_shadow_qualification import (
    CONDITIONS,
    FRAME_PHASES,
    PREDECESSOR_V1_BYTES,
    PREDECESSOR_V1_CONTENT_HASH,
    PREDECESSOR_V1_FILE_SHA256,
    PREDECESSOR_V1_PATH,
    SCENARIOS,
    SOURCE_PATHS,
    VALIDATION_PATHS,
    SaturationRecoveryShadowPublicQualification,
    build_saturation_recovery_shadow_public_qualification,
    load_saturation_recovery_shadow_public_qualification,
    materialize_saturation_recovery_shadow_public_qualification,
    qualification_bytes,
)
from patchloop.errors import RecoveryError
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def qualification() -> SaturationRecoveryShadowPublicQualification:
    return build_saturation_recovery_shadow_public_qualification(REPOSITORY)


def _rehash(body: dict[str, Any]) -> dict[str, Any]:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_boundary_frame_qualifies_exact_4_2_2_decisions(
    qualification: SaturationRecoveryShadowPublicQualification,
) -> None:
    assert qualification.status == (
        "PUBLIC_SYNTHETIC_NO_CALL_ADMISSION_RECOVERY_QUALIFIED_RUNTIME_CLOSED"
    )
    assert qualification.scenarios == SCENARIOS
    assert qualification.conditions == CONDITIONS
    assert len(qualification.boundary_observations) == 9
    by_scenario = {item.scenario: item for item in qualification.boundary_observations}

    assert by_scenario["semantic-replay-three"].semantic_replay_count == 3
    assert by_scenario["semantic-replay-three"].admission_mode == "normal"
    assert by_scenario["semantic-replay-four"].semantic_replay_count == 4
    assert by_scenario["semantic-replay-four"].selected_tool_names == (
        "apply_patch",
        "run_check",
    )
    assert by_scenario["no-progress-one"].no_progress_streak == 1
    assert by_scenario["no-progress-one"].admission_mode == "normal"
    assert by_scenario["no-progress-two"].admission_mode == ("strategy-change-required")
    assert by_scenario["patch-rejection-one"].patch_rejection_count == 1
    assert by_scenario["patch-rejection-one"].shadow.freeform_patch_admitted is True
    assert by_scenario["patch-rejection-two"].selected_tool_names == (
        "search_files",
        "read_file",
        "apply_structured_edit",
        "run_check",
    )
    assert by_scenario["combined-restriction"].selected_tool_names == (
        "apply_structured_edit",
        "run_check",
    )
    reset = by_scenario["patch-applied-reset"]
    assert (
        reset.semantic_replay_count,
        reset.no_progress_streak,
        reset.patch_rejection_count,
    ) == (0, 0, 0)
    assert reset.admission_mode == "normal"


def test_combined_restriction_crosses_all_current_phase_surfaces(
    qualification: SaturationRecoveryShadowPublicQualification,
) -> None:
    assert qualification.frame_phases == FRAME_PHASES
    assert tuple(item.phase for item in qualification.phase_observations) == FRAME_PHASES
    for item in qualification.phase_observations:
        assert item.scenario == "combined-restriction"
        assert item.shadow.evidence_saturated is True
        assert item.shadow.structured_edit_required is True
        assert "read_file" not in item.selected_tool_names
        assert "search_files" not in item.selected_tool_names
        assert "apply_patch" not in item.selected_tool_names
        assert "apply_structured_edit" in item.selected_tool_names
        assert any(name in item.selected_tool_names for name in ("run_check", "get_diff"))
        assert item.condition_pair_equal is True
        assert item.no_memory_projection_hash == item.structured_projection_hash


def test_claim_and_authority_boundaries_remain_closed(
    qualification: SaturationRecoveryShadowPublicQualification,
) -> None:
    assert qualification.condition_neutral_projection is True
    assert qualification.structured_edit_runtime_registered is False
    assert qualification.threshold_optimality_established is False
    assert qualification.provider_token_savings_verified is False
    assert qualification.success_effect_verified is False
    assert qualification.public_task_files_read == 0
    assert qualification.private_task_files_read == 0
    assert qualification.hidden_files_read == 0
    assert qualification.reference_patches_read == 0
    assert qualification.runtime_state_files_read == 0
    assert qualification.provider_transport_calls == 0
    assert qualification.provider_generation_calls == 0
    assert qualification.runner_calls == 0
    assert qualification.tool_execution_calls == 0
    assert qualification.docker_calls == 0
    assert qualification.evaluator_calls == 0
    assert qualification.added_model_cost_usd == 0
    assert qualification.provider_calls_authorized is False
    assert qualification.runner_activation_authorized is False
    assert qualification.tool_policy_activation_authorized is False
    assert qualification.request_integration_authorized is False
    assert qualification.request_persistence_authorized is False
    assert qualification.state_mutation_authorized is False
    assert qualification.paid_execution_authorized is False
    assert qualification.next_gate == (
        "predeclare-budget-adequacy-measurement-contract-before-fresh-design"
    )


def test_v1_is_preserved_as_an_invalidated_append_only_predecessor(
    qualification: SaturationRecoveryShadowPublicQualification,
) -> None:
    predecessor = qualification.predecessor_v1
    raw = (REPOSITORY / PREDECESSOR_V1_PATH).read_bytes()

    assert predecessor.path == PREDECESSOR_V1_PATH
    assert predecessor.file_bytes == len(raw) == PREDECESSOR_V1_BYTES
    assert predecessor.file_sha256 == sha256_bytes(raw) == PREDECESSOR_V1_FILE_SHA256
    assert predecessor.content_hash == PREDECESSOR_V1_CONTENT_HASH
    assert qualification.predecessor_v1_disposition == (
        "invalidated-by-post-materialization-self-validation-hardening"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("semantic_replay_threshold", 5),
        ("no_progress_strategy_threshold", 3),
        ("structured_edit_escalation_rejections", 3),
        ("condition_neutral_projection", False),
        ("provider_calls_authorized", True),
        ("runner_activation_authorized", True),
        ("request_integration_authorized", True),
    ],
)
def test_rehashed_threshold_claim_or_authority_drift_is_rejected(
    qualification: SaturationRecoveryShadowPublicQualification,
    field: str,
    value: object,
) -> None:
    body = qualification.model_dump(mode="python")
    body[field] = value
    with pytest.raises(ValidationError):
        SaturationRecoveryShadowPublicQualification.model_validate(_rehash(body))


def test_rehashed_nested_decision_and_condition_drift_is_rejected(
    qualification: SaturationRecoveryShadowPublicQualification,
) -> None:
    decision = qualification.model_dump(mode="python")
    decision["boundary_observations"][2]["selected_tool_names"] = ("apply_patch",)
    with pytest.raises(ValidationError):
        SaturationRecoveryShadowPublicQualification.model_validate(_rehash(decision))

    condition = qualification.model_dump(mode="python")
    condition["phase_observations"][0]["structured_projection_hash"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="condition projection differs"):
        SaturationRecoveryShadowPublicQualification.model_validate(_rehash(condition))


def test_source_and_validation_inventories_bind_current_bytes(
    qualification: SaturationRecoveryShadowPublicQualification,
) -> None:
    assert tuple(item.path for item in qualification.source_files) == SOURCE_PATHS
    assert tuple(item.path for item in qualification.validation_files) == VALIDATION_PATHS
    for item in (*qualification.source_files, *qualification.validation_files):
        raw = (REPOSITORY / item.path).read_bytes()
        assert item.file_bytes == len(raw)
        assert item.file_sha256 == sha256_bytes(raw)


def test_builder_reads_only_predecessor_and_qualification_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[str] = []
    original = Path.read_bytes

    def tracked(path: Path) -> bytes:
        opened.append(str(path.resolve(strict=False)).replace("\\", "/").lower())
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", tracked)
    built = build_saturation_recovery_shadow_public_qualification(REPOSITORY)

    assert built.runtime_state_files_read == 0
    assert not any("/.patchloop/" in item for item in opened)
    assert not any("/tasks/" in item for item in opened)
    assert not any(
        token in item
        for item in opened
        for token in ("private.yaml", "/hidden", "reference.patch", "r16")
    )


def test_predecessor_byte_or_content_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "THRESHOLD_QUALIFICATION_BYTES", 1)
    with pytest.raises(RecoveryError, match="threshold predecessor differs"):
        build_saturation_recovery_shadow_public_qualification(REPOSITORY)


def test_materialization_is_append_only_canonical_and_replayable(
    tmp_path: Path,
) -> None:
    output = tmp_path / "admission-shadow.json"
    first = materialize_saturation_recovery_shadow_public_qualification(
        REPOSITORY,
        output,
    )
    first_bytes = output.read_bytes()
    first_mtime = output.stat().st_mtime_ns
    second = materialize_saturation_recovery_shadow_public_qualification(
        REPOSITORY,
        output,
    )

    assert first == second
    assert output.read_bytes() == first_bytes == qualification_bytes(first)
    assert output.stat().st_mtime_ns == first_mtime
    assert load_saturation_recovery_shadow_public_qualification(REPOSITORY, output) == first

    output.write_bytes(first_bytes + b" ")
    with pytest.raises(RecoveryError, match="existing.*differs"):
        materialize_saturation_recovery_shadow_public_qualification(
            REPOSITORY,
            output,
        )


def test_qualification_has_no_runner_gateway_request_or_state_surface() -> None:
    source = inspect.getsource(subject)
    runner = (REPOSITORY / "patchloop/agent/runner.py").read_text(encoding="utf-8")

    assert "StateStore" not in source
    assert "ToolGateway" not in source
    assert "OpenAIResponsesAdapter" not in source
    assert "load_task" not in source
    assert ".execute(" not in source
    assert "saturation_recovery_shadow_qualification" not in runner
    assert "build_saturation_recovery_shadow_public_qualification" not in runner
