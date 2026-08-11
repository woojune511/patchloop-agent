from __future__ import annotations

import json
import os
import socket
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent import model as agent_model
from patchloop.agent import runner as agent_runner
from patchloop.evals import evaluator_v2_source_qualification as source_q
from patchloop.evals import runner as eval_runner
from patchloop.memory import retrieval
from patchloop.sandbox import runner as sandbox_runner
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json
from patchloop.verifier import core as verifier_core

REPOSITORY = Path(__file__).resolve().parents[1]


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"source qualification crossed forbidden {label} boundary")

    return fail


@pytest.fixture
def isolated_output(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Path]:
    relative = source_q.OUTPUT_PATH.parent / f".pytest-evaluator-v2-{uuid.uuid4().hex}.json"
    output = REPOSITORY / relative
    assert not output.exists()
    monkeypatch.setattr(source_q, "OUTPUT_PATH", relative)

    process_forbidden = _forbidden("process")
    network_forbidden = _forbidden("network")
    provider_forbidden = _forbidden("provider")
    evaluator_forbidden = _forbidden("evaluator")
    docker_forbidden = _forbidden("Docker")
    agent_forbidden = _forbidden("agent")
    retrieval_forbidden = _forbidden("retrieval")

    monkeypatch.setattr(subprocess, "run", process_forbidden)
    monkeypatch.setattr(subprocess, "Popen", process_forbidden)
    monkeypatch.setattr(os, "system", process_forbidden)
    monkeypatch.setattr(socket, "socket", network_forbidden)
    monkeypatch.setattr(socket, "create_connection", network_forbidden)
    monkeypatch.setattr(agent_model, "OpenAI", provider_forbidden)
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
    monkeypatch.setattr(verifier_core.EvaluationEngine, "evaluate", evaluator_forbidden)
    monkeypatch.setattr(
        verifier_core.EvaluationEngine,
        "evaluate_v2_candidate",
        evaluator_forbidden,
    )
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "available", docker_forbidden)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "image_identity", docker_forbidden)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "run_check", docker_forbidden)
    monkeypatch.setattr(retrieval, "retrieve_memory", retrieval_forbidden)
    monkeypatch.setattr(retrieval, "_query_embedding", retrieval_forbidden)

    try:
        yield output
    finally:
        if output.exists() or output.is_symlink():
            output.unlink()


def _build(output: Path) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    summary = source_q.run_evaluator_v2_ac_source_qualification(repository=REPOSITORY)
    raw = output.read_bytes()
    payload = json.loads(raw)
    assert isinstance(payload, dict)
    return summary, payload, raw


