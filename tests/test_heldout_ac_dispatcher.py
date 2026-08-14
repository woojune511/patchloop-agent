from __future__ import annotations

import json
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import pytest

from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
from patchloop.contracts import RunStatus, VerdictState
from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_dispatcher import (
    HeldoutACSettledCampaignRow,
    _append_journal,
    _create_journal,
    _prepared_result,
    _row_identity,
    _validate_settlement_limits,
    prepare_heldout_ac_approved_plan,
    run_heldout_ac_campaign,
    validate_heldout_ac_campaign_result,
)
from patchloop.evals.heldout_ac_execution import (
    MATERIALIZATION_PATH,
    HeldoutACExecutionCandidate,
    HeldoutACFileBinding,
    HeldoutACSourceQualificationBinding,
    build_heldout_ac_execution_candidate,
    build_heldout_ac_no_call_readiness,
    build_heldout_ac_run_manifest,
    materialize_heldout_ac_runtime_task_authority,
)
from patchloop.evals.heldout_ac_live_contract import (
    DISPATCH_SOURCE_QUALIFICATION_ID,
    heldout_ac_live_plan_matches_manifest,
)
from patchloop.evals.heldout_ac_persisted_adapter import (
    HeldoutACAuthenticatedPersistedRow,
    HeldoutACPersistedUsageEvidence,
)
from patchloop.evals.heldout_ac_preflight_source_qualification import (
    load_heldout_ac_preflight_source_binding,
)
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_json
from scripts.run_heldout_ac_campaign import _candidate_payload
from tests.test_evaluator_v2_contracts import _v2_chain

ROOT = Path(__file__).resolve().parents[1]


def _images() -> list[tuple[str, str]]:
    materialization = json.loads((ROOT / MATERIALIZATION_PATH).read_text("utf-8"))
    return sorted(
        {
            (item["task"]["evaluator_image"], item["task"]["evaluator_image_digest"])
            for item in materialization["task_bindings"]
        }
    )


def _candidate() -> HeldoutACExecutionCandidate:
    binding = load_heldout_ac_preflight_source_binding(repository=ROOT)
    assert binding.qualification_id == DISPATCH_SOURCE_QUALIFICATION_ID
    readiness = build_heldout_ac_no_call_readiness(
        observed_at=datetime(2026, 8, 14, 12, 0, tzinfo=UTC),
        git_commit="1" * 40,
        git_tree="2" * 40,
        docker_images=_images(),
        openai_sdk_version=version("openai"),
        credential_present=True,
        custom_base_url_present=False,
    )
    return build_heldout_ac_execution_candidate(
        readiness=readiness,
        source_qualification=binding,
        repository=ROOT,
    )


def _plan(tmp_path: Path) -> tuple[HeldoutACExecutionCandidate, Path, dict]:
    candidate = _candidate()
    plan_path = prepare_heldout_ac_approved_plan(
        candidate=candidate,
        approve_live_cost=True,
        approved_execution_hash=candidate.execution_hash,
        root=tmp_path,
        repository=ROOT,
        created_at=datetime(2026, 8, 14, 12, 1, tzinfo=UTC),
    )
    return candidate, plan_path, json.loads(plan_path.read_text("utf-8"))


def test_campaign_cli_loader_accepts_only_a_candidate_object(tmp_path: Path) -> None:
    candidate = _candidate().model_dump(mode="json")
    direct = tmp_path / "candidate.json"
    wrapped = tmp_path / "preflight.json"
    invalid = tmp_path / "invalid.json"
    direct.write_text(json.dumps(candidate), encoding="utf-8")
    wrapped.write_text(json.dumps({"candidate": candidate}), encoding="utf-8")
    invalid.write_text(json.dumps({"candidate": None}), encoding="utf-8")

    assert _candidate_payload(direct) == candidate
    assert _candidate_payload(wrapped) == candidate
    with pytest.raises(ContractError, match="no candidate object"):
        _candidate_payload(invalid)


def _manifest(candidate: HeldoutACExecutionCandidate, order: int = 1):
    row = candidate.schedule[order - 1]
    package = load_task_package(ROOT / row.task_path)
    authority = materialize_heldout_ac_runtime_task_authority(
        candidate=candidate,
        task_id=row.task_id,
        package=package,
        api_key="dispatcher-unit-secret",
        repository=ROOT,
    )
    manifest = build_heldout_ac_run_manifest(
        candidate=candidate,
        row_order=order,
        run_id=f"run_heldout_dispatch_{order:02d}",
        created_at=datetime(2026, 8, 14, 12, 2, tzinfo=UTC),
        authority=authority,
    )
    return manifest, authority


