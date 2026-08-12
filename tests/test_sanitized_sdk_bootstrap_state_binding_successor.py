from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals import sanitized_sdk_bootstrap_state_binding_successor as successor

REPOSITORY = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
SHA_A = "sha256:" + "a" * 64


@pytest.fixture(scope="module")
def contract() -> successor.StateBindingSuccessorContract:
    return successor.load_contract(repository=REPOSITORY)


@pytest.fixture(autouse=True)
def cached_contract_validation(
    monkeypatch: pytest.MonkeyPatch,
    contract: successor.StateBindingSuccessorContract,
) -> None:
    monkeypatch.setattr(successor, "load_contract", lambda **_kwargs: contract)


def _file(path: Path) -> successor.CommittedFileBinding:
    return successor.CommittedFileBinding(
        path=path.as_posix(),
        blob_oid="a" * 40,
        file_bytes=1,
        file_sha256=SHA_A,
    )


def _qualification(
    contract: successor.StateBindingSuccessorContract,
) -> successor.SourceQualification:
    files = tuple(_file(path) for path in successor.SOURCE_FILES)
    by_path = {item.path: item for item in files}
    body = {
        "schema_version": successor.QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": successor.QUALIFICATION_ID,
        "status": successor.QUALIFICATION_STATUS,
        "recorded_at": NOW,
        "source_commit": successor.SourceCommitBinding(
            commit="b" * 40,
            tree="c" * 40,
            parents=(successor.SOURCE_PARENT_COMMIT,),
            added_paths=successor.SOURCE_ADDED_PATHS,
        ).model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "contract_file": by_path[successor.CONTRACT_PATH.as_posix()].model_dump(mode="json"),
        "runtime_file": by_path[successor.RUNTIME_PATH.as_posix()].model_dump(mode="json"),
        "predecessor_contract_file": by_path[successor.v9.CONTRACT_PATH.as_posix()].model_dump(
            mode="json"
        ),
        "predecessor_runtime_file": by_path[successor.v9.RUNTIME_PATH.as_posix()].model_dump(
            mode="json"
        ),
        "predecessor_qualification_file": by_path[
            successor.v9.QUALIFICATION_PATH.as_posix()
        ].model_dump(mode="json"),
        "predecessor_source_commit": successor.V9_SOURCE_COMMIT,
        "predecessor_source_qualification_hash": contract.predecessor.source_qualification_hash,
        "authority": successor.QualificationAuthority().model_dump(mode="json"),
        "next_gate": successor.QUALIFICATION_NEXT_GATE,
    }
    return successor.SourceQualification(**body, content_hash=successor._hash_body(body))


def test_contract_binds_exact_v9_and_closes_live_authority() -> None:
    contract = successor.load_contract(repository=REPOSITORY)

    assert contract.predecessor.source_commit == successor.V9_SOURCE_COMMIT
    assert contract.predecessor.qualification_commit == successor.V9_QUALIFICATION_COMMIT
    assert contract.predecessor.v9_parent_runtime_integration_implemented is True
    assert contract.predecessor.v9_state_approval_or_attempt_entrypoint_implemented is False
    assert contract.state_rule.dotenv_exact_key_names == ("OPENAI_API_KEY",)
    assert contract.state_rule.state_change_evidence_reusable is False
    assert contract.state_rule.generic_continuation_is_exact_attestation_or_approval is False
    assert contract.state_materializer_implemented is True
    assert contract.approval_or_attempt_entrypoint_implemented is False
    authority = contract.authority.model_dump(mode="json")
    assert authority["contract_materialization_authorized"] is True
    assert authority["source_qualification_authorized"] is True
    assert authority["future_exact_attestation_binding_supported"] is True
    assert authority["future_state_evidence_binding_supported"] is True
    assert all(
        value is False
        for key, value in authority.items()
        if key
        not in {
            "contract_materialization_authorized",
            "source_qualification_authorized",
            "future_exact_attestation_binding_supported",
            "future_state_evidence_binding_supported",
        }
    )


def test_exact_post_qualification_statement_builds_unverified_state() -> None:
    contract = successor.load_contract(repository=REPOSITORY)
    qualification = _qualification(contract)
    statement = successor.expected_attestation_statement(contract, qualification)
    attestation = successor.build_user_attestation(
        contract,
        qualification,
        statement=statement,
        recorded_at=NOW,
    )
    state = successor.bind_state_evidence(
        contract,
        qualification,
        attestation,
        recorded_at=NOW,
    )

    assert contract.contract_id in statement
    assert qualification.content_hash in statement
    assert attestation.statement_sha256 == successor.sha256_bytes(statement.encode("utf-8"))
    assert attestation.docker_desktop_running_reported is True
    assert attestation.dotenv_exact_key_names_reported == ("OPENAI_API_KEY",)
    assert attestation.independent_verification_completed is False
    assert attestation.execution_authority_granted is False
    assert state.evidence_id.startswith("ncpstate_")
    assert state.docker_daemon_ready_verified is False
    assert state.dotenv_file_or_membership_verified is False
    assert state.systemroot_presence_or_value_attested is False
    assert state.runtime_execution_authorized is False
    assert state.separate_exact_approval_required is True
    assert state.state_change_evidence_reusable is False
    assert state.patchloop_external_observation_count == 0
    assert state.patchloop_external_mutation_count == 0


