from __future__ import annotations

import copy
import inspect
import json
from contextlib import nullcontext
from typing import Any

import pytest

from patchloop.evals import d127_docker_remediation as d127
from patchloop.evals import d128_docker_no_start_remediation as d128
from patchloop.util import sha256_bytes


def _cli_binding() -> dict[str, Any]:
    return {
        "file_name": "docker.exe",
        "file_bytes": d128.APPROVED_CLI_BYTES,
        "file_sha256": d128.APPROVED_CLI_SHA256,
        "linklike": False,
    }


def _result(
    tail: tuple[str, ...],
    *,
    stdout: bytes = b"",
    stderr: bytes = b"",
    return_code: int = 0,
    timed_out: bool = False,
) -> d127.BoundedCommandResult:
    return d127.BoundedCommandResult(
        argv=("docker.exe", *tail),
        return_code=return_code,
        timed_out=timed_out,
        stdout_prefix=stdout,
        stderr_prefix=stderr,
        stdout_bytes=len(stdout),
        stderr_bytes=len(stderr),
        stdout_sha256=sha256_bytes(stdout),
        stderr_sha256=sha256_bytes(stderr),
    )


def _present_projection(index: int) -> dict[str, Any]:
    image = d128.EXACT_DOCKER_IMAGES[index]
    return {
        "requested_repo_digest": image,
        "requested_digest": image.rsplit("@", 1)[1],
        "config_id": "sha256:" + str(index + 1) * 64,
        "repo_digests": [image],
        "matched_repo_digest": image,
    }


def _absent_result(index: int) -> d127.BoundedCommandResult:
    image = d128.EXACT_DOCKER_IMAGES[index]
    stderr = f"Error response from daemon: No such image: {image}\n".encode()
    return _result(
        (
            "image",
            "inspect",
            "--format",
            d127.IMAGE_PROJECTION_FORMAT,
            image,
        ),
        stderr=stderr,
        return_code=1,
    )


