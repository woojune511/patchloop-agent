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
from patchloop.evals import d124_ac_settlement_reconciliation_correction as d124
from patchloop.evals import runner as eval_runner
from patchloop.util import canonical_json, sha256_bytes, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]
PRODUCTION_OUTPUT_PATH = d124.OUTPUT_PATH


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"D-124 crossed forbidden {label} boundary")

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
    relative = PRODUCTION_OUTPUT_PATH.parent / f".pytest-d124-{token}.json"
    output = REPOSITORY / relative
    target = output.with_suffix(".target")
    assert output.parent.resolve(strict=True).is_relative_to(REPOSITORY.resolve(strict=True))
    assert not output.exists()
    assert not target.exists()
    monkeypatch.setattr(d124, "OUTPUT_PATH", relative)
    monkeypatch.setattr(subprocess, "run", _forbidden("subprocess"))
    monkeypatch.setattr(subprocess, "Popen", _forbidden("subprocess"))
    monkeypatch.setattr(os, "system", _forbidden("subprocess"))
    monkeypatch.setattr(socket, "socket", _forbidden("socket/network"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("socket/network"))
    monkeypatch.setattr(agent_model, "OpenAI", _forbidden("provider"))
    monkeypatch.setattr(agent_runner.AgentRunner, "start", _forbidden("agent run"))
    monkeypatch.setattr(eval_runner, "preflight_suite", _forbidden("preflight"))
    monkeypatch.setattr(eval_runner, "evaluate_suite", _forbidden("evaluator"))
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


def test_exact_d123_seal_and_corrected_source_are_bound() -> None:
    source = d124._source_state(REPOSITORY)
    predecessor = source["predecessor_binding"]
    assert predecessor["gate_id"] == d124.D123_GATE_ID
    assert predecessor["semantic_body_hash"] == d124.D123_BODY_SHA256
    assert predecessor["file_sha256"] == d124.D123_FILE_SHA256
    assert predecessor["file_bytes"] == d124.D123_FILE_BYTES
    assert predecessor["validation_mode"] == "sealed-historical"
    assert predecessor["artifact_mutated"] is False
    assert predecessor["historical_implementation"]["runner"] == {
        "path": "patchloop/evals/runner.py",
        "file_bytes": d124.D123_RUNNER_FILE_BYTES,
        "file_sha256": d124.D123_RUNNER_FILE_SHA256,
    }
    assert source["inherited_ac_contract"]["schedule_binding"]["expected_run_count"] == 4
    correction = source["correction_contract"]
    assert correction["builder_truth_table_probe"]["observed"] == {
        "exact-final-durable-state": True,
        "usage-projection-failed": False,
        "persisted-result-projection-failed": False,
        "durable-evidence-missing": False,
        "durable-hash-missing": False,
        "durable-hash-mismatch": False,
        "settlement-unavailable": False,
    }
    assert correction["d123_artifact_rewritten"] is False
    assert correction["runtime_failure_path_live_executed"] is False


def test_exact_historical_copy_is_canonical_idempotent_and_authority_closed(
    isolated_sealed_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_sealed_output
    raw = output.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    first = d124.validate_d124_correction_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )
    second = d124.validate_d124_correction_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )
    assert first == second
    assert output.read_bytes() == raw == d124._canonical_bytes(payload)
    assert payload["gate_id"] == (f"d124_{payload['semantic_body_hash'].removeprefix('sha256:')}")
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(payload["semantic_body"]))
    body = payload["semantic_body"]
    assert body["status"] == d124.STATUS
    assert body["blocked_prerequisites"] == list(d124.BLOCKED_PREREQUISITES)
    assert body["finding"]["disposition"] == "CONFIRMED_SOURCE_DEFECT_NO_LIVE_RESULT"
    assert body["offline_qualification"]["runtime_emitter_integration_corrected_prospectively"]
    authority = body["authority"]
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


def test_sealed_validation_does_not_replay_mutable_d123_constants(
    isolated_sealed_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, _target = isolated_sealed_output
    before = output.read_bytes()
    monkeypatch.setattr(d123, "SEALED_HISTORICAL_FILE_SHA256", "sha256:" + "0" * 64)
    result = d124.validate_d124_correction_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )
    assert result["gate_id"] == d124.SEALED_HISTORICAL_GATE_ID
    assert output.read_bytes() == before


@pytest.mark.parametrize(
    "drift_path",
    [
        Path("patchloop/evals/runner.py"),
        Path("tests/test_ac_fixed_bundle_cost_completion.py"),
    ],
)
def test_sealed_validation_does_not_replay_reviewed_source_identity(
    isolated_sealed_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    drift_path: Path,
) -> None:
    output, _target = isolated_sealed_output
    before = output.read_bytes()
    stable_read = d124._stable_read

    def drift(root: Path, relative: Path) -> bytes:
        content = stable_read(root, relative)
        return content + b"\n" if relative == drift_path else content

    monkeypatch.setattr(d124, "_stable_read", drift)
    result = d124.validate_d124_correction_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )
    assert result["gate_id"] == d124.SEALED_HISTORICAL_GATE_ID
    assert output.read_bytes() == before


