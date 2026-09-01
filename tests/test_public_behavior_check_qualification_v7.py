from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from patchloop.evals import public_behavior_check_qualification_v7 as qualification
from patchloop.evals.public_behavior_check_qualification_v7 import (
    PublicBehaviorCheckQualificationError,
    build_candidate,
    expected_approval_message,
    observe_candidate,
)
from patchloop.sandbox import SandboxResult
from patchloop.util import sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]


def test_candidate_is_deterministic_execution_closed_and_binds_task_v6(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_docker_call(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("candidate construction invoked the Docker CLI or daemon")

    monkeypatch.setattr(
        qualification.DockerSandbox,
        "image_identity_projection",
        unexpected_docker_call,
    )
    monkeypatch.setattr(qualification.DockerSandbox, "run_check", unexpected_docker_call)

    candidate = build_candidate(REPOSITORY)
    second = build_candidate(REPOSITORY)

    assert candidate == second
    assert candidate["schema_version"] == "public-behavior-check-qualification-candidate-v7"
    assert candidate["predecessor_execution_hash"] == qualification.PREDECESSOR_EXECUTION_HASH
    assert candidate["public_source_reconciliation"] == qualification.PUBLIC_SOURCE_RECONCILIATION
    assert candidate["candidate_build_contract"] == {
        "docker_cli_invocations": 0,
        "docker_daemon_calls": 0,
        "container_runs": 0,
        "network_calls": 0,
        "provider_calls": 0,
        "added_cost_usd": 0,
    }
    assert [row["source_state"] for row in candidate["schedule"]] == ["base", "reference"]
    assert {row["task_version"] for row in candidate["schedule"]} == {6}
    assert {
        (task["task_id"], task["task_version"])
        for task in candidate["task_bindings"]
    } == {
        ("pdm-ignore-active-venv-resolution", 6),
        ("anyio-interrupt-runner-cleanup", 4),
    }
    assert candidate["execution_authorized"] is False
    assert candidate["docker_calls_made"] == 0
    assert candidate["provider_calls_made"] == 0
    assert candidate["added_cost_usd"] == 0
    assert candidate["execution_hash"] in expected_approval_message(candidate)


def test_candidate_rejects_semantic_or_schedule_tampering() -> None:
    candidate = build_candidate(REPOSITORY)

    changed = copy.deepcopy(candidate)
    changed["public_source_reconciliation"]["case_removed"] = True
    with pytest.raises(PublicBehaviorCheckQualificationError, match="identity differs"):
        qualification._validate_candidate(changed)

    changed = copy.deepcopy(candidate)
    changed["schedule"][0]["task_version"] = 5
    with pytest.raises(PublicBehaviorCheckQualificationError, match="identity differs"):
        qualification._validate_candidate(changed)


def test_materialized_candidate_and_consumed_terminal_are_exact() -> None:
    path = REPOSITORY / qualification.CANDIDATE_PATH
    raw = path.read_bytes()
    candidate = json.loads(raw)

    assert sha256_bytes(raw) == (
        "sha256:5f2935d5e99f8c7e0207387fed20d84736ca6829c1b021f66cca77336ce41e70"
    )
    assert raw == qualification._json_bytes(candidate)
    assert candidate["execution_hash"] == (
        "sha256:bb0a182325cfeb66fe030251b244d4528ca84777758ba0a6c41a2de431a28f20"
    )
    assert candidate["content_hash"] == (
        "sha256:0bbf713fcdd58e4d6ebe9f3fa113a1f3054a4c6b698e42ce665e6fc0ff061976"
    )
    expected_files = {
        qualification.APPROVAL_PATH: (
            "sha256:94b7896e0a2edb922b2469aa828c59cc4fef79c847072cc0ec42b33d391b0cd7"
        ),
        qualification.ATTEMPT_PATH: (
            "sha256:642655d513ef5bdd646e622b08e190f09141f711ca04bc66ed4105a5e71b4d28"
        ),
        qualification.RESULT_PATH: (
            "sha256:57756c0b4d51c800ae179a4078573e623b9b2cf0f37c12650969d2d79fca3f9f"
        ),
    }
    for relative, expected_hash in expected_files.items():
        assert sha256_bytes((REPOSITORY / relative).read_bytes()) == expected_hash

    result = json.loads((REPOSITORY / qualification.RESULT_PATH).read_bytes())
    assert result["status"] == "PUBLIC_BEHAVIOR_CHECKS_NOT_QUALIFIED"
    assert result["execution_error_class"] is None
    assert result["docker_image_inspect_calls"] == 1
    assert result["docker_container_run_attempts"] == 2
    assert result["docker_container_run_completions"] == 2
    assert result["image_pull_build_tag_remove_prune_calls"] == 0
    assert result["provider_calls"] == result["network_calls"] == 0
    assert result["added_cost_usd"] == 0
    base, reference = result["row_observations"]
    assert base["expected_observation_matched"] is True
    assert base["public_case_markers"] == ["PUBLIC_CASE:pdm:false-zero:no-python"]
    assert reference["expected_observation_matched"] is False
    assert reference["exit_code"] == 1
    assert reference["public_assertion_marker_observed"] is False
    assert reference["public_case_markers"] == []
    assert all(row["raw_output_persisted"] is False for row in (base, reference))


def test_consumed_result_blocks_retry_before_docker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_docker_call(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("Docker was reached before exact approval")

    monkeypatch.setattr(
        qualification.DockerSandbox,
        "image_identity_projection",
        unexpected_docker_call,
    )
    monkeypatch.setattr(qualification.DockerSandbox, "run_check", unexpected_docker_call)

    with pytest.raises(PublicBehaviorCheckQualificationError, match="already consumed"):
        qualification.run_once(REPOSITORY)

    assert (REPOSITORY / qualification.ATTEMPT_PATH).is_file()
    assert (REPOSITORY / qualification.RESULT_PATH).is_file()


def test_observer_qualifies_only_expected_base_failure_and_reference_pass(
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
            base = workspace.name.endswith("-base")
            return SandboxResult(
                command=list(check.command),  # type: ignore[attr-defined]
                exit_code=1 if base else 0,
                stdout="",
                stderr=(
                    "Traceback\nAssertionError: PUBLIC_CASE:pdm:false-zero:no-python\n"
                    if base
                    else ""
                ),
                duration_ms=1,
                timed_out=False,
                truncated=False,
                original_output_bytes=70 if base else 0,
                execution_policy={"pull_policy": "never"},
            )

    monkeypatch.setattr(qualification, "DockerSandbox", FakeSandbox)
    result = observe_candidate(REPOSITORY, candidate)

    assert result["status"] == "PUBLIC_BEHAVIOR_CHECKS_QUALIFIED"
    assert result["docker_image_inspect_calls"] == 1
    assert result["docker_container_run_attempts"] == 2
    assert result["docker_container_run_completions"] == 2
    assert result["provider_calls"] == result["network_calls"] == 0
    assert result["added_cost_usd"] == 0
    assert len(calls) == 2
    assert all("public-ignore-active-venv-resolution" in call for call in calls)


def test_observer_fails_closed_on_image_identity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = build_candidate(REPOSITORY)

    class BrokenSandbox:
        def __init__(self, _image: str) -> None:
            pass

        def image_identity_projection(self) -> object:
            raise RuntimeError("daemon unavailable")

    monkeypatch.setattr(qualification, "DockerSandbox", BrokenSandbox)
    result = observe_candidate(REPOSITORY, candidate)

    assert result["status"] == "PUBLIC_BEHAVIOR_CHECKS_BLOCKED_IMAGE_IDENTITY"
    assert result["docker_image_inspect_calls"] == 1
    assert result["docker_container_run_attempts"] == 0
    assert result["docker_container_run_completions"] == 0
    assert result["execution_error_class"] == "RuntimeError"
