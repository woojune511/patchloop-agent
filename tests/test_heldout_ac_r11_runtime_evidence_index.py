from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals.heldout_ac_r11_campaign_evidence import (
    EXECUTION_HASH,
    OUTPUT_PATH,
    HeldoutACR11CampaignEvidence,
    HeldoutACR11CampaignEvidenceError,
    _build_candidate,
    _verify_historical_failure_event,
    revalidate_heldout_ac_r11_runtime_evidence,
    run_heldout_ac_r11_campaign_evidence,
    validate_heldout_ac_r11_campaign_evidence,
)
from patchloop.util import sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]


def _candidate() -> HeldoutACR11CampaignEvidence:
    return _build_candidate(recorded_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC))


def _database_snapshot() -> dict[str, tuple[int, str, int]]:
    snapshot: dict[str, tuple[int, str, int]] = {}
    for name in (
        "state.sqlite3",
        "state.sqlite3-wal",
        "state.sqlite3-shm",
        "state.sqlite3-journal",
    ):
        selected = ROOT / ".patchloop" / name
        if not selected.exists():
            continue
        raw = selected.read_bytes()
        snapshot[name] = (len(raw), sha256_bytes(raw), selected.stat().st_mtime_ns)
    return snapshot


def test_r11_candidate_binds_corrected_accounting_without_authority() -> None:
    payload = _candidate()

    assert payload.approval.execution_hash == EXECUTION_HASH
    assert payload.campaign_correction.model_dump(mode="json") == {
        "disposition": "inconclusive-matrix",
        "expected_runs": 48,
        "started_runs": 3,
        "terminal_settled_runs": 2,
        "observed_unsettled_runs": 1,
        "not_started_runs": 45,
        "settled_model_cost_nanos": 156_995_250,
        "observed_unsettled_model_cost_nanos": 261_021_000,
        "observed_started_model_cost_nanos": 418_016_250,
        "historical_result_cost_accounting_complete": False,
        "corrected_observation_accounting_complete": True,
        "analysis_ready": False,
        "official_heldout_analysis": False,
        "memory_benefit_claim_authorized": False,
        "broad_generalization_claim_authorized": False,
    }
    assert [row.outcome_kind for row in payload.observed_rows] == [
        "resolved",
        "task_failure",
        "infrastructure_error",
    ]
    assert [row.model_cost_nanos for row in payload.observed_rows] == [
        97_291_500,
        59_703_750,
        261_021_000,
    ]
    assert payload.authority.execution_candidates_created == 0
    assert payload.authority.provider_calls_made == 0
    assert payload.authority.docker_calls_made == 0
    assert payload.authority.added_model_cost_usd == 0.0


def test_r11_marker_and_failure_attribution_keep_runtime_and_successor_distinct() -> None:
    payload = _candidate()
    boundary = payload.marker_boundary
    failure = payload.failure_attribution

    assert boundary.evaluator_private_redaction_match_count == 14
    assert boundary.event_prefix_match_count == 0
    assert boundary.submitted_patch_match_count == 0
    assert boundary.agent_visible_marker_match_count == 0
    assert failure.historical_event.observed_runtime_error_code == "CONTRACT_ERROR"
    assert failure.successor_diagnosis_code == "EVALUATOR_CONTROL_CONTRACT_COLLISION"
    assert failure.historical_runtime_typed_code_observed is False
    assert failure.successor_diagnosis_is_post_runtime_deterministic_attribution is True
    serialized = payload.model_dump_json()
    assert "private marker escaped into the supplied evaluator evidence chain" not in serialized
    assert '"error_type":"ContractError"' not in serialized


def test_historical_failure_projection_is_closed_and_content_addressed() -> None:
    projection = _candidate().failure_attribution.historical_event
    assert projection.content_hash == sha256_json(
        projection.model_dump(mode="json", exclude={"content_hash"})
    )

    typed_rewrite = projection.model_dump(mode="json")
    typed_rewrite["observed_runtime_error_code"] = "EVALUATOR_CONTROL_CONTRACT_COLLISION"
    typed_rewrite["content_hash"] = sha256_json(
        {key: value for key, value in typed_rewrite.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError):
        type(projection).model_validate(typed_rewrite)

    message_injection = projection.model_dump(mode="json")
    message_injection["message"] = "do not persist raw diagnostics"
    message_injection["content_hash"] = sha256_json(
        {key: value for key, value in message_injection.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError):
        type(projection).model_validate(message_injection)


def test_r11_checked_in_index_is_canonical_and_idempotent() -> None:
    summary = validate_heldout_ac_r11_campaign_evidence(repository=ROOT)
    selected = ROOT / OUTPUT_PATH
    before = selected.read_bytes()
    before_mtime = selected.stat().st_mtime_ns

    assert summary["execution_hash"] == EXECUTION_HASH
    assert summary["file_bytes"] == len(before)
    assert summary["file_sha256"] == sha256_bytes(before)
    assert summary["runtime_revalidated"] is False
    rerun = run_heldout_ac_r11_campaign_evidence(repository=ROOT)
    assert rerun == summary
    assert selected.read_bytes() == before
    assert selected.stat().st_mtime_ns == before_mtime


def test_r11_runtime_revalidation_is_read_only_when_historical_files_exist() -> None:
    if not (ROOT / ".patchloop/state.sqlite3").is_file():
        return
    before = _database_snapshot()
    assert set(before) == {"state.sqlite3"}

    summary = revalidate_heldout_ac_r11_runtime_evidence(repository=ROOT)

    assert summary["runtime_revalidated"] is True
    assert summary["observed_unsettled_model_cost_nanos"] == 261_021_000
    assert _database_snapshot() == before


def test_missing_historical_database_fails_without_creating_state(tmp_path: Path) -> None:
    payload = _candidate()
    runtime_root = tmp_path / ".patchloop"
    runtime_root.mkdir()

    with pytest.raises(
        HeldoutACR11CampaignEvidenceError,
        match="checkpointed main-only snapshot",
    ):
        _verify_historical_failure_event(tmp_path, payload)

    assert list(runtime_root.iterdir()) == []
