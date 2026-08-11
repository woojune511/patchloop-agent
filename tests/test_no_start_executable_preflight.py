from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.evals import executable_no_call_preflight as v3
from patchloop.evals import no_start_executable_preflight as preflight

REPOSITORY = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 8, 12, 2, 0, tzinfo=UTC)
SHA_A = "sha256:" + "a" * 64


def _checked_in_contract() -> preflight.NoStartExecutableContract:
    return preflight.NoStartExecutableContract.model_validate_json(
        (REPOSITORY / preflight.CONTRACT_PATH).read_bytes()
    )


def _checked_in_state() -> preflight.v4.ManualDockerStartStateEvidence:
    return preflight.v4.ManualDockerStartStateEvidence.model_validate_json(
        (REPOSITORY / preflight.v4.STATE_EVIDENCE_PATH).read_bytes()
    )


@contextmanager
def _temporary_repository() -> Any:
    with TemporaryDirectory(prefix="patchloop-v5-", dir=REPOSITORY) as selected:
        yield Path(selected)


def _qualification(
    contract: preflight.NoStartExecutableContract,
) -> preflight.SourceQualification:
    files = tuple(
        preflight.CommittedFileBinding(
            path=path.as_posix(),
            blob_oid="b" * 40,
            file_bytes=1,
            file_sha256=SHA_A,
        )
        for path in preflight.SOURCE_FILES
    )
    by_path = {item.path: item for item in files}
    body = {
        "schema_version": preflight.QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": preflight.QUALIFICATION_ID,
        "status": preflight.QUALIFICATION_STATUS,
        "recorded_at": T0,
        "source_commit": preflight.SourceCommitBinding(
            commit="c" * 40,
            tree="d" * 40,
            parents=(preflight.PREDECESSOR_STATE_COMMIT,),
            added_paths=preflight.SOURCE_ADDED_PATHS,
        ).model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "contract_file": by_path[preflight.CONTRACT_PATH.as_posix()].model_dump(mode="json"),
        "runtime_file": by_path[preflight.RUNTIME_PATH.as_posix()].model_dump(mode="json"),
        "child_file": by_path[preflight.CHILD_PATH.as_posix()].model_dump(mode="json"),
        "d137_observer_file": by_path[preflight.D137_PATH.as_posix()].model_dump(mode="json"),
        "predecessor_state_file": by_path[preflight.v4.STATE_EVIDENCE_PATH.as_posix()].model_dump(
            mode="json"
        ),
        "authority": preflight.QualificationAuthority().model_dump(mode="json"),
        "next_gate": preflight.NEXT_GATE,
    }
    return preflight.SourceQualification(
        **body,
        content_hash=preflight._semantic_hash(body),
    )


def _approval_chain() -> tuple[
    preflight.NoStartExecutableContract,
    preflight.SourceQualification,
    preflight.v4.ManualDockerStartStateEvidence,
    preflight.ApprovalReceipt,
    preflight.ApprovalBinding,
]:
    contract = _checked_in_contract()
    qualification = _qualification(contract)
    state = _checked_in_state()
    receipt = preflight.build_approval_receipt(
        contract,
        qualification,
        state,
        recorded_at=T0 + timedelta(seconds=1),
    )
    approval = preflight.bind_approval(
        contract,
        qualification,
        state,
        receipt,
        recorded_at=T0 + timedelta(seconds=1),
    )
    return contract, qualification, state, receipt, approval


def _attempt_chain() -> tuple[
    preflight.AttemptIntent,
    preflight.ActionStarted,
]:
    contract, qualification, state, _receipt, approval = _approval_chain()
    attempt = preflight._build_attempt(
        contract,
        qualification,
        state,
        approval,
        ledger_snapshot_hash=preflight._empty_ledger_hash(),
        created_at=T0 + timedelta(seconds=2),
    )
    action = preflight._build_action(
        attempt,
        recorded_at=T0 + timedelta(seconds=3),
    )
    return attempt, action


def _v3_docker_blocked_observation() -> dict[str, Any]:
    terminal = json.loads((REPOSITORY / v3.TERMINAL_PATH).read_text(encoding="utf-8"))
    observation = terminal["docker_observation"]
    assert isinstance(observation, dict) and observation["passed"] is False
    return observation


