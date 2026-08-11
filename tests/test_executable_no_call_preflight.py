from __future__ import annotations

import importlib.util
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.evals import executable_no_call_preflight as preflight
from patchloop.evals import user_attested_no_call_preflight as v2

REPOSITORY = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 8, 12, 1, 0, tzinfo=UTC)


def _child_module() -> ModuleType:
    path = REPOSITORY / preflight.CHILD_PATH
    spec = importlib.util.spec_from_file_location("patchloop_test_dotenv_child", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _contract() -> preflight.ExecutableNoCallPreflightContract:
    return preflight.load_executable_no_call_preflight_contract(repository=REPOSITORY)


def _v2_chain() -> tuple[
    v2.UserCredentialLocationAttestation,
    v2.UserAttestedStateChangeEvidence,
]:
    attestation = v2.UserCredentialLocationAttestation.model_validate_json(
        (REPOSITORY / v2.USER_ATTESTATION_PATH).read_bytes()
    )
    state = v2.UserAttestedStateChangeEvidence.model_validate_json(
        (REPOSITORY / v2.STATE_EVIDENCE_PATH).read_bytes()
    )
    return attestation, state


def _qualification_stub(
    contract: preflight.ExecutableNoCallPreflightContract,
) -> preflight.ExecutableSourceQualification:
    source_commit = preflight.SourceCommitBinding(
        commit="1" * 40,
        tree="2" * 40,
        parents=(preflight.PREDECESSOR_STATE_COMMIT,),
        added_paths=preflight.SOURCE_ADDED_PATHS,
    )
    files = tuple(
        preflight.CommittedFileBinding(
            path=path.as_posix(),
            blob_oid="3" * 40,
            file_bytes=1,
            file_sha256="sha256:" + "4" * 64,
        )
        for path in preflight.SOURCE_FILES
    )
    by_path = {item.path: item for item in files}
    body = {
        "schema_version": preflight.QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": preflight.QUALIFICATION_ID,
        "status": preflight.QUALIFICATION_STATUS,
        "recorded_at": T0,
        "source_commit": source_commit.model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "contract_file": by_path[preflight.CONTRACT_PATH.as_posix()].model_dump(mode="json"),
        "runtime_file": by_path[preflight.RUNTIME_PATH.as_posix()].model_dump(mode="json"),
        "child_file": by_path[preflight.CHILD_PATH.as_posix()].model_dump(mode="json"),
        "authority": preflight.ExecutableQualificationAuthority().model_dump(mode="json"),
        "next_gate": "fresh-state-binding-then-exact-user-approval",
    }
    return preflight.ExecutableSourceQualification(
        **body,
        content_hash=preflight._semantic_hash(body),
    )


def _state(
    contract: preflight.ExecutableNoCallPreflightContract,
    qualification: preflight.ExecutableSourceQualification,
) -> preflight.ExecutableStateChangeEvidence:
    attestation, predecessor = _v2_chain()
    return preflight.bind_executable_state_change_evidence(
        contract,
        qualification,
        attestation,
        predecessor,
        recorded_at=T0 + timedelta(seconds=1),
    )


def test_child_parser_returns_only_membership_and_never_value(tmp_path: Path) -> None:
    child = _child_module()
    secret = "test-value-must-never-return"
    dotenv = tmp_path / ".env"
    dotenv.write_text(f"IGNORED=x\nOPENAI_API_KEY='{secret}'\n", encoding="utf-8")

    result, reads = child._dotenv_membership(dotenv)
    serialized = json.dumps(result, sort_keys=True)

    assert reads == 1
    assert result["dotenv"]["exact_subject_declared"] is True
    assert result["dotenv"]["exact_subject_nonempty"] is True
    assert result["dotenv"]["raw_value_returned"] is False
    assert result["dotenv"]["value_hash_prefix_or_length_returned"] is False
    assert result["activity"]["credential_assignment_parse_count"] == 1
    assert secret not in serialized
    assert str(len(secret)) not in serialized


def test_child_parser_fails_closed_on_missing_duplicate_and_oversize(tmp_path: Path) -> None:
    child = _child_module()
    missing, reads = child._dotenv_membership(tmp_path / ".env")
    assert reads == 0
    assert missing["dotenv"]["error_code"] == "dotenv_missing"

    dotenv = tmp_path / ".env"
    dotenv.write_text("OPENAI_API_KEY=one\nOPENAI_API_KEY=two\n", encoding="utf-8")
    duplicate, reads = child._dotenv_membership(dotenv)
    assert reads == 1
    assert duplicate["dotenv"]["duplicate_subject"] is True
    assert duplicate["dotenv"]["exact_subject_nonempty"] is False

    dotenv.write_bytes(b"x" * (child.MAX_DOTENV_BYTES + 1))
    oversized, reads = child._dotenv_membership(dotenv)
    assert reads == 0
    assert oversized["dotenv"]["error_code"] == "dotenv_size_limit"


def test_contract_materialization_is_deterministic_and_binds_runtime() -> None:
    first = preflight.materialize_executable_no_call_preflight_contract(repository=REPOSITORY)
    path = REPOSITORY / preflight.CONTRACT_PATH
    raw = path.read_bytes()
    mtime = path.stat().st_mtime_ns
    replay = preflight.materialize_executable_no_call_preflight_contract(repository=REPOSITORY)

    assert replay == first
    assert path.read_bytes() == raw
    assert path.stat().st_mtime_ns == mtime
    assert first["runtime_implemented"] is True
    assert first["external_observations_made"] == 0
    assert first["execution_authorized"] is False

    contract = _contract()
    assert contract.runtime_profile.credential_value_return_hash_prefix_or_length_limit == 0
    assert contract.runtime_profile.dotenv_entire_file_bytes_confined_to_isolated_child is True
    assert contract.runtime_profile.sdk_uses_fixed_nonsecret_placeholder is True
    assert contract.runtime_profile.network_call_limit == 0
    assert contract.source_authority.exact_approval_required is True
    assert contract.source_authority.docker_sdk_or_dotenv_observation_authorized is False


def test_state_rebind_is_still_nonproof_and_requires_current_reconfirmation() -> None:
    contract = _contract()
    qualification = _qualification_stub(contract)
    state = _state(contract, qualification)

    assert state.evidence_id == "ncpstate_" + state.content_hash.removeprefix("sha256:")
    assert (
        state.predecessor_state_change_evidence_id == contract.predecessor_state_change_evidence_id
    )
    assert state.independent_verification_completed is False
    assert state.attestation_proves_credential_presence is False
    assert state.exact_approval_must_reconfirm_current_state is True
    assert state.dotenv_read_or_stat_performed is False
    assert state.raw_credential_value_observed is False


def test_exact_approval_binds_contract_source_and_state() -> None:
    contract = _contract()
    qualification = _qualification_stub(contract)
    state = _state(contract, qualification)
    receipt = preflight.build_executable_approval_receipt(
        contract,
        qualification,
        state,
        recorded_at=T0 + timedelta(seconds=2),
    )
    approval = preflight.bind_executable_approval(
        contract,
        qualification,
        state,
        receipt,
        recorded_at=T0 + timedelta(seconds=2),
    )

    assert approval.state_change_evidence_id == state.evidence_id
    assert approval.source_qualification_content_hash == qualification.content_hash
    assert approval.approved_scopes == preflight.APPROVED_SCOPES
    assert receipt.current_dotenv_placement_reconfirmed is True
    assert receipt.network_or_transport_authorized is False
    assert receipt.execution_hash_candidate_cost_or_paid_execution_authorized is False
    assert approval.identity_assurance == preflight.IDENTITY_ASSURANCE
    assert approval.network_or_transport_authorized is False

    changed = approval.model_copy(update={"state_change_evidence_id": "ncpstate_" + "f" * 64})
    with pytest.raises(ValidationError):
        preflight.ExecutableApprovalBinding.model_validate(changed.model_dump(mode="json"))


def test_post_marker_checker_error_preserves_unknown_activity_boundary() -> None:
    contract = _contract()
    qualification = _qualification_stub(contract)
    state = _state(contract, qualification)
    receipt = preflight.build_executable_approval_receipt(
        contract,
        qualification,
        state,
        recorded_at=T0 + timedelta(seconds=2),
    )
    approval = preflight.bind_executable_approval(
        contract,
        qualification,
        state,
        receipt,
        recorded_at=T0 + timedelta(seconds=2),
    )
    attempt = preflight._build_attempt(
        contract,
        qualification,
        state,
        approval,
        ledger_snapshot_hash=preflight._empty_ledger_snapshot_hash(),
        created_at=T0 + timedelta(seconds=3),
    )
    action = preflight._build_action_started(
        attempt,
        recorded_at=T0 + timedelta(seconds=4),
    )
    terminal = preflight._build_terminal(
        attempt,
        action,
        outcome=preflight.TerminalOutcome.ERROR,
        reason=preflight.TerminalReason.CHECKER_ERROR,
        docker_observation=None,
        sdk_observation=None,
        activity_accounting_complete=False,
        recorded_at=T0 + timedelta(seconds=5),
    )

    assert terminal.activity_accounting_complete is False
    assert terminal.unknown_post_marker_activity_possible is True
    assert terminal.docker_cli_command_count is None
    assert terminal.dotenv_file_read_count is None
    assert terminal.sdk_child_start_count is None


def test_dirty_parent_environment_suppresses_child() -> None:
    contract = _contract()
    calls = 0

    def forbidden_run(*_args: Any, **_kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        raise AssertionError("child should be suppressed")

    observation = preflight.run_isolated_dotenv_sdk_observation(
        contract,
        repository=REPOSITORY,
        environment_present=lambda name: name == "PYTHONPATH",
        run=forbidden_run,
    )

    assert observation.passed is False
    assert observation.child_start_count == 0
    assert observation.parent_pythonpath_absent is False
    assert calls == 0


def test_isolated_child_invocation_inherits_no_parent_environment_or_secret() -> None:
    contract = _contract()
    captured: dict[str, Any] = {}
    payload = {
        "schema_version": preflight.CHILD_SCHEMA_VERSION,
        "dotenv": {
            "file_present": False,
            "exact_subject_declared": False,
            "exact_subject_nonempty": False,
            "duplicate_subject": False,
            "error_code": "dotenv_missing",
            "raw_value_returned": False,
            "value_hash_prefix_or_length_returned": False,
        },
        "sdk_observation": None,
        "activity": {
            "dotenv_file_read_count": 0,
            "dotenv_subject_membership_check_count": 0,
            "credential_assignment_parse_count": 0,
            "credential_value_return_count": 0,
            "credential_value_hash_prefix_or_length_count": 0,
            "network_call_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
    }

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        captured["argv"] = argv
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=(json.dumps(payload, separators=(",", ":")) + "\n").encode(),
            stderr=b"",
        )

    observation = preflight.run_isolated_dotenv_sdk_observation(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        run=fake_run,
    )

    assert observation.passed is False
    assert observation.child_start_count == 1
    assert captured["env"] == {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    assert captured["shell"] is False
    assert "-I" in captured["argv"] and "-E" in captured["argv"]
    assert all("test-value" not in str(value) for value in captured.values())


def test_child_output_schema_rejects_extra_secret_channel() -> None:
    payload = {
        "schema_version": preflight.CHILD_SCHEMA_VERSION,
        "dotenv": {
            "file_present": True,
            "exact_subject_declared": True,
            "exact_subject_nonempty": True,
            "duplicate_subject": False,
            "error_code": None,
            "raw_value_returned": False,
            "value_hash_prefix_or_length_returned": False,
            "secret": "must-not-be-accepted",
        },
        "sdk_observation": None,
        "activity": {
            "dotenv_file_read_count": 1,
            "dotenv_subject_membership_check_count": 1,
            "credential_assignment_parse_count": 1,
            "credential_value_return_count": 0,
            "credential_value_hash_prefix_or_length_count": 0,
            "network_call_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
    }
    with pytest.raises(ValidationError):
        preflight.IsolatedDotenvSDKObservation.model_validate(payload)


def test_live_entrypoint_refuses_before_exact_approval_and_makes_no_observation() -> None:
    selected = REPOSITORY / preflight.QUALIFICATION_PATH
    state = REPOSITORY / preflight.STATE_EVIDENCE_PATH
    if not selected.exists() or not state.exists():
        pytest.skip("source qualification and state are created only after the exact source commit")
    calls = {"docker": 0, "sdk": 0}

    def docker(**_kwargs: Any) -> dict[str, Any]:
        calls["docker"] += 1
        raise AssertionError("Docker observation crossed approval boundary")

    def sdk(*_args: Any, **_kwargs: Any) -> Any:
        calls["sdk"] += 1
        raise AssertionError("SDK observation crossed approval boundary")

    with pytest.raises((preflight.ExecutableNoCallPreflightError, FileNotFoundError)):
        preflight.run_executable_no_call_preflight_once(
            repository=REPOSITORY,
            docker_observer=docker,
            sdk_observer=sdk,
        )
    assert calls == {"docker": 0, "sdk": 0}


def test_source_qualification_replays_when_artifact_exists() -> None:
    selected = REPOSITORY / preflight.QUALIFICATION_PATH
    if not selected.exists():
        pytest.skip("source qualification is created only after the exact source commit")
    summary = preflight.validate_executable_source_qualification(repository=REPOSITORY)
    assert summary["external_observations_made"] == 0
    assert summary["execution_authorized"] is False
