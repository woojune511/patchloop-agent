from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.evals import d137_no_call_preflight as d137
from patchloop.evals import sanitized_sdk_diagnostic_successor as successor
from scripts import run_sanitized_sdk_diagnostic_child as child

REPOSITORY = Path(__file__).resolve().parents[1]
SENSITIVE_EXCEPTION_TEXT = "must-never-appear-in-a-diagnostic"


def _fake_modules(
    *, constructor_error: bool = False, dispatch_during_constructor: bool = False
) -> tuple[ModuleType, ModuleType]:
    httpx_module = ModuleType("httpx")
    openai_module = ModuleType("openai")

    class MockTransport:
        def __init__(self, handler: Any) -> None:
            self.handler = handler

    class Client:
        def __init__(self, *, transport: MockTransport, trust_env: bool) -> None:
            self.transport = transport
            self.trust_env = trust_env
            self.is_closed = False

        def close(self) -> None:
            self.is_closed = True

    class OpenAI:
        def __init__(
            self,
            *,
            api_key: str,
            organization: str,
            project: str,
            webhook_secret: str,
            base_url: str,
            max_retries: int,
            http_client: Client,
        ) -> None:
            del api_key, organization, project, webhook_secret
            if dispatch_during_constructor:
                http_client.transport.handler(object())
            if constructor_error:
                raise RuntimeError(SENSITIVE_EXCEPTION_TEXT)
            self.base_url = base_url
            self.max_retries = max_retries
            self._http_client = http_client

        def close(self) -> None:
            self._http_client.close()

    httpx_module.MockTransport = MockTransport  # type: ignore[attr-defined]
    httpx_module.Client = Client  # type: ignore[attr-defined]
    openai_module.OpenAI = OpenAI  # type: ignore[attr-defined]
    return openai_module, httpx_module


def _presence_dependencies(*, present: Any) -> d137.SDKObservationDependencies:
    return d137.SDKObservationDependencies(
        python_executable=Path("never-used-python"),
        python_version="0.0.0",
        file_binding=lambda _path: {},
        distribution_version=lambda _name: None,
        find_module_spec=lambda _name: None,
        import_module=lambda _name: ModuleType("unused"),
        environment_present=present,
    )


def test_contract_binds_consumed_v5_and_keeps_all_runtime_authority_closed() -> None:
    summary = successor.materialize_contract(repository=REPOSITORY)
    contract = successor.load_contract(repository=REPOSITORY)

    assert summary["external_observations_made"] == 0
    assert summary["execution_authorized"] is False
    assert contract.predecessor.terminal_commit == successor.PREDECESSOR_TERMINAL_COMMIT
    assert contract.predecessor.outcome == "error"
    assert contract.predecessor.reason == "checker_error"
    assert contract.predecessor.retry_or_resume_allowed is False
    assert contract.profile.diagnostic_runtime_integration_implemented is False
    assert contract.profile.approval_or_attempt_entrypoint_implemented is False
    assert contract.source_authority.docker_sdk_or_dotenv_observation_authorized is False
    assert contract.source_authority.network_or_transport_authorized is False
    assert contract.source_authority.state_binding_or_approval_authorized is False


def test_synthetic_probe_succeeds_without_transport_dispatch() -> None:
    openai_module, httpx_module = _fake_modules()
    outcome = successor._sanitized_probe(
        openai_module=openai_module,
        httpx_module=httpx_module,
    )

    assert outcome.failure_stage is None
    assert outcome.transport_dispatch_count == 0
    assert outcome.probe is not None and outcome.probe["passed"] is True
    assert outcome.probe["ambient_credential_value_used"] is False
    assert outcome.probe["http_client_closed"] is True


def test_constructor_exception_is_reduced_to_fixed_stage_and_code() -> None:
    openai_module, httpx_module = _fake_modules(constructor_error=True)
    outcome = successor._sanitized_probe(
        openai_module=openai_module,
        httpx_module=httpx_module,
    )

    assert outcome.failure_stage == successor.SDKDiagnosticStage.OPENAI_CLIENT
    assert outcome.failure_code == successor.SDKDiagnosticCode.OPENAI_CLIENT_ERROR
    assert outcome.transport_dispatch_count == 0
    assert SENSITIVE_EXCEPTION_TEXT not in repr(outcome)


def test_any_synthetic_transport_dispatch_is_rejected_and_counted_once() -> None:
    openai_module, httpx_module = _fake_modules(dispatch_during_constructor=True)
    outcome = successor._sanitized_probe(
        openai_module=openai_module,
        httpx_module=httpx_module,
    )

    assert outcome.failure_stage == successor.SDKDiagnosticStage.OPENAI_CLIENT
    assert outcome.failure_code == successor.SDKDiagnosticCode.TRANSPORT_DISPATCH_REJECTED
    assert outcome.transport_dispatch_count == 1
    assert outcome.probe is None


