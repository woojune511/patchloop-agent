from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from patchloop.evals.heldout_ac_r15_campaign_evidence import (
    EXECUTION_HASH,
    OUTPUT_PATH,
    HeldoutACR15CampaignEvidence,
    HeldoutACR15CampaignEvidenceError,
    _build_candidate,
    _verify_runtime_files,
    revalidate_heldout_ac_r15_runtime_evidence,
    run_heldout_ac_r15_campaign_evidence,
    validate_heldout_ac_r15_campaign_evidence,
)
from patchloop.util import sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]


def _candidate() -> HeldoutACR15CampaignEvidence:
    return _build_candidate(recorded_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC))


def _bound_paths(payload: HeldoutACR15CampaignEvidence) -> tuple[Path, ...]:
    runtime = payload.runtime_files
    return tuple(ROOT / binding.path for binding in payload.source_chain) + tuple(
        ROOT / binding.path
        for binding in (
            runtime.candidate_preflight,
            runtime.execution_plan,
            runtime.journal,
            runtime.prepared_result,
            runtime.final_result,
            runtime.confounded_result,
            runtime.confounded_qualification,
            runtime.confounded_usage,
            runtime.confounded_cost_observation,
        )
    )


def _snapshot(paths: tuple[Path, ...]) -> dict[str, tuple[int, str, int]]:
    return {
        path.relative_to(ROOT).as_posix(): (
            len(raw := path.read_bytes()),
            sha256_bytes(raw),
            path.stat().st_mtime_ns,
        )
        for path in paths
    }


def test_r15_candidate_preserves_terminal_accounting_without_authority() -> None:
    payload = _candidate()
    observation = payload.campaign_observation
    authority = payload.authority

    assert payload.execution_hash == EXECUTION_HASH
    assert observation.terminal_settled_runs == 2
    assert observation.observed_unsettled_runs == 1
    assert observation.not_started_runs == 45
    assert observation.settled_model_cost_nanos == 200_233_500
    assert observation.observed_unsettled_model_cost_nanos == 911_878_500
    assert observation.observed_started_model_cost_nanos == 1_112_112_000
    assert observation.analysis_ready is False
    assert observation.official_heldout_analysis is False
    assert observation.memory_benefit_claim_authorized is False
    assert authority.r15_campaign_is_immutable_and_consumed is True
    assert authority.historical_runtime_files_mutated is False
    assert authority.historical_row_reauthentication_authorized is False
    assert authority.retry_replacement_or_resume_performed is False
    assert authority.execution_candidates_created == 0
    assert authority.provider_calls_made == 0
    assert authority.evaluator_calls_made == 0
    assert authority.agent_runs_made == 0
    assert authority.docker_calls_made == 0
    assert authority.sdk_calls_made == 0
    assert authority.added_model_cost_usd == 0.0


def test_r15_budget_terminal_preserves_sanitized_result_and_typed_events() -> None:
    terminal = _candidate().budget_terminal

    assert terminal.result_terminal_error == {
        "code": "AGENT_SUBMISSION_FAILED",
        "phase": "agent",
    }
    assert terminal.failed_check_id == "terminal_result_integrity"
    assert terminal.failed_binding_required is True
    assert terminal.failed_binding_valid is False
    assert terminal.blocked_reason_code == "exact_request_budget_exceeded"
    assert terminal.blocked_error_code == "MODEL_GENERATION_BUDGET_EXCEEDED"
    assert terminal.blocked_payload_hash == terminal.terminal_error_details_hash
    assert terminal.usage.input_tokens == 992_884
    assert terminal.usage.output_tokens == 37_159
    assert terminal.usage.model_cost_nanos == 911_878_500


