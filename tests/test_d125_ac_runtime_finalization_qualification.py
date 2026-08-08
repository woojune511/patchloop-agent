from __future__ import annotations

import copy
import json
import os
import socket
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from patchloop.agent import model as agent_model
from patchloop.agent import runner as agent_runner
from patchloop.evals import d122_ac_fixed_bundle_qualification as d122
from patchloop.evals import d124_ac_settlement_reconciliation_correction as d124
from patchloop.evals import d125_ac_runtime_finalization_qualification as d125
from patchloop.evals import runner as eval_runner
from patchloop.util import canonical_json, sha256_bytes, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]
PRODUCTION_OUTPUT_PATH = d125.OUTPUT_PATH


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"D-125 crossed forbidden {label} boundary")

    return fail


def _remove_exact(path: Path) -> None:
    if d122._is_linklike(path):
        path.unlink()
    elif path.exists() and path.is_dir():
        path.rmdir()
    elif path.exists():
        path.unlink()


@pytest.fixture
def isolated_output(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Path, Path]]:
    token = uuid.uuid4().hex
    relative = PRODUCTION_OUTPUT_PATH.parent / f".pytest-d125-{token}.json"
    output = REPOSITORY / relative
    target = output.with_suffix(".target")
    assert output.parent.resolve(strict=True).is_relative_to(REPOSITORY.resolve(strict=True))
    assert not output.exists()
    assert not target.exists()
    monkeypatch.setattr(d125, "OUTPUT_PATH", relative)
    monkeypatch.setattr(subprocess, "run", _forbidden("subprocess"))
    monkeypatch.setattr(subprocess, "Popen", _forbidden("subprocess"))
    monkeypatch.setattr(os, "system", _forbidden("subprocess"))
    monkeypatch.setattr(socket, "socket", _forbidden("socket/network"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("socket/network"))
    monkeypatch.setattr(agent_model, "OpenAI", _forbidden("provider"))
    monkeypatch.setattr(agent_runner.AgentRunner, "start", _forbidden("agent run"))
    monkeypatch.setattr(eval_runner, "preflight_suite", _forbidden("preflight"))
    monkeypatch.setattr(eval_runner, "evaluate_suite", _forbidden("evaluator"))
    monkeypatch.setattr(
        eval_runner,
        "recover_ac_campaign_finalization",
        _forbidden("runtime recovery"),
    )
    monkeypatch.setattr(d124, "_validate_payload", _forbidden("D-124 current-source replay"))
    monkeypatch.setattr(d124, "_source_state", _forbidden("D-124 current-source replay"))
    try:
        yield output, target
    finally:
        _remove_exact(output)
        _remove_exact(target)


@pytest.fixture
def isolated_sealed_output(
    isolated_output: tuple[Path, Path],
) -> tuple[Path, Path]:
    output, target = isolated_output
    production = REPOSITORY / PRODUCTION_OUTPUT_PATH
    output.write_bytes(production.read_bytes())
    return output, target


def test_exact_d124_seal_and_compact_inherited_contract_are_bound(
    isolated_output: tuple[Path, Path],
) -> None:
    _output, _target = isolated_output
    source = d125._source_state(REPOSITORY)
    assert source["predecessor_binding"] == {
        "milestone": "D-124",
        "path": d125.D124_PATH.as_posix(),
        "gate_id": d125.D124_GATE_ID,
        "semantic_body_hash": d125.D124_BODY_SHA256,
        "file_bytes": d125.D124_FILE_BYTES,
        "file_sha256": d125.D124_FILE_SHA256,
        "status": d125.D124_STATUS,
        "recorded_at": d125.D124_RECORDED_AT,
        "validation_mode": "sealed-historical",
        "artifact_mutated": False,
        "execution_or_result_existed": False,
    }
    assert source["inherited_contract_binding"] == {
        "experiment_id": d125.EXPERIMENT_ID,
        "correction_contract_hash": d125.D124_CORRECTION_CONTRACT_SHA256,
        "inherited_ac_contract_hash": d125.D124_INHERITED_AC_CONTRACT_SHA256,
        "suite_hash": d125.D124_SUITE_HASH,
        "schedule_hash": d125.D124_SCHEDULE_HASH,
        "cost_control_hash": d125.D124_COST_CONTROL_HASH,
        "completion_contract_hash": d125.D124_COMPLETION_CONTRACT_HASH,
    }


def test_runtime_contract_states_only_the_two_honest_offline_properties() -> None:
    wrapper = d125._runtime_finalization_contract()
    contract = wrapper["contract"]
    assert wrapper["contract_hash"] == sha256_text(canonical_json(contract))
    row = contract["row_start_consumption"]
    assert row["repository_local_at_most_once_paid_boundary_verified"] is True
    assert row["cross_store_atomicity_claimed"] is False
    assert row["run_started_to_sqlite_crash_gap_policy"] == "fail-closed-no-resume"
    assert row["crash_gap_liveness_or_recovery_verified"] is False
    assert row["whole_root_rollback_protection_verified"] is False
    assert row["whole_root_rollback_excluded_from_qualified_scope"] is True
    assert row["global_or_cross_clone_exclusion_claimed"] is False
    finalization = contract["campaign_finalization_recovery"]
    assert finalization["unique_same_directory_temp_written_fsynced_and_stable_verified"]
    assert finalization["deterministic_prepared_path_published_by_hard_link_no_replace"]
    assert finalization["final_output_published_from_prepared_by_hard_link_no_replace"]
    assert finalization["mocked_process_fault_boundary_finalization_recovery_verified"]
    assert finalization["actual_process_kill_executed"] is False
    assert finalization["torn_write_or_power_loss_durability_verified"] is False
    assert finalization["noncooperative_path_swap_protection_verified"] is False
    assert finalization["noncooperative_path_swap_excluded_from_qualified_scope"] is True
    assert finalization["recovery_reruns_row_agent_provider_or_evaluator"] is False


def test_external_test_attestations_are_exact_and_non_additive() -> None:
    attestation = d125._external_test_attestation()
    assert attestation["attestation_kind"] == "self-attested-external-to-builder"
    assert attestation["builder_executed_tests"] is False

    row = attestation["row_start_consumption"]
    assert row["selections_are_node_disjoint"] is True
    assert row["distinct_collected_tests_passed"] == 147
    assert sum(selection["passed"] for selection in row["selections"]) == 147
    assert [selection["collected"] for selection in row["selections"]] == [12, 51, 44, 40]
    assert row["focused_reruns_counted_as_additional_evidence"] is False

    finalization = attestation["campaign_finalization"]
    assert finalization["component_selections_are_node_disjoint"] is True
    assert finalization["distinct_collected_tests_passed"] == 136
    counted = [
        selection
        for selection in finalization["selections"]
        if selection["counted_in_distinct_total"]
    ]
    assert sum(selection["passed"] for selection in counted) == 136
    combined = finalization["selections"][-1]
    assert combined["label"] == "combined-union-rerun"
    assert combined["passed"] == combined["collected"] == 136
    assert combined["counted_in_distinct_total"] is False
    assert finalization["combined_union_is_overlapping_corroboration"] is True
    assert attestation["row_and_finalization_totals_are_non_additive_due_to_overlap"]
    assert attestation["unique_total_across_both_attestations_claimed"] is False


def test_exact_historical_copy_is_canonical_idempotent_and_authority_closed(
    isolated_sealed_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_sealed_output
    raw = output.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    first = d125.validate_d125_source_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )
    second = d125.validate_d125_source_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )
    assert first == second
    assert output.read_bytes() == raw == d125._canonical_bytes(payload)
    assert first == {
        "status": d125.STATUS,
        "gate_id": d125.SEALED_HISTORICAL_GATE_ID,
        "semantic_body_hash": d125.SEALED_HISTORICAL_BODY_SHA256,
        "file_bytes": d125.SEALED_HISTORICAL_FILE_BYTES,
        "file_sha256": d125.SEALED_HISTORICAL_FILE_SHA256,
        "execution_authorization_candidate_ready": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
    }
    assert payload["gate_id"] == d125.SEALED_HISTORICAL_GATE_ID
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(payload["semantic_body"]))
    body = payload["semantic_body"]
    assert body["status"] == d125.STATUS
    assert body["blocked_prerequisites"] == list(d125.BLOCKED_PREREQUISITES)
    authority = body["authority"]
    assert authority["repository_local_at_most_once_paid_boundary_consumption_verified"]
    assert authority["cross_store_atomic_row_start_consumption_verified"] is False
    assert authority["mocked_process_fault_boundary_finalization_recovery_verified"]
    assert authority["actual_process_kill_recovery_verified"] is False
    assert authority["torn_write_or_power_loss_recovery_verified"] is False
    assert authority["execution_authorization_candidate_ready"] is False
    assert authority["approved_execution_hash"] is None
    assert authority["reservation_executed"] is False
    assert authority["completion_result_present"] is False
    assert [
        authority["provider_calls_made"],
        authority["evaluator_calls_made"],
        authority["docker_calls_made"],
        authority["agent_runs_made"],
        authority["retrieval_calls_made"],
        authority["added_model_cost_usd"],
    ] == [0, 0, 0, 0, 0, 0]


