from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from patchloop.evals import d127_d126_successor_no_call_preflight as d127
from patchloop.util import canonical_json, sha256_bytes, sha256_text


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / d127.RECEIPT_PATH.parent).mkdir(parents=True)
    (tmp_path / "patchloop/agent").mkdir(parents=True)
    gate = Path(__file__).resolve().parents[1] / d127.D126_GATE_PATH
    (tmp_path / d127.D126_GATE_PATH).write_bytes(gate.read_bytes())
    monkeypatch.setattr(
        d127.d126,
        "validate_d126_preflight_gate",
        lambda **_kwargs: {
            "gate_id": d127.D126_GATE_ID,
            "semantic_body_hash": d127.D126_BODY_SHA256,
            "file_bytes": d127.D126_FILE_BYTES,
            "file_sha256": d127.D126_FILE_SHA256,
        },
    )
    return tmp_path


def _factory_source() -> str:
    return '''\
import httpx
from openai import OpenAI
OFFICIAL_API_BASE_URL = "https://api.openai.com/v1"
def create_openai_client(config):
    http_client = httpx.Client(trust_env=False)
    constructor_kwargs: dict = {
        "base_url": OFFICIAL_API_BASE_URL,
        "http_client": http_client,
    }
    if config.transport_max_retries is not None:
        constructor_kwargs["max_retries"] = config.transport_max_retries
    try:
        return OpenAI(**constructor_kwargs)
    except BaseException:
        http_client.close()
        raise
class OpenAIResponsesAdapter:
    def __init__(self, config, client=None):
        self.client = client if client is not None else create_openai_client(config)
'''


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _commit_all(repository: Path, message: str = "D127 test source") -> None:
    if not (repository / ".git").exists():
        _git(repository, "init", "-b", "codex/d127-test")
        _git(repository, "config", "user.email", "d127-test@example.invalid")
        _git(repository, "config", "user.name", "D127 Test")
        _git(repository, "config", "core.autocrlf", "false")
        _git(repository, "config", "core.safecrlf", "false")
        _git(repository, "config", "core.filemode", "false")
    _git(repository, "add", "--all")
    _git(repository, "commit", "-m", message)


def _prepare_success(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    d127.create_d127_approval_receipt(repository=repository)
    (repository / "patchloop/agent/model.py").write_text(_factory_source(), encoding="utf-8")
    _commit_all(repository)
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-never-rendered")
    for name in d127.FORBIDDEN_ROUTING_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name in d127.FORBIDDEN_PYTHON_ROUTING_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        d127,
        "_approved_docker_cli_identity",
        lambda: {
            "file_name": "docker.exe",
            "file_bytes": d127.DOCKER_CLI_BYTES,
            "file_sha256": d127.DOCKER_CLI_SHA256,
            "approved_version": d127.DOCKER_CLI_VERSION,
            "version_bound_by_exact_approved_file_identity": True,
            "version_process_observation_performed": False,
        },
    )