def test_r15_historical_reason_and_post_runtime_attribution_are_distinct() -> None:
    payload = _candidate()

    assert payload.historical_confound.historical_reason_code == (
        "DURABLE_EVIDENCE_AUTHENTICATION_FAILED"
    )
    assert payload.historical_confound.historical_reason_preserved_without_relabeling is True
    assert payload.post_runtime_attribution.diagnosis_code == (
        "TRACE_QUALIFICATION_V2_TERMINAL_RESULT_SCHEMA_MISMATCH"
    )
    assert payload.post_runtime_attribution.historical_typed_diagnosis_code_observed is False
    assert payload.post_runtime_attribution.changes_historical_reason_code is False
    assert payload.post_runtime_attribution.historical_row_reauthenticated is False
    assert payload.post_runtime_attribution.historical_row_reclassified is False
    assert payload.post_runtime_attribution.task_or_memory_effect_claimed is False
    serialized = payload.model_dump_json()
    assert '"message"' not in serialized
    assert "request_artifact_path" not in serialized


def test_r15_attribution_cannot_replace_historical_reason() -> None:
    body = _candidate().model_dump(mode="json")
    body["historical_confound"]["historical_reason_code"] = (
        "TRACE_QUALIFICATION_V2_TERMINAL_RESULT_SCHEMA_MISMATCH"
    )
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError):
        HeldoutACR15CampaignEvidence.model_validate(body)


def test_r15_evidence_module_has_no_execution_or_reauthentication_import() -> None:
    source = (ROOT / "patchloop/evals/heldout_ac_r15_campaign_evidence.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "heldout_ac_persisted_adapter",
        "heldout_ac_execution",
        "heldout_ac_dispatcher",
        "task_loader",
        "subprocess",
        "docker",
        "openai",
        "os.environ",
        "StateStore",
    ):
        assert f"import {forbidden}" not in source
        assert f"from patchloop.evals.{forbidden}" not in source


def test_r15_checked_in_index_is_canonical_and_idempotent() -> None:
    summary = validate_heldout_ac_r15_campaign_evidence(repository=ROOT)
    selected = ROOT / OUTPUT_PATH
    before = selected.read_bytes()
    before_mtime = selected.stat().st_mtime_ns

    assert summary["execution_hash"] == EXECUTION_HASH
    assert summary["terminal_settled_runs"] == 2
    assert summary["observed_unsettled_runs"] == 1
    assert summary["not_started_runs"] == 45
    assert summary["observed_started_model_cost_nanos"] == 1_112_112_000
    assert summary["file_bytes"] == len(before)
    assert summary["file_sha256"] == sha256_bytes(before)
    assert summary["runtime_revalidated"] is False
    rerun = run_heldout_ac_r15_campaign_evidence(repository=ROOT)
    assert rerun == summary
    assert selected.read_bytes() == before
    assert selected.stat().st_mtime_ns == before_mtime


def test_r15_runtime_revalidation_is_read_only() -> None:
    payload = _candidate()
    paths = _bound_paths(payload)
    before = _snapshot(paths)
    state = ROOT / ".patchloop/state.sqlite3"
    state_before = (
        state.stat().st_size,
        sha256_bytes(state.read_bytes()),
        state.stat().st_mtime_ns,
    )

    summary = revalidate_heldout_ac_r15_runtime_evidence(repository=ROOT)

    assert summary["runtime_revalidated"] is True
    assert summary["observed_started_model_cost_nanos"] == 1_112_112_000
    assert _snapshot(paths) == before
    assert (state.stat().st_size, sha256_bytes(state.read_bytes()), state.stat().st_mtime_ns) == (
        state_before
    )


def test_missing_runtime_fails_without_creating_files() -> None:
    missing_root = ROOT / ".patchloop" / f"missing-r15-evidence-{uuid4().hex}"
    assert not missing_root.exists()

    with pytest.raises(
        HeldoutACR15CampaignEvidenceError,
        match=r"evidence file is unavailable: \.patchloop/heldout-ac-preflight-r15",
    ):
        _verify_runtime_files(missing_root, _candidate())

    assert not missing_root.exists()
