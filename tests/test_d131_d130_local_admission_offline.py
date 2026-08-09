from __future__ import annotations

import ast
import copy
import inspect
import json
import os
import shutil
import socket
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from patchloop.agent import model as agent_model
from patchloop.agent import runner as agent_runner
from patchloop.evals import d129_d128_terminal_successor_offline as d129_offline
from patchloop.evals import d130_d129_sequence_block_successor_offline as d130
from patchloop.evals import d131_d130_local_admission_offline as d131
from patchloop.evals import runner as eval_runner
from patchloop.memory import retrieval
from patchloop.sandbox import runner as sandbox_runner
from patchloop.util import canonical_json, sha256_bytes, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_PATH = Path("patchloop/evals/d131_d130_local_admission_offline.py")
SCRIPT_PATH = Path("scripts/build_d131_d130_local_admission_offline.py")
TEST_PATH = Path("tests/test_d131_d130_local_admission_offline.py")

D130_GATE_ID = "d130_443b0bc935ba6affd4a009dee780ae85ec1ecdc1e3ce62edcd566e12307c74db"
D130_GATE_BODY_SHA = "sha256:443b0bc935ba6affd4a009dee780ae85ec1ecdc1e3ce62edcd566e12307c74db"
D130_GATE_FILE_SHA = "sha256:6d580dd979dc77659efed07291264c4ea2a16dca02d9070a32928e9fbefff468"
D130_GATE_BYTES = 17_416
D130_GATE_RECORDED_AT = "2026-08-09T08:54:48.400693Z"
D130_SOURCE_COMMIT = "e6acdc23050e93f5324827a2dac1ed519fe35406"
D130_EVIDENCE_COMMIT = "d6079e55fd1c4745b05c2e345228b1a66d0a3df4"
D130_EVIDENCE_TREE = "564cc3719b6acaeb709a838d574b8b0f943c4b08"
D130_GATE_BLOB = "c20cf331c324d3716f9677e509a5fc0c05791b6b"

SOURCE_COMMIT = "a" * 40
SOURCE_TREE = "b" * 40
GATE_COMMIT = "c" * 40
GATE_TREE = "d" * 40
RECEIPT_COMMIT = "e" * 40
RECEIPT_TREE = "f" * 40
INTENT_COMMIT = "1" * 40
INTENT_TREE = "2" * 40

GATE_RECORDED_AT = "2026-08-09T09:00:00Z"
RECEIPT_RECORDED_AT = "2026-08-09T09:00:01Z"
INTENT_RECORDED_AT = "2026-08-09T09:00:02Z"
SECRET = "d131-local-admission-secret-must-not-be-read-or-rendered"


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"D-131 crossed forbidden {label} boundary")

    return fail


@pytest.fixture(autouse=True)
def zero_external_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", _forbidden("generic subprocess"))
    monkeypatch.setattr(subprocess, "Popen", _forbidden("subprocess"))
    monkeypatch.setattr(os, "system", _forbidden("shell"))
    monkeypatch.setattr(socket, "socket", _forbidden("socket/network"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("socket/network"))
    monkeypatch.setattr(agent_model, "OpenAI", _forbidden("provider"))
    monkeypatch.setattr(agent_runner.AgentRunner, "start", _forbidden("agent"))
    monkeypatch.setattr(agent_runner.AgentRunner, "resume", _forbidden("agent"))
    monkeypatch.setattr(eval_runner, "preflight_suite", _forbidden("execution hash"))
    monkeypatch.setattr(eval_runner, "evaluate_suite", _forbidden("evaluator"))
    monkeypatch.setattr(retrieval, "retrieve_memory", _forbidden("retrieval"))
    monkeypatch.setattr(retrieval, "_query_embedding", _forbidden("retrieval"))
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "available", _forbidden("Docker"))
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "run_check", _forbidden("Docker"))
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "run_probe", _forbidden("Docker"))


def _fake_git_observation() -> dict[str, Any]:
    return {
        "resolved_path": r"C:\Program Files\Git\mingw64\bin\git.exe",
        "file_name": "git.exe",
        "file_bytes": 4_422_544,
        "file_sha256": f"sha256:{'1' * 64}",
        "linklike": False,
        "version": "git version 2.54.0.windows.1",
        "actual_git_engine_invoked_directly": True,
        "repository_local_core_autocrlf": "false",
        "authenticated_or_vendor_signed_identity_claimed": False,
        "stable_during_observation": True,
        "minimal_secret_free_environment": True,
        "fsmonitor_disabled": True,
        "shell_used": False,
    }