def test_contract_binds_v4_state_and_forbids_start_pull_container_and_network() -> None:
    summary = preflight.materialize_contract(repository=REPOSITORY)
    contract = _checked_in_contract()

    assert summary["external_observations_made"] == 0
    assert summary["execution_authorized"] is False
    assert contract.predecessor.state_commit == preflight.PREDECESSOR_STATE_COMMIT
    assert contract.predecessor.manual_start_reported is True
    assert contract.predecessor.daemon_ready_verified is False
    assert contract.runtime_profile.runtime_implemented is True
    assert contract.runtime_profile.docker_expected_command_count == 8
    assert contract.runtime_profile.docker_desktop_or_daemon_start_limit == 0
    assert contract.runtime_profile.docker_image_pull_load_or_store_mutation_limit == 0
    assert contract.runtime_profile.container_create_start_run_exec_limit == 0
    assert contract.runtime_profile.network_call_limit == 0
    assert contract.current_manual_start_and_dotenv_reconfirmation_required is True
    assert contract.source_authority.external_preflight_attempt_authorized is False


def test_approval_binds_exact_source_state_and_two_current_reconfirmations() -> None:
    contract, qualification, state, receipt, approval = _approval_chain()

    assert receipt.contract_id == contract.contract_id
    assert receipt.source_qualification_content_hash == qualification.content_hash
    assert receipt.state_change_evidence_id == state.evidence_id
    assert receipt.current_manual_docker_start_state_reconfirmed is True
    assert receipt.current_dotenv_placement_reconfirmed is True
    assert receipt.approved_scopes == preflight.APPROVED_SCOPES
    assert approval.receipt_id == receipt.receipt_id
    assert approval.attempt_limit == 1
    assert approval.docker_desktop_or_daemon_start_authorized is False
    assert approval.image_pull_load_or_store_mutation_authorized is False
    assert approval.container_operation_authorized is False
    assert approval.network_or_transport_authorized is False

    changed = approval.model_dump(mode="json")
    changed["approved_scopes"] = changed["approved_scopes"][:-1]
    with pytest.raises(ValidationError):
        preflight.ApprovalBinding.model_validate(changed)


def test_docker_blocked_terminal_is_consumed_and_accounts_exact_no_start_activity() -> None:
    attempt, action = _attempt_chain()
    terminal = preflight._build_terminal(
        attempt,
        action,
        outcome=v3.TerminalOutcome.BLOCKED,
        reason=v3.TerminalReason.DOCKER_NOT_READY,
        docker_observation=_v3_docker_blocked_observation(),
        sdk_observation=None,
        activity_accounting_complete=True,
        recorded_at=T0 + timedelta(seconds=4),
    )

    assert terminal.docker_cli_command_count == 8
    assert terminal.dotenv_file_read_count == 0
    assert terminal.sdk_child_start_count == 0
    assert terminal.docker_desktop_or_daemon_start_count == 0
    assert terminal.image_pull_load_or_store_mutation_count == 0
    assert terminal.container_operation_count == 0
    assert terminal.network_call_count == 0
    assert terminal.provider_evaluator_agent_call_count == 0


def test_terminal_rejects_fabricated_sdk_block_and_activity_projection() -> None:
    attempt, action = _attempt_chain()
    body = preflight._build_terminal(
        attempt,
        action,
        outcome=v3.TerminalOutcome.BLOCKED,
        reason=v3.TerminalReason.DOCKER_NOT_READY,
        docker_observation=_v3_docker_blocked_observation(),
        sdk_observation=None,
        activity_accounting_complete=True,
        recorded_at=T0 + timedelta(seconds=4),
    ).model_dump(mode="json")
    body["reason"] = v3.TerminalReason.DOTENV_CREDENTIAL_MISSING
    body["content_hash"] = preflight.sha256_json(
        {key: value for key, value in body.items() if key not in {"terminal_id", "content_hash"}}
    )
    body["terminal_id"] = preflight._derived_id("ncpterminal", body["content_hash"])
    with pytest.raises(ValidationError, match="SDK-blocked"):
        preflight.TerminalTransition.model_validate(body)

    body["reason"] = v3.TerminalReason.DOCKER_NOT_READY
    body["docker_cli_command_count"] = 7
    body["content_hash"] = preflight.sha256_json(
        {key: value for key, value in body.items() if key not in {"terminal_id", "content_hash"}}
    )
    body["terminal_id"] = preflight._derived_id("ncpterminal", body["content_hash"])
    with pytest.raises(ValidationError):
        preflight.TerminalTransition.model_validate(body)


