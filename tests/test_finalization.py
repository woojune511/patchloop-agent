from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.finalization import (
    R8_FINALIZATION_RESERVE_ARTIFACT_FILE_BYTES,
    R8_FINALIZATION_RESERVE_ARTIFACT_FILE_SHA256,
    R8_FINALIZATION_RESERVE_ARTIFACT_PATH,
    FinalizationRequestEvidence,
    FinalizationReserveContract,
    PhaseToolSurfaceProjection,
    load_r8_public_development_finalization_reserve,
    project_finalization_request_mode,
    project_phase_tool_surface,
    project_recounted_finalization_request,
    r8_public_development_finalization_reserve,
)
from patchloop.agent.phases import EvidenceState
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _reserve() -> FinalizationReserveContract:
    return r8_public_development_finalization_reserve()


def _phase_evidence(actions: tuple[str, ...]) -> EvidenceState:
    return EvidenceState(
        worktree_diff_hash="sha256:" + "0" * 64,
        mutation_event_sequence=1,
        mutation_present=True,
        completed_checks=("public-check",),
        pending_checks=(),
        current_diff_check_event_sequences=(2,),
        latest_check_sequence=2,
        review_event_sequence=3,
        review_presented_to_model=True,
        task_review_event_sequence=None,
        task_review_presented_to_model=False,
        task_review_coverage_complete=None,
        unresolved_coverage_target_ids=(),
        submission_ready=False,
        missing_evidence=("review_phase",),
        allowed_next_actions=actions,
    )


def _mode(**updates: int):
    values = {
        "requested_input_tokens": 10_000,
        "configured_max_output_tokens": 25_000,
        "input_tokens_used": 100_000,
        "output_tokens_used": 10_000,
        "max_cumulative_input_tokens": 1_000_000,
        "max_cumulative_output_tokens": 100_000,
        "max_total_tokens": 1_100_000,
    }
    values.update(updates)
    return project_finalization_request_mode(reserve=_reserve(), **values)


def _finalization_surface() -> PhaseToolSurfaceProjection:
    return project_phase_tool_surface(
        reserve=_reserve(),
        tool_schemas=TOOL_SCHEMAS_V2,
        phase_evidence=_phase_evidence(
            (
                "search_files",
                "read_file",
                "apply_patch",
                "run_check",
                "get_diff",
                "finish_task",
            )
        ),
        mode="finalization",
    )


def _rehash(body: dict[str, Any]) -> dict[str, Any]:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_r8_candidate_binds_public_development_evidence_and_zero_authority() -> None:
    reserve = _reserve()
    evidence = REPOSITORY / reserve.development_evidence_path

    assert evidence.stat().st_size == reserve.development_evidence_file_bytes
    assert sha256_bytes(evidence.read_bytes()) == reserve.development_evidence_file_sha256
    assert reserve.content_hash == (
        "sha256:9458bb1d59d51aaf94a082504a3883d799bf4d807ce7a83376bdc391ab6348db"
    )
    assert reserve.status == "development-candidate-runtime-closed"
    assert reserve.runtime_activation_authorized is False
    assert reserve.provider_calls_authorized is False
    assert reserve.fresh_panel_authorized is False
    assert reserve.requires_public_development_requalification is True
    assert reserve.raw_trace_replayable_from_checked_in_files is False


def test_append_only_candidate_artifact_is_exact_and_matches_source_contract() -> None:
    path = REPOSITORY / R8_FINALIZATION_RESERVE_ARTIFACT_PATH

    assert path.stat().st_size == R8_FINALIZATION_RESERVE_ARTIFACT_FILE_BYTES
    assert sha256_bytes(path.read_bytes()) == R8_FINALIZATION_RESERVE_ARTIFACT_FILE_SHA256
    assert load_r8_public_development_finalization_reserve(REPOSITORY) == _reserve()


def test_candidate_loader_reads_only_the_offline_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = Path.read_bytes
    reads: list[Path] = []

    def tracked(path: Path) -> bytes:
        reads.append(path.resolve())
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", tracked)

    loaded = load_r8_public_development_finalization_reserve(REPOSITORY)

    assert loaded == _reserve()
    assert reads == [(REPOSITORY / R8_FINALIZATION_RESERVE_ARTIFACT_PATH).resolve()]


