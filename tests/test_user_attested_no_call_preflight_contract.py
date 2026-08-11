from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals import user_attested_no_call_preflight as preflight

REPOSITORY = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 8, 12, 0, 0, tzinfo=UTC)


def _contract() -> preflight.UserAttestedNoCallPreflightContract:
    return preflight.load_user_attested_no_call_preflight_contract(repository=REPOSITORY)


def _attestation(
    contract: preflight.UserAttestedNoCallPreflightContract,
    *,
    recorded_at: datetime = T0,
) -> preflight.UserCredentialLocationAttestation:
    return preflight.build_user_credential_location_attestation(
        contract,
        claim=preflight.ATTESTATION_CLAIM,
        recorded_at=recorded_at,
    )


def _evidence(
    contract: preflight.UserAttestedNoCallPreflightContract,
    attestation: preflight.UserCredentialLocationAttestation,
    *,
    recorded_at: datetime = T0,
) -> preflight.UserAttestedStateChangeEvidence:
    return preflight.bind_user_attested_state_change_evidence(
        contract,
        attestation,
        recorded_at=recorded_at,
    )


def _approval_pair(
    contract: preflight.UserAttestedNoCallPreflightContract,
    evidence: preflight.UserAttestedStateChangeEvidence,
) -> tuple[preflight.UserExactApprovalReceipt, preflight.UserAttestedApprovalBinding]:
    receipt = preflight.build_user_exact_approval_receipt(
        contract,
        evidence,
        recorded_at=T0 + timedelta(seconds=1),
    )
    approval = preflight.bind_user_attested_approval(
        contract,
        evidence,
        receipt,
        recorded_at=T0 + timedelta(seconds=1),
    )
    return receipt, approval


def test_contract_materialization_is_deterministic_and_live_closed() -> None:
    first = preflight.materialize_user_attested_no_call_preflight_contract(repository=REPOSITORY)
    path = REPOSITORY / preflight.CONTRACT_PATH
    raw = path.read_bytes()
    mtime = path.stat().st_mtime_ns
    replay = preflight.materialize_user_attested_no_call_preflight_contract(repository=REPOSITORY)

    assert replay == first
    assert path.read_bytes() == raw
    assert path.stat().st_mtime_ns == mtime
    assert first["execution_authorized"] is False
    assert first["dotenv_or_credential_observed"] is False


def test_contract_versions_receipt_free_attestation_without_claiming_proof() -> None:
    contract = _contract()

    assert contract.contract_version == preflight.CONTRACT_VERSION
    assert contract.predecessor_contract_version == "ac-evaluator-v2-no-call-preflight-v1"
    assert contract.state_change_rule.external_receipt_required is False
    assert contract.state_change_rule.independent_trust_anchor_required is False
    assert contract.state_change_rule.attestation_proves_credential_presence is False
    assert contract.state_change_rule.exact_preflight_still_required is True
    assert contract.dotenv_loader_contract.exact_key_names == ("OPENAI_API_KEY",)
    assert contract.dotenv_loader_contract.parent_or_agent_value_return_limit == 0
    assert contract.dotenv_loader_contract.value_log_persist_hash_prefix_or_length_limit == 0
    assert contract.dotenv_loader_contract.loader_runtime_implemented is False
    assert contract.source_authority.external_preflight_attempt_authorized is False


def test_user_attestation_and_state_evidence_are_nonsecret_and_content_addressed() -> None:
    contract = _contract()
    attestation = _attestation(contract)
    evidence = _evidence(contract, attestation)

    assert attestation.attestation_id == "ncpattestation_" + attestation.content_hash.removeprefix(
        "sha256:"
    )
    assert evidence.evidence_id == "ncpstate_" + evidence.content_hash.removeprefix("sha256:")
    assert evidence.user_attestation_id == attestation.attestation_id
    assert evidence.external_receipt_present is False
    assert evidence.independent_verification_completed is False
    assert evidence.attestation_proves_credential_presence is False
    assert evidence.exact_preflight_still_required is True
    assert evidence.raw_credential_value_observed is False
    assert evidence.raw_credential_value_persisted is False
    raw = preflight._canonical_bytes(attestation) + preflight._canonical_bytes(evidence)
    preflight.validate_no_secret_material((raw,))
    assert b"sk-" not in raw.lower()


def test_attestation_claim_and_chronology_fail_closed() -> None:
    contract = _contract()
    with pytest.raises(preflight.UserAttestedNoCallPreflightError, match="claim"):
        preflight.build_user_credential_location_attestation(
            contract,
            claim="not-the-exact-claim",  # type: ignore[arg-type]
            recorded_at=T0,
        )
    attestation = _attestation(contract)
    with pytest.raises(preflight.UserAttestedNoCallPreflightError, match="predates"):
        _evidence(contract, attestation, recorded_at=T0 - timedelta(seconds=1))