@pytest.fixture
def repository(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, dict[str, Any]]]:
    root = REPOSITORY / f"tmp-d131-test-{uuid.uuid4().hex}"
    assert not root.exists()
    root.mkdir()
    required = {d131.D130_GATE_PATH, *d131.SOURCE_BINDING_PATHS}
    for relative in required:
        source = REPOSITORY / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())

    state: dict[str, Any] = {
        "head": SOURCE_COMMIT,
        "times": iter((GATE_RECORDED_AT, RECEIPT_RECORDED_AT, INTENT_RECORDED_AT)),
        "writes": [],
    }
    identities = {
        D130_EVIDENCE_COMMIT: {
            "commit": D130_EVIDENCE_COMMIT,
            "tree": D130_EVIDENCE_TREE,
            "parents": [D130_SOURCE_COMMIT],
        },
        SOURCE_COMMIT: {
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "parents": [D130_EVIDENCE_COMMIT],
        },
        GATE_COMMIT: {
            "commit": GATE_COMMIT,
            "tree": GATE_TREE,
            "parents": [SOURCE_COMMIT],
        },
        RECEIPT_COMMIT: {
            "commit": RECEIPT_COMMIT,
            "tree": RECEIPT_TREE,
            "parents": [GATE_COMMIT],
        },
        INTENT_COMMIT: {
            "commit": INTENT_COMMIT,
            "tree": INTENT_TREE,
            "parents": [RECEIPT_COMMIT],
        },
    }

    def commit_identity(_root: Path, commit: str) -> dict[str, Any]:
        return copy.deepcopy(identities[commit])

    def diff_rows(_root: Path, commit: str) -> list[dict[str, str]]:
        if commit == D130_EVIDENCE_COMMIT:
            return [
                {"status": "A", "path": d131.D130_GATE_PATH.as_posix()},
                *({"status": "M", "path": path.as_posix()} for path in d131.ACTIVE_DOC_PATHS),
            ]
        if commit == SOURCE_COMMIT:
            return [{"status": "A", "path": path.as_posix()} for path in d131.IMPLEMENTATION_PATHS]
        if commit == GATE_COMMIT:
            return [
                {"status": "A", "path": d131.OUTPUT_PATH.as_posix()},
                *({"status": "M", "path": path.as_posix()} for path in d131.ACTIVE_DOC_PATHS),
            ]
        if commit == RECEIPT_COMMIT:
            return [{"status": "A", "path": d131.RECEIPT_PATH.as_posix()}]
        if commit == INTENT_COMMIT:
            return [{"status": "A", "path": d131.INTENT_PATH.as_posix()}]
        raise AssertionError(f"unexpected commit diff: {commit}")

    def commit_blob(selected_root: Path, commit: str, relative: Path) -> tuple[str, bytes]:
        if commit == D130_EVIDENCE_COMMIT and relative == d131.D130_GATE_PATH:
            return D130_GATE_BLOB, (selected_root / relative).read_bytes()
        if commit == SOURCE_COMMIT and relative in d131.SOURCE_BINDING_PATHS:
            index = d131.SOURCE_BINDING_PATHS.index(relative) + 2
            return f"{index:x}" * 40, (selected_root / relative).read_bytes()
        if commit == GATE_COMMIT and relative == d131.OUTPUT_PATH:
            return "9" * 40, (selected_root / relative).read_bytes()
        if commit == RECEIPT_COMMIT and relative == d131.RECEIPT_PATH:
            return "8" * 40, (selected_root / relative).read_bytes()
        if commit == INTENT_COMMIT and relative == d131.INTENT_PATH:
            return "7" * 40, (selected_root / relative).read_bytes()
        raise AssertionError(f"unexpected committed blob: {commit}:{relative}")

    def status_lines(selected_root: Path) -> list[str]:
        head = state["head"]
        if head == SOURCE_COMMIT:
            path = d131.OUTPUT_PATH
        elif head == GATE_COMMIT:
            path = d131.RECEIPT_PATH
        elif head == RECEIPT_COMMIT:
            path = d131.INTENT_PATH
        else:
            return []
        return [f"?? {path.as_posix()}"] if (selected_root / path).exists() else []

    real_write = d131._write_new

    def write_new(selected_root: Path, relative: Path, raw: bytes) -> None:
        state["writes"].append(relative)
        real_write(selected_root, relative, raw)

    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    monkeypatch.setattr(d131, "_assert_runtime_import_boundary", lambda _root: None)
    monkeypatch.setattr(d131, "_now", lambda: next(state["times"]))
    monkeypatch.setattr(d131, "_commit_identity", commit_identity)
    monkeypatch.setattr(d131, "_diff_rows", diff_rows)
    monkeypatch.setattr(d131, "_commit_blob", commit_blob)
    monkeypatch.setattr(d131, "_status_lines", status_lines)
    monkeypatch.setattr(d131, "_head", lambda _root: state["head"])
    monkeypatch.setattr(d131, "_write_new", write_new)
    monkeypatch.setattr(d131, "_git_cli_observation", lambda _root: _fake_git_observation())

    def loaded_module_bindings(selected_root: Path, commit: str) -> list[dict[str, Any]]:
        return [
            {
                **d131._file_binding(selected_root, commit, relative),
                "module_name": module_name,
                "loaded_path": relative.as_posix(),
                "loaded_path_matches_repository": True,
            }
            for relative, module_name in d131.LOADED_MODULE_PATHS
        ]

    monkeypatch.setattr(d131, "_loaded_module_bindings", loaded_module_bindings)
    try:
        yield root, state
    finally:
        if root.exists():
            assert root.resolve(strict=True).parent == REPOSITORY.resolve(strict=True)
            shutil.rmtree(root)


