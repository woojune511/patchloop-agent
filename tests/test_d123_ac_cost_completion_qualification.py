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
from patchloop.evals import d123_ac_cost_completion_qualification as d123
from patchloop.evals import runner as eval_runner
from patchloop.memory import retrieval
from patchloop.sandbox import runner as sandbox_runner
from patchloop.util import canonical_json, sha256_bytes, sha256_text
from patchloop.verifier import core as verifier_core

REPOSITORY = Path(__file__).resolve().parents[1]
PRODUCTION_OUTPUT_PATH = d123.OUTPUT_PATH


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"D-123 crossed forbidden {label} boundary")

    return fail


def _remove_exact(path: Path) -> None:
    if d122._is_linklike(path):
        path.unlink()
    elif path.exists() and path.is_dir():
        path.rmdir()
    elif path.exists():
        path.unlink()


@pytest.fixture
def isolated_output(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, Path]]:
    token = uuid.uuid4().hex
    relative = PRODUCTION_OUTPUT_PATH.parent / f".pytest-d123-{token}.json"
    output = REPOSITORY / relative
    symlink_target = output.with_suffix(".target")
    assert output.parent.resolve(strict=True).is_relative_to(REPOSITORY.resolve(strict=True))
    assert not output.exists()
    assert not symlink_target.exists()
    monkeypatch.setattr(d123, "OUTPUT_PATH", relative)

    process_forbidden = _forbidden("subprocess")
    socket_forbidden = _forbidden("socket/network")
    provider_forbidden = _forbidden("provider")
    evaluator_forbidden = _forbidden("evaluator")
    docker_forbidden = _forbidden("Docker")
    agent_forbidden = _forbidden("agent-run")
    retrieval_forbidden = _forbidden("retrieval")

    monkeypatch.setattr(subprocess, "run", process_forbidden)
    monkeypatch.setattr(subprocess, "Popen", process_forbidden)
    monkeypatch.setattr(os, "system", process_forbidden)
    monkeypatch.setattr(socket, "socket", socket_forbidden)
    monkeypatch.setattr(socket, "create_connection", socket_forbidden)
    monkeypatch.setattr(agent_model, "OpenAI", provider_forbidden)
    monkeypatch.setattr(
        agent_model.OpenAIResponsesAdapter,
        "count_input_tokens",
        provider_forbidden,
    )
    monkeypatch.setattr(
        agent_model.OpenAIResponsesAdapter,
        "execute_request",
        provider_forbidden,
    )
    monkeypatch.setattr(agent_runner.AgentRunner, "start", agent_forbidden)
    monkeypatch.setattr(agent_runner.AgentRunner, "resume", agent_forbidden)
    monkeypatch.setattr(eval_runner, "preflight_suite", evaluator_forbidden)
    monkeypatch.setattr(eval_runner, "evaluate_suite", evaluator_forbidden)
    monkeypatch.setattr(eval_runner, "_docker_image_state", docker_forbidden)
    monkeypatch.setattr(verifier_core.EvaluationEngine, "evaluate", evaluator_forbidden)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "available", docker_forbidden)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "run_check", docker_forbidden)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "run_probe", docker_forbidden)
    monkeypatch.setattr(retrieval, "retrieve_memory", retrieval_forbidden)
    monkeypatch.setattr(retrieval, "_query_embedding", retrieval_forbidden)

    try:
        yield output, symlink_target
    finally:
        _remove_exact(output)
        _remove_exact(symlink_target)


def _build(output: Path) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    result = d123.run_d123_offline_source_gate(repository=REPOSITORY)
    raw = output.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    return result, payload, raw


def test_production_d123_sealed_historical_bytes_remain_valid() -> None:
    result = d123.validate_d123_source_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )
    assert result == {
        "status": d123.STATUS,
        "gate_id": d123.SEALED_HISTORICAL_GATE_ID,
        "semantic_body_hash": d123.SEALED_HISTORICAL_BODY_SHA256,
        "file_bytes": d123.SEALED_HISTORICAL_FILE_BYTES,
        "file_sha256": d123.SEALED_HISTORICAL_FILE_SHA256,
        "execution_authorization_candidate_ready": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
    }


