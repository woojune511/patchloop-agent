from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.evals import sanitized_sdk_import_bootstrap_successor as successor
from scripts import run_sanitized_sdk_import_bootstrap_child as child

REPOSITORY = Path(__file__).resolve().parents[1]
SENSITIVE_SYSTEMROOT = r"C:\must-never-persist\private-bootstrap-value"
SENSITIVE_EXCEPTION = "must-never-persist-import-exception"


def _validated(value: dict[str, Any]) -> successor.ImportBootstrapObservation:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return successor.validate_child_observation(payload)


def test_contract_binds_consumed_v7_and_keeps_runtime_closed() -> None:
    summary = successor.materialize_contract(repository=REPOSITORY)
    contract = successor.load_contract(repository=REPOSITORY)

    assert summary["external_observations_made"] == 0
    assert summary["execution_authorized"] is False
    assert contract.predecessor.terminal_id == successor.PREDECESSOR_TERMINAL_ID
    assert contract.predecessor.outcome == "error"
    assert contract.predecessor.reason == "sdk_diagnostic_error"
    assert contract.predecessor.docker_ready is True
    assert contract.predecessor.docker_cli_command_count == 8
    assert contract.predecessor.child_error_code == "diagnostic_runtime_import_error"
    assert contract.predecessor.transport_dispatch_count == 0
    assert contract.predecessor.activity_accounting_complete is True
    assert contract.predecessor.retry_or_resume_allowed is False
    assert contract.profile.v7_child_environment_names == (
        "PYTHONIOENCODING",
        "PYTHONUTF8",
    )
    assert contract.profile.required_bootstrap_passthrough_names == ("SYSTEMROOT",)
    assert contract.profile.bootstrap_value_return_limit == 0
    assert contract.profile.parent_runtime_integration_implemented is False
    assert contract.source_authority.parent_runtime_integration_authorized is False
    assert contract.source_authority.state_binding_or_exact_approval_authorized is False
    assert (
        contract.source_authority.docker_dotenv_sdk_client_probe_or_environment_observation_authorized
        is False
    )


@pytest.mark.parametrize(
    ("systemroot", "expected_code"),
    ((None, "systemroot_missing"), ("", "systemroot_empty")),
)
def test_systemroot_precondition_blocks_before_import(
    systemroot: str | None, expected_code: str
) -> None:
    calls: list[str] = []
    result = _validated(
        child.diagnose_import_bootstrap(
            environment_value=lambda _name: systemroot,
            import_module=lambda name: calls.append(name),
            sdk_package_present=lambda: False,
        )
    )

    assert result.state == "blocked"
    assert result.code == expected_code
    assert result.activity.import_attempt_count == 0
    assert result.activity.dotenv_file_read_count == 0
    assert result.activity.sdk_package_import_count == 0
    assert calls == []


def test_systemroot_presence_exception_is_sanitized() -> None:
    def environment_value(_name: str) -> str | None:
        raise RuntimeError(SENSITIVE_EXCEPTION)

    raw = child.diagnose_import_bootstrap(
        environment_value=environment_value,
        import_module=lambda _name: ModuleType("unused"),
        sdk_package_present=lambda: False,
    )
    result = _validated(raw)
    serialized = json.dumps(raw, sort_keys=True)

    assert result.state == "error"
    assert result.code == "systemroot_presence_error"
    assert SENSITIVE_EXCEPTION not in serialized
    assert "RuntimeError" not in serialized


@pytest.mark.parametrize(("failed_stage", "module_name"), child.IMPORT_STAGES)
def test_each_import_failure_has_one_fixed_value_free_code(
    failed_stage: str, module_name: str
) -> None:
    calls: list[str] = []

    def import_module(name: str) -> ModuleType:
        calls.append(name)
        if name == module_name:
            raise RuntimeError(SENSITIVE_EXCEPTION)
        return ModuleType(name)

    raw = child.diagnose_import_bootstrap(
        environment_value=lambda _name: SENSITIVE_SYSTEMROOT,
        import_module=import_module,
        sdk_package_present=lambda: False,
    )
    result = _validated(raw)
    serialized = json.dumps(raw, sort_keys=True)

    assert result.state == "error"
    assert result.stage.value == failed_stage
    assert result.code.value == f"{failed_stage}_import_error"
    assert result.activity.import_attempt_count == len(calls)
    assert result.activity.import_completed_count == len(calls) - 1
    assert result.activity.environment_value_return_count == 0
    assert result.activity.exception_message_type_repr_or_traceback_return_count == 0
    assert SENSITIVE_SYSTEMROOT not in serialized
    assert SENSITIVE_EXCEPTION not in serialized
    assert "RuntimeError" not in serialized