def test_exact_approval_binds_the_later_exact_state_identity_only() -> None:
    contract = _contract()
    evidence = _evidence(contract, _attestation(contract))
    receipt, approval = _approval_pair(contract, evidence)

    assert receipt.state_change_evidence_id == evidence.evidence_id
    assert approval.state_change_evidence_id == evidence.evidence_id
    assert approval.user_approval_receipt_id == receipt.receipt_id
    assert approval.approved_scopes == preflight.APPROVED_SCOPES
    assert approval.attempt_limit == 1
    assert approval.cost_or_paid_execution_authorized is False
    assert approval.provider_evaluator_agent_execution_authorized is False

    wrong = evidence.model_copy(update={"evidence_id": "ncpstate_" + "f" * 64})
    with pytest.raises(ValidationError):
        preflight.UserAttestedStateChangeEvidence.model_validate(wrong.model_dump(mode="json"))
    with pytest.raises(preflight.UserAttestedNoCallPreflightError, match="predates"):
        preflight.build_user_exact_approval_receipt(
            contract,
            evidence,
            recorded_at=T0 - timedelta(seconds=1),
        )


def test_binding_rejects_tamper_after_model_copy() -> None:
    contract = _contract()
    attestation = _attestation(contract)
    evidence = _evidence(contract, attestation)
    _, approval = _approval_pair(contract, evidence)

    for value, model, field, replacement in (
        (
            contract,
            preflight.UserAttestedNoCallPreflightContract,
            "content_hash",
            "sha256:" + "0" * 64,
        ),
        (
            attestation,
            preflight.UserCredentialLocationAttestation,
            "content_hash",
            "sha256:" + "1" * 64,
        ),
        (
            evidence,
            preflight.UserAttestedStateChangeEvidence,
            "user_attestation_content_hash",
            "sha256:" + "2" * 64,
        ),
        (
            approval,
            preflight.UserAttestedApprovalBinding,
            "state_change_evidence_content_hash",
            "sha256:" + "3" * 64,
        ),
    ):
        changed = value.model_copy(update={field: replacement})
        with pytest.raises(ValidationError):
            model.model_validate(changed.model_dump(mode="json"))


def test_state_writer_is_append_only_and_does_not_read_or_stat_dotenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suffix = uuid.uuid4().hex
    attestation_path = Path("reports/live-pilot/artifacts") / f".pytest-attestation-{suffix}.json"
    evidence_path = Path("reports/live-pilot/artifacts") / f".pytest-state-{suffix}.json"
    original_read = preflight._read_bytes
    observed_paths: list[str] = []

    def audited_read(root: Path, relative: Path) -> bytes:
        observed_paths.append(relative.as_posix())
        assert relative.as_posix() != ".env"
        return original_read(root, relative)

    monkeypatch.setattr(preflight, "USER_ATTESTATION_PATH", attestation_path)
    monkeypatch.setattr(preflight, "STATE_EVIDENCE_PATH", evidence_path)
    monkeypatch.setattr(
        preflight,
        "validate_user_attested_source_qualification",
        lambda **_kwargs: {"status": "test-only-qualified"},
    )
    monkeypatch.setattr(preflight, "_read_bytes", audited_read)
    try:
        summary = preflight.record_user_attested_state_change(
            claim=preflight.ATTESTATION_CLAIM,
            recorded_at=T0,
            repository=REPOSITORY,
        )
        assert summary["credential_presence_verified"] is False
        assert summary["dotenv_read_or_stat_performed"] is False
        assert summary["exact_approval_required"] is True
        with pytest.raises(preflight.UserAttestedNoCallPreflightError, match="already exists"):
            preflight.record_user_attested_state_change(
                claim=preflight.ATTESTATION_CLAIM,
                recorded_at=T0,
                repository=REPOSITORY,
            )
        assert ".env" not in observed_paths
    finally:
        for relative in (attestation_path, evidence_path):
            selected = REPOSITORY / relative
            if selected.exists():
                selected.unlink()


def test_source_qualification_replays_when_artifact_exists() -> None:
    selected = REPOSITORY / preflight.QUALIFICATION_PATH
    if not selected.exists():
        pytest.skip("source qualification is created only after the exact source commit")
    summary = preflight.validate_user_attested_source_qualification(repository=REPOSITORY)
    assert summary["execution_authorized"] is False
    assert summary["dotenv_or_credential_observations_made"] == 0


def test_module_has_no_dotenv_sdk_docker_or_network_observation_entrypoint() -> None:
    source = (REPOSITORY / "patchloop/evals/user_attested_no_call_preflight.py").read_text(
        encoding="utf-8"
    )

    assert "dotenv_values" not in source
    assert "load_dotenv" not in source
    assert "os.environ[" not in source
    assert "socket." not in source
    assert "DockerSandbox" not in source
    assert "OpenAI(" not in source
    assert "loader_runtime_implemented: Literal[False]" in source