def test_exact_r2_source_cost_and_completion_contracts_are_bound() -> None:
    source = d123._source_state(REPOSITORY)

    assert source["predecessor_binding"] == {
        "milestone": "D-122",
        "path": d122.OUTPUT_PATH.as_posix(),
        "gate_id": d123.D122_GATE_ID,
        "semantic_body_hash": d123.D122_BODY_SHA256,
        "file_bytes": d123.D122_FILE_BYTES,
        "file_sha256": d123.D122_FILE_SHA256,
        "status": d123.D122_STATUS,
        "validation_mode": "sealed-historical",
        "historical_artifact_mutated": False,
        "r1_source_bytes": {
            "plan": {
                "path": d123.R1_PLAN_PATH.as_posix(),
                "file_bytes": d123.R1_PLAN_FILE_BYTES,
                "file_sha256": d123.R1_PLAN_FILE_SHA256,
                "sealed_suite_or_plan_hash": None,
            },
            "suite": {
                "path": d123.R1_SUITE_PATH.as_posix(),
                "file_bytes": d123.R1_SUITE_FILE_BYTES,
                "file_sha256": d123.R1_SUITE_FILE_SHA256,
                "sealed_suite_or_plan_hash": d123.R1_SUITE_HASH,
            },
            "match_d122_bindings": True,
        },
    }
    assert source["plan_binding"]["file_sha256"] == d123.PLAN_FILE_SHA256
    assert source["suite_binding"]["file_sha256"] == d123.SUITE_FILE_SHA256
    assert source["suite_binding"]["suite_hash"] == d123.SUITE_HASH
    assert source["schedule_binding"]["schedule_hash"] == d123.SCHEDULE_HASH
    assert tuple(
        row["schedule_row_id"] for row in source["schedule_binding"]["ordered_rows"]
    ) == d123.EXPECTED_SCHEDULE_IDS
    assert tuple(
        (row["task_id"], row["condition"])
        for row in source["schedule_binding"]["ordered_rows"]
    ) == d123.EXPECTED_TASK_CONDITIONS

    cost = source["cost_reservation_and_settlement_contract"]
    assert cost["policy"] == eval_runner.AC_FIXED_BUNDLE_COST_POLICY
    assert cost["control"]["content_hash"] == d123.COST_CONTROL_HASH
    assert cost["reservation_source_implemented"] is True
    assert cost["reservation_executed"] is False
    assert cost["journal_contract"]["reserve_fsynced_before_first_run_started"] is True
    assert cost["journal_contract"]["atomic_row_start_one_use_consumption_verified"] is False
    assert cost["journal_contract"]["noncooperative_path_swap_excluded"] is False
    assert cost["journal_contract"]["agent_runner_root_bound_to_approved_root"] is True
    assert (
        cost["journal_contract"][
            "exact_event_and_usage_descriptor_keysets_and_monotonic_chronology_verified"
        ]
        is True
    )
    assert (
        cost["journal_contract"]["prior_row_durable_usage_reloaded_and_repriced_before_paid_call"]
        is True
    )
    assert cost["journal_contract"]["settlement_unavailable_is_sealed_as_inconclusive"] is True
    assert (
        cost["journal_contract"][
            "final_result_and_campaign_completed_crash_collision_recovery_verified"
        ]
        is False
    )
    assert cost["usage_settlement_result_present"] is False

    completion = source["completion_gate_contract"]
    assert completion["completion_gate_source_implemented"] is True
    assert completion["contract"]["resolved_scrr_and_four_verdict_conjunction_required"] is True
    assert completion["completion_result_present"] is False
    assert completion["analysis_ready"] is False
    assert completion["contract"]["official_evaluator_required_runs"] == 4
    assert completion["contract"]["accepted_outcomes"] == ["resolved", "task_failure"]
    assert completion["contract"]["task_success_required"] is False


