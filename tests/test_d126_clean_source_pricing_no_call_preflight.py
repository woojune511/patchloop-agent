from __future__ import annotations

import copy
import json
import os
import shutil
import socket
import subprocess
import sys
import types
import uuid
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest

from patchloop.agent import model as agent_model
from patchloop.agent import runner as agent_runner
from patchloop.evals import d126_clean_source_pricing_no_call_preflight as d126
from patchloop.evals import runner as eval_runner
from patchloop.memory import retrieval
from patchloop.sandbox import runner as sandbox_runner
from patchloop.util import canonical_json, sha256_bytes, sha256_text
from patchloop.verifier import core as verifier_core

REPOSITORY = Path(__file__).resolve().parents[1]
RECORDED_AT = "2026-08-09T01:00:00Z"
SOURCE_COMMIT = "1" * 40
SOURCE_TREE = "2" * 40
SOURCE_PARENT = "3" * 40
TRACKED_LISTING = "100644 blob " + "a" * 40 + "\tAGENTS.md"
MODEL_PAGE = (
    b"Default snapshot: `gpt-5.4-mini-2026-03-17`\n"
    b"| Input | $0.75 | 1M tokens |\n"
    b"| Cached input | $0.075 | 1M tokens |\n"
    b"| Output | $4.5 | 1M tokens |\n"
    b"| Responses | `v1/responses` | Supported |\n"
    b"| GPT-5.4 mini | $0.75 | $0.075 | $4.5 |\n"
)


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"D-126 crossed forbidden {label} boundary")

    return fail


def _remove_exact(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if d126._is_linklike(path):
        path.unlink()
    elif path.exists() and path.is_dir():
        path.rmdir()
    elif path.exists():
        path.unlink()


@pytest.fixture
def isolated_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[dict[str, Path]]:
    token = uuid.uuid4().hex
    relative_paths = {
        "receipt": d126.RECEIPT_PATH.parent / f".pytest-d126-receipt-{token}.json",
        "preflight": d126.PREFLIGHT_PATH.parent / f".pytest-d126-preflight-{token}.json",
        "gate": d126.GATE_PATH.parent / f".pytest-d126-gate-{token}.json",
    }
    paths = {name: REPOSITORY / relative for name, relative in relative_paths.items()}
    for path in paths.values():
        assert path.parent.resolve(strict=True).is_relative_to(REPOSITORY.resolve(strict=True))
        assert not path.exists()
    monkeypatch.setattr(d126, "RECEIPT_PATH", relative_paths["receipt"])
    monkeypatch.setattr(d126, "PREFLIGHT_PATH", relative_paths["preflight"])
    monkeypatch.setattr(d126, "GATE_PATH", relative_paths["gate"])
    monkeypatch.setattr(d126, "_now", lambda: RECORDED_AT)

    monkeypatch.setattr(subprocess, "run", _forbidden("subprocess"))
    monkeypatch.setattr(subprocess, "Popen", _forbidden("subprocess"))
    monkeypatch.setattr(os, "system", _forbidden("shell"))
    monkeypatch.setattr(socket, "socket", _forbidden("socket/network"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("socket/network"))
    monkeypatch.setattr(agent_model, "OpenAI", _forbidden("provider"))
    monkeypatch.setattr(agent_runner.AgentRunner, "start", _forbidden("agent run"))
    monkeypatch.setattr(agent_runner.AgentRunner, "resume", _forbidden("agent run"))
    monkeypatch.setattr(
        agent_runner,
        "issue_live_execution_authorization",
        _forbidden("execution hash"),
    )
    monkeypatch.setattr(
        agent_runner,
        "issue_campaign_cost_reservation_authorization",
        _forbidden("cost reservation"),
    )
    monkeypatch.setattr(eval_runner, "preflight_suite", _forbidden("suite preflight"))
    monkeypatch.setattr(eval_runner, "evaluate_suite", _forbidden("evaluator"))
    monkeypatch.setattr(verifier_core.EvaluationEngine, "evaluate", _forbidden("evaluator"))
    monkeypatch.setattr(retrieval, "retrieve_memory", _forbidden("retrieval"))
    monkeypatch.setattr(retrieval, "_query_embedding", _forbidden("retrieval"))
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "available", _forbidden("Docker"))
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "run_check", _forbidden("Docker"))
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "run_probe", _forbidden("Docker"))
    try:
        yield paths
    finally:
        for path in paths.values():
            _remove_exact(path)
            for temporary in path.parent.glob(f".{path.name}.*.tmp"):
                _remove_exact(temporary)


