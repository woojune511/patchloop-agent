from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from patchloop.evals import typed_diagnostic_activation_successor as successor

REPOSITORY = Path(__file__).resolve().parents[1]


def _v22_pair() -> tuple[Any, Any]:
    contract = successor.v22.EnvelopeDiagnosticActivationContract.model_validate_json(
        (REPOSITORY / successor.v22.CONTRACT_PATH).read_bytes()
    )
    qualification = successor.v22.SourceQualification.model_validate_json(
        (REPOSITORY / successor.v22.QUALIFICATION_PATH).read_bytes()
    )
    return contract, qualification


@pytest.fixture(scope="module")
def contract() -> successor.TypedDiagnosticActivationContract:
    return successor._build_contract(REPOSITORY)


@pytest.fixture(autouse=True)
def cached_sources(
    monkeypatch: pytest.MonkeyPatch,
    contract: successor.TypedDiagnosticActivationContract,
) -> None:
    predecessor = _v22_pair()
    monkeypatch.setattr(successor, "load_contract", lambda **_kwargs: contract)
    monkeypatch.setattr(successor, "_load_v22_source", lambda _root: predecessor)


def _find_docker(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        if value.get("schema_version") == "d137-d136-docker-no-call-preflight-observation-v1":
            return value
        for nested in value.values():
            try:
                return _find_docker(nested)
            except LookupError:
                pass
    elif isinstance(value, list):
        for nested in value:
            try:
                return _find_docker(nested)
            except LookupError:
                pass
    raise LookupError("Docker observation not found")


def _docker(*, passed: bool) -> dict[str, Any]:
    name = (
        "evaluator-v2-dual-pipe-activation-v20-terminal.json"
        if passed
        else "evaluator-v2-sanitized-sdk-bootstrap-framed-v13-terminal.json"
    )
    value = json.loads((REPOSITORY / "reports/live-pilot/artifacts" / name).read_text())
    docker = _find_docker(value)
    successor.v7.d137.validate_d137_docker_no_call_preflight_observation(docker)
    assert docker["passed"] is passed
    return docker


def _blocked_channel() -> successor.ChannelObservation:
    child = successor.channel._fixed_child()
    worker = successor.channel.project_worker_envelope(
        REPOSITORY,
        mode=successor.channel.Mode.LIVE,
        observed_child=child,
    )
    decoded = successor.channel.decode_worker_frame(
        successor.channel.encode_frame(worker),
        mode=successor.channel.Mode.LIVE,
    )
    outcome = successor.channel.WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=1,
        returncode=0,
        frame=decoded,
        activity_accounting_complete=True,
        unknown_process_activity_possible=False,
    )
    envelope = successor.channel.build_supervisor_envelope(
        REPOSITORY,
        mode=successor.channel.Mode.LIVE,
        observed_outcome=outcome,
    )
    return successor._channel_from_process(
        {
            "launch_attempt_count": 1,
            "process_return_count": 1,
            "returncode": 0,
            "frame_stage": "valid",
            "envelope": envelope,
            "activity_accounting_complete": True,
            "unknown_process_activity_possible": False,
        }
    )


def _blocked_observation() -> successor.PreflightObservation:
    return successor._compose_parent_observation(_docker(passed=True), _blocked_channel())


def test_contract_binds_v22_and_keeps_source_qualification_closed(
    contract: successor.TypedDiagnosticActivationContract,
) -> None:
    assert contract.predecessor.source_commit == successor.V22_SOURCE_COMMIT
    assert contract.predecessor.source_tree == successor.V22_SOURCE_TREE
    assert contract.predecessor.qualification_commit == successor.V22_QUALIFICATION_COMMIT
    assert contract.predecessor.source_qualification_hash == successor.V22_QUALIFICATION_HASH
    assert contract.predecessor.state_approval_attempt_or_terminal_count == 0
    assert contract.runtime.approved_scopes == successor.APPROVED_SCOPES
    assert contract.runtime.default_observer_reachable_only_after_action_started is True
    assert contract.runtime.standalone_observation_cli_exposed is False
    assert contract.runtime.parent_to_supervisor_launch_limit == 1
    assert contract.runtime.supervisor_to_worker_launch_limit == 1
    assert contract.lifecycle.v22_source_or_qualification_mutation_allowed is False
    assert contract.state_approval_and_attempt_entrypoints_implemented is True
    assert contract.execution_currently_authorized is False
    assert contract.next_gate == "fresh-exact-v23-state-statement"