def test_approved_plan_binds_live_manifest_reservation_and_one_use_row(tmp_path: Path) -> None:
    candidate, plan_path, plan = _plan(tmp_path)
    manifest, authority = _manifest(candidate)
    live = issue_live_execution_authorization(candidate.execution_hash, root=tmp_path)
    journal = Path(plan["journal_path"])
    _create_journal(journal, candidate, live.plan_hash)
    _append_journal(
        journal,
        "RunStarted",
        {
            **_row_identity(candidate.schedule[0]),
            "run_id": manifest.run_id,
            "execution_hash": candidate.execution_hash,
            "execution_plan_file_sha256": live.plan_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        },
    )

    assert heldout_ac_live_plan_matches_manifest(
        plan=plan,
        manifest=manifest,
        plan_path=plan_path,
        plan_file_sha256=live.plan_hash,
        repository=ROOT,
    )
    AgentRunner._require_live_authorization(
        manifest,
        live,
        runner_root=tmp_path,
        evaluator_v2_authority=authority.qualification_authority,
    )
    runner = AgentRunner(root=tmp_path)
    runner.state.claim_run_for_worker(
        manifest.run_id,
        owner_id="worker_dispatch_test",
        owner_pid=1,
        owner_hostname="test",
        allowed_statuses={RunStatus.CREATED},
        manifest=manifest,
    )
    assert runner._consume_ac_row_start_once(manifest, live) is not None
    with pytest.raises(ContractError, match="already consumed"):
        runner._consume_ac_row_start_once(manifest, live)


def test_live_plan_fails_closed_on_rehashed_runtime_drift(tmp_path: Path) -> None:
    candidate, plan_path, plan = _plan(tmp_path)
    manifest, _authority = _manifest(candidate)
    live = issue_live_execution_authorization(candidate.execution_hash, root=tmp_path)
    plan["runtime_contract"]["budget"]["max_model_calls"] = 241

    assert not heldout_ac_live_plan_matches_manifest(
        plan=plan,
        manifest=manifest,
        plan_path=plan_path,
        plan_file_sha256=live.plan_hash,
        repository=ROOT,
    )


def test_dispatcher_revalidates_custom_base_url_before_any_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate, _plan_path, _plan_payload = _plan(tmp_path)
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=dispatcher-test-secret\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid")

    with patch.object(AgentRunner, "start") as start:
        result = run_heldout_ac_campaign(
            execution_hash=candidate.execution_hash,
            env_file=env_file,
            root=tmp_path,
            repository=ROOT,
        )
    start.assert_not_called()
    assert result.disposition == "inconclusive-matrix"
    assert result.confound is not None
    assert result.confound.run_started_event_written is False
    assert result.unsettled_dispatched_runs == 0
    assert result.cost_accounting_complete is True

    with pytest.raises(ContractError, match="cannot retry or resume"):
        run_heldout_ac_campaign(
            execution_hash=candidate.execution_hash,
            env_file=env_file,
            root=tmp_path,
            repository=ROOT,
        )


def test_dispatcher_revalidates_sdk_version_before_any_row(tmp_path: Path) -> None:
    candidate, _plan_path, _plan_payload = _plan(tmp_path)
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=dispatcher-test-secret\n", encoding="utf-8")

    with (
        patch("patchloop.evals.heldout_ac_dispatcher.version", return_value="0.0-drift"),
        patch.object(AgentRunner, "start") as start,
    ):
        result = run_heldout_ac_campaign(
            execution_hash=candidate.execution_hash,
            env_file=env_file,
            root=tmp_path,
            repository=ROOT,
        )
    start.assert_not_called()
    assert result.disposition == "inconclusive-matrix"
    assert result.confound is not None
    assert result.confound.run_started_event_written is False
    assert result.not_started_runs == 47


def test_dispatcher_consumes_invalid_credential_before_any_row(tmp_path: Path) -> None:
    candidate, _plan_path, _plan_payload = _plan(tmp_path)
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=\n", encoding="utf-8")

    with patch.object(AgentRunner, "start") as start:
        result = run_heldout_ac_campaign(
            execution_hash=candidate.execution_hash,
            env_file=env_file,
            root=tmp_path,
            repository=ROOT,
        )

    start.assert_not_called()
    assert result.disposition == "inconclusive-matrix"
    assert result.confound is not None
    assert result.confound.run_started_event_written is False
    assert result.settled_model_cost_nanos == 0
    assert result.cost_accounting_complete is True


