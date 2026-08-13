from __future__ import annotations

import ast
import hashlib
import json
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.evals import envelope_diagnostic_activation_successor as successor
from patchloop.evals.sanitized_sdk_parent_integration import IsolatedDiagnosticChild
from scripts import run_sanitized_sdk_bootstrap_envelope_diagnostic_v22 as channel

REPOSITORY = Path(__file__).resolve().parents[1]
SENTINEL_A = "sk-v22-ambient-secret-a"
SENTINEL_B = "sk-v22-ambient-secret-b-with-different-length"
EXCEPTION_SENTINEL = "v22-exception-material-must-not-escape"


@pytest.fixture(scope="module")
def contract() -> successor.EnvelopeDiagnosticActivationContract:
    return successor._build_contract(REPOSITORY)


def _blocked_child() -> dict[str, Any]:
    return {
        "schema_version": "isolated-dotenv-sanitized-sdk-diagnostic-v1",
        "state": "blocked",
        "dotenv": {
            "file_present": False,
            "exact_subject_declared": False,
            "exact_subject_nonempty": False,
            "duplicate_subject": False,
            "error_code": "dotenv_missing",
            "raw_value_returned": False,
            "value_hash_prefix_or_length_returned": False,
        },
        "diagnostic": None,
        "error_code": "dotenv_missing",
        "activity": {
            "dotenv_file_read_count": 0,
            "dotenv_subject_membership_check_count": 0,
            "credential_assignment_parse_count": 0,
            "credential_value_return_count": 0,
            "credential_value_hash_prefix_or_length_count": 0,
            "exception_message_type_repr_or_traceback_return_count": 0,
            "transport_dispatch_count": 0,
            "network_call_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
        "raw_credential_value_returned": False,
        "credential_hash_prefix_or_length_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
    }


def _typed_child(value: dict[str, Any]) -> dict[str, Any]:
    return IsolatedDiagnosticChild.model_validate(value).model_dump(mode="json")


def _framed_body(body: bytes) -> bytes:
    return len(body).to_bytes(4, "big") + hashlib.sha256(body).digest() + body


def _live_worker(child: dict[str, Any] | None = None) -> dict[str, Any]:
    selected = _blocked_child() if child is None else child
    return channel.project_worker_envelope(
        REPOSITORY,
        mode=channel.Mode.LIVE,
        observed_child=selected,
    )


def test_contract_binds_exact_v21_and_keeps_every_lifecycle_authority_closed(
    contract: successor.EnvelopeDiagnosticActivationContract,
) -> None:
    predecessor = contract.predecessor
    assert predecessor.source_commit == successor.V21_SOURCE_COMMIT
    assert predecessor.source_tree == successor.V21_SOURCE_TREE
    assert predecessor.qualification_commit == successor.V21_QUALIFICATION_COMMIT
    assert predecessor.contract_id == successor.V21_CONTRACT_ID
    assert predecessor.source_qualification_hash == successor.V21_QUALIFICATION_HASH
    assert predecessor.fixture_passed is True
    assert predecessor.fixture_is_transport_evidence_only is True
    assert predecessor.fixture_process_external_activity_absence_proven is False
    assert predecessor.readiness_or_sdk_result_created is False
    assert predecessor.state_approval_attempt_or_terminal_count == 0
    assert predecessor.execution_authorized is False

    runtime = contract.runtime
    assert runtime.typed_live_diagnostic_envelope_required is True
    assert runtime.fixed_fixture_and_live_schema_separated is True
    assert runtime.live_observation_input_projection_only is True
    assert runtime.live_supervisor_input_projection_only is True
    assert runtime.live_diagnostic_default_exposed is False
    assert runtime.activation_runtime_exposed is False
    assert runtime.offline_fixed_mock_local_test_entrypoint_exposed is True
    assert runtime.offline_fixed_mock_local_test_process_launch_limit == 2
    assert runtime.live_process_entrypoint_exposed is False
    assert runtime.qualification_diagnostic_or_mock_process_launch_limit == 0
    assert runtime.local_git_provenance_subprocesses_may_run is True
    assert runtime.qualification_reuses_recorded_v21_evidence_only is True
    assert runtime.parent_to_supervisor_launch_limit == 1
    assert runtime.supervisor_to_worker_launch_limit == 1
    assert runtime.invalid_raw_payload_metadata_persisted is False
    assert runtime.offline_worker_schema_version == channel.OFFLINE_WORKER_SCHEMA_VERSION
    assert runtime.offline_supervisor_schema_version == channel.OFFLINE_SUPERVISOR_SCHEMA_VERSION
    assert runtime.live_worker_schema_version == channel.LIVE_WORKER_SCHEMA_VERSION
    assert runtime.live_supervisor_schema_version == channel.LIVE_SUPERVISOR_SCHEMA_VERSION
    assert successor.UV_LOCK_PATH in successor.SOURCE_FILES
    assert successor.PRODUCTION_MODEL_PATH in successor.SOURCE_FILES

    assert contract.lifecycle.fresh_source_bound_state_required is True
    assert contract.lifecycle.separate_exact_approval_required is True
    assert contract.lifecycle.retry_replacement_or_resume_allowed is False
    assert contract.authority.offline_fixed_mock_local_test_process_launch_authorized is True
    assert contract.authority.live_process_launch_authorized is False
    assert contract.authority.state_approval_attempt_action_or_terminal_creation_authorized is False
    assert contract.authority.docker_dotenv_sdk_network_or_provider_observation_authorized is False
    assert contract.state_approval_attempt_or_terminal_entrypoints_implemented is False
    assert contract.offline_fixed_mock_test_entrypoint_exposed is True
    assert contract.live_process_entrypoint_exposed is False
    assert contract.readiness_or_sdk_result_created is False
    assert contract.execution_currently_authorized is False
    assert contract.next_gate == "new-versioned-v23-activation-wrapper-required"
    for name in (
        "STATE_PATH",
        "APPROVAL_PATH",
        "ATTEMPT_PATH",
        "ACTION_STARTED_PATH",
        "TERMINAL_PATH",
        "build_state_evidence",
        "build_approval",
        "run_once",
        "run_parent_preflight_injected",
    ):
        assert not hasattr(successor, name)
    assert not hasattr(channel, "build_worker_envelope")


def test_cli_is_offline_fixed_mock_only_and_top_level_imports_are_stdlib() -> None:
    source = (REPOSITORY / successor.SUPERVISOR_PATH).read_text(encoding="utf-8")
    assert '"--offline-fixed-mock"' in source
    assert '"--live"' not in source
    assert '"--repository"' not in source

    tree = ast.parse(source)
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    imported = {alias.name.split(".", 1)[0] for node in imports for alias in node.names}
    assert not imported.intersection({"patchloop", "openai", "httpx", "dotenv"})


def test_live_adapter_maps_only_a_strict_typed_child() -> None:
    envelope = _live_worker()
    assert channel.validate_live_worker_envelope(envelope) is True
    assert envelope["code"] is None
    assert envelope["child"] == _typed_child(_blocked_child())
    assert envelope["activity"]["diagnostic_invocation_count"] == 1
    assert envelope["activity"]["typed_validation_count"] == 1
    decoded = channel.decode_worker_frame(
        channel.encode_frame(envelope),
        mode=channel.Mode.LIVE,
    )
    assert decoded.stage == "valid"
    assert decoded.value == envelope


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update({"unexpected": "field"}),
        lambda value: value.update({"state": "ready"}),
        lambda value: value.update({"error_code": None}),
        lambda value: value["dotenv"].update({"file_present": "false"}),
        lambda value: value["activity"].update({"dotenv_file_read_count": True}),
    ],
)
def test_live_adapter_rejects_extra_bool_and_semantic_child_drift(
    mutate: Any,
) -> None:
    child = _blocked_child()
    mutate(child)
    envelope = channel.project_worker_envelope(
        REPOSITORY,
        mode=channel.Mode.LIVE,
        observed_child=child,
    )
    assert envelope["child"] is None
    assert envelope["code"] == "diagnostic_result_invalid"
    assert envelope["activity"]["activity_accounting_complete"] is False
    assert envelope["activity"]["unknown_workload_activity_possible"] is True
    assert channel.validate_live_worker_envelope(envelope) is True


