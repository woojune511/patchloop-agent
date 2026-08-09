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
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from patchloop.agent import model as agent_model
from patchloop.agent import runner as agent_runner
from patchloop.evals import d128_docker_no_start_remediation as d128_docker
from patchloop.evals import d128_terminal_successor_no_call_preflight as d128_external
from patchloop.evals import d129_d128_terminal_successor_offline as d129
from patchloop.evals import runner as eval_runner
from patchloop.memory import retrieval
from patchloop.sandbox import runner as sandbox_runner
from patchloop.util import canonical_json, sha256_bytes, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_PATH = Path("patchloop/evals/d129_d128_terminal_successor_offline.py")
SCRIPT_PATH = Path("scripts/build_d129_d128_terminal_successor_offline.py")
TEST_PATH = Path("tests/test_d129_d128_terminal_successor_offline.py")
SOURCE_COMMIT = "f" * 40
SOURCE_TREE = "e" * 40
SOURCE_BRANCH = "codex/d129-test"
REAL_GIT_COMMAND = d129._git_command
REAL_GIT_ENVIRONMENT = d129._git_environment


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"D-129 crossed forbidden {label} boundary")

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
        _forbidden("D-128 retry"),
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


def _artifact_blob_map() -> dict[Path, str]:
    return {
        d129.D128_OFFLINE_PATH: d129.D128_OFFLINE_BLOB_OID,
        d129.D128_RECEIPT_PATH: d129.D128_RECEIPT_BLOB_OID,
        d129.D128_ATTEMPT_PATH: d129.D128_ATTEMPT_BLOB_OID,
        d129.D128_TERMINAL_PATH: d129.D128_TERMINAL_BLOB_OID,
    }


@pytest.fixture(autouse=True)
def deterministic_git_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    identities = {
        d129.D128_SOURCE_COMMIT: {
            "commit": d129.D128_SOURCE_COMMIT,
            "tree": d129.D128_SOURCE_TREE,
            "parents": [d129.D128_SOURCE_PARENT],
        },
        d129.D128_RECEIPT_COMMIT: {
            "commit": d129.D128_RECEIPT_COMMIT,
            "tree": d129.D128_RECEIPT_TREE,
            "parents": [d129.D128_SOURCE_COMMIT],
        },
        d129.D128_EVIDENCE_COMMIT: {
            "commit": d129.D128_EVIDENCE_COMMIT,
            "tree": d129.D128_EVIDENCE_TREE,
            "parents": [d129.D128_RECEIPT_COMMIT],
        },
        SOURCE_COMMIT: {
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "parents": [d129.D128_EVIDENCE_COMMIT],
        },
    }

    def commit_identity(_root: Path, commit: str) -> dict[str, Any]:
        return copy.deepcopy(identities[commit])

    def diff_rows(_root: Path, commit: str) -> list[dict[str, str]]:
        if commit == d129.D128_RECEIPT_COMMIT:
            return [{"status": "A", "path": d129.D128_RECEIPT_PATH.as_posix()}]
        if commit == d129.D128_EVIDENCE_COMMIT:
            return [
                *({"status": "M", "path": path.as_posix()} for path in d129.ACTIVE_DOC_PATHS),
                {"status": "A", "path": d129.D128_ATTEMPT_PATH.as_posix()},
                {"status": "A", "path": d129.D128_TERMINAL_PATH.as_posix()},
            ]
        if commit == SOURCE_COMMIT:
            return [{"status": "A", "path": path.as_posix()} for path in d129.IMPLEMENTATION_PATHS]
        raise AssertionError(f"unexpected commit diff: {commit}")

    artifact_oids = _artifact_blob_map()

    def commit_blob(_root: Path, commit: str, relative: Path) -> tuple[str, bytes]:
        if commit == d129.D128_EVIDENCE_COMMIT and relative in artifact_oids:
            return artifact_oids[relative], (REPOSITORY / relative).read_bytes()
        if commit == SOURCE_COMMIT and relative in d129.IMPLEMENTATION_PATHS:
            index = d129.IMPLEMENTATION_PATHS.index(relative) + 2
            return f"{index:x}" * 40, (REPOSITORY / relative).read_bytes()
        raise AssertionError(f"unexpected committed blob: {commit}:{relative}")

    def git_command(root: Path, *args: str, binary: bool = False) -> bytes | str:
        del binary
        if args == ("rev-parse", "--show-toplevel"):
            return str(root)
        if args == ("rev-parse", "HEAD"):
            return SOURCE_COMMIT
        if args == ("branch", "--show-current"):
            return SOURCE_BRANCH
        raise AssertionError(f"unexpected Git command: {args}")

    def status_lines(root: Path) -> list[str]:
        output = root / d129.OUTPUT_PATH
        return [f"?? {d129.OUTPUT_PATH.as_posix()}"] if os.path.lexists(output) else []

    monkeypatch.setattr(d129, "_commit_identity", commit_identity)
    monkeypatch.setattr(d129, "_diff_rows", diff_rows)
    monkeypatch.setattr(d129, "_commit_blob", commit_blob)
    monkeypatch.setattr(d129, "_git_command", git_command)
    monkeypatch.setattr(d129, "_git_cli_observation", lambda _root: _fake_git_observation())
    monkeypatch.setattr(d129, "_status_lines", status_lines)