def _build_gate(root: Path) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    result = d131.run_d131_offline_source_gate(repository=root)
    raw = (root / d131.OUTPUT_PATH).read_bytes()
    return result, json.loads(raw.decode("utf-8")), raw


def _rewrite_gate(path: Path, payload: dict[str, Any]) -> bytes:
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload["gate_id"] = f"d131_{body_hash.removeprefix('sha256:')}"
    raw = d131._pretty_bytes(payload)
    path.write_bytes(raw)
    return raw


def _rewrite_artifact(path: Path, payload: dict[str, Any], *, prefix: str) -> bytes:
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload["artifact_id"] = f"{prefix}_{body_hash.removeprefix('sha256:')}"
    raw = d131._pretty_bytes(payload)
    path.write_bytes(raw)
    return raw


def _prepare_receipt(
    root: Path, state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    _build_gate(root)
    state["head"] = GATE_COMMIT
    result = d131.create_d130_local_admission_receipt(repository=root)
    raw = (root / d131.RECEIPT_PATH).read_bytes()
    return result, json.loads(raw.decode("utf-8")), raw


def _prepare_intent(
    root: Path, state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    _prepare_receipt(root, state)
    state["head"] = RECEIPT_COMMIT
    result = d131.create_d130_armed_intent(repository=root)
    raw = (root / d131.INTENT_PATH).read_bytes()
    return result, json.loads(raw.decode("utf-8")), raw


def test_exact_d130_gate_evidence_and_unexercised_prior_approval_are_bound(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, _state = repository
    predecessor = d131._d130_predecessor_binding(root)
    assert predecessor == {
        "path": d130.OUTPUT_PATH.as_posix(),
        "schema_version": d130.SCHEMA_VERSION,
        "gate_id": D130_GATE_ID,
        "semantic_body_hash": D130_GATE_BODY_SHA,
        "file_sha256": D130_GATE_FILE_SHA,
        "file_bytes": D130_GATE_BYTES,
        "status": d130.STATUS,
        "recorded_at": D130_GATE_RECORDED_AT,
        "evidence_commit": D130_EVIDENCE_COMMIT,
        "evidence_tree": D130_EVIDENCE_TREE,
        "evidence_parents": [D130_SOURCE_COMMIT],
        "gate_blob_oid": D130_GATE_BLOB,
        "artifact_mutated": False,
    }
    _, payload, _ = _build_gate(root)
    body = payload["semantic_body"]
    assert body["predecessor_binding"] == predecessor
    assert body["evidence_boundary"] == {
        "today_d130_approval_was_not_exercised_due_missing_committed_writer": True,
        "today_d130_approval_must_not_be_reused_after_d131_topology_change": True,
        "d131_implemented_but_did_not_invoke_future_writers": True,
        "d131_performed_no_external_or_credential_observation": True,
        "git_identity_is_observed_not_vendor_authenticated_or_signed": True,
        "gate_does_not_self_bind_its_future_evidence_commit": True,
        "d131_source_preparation_approval": {
            "approval_mode": "current-user-message-self-attested-unsigned",
            "approval_is_authenticated_or_cryptographically_signed": False,
            "approved_scope": list(d131.D131_SOURCE_PREPARATION_SCOPE),
            "not_authorized": list(d131.D131_SOURCE_PREPARATION_EXCLUSIONS),
            "local_admission_authority_recorded": False,
        },
    }
    integrity = body["implementation_integrity"]
    assert integrity["gate_builder_reads_dotenv_or_credential_value"] is False
    assert integrity["gate_builder_reads_parent_environment_values_for_git"] is False
    assert integrity["gate_builder_uses_fixed_literal_secret_free_git_environment"] is True
    authority = body["authority"]
    assert authority["d130_stage1_prior_approval_received_but_not_exercised"] is True
    assert authority["d130_stage1_prior_approval_reusable_after_topology_change"] is False
    assert authority["d131_local_admission_approval_recorded"] is False
    assert authority["d130_receipt_created"] is False
    assert authority["d130_armed_intent_created"] is False


def test_s131_is_clean_exact_a_only_source_with_loaded_module_bindings(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _state = repository
    for name in (
        "_git_command",
        "_commit_identity",
        "_diff_rows",
        "_commit_blob",
        "_status_lines",
        "_git_cli_observation",
    ):
        monkeypatch.setattr(d129_offline, name, _forbidden(f"inherited D-129 {name}"))
    source = d131._source_identity_for_gate(root)
    assert source["commit"] == SOURCE_COMMIT
    assert source["tree"] == SOURCE_TREE
    assert source["parents"] == [D130_EVIDENCE_COMMIT]
    assert source["implementation_paths_added"] == [
        path.as_posix() for path in d131.IMPLEMENTATION_PATHS
    ]
    assert [row["path"] for row in source["file_bindings"]] == [
        path.as_posix() for path in d131.SOURCE_BINDING_PATHS
    ]
    expected_by_path = {row["path"]: row for row in source["file_bindings"]}
    assert source["loaded_module_bindings"] == [
        {
            **expected_by_path[relative.as_posix()],
            "module_name": module_name,
            "loaded_path": relative.as_posix(),
            "loaded_path_matches_repository": True,
        }
        for relative, module_name in d131.LOADED_MODULE_PATHS
    ]
    assert source["python_routing_env_presence"] == {"PYTHONHOME": False, "PYTHONPATH": False}
    assert source["worktree_and_index_clean_before_gate"] is True
    assert source["git_identity_vendor_authenticated_or_signed"] is False


def test_gate_builder_never_invokes_future_writers_or_challenge_and_leaves_them_absent(
    repository: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _state = repository
    for name in (
        "create_d130_local_admission_receipt",
        "create_d130_armed_intent",
        "render_d130_external_activation_challenge",
    ):
        monkeypatch.setattr(d131, name, _forbidden(name))
    result, payload, raw = _build_gate(root)
    integrity = payload["semantic_body"]["implementation_integrity"]
    assert integrity["gate_builder_writer_invocation_count"] == 0
    assert integrity["gate_builder_challenge_render_count"] == 0
    assert result["receipt_created"] is False
    assert result["armed_intent_created"] is False
    assert result["external_call_count"] == 0
    assert SECRET.encode() not in raw
    assert not (root / d131.RECEIPT_PATH).exists()
    assert not (root / d131.INTENT_PATH).exists()
    assert not any((root / path).exists() for path in d131.FUTURE_EXTERNAL_PATHS)


def test_d131_gate_is_canonical_new_only_idempotent_and_preserves_d130(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    predecessor_before = (root / d131.D130_GATE_PATH).read_bytes()
    first, payload, raw = _build_gate(root)
    second = d131.run_d131_offline_source_gate(repository=root)
    third = d131.validate_d131_offline_source_gate(repository=root)
    assert first == second == third
    assert state["writes"] == [d131.OUTPUT_PATH]
    assert tuple(payload) == d131.GATE_ROOT_KEYS
    assert tuple(payload["semantic_body"]) == d131.GATE_BODY_KEYS
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(payload["semantic_body"]))
    assert payload["gate_id"] == f"d131_{payload['semantic_body_hash'].removeprefix('sha256:')}"
    assert first["file_sha256"] == sha256_bytes(raw)
    assert first["file_bytes"] == len(raw)
    assert (root / d131.OUTPUT_PATH).read_bytes() == raw
    assert (root / d131.D130_GATE_PATH).read_bytes() == predecessor_before


def test_d131_gate_collision_linklike_and_future_orphan_fail_without_repair(
    repository: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _state = repository
    output = root / d131.OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    foreign = b"foreign-d131-gate"
    output.write_bytes(foreign)
    with pytest.raises(d131.D131LocalAdmissionOfflineError):
        d131.run_d131_offline_source_gate(repository=root)
    assert output.read_bytes() == foreign
    output.unlink()

    orphan = root / d131.RECEIPT_PATH
    orphan.write_bytes(b"orphan-receipt")
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="unexpected artifact"):
        d131.run_d131_offline_source_gate(repository=root)
    assert orphan.read_bytes() == b"orphan-receipt"
    assert not output.exists()
    orphan.unlink()

    output.write_bytes(b"linklike-gate")
    real_linklike = d129_offline._is_linklike
    monkeypatch.setattr(
        d129_offline,
        "_is_linklike",
        lambda path: True if path == output else real_linklike(path),
    )
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="linklike"):
        d131._write_new(root, d131.OUTPUT_PATH, b"replacement")
    assert output.read_bytes() == b"linklike-gate"


def test_fully_rehashed_gate_tamper_and_wrong_post_evidence_scope_are_rejected(
    repository: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = repository
    _, payload, raw = _build_gate(root)
    output = root / d131.OUTPUT_PATH
    tampered_payload = copy.deepcopy(payload)
    tampered_payload["semantic_body"]["authority"]["d130_receipt_created"] = True
    tampered = _rewrite_gate(output, tampered_payload)
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="full rebuild"):
        d131.validate_d131_offline_source_gate(repository=root)
    assert output.read_bytes() == tampered

    output.write_bytes(raw)
    state["head"] = GATE_COMMIT
    result = d131.validate_d131_offline_source_gate(repository=root)
    assert result["source_commit"] == SOURCE_COMMIT
    assert result["evidence_commit"] == GATE_COMMIT

    real_diff = d131._diff_rows

    def wrong_scope(selected_root: Path, commit: str) -> list[dict[str, str]]:
        rows = real_diff(selected_root, commit)
        if commit == GATE_COMMIT:
            return [*rows, {"status": "M", "path": "patchloop/agent/model.py"}]
        return rows

    monkeypatch.setattr(d131, "_diff_rows", wrong_scope)
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="evidence scope"):
        d131.validate_d131_offline_source_gate(repository=root)
    assert output.read_bytes() == raw


def test_receipt_writer_is_canonical_idempotent_scope_exact_and_zero_action(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    first, payload, raw = _prepare_receipt(root, state)
    second = d131.create_d130_local_admission_receipt(repository=root)
    third = d131.validate_d130_local_admission(repository=root, mode="receipt")
    assert first == second == third
    assert state["writes"] == [d131.OUTPUT_PATH, d131.RECEIPT_PATH]
    assert tuple(payload) == d131.ROOT_KEYS
    assert tuple(payload["semantic_body"]) == d131.RECEIPT_BODY_KEYS
    assert payload["schema_version"] == d131.RECEIPT_SCHEMA
    assert payload["artifact_id"] == (
        f"d130approval_{payload['semantic_body_hash'].removeprefix('sha256:')}"
    )
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(payload["semantic_body"]))
    body = payload["semantic_body"]
    assert body["status"] == d131.RECEIPT_STATUS
    gate_commit = body["d131_gate_binding"]["evidence_commit_binding"]
    assert tuple(gate_commit) == d131.GATE_EVIDENCE_COMMIT_BINDING_KEYS
    assert gate_commit["exact_gate_add_and_active_docs_modify_commit"] is True
    assert "single_artifact_add_commit" not in gate_commit
    assert body["approval_binding"]["approved_scope"] == list(d131.LOCAL_ADMISSION_SCOPE)
    assert body["approval_binding"]["not_authorized"] == list(d131.LOCAL_ADMISSION_EXCLUSIONS)
    assert body["approval_binding"]["prior_d130_approval_reused"] is False
    assert body["event_order"] == [
        {"ordinal": 1, "event": "fresh-exact-d131-qualified-local-admission-approved"},
        {"ordinal": 2, "event": "approval-receipt-recorded"},
    ]
    authority = body["authority"]
    assert authority["d131_local_admission_approval_recorded"] is True
    assert authority["d130_receipt_created"] is True
    assert authority["d130_receipt_committed"] is False
    assert authority["d130_armed_intent_created"] is False
    assert first["external_call_count"] == 0
    assert SECRET.encode() not in raw
    assert not (root / d131.INTENT_PATH).exists()

    intent = root / d131.INTENT_PATH
    intent.write_bytes(b"corrupt-intent-after-valid-receipt")
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="unexpected artifact"):
        d131.create_d130_local_admission_receipt(repository=root)
    assert intent.read_bytes() == b"corrupt-intent-after-valid-receipt"
    intent.unlink()

    activation = root / d131.ACTIVATION_PATH
    activation.write_bytes(b"orphan-activation-after-valid-receipt")
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="unexpected artifact"):
        d131.create_d130_local_admission_receipt(repository=root)
    assert activation.read_bytes() == b"orphan-activation-after-valid-receipt"


def test_receipt_collision_linklike_and_orphan_intent_are_preserved(
    repository: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = repository
    _build_gate(root)
    state["head"] = GATE_COMMIT
    intent = root / d131.INTENT_PATH
    intent.write_bytes(b"orphan-intent")
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="unexpected artifact"):
        d131.create_d130_local_admission_receipt(repository=root)
    assert intent.read_bytes() == b"orphan-intent"
    assert not (root / d131.RECEIPT_PATH).exists()
    intent.unlink()

    receipt = root / d131.RECEIPT_PATH
    receipt.write_bytes(b"foreign-receipt")
    with pytest.raises(d131.D131LocalAdmissionOfflineError):
        d131.create_d130_local_admission_receipt(repository=root)
    assert receipt.read_bytes() == b"foreign-receipt"
    receipt.unlink()

    receipt.write_bytes(b"linklike-receipt")
    real_linklike = d129_offline._is_linklike
    monkeypatch.setattr(
        d129_offline,
        "_is_linklike",
        lambda path: True if path == receipt else real_linklike(path),
    )
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="linklike"):
        d131._write_new(root, d131.RECEIPT_PATH, b"replacement")
    assert receipt.read_bytes() == b"linklike-receipt"


