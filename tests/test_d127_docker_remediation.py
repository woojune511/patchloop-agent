from __future__ import annotations

import json
import os
from typing import Any

import pytest

from patchloop.evals import d127_docker_remediation as remediation
from patchloop.util import sha256_bytes


def _result(
    argv: tuple[str, ...],
    *,
    stdout: bytes = b"",
    stderr: bytes = b"",
    return_code: int = 0,
) -> remediation.BoundedCommandResult:
    return remediation.BoundedCommandResult(
        argv=argv,
        return_code=return_code,
        timed_out=False,
        stdout_prefix=stdout,
        stderr_prefix=stderr,
        stdout_bytes=len(stdout),
        stderr_bytes=len(stderr),
        stdout_sha256=sha256_bytes(stdout),
        stderr_sha256=sha256_bytes(stderr),
    )


def _daemon_result() -> remediation.BoundedCommandResult:
    stdout = (
        json.dumps(
            {
                "ClientVersion": remediation.APPROVED_CLI_VERSION,
                "ServerVersion": "29.6.2",
                "ServerOs": "linux",
                "ServerArch": "amd64",
            },
            separators=(",", ":"),
        )
        + "\n"
    ).encode()
    return _result(
        ("docker.exe", "version", "--format", remediation.d126.DOCKER_VERSION_FORMAT),
        stdout=stdout,
    )


def _ready(label: str = "ready") -> dict[str, Any]:
    del label
    images: dict[str, Any] = {}
    for key, image, config in zip(
        ("moto", "babel"),
        remediation.DOCKER_IMAGES,
        ("a", "b"),
        strict=True,
    ):
        images[key] = {
            "requested_repo_digest": image,
            "requested_digest": image.rsplit("@", 1)[1],
            "config_id": "sha256:" + config * 64,
            "repo_digests": [image.removeprefix("docker.io/")],
            "matched_repo_digest": image.removeprefix("docker.io/"),
        }
    return {
        "daemon": {
            "ClientVersion": remediation.APPROVED_CLI_VERSION,
            "ServerVersion": "29.6.2",
            "ServerOs": "linux",
            "ServerArch": "amd64",
        },
        "images": images,
        "passed": True,
    }


def _confirmed_absent(image: str, *, stdout: bytes = b"") -> dict[str, Any]:
    stderr = f"Error response from daemon: No such image: {image}\n".encode()
    return {
        "state": "confirmed-absent",
        "requested_repo_digest": image,
        "absence_code": "exact-docker-no-such-image",
        "stdout_bytes": len(stdout),
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_bytes": len(stderr),
        "stderr_sha256": sha256_bytes(stderr),
    }


def _missing(*, daemon: bool, confirmed_absent: bool = False) -> dict[str, Any]:
    return {
        "daemon": _ready()["daemon"] if daemon else None,
        "images": {
            key: (_confirmed_absent(image) if confirmed_absent else None)
            for key, image in zip(("moto", "babel"), remediation.DOCKER_IMAGES, strict=True)
        },
        "passed": False,
    }


def _cli_binding() -> dict[str, Any]:
    return {
        "file_name": "docker.exe",
        "file_bytes": remediation.APPROVED_CLI_BYTES,
        "file_sha256": remediation.APPROVED_CLI_SHA256,
        "linklike": False,
    }


def _ready_rows() -> list[dict[str, Any]]:
    ready = _ready()
    rows = [_daemon_result().summary("daemon-version")]
    for key, image in zip(("moto", "babel"), remediation.DOCKER_IMAGES, strict=True):
        stdout = (
            json.dumps(
                {
                    "Id": ready["images"][key]["config_id"],
                    "RepoDigests": ready["images"][key]["repo_digests"],
                },
                separators=(",", ":"),
            )
            + "\n"
        ).encode()
        rows.append(
            _result(
                (
                    "docker.exe",
                    "image",
                    "inspect",
                    "--format",
                    remediation.IMAGE_PROJECTION_FORMAT,
                    image,
                ),
                stdout=stdout,
            ).summary(f"image-{key}")
        )
    return rows


