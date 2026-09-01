from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals.fresh_all_cross_successor import CANDIDATE_IDS
from patchloop.evals.fresh_harbor_partial_preflight import (
    APPROVAL_MESSAGE_SHA256,
    BASE_IMAGE_BY_TASK,
    DOCKER_VERSION_ARGS,
    EXECUTION_HASH,
    AttemptIntent,
    DockerCliBinding,
    ImageRequest,
    TerminalObservation,
    _denied_scope,
    _image_inspect_args,
    _image_requests,
    _jsonable,
    _runner_binding,
    _source_checks,
    build_source_qualification,
    observe_preflight,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _request(task_id: str, ordinal: int) -> ImageRequest:
    body = {
        "task_id": task_id,
        "archive_path": f".tmp/archive-{ordinal}/dist.tar.gz",
        "archive_bytes": 100 + ordinal,
        "archive_sha256": f"sha256:{ordinal:064x}",
        "dockerfile_bytes": 30 + ordinal,
        "dockerfile_sha256": f"sha256:{ordinal + 100:064x}",
        "base_image_ref": BASE_IMAGE_BY_TASK[task_id],
    }
    return ImageRequest(**body, content_hash=sha256_json(body))


def _attempt() -> AttemptIntent:
    requests = tuple(_request(task_id, ordinal) for ordinal, task_id in enumerate(CANDIDATE_IDS, 1))
    body = {
        "schema_version": "lean-fresh-harbor-partial-preflight-attempt-v1",
        "attempt_id": "lean-fresh-harbor-partial-preflight-attempt-20260818-r1",
        "recorded_at": "2026-08-18T00:00:00Z",
        "status": "READ_ONLY_DOCKER_PREFLIGHT_ATTEMPT_RECORDED_BEFORE_CALL",
        "approval_binding": {
            "path": "reports/fresh-panel/artifacts/approval.json",
            "file_bytes": 1,
            "file_sha256": f"sha256:{'a' * 64}",
            "content_hash": f"sha256:{'b' * 64}",
            "role": "exact-user-preflight-approval",
        },
        "runner_candidate_binding": {
            "path": "experiments/runner.json",
            "file_bytes": 1,
            "file_sha256": f"sha256:{'c' * 64}",
            "content_hash": f"sha256:{'d' * 64}",
            "role": "sealed-partial-runner-candidate",
        },
        "execution_hash": EXECUTION_HASH,
        "docker_cli": DockerCliBinding(
            resolved_path="C:/docker.exe",
            file_bytes=43_095_472,
            file_sha256="sha256:8985cd8ac002c3240b5aa48fe401fcb55dca5d849b537e3c835564e8e8c49a70",
        ),
        "docker_context": "desktop-linux",
        "docker_endpoint": "npipe:////./pipe/dockerDesktopLinuxEngine",
        "environment_override_absent": True,
        "image_requests": requests,
        "image_request_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in requests]
        ),
        "version_arguments": DOCKER_VERSION_ARGS,
        "image_inspect_arguments_hash": sha256_json(list(_image_inspect_args(requests))),
        "shell": False,
        "stdin": "closed",
        "maximum_docker_cli_calls": 2,
        "authority": {
            "user_approval_recorded": True,
            "package_archives_read": 12,
            "dockerfiles_read": 12,
            "private_tests_or_reference_patches_read": 0,
            "docker_cli_calls": 0,
            "docker_daemon_calls": 0,
            "network_calls": 0,
            "image_store_mutations": 0,
            "container_mutations": 0,
            "task_evaluator_agent_provider_calls": 0,
            "added_cost_usd": 0,
            "execution_authorized": False,
        },
    }
    return AttemptIntent(**body, content_hash=sha256_json(_jsonable(body)))


def _version_result(return_code: int = 0) -> subprocess.CompletedProcess[bytes]:
    payload = {
        "Client": {"Version": "29.6.2", "ApiVersion": "1.53"},
        "Server": {
            "Version": "29.6.2",
            "ApiVersion": "1.53",
            "Os": "linux",
            "Arch": "amd64",
        },
    }
    return subprocess.CompletedProcess(
        [], return_code, json.dumps(payload).encode(), b"daemon error"
    )