@pytest.mark.parametrize("approved", [False, 1, "true"])
def test_plan_preparation_requires_exact_boolean_approval(tmp_path: Path, approved: object) -> None:
    candidate = _candidate()
    with pytest.raises(ContractError, match="exact boolean true"):
        prepare_heldout_ac_approved_plan(
            candidate=candidate,
            approve_live_cost=approved,  # type: ignore[arg-type]
            approved_execution_hash=candidate.execution_hash,
            root=tmp_path,
            repository=ROOT,
        )


def test_plan_rejects_candidate_bound_to_superseded_r2_source(tmp_path: Path) -> None:
    r2 = HeldoutACSourceQualificationBinding(
        schema_version="heldout-ac-execution-source-qualification-binding-v1",
        qualification_id="core-ac-fixed-bundle-heldout-preflight-source-20260814-r2",
        qualification_file=HeldoutACFileBinding(
            path=("reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r2.json"),
            file_bytes=15_725,
            file_sha256=("sha256:5a06587069932599fd18aa7c2a3e72be098ccc0887b3b5906a6f5a0891391589"),
            content_hash=(
                "sha256:7384a8bfa9a44ae3db2edd36c3a860ff0e85567652579770c42d781e4335f224"
            ),
        ),
        source_qualification_hash=(
            "sha256:7384a8bfa9a44ae3db2edd36c3a860ff0e85567652579770c42d781e4335f224"
        ),
        evaluator_source_hash=(
            "sha256:b9acab3b68981d6be321a3019282b977b885f83d38b359f707bc6e7b29725aeb"
        ),
        source_replay_valid=True,
        provider_evaluator_agent_calls_made=0,
    )
    readiness = build_heldout_ac_no_call_readiness(
        observed_at=datetime(2026, 8, 14, 12, 0, tzinfo=UTC),
        git_commit="1" * 40,
        git_tree="2" * 40,
        docker_images=_images(),
        openai_sdk_version=version("openai"),
        credential_present=True,
        custom_base_url_present=False,
    )
    candidate = build_heldout_ac_execution_candidate(
        readiness=readiness,
        source_qualification=r2,
        repository=ROOT,
    )

    with pytest.raises(ContractError, match="dispatcher-qualified successor"):
        prepare_heldout_ac_approved_plan(
            candidate=candidate,
            approve_live_cost=True,
            approved_execution_hash=candidate.execution_hash,
            root=tmp_path,
            repository=ROOT,
        )


def _fake_settled_row(
    candidate: HeldoutACExecutionCandidate, order: int
) -> HeldoutACSettledCampaignRow:
    scheduled = candidate.schedule[order - 1]
    chain = _v2_chain(
        VerdictState.PASS,
        task_path=scheduled.task_path,
        evaluator_source_hash=candidate.source_qualification.evaluator_source_hash,
    )
    result = chain.result
    usage_body = {
        "schema_version": "heldout-ac-durable-usage-evidence-v1",
        "run_id": result.run_id,
        "schedule_row_id": scheduled.schedule_row_id,
        "pricing_binding_hash": candidate.pricing_binding_hash,
        "price_nanos_per_token": {
            "uncached_input": 750,
            "cached_input": 75,
            "cache_write_input": 750,
            "output": 4_500,
        },
        "usage": {
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "output_tokens": 0,
            "reasoning_output_tokens": 0,
            "model_calls": 0,
            "input_token_count_calls": 0,
            "tool_calls": 0,
            "wall_clock_ms": 0,
        },
        "token_derived_cost_nanos": 0,
        "qualification_hash": "sha256:" + "d" * 64,
        "source_evidence_hash": "sha256:" + "e" * 64,
        "persisted_result_file_hash": "sha256:" + "f" * 64,
        "evaluator_v2_receipt_file_hash": "sha256:" + "1" * 64,
    }
    usage = HeldoutACPersistedUsageEvidence(**usage_body, content_hash=sha256_json(usage_body))
    authenticated_body = {
        "schema_version": "heldout-ac-authenticated-persisted-row-v1",
        "persisted_evidence_authenticated": True,
        "order": order,
        "wave": scheduled.wave,
        "task_id": scheduled.task_id,
        "role": scheduled.role,
        "condition": scheduled.condition,
        "repetition": scheduled.repetition,
        "run_id": result.run_id,
        "schedule_row_id": scheduled.schedule_row_id,
        "execution_hash": candidate.execution_hash,
        "task_evaluator_binding_hash": "sha256:" + "2" * 64,
        "persisted_result_file_hash": "sha256:" + "f" * 64,
        "persisted_result_semantic_hash": "sha256:" + "3" * 64,
        "qualification_file_hash": "sha256:" + "4" * 64,
        "qualification_hash": "sha256:" + "d" * 64,
        "source_evidence_hash": "sha256:" + "e" * 64,
        "usage_evidence_file_hash": "sha256:" + "5" * 64,
        "usage_evidence_hash": usage.content_hash,
        "evaluator_v2_receipt_hash": "sha256:" + "6" * 64,
        "evaluator_v2_receipt_file_hash": "sha256:" + "1" * 64,
        "result": result.model_dump(mode="json"),
        "usage_evidence": usage.model_dump(mode="json"),
    }
    authenticated = HeldoutACAuthenticatedPersistedRow(
        **authenticated_body, content_hash=sha256_json(authenticated_body)
    )
    settled_body = {
        "schema_version": "heldout-ac-settled-campaign-row-v1",
        "authenticated_row": authenticated.model_dump(mode="json"),
        "terminal_type": None,
    }
    return HeldoutACSettledCampaignRow(**settled_body, content_hash=sha256_json(settled_body))


