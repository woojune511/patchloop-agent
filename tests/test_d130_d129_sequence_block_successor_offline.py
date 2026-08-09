from __future__ import annotations

import ast
import copy
import json
import os
import shutil
import socket
import subprocess
import uuid
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from patchloop.agent import model as agent_model
from patchloop.agent import runner as agent_runner
from patchloop.evals import d128_docker_no_start_remediation as d128_docker
from patchloop.evals import d128_terminal_successor_no_call_preflight as d128_external
from patchloop.evals import d129_d128_terminal_successor_offline as d129_offline
from patchloop.evals import d129_external_sequence_block as d129_incident
from patchloop.evals import d130_d129_sequence_block_successor_offline as d130
from patchloop.evals import runner as eval_runner
from patchloop.memory import retrieval
from patchloop.sandbox import runner as sandbox_runner
from patchloop.util import canonical_json, sha256_bytes, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_PATH = Path("patchloop/evals/d130_d129_sequence_block_successor_offline.py")
SCRIPT_PATH = Path("scripts/build_d130_d129_sequence_block_successor_offline.py")
TEST_PATH = Path("tests/test_d130_d129_sequence_block_successor_offline.py")

D129_GATE_PATH = Path(
    "reports/live-pilot/artifacts/d129-d128-terminal-successor-offline-source-gate.json"
)
D129_GATE_ID = "d129_fa5412dd269ba6d4f502220fe1655d6f84b746eff6fa95633691464d6e29243c"
D129_GATE_BODY_SHA = "sha256:fa5412dd269ba6d4f502220fe1655d6f84b746eff6fa95633691464d6e29243c"
D129_GATE_FILE_SHA = "sha256:fd57c187d1f260952b581e60f7d0ff98243f3b4ef172c9a6d6669b3e84968512"
D129_GATE_BYTES = 18_678
D129_GATE_STATUS = "D129_D128_TERMINAL_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_APPROVAL_REQUIRED"
D129_GATE_BLOB = "5ccf4a0e4ddaf7b4096186bc960035fdb76f337e"

D129_RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/d129-terminal-successor-external-no-call-approval-receipt.json"
)
D129_RECEIPT_ID = "d129approval_0d505214f607b0f2a2536e1b754750131bc4b6dab2995d24a12554d63090fb42"
D129_RECEIPT_BODY_SHA = "sha256:0d505214f607b0f2a2536e1b754750131bc4b6dab2995d24a12554d63090fb42"
D129_RECEIPT_FILE_SHA = "sha256:820c67d9c5f75cda89aa52f3252295a08ba0ee385e61e6a8ac83cd0637a23885"
D129_RECEIPT_BYTES = 12_014
D129_RECEIPT_STATUS = "D129_EXTERNAL_NO_CALL_APPROVAL_RECORDED_AFTER_PRE_RECEIPT_ACTIVITY"
D129_RECEIPT_BLOB = "c16793a4b1fc87c3e526976e4652a2dafceaff7a"

D129_TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d129-external-no-call-sequence-observed-blocked.json"
)
D129_TERMINAL_ID = (
    "d129sequenceblock_b5fc90e29ed2ca7febda54a2e63e4f5a0606703e0e93a997fab719d33797f5c8"
)
D129_TERMINAL_BODY_SHA = "sha256:b5fc90e29ed2ca7febda54a2e63e4f5a0606703e0e93a997fab719d33797f5c8"
D129_TERMINAL_FILE_SHA = "sha256:fbb7fac37555ea4d8a2de0d5947fdffe74e3b716b359e2a23834ed6689bd732d"
D129_TERMINAL_BYTES = 13_118
D129_TERMINAL_STATUS = "D129_EXTERNAL_NO_CALL_SEQUENCE_OBSERVED_BLOCKED"
D129_TERMINAL_BLOCKER = (
    "durable-receipt-and-phase-attempt-did-not-precede-first-external-docs-lookup"
)
D129_TERMINAL_BLOB = "c0fd613da5a745dc2bb3b50afb984d6e4d1b7fd0"

