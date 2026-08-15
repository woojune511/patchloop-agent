from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from patchloop.evals.heldout_ac_r16_campaign_evidence import (
    EXECUTION_HASH,
    OUTPUT_PATH,
    HeldoutACR16CampaignEvidence,
    HeldoutACR16CampaignEvidenceError,
    _build_candidate,
    _verify_runtime_files,
    revalidate_heldout_ac_r16_runtime_evidence,
    run_heldout_ac_r16_campaign_evidence,
    validate_heldout_ac_r16_campaign_evidence,
)
from patchloop.util import sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]


def _candidate() -> HeldoutACR16CampaignEvidence:
    return _build_candidate(recorded_at=datetime(2026, 8, 15, 18, 30, tzinfo=UTC))


def _bound_paths(payload: HeldoutACR16CampaignEvidence) -> tuple[Path, ...]:
    runtime = payload.runtime_files
    return tuple(ROOT / binding.path for binding in payload.source_chain) + tuple(
        ROOT / binding.path
        for binding in (
            runtime.candidate_preflight,
            runtime.execution_plan,
            runtime.journal,
            runtime.prepared_result,
            runtime.final_result,
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


def test_r16_candidate_records_complete_matrix_and_claim_boundary() -> None:
    payload = _candidate()
    observation = payload.campaign_observation
    authority = payload.authority

    assert payload.execution_hash == EXECUTION_HASH
    assert observation.terminal_settled_runs == 48
    assert observation.observed_unsettled_runs == 0
    assert observation.not_started_runs == 0
    assert observation.confounded_runs == 0
    assert observation.settled_model_cost_nanos == 27_244_658_250
    assert observation.analysis_ready is True
    assert observation.official_heldout_analysis is True
    assert observation.memory_benefit_claim_authorized is False
    assert observation.broad_generalization_claim_authorized is False
    assert authority.r16_campaign_is_immutable_and_consumed is True
    assert authority.official_frozen_panel_analysis_recorded is True
    assert authority.causal_or_general_memory_benefit_claim_authorized is False
    assert authority.future_candidate_or_paid_execution_authorized is False
    assert authority.provider_calls_made == 0
    assert authority.evaluator_calls_made == 0
    assert authority.agent_runs_made == 0
    assert authority.added_model_cost_usd == 0.0


def test_r16_official_analysis_summary_is_exact_and_descriptive() -> None:
    analysis = _candidate().official_analysis
    conditions = {item.condition: item for item in analysis.conditions}
    strata = {item.role: item for item in analysis.role_strata}

    assert analysis.primary_estimate.model_dump() == {"numerator": -1, "denominator": 24}
    assert conditions["no_memory"].successes == 8
    assert conditions["structured"].successes == 7
    assert analysis.stability_interval.lower.model_dump() == {
        "numerator": -1,
        "denominator": 4,
    }
    assert analysis.stability_interval.upper.model_dump() == {
        "numerator": 1,
        "denominator": 6,
    }
    assert analysis.stability_interval.confidence_interval_claim_authorized is False
    assert analysis.sign_flip_sensitivity.p_value.model_dump() == {
        "numerator": 1,
        "denominator": 1,
    }
    assert analysis.sign_flip_sensitivity.headline_use_authorized is False
    assert analysis.directional_flips.benefit_count == 3
    assert analysis.directional_flips.negative_transfer_count == 4
    assert strata["core-same-repo"].estimate.numerator == 0
    assert strata["core-cross-repo"].estimate.model_dump() == {
        "numerator": -1,
        "denominator": 12,
    }


def test_r16_rehashed_summary_or_claim_drift_is_rejected() -> None:
    body = _candidate().model_dump(mode="json")
    body["campaign_observation"]["memory_benefit_claim_authorized"] = True
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError):
        HeldoutACR16CampaignEvidence.model_validate(body)


def test_r16_strict_types_reject_bool_as_cost() -> None:
    body = _candidate().model_dump(mode="json")
    body["campaign_observation"]["settled_model_cost_nanos"] = True
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError):
        HeldoutACR16CampaignEvidence.model_validate(body)


def test_r16_evidence_module_has_no_execution_or_runtime_import() -> None:
    source = (ROOT / "patchloop/evals/heldout_ac_r16_campaign_evidence.py").read_text(
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
        "sqlite3",
    ):
        assert f"import {forbidden}" not in source
        assert f"from patchloop.evals.{forbidden}" not in source


def test_r16_checked_in_index_is_canonical_and_idempotent() -> None:
    summary = validate_heldout_ac_r16_campaign_evidence(repository=ROOT)
    selected = ROOT / OUTPUT_PATH
    before = selected.read_bytes()
    before_mtime = selected.stat().st_mtime_ns

    assert summary["execution_hash"] == EXECUTION_HASH
    assert summary["terminal_settled_runs"] == 48
    assert summary["observed_unsettled_runs"] == 0
    assert summary["not_started_runs"] == 0
    assert summary["settled_model_cost_nanos"] == 27_244_658_250
    assert summary["analysis_ready"] is True
    assert summary["official_heldout_analysis"] is True
    assert summary["primary_estimate"] == {"numerator": -1, "denominator": 24}
    assert summary["file_bytes"] == len(before)
    assert summary["file_sha256"] == sha256_bytes(before)
    assert summary["runtime_revalidated"] is False
    rerun = run_heldout_ac_r16_campaign_evidence(repository=ROOT)
    assert rerun == summary
    assert selected.read_bytes() == before
    assert selected.stat().st_mtime_ns == before_mtime


def test_r16_runtime_revalidation_is_read_only() -> None:
    payload = _candidate()
    paths = _bound_paths(payload)
    before = _snapshot(paths)

    summary = revalidate_heldout_ac_r16_runtime_evidence(repository=ROOT)

    assert summary["runtime_revalidated"] is True
    assert summary["settled_model_cost_nanos"] == 27_244_658_250
    assert _snapshot(paths) == before


def test_missing_runtime_fails_without_creating_files() -> None:
    missing_root = ROOT / ".patchloop" / f"missing-r16-evidence-{uuid4().hex}"
    assert not missing_root.exists()

    with pytest.raises(
        HeldoutACR16CampaignEvidenceError,
        match=r"evidence file is unavailable: \.patchloop/heldout-ac-preflight-r16",
    ):
        _verify_runtime_files(missing_root, _candidate())

    assert not missing_root.exists()