def test_internal_live_script_has_only_stdlib_top_level_imports() -> None:
    source = (REPOSITORY / successor.LIVE_CHANNEL_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    imported = {alias.name.split(".", 1)[0] for node in imports for alias in node.names}
    assert not imported.intersection({"patchloop", "openai", "httpx", "dotenv"})
    assert 'role.add_argument("--worker"' in source
    assert 'role.add_argument("--supervisor"' in source
    assert "run_live_supervisor_process" in source


def test_forged_contract_suppresses_docker(
    contract: successor.TypedDiagnosticActivationContract,
) -> None:
    forged = contract.model_copy(update={"content_hash": "sha256:" + "0" * 64})
    result = successor._run_parent_preflight(
        forged,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: pytest.fail("Docker must not run"),
    )
    assert result.state == "error"
    assert result.reason == "contract_binding_error"
    assert result.channel_observation is None
    assert result.activity_accounting_complete is False
    assert result.unknown_post_marker_activity_possible is True


def test_docker_block_suppresses_typed_channel(
    contract: successor.TypedDiagnosticActivationContract,
) -> None:
    result = successor._run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _docker(passed=False),
        channel_observer=lambda *_args, **_kwargs: pytest.fail("channel must not run"),
    )
    assert result.state == "blocked"
    assert result.reason == "docker_not_ready"
    assert result.parent_to_supervisor_launch_attempt_count == 0
    assert result.supervisor_to_worker_launch_attempt_count == 0
    assert result.activity_accounting_complete is True


def test_typed_channel_maps_strict_blocked_child_without_raw_data(
    contract: successor.TypedDiagnosticActivationContract,
) -> None:
    channel_observation = _blocked_channel()
    result = successor._run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _docker(passed=True),
        channel_observer=lambda *_args, **_kwargs: channel_observation,
    )
    assert result.state == "blocked"
    assert result.reason == "dotenv_not_ready"
    assert result.parent_to_supervisor_launch_attempt_count == 1
    assert result.supervisor_to_worker_launch_attempt_count == 1
    assert result.network_call_count == 0
    assert result.provider_evaluator_agent_call_count == 0
    assert result.activity_accounting_complete is True
    rendered = json.dumps(result.model_dump(mode="json"), sort_keys=True)
    assert "OPENAI_API_KEY=" not in rendered
    assert "sk-" not in rendered.lower()


def test_invalid_outer_frame_preserves_unknown_accounting() -> None:
    value = successor._channel_from_process(
        {
            "launch_attempt_count": 1,
            "process_return_count": 1,
            "returncode": 0,
            "frame_stage": "digest_invalid",
            "envelope": None,
            "activity_accounting_complete": False,
            "unknown_process_activity_possible": True,
        }
    )
    assert value.code == "supervisor_frame_invalid"
    assert value.activity_accounting_complete is False
    assert value.unknown_process_activity_possible is True


def test_live_process_launcher_uses_fixed_null_stdio_and_one_result_channel() -> None:
    captured: dict[str, Any] = {}

    class FakeProcess:
        def wait(self, *, timeout: int) -> int:
            assert timeout == successor.live_channel.PROCESS_TIMEOUT_SECONDS
            return 1

        def kill(self) -> None:
            pytest.fail("non-timeout fake process must not be killed")

    def fake_popen(argv: list[str], **kwargs: Any) -> FakeProcess:
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return FakeProcess()

    result = successor.live_channel.run_live_supervisor_process(
        REPOSITORY,
        popen=fake_popen,
    )
    argv = captured["argv"]
    kwargs = captured["kwargs"]
    assert "--supervisor" in argv
    assert kwargs["shell"] is False
    assert kwargs["close_fds"] is True
    assert kwargs["stdin"] is not None
    assert kwargs["stdout"] is not None
    assert kwargs["stderr"] is not None
    assert "OPENAI_API_KEY" not in kwargs["env"]
    assert "PYTHONHOME" not in kwargs["env"]
    assert "PYTHONPATH" not in kwargs["env"]
    assert all("proxy" not in key.lower() for key in kwargs["env"])
    if "pass_fds" in kwargs:
        assert len(kwargs["pass_fds"]) == 1
    else:
        assert len(kwargs["startupinfo"].lpAttributeList["handle_list"]) == 1
    assert result["process_return_count"] == 1
    assert result["returncode"] == 1
    assert result["envelope"] is None
    assert result["activity_accounting_complete"] is False
    assert result["unknown_process_activity_possible"] is True