def test_receipt_only_commit_topology_is_exact_and_required_before_intent(
    repository: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = repository
    _result, receipt, receipt_raw = _prepare_receipt(root, state)
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="clean receipt commit"):
        d131.create_d130_armed_intent(repository=root)
    assert not (root / d131.INTENT_PATH).exists()

    state["head"] = RECEIPT_COMMIT
    binding = d131._receipt_commit_binding(root, receipt, receipt_raw)
    assert binding == {
        "commit": RECEIPT_COMMIT,
        "tree": RECEIPT_TREE,
        "parents": [GATE_COMMIT],
        "artifact_path": d131.RECEIPT_PATH.as_posix(),
        "artifact_blob_oid": "8" * 40,
        "artifact_file_sha256": sha256_bytes(receipt_raw),
        "artifact_file_bytes": len(receipt_raw),
        "single_artifact_add_commit": True,
    }

    real_diff = d131._diff_rows

    def extra_file(selected_root: Path, commit: str) -> list[dict[str, str]]:
        rows = real_diff(selected_root, commit)
        if commit == RECEIPT_COMMIT:
            return [*rows, {"status": "M", "path": "README.md"}]
        return rows

    monkeypatch.setattr(d131, "_diff_rows", extra_file)
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="not artifact-only"):
        d131._receipt_commit_binding(root, receipt, receipt_raw)
    assert not (root / d131.INTENT_PATH).exists()


