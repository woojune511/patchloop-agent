from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.agent.context_event_shadow_qualification import (
    CONDITIONS,
    FRAME_PHASES,
    PREDECESSOR_BYTES,
    PREDECESSOR_CONTENT_HASH,
    PREDECESSOR_FILE_SHA256,
    PREDECESSOR_PATH,
    SOURCE_PATHS,
    TASK_PATHS,
    VALIDATION_PATHS,
    CompactedShadowPublicQualification,
    build_compacted_shadow_public_qualification,
    load_compacted_shadow_public_qualification,
    materialize_compacted_shadow_public_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def qualification() -> CompactedShadowPublicQualification:
    return build_compacted_shadow_public_qualification(REPOSITORY)


def _rehash(body: dict[str, object]) -> dict[str, object]:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_public_no_call_frame_binds_predecessor_and_current_runtime(
    qualification: CompactedShadowPublicQualification,
) -> None:
    assert qualification.status == ("PUBLIC_NO_CALL_SHADOW_PHASE_POLICY_QUALIFIED_RUNTIME_CLOSED")
    assert qualification.frame_source == "deterministic-synthetic-public-events"
    assert qualification.phase_evidence_source == (
        "rendered-phase-contract-derived-synthetic-evidence-state"
    )
    assert qualification.live_public_trace_files_read == 0
    assert qualification.live_public_trace_replay_verified is False
    assert qualification.non_public_task_repository_files_read == 0
    predecessor = qualification.predecessor_event_compaction
    assert predecessor.path == PREDECESSOR_PATH
    assert predecessor.file_bytes == PREDECESSOR_BYTES
    assert predecessor.file_sha256 == PREDECESSOR_FILE_SHA256
    assert qualification.predecessor_event_compaction_content_hash == (PREDECESSOR_CONTENT_HASH)
    assert qualification.runtime_input_limit == 1_000_000
    assert qualification.runtime_output_limit == 100_000
    assert qualification.runtime_total_limit == 1_100_000
    assert qualification.configured_max_output_tokens == 25_000
    assert tuple(item.path for item in qualification.task_bindings) == TASK_PATHS
    assert qualification.frame_phases == FRAME_PHASES
    assert qualification.conditions == CONDITIONS
    assert len(qualification.observations) == 24


def test_current_phase_surfaces_and_request_savings_are_exact(
    qualification: CompactedShadowPublicQualification,
) -> None:
    expected_tools = {
        "INTAKE": ("search_files", "read_file", "apply_patch", "run_check"),
        "REPRODUCE": ("search_files", "read_file", "apply_patch", "run_check"),
        "PLAN": ("search_files", "read_file", "apply_patch", "run_check"),
        "IMPLEMENT": ("search_files", "read_file", "apply_patch", "run_check"),
        "VERIFY": ("search_files", "read_file", "apply_patch", "get_diff"),
        "REVIEW": ("search_files", "read_file", "apply_patch", "get_diff"),
    }
    assert qualification.all_phase_tool_surfaces_exact is True
    assert qualification.all_request_modes_unchanged is True
    assert qualification.all_request_readiness_unchanged is True
    assert qualification.current_phase_policy_requalified is True
    assert qualification.exact_roundtrip_all is True
    assert qualification.condition_neutral_projection is True
    assert qualification.aggregate_counted_input_units_saved > 0
    assert qualification.aggregate_phase_request_bytes_saved > 0
    assert qualification.observed_phase_proxy_reduction_basis_points_floor >= 100
    assert qualification.frames_with_compaction == 20
    assert qualification.noop_frames == 4
    assert qualification.aggregate_removed_descriptor_count == 52
    assert all(
        item.selected_tool_names == expected_tools[item.phase]
        and item.request_mode == "exploration"
        and item.request_ready is True
        and item.phase_tool_surface_unchanged is True
        and item.exact_source_roundtrip is True
        for item in qualification.observations
    )
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for item in qualification.observations:
        grouped.setdefault((item.task_id, item.phase), {})[item.condition] = item
    for pair in grouped.values():
        no_memory = pair["no_memory"]
        structured = pair["structured"]
        assert no_memory.selected_tool_names == structured.selected_tool_names
        assert no_memory.phase_request_bytes_saved == (structured.phase_request_bytes_saved)
        assert no_memory.counted_input_units_saved == (structured.counted_input_units_saved)


def test_authority_and_private_boundaries_are_closed(
    qualification: CompactedShadowPublicQualification,
) -> None:
    assert qualification.public_task_files_read == 2
    assert qualification.private_task_files_read == 0
    assert qualification.hidden_files_read == 0
    assert qualification.reference_patches_read == 0
    assert qualification.in_memory_fixture_artifacts == 8
    assert qualification.adapter_payload_builds == 96
    assert qualification.isolated_count_calls == 48
    assert qualification.provider_transport_calls == 0
    assert qualification.provider_generation_calls == 0
    assert qualification.runner_calls == 0
    assert qualification.docker_calls == 0
    assert qualification.evaluator_calls == 0
    assert qualification.added_model_cost_usd == 0
    assert qualification.provider_calls_authorized is False
    assert qualification.runner_activation_authorized is False
    assert qualification.request_integration_authorized is False
    assert qualification.request_persistence_authorized is False
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

    built = build_compacted_shadow_public_qualification(REPOSITORY)

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
        ("request_integration_authorized", True),
        ("paid_execution_authorized", True),
        ("private_task_files_read", 1),
    ],
)
def test_rehashed_authority_or_scope_drift_is_rejected(
    qualification: CompactedShadowPublicQualification,
    field: str,
    value: object,
) -> None:
    body = qualification.model_dump(mode="python")
    body[field] = value
    with pytest.raises(ValidationError):
        CompactedShadowPublicQualification.model_validate(_rehash(body))


