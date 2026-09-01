from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.agent.context_event_compaction_qualification import (
    CONDITIONS,
    FRAME_PHASES,
    INTEGRATION_THRESHOLD_BASIS_POINTS,
    SOURCE_PATHS,
    TASK_PATHS,
    VALIDATION_PATHS,
    EventCompactionPublicQualification,
    build_event_compaction_public_qualification,
    load_event_compaction_public_qualification,
    materialize_event_compaction_public_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def qualification() -> EventCompactionPublicQualification:
    return build_event_compaction_public_qualification(REPOSITORY)


def _rehash(body: dict[str, object]) -> dict[str, object]:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_public_frame_is_explicit_synthetic_and_complete(
    qualification: EventCompactionPublicQualification,
) -> None:
    assert qualification.status == ("PUBLIC_BYTE_PROXY_EFFICIENCY_QUALIFIED_REQUEST_SHADOW_NEXT")
    assert qualification.frame_source == "deterministic-synthetic-public-events"
    assert qualification.live_public_trace_files_read == 0
    assert qualification.live_public_trace_replay_verified is False
    assert qualification.non_public_task_repository_files_read == 0
    assert tuple(item.path for item in qualification.task_bindings) == TASK_PATHS
    assert qualification.frame_phases == FRAME_PHASES
    assert qualification.conditions == CONDITIONS
    assert len(qualification.observations) == 24
    assert {(item.task_id, item.phase, item.condition) for item in qualification.observations} == {
        (task.task_id, phase, condition)
        for task in qualification.task_bindings
        for phase in FRAME_PHASES
        for condition in CONDITIONS
    }
    assert qualification.adapter_payload_builds == 48
    assert qualification.isolated_count_calls == 48
    assert qualification.provider_token_count_verified is False
    assert qualification.in_memory_fixture_artifacts == 8


def test_projection_passes_exact_efficiency_and_neutrality_gate(
    qualification: EventCompactionPublicQualification,
) -> None:
    assert qualification.structural_acceptance_passed is True
    assert qualification.exact_roundtrip_all is True
    assert qualification.direct_components_preserved_all is True
    assert qualification.tool_result_bodies_preserved_all is True
    assert qualification.artifact_id_and_path_preserved_all is True
    assert qualification.condition_neutral_projection is True
    assert qualification.every_context_nonincreasing is True
    assert qualification.every_proxy_count_nonincreasing is True
    assert qualification.efficiency_gate_passed is True
    assert qualification.request_shadow_integration_recommended is True
    assert qualification.public_integration_threshold_basis_points == (
        INTEGRATION_THRESHOLD_BASIS_POINTS
    )
    assert qualification.observed_proxy_reduction_basis_points_floor >= (
        INTEGRATION_THRESHOLD_BASIS_POINTS
    )
    assert qualification.frames_with_compaction > 0
    assert qualification.aggregate_removed_descriptor_count > 0
    assert qualification.aggregate_context_bytes_saved > 0
    assert qualification.aggregate_proxy_input_units_saved > 0
    assert all(
        item.projected_context_bytes <= item.source_context_bytes
        and item.projected_proxy_input_units <= item.source_proxy_input_units
        and item.exact_source_roundtrip is True
        and item.direct_components_preserved is True
        and item.tool_result_bodies_preserved is True
        and item.artifact_id_and_path_preserved is True
        for item in qualification.observations
    )
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for item in qualification.observations:
        grouped.setdefault((item.task_id, item.phase), {})[item.condition] = item
    for pair in grouped.values():
        no_memory = pair["no_memory"]
        structured = pair["structured"]
        assert no_memory.context_bytes_saved == structured.context_bytes_saved
        assert no_memory.proxy_input_units_saved == structured.proxy_input_units_saved
        assert no_memory.removed_descriptor_count == structured.removed_descriptor_count


def test_task_and_runtime_authority_boundaries_are_closed(
    qualification: EventCompactionPublicQualification,
) -> None:
    assert qualification.public_task_files_read == 2
    assert qualification.private_task_files_read == 0
    assert qualification.hidden_files_read == 0
    assert qualification.reference_patches_read == 0
    assert all(
        item.private_file_opened is False
        and item.hidden_file_opened is False
        and item.reference_patch_opened is False
        for item in qualification.task_bindings
    )
    assert qualification.provider_transport_calls == 0
    assert qualification.provider_generation_calls == 0
    assert qualification.runner_calls == 0
    assert qualification.docker_calls == 0
    assert qualification.evaluator_calls == 0
    assert qualification.added_model_cost_usd == 0
    assert qualification.provider_calls_authorized is False
    assert qualification.runner_activation_authorized is False
    assert qualification.request_shadow_integration_authorized is False
    assert qualification.state_mutation_authorized is False
    assert qualification.paid_execution_authorized is False


def test_build_read_scope_never_opens_private_task_or_oracle_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[str] = []
    original_open = Path.open
    original_read_bytes = Path.read_bytes
    original_read_text = Path.read_text

    def tracked_open(path: Path, *args, **kwargs):
        opened.append(str(path.resolve(strict=False)).replace("\\", "/"))
        return original_open(path, *args, **kwargs)

    def tracked_read_bytes(path: Path) -> bytes:
        opened.append(str(path.resolve(strict=False)).replace("\\", "/"))
        return original_read_bytes(path)

    def tracked_read_text(path: Path, *args, **kwargs) -> str:
        opened.append(str(path.resolve(strict=False)).replace("\\", "/"))
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracked_open)
    monkeypatch.setattr(Path, "read_bytes", tracked_read_bytes)
    monkeypatch.setattr(Path, "read_text", tracked_read_text)

    built = build_event_compaction_public_qualification(REPOSITORY)

    assert built.private_task_files_read == 0
    task_reads = [item for item in opened if "/tasks/" in item.lower()]
    assert task_reads
    assert {
        item.removeprefix(str(REPOSITORY).replace("\\", "/") + "/") for item in task_reads
    } == set(TASK_PATHS)
    assert not any(
        token in item.lower()
        for item in opened
        for token in ("/private.yaml", "/hidden", "/reference.patch")
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider_calls_authorized", True),
        ("runner_activation_authorized", True),
        ("request_shadow_integration_authorized", True),
        ("paid_execution_authorized", True),
        ("private_task_files_read", 1),
    ],
)
def test_rehashed_authority_or_scope_drift_is_rejected(
    qualification: EventCompactionPublicQualification,
    field: str,
    value: object,
) -> None:
    body = qualification.model_dump(mode="python")
    body[field] = value
    with pytest.raises(ValidationError):
        EventCompactionPublicQualification.model_validate(_rehash(body))


