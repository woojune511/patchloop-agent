from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals.heldout_ac_preflight_source_qualification import (
    OUTPUT_PATH,
    R2_PATH,
    R3_PATH,
    R4_PATH,
    R5_PATH,
    R6_PATH,
    SOURCE_ENTRYPOINTS,
    STATUS,
    _build_candidate,
    load_heldout_ac_preflight_source_binding,
    run_heldout_ac_preflight_source_qualification,
    validate_heldout_ac_preflight_source_qualification,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_offline_candidate_binds_preflight_closure_without_observation() -> None:
    payload = _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 14, 12, 30, tzinfo=UTC),
    )

    assert payload.status == STATUS
    assert payload.source_entrypoints == tuple(item.as_posix() for item in SOURCE_ENTRYPOINTS)
    assert "patchloop/agent/runner.py" in payload.import_closure
    assert "patchloop/evals/heldout_ac_preflight.py" in payload.import_closure
    assert "patchloop/evals/heldout_ac_preflight_source_qualification.py" in (
        payload.import_closure
    )
    assert payload.projection.scheduled_rows == 48
    assert payload.projection.r6_predecessor_bytes_preserved is True
    assert payload.projection.append_only_48_row_dispatcher_bound is True
    assert payload.projection.persisted_v2_authentication_bound is True
    assert payload.projection.persisted_campaign_replay_validator_bound is True
    assert payload.projection.preregistered_analysis_unlock_bound is True
    assert payload.projection.execution_candidates_created == 0
    assert payload.projection.approved_plans_created == 0
    assert payload.authority.git_docker_sdk_or_credential_observation_authorized is False
    assert payload.authority.credential_values_observed == 0
    assert payload.authority.provider_calls_made == 0
    assert payload.authority.docker_calls_made == 0
    assert payload.authority.added_model_cost_usd == 0.0


def test_r2_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R2_PATH
    assert len(selected.read_bytes()) == 15_725
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:5a06587069932599fd18aa7c2a3e72be098ccc0887b3b5906a6f5a0891391589"
    )


def test_r3_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R3_PATH
    assert len(selected.read_bytes()) == 18_334
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:88831118d5da9b9d0a826a49ef585a3532195003e78f8cb67c8b243ba4d4ff16"
    )


def test_r4_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R4_PATH
    assert len(selected.read_bytes()) == 18_354
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:5616484bc441baad27d5edd435aacdec7be292141a2f68b30bf9ae6dd9a45100"
    )


def test_r5_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R5_PATH
    assert len(selected.read_bytes()) == 18_415
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:6a46651ed3774ae3192e5674c57452220306d191f1f98ab76626e1cf5798bf5b"
    )


def test_r6_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R6_PATH
    assert len(selected.read_bytes()) == 18_413
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:10ccf88e9255c6ae0a0d8246ca8f2d478137bac03b7ffd7e6f59d23b938e942b"
    )


def test_preflight_source_artifact_replays_and_exports_binding() -> None:
    summary = validate_heldout_ac_preflight_source_qualification(repository=ROOT)
    binding = load_heldout_ac_preflight_source_binding(repository=ROOT)
    raw = (ROOT / OUTPUT_PATH).read_bytes()

    assert summary["status"] == STATUS
    assert summary["source_qualification_hash"] == binding.source_qualification_hash
    assert summary["evaluator_source_hash"] == binding.evaluator_source_hash
    assert binding.qualification_file.file_bytes == len(raw)
    assert binding.qualification_file.file_sha256 == sha256_bytes(raw)
    assert summary["execution_candidate_created"] is False
    assert summary["approved_plan_created"] is False
    assert summary["campaign_journal_created"] is False
    assert summary["credential_values_observed"] == 0
    assert summary["provider_calls_made"] == 0


def test_preflight_source_rerun_is_byte_and_mtime_stable() -> None:
    selected = ROOT / OUTPUT_PATH
    before = selected.read_bytes()
    before_mtime = selected.stat().st_mtime_ns
    summary = run_heldout_ac_preflight_source_qualification(repository=ROOT)

    assert summary["status"] == STATUS
    assert selected.read_bytes() == before
    assert selected.stat().st_mtime_ns == before_mtime


def test_preflight_source_rejects_rehashed_authority_escalation() -> None:
    payload = _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 14, 12, 30, tzinfo=UTC),
    )
    body = payload.model_dump(mode="json")
    body["authority"]["provider_evaluator_or_agent_execution_authorized"] = True
    with pytest.raises(ValidationError):
        type(payload).model_validate(body)


def test_preflight_source_qualification_does_not_observe_runtime_surfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import patchloop.environment as environment
    import patchloop.sandbox.runner as sandbox_runner

    def bomb(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("source qualification crossed a no-call runtime boundary")

    monkeypatch.setattr(environment, "exact_openai_api_key_present", bomb)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "available", bomb)
    payload = _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 14, 12, 30, tzinfo=UTC),
    )
    assert payload.authority.sdk_calls_made == 0
    assert payload.authority.docker_calls_made == 0