def test_armed_intent_is_canonical_idempotent_exact_state_and_zero_action(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    first, payload, raw = _prepare_intent(root, state)
    second = d131.create_d130_armed_intent(repository=root)
    third = d131.validate_d130_local_admission(repository=root, mode="armed-intent")
    assert first == second == third
    assert state["writes"] == [d131.OUTPUT_PATH, d131.RECEIPT_PATH, d131.INTENT_PATH]
    assert tuple(payload) == d131.ROOT_KEYS
    assert tuple(payload["semantic_body"]) == d131.INTENT_BODY_KEYS
    assert payload["schema_version"] == d131.INTENT_SCHEMA
    assert payload["artifact_id"] == (
        f"d130intent_{payload['semantic_body_hash'].removeprefix('sha256:')}"
    )
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(payload["semantic_body"]))
    body = payload["semantic_body"]
    assert body["status"] == d131.INTENT_STATUS
    assert body["armed_state"] == {
        "state": "ARMED_WAITING_EXACT_ACTIVATION",
        "receipt_consumed_for_single_intent": True,
        "activation_recorded": False,
        "external_phase_attempt_created": False,
        "retry_resume_or_replacement_authorized": False,
    }
    assert body["activation_challenge_contract"]["proposed_approved_scope"] == list(
        d131.ACTIVATION_SCOPE
    )
    assert body["activation_challenge_contract"]["explicitly_not_authorized"] == list(
        d131.ACTIVATION_EXCLUSIONS
    )
    assert all(
        value == 0 for key, value in body["activity_accounting"].items() if key.endswith("_count")
    )
    assert body["activity_accounting"]["cost_reserved_or_spent_usd"] == "0"
    assert body["authority"]["d130_armed_intent_created"] is True
    assert body["authority"]["d130_external_activation_recorded"] is False
    assert first["status"] == d131.INTENT_STATUS
    assert first["armed_waiting_exact_activation"] is True
    assert first["external_call_count"] == 0
    assert SECRET.encode() not in raw


