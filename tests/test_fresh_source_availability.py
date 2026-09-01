from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

import patchloop.evals.fresh_source_availability as availability_module
from patchloop.errors import ContractError
from patchloop.evals.fresh_source_availability import (
    OUTPUT_PATH,
    FreshSourceAvailabilityCheckpoint,
    FreshSourceAvailabilityError,
    build_fresh_source_availability_checkpoint,
    checkpoint_bytes,
    load_fresh_source_availability_checkpoint,
    materialize_fresh_source_availability_checkpoint,
)
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _build() -> FreshSourceAvailabilityCheckpoint:
    return build_fresh_source_availability_checkpoint(REPOSITORY)


def test_checkpoint_blocks_registry_without_relaxing_preregistration() -> None:
    value = _build()

    assert value.status == "NO_QUALIFYING_SNAPSHOT_OBSERVED_AT_CHECKPOINT"
    assert value.schema_version == "lean-harness-fresh-source-availability-v3"
    assert value.checkpoint_id == "lean-harness-fresh-source-availability-20260818-v3"
    assert value.required_snapshot.source_window_end_inclusive == "2026-08-16T23:59:59Z"
    assert value.decision.qualifying_snapshot_observed is False
    assert value.decision.candidate_registry_materialized is False
    assert value.decision.task_package_materialization_allowed is False
    assert value.decision.acquisition_rules_relaxed is False
    assert value.decision.disposition == "blocked-without-relaxation"


def test_predecessor_is_exact_and_remains_consumed() -> None:
    value = _build()
    selected = REPOSITORY / value.predecessor_binding.path
    raw = selected.read_bytes()

    assert len(raw) == value.predecessor_binding.file_bytes
    assert sha256_bytes(raw) == value.predecessor_binding.file_sha256
    assert value.predecessor_binding.content_hash == (
        "sha256:6c841590acf00d88605fd3e4095cf8b6626918bf95bc6e0a494ccba39d61efb3"
    )


def test_public_metadata_observations_are_exact_and_bounded() -> None:
    value = _build()
    hf = value.hugging_face_observation
    harbor = value.harbor_observation

    assert hf.data_tree_head_short_commit == "ab4805d"
    assert hf.latest_monthly_split_observed == "2026_03"
    assert hf.complete_frozen_window_observed is False
    assert harbor.direct_fetch_attempts == 2
    assert harbor.successful_direct_fetches == 0
    assert harbor.main_dataset_fetch_outcome == "timeout"
    assert harbor.august_snapshot_fetch_outcome == "safe-open-rejected"
    assert harbor.public_search_queries == 2
    assert harbor.public_search_results_observed == 0
    assert harbor.current_http_status_observed is False
    assert harbor.august_2026_monthly_snapshot_observed is False
    assert harbor.complete_frozen_window_observed is False


def test_remote_observation_limitations_are_explicit() -> None:
    limitations = _build().evidence_limitations

    assert limitations.direct_public_metadata_fetch_attempts == 4
    assert limitations.successful_authoritative_page_reads == 2
    assert limitations.inconclusive_harbor_fetches == 2
    assert limitations.search_queries_with_zero_results == 3
    assert limitations.harbor_current_status_established is False
    assert limitations.raw_http_response_bytes_persisted is False
    assert limitations.remote_page_file_hashes_recorded is False
    assert limitations.future_snapshot_availability_ruled_out is False
    assert limitations.task_validity_established is False
    assert limitations.registry_completeness_established is False


def test_all_task_runtime_and_claim_authority_is_closed() -> None:
    authority = _build().authority

    assert authority.public_metadata_browser_lookup_performed is True
    assert authority.public_metadata_fetches_attempted == 4
    assert authority.public_metadata_pages_read == 2
    assert authority.public_search_queries == 3
    assert authority.offline_builder_network_calls == 0
    assert authority.task_rows_downloaded == 0
    assert authority.task_package_files_read == 0
    assert authority.private_task_files_read == 0
    assert authority.oracle_solution_pages_opened == 0
    assert authority.r16_row_outcomes_or_traces_read == 0
    assert authority.docker_calls == authority.provider_calls == 0
    assert authority.evaluator_calls == authority.agent_runs == 0
    assert authority.added_model_cost_usd == 0
    assert authority.candidate_registry_materialized is False
    assert authority.fresh_task_panel_materialized is False
    assert authority.task_admission_authorized is False
    assert authority.candidate_created is False
    assert authority.approval_granted is False
    assert authority.execution_authorized is False
    assert authority.official_analysis_authorized is False
    assert authority.memory_effect_claim_authorized is False