def test_r8_candidate_derivation_is_exact_and_condition_balanced() -> None:
    reserve = _reserve()

    assert reserve.observed_max_model_turns == 5
    assert reserve.observed_max_requested_input_tokens_per_turn == 15_801
    assert reserve.observed_max_output_tokens_per_turn == 3_046
    assert reserve.max_requested_input_tokens_per_turn == 20_000
    assert reserve.max_output_tokens_per_turn == 5_000
    assert reserve.reserved_input_tokens == 100_000
    assert reserve.reserved_output_tokens == 25_000
    assert reserve.reserved_total_tokens == 125_000
    assert {(item.task_id, item.condition) for item in reserve.observations} == {
        ("moto-query-scanned-count", "no_memory"),
        ("moto-query-scanned-count", "structured"),
        ("babel-strict-grouped-decimal-trailing-zeroes", "no_memory"),
        ("babel-strict-grouped-decimal-trailing-zeroes", "structured"),
    }


def test_public_success_evidence_requires_read_file_but_not_search() -> None:
    reserve = _reserve()
    observed_tools = {
        tool for item in reserve.observations for turn in item.turns for tool in turn.tool_names
    }

    assert "read_file" in observed_tools
    assert "read_file" in reserve.finalization_tool_names
    assert "search_files" not in reserve.finalization_tool_names


def test_contract_rejects_rehashed_observation_drift_under_the_same_id() -> None:
    body = _reserve().model_dump(mode="python")
    body["observations"][0]["turns"][0]["output_tokens"] = 1_553
    body = _rehash(body)

    with pytest.raises(ValidationError):
        FinalizationReserveContract.model_validate(body)


def test_exploration_is_allowed_only_when_the_full_reserve_remains() -> None:
    projection = _mode()

    assert projection.mode == "exploration"
    assert projection.reserve_constrained_dimensions == ()
    assert projection.request_rebuild_required is False
    assert projection.exact_input_recount_required is False
    assert projection.investigation_allowed is True
    assert projection.provider_calls_authorized is False


@pytest.mark.parametrize(
    ("updates", "dimension"),
    [
        ({"input_tokens_used": 890_001}, "input_tokens"),
        ({"output_tokens_used": 50_001}, "output_tokens"),
        (
            {
                "input_tokens_used": 800_000,
                "output_tokens_used": 50_000,
                "max_total_tokens": 1_000_000,
            },
            "total_tokens",
        ),
    ],
)
def test_each_split_reserve_boundary_forces_rebuild_and_recount(
    updates: dict[str, int],
    dimension: str,
) -> None:
    projection = _mode(**updates)

    assert projection.mode == "finalization"
    assert dimension in projection.reserve_constrained_dimensions
    assert projection.request_rebuild_required is True
    assert projection.exact_input_recount_required is True
    assert projection.investigation_allowed is False


def test_no_remaining_split_budget_blocks_before_rebuild() -> None:
    projection = _mode(output_tokens_used=100_000)

    assert projection.mode == "block"
    assert projection.request_rebuild_required is False
    assert projection.exact_input_recount_required is False
    assert projection.investigation_allowed is False


def test_exploration_surface_is_exactly_phase_filtered_in_source_order() -> None:
    projection = project_phase_tool_surface(
        reserve=_reserve(),
        tool_schemas=TOOL_SCHEMAS_V2,
        phase_evidence=_phase_evidence(("read_file", "apply_patch")),
        mode="exploration",
    )

    assert projection.selected_tool_names == ("read_file", "apply_patch")
    assert projection.removed_tool_names == (
        "search_files",
        "run_check",
        "get_diff",
        "finish_task",
    )
    assert projection.request_rebuild_required is True
    assert projection.exact_input_recount_required is True


def test_finalization_surface_closes_search_and_preserves_public_suffix_tools() -> None:
    projection = _finalization_surface()

    assert projection.selected_tool_names == (
        "read_file",
        "apply_patch",
        "run_check",
        "get_diff",
        "finish_task",
    )
    assert projection.removed_tool_names == ("search_files",)
    assert projection.selected_tool_schemas == tuple(
        schema for schema in TOOL_SCHEMAS_V2 if schema["name"] != "search_files"
    )
    assert projection.source_tool_schema_hash != projection.selected_tool_schema_hash
    assert projection.provider_calls_authorized is False


def test_phase_filter_rejects_unknown_duplicate_or_empty_finalization_surface() -> None:
    with pytest.raises(ValueError, match="unknown tool"):
        project_phase_tool_surface(
            reserve=_reserve(),
            tool_schemas=TOOL_SCHEMAS_V2,
            phase_evidence=_phase_evidence(("unknown",)),
            mode="exploration",
        )
    with pytest.raises(ValueError, match="unique"):
        project_phase_tool_surface(
            reserve=_reserve(),
            tool_schemas=TOOL_SCHEMAS_V2,
            phase_evidence=_phase_evidence(("read_file", "read_file")),
            mode="exploration",
        )
    with pytest.raises(ValueError, match="no callable tool"):
        project_phase_tool_surface(
            reserve=_reserve(),
            tool_schemas=TOOL_SCHEMAS_V2,
            phase_evidence=_phase_evidence(("search_files",)),
            mode="finalization",
        )


