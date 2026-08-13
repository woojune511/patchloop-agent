from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from patchloop.evals import d137_no_call_preflight as d137
from patchloop.evals import order_stable_typed_diagnostic_activation_successor as successor
from patchloop.evals import sanitized_sdk_diagnostic_successor as sdk
from scripts import run_sanitized_sdk_diagnostic_child as diagnostic_child

REPOSITORY = Path(__file__).resolve().parents[1]


def _v24_pair() -> tuple[Any, Any]:
    contract = successor.v24.OrderStableDiagnosticContract.model_validate_json(
        (REPOSITORY / successor.v24.CONTRACT_PATH).read_bytes()
    )
    qualification = successor.v24.SourceQualification.model_validate_json(
        (REPOSITORY / successor.v24.QUALIFICATION_PATH).read_bytes()
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
    predecessor = _v24_pair()
    monkeypatch.setattr(successor, "load_contract", lambda **_kwargs: contract)
    monkeypatch.setattr(successor, "_load_v24_source", lambda _root: predecessor)


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
    child = successor.v23.channel._fixed_child()
    projected = successor.v24.projection.project_observed_child(REPOSITORY, child)
    decoded = successor.channel.decode_worker_frame(
        REPOSITORY,
        successor.channel.encode_frame(REPOSITORY, projected),
    )
    outcome = successor.channel.WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=1,
        returncode=0,
        frame=decoded,
        activity_accounting_complete=True,
        unknown_process_activity_possible=False,
    )
    envelope = successor.channel.build_supervisor_envelope(outcome)
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


def _sdk_blocked_child() -> dict[str, Any]:
    dependencies = d137.SDKObservationDependencies(
        python_executable=Path("v25-never-used-python"),
        python_version="0.0.0",
        file_binding=lambda _path: {},
        distribution_version=lambda _name: None,
        find_module_spec=lambda _name: None,
        import_module=lambda _name: ModuleType("unused"),
        environment_present=lambda name: name == "OPENAI_API_KEY",
    )
    diagnostic = sdk.run_sanitized_sdk_diagnostic(
        repository=REPOSITORY,
        dependency_factory=lambda: dependencies,
    )
    assert diagnostic.state == "blocked"
    return diagnostic_child._result(
        dotenv={
            "file_present": True,
            "exact_subject_declared": True,
            "exact_subject_nonempty": True,
            "duplicate_subject": False,
            "error_code": None,
            "raw_value_returned": False,
            "value_hash_prefix_or_length_returned": False,
        },
        dotenv_activity={
            "dotenv_file_read_count": 1,
            "dotenv_subject_membership_check_count": 1,
            "credential_assignment_parse_count": 1,
        },
        diagnostic=diagnostic.model_dump(mode="json"),
        state=diagnostic.state,
        error_code=diagnostic.code.value,
    )


def _channel_for_projection(projected: dict[str, Any]) -> successor.ChannelObservation:
    decoded = successor.channel.decode_worker_frame(
        REPOSITORY,
        successor.channel.encode_frame(REPOSITORY, projected),
    )
    activity = projected["activity"]
    outcome = successor.channel.WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=1,
        returncode=0,
        frame=decoded,
        activity_accounting_complete=activity["activity_accounting_complete"],
        unknown_process_activity_possible=activity["unknown_workload_activity_possible"],
    )
    envelope = successor.channel.build_supervisor_envelope(outcome)
    assert successor.channel.validate_live_supervisor_envelope(envelope)
    return successor._channel_from_process(
        {
            "launch_attempt_count": 1,
            "process_return_count": 1,
            "returncode": 0,
            "frame_stage": "valid",
            "envelope": envelope,
            "activity_accounting_complete": activity["activity_accounting_complete"],
            "unknown_process_activity_possible": activity["unknown_workload_activity_possible"],
        }
    )


def _blocked_observation() -> successor.PreflightObservation:
    return successor._compose_parent_observation(_docker(passed=True), _blocked_channel())


def test_contract_binds_v24_and_keeps_source_qualification_closed(
    contract: successor.TypedDiagnosticActivationContract,
) -> None:
    assert contract.predecessor.source_commit == successor.V24_SOURCE_COMMIT
    assert contract.predecessor.source_tree == successor.V24_SOURCE_TREE
    assert contract.predecessor.qualification_commit == successor.V24_QUALIFICATION_COMMIT
    assert contract.predecessor.source_qualification_hash == successor.V24_QUALIFICATION_HASH
    assert contract.predecessor.state_approval_attempt_or_terminal_count == 0
    assert contract.runtime.approved_scopes == successor.APPROVED_SCOPES
    assert contract.runtime.default_observer_reachable_only_after_action_started is True
    assert contract.runtime.standalone_observation_cli_exposed is False
    assert contract.runtime.parent_to_supervisor_launch_limit == 1
    assert contract.runtime.supervisor_to_worker_launch_limit == 1
    assert contract.runtime.typed_v24_projection_required is True
    assert contract.runtime.direct_precanonical_child_to_v24_projection_required is True
    assert contract.runtime.full_legacy_child_cross_process_transmission_allowed is False
    assert contract.runtime.value_free_summary_only is True
    assert contract.lifecycle.v24_source_or_qualification_mutation_allowed is False
    assert contract.state_approval_and_attempt_entrypoints_implemented is True
    assert contract.execution_currently_authorized is False
    assert contract.next_gate == "fresh-exact-v25-state-statement"


def test_internal_live_script_has_only_stdlib_top_level_imports() -> None:
    source = (REPOSITORY / successor.LIVE_CHANNEL_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    imported = {alias.name.split(".", 1)[0] for node in imports for alias in node.names}
    assert not imported.intersection({"patchloop", "openai", "httpx", "dotenv"})
    assert 'role.add_argument("--worker"' in source
    assert 'role.add_argument("--supervisor"' in source
    assert "run_live_supervisor_process" in source
    assert "project_observed_child(root, observed)" in source


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
    assert '"projection"' in rendered
    assert '"sdk_observation"' not in rendered
    assert '"child"' not in rendered
    assert "OPENAI_API_KEY=" not in rendered
    assert "sk-" not in rendered.lower()


def test_sdk_observation_crosses_v25_only_as_order_stable_value_free_summary(
    contract: successor.TypedDiagnosticActivationContract,
) -> None:
    observed = _sdk_blocked_child()
    projected = successor.v24.projection.project_observed_child(REPOSITORY, observed)
    channel_observation = _channel_for_projection(projected)

    result = successor._run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _docker(passed=True),
        channel_observer=lambda *_args, **_kwargs: channel_observation,
    )

    assert result.state == "blocked"
    assert result.reason == "sdk_diagnostic_blocked"
    assert result.network_call_count == 0
    assert result.provider_evaluator_agent_call_count == 0
    assert result.activity_accounting_complete is True
    rendered = json.dumps(result.model_dump(mode="json"), sort_keys=True)
    assert '"sdk_observation"' not in rendered
    assert '"child"' not in rendered


def test_fixed_invalid_projection_stays_incomplete_and_unknown() -> None:
    projected = successor.v24.projection.project_observed_child(
        REPOSITORY, {"schema_version": "invalid"}
    )
    channel_observation = _channel_for_projection(projected)
    result = successor._compose_parent_observation(_docker(passed=True), channel_observation)

    assert result.state == "error"
    assert result.reason == "child_checker_error"
    assert result.network_call_count is None
    assert result.provider_evaluator_agent_call_count is None
    assert result.activity_accounting_complete is False
    assert result.unknown_post_marker_activity_possible is True


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