@pytest.fixture
def d126_tmp_path() -> Iterator[Path]:
    path = REPOSITORY / f"tmp-d126-test-{uuid.uuid4().hex}"
    assert not path.exists()
    path.mkdir()
    try:
        yield path
    finally:
        if path.exists():
            shutil.rmtree(path)


class FakeFetcher:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def fetch(self, url: str) -> d126.FetchedDocument:
        self.urls.append(url)
        return d126.FetchedDocument(
            status_code=200,
            final_url=d126.OFFICIAL_MODEL_PAGE_URL,
            content_type="text/markdown; charset=utf-8",
            etag='"d126-test-etag"',
            body=MODEL_PAGE,
        )


class FakeDockerRunner:
    def __init__(self, *, fail_daemon_and_images: bool = False) -> None:
        self.fail_daemon_and_images = fail_daemon_and_images
        self.calls: list[tuple[list[str], dict[str, str], int]] = []

    def run(
        self,
        command: Sequence[str],
        *,
        environment: dict[str, str],
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[bytes]:
        argv = list(command)
        self.calls.append((argv, dict(environment), timeout_seconds))
        tail = argv[1:]
        if tail == ["--version"]:
            stdout = b"Docker version 28.0.0, build d126\n"
        elif tail == ["context", "show"]:
            stdout = (d126.LOCAL_DOCKER_CONTEXT + "\n").encode()
        elif tail[:3] == ["context", "inspect", d126.LOCAL_DOCKER_CONTEXT]:
            stdout = (json.dumps(d126.LOCAL_DOCKER_ENDPOINT) + "\n").encode()
        elif tail[:2] == ["version", "--format"]:
            if self.fail_daemon_and_images:
                return subprocess.CompletedProcess(argv, 1, b"", b"daemon unavailable")
            stdout = json.dumps(
                {
                    "ClientVersion": "28.0.0",
                    "ServerVersion": "28.0.0",
                    "ServerOs": "linux",
                    "ServerArch": "amd64",
                }
            ).encode()
        elif tail[:3] == ["image", "inspect", "--format"]:
            if self.fail_daemon_and_images:
                return subprocess.CompletedProcess(argv, 1, b"", b"image unavailable")
            image = tail[-1]
            stdout = ("sha256:" + image.rsplit("sha256:", 1)[1] + "\n").encode()
        else:
            raise AssertionError(f"unexpected Docker argv: {argv!r}")
        return subprocess.CompletedProcess(argv, 0, stdout, b"")


def _install_fake_docker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    docker = tmp_path / "Programs/DockerDesktop/resources/bin/docker.exe"
    docker.parent.mkdir(parents=True)
    docker.write_bytes(b"d126-fake-docker-cli")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("PATCHLOOP_DOCKER_CLI", raising=False)
    return docker


def _source_observation() -> dict[str, Any]:
    return {
        "commit": SOURCE_COMMIT,
        "tree": SOURCE_TREE,
        "parent": SOURCE_PARENT,
        "branch": "codex/d126-test",
        "tracked_tree_listing_sha256": sha256_bytes((TRACKED_LISTING + "\n").encode()),
        "worktree_clean_before_observation": True,
        "index_clean_before_observation": True,
        "scope": "current-main-worktree-commit-tree-only",
        "ignored_or_external_worktrees_claimed_clean": False,
    }


def _sdk_observation(*, ready: bool) -> dict[str, Any]:
    checks = {
        "python_is_repository_venv": True,
        "openai_sdk_installed": True,
        "openai_sdk_matches_lock": True,
        "api_key_present": ready,
        "alternate_openai_or_proxy_tls_environment_absent": True,
        "synthetic_explicit_official_endpoint_no_call_probe_passed": True,
        "production_client_factory_explicit_official_base_url": True,
        "production_client_factory_trust_env_false": True,
    }
    return {
        "python": {"version": "3.12.0", "file_name": "python.exe"},
        "openai_sdk": {"installed_version": "1.99.0", "locked_version": "1.99.0"},
        "credential": {
            "name": "OPENAI_API_KEY",
            "present": ready,
            "value_hash_length_or_prefix_persisted": False,
            "identity_continuity_claimed": False,
        },
        "routing_environment_presence": {"OPENAI_API_KEY": ready},
        "routing_environment_values_persisted": False,
        "official_endpoint": d126.OFFICIAL_API_BASE_URL,
        "network_call_count": 0,
        "checks": checks,
        "passed": all(checks.values()),
    }


class FakeGitCommands:
    def __init__(self) -> None:
        self.status_calls = 0

    def run(self, _root: Path, *args: str) -> str:
        if args == ("status", "--porcelain", "--untracked-files=all"):
            self.status_calls += 1
            if self.status_calls == 1:
                return ""
            return "\n".join(
                (
                    f"?? {d126.PREFLIGHT_PATH.as_posix()}",
                    f"?? {d126.GATE_PATH.as_posix()}",
                )
            )
        responses = {
            ("rev-parse", "HEAD"): SOURCE_COMMIT,
            ("rev-parse", "HEAD^{tree}"): SOURCE_TREE,
            ("rev-parse", "HEAD^"): SOURCE_PARENT,
            ("branch", "--show-current"): "codex/d126-test",
            ("ls-tree", "-r", "--full-tree", "HEAD"): TRACKED_LISTING,
        }
        if args not in responses:
            raise AssertionError(f"unexpected Git argv: {args!r}")
        return responses[args]


def _install_fake_sdk(
    monkeypatch: pytest.MonkeyPatch,
    *,
    credential_present: bool,
) -> tuple[str, list[Any]]:
    secret = "sk-d126-secret-must-never-be-recorded"
    for name in d126.SENSITIVE_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    if credential_present:
        monkeypatch.setenv("OPENAI_API_KEY", secret)
    monkeypatch.setattr(d126.importlib.metadata, "version", lambda _name: "1.99.0")
    monkeypatch.setattr(d126, "_locked_openai_version", lambda _root: "1.99.0")
    stable_read = d126._stable_read

    def source_read(root: Path, relative: Path) -> bytes:
        if relative == Path("patchloop/agent/model.py"):
            return (
                b"class OpenAIResponsesAdapter:\n"
                b"    def __init__(self):\n"
                b"        self.client = OpenAI(\n"
                b"            base_url=OFFICIAL_API_BASE_URL,\n"
                b"            http_client=httpx.Client(trust_env=False),\n"
                b"        )\n"
            )
        return stable_read(root, relative)

    monkeypatch.setattr(d126, "_stable_read", source_read)
    clients: list[Any] = []

    class FakeHttpClient:
        def __init__(self, *, trust_env: bool) -> None:
            assert trust_env is False

    class FakeOpenAI:
        def __init__(
            self,
            *,
            api_key: str,
            base_url: str,
            max_retries: int,
            http_client: Any,
        ) -> None:
            assert api_key == "d126-nonsecret-placeholder"
            assert isinstance(http_client, FakeHttpClient)
            self.base_url = base_url
            self.max_retries = max_retries
            clients.append(self)

        def close(self) -> None:
            return None

    monkeypatch.setitem(sys.modules, "httpx", types.SimpleNamespace(Client=FakeHttpClient))
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    return secret, clients


def _build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    sdk_ready: bool,
    docker_ready: bool,
) -> tuple[dict[str, Any], FakeFetcher, FakeDockerRunner]:
    _install_fake_docker(monkeypatch, tmp_path)
    _install_fake_sdk(monkeypatch, credential_present=sdk_ready)
    fetcher = FakeFetcher()
    runner = FakeDockerRunner(fail_daemon_and_images=not docker_ready)
    git = FakeGitCommands()
    monkeypatch.setattr(d126, "_run_git", git.run)
    monkeypatch.setattr(
        d126.OfficialDocsFetcher,
        "fetch",
        lambda _self, url: fetcher.fetch(url),
    )

    def run_command(
        _self: d126.SubprocessCommandRunner,
        command: Sequence[str],
        *,
        environment: dict[str, str],
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[bytes]:
        return runner.run(
            command,
            environment=environment,
            timeout_seconds=timeout_seconds,
        )

    monkeypatch.setattr(d126.SubprocessCommandRunner, "run", run_command)
    d126.create_d126_approval_receipt(repository=REPOSITORY)
    result = d126.run_d126_preflight(repository=REPOSITORY)
    return result, fetcher, runner


def test_exact_d125_approval_tuple_scope_and_receipt_are_canonical_and_idempotent(
    isolated_artifacts: dict[str, Path],
) -> None:
    result = d126.create_d126_approval_receipt(repository=REPOSITORY)
    raw = isolated_artifacts["receipt"].read_bytes()
    payload = json.loads(raw)
    body = payload["semantic_body"]

    assert body["predecessor_binding"] == {
        "path": d126.D125_PATH.as_posix(),
        "gate_id": "d125_ed9c892a598ce4543591bf3b9135a1cbe3752589fdc447b05867d59e07d45539",
        "semantic_body_hash": (
            "sha256:ed9c892a598ce4543591bf3b9135a1cbe3752589fdc447b05867d59e07d45539"
        ),
        "file_bytes": 13_820,
        "file_sha256": "sha256:9bc5f6e618f31312dc5026a807eabf478e47c05893cca72c71328378b593856e",
        "status": "D125_AC_RUNTIME_FINALIZATION_SOURCE_QUALIFIED_EXECUTION_CANDIDATE_BLOCKED",
        "artifact_mutated": False,
    }
    assert body["approval"]["approved_scope"] == list(d126.APPROVED_SCOPE)
    assert body["approval"]["explicitly_not_authorized"] == list(d126.NOT_AUTHORIZED)
    assert body["authority"]["execution_hash_creation_authorized"] is False
    assert body["authority"]["execution_candidate_creation_authorized"] is False
    assert raw == d126._pretty_bytes(payload)
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(body))
    assert result == d126.create_d126_approval_receipt(repository=REPOSITORY)
    assert isolated_artifacts["receipt"].read_bytes() == raw