@pytest.mark.parametrize(
    "replacement",
    (
        "진행해줘",
        "Docker Desktop is running and .env has OPENAI_API_KEY",
        successor.ATTESTATION_TEMPLATE.replace("{contract_id}", "ncpcontract_" + "0" * 64),
    ),
)
def test_stale_generic_or_wrong_identity_statement_fails(replacement: str) -> None:
    contract = successor.load_contract(repository=REPOSITORY)
    qualification = _qualification(contract)
    statement = replacement.format(qualification_hash=qualification.content_hash)
    with pytest.raises(successor.StateBindingSuccessorError, match="statement differs"):
        successor.build_user_attestation(
            contract,
            qualification,
            statement=statement,
            recorded_at=NOW,
        )


def test_attestation_must_follow_qualification_and_state_must_follow_attestation() -> None:
    contract = successor.load_contract(repository=REPOSITORY)
    qualification = _qualification(contract)
    statement = successor.expected_attestation_statement(contract, qualification)
    with pytest.raises(successor.StateBindingSuccessorError, match="predates qualification"):
        successor.build_user_attestation(
            contract,
            qualification,
            statement=statement,
            recorded_at=NOW - timedelta(seconds=1),
        )
    attestation = successor.build_user_attestation(
        contract,
        qualification,
        statement=statement,
        recorded_at=NOW,
    )
    with pytest.raises(successor.StateBindingSuccessorError, match="state predates"):
        successor.bind_state_evidence(
            contract,
            qualification,
            attestation,
            recorded_at=NOW - timedelta(seconds=1),
        )


def test_hash_extra_field_and_claim_tamper_fail() -> None:
    contract = successor.load_contract(repository=REPOSITORY)
    payload = contract.model_dump(mode="json")
    payload["content_hash"] = SHA_A
    with pytest.raises(ValidationError):
        successor.StateBindingSuccessorContract.model_validate(payload)
    payload = contract.model_dump(mode="json")
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        successor.StateBindingSuccessorContract.model_validate(payload)

    qualification = _qualification(contract)
    attestation = successor.build_user_attestation(
        contract,
        qualification,
        statement=successor.expected_attestation_statement(contract, qualification),
        recorded_at=NOW,
    )
    changed = attestation.model_dump(mode="json")
    changed["execution_authority_granted"] = True
    with pytest.raises(ValidationError):
        successor.CurrentStateUserAttestation.model_validate(changed)


def test_append_only_writer_rejects_reuse(tmp_path: Path) -> None:
    target = Path("reports/state.json")
    successor._write_once(tmp_path, target, b"{}\n")
    with pytest.raises(successor.StateBindingSuccessorError, match="already exists"):
        successor._write_once(tmp_path, target, b"{}\n")


def test_source_has_no_observation_approval_or_attempt_entrypoint() -> None:
    forbidden = {
        "run_docker",
        "read_dotenv",
        "read_environment",
        "run_sdk",
        "record_exact_approval",
        "run_attempt",
        "resume_attempt",
    }
    assert forbidden.isdisjoint(vars(successor))
    assert not (REPOSITORY / successor.USER_ATTESTATION_PATH).exists()
    assert not (REPOSITORY / successor.STATE_EVIDENCE_PATH).exists()


def test_checked_in_source_qualification_when_present() -> None:
    path = REPOSITORY / successor.QUALIFICATION_PATH
    if not path.exists():
        pytest.skip("qualification is created only after the source commit")
    summary = successor.validate_source_qualification(repository=REPOSITORY)
    assert summary["user_attestation_created"] is False
    assert summary["state_change_evidence_created"] is False
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["execution_authorized"] is False


def test_checked_in_state_when_present() -> None:
    path = REPOSITORY / successor.STATE_EVIDENCE_PATH
    if not path.exists():
        pytest.skip("fresh exact post-qualification attestation is still required")
    summary = successor.validate_current_state(repository=REPOSITORY)
    assert summary["docker_daemon_ready_verified"] is False
    assert summary["dotenv_file_or_membership_verified"] is False
    assert summary["external_observations_made"] == 0
    assert summary["execution_authorized"] is False