def test_intent_collision_linklike_and_external_orphan_are_preserved(
    repository: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = repository
    _prepare_receipt(root, state)
    state["head"] = RECEIPT_COMMIT
    orphan_path = d131.FUTURE_EXTERNAL_PATHS[0]
    orphan = root / orphan_path
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_bytes(b"orphan-external-descendant")
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="unexpected artifact"):
        d131.create_d130_armed_intent(repository=root)
    assert orphan.read_bytes() == b"orphan-external-descendant"
    assert not (root / d131.INTENT_PATH).exists()
    orphan.unlink()

    intent = root / d131.INTENT_PATH
    intent.write_bytes(b"foreign-intent")
    with pytest.raises(d131.D131LocalAdmissionOfflineError):
        d131.create_d130_armed_intent(repository=root)
    assert intent.read_bytes() == b"foreign-intent"
    intent.unlink()

    intent.write_bytes(b"linklike-intent")
    real_linklike = d129_offline._is_linklike
    monkeypatch.setattr(
        d129_offline,
        "_is_linklike",
        lambda path: True if path == intent else real_linklike(path),
    )
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="linklike"):
        d131._write_new(root, d131.INTENT_PATH, b"replacement")
    assert intent.read_bytes() == b"linklike-intent"


def test_intent_only_commit_topology_is_exact_and_challenge_requires_it(
    repository: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = repository
    _result, intent, intent_raw = _prepare_intent(root, state)
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="clean intent commit"):
        d131.validate_d130_local_admission(repository=root, mode="post-intent-commit")

    state["head"] = INTENT_COMMIT
    result = d131.validate_d130_local_admission(repository=root, mode="post-intent-commit")
    assert result["intent_commit"] == INTENT_COMMIT
    binding = d131._rebuild_intent_commit_binding(
        root,
        commit=INTENT_COMMIT,
        intent=intent,
        intent_raw=intent_raw,
    )
    assert binding == {
        "commit": INTENT_COMMIT,
        "tree": INTENT_TREE,
        "parents": [RECEIPT_COMMIT],
        "artifact_path": d131.INTENT_PATH.as_posix(),
        "artifact_blob_oid": "7" * 40,
        "artifact_file_sha256": sha256_bytes(intent_raw),
        "artifact_file_bytes": len(intent_raw),
        "single_artifact_add_commit": True,
    }

    real_diff = d131._diff_rows

    def extra_file(selected_root: Path, commit: str) -> list[dict[str, str]]:
        rows = real_diff(selected_root, commit)
        if commit == INTENT_COMMIT:
            return [*rows, {"status": "A", "path": "reports/foreign.json"}]
        return rows

    monkeypatch.setattr(d131, "_diff_rows", extra_file)
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="not artifact-only"):
        d131.validate_d130_local_admission(repository=root, mode="post-intent-commit")


