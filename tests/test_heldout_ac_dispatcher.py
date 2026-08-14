from __future__ import annotations

import json
import os
from contextlib import ExitStack
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
from patchloop.contracts import (
    EvaluatorV2EvaluationReceipt,
    EventType,
    RunEvent,
    RunResult,
    RunStatus,
    VerdictState,
)
from patchloop.errors import ContractError, EvaluatorControlContractCollision
from patchloop.evals import heldout_ac_persisted_adapter as persisted_adapter
from patchloop.evals.heldout_ac_completion import (
    HeldoutACAuthenticatedCompletionProjection,
    HeldoutACOfficialAnalysisEnvelope,
)
from patchloop.evals.heldout_ac_dispatcher import (
    HeldoutACCampaignConfoundV2,
    HeldoutACConfoundedDurableEvidence,
    HeldoutACDispatchedCostObservation,
    HeldoutACEvaluatorFailureEventProjection,
    HeldoutACSettledCampaignRow,
    HeldoutACSettledCampaignRowV2,
    _append_journal,
    _append_terminal_cost_settled,
    _candidate_from_mapping,
    _confound_reason_code,
    _create_journal,
    _durable_evidence_from_authenticated,
    _prepared_result,
    _record_confound,
    _row_identity,
    _settled_row,
    _trigger_for_reason,
    _validate_settlement_limits,
    _verify_confound_durable_evidence,
    _verify_settled_agent_terminal_sidecar,
    heldout_ac_paid_campaign_identity_consumed,
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
    heldout_ac_candidate_has_bound_source_qualification,
    heldout_ac_candidate_has_current_source_binding,
    heldout_ac_live_plan_matches_manifest,
    validate_heldout_ac_dispatch_plan,
    validate_heldout_ac_reservation_journal_prefix,
)
from patchloop.evals.heldout_ac_persisted_adapter import (
    HeldoutACAuthenticatedPersistedEvidence,
    HeldoutACAuthenticatedPersistedRow,
    HeldoutACAuthenticatedQualificationProjection,
    HeldoutACPersistedUsageEvidence,
    authenticate_heldout_ac_persisted_evidence,
    project_authenticated_heldout_ac_persisted_evidence,
)
from patchloop.evals.heldout_ac_preflight_source_qualification import (
    OUTPUT_PATH as PREFLIGHT_SOURCE_QUALIFICATION_PATH,
)
from patchloop.evals.heldout_ac_preflight_source_qualification import (
    load_heldout_ac_preflight_source_binding,
)
from patchloop.evals.heldout_ac_suite import load_heldout_ac_suite
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json
from scripts.run_heldout_ac_campaign import _candidate_payload
from tests.test_evaluator_v2_contracts import _v2_chain
from tests.test_heldout_ac_persisted_adapter import (
    EXECUTION_HASH as ADAPTER_EXECUTION_HASH,
)
from tests.test_heldout_ac_persisted_adapter import PRICING_HASH as ADAPTER_PRICING_HASH
from tests.test_heldout_ac_persisted_adapter import (
    _post_submission_evaluator_confound_files,
    _row_files,
)

ROOT = Path(__file__).resolve().parents[1]


def _images() -> list[tuple[str, str]]:
    materialization = json.loads((ROOT / MATERIALIZATION_PATH).read_text("utf-8"))
    return sorted(
        {
            (item["task"]["evaluator_image"], item["task"]["evaluator_image_digest"])
            for item in materialization["task_bindings"]
        }
    )


