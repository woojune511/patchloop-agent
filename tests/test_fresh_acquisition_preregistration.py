from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import patchloop.evals.fresh_acquisition_preregistration as preregistration_module
from patchloop.errors import ContractError
from patchloop.evals.fresh_acquisition_preregistration import (
    OUTPUT_PATH,
    FreshAcquisitionPreregistration,
    FreshAcquisitionPreregistrationError,
    build_fresh_acquisition_preregistration,
    load_fresh_acquisition_preregistration,
    materialize_fresh_acquisition_preregistration,
    preregistration_bytes,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]
FROZEN_TIME = "2026-08-17T12:00:00.000000Z"


def _build() -> FreshAcquisitionPreregistration:
    return build_fresh_acquisition_preregistration(REPOSITORY, preregistered_at=FROZEN_TIME)


def test_current_manifest_has_no_unused_fresh_core_panel() -> None:
    value = _build()

    assert value.current_pool_audit.manifest_task_count == 25
    assert value.current_pool_audit.consumed_core_task_count == 12
    assert value.current_pool_audit.unused_core_task_count == 0
    assert value.current_pool_audit.eligible_fresh_task_count == 0
    assert value.current_pool_audit.current_manifest_can_supply_fresh_panel is False
    assert value.current_pool_audit.current_core_exactly_matches_consumed_preregistration is True


def test_acquisition_rule_is_frozen_before_candidate_registry() -> None:
    value = _build()
    design = value.acquisition_design

    assert design.target_task_count == 12
    assert design.candidate_source_family == "SWE-rebench-leaderboard"
    assert design.source_snapshot_selection.startswith("earliest-published-immutable-revision")
    assert design.same_repository_task_count == design.cross_repository_task_count == 6
    assert len(design.same_repository_targets) == 6
    assert design.cross_repository_disjoint_from_all_current_manifest_repositories is True
    assert design.ranking_algorithm == "ascending-sha256-utf8"
    assert design.minimum_difficulty_tier == "medium"
    assert design.minimum_reference_pass_runs == 3
    assert design.minimum_rejected_bad_patches == 8
    assert design.experimental_model_runs_during_acquisition == 0
    assert design.r16_row_outcomes_or_traces_used_for_selection is False


def test_eventual_experiment_is_design_only_and_condition_neutral() -> None:
    value = _build()
    design = value.eventual_experiment_design

    assert design.conditions == ("no_memory", "structured")
    assert design.repetitions_per_task == 2
    assert design.expected_rows_after_panel_seal == 48
    assert design.harness == "lean-harness-v1"
    assert design.tool_schema == "v7"
    assert design.phase_evidence == "phase-evidence-v12"
    assert design.equal_condition_budget_required is True
    assert design.runtime_budget_binding == "pending-public-development-provider-qualification"
    assert design.partial_panel_primary_analysis_authorized is False


def test_all_runtime_and_claim_authority_is_closed() -> None:
    authority = _build().authority

    assert authority.task_package_files_read == 0
    assert authority.private_task_files_read == 0
    assert authority.r16_runtime_or_trace_files_read == 0
    assert authority.network_calls == authority.docker_calls == authority.provider_calls == 0
    assert authority.evaluator_calls == authority.agent_runs == 0
    assert authority.added_model_cost_usd == 0
    assert authority.candidate_registry_materialized is False
    assert authority.fresh_task_panel_materialized is False
    assert authority.full_experiment_preregistered is False
    assert authority.candidate_created is False
    assert authority.approval_granted is False
    assert authority.execution_authorized is False
    assert authority.memory_effect_analysis_authorized is False


def test_build_reads_only_four_frozen_metadata_or_evidence_files(
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
        "data/dataset-manifest.yaml",
        "experiments/heldout-ac-preregistration-20260814-v1.yaml",
        "experiments/lean-harness-runtime-source-qualification-20260817-v1.json",
        "reports/heldout-ac/artifacts/heldout-ac-r16-campaign-complete-r1.json",
    }
    assert all("tasks/" not in path for path in relative)
    assert all(".patchloop/" not in path for path in relative)


def test_r16_index_is_hash_bound_without_parsing_row_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    labels: list[str] = []
    original = preregistration_module._json_object

    def tracked(raw: bytes, *, label: str) -> dict[str, object]:
        labels.append(label)
        return original(raw, label=label)

    monkeypatch.setattr(preregistration_module, "_json_object", tracked)
    _build()

    assert labels == ["Lean source qualification"]


def test_module_has_no_runner_task_loader_or_external_execution_imports() -> None:
    source = Path(preregistration_module.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "from patchloop.agent.runner",
        "from patchloop.task_loader",
        "import subprocess",
        "import socket",
        "import openai",
        "import docker",
        "import requests",
    ):
        assert forbidden not in source.lower()


def test_materialization_is_append_only_and_idempotent(tmp_path: Path) -> None:
    output = tmp_path / "fresh-acquisition.json"
    relative = output.relative_to(REPOSITORY).as_posix()

    first = materialize_fresh_acquisition_preregistration(
        REPOSITORY,
        relative,
        preregistered_at=FROZEN_TIME,
    )
    before = output.stat().st_mtime_ns
    second = materialize_fresh_acquisition_preregistration(REPOSITORY, relative)

    assert first == second
    assert output.stat().st_mtime_ns == before
    assert output.read_bytes() == preregistration_bytes(first)


def test_canonical_artifact_loads_when_present() -> None:
    path = REPOSITORY / OUTPUT_PATH
    if not path.exists():
        pytest.skip("canonical fresh-acquisition preregistration is not materialized yet")
    value = load_fresh_acquisition_preregistration(REPOSITORY)
    assert value.status == "PREREGISTERED_ACQUISITION_CLOSED_NO_FRESH_TASKS"


def test_generic_experiment_loader_rejects_acquisition_preregistration() -> None:
    from patchloop.evals.runner import load_suite

    with pytest.raises(ContractError, match="experiment contract validation failed"):
        load_suite(REPOSITORY / OUTPUT_PATH)


def test_rehashed_semantic_drift_is_rejected(tmp_path: Path) -> None:
    value = _build()
    body = value.model_dump(mode="json")
    body["authority"]["execution_authorized"] = True
    body["content_hash"] = sha256_json(
        {key: item for key, item in body.items() if key != "content_hash"}
    )
    output = tmp_path / "drift.json"
    output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises((FreshAcquisitionPreregistrationError, ValidationError)):
        load_fresh_acquisition_preregistration(
            REPOSITORY, output.relative_to(REPOSITORY).as_posix()
        )


def test_extra_field_and_nonexact_scalar_types_are_rejected() -> None:
    body = _build().model_dump(mode="json")
    body["unexpected"] = True
    with pytest.raises(ValidationError):
        FreshAcquisitionPreregistration.model_validate(body)


def test_duplicate_json_key_is_rejected_before_interpretation(tmp_path: Path) -> None:
    output = tmp_path / "duplicate.json"
    output.write_text('{"schema_version":"x","schema_version":"y"}\n', encoding="utf-8")

    with pytest.raises(FreshAcquisitionPreregistrationError, match="duplicate JSON key"):
        load_fresh_acquisition_preregistration(
            REPOSITORY, output.relative_to(REPOSITORY).as_posix()
        )

    body = _build().model_dump(mode="json")
    body["current_pool_audit"]["manifest_task_count"] = 25.0
    with pytest.raises(ValidationError):
        FreshAcquisitionPreregistration.model_validate(body)