def _snapshot(
    *,
    daemon: bool = True,
    states: tuple[str, str] = ("present", "present"),
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    daemon_projection = (
        {
            "ClientVersion": d128.APPROVED_CLI_VERSION,
            "ServerVersion": "29.6.2",
            "ServerOs": "linux",
            "ServerArch": "amd64",
        }
        if daemon
        else None
    )
    if daemon_projection is None:
        version_result = _result(
            ("version", "--format", d127.d126.DOCKER_VERSION_FORMAT),
            stderr=b"daemon unavailable\n",
            return_code=1,
        )
    else:
        stdout = (json.dumps(daemon_projection, separators=(",", ":")) + "\n").encode()
        version_result = _result(
            ("version", "--format", d127.d126.DOCKER_VERSION_FORMAT),
            stdout=stdout,
        )

    rows = [version_result.summary("daemon-version")]
    images: dict[str, Any] = {}
    for index, (key, state) in enumerate(zip(("moto", "babel"), states, strict=True)):
        image = d128.EXACT_DOCKER_IMAGES[index]
        tail = (
            "image",
            "inspect",
            "--format",
            d127.IMAGE_PROJECTION_FORMAT,
            image,
        )
        if not daemon:
            result = _result(tail, stderr=b"daemon unavailable\n", return_code=1)
            projection = None
        elif state == "present":
            projection = _present_projection(index)
            stdout = (
                json.dumps(
                    {"Id": projection["config_id"], "RepoDigests": projection["repo_digests"]},
                    separators=(",", ":"),
                )
                + "\n"
            ).encode()
            result = _result(tail, stdout=stdout)
        elif state == "absent":
            result = _absent_result(index)
            projection = d127._confirmed_missing_projection(result, image)
            assert projection is not None
        elif state == "ambiguous":
            result = _result(tail, stderr=b"inspect failed ambiguously\n", return_code=2)
            projection = None
        else:  # pragma: no cover - test helper contract
            raise AssertionError(state)
        rows.append(result.summary(f"image-{key}"))
        images[key] = projection

    observation = {
        "daemon": daemon_projection,
        "images": images,
        "passed": daemon_projection is not None
        and all(d127._image_is_present(images[key]) for key in ("moto", "babel")),
    }
    return observation, rows


@pytest.fixture
def isolated_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    binding = _cli_binding()
    monkeypatch.setattr(d128.d127, "_isolated_docker_config", lambda: nullcontext())
    monkeypatch.setattr(d128.d127, "approved_cli_binding", lambda: dict(binding))
    monkeypatch.setattr(
        d128.d127,
        "_launch_desktop",
        lambda: pytest.fail("D-128 must never launch Docker Desktop"),
    )


def test_ready_daemon_never_starts_or_pulls(
    monkeypatch: pytest.MonkeyPatch,
    isolated_helper: None,
) -> None:
    snapshots = iter((_snapshot(), _snapshot()))
    monkeypatch.setattr(d128.d127, "_observe_readiness", lambda: next(snapshots))
    monkeypatch.setattr(
        d128.d127,
        "_docker_command",
        lambda *_args, **_kwargs: pytest.fail("present images must not be pulled"),
    )

    result = d128.remediate_already_running_docker_environment()

    assert result["passed"] is True
    assert result["observed_blockers"] == []
    assert result["daemon_start_attempted"] is False
    assert result["daemon_start_count"] == 0
    assert result["docker_cli_command_count"] == 6
    assert result["read_only_daemon_or_image_call_count"] == 6
    assert result["image_pull_call_count"] == 0
    assert result["image_store_mutation_count"] == 0
    assert result["container_create_start_run_exec_count"] == 0
    assert result["docker_workload_call_count"] == 0
    assert result["raw_stdout_or_stderr_persisted"] is False


def test_absent_daemon_stops_after_one_readiness_observation(
    monkeypatch: pytest.MonkeyPatch,
    isolated_helper: None,
) -> None:
    calls = 0

    def observe() -> tuple[dict[str, Any], list[dict[str, Any]]]:
        nonlocal calls
        calls += 1
        return _snapshot(daemon=False)

    monkeypatch.setattr(d128.d127, "_observe_readiness", observe)
    monkeypatch.setattr(
        d128.d127,
        "_docker_command",
        lambda *_args, **_kwargs: pytest.fail("daemon absence must not reach pull"),
    )

    result = d128.remediate_already_running_docker_environment()

    assert calls == 1
    assert result["passed"] is False
    assert result["observed_blockers"] == [d128.DAEMON_UNAVAILABLE_BLOCKER]
    assert result["after_observation_performed"] is False
    assert result["after"] == result["before"]
    assert result["docker_cli_command_count"] == 3
    assert result["read_only_daemon_or_image_call_count"] == 3
    assert result["image_pull_call_count"] == 0
    assert result["image_store_mutation_count"] == 0


def test_only_confirmed_absent_exact_digests_are_pulled(
    monkeypatch: pytest.MonkeyPatch,
    isolated_helper: None,
) -> None:
    snapshots = iter(
        (
            _snapshot(states=("absent", "absent")),
            _snapshot(states=("present", "present")),
        )
    )
    monkeypatch.setattr(d128.d127, "_observe_readiness", lambda: next(snapshots))
    calls: list[tuple[tuple[str, ...], int]] = []

    def pull(*tail: str, timeout_seconds: int) -> d127.BoundedCommandResult:
        calls.append((tail, timeout_seconds))
        expected_index = len(calls) - 1
        assert tail == (
            "image",
            "pull",
            "--quiet",
            "--platform",
            "linux/amd64",
            d128.EXACT_DOCKER_IMAGES[expected_index],
        )
        return _result(tail, stdout=(d128.EXACT_DOCKER_IMAGES[expected_index] + "\n").encode())

    monkeypatch.setattr(d128.d127, "_docker_command", pull)

    result = d128.remediate_already_running_docker_environment()

    assert [tail[-1] for tail, _timeout in calls] == list(d128.EXACT_DOCKER_IMAGES)
    assert all(timeout == 1_200 for _tail, timeout in calls)
    assert result["passed"] is True
    assert result["pulled_images"] == list(d128.EXACT_DOCKER_IMAGES)
    assert result["image_pull_call_count"] == 2
    assert result["image_store_mutation_count"] == 2
    assert [row["role"] for row in result["commands"]] == [
        "daemon-version",
        "image-moto",
        "image-babel",
        "pull-moto",
        "pull-babel",
        "daemon-version",
        "image-moto",
        "image-babel",
    ]


def test_ambiguous_inspect_never_authorizes_pull_and_remains_blocked(
    monkeypatch: pytest.MonkeyPatch,
    isolated_helper: None,
) -> None:
    snapshots = iter(
        (
            _snapshot(states=("ambiguous", "present")),
            _snapshot(states=("ambiguous", "present")),
        )
    )
    monkeypatch.setattr(d128.d127, "_observe_readiness", lambda: next(snapshots))
    monkeypatch.setattr(
        d128.d127,
        "_docker_command",
        lambda *_args, **_kwargs: pytest.fail("ambiguous absence must not authorize pull"),
    )

    result = d128.remediate_already_running_docker_environment()

    assert result["passed"] is False
    assert result["observed_blockers"] == [d128.READINESS_BLOCKER]
    assert result["image_pull_call_count"] == 0
    assert result["image_store_mutation_count"] == 0


def test_initial_readiness_rows_are_replayed_before_any_pull(
    monkeypatch: pytest.MonkeyPatch,
    isolated_helper: None,
) -> None:
    before, rows = _snapshot(states=("absent", "present"))
    rows[1]["argv_contract"] = ["docker.exe", "image", "pull", "unexpected"]
    monkeypatch.setattr(d128.d127, "_observe_readiness", lambda: (before, rows))
    monkeypatch.setattr(
        d128.d127,
        "_docker_command",
        lambda *_args, **_kwargs: pytest.fail("invalid pull authority must fail first"),
    )

    with pytest.raises(d128.D128DockerNoStartRemediationError, match="command row"):
        d128.remediate_already_running_docker_environment()


def test_helper_contract_drift_blocks_before_any_docker_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(d128.d127, "ALLOW_DAEMON_START_WITH_UNVERIFIED_RESTART_STATE", True)
    monkeypatch.setattr(
        d128.d127,
        "_observe_readiness",
        lambda: pytest.fail("helper drift must fail before Docker"),
    )

    with pytest.raises(d128.D128DockerNoStartRemediationError, match="permits daemon start"):
        d128.remediate_already_running_docker_environment()


def test_read_only_public_wrappers_delegate_without_start_or_mutation(
    monkeypatch: pytest.MonkeyPatch,
    isolated_helper: None,
) -> None:
    snapshot = {"schema_version": "delegated-read-only-snapshot"}
    calls: list[str] = []

    def observe() -> dict[str, Any]:
        calls.append("observe")
        return snapshot

    def validate(value: Any) -> dict[str, Any]:
        calls.append("validate")
        assert value is snapshot
        return value

    monkeypatch.setattr(d128.d127, "observe_docker_readiness", observe)
    monkeypatch.setattr(d128.d127, "validate_docker_readiness_snapshot", validate)

    assert d128.approved_cli_binding() == _cli_binding()
    assert d128.observe_docker_readiness() is snapshot
    assert d128.validate_docker_readiness_snapshot(snapshot) is snapshot
    assert calls == ["observe", "validate", "validate"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.__setitem__("daemon_start_attempted", True), "start was attempted"),
        (lambda value: value.__setitem__("daemon_start_count", False), "start count"),
        (
            lambda value: value["commands"][0].__setitem__("argv_contract", ["docker.exe", "ps"]),
            "command row",
        ),
        (
            lambda value: value.__setitem__("container_create_start_run_exec_count", 1),
            "container action count",
        ),
        (
            lambda value: value.__setitem__("raw_stdout_or_stderr_persisted", True),
            "raw-output boundary",
        ),
    ],
)
def test_validator_rejects_no_start_scope_or_replay_tamper(
    monkeypatch: pytest.MonkeyPatch,
    isolated_helper: None,
    mutate: Any,
    message: str,
) -> None:
    snapshots = iter((_snapshot(), _snapshot()))
    monkeypatch.setattr(d128.d127, "_observe_readiness", lambda: next(snapshots))
    monkeypatch.setattr(
        d128.d127,
        "_docker_command",
        lambda *_args, **_kwargs: pytest.fail("ready fixture must not pull"),
    )
    result = d128.remediate_already_running_docker_environment()
    tampered = copy.deepcopy(result)
    mutate(tampered)

    with pytest.raises(d128.D128DockerNoStartRemediationError, match=message):
        d128.validate_docker_no_start_remediation_observation(tampered)


def test_module_contains_no_desktop_process_poll_or_container_command_path() -> None:
    source = inspect.getsource(d128)

    for forbidden in (
        "import subprocess",
        "subprocess.",
        "Popen",
        "_launch_desktop(",
        "docker_desktop_path(",
        "time.sleep(",
        '"daemon-version-poll"',
    ):
        assert forbidden not in source
    assert 'container_create_start_run_exec_count": 0' in source
    assert 'docker_workload_call_count": 0' in source