def test_rehashed_aggregate_observation_or_predecessor_drift_is_rejected(
    qualification: CompactedShadowPublicQualification,
) -> None:
    aggregate = qualification.model_dump(mode="python")
    aggregate["aggregate_counted_input_units_saved"] += 1
    with pytest.raises(ValidationError, match="aggregate differs"):
        CompactedShadowPublicQualification.model_validate(_rehash(aggregate))

    observation = qualification.model_dump(mode="python")
    observation["observations"][0]["compacted_phase_request_bytes"] += 1
    with pytest.raises(ValidationError, match="observation savings differ"):
        CompactedShadowPublicQualification.model_validate(_rehash(observation))

    phase_policy = qualification.model_dump(mode="python")
    phase_policy["observations"][0]["selected_tool_names"] = (
        "read_file",
        "apply_patch",
    )
    with pytest.raises(ValidationError, match="phase policy differs"):
        CompactedShadowPublicQualification.model_validate(_rehash(phase_policy))

    predecessor = qualification.model_dump(mode="python")
    predecessor["predecessor_event_compaction"]["file_bytes"] += 1
    with pytest.raises(ValidationError, match="predecessor differs"):
        CompactedShadowPublicQualification.model_validate(_rehash(predecessor))


def test_source_and_validation_inventories_are_exact_current_bytes(
    qualification: CompactedShadowPublicQualification,
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
    first = materialize_compacted_shadow_public_qualification(REPOSITORY, output)
    first_bytes = output.read_bytes()
    first_mtime = output.stat().st_mtime_ns
    second = materialize_compacted_shadow_public_qualification(REPOSITORY, output)

    assert first == second
    assert output.read_bytes() == first_bytes == qualification_bytes(first)
    assert output.stat().st_mtime_ns == first_mtime
    assert load_compacted_shadow_public_qualification(REPOSITORY, output) == first


def test_qualification_has_no_runner_or_generation_surface() -> None:
    source = inspect.getsource(
        __import__(
            "patchloop.agent.context_event_shadow_qualification",
            fromlist=["context_event_shadow_qualification"],
        )
    )
    runner = (REPOSITORY / "patchloop/agent/runner.py").read_text(encoding="utf-8")

    assert "load_task_package" not in source
    assert "private.yaml" not in source
    assert ".execute_request(" not in source
    assert "context_event_shadow" not in runner
    assert "project_lean_harness_compacted_shadow_request" not in runner
