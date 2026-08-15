from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from patchloop.evals import heldout_ac_execution_source_qualification as source_q
from patchloop.evals.heldout_ac_execution_source_qualification import (
    MATERIALIZATION_CONTENT_HASH,
    MATERIALIZATION_FILE_BYTES,
    MATERIALIZATION_FILE_SHA256,
    MATERIALIZATION_PATH,
    MATERIALIZATION_SOURCE_HASH,
    OUTPUT_PATH,
    QUALIFICATION_ID,
    R6_CONTENT_HASH,
    R6_FILE_BYTES,
    R6_FILE_SHA256,
    R6_PATH,
    REQUIRED_PAID_PATHS,
    SCHEMA_VERSION,
    SOURCE_ENTRYPOINTS,
    STATUS,
    _build_candidate,
    _paid_path_import_closure,
    load_heldout_ac_execution_source_binding,
    run_heldout_ac_execution_source_qualification,
    validate_heldout_ac_execution_source_qualification,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def isolated_r7_output(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    relative = Path(".patchloop") / f"heldout-ac-execution-source-r7-{uuid4().hex}.json"
    selected = ROOT / relative
    assert not selected.exists()
    monkeypatch.setattr(source_q, "OUTPUT_PATH", relative)
    try:
        yield selected
    finally:
        if selected.exists() or selected.is_symlink():
            selected.unlink()


def test_offline_candidate_binds_paid_path_closure_without_authority() -> None:
    payload = _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 14, 10, 30, tzinfo=UTC),
    )

    assert payload.status == STATUS
    assert payload.schema_version == SCHEMA_VERSION
    assert payload.schema_version == "heldout-ac-execution-source-qualification-v7"
    assert payload.qualification_id == QUALIFICATION_ID
    assert payload.qualification_id.endswith("20260815-r7")
    assert OUTPUT_PATH.as_posix().endswith("heldout-ac-execution-source-qualification-r7.json")
    assert payload.source_entrypoints == tuple(item.as_posix() for item in SOURCE_ENTRYPOINTS)
    assert "patchloop/agent/runner.py" in payload.paid_path_import_closure
    assert "patchloop/verifier/core.py" in payload.paid_path_import_closure
    assert "patchloop/evals/heldout_ac_execution.py" in payload.paid_path_import_closure
    assert payload.projection.scheduled_rows == 48
    assert payload.projection.candidate_created is False
    assert payload.projection.runtime_secret_markers_materialized == 0
    assert payload.projection.final_evaluator_contracts_materialized == 0
    assert payload.projection.r6_predecessor_bytes_preserved is True
    assert payload.projection.materialization_r6_exact_binding_bound is True
    assert payload.projection.staged_r15_preflight_source_bound is True
    assert payload.projection.paid_dispatcher_source_bound is True
    assert payload.projection.current_candidate_schema == "heldout-ac-execution-candidate-v3"
    assert payload.projection.candidate_v3_realized_schedule_bound is True
    assert payload.projection.candidate_runtime_tuple_recomputed_before_plan_write is True
    assert payload.projection.runtime_tuple_candidate_bound_in_persisted_evidence is True
    assert payload.projection.campaign_cost_control_candidate_bound_in_persisted_evidence is True
    assert payload.projection.prior_row_runtime_cost_usage_budget_revalidated is True
    assert payload.predecessor.content_hash == R6_CONTENT_HASH
    assert payload.predecessor.disposition == (
        "invalidated-by-current-runtime-contract-and-r15-source-successor"
    )
    assert payload.predecessor.invalidation_reason == (
        "contract-binding-materialization-r6-candidate-v3-runtime-cost-and-r15-source-"
        "staged-after-execution-r6"
    )
    assert payload.predecessor.current_source_replay_valid is False
    assert payload.materialization.path == MATERIALIZATION_PATH.as_posix()
    assert payload.materialization.file_bytes == MATERIALIZATION_FILE_BYTES
    assert payload.materialization.file_sha256 == MATERIALIZATION_FILE_SHA256
    assert payload.materialization.content_hash == MATERIALIZATION_CONTENT_HASH
    assert payload.materialization.source_hash == MATERIALIZATION_SOURCE_HASH
    assert payload.authority.heldout_task_packages_opened == 0
    assert payload.authority.credential_values_observed == 0
    assert payload.authority.provider_calls_made == 0
    assert payload.authority.docker_calls_made == 0
    assert payload.authority.added_model_cost_usd == 0.0


def test_paid_execution_closure_retains_lazy_runtime_modules() -> None:
    closure = {
        item.as_posix() for item in _paid_path_import_closure(ROOT, entrypoints=SOURCE_ENTRYPOINTS)
    }

    assert set(REQUIRED_PAID_PATHS).issubset(closure)
    assert {
        "patchloop/evals/heldout_ac_completion.py",
        "patchloop/evals/heldout_ac_dispatcher.py",
        "patchloop/evals/heldout_ac_execution.py",
        "patchloop/evals/heldout_ac_task_pricing_materialization.py",
        "patchloop/evals/heldout_ac_live_contract.py",
        "patchloop/evals/heldout_ac_persisted_adapter.py",
        "patchloop/evals/heldout_ac_preflight_source_qualification.py",
        "patchloop/evals/qualification.py",
        "patchloop/verifier/runtime_evidence.py",
    }.issubset(closure)


def test_r6_artifact_is_byte_preserved_as_an_immutable_predecessor() -> None:
    raw = (ROOT / R6_PATH).read_bytes()
    payload = json.loads(raw)

    assert len(raw) == R6_FILE_BYTES
    assert sha256_bytes(raw) == R6_FILE_SHA256
    assert payload["content_hash"] == R6_CONTENT_HASH
    assert payload["schema_version"] == "heldout-ac-execution-source-qualification-v6"
    assert payload["predecessor"]["path"].endswith(
        "heldout-ac-execution-source-qualification-r5.json"
    )


def test_source_qualification_rerun_is_byte_and_mtime_stable(
    isolated_r7_output: Path,
) -> None:
    selected = isolated_r7_output
    created = run_heldout_ac_execution_source_qualification(repository=ROOT)
    before = selected.read_bytes()
    before_mtime = selected.stat().st_mtime_ns
    validated = validate_heldout_ac_execution_source_qualification(repository=ROOT)
    binding = load_heldout_ac_execution_source_binding(repository=ROOT)
    rerun = run_heldout_ac_execution_source_qualification(repository=ROOT)

    assert created == validated == rerun
    assert binding.source_qualification_hash == validated["source_qualification_hash"]
    assert binding.qualification_file.path == source_q.OUTPUT_PATH.as_posix()
    assert binding.qualification_file.file_bytes == len(before)
    assert binding.qualification_file.file_sha256 == sha256_bytes(before)
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