E_COMMIT = "70f9955dca8d873f91d622505f7afe7f3cfec59e"
E_TREE = "ad9e348284c1161f258ef7e20ea7cc63cd55399d"
E_PARENT = "1fef6716cddca571777c8b7f9f1dc4501f988d1c"
S_COMMIT = "d42334312c4752cbe9f4aa039c22b8ed51b8b66b"
S_TREE = "4a5f75ba8af5d879af735385fc81b0008267e27e"
R_COMMIT = "3fdfaa79a93df1e709eb9c01fdea9c4646cf0ad9"
R_TREE = "44e68cd7aed2a22ffa9591d4338277a75de6c545"
T_COMMIT = "a4598a15be1432b52f0e26d21d79ace17944e6a9"
T_TREE = "f0c9464d58e6025a5edf3081ba41ddd8c4f3defa"

SOURCE_COMMIT = "f" * 40
SOURCE_TREE = "e" * 40
POST_GATE_COMMIT = "c" * 40
POST_GATE_TREE = "d" * 40
SOURCE_BRANCH = "codex/d130-test"

D129_SOURCE_BLOBS = {
    Path("patchloop/evals/d129_external_sequence_block.py"): (
        "b21b4647a144996b8deed3f489600623d652b998"
    ),
    Path("scripts/build_d129_external_sequence_block.py"): (
        "8376693ce92ad2c00deeabd9f180a1b8204f48f1"
    ),
    Path("tests/test_d129_external_sequence_block.py"): (
        "d1daa8d4cb10b228173ca40e07f09fa9f769c99b"
    ),
}

D129_DESCENDANTS = (
    Path(
        "reports/live-pilot/artifacts/d129-docker-image-readiness-remediation-attempt-intent.json"
    ),
    Path(
        "reports/live-pilot/artifacts/d129-exact-docker-image-readiness-remediation-observation.json"
    ),
    Path("reports/live-pilot/artifacts/d129-official-pricing-capture-attempt-intent.json"),
    Path("reports/live-pilot/artifacts/d129-replayable-official-pricing-evidence.json"),
    Path("reports/live-pilot/artifacts/d129-read-only-preflight-attempt-intent.json"),
    Path("reports/live-pilot/artifacts/d129-repeated-no-call-readiness-preflight.json"),
    Path(
        "reports/live-pilot/artifacts/d129-terminal-successor-external-no-call-preflight-gate.json"
    ),
)

REAL_GIT_COMMAND = d129_offline._git_command
REAL_GIT_ENVIRONMENT = d129_offline._git_environment
REAL_RUNTIME_IMPORT_BOUNDARY = d130._assert_runtime_import_boundary


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"D-130 crossed forbidden {label} boundary")

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
    monkeypatch.setattr(
        d128_docker,
        "remediate_already_running_docker_environment",
        _forbidden("Docker remediation"),
    )
    monkeypatch.setattr(
        d128_external,
        "run_d128_external_no_call_preflight",
        _forbidden("D-128 external retry"),
    )
    monkeypatch.setattr(
        d129_incident,
        "create_d129_approval_receipt",
        _forbidden("D-129 receipt repair"),
    )
    monkeypatch.setattr(
        d129_incident,
        "record_d129_sequence_block_terminal",
        _forbidden("D-129 terminal repair"),
    )


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


def _identity(commit: str, tree: str, parent: str) -> dict[str, Any]:
    return {"commit": commit, "tree": tree, "parents": [parent]}