def test_live_adapter_rejects_enum_values_that_require_type_coercion() -> None:
    class Zero(IntEnum):
        VALUE = 0

    class Blocked(StrEnum):
        VALUE = "blocked"

    int_child = _blocked_child()
    int_child["activity"]["dotenv_file_read_count"] = Zero.VALUE
    str_child = _blocked_child()
    str_child["state"] = Blocked.VALUE
    for child in (int_child, str_child):
        value = channel.project_worker_envelope(
            REPOSITORY,
            mode=channel.Mode.LIVE,
            observed_child=child,
        )
        assert value["code"] == "diagnostic_result_invalid"
        assert value["child"] is None


def test_live_adapter_rejects_primitive_subclasses_before_json_projection() -> None:
    class IntSubclass(int):
        pass

    class StrSubclass(str):
        pass

    int_child = _blocked_child()
    int_child["activity"]["dotenv_file_read_count"] = IntSubclass(0)
    str_child = _blocked_child()
    str_child["state"] = StrSubclass("blocked")
    for child in (int_child, str_child):
        value = channel.project_worker_envelope(
            REPOSITORY,
            mode=channel.Mode.LIVE,
            observed_child=child,
        )
        assert value["code"] == "diagnostic_result_invalid"
        assert value["child"] is None


def test_fixed_error_and_invalid_child_reduce_to_value_free_results() -> None:
    execution_error = channel.project_worker_envelope(
        REPOSITORY,
        mode=channel.Mode.LIVE,
        observed_error=channel.WorkerCode.DIAGNOSTIC_EXECUTION_ERROR,
    )
    invalid = channel.project_worker_envelope(
        REPOSITORY,
        mode=channel.Mode.LIVE,
        observed_child={"secret": SENTINEL_A},
    )
    assert execution_error["code"] == "diagnostic_execution_error"
    assert invalid["code"] == "diagnostic_result_invalid"
    for value in (execution_error, invalid):
        assert value["child"] is None
        rendered = json.dumps(value, sort_keys=True)
        assert SENTINEL_A not in rendered
        assert EXCEPTION_SENTINEL not in rendered
        assert value["raw_output_returned"] is False
        assert value["exception_message_type_repr_or_traceback_returned"] is False
        assert value["credential_value_hash_prefix_or_length_returned"] is False


