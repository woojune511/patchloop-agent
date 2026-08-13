from __future__ import annotations

import ast
import json
from enum import IntEnum, StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from patchloop.evals import d137_no_call_preflight as d137
from patchloop.evals import order_stable_typed_diagnostic_successor as successor
from patchloop.evals import sanitized_sdk_diagnostic_successor as sdk
from scripts import run_order_stable_typed_diagnostic_projection_v24 as projection
from scripts import run_sanitized_sdk_bootstrap_envelope_diagnostic_v22 as old_channel
from scripts import run_sanitized_sdk_diagnostic_child as diagnostic_child

REPOSITORY = Path(__file__).resolve().parents[1]
SECRET_SENTINEL = "sk-v24-invalid-input-must-never-persist"
EXCEPTION_SENTINEL = "v24-exception-text-must-never-persist"


def _ready_dotenv() -> dict[str, Any]:
    return {
        "file_present": True,
        "exact_subject_declared": True,
        "exact_subject_nonempty": True,
        "duplicate_subject": False,
        "error_code": None,
        "raw_value_returned": False,
        "value_hash_prefix_or_length_returned": False,
    }


def _dotenv_activity() -> dict[str, Any]:
    return {
        "dotenv_file_read_count": 1,
        "dotenv_subject_membership_check_count": 1,
        "credential_assignment_parse_count": 1,
    }


def _sdk_present_child() -> dict[str, Any]:
    dependencies = d137.SDKObservationDependencies(
        python_executable=Path("v24-never-used-python"),
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
    assert diagnostic.sdk_observation is not None
    return diagnostic_child._result(
        dotenv=_ready_dotenv(),
        dotenv_activity=_dotenv_activity(),
        diagnostic=diagnostic.model_dump(mode="json"),
        state=diagnostic.state,
        error_code=diagnostic.code.value,
    )


def _dotenv_blocked_child() -> dict[str, Any]:
    return diagnostic_child._result(
        dotenv={
            "file_present": False,
            "exact_subject_declared": False,
            "exact_subject_nonempty": False,
            "duplicate_subject": False,
            "error_code": "dotenv_missing",
            "raw_value_returned": False,
            "value_hash_prefix_or_length_returned": False,
        },
        dotenv_activity={},
        diagnostic=None,
        state="blocked",
        error_code="dotenv_missing",
    )


def test_contract_binds_consumed_v23_and_keeps_activation_closed() -> None:
    contract = successor._build_contract(REPOSITORY)

    assert contract.predecessor.contract_id == successor.V23_CONTRACT_ID
    assert contract.predecessor.terminal_id == successor.V23_TERMINAL_ID
    assert contract.predecessor.worker_code == "diagnostic_result_invalid"
    assert contract.predecessor.activity_accounting_complete is False
    assert contract.predecessor.unknown_activity_possible is True
    assert contract.predecessor.retry_replacement_or_resume_allowed is False
    assert contract.runtime.predecessor_failure_reproduced_with_sdk_observation_fixture is True
    assert contract.runtime.predecessor_terminal_exact_invalid_field_proven is False
    assert contract.runtime.legacy_validation_preserves_input_mapping_order is True
    assert contract.runtime.projection_requires_direct_precanonical_observed_child is True
    assert contract.runtime.canonical_frame_transmits_full_legacy_child is False
    assert contract.runtime.canonical_frame_transmits_value_free_summary is True
    assert contract.runtime.activation_runtime_or_live_callback_exposed is False
    assert contract.authority.diagnostic_mock_or_live_process_launch_authorized is False
    assert contract.authority.local_git_provenance_subprocesses_may_run is True
    assert contract.authority.docker_dotenv_sdk_live_observation_authorized is False
    assert contract.authority.state_approval_attempt_action_or_terminal_authorized is False
    assert contract.lifecycle_or_live_execution_implemented is False
    assert contract.execution_currently_authorized is False
    assert contract.next_gate == "new-versioned-v25-activation-wrapper-required"


def test_sdk_observation_order_loss_reproduces_old_failure_and_v24_passes() -> None:
    observed = _sdk_present_child()

    old = old_channel.project_worker_envelope(
        REPOSITORY,
        mode=old_channel.Mode.LIVE,
        observed_child=observed,
    )
    assert old["code"] == "diagnostic_result_invalid"
    assert old["child"] is None

    corrected = projection.project_observed_child(REPOSITORY, observed)
    assert corrected["code"] is None
    assert corrected["activity"]["activity_accounting_complete"] is True
    summary = corrected["summary"]
    assert summary is not None
    assert summary["state"] == "blocked"
    assert summary["diagnostic"]["code"] == "sdk_blocked"
    assert "sdk_observation" not in summary["diagnostic"]
    assert projection.validate_projection(corrected) is True

    decoded = projection.decode_projection_frame(projection.encode_projection_frame(corrected))
    assert decoded.stage.value == "valid"
    assert decoded.value == corrected


def test_dotenv_blocked_child_remains_valid_without_sdk_summary() -> None:
    result = projection.project_observed_child(REPOSITORY, _dotenv_blocked_child())

    assert result["code"] is None
    assert result["summary"]["state"] == "blocked"
    assert result["summary"]["diagnostic"] is None
    assert result["summary"]["error_code"] == "dotenv_missing"
    assert projection.validate_projection(result) is True


def test_already_canonicalized_legacy_sdk_mapping_fails_closed() -> None:
    observed = _sdk_present_child()
    reordered = json.loads(json.dumps(observed, sort_keys=True))

    result = projection.project_observed_child(REPOSITORY, reordered)

    assert result["summary"] is None
    assert result["code"] == "diagnostic_result_invalid"
    assert result["activity"]["unknown_workload_activity_possible"] is True


def test_invalid_and_secret_bearing_inputs_reduce_to_one_fixed_result() -> None:
    invalid_values = (
        {"secret": SECRET_SENTINEL},
        {"exception": EXCEPTION_SENTINEL},
        {"schema_version": "unexpected", "value": SECRET_SENTINEL},
    )
    for observed in invalid_values:
        result = projection.project_observed_child(REPOSITORY, observed)
        rendered = json.dumps(result, sort_keys=True)
        assert result["summary"] is None
        assert result["code"] == "diagnostic_result_invalid"
        assert result["activity"]["activity_accounting_complete"] is False
        assert result["activity"]["unknown_workload_activity_possible"] is True
        assert result["raw_output_returned"] is False
        assert result["exception_message_type_repr_or_traceback_returned"] is False
        assert result["credential_value_hash_prefix_or_length_returned"] is False
        assert SECRET_SENTINEL not in rendered
        assert EXCEPTION_SENTINEL not in rendered


def test_projection_rejects_python_coercion_types_before_json() -> None:
    class Zero(IntEnum):
        VALUE = 0

    class Blocked(StrEnum):
        VALUE = "blocked"

    class IntSubclass(int):
        pass

    class StrSubclass(str):
        pass

    values = []
    for replacement in (Zero.VALUE, IntSubclass(1)):
        child = _dotenv_blocked_child()
        child["activity"]["dotenv_file_read_count"] = replacement
        values.append(child)
    for replacement in (Blocked.VALUE, StrSubclass("blocked")):
        child = _dotenv_blocked_child()
        child["state"] = replacement
        values.append(child)
    for child in values:
        result = projection.project_observed_child(REPOSITORY, child)
        assert result["code"] == "diagnostic_result_invalid"
        assert result["summary"] is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["summary"].update({"unexpected": True}),
        lambda value: value["summary"].update({"state": "ready"}),
        lambda value: value["summary"]["diagnostic"].update({"code": "ready"}),
        lambda value: value["summary"]["diagnostic"].update(
            {"stage": "presence", "code": "openai_client_error"}
        ),
        lambda value: value["summary"]["activity"].update({"transport_dispatch_count": True}),
        lambda value: value["summary"]["activity"].update({"network_call_count": 1}),
        lambda value: value["summary"]["dotenv"].update({"exact_subject_nonempty": False}),
        lambda value: value["activity"].update({"activity_accounting_complete": False}),
        lambda value: value["activity"].update({"input_validation_count": True}),
        lambda value: value["activity"].update({"summary_projection_count": True}),
    ],
)
def test_summary_semantic_drift_fails_closed(mutate: Any) -> None:
    value = projection.project_observed_child(REPOSITORY, _sdk_present_child())
    mutate(value)

    assert projection.validate_projection(value) is False
    with pytest.raises(ValueError, match="projection is invalid"):
        projection.encode_projection_frame(value)


