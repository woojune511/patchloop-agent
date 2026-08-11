from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals import manual_docker_start_state_successor as successor

REPOSITORY = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 12, 1, 0, tzinfo=UTC)
SHA_A = "sha256:" + "a" * 64


def _file(path: Path) -> successor.CommittedFileBinding:
    return successor.CommittedFileBinding(
        path=path.as_posix(),
        blob_oid="a" * 40,
        file_bytes=1,
        file_sha256=SHA_A,
    )


def _qualification(
    contract: successor.ManualDockerStartStateContract,
) -> successor.ManualDockerStartSourceQualification:
    files = tuple(_file(path) for path in successor.SOURCE_FILES)
    body = {
        "schema_version": successor.QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": successor.QUALIFICATION_ID,
        "status": successor.QUALIFICATION_STATUS,
        "recorded_at": NOW,
        "source_commit": successor.SourceCommitBinding(
            commit="b" * 40,
            tree="c" * 40,
            parents=(successor.PREDECESSOR_EVIDENCE_COMMIT,),
            added_paths=successor.SOURCE_ADDED_PATHS,
        ).model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "contract_file": files[successor.SOURCE_FILES.index(successor.CONTRACT_PATH)].model_dump(
            mode="json"
        ),
        "predecessor_terminal_id": contract.predecessor.terminal_id,
        "predecessor_terminal_content_hash": contract.predecessor.terminal_content_hash,
        "authority": successor.QualificationAuthority().model_dump(mode="json"),
        "next_gate": "manual-start-attestation-state-binding",
    }
    return successor.ManualDockerStartSourceQualification(
        **body,
        content_hash=successor._hash_body(body),
    )


def test_contract_binds_consumed_v3_and_closes_all_live_authority() -> None:
    contract = successor.load_contract(repository=REPOSITORY)

    assert contract.predecessor.evidence_commit == successor.PREDECESSOR_EVIDENCE_COMMIT
    assert contract.predecessor.terminal_outcome == "blocked"
    assert contract.predecessor.terminal_reason == "docker_not_ready"
    assert contract.predecessor.docker_cli_command_count == 8
    assert contract.predecessor.dotenv_file_read_count == 0
    assert contract.predecessor.sdk_child_start_count == 0
    assert contract.predecessor.retry_or_resume_allowed is False
    assert contract.executable_runtime_implemented is False
    assert contract.next_gate == successor.NEXT_GATE
    authority = contract.authority.model_dump(mode="json")
    assert authority["contract_materialization_authorized"] is True
    assert authority["source_qualification_authorized"] is True
    assert authority["manual_user_attestation_binding_authorized"] is True
    assert authority["state_evidence_binding_authorized"] is True
    assert all(
        value is False
        for key, value in authority.items()
        if key
        not in {
            "contract_materialization_authorized",
            "source_qualification_authorized",
            "manual_user_attestation_binding_authorized",
            "state_evidence_binding_authorized",
        }
    )


def test_manual_start_attestation_and_state_do_not_claim_readiness() -> None:
    contract = successor.load_contract(repository=REPOSITORY)
    qualification = _qualification(contract)
    attestation = successor.build_user_attestation(
        contract,
        qualification,
        claim=successor.MANUAL_START_CLAIM,
        recorded_at=NOW,
    )
    state = successor.bind_state_evidence(
        contract,
        qualification,
        attestation,
        recorded_at=NOW,
    )

    assert attestation.manual_start_reported is True
    assert attestation.daemon_ready_claimed is False
    assert attestation.exact_images_present_claimed is False
    assert attestation.container_inventory_safe_claimed is False
    assert attestation.v3_retry_or_resume_authorized is False
    assert attestation.patchloop_docker_cli_call_count == 0
    assert attestation.patchloop_dotenv_read_or_stat_count == 0
    assert state.relevant_external_state_change_reported is True
    assert state.independent_verification_completed is False
    assert state.daemon_ready_verified is False
    assert state.executable_runtime_implemented is False
    assert state.exact_approval_allowed_for_this_structural_source is False
    assert state.patchloop_external_observation_count == 0
    assert state.patchloop_mutation_count == 0


def test_claim_contract_and_chronology_tamper_fail() -> None:
    contract = successor.load_contract(repository=REPOSITORY)
    qualification = _qualification(contract)
    with pytest.raises(successor.ManualDockerStartStateError, match="claim differs"):
        successor.build_user_attestation(
            contract,
            qualification,
            claim="docker-ready",
            recorded_at=NOW,
        )
    attestation = successor.build_user_attestation(
        contract,
        qualification,
        claim=successor.MANUAL_START_CLAIM,
        recorded_at=NOW,
    )
    changed = attestation.model_dump(mode="json")
    changed["daemon_ready_claimed"] = True
    with pytest.raises(ValidationError):
        successor.ManualDockerStartUserAttestation.model_validate(changed)
    with pytest.raises(successor.ManualDockerStartStateError, match="state predates"):
        successor.bind_state_evidence(
            contract,
            qualification,
            attestation,
            recorded_at=datetime(2026, 8, 12, 0, 59, tzinfo=UTC),
        )


def test_hash_tamper_extra_fields_and_non_utc_time_fail() -> None:
    contract = successor.load_contract(repository=REPOSITORY)
    payload = contract.model_dump(mode="json")
    payload["content_hash"] = SHA_A
    with pytest.raises(ValidationError):
        successor.ManualDockerStartStateContract.model_validate(payload)
    payload = contract.model_dump(mode="json")
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        successor.ManualDockerStartStateContract.model_validate(payload)
    qualification = _qualification(contract)
    with pytest.raises(successor.ManualDockerStartStateError, match="timezone-aware"):
        successor.build_user_attestation(
            contract,
            qualification,
            claim=successor.MANUAL_START_CLAIM,
            recorded_at=datetime(2026, 8, 12, 1, 0),
        )


def test_append_only_writer_rejects_reuse(tmp_path: Path) -> None:
    target = Path("reports/state.json")
    successor._write_once(tmp_path, target, b"{}\n")
    with pytest.raises(successor.ManualDockerStartStateError, match="already exists"):
        successor._write_once(tmp_path, target, b"{}\n")


def test_module_exposes_no_live_observation_or_execution_entrypoint() -> None:
    forbidden = {
        "run_docker",
        "start_docker",
        "pull_images",
        "run_sdk",
        "read_dotenv",
        "record_exact_approval",
        "run_attempt",
    }
    assert forbidden.isdisjoint(vars(successor))


def test_checked_in_source_qualification_when_present() -> None:
    path = REPOSITORY / successor.QUALIFICATION_PATH
    if not path.exists():
        pytest.skip("qualification is created only after the source commit")
    summary = successor.validate_source_qualification(repository=REPOSITORY)
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["execution_authorized"] is False


def test_checked_in_manual_state_when_present() -> None:
    path = REPOSITORY / successor.STATE_EVIDENCE_PATH
    if not path.exists():
        pytest.skip("state is created only after source qualification")
    summary = successor.validate_manual_start_state(repository=REPOSITORY)
    assert summary["daemon_ready_verified"] is False
    assert summary["exact_images_present_verified"] is False
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["execution_authorized"] is False