def test_builder_is_canonical_idempotent_and_zero_call(
    isolated_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_output
    result, payload, raw = _build(output)

    assert set(payload) == set(d123.ROOT_KEYS)
    assert set(payload["semantic_body"]) == set(d123.BODY_KEYS)
    assert raw == d123._canonical_bytes(payload)
    assert payload["semantic_body_hash"] == sha256_text(
        canonical_json(payload["semantic_body"])
    )
    assert payload["gate_id"] == (
        f"d123_{payload['semantic_body_hash'].removeprefix('sha256:')}"
    )
    assert result == d123.validate_d123_source_gate(repository=REPOSITORY)
    assert result == d123.run_d123_offline_source_gate(repository=REPOSITORY)
    assert output.read_bytes() == raw
    assert result["execution_authorization_candidate_ready"] is False
    assert [
        result["provider_calls_made"],
        result["evaluator_calls_made"],
        result["docker_calls_made"],
    ] == [0, 0, 0]


def test_materialized_authority_remains_exactly_offline_and_blocked(
    isolated_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_output
    _result, payload, _raw = _build(output)
    body = payload["semantic_body"]
    authority = body["authority"]

    assert body["status"] == d123.STATUS
    assert body["blocked_prerequisites"] == list(d123.BLOCKED_PREREQUISITES)
    assert authority["r2_cost_policy_source_implemented"] is True
    assert authority["r2_completion_gate_source_implemented"] is True
    assert authority["reservation_executed"] is False
    assert authority["completion_result_present"] is False
    assert authority["execution_candidate_prepared"] is False
    assert authority["execution_authorization_candidate_ready"] is False
    assert authority["approved_execution_hash"] is None
    assert authority["runtime_memory_injection_authorized"] is False
    assert authority["analysis_or_memory_benefit_claim_authorized"] is False
    assert [
        authority["provider_calls_made"],
        authority["evaluator_calls_made"],
        authority["docker_calls_made"],
        authority["agent_runs_made"],
        authority["retrieval_calls_made"],
        authority["added_model_cost_usd"],
    ] == [0, 0, 0, 0, 0, 0]


@pytest.mark.parametrize("state_name", ["_source_state", "_implementation_state"])
def test_current_source_or_implementation_drift_invalidates_gate(
    isolated_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    state_name: str,
) -> None:
    output, _target = isolated_output
    _result, _payload, original = _build(output)
    state_builder = getattr(d123, state_name)
    drifted = copy.deepcopy(state_builder(REPOSITORY))
    if state_name == "_source_state":
        drifted["suite_binding"]["file_sha256"] = "sha256:" + "0" * 64
    else:
        drifted["files"][0]["file_sha256"] = "sha256:" + "0" * 64
        drifted["fingerprint"] = sha256_text(canonical_json(drifted["files"]))
    monkeypatch.setattr(d123, state_name, lambda _root: copy.deepcopy(drifted))

    with pytest.raises(d123.D123QualificationError, match="full expected payload differs"):
        d123.validate_d123_source_gate(repository=REPOSITORY)
    assert output.read_bytes() == original


def test_d122_predecessor_drift_fails_before_d123_output(
    isolated_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, _target = isolated_output
    predecessor = d122.validate_d122_source_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )
    predecessor["file_sha256"] = "sha256:" + "0" * 64
    monkeypatch.setattr(
        d122,
        "validate_d122_source_gate",
        lambda **_kwargs: copy.deepcopy(predecessor),
    )

    with pytest.raises(d123.D123QualificationError, match="predecessor validation differs"):
        d123.run_d123_offline_source_gate(repository=REPOSITORY)
    assert not output.exists()


def test_d122_module_constant_drift_cannot_redefine_predecessor(
    isolated_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, _target = isolated_output
    monkeypatch.setattr(
        d122,
        "SEALED_HISTORICAL_FILE_SHA256",
        "sha256:" + "0" * 64,
    )

    with pytest.raises(
        d123.D123QualificationError,
        match="independently pinned predecessor",
    ):
        d123.run_d123_offline_source_gate(repository=REPOSITORY)
    assert not output.exists()


def test_current_r1_plan_bytes_must_still_match_the_d122_seal(
    isolated_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, _target = isolated_output
    stable_read = d123._stable_read

    def drift_r1(root: Path, relative: Path) -> bytes:
        content = stable_read(root, relative)
        return content + b"\n" if relative == d123.R1_PLAN_PATH else content

    monkeypatch.setattr(d123, "_stable_read", drift_r1)
    with pytest.raises(d123.D123QualificationError, match="current R1 plan differs"):
        d123.run_d123_offline_source_gate(repository=REPOSITORY)
    assert not output.exists()


def test_partial_file_and_directory_collisions_are_never_repaired(
    isolated_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_output
    for collision in (b"", b'{"schema_version":', b"unapproved-collision"):
        output.write_bytes(collision)
        with pytest.raises((d123.D123QualificationError, d122.D122QualificationError)):
            d123.run_d123_offline_source_gate(repository=REPOSITORY)
        assert output.read_bytes() == collision
        output.unlink()

    output.mkdir()
    with pytest.raises((d123.D123QualificationError, d122.D122QualificationError)):
        d123.run_d123_offline_source_gate(repository=REPOSITORY)
    assert output.is_dir()
    output.rmdir()


def test_output_symlink_is_rejected_without_touching_target(
    isolated_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, target = isolated_output
    target_bytes = b"D-123 symlink target must remain unchanged"
    target.write_bytes(target_bytes)

    def assert_rejected() -> None:
        with pytest.raises(d123.D123QualificationError, match="output path is unsafe"):
            d123.run_d123_offline_source_gate(repository=REPOSITORY)

    try:
        output.symlink_to(target)
    except OSError:
        original = d122._is_linklike
        with monkeypatch.context() as link_guard:
            link_guard.setattr(
                d122,
                "_is_linklike",
                lambda path: path == output or original(path),
            )
            assert_rejected()
        assert not output.exists()
    else:
        assert_rejected()
        assert output.is_symlink()
    assert target.read_bytes() == target_bytes


@pytest.mark.parametrize("tamper", ["unknown", "authority", "cost", "completion"])
def test_fully_rehashed_tamper_fails_full_expected_rebuild(
    isolated_output: tuple[Path, Path],
    tamper: str,
) -> None:
    output, _target = isolated_output
    _result, payload, original = _build(output)
    body = copy.deepcopy(payload["semantic_body"])
    if tamper == "unknown":
        body["authority"]["unapproved_future_authority"] = False
    elif tamper == "authority":
        body["authority"]["provider_execution_authorized"] = True
    elif tamper == "cost":
        body["cost_reservation_and_settlement_contract"]["reservation_executed"] = True
    else:
        body["completion_gate_contract"]["completion_result_present"] = True
    rewritten = d123._envelope(body)
    tampered = d123._canonical_bytes(rewritten)
    output.write_bytes(tampered)
    assert sha256_bytes(tampered) != sha256_bytes(original)

    with pytest.raises(d123.D123QualificationError, match="full expected payload differs"):
        d123.validate_d123_source_gate(repository=REPOSITORY)
    assert output.read_bytes() == tampered
