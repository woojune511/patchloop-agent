from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.agent.lean_runtime_source_qualification import (
    CONSUMED_QUALIFICATION_FILE_BYTES,
    CONSUMED_QUALIFICATION_FILE_SHA256,
    QUALIFICATION_PATH,
    LeanRuntimeSourceQualification,
    load_lean_runtime_source_qualification,
    materialize_lean_runtime_source_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def test_public_mock_frame_builds_once_and_replays_append_only(tmp_path: Path) -> None:
    output = tmp_path / "lean-runtime-source-qualification.json"
    relative = output.relative_to(REPOSITORY).as_posix()

    first = materialize_lean_runtime_source_qualification(REPOSITORY, relative)
    before = output.stat().st_mtime_ns
    second = materialize_lean_runtime_source_qualification(REPOSITORY, relative)

    assert first == second
    assert output.read_bytes() == qualification_bytes(first)
    assert output.stat().st_mtime_ns == before
    assert first.resolved_rows == 12
    assert first.model_turns == first.persisted_request_evidence_rows == 60
    assert first.terminal_tool_calls == 60
    assert first.typed_token_terminals == 0
    assert all(item.non_memory_request_semantics_equal for item in first.pair_parity)
    assert first.boundary_revalidation.phase_surface_cases == 6
    assert first.boundary_revalidation.saturation_boundary_cases == 9
    assert first.boundary_revalidation.split_budget_terminal_dimensions == 3
    assert first.provider_transport_calls == first.provider_generation_calls == 0
    assert first.network_calls == first.docker_cli_calls == 0
    assert first.added_model_cost_usd == 0
    assert first.provider_calls_authorized is False
    assert first.paid_execution_authorized is False
    assert first.memory_effect_estimate_authorized is False


def test_canonical_qualification_loads_with_exact_closed_authority() -> None:
    qualification = load_lean_runtime_source_qualification(REPOSITORY)

    assert Path(QUALIFICATION_PATH).is_file()
    raw = Path(QUALIFICATION_PATH).read_bytes()
    assert len(raw) == CONSUMED_QUALIFICATION_FILE_BYTES
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == (
        CONSUMED_QUALIFICATION_FILE_SHA256
    )
    assert qualification.source_integration_completed is True
    assert qualification.source_qualification_completed is True
    assert qualification.validation_frame_executed is True
    assert qualification.future_runner_activation_authorized is False
    assert qualification.fresh_memory_comparison_authorized is False
    assert len(qualification.rows) == 12
    assert len(qualification.pair_parity) == 6


def test_rehashed_authority_or_row_drift_is_rejected() -> None:
    qualification = load_lean_runtime_source_qualification(REPOSITORY)
    body = qualification.model_dump(mode="python")
    body["provider_calls_authorized"] = True
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError):
        LeanRuntimeSourceQualification.model_validate(body)

    body = qualification.model_dump(mode="python")
    body["rows"][0]["tool_sequence"] = (
        "read_file",
        "run_check",
        "apply_patch",
        "get_diff",
        "finish_task",
    )
    row = body["rows"][0]
    row["observation_id"] = sha256_json(
        {key: value for key, value in row.items() if key != "observation_id"}
    )
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError, match="terminal tool sequence"):
        LeanRuntimeSourceQualification.model_validate(body)