@pytest.fixture(autouse=True)
def deterministic_git_contract(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Any]]:
    state = {"post_gate": False}
    identities = {
        E_COMMIT: _identity(E_COMMIT, E_TREE, E_PARENT),
        S_COMMIT: _identity(S_COMMIT, S_TREE, E_COMMIT),
        R_COMMIT: _identity(R_COMMIT, R_TREE, S_COMMIT),
        T_COMMIT: _identity(T_COMMIT, T_TREE, R_COMMIT),
        SOURCE_COMMIT: _identity(SOURCE_COMMIT, SOURCE_TREE, T_COMMIT),
        POST_GATE_COMMIT: _identity(POST_GATE_COMMIT, POST_GATE_TREE, SOURCE_COMMIT),
    }

    def commit_identity(_root: Path, commit: str) -> dict[str, Any]:
        return copy.deepcopy(identities[commit])

    def diff_rows(_root: Path, commit: str) -> list[dict[str, str]]:
        if commit == E_COMMIT:
            return [
                {"status": "A", "path": D129_GATE_PATH.as_posix()},
                *({"status": "M", "path": path.as_posix()} for path in d130.ACTIVE_DOC_PATHS),
            ]
        if commit == S_COMMIT:
            return [{"status": "A", "path": path.as_posix()} for path in D129_SOURCE_BLOBS]
        if commit == R_COMMIT:
            return [{"status": "A", "path": D129_RECEIPT_PATH.as_posix()}]
        if commit == T_COMMIT:
            return [
                {"status": "A", "path": D129_TERMINAL_PATH.as_posix()},
                *({"status": "M", "path": path.as_posix()} for path in d130.ACTIVE_DOC_PATHS),
            ]
        if commit == SOURCE_COMMIT:
            return [{"status": "A", "path": path.as_posix()} for path in d130.IMPLEMENTATION_PATHS]
        if commit == POST_GATE_COMMIT:
            return [
                {"status": "A", "path": d130.OUTPUT_PATH.as_posix()},
                *({"status": "M", "path": path.as_posix()} for path in d130.ACTIVE_DOC_PATHS),
            ]
        raise AssertionError(f"unexpected commit diff: {commit}")

    historical_paths = {
        D129_GATE_PATH: (D129_GATE_BLOB, E_COMMIT),
        D129_RECEIPT_PATH: (D129_RECEIPT_BLOB, R_COMMIT),
        D129_TERMINAL_PATH: (D129_TERMINAL_BLOB, T_COMMIT),
    }

    def commit_blob(root: Path, commit: str, relative: Path) -> tuple[str, bytes]:
        if relative in historical_paths:
            oid, first_commit = historical_paths[relative]
            allowed = {
                E_COMMIT: (E_COMMIT, S_COMMIT, R_COMMIT, T_COMMIT),
                R_COMMIT: (R_COMMIT, T_COMMIT),
                T_COMMIT: (T_COMMIT,),
            }[first_commit]
            if commit in allowed:
                return oid, (root / relative).read_bytes()
        if relative in D129_SOURCE_BLOBS and commit in (S_COMMIT, R_COMMIT, T_COMMIT):
            return D129_SOURCE_BLOBS[relative], (REPOSITORY / relative).read_bytes()
        if commit == SOURCE_COMMIT and relative in d130.SOURCE_BINDING_PATHS:
            index = d130.SOURCE_BINDING_PATHS.index(relative) + 2
            return f"{index:x}" * 40, (REPOSITORY / relative).read_bytes()
        if commit == POST_GATE_COMMIT and relative == d130.OUTPUT_PATH:
            return "9" * 40, (root / relative).read_bytes()
        raise AssertionError(f"unexpected committed blob: {commit}:{relative}")

    def git_command(root: Path, *args: str, binary: bool = False) -> bytes | str:
        del binary
        if args == ("rev-parse", "--show-toplevel"):
            return str(root)
        if args == ("rev-parse", "HEAD"):
            return POST_GATE_COMMIT if state["post_gate"] else SOURCE_COMMIT
        if args == ("branch", "--show-current"):
            return SOURCE_BRANCH
        raise AssertionError(f"unexpected Git command: {args}")

    def status_lines(root: Path) -> list[str]:
        if state["post_gate"]:
            return []
        output = root / d130.OUTPUT_PATH
        return [f"?? {d130.OUTPUT_PATH.as_posix()}"] if os.path.lexists(output) else []

    monkeypatch.setattr(d130, "_commit_identity", commit_identity)
    monkeypatch.setattr(d130, "_diff_rows", diff_rows)
    monkeypatch.setattr(d130, "_commit_blob", commit_blob)
    monkeypatch.setattr(d130, "_status_lines", status_lines)
    monkeypatch.setattr(d130, "_assert_runtime_import_boundary", lambda _root: None)

    def loaded_module_bindings(root: Path, commit: str) -> list[dict[str, Any]]:
        return [
            {
                **d130._file_binding(root, commit, relative),
                "module_name": module_name,
                "loaded_path": relative.as_posix(),
                "loaded_path_matches_repository": True,
            }
            for relative, module_name in d130.LOADED_MODULE_PATHS
        ]

    monkeypatch.setattr(d130, "_loaded_module_bindings", loaded_module_bindings)
    monkeypatch.setattr(d129_offline, "_git_command", git_command)
    monkeypatch.setattr(d129_offline, "_git_cli_observation", lambda _root: _fake_git_observation())
    monkeypatch.setattr(
        d129_incident,
        "_validate_receipt_payload",
        lambda _root, payload, _raw: payload,
    )
    monkeypatch.setattr(
        d129_incident,
        "_validate_terminal_payload",
        lambda _root, payload, _raw: payload,
    )
    yield state


