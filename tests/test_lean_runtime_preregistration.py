from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.lean_runtime_preregistration import (
    PREREGISTRATION_PATH,
    DevelopmentValidationContract,
    LeanRuntimeContract,
    LeanRuntimeIntegrationPreregistration,
    build_lean_runtime_integration_preregistration,
    load_lean_runtime_integration_preregistration,
    materialize_lean_runtime_integration_preregistration,
    preregistration_bytes,
)
from patchloop.errors import RecoveryError
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _rehash_preregistration(**updates: Any) -> dict[str, Any]:
    body = build_lean_runtime_integration_preregistration(REPOSITORY).model_dump(mode="python")
    body.update(updates)
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def _rehash_nested(body: dict[str, Any]) -> dict[str, Any]:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_preregistration_freezes_an_outcome_blind_public_calibration_frame() -> None:
    preregistration = build_lean_runtime_integration_preregistration(REPOSITORY)
    frame = preregistration.development_validation

    assert preregistration.status == "PREREGISTERED_SOURCE_AND_EXECUTION_CLOSED"
    assert frame.frame_kind == "deterministic-public-calibration-integration"
    assert frame.prior_lean_runtime_outcomes_used_for_selection is False
    assert [item.task_id for item in frame.tasks] == [
        "config-falsy-override",
        "csv-quoted-newline",
        "path-prefix-boundary",
    ]
    assert all(item.role == "calibration" for item in frame.tasks)
    assert all(item.contamination_risk == "none" for item in frame.tasks)
    assert frame.unseen_task_or_population_claimed is False
    assert frame.quality_effect_estimate_authorized is False
    assert frame.memory_effect_estimate_authorized is False


def test_schedule_is_balanced_adjacent_and_orientation_reversed() -> None:
    frame = build_lean_runtime_integration_preregistration(REPOSITORY).development_validation

    assert len(frame.schedule) == 12
    assert [row.order for row in frame.schedule] == list(range(1, 13))
    assert sum(row.condition == "no_memory" for row in frame.schedule) == 6
    assert sum(row.condition == "structured" for row in frame.schedule) == 6
    for task in frame.tasks:
        blocks = []
        for repetition in (1, 2):
            block = [
                row
                for row in frame.schedule
                if row.task_id == task.task_id and row.repetition == repetition
            ]
            assert len(block) == 2
            assert block[1].order == block[0].order + 1
            assert {row.condition for row in block} == {"no_memory", "structured"}
            blocks.append(block[0].orientation)
        assert blocks[0] != blocks[1]
    assert frame.realized_schedule_hash == sha256_json(
        [item.model_dump(mode="json") for item in frame.schedule]
    )


def test_runtime_contract_freezes_version_pipeline_and_condition_neutrality() -> None:
    runtime = build_lean_runtime_integration_preregistration(REPOSITORY).runtime_contract

    assert runtime.runtime_policy_version == "lean-harness-v1"
    assert runtime.proposed_tool_schema_version == "v7"
    assert runtime.proposed_context_policy_version == "phase-evidence-v12"
    assert runtime.system_prompt_version == "SYSTEM_PROMPT_V3"
    assert runtime.base_tool_schema_version == "v2"
    assert runtime.model_provider == "mock"
    assert runtime.conditions == ("no_memory", "structured")
    assert runtime.tool_filter_is_condition_neutral is True
    assert runtime.budget_policy_is_condition_neutral is True
    assert runtime.semantic_replay_threshold == 4
    assert runtime.no_progress_streak_threshold == 2
    assert runtime.patch_rejection_threshold == 2
    assert runtime.finalization_max_output_tokens == 5_000
    assert runtime.provider_request_requires_persisted_evidence is True
    assert runtime.no_fallback_to_legacy_after_opt_in is True