def _missing_rows() -> list[dict[str, Any]]:
    rows = [
        _result(
            ("docker.exe", "version", "--format", remediation.d126.DOCKER_VERSION_FORMAT),
            return_code=1,
        ).summary("daemon-version")
    ]
    for key, image in zip(("moto", "babel"), remediation.DOCKER_IMAGES, strict=True):
        rows.append(
            _result(
                (
                    "docker.exe",
                    "image",
                    "inspect",
                    "--format",
                    remediation.IMAGE_PROJECTION_FORMAT,
                    image,
                ),
                return_code=1,
            ).summary(f"image-{key}")
        )
    return rows


def _ambiguous_image_error_rows() -> list[dict[str, Any]]:
    rows = [_daemon_result().summary("daemon-version")]
    for key, image in zip(("moto", "babel"), remediation.DOCKER_IMAGES, strict=True):
        rows.append(
            _result(
                (
                    "docker.exe",
                    "image",
                    "inspect",
                    "--format",
                    remediation.IMAGE_PROJECTION_FORMAT,
                    image,
                ),
                stderr=b"permission denied\n",
                return_code=1,
            ).summary(f"image-{key}")
        )
    return rows


def test_readiness_uses_exact_version_and_two_repo_digest_projections(monkeypatch) -> None:
    calls: list[tuple[tuple[str, ...], int]] = []

    def fake_command(*tail: str, timeout_seconds: int = 30):
        calls.append((tail, timeout_seconds))
        if tail[0] == "version":
            return _daemon_result()
        image = tail[-1]
        config_id = "sha256:" + ("a" if image == remediation.DOCKER_IMAGES[0] else "b") * 64
        printed = image.removeprefix("docker.io/")
        stdout = json.dumps(
            {"Id": config_id, "RepoDigests": [printed]},
            separators=(",", ":"),
        ).encode()
        return _result(("docker.exe", *tail), stdout=stdout)

    monkeypatch.setattr(remediation, "_docker_command", fake_command)
    observed, rows = remediation._observe_readiness()

    assert observed["passed"] is True
    assert observed["images"]["moto"]["requested_digest"].startswith("sha256:")
    assert observed["images"]["moto"]["config_id"] == "sha256:" + "a" * 64
    assert observed["images"]["babel"]["config_id"] == "sha256:" + "b" * 64
    assert len(rows) == 3
    assert calls == [
        (("version", "--format", remediation.d126.DOCKER_VERSION_FORMAT), 30),
        (
            (
                "image",
                "inspect",
                "--format",
                remediation.IMAGE_PROJECTION_FORMAT,
                remediation.DOCKER_IMAGES[0],
            ),
            30,
        ),
        (
            (
                "image",
                "inspect",
                "--format",
                remediation.IMAGE_PROJECTION_FORMAT,
                remediation.DOCKER_IMAGES[1],
            ),
            30,
        ),
    ]


def test_only_exact_no_such_image_response_is_confirmed_absent(monkeypatch) -> None:
    def fake_command(*tail: str, timeout_seconds: int = 30):
        del timeout_seconds
        if tail[0] == "version":
            return _daemon_result()
        image = tail[-1]
        stderr = f"Error response from daemon: No such image: {image}\n".encode()
        return _result(("docker.exe", *tail), stdout=b"\n", stderr=stderr, return_code=1)

    monkeypatch.setattr(remediation, "_docker_command", fake_command)

    observed, rows = remediation._observe_readiness()

    assert observed["passed"] is False
    assert observed["images"] == {
        key: _confirmed_absent(image, stdout=b"\n")
        for key, image in zip(("moto", "babel"), remediation.DOCKER_IMAGES, strict=True)
    }
    remediation._validate_readiness_rows(observed, rows)