def test_filter_copies_schema_bodies_before_hashing() -> None:
    schemas = [dict(item) for item in TOOL_SCHEMAS_V2]
    projection = project_phase_tool_surface(
        reserve=_reserve(),
        tool_schemas=schemas,
        phase_evidence=_phase_evidence(("read_file",)),
        mode="exploration",
    )
    schemas[1]["description"] = "mutated after projection"

    assert projection.selected_tool_schemas[0]["description"] != schemas[1]["description"]


def test_recounted_finalization_binds_filtered_surface_and_split_allowance() -> None:
    mode = _mode(output_tokens_used=50_001)
    surface = _finalization_surface()
    evidence = project_recounted_finalization_request(
        reserve=_reserve(),
        request_mode=mode,
        tool_surface=surface,
        recounted_input_tokens=8_000,
    )

    assert evidence.allowance.decision == "admit_full"
    assert evidence.allowance.configured_max_output_tokens == 5_000
    assert evidence.allowance.effective_max_output_tokens == 5_000
    assert evidence.recounted_input_tokens == 8_000
    assert evidence.tool_surface_hash == surface.content_hash
    assert evidence.provider_calls_authorized is False


def test_recounted_finalization_uses_the_exact_residual_output_allowance() -> None:
    mode = _mode(output_tokens_used=97_000)
    evidence = project_recounted_finalization_request(
        reserve=_reserve(),
        request_mode=mode,
        tool_surface=_finalization_surface(),
        recounted_input_tokens=8_000,
    )

    assert evidence.allowance.decision == "admit_reduced"
    assert evidence.allowance.effective_max_output_tokens == 3_000


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("recounted_input_tokens", 8_001),
        ("selected_tool_schema_hash", "sha256:" + "0" * 64),
        ("request_mode_hash", "sha256:" + "1" * 64),
    ],
)
def test_request_evidence_rejects_rehashed_cross_binding_drift(
    field: str,
    replacement: object,
) -> None:
    evidence = project_recounted_finalization_request(
        reserve=_reserve(),
        request_mode=_mode(output_tokens_used=50_001),
        tool_surface=_finalization_surface(),
        recounted_input_tokens=8_000,
    )
    body = evidence.model_dump(mode="python")
    body[field] = replacement
    body = _rehash(body)

    with pytest.raises(ValidationError):
        FinalizationRequestEvidence.model_validate(body)


def test_tool_surface_rejects_rehashed_selection_drift() -> None:
    body = _finalization_surface().model_dump(mode="python")
    body["selected_tool_schemas"] = body["selected_tool_schemas"][:-1]
    body["selected_tool_names"] = body["selected_tool_names"][:-1]
    body["removed_tool_names"] = (*body["removed_tool_names"], "finish_task")
    body["selected_tool_schema_hash"] = sha256_json(list(body["selected_tool_schemas"]))
    body = _rehash(body)

    with pytest.raises(ValidationError):
        PhaseToolSurfaceProjection.model_validate(body)


def test_tool_surface_rejects_rehashed_phase_evidence_drift() -> None:
    body = _finalization_surface().model_dump(mode="python")
    body["phase_evidence"]["submission_ready"] = True
    body = _rehash(body)

    with pytest.raises(ValidationError):
        PhaseToolSurfaceProjection.model_validate(body)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("requested_input_tokens", True),
        ("configured_max_output_tokens", 5.0),
    ],
)
def test_request_mode_rejects_noncanonical_scalar_inputs(
    field: str,
    replacement: object,
) -> None:
    with pytest.raises(TypeError):
        _mode(**{field: replacement})  # type: ignore[arg-type]


def test_projection_surface_has_no_condition_input() -> None:
    assert "condition" not in inspect.signature(project_finalization_request_mode).parameters
    assert "condition" not in inspect.signature(project_phase_tool_surface).parameters


def test_historical_runner_does_not_activate_the_candidate_contract() -> None:
    runner_source = (REPOSITORY / "patchloop/agent/runner.py").read_text(encoding="utf-8")

    assert "patchloop.agent.finalization" not in runner_source
    assert "project_finalization_request_mode" not in runner_source