def _mock_external_run_boundaries(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    remediation_passed: bool = True,
) -> tuple[dict[str, int], dict[str, Any]]:
    timestamp = "2026-08-09T00:00:00Z"
    monkeypatch.setattr(d127, "_now", lambda: timestamp)
    d127.create_d127_approval_receipt(repository=repository)
    source: dict[str, object] = {
        "commit": "a" * 40,
        "tree": "b" * 40,
        "parents": ["c" * 40],
        "branch": "codex/d127-test",
        "source_paths_and_index_clean": True,
        "git_cli_observation": {},
    }
    factory = {key: True for key in d127.MODEL_FACTORY_CHECK_KEYS}
    cli = {
        "file_name": "docker.exe",
        "file_bytes": d127.DOCKER_CLI_BYTES,
        "file_sha256": d127.DOCKER_CLI_SHA256,
        "approved_version": d127.DOCKER_CLI_VERSION,
        "version_bound_by_exact_approved_file_identity": True,
        "version_process_observation_performed": False,
    }
    remediation = {
        "passed": remediation_passed,
        "desktop_start_count": 0,
        "desktop_start_skipped_reason": (
            None if remediation_passed else d127.DAEMON_START_SKIPPED_REASON
        ),
        "image_store_mutation_count": 0,
        "docker_cli_command_count": 6,
        "exact_authorized_images": list(d127.DOCKER_IMAGE_REFS),
    }
    evidence = {
        "observed_at": timestamp,
        "public_get_request_count": 1,
    }
    snapshot = {
        "observation": {"passed": True},
        "docker_cli_command_count": 3,
    }
    sdk = {"passed": True, "network_call_count": 0}
    calls = {"remediation": 0, "pricing": 0, "snapshot": 0}
    state: dict[str, Any] = {"source": source, "events": []}

    def remediate() -> dict[str, object]:
        calls["remediation"] += 1
        state["events"].append("remediation")
        return json.loads(json.dumps(remediation))

    def capture() -> dict[str, object]:
        calls["pricing"] += 1
        state["events"].append("pricing")
        return json.loads(json.dumps(evidence))

    def observe() -> dict[str, object]:
        calls["snapshot"] += 1
        state["events"].append("snapshot")
        return json.loads(json.dumps(snapshot))

    monkeypatch.setattr(
        d127,
        "_check_static_prerequisites",
        lambda _root, *, allowed_outputs: {
            "source": state["source"],
            "production_model_factory_checks": factory,
        },
    )
    monkeypatch.setattr(d127, "_require_receipt_tracked_at_head", lambda *_a, **_k: None)
    monkeypatch.setattr(d127, "_require_current_source", lambda *_a, **_k: None)
    monkeypatch.setattr(d127, "_validate_source_identity", lambda *_a, **_k: None)
    monkeypatch.setattr(d127, "_loaded_module_bindings", lambda *_a, **_k: [])
    monkeypatch.setattr(d127, "_validate_loaded_module_bindings", lambda *_a, **_k: None)
    monkeypatch.setattr(d127, "_require_modules_unchanged", lambda *_a, **_k: None)
    monkeypatch.setattr(d127, "_approved_docker_cli_identity", lambda: dict(cli))
    monkeypatch.setattr(d127, "_model_factory_contract", lambda _root: dict(factory))
    monkeypatch.setattr(d127, "_sdk_observation", lambda *_a, **_k: dict(sdk))
    monkeypatch.setattr(d127, "_validate_sdk_observation", lambda *_a, **_k: None)
    monkeypatch.setattr(
        d127,
        "_require_current_sdk_matches_artifact",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        d127.docker_remediation,
        "validate_docker_remediation_observation",
        lambda value: value,
    )
    monkeypatch.setattr(
        d127.docker_remediation,
        "validate_docker_readiness_snapshot",
        lambda value: value,
    )
    monkeypatch.setattr(
        d127.pricing_capture,
        "validate_official_pricing_evidence",
        lambda value: value,
    )
    monkeypatch.setattr(d127.docker_remediation, "remediate_docker_environment", remediate)
    monkeypatch.setattr(d127.docker_remediation, "observe_docker_readiness", observe)
    monkeypatch.setattr(d127.pricing_capture, "capture_official_pricing_evidence", capture)
    return calls, state


def _rewrite_artifact(
    repository: Path,
    relative: Path,
    *,
    schema: str,
    prefix: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    path = repository / relative
    payload = json.loads(path.read_bytes())
    mutate(payload["semantic_body"])
    rewritten = d127._artifact_envelope(schema, prefix, payload["semantic_body"])
    path.write_bytes(d127._pretty_bytes(rewritten))


def test_receipt_binds_exact_d126_scope_cli_and_two_images_canonically(
    repository: Path,
) -> None:
    result = d127.create_d127_approval_receipt(repository=repository)
    raw = (repository / d127.RECEIPT_PATH).read_bytes()
    payload = json.loads(raw)
    body = payload["semantic_body"]

    assert body["predecessor_binding"] == {
        "path": d127.D126_GATE_PATH.as_posix(),
        "gate_id": d127.D126_GATE_ID,
        "semantic_body_hash": d127.D126_BODY_SHA256,
        "file_bytes": d127.D126_FILE_BYTES,
        "file_sha256": d127.D126_FILE_SHA256,
        "status": d127.D126_STATUS,
        "artifact_mutated": False,
    }
    assert body["approval"]["approved_scope"] == list(d127.APPROVED_SCOPE)
    assert body["approval"]["explicitly_not_authorized"] == list(d127.NOT_AUTHORIZED)
    assert body["approval"]["approved_docker_cli"] == {
        "version": "29.6.2",
        "file_bytes": 43_095_472,
        "file_sha256": d127.DOCKER_CLI_SHA256,
    }
    assert body["approval"]["approved_exact_image_refs"] == list(d127.DOCKER_IMAGE_REFS)
    assert len(body["approval"]["approved_exact_image_refs"]) == 2
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(body))
    assert raw == d127._pretty_bytes(payload)
    assert result == d127.create_d127_approval_receipt(repository=repository)
    assert (repository / d127.RECEIPT_PATH).read_bytes() == raw