@pytest.fixture
def repository() -> Iterator[Path]:
    root = REPOSITORY / f"tmp-d129-test-{uuid.uuid4().hex}"
    assert not root.exists()
    root.mkdir()
    required = {
        d129.D128_OFFLINE_PATH,
        d129.D128_RECEIPT_PATH,
        d129.D128_ATTEMPT_PATH,
        d129.D128_TERMINAL_PATH,
        *d129.IMPLEMENTATION_PATHS,
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
    result = d129.run_d129_offline_source_gate(repository=root)
    raw = (root / d129.OUTPUT_PATH).read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    return result, payload, raw


def _rewrite_envelope(path: Path, payload: dict[str, Any]) -> None:
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload["gate_id"] = f"d129_{body_hash.removeprefix('sha256:')}"
    path.write_bytes((json.dumps(payload, ensure_ascii=True, indent=2) + "\n").encode())


def test_exact_d128_predecessor_chain_is_bound_terminal_consumed_and_descendant_free(
    repository: Path,
) -> None:
    chain = d129._predecessor_chain(repository)
    assert chain["offline_source_gate"]["artifact_id"] == d129.D128_OFFLINE_ID
    assert chain["approval_receipt"]["artifact_id"] == d129.D128_RECEIPT_ID
    assert chain["docker_attempt"]["artifact_id"] == d129.D128_ATTEMPT_ID
    assert chain["blocked_docker_terminal"]["artifact_id"] == d129.D128_TERMINAL_ID
    assert chain["terminal_blocker"] == d129.D128_TERMINAL_BLOCKER
    assert chain["receipt_is_consumed"] is True
    assert chain["d128_retry_resume_or_repair_opened"] is False
    assert chain["d128_pricing_preflight_and_gate_descendants_absent"] is True
    assert chain["historical_d128_agent_docker_cli_calls"] == 3
    assert chain["historical_d128_agent_image_pull_calls"] == 0


def test_exact_d128_s_r_e_git_chain_and_committed_blobs_are_bound(
    repository: Path,
) -> None:
    chain = d129._predecessor_chain(repository)
    topology = chain["d128_source_receipt_evidence_git_topology"]
    assert topology["source"] == {
        "commit": d129.D128_SOURCE_COMMIT,
        "tree": d129.D128_SOURCE_TREE,
        "parents": [d129.D128_SOURCE_PARENT],
    }
    assert topology["receipt"]["parents"] == [d129.D128_SOURCE_COMMIT]
    assert topology["receipt"]["tree"] == d129.D128_RECEIPT_TREE
    assert topology["evidence"]["parents"] == [d129.D128_RECEIPT_COMMIT]
    assert topology["evidence"]["tree"] == d129.D128_EVIDENCE_TREE
    assert chain["offline_source_gate"]["blob_oid_at_d128_evidence_commit"] == (
        d129.D128_OFFLINE_BLOB_OID
    )
    assert chain["approval_receipt"]["blob_oid_at_d128_evidence_commit"] == (
        d129.D128_RECEIPT_BLOB_OID
    )
    assert chain["docker_attempt"]["blob_oid_at_d128_evidence_commit"] == (
        d129.D128_ATTEMPT_BLOB_OID
    )
    assert chain["blocked_docker_terminal"]["blob_oid_at_d128_evidence_commit"] == (
        d129.D128_TERMINAL_BLOB_OID
    )


def test_user_daemon_success_and_no_auto_start_attestation_is_bounded(
    repository: Path,
) -> None:
    _, payload, _ = _build(repository)
    attestation = payload["semantic_body"]["manual_readiness_attestation"]
    assert attestation == d129._manual_readiness_attestation()
    assert attestation["docker_endpoint"] == "npipe:////./pipe/dockerDesktopLinuxEngine"
    assert (
        attestation["reported_client_version"],
        attestation["reported_server_version"],
        attestation["reported_server_os"],
        attestation["reported_server_arch"],
        attestation["reported_exit_code"],
    ) == ("29.6.2", "29.6.2", "linux", "amd64", 0)
    assert attestation["user_reported_no_preexisting_container_auto_started"] is True
    assert attestation["user_self_attested"] is True
    assert attestation["authenticated_or_signed"] is False
    assert attestation["independently_observed_by_agent"] is False
    assert attestation["user_reported_manual_docker_check_attempt_count"] == 2
    assert attestation["user_reported_successful_readiness_check_count"] == 1
    assert attestation["user_reported_failed_readiness_check_count"] == 1
    assert attestation["future_external_phase_must_reobserve_after_new_receipt"] is True


def test_successor_scope_and_all_live_authority_are_exactly_closed(
    repository: Path,
) -> None:
    _, payload, _ = _build(repository)
    body = payload["semantic_body"]
    contract = body["successor_contract"]["contract"]
    assert tuple(contract["future_approved_scope"]) == d129.FUTURE_APPROVED_SCOPE
    assert tuple(contract["future_explicitly_not_authorized"]) == d129.FUTURE_NOT_AUTHORIZED
    assert contract["manual_prerequisite_supplied"] is True
    assert contract["external_approval_recorded"] is False
    assert contract["external_entrypoint_present_in_this_module"] is False
    authority = body["authority"]
    assert authority["historical_d128_agent_read_only_docker_calls"] == 3
    assert authority["user_reported_manual_docker_check_attempts"] == 2
    assert authority["user_reported_successful_manual_docker_readiness_checks"] == 1
    assert authority["user_reported_failed_manual_docker_readiness_checks"] == 1
    for key, value in authority.items():
        if key in {
            "d129_offline_source_gate_materialized",
            "d129_manual_readiness_attestation_recorded",
            "d129_source_commit_bound",
            "historical_d128_agent_read_only_docker_calls",
            "user_reported_manual_docker_check_attempts",
            "user_reported_successful_manual_docker_readiness_checks",
            "user_reported_failed_manual_docker_readiness_checks",
            "d129_offline_cost_reserved_or_spent_usd",
        }:
            continue
        assert value in (0, False), key
    assert authority["d129_offline_cost_reserved_or_spent_usd"] == "0"


def test_gate_is_canonical_new_only_idempotent_and_validation_is_read_only(
    repository: Path,
) -> None:
    before = {
        path: (repository / path).read_bytes()
        for path in (
            d129.D128_OFFLINE_PATH,
            d129.D128_RECEIPT_PATH,
            d129.D128_ATTEMPT_PATH,
            d129.D128_TERMINAL_PATH,
        )
    }
    first, payload, raw = _build(repository)
    second = d129.run_d129_offline_source_gate(repository=repository)
    third = d129.validate_d129_offline_source_gate(repository=repository)
    assert first == second == third
    assert tuple(payload) == d129.ROOT_KEYS
    assert tuple(payload["semantic_body"]) == d129.BODY_KEYS
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(payload["semantic_body"]))
    assert payload["gate_id"] == (f"d129_{payload['semantic_body_hash'].removeprefix('sha256:')}")
    assert first["file_sha256"] == sha256_bytes(raw)
    assert (repository / d129.OUTPUT_PATH).read_bytes() == raw
    assert before == {path: (repository / path).read_bytes() for path in before}