@pytest.fixture
def repository() -> Iterator[Path]:
    root = REPOSITORY / f"tmp-d130-test-{uuid.uuid4().hex}"
    assert not root.exists()
    root.mkdir()
    required = {
        D129_GATE_PATH,
        D129_RECEIPT_PATH,
        D129_TERMINAL_PATH,
        *d130.SOURCE_BINDING_PATHS,
    }
    try:
        for relative in required:
            source = REPOSITORY / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        yield root
    finally:
        if root.exists():
            assert root.resolve(strict=True).parent == REPOSITORY.resolve(strict=True)
            shutil.rmtree(root)


def _build(root: Path) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    result = d130.run_d130_offline_source_gate(repository=root)
    raw = (root / d130.OUTPUT_PATH).read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    return result, payload, raw


def _rewrite_envelope(path: Path, payload: dict[str, Any]) -> None:
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload["gate_id"] = f"d130_{body_hash.removeprefix('sha256:')}"
    path.write_bytes((json.dumps(payload, ensure_ascii=True, indent=2) + "\n").encode())


def _walk_dicts(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_dicts(item)


def _dict_with(value: Any, key: str, expected: Any) -> dict[str, Any]:
    for item in _walk_dicts(value):
        if item.get(key) == expected:
            return item
    raise AssertionError(f"missing nested binding: {key}={expected!r}")


def test_exact_d129_gate_receipt_and_terminal_tuples_are_bound(repository: Path) -> None:
    chain = d130._predecessor_chain(repository)
    gate = chain["offline_source_gate"]
    receipt = chain["approval_receipt"]
    terminal = chain["sequence_block_terminal"]

    assert gate == {
        "path": D129_GATE_PATH.as_posix(),
        "schema_version": d129_offline.SCHEMA_VERSION,
        "artifact_id": D129_GATE_ID,
        "semantic_body_hash": D129_GATE_BODY_SHA,
        "file_sha256": D129_GATE_FILE_SHA,
        "file_bytes": D129_GATE_BYTES,
        "status": D129_GATE_STATUS,
        "recorded_at": "2026-08-09T07:00:36.222143Z",
        "commit": E_COMMIT,
        "blob_oid": D129_GATE_BLOB,
        "artifact_mutated": False,
    }
    assert receipt == {
        "path": D129_RECEIPT_PATH.as_posix(),
        "schema_version": d129_incident.RECEIPT_SCHEMA,
        "artifact_id": D129_RECEIPT_ID,
        "semantic_body_hash": D129_RECEIPT_BODY_SHA,
        "file_sha256": D129_RECEIPT_FILE_SHA,
        "file_bytes": D129_RECEIPT_BYTES,
        "status": D129_RECEIPT_STATUS,
        "recorded_at": "2026-08-09T08:10:18.466324Z",
        "commit": R_COMMIT,
        "blob_oid": D129_RECEIPT_BLOB,
        "artifact_mutated": False,
    }
    assert terminal == {
        "path": D129_TERMINAL_PATH.as_posix(),
        "schema_version": d129_incident.TERMINAL_SCHEMA,
        "artifact_id": D129_TERMINAL_ID,
        "semantic_body_hash": D129_TERMINAL_BODY_SHA,
        "file_sha256": D129_TERMINAL_FILE_SHA,
        "file_bytes": D129_TERMINAL_BYTES,
        "status": D129_TERMINAL_STATUS,
        "recorded_at": "2026-08-09T08:12:10.616306Z",
        "commit": T_COMMIT,
        "blob_oid": D129_TERMINAL_BLOB,
        "artifact_mutated": False,
    }


def test_exact_e_s_r_t_git_topology_and_scopes_are_replayed(repository: Path) -> None:
    topology = d130._predecessor_chain(repository)["d129_e_s_r_t_git_topology"]
    assert topology == {
        "e129": _identity(E_COMMIT, E_TREE, E_PARENT),
        "s129": _identity(S_COMMIT, S_TREE, E_COMMIT),
        "r129": _identity(R_COMMIT, R_TREE, S_COMMIT),
        "t129": _identity(T_COMMIT, T_TREE, R_COMMIT),
    }
    assert d130.E129_COMMIT == E_COMMIT
    assert d130.S129_COMMIT == S_COMMIT
    assert d130.R129_COMMIT == R_COMMIT
    assert d130.T129_COMMIT == T_COMMIT
    assert d130.T129_TREE == T_TREE


def test_chronology_nonretroactivity_and_unknown_http_are_preserved(repository: Path) -> None:
    chain = d130._predecessor_chain(repository)
    incident = chain["sequence_incident"]
    assert incident == {
        "approval_preceded_lookup": True,
        "receipt_preceded_lookup": False,
        "phase_attempt_preceded_lookup": False,
        "no_attempt_retroactively_created": True,
        "official_docs_web_tool_open_invocation_count": 1,
        "underlying_http_request_or_redirect_count": "unknown",
        "canonical_pricing_capture_get_count": 0,
        "canonical_replayable_entity_retained": False,
        "d129_receipt_consumed": True,
        "retry_resume_or_repair_authorized": False,
    }
    times = [
        datetime.fromisoformat(chain[key]["recorded_at"].replace("Z", "+00:00"))
        for key in ("offline_source_gate", "approval_receipt", "sequence_block_terminal")
    ]
    assert times == sorted(times)
    terminal = json.loads((repository / D129_TERMINAL_PATH).read_bytes())["semantic_body"]
    sequence = terminal["sequence_block"]
    activity = terminal["activity_accounting"]["pre_receipt_official_docs_activity"]
    assert sequence["receipt_does_not_repair_sequence"] is True
    assert sequence["no_attempt_retroactively_created"] is True
    assert activity["underlying_http_request_or_redirect_count"] == "unknown"
    assert activity["web_tool_returned_content_bytes"] == "unknown"
    assert activity["exact_lookup_timestamp_retained"] is False
    assert (
        d130._incident_preservation()["d129_sequence_incident_preserved_without_reinterpretation"]
        is True
    )


def test_all_d129_and_d130_descendants_must_be_absent(repository: Path) -> None:
    _build(repository)
    assert not any((repository / path).exists() for path in d130.D129_FORBIDDEN_DESCENDANTS)
    assert not any((repository / path).exists() for path in d130.D130_FUTURE_PATHS)

    second = REPOSITORY / f"tmp-d130-descendant-{uuid.uuid4().hex}"
    second.mkdir()
    try:
        for relative in {
            D129_GATE_PATH,
            D129_RECEIPT_PATH,
            D129_TERMINAL_PATH,
            *d130.SOURCE_BINDING_PATHS,
        }:
            target = second / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPOSITORY / relative).read_bytes())
        descendant = second / d130.D130_FUTURE_PATHS[0]
        descendant.parent.mkdir(parents=True, exist_ok=True)
        descendant.write_bytes(b"foreign")
        with pytest.raises(d130.D130OfflineGateError, match="unexpected artifact exists"):
            d130.run_d130_offline_source_gate(repository=second)
        assert not (second / d130.OUTPUT_PATH).exists()
        assert descendant.read_bytes() == b"foreign"
    finally:
        if second.exists():
            shutil.rmtree(second)