def test_d124_constant_drift_creates_no_output(
    isolated_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, _target = isolated_output
    monkeypatch.setattr(d124, "SEALED_HISTORICAL_FILE_SHA256", "sha256:" + "0" * 64)
    with pytest.raises(d125.D125QualificationError, match="independently pinned"):
        d125.run_d125_offline_source_gate(repository=REPOSITORY)
    assert not output.exists()


def test_pending_reviewed_identity_fails_closed_before_output(
    isolated_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, _target = isolated_output
    monkeypatch.setattr(d125, "REVIEWED_EVAL_RUNNER_FILE_SHA256", None)
    with pytest.raises(d125.D125QualificationError, match="identities are pending"):
        d125.run_d125_offline_source_gate(repository=REPOSITORY)
    assert not output.exists()


@pytest.mark.parametrize("drift_path", d125.REVIEWED_RUNTIME_PATHS)
def test_reviewed_runtime_source_drift_creates_no_output(
    isolated_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    drift_path: Path,
) -> None:
    output, _target = isolated_output
    stable_read = d125._stable_read

    def drift(root: Path, relative: Path) -> bytes:
        content = stable_read(root, relative)
        return content + b"\n" if relative == drift_path else content

    monkeypatch.setattr(d125, "_stable_read", drift)
    with pytest.raises(d125.D125QualificationError, match="source identities differ"):
        d125.run_d125_offline_source_gate(repository=REPOSITORY)
    assert not output.exists()


def test_post_successor_current_source_rejects_while_sealed_copy_remains_valid(
    isolated_sealed_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_sealed_output
    original = output.read_bytes()
    with pytest.raises(d125.D125QualificationError, match="source identities differ"):
        d125.validate_d125_source_gate(
            repository=REPOSITORY,
            mode="current-source",
        )
    result = d125.validate_d125_source_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )
    assert result["gate_id"] == d125.SEALED_HISTORICAL_GATE_ID
    assert output.read_bytes() == original


def test_partial_file_and_directory_collisions_are_not_repaired(
    isolated_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_output
    for collision in (b"", b'{"schema_version":', b"unapproved"):
        output.write_bytes(collision)
        with pytest.raises((d125.D125QualificationError, d122.D122QualificationError)):
            d125.run_d125_offline_source_gate(repository=REPOSITORY)
        assert output.read_bytes() == collision
        output.unlink()
    output.mkdir()
    with pytest.raises((d125.D125QualificationError, d122.D122QualificationError)):
        d125.run_d125_offline_source_gate(repository=REPOSITORY)
    assert output.is_dir()
    output.rmdir()


def test_output_symlink_is_rejected_without_touching_target(
    isolated_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, target = isolated_output
    target.write_bytes(b"D-125 target")
    try:
        output.symlink_to(target)
    except OSError:
        original = d122._is_linklike
        with monkeypatch.context() as context:
            context.setattr(d122, "_is_linklike", lambda path: path == output or original(path))
            with pytest.raises(d125.D125QualificationError, match="output path is unsafe"):
                d125.run_d125_offline_source_gate(repository=REPOSITORY)
        assert not output.exists()
    else:
        with pytest.raises(d125.D125QualificationError, match="output path is unsafe"):
            d125.run_d125_offline_source_gate(repository=REPOSITORY)
        assert output.is_symlink()
    assert target.read_bytes() == b"D-125 target"


@pytest.mark.parametrize(
    "tamper",
    ["unknown", "authority", "property", "chronology", "blocker"],
)
def test_fully_rehashed_tamper_or_backward_chronology_fails(
    isolated_sealed_output: tuple[Path, Path],
    tamper: str,
) -> None:
    output, _target = isolated_sealed_output
    original = output.read_bytes()
    payload = json.loads(original.decode("utf-8"))
    body = copy.deepcopy(payload["semantic_body"])
    if tamper == "unknown":
        body["authority"]["unapproved"] = False
    elif tamper == "authority":
        body["authority"]["provider_execution_authorized"] = True
    elif tamper == "property":
        contract = body["runtime_finalization_contract"]["contract"]
        contract["row_start_consumption"]["cross_store_atomicity_claimed"] = True
    elif tamper == "chronology":
        body["recorded_at"] = "2000-01-01T00:00:00Z"
    else:
        body["blocked_prerequisites"] = body["blocked_prerequisites"][1:]
    rewritten = d125._envelope(body)
    tampered = d125._canonical_bytes(rewritten)
    output.write_bytes(tampered)
    assert sha256_bytes(tampered) != sha256_bytes(original)
    with pytest.raises(d125.D125QualificationError, match="sealed|hash|size"):
        d125.validate_d125_source_gate(
            repository=REPOSITORY,
            mode="sealed-historical",
        )
    assert output.read_bytes() == tampered


def test_production_d125_sealed_historical_bytes_remain_valid() -> None:
    production = REPOSITORY / PRODUCTION_OUTPUT_PATH
    before = production.read_bytes()
    with pytest.raises(d125.D125QualificationError, match="source identities differ"):
        d125.validate_d125_source_gate(
            repository=REPOSITORY,
            mode="current-source",
        )
    result = d125.validate_d125_source_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )
    raw = production.read_bytes()
    assert result == {
        "status": d125.STATUS,
        "gate_id": d125.SEALED_HISTORICAL_GATE_ID,
        "semantic_body_hash": d125.SEALED_HISTORICAL_BODY_SHA256,
        "file_bytes": d125.SEALED_HISTORICAL_FILE_BYTES,
        "file_sha256": d125.SEALED_HISTORICAL_FILE_SHA256,
        "execution_authorization_candidate_ready": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
    }
    assert len(raw) == d125.SEALED_HISTORICAL_FILE_BYTES
    assert sha256_bytes(raw) == d125.SEALED_HISTORICAL_FILE_SHA256
    assert raw == before
