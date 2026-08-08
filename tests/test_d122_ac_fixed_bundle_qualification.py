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
from patchloop.evals import runner as eval_runner
from patchloop.memory import retrieval
from patchloop.sandbox import runner as sandbox_runner
from patchloop.util import canonical_json, sha256_bytes, sha256_text
from patchloop.verifier import core as verifier_core

REPOSITORY = Path(__file__).resolve().parents[1]
PRODUCTION_OUTPUT_PATH = d122.OUTPUT_PATH


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"D-122 crossed forbidden {label} boundary")

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
    """Redirect the append-only artifact to one exact repository-local test path."""

    token = uuid.uuid4().hex
    relative = PRODUCTION_OUTPUT_PATH.parent / f".pytest-d122-{token}.json"
    output = REPOSITORY / relative
    symlink_target = output.with_suffix(".target")
    assert relative != PRODUCTION_OUTPUT_PATH
    assert output.parent.resolve(strict=True).is_relative_to(REPOSITORY.resolve(strict=True))
    assert not output.exists()
    assert not d122._is_linklike(output)
    assert not symlink_target.exists()
    monkeypatch.setattr(d122, "OUTPUT_PATH", relative)

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
    monkeypatch.setattr(
        agent_model.OpenAIResponsesAdapter,
        "next_turn",
        provider_forbidden,
    )
    monkeypatch.setattr(agent_runner.AgentRunner, "start", agent_forbidden)
    monkeypatch.setattr(agent_runner.AgentRunner, "resume", agent_forbidden)
    monkeypatch.setattr(eval_runner, "preflight_suite", evaluator_forbidden)
    monkeypatch.setattr(eval_runner, "evaluate_suite", evaluator_forbidden)
    monkeypatch.setattr(eval_runner, "_docker_image_state", docker_forbidden)
    monkeypatch.setattr(eval_runner, "latest_frozen_index", retrieval_forbidden)
    monkeypatch.setattr(verifier_core.EvaluationEngine, "evaluate", evaluator_forbidden)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "cli_path", docker_forbidden)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "available", docker_forbidden)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "image_identity", docker_forbidden)
    monkeypatch.setattr(
        sandbox_runner.DockerSandbox,
        "probe_image_identity",
        docker_forbidden,
    )
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "run_check", docker_forbidden)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "run_probe", docker_forbidden)
    monkeypatch.setattr(retrieval, "retrieve_memory", retrieval_forbidden)
    monkeypatch.setattr(retrieval, "_query_embedding", retrieval_forbidden)

    try:
        yield output, symlink_target
    finally:
        _remove_exact(output)
        _remove_exact(symlink_target)


