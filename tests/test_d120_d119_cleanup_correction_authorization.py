from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from patchloop.memory import d120_d119_cleanup_correction_authorization as d120

REPOSITORY = Path(__file__).resolve().parents[1]


def _copy(relative: str | Path, destination: Path) -> None:
    source = REPOSITORY / relative
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _copy_candidate_repository(destination: Path) -> None:
    paths = {
        *(Path(spec["path"]) for spec in d120.D119_PARTIAL_SPECS),
        Path(d120.D119_JOURNAL_SPEC["path"]),
        *(Path(spec["path"]) for spec in d120.D119_IMPLEMENTATION_SPECS),
        *d120.D120_IMPLEMENTATION_PATHS,
    }
    for relative in sorted(paths, key=lambda value: value.as_posix()):
        _copy(relative, destination)


@pytest.fixture
def candidate_repository(tmp_path: Path) -> Path:
    _copy_candidate_repository(tmp_path)
    return tmp_path


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    assert isinstance(value, dict)
    return value


def _rewrite_envelope(
    path: Path,
    *,
    id_field: str,
    id_prefix: str,
    mutate: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    value = _json(path)
    mutate(value["semantic_body"])
    rewritten = d120._envelope(
        schema_version=value["schema_version"],
        id_field=id_field,
        id_prefix=id_prefix,
        body=value["semantic_body"],
    )
    path.write_bytes(d120._pretty_bytes(rewritten))
    return rewritten


def _d119_bound_paths() -> tuple[Path, ...]:
    return (
        *(Path(spec["path"]) for spec in d120.D119_PARTIAL_SPECS),
        Path(d120.D119_JOURNAL_SPEC["path"]),
        *(Path(spec["path"]) for spec in d120.D119_IMPLEMENTATION_SPECS),
    )


def test_exact_real_partial_d119_state_is_three_present_three_absent_and_consumed() -> None:
    context = d120._d119_partial_context(REPOSITORY)

    assert context["status"] == "PARTIAL_CONSUMED_FAILED"
    assert len(context["artifacts_present"]) == 2
    assert context["journal"]["record_count"] == 4
    assert len(context["artifacts_present"]) + 1 == 3
    assert context["journal"]["events"] == [
        "ExecutionClaimed",
        "ImageIdentityVerified",
        "IsolationSessionStarted",
        "ExecutionFailed",
    ]
    assert context["artifacts_absent"] == list(d120.D119_ABSENT_OUTPUTS)
    assert len(context["artifacts_absent"]) == 3
    assert all(not (REPOSITORY / relative).exists() for relative in context["artifacts_absent"])
    assert context["durable_completed_session_count"] == 0
    assert context["sealed_probe_outcome_count"] == 0
    assert context["probe_outcome"] == "UNSEALED_UNKNOWN"
    assert context["same_d119_retry_resume_or_repair_allowed"] is False


def test_in_memory_candidate_keeps_authority_closed_and_unknown_boundary() -> None:
    context = d120._d119_partial_context(REPOSITORY)
    implementation = d120._d120_implementation_state(REPOSITORY)
    timestamp = "2026-08-07T13:30:00Z"
    preflight, candidate, gate = d120._build_expected(
        context=context,
        implementation=implementation,
        preflight_recorded_at=timestamp,
        candidate_recorded_at=timestamp,
        gate_recorded_at=timestamp,
    )

    authority = d120._authority()
    assert preflight["semantic_body"]["authority"] == authority
    assert candidate["semantic_body"]["authority"] == authority
    assert gate["semantic_body"]["authority"] == authority
    assert authority["partial_failure_sealed"] is True
    assert authority["cleanup_failure_diagnosis_recorded"] is True
    assert authority["root_cause_source_consistent_and_self_attested"] is True
    assert authority["root_cause_portably_proved"] is False
    assert authority["cleanup_correction_candidate_ready"] is True
    assert authority["exact_candidate_user_approval_received"] is False
    assert authority["d119_mutation_authorized"] is False
    assert authority["d119_retry_resume_or_repair_authorized"] is False
    assert authority["successor_implementation_authorized"] is False
    assert authority["successor_execution_authorization_candidate_preparation_authorized"] is False
    assert authority["fresh_successor_run_authorized"] is False
    assert authority["successor_run_count"] == 0
    assert authority["opaque_source_read_count"] == 0
    assert authority["docker_or_network_call_count_during_candidate_build_self_attested"] == 0
    assert candidate["semantic_body"]["failure_status"] == "PARTIAL_CONSUMED_FAILED"
    assert candidate["semantic_body"]["probe_outcome"] == "UNSEALED_UNKNOWN"
    assert gate["semantic_body"]["qualification"] == {
        "partial_failure_exactly_bound": True,
        "cleanup_failure_diagnosis_source_consistent_and_self_attested": True,
        "cleanup_root_cause_portably_proved": False,
        "first_probe_outcome": "UNSEALED_UNKNOWN",
        "durable_completed_session_count": 0,
        "d121_implementation_and_execution_candidate_plan_ready": True,
        "successor_execution_ready": False,
    }


def test_temp_build_is_append_only_idempotent_and_does_not_mutate_d119(
    candidate_repository: Path,
) -> None:
    before = {
        relative: (candidate_repository / relative).read_bytes() for relative in _d119_bound_paths()
    }
    absent_before = {
        relative: (candidate_repository / relative).exists()
        for relative in d120.D119_ABSENT_OUTPUTS
    }

    result = d120.run_d120_cleanup_correction_candidate(repository=candidate_repository)
    output_bytes = {
        key: (candidate_repository / relative).read_bytes()
        for key, relative in d120.OUTPUT_PATHS.items()
    }

    assert result["status"] == "D119_PARTIAL_FAILURE_SEALED_D120_CANDIDATE_PENDING_APPROVAL"
    assert result["partial_failure_status"] == "PARTIAL_CONSUMED_FAILED"
    assert result["probe_outcome"] == "UNSEALED_UNKNOWN"
    assert result["cleanup_correction_candidate_ready"] is True
    assert result["exact_candidate_user_approval_received"] is False
    assert result["successor_execution_authorization_candidate_preparation_authorized"] is False
    assert result["fresh_successor_run_authorized"] is False
    assert all((candidate_repository / path).is_file() for path in d120.OUTPUT_PATHS.values())
    assert before == {
        relative: (candidate_repository / relative).read_bytes() for relative in _d119_bound_paths()
    }
    assert absent_before == {
        relative: (candidate_repository / relative).exists()
        for relative in d120.D119_ABSENT_OUTPUTS
    }

    replay = d120.run_d120_cleanup_correction_candidate(repository=candidate_repository)
    assert replay == result
    assert output_bytes == {
        key: (candidate_repository / relative).read_bytes()
        for key, relative in d120.OUTPUT_PATHS.items()
    }


def test_candidate_build_uses_no_docker_subprocess_socket_or_opaque_source(
    candidate_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened_opaque_paths: list[Path] = []
    original_open = Path.open

    def guarded_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        resolved = path.resolve(strict=False)
        if ".patchloop" in resolved.parts and "external-evidence" in resolved.parts:
            opened_opaque_paths.append(resolved)
            raise AssertionError(f"D-120 opened opaque source: {resolved}")
        return original_open(path, *args, **kwargs)

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("D-120 invoked an execution or network boundary")

    monkeypatch.setattr(Path, "open", guarded_open)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(os, "system", forbidden)

    result = d120.run_d120_cleanup_correction_candidate(repository=candidate_repository)

    assert result["status"] == "D119_PARTIAL_FAILURE_SEALED_D120_CANDIDATE_PENDING_APPROVAL"
    assert opened_opaque_paths == []


def test_fully_rehashed_d119_partial_input_tamper_fails_exact_binding(
    candidate_repository: Path,
) -> None:
    approval_spec = d120.D119_PARTIAL_SPECS[0]
    approval_path = candidate_repository / approval_spec["path"]
    value = _json(approval_path)
    prefix = str(value[approval_spec["id_field"]])[:-64]
    _rewrite_envelope(
        approval_path,
        id_field=approval_spec["id_field"],
        id_prefix=prefix,
        mutate=lambda body: body.update(fully_rehashed_unknown_claim=False),
    )

    with pytest.raises(
        d120.D120AuthorizationError,
        match="D-119 partial artifact bytes differ",
    ):
        d120._d119_partial_context(candidate_repository)


def test_fully_rehashed_d119_journal_tamper_fails_exact_binding(
    candidate_repository: Path,
) -> None:
    journal_path = candidate_repository / d120.D119_JOURNAL_SPEC["path"]
    rows = [json.loads(line) for line in journal_path.read_bytes().splitlines()]
    rows[-1]["event"] = "ExecutionPassed"
    previous = "sha256:" + "0" * 64
    encoded = []
    for row in rows:
        row["previous_record_hash"] = previous
        body = {key: value for key, value in row.items() if key != "record_hash"}
        row["record_hash"] = d120.sha256_bytes(d120._canonical_bytes(body))
        previous = row["record_hash"]
        encoded.append(d120._canonical_bytes(row) + b"\n")
    journal_path.write_bytes(b"".join(encoded))

    with pytest.raises(d120.D120AuthorizationError, match="journal SHA differs"):
        d120._d119_partial_context(candidate_repository)


def test_fully_rehashed_candidate_and_gate_binding_tamper_fails_rebuild(
    candidate_repository: Path,
) -> None:
    d120.run_d120_cleanup_correction_candidate(repository=candidate_repository)
    candidate_path = candidate_repository / d120.OUTPUT_PATHS["candidate"]
    candidate = _rewrite_envelope(
        candidate_path,
        id_field="candidate_id",
        id_prefix="d120cleanupcandidate_",
        mutate=lambda body: body.update(fully_rehashed_unknown_claim=False),
    )
    candidate_content = d120._pretty_bytes(candidate)
    candidate_binding = d120._binding(
        d120.OUTPUT_PATHS["candidate"],
        candidate_content,
        candidate_id=candidate["candidate_id"],
        semantic_body_hash=candidate["semantic_body_hash"],
    )
    gate_path = candidate_repository / d120.OUTPUT_PATHS["source_gate"]
    _rewrite_envelope(
        gate_path,
        id_field="gate_id",
        id_prefix="d120_",
        mutate=lambda body: body.update(candidate=candidate_binding),
    )

    with pytest.raises(
        d120.D120AuthorizationError,
        match="D-120 candidate expected payload differs",
    ):
        d120.validate_d120_source_gate(repository=candidate_repository)


def test_fully_rehashed_source_gate_tamper_fails_rebuild(
    candidate_repository: Path,
) -> None:
    d120.run_d120_cleanup_correction_candidate(repository=candidate_repository)
    gate_path = candidate_repository / d120.OUTPUT_PATHS["source_gate"]
    _rewrite_envelope(
        gate_path,
        id_field="gate_id",
        id_prefix="d120_",
        mutate=lambda body: body["authority"].update(fresh_successor_run_authorized=True),
    )

    with pytest.raises(
        d120.D120AuthorizationError,
        match="D-120 source_gate expected payload differs",
    ):
        d120.validate_d120_source_gate(repository=candidate_repository)


def test_partial_d120_output_collision_is_not_repaired(
    candidate_repository: Path,
) -> None:
    conflict = candidate_repository / d120.OUTPUT_PATHS["candidate"]
    conflict.write_bytes(b"conflicting-candidate")

    with pytest.raises(
        d120.D120AuthorizationError,
        match="partial D-120 output state is not repairable",
    ):
        d120.run_d120_cleanup_correction_candidate(repository=candidate_repository)

    assert conflict.read_bytes() == b"conflicting-candidate"
    assert not (candidate_repository / d120.OUTPUT_PATHS["preflight"]).exists()
    assert not (candidate_repository / d120.OUTPUT_PATHS["source_gate"]).exists()


def test_future_d121_is_fresh_not_retry_and_has_exact_cleanup_inventory_contract() -> None:
    action = d120._future_action()
    relationship = action["relationship_to_d119"]
    execution = action["prospective_execution_contract"]
    cleanup = action["cleanup_observation_contract"]

    assert relationship == {
        "fresh_successor_run_planned": True,
        "d119_retry": False,
        "d119_resume": False,
        "d119_repair": False,
        "d119_partial_artifacts_and_implementation_immutable": True,
    }
    assert action["unchanged_d119_execution_tuple"] == d120.D119_EXECUTION_TUPLE
    assert action["execution_tuple_reverification_required_before_any_later_run"] is True
    assert action["unchanged_probe_image_profile_source_tuple"] is True
    assert action["planned_behavioral_changes"] == [
        "fresh-d121-container-label-and-name-namespace",
        "cleanup-no-row-presentation-normalization",
        "exact-id-and-label-wide-residual-inventories",
        "primary-probe-outcome-preserved-before-cleanup-validation",
        "expanded-cleanup-and-session-journal-events",
    ]
    assert action["new_paths"] == list(d120.D121_PREPARATION_PATHS)
    assert action["mutation_whitelist"] == list(d120.D121_PREPARATION_PATHS)
    assert action["prospective_run_output_paths_not_authorized"] == list(
        d120.D121_PROSPECTIVE_RUN_OUTPUT_PATHS
    )
    assert action["container_namespace"] == {
        "label": "io.patchloop.managed=d121-isolation-successor",
        "name_prefix": "patchloop-d121-",
        "disjoint_from_d119_and_d120": True,
        "disjointness_validated_by": "d120-declared-path-contract",
    }
    assert execution["fresh_run_count"] == 1
    assert execution["session_count"] == 2
    assert execution["both_exact_d119_sources_rerun"] is True
    assert execution["automatic_retry_count"] == 0
    assert execution["failure_remains_consumed"] is True
    assert cleanup["required_events_in_order"] == [
        "ProbeResultValidated",
        "ContainerRemovalVerified",
        "IsolationSessionCompleted",
    ]
    assert cleanup["accepted_no_row_stdout_exact_bytes"] == [
        {"presentation": "empty-bytes", "hex": ""},
        {"presentation": "empty-json-array", "hex": "5b5d"},
        {"presentation": "empty-json-array-lf", "hex": "5b5d0a"},
        {"presentation": "empty-json-array-crlf", "hex": "5b5d0d0a"},
    ]
    assert cleanup["arbitrary_stdout_forbidden"] is True
    assert cleanup["exact_id_rm_argv"] == [
        "<exact-pinned-docker-cli>",
        "rm",
        "--force",
        "<exact-container-id>",
    ]
    assert cleanup["post_remove_inspect_argv"] == [
        "<exact-pinned-docker-cli>",
        "inspect",
        "<exact-container-id>",
    ]
    assert cleanup["exact_id_inventory_argv"] == [
        "<exact-pinned-docker-cli>",
        "ps",
        "--all",
        "--quiet",
        "--no-trunc",
        "--filter",
        "id=<exact-container-id>",
    ]
    assert cleanup["successor_label_inventory_argv"] == [
        "<exact-pinned-docker-cli>",
        "ps",
        "--all",
        "--quiet",
        "--no-trunc",
        "--filter",
        "label=io.patchloop.managed=d121-isolation-successor",
    ]
    assert cleanup["observation_order_before_validation"] == [
        "remove-by-exact-id",
        "inspect-by-exact-id",
        "exact-id-inventory",
        "successor-label-inventory",
    ]
    assert cleanup["exact_id_inventory_must_be_empty"] is True
    assert cleanup["successor_label_inventory_must_be_empty"] is True
    assert cleanup["both_inventories_execute_even_if_presentation_validation_fails"] is True
    assert cleanup["raw_stderr_persisted"] is False
    assert cleanup["bounded_stderr_size_and_sha_persisted"] is True


def test_d120_approval_scope_stops_before_docker_source_read_or_d121_execution() -> None:
    context = d120._d119_partial_context(REPOSITORY)
    implementation = d120._d120_implementation_state(REPOSITORY)
    timestamp = "2026-08-07T13:30:00Z"
    _preflight, candidate, _gate = d120._build_expected(
        context=context,
        implementation=implementation,
        preflight_recorded_at=timestamp,
        candidate_recorded_at=timestamp,
        gate_recorded_at=timestamp,
    )
    action = candidate["semantic_body"]["proposed_action"]

    assert action["d120_approval_authorizes"] == {
        "d121_new_only_implementation": True,
        "offline_tests": True,
        "no_start_exact_docker_readiness_preflight": True,
        "execution_authorization_candidate_preparation": True,
    }
    assert action["d120_approval_does_not_authorize"] == {
        "docker_container_start": True,
        "opaque_source_read": True,
        "d121_successor_execution": True,
    }
    approval = candidate["semantic_body"]["approval_contract"]
    assert approval[
        "d120_approval_authorizes_only_d121_implementation_test_readiness_and_candidate"
    ]
    assert approval["d121_execution_requires_separate_exact_candidate_approval"]
    assert approval["approval_does_not_authorize_d119_mutation_or_retry"]
    assert candidate["semantic_body"]["authority"]["fresh_successor_run_authorized"] is False


def test_diagnosis_is_source_consistent_self_attested_and_not_portable_proof() -> None:
    diagnosis = d120._diagnosis_contract()

    assert diagnosis["proof_grade"] == (
        "source-consistent-self-attested-diagnosis-not-portable-proof"
    )
    assert diagnosis["d119_journal_evidence"] == {
        "failure_event": "ExecutionFailed",
        "recorded_error_type": "D119QualificationError",
        "cleanup_detail_recorded": False,
        "probe_result_recorded": False,
    }
    assert diagnosis["source_derived_finding"]["incorrect_additional_predicate"] == (
        "removed_inspect.stdout == b-empty"
    )
    operator = diagnosis["actual_execution_operator_observation"]
    assert operator["evidence_kind"] == "self-attested-operator-observation-not-journal-evidence"
    assert operator["raw_command_transcript_available"] is False
    assert operator["raw_removed_inspect_stdout_available"] is False
    assert operator["portable_replay_proof"] is False
    current = diagnosis["current_cli_observation"]
    assert current["evidence_kind"] == "current-read-only-self-attested-reproduction"
    assert current["original_d119_journal_contains_this_observation"] is False
    assert diagnosis["classification_boundary"]["first_probe_outcome"] == "UNSEALED_UNKNOWN"
    assert diagnosis["classification_boundary"]["first_probe_success_established"] is False


def test_declared_path_sets_and_d121_whitelist_are_exactly_disjoint() -> None:
    contract = d120._declared_path_contract(REPOSITORY)
    path_sets = contract["path_sets"]
    d119_paths = set(path_sets["d119_immutable_or_absent"])
    d120_paths = set(path_sets["d120_candidate"])
    d121_preparation_paths = set(path_sets["d121_preparation_new_only"])
    d121_run_output_paths = set(path_sets["d121_prospective_run_outputs_not_authorized"])

    assert contract["normalization"] == "unicode-nfkc-casefold-posix"
    assert contract["alternate_data_streams_forbidden"] is True
    assert contract["symlink_junction_or_reparse_traversal_forbidden"] is True
    assert contract["casefold_and_normalized_aliases_absent"] is True
    assert contract["existing_inode_aliases_absent"] is True
    assert contract["sets_pairwise_disjoint"] is True
    assert contract["all_d121_paths_absent_before_authorization"] is True
    assert d119_paths.isdisjoint(d120_paths)
    assert d119_paths.isdisjoint(d121_preparation_paths)
    assert d119_paths.isdisjoint(d121_run_output_paths)
    assert d120_paths.isdisjoint(d121_preparation_paths)
    assert d120_paths.isdisjoint(d121_run_output_paths)
    assert d121_preparation_paths.isdisjoint(d121_run_output_paths)
    assert d121_preparation_paths == set(d120.D121_PREPARATION_PATHS)
    assert d121_run_output_paths == set(d120.D121_PROSPECTIVE_RUN_OUTPUT_PATHS)
    assert contract["d121_preparation_mutation_whitelist"] == list(d120.D121_PREPARATION_PATHS)
    assert contract["d121_prospective_run_outputs_authorized"] is False


def test_preexisting_d121_path_fails_new_only_contract(candidate_repository: Path) -> None:
    unexpected = candidate_repository / d120.D121_PREPARATION_PATHS[0]
    unexpected.parent.mkdir(parents=True, exist_ok=True)
    unexpected.write_bytes(b"unapproved-d121-content")

    with pytest.raises(
        d120.D120AuthorizationError,
        match="path must be absent before D-121 authorization",
    ):
        d120._declared_path_contract(candidate_repository)


def test_exact_d119_execution_tuple_is_derived_from_bound_preflight() -> None:
    context = d120._d119_partial_context(REPOSITORY)

    assert context["d119_execution_tuple"] == d120.D119_EXECUTION_TUPLE
    assert context["d119_execution_tuple"]["ordered_sources"][0]["source_id"] == (
        "swe-bench-dev-f5351"
    )
    assert context["d119_execution_tuple"]["ordered_sources"][1]["source_id"] == (
        "swe-gym-train-26a6"
    )


def test_d120_artifact_chronology_cannot_predate_d119_failure() -> None:
    context = d120._d119_partial_context(REPOSITORY)
    implementation = d120._d120_implementation_state(REPOSITORY)
    before_failure = "2026-08-07T12:58:58Z"

    with pytest.raises(
        d120.D120AuthorizationError,
        match="preflight predates the sealed D-119 failure",
    ):
        d120._build_expected(
            context=context,
            implementation=implementation,
            preflight_recorded_at=before_failure,
            candidate_recorded_at=before_failure,
            gate_recorded_at=before_failure,
        )


def test_normalized_declared_path_alias_fails_closed(
    candidate_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    duplicate = d120.D120_IMPLEMENTATION_PATHS[0].as_posix().upper()
    monkeypatch.setattr(
        d120,
        "D121_PREPARATION_PATHS",
        (*d120.D121_PREPARATION_PATHS, duplicate),
    )

    with pytest.raises(d120.D120AuthorizationError, match="declared path aliases"):
        d120._declared_path_contract(candidate_repository)


def test_zero_call_claim_is_self_attested_and_not_materialization_instrumentation() -> None:
    authority = d120._authority()
    context = d120._d119_partial_context(REPOSITORY)
    implementation = d120._d120_implementation_state(REPOSITORY)
    preflight, _candidate, _gate = d120._build_expected(
        context=context,
        implementation=implementation,
        preflight_recorded_at="2026-08-07T13:30:00Z",
        candidate_recorded_at="2026-08-07T13:30:00Z",
        gate_recorded_at="2026-08-07T13:30:00Z",
    )
    boundary = preflight["semantic_body"]["evidence_boundary"]

    assert authority["docker_or_network_call_count_during_candidate_build_self_attested"] == 0
    assert authority["subprocess_or_socket_instrumented_during_materialization"] is False
    assert authority["focused_test_forbidden_boundary_guards_defined"] is True
    assert boundary["docker_or_network_invoked_self_attested"] is False
    assert boundary["materialization_subprocess_or_socket_instrumentation"] is False
    assert boundary["zero_call_claim_evidence_kind"] == (
        "source-path-static-audit-and-focused-test-guards"
    )
    assert boundary["root_cause_portable_proof_claimed"] is False