def test_exact_state_approval_and_run_statements_are_distinct(
    contract: successor.TypedDiagnosticActivationContract,
) -> None:
    now = datetime.now(UTC)
    qualification = SimpleNamespace(
        contract_id=contract.contract_id,
        content_hash="sha256:" + "1" * 64,
        recorded_at=now,
    )
    state_statement = successor.expected_state_statement(contract, qualification)
    state = successor.build_state_evidence(
        contract,
        qualification,
        statement=state_statement,
        recorded_at=now,
    )
    approval_statement = successor.expected_approval_statement(contract, qualification, state)
    approval = successor.build_approval(
        contract,
        qualification,
        state,
        statement=approval_statement,
        recorded_at=now + timedelta(seconds=1),
    )
    run_statement = successor.expected_run_statement(contract, qualification, state, approval)
    assert state.execution_authorized is False
    assert state.self_attested_nonproof is True
    assert approval.parent_to_supervisor_launch_limit == 1
    assert approval.supervisor_to_worker_launch_limit == 1
    assert approval.attempt_started is False
    assert state_statement != approval_statement != run_statement
    with pytest.raises(successor.TypedDiagnosticActivationError):
        successor.build_state_evidence(
            contract,
            qualification,
            statement="generic proceed",
            recorded_at=now,
        )


def test_mock_attempt_orders_ledger_and_generic_text_creates_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    contract: successor.TypedDiagnosticActivationContract,
) -> None:
    now = datetime.now(UTC) - timedelta(seconds=10)
    qualification = SimpleNamespace(
        contract_id=contract.contract_id,
        content_hash="sha256:" + "2" * 64,
        recorded_at=now,
    )
    state = successor.build_state_evidence(
        contract,
        qualification,
        statement=successor.expected_state_statement(contract, qualification),
        recorded_at=now + timedelta(seconds=1),
    )
    approval = successor.build_approval(
        contract,
        qualification,
        state,
        statement=successor.expected_approval_statement(contract, qualification, state),
        recorded_at=now + timedelta(seconds=2),
    )
    statement = successor.expected_run_statement(contract, qualification, state, approval)
    observation = _blocked_observation()
    monkeypatch.setattr(successor, "_load_qualification", lambda _root: qualification)
    monkeypatch.setattr(successor, "_load_state", lambda _root: state)
    monkeypatch.setattr(successor, "_load_approval", lambda _root: approval)

    rejected = tmp_path / "rejected"
    rejected.mkdir()
    with pytest.raises(successor.TypedDiagnosticActivationError):
        successor.run_once(
            statement="generic proceed",
            repository=rejected,
            parent_observer=lambda *_args, **_kwargs: observation,
        )
    assert not any((rejected / path).exists() for path in successor._ledger_paths())

    accepted = tmp_path / "accepted"
    accepted.mkdir()
    result = successor.run_once(
        statement=statement,
        repository=accepted,
        parent_observer=lambda *_args, **_kwargs: observation,
    )
    assert result["outcome"] == "blocked"
    assert result["reason"] == "dotenv_not_ready"
    assert result["retry_or_resume_allowed"] is False
    assert all((accepted / path).is_file() for path in successor._ledger_paths())


def test_source_modes_create_no_lifecycle_or_runtime_evidence(
    contract: successor.TypedDiagnosticActivationContract,
) -> None:
    authority = contract.authority
    assert (
        authority.state_approval_attempt_action_or_terminal_during_qualification_authorized is False
    )
    assert (
        authority.live_process_or_docker_dotenv_sdk_observation_during_qualification_authorized
        is False
    )
    for path in (
        successor.STATE_PATH,
        successor.APPROVAL_PATH,
        successor.RUN_AUTHORIZATION_PATH,
        successor.ATTEMPT_PATH,
        successor.ACTION_STARTED_PATH,
        successor.TERMINAL_PATH,
    ):
        assert not (REPOSITORY / path).exists()


def test_checked_in_source_qualification_when_present() -> None:
    if not (REPOSITORY / successor.QUALIFICATION_PATH).exists():
        pytest.skip("qualification is created only after the exact source commit")
    summary = successor.validate_source_qualification(repository=REPOSITORY)
    assert summary["diagnostic_mock_or_live_process_launch_count"] == 0
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["execution_authorized"] is False