def test_activation_challenge_quotes_gate_receipt_intent_and_both_commits_read_only(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _prepare_intent(root, state)
    state["head"] = INTENT_COMMIT
    gate_payload = json.loads((root / d131.OUTPUT_PATH).read_bytes())
    receipt_payload = json.loads((root / d131.RECEIPT_PATH).read_bytes())
    intent_payload = json.loads((root / d131.INTENT_PATH).read_bytes())
    gate = intent_payload["semantic_body"]["d131_gate_binding"]
    receipt_commit = intent_payload["semantic_body"]["receipt_commit_binding"]
    receipt_raw = (root / d131.RECEIPT_PATH).read_bytes()
    intent_raw = (root / d131.INTENT_PATH).read_bytes()
    intent_commit = d131._rebuild_intent_commit_binding(
        root,
        commit=INTENT_COMMIT,
        intent=intent_payload,
        intent_raw=intent_raw,
    )
    before = {
        path: (root / path).read_bytes()
        for path in (d131.OUTPUT_PATH, d131.RECEIPT_PATH, d131.INTENT_PATH)
    }
    challenge = d131.render_d130_external_activation_challenge(repository=root)
    after = {path: (root / path).read_bytes() for path in before}
    expected_lines = [
        "D-130 external no-call preflight exact activation request",
        "",
        f"D-131 gate: {gate_payload['gate_id']}",
        f"D-131 gate body SHA: {gate_payload['semantic_body_hash']}",
        f"D-131 gate file SHA: {sha256_bytes(before[d131.OUTPUT_PATH])}",
        f"D-131 gate file bytes: {len(before[d131.OUTPUT_PATH])}",
        f"D-131 gate evidence commit tuple: {canonical_json(gate['evidence_commit_binding'])}",
        f"Receipt ID: {receipt_payload['artifact_id']}",
        f"Receipt body SHA: {receipt_payload['semantic_body_hash']}",
        f"Receipt file SHA: {sha256_bytes(receipt_raw)}",
        f"Receipt file bytes: {len(receipt_raw)}",
        f"Receipt commit tuple: {canonical_json(receipt_commit)}",
        f"Intent ID: {intent_payload['artifact_id']}",
        f"Intent body SHA: {intent_payload['semantic_body_hash']}",
        f"Intent file SHA: {sha256_bytes(intent_raw)}",
        f"Intent file bytes: {len(intent_raw)}",
        f"Intent commit tuple: {canonical_json(intent_commit)}",
        "",
        "Proposed approved scope:",
        *(f"- {item}" for item in d131.ACTIVATION_SCOPE),
        "",
        "Explicitly not authorized:",
        *(f"- {item}" for item in d131.ACTIVATION_EXCLUSIONS),
        "",
        "This challenge is not activation. A new exact user message must quote every tuple above.",
    ]
    assert challenge == "\n".join(expected_lines)
    for binding in (gate["evidence_commit_binding"], receipt_commit, intent_commit):
        for value in binding.values():
            assert canonical_json(value) in challenge
    assert before == after
    assert state["writes"] == [d131.OUTPUT_PATH, d131.RECEIPT_PATH, d131.INTENT_PATH]
    assert not (root / d131.ACTIVATION_PATH).exists()


def test_activation_challenge_rejects_uncommitted_and_fully_rehashed_tamper(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _prepare_intent(root, state)
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="clean intent commit"):
        d131.render_d130_external_activation_challenge(repository=root)

    state["head"] = INTENT_COMMIT
    intent_path = root / d131.INTENT_PATH
    intent_original = intent_path.read_bytes()
    intent_payload = json.loads(intent_original)
    intent_payload["semantic_body"]["activity_accounting"][
        "official_docs_or_network_call_count"
    ] = 1
    tampered_intent = _rewrite_artifact(intent_path, intent_payload, prefix="d130intent")
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="full rebuild"):
        d131.render_d130_external_activation_challenge(repository=root)
    assert intent_path.read_bytes() == tampered_intent

    intent_path.write_bytes(intent_original)
    receipt_path = root / d131.RECEIPT_PATH
    receipt_payload = json.loads(receipt_path.read_bytes())
    receipt_payload["semantic_body"]["authority"]["official_docs_or_network_call_count"] = 1
    tampered_receipt = _rewrite_artifact(receipt_path, receipt_payload, prefix="d130approval")
    with pytest.raises(d131.D131LocalAdmissionOfflineError, match="full rebuild"):
        d131.render_d130_external_activation_challenge(repository=root)
    assert receipt_path.read_bytes() == tampered_receipt


