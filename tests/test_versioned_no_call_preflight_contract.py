from __future__ import annotations

import socket
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.evals import versioned_no_call_preflight as preflight
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"preflight source crossed forbidden {label} boundary")

    return fail


@pytest.fixture
def isolated_contract_path(monkeypatch: pytest.MonkeyPatch):
    relative = Path("experiments") / f".pytest-preflight-{uuid.uuid4().hex}.json"
    selected = REPOSITORY / relative
    monkeypatch.setattr(preflight, "CONTRACT_PATH", relative)
    monkeypatch.setattr(preflight.subprocess, "run", _forbidden("process"))
    monkeypatch.setattr(preflight.subprocess, "Popen", _forbidden("process"))
    monkeypatch.setattr(socket, "socket", _forbidden("network"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("network"))
    try:
        yield selected
    finally:
        if selected.exists() or selected.is_symlink():
            selected.unlink()


def _contract() -> preflight.VersionedNoCallPreflightContract:
    return preflight.load_versioned_no_call_preflight_contract(repository=REPOSITORY)


def _evidence(
    contract: preflight.VersionedNoCallPreflightContract,
    *,
    receipt_hash: str = SHA_A,
    trust_hash: str = SHA_B,
    recorded_at: datetime = T0,
) -> preflight.PreflightStateChangeEvidence:
    return preflight.bind_preflight_state_change_evidence(
        contract,
        provisioning_receipt_hash=receipt_hash,
        independent_trust_anchor_hash=trust_hash,
        recorded_at=recorded_at,
    )


def _approval(
    contract: preflight.VersionedNoCallPreflightContract,
    evidence: preflight.PreflightStateChangeEvidence,
    *,
    approval_hash: str = SHA_C,
    recorded_at: datetime = T0 + timedelta(seconds=1),
) -> preflight.PreflightApprovalBinding:
    return preflight.bind_preflight_approval(
        contract,
        evidence,
        authenticated_approval_receipt_hash=approval_hash,
        recorded_at=recorded_at,
    )


def _snapshot(
    *,
    evidence_ids: tuple[str, ...] = (),
    approval_ids: tuple[str, ...] = (),
    attempt_ids: tuple[str, ...] = (),
) -> preflight.PreflightConsumptionSnapshot:
    return preflight.build_preflight_consumption_snapshot(
        ledger_root_hash=sha256_json(
            {
                "evidence": list(evidence_ids),
                "approvals": list(approval_ids),
                "attempts": list(attempt_ids),
            }
        ),
        through_sequence=len(evidence_ids) + len(approval_ids) + len(attempt_ids),
        consumed_state_change_evidence_ids=evidence_ids,
        consumed_approval_ids=approval_ids,
        reserved_or_terminal_attempt_ids=attempt_ids,
    )


def _attempt(
    contract: preflight.VersionedNoCallPreflightContract,
    evidence: preflight.PreflightStateChangeEvidence,
    approval: preflight.PreflightApprovalBinding,
    snapshot: preflight.PreflightConsumptionSnapshot,
    *,
    created_at: datetime = T0 + timedelta(seconds=2),
) -> preflight.PreflightAttemptIntent:
    return preflight.build_preflight_attempt_intent(
        contract,
        evidence,
        approval,
        snapshot,
        trusted_state_change_evidence_content_hash=evidence.content_hash,
        trusted_approval_content_hash=approval.content_hash,
        trusted_consumption_snapshot_hash=snapshot.content_hash,
        created_at=created_at,
    )


def _ready_activity() -> preflight.PreflightActivitySummary:
    return preflight.PreflightActivitySummary(
        docker_metadata_query_count=2,
        environment_membership_check_count=3,
        sdk_isolated_child_start_count=1,
    )


def _ready_observation() -> preflight.PreflightObservationResult:
    return preflight.PreflightObservationResult(
        docker_engine_available=True,
        qualified_image_identity_matched=True,
        openai_api_key_present=True,
        pythonhome_absent=True,
        pythonpath_absent=True,
        sdk_import_succeeded=True,
        official_api_base_url_default=True,
        sdk_transport_retry_zero=True,
    )


def test_contract_materialization_is_deterministic_append_only_and_offline(
    isolated_contract_path: Path,
) -> None:
    first = preflight.materialize_versioned_no_call_preflight_contract(repository=REPOSITORY)
    raw = isolated_contract_path.read_bytes()
    first_mtime = isolated_contract_path.stat().st_mtime_ns
    replay = preflight.materialize_versioned_no_call_preflight_contract(repository=REPOSITORY)

    assert replay == first
    assert isolated_contract_path.read_bytes() == raw
    assert isolated_contract_path.stat().st_mtime_ns == first_mtime
    assert first["execution_authorized"] is False
    assert first["contract_version"] == preflight.CONTRACT_VERSION
    assert first["file_sha256"] == sha256_bytes(raw)


def test_contract_binds_successor_and_keeps_d142_audit_only() -> None:
    contract = _contract()

    assert contract.contract_id == "ncpcontract_" + contract.content_hash.removeprefix("sha256:")
    assert contract.d141_blocked_terminal.status == preflight.D141_TERMINAL_STATUS
    assert contract.d142_deferred_gate.identity == preflight.D142_GATE_ID
    assert contract.d142_is_audit_only is True
    assert contract.state_change_rule.exact_subject_names == ("OPENAI_API_KEY",)
    assert contract.state_change_rule.unchanged_blocker_is_state_change is False
    assert contract.state_change_rule.source_or_contract_change_requires_version_bump is True
    assert contract.observation_contract.phases == ("docker_metadata", "sdk_no_call")
    assert contract.source_authority.external_preflight_attempt_authorized is False
    assert contract.source_authority.credential_provisioning_authorized is False


def test_contract_contains_no_raw_credential_or_runtime_result() -> None:
    raw = (REPOSITORY / preflight.CONTRACT_PATH).read_bytes()
    lowered = raw.lower()

    assert b"sk-" not in lowered
    assert b'credential_value"' not in lowered
    assert b"openai_api_key_present" not in lowered
    assert b"environment_presence_bits" not in lowered
    assert b"attempt_id" not in lowered
    assert b"approval_id" not in lowered


def test_attempt_identity_binds_contract_state_change_approval_and_trusted_ledger() -> None:
    contract = _contract()
    evidence = _evidence(contract)
    approval = _approval(contract, evidence)
    snapshot = _snapshot()
    attempt = _attempt(contract, evidence, approval, snapshot)

    assert attempt.contract_id == contract.contract_id
    assert attempt.state_change_evidence_id == evidence.evidence_id
    assert attempt.approval_id == approval.approval_id
    assert attempt.consumption_snapshot_hash == snapshot.content_hash
    assert attempt.authority.environment_membership_observation_authorized is True
    assert attempt.authority.credential_value_read_authorized is False
    assert attempt.authority.provider_evaluator_agent_execution_authorized is False
    assert attempt.retry_or_resume_allowed is False

    changed_evidence = _evidence(contract, receipt_hash="sha256:" + "d" * 64)
    changed_approval = _approval(contract, changed_evidence)
    changed_attempt = _attempt(contract, changed_evidence, changed_approval, snapshot)
    assert changed_attempt.attempt_id != attempt.attempt_id


def test_evidence_approval_and_attempt_require_independent_chronological_bindings() -> None:
    contract = _contract()
    with pytest.raises(preflight.VersionedNoCallPreflightError, match="independent"):
        _evidence(contract, receipt_hash=SHA_A, trust_hash=SHA_A)

    evidence = _evidence(contract)
    with pytest.raises(preflight.VersionedNoCallPreflightError, match="independent"):
        _approval(contract, evidence, approval_hash=SHA_A)
    with pytest.raises(preflight.VersionedNoCallPreflightError, match="predates"):
        _approval(contract, evidence, recorded_at=T0 - timedelta(seconds=1))

    approval = _approval(contract, evidence)
    with pytest.raises(preflight.VersionedNoCallPreflightError, match="predates"):
        _attempt(
            contract,
            evidence,
            approval,
            _snapshot(),
            created_at=T0,
        )


@pytest.mark.parametrize(
    ("trusted_evidence", "trusted_approval", "trusted_snapshot", "match"),
    [
        (SHA_A, None, None, "state-change evidence"),
        (None, SHA_A, None, "approval"),
        (None, None, SHA_A, "consumption snapshot"),
    ],
)
def test_attempt_rejects_any_untrusted_binding(
    trusted_evidence: str | None,
    trusted_approval: str | None,
    trusted_snapshot: str | None,
    match: str,
) -> None:
    contract = _contract()
    evidence = _evidence(contract)
    approval = _approval(contract, evidence)
    snapshot = _snapshot()

    with pytest.raises(preflight.VersionedNoCallPreflightError, match=match):
        preflight.build_preflight_attempt_intent(
            contract,
            evidence,
            approval,
            snapshot,
            trusted_state_change_evidence_content_hash=(
                evidence.content_hash if trusted_evidence is None else trusted_evidence
            ),
            trusted_approval_content_hash=(
                approval.content_hash if trusted_approval is None else trusted_approval
            ),
            trusted_consumption_snapshot_hash=(
                snapshot.content_hash if trusted_snapshot is None else trusted_snapshot
            ),
            created_at=T0 + timedelta(seconds=2),
        )


def test_consumed_state_change_or_approval_cannot_create_another_attempt() -> None:
    contract = _contract()
    evidence = _evidence(contract)
    approval = _approval(contract, evidence)

    with pytest.raises(preflight.VersionedNoCallPreflightError, match="already consumed"):
        _attempt(contract, evidence, approval, _snapshot(evidence_ids=(evidence.evidence_id,)))
    with pytest.raises(preflight.VersionedNoCallPreflightError, match="already consumed"):
        _attempt(contract, evidence, approval, _snapshot(approval_ids=(approval.approval_id,)))


def test_attempt_ledger_rejects_reused_evidence_and_approval() -> None:
    contract = _contract()
    evidence = _evidence(contract)
    approval = _approval(contract, evidence)
    snapshot = _snapshot()
    first = _attempt(contract, evidence, approval, snapshot)
    second = _attempt(
        contract,
        evidence,
        approval,
        snapshot,
        created_at=T0 + timedelta(seconds=3),
    )

    with pytest.raises(preflight.VersionedNoCallPreflightError, match="state-change evidence"):
        preflight.validate_preflight_attempt_ledger(contract, (first, second))


def test_intent_and_action_started_are_consuming_and_never_retryable() -> None:
    contract = _contract()
    evidence = _evidence(contract)
    approval = _approval(contract, evidence)
    attempt = _attempt(contract, evidence, approval, _snapshot())

    intent_only = preflight.validate_preflight_transition_chain(attempt, ())
    assert intent_only["evidence_consumed"] is True
    assert intent_only["observation_started"] is False
    assert intent_only["retry_or_resume_allowed"] is False

    started = preflight.build_preflight_action_started_transition(
        attempt, recorded_at=T0 + timedelta(seconds=3)
    )
    started_only = preflight.validate_preflight_transition_chain(attempt, (started,))
    assert started_only["observation_started"] is True
    assert started_only["terminal"] is False
    assert started_only["retry_or_resume_allowed"] is False


def test_ready_terminal_requires_complete_bounded_zero_call_activity() -> None:
    contract = _contract()
    evidence = _evidence(contract)
    approval = _approval(contract, evidence)
    attempt = _attempt(contract, evidence, approval, _snapshot())
    started = preflight.build_preflight_action_started_transition(
        attempt, recorded_at=T0 + timedelta(seconds=3)
    )
    terminal = preflight.build_preflight_terminal_transition(
        attempt,
        started,
        outcome=preflight.PreflightTerminalOutcome.READY,
        reason=None,
        activity=_ready_activity(),
        observation=_ready_observation(),
        recorded_at=T0 + timedelta(seconds=4),
    )
    result = preflight.validate_preflight_transition_chain(attempt, (started, terminal))

    assert result["terminal"] is True
    assert result["terminal_outcome"] == "ready"
    assert terminal.activity is not None
    assert terminal.activity.network_call_count == 0
    assert terminal.activity.provider_evaluator_agent_call_count == 0

    incomplete = preflight.PreflightActivitySummary(
        docker_metadata_query_count=1,
        environment_membership_check_count=3,
        sdk_isolated_child_start_count=1,
    )
    with pytest.raises(ValidationError, match="complete bounded observations"):
        preflight.build_preflight_terminal_transition(
            attempt,
            started,
            outcome=preflight.PreflightTerminalOutcome.READY,
            reason=None,
            activity=incomplete,
            observation=_ready_observation(),
            recorded_at=T0 + timedelta(seconds=4),
        )

    incomplete_result = _ready_observation().model_copy(
        update={"qualified_image_identity_matched": False}
    )
    with pytest.raises(ValidationError, match="exact positive observations"):
        preflight.build_preflight_terminal_transition(
            attempt,
            started,
            outcome=preflight.PreflightTerminalOutcome.READY,
            reason=None,
            activity=_ready_activity(),
            observation=incomplete_result,
            recorded_at=T0 + timedelta(seconds=4),
        )


def test_blocked_error_reason_matrix_and_terminal_append_are_fail_closed() -> None:
    contract = _contract()
    evidence = _evidence(contract)
    approval = _approval(contract, evidence)
    attempt = _attempt(contract, evidence, approval, _snapshot())
    started = preflight.build_preflight_action_started_transition(
        attempt, recorded_at=T0 + timedelta(seconds=3)
    )
    activity = preflight.PreflightActivitySummary(
        docker_metadata_query_count=0,
        environment_membership_check_count=3,
        sdk_isolated_child_start_count=0,
    )
    blocked = preflight.build_preflight_terminal_transition(
        attempt,
        started,
        outcome=preflight.PreflightTerminalOutcome.BLOCKED,
        reason=preflight.PreflightTerminalReason.CREDENTIAL_MEMBERSHIP_MISSING,
        activity=activity,
        observation=preflight.PreflightObservationResult(openai_api_key_present=False),
        recorded_at=T0 + timedelta(seconds=4),
    )
    assert (
        preflight.validate_preflight_transition_chain(attempt, (started, blocked))[
            "terminal_outcome"
        ]
        == "blocked"
    )

    with pytest.raises(ValidationError, match="ERROR-only"):
        preflight.build_preflight_terminal_transition(
            attempt,
            started,
            outcome=preflight.PreflightTerminalOutcome.BLOCKED,
            reason=preflight.PreflightTerminalReason.INTEGRITY_ERROR,
            activity=activity,
            observation=preflight.PreflightObservationResult(openai_api_key_present=False),
            recorded_at=T0 + timedelta(seconds=4),
        )
    with pytest.raises(ValidationError, match="blocker reason"):
        preflight.build_preflight_terminal_transition(
            attempt,
            started,
            outcome=preflight.PreflightTerminalOutcome.ERROR,
            reason=preflight.PreflightTerminalReason.SDK_IMPORT_UNAVAILABLE,
            activity=activity,
            observation=preflight.PreflightObservationResult(sdk_import_succeeded=False),
            recorded_at=T0 + timedelta(seconds=4),
        )
    with pytest.raises(preflight.VersionedNoCallPreflightError, match="append after terminal"):
        preflight.validate_preflight_transition_chain(attempt, (started, blocked, blocked))

    with pytest.raises(ValidationError, match="does not match observation"):
        preflight.build_preflight_terminal_transition(
            attempt,
            started,
            outcome=preflight.PreflightTerminalOutcome.BLOCKED,
            reason=preflight.PreflightTerminalReason.CREDENTIAL_MEMBERSHIP_MISSING,
            activity=activity,
            observation=preflight.PreflightObservationResult(openai_api_key_present=True),
            recorded_at=T0 + timedelta(seconds=4),
        )


def test_hash_tamper_extra_secret_field_and_wrong_contract_fail_closed() -> None:
    contract = _contract()
    evidence = _evidence(contract)
    approval = _approval(contract, evidence)
    snapshot = _snapshot()

    with pytest.raises(ValidationError, match="content hash mismatch"):
        preflight.PreflightStateChangeEvidence.model_validate(
            {**evidence.model_dump(mode="json"), "content_hash": SHA_A}
        )
    with pytest.raises(ValidationError, match="extra_forbidden"):
        preflight.PreflightStateChangeEvidence.model_validate(
            {**evidence.model_dump(mode="json"), "credential_value": "raw-secret"}
        )
    with pytest.raises(ValidationError, match="exact booleans"):
        preflight.PreflightObservationResult(openai_api_key_present="true")
    with pytest.raises(ValidationError, match="exact integers"):
        preflight.PreflightActivitySummary(
            docker_metadata_query_count="2",
            environment_membership_check_count=3,
            sdk_isolated_child_start_count=1,
        )
    forged_contract = contract.model_copy(update={"content_hash": SHA_A})
    with pytest.raises(ValidationError, match="content hash mismatch"):
        preflight.build_preflight_attempt_intent(
            forged_contract,
            evidence,
            approval,
            snapshot,
            trusted_state_change_evidence_content_hash=evidence.content_hash,
            trusted_approval_content_hash=approval.content_hash,
            trusted_consumption_snapshot_hash=snapshot.content_hash,
            created_at=T0 + timedelta(seconds=2),
        )


def test_source_qualification_factory_binds_committed_bytes_and_closes_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_commit = preflight.SourceCommitBinding(
        commit="1" * 40,
        tree="2" * 40,
        parents=("3" * 40,),
        added_paths=preflight.SOURCE_COMMIT_ADDED_PATHS,
    )
    monkeypatch.setattr(preflight, "_commit_binding", lambda _root, _commit: fake_commit)

    def committed_file(
        root: Path, _commit: str, path: Path
    ) -> tuple[preflight.CommittedFileBinding, bytes]:
        raw = (root / path).read_bytes()
        return (
            preflight.CommittedFileBinding(
                path=path.as_posix(),
                blob_oid=sha256_bytes(raw).removeprefix("sha256:")[:40],
                file_bytes=len(raw),
                file_sha256=sha256_bytes(raw),
            ),
            raw,
        )

    monkeypatch.setattr(preflight, "_committed_file", committed_file)
    value = preflight._build_source_qualification(
        REPOSITORY,
        source_commit="synthetic",
        recorded_at=T0,
    )

    assert value.source_commit == fake_commit
    assert value.contract_file.path == preflight.CONTRACT_PATH.as_posix()
    assert value.authority.contract_source_qualified is True
    assert value.authority.state_change_evidence_created is False
    assert value.authority.approval_created_or_inferred is False
    assert value.authority.attempt_or_transition_created is False
    assert value.authority.network_provider_evaluator_agent_call_count == 0


def test_checked_in_source_qualification_replays_when_present() -> None:
    selected = REPOSITORY / preflight.QUALIFICATION_PATH
    if not selected.exists():
        pytest.skip("source commit must be created before the append-only qualification artifact")
    first_mtime = selected.stat().st_mtime_ns
    validated = preflight.validate_versioned_no_call_preflight_source_qualification(
        repository=REPOSITORY
    )
    replay = preflight.run_versioned_no_call_preflight_source_qualification(repository=REPOSITORY)
    assert replay == validated
    assert selected.stat().st_mtime_ns == first_mtime
    assert validated["execution_authorized"] is False
    assert validated["credential_or_environment_observations_made"] == 0
    assert validated["docker_or_sdk_observations_made"] == 0
    assert validated["provider_evaluator_agent_calls_made"] == 0


def test_cli_has_no_attempt_or_external_observation_mode() -> None:
    source = (REPOSITORY / "scripts/build_versioned_no_call_preflight_contract.py").read_text(
        encoding="utf-8"
    )
    assert "--materialize-contract" in source
    assert "--qualify-source" in source
    assert "--validate" in source
    assert "--run-attempt" not in source
    assert "--observe" not in source
    assert "OPENAI_API_KEY" not in source
    assert "DockerSandbox" not in source
