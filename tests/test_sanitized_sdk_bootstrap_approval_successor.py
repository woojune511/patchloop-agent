from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals import sanitized_sdk_bootstrap_approval_successor as successor

REPOSITORY = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 12, 16, 0, tzinfo=UTC)
SHA_A = "sha256:" + "a" * 64


@pytest.fixture(scope="module")
def contract() -> successor.ApprovalSuccessorContract:
    return successor.load_contract(repository=REPOSITORY)


@pytest.fixture(autouse=True)
def cached_contract_validation(
    monkeypatch: pytest.MonkeyPatch,
    contract: successor.ApprovalSuccessorContract,
) -> None:
    monkeypatch.setattr(successor, "load_contract", lambda **_kwargs: contract)


def _file(path: Path) -> successor.v10.CommittedFileBinding:
    return successor.v10.CommittedFileBinding(
        path=path.as_posix(),
        blob_oid="a" * 40,
        file_bytes=1,
        file_sha256=SHA_A,
    )


def _qualification(
    contract: successor.ApprovalSuccessorContract,
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
        "predecessor_contract_file": by_path[successor.v10.CONTRACT_PATH.as_posix()].model_dump(
            mode="json"
        ),
        "predecessor_qualification_file": by_path[
            successor.v10.QUALIFICATION_PATH.as_posix()
        ].model_dump(mode="json"),
        "predecessor_attestation_file": by_path[
            successor.v10.USER_ATTESTATION_PATH.as_posix()
        ].model_dump(mode="json"),
        "predecessor_state_file": by_path[successor.v10.STATE_EVIDENCE_PATH.as_posix()].model_dump(
            mode="json"
        ),
        "predecessor_state_evidence_id": contract.predecessor.state_change_evidence_id,
        "predecessor_state_evidence_content_hash": (
            contract.predecessor.state_change_evidence_content_hash
        ),
        "authority": successor.QualificationAuthority().model_dump(mode="json"),
        "next_gate": successor.QUALIFICATION_NEXT_GATE,
    }
    return successor.SourceQualification(
        **body,
        content_hash=successor.v10._hash_body(body),
    )


def test_contract_binds_exact_v10_state_and_v9_runtime(
    contract: successor.ApprovalSuccessorContract,
) -> None:
    assert contract.predecessor.source_commit == successor.V10_SOURCE_COMMIT
    assert contract.predecessor.state_evidence_commit == successor.V10_STATE_EVIDENCE_COMMIT
    assert contract.predecessor.state_change_evidence_id == (
        "ncpstate_cf5f91ae06c6c49dc988ec217a535301b5162208ed227186cb76b15be572abe5"
    )
    assert contract.predecessor.independent_verification_completed is False
    assert contract.predecessor.state_change_evidence_reusable is False
    assert contract.approved_runtime.entrypoint == successor.APPROVED_RUNTIME
    assert contract.approved_runtime.approved_scopes == successor.APPROVED_SCOPES
    assert contract.approved_runtime.docker_expected_command_count == 8
    assert contract.approved_runtime.network_call_limit == 0
    assert contract.approval_rule.attempt_limit == 1
    assert contract.approval_rule.approval_reusable is False
    assert contract.approval_rule.state_reusable is False
    assert contract.approval_materializer_implemented is True
    assert contract.attempt_entrypoint_implemented is False


def test_source_authority_is_offline_and_attempt_closed(
    contract: successor.ApprovalSuccessorContract,
) -> None:
    authority = contract.authority.model_dump(mode="json")
    assert authority["contract_materialization_authorized"] is True
    assert authority["source_qualification_authorized"] is True
    assert authority["future_exact_approval_binding_supported"] is True
    assert all(
        value is False
        for key, value in authority.items()
        if key
        not in {
            "contract_materialization_authorized",
            "source_qualification_authorized",
            "future_exact_approval_binding_supported",
        }
    )


def test_exact_statement_builds_nonexecuting_one_use_approval(
    contract: successor.ApprovalSuccessorContract,
) -> None:
    qualification = _qualification(contract)
    statement = successor.expected_approval_statement(contract, qualification)
    receipt = successor.build_user_approval_receipt(
        contract,
        qualification,
        statement=statement,
        recorded_at=NOW,
    )
    approval = successor.bind_exact_approval(
        contract,
        qualification,
        receipt,
        recorded_at=NOW,
    )

    assert contract.contract_id in statement
    assert qualification.content_hash in statement
    assert contract.predecessor.state_change_evidence_id in statement
    assert contract.predecessor.state_change_evidence_content_hash in statement
    assert receipt.attempt_limit == 1
    assert receipt.approval_binding_only is True
    assert receipt.attempt_started is False
    assert receipt.approval_reusable is False
    assert receipt.network_or_transport_authorized is False
    assert approval.approval_id.startswith("ncpapproval_")
    assert approval.attempt_entrypoint_available is False
    assert approval.attempt_started is False
    assert approval.attempt_consumed is False
    assert approval.next_gate == successor.APPROVAL_NEXT_GATE