def test_sealed_validation_does_not_replay_current_behavior_probe(
    isolated_sealed_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, _target = isolated_sealed_output
    before = output.read_bytes()
    monkeypatch.setattr(
        d124,
        "_terminal_cost_settlement_reconciliation_passed",
        lambda **_values: False,
    )
    result = d124.validate_d124_correction_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )
    assert result["gate_id"] == d124.SEALED_HISTORICAL_GATE_ID
    assert output.read_bytes() == before


def test_post_successor_current_source_rejects_while_sealed_copy_remains_valid(
    isolated_sealed_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_sealed_output
    original = output.read_bytes()
    with pytest.raises(d124.D124CorrectionError, match="source identities differ"):
        d124.validate_d124_correction_gate(
            repository=REPOSITORY,
            mode="current-source",
        )
    result = d124.validate_d124_correction_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )
    assert result["gate_id"] == d124.SEALED_HISTORICAL_GATE_ID
    assert output.read_bytes() == original


def test_partial_file_and_directory_collisions_are_not_repaired(
    isolated_output: tuple[Path, Path],
) -> None:
    output, _target = isolated_output
    for collision in (b"", b'{"schema_version":', b"unapproved"):
        output.write_bytes(collision)
        with pytest.raises((d124.D124CorrectionError, d122.D122QualificationError)):
            d124.validate_d124_correction_gate(
                repository=REPOSITORY,
                mode="sealed-historical",
            )
        assert output.read_bytes() == collision
        output.unlink()
    output.mkdir()
    with pytest.raises((d124.D124CorrectionError, d122.D122QualificationError)):
        d124.validate_d124_correction_gate(
            repository=REPOSITORY,
            mode="sealed-historical",
        )
    assert output.is_dir()
    output.rmdir()


def test_output_symlink_is_rejected_without_touching_target(
    isolated_output: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, target = isolated_output
    target.write_bytes(b"D-124 target")
    try:
        output.symlink_to(target)
    except OSError:
        original = d122._is_linklike
        with monkeypatch.context() as context:
            context.setattr(d122, "_is_linklike", lambda path: path == output or original(path))
            with pytest.raises(
                d124.D124CorrectionError,
                match="unsafe|cannot stably read",
            ):
                d124.validate_d124_correction_gate(
                    repository=REPOSITORY,
                    mode="sealed-historical",
                )
        assert not output.exists()
    else:
        with pytest.raises(
            d124.D124CorrectionError,
            match="unsafe|cannot stably read",
        ):
            d124.validate_d124_correction_gate(
                repository=REPOSITORY,
                mode="sealed-historical",
            )
        assert output.is_symlink()
    assert target.read_bytes() == b"D-124 target"


@pytest.mark.parametrize("tamper", ["unknown", "authority", "finding", "chronology"])
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
    elif tamper == "finding":
        body["finding"]["live_execution_or_cost_result_observed"] = True
    else:
        body["recorded_at"] = "2000-01-01T00:00:00Z"
    rewritten = d124._envelope(body)
    tampered = d124._canonical_bytes(rewritten)
    output.write_bytes(tampered)
    assert sha256_bytes(tampered) != sha256_bytes(original)
    with pytest.raises(d124.D124CorrectionError, match="sealed|hash|size"):
        d124.validate_d124_correction_gate(
            repository=REPOSITORY,
            mode="sealed-historical",
        )
    assert output.read_bytes() == tampered


def test_production_d124_sealed_historical_bytes_remain_valid() -> None:
    production = REPOSITORY / PRODUCTION_OUTPUT_PATH
    before = production.read_bytes()
    with pytest.raises(d124.D124CorrectionError, match="source identities differ"):
        d124.validate_d124_correction_gate(
            repository=REPOSITORY,
            mode="current-source",
        )
    result = d124.validate_d124_correction_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )
    raw = production.read_bytes()
    assert result == {
        "status": d124.STATUS,
        "gate_id": d124.SEALED_HISTORICAL_GATE_ID,
        "semantic_body_hash": d124.SEALED_HISTORICAL_BODY_SHA256,
        "file_bytes": d124.SEALED_HISTORICAL_FILE_BYTES,
        "file_sha256": d124.SEALED_HISTORICAL_FILE_SHA256,
        "execution_authorization_candidate_ready": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
    }
    assert len(raw) == d124.SEALED_HISTORICAL_FILE_BYTES
    assert sha256_bytes(raw) == d124.SEALED_HISTORICAL_FILE_SHA256
    assert raw == before