def test_d125_sealed_constant_drift_creates_no_receipt(
    isolated_artifacts: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        d126.d125,
        "SEALED_HISTORICAL_FILE_SHA256",
        "sha256:" + "0" * 64,
    )
    with pytest.raises(d126.D126PreflightError, match="sealed constants differ"):
        d126.create_d126_approval_receipt(repository=REPOSITORY)
    assert not any(path.exists() for path in isolated_artifacts.values())


def test_preflight_requires_receipt_before_any_observation(
    isolated_artifacts: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeFetcher()
    runner = FakeDockerRunner()
    monkeypatch.setattr(d126, "_git_observation", _forbidden("Git observation"))
    monkeypatch.setattr(d126, "_sdk_observation", _forbidden("SDK observation"))
    monkeypatch.setattr(
        d126.OfficialDocsFetcher,
        "fetch",
        lambda _self, url: fetcher.fetch(url),
    )
    monkeypatch.setattr(
        d126.SubprocessCommandRunner,
        "run",
        lambda _self, command, *, environment, timeout_seconds: runner.run(
            command,
            environment=environment,
            timeout_seconds=timeout_seconds,
        ),
    )

    with pytest.raises(d126.D126PreflightError):
        d126.run_d126_preflight(repository=REPOSITORY)
    assert fetcher.urls == []
    assert runner.calls == []
    assert not any(path.exists() for path in isolated_artifacts.values())


def test_official_pricing_decimal_math_and_freshness_are_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeFetcher()
    pricing = d126._pricing_observation(fetcher, RECORDED_AT)
    assert fetcher.urls == [d126.OFFICIAL_MODEL_PAGE_URL]
    assert pricing["facts"] == {
        "model_label": "GPT-5.4 mini",
        "dated_model_id": "gpt-5.4-mini-2026-03-17",
        "service_tier": "default-standard",
        "unit": "usd-per-1m-text-tokens",
        "input_usd": "0.75",
        "cached_input_usd": "0.075",
        "cache_write_input_usd": None,
        "output_usd": "4.5",
        "responses_endpoint_supported": True,
    }
    assert pricing["facts_sha256"] == sha256_text(canonical_json(pricing["facts"]))
    assert pricing["planning_math"] == {
        "max_total_tokens": 3_000_000,
        "max_output_tokens": 25_000,
        "conservative_worst_rate_usd_per_million": "4.5",
        "per_row_reserve_usd": "13.6125",
        "scheduled_rows": 4,
        "full_schedule_reserve_usd": "54.45",
        "hard_cap_usd": "55.00",
        "per_row_reserve_nanos": 13_612_500_000,
        "full_schedule_reserve_nanos": 54_450_000_000,
        "hard_cap_nanos": 55_000_000_000,
    }
    stale = copy.deepcopy(pricing)
    stale["observed_at"] = "2026-08-09T01:00:00Z"
    with pytest.raises(d126.D126PreflightError, match="pricing is stale"):
        d126._preflight_body(
            receipt_binding={},
            receipt_recorded_at=RECORDED_AT,
            source=_source_observation(),
            pricing=stale,
            docker={"passed": True},
            sdk=_sdk_observation(ready=True),
            recorded_at="2026-08-12T01:00:01Z",
        )


def test_docker_probe_uses_only_exact_read_only_allowlist_and_forced_local_endpoint(
    isolated_artifacts: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    d126_tmp_path: Path,
) -> None:
    del isolated_artifacts
    docker = _install_fake_docker(monkeypatch, d126_tmp_path)
    monkeypatch.setenv("DOCKER_HOST", "tcp://unapproved.example:2375")
    monkeypatch.setenv("DOCKER_TLS_VERIFY", "1")
    runner = FakeDockerRunner()
    observed = d126._docker_observation(runner)

    assert observed["passed"] is True
    assert observed["total_command_count"] == 12
    assert observed["read_only_daemon_call_count"] == 6
    assert observed["docker_workload_or_mutating_call_count"] == 0
    allowed = {tuple(command) for _role, _mode, command in d126._docker_commands(str(docker))}
    forbidden = {"pull", "info", "build", "create", "start", "run", "exec", "rm", "ps"}
    for command, environment, timeout in runner.calls:
        assert tuple(command) in allowed
        assert not forbidden.intersection(command[1:])
        assert timeout == 30
        docker_environment = {
            key: value for key, value in environment.items() if key.upper().startswith("DOCKER_")
        }
        if command[1] in {"version", "image"}:
            assert docker_environment == {"DOCKER_HOST": d126.LOCAL_DOCKER_ENDPOINT}
        else:
            assert docker_environment == {}


def test_hostile_docker_context_stdout_is_not_serialized(
    isolated_artifacts: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    d126_tmp_path: Path,
) -> None:
    del isolated_artifacts
    _install_fake_docker(monkeypatch, d126_tmp_path)
    secret = "sk-d126-hostile-docker-stdout-secret"

    class HostileDockerRunner(FakeDockerRunner):
        def run(
            self,
            command: Sequence[str],
            *,
            environment: dict[str, str],
            timeout_seconds: int,
        ) -> subprocess.CompletedProcess[bytes]:
            result = super().run(
                command,
                environment=environment,
                timeout_seconds=timeout_seconds,
            )
            if list(command)[1:3] == ["context", "inspect"]:
                hostile = json.dumps(f"{d126.LOCAL_DOCKER_ENDPOINT}?token={secret}").encode()
                return subprocess.CompletedProcess(list(command), 0, hostile, b"")
            return result

    observed = d126._docker_observation(HostileDockerRunner())
    rendered = canonical_json(observed)

    assert observed["passed"] is False
    assert all(
        snapshot["observed_projection"]["context_endpoint"] is None
        for snapshot in observed["snapshots"]
    )
    assert secret not in rendered
    assert all(
        row["raw_stdout_persisted"] is False
        for snapshot in observed["snapshots"]
        for row in snapshot["commands"]
    )


def test_sdk_probe_records_credential_presence_only_and_never_the_secret(
    isolated_artifacts: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del isolated_artifacts
    secret, clients = _install_fake_sdk(monkeypatch, credential_present=True)
    observed = d126._sdk_observation(REPOSITORY)
    rendered = canonical_json(observed)

    assert observed["passed"] is True
    assert observed["credential"] == {
        "name": "OPENAI_API_KEY",
        "present": True,
        "value_hash_length_or_prefix_persisted": False,
        "identity_continuity_claimed": False,
    }
    assert observed["routing_environment_values_persisted"] is False
    assert observed["network_call_count"] == 0
    assert secret not in rendered
    assert clients


def test_blocked_missing_credential_daemon_and_images_is_sealed_without_live_calls(
    isolated_artifacts: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    d126_tmp_path: Path,
) -> None:
    result, fetcher, runner = _build(
        monkeypatch,
        d126_tmp_path,
        sdk_ready=False,
        docker_ready=False,
    )
    gate = json.loads(isolated_artifacts["gate"].read_bytes())
    preflight = json.loads(isolated_artifacts["preflight"].read_bytes())

    assert result["status"] == d126.BLOCKED_STATUS
    assert result["environment_ready_for_execution_hash"] is False
    assert set(result["observed_blockers"]) == {
        "docker-cli-observed-identity-awaits-separate-exact-approval",
        "docker-local-daemon-and-exact-images-readiness-failed",
        "openai-api-key-presence-missing",
    }
    assert fetcher.urls == [d126.OFFICIAL_MODEL_PAGE_URL]
    assert len(runner.calls) == 12
    assert gate["semantic_body"]["authority"]["execution_hash_authorized_or_created"] is False
    authority = preflight["semantic_body"]["authority"]
    assert [
        authority["provider_calls_made"],
        authority["evaluator_calls_made"],
        authority["agent_runs_started"],
        authority["runtime_memory_injection_count"],
        authority["retrieval_call_count"],
        authority["docker_workload_or_mutating_call_count"],
        authority["cost_reserved_or_spent_usd"],
    ] == [0, 0, 0, 0, 0, 0, "0"]


def test_best_case_remains_blocked_canonical_idempotent_and_source_bound(
    isolated_artifacts: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    d126_tmp_path: Path,
) -> None:
    result, _fetcher, _runner = _build(
        monkeypatch,
        d126_tmp_path,
        sdk_ready=True,
        docker_ready=True,
    )
    originals = {name: path.read_bytes() for name, path in isolated_artifacts.items()}
    gate = json.loads(originals["gate"])
    preflight = json.loads(originals["preflight"])

    assert result["status"] == d126.BLOCKED_STATUS
    assert result["source_commit"] == SOURCE_COMMIT
    assert result["environment_ready_for_execution_hash"] is False
    assert result["observed_blockers"] == [
        "docker-cli-observed-identity-awaits-separate-exact-approval"
    ]
    assert result["execution_hash_created"] is False
    assert result["execution_candidate_created"] is False
    assert preflight["semantic_body"]["source_commit_observation"] == _source_observation()
    assert originals["gate"] == d126._pretty_bytes(gate)
    assert gate["semantic_body_hash"] == sha256_text(canonical_json(gate["semantic_body"]))
    assert result == d126.run_d126_preflight(repository=REPOSITORY)
    assert originals == {name: path.read_bytes() for name, path in isolated_artifacts.items()}

    monkeypatch.setattr(
        d126,
        "_run_git",
        lambda _root, *args: "f" * 40 if args == ("rev-parse", "HEAD") else "",
    )
    with pytest.raises(d126.D126PreflightError, match="current source commit differs"):
        d126.validate_d126_preflight_gate(repository=REPOSITORY)


def test_persisted_preflight_cannot_resume_gate_after_pricing_expires(
    isolated_artifacts: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    d126_tmp_path: Path,
) -> None:
    receipt_time = "2026-08-09T01:00:00Z"
    pricing_at_71_hours = "2026-08-12T00:00:00Z"
    clock = iter(
        [
            receipt_time,
            pricing_at_71_hours,
            pricing_at_71_hours,
            pricing_at_71_hours,
        ]
    )
    monkeypatch.setattr(d126, "_now", lambda: next(clock))
    _build(monkeypatch, d126_tmp_path, sdk_ready=True, docker_ready=True)
    preflight_bytes = isolated_artifacts["preflight"].read_bytes()
    isolated_artifacts["gate"].unlink()
    monkeypatch.setattr(d126, "_now", lambda: "2026-08-15T00:00:01Z")

    with pytest.raises(d126.D126PreflightError, match="pricing is not fresh at gate creation"):
        d126.run_d126_preflight(repository=REPOSITORY)
    assert isolated_artifacts["preflight"].read_bytes() == preflight_bytes
    assert not isolated_artifacts["gate"].exists()


@pytest.mark.parametrize(
    "tamper",
    [
        "unknown",
        "authority",
        "approval-scope",
        "source",
        "pricing",
        "redirect-count",
        "docker",
        "sdk",
    ],
)
def test_fully_rehashed_tamper_is_rejected(
    isolated_artifacts: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    d126_tmp_path: Path,
    tamper: str,
) -> None:
    _build(monkeypatch, d126_tmp_path, sdk_ready=True, docker_ready=True)
    if tamper == "approval-scope":
        path = isolated_artifacts["receipt"]
        payload = json.loads(path.read_bytes())
        body = copy.deepcopy(payload["semantic_body"])
        body["approval"]["approved_scope"].append("execution-hash-creation")
        rewritten = d126._envelope(d126.RECEIPT_SCHEMA, "d126approval_", body)
    elif tamper in {"unknown", "authority"}:
        path = isolated_artifacts["gate"]
        payload = json.loads(path.read_bytes())
        body = copy.deepcopy(payload["semantic_body"])
        if tamper == "unknown":
            body["authority"]["future_authority"] = False
        else:
            body["authority"]["execution_hash_authorized_or_created"] = True
        rewritten = d126._envelope(d126.GATE_SCHEMA, "d126_", body)
    else:
        path = isolated_artifacts["preflight"]
        payload = json.loads(path.read_bytes())
        body = copy.deepcopy(payload["semantic_body"])
        if tamper == "source":
            body["source_commit_observation"]["commit"] = "not-a-git-commit"
        elif tamper == "pricing":
            body["official_pricing_observation"]["planning_math"]["per_row_reserve_nanos"] += 1
        elif tamper == "redirect-count":
            body["official_pricing_observation"]["redirect_count"] = 4
            body["official_pricing_observation"]["public_get_request_count"] = 5
        elif tamper == "docker":
            body["docker_observation"]["total_command_count"] += 1
        else:
            body["sdk_credential_endpoint_observation"]["credential"]["present"] = False
        rewritten = d126._envelope(d126.PREFLIGHT_SCHEMA, "d126preflight_", body)
    tampered = d126._pretty_bytes(rewritten)
    path.write_bytes(tampered)

    with pytest.raises(d126.D126PreflightError):
        d126.validate_d126_preflight_gate(repository=REPOSITORY)
    assert path.read_bytes() == tampered


def test_partial_directory_and_linklike_collisions_are_not_repaired(
    isolated_artifacts: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = isolated_artifacts["receipt"]
    for collision in (b"", b'{"schema_version":', b"unapproved-collision"):
        receipt.write_bytes(collision)
        with pytest.raises(d126.D126PreflightError):
            d126.create_d126_approval_receipt(repository=REPOSITORY)
        assert receipt.read_bytes() == collision
        receipt.unlink()

    receipt.mkdir()
    with pytest.raises(d126.D126PreflightError):
        d126.create_d126_approval_receipt(repository=REPOSITORY)
    assert receipt.is_dir()
    receipt.rmdir()

    target = receipt.with_suffix(".target")
    target.write_bytes(b"D-126 target must remain unchanged")
    try:
        receipt.symlink_to(target)
    except OSError:
        receipt.write_bytes(b"simulated-linklike-output")
        original = d126._is_linklike
        monkeypatch.setattr(
            d126,
            "_is_linklike",
            lambda path: path == receipt or original(path),
        )
    with pytest.raises(d126.D126PreflightError, match="linklike"):
        d126.create_d126_approval_receipt(repository=REPOSITORY)
    assert target.read_bytes() == b"D-126 target must remain unchanged"
    _remove_exact(receipt)
    target.unlink()


def test_clean_source_observation_binds_exact_git_commit_tree_and_rejects_dirty(
    isolated_artifacts: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del isolated_artifacts
    tracked = "100644 blob " + "a" * 40 + "\tAGENTS.md"
    responses = {
        ("status", "--porcelain", "--untracked-files=all"): "",
        ("rev-parse", "HEAD"): SOURCE_COMMIT,
        ("rev-parse", "HEAD^{tree}"): SOURCE_TREE,
        ("rev-parse", "HEAD^"): SOURCE_PARENT,
        ("branch", "--show-current"): "codex/d126-test",
        ("ls-tree", "-r", "--full-tree", "HEAD"): tracked,
    }
    calls: list[tuple[str, ...]] = []

    def fake_git(_root: Path, *args: str) -> str:
        calls.append(args)
        return responses[args]

    monkeypatch.setattr(d126, "_run_git", fake_git)
    observed = d126._git_observation(REPOSITORY)
    assert observed["commit"] == SOURCE_COMMIT
    assert observed["tree"] == SOURCE_TREE
    assert observed["parent"] == SOURCE_PARENT
    assert observed["tracked_tree_listing_sha256"] == sha256_bytes((tracked + "\n").encode())
    assert calls == list(responses)

    monkeypatch.setattr(
        d126,
        "_run_git",
        lambda _root, *_args: " M patchloop/evals/runner.py",
    )
    with pytest.raises(d126.D126PreflightError, match="clean Git worktree"):
        d126._git_observation(REPOSITORY)


def test_production_d126_sealed_historical_bytes_validate_without_current_source_replay() -> None:
    result = d126.validate_d126_preflight_gate(
        repository=REPOSITORY,
        mode="sealed-historical",
    )

    assert result["status"] == d126.BLOCKED_STATUS
    assert result["gate_id"] == d126.SEALED_HISTORICAL_GATE_ID
    assert result["semantic_body_hash"] == d126.SEALED_HISTORICAL_BODY_SHA256
    assert result["file_bytes"] == d126.SEALED_HISTORICAL_FILE_BYTES
    assert result["file_sha256"] == d126.SEALED_HISTORICAL_FILE_SHA256
    assert result["environment_ready_for_execution_hash"] is False