def _candidate_at(observed_at: datetime) -> HeldoutACExecutionCandidate:
    binding = load_heldout_ac_preflight_source_binding(repository=ROOT)
    readiness = build_heldout_ac_no_call_readiness(
        observed_at=observed_at,
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


def _candidate() -> HeldoutACExecutionCandidate:
    return _candidate_at(datetime(2026, 8, 14, 12, 0, tzinfo=UTC))


def _checked_in_preflight_source_binding_without_replay() -> HeldoutACSourceQualificationBinding:
    selected = ROOT / PREFLIGHT_SOURCE_QUALIFICATION_PATH
    raw = selected.read_bytes()
    payload = json.loads(raw)
    return HeldoutACSourceQualificationBinding(
        schema_version="heldout-ac-execution-source-qualification-binding-v1",
        qualification_id=payload["qualification_id"],
        qualification_file=HeldoutACFileBinding(
            path=PREFLIGHT_SOURCE_QUALIFICATION_PATH.as_posix(),
            file_bytes=len(raw),
            file_sha256=sha256_bytes(raw),
            content_hash=payload["content_hash"],
        ),
        source_qualification_hash=payload["content_hash"],
        evaluator_source_hash=payload["evaluator_source_hash"],
        source_replay_valid=True,
        provider_evaluator_agent_calls_made=0,
    )


def _synthetic_source_successor(
    predecessor: HeldoutACSourceQualificationBinding,
) -> HeldoutACSourceQualificationBinding:
    content_hash = "sha256:" + "c" * 64
    qualification_file = HeldoutACFileBinding(
        **predecessor.qualification_file.model_dump(mode="python", exclude={"content_hash"}),
        content_hash=content_hash,
    )
    return HeldoutACSourceQualificationBinding(
        **predecessor.model_dump(
            mode="python",
            exclude={
                "qualification_id",
                "qualification_file",
                "source_qualification_hash",
            },
        ),
        qualification_id="synthetic-current-heldout-source-successor",
        qualification_file=qualification_file,
        source_qualification_hash=content_hash,
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


def test_current_dispatch_gate_is_loader_bound_while_predecessor_remains_replayable(
    tmp_path: Path,
) -> None:
    predecessor = _checked_in_preflight_source_binding_without_replay()
    with patch(
        f"{__name__}.load_heldout_ac_preflight_source_binding",
        return_value=predecessor,
    ):
        candidate = _candidate()
    parsed = _candidate_from_mapping(candidate.model_dump(mode="json"))
    assert parsed == candidate
    assert heldout_ac_candidate_has_bound_source_qualification(candidate, repository=ROOT)

    successor = _synthetic_source_successor(predecessor)
    with patch(
        "patchloop.evals.heldout_ac_preflight_source_qualification."
        "load_heldout_ac_preflight_source_binding",
        return_value=successor,
    ):
        assert not heldout_ac_candidate_has_current_source_binding(
            candidate,
            repository=ROOT,
        )
        with pytest.raises(ContractError, match="differs from the current successor"):
            prepare_heldout_ac_approved_plan(
                candidate=candidate,
                approve_live_cost=True,
                approved_execution_hash=candidate.execution_hash,
                root=tmp_path,
                repository=ROOT,
            )
    assert not (tmp_path / "experiments").exists()


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
    _create_journal(journal, candidate, live.plan_hash, run_root=tmp_path)
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
        run_root=tmp_path,
    )

    assert heldout_ac_live_plan_matches_manifest(
        plan=plan,
        manifest=manifest,
        plan_path=plan_path,
        plan_file_sha256=live.plan_hash,
        expected_run_root=tmp_path,
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


def test_v2_atomic_settlement_admits_row_two_from_dispatcher_wrapper_bytes(
    tmp_path: Path,
) -> None:
    candidate, plan_path, plan = _plan(tmp_path)
    live = issue_live_execution_authorization(candidate.execution_hash, root=tmp_path)
    journal = Path(plan["journal_path"])
    _create_journal(journal, candidate, live.plan_hash, run_root=tmp_path)
    settled = _fake_settled_row_v2(candidate, 1)
    authenticated = settled.authenticated_evidence
    row = candidate.schedule[0]
    row_bytes = authenticated.model_dump_json(indent=2).encode("utf-8")
    relative = (
        Path("experiments")
        / "heldout-ac"
        / "rows"
        / candidate.execution_hash.removeprefix("sha256:")
        / f"01-{authenticated.row.run_id}-authenticated.json"
    )
    row_path = tmp_path / relative
    row_path.parent.mkdir(parents=True, exist_ok=True)
    row_path.write_bytes(row_bytes)
    _append_journal(
        journal,
        "RunStarted",
        {
            **_row_identity(row),
            "run_id": authenticated.row.run_id,
            "execution_hash": candidate.execution_hash,
            "execution_plan_file_sha256": live.plan_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        },
        run_root=tmp_path,
    )
    _append_terminal_cost_settled(
        journal,
        run_root=tmp_path,
        candidate=candidate,
        row=row,
        authenticated=authenticated.row,
        run_id=authenticated.row.run_id,
        authenticated_row_path=relative.as_posix(),
        authenticated_row_bytes=row_bytes,
        authenticated_row_content_hash=authenticated.content_hash,
        actual_run_cost_nanos=authenticated.row.usage_evidence.token_derived_cost_nanos,
        accrued_cost_nanos_before=0,
    )
    manifest, _authority = _manifest(candidate, 2)
    row_two = candidate.schedule[1]
    _append_journal(
        journal,
        "RunStarted",
        {
            **_row_identity(row_two),
            "run_id": manifest.run_id,
            "execution_hash": candidate.execution_hash,
            "execution_plan_file_sha256": live.plan_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        },
        run_root=tmp_path,
    )

    validated = validate_heldout_ac_reservation_journal_prefix(
        plan=plan,
        manifest=manifest,
        plan_path=plan_path,
        plan_file_sha256=live.plan_hash,
        runner_root=tmp_path,
        repository=ROOT,
    )
    events = [json.loads(line) for line in journal.read_text("utf-8").splitlines()]
    assert validated["row_started_event_hash"] == events[-1]["event_hash"]
    assert [event["event_type"] for event in events[-3:]] == [
        "RunStarted",
        "RunTerminalCostSettled",
        "RunStarted",
    ]

    alternate_relative = relative.with_name("alternate-authenticated.json")
    alternate = tmp_path / alternate_relative
    alternate.write_bytes(row_bytes)
    terminal_event = events[-2]
    terminal_event["payload"]["authenticated_row_path"] = alternate_relative.as_posix()
    terminal_event["event_hash"] = sha256_json(
        {key: value for key, value in terminal_event.items() if key != "event_hash"}
    )
    current_event = events[-1]
    current_event["previous_event_hash"] = terminal_event["event_hash"]
    current_event["event_hash"] = sha256_json(
        {key: value for key, value in current_event.items() if key != "event_hash"}
    )
    journal.write_bytes(
        (
            "\n".join(json.dumps(event, sort_keys=True, separators=(",", ":")) for event in events)
            + "\n"
        ).encode("utf-8")
    )
    with pytest.raises(ContractError, match="authenticated evidence path differs"):
        validate_heldout_ac_reservation_journal_prefix(
            plan=plan,
            manifest=manifest,
            plan_path=plan_path,
            plan_file_sha256=live.plan_hash,
            runner_root=tmp_path,
            repository=ROOT,
        )


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
        expected_run_root=tmp_path,
        repository=ROOT,
    )


def test_paid_campaign_one_use_identity_ignores_readiness_observation_time(
    tmp_path: Path,
) -> None:
    first = _candidate_at(datetime(2026, 8, 14, 12, 0, tzinfo=UTC))
    second = _candidate_at(datetime(2026, 8, 14, 12, 5, tzinfo=UTC))
    assert first.execution_hash != second.execution_hash
    prepare_heldout_ac_approved_plan(
        candidate=first,
        approve_live_cost=True,
        approved_execution_hash=first.execution_hash,
        root=tmp_path,
        repository=ROOT,
    )

    with pytest.raises(ContractError, match="paid campaign identity was already consumed"):
        prepare_heldout_ac_approved_plan(
            candidate=second,
            approve_live_cost=True,
            approved_execution_hash=second.execution_hash,
            root=tmp_path,
            repository=ROOT,
        )


def test_plan_preparation_rejects_parent_link_before_any_runtime_write(
    tmp_path: Path,
) -> None:
    candidate = _candidate()
    run_root = tmp_path / "runtime"
    outside = tmp_path / "outside"
    run_root.mkdir()
    outside.mkdir()
    try:
        os.symlink(outside, run_root / "experiments", target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink is unavailable: {exc}")

    with pytest.raises(ContractError, match="link or reparse point"):
        prepare_heldout_ac_approved_plan(
            candidate=candidate,
            approve_live_cost=True,
            approved_execution_hash=candidate.execution_hash,
            root=run_root,
            repository=ROOT,
        )
    assert list(outside.iterdir()) == []


def test_one_use_scan_fails_closed_without_reading_linked_plan(tmp_path: Path) -> None:
    candidate = _candidate()
    run_root = tmp_path / "runtime"
    plans = run_root / "experiments" / "plans"
    outside = tmp_path / "outside-plan.json"
    plans.mkdir(parents=True)
    outside.write_text("external sentinel", encoding="utf-8")
    try:
        os.symlink(outside, plans / "linked.json")
    except OSError as exc:
        pytest.skip(f"file symlink is unavailable: {exc}")

    assert heldout_ac_paid_campaign_identity_consumed(candidate, root=run_root) is True


@pytest.mark.parametrize(
    ("field", "coercive_value"),
    [
        ("scheduled_run_count", 48.0),
        ("full_schedule_reserve_nanos", 252_000_000_000.0),
        ("hard_cap_nanos", 275_000_000_000.0),
    ],
)
def test_dispatch_plan_rejects_rehashed_coercive_ledger_numbers(
    tmp_path: Path,
    field: str,
    coercive_value: float,
) -> None:
    _candidate_value, plan_path, plan = _plan(tmp_path)
    ledger_path = Path(plan["campaign_one_use_ledger_path"])
    ledger = json.loads(ledger_path.read_text("utf-8"))
    ledger[field] = coercive_value
    ledger["content_hash"] = sha256_json(
        {key: value for key, value in ledger.items() if key != "content_hash"}
    )
    ledger_bytes = (json.dumps(ledger, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    ledger_path.write_bytes(ledger_bytes)
    plan["campaign_one_use_ledger_file_sha256"] = sha256_bytes(ledger_bytes)
    plan["campaign_one_use_ledger_content_hash"] = ledger["content_hash"]
    plan_bytes = (json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    plan_path.write_bytes(plan_bytes)

    with pytest.raises(ContractError, match="dispatch plan is invalid"):
        validate_heldout_ac_dispatch_plan(
            plan=plan,
            plan_path=plan_path,
            plan_file_sha256=sha256_bytes(plan_bytes),
            expected_run_root=tmp_path,
            repository=ROOT,
        )


def test_dispatch_validates_canonical_plan_before_creating_journal(
    tmp_path: Path,
) -> None:
    candidate, plan_path, plan = _plan(tmp_path)
    canonical_journal = Path(plan["journal_path"])
    plan["journal_path"] = str(tmp_path / "outside-canonical-journal.jsonl")
    plan_path.write_bytes(
        (json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    )

    with (
        patch.object(AgentRunner, "start") as start,
        pytest.raises(ContractError, match="dispatch plan is invalid"),
    ):
        run_heldout_ac_campaign(
            execution_hash=candidate.execution_hash,
            env_file=tmp_path / "unused.env",
            root=tmp_path,
            repository=ROOT,
        )
    start.assert_not_called()
    assert not canonical_journal.exists()
    assert not Path(plan["journal_path"]).exists()


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


def test_dispatcher_seals_credential_context_entry_failure(tmp_path: Path) -> None:
    candidate, _plan_path, _plan_payload = _plan(tmp_path)
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=dispatcher-test-secret\n", encoding="utf-8")

    class EntryFailure:
        def __enter__(self) -> None:
            raise RuntimeError("offline credential entry failure")

        def __exit__(self, *_args: object) -> None:
            return None

    with (
        patch(
            "patchloop.evals.heldout_ac_dispatcher.exact_openai_api_key_environment",
            return_value=EntryFailure(),
        ),
        patch.object(AgentRunner, "start") as start,
    ):
        result = run_heldout_ac_campaign(
            execution_hash=candidate.execution_hash,
            env_file=env_file,
            root=tmp_path,
            repository=ROOT,
        )

    start.assert_not_called()
    assert result.confound is not None
    assert result.confound.phase == "row-dispatch"
    assert result.confound.reason_code == "ROW_DISPATCH_FAILED"
    assert result.confound.run_started_event_written is False
    assert result.cost_accounting_complete is True
    assert result.unsettled_dispatched_runs == 0
    assert Path(result.journal_path).exists()
    assert Path(result.prepared_result_path).exists()


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

    with pytest.raises(ContractError, match="current successor"):
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


def _fake_settled_row_v2(
    candidate: HeldoutACExecutionCandidate,
    order: int,
) -> HeldoutACSettledCampaignRowV2:
    legacy = _fake_settled_row(candidate, order).authenticated_row
    run_id = f"run_heldout_fake_{order:02d}"

    def replace_run_id(value: object) -> object:
        if isinstance(value, dict):
            return {key: replace_run_id(item) for key, item in value.items()}
        if isinstance(value, list):
            return [replace_run_id(item) for item in value]
        return run_id if value == legacy.run_id else value

    result = RunResult.model_validate(replace_run_id(legacy.result.model_dump(mode="json")))
    usage_body = {
        **legacy.usage_evidence.model_dump(mode="json", exclude={"content_hash"}),
        "run_id": run_id,
    }
    usage = HeldoutACPersistedUsageEvidence(
        **usage_body,
        content_hash=sha256_json(usage_body),
    )
    authenticated_body = {
        **legacy.model_dump(mode="json", exclude={"content_hash"}),
        "run_id": run_id,
        "persisted_result_semantic_hash": sha256_json(result.model_dump(mode="json")),
        "usage_evidence_hash": usage.content_hash,
        "result": result.model_dump(mode="json"),
        "usage_evidence": usage.model_dump(mode="json"),
    }
    authenticated = HeldoutACAuthenticatedPersistedRow(
        **authenticated_body,
        content_hash=sha256_json(authenticated_body),
    )
    qualification_body = {
        "schema_version": "heldout-ac-authenticated-trace-qualification-projection-v2",
        "source_schema_version": "trace-qualification-v2",
        "run_id": run_id,
        "qualified": True,
        "trace_integrity_passed": True,
        "leakage_scan_passed": True,
        "evaluation_reached": True,
        "outcome_kind": result.outcome_kind.value,
        "purpose": "core",
        "experiment_id": candidate.suite_id,
        "dataset_role": authenticated.role,
        "task_id": authenticated.task_id,
        "suite_hash": candidate.suite_content_hash,
        "execution_hash": candidate.execution_hash,
        "schedule_row_id": authenticated.schedule_row_id,
        "memory_condition": authenticated.condition,
        "source_evidence_hash": authenticated.source_evidence_hash,
        "source_qualification_hash": authenticated.qualification_hash,
        "check_count": 28,
        "checks_hash": "sha256:" + "8" * 64,
        "evaluator_version": "v2",
        "evaluator_v2_source_hash": candidate.source_qualification.evaluator_source_hash,
        "evaluator_v2_source_qualification_hash": (
            candidate.source_qualification.source_qualification_hash
        ),
        "evaluator_v2_receipt_hash": authenticated.evaluator_v2_receipt_hash,
        "evaluator_v2_receipt_file_hash": authenticated.evaluator_v2_receipt_file_hash,
        "evaluator_v2_runtime_authenticated": True,
        "evaluator_v2_completion_eligible": True,
    }
    qualification = HeldoutACAuthenticatedQualificationProjection(
        **qualification_body,
        content_hash=sha256_json(qualification_body),
    )
    evidence_body = {
        "schema_version": "heldout-ac-authenticated-persisted-evidence-v4",
        "persisted_evidence_authenticated": True,
        "official": False,
        "analysis_eligible": False,
        "row": authenticated.model_dump(mode="json"),
        "qualification": qualification.model_dump(mode="json"),
        "terminal_type": None,
        "terminal_event": None,
    }
    evidence = HeldoutACAuthenticatedPersistedEvidence(
        **evidence_body,
        content_hash=sha256_json(evidence_body),
    )
    settled_body = {
        "schema_version": "heldout-ac-settled-campaign-row-v2",
        "authenticated_evidence": evidence.model_dump(mode="json"),
        "agent_terminal_event_relative_path": None,
        "agent_terminal_event_file_sha256": None,
        "agent_terminal_event_content_hash": None,
    }
    return HeldoutACSettledCampaignRowV2(
        **settled_body,
        content_hash=sha256_json(settled_body),
    )


def test_complete_authenticated_matrix_unlocks_only_preregistered_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate, plan_path, plan = _plan(tmp_path)
    projected = [
        _fake_settled_row_v2(candidate, order).authenticated_evidence for order in range(1, 49)
    ]
    queued = iter(projected)
    monkeypatch.setattr(
        persisted_adapter,
        "_load_and_project_heldout_ac_persisted_evidence",
        lambda **_kwargs: next(queued),
    )
    issued = [
        authenticate_heldout_ac_persisted_evidence(
            suite=load_heldout_ac_suite(
                Path("experiments/heldout-ac-suite-20260814-v1.yaml"),
                repository=ROOT,
            ),
            execution_hash=candidate.execution_hash,
            expected_pricing_binding_hash=candidate.pricing_binding_hash,
            order=order,
            task_evaluator_binding=object(),  # type: ignore[arg-type]
            run_root=tmp_path,
            task_dir=ROOT,
            dataset_manifest_path=ROOT / "data/dataset-manifest.yaml",
            evaluator_authority=object(),  # type: ignore[arg-type]
            usage_evidence_relative_path="unused.json",
        )
        for order in range(1, 49)
    ]
    settled = [_settled_row(row, run_root=tmp_path) for row in issued]
    assert all(
        isinstance(item, HeldoutACSettledCampaignRowV2) and item.authenticated_evidence is row
        for item, row in zip(settled, issued, strict=True)
    )
    journal = Path(plan["journal_path"])
    _create_journal(journal, candidate, "sha256:" + "7" * 64, run_root=tmp_path)

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
    assert prepared["authenticated_completion"] is not None
    assert prepared["official_analysis_envelope"] is not None
    assert (
        prepared["official_analysis_envelope"]["completion_projection_hash"]
        == prepared["authenticated_completion"]["content_hash"]
    )
    assert prepared["memory_benefit_claim_authorized"] is False
    assert projection is not None and len(projection.rows) == 48
    assert analysis is not None and analysis.primary_estimate.numerator == 0

    replay_rows = [
        HeldoutACSettledCampaignRowV2.model_validate_json(item.model_dump_json())
        for item in settled
        if isinstance(item, HeldoutACSettledCampaignRowV2)
    ]
    replay_completion = HeldoutACAuthenticatedCompletionProjection.model_validate_json(
        json.dumps(prepared["authenticated_completion"])
    )
    replay_envelope = HeldoutACOfficialAnalysisEnvelope.model_validate_json(
        json.dumps(prepared["official_analysis_envelope"])
    )
    replayed, _projection, _analysis = _prepared_result(
        candidate=candidate,
        plan_path=plan_path,
        plan_hash="sha256:" + "7" * 64,
        journal_path=journal,
        settled=replay_rows,
        confound=None,
        not_started=[],
        persisted_official=(replay_completion, replay_envelope),
    )
    assert replayed == prepared


def test_settlement_fails_closed_above_frozen_per_row_cost() -> None:
    candidate = _candidate()
    authenticated = _fake_settled_row(candidate, 1).authenticated_row
    oversized_usage = authenticated.usage_evidence.model_copy(
        update={"token_derived_cost_nanos": 5_250_000_001}
    )
    oversized = authenticated.model_copy(update={"usage_evidence": oversized_usage})

    with pytest.raises(ContractError, match="per-row boundary"):
        _validate_settlement_limits(oversized, accrued_before=0)


def test_confounded_durable_cost_is_observed_but_not_settled(tmp_path: Path) -> None:
    candidate, plan_path, plan = _plan(tmp_path)
    journal = Path(plan["journal_path"])
    _create_journal(journal, candidate, "sha256:" + "7" * 64, run_root=tmp_path)
    durable_body = {
        "schema_version": "heldout-ac-confounded-durable-evidence-v1",
        "run_id": "run_heldout_observed_cost",
        "result_relative_path": "artifacts/runs/run_heldout_observed_cost/result.json",
        "result_file_sha256": "sha256:" + "1" * 64,
        "result_semantic_hash": "sha256:" + "2" * 64,
        "cost_observation_relative_path": (
            "experiments/heldout-ac/rows/observed-cost-observation.json"
        ),
        "cost_observation_file_sha256": "sha256:" + "9" * 64,
        "cost_observation_content_hash": "sha256:" + "a" * 64,
        "qualification_relative_path": "qualifications/run_heldout_observed_cost.json",
        "qualification_file_sha256": "sha256:" + "3" * 64,
        "qualification_hash": "sha256:" + "4" * 64,
        "usage_relative_path": "experiments/heldout-ac/rows/observed-cost.json",
        "usage_file_sha256": "sha256:" + "5" * 64,
        "usage_evidence_hash": "sha256:" + "6" * 64,
        "receipt_relative_path": None,
        "receipt_file_sha256": None,
        "receipt_content_hash": None,
        "evaluator_failure_code": None,
        "evaluator_failure_event_relative_path": None,
        "evaluator_failure_event_file_sha256": None,
        "evaluator_failure_event_hash": None,
        "evaluator_failure_event": None,
        "token_derived_cost_nanos": 261_021_000,
    }
    durable = HeldoutACConfoundedDurableEvidence(
        **durable_body,
        content_hash=sha256_json(durable_body),
    )
    confound, not_started = _record_confound(
        candidate=candidate,
        run_root=tmp_path,
        journal_path=journal,
        row=candidate.schedule[0],
        run_id=durable.run_id,
        exc=ContractError("authenticated evaluator collision"),
        phase="authentication",
        run_started_event_written=True,
        reason_code="EVALUATOR_CONTROL_CONTRACT_COLLISION",
        durable_evidence=durable,
    )
    assert isinstance(confound, HeldoutACCampaignConfoundV2)

    prepared, projection, analysis = _prepared_result(
        candidate=candidate,
        plan_path=plan_path,
        plan_hash="sha256:" + "7" * 64,
        journal_path=journal,
        settled=[],
        confound=confound,
        not_started=not_started,
    )

    assert prepared["settled_model_cost_nanos"] == 0
    assert prepared["observed_unsettled_model_cost_nanos"] == 261_021_000
    assert prepared["observed_started_model_cost_nanos"] == 261_021_000
    assert prepared["unsettled_dispatched_runs"] == 1
    assert prepared["cost_accounting_complete"] is True
    assert projection is None and analysis is None
    confound_event = json.loads(journal.read_text("utf-8").splitlines()[2])
    assert confound_event["payload"]["durable_evidence"]["token_derived_cost_nanos"] == 261_021_000


def test_confound_classification_never_depends_on_exception_message() -> None:
    messages = (
        "marker leak source schedule cost duplicate",
        "entirely unrelated text",
    )
    classifications = []
    for message in messages:
        exc = EvaluatorControlContractCollision(message)
        reason = _confound_reason_code(exc, "authentication")
        classifications.append((reason, _trigger_for_reason(reason)))

    assert classifications == [
        (
            "EVALUATOR_CONTROL_CONTRACT_COLLISION",
            "qualification-or-completion-contract-mismatch",
        ),
        (
            "EVALUATOR_CONTROL_CONTRACT_COLLISION",
            "qualification-or-completion-contract-mismatch",
        ),
    ]


def _persist_evaluator_confound_durable(
    tmp_path: Path,
) -> tuple[
    HeldoutACConfoundedDurableEvidence,
    SimpleNamespace,
    SimpleNamespace,
]:
    (
        suite,
        binding,
        result_bytes,
        qualification,
        qualification_bytes,
        usage_bytes,
        failure_event,
    ) = _post_submission_evaluator_confound_files()
    evidence = project_authenticated_heldout_ac_persisted_evidence(
        suite=suite,
        execution_hash=ADAPTER_EXECUTION_HASH,
        expected_pricing_binding_hash=ADAPTER_PRICING_HASH,
        order=1,
        task_evaluator_binding=binding,
        persisted_result_bytes=result_bytes,
        qualification_bytes=qualification_bytes,
        recomputed_qualification=qualification,
        usage_evidence_bytes=usage_bytes,
        receipt_validation=None,
        receipt_bytes=None,
        evaluator_failure_event=failure_event,
    )
    assert not isinstance(evidence, HeldoutACAuthenticatedPersistedEvidence)
    run_id = evidence.run_id
    result_relative = Path("artifacts") / "runs" / run_id / "result.json"
    qualification_relative = Path("qualifications") / f"{run_id}.json"
    usage_relative = (
        Path("experiments")
        / "heldout-ac"
        / "rows"
        / ADAPTER_EXECUTION_HASH.removeprefix("sha256:")
        / f"01-{run_id}-usage.json"
    )
    for relative, content in (
        (result_relative, result_bytes),
        (qualification_relative, qualification_bytes),
        (usage_relative, usage_bytes),
    ):
        selected = tmp_path / relative
        selected.parent.mkdir(parents=True, exist_ok=True)
        selected.write_bytes(content)

    observation_body = {
        "schema_version": "heldout-ac-dispatched-cost-observation-v1",
        "run_id": run_id,
        "schedule_row_id": evidence.schedule_row_id,
        "pricing_binding_hash": ADAPTER_PRICING_HASH,
        "price_nanos_per_token": {
            "uncached_input": 750,
            "cached_input": 75,
            "cache_write_input": 750,
            "output": 4_500,
        },
        "usage": evidence.usage_evidence.usage.model_dump(mode="json"),
        "result_relative_path": result_relative.as_posix(),
        "result_file_sha256": evidence.persisted_result_file_hash,
        "result_semantic_hash": evidence.persisted_result_semantic_hash,
        "token_derived_cost_nanos": evidence.usage_evidence.token_derived_cost_nanos,
    }
    observation = HeldoutACDispatchedCostObservation(
        **observation_body,
        content_hash=sha256_json(observation_body),
    )
    observation_relative = (
        Path("experiments")
        / "heldout-ac"
        / "rows"
        / ADAPTER_EXECUTION_HASH.removeprefix("sha256:")
        / f"01-{run_id}-cost-observation.json"
    )
    observation_bytes = (
        json.dumps(
            observation.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")
    observation_path = tmp_path / observation_relative
    observation_path.parent.mkdir(parents=True, exist_ok=True)
    observation_path.write_bytes(observation_bytes)
    event_body = {
        "event_id": failure_event.event_id,
        "run_id": failure_event.run_id,
        "sequence": failure_event.sequence,
        "type": failure_event.type.value,
        "timestamp": failure_event.model_dump(mode="json")["timestamp"],
        "actor": failure_event.actor,
        "error_code": evidence.evaluator_failure_code,
    }
    projection = HeldoutACEvaluatorFailureEventProjection(
        event_id=failure_event.event_id,
        run_id=failure_event.run_id,
        sequence=failure_event.sequence,
        type="RunFailed",
        timestamp=event_body["timestamp"],
        actor="runner",
        error_code=evidence.evaluator_failure_code,
        content_hash=sha256_json(event_body),
    )
    assert projection.content_hash == evidence.evaluator_failure_event_hash
    with patch(
        "patchloop.evals.heldout_ac_dispatcher._evaluator_failure_event_projection",
        return_value=projection,
    ):
        durable = _durable_evidence_from_authenticated(
            evidence,
            run_root=tmp_path,
            usage_relative_path=usage_relative,
            cost_observation=observation,
            cost_observation_relative_path=observation_relative,
        )
    candidate = SimpleNamespace(
        execution_hash=ADAPTER_EXECUTION_HASH,
        pricing_binding_hash=ADAPTER_PRICING_HASH,
        suite_content_hash=suite.content_hash,
        source_qualification=SimpleNamespace(
            evaluator_source_hash="sha256:" + "a" * 64,
            source_qualification_hash="sha256:" + "b" * 64,
        ),
    )
    expected_row = SimpleNamespace(order=1, schedule_row_id=evidence.schedule_row_id)
    return durable, candidate, expected_row


def test_evaluator_failure_sidecar_replay_is_db_free_and_read_only(tmp_path: Path) -> None:
    durable, candidate, expected_row = _persist_evaluator_confound_durable(tmp_path)
    assert durable.evaluator_failure_event_relative_path is not None
    sidecar = tmp_path / durable.evaluator_failure_event_relative_path
    assert sidecar.read_bytes().endswith(b"\n")
    assert not (tmp_path / "state.sqlite3").exists()
    before = {
        path.relative_to(tmp_path).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    _verify_confound_durable_evidence(
        durable,
        run_root=tmp_path,
        candidate=candidate,
        expected_row=expected_row,
    )

    after = {
        path.relative_to(tmp_path).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert not (tmp_path / "state.sqlite3").exists()


@pytest.mark.parametrize(
    ("target", "field"),
    [
        ("observation", "schedule_row_id"),
        ("observation", "pricing_binding_hash"),
        ("usage", "schedule_row_id"),
        ("usage", "pricing_binding_hash"),
    ],
)
def test_confound_replay_rejects_row_or_pricing_rebinding(
    tmp_path: Path,
    target: str,
    field: str,
) -> None:
    durable, candidate, expected_row = _persist_evaluator_confound_durable(tmp_path)
    body = durable.model_dump(mode="json", exclude={"content_hash"})
    relative_key = (
        "cost_observation_relative_path" if target == "observation" else "usage_relative_path"
    )
    selected = tmp_path / body[relative_key]
    payload = json.loads(selected.read_bytes())
    payload[field] = "sha256:" + "9" * 64
    payload["content_hash"] = sha256_json(
        {key: value for key, value in payload.items() if key != "content_hash"}
    )
    selected_bytes = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
        + ("\n" if target == "observation" else "")
    ).encode("utf-8")
    selected.write_bytes(selected_bytes)
    if target == "observation":
        body["cost_observation_file_sha256"] = sha256_bytes(selected_bytes)
        body["cost_observation_content_hash"] = payload["content_hash"]
    else:
        body["usage_file_sha256"] = sha256_bytes(selected_bytes)
        body["usage_evidence_hash"] = payload["content_hash"]
    drifted = HeldoutACConfoundedDurableEvidence(
        **body,
        content_hash=sha256_json(body),
    )

    with pytest.raises(ContractError, match="replay differs|cross-binding differs"):
        _verify_confound_durable_evidence(
            drifted,
            run_root=tmp_path,
            candidate=candidate,
            expected_row=expected_row,
        )


def test_confound_replay_recomputes_observed_cost_from_result(tmp_path: Path) -> None:
    durable, candidate, expected_row = _persist_evaluator_confound_durable(tmp_path)
    body = durable.model_dump(mode="json", exclude={"content_hash"})
    observation_path = tmp_path / durable.cost_observation_relative_path
    observation = json.loads(observation_path.read_bytes())
    observation["usage"] = {key: 0 for key in observation["usage"]}
    observation["token_derived_cost_nanos"] = 0
    observation["content_hash"] = sha256_json(
        {key: value for key, value in observation.items() if key != "content_hash"}
    )
    observation_bytes = (
        json.dumps(observation, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    observation_path.write_bytes(observation_bytes)
    body["cost_observation_file_sha256"] = sha256_bytes(observation_bytes)
    body["cost_observation_content_hash"] = observation["content_hash"]
    body["token_derived_cost_nanos"] = 0
    drifted = HeldoutACConfoundedDurableEvidence(
        **body,
        content_hash=sha256_json(body),
    )

    with pytest.raises(ContractError, match="replay differs"):
        _verify_confound_durable_evidence(
            drifted,
            run_root=tmp_path,
            candidate=candidate,
            expected_row=expected_row,
        )


def test_confound_replay_rejects_in_root_path_substitution(tmp_path: Path) -> None:
    durable, candidate, expected_row = _persist_evaluator_confound_durable(tmp_path)
    original = tmp_path / durable.cost_observation_relative_path
    alternate_relative = Path(durable.cost_observation_relative_path).with_name(
        "alternate-cost-observation.json"
    )
    alternate = tmp_path / alternate_relative
    alternate.write_bytes(original.read_bytes())
    body = {
        **durable.model_dump(mode="json", exclude={"content_hash"}),
        "cost_observation_relative_path": alternate_relative.as_posix(),
    }
    drifted = HeldoutACConfoundedDurableEvidence(
        **body,
        content_hash=sha256_json(body),
    )

    with pytest.raises(ContractError, match="evidence path differs"):
        _verify_confound_durable_evidence(
            drifted,
            run_root=tmp_path,
            candidate=candidate,
            expected_row=expected_row,
        )


def test_agent_terminal_sidecar_binds_runtime_classification(tmp_path: Path) -> None:
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files()
    result = RunResult.model_validate_json(result_bytes)
    failure_event = RunEvent(
        event_id="evt_agent_terminal_sidecar",
        run_id=result.run_id,
        sequence=10,
        type=EventType.RUN_FAILED,
        timestamp=datetime(2026, 8, 14, tzinfo=UTC),
        actor="runner",
        payload={"error_code": None},
    )
    evidence = project_authenticated_heldout_ac_persisted_evidence(
        suite=suite,
        execution_hash=ADAPTER_EXECUTION_HASH,
        expected_pricing_binding_hash=ADAPTER_PRICING_HASH,
        order=1,
        task_evaluator_binding=binding,
        persisted_result_bytes=result_bytes,
        qualification_bytes=qualification_bytes,
        recomputed_qualification=qualification,
        usage_evidence_bytes=usage_bytes,
        receipt_validation=None,
        receipt_bytes=None,
        agent_terminal_type="submission-failure",
        agent_terminal_event=failure_event,
    )
    assert isinstance(evidence, HeldoutACAuthenticatedPersistedEvidence)
    settled = _settled_row(evidence, run_root=tmp_path)
    assert isinstance(settled, HeldoutACSettledCampaignRowV2)
    assert settled.agent_terminal_event_relative_path is not None
    assert not (tmp_path / "state.sqlite3").exists()

    _verify_settled_agent_terminal_sidecar(settled, run_root=tmp_path)

    sidecar = tmp_path / settled.agent_terminal_event_relative_path
    drifted = json.loads(sidecar.read_bytes())
    drifted["event_id"] = "evt_agent_terminal_tampered"
    drifted["content_hash"] = sha256_json(
        {key: value for key, value in drifted.items() if key != "content_hash"}
    )
    sidecar.write_bytes((json.dumps(drifted, indent=2) + "\n").encode("utf-8"))
    with pytest.raises(ContractError, match="sidecar replay differs"):
        _verify_settled_agent_terminal_sidecar(settled, run_root=tmp_path)


def _fake_cost_observation_and_durable(
    candidate: HeldoutACExecutionCandidate,
    *,
    run_id: str,
    full: bool,
) -> tuple[HeldoutACDispatchedCostObservation, HeldoutACConfoundedDurableEvidence]:
    observation_body = {
        "schema_version": "heldout-ac-dispatched-cost-observation-v1",
        "run_id": run_id,
        "schedule_row_id": candidate.schedule[0].schedule_row_id,
        "pricing_binding_hash": candidate.pricing_binding_hash,
        "price_nanos_per_token": {
            "uncached_input": 750,
            "cached_input": 75,
            "cache_write_input": 750,
            "output": 4_500,
        },
        "usage": {
            "input_tokens": 348_028,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "output_tokens": 0,
            "reasoning_output_tokens": 0,
            "model_calls": 1,
            "input_token_count_calls": 0,
            "tool_calls": 0,
            "wall_clock_ms": 1,
        },
        "result_relative_path": f"artifacts/runs/{run_id}/result.json",
        "result_file_sha256": "sha256:" + "1" * 64,
        "result_semantic_hash": "sha256:" + "2" * 64,
        "token_derived_cost_nanos": 261_021_000,
    }
    observation = HeldoutACDispatchedCostObservation(
        **observation_body,
        content_hash=sha256_json(observation_body),
    )
    durable_body = {
        "schema_version": "heldout-ac-confounded-durable-evidence-v1",
        "run_id": run_id,
        "result_relative_path": observation.result_relative_path,
        "result_file_sha256": observation.result_file_sha256,
        "result_semantic_hash": observation.result_semantic_hash,
        "cost_observation_relative_path": f"experiments/heldout-ac/rows/{run_id}-cost.json",
        "cost_observation_file_sha256": "sha256:" + "3" * 64,
        "cost_observation_content_hash": observation.content_hash,
        "qualification_relative_path": f"qualifications/{run_id}.json" if full else None,
        "qualification_file_sha256": "sha256:" + "4" * 64 if full else None,
        "qualification_hash": "sha256:" + "5" * 64 if full else None,
        "usage_relative_path": (
            "experiments/heldout-ac/rows/"
            f"{candidate.execution_hash.removeprefix('sha256:')}/01-{run_id}-usage.json"
            if full
            else None
        ),
        "usage_file_sha256": "sha256:" + "6" * 64 if full else None,
        "usage_evidence_hash": "sha256:" + "7" * 64 if full else None,
        "receipt_relative_path": None,
        "receipt_file_sha256": None,
        "receipt_content_hash": None,
        "evaluator_failure_code": None,
        "evaluator_failure_event_relative_path": None,
        "evaluator_failure_event_file_sha256": None,
        "evaluator_failure_event_hash": None,
        "evaluator_failure_event": None,
        "token_derived_cost_nanos": observation.token_derived_cost_nanos,
    }
    durable = HeldoutACConfoundedDurableEvidence(
        **durable_body,
        content_hash=sha256_json(durable_body),
    )
    return observation, durable


@pytest.mark.parametrize(
    ("failure_stage", "expected_phase", "full_evidence"),
    [
        ("qualification", "qualification", False),
        ("authentication", "authentication", True),
    ],
)
def test_dispatched_cost_survives_qualification_or_authentication_failure(
    tmp_path: Path,
    failure_stage: str,
    expected_phase: str,
    full_evidence: bool,
) -> None:
    candidate, _plan_path, _plan_payload = _plan(tmp_path)
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=dispatcher-test-secret\n", encoding="utf-8")
    run_id = "run_heldout_cost_failure"
    observation, cost_only = _fake_cost_observation_and_durable(
        candidate,
        run_id=run_id,
        full=False,
    )
    _unused, full = _fake_cost_observation_and_durable(
        candidate,
        run_id=run_id,
        full=True,
    )

    with ExitStack() as stack:
        stack.enter_context(
            patch("patchloop.evals.heldout_ac_dispatcher.make_run_id", return_value=run_id)
        )
        stack.enter_context(patch.object(AgentRunner, "start", return_value=None))
        stack.enter_context(
            patch(
                "patchloop.evals.heldout_ac_dispatcher."
                "materialize_heldout_ac_runtime_task_authority",
                return_value=SimpleNamespace(
                    qualification_authority=object(),
                    task_binding=object(),
                ),
            )
        )
        stack.enter_context(
            patch(
                "patchloop.evals.heldout_ac_dispatcher.build_heldout_ac_run_manifest",
                return_value=object(),
            )
        )
        stack.enter_context(
            patch(
                "patchloop.evals.heldout_ac_dispatcher._persist_cost_observation",
                return_value=(observation, Path(cost_only.cost_observation_relative_path)),
            )
        )
        stack.enter_context(
            patch(
                "patchloop.evals.heldout_ac_dispatcher._durable_evidence_from_cost_observation",
                return_value=cost_only,
            )
        )
        if failure_stage == "qualification":
            stack.enter_context(
                patch(
                    "patchloop.evals.heldout_ac_dispatcher._persist_usage_evidence",
                    side_effect=ContractError("arbitrary marker source cost words"),
                )
            )
        else:
            stack.enter_context(
                patch(
                    "patchloop.evals.heldout_ac_dispatcher._persist_usage_evidence",
                    return_value=Path(full.usage_relative_path or "missing"),
                )
            )
            stack.enter_context(
                patch(
                    "patchloop.evals.heldout_ac_dispatcher._extend_durable_evidence_from_files",
                    return_value=full,
                )
            )
            stack.enter_context(
                patch(
                    "patchloop.evals.heldout_ac_dispatcher._authenticate_persisted_evidence",
                    side_effect=ContractError("completely different arbitrary message"),
                )
            )
        result = run_heldout_ac_campaign(
            execution_hash=candidate.execution_hash,
            env_file=env_file,
            root=tmp_path,
            repository=ROOT,
        )

    assert result.confound is not None
    assert result.confound.phase == expected_phase
    assert result.confound.durable_evidence == (full if full_evidence else cost_only)
    assert result.settled_model_cost_nanos == 0
    assert result.observed_unsettled_model_cost_nanos == 261_021_000
    assert result.observed_started_model_cost_nanos == 261_021_000
    assert result.unsettled_dispatched_runs == 1
    assert result.cost_accounting_complete is True


@pytest.mark.parametrize("receipt_kind", ["malformed", "wrong-binding"])
def test_completed_invalid_receipt_preserves_cost_only_confound_replay(
    tmp_path: Path,
    receipt_kind: str,
) -> None:
    source_binding = _checked_in_preflight_source_binding_without_replay()
    with (
        patch(
            f"{__name__}.load_heldout_ac_preflight_source_binding",
            return_value=source_binding,
        ),
        patch(
            "patchloop.evals.heldout_ac_dispatcher.heldout_ac_candidate_has_current_source_binding",
            return_value=True,
        ),
        patch(
            "patchloop.evals.heldout_ac_live_contract."
            "heldout_ac_candidate_has_current_source_binding",
            return_value=True,
        ),
    ):
        candidate, _plan_path, _plan_payload = _plan(tmp_path)

    row = candidate.schedule[0]
    chain = _v2_chain(
        VerdictState.PASS,
        task_path=row.task_path,
        evaluator_source_hash=candidate.source_qualification.evaluator_source_hash,
    )
    result_body = chain.result.model_dump(mode="json")
    result_body["usage"] = {
        **result_body["usage"],
        "input_tokens": 100,
        "output_tokens": 10,
        "model_cost_usd": 0.00012,
    }
    result = RunResult.model_validate(result_body)
    run_id = result.run_id
    result_bytes = result.model_dump_json(indent=2).encode("utf-8")
    result_relative = Path("artifacts") / "runs" / run_id / "result.json"
    result_path = tmp_path / result_relative
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_bytes(result_bytes)

    assert result.evaluator_contract is not None
    receipt_body = {
        "schema_version": "evaluator-v2-evaluation-receipt-v1",
        "run_id": run_id,
        "evaluator_contract_hash": result.evaluator_contract.contract_hash,
        "evaluator_source_hash": candidate.source_qualification.evaluator_source_hash,
        "suite_hash": "sha256:" + "0" * 64,
        "source_qualification_hash": (candidate.source_qualification.source_qualification_hash),
        "tool_schema_hash": "sha256:" + "1" * 64,
        "manifest_file_hash": "sha256:" + "2" * 64,
        "result_file_hash": sha256_bytes(result_bytes),
        "provenance_file_hash": "sha256:" + "3" * 64,
        "safety_bundle_file_hash": "sha256:" + "4" * 64,
        "safety_bundle_semantic_hash": "sha256:" + "5" * 64,
        "safety_bundle_artifact_hash": "sha256:" + "6" * 64,
        "submitted_patch_artifact_id": result.submitted_patch_artifact_id,
        "submitted_patch_content_hash": result.submitted_patch_artifact.content_hash,
        "event_prefix_hash": "sha256:" + "7" * 64,
        "through_sequence": 1,
        "preterminal_event_hash": "sha256:" + "8" * 64,
        "preterminal_through_sequence": 1,
        "evidence_inventory_hash": "sha256:" + "9" * 64,
        "evidence_artifact_count": 1,
        "evaluator_duration_ms": 1,
        "runtime_authenticated": True,
        "qualification_eligible": True,
    }
    receipt = EvaluatorV2EvaluationReceipt(
        **receipt_body,
        content_hash=sha256_json(receipt_body),
    )
    receipt_bytes = (
        b"{malformed-receipt"
        if receipt_kind == "malformed"
        else receipt.model_dump_json(indent=2).encode("utf-8")
    )
    receipt_relative = Path("artifacts") / "runs" / run_id / "evaluation-receipt.json"
    (tmp_path / receipt_relative).write_bytes(receipt_bytes)

    qualification_body = {
        "qualification_hash": "sha256:" + "a" * 64,
        "source_evidence_hash": "sha256:" + "b" * 64,
        "evaluator_v2_receipt_hash": receipt.content_hash,
        "evaluator_v2_receipt_file_hash": sha256_bytes(receipt_bytes),
        "evaluator_v2_source_hash": receipt.evaluator_source_hash,
        "evaluator_v2_source_qualification_hash": receipt.source_qualification_hash,
    }
    qualification_relative = Path("qualifications") / f"{run_id}.json"
    qualification_path = tmp_path / qualification_relative
    qualification_path.parent.mkdir(parents=True, exist_ok=True)
    qualification_path.write_bytes(
        json.dumps(
            qualification_body,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
    )

    usage_body = {
        "schema_version": "heldout-ac-durable-usage-evidence-v1",
        "run_id": run_id,
        "schedule_row_id": row.schedule_row_id,
        "pricing_binding_hash": candidate.pricing_binding_hash,
        "price_nanos_per_token": {
            "uncached_input": 750,
            "cached_input": 75,
            "cache_write_input": 750,
            "output": 4_500,
        },
        "usage": {
            key: result.usage.model_dump(mode="json")[key]
            for key in (
                "input_tokens",
                "cached_input_tokens",
                "cache_write_input_tokens",
                "output_tokens",
                "reasoning_output_tokens",
                "model_calls",
                "input_token_count_calls",
                "tool_calls",
                "wall_clock_ms",
            )
        },
        "token_derived_cost_nanos": 120_000,
        "qualification_hash": qualification_body["qualification_hash"],
        "source_evidence_hash": qualification_body["source_evidence_hash"],
        "persisted_result_file_hash": sha256_bytes(result_bytes),
        "evaluator_v2_receipt_file_hash": sha256_bytes(receipt_bytes),
    }
    usage = HeldoutACPersistedUsageEvidence(
        **usage_body,
        content_hash=sha256_json(usage_body),
    )
    usage_relative = (
        Path("experiments")
        / "heldout-ac"
        / "rows"
        / candidate.execution_hash.removeprefix("sha256:")
        / f"01-{run_id}-usage.json"
    )
    usage_path = tmp_path / usage_relative
    usage_path.parent.mkdir(parents=True, exist_ok=True)
    usage_path.write_bytes(
        json.dumps(
            usage.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
    )

    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=dispatcher-test-secret\n", encoding="utf-8")
    with ExitStack() as stack:
        stack.enter_context(
            patch("patchloop.evals.heldout_ac_dispatcher.make_run_id", return_value=run_id)
        )
        stack.enter_context(patch.object(AgentRunner, "start", return_value=None))
        stack.enter_context(
            patch(
                "patchloop.evals.heldout_ac_dispatcher."
                "materialize_heldout_ac_runtime_task_authority",
                return_value=SimpleNamespace(
                    qualification_authority=object(),
                    task_binding=object(),
                ),
            )
        )
        stack.enter_context(
            patch(
                "patchloop.evals.heldout_ac_dispatcher.build_heldout_ac_run_manifest",
                return_value=object(),
            )
        )
        stack.enter_context(
            patch(
                "patchloop.evals.heldout_ac_dispatcher._persist_usage_evidence",
                return_value=usage_relative,
            )
        )
        stack.enter_context(
            patch(
                "patchloop.evals.heldout_ac_live_contract."
                "heldout_ac_candidate_has_current_source_binding",
                return_value=True,
            )
        )
        result_record = run_heldout_ac_campaign(
            execution_hash=candidate.execution_hash,
            env_file=env_file,
            root=tmp_path,
            repository=ROOT,
        )

    assert result_record.confound is not None
    assert result_record.confound.durable_evidence is not None
    assert result_record.confound.durable_evidence.qualification_relative_path is None
    assert result_record.confound.durable_evidence.usage_relative_path is None
    assert result_record.confound.durable_evidence.receipt_relative_path is None
    assert result_record.settled_model_cost_nanos == 0
    assert result_record.observed_unsettled_model_cost_nanos == 120_000
    assert result_record.observed_started_model_cost_nanos == 120_000
    assert result_record.cost_accounting_complete is True

    successor = _synthetic_source_successor(source_binding)
    with (
        patch(
            "patchloop.evals.heldout_ac_preflight_source_qualification."
            "load_heldout_ac_preflight_source_binding",
            return_value=successor,
        ),
        patch(
            "patchloop.evals.heldout_ac_dispatcher.heldout_ac_candidate_has_current_source_binding",
            side_effect=AssertionError("historical replay consulted current source"),
        ),
        patch(
            "patchloop.evals.heldout_ac_live_contract."
            "heldout_ac_candidate_has_current_source_binding",
            side_effect=AssertionError("historical replay consulted current source"),
        ),
    ):
        assert not heldout_ac_candidate_has_current_source_binding(
            candidate,
            repository=ROOT,
        )
        replay = validate_heldout_ac_campaign_result(
            execution_hash=candidate.execution_hash,
            root=tmp_path,
            repository=ROOT,
        )
    assert replay["disposition"] == "inconclusive-matrix"
    assert replay["observed_unsettled_model_cost_nanos"] == 120_000
    assert replay["provider_calls_made_by_validation"] == 0


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
