from __future__ import annotations

import io
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from patchloop.evals import public_behavior_check_qualification as qualification
from patchloop.evals.public_behavior_check_qualification import (
    PublicBehaviorCheckQualificationError,
    _result_projection,
    build_candidate,
    expected_approval_message,
    observe_candidate,
)
from patchloop.sandbox import SandboxResult
from patchloop.util import sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]


def _archive(required_path: str) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:") as archive:
        raw = b"public source\n"
        member = tarfile.TarInfo(required_path)
        member.size = len(raw)
        archive.addfile(member, io.BytesIO(raw))
    return output.getvalue()


@pytest.fixture
def offline_candidate(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    archives = {
        spec["task_id"]: _archive(spec["target_path"])
        for spec in qualification.TASK_SPECS
    }

    def executable(name: str) -> dict[str, object]:
        return {
            "resolved_path": f"C:/{name}.exe",
            "file_bytes": 10,
            "file_sha256": f"sha256:{'a' if name == 'docker' else 'b'}" + "0" * 63,
        }

    def source_archive(
        _root: Path,
        spec: dict[str, str],
        _git_cli: dict[str, object],
    ) -> tuple[bytes, dict[str, object]]:
        raw = archives[spec["task_id"]]
        return raw, {
            "provenance": "consumed-rapid-v6-local-git-object",
            "seed_workspace": spec["seed_workspace"],
            "base_commit": (
                "881cd4e38d31663ae67bdae227ec1ccdfd5e2c77"
                if spec["task_id"].startswith("pdm-")
                else "cb245dba9883516f2ed4c23899de157183a1cb50"
            ),
            "archive_format": "git-archive-tar-v1",
            "archive_bytes": len(raw),
            "archive_sha256": sha256_bytes(raw),
            "archive_member_count": 1,
            "target_path_present": True,
        }

    monkeypatch.setattr(qualification, "_executable_binding", executable)
    monkeypatch.setattr(
        qualification,
        "_docker_context_binding",
        lambda: {
            "context": qualification.DOCKER_CONTEXT,
            "endpoint": qualification.DOCKER_ENDPOINT,
        },
    )
    monkeypatch.setattr(qualification, "_source_archive", source_archive)
    monkeypatch.setattr(
        qualification,
        "_validate_reference_patch_applies",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        qualification,
        "_apply_reference_patch",
        lambda *_args, **_kwargs: None,
    )
    candidate = build_candidate(REPOSITORY)
    candidate["_test_archive_provider"] = source_archive
    return candidate


def _without_test_provider(candidate: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in candidate.items() if key != "_test_archive_provider"}


def test_candidate_is_deterministic_four_row_and_execution_closed(
    offline_candidate: dict[str, object],
) -> None:
    candidate = _without_test_provider(offline_candidate)
    second = build_candidate(REPOSITORY)

    assert candidate == second
    assert [row["source_state"] for row in candidate["schedule"]] == [
        "base",
        "reference",
        "base",
        "reference",
    ]
    assert candidate["docker_contract"] == {
        "image_identity_inspect_calls": 2,
        "container_run_calls": 4,
        "pull_policy": "never",
        "network": "none",
        "root_filesystem": "read_only",
        "workspace_mount": "read_only",
        "agent_calls": 0,
        "evaluator_calls": 0,
        "provider_calls": 0,
        "network_calls": 0,
        "added_cost_usd": 0,
    }
    assert candidate["execution_authorized"] is False
    assert candidate["docker_calls_made"] == 0
    assert candidate["provider_calls_made"] == 0
    assert candidate["added_cost_usd"] == 0
    assert candidate["execution_hash"] in expected_approval_message(candidate)


def test_observer_qualifies_only_base_assertion_and_reference_pass(
    offline_candidate: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _without_test_provider(offline_candidate)
    provider = offline_candidate["_test_archive_provider"]
    calls: list[str] = []

    class FakeSandbox:
        def __init__(self, image: str) -> None:
            self.image = image

        def image_identity_projection(self) -> SimpleNamespace:
            digest = self.image.rsplit("@", 1)[1]
            return SimpleNamespace(
                verified_identity=digest,
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
                stderr="Traceback\nAssertionError\n" if base else "",
                duration_ms=1,
                timed_out=False,
                truncated=False,
                original_output_bytes=25 if base else 0,
                execution_policy={"pull_policy": "never"},
            )

    monkeypatch.setattr(qualification, "DockerSandbox", FakeSandbox)
    result = observe_candidate(
        REPOSITORY,
        candidate,
        archive_provider=provider,  # type: ignore[arg-type]
    )

    assert result["status"] == "PUBLIC_BEHAVIOR_CHECKS_QUALIFIED"
    assert result["docker_image_inspect_calls"] == 2
    assert result["docker_container_run_attempts"] == 4
    assert result["docker_container_run_completions"] == 4
    assert len(calls) == 4
    assert all(row["expected_observation_matched"] for row in result["row_observations"])
    assert all(row["raw_output_persisted"] is False for row in result["row_observations"])


def test_image_inspect_exception_becomes_terminal_projection(
    offline_candidate: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _without_test_provider(offline_candidate)

    class FailingSandbox:
        def __init__(self, _image: str) -> None:
            pass

        def image_identity_projection(self) -> None:
            raise OSError("simulated Docker CLI failure")

        def run_check(self, _workspace: Path, _check: object) -> SandboxResult:
            raise AssertionError("container must not start after identity failure")

    monkeypatch.setattr(qualification, "DockerSandbox", FailingSandbox)
    result = observe_candidate(REPOSITORY, candidate)

    assert result["status"] == "PUBLIC_BEHAVIOR_CHECKS_BLOCKED_IMAGE_IDENTITY"
    assert result["docker_image_inspect_calls"] == 2
    assert result["docker_container_run_attempts"] == 0
    assert [item["error_class"] for item in result["image_identity_observations"]] == [
        "OSError",
        "OSError",
    ]


def test_base_import_failure_does_not_qualify_as_behavior_discrimination() -> None:
    row = {"source_state": "base", "expected_observation": "public-assertion-failure"}
    result = SandboxResult(
        command=["python", "-c", "raise ImportError"],
        exit_code=1,
        stdout="",
        stderr="ImportError: missing dependency",
        duration_ms=1,
        timed_out=False,
        truncated=False,
        original_output_bytes=31,
        execution_policy=None,
    )

    projected = _result_projection(row, result)

    assert projected["observation"] == "unexpected-base-result"
    assert projected["expected_observation_matched"] is False


def test_candidate_rejects_schedule_tampering(
    offline_candidate: dict[str, object],
) -> None:
    candidate = _without_test_provider(offline_candidate)
    candidate["schedule"][0]["source_state"] = "reference"

    with pytest.raises(PublicBehaviorCheckQualificationError, match="identity differs"):
        qualification._validate_candidate(candidate)