def test_error_terminal_preserves_unknown_post_marker_activity() -> None:
    attempt, action = _attempt_chain()
    terminal = preflight._build_terminal(
        attempt,
        action,
        outcome=v3.TerminalOutcome.ERROR,
        reason=v3.TerminalReason.CHECKER_ERROR,
        docker_observation=None,
        sdk_observation=None,
        activity_accounting_complete=False,
        recorded_at=T0 + timedelta(seconds=4),
    )

    assert terminal.activity_accounting_complete is False
    assert terminal.unknown_post_marker_activity_possible is True
    assert terminal.docker_cli_command_count is None
    assert terminal.dotenv_file_read_count is None
    assert terminal.sdk_child_start_count is None


def test_append_only_writer_rejects_reuse() -> None:
    with _temporary_repository() as root:
        target = Path("reports/v5.json")
        preflight._write_once(root, target, b"{}\n")
        with pytest.raises(preflight.NoStartExecutablePreflightError, match="already exists"):
            preflight._write_once(root, target, b"{}\n")


def test_current_checkout_refuses_attempt_before_exact_approval() -> None:
    if not (REPOSITORY / preflight.QUALIFICATION_PATH).exists():
        pytest.skip("source qualification is created only after the source commit")
    if (REPOSITORY / preflight.APPROVAL_BINDING_PATH).exists():
        pytest.skip("approval has advanced the immutable evidence chain")
    calls = {"docker": 0, "sdk": 0}

    def docker(**_kwargs: Any) -> dict[str, Any]:
        calls["docker"] += 1
        raise AssertionError("Docker observation crossed approval boundary")

    def sdk(*_args: Any, **_kwargs: Any) -> Any:
        calls["sdk"] += 1
        raise AssertionError("SDK observation crossed approval boundary")

    with pytest.raises((preflight.NoStartExecutablePreflightError, FileNotFoundError)):
        preflight.run_once(
            repository=REPOSITORY,
            docker_observer=docker,
            sdk_observer=sdk,
        )
    assert calls == {"docker": 0, "sdk": 0}
    assert not (REPOSITORY / preflight.ATTEMPT_PATH).exists()
    assert not (REPOSITORY / preflight.ACTION_STARTED_PATH).exists()
    assert not (REPOSITORY / preflight.TERMINAL_PATH).exists()


def test_approval_recorder_requires_both_current_reconfirmations() -> None:
    if not (REPOSITORY / preflight.QUALIFICATION_PATH).exists():
        pytest.skip("source qualification is created only after the source commit")
    if (REPOSITORY / preflight.APPROVAL_BINDING_PATH).exists():
        pytest.skip("approval has advanced the immutable evidence chain")
    contract = preflight.load_contract(repository=REPOSITORY)
    qualification = preflight._load_qualification(REPOSITORY)
    state = preflight._load_v4_state(REPOSITORY)

    with pytest.raises(preflight.NoStartExecutablePreflightError, match="manual start"):
        preflight.record_exact_approval(
            exact_contract_id=contract.contract_id,
            exact_source_qualification_hash=qualification.content_hash,
            exact_state_change_evidence_id=state.evidence_id,
            reconfirm_current_manual_start=False,
            reconfirm_current_dotenv_placement=True,
            recorded_at=T0,
            repository=REPOSITORY,
        )
    with pytest.raises(preflight.NoStartExecutablePreflightError, match="dotenv placement"):
        preflight.record_exact_approval(
            exact_contract_id=contract.contract_id,
            exact_source_qualification_hash=qualification.content_hash,
            exact_state_change_evidence_id=state.evidence_id,
            reconfirm_current_manual_start=True,
            reconfirm_current_dotenv_placement=False,
            recorded_at=T0,
            repository=REPOSITORY,
        )


def test_checked_in_source_qualification_when_present() -> None:
    if not (REPOSITORY / preflight.QUALIFICATION_PATH).exists():
        pytest.skip("qualification is created only after the source commit")
    summary = preflight.validate_source_qualification(repository=REPOSITORY)
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["execution_authorized"] is False