def test_dependency_and_presence_exceptions_return_no_exception_material(tmp_path: Path) -> None:
    def dependency_error() -> d137.SDKObservationDependencies:
        raise RuntimeError(SENSITIVE_EXCEPTION_TEXT)

    dependency_result = successor.run_sanitized_sdk_diagnostic(
        repository=tmp_path,
        dependency_factory=dependency_error,
    )
    assert dependency_result.stage == successor.SDKDiagnosticStage.DEPENDENCY_BUILD
    assert dependency_result.code == successor.SDKDiagnosticCode.DEPENDENCY_BUILD_ERROR

    def presence_error(_name: str) -> bool:
        raise RuntimeError(SENSITIVE_EXCEPTION_TEXT)

    presence_result = successor.run_sanitized_sdk_diagnostic(
        repository=tmp_path,
        dependency_factory=lambda: _presence_dependencies(present=presence_error),
    )
    assert presence_result.stage == successor.SDKDiagnosticStage.PRESENCE
    assert presence_result.code == successor.SDKDiagnosticCode.PRESENCE_ERROR
    serialized = json.dumps(
        [
            dependency_result.model_dump(mode="json"),
            presence_result.model_dump(mode="json"),
        ],
        sort_keys=True,
    )
    assert SENSITIVE_EXCEPTION_TEXT not in serialized
    assert "RuntimeError" not in serialized
    assert dependency_result.exception_message_type_repr_or_traceback_returned is False
    assert presence_result.exception_message_type_repr_or_traceback_returned is False


def test_missing_presence_is_typed_blocked_without_later_sdk_stages(tmp_path: Path) -> None:
    result = successor.run_sanitized_sdk_diagnostic(
        repository=tmp_path,
        dependency_factory=lambda: _presence_dependencies(present=lambda _name: False),
    )

    assert result.state == "blocked"
    assert result.stage == successor.SDKDiagnosticStage.COMPLETE
    assert result.code == successor.SDKDiagnosticCode.SDK_BLOCKED
    assert result.sdk_observation is not None
    assert result.sdk_observation["passed"] is False
    assert result.activity.attempted_stages == (
        successor.SDKDiagnosticStage.DEPENDENCY_BUILD,
        successor.SDKDiagnosticStage.PRESENCE,
        successor.SDKDiagnosticStage.COMPLETE,
    )
    assert result.activity.transport_dispatch_count == 0


def test_unclassified_checker_fault_is_reduced_to_internal_sanitizer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def escaped_fault(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(SENSITIVE_EXCEPTION_TEXT)

    monkeypatch.setattr(successor, "_completed_result", escaped_fault)
    result = successor.run_sanitized_sdk_diagnostic(
        repository=tmp_path,
        dependency_factory=lambda: _presence_dependencies(present=lambda _name: False),
    )

    assert result.stage == successor.SDKDiagnosticStage.INTERNAL_SANITIZER
    assert result.code == successor.SDKDiagnosticCode.INTERNAL_SANITIZER_ERROR
    assert SENSITIVE_EXCEPTION_TEXT not in json.dumps(result.model_dump(mode="json"))


def test_stage_activity_rejects_repetition_and_non_prefix_completion() -> None:
    with pytest.raises(ValidationError):
        successor.DiagnosticActivity(
            attempted_stages=(
                successor.SDKDiagnosticStage.PRESENCE,
                successor.SDKDiagnosticStage.PRESENCE,
            ),
            completed_stages=(successor.SDKDiagnosticStage.PRESENCE,),
            transport_dispatch_count=0,
        )
    with pytest.raises(ValidationError):
        successor.DiagnosticActivity(
            attempted_stages=(
                successor.SDKDiagnosticStage.DEPENDENCY_BUILD,
                successor.SDKDiagnosticStage.PRESENCE,
            ),
            completed_stages=(successor.SDKDiagnosticStage.PRESENCE,),
            transport_dispatch_count=0,
        )


def test_child_missing_dotenv_does_not_enter_sdk_diagnostic(tmp_path: Path) -> None:
    result = child._run(tmp_path)

    assert result["state"] == "blocked"
    assert result["dotenv"]["error_code"] == "dotenv_missing"
    assert result["diagnostic"] is None
    assert result["activity"]["dotenv_file_read_count"] == 0
    assert result["activity"]["transport_dispatch_count"] == 0
    assert result["activity"]["network_call_count"] == 0
    assert result["raw_credential_value_returned"] is False


def test_no_approval_attempt_or_runtime_integration_entrypoint_exists() -> None:
    assert not hasattr(successor, "record_exact_approval")
    assert not hasattr(successor, "run_once")
    assert not hasattr(successor, "materialize_state_change_evidence")


def test_checked_in_source_qualification_when_present() -> None:
    if not (REPOSITORY / successor.QUALIFICATION_PATH).exists():
        pytest.skip("qualification is created only after the exact source commit")
    summary = successor.validate_source_qualification(repository=REPOSITORY)
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["execution_authorized"] is False
