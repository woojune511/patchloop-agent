from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals.heldout_ac_execution_source_qualification import (
    OUTPUT_PATH,
    R4_CONTENT_HASH,
    R4_FILE_BYTES,
    R4_FILE_SHA256,
    R4_PATH,
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


def test_offline_candidate_binds_paid_path_closure_without_authority() -> None:
    payload = _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 14, 10, 30, tzinfo=UTC),
    )

    assert payload.status == STATUS
    assert payload.schema_version == "heldout-ac-execution-source-qualification-v5"
    assert payload.qualification_id.endswith("20260815-r5")
    assert payload.source_entrypoints == tuple(item.as_posix() for item in SOURCE_ENTRYPOINTS)
    assert "patchloop/agent/runner.py" in payload.paid_path_import_closure
    assert "patchloop/verifier/core.py" in payload.paid_path_import_closure
    assert "patchloop/evals/heldout_ac_execution.py" in payload.paid_path_import_closure
    assert payload.projection.scheduled_rows == 48
    assert payload.projection.candidate_created is False
    assert payload.projection.runtime_secret_markers_materialized == 0
    assert payload.projection.final_evaluator_contracts_materialized == 0
    assert payload.predecessor.content_hash == R4_CONTENT_HASH
    assert payload.predecessor.disposition == "invalidated-by-final-r13-preflight-source-staging"
    assert payload.predecessor.invalidation_reason == (
        "final-r13-preflight-source-staged-after-execution-r4"
    )
    assert payload.predecessor.current_source_replay_valid is False
    assert payload.materialization.path.endswith("task-pricing-materialization-r4.json")
    assert payload.authority.heldout_task_packages_opened == 0
    assert payload.authority.credential_values_observed == 0
    assert payload.authority.provider_calls_made == 0
    assert payload.authority.docker_calls_made == 0
    assert payload.authority.added_model_cost_usd == 0.0


def test_paid_execution_closure_retains_lazy_runtime_modules() -> None:
    closure = {
        item.as_posix() for item in _paid_path_import_closure(ROOT, entrypoints=SOURCE_ENTRYPOINTS)
    }

    assert {
        "patchloop/evals/heldout_ac_execution.py",
        "patchloop/evals/heldout_ac_task_pricing_materialization.py",
        "patchloop/evals/heldout_ac_live_contract.py",
        "patchloop/evals/qualification.py",
        "patchloop/verifier/runtime_evidence.py",
    }.issubset(closure)


def test_r4_artifact_is_byte_preserved_as_an_immutable_predecessor() -> None:
    raw = (ROOT / R4_PATH).read_bytes()
    payload = json.loads(raw)

    assert len(raw) == R4_FILE_BYTES
    assert sha256_bytes(raw) == R4_FILE_SHA256
    assert payload["content_hash"] == R4_CONTENT_HASH
    assert payload["schema_version"] == "heldout-ac-execution-source-qualification-v4"
    assert payload["predecessor"]["path"].endswith(
        "heldout-ac-execution-source-qualification-r3.json"
    )


def test_source_qualification_rerun_is_byte_and_mtime_stable() -> None:
    selected = ROOT / OUTPUT_PATH
    before = selected.read_bytes()
    before_mtime = selected.stat().st_mtime_ns
    validated = validate_heldout_ac_execution_source_qualification(repository=ROOT)
    binding = load_heldout_ac_execution_source_binding(repository=ROOT)
    rerun = run_heldout_ac_execution_source_qualification(repository=ROOT)

    assert validated == rerun
    assert binding.source_qualification_hash == validated["source_qualification_hash"]
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