@pytest.mark.parametrize(
    "statement",
    (
        "진행해줘",
        "approve work item 4",
        "Docker is running; approve one attempt",
    ),
)
def test_generic_or_stale_approval_statement_fails(
    statement: str,
    contract: successor.ApprovalSuccessorContract,
) -> None:
    qualification = _qualification(contract)
    with pytest.raises(successor.ApprovalSuccessorError, match="statement differs"):
        successor.build_user_approval_receipt(
            contract,
            qualification,
            statement=statement,
            recorded_at=NOW,
        )


def test_approval_must_follow_qualification_and_binding_must_follow_receipt(
    contract: successor.ApprovalSuccessorContract,
) -> None:
    qualification = _qualification(contract)
    statement = successor.expected_approval_statement(contract, qualification)
    with pytest.raises(successor.ApprovalSuccessorError, match="predates qualification"):
        successor.build_user_approval_receipt(
            contract,
            qualification,
            statement=statement,
            recorded_at=NOW - timedelta(seconds=1),
        )
    receipt = successor.build_user_approval_receipt(
        contract,
        qualification,
        statement=statement,
        recorded_at=NOW,
    )
    with pytest.raises(successor.ApprovalSuccessorError, match="predates receipt"):
        successor.bind_exact_approval(
            contract,
            qualification,
            receipt,
            recorded_at=NOW - timedelta(seconds=1),
        )


def test_hash_scope_state_and_extra_field_tamper_fail(
    contract: successor.ApprovalSuccessorContract,
) -> None:
    payload = contract.model_dump(mode="json")
    payload["content_hash"] = SHA_A
    with pytest.raises(ValidationError):
        successor.ApprovalSuccessorContract.model_validate(payload)
    payload = contract.model_dump(mode="json")
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        successor.ApprovalSuccessorContract.model_validate(payload)

    qualification = _qualification(contract)
    receipt = successor.build_user_approval_receipt(
        contract,
        qualification,
        statement=successor.expected_approval_statement(contract, qualification),
        recorded_at=NOW,
    )
    changed = receipt.model_dump(mode="json")
    changed["attempt_limit"] = 2
    with pytest.raises(ValidationError):
        successor.UserExactApprovalReceipt.model_validate(changed)
    changed = receipt.model_dump(mode="json")
    changed["state_change_evidence_id"] = "ncpstate_" + "0" * 64
    changed["content_hash"] = successor.v10._hash_body(
        {key: value for key, value in changed.items() if key not in {"receipt_id", "content_hash"}}
    )
    changed["receipt_id"] = successor.v10._derived_id("ncpapprovalreceipt", changed["content_hash"])
    forged = successor.UserExactApprovalReceipt.model_validate(changed)
    with pytest.raises(successor.ApprovalSuccessorError, match="exact state"):
        successor.bind_exact_approval(
            contract,
            qualification,
            forged,
            recorded_at=NOW,
        )


def test_append_only_writer_rejects_reuse(tmp_path: Path) -> None:
    target = Path("reports/approval.json")
    successor.v10._write_once(tmp_path, target, b"{}\n")
    with pytest.raises(successor.v10.StateBindingSuccessorError, match="already exists"):
        successor.v10._write_once(tmp_path, target, b"{}\n")


def test_module_exposes_no_observation_or_attempt_executor() -> None:
    forbidden = {
        "run_parent_preflight",
        "run_docker",
        "read_dotenv",
        "run_sdk",
        "create_attempt",
        "run_attempt",
        "resume_attempt",
        "record_terminal",
    }
    assert forbidden.isdisjoint(vars(successor))


def test_checked_in_source_qualification_when_present() -> None:
    path = REPOSITORY / successor.QUALIFICATION_PATH
    if not path.exists():
        pytest.skip("qualification is created only after the source commit")
    summary = successor.validate_source_qualification(repository=REPOSITORY)
    assert summary["approval_created"] is False
    assert summary["attempt_created"] is False
    assert summary["external_observations_made"] == 0
    assert summary["execution_authorized"] is False


def test_checked_in_approval_when_present() -> None:
    path = REPOSITORY / successor.APPROVAL_BINDING_PATH
    if not path.exists():
        pytest.skip("fresh exact post-qualification approval is still required")
    summary = successor.validate_exact_approval(repository=REPOSITORY)
    assert summary["attempt_limit"] == 1
    assert summary["attempt_started"] is False
    assert summary["attempt_entrypoint_available"] is False
    assert summary["external_observations_made"] == 0