def test_complete_authenticated_matrix_unlocks_only_preregistered_analysis(
    tmp_path: Path,
) -> None:
    candidate, plan_path, plan = _plan(tmp_path)
    settled = [_fake_settled_row(candidate, order) for order in range(1, 49)]
    journal = Path(plan["journal_path"])
    _create_journal(journal, candidate, "sha256:" + "7" * 64)

    prepared, projection, analysis = _prepared_result(
        candidate=candidate,
        plan_path=plan_path,
        plan_hash="sha256:" + "7" * 64,
        journal_path=journal,
        settled=settled,
        confound=None,
        not_started=[],
    )

    assert prepared["disposition"] == "complete-matrix"
    assert prepared["official_heldout_analysis"] is True
    assert prepared["memory_benefit_claim_authorized"] is False
    assert projection is not None and len(projection.rows) == 48
    assert analysis is not None and analysis.primary_estimate.numerator == 0


def test_settlement_fails_closed_above_frozen_per_row_cost() -> None:
    candidate = _candidate()
    authenticated = _fake_settled_row(candidate, 1).authenticated_row
    oversized_usage = authenticated.usage_evidence.model_copy(
        update={"token_derived_cost_nanos": 5_250_000_001}
    )
    oversized = authenticated.model_copy(update={"usage_evidence": oversized_usage})

    with pytest.raises(ContractError, match="per-row boundary"):
        _validate_settlement_limits(oversized, accrued_before=0)


def test_dispatcher_seals_first_row_infrastructure_confound_without_provider_retry(
    tmp_path: Path,
) -> None:
    candidate, _plan_path, _plan_payload = _plan(tmp_path)
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=dispatcher-test-secret\n", encoding="utf-8")

    with patch.object(AgentRunner, "start", side_effect=RuntimeError("offline injected")) as start:
        result = run_heldout_ac_campaign(
            execution_hash=candidate.execution_hash,
            env_file=env_file,
            root=tmp_path,
            repository=ROOT,
        )

    assert start.call_count == 1
    assert result.disposition == "inconclusive-matrix"
    assert result.terminal_settled_runs == 0
    assert result.not_started_runs == 47
    assert result.confound is not None
    assert result.confound.order == 1
    assert result.confound.run_started_event_written is True
    assert result.settled_model_cost_nanos == 0
    assert result.unsettled_dispatched_runs == 1
    assert result.cost_accounting_complete is False
    assert result.official_heldout_analysis is False
    assert "dispatcher-test-secret" not in Path(result.journal_path).read_text("utf-8")
    assert "dispatcher-test-secret" not in Path(result.execution_plan_path).read_text("utf-8")
    assert "dispatcher-test-secret" not in Path(result.prepared_result_path).read_text("utf-8")
    assert "dispatcher-test-secret" not in result.model_dump_json()

    replay = validate_heldout_ac_campaign_result(
        execution_hash=candidate.execution_hash,
        root=tmp_path,
        repository=ROOT,
    )
    assert replay["disposition"] == "inconclusive-matrix"
    assert replay["cost_accounting_complete"] is False
    assert replay["provider_calls_made_by_validation"] == 0

    prepared_path = Path(result.prepared_result_path)
    prepared_path.write_bytes(prepared_path.read_bytes() + b"\n")
    with pytest.raises(ContractError, match="prepared result replay differs"):
        validate_heldout_ac_campaign_result(
            execution_hash=candidate.execution_hash,
            root=tmp_path,
            repository=ROOT,
        )

    with (
        patch.object(AgentRunner, "start") as resumed_start,
        pytest.raises(ContractError, match="cannot retry or resume"),
    ):
        run_heldout_ac_campaign(
            execution_hash=candidate.execution_hash,
            env_file=env_file,
            root=tmp_path,
            repository=ROOT,
        )
    resumed_start.assert_not_called()