def test_build_validate_and_replay_are_append_only_and_offline(
    isolated_output: Path,
) -> None:
    first, payload, raw = _build(isolated_output)
    first_mtime = isolated_output.stat().st_mtime_ns
    validated = source_q.validate_evaluator_v2_ac_source_qualification(repository=REPOSITORY)
    replay = source_q.run_evaluator_v2_ac_source_qualification(repository=REPOSITORY)

    assert first == validated == replay
    assert isolated_output.read_bytes() == raw
    assert isolated_output.stat().st_mtime_ns == first_mtime
    assert first == {
        "status": source_q.STATUS,
        "qualification_id": source_q.QUALIFICATION_ID,
        "source_qualification_hash": payload["content_hash"],
        "evaluator_source_hash": payload["evaluator_source_hash"],
        "successor_suite_hash": payload["successor_suite"]["content_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_authorized": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
        "agent_runs_made": 0,
    }
    assert payload["authority"] == {
        **source_q._EXPECTED_AUTHORITY,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
        "agent_runs_made": 0,
        "retrieval_calls_made": 0,
        "added_model_cost_usd": 0,
    }


def test_successor_suite_is_new_and_preserves_exact_ac_treatment(
    isolated_output: Path,
) -> None:
    _summary, payload, _raw = _build(isolated_output)
    successor = payload["successor_suite"]
    assert successor["suite_id"] == source_q.QUALIFICATION_ID
    assert successor["content_hash"] != payload["base_suite_hash"]
    assert successor["base_suite_hash"] == payload["base_suite_hash"]
    assert successor["evaluator_source_hash"] == payload["evaluator_source_hash"]
    assert [
        (row["order"], row["task_id"], row["condition"], row["repetition"])
        for row in successor["schedule"]
    ] == [
        (1, "moto-query-scanned-count", "no_memory", 1),
        (2, "moto-query-scanned-count", "structured", 1),
        (3, "babel-strict-grouped-decimal-trailing-zeroes", "structured", 1),
        (4, "babel-strict-grouped-decimal-trailing-zeroes", "no_memory", 1),
    ]
    assert successor["runtime_tuple_hash"] == source_q._qualified_runtime_tuple_hash()
    assert successor["treatment_hash"] == sha256_json(source_q._EXPECTED_TREATMENT)
    assert payload["fixed_bundle_sha256"] == source_q.FIXED_BUNDLE_SHA256


def test_source_and_validation_inventories_are_exact_current_bytes(
    isolated_output: Path,
) -> None:
    _summary, payload, _raw = _build(isolated_output)
    for key, expected_paths in (
        ("evaluator_source_files", source_q.SOURCE_PATHS),
        ("validation_files", source_q.VALIDATION_PATHS),
    ):
        bindings = payload[key]
        assert [item["path"] for item in bindings] == [item.as_posix() for item in expected_paths]
        for item in bindings:
            content = (REPOSITORY / item["path"]).read_bytes()
            assert item["file_bytes"] == len(content)
            assert item["file_sha256"] == sha256_bytes(content)


def test_private_ids_and_reference_hashes_do_not_persist(
    isolated_output: Path,
) -> None:
    _summary, _payload, raw = _build(isolated_output)
    for task_path in source_q.TASK_PATHS:
        package = load_task_package(REPOSITORY / task_path)
        private_markers = source_q.evaluator_v2_task_private_markers(package)
        assert all(marker not in raw for marker in private_markers)


def test_authority_factory_requires_exact_task_and_run_secret_boundary(
    isolated_output: Path,
) -> None:
    summary, _payload, _raw = _build(isolated_output)
    task = REPOSITORY / source_q.TASK_PATHS[0]
    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="run-bound secret marker",
    ):
        source_q.load_evaluator_v2_ac_qualification_authority(
            task,
            repository=REPOSITORY,
        )

    secret = b"sk-run-bound-test-marker-not-a-real-key"
    live_shape = source_q.load_evaluator_v2_ac_qualification_authority(
        task,
        runtime_secret_markers=(secret,),
        repository=REPOSITORY,
    )
    assert live_shape.suite_hash == summary["successor_suite_hash"]
    assert live_shape.source_qualification_hash == summary["source_qualification_hash"]
    assert live_shape.runtime_tuple_hash == source_q._qualified_runtime_tuple_hash()
    assert live_shape.runtime.evaluator_source_hash == summary["evaluator_source_hash"]
    assert live_shape.runtime.safety_contract.task_id == "moto-query-scanned-count"
    assert secret in live_shape.runtime.private_markers
    assert secret not in isolated_output.read_bytes()


def test_authority_factory_rejects_unqualified_task_and_bad_markers(
    isolated_output: Path,
) -> None:
    _build(isolated_output)
    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="outside the qualified successor suite",
    ):
        source_q.load_evaluator_v2_ac_qualification_authority(
            REPOSITORY / "tasks/smoke/csv-quoted-newline",
            runtime_secret_markers=(b"test-secret-marker",),
            repository=REPOSITORY,
        )
    task = REPOSITORY / source_q.TASK_PATHS[0]
    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="duplicated",
    ):
        source_q.load_evaluator_v2_ac_qualification_authority(
            task,
            runtime_secret_markers=(b"duplicate-secret", b"duplicate-secret"),
            repository=REPOSITORY,
        )


def test_current_source_drift_fails_closed(
    isolated_output: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _build(isolated_output)
    original = source_q._file_binding

    def drifted(root: Path, relative: Path) -> source_q.QualificationFileBinding:
        value = original(root, relative)
        if relative == source_q.SOURCE_PATHS[0]:
            return source_q.QualificationFileBinding(
                path=value.path,
                file_bytes=value.file_bytes,
                file_sha256="sha256:" + "0" * 64,
            )
        return value

    monkeypatch.setattr(source_q, "_file_binding", drifted)
    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="has drifted",
    ):
        source_q.validate_evaluator_v2_ac_source_qualification(repository=REPOSITORY)


def test_plan_or_artifact_tamper_fails_closed(
    isolated_output: Path,
) -> None:
    _summary, payload, _raw = _build(isolated_output)
    payload["authority"]["provider_or_evaluator_execution_authorized"] = True
    isolated_output.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        source_q.EvaluatorV2SourceQualificationError,
        match="artifact is invalid|bytes are not canonical",
    ):
        source_q.validate_evaluator_v2_ac_source_qualification(repository=REPOSITORY)


def test_content_hash_tamper_is_rejected_after_model_copy_roundtrip(
    isolated_output: Path,
) -> None:
    _summary, payload, _raw = _build(isolated_output)
    parsed = source_q.EvaluatorV2ACSourceQualification.model_validate(payload)
    tampered = parsed.model_copy(update={"content_hash": "sha256:" + "0" * 64})
    with pytest.raises(ValidationError):
        source_q.EvaluatorV2ACSourceQualification.model_validate(tampered.model_dump(mode="json"))