def test_imports_cli_and_public_api_preserve_zero_external_boundary(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_tree = ast.parse((REPOSITORY / MODULE_PATH).read_text(encoding="utf-8"))
    calls = [node for node in ast.walk(module_tree) if isinstance(node, ast.Call)]
    assert not any(
        isinstance(node.func, ast.Attribute)
        and node.func.attr
        in {
            "Popen",
            "system",
            "create_connection",
            "start",
            "resume",
            "evaluate_suite",
            "preflight_suite",
        }
        for node in calls
    )
    assert not any(
        isinstance(node, (ast.Import, ast.ImportFrom))
        and any(alias.name.split(".")[0] in {"httpx", "openai", "socket"} for alias in node.names)
        for node in ast.walk(module_tree)
    )
    run_calls = [
        node
        for node in calls
        if isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr == "run"
    ]
    assert len(run_calls) == 1
    assert set(d129.__all__) == {
        "D129OfflineGateError",
        "OUTPUT_PATH",
        "render_d129_successor_approval_template",
        "run_d129_offline_source_gate",
        "validate_d129_offline_source_gate",
    }
    script = (REPOSITORY / SCRIPT_PATH).read_text(encoding="utf-8")
    assert "add_mutually_exclusive_group(required=True)" in script
    assert "--build" in script and "--validate" in script
    assert "--print-approval-template" in script
    assert "receipt" not in " ".join(d129.__all__).casefold()
    assert "external" not in " ".join(d129.__all__).casefold()
    fake_git = repository / "git.exe"
    fake_git.write_bytes(b"fixed local git engine")
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def fake_run(argv: list[str], **kwargs: Any) -> SimpleNamespace:
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout=b"ok\n", stderr=b"")

    monkeypatch.setattr(d129, "_git_executable", lambda: fake_git.resolve(strict=True))
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("OPENAI_API_KEY", "sentinel-must-not-reach-git")
    assert REAL_GIT_COMMAND(repository, "rev-parse", "HEAD") == "ok"
    argv, kwargs = calls.pop()
    assert argv == [
        str(fake_git.resolve(strict=True)),
        "-c",
        "core.fsmonitor=false",
        "-c",
        "commit.gpgSign=false",
        "rev-parse",
        "HEAD",
    ]
    assert kwargs["shell"] is False
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is False
    assert kwargs["check"] is False
    assert kwargs["timeout"] == 20
    assert "OPENAI_API_KEY" not in kwargs["env"]
    assert kwargs["env"]["GIT_CONFIG_NOSYSTEM"] == "1"
    assert kwargs["env"]["GIT_OPTIONAL_LOCKS"] == "0"
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", "forbidden")
    with pytest.raises(d129.D129OfflineGateError, match="routing environment"):
        REAL_GIT_ENVIRONMENT()
    monkeypatch.delenv("GIT_OBJECT_DIRECTORY")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout=b"",
            stderr=b"not persisted",
        ),
    )
    with pytest.raises(d129.D129OfflineGateError, match="git command failed"):
        REAL_GIT_COMMAND(repository, "rev-parse", "HEAD")


