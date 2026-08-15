from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from patchloop.evals.heldout_ac_r14_campaign_evidence import (
    EXECUTION_HASH,
    OUTPUT_PATH,
    HeldoutACR14CampaignEvidence,
    HeldoutACR14CampaignEvidenceError,
    _build_candidate,
    _verify_runtime_files,
    revalidate_heldout_ac_r14_runtime_evidence,
    run_heldout_ac_r14_campaign_evidence,
    validate_heldout_ac_r14_campaign_evidence,
)
from patchloop.util import sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]


def _candidate() -> HeldoutACR14CampaignEvidence:
    return _build_candidate(recorded_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC))


def _bound_paths(payload: HeldoutACR14CampaignEvidence) -> tuple[Path, ...]:
    historical = payload.historical_source
    chain = payload.historical_source_chain
    runtime = payload.runtime_files
    row = payload.observed_row
    bindings = (
        historical.suite_file,
        historical.source_qualification,
        chain.contract_source,
        chain.binding_adapter_source,
        chain.task_pricing_materialization,
        chain.execution_source,
        runtime.candidate_preflight,
        runtime.execution_plan,
        runtime.journal,
        runtime.prepared_result,
        runtime.final_result,
        row.result,
        row.qualification,
        row.receipt,
        row.usage,
        row.cost_observation,
    )
    return tuple(ROOT / binding.path for binding in bindings)


def _snapshot(paths: tuple[Path, ...]) -> dict[str, tuple[int, str, int]]:
    return {
        path.relative_to(ROOT).as_posix(): (
            len(raw := path.read_bytes()),
            sha256_bytes(raw),
            path.stat().st_mtime_ns,
        )
        for path in paths
    }


def test_r14_candidate_preserves_terminal_accounting_without_authority() -> None:
    payload = _candidate()

    assert payload.approval.execution_hash == EXECUTION_HASH
    assert payload.campaign_observation.model_dump(mode="json") == {
        "disposition": "inconclusive-matrix",
        "expected_runs": 48,
        "started_runs": 1,
        "terminal_settled_runs": 0,
        "observed_unsettled_runs": 1,
        "not_started_runs": 47,
        "settled_model_cost_nanos": 0,
        "observed_unsettled_model_cost_nanos": 126_342_000,
        "observed_started_model_cost_nanos": 126_342_000,
        "historical_result_cost_accounting_complete": True,
        "analysis_ready": False,
        "official_heldout_analysis": False,
        "memory_benefit_claim_authorized": False,
        "broad_generalization_claim_authorized": False,
        "campaign_settlement_preserved_without_reauthentication": True,
    }
    assert payload.authority.r14_campaign_is_immutable_and_consumed is True
    assert payload.authority.historical_runtime_files_mutated is False
    assert payload.authority.historical_row_reauthentication_authorized is False
    assert payload.authority.retry_replacement_or_resume_performed is False
    assert payload.authority.execution_candidates_created == 0
    assert payload.authority.provider_calls_made == 0
    assert payload.authority.evaluator_calls_made == 0
    assert payload.authority.agent_runs_made == 0
    assert payload.authority.docker_calls_made == 0
    assert payload.authority.sdk_calls_made == 0
    assert payload.authority.added_model_cost_usd == 0.0


def test_r14_historical_reason_and_post_runtime_attribution_are_distinct() -> None:
    payload = _candidate()
    historical = payload.historical_confound
    attribution = payload.post_runtime_attribution

    assert historical.historical_reason_code == "DURABLE_EVIDENCE_AUTHENTICATION_FAILED"
    assert historical.historical_reason_preserved_without_relabeling is True
    assert attribution.diagnosis_code == ("TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH")
    assert attribution.historical_typed_diagnosis_code_observed is False
    assert attribution.post_runtime_deterministic_attribution is True
    assert attribution.changes_historical_reason_code is False
    assert attribution.historical_row_reauthenticated is False
    assert attribution.historical_row_reclassified is False
    assert attribution.candidate_budget.max_cumulative_input_tokens == 1_000_000
    assert attribution.candidate_budget.max_cumulative_output_tokens == 100_000
    assert attribution.candidate_budget.max_total_tokens == 1_100_000
    assert attribution.immutable_suite_budget.max_cumulative_input_tokens == 4_000_000
    assert attribution.immutable_suite_budget.max_cumulative_output_tokens == 500_000
    assert attribution.immutable_suite_budget.max_total_tokens == 4_500_000
    serialized = payload.model_dump_json()
    assert '"message"' not in serialized