def test_ready_environment_does_not_start_desktop_or_pull(monkeypatch) -> None:
    binding = _cli_binding()
    monkeypatch.setattr(remediation, "approved_cli_binding", lambda: binding)
    monkeypatch.setattr(remediation, "_observe_readiness", lambda: (_ready(), _ready_rows()))
    monkeypatch.setattr(
        remediation,
        "_launch_desktop",
        lambda: pytest.fail("ready daemon must not be started"),
    )
    monkeypatch.setattr(
        remediation,
        "_docker_command",
        lambda *_args, **_kwargs: pytest.fail("ready images must not be pulled"),
    )

    result = remediation.remediate_docker_environment()

    assert result["passed"] is True
    assert result["desktop_start_count"] == 0
    assert result["image_store_mutation_count"] == 0
    assert result["container_create_start_run_exec_count"] == 0
    assert remediation.validate_docker_remediation_observation(result) == result

    extra_pull = json.loads(json.dumps(result))
    pull = _result(
        (
            "docker.exe",
            "image",
            "pull",
            "--quiet",
            "--platform",
            "linux/amd64",
            remediation.DOCKER_IMAGES[0],
        ),
        stdout=(remediation.DOCKER_IMAGES[0] + "\n").encode(),
    ).summary("pull-moto")
    extra_pull["commands"].insert(-3, pull)
    extra_pull["image_store_mutation_count"] = 1
    extra_pull["pulled_images"] = [remediation.DOCKER_IMAGES[0]]
    extra_pull["docker_cli_command_count"] = 7
    with pytest.raises(remediation.D127DockerRemediationError, match="missing from the pull basis"):
        remediation.validate_docker_remediation_observation(extra_pull)


def test_unavailable_daemon_starts_once_and_pulls_only_two_exact_refs(monkeypatch) -> None:
    monkeypatch.setattr(remediation, "ALLOW_DAEMON_START_WITH_UNVERIFIED_RESTART_STATE", True)
    bindings = iter(
        (
            {"file_name": "docker.exe", "file_bytes": remediation.APPROVED_CLI_BYTES},
            {"file_name": "docker.exe", "file_bytes": remediation.APPROVED_CLI_BYTES},
        )
    )
    monkeypatch.setattr(remediation, "approved_cli_binding", lambda: next(bindings))
    monkeypatch.setattr(
        remediation,
        "observed_desktop_binding",
        lambda: {
            "file_name": "Docker Desktop.exe",
            "file_bytes": remediation.OBSERVED_DESKTOP_BYTES,
        },
    )
    monkeypatch.setattr(remediation, "_launch_desktop", lambda: (True, None))
    monkeypatch.setattr(remediation.time, "sleep", lambda _seconds: None)
    observations = iter(
        (
            (_missing(daemon=False), []),
            (_missing(daemon=True, confirmed_absent=True), []),
            (_ready(), _ready_rows()),
        )
    )
    monkeypatch.setattr(remediation, "_observe_readiness", lambda: next(observations))
    calls: list[tuple[str, ...]] = []

    def fake_command(*tail: str, timeout_seconds: int = 30):
        calls.append(tail)
        if tail[0] == "version":
            return _daemon_result()
        assert tail[:5] == ("image", "pull", "--quiet", "--platform", "linux/amd64")
        assert timeout_seconds == 1_200
        return _result(("docker.exe", *tail), stdout=(tail[-1] + "\n").encode())

    monkeypatch.setattr(remediation, "_docker_command", fake_command)
    result = remediation.remediate_docker_environment()

    assert result["passed"] is True
    assert result["desktop_start_count"] == 1
    assert result["daemon_poll_count"] == 1
    assert result["image_store_mutation_count"] == 2
    assert result["pulled_images"] == list(remediation.DOCKER_IMAGES)
    assert [call[-1] for call in calls if call[:2] == ("image", "pull")] == list(
        remediation.DOCKER_IMAGES
    )
    assert result["container_create_start_run_exec_count"] == 0