def test_public_api_cli_templates_and_source_have_no_external_or_dotenv_surface(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = repository
    _build_gate(root)
    state["head"] = GATE_COMMIT
    before = (root / d131.OUTPUT_PATH).read_bytes()
    template = d131.render_d131_local_admission_template(repository=root)
    assert f"Gate ID: {json.loads(before)['gate_id']}" in template
    assert f"File SHA: {sha256_bytes(before)}" in template
    assert f"Source/evidence commit: {GATE_COMMIT}" in template
    assert "external actions remain zero" in template
    assert "A later exact activation must quote" in template
    assert (root / d131.OUTPUT_PATH).read_bytes() == before
    assert not (root / d131.RECEIPT_PATH).exists()
    assert not (root / d131.INTENT_PATH).exists()

    source_text = (REPOSITORY / MODULE_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert not {"docker", "httpx", "openai", "requests", "socket", "urllib"}.intersection(
        imported_roots
    )
    assert imported_roots.intersection({"subprocess"}) == {"subprocess"}
    assert source_text.count("subprocess.run(") == 1
    assert "os.environ.items" not in source_text
    assert "os.environ.get" not in source_text
    for forbidden in (
        "OPENAI_API_KEY",
        "load_dotenv",
        "dotenv_values",
        "import httpx",
        "import openai",
        "developers.openai.com",
        "docker.exe",
    ):
        assert forbidden not in source_text

    git_binding = _fake_git_observation()
    engine_binding = {
        key: git_binding[key]
        for key in ("resolved_path", "file_name", "file_bytes", "file_sha256", "linklike")
    }
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def fixed_git_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout=b"exact-output\n", stderr=b"")

    monkeypatch.setattr(d131, "_git_engine_binding", lambda: engine_binding)
    monkeypatch.setattr(subprocess, "run", fixed_git_run)
    assert d131._git_command(root, "rev-parse", "HEAD") == "exact-output"
    assert len(calls) == 1
    argv, kwargs = calls[0]
    assert argv == [
        str(d131.D131_GIT_ENGINE_PATH),
        "-c",
        "core.fsmonitor=false",
        "-c",
        "commit.gpgSign=false",
        "rev-parse",
        "HEAD",
    ]
    assert kwargs["env"] == d131.D131_FIXED_GIT_ENVIRONMENT
    assert set(kwargs["env"]) == {
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_SYSTEM",
        "GIT_OPTIONAL_LOCKS",
        "GIT_NO_REPLACE_OBJECTS",
        "GIT_NO_LAZY_FETCH",
        "GIT_TERMINAL_PROMPT",
        "LC_ALL",
    }
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 20
    assert tuple(inspect.signature(d131.create_d130_local_admission_receipt).parameters) == (
        "repository",
    )
    assert tuple(inspect.signature(d131.create_d130_armed_intent).parameters) == ("repository",)
    assert tuple(inspect.signature(d131.render_d130_external_activation_challenge).parameters) == (
        "repository",
    )
    assert set(d131.__all__) == {
        "D131LocalAdmissionOfflineError",
        "INTENT_PATH",
        "INTENT_SCHEMA",
        "INTENT_STATUS",
        "OUTPUT_PATH",
        "RECEIPT_PATH",
        "RECEIPT_SCHEMA",
        "RECEIPT_STATUS",
        "SCHEMA_VERSION",
        "STATUS",
        "create_d130_armed_intent",
        "create_d130_local_admission_receipt",
        "render_d130_external_activation_challenge",
        "render_d131_local_admission_template",
        "run_d131_offline_source_gate",
        "validate_d130_local_admission",
        "validate_d131_offline_source_gate",
    }
    script = (REPOSITORY / SCRIPT_PATH).read_text(encoding="utf-8")
    assert "add_mutually_exclusive_group(required=True)" in script
    for required in (
        "--build-gate",
        "--validate-gate",
        "--print-local-admission-template",
        "--create-receipt",
        "--validate-receipt",
        "--create-armed-intent",
        "--validate-armed-intent",
        "--validate-post-intent-commit",
        "--print-activation-challenge",
    ):
        assert required in script
    for forbidden in ("--external", "--pull", "--capture-pricing", "--sdk-preflight"):
        assert forbidden not in script