def test_preregistration_grants_no_runtime_or_analysis_authority() -> None:
    preregistration = build_lean_runtime_integration_preregistration(REPOSITORY)

    assert preregistration.provider_transport_calls == 0
    assert preregistration.provider_generation_calls == 0
    assert preregistration.runner_calls == 0
    assert preregistration.tool_execution_calls == 0
    assert preregistration.docker_calls == 0
    assert preregistration.evaluator_calls == 0
    assert preregistration.added_model_cost_usd == 0
    assert preregistration.source_integration_completed is False
    assert preregistration.source_qualification_completed is False
    assert preregistration.validation_frame_executed is False
    assert preregistration.provider_calls_authorized is False
    assert preregistration.runner_activation_authorized is False
    assert preregistration.tool_policy_activation_authorized is False
    assert preregistration.request_integration_authorized is False
    assert preregistration.state_mutation_authorized is False
    assert preregistration.paid_execution_authorized is False
    assert preregistration.fresh_memory_comparison_authorized is False
    assert preregistration.official_analysis_authorized is False


def test_builder_reads_only_manifest_predecessors_and_own_source_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = Path.read_bytes
    reads: list[Path] = []

    def tracked(path: Path) -> bytes:
        reads.append(path.resolve())
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", tracked)

    preregistration = build_lean_runtime_integration_preregistration(REPOSITORY)

    expected = {
        (REPOSITORY / preregistration.dataset_manifest.path).resolve(),
        *(
            (REPOSITORY / item.path).resolve()
            for item in (
                *preregistration.predecessor_artifacts,
                *preregistration.source_files,
                *preregistration.validation_files,
            )
        ),
    }
    assert set(reads) == expected
    assert len(reads) == 8
    assert not any("tasks" in path.parts for path in reads)
    assert not any(path.name == "state.sqlite3" for path in reads)


def test_predecessor_bytes_and_content_hashes_are_exact() -> None:
    preregistration = build_lean_runtime_integration_preregistration(REPOSITORY)

    for binding in preregistration.predecessor_artifacts:
        raw = (REPOSITORY / binding.path).read_bytes()
        payload = json.loads(raw)
        assert len(raw) == binding.file_bytes
        assert sha256_bytes(raw) == binding.file_sha256
        assert payload["content_hash"] == binding.content_hash


def test_runtime_contract_rejects_rehashed_semantic_drift() -> None:
    preregistration = build_lean_runtime_integration_preregistration(REPOSITORY)
    runtime = preregistration.runtime_contract.model_dump(mode="python")
    runtime["semantic_replay_threshold"] = 5
    _rehash_nested(runtime)

    with pytest.raises(ValidationError):
        LeanRuntimeContract.model_validate(runtime)


def test_frame_rejects_fully_rehashed_condition_orientation_drift() -> None:
    preregistration = build_lean_runtime_integration_preregistration(REPOSITORY)
    frame = preregistration.development_validation.model_dump(mode="python")
    row = frame["schedule"][0]
    row["condition"] = "structured"
    identity = {key: value for key, value in row.items() if key != "row_id"}
    identity["preregistration_id"] = preregistration.preregistration_id
    row["row_id"] = sha256_json(identity)
    frame["realized_schedule_hash"] = sha256_json(frame["schedule"])
    _rehash_nested(frame)

    with pytest.raises(ValidationError, match="condition denominator|A/C"):
        DevelopmentValidationContract.model_validate(frame)