def test_clean_exact_a_only_source_commit_and_module_blobs_are_bound(repository: Path) -> None:
    source = d130._source_identity_for_build(repository)
    assert source["commit"] == SOURCE_COMMIT
    assert source["tree"] == SOURCE_TREE
    assert source["parents"] == [T_COMMIT]
    assert source["implementation_paths_added"] == [
        path.as_posix() for path in d130.IMPLEMENTATION_PATHS
    ]
    bindings = source["file_bindings"]
    assert [binding["path"] for binding in bindings] == [
        path.as_posix() for path in d130.SOURCE_BINDING_PATHS
    ]
    for index, (binding, relative) in enumerate(
        zip(bindings, d130.SOURCE_BINDING_PATHS, strict=True), start=2
    ):
        raw = (REPOSITORY / relative).read_bytes()
        assert binding == {
            "path": relative.as_posix(),
            "file_bytes": len(raw),
            "file_sha256": sha256_bytes(raw),
            "blob_oid": f"{index:x}" * 40,
            "current_bytes_match_commit": True,
        }
    expected_by_path = {binding["path"]: binding for binding in bindings}
    assert source["loaded_module_bindings"] == [
        {
            **expected_by_path[relative.as_posix()],
            "module_name": module_name,
            "loaded_path": relative.as_posix(),
            "loaded_path_matches_repository": True,
        }
        for relative, module_name in d130.LOADED_MODULE_PATHS
    ]
    assert source["worktree_and_index_clean_before_gate"] is True
    assert source["git_identity_vendor_authenticated_or_signed"] is False


