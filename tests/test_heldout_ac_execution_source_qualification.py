from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals.heldout_ac_execution_source_qualification import (
    OUTPUT_PATH,
    SOURCE_ENTRYPOINTS,
    STATUS,
    _build_candidate,
    load_heldout_ac_execution_source_binding,
    run_heldout_ac_execution_source_qualification,
    validate_heldout_ac_execution_source_qualification,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_offline_candidate_binds_paid_path_closure_without_authority() -> None:
    payload = _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 14, 10, 30, tzinfo=UTC),
    )

    assert payload.status == STATUS
    assert payload.source_entrypoints == tuple(item.as_posix() for item in SOURCE_ENTRYPOINTS)
    assert "patchloop/agent/runner.py" in payload.paid_path_import_closure
    assert "patchloop/verifier/core.py" in payload.paid_path_import_closure
    assert "patchloop/evals/heldout_ac_execution.py" in payload.paid_path_import_closure
    assert payload.projection.scheduled_rows == 48
    assert payload.projection.candidate_created is False
    assert payload.projection.runtime_secret_markers_materialized == 0
    assert payload.projection.final_evaluator_contracts_materialized == 0
    assert payload.authority.heldout_task_packages_opened == 0
    assert payload.authority.credential_values_observed == 0
    assert payload.authority.provider_calls_made == 0
    assert payload.authority.docker_calls_made == 0
    assert payload.authority.added_model_cost_usd == 0.0


def test_source_qualification_artifact_replays_and_exports_binding() -> None:
    summary = validate_heldout_ac_execution_source_qualification(repository=ROOT)
    binding = load_heldout_ac_execution_source_binding(repository=ROOT)
    raw = (ROOT / OUTPUT_PATH).read_bytes()

    assert summary["status"] == STATUS
    assert summary["source_qualification_hash"] == binding.source_qualification_hash
    assert summary["evaluator_source_hash"] == binding.evaluator_source_hash
    assert binding.qualification_file.file_bytes == len(raw)
    assert binding.qualification_file.file_sha256 == sha256_bytes(raw)
    assert summary["execution_candidate_created"] is False
    assert summary["credential_values_observed"] == 0
    assert summary["provider_calls_made"] == 0


def test_source_qualification_rerun_is_byte_and_mtime_stable() -> None:
    selected = ROOT / OUTPUT_PATH
    before = selected.read_bytes()
    before_mtime = selected.stat().st_mtime_ns
    summary = run_heldout_ac_execution_source_qualification(repository=ROOT)

    assert summary["status"] == STATUS
    assert selected.read_bytes() == before
    assert selected.stat().st_mtime_ns == before_mtime


def test_source_qualification_rejects_rehashed_authority_escalation() -> None:
    payload = _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 14, 10, 30, tzinfo=UTC),
    )
    body = payload.model_dump(mode="json")
    body["authority"]["provider_evaluator_or_agent_execution_authorized"] = True
    with pytest.raises(ValidationError):
        type(payload).model_validate(body)


def test_source_qualification_does_not_observe_runtime_surfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import patchloop.environment as environment
    import patchloop.sandbox.runner as sandbox_runner

    def bomb(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("offline source qualification crossed a runtime boundary")

    monkeypatch.setattr(environment, "exact_openai_api_key_present", bomb)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "available", bomb)
    payload = _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 14, 10, 30, tzinfo=UTC),
    )
    assert payload.authority.sdk_calls_made == 0
    assert payload.authority.docker_calls_made == 0