def _payload(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    assert isinstance(value, dict)
    return value


def _build(path: Path) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    result = d122.run_d122_offline_source_gate(repository=REPOSITORY)
    raw = path.read_bytes()
    return result, _payload(path), raw


def test_canonical_build_validate_and_rerun_are_exact_append_only(
    isolated_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_output
    first, payload, raw = _build(output)
    first_mtime = output.stat().st_mtime_ns
    validated = d122.validate_d122_source_gate(repository=REPOSITORY)
    replay = d122.run_d122_offline_source_gate(repository=REPOSITORY)

    assert first == validated == replay
    assert output.read_bytes() == raw
    assert output.stat().st_mtime_ns == first_mtime
    assert raw == (canonical_json(payload) + "\n").encode("utf-8")
    assert set(payload) == set(d122.ROOT_KEYS)
    body = payload["semantic_body"]
    assert set(body) == set(d122.BODY_KEYS)
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(body))
    assert payload["gate_id"] == (f"d122_{payload['semantic_body_hash'].removeprefix('sha256:')}")
    assert first == {
        "status": d122.STATUS,
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_authorization_candidate_ready": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
    }

    schedule = body["schedule_binding"]
    assert set(schedule) == {
        "schedule_hash",
        "expected_run_count",
        "ordered_rows",
        "counterbalanced_task_pair_order",
        "automatic_retry_or_replacement_allowed",
    }
    assert schedule["expected_run_count"] == 4
    assert schedule["counterbalanced_task_pair_order"] is True
    assert schedule["automatic_retry_or_replacement_allowed"] is False
    assert [
        (row["order"], row["task_id"], row["condition"], row["repetition"])
        for row in schedule["ordered_rows"]
    ] == [
        (1, "moto-query-scanned-count", "no_memory", 1),
        (2, "moto-query-scanned-count", "structured", 1),
        (3, "babel-strict-grouped-decimal-trailing-zeroes", "structured", 1),
        (4, "babel-strict-grouped-decimal-trailing-zeroes", "no_memory", 1),
    ]
    row_ids = [row["schedule_row_id"] for row in schedule["ordered_rows"]]
    assert len(set(row_ids)) == 4
    assert all(value.startswith("sha256:") and len(value) == 71 for value in row_ids)

    for relative, binding in (
        (d122.PLAN_PATH, body["plan_binding"]),
        (d122.SUITE_PATH, body["suite_binding"]),
    ):
        content = (REPOSITORY / relative).read_bytes()
        assert binding["path"] == relative.as_posix()
        assert binding["file_bytes"] == len(content)
        assert binding["file_sha256"] == sha256_bytes(content)
    implementation_files = [
        {
            "path": relative.as_posix(),
            "file_bytes": len((REPOSITORY / relative).read_bytes()),
            "file_sha256": sha256_bytes((REPOSITORY / relative).read_bytes()),
        }
        for relative in d122.IMPLEMENTATION_PATHS
    ]
    assert body["implementation_integrity"] == {
        "files": implementation_files,
        "file_count": len(implementation_files),
        "fingerprint": sha256_text(canonical_json(implementation_files)),
    }


def test_status_authority_and_cost_blockers_remain_exactly_closed(
    isolated_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_output
    _result, payload, _raw = _build(output)
    body = payload["semantic_body"]

    assert body["status"] == "D122_OFFLINE_SOURCE_QUALIFIED_EXECUTION_CANDIDATE_BLOCKED"
    assert body["suite_binding"]["live_cost_approved"] is False
    assert body["suite_binding"]["approved_execution_hash"] is None
    assert body["suite_binding"]["pricing_verified_at"] is None
    assert body["blocked_prerequisites"] == list(d122.BLOCKED_PREREQUISITES)
    assert body["resource_and_cost_boundary"] == {
        "schema_version": "ac-fixed-bundle-full-schedule-reserve-v1",
        "accounting_scope": "campaign-local",
        "accounting_basis": "usage-derived-standard-list-price",
        "scheduled_run_count": 4,
        "per_run_worst_rate_reserve_usd": 13.6125,
        "full_schedule_worst_rate_reserve_usd": 54.45,
        "hard_cap_usd": 55.0,
        "hard_cap_slack_usd": 0.55,
        "money_scale": "nano-usd",
        "per_run_reserve_nanos": 13_612_500_000,
        "full_schedule_reserve_nanos": 54_450_000_000,
        "hard_cap_nanos": 55_000_000_000,
        "reservation_mode": "row-bound-full-schedule-up-front",
        "initial_reservation_boundary": "before-first-provider-call",
        "row_reserve_count": 4,
        "cost_censoring_allowed": False,
        "not_started_due_to_cost_allowed": False,
        "automatic_retry_or_replacement_allowed": False,
        "settlement_basis": "durable-token-derived-standard-list-price",
        "live_resume_policy": "disabled",
        "completion_guaranteed": False,
        "invoice_or_free_tier_claimed": False,
        "calculation": "(3000000 + 25000) * 4.5 / 1000000",
        "slack_nanos": 550_000_000,
        "historical_formula_provenance_only": True,
        "historical_d108_bundle_delta_tokens": 702,
        "historical_d108_delta_is_not_per_request_live_evidence": True,
        "fresh_official_pricing_verified": False,
        "full_schedule_reservation_enforced": False,
        "hard_cap_enforced": False,
        "cost_settlement_evidence_present": False,
    }
    assert body["authority"] == {
        "offline_source_qualification_materialized": True,
        "exact_four_row_suite_materialized": True,
        "fixed_bundle_delivery_implementation_present": True,
        "structured_trace_qualifier_implementation_present": True,
        "execution_candidate_prepared": False,
        "execution_authorization_candidate_ready": False,
        "exact_execution_hash_created": False,
        "approved_execution_hash": None,
        "provider_execution_authorized": False,
        "evaluator_execution_authorized": False,
        "runtime_memory_injection_authorized": False,
        "fixed_bundle_delivery_live_authorized": False,
        "retrieval_authorized": False,
        "docker_preflight_authorized": False,
        "score_policy_mutation_authorized": False,
        "automatic_retry_replacement_or_resume_authorized": False,
        "core_or_heldout_campaign_authorized": False,
        "analysis_or_memory_benefit_claim_authorized": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
        "agent_runs_made": 0,
        "retrieval_calls_made": 0,
        "added_model_cost_usd": 0,
    }
    qualification = body["offline_qualification"]
    assert qualification["live_preflight_has_unconditional_cost_control_blocker"] is True
    assert qualification["execution_candidate_prepared"] is False
    assert qualification["execution_authorization_candidate_ready"] is False
    assert body["next_gate"] == {
        "action": (
            "implement-exact-four-row-cost-and-completion-gates-then-"
            "prepare-clean-no-call-execution-authorization-candidate"
        ),
        "requires_fresh_official_pricing": True,
        "requires_clean_committed_source": True,
        "requires_separately_authorized_no_call_docker_sdk_preflight": True,
        "requires_separate_exact_candidate_execution_hash_and_cap_approval": True,
        "proposed_hard_cap_usd": 55.0,
        "does_not_authorize_execution": True,
    }


def test_builder_and_validator_make_no_external_or_runtime_calls(
    isolated_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_output
    result, payload, _raw = _build(output)
    validated = d122.validate_d122_source_gate(repository=REPOSITORY)

    assert validated == result
    authority = payload["semantic_body"]["authority"]
    assert [
        authority[key]
        for key in (
            "provider_calls_made",
            "evaluator_calls_made",
            "docker_calls_made",
            "agent_runs_made",
            "retrieval_calls_made",
            "added_model_cost_usd",
        )
    ] == [0, 0, 0, 0, 0, 0]


@pytest.mark.parametrize("state_name", ["_source_state", "_implementation_state"])
def test_current_source_or_implementation_drift_invalidates_existing_gate(
    isolated_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    state_name: str,
) -> None:
    output, _target = isolated_output
    _result, _payload_value, original_bytes = _build(output)
    state_builder = getattr(d122, state_name)
    drifted = copy.deepcopy(state_builder(REPOSITORY))
    if state_name == "_source_state":
        drifted["plan_binding"]["file_sha256"] = "sha256:" + "0" * 64
    else:
        drifted["files"][0]["file_sha256"] = "sha256:" + "0" * 64
        drifted["fingerprint"] = sha256_text(canonical_json(drifted["files"]))
    monkeypatch.setattr(d122, state_name, lambda _root: copy.deepcopy(drifted))

    with pytest.raises(d122.D122QualificationError, match="full expected payload differs"):
        d122.validate_d122_source_gate(repository=REPOSITORY)
    with pytest.raises(d122.D122QualificationError, match="full expected payload differs"):
        d122.run_d122_offline_source_gate(repository=REPOSITORY)
    assert output.read_bytes() == original_bytes


def test_checked_in_gate_validates_as_exact_sealed_historical_bytes() -> None:
    result = d122.validate_d122_source_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )

    assert result == {
        "status": d122.STATUS,
        "gate_id": d122.SEALED_HISTORICAL_GATE_ID,
        "semantic_body_hash": d122.SEALED_HISTORICAL_BODY_SHA256,
        "file_bytes": d122.SEALED_HISTORICAL_FILE_BYTES,
        "file_sha256": d122.SEALED_HISTORICAL_FILE_SHA256,
        "execution_authorization_candidate_ready": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
    }


def test_partial_file_and_directory_collisions_are_never_repaired(
    isolated_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_output
    for collision in (b"", b'{"schema_version":', b"unapproved-collision"):
        output.write_bytes(collision)
        with pytest.raises(d122.D122QualificationError):
            d122.run_d122_offline_source_gate(repository=REPOSITORY)
        assert output.read_bytes() == collision
        output.unlink()

    output.mkdir()
    with pytest.raises(d122.D122QualificationError, match="not a regular file"):
        d122.run_d122_offline_source_gate(repository=REPOSITORY)
    assert output.is_dir()
    output.rmdir()


def test_output_symlink_is_rejected_without_touching_target(
    isolated_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, target = isolated_output
    target_bytes = b"D-122 symlink target must remain unchanged"
    target.write_bytes(target_bytes)

    def assert_rejected() -> None:
        for operation in (
            d122.run_d122_offline_source_gate,
            d122.validate_d122_source_gate,
        ):
            with pytest.raises(d122.D122QualificationError, match="link or reparse point"):
                operation(repository=REPOSITORY)

    try:
        output.symlink_to(target)
    except OSError:
        original_is_linklike = d122._is_linklike
        with monkeypatch.context() as link_guard:
            link_guard.setattr(
                d122,
                "_is_linklike",
                lambda path: path == output or original_is_linklike(path),
            )
            assert_rejected()
        assert not output.exists()
    else:
        assert_rejected()
        assert output.is_symlink()
    assert target.read_bytes() == target_bytes


def test_fully_rehashed_unknown_and_authority_tamper_fail_exact_rebuild(
    isolated_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_output
    _result, payload, original_bytes = _build(output)

    for tamper in ("unknown", "authority"):
        body = copy.deepcopy(payload["semantic_body"])
        if tamper == "unknown":
            body["authority"]["future_unapproved_authority"] = False
        else:
            body["authority"]["provider_execution_authorized"] = True
        rewritten = d122._envelope(body)
        tampered_bytes = d122._canonical_bytes(rewritten)
        output.write_bytes(tampered_bytes)
        assert rewritten["semantic_body_hash"] == sha256_text(canonical_json(body))
        assert rewritten["gate_id"] == (
            f"d122_{rewritten['semantic_body_hash'].removeprefix('sha256:')}"
        )

        with pytest.raises(d122.D122QualificationError, match="full expected payload differs"):
            d122.validate_d122_source_gate(repository=REPOSITORY)
        with pytest.raises(d122.D122QualificationError, match="full expected payload differs"):
            d122.run_d122_offline_source_gate(repository=REPOSITORY)
        assert output.read_bytes() == tampered_bytes
        output.write_bytes(original_bytes)