def test_gate_is_canonical_new_only_idempotent_and_validation_is_read_only(
    repository: Path,
) -> None:
    historical_before = {
        path: (repository / path).read_bytes()
        for path in (D129_GATE_PATH, D129_RECEIPT_PATH, D129_TERMINAL_PATH)
    }
    first, payload, raw = _build(repository)
    second = d130.run_d130_offline_source_gate(repository=repository)
    third = d130.validate_d130_offline_source_gate(repository=repository)
    assert first == second == third
    assert tuple(payload) == d130.ROOT_KEYS
    assert tuple(payload["semantic_body"]) == d130.BODY_KEYS
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(payload["semantic_body"]))
    assert payload["gate_id"] == (f"d130_{payload['semantic_body_hash'].removeprefix('sha256:')}")
    assert first["file_sha256"] == sha256_bytes(raw)
    assert (repository / d130.OUTPUT_PATH).read_bytes() == raw
    assert historical_before == {
        path: (repository / path).read_bytes() for path in historical_before
    }


def test_missing_or_fully_rehashed_predecessor_tamper_fails_before_output(
    repository: Path,
) -> None:
    target = repository / D129_TERMINAL_PATH
    original = target.read_bytes()
    target.unlink()
    with pytest.raises(d130.D130OfflineGateError):
        d130.run_d130_offline_source_gate(repository=repository)
    assert not (repository / d130.OUTPUT_PATH).exists()
    target.write_bytes(original)

    receipt_path = repository / D129_RECEIPT_PATH
    receipt = json.loads(receipt_path.read_bytes())
    receipt["semantic_body"]["authority"]["d129_external_phase_attempt_created"] = True
    body_hash = sha256_text(canonical_json(receipt["semantic_body"]))
    receipt["semantic_body_hash"] = body_hash
    receipt["artifact_id"] = f"d129approval_{body_hash.removeprefix('sha256:')}"
    receipt_path.write_bytes((json.dumps(receipt, ensure_ascii=True, indent=2) + "\n").encode())
    with pytest.raises(d130.D130OfflineGateError):
        d130.run_d130_offline_source_gate(repository=repository)
    assert not (repository / d130.OUTPUT_PATH).exists()