def test_all_staged_imports_ready_without_dotenv_or_sdk_package() -> None:
    calls: list[str] = []

    def import_module(name: str) -> ModuleType:
        calls.append(name)
        return ModuleType(name)

    raw = child.diagnose_import_bootstrap(
        environment_value=lambda _name: SENSITIVE_SYSTEMROOT,
        import_module=import_module,
        sdk_package_present=lambda: False,
    )
    result = _validated(raw)
    serialized = json.dumps(raw, sort_keys=True)

    assert result.state == "ready"
    assert result.stage == successor.ImportStage.COMPLETE
    assert result.code == successor.ImportCode.READY
    assert result.activity.import_attempt_count == len(child.IMPORT_STAGES)
    assert result.activity.import_completed_count == len(child.IMPORT_STAGES)
    assert result.activity.dotenv_file_read_count == 0
    assert result.activity.sdk_package_import_count == 0
    assert result.activity.network_call_count == 0
    assert SENSITIVE_SYSTEMROOT not in serialized


def test_recursive_sdk_package_import_is_counted_without_client_or_probe() -> None:
    result = _validated(
        child.diagnose_import_bootstrap(
            environment_value=lambda _name: SENSITIVE_SYSTEMROOT,
            import_module=lambda name: ModuleType(name),
            sdk_package_present=lambda: True,
        )
    )

    assert result.state == "ready"
    assert result.activity.sdk_package_import_count == 1
    assert result.activity.sdk_client_or_probe_count == 0
    assert result.activity.transport_dispatch_count == 0
    assert result.activity.network_call_count == 0


def test_observation_rejects_false_ready_projection() -> None:
    blocked = child.diagnose_import_bootstrap(
        environment_value=lambda _name: None,
        import_module=lambda name: ModuleType(name),
        sdk_package_present=lambda: False,
    )
    blocked.update({"state": "ready", "stage": "complete", "code": "ready"})
    with pytest.raises(ValidationError):
        successor.ImportBootstrapObservation.model_validate(blocked)


@pytest.mark.skipif(os.name != "nt", reason="v7 failure is Windows-specific")
def test_exact_v7_environment_reproduces_and_systemroot_corrects_import_boundary() -> None:
    systemroot = os.environ.get("SYSTEMROOT")
    if not systemroot:
        pytest.skip("current Windows process has no SYSTEMROOT")
    code = r"""
import importlib, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
try:
    importlib.import_module("asyncio.windows_events")
except OSError as exc:
    print("BLOCKED_10106" if getattr(exc, "winerror", None) == 10106 else "BLOCKED_OTHER")
except BaseException:
    print("BLOCKED_OTHER")
else:
    print("WINDOWS_EVENTS_READY")
"""
    base_environment = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    missing = subprocess.run(
        [sys.executable, "-I", "-E", "-s", "-B", "-c", code],
        cwd=REPOSITORY,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        shell=False,
        timeout=60,
        env=base_environment,
    )
    corrected = subprocess.run(
        [sys.executable, "-I", "-E", "-s", "-B", "-c", code],
        cwd=REPOSITORY,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        shell=False,
        timeout=60,
        env={**base_environment, "SYSTEMROOT": systemroot},
    )

    assert missing.returncode == 0
    assert missing.stdout.strip() == b"BLOCKED_10106"
    assert missing.stderr == b""
    assert corrected.returncode == 0
    assert corrected.stdout.strip() == b"WINDOWS_EVENTS_READY"
    assert corrected.stderr == b""


def test_checked_in_source_qualification_when_present() -> None:
    if not (REPOSITORY / successor.QUALIFICATION_PATH).exists():
        pytest.skip("qualification is created only after the exact source commit")
    summary = successor.validate_source_qualification(repository=REPOSITORY)
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["execution_authorized"] is False