def test_receipt_rejects_d126_constant_drift_without_output(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(d127.d126, "SEALED_HISTORICAL_FILE_SHA256", "sha256:" + "0" * 64)
    with pytest.raises(d127.D127PreflightError, match="sealed constants differ"):
        d127.create_d127_approval_receipt(repository=repository)
    assert not (repository / d127.RECEIPT_PATH).exists()


def test_receipt_collision_is_never_repaired_or_overwritten(repository: Path) -> None:
    path = repository / d127.RECEIPT_PATH
    collision = b"unapproved-existing-bytes"
    path.write_bytes(collision)
    with pytest.raises(d127.D127PreflightError):
        d127.create_d127_approval_receipt(repository=repository)
    assert path.read_bytes() == collision


def test_static_prerequisites_are_complete_secret_safe_and_zero_call(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_success(repository, monkeypatch)
    monkeypatch.setattr(
        d127.docker_remediation,
        "remediate_docker_environment",
        lambda: pytest.fail("static check must not run Docker remediation"),
    )
    monkeypatch.setattr(
        d127.docker_remediation,
        "observe_docker_readiness",
        lambda: pytest.fail("static check must not invoke Docker"),
    )
    monkeypatch.setattr(
        d127.pricing_capture,
        "capture_official_pricing_evidence",
        lambda: pytest.fail("static check must not access the network"),
    )
    result = d127.check_d127_static_prerequisites(repository=repository)
    rendered = canonical_json(result)

    assert result["status"] == d127.STATIC_READY_STATUS
    assert result["credential"]["present"] is True
    assert result["source"]["source_paths_and_index_clean"] is True
    assert result["docker_cli"]["file_sha256"] == d127.DOCKER_CLI_SHA256
    assert all(result["production_model_factory_checks"].values())
    assert set(result["external_activity"].values()) == {0}
    assert result["external_remediation_or_repeated_preflight_implemented"] is True
    assert result["artifact_created_by_static_check"] is False
    assert "test-secret-never-rendered" not in rendered


def test_approved_docker_identity_is_checked_from_bytes_without_process_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker = tmp_path / "Programs/DockerDesktop/resources/bin/docker.exe"
    docker.parent.mkdir(parents=True)
    content = b"synthetic-exact-docker-cli"
    docker.write_bytes(content)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("PATCHLOOP_DOCKER_CLI", raising=False)
    monkeypatch.setattr(d127, "DOCKER_CLI_BYTES", len(content))
    monkeypatch.setattr(d127, "DOCKER_CLI_SHA256", sha256_bytes(content))
    monkeypatch.setattr(
        d127.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("Docker process must not be invoked"),
    )

    result = d127._approved_docker_cli_identity()

    assert result["file_name"] == "docker.exe"
    assert result["file_bytes"] == len(content)
    assert result["file_sha256"] == sha256_bytes(content)
    assert result["approved_version"] == "29.6.2"
    assert result["version_process_observation_performed"] is False


@pytest.mark.parametrize("failure", ["dirty", "credential", "routing", "docker", "factory"])
def test_static_prerequisites_fail_closed(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    _prepare_success(repository, monkeypatch)
    if failure == "dirty":
        (repository / "patchloop/agent/model.py").write_text(
            _factory_source() + "\n# dirty\n",
            encoding="utf-8",
        )
    elif failure == "credential":
        monkeypatch.delenv("OPENAI_API_KEY")
    elif failure == "routing":
        monkeypatch.setenv("HTTPS_PROXY", "https://unapproved.invalid")
    elif failure == "docker":
        monkeypatch.setattr(
            d127,
            "_approved_docker_cli_identity",
            lambda: (_ for _ in ()).throw(d127.D127PreflightError("Docker CLI SHA differs")),
        )
    else:
        (repository / "patchloop/agent/model.py").write_text(
            _factory_source().replace("trust_env=False", "trust_env=True"),
            encoding="utf-8",
        )
        _commit_all(repository, "Commit invalid factory")

    with pytest.raises(d127.D127PreflightError):
        d127.check_d127_static_prerequisites(repository=repository)


def test_receipt_creation_rejects_orphaned_downstream_output(repository: Path) -> None:
    path = repository / d127.REMEDIATION_ATTEMPT_PATH
    collision = b"orphaned-attempt-must-remain"
    path.write_bytes(collision)

    with pytest.raises(d127.D127PreflightError, match="downstream evidence"):
        d127.create_d127_approval_receipt(repository=repository)

    assert path.read_bytes() == collision
    assert not (repository / d127.RECEIPT_PATH).exists()


def test_static_check_creates_no_artifact_beyond_existing_receipt(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_success(repository, monkeypatch)
    before = {
        path.relative_to(repository).as_posix(): sha256_bytes(path.read_bytes())
        for path in repository.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repository).parts
    }
    d127.check_d127_static_prerequisites(repository=repository)
    after = {
        path.relative_to(repository).as_posix(): sha256_bytes(path.read_bytes())
        for path in repository.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repository).parts
    }
    assert after == before


def test_external_run_builds_bound_gate_in_order_and_resumes_without_calls(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, state = _mock_external_run_boundaries(repository, monkeypatch)

    first = d127.run_d127_external_remediation_and_preflight(repository=repository)

    assert first["status"] == d127.GATE_READY_STATUS
    assert first["environment_ready_for_execution_hash"] is True
    assert calls == {"remediation": 1, "pricing": 1, "snapshot": 2}
    assert state["events"] == ["remediation", "pricing", "snapshot", "snapshot"]
    before = {
        path: (repository / path).read_bytes() for path in d127._EXTERNAL_OUTPUT_PATHS
    }

    second = d127.run_d127_external_remediation_and_preflight(repository=repository)

    assert second == first
    assert calls == {"remediation": 1, "pricing": 1, "snapshot": 2}
    assert before == {
        path: (repository / path).read_bytes() for path in d127._EXTERNAL_OUTPUT_PATHS
    }
    assert d127.validate_d127_no_call_gate(repository=repository) == first

    def reject_ambient(*_args: object, **_kwargs: object) -> None:
        raise d127.D127PreflightError("ambient current SDK differs")

    monkeypatch.setattr(d127, "_require_current_sdk_matches_artifact", reject_ambient)
    with pytest.raises(d127.D127PreflightError, match="ambient current SDK differs"):
        d127.validate_d127_no_call_gate(repository=repository, mode="current-source")
    monkeypatch.setattr(
        d127,
        "_post_evidence_commit_state",
        lambda _root, source: {
            "head": "d" * 40,
            "source_commit": source["commit"],
            "changed_paths": [path.as_posix() for path in d127._EXTERNAL_OUTPUT_PATHS],
        },
    )
    post = d127.validate_d127_no_call_gate(
        repository=repository,
        mode="post-evidence-commit",
    )
    assert post["status"] == d127.GATE_READY_STATUS
    assert post["post_commit"]["source_commit"] == "a" * 40


def test_blocked_remediation_is_terminal_for_receipt_and_never_gets_pricing(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, state = _mock_external_run_boundaries(
        repository,
        monkeypatch,
        remediation_passed=False,
    )

    first = d127.run_d127_external_remediation_and_preflight(repository=repository)
    second = d127.run_d127_external_remediation_and_preflight(repository=repository)

    assert first == second
    assert first["status"] == d127.REMEDIATION_BLOCKED_STATUS
    assert first["observed_blockers"] == [d127.DAEMON_START_SKIPPED_REASON]
    assert calls == {"remediation": 1, "pricing": 0, "snapshot": 0}
    assert state["events"] == ["remediation"]
    assert (repository / d127.REMEDIATION_ATTEMPT_PATH).is_file()
    assert (repository / d127.REMEDIATION_PATH).is_file()
    assert not (repository / d127.PRICING_ATTEMPT_PATH).exists()
    assert not (repository / d127.GATE_PATH).exists()


def test_orphaned_attempt_blocks_retry_after_uncertain_external_failure(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, _state = _mock_external_run_boundaries(repository, monkeypatch)

    def fail_after_attempt() -> dict[str, object]:
        calls["remediation"] += 1
        raise RuntimeError("uncertain Docker boundary failure")

    monkeypatch.setattr(
        d127.docker_remediation,
        "remediate_docker_environment",
        fail_after_attempt,
    )
    with pytest.raises(RuntimeError, match="uncertain Docker boundary failure"):
        d127.run_d127_external_remediation_and_preflight(repository=repository)
    assert (repository / d127.REMEDIATION_ATTEMPT_PATH).is_file()
    assert not (repository / d127.REMEDIATION_PATH).exists()

    with pytest.raises(d127.D127PreflightError, match="orphaned docker-remediation"):
        d127.run_d127_external_remediation_and_preflight(repository=repository)
    assert calls == {"remediation": 1, "pricing": 0, "snapshot": 0}


@pytest.mark.parametrize(
    ("path", "message"),
    [
        (d127.REMEDIATION_PATH, "terminal exists without attempt"),
        (d127.PRICING_ATTEMPT_PATH, "before its predecessor phase completed"),
    ],
)
def test_existing_phase_order_violations_fail_before_validation(
    repository: Path,
    path: Path,
    message: str,
) -> None:
    d127.create_d127_approval_receipt(repository=repository)
    (repository / path).write_bytes(b"orphaned-order-evidence")

    with pytest.raises(d127.D127PreflightError, match=message):
        d127._validated_existing_outputs(repository)


def test_attempt_content_drift_blocks_before_first_docker_action(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, _state = _mock_external_run_boundaries(repository, monkeypatch)
    create = d127._create_attempt_artifact

    def create_then_drift(*args: object, **kwargs: object) -> dict[str, Any]:
        payload = create(*args, **kwargs)
        _rewrite_artifact(
            repository,
            d127.REMEDIATION_ATTEMPT_PATH,
            schema=d127.ATTEMPT_SCHEMA,
            prefix="d127dockerremediationattempt_",
            mutate=lambda body: body.update({"recorded_at": "2026-08-09T00:00:01Z"}),
        )
        return payload

    monkeypatch.setattr(d127, "_create_attempt_artifact", create_then_drift)
    with pytest.raises(d127.D127PreflightError, match="attempt changed"):
        d127.run_d127_external_remediation_and_preflight(repository=repository)
    assert calls == {"remediation": 0, "pricing": 0, "snapshot": 0}


def test_existing_source_drift_and_helper_constant_drift_block_before_action(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, state = _mock_external_run_boundaries(repository, monkeypatch)
    source = state["source"]
    attempt = d127._create_attempt_artifact(
        repository,
        phase="docker-remediation",
        source=source,
        module_bindings=[],
    )
    observation = {
        "passed": True,
        "desktop_start_count": 0,
        "desktop_start_skipped_reason": None,
        "image_store_mutation_count": 0,
        "docker_cli_command_count": 6,
        "exact_authorized_images": list(d127.DOCKER_IMAGE_REFS),
    }
    d127._write_remediation_terminal(
        repository,
        source=source,
        observation=observation,
        expected_attempt=attempt,
    )
    state["source"] = {**source, "commit": "d" * 40}

    with pytest.raises(d127.D127PreflightError, match="existing artifact source differs"):
        d127.run_d127_external_remediation_and_preflight(repository=repository)
    assert calls == {"remediation": 0, "pricing": 0, "snapshot": 0}

    fresh = repository / "fresh"
    fresh.mkdir()
    fresh_repository = repository / "fresh"
    (fresh_repository / d127.RECEIPT_PATH.parent).mkdir(parents=True)
    (fresh_repository / d127.D126_GATE_PATH).write_bytes(
        (repository / d127.D126_GATE_PATH).read_bytes()
    )
    drift_calls, _ = _mock_external_run_boundaries(fresh_repository, monkeypatch)
    monkeypatch.setattr(
        d127.docker_remediation,
        "APPROVED_CLI_SHA256",
        "sha256:" + "0" * 64,
    )
    with pytest.raises(d127.D127PreflightError, match="helper constants differ"):
        d127.run_d127_external_remediation_and_preflight(repository=fresh_repository)
    assert drift_calls == {"remediation": 0, "pricing": 0, "snapshot": 0}
    assert not (fresh_repository / d127.REMEDIATION_ATTEMPT_PATH).exists()


def test_recomputed_nested_gate_tamper_and_cross_phase_time_inversion_fail(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_external_run_boundaries(repository, monkeypatch)
    d127.run_d127_external_remediation_and_preflight(repository=repository)

    original_gate = (repository / d127.GATE_PATH).read_bytes()
    _rewrite_artifact(
        repository,
        d127.GATE_PATH,
        schema=d127.GATE_SCHEMA,
        prefix="d127_",
        mutate=lambda body: body["authority"].update(
            {"execution_hash_authorized_or_created": True}
        ),
    )
    with pytest.raises(d127.D127PreflightError, match="gate body differs"):
        d127.validate_d127_no_call_gate(repository=repository)

    (repository / d127.GATE_PATH).write_bytes(original_gate)
    _rewrite_artifact(
        repository,
        d127.REMEDIATION_PATH,
        schema=d127.REMEDIATION_SCHEMA,
        prefix="d127remediation_",
        mutate=lambda body: body.update({"recorded_at": "2026-08-09T00:00:02Z"}),
    )
    _rewrite_artifact(
        repository,
        d127.PRICING_ATTEMPT_PATH,
        schema=d127.ATTEMPT_SCHEMA,
        prefix="d127officialpricingcaptureattempt_",
        mutate=lambda body: body.update({"recorded_at": "2026-08-09T00:00:01Z"}),
    )
    _rewrite_artifact(
        repository,
        d127.PRICING_PATH,
        schema=d127.PRICING_SCHEMA,
        prefix="d127pricing_",
        mutate=lambda body: body.update(
            {"attempt_binding": d127._artifact_binding(repository, d127.PRICING_ATTEMPT_PATH)}
        ),
    )
    with pytest.raises(d127.D127PreflightError, match="predates remediation terminal"):
        d127._validate_pricing_artifact(repository)


def _postcommit_repository(
    root: Path,
    *,
    preexisting_output: Path | None = None,
    unexpected_source_change: bool = False,
) -> tuple[Path, dict[str, Any]]:
    root.mkdir(parents=True)
    (root / "seed.txt").write_text("source\n", encoding="utf-8")
    if preexisting_output is not None:
        (root / preexisting_output).parent.mkdir(parents=True, exist_ok=True)
        (root / preexisting_output).write_text("preexisting\n", encoding="utf-8")
    _commit_all(root, "source")
    source = d127._source_identity(root)
    for path in d127._EXTERNAL_OUTPUT_PATHS:
        selected = root / path
        selected.parent.mkdir(parents=True, exist_ok=True)
        selected.write_text(f"successor:{path.as_posix()}\n", encoding="utf-8")
    if unexpected_source_change:
        selected = root / "patchloop/agent/model.py"
        selected.parent.mkdir(parents=True, exist_ok=True)
        selected.write_text("unexpected source\n", encoding="utf-8")
    _commit_all(root, "evidence")
    return root, source


def test_postcommit_requires_single_parent_new_only_outputs_and_exact_scope(
    tmp_path: Path,
) -> None:
    valid_root, valid_source = _postcommit_repository(tmp_path / "valid")
    result = d127._post_evidence_commit_state(valid_root, valid_source)
    assert set(result["changed_paths"]) == {
        path.as_posix() for path in d127._EXTERNAL_OUTPUT_PATHS
    }

    replacement_root, replacement_source = _postcommit_repository(
        tmp_path / "replacement",
        preexisting_output=d127.REMEDIATION_ATTEMPT_PATH,
    )
    with pytest.raises(d127.D127PreflightError, match="not newly added"):
        d127._post_evidence_commit_state(replacement_root, replacement_source)

    scope_root, scope_source = _postcommit_repository(
        tmp_path / "scope",
        unexpected_source_change=True,
    )
    with pytest.raises(d127.D127PreflightError, match="changed source paths"):
        d127._post_evidence_commit_state(scope_root, scope_source)