def test_r14_underlying_task_failure_is_not_reclassified_as_campaign_settlement() -> None:
    row = _candidate().observed_row

    assert row.underlying_outcome_kind == "task_failure"
    assert row.verdicts.hidden_tests == "fail"
    assert row.verdicts.regression_tests == "pass"
    assert row.verdicts.scope_policy == "pass"
    assert row.verdicts.safety_policy == "pass"
    assert row.model_cost_nanos == 126_342_000
    assert row.campaign_settled is False
    assert row.authenticated_row_persisted is False
    assert row.qualification_schema_version == "trace-qualification-v2"
    assert row.qualification_check_count == 28
    assert row.qualification_passed_check_count == 28


def test_r14_attribution_cannot_replace_historical_reason() -> None:
    payload = _candidate()
    rewritten = payload.model_dump(mode="json")
    rewritten["historical_confound"]["historical_reason_code"] = (
        "TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH"
    )
    rewritten["content_hash"] = sha256_json(
        {key: value for key, value in rewritten.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError):
        HeldoutACR14CampaignEvidence.model_validate(rewritten)


def test_r14_evidence_module_has_no_runtime_execution_or_reauthentication_import() -> None:
    source = (ROOT / "patchloop/evals/heldout_ac_r14_campaign_evidence.py").read_text(
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
    ):
        assert f"import {forbidden}" not in source
        assert f"from patchloop.evals.{forbidden}" not in source


def test_r14_checked_in_index_is_canonical_and_idempotent() -> None:
    summary = validate_heldout_ac_r14_campaign_evidence(repository=ROOT)
    selected = ROOT / OUTPUT_PATH
    before = selected.read_bytes()
    before_mtime = selected.stat().st_mtime_ns

    assert summary["execution_hash"] == EXECUTION_HASH
    assert summary["terminal_settled_runs"] == 0
    assert summary["observed_unsettled_runs"] == 1
    assert summary["not_started_runs"] == 47
    assert summary["observed_started_model_cost_nanos"] == 126_342_000
    assert summary["file_bytes"] == len(before)
    assert summary["file_sha256"] == sha256_bytes(before)
    assert summary["runtime_revalidated"] is False
    rerun = run_heldout_ac_r14_campaign_evidence(repository=ROOT)
    assert rerun == summary
    assert selected.read_bytes() == before
    assert selected.stat().st_mtime_ns == before_mtime


def test_r14_runtime_revalidation_is_read_only_when_historical_files_exist() -> None:
    payload = _candidate()
    paths = _bound_paths(payload)
    if not all(path.is_file() for path in paths):
        return
    before = _snapshot(paths)

    summary = revalidate_heldout_ac_r14_runtime_evidence(repository=ROOT)

    assert summary["runtime_revalidated"] is True
    assert summary["observed_started_model_cost_nanos"] == 126_342_000
    assert _snapshot(paths) == before


def test_missing_historical_runtime_fails_without_creating_files() -> None:
    payload = _candidate()
    missing_root = ROOT / ".patchloop" / f"missing-r14-evidence-{uuid4().hex}"
    assert not missing_root.exists()

    with pytest.raises(
        HeldoutACR14CampaignEvidenceError,
        match="heldout-ac-preflight-budget-v1",
    ):
        _verify_runtime_files(missing_root, payload)

    assert not missing_root.exists()