def test_cli_identity_drift_fails_after_observation_without_claiming_success(monkeypatch) -> None:
    bindings = iter(({"generation": 1}, {"generation": 2}))
    monkeypatch.setattr(remediation, "approved_cli_binding", lambda: next(bindings))
    monkeypatch.setattr(remediation, "_observe_readiness", lambda: (_ready(), []))

    with pytest.raises(remediation.D127DockerRemediationError, match="changed"):
        remediation.remediate_docker_environment()


def test_desktop_launcher_identity_drift_fails_before_poll_or_pull(monkeypatch) -> None:
    monkeypatch.setattr(remediation, "ALLOW_DAEMON_START_WITH_UNVERIFIED_RESTART_STATE", True)
    monkeypatch.setattr(remediation, "approved_cli_binding", _cli_binding)
    monkeypatch.setattr(
        remediation,
        "_observe_readiness",
        lambda: (_missing(daemon=False), _missing_rows()),
    )
    desktop_bindings = iter(({"generation": 1}, {"generation": 2}))
    monkeypatch.setattr(
        remediation,
        "observed_desktop_binding",
        lambda: next(desktop_bindings),
    )
    monkeypatch.setattr(remediation, "_launch_desktop", lambda: (True, None))
    monkeypatch.setattr(
        remediation.time,
        "sleep",
        lambda _seconds: pytest.fail("launcher drift must fail before polling"),
    )

    with pytest.raises(remediation.D127DockerRemediationError, match="launcher changed"):
        remediation.remediate_docker_environment()


def test_unavailable_daemon_does_not_start_without_auto_restart_state_proof(monkeypatch) -> None:
    monkeypatch.setattr(remediation, "approved_cli_binding", _cli_binding)
    monkeypatch.setattr(
        remediation,
        "_observe_readiness",
        lambda: (_missing(daemon=False), _missing_rows()),
    )
    monkeypatch.setattr(
        remediation,
        "_launch_desktop",
        lambda: pytest.fail("daemon start may auto-start non-authorized containers"),
    )

    result = remediation.remediate_docker_environment()

    assert result["desktop_start_count"] == 0
    assert result["desktop_start_skipped_reason"] == remediation.DAEMON_START_SKIPPED_REASON
    assert result["passed"] is False
    assert remediation.validate_docker_remediation_observation(result) == result


def test_ambiguous_image_inspect_failure_never_authorizes_pull(monkeypatch) -> None:
    monkeypatch.setattr(remediation, "approved_cli_binding", _cli_binding)
    monkeypatch.setattr(
        remediation,
        "_observe_readiness",
        lambda: (_missing(daemon=True), _ambiguous_image_error_rows()),
    )
    monkeypatch.setattr(
        remediation,
        "_docker_command",
        lambda *_args, **_kwargs: pytest.fail("ambiguous inspect failure must not authorize pull"),
    )

    result = remediation.remediate_docker_environment()

    assert result["image_store_mutation_count"] == 0
    assert result["pulled_images"] == []
    assert result["passed"] is False
    assert remediation.validate_docker_remediation_observation(result) == result

    forged = json.loads(json.dumps(result))
    forged["pull_basis"]["images"]["moto"] = {
        "state": "confirmed-absent",
        "requested_repo_digest": remediation.DOCKER_IMAGES[0],
        "absence_code": "exact-docker-no-such-image",
        "stdout_bytes": 0,
        "stdout_sha256": sha256_bytes(b""),
        "stderr_bytes": 1,
        "stderr_sha256": "sha256:" + "0" * 64,
    }
    with pytest.raises(remediation.D127DockerRemediationError, match="confirmed-absence"):
        remediation.validate_docker_remediation_observation(forged)