def test_public_surface_has_no_live_callback_process_or_lifecycle_mode() -> None:
    runtime_source = (REPOSITORY / successor.PROJECTION_PATH).read_text(encoding="utf-8")
    build_source = (REPOSITORY / successor.BUILD_SCRIPT_PATH).read_text(encoding="utf-8")
    tree = ast.parse(runtime_source)
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    imported = {alias.name.split(".", 1)[0] for node in imports for alias in node.names}

    assert not imported.intersection({"patchloop", "openai", "httpx", "dotenv"})
    assert "subprocess" not in imported
    assert "--live" not in build_source
    assert "--run" not in build_source
    assert "--record-state" not in build_source
    assert "--record-approval" not in build_source
    assert "--materialize-contract" in build_source
    assert "--qualify-source" in build_source
    for name in ("run_once", "record_state", "record_approval", "run_live"):
        assert not hasattr(successor, name)


def test_checked_in_contract_and_qualification_when_present() -> None:
    if not (REPOSITORY / successor.CONTRACT_PATH).exists():
        pytest.skip("contract is materialized after source implementation")
    contract = successor.load_contract(repository=REPOSITORY)
    assert contract == successor._build_contract(REPOSITORY)
    if not (REPOSITORY / successor.QUALIFICATION_PATH).exists():
        pytest.skip("qualification is created only after the exact source commit")
    summary = successor.validate_source_qualification(repository=REPOSITORY)
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["diagnostic_mock_or_live_process_launch_count"] == 0
    assert summary["execution_authorized"] is False