def test_build_reads_only_the_sealed_preregistration_and_predecessor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reads: list[Path] = []
    original = Path.read_bytes

    def tracked(path: Path) -> bytes:
        reads.append(path.resolve(strict=False))
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", tracked)
    _build()

    relative = {path.relative_to(REPOSITORY).as_posix() for path in reads}
    assert relative == {
        "experiments/lean-harness-fresh-acquisition-preregistration-20260817-v1.json",
        "experiments/lean-harness-fresh-source-availability-20260818-v2.json",
    }
    assert all("tasks/" not in path for path in relative)
    assert all(".patchloop/" not in path for path in relative)


def test_build_performs_no_network_or_child_process_call(monkeypatch: pytest.MonkeyPatch) -> None:
    def bomb(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("availability builder attempted external execution")

    monkeypatch.setattr(socket, "create_connection", bomb)
    monkeypatch.setattr(socket.socket, "connect", bomb)
    monkeypatch.setattr(subprocess, "Popen", bomb)

    _build()


def test_module_has_no_runner_task_loader_or_external_execution_imports() -> None:
    source = Path(availability_module.__file__).read_text(encoding="utf-8").lower()
    for forbidden in (
        "from patchloop.agent.runner",
        "from patchloop.task_loader",
        "import subprocess",
        "import socket",
        "import openai",
        "import docker",
        "import requests",
        "import httpx",
        "import urllib",
    ):
        assert forbidden not in source


def test_materialization_is_append_only_offline_and_idempotent(tmp_path: Path) -> None:
    output = tmp_path / "fresh-source-availability.json"
    relative = output.relative_to(REPOSITORY).as_posix()

    first = materialize_fresh_source_availability_checkpoint(REPOSITORY, relative)
    before = output.stat().st_mtime_ns
    second = materialize_fresh_source_availability_checkpoint(REPOSITORY, relative)

    assert first == second
    assert output.stat().st_mtime_ns == before
    assert output.read_bytes() == checkpoint_bytes(first)


def test_canonical_artifact_loads_when_present() -> None:
    path = REPOSITORY / OUTPUT_PATH
    if not path.exists():
        pytest.skip("canonical fresh-source availability checkpoint is not materialized yet")
    value = load_fresh_source_availability_checkpoint(REPOSITORY)
    assert value.decision.qualifying_snapshot_observed is False
    assert value.predecessor_binding.path.endswith("20260818-v2.json")


def test_generic_experiment_loader_rejects_availability_checkpoint(tmp_path: Path) -> None:
    from patchloop.evals.runner import load_suite

    output = tmp_path / "availability.json"
    output.write_bytes(checkpoint_bytes(_build()))
    with pytest.raises(ContractError, match="experiment contract validation failed"):
        load_suite(output)


@pytest.mark.parametrize(
    ("section", "field", "replacement"),
    [
        ("decision", "qualifying_snapshot_observed", True),
        ("decision", "acquisition_rules_relaxed", True),
        ("authority", "task_rows_downloaded", 1),
        ("authority", "execution_authorized", True),
        ("evidence_limitations", "harbor_current_status_established", True),
        ("hugging_face_observation", "latest_monthly_split_observed", "2026_08"),
    ],
)
def test_rehashed_semantic_drift_is_rejected(
    tmp_path: Path, section: str, field: str, replacement: object
) -> None:
    body = _build().model_dump(mode="json")
    body[section][field] = replacement
    body["content_hash"] = sha256_json(
        {key: item for key, item in body.items() if key != "content_hash"}
    )
    output = tmp_path / f"drift-{section}-{field}.json"
    output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises((FreshSourceAvailabilityError, ValidationError)):
        load_fresh_source_availability_checkpoint(
            REPOSITORY, output.relative_to(REPOSITORY).as_posix()
        )


def test_extra_field_and_nonexact_scalar_types_are_rejected() -> None:
    body = _build().model_dump(mode="json")
    body["unexpected"] = True
    with pytest.raises(ValidationError):
        FreshSourceAvailabilityCheckpoint.model_validate(body)

    body = _build().model_dump(mode="json")
    body["harbor_observation"]["direct_fetch_attempts"] = 2.0
    with pytest.raises(ValidationError):
        FreshSourceAvailabilityCheckpoint.model_validate(body)


def test_duplicate_json_key_is_rejected_before_interpretation(tmp_path: Path) -> None:
    output = tmp_path / "duplicate.json"
    output.write_text('{"schema_version":"x","schema_version":"y"}\n', encoding="utf-8")

    with pytest.raises(FreshSourceAvailabilityError, match="duplicate JSON key"):
        load_fresh_source_availability_checkpoint(
            REPOSITORY, output.relative_to(REPOSITORY).as_posix()
        )