def test_rehashed_aggregate_or_observation_drift_is_rejected(
    qualification: EventCompactionPublicQualification,
) -> None:
    aggregate = qualification.model_dump(mode="python")
    aggregate["aggregate_proxy_input_units_saved"] += 1
    with pytest.raises(ValidationError, match="aggregate differs"):
        EventCompactionPublicQualification.model_validate(_rehash(aggregate))

    observation = qualification.model_dump(mode="python")
    observation["observations"][0]["projected_proxy_input_units"] += 1
    with pytest.raises(ValidationError, match="proxy savings differ"):
        EventCompactionPublicQualification.model_validate(_rehash(observation))

    identity = qualification.model_dump(mode="python")
    identity["observations"][0]["task_id"] = "forged-public-task"
    identity["observations"][0]["frame_id"] = sha256_json(
        {
            key: identity["observations"][0][key]
            for key in ("task_id", "task_path", "condition", "phase", "frame_order")
        }
    )
    with pytest.raises(ValidationError, match="observation identity differs"):
        EventCompactionPublicQualification.model_validate(_rehash(identity))


def test_source_and_validation_inventories_are_exact_current_bytes(
    qualification: EventCompactionPublicQualification,
) -> None:
    assert tuple(item.path for item in qualification.source_files) == SOURCE_PATHS
    assert tuple(item.path for item in qualification.validation_files) == VALIDATION_PATHS
    for item in (*qualification.source_files, *qualification.validation_files):
        content = (REPOSITORY / item.path).read_bytes()
        assert item.file_bytes == len(content)
        assert item.file_sha256 == sha256_bytes(content)


def test_materialization_is_append_only_canonical_and_replayable(
    tmp_path: Path,
) -> None:
    output = tmp_path / "qualification.json"
    first = materialize_event_compaction_public_qualification(REPOSITORY, output)
    first_bytes = output.read_bytes()
    first_mtime = output.stat().st_mtime_ns
    second = materialize_event_compaction_public_qualification(REPOSITORY, output)

    assert first == second
    assert output.read_bytes() == first_bytes == qualification_bytes(first)
    assert output.stat().st_mtime_ns == first_mtime
    assert load_event_compaction_public_qualification(REPOSITORY, output) == first


def test_qualification_has_no_runner_or_generation_surface() -> None:
    source = inspect.getsource(
        __import__(
            "patchloop.agent.context_event_compaction_qualification",
            fromlist=["context_event_compaction_qualification"],
        )
    )
    runner = (REPOSITORY / "patchloop/agent/runner.py").read_text(encoding="utf-8")
    shadow = (REPOSITORY / "patchloop/agent/shadow_runtime.py").read_text(encoding="utf-8")

    assert "load_task_package" not in source
    assert "private.yaml" not in source
    assert ".execute_request(" not in source
    assert "context_event_compaction_qualification" not in runner
    assert "project_lean_context_event_descriptors" not in runner
    assert "context_event_compaction_qualification" not in shadow
    assert "project_lean_context_event_descriptors" not in shadow
