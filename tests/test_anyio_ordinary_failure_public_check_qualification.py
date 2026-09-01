from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from patchloop.evals import anyio_ordinary_failure_public_check_qualification as qualification
from patchloop.evals.anyio_ordinary_failure_public_check_qualification import (
    PublicBehaviorCheckQualificationError,
    build_candidate,
    expected_approval_message,
    observe_candidate,
)
from patchloop.sandbox import SandboxResult
from patchloop.util import sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]


def test_candidate_is_deterministic_and_docker_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_docker_call(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("candidate construction invoked Docker")

    monkeypatch.setattr(
        qualification.DockerSandbox,
        "image_identity_projection",
        unexpected_docker_call,
    )
    monkeypatch.setattr(qualification.DockerSandbox, "run_check", unexpected_docker_call)

    first = build_candidate(REPOSITORY)
    second = build_candidate(REPOSITORY)

    assert first == second
    assert first["schema_version"].endswith("candidate-v1")
    assert first["source_qualification"]["file_sha256"] == (
        qualification.SOURCE_QUALIFICATION_FILE_SHA256
    )
    assert first["source_qualification_content_hash"] == (
        qualification.SOURCE_QUALIFICATION_CONTENT_HASH
    )
    assert first["candidate_build_contract"] == {
        "docker_cli_invocations": 0,
        "docker_daemon_calls": 0,
        "container_runs": 0,
        "registered_check_calls": 0,
        "network_calls": 0,
        "provider_calls": 0,
        "evaluator_calls": 0,
        "added_cost_usd": 0,
    }
    assert first["task_binding"]["task_id"] == "anyio-interrupt-runner-cleanup"
    assert first["task_binding"]["task_version"] == 4
    assert first["proposed_check"]["id"] == "public-ordinary-failure-preservation"
    assert [row["source_state"] for row in first["schedule"]] == ["base", "reference"]
    assert all(row["expected_observation"] == "pass" for row in first["schedule"])
    assert first["task_successor_created"] is False
    assert first["execution_authorized"] is False
    assert first["docker_calls_made"] == 0
    assert first["provider_calls_made"] == 0
    assert first["added_cost_usd"] == 0
    assert first["execution_hash"] in expected_approval_message(first)


def test_candidate_rejects_schedule_check_or_boundary_tampering() -> None:
    candidate = build_candidate(REPOSITORY)

    changed = copy.deepcopy(candidate)
    changed["schedule"][0]["expected_observation"] = "failure"
    with pytest.raises(PublicBehaviorCheckQualificationError, match="identity differs"):
        qualification._validate_candidate(changed)

    changed = copy.deepcopy(candidate)
    changed["proposed_check"]["id"] = "different-check"
    with pytest.raises(PublicBehaviorCheckQualificationError, match="identity differs"):
        qualification._validate_candidate(changed)

    changed = copy.deepcopy(candidate)
    changed["task_successor_created"] = True
    with pytest.raises(PublicBehaviorCheckQualificationError, match="identity differs"):
        qualification._validate_candidate(changed)


def test_materialized_candidate_is_canonical_and_current() -> None:
    path = REPOSITORY / qualification.CANDIDATE_PATH
    raw = path.read_bytes()
    stored = json.loads(raw)

    assert raw == qualification._json_bytes(stored)
    assert stored == build_candidate(REPOSITORY)
    assert len(raw) == 14_636
    assert sha256_bytes(raw) == (
        "sha256:3b3341d1dc5802fad004973ef4b92d31ba8233f9a95dcd9153ed66e9e6c9fa0b"
    )
    assert stored["execution_hash"] == (
        "sha256:4269db56125f87e84e22a26299c9e2c58c55832e696f344068f6f09063544600"
    )
    assert stored["content_hash"] == (
        "sha256:e1323a1ae39b412f21949d2687eb7186ef136f16fe5b6f3947bc41a4502cd630"
    )


def test_observer_requires_both_base_and_reference_to_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = build_candidate(REPOSITORY)
    calls: list[str] = []

    class FakeSandbox:
        def __init__(self, image: str) -> None:
            self.image = image

        def image_identity_projection(self) -> SimpleNamespace:
            return SimpleNamespace(
                verified_identity=self.image.rsplit("@", 1)[1],
                config_id=f"sha256:{'c' * 64}",
                matched_repo_digest=self.image,
            )

        def run_check(self, workspace: Path, check: object) -> SandboxResult:
            calls.append(f"{workspace.name}:{check.id}")  # type: ignore[attr-defined]
            return SandboxResult(
                command=list(check.command),  # type: ignore[attr-defined]
                exit_code=0,
                stdout="",
                stderr="",
                duration_ms=1,
                timed_out=False,
                truncated=False,
                original_output_bytes=0,
                execution_policy=candidate["requested_execution_policy"],
            )

    monkeypatch.setattr(qualification, "DockerSandbox", FakeSandbox)
    result = observe_candidate(REPOSITORY, candidate)

    assert result["status"] == "PUBLIC_ORDINARY_FAILURE_CHECK_QUALIFIED"
    assert result["docker_image_inspect_calls"] == 1
    assert result["docker_container_run_attempts"] == 2
    assert result["docker_container_run_completions"] == 2
    assert result["provider_calls"] == result["network_calls"] == 0
    assert result["added_cost_usd"] == 0
    assert calls == [
        "01-base:public-ordinary-failure-preservation",
        "02-reference:public-ordinary-failure-preservation",
    ]
    assert all(row["expected_observation_matched"] for row in result["row_observations"])
    assert all(row["raw_output_persisted"] is False for row in result["row_observations"])


def test_observer_fails_closed_and_projects_only_allowlisted_public_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = build_candidate(REPOSITORY)
    calls = 0

    class FailingReferenceSandbox:
        def __init__(self, image: str) -> None:
            self.image = image

        def image_identity_projection(self) -> SimpleNamespace:
            return SimpleNamespace(
                verified_identity=self.image.rsplit("@", 1)[1],
                config_id=f"sha256:{'d' * 64}",
                matched_repo_digest=self.image,
            )

        def run_check(self, _workspace: Path, check: object) -> SandboxResult:
            nonlocal calls
            calls += 1
            failed = calls == 2
            stderr = "AssertionError: PUBLIC_CASE:anyio:ordinary-failure-events" if failed else ""
            return SandboxResult(
                command=list(check.command),  # type: ignore[attr-defined]
                exit_code=1 if failed else 0,
                stdout="",
                stderr=stderr,
                duration_ms=1,
                timed_out=False,
                truncated=False,
                original_output_bytes=len(stderr.encode()),
                execution_policy=candidate["requested_execution_policy"],
            )

    monkeypatch.setattr(qualification, "DockerSandbox", FailingReferenceSandbox)
    result = observe_candidate(REPOSITORY, candidate)

    assert result["status"] == "PUBLIC_ORDINARY_FAILURE_CHECK_NOT_QUALIFIED"
    reference = result["row_observations"][1]
    assert reference["expected_observation_matched"] is False
    assert reference["public_case_markers"] == ["PUBLIC_CASE:anyio:ordinary-failure-events"]
    assert "AssertionError" not in json.dumps(result)
    assert result["raw_output_persisted"] is False


def test_observer_stops_before_containers_on_image_identity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = build_candidate(REPOSITORY)

    class BrokenSandbox:
        def __init__(self, _image: str) -> None:
            pass

        def image_identity_projection(self) -> object:
            raise RuntimeError("daemon unavailable")

        def run_check(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("container ran after identity failure")

    monkeypatch.setattr(qualification, "DockerSandbox", BrokenSandbox)
    result = observe_candidate(REPOSITORY, candidate)

    assert result["status"] == "PUBLIC_ORDINARY_FAILURE_CHECK_BLOCKED_IMAGE_IDENTITY"
    assert result["docker_image_inspect_calls"] == 1
    assert result["docker_container_run_attempts"] == 0
    assert result["docker_container_run_completions"] == 0
    assert result["execution_error_class"] == "RuntimeError"


def test_run_once_rejects_missing_exact_approval_before_docker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = build_candidate(REPOSITORY)

    def unexpected_docker_call(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("Docker was reached before exact approval")

    def missing_approval(_root: Path, relative: Path) -> dict[str, object]:
        if relative == qualification.APPROVAL_PATH:
            raise PublicBehaviorCheckQualificationError("artifact is unavailable")
        raise AssertionError("unexpected artifact lookup")

    monkeypatch.setattr(
        qualification,
        "ATTEMPT_PATH",
        Path(".patchloop/test-ordinary-failure-qualification-attempt.json"),
    )
    monkeypatch.setattr(
        qualification,
        "RESULT_PATH",
        Path(".patchloop/test-ordinary-failure-qualification-result.json"),
    )
    monkeypatch.setattr(qualification, "load_candidate", lambda _root: candidate)
    monkeypatch.setattr(qualification, "_load_canonical", missing_approval)
    monkeypatch.setattr(
        qualification.DockerSandbox,
        "image_identity_projection",
        unexpected_docker_call,
    )
    monkeypatch.setattr(qualification.DockerSandbox, "run_check", unexpected_docker_call)

    with pytest.raises(PublicBehaviorCheckQualificationError, match="unavailable"):
        qualification.run_once(REPOSITORY)


def test_consumed_qualification_is_exact_and_blocks_retry_before_docker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = {
        qualification.APPROVAL_PATH: (
            1_025,
            "sha256:4480985785f5143cc431f6108c20babbefc410d8fe17f54a769fb317b05cf5a0",
        ),
        qualification.ATTEMPT_PATH: (
            1_126,
            "sha256:947157dbee188f4f5c55b1cddcc16c5f61ad722bc5f8217b5386441cee5203ad",
        ),
        qualification.RESULT_PATH: (
            5_885,
            "sha256:ff70ac1a63a78d5cbb05b1a50510ce270c294252192aed196804848e3f81f760",
        ),
    }
    for relative, (expected_bytes, expected_hash) in expected.items():
        raw = (REPOSITORY / relative).read_bytes()
        assert len(raw) == expected_bytes
        assert sha256_bytes(raw) == expected_hash

    result = json.loads((REPOSITORY / qualification.RESULT_PATH).read_bytes())
    assert result["status"] == "PUBLIC_ORDINARY_FAILURE_CHECK_QUALIFIED"
    assert result["content_hash"] == (
        "sha256:0e5d5e48dc15b0fa01bb1d83ff8068cdf28d6ebe6affed7c407e6eb1cdef465a"
    )
    assert result["docker_image_inspect_calls"] == 1
    assert result["docker_container_run_attempts"] == 2
    assert result["docker_container_run_completions"] == 2
    assert [row["expected_observation_matched"] for row in result["row_observations"]] == [
        True,
        True,
    ]
    assert result["provider_calls"] == result["network_calls"] == 0
    assert result["added_cost_usd"] == 0

    def unexpected_docker_call(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("Docker was reached after the result was consumed")

    monkeypatch.setattr(
        qualification.DockerSandbox,
        "image_identity_projection",
        unexpected_docker_call,
    )
    monkeypatch.setattr(qualification.DockerSandbox, "run_check", unexpected_docker_call)
    with pytest.raises(PublicBehaviorCheckQualificationError, match="already consumed"):
        qualification.run_once(REPOSITORY)