def test_frame_rejects_rehashed_task_binding_drift() -> None:
    preregistration = build_lean_runtime_integration_preregistration(REPOSITORY)
    frame = preregistration.development_validation.model_dump(mode="python")
    task = frame["tasks"][0]
    task["public_spec_hash"] = "sha256:" + "0" * 64
    task["entry_hash"] = sha256_json(
        {key: value for key, value in task.items() if key != "entry_hash"}
    )
    _rehash_nested(frame)

    with pytest.raises(ValidationError, match="task binding differs"):
        DevelopmentValidationContract.model_validate(frame)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider_calls_authorized", True),
        ("runner_calls", 1),
        ("r16_artifact_files_read", 1),
        ("validation_frame_executed", True),
        ("paid_execution_authorized", True),
        ("official_analysis_authorized", True),
    ],
)
def test_preregistration_rejects_authority_or_observation_drift(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        LeanRuntimeIntegrationPreregistration.model_validate(
            _rehash_preregistration(**{field: value})
        )


def test_preregistration_models_reject_extra_fields_and_raw_type_drift() -> None:
    with pytest.raises(ValidationError):
        LeanRuntimeIntegrationPreregistration.model_validate(
            _rehash_preregistration(unregistered=True)
        )

    runtime = build_lean_runtime_integration_preregistration(
        REPOSITORY
    ).runtime_contract.model_dump(mode="python")
    runtime["max_model_calls"] = 240.0
    _rehash_nested(runtime)
    with pytest.raises(ValidationError):
        LeanRuntimeContract.model_validate(runtime)


def test_preregistration_bytes_are_deterministic_and_round_trip() -> None:
    first = build_lean_runtime_integration_preregistration(REPOSITORY)
    second = build_lean_runtime_integration_preregistration(REPOSITORY)
    raw = preregistration_bytes(first)

    assert first == second
    assert raw == preregistration_bytes(second)
    assert raw.endswith(b"\n")
    assert LeanRuntimeIntegrationPreregistration.model_validate_json(raw) == first


def test_loader_rejects_duplicate_json_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = preregistration_bytes(build_lean_runtime_integration_preregistration(REPOSITORY))
    duplicate = raw.replace(
        b'{\n  "schema_version":',
        b'{\n  "schema_version": "duplicate",\n  "schema_version":',
        1,
    )
    original = Path.read_bytes

    def fake(path: Path) -> bytes:
        if path.name == "duplicate-lean-runtime.json":
            return duplicate
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", fake)

    with pytest.raises(RecoveryError, match="invalid JSON"):
        load_lean_runtime_integration_preregistration(
            REPOSITORY,
            "experiments/duplicate-lean-runtime.json",
        )


def test_builder_rejects_predecessor_byte_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    preregistration = build_lean_runtime_integration_preregistration(REPOSITORY)
    target = (REPOSITORY / preregistration.predecessor_artifacts[0].path).resolve()
    original = Path.read_bytes

    def drift(path: Path) -> bytes:
        raw = original(path)
        return raw + b" " if path.resolve() == target else raw

    monkeypatch.setattr(Path, "read_bytes", drift)

    with pytest.raises(RecoveryError, match="predecessor differs"):
        build_lean_runtime_integration_preregistration(REPOSITORY)


def test_canonical_artifact_loads_exactly_after_materialization() -> None:
    path = REPOSITORY / PREREGISTRATION_PATH
    if not path.exists():
        pytest.skip("canonical Lean Harness preregistration is not materialized yet")

    loaded = load_lean_runtime_integration_preregistration(REPOSITORY)

    assert path.read_bytes() == preregistration_bytes(loaded)
    assert loaded == build_lean_runtime_integration_preregistration(REPOSITORY)


def test_materializer_is_append_only_and_idempotent_after_seal() -> None:
    path = REPOSITORY / PREREGISTRATION_PATH
    if not path.exists():
        pytest.skip("canonical Lean Harness preregistration is not materialized yet")
    before = path.stat().st_mtime_ns
    first = materialize_lean_runtime_integration_preregistration(REPOSITORY)
    second = materialize_lean_runtime_integration_preregistration(REPOSITORY)

    assert first == second
    assert path.stat().st_mtime_ns == before


def test_source_has_no_runner_provider_task_loader_or_runtime_dependency() -> None:
    source = (REPOSITORY / "patchloop/agent/lean_runtime_preregistration.py").read_text(
        encoding="utf-8"
    )

    assert "patchloop.agent.runner" not in source
    assert "patchloop.task_loader" not in source
    assert "openai" not in source.lower()
    assert "subprocess" not in source
    assert "socket" not in source
    assert "state.sqlite3" not in source