def test_worker_decoder_rejects_cross_schema_noncanonical_duplicate_and_bool_counter() -> None:
    offline = channel.fixed_worker_fixture()
    cross = channel.decode_worker_frame(
        channel.encode_frame(offline),
        mode=channel.Mode.LIVE,
    )
    assert cross.stage == "schema_invalid"
    assert cross.value is None

    live = _live_worker()
    noncanonical = (json.dumps(live, indent=2) + "\n").encode("utf-8")
    decoded = channel.decode_worker_frame(_framed_body(noncanonical), mode=channel.Mode.LIVE)
    assert decoded.stage == "schema_invalid"
    assert decoded.value is None

    canonical = json.dumps(live, sort_keys=True, separators=(",", ":"))
    duplicate = (
        canonical.replace(
            f'"schema_version":"{channel.LIVE_WORKER_SCHEMA_VERSION}"',
            f'"schema_version":"{channel.LIVE_WORKER_SCHEMA_VERSION}",'
            f'"schema_version":"{channel.LIVE_WORKER_SCHEMA_VERSION}"',
            1,
        ).encode("utf-8")
        + b"\n"
    )
    decoded = channel.decode_worker_frame(_framed_body(duplicate), mode=channel.Mode.LIVE)
    assert decoded.stage == "json_invalid"
    assert decoded.value is None

    live["activity"]["diagnostic_invocation_count"] = True
    decoded = channel.decode_worker_frame(channel.encode_frame(live), mode=channel.Mode.LIVE)
    assert decoded.stage == "semantic_invalid"
    assert decoded.value is None

    forged_child = _live_worker()
    forged_child["child"]["state"] = "ready"
    decoded = channel.decode_worker_frame(
        channel.encode_frame(forged_child), mode=channel.Mode.LIVE
    )
    assert decoded.stage == "semantic_invalid"
    assert decoded.value is None


def test_live_supervisor_rejects_a_worker_callback_without_invoking_it() -> None:
    calls = 0

    def raises_once(*_args: Any, **_kwargs: Any) -> channel.WorkerProcessOutcome:
        nonlocal calls
        calls += 1
        raise TypeError(EXCEPTION_SENTINEL)

    with pytest.raises(ValueError):
        channel.build_supervisor_envelope(
            REPOSITORY,
            mode=channel.Mode.LIVE,
            worker_runner=raises_once,
        )
    assert calls == 0


def test_supervisor_preserves_inner_unknown_accounting() -> None:
    worker_value = channel.project_worker_envelope(
        REPOSITORY,
        mode=channel.Mode.LIVE,
        observed_error=channel.WorkerCode.DIAGNOSTIC_EXECUTION_ERROR,
    )
    outcome = channel.WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=1,
        returncode=0,
        frame=channel.decode_worker_frame(
            channel.encode_frame(worker_value), mode=channel.Mode.LIVE
        ),
        activity_accounting_complete=True,
        unknown_process_activity_possible=False,
    )
    value = channel.build_supervisor_envelope(
        REPOSITORY,
        mode=channel.Mode.LIVE,
        observed_outcome=outcome,
    )
    assert value["code"] is None
    assert value["worker"]["code"] == "diagnostic_execution_error"
    assert value["activity"]["activity_accounting_complete"] is False
    assert value["activity"]["unknown_process_activity_possible"] is True
    assert channel.validate_live_supervisor_envelope(value) is True