def test_daemon_commands_use_an_empty_isolated_docker_config(monkeypatch) -> None:
    monkeypatch.setenv("DOCKER_CONFIG", "C:/ambient/docker-config")
    monkeypatch.setenv("DOCKER_AUTH_CONFIG", "credential-like-ambient-value")
    monkeypatch.setenv("USERPROFILE", "C:/ambient/profile")
    monkeypatch.setenv("APPDATA", "C:/ambient/appdata")

    with remediation._isolated_docker_config():
        environment = remediation._minimal_environment(daemon=True)
        docker_config = environment["DOCKER_CONFIG"]
        assert os.path.isdir(docker_config)
        assert os.listdir(docker_config) == []

    assert environment["DOCKER_HOST"] == remediation.LOCAL_DOCKER_ENDPOINT
    assert environment["DOCKER_CONFIG"] != "C:/ambient/docker-config"
    assert "DOCKER_AUTH_CONFIG" not in environment
    assert "USERPROFILE" not in environment
    assert "APPDATA" not in environment


def test_readiness_snapshot_validator_rejects_rehashed_unknown_or_mutating_argv(
    monkeypatch,
) -> None:
    monkeypatch.setattr(remediation, "approved_cli_binding", _cli_binding)

    def fake_observe():
        ready = _ready()
        rows = [
            _daemon_result().summary("daemon-version"),
            _result(
                (
                    "docker.exe",
                    "image",
                    "inspect",
                    "--format",
                    remediation.IMAGE_PROJECTION_FORMAT,
                    remediation.DOCKER_IMAGES[0],
                ),
                stdout=(
                    json.dumps(
                        {
                            "Id": ready["images"]["moto"]["config_id"],
                            "RepoDigests": ready["images"]["moto"]["repo_digests"],
                        },
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode(),
            ).summary("image-moto"),
            _result(
                (
                    "docker.exe",
                    "image",
                    "inspect",
                    "--format",
                    remediation.IMAGE_PROJECTION_FORMAT,
                    remediation.DOCKER_IMAGES[1],
                ),
                stdout=(
                    json.dumps(
                        {
                            "Id": ready["images"]["babel"]["config_id"],
                            "RepoDigests": ready["images"]["babel"]["repo_digests"],
                        },
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode(),
            ).summary("image-babel"),
        ]
        return ready, rows

    monkeypatch.setattr(remediation, "_observe_readiness", fake_observe)
    snapshot = remediation.observe_docker_readiness()
    assert remediation.validate_docker_readiness_snapshot(snapshot) == snapshot

    unknown = dict(snapshot)
    unknown["unknown"] = True
    with pytest.raises(remediation.D127DockerRemediationError, match="fields"):
        remediation.validate_docker_readiness_snapshot(unknown)

    mutated = json.loads(json.dumps(snapshot))
    mutated["commands"][1]["argv_contract"] = ["docker.exe", "container", "start", "foreign"]
    with pytest.raises(remediation.D127DockerRemediationError, match="does not match its role"):
        remediation.validate_docker_readiness_snapshot(mutated)

    relabeled = json.loads(json.dumps(snapshot))
    relabeled["commands"][1]["role"] = "image-babel"
    with pytest.raises(remediation.D127DockerRemediationError, match="does not match its role"):
        remediation.validate_docker_readiness_snapshot(relabeled)

    false_bound = json.loads(json.dumps(snapshot))
    false_bound["commands"][0]["stdout_within_bound"] = False
    with pytest.raises(remediation.D127DockerRemediationError, match="bound flag"):
        remediation.validate_docker_readiness_snapshot(false_bound)

    malformed_repo_digest = json.loads(json.dumps(snapshot))
    malformed_repo_digest["observation"]["images"]["moto"]["repo_digests"] = ["not-a-digest"]
    with pytest.raises(remediation.D127DockerRemediationError, match="RepoDigest projection"):
        remediation.validate_docker_readiness_snapshot(malformed_repo_digest)


def test_command_summary_never_persists_raw_output() -> None:
    secret = b"credential-like-output-must-not-be-persisted"
    result = _result(("docker.exe", "version"), stdout=secret, stderr=secret)
    serialized = json.dumps(result.summary("hostile"), sort_keys=True)

    assert secret.decode() not in serialized
    assert result.summary("hostile")["raw_stdout_persisted"] is False
    assert result.summary("hostile")["raw_stderr_persisted"] is False