def test_source_or_historical_git_drift_is_rejected_without_repair(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_path = repository / MODULE_PATH
    source_path.write_bytes(source_path.read_bytes() + b"\n# drift\n")
    with pytest.raises(d130.D130OfflineGateError, match="source drift"):
        d130.run_d130_offline_source_gate(repository=repository)
    assert not (repository / d130.OUTPUT_PATH).exists()

    source_path.write_bytes((REPOSITORY / MODULE_PATH).read_bytes())
    real_identity = d130._commit_identity

    def drifted_identity(root: Path, commit: str) -> dict[str, Any]:
        value = real_identity(root, commit)
        if commit == T_COMMIT:
            value["tree"] = "0" * 40
        return value

    monkeypatch.setattr(d130, "_commit_identity", drifted_identity)
    with pytest.raises(d130.D130OfflineGateError, match="t129 topology differs"):
        d130.run_d130_offline_source_gate(repository=repository)
    assert not (repository / d130.OUTPUT_PATH).exists()


def test_output_collision_directory_and_linklike_paths_are_never_repaired(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = repository / d130.OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    with pytest.raises(d130.D130OfflineGateError):
        d130.run_d130_offline_source_gate(repository=repository)
    assert output.is_dir()
    output.rmdir()
    output.write_bytes(b"partial")
    with pytest.raises(d130.D130OfflineGateError):
        d130.run_d130_offline_source_gate(repository=repository)
    assert output.read_bytes() == b"partial"
    output.unlink()

    real_lexists = d129_offline._lexists
    real_linklike = d129_offline._is_linklike
    monkeypatch.setattr(
        d129_offline,
        "_lexists",
        lambda path: True if path == output else real_lexists(path),
    )
    monkeypatch.setattr(
        d129_offline,
        "_is_linklike",
        lambda path: True if path == output else real_linklike(path),
    )
    with pytest.raises(d130.D130OfflineGateError, match="linklike"):
        d130.run_d130_offline_source_gate(repository=repository)
    assert not output.exists()


def test_fully_rehashed_gate_authority_incident_unknown_and_chronology_tamper_fail(
    repository: Path,
) -> None:
    _, payload, raw = _build(repository)
    output = repository / d130.OUTPUT_PATH
    variants: list[dict[str, Any]] = []
    authority = copy.deepcopy(payload)
    authority["semantic_body"]["authority"]["d130_receipt_created"] = True
    variants.append(authority)
    incident = copy.deepcopy(payload)
    incident["semantic_body"]["procedural_incident_preservation"][
        "underlying_http_request_or_redirect_count"
    ] = 1
    variants.append(incident)
    unknown = copy.deepcopy(payload)
    unknown["semantic_body"]["unknown_authority"] = True
    variants.append(unknown)
    chronology = copy.deepcopy(payload)
    chronology["semantic_body"]["recorded_at"] = "2026-08-09T08:00:00Z"
    variants.append(chronology)
    loaded_module = copy.deepcopy(payload)
    loaded_module["semantic_body"]["source_identity"]["loaded_module_bindings"][0][
        "loaded_path"
    ] = "patchloop/evals/foreign.py"
    variants.append(loaded_module)

    for variant in variants:
        _rewrite_envelope(output, variant)
        tampered = output.read_bytes()
        with pytest.raises(d130.D130OfflineGateError):
            d130.validate_d130_offline_source_gate(repository=repository)
        assert output.read_bytes() == tampered
    output.write_bytes(raw)
    assert d130.validate_d130_offline_source_gate(repository=repository)["status"] == d130.STATUS


def test_public_api_and_cli_have_no_external_receipt_intent_or_activation_entrypoint(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_tree = ast.parse((REPOSITORY / MODULE_PATH).read_text(encoding="utf-8"))
    imports = [
        alias.name.split(".")[0]
        for node in ast.walk(module_tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    ]
    assert not {"httpx", "openai", "socket", "subprocess"}.intersection(imports)
    source = (REPOSITORY / MODULE_PATH).read_text(encoding="utf-8")
    for forbidden in (
        "OPENAI_API_KEY",
        "create_d130_approval_receipt",
        "create_d130_armed_intent",
        "activate_d130_external_phase",
        "run_d130_external",
        "capture_official_pricing_evidence(",
        "remediate_already_running_docker_environment(",
    ):
        assert forbidden not in source
    assert set(d130.__all__) == {
        "D130OfflineGateError",
        "OUTPUT_PATH",
        "SCHEMA_VERSION",
        "STATUS",
        "render_d130_two_stage_admission_template",
        "run_d130_offline_source_gate",
        "validate_d130_offline_source_gate",
    }
    script = (REPOSITORY / SCRIPT_PATH).read_text(encoding="utf-8")
    assert "add_mutually_exclusive_group(required=True)" in script
    for required in ("--build", "--validate", "--print-admission-template"):
        assert required in script
    for forbidden in ("--create-receipt", "--arm", "--activate", "--external"):
        assert forbidden not in script

    monkeypatch.setenv("PYTHONPATH", str(repository))
    with pytest.raises(d130.D130OfflineGateError, match="routing environment"):
        REAL_RUNTIME_IMPORT_BOUNDARY(REPOSITORY)
    monkeypatch.delenv("PYTHONPATH")
    monkeypatch.setattr(d130, "__file__", str(REPOSITORY / TEST_PATH))
    with pytest.raises(d130.D130OfflineGateError, match="outside repository"):
        REAL_RUNTIME_IMPORT_BOUNDARY(REPOSITORY)

    fake_git = repository / "git.exe"
    fake_git.write_bytes(b"fixed local git engine")
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def fake_run(argv: list[str], **kwargs: Any) -> SimpleNamespace:
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout=b"ok\n", stderr=b"")

    monkeypatch.setattr(d129_offline, "_git_executable", lambda: fake_git.resolve(strict=True))
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("OPENAI_API_KEY", "secret-must-not-reach-git")
    assert REAL_GIT_COMMAND(repository, "rev-parse", "HEAD") == "ok"
    argv, kwargs = calls.pop()
    assert argv[0] == str(fake_git.resolve(strict=True))
    assert kwargs["shell"] is False
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is False
    assert "OPENAI_API_KEY" not in kwargs["env"]
    assert kwargs["env"]["GIT_CONFIG_NOSYSTEM"] == "1"
    assert kwargs["env"]["GIT_OPTIONAL_LOCKS"] == "0"
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", "forbidden")
    with pytest.raises(d129_offline.D129OfflineGateError, match="routing environment"):
        REAL_GIT_ENVIRONMENT()


def test_two_stage_admission_template_is_exact_read_only_and_non_authoritative(
    repository: Path,
) -> None:
    result, _, raw = _build(repository)
    before = {
        path.relative_to(repository): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }
    template = d130.render_d130_two_stage_admission_template(repository=repository)
    after = {
        path.relative_to(repository): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }
    assert before == after
    assert template == "\n".join(
        (
            "D-130 local admission approval (no external actions)",
            "",
            f"Gate ID: {result['gate_id']}",
            f"Body SHA: {result['semantic_body_hash']}",
            f"File SHA: {result['file_sha256']}",
            f"File bytes: {result['file_bytes']}",
            "Source/evidence commit: <exact D-130 gate+docs evidence commit>",
            "",
            "Approved local-only scope:",
            "- create and commit one exact D-130 approval receipt",
            "- create and commit one durable ARMED_WAITING_EXACT_ACTIVATION intent",
            "- render the exact activation challenge",
            "",
            "Explicitly not approved in this admission:",
            "- search or open official docs, network, pricing capture",
            "- Docker, SDK, credential or endpoint observation",
            "- provider/evaluator/agent, memory/retrieval",
            "- execution hash/candidate, cost, or four-row A/C",
            "",
            "A later exact activation must quote the receipt, armed-intent, and commit tuples.",
        )
    )
    assert (repository / d130.OUTPUT_PATH).read_bytes() == raw
    assert not any((repository / path).exists() for path in d130.D130_FUTURE_PATHS)


def test_zero_authority_and_exact_post_gate_docs_commit_are_enforced(
    repository: Path,
    deterministic_git_contract: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, payload, raw = _build(repository)
    authority = payload["semantic_body"]["authority"]
    assert authority == d130._authority()
    assert authority["d130_offline_source_gate_materialized"] is True
    assert authority["d129_sequence_incident_preserved"] is True
    for key, value in authority.items():
        if key in {
            "d130_offline_source_gate_materialized",
            "d129_sequence_incident_preserved",
            "d130_cost_reserved_or_spent_usd",
        }:
            continue
        assert value in (0, False), key
    assert authority["d130_cost_reserved_or_spent_usd"] == "0"

    deterministic_git_contract["post_gate"] = True
    result = d130.validate_d130_offline_source_gate(repository=repository)
    assert result["source_commit"] == SOURCE_COMMIT
    assert result["evidence_commit"] == POST_GATE_COMMIT
    assert (repository / d130.OUTPUT_PATH).read_bytes() == raw

    real_diff = d130._diff_rows

    def wrong_evidence_scope(root: Path, commit: str) -> list[dict[str, str]]:
        rows = real_diff(root, commit)
        if commit == POST_GATE_COMMIT:
            return [*rows, {"status": "A", "path": "reports/foreign.json"}]
        return rows

    monkeypatch.setattr(d130, "_diff_rows", wrong_evidence_scope)
    with pytest.raises(d130.D130OfflineGateError, match="evidence scope differs"):
        d130.validate_d130_offline_source_gate(repository=repository)
    assert (repository / d130.OUTPUT_PATH).read_bytes() == raw
