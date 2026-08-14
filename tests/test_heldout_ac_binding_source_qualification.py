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

from patchloop import task_loader
from patchloop.agent import model as agent_model
from patchloop.errors import ContractError
from patchloop.evals import heldout_ac_binding_source_qualification as source_q
from patchloop.evals import runner as generic_runner
from patchloop.sandbox import runner as sandbox_runner
from patchloop.util import sha256_bytes, sha256_json
from patchloop.verifier import core as verifier_core

ROOT = Path(__file__).resolve().parents[1]
SEALED_R5_PATH = ROOT / source_q.OUTPUT_PATH


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"binding source qualification crossed {label}")

    return fail


@pytest.fixture
def isolated_output(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    relative = source_q.OUTPUT_PATH.parent / f".pytest-binding-{uuid.uuid4().hex}.json"
    output = ROOT / relative
    monkeypatch.setattr(source_q, "OUTPUT_PATH", relative)
    monkeypatch.setattr(subprocess, "run", _forbidden("process boundary"))
    monkeypatch.setattr(subprocess, "Popen", _forbidden("process boundary"))
    monkeypatch.setattr(os, "system", _forbidden("process boundary"))
    monkeypatch.setattr(socket, "socket", _forbidden("network boundary"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("network boundary"))
    monkeypatch.setattr(task_loader, "load_task_package", _forbidden("task package boundary"))
    monkeypatch.setattr(agent_model, "OpenAI", _forbidden("provider boundary"))
    monkeypatch.setattr(generic_runner, "preflight_suite", _forbidden("preflight boundary"))
    monkeypatch.setattr(generic_runner, "evaluate_suite", _forbidden("evaluation boundary"))
    monkeypatch.setattr(verifier_core.EvaluationEngine, "evaluate", _forbidden("evaluator"))
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "available", _forbidden("Docker"))
    try:
        yield output
    finally:
        if output.exists() or output.is_symlink():
            output.unlink()


def test_r5_identity_is_source_only_and_materialization_closed() -> None:
    assert source_q.SCHEMA_VERSION == "heldout-ac-binding-adapter-source-qualification-v3"
    assert source_q.QUALIFICATION_ID.endswith("20260814-r5")
    assert source_q.STATUS.endswith("RUNTIME_MATERIALIZATION_CLOSED")
    assert source_q.NEXT_GATE == (
        "authorized-task-package-materialization-and-fresh-pricing-before-candidate"
    )


def test_historical_builder_fails_closed_without_creating_a_successor(
    isolated_output: Path,
) -> None:
    with pytest.raises(ContractError, match="contract source qualification has drifted"):
        source_q.run_heldout_ac_binding_source_qualification(repository=ROOT)
    assert not isolated_output.exists()


def test_sealed_r5_artifact_bytes_and_closed_authority_are_preserved() -> None:
    raw = SEALED_R5_PATH.read_bytes()
    payload = json.loads(raw)

    assert len(raw) == 4_759
    assert sha256_bytes(raw) == (
        "sha256:809981c460c9d28e0dbc17e179260e20eb48641489973cac669b6de72282094c"
    )
    assert payload["content_hash"] == (
        "sha256:c1dc0d53f5df3cbd8c37cdc453fea738a803177add7a49d6e267b186192d5f59"
    )
    assert payload["predecessor"] == {
        "path": source_q.R4_PATH.as_posix(),
        "file_bytes": source_q.R4_FILE_BYTES,
        "file_sha256": source_q.R4_FILE_SHA256,
        "source_qualification_hash": source_q.R4_CONTENT_HASH,
        "original_status": source_q.STATUS,
        "disposition": "superseded-by-final-format-conformance",
        "current_source_replay_valid": False,
        "r3_source_qualification_hash": source_q.R3_CONTENT_HASH,
        "r2_source_qualification_hash": source_q.R2_CONTENT_HASH,
    }
    projection = payload["projection"]
    assert projection["metadata_task_count"] == 12
    assert projection["r2_contract_source_replay_valid"] is True
    assert projection["task_evaluator_materializer_source_present"] is True
    assert projection["persisted_adapter_source_present"] is True
    assert projection["invokes_evaluator_v2_receipt_revalidation"] is True
    assert projection["invokes_read_only_trace_recomputation"] is True
    assert projection["task_evaluator_contract_materializations"] == 0
    assert projection["authenticated_persisted_rows"] == 0
    assert all(
        value is False or value == 0 or value == 0.0 for value in payload["authority"].values()
    )


def test_gate_never_opens_a_task_path(
    isolated_output: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[str] = []
    original_read_bytes = Path.read_bytes
    original_read_text = Path.read_text

    def read_bytes(path: Path, *args, **kwargs):
        opened.append(path.resolve().as_posix())
        return original_read_bytes(path, *args, **kwargs)

    def read_text(path: Path, *args, **kwargs):
        opened.append(path.resolve().as_posix())
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setattr(Path, "read_text", read_text)
    with pytest.raises(ContractError, match="contract source qualification has drifted"):
        source_q.run_heldout_ac_binding_source_qualification(repository=ROOT)

    assert opened
    assert all("/tasks/" not in path for path in opened)


def test_equal_but_wrong_scalar_type_fails_closed() -> None:
    payload = json.loads(SEALED_R5_PATH.read_bytes())
    payload["projection"]["metadata_task_count"] = 12.0
    payload["content_hash"] = sha256_json(
        {key: value for key, value in payload.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError):
        source_q.HeldoutACBindingSourceQualification.model_validate(payload)


def test_invalid_existing_artifact_is_never_overwritten(isolated_output: Path) -> None:
    isolated_output.parent.mkdir(parents=True, exist_ok=True)
    isolated_output.write_bytes(b"not-json")
    before = isolated_output.read_bytes()

    with pytest.raises(source_q.HeldoutACBindingSourceQualificationError):
        source_q.run_heldout_ac_binding_source_qualification(repository=ROOT)
    assert isolated_output.read_bytes() == before