def test_supervisor_decoder_rejects_cross_schema_and_semantic_counter_drift() -> None:
    worker = channel.WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=1,
        returncode=0,
        frame=channel.decode_worker_frame(
            channel.encode_frame(channel.fixed_worker_fixture()),
            mode=channel.Mode.OFFLINE_FIXED_MOCK,
        ),
        activity_accounting_complete=True,
        unknown_process_activity_possible=False,
    )
    offline = channel.build_supervisor_envelope(
        REPOSITORY,
        mode=channel.Mode.OFFLINE_FIXED_MOCK,
        worker_runner=lambda *_args, **_kwargs: worker,
    )
    decoded = channel.decode_supervisor_frame(
        channel.encode_frame(offline),
        mode=channel.Mode.LIVE,
    )
    assert decoded.stage == "schema_invalid"
    assert decoded.value is None

    offline["activity"]["worker_launch_attempt_count"] = True
    decoded = channel.decode_supervisor_frame(
        channel.encode_frame(offline),
        mode=channel.Mode.OFFLINE_FIXED_MOCK,
    )
    assert decoded.stage == "semantic_invalid"
    assert decoded.value is None


def test_fixed_mock_two_hop_chain_is_typed_and_ambient_key_independent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", SENTINEL_A)
    first = channel.run_offline_fixed_mock_chain()
    monkeypatch.setenv("OPENAI_API_KEY", SENTINEL_B)
    second = channel.run_offline_fixed_mock_chain()
    assert first == second
    assert first["schema_version"] == channel.OFFLINE_SUPERVISOR_SCHEMA_VERSION
    assert first["worker_frame_stage"] == "valid"
    assert first["fixture"] == channel.fixed_worker_fixture()
    activity = first["activity"]
    assert activity["worker_launch_attempt_count"] == 1
    assert activity["worker_process_return_count"] == 1
    assert activity["worker_valid_frame_count"] == 1
    assert activity["activity_accounting_complete"] is True
    assert activity["unknown_process_activity_possible"] is False
    rendered = json.dumps(first, sort_keys=True)
    assert SENTINEL_A not in rendered
    assert SENTINEL_B not in rendered


def test_fixed_process_environment_has_no_credential_or_proxy_inputs() -> None:
    environment = channel.FIXED_PROCESS_ENVIRONMENT
    assert "OPENAI_API_KEY" not in environment
    assert "PYTHONHOME" not in environment
    assert "PYTHONPATH" not in environment
    assert all("proxy" not in key.lower() for key in environment)
    assert channel.CHILD_FLAGS == ("-I", "-E", "-s", "-B")


def test_qualification_runs_no_diagnostic_or_mock_and_creates_no_runtime_evidence(
    contract: successor.EnvelopeDiagnosticActivationContract,
) -> None:
    authority = successor.QualificationAuthority()
    assert authority.offline_fixed_mock_or_live_process_launch_count == 0
    assert authority.state_approval_attempt_action_or_terminal_created is False
    assert authority.docker_dotenv_sdk_network_or_provider_observation_count == 0
    assert authority.credential_value_or_metadata_observation_count == 0
    assert authority.external_mutation_count == 0
    assert authority.execution_authorized is False
    assert contract.runtime.qualification_diagnostic_or_mock_process_launch_limit == 0
    assert contract.runtime.local_git_provenance_subprocesses_may_run is True

    source = (REPOSITORY / successor.RUNTIME_PATH).read_text(encoding="utf-8")
    qualification_section = source[source.index("def _build_qualification") :]
    assert "run_offline_fixed_mock_chain" not in qualification_section
    assert "OPENAI_API_KEY" not in qualification_section
    assert "run_sanitized_sdk_diagnostic" not in qualification_section


def test_runtime_tamper_fails_contract_identity_and_there_is_no_launch_path(
    contract: successor.EnvelopeDiagnosticActivationContract,
) -> None:
    forged = contract.model_copy(update={"content_hash": "sha256:" + "0" * 64})
    with pytest.raises(ValidationError):
        successor.EnvelopeDiagnosticActivationContract.model_validate(
            forged.model_dump(mode="json")
        )
    assert not hasattr(successor, "run_offline_fixed_mock_chain")
    assert not hasattr(successor, "run_parent_preflight_injected")


def test_checked_in_source_qualification_when_present() -> None:
    if not (REPOSITORY / successor.QUALIFICATION_PATH).exists():
        pytest.skip("qualification is created only after the exact source commit")
    summary = successor.validate_source_qualification(repository=REPOSITORY)
    assert summary["offline_fixed_mock_or_live_process_launch_count"] == 0
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["execution_authorized"] is False