def test_missing_or_rehashed_d128_predecessor_fails_before_output(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = repository / d129.OUTPUT_PATH
    target = repository / d129.D128_TERMINAL_PATH
    original = target.read_bytes()
    target.unlink()
    with pytest.raises(d129.D129OfflineGateError):
        d129.run_d129_offline_source_gate(repository=repository)
    assert not output.exists()
    target.write_bytes(original)
    real_datetime = datetime

    class RegressedClock(real_datetime):
        @classmethod
        def now(cls, _timezone: Any) -> datetime:
            return real_datetime(2026, 8, 9, 5, 14, 43, tzinfo=UTC)

    with monkeypatch.context() as context:
        context.setattr(d129, "datetime", RegressedClock)
        with pytest.raises(d129.D129OfflineGateError, match="before output publication"):
            d129.run_d129_offline_source_gate(repository=repository)
    assert not output.exists()
    payload = json.loads(original.decode("utf-8"))
    payload["semantic_body"]["status"] = "D128_REHASHED_TAMPER"
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload["artifact_id"] = f"d128dockerremediation_{body_hash.removeprefix('sha256:')}"
    target.write_bytes((json.dumps(payload, ensure_ascii=True, indent=2) + "\n").encode())
    with pytest.raises(d129.D129OfflineGateError):
        d129.run_d129_offline_source_gate(repository=repository)
    assert not output.exists()


def test_unexpected_d128_descendant_or_linklike_path_is_rejected(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = repository / d129.OUTPUT_PATH
    descendant = repository / d129.D128_DESCENDANT_PATHS[0]
    descendant.parent.mkdir(parents=True, exist_ok=True)
    descendant.write_text("foreign", encoding="utf-8")
    with pytest.raises(d129.D129OfflineGateError, match="descendant evidence exists"):
        d129.run_d129_offline_source_gate(repository=repository)
    assert not output.exists()
    descendant.unlink()
    original_lexists = d129._lexists
    monkeypatch.setattr(
        d129,
        "_lexists",
        lambda path: True if path == descendant else original_lexists(path),
    )
    with pytest.raises(d129.D129OfflineGateError, match="descendant evidence exists"):
        d129.run_d129_offline_source_gate(repository=repository)
    assert not output.exists()


def test_implementation_or_historical_git_drift_invalidates_without_repair(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, raw = _build(repository)
    source_path = repository / MODULE_PATH
    original_source = source_path.read_bytes()
    source_path.write_bytes(original_source + b"\n# drift\n")
    with pytest.raises(d129.D129OfflineGateError, match="current source drifted"):
        d129.validate_d129_offline_source_gate(repository=repository)
    assert (repository / d129.OUTPUT_PATH).read_bytes() == raw
    source_path.write_bytes(original_source)
    original_identity = d129._commit_identity

    def drifted_identity(root: Path, commit: str) -> dict[str, Any]:
        value = original_identity(root, commit)
        if commit == d129.D128_EVIDENCE_COMMIT:
            value["tree"] = "0" * 40
        return value

    monkeypatch.setattr(d129, "_commit_identity", drifted_identity)
    with pytest.raises(d129.D129OfflineGateError, match="evidence commit differs"):
        d129.validate_d129_offline_source_gate(repository=repository)
    assert (repository / d129.OUTPUT_PATH).read_bytes() == raw


def test_output_collision_directory_and_linklike_paths_are_never_repaired(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = repository / d129.OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    with pytest.raises(d129.D129OfflineGateError):
        d129.run_d129_offline_source_gate(repository=repository)
    assert output.is_dir()
    output.rmdir()
    output.write_bytes(b"partial")
    with pytest.raises(d129.D129OfflineGateError):
        d129.run_d129_offline_source_gate(repository=repository)
    assert output.read_bytes() == b"partial"
    output.unlink()
    original_lexists = d129._lexists
    original_linklike = d129._is_linklike
    monkeypatch.setattr(
        d129,
        "_lexists",
        lambda path: True if path == output else original_lexists(path),
    )
    monkeypatch.setattr(
        d129,
        "_is_linklike",
        lambda path: True if path == output else original_linklike(path),
    )
    with pytest.raises(d129.D129OfflineGateError, match="linklike"):
        d129.run_d129_offline_source_gate(repository=repository)
    assert not output.exists()


def test_fully_rehashed_authority_attestation_unknown_and_chronology_tamper_fail(
    repository: Path,
) -> None:
    _, payload, raw = _build(repository)
    output = repository / d129.OUTPUT_PATH
    variants: list[dict[str, Any]] = []
    authority = copy.deepcopy(payload)
    authority["semantic_body"]["authority"]["execution_hash_created"] = True
    variants.append(authority)
    attestation = copy.deepcopy(payload)
    attestation["semantic_body"]["manual_readiness_attestation"][
        "independently_observed_by_agent"
    ] = True
    variants.append(attestation)
    unknown = copy.deepcopy(payload)
    unknown["semantic_body"]["unknown_authority"] = True
    variants.append(unknown)
    chronology = copy.deepcopy(payload)
    chronology["semantic_body"]["recorded_at"] = "2026-08-09T05:00:00Z"
    variants.append(chronology)
    for variant in variants:
        _rewrite_envelope(output, variant)
        tampered = output.read_bytes()
        with pytest.raises(d129.D129OfflineGateError):
            d129.validate_d129_offline_source_gate(repository=repository)
        assert output.read_bytes() == tampered
    output.write_bytes(raw)
    assert d129.validate_d129_offline_source_gate(repository=repository)["status"] == (d129.STATUS)


def test_approval_template_is_exact_non_authoritative_and_creates_no_receipt(
    repository: Path,
) -> None:
    result, _, raw = _build(repository)
    before = {
        path.relative_to(repository): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }
    template = d129.render_d129_successor_approval_template(repository=repository)
    after = {
        path.relative_to(repository): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }
    assert before == after
    assert result["gate_id"] in template
    assert result["semantic_body_hash"] in template
    assert result["file_sha256"] in template
    assert str(result["file_bytes"]) in template
    assert "<exact commit after gate/docs commit>" in template
    expected = "\n".join(
        (
            "D-129 terminal-successor external no-call preflight approval",
            "",
            f"Gate ID\n{result['gate_id']}",
            f"Semantic body SHA\n{result['semantic_body_hash']}",
            f"File SHA\n{result['file_sha256']}",
            f"File bytes\n{result['file_bytes']}",
            "Source/evidence commit\n<exact commit after gate/docs commit>",
            "",
            "User prerequisite already self-attested",
            "- Docker Desktop Linux daemon reported ready: 29.6.2/linux/amd64/rc=0.",
            "- No pre-existing container auto-start was reported.",
            "- The future phase must reobserve readiness; the agent must not start the daemon.",
            "",
            "Approved scope",
            *(f"- {item}" for item in d129.FUTURE_APPROVED_SCOPE),
            "",
            "Explicitly not authorized",
            *(f"- {item}" for item in d129.FUTURE_NOT_AUTHORIZED),
        )
    )
    assert template == expected
    assert (repository / d129.OUTPUT_PATH).read_bytes() == raw
    assert not any("approval-receipt" in path.name for path in repository.rglob("*d129*"))