def _image_result(
    attempt: AttemptIntent, return_code: int = 0
) -> subprocess.CompletedProcess[bytes]:
    values = [
        {
            "Id": f"sha256:{ordinal:064x}",
            "Os": "linux",
            "Architecture": "amd64",
            "Size": 1_000 + ordinal,
        }
        for ordinal, _item in enumerate(attempt.image_requests, 1)
    ]
    stderr = b"" if return_code == 0 else attempt.image_requests[0].base_image_ref.encode()
    return subprocess.CompletedProcess([], return_code, json.dumps(values).encode(), stderr)


def test_contract_has_exact_scope_and_no_execution_authority() -> None:
    assert APPROVAL_MESSAGE_SHA256.startswith("sha256:")
    assert _source_checks()["exact-two-command-read-only-docker-surface"] is True
    assert "image-pull-load-build-tag-remove-or-prune" in _denied_scope()


def test_source_and_twelve_dockerfiles_validate_without_docker() -> None:
    source = build_source_qualification(REPOSITORY)
    _binding, candidate = _runner_binding(REPOSITORY)
    requests = _image_requests(REPOSITORY, candidate)

    assert source.runner_candidate_binding.content_hash.startswith("sha256:")
    assert source.authority.docker_cli_calls == source.authority.docker_daemon_calls == 0
    assert tuple(item.task_id for item in requests) == CANDIDATE_IDS
    assert tuple(item.base_image_ref for item in requests) == tuple(BASE_IMAGE_BY_TASK.values())


def test_success_observes_only_version_and_one_bulk_inspect() -> None:
    attempt = _attempt()
    calls: list[tuple[str, ...]] = []

    def runner(arguments: tuple[str, ...], _timeout: int) -> subprocess.CompletedProcess[bytes]:
        calls.append(arguments)
        return _version_result() if len(calls) == 1 else _image_result(attempt)

    terminal = observe_preflight(attempt, "2026-08-18T00:01:00Z", runner)

    assert calls == [DOCKER_VERSION_ARGS, _image_inspect_args(attempt.image_requests)]
    assert terminal.status == "READ_ONLY_DOCKER_PREFLIGHT_PASS"
    assert len(terminal.images) == 12
    assert terminal.authority.docker_daemon_read_calls == 2
    assert terminal.authority.image_pull_or_build_calls == 0
    assert terminal.authority.container_create_start_run_exec_calls == 0
    assert terminal.authority.execution_authorized is False


def test_daemon_failure_stops_before_image_inspect() -> None:
    attempt = _attempt()
    calls: list[tuple[str, ...]] = []

    def runner(arguments: tuple[str, ...], _timeout: int) -> subprocess.CompletedProcess[bytes]:
        calls.append(arguments)
        return _version_result(return_code=1)

    terminal = observe_preflight(attempt, "2026-08-18T00:01:00Z", runner)
    assert calls == [DOCKER_VERSION_ARGS]
    assert terminal.status == "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_DAEMON"
    assert terminal.image_inspect_command is None
    assert terminal.authority.docker_cli_calls == 1


def test_missing_image_is_terminal_and_grants_no_remediation() -> None:
    attempt = _attempt()
    results = iter((_version_result(), _image_result(attempt, return_code=1)))

    terminal = observe_preflight(
        attempt,
        "2026-08-18T00:01:00Z",
        lambda _arguments, _timeout: next(results),
    )
    assert terminal.status == "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_IMAGES"
    assert terminal.missing_refs_identified_from_stderr == (
        attempt.image_requests[0].base_image_ref,
    )
    assert terminal.next_gate == "obtain-separate-local-image-readiness-remediation-authority"
    assert terminal.authority.image_store_mutations == 0


def test_rehashed_attempt_or_terminal_authority_drift_is_rejected() -> None:
    attempt = _attempt()
    body = attempt.model_dump(mode="json")
    body["maximum_docker_cli_calls"] = 3
    body["content_hash"] = sha256_json({k: v for k, v in body.items() if k != "content_hash"})
    with pytest.raises(ValidationError):
        AttemptIntent.model_validate(body)

    results = iter((_version_result(), _image_result(attempt)))
    terminal = observe_preflight(
        attempt,
        "2026-08-18T00:01:00Z",
        lambda _arguments, _timeout: next(results),
    )
    body = terminal.model_dump(mode="json")
    body["authority"]["execution_authorized"] = True
    body["content_hash"] = sha256_json({k: v for k, v in body.items() if k != "content_hash"})
    with pytest.raises(ValidationError):
        TerminalObservation.model_validate(body)
