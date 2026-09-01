from __future__ import annotations

import copy
import io
import json
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from patchloop.evals import public_behavior_check_qualification_v6 as qualification
from patchloop.evals.public_behavior_check_qualification_v6 import (
    PublicBehaviorCheckQualificationError,
    build_candidate,
    expected_approval_message,
    observe_candidate,
)
from patchloop.sandbox import SandboxResult
from patchloop.util import sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]
ANYIO_ARCHIVE_SHA256 = "sha256:28cecaf9114d994f69ca8bd8eafa2abebbd0ae4b6c9a89367ca04dbfc45d5326"


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
    archives = {spec["task_id"]: _archive(spec["target_path"]) for spec in qualification.TASK_SPECS}

    def executable(name: str) -> dict[str, object]:
        return {
            "resolved_path": f"C:/{name}.exe",
            "file_bytes": 10,
            "file_sha256": f"sha256:{'a' if name == 'docker' else 'b'}" + "0" * 63,
        }

    def source_archive(
        _root: Path,
        spec: dict[str, object],
        _git_cli: dict[str, object],
    ) -> tuple[bytes, dict[str, object]]:
        task_id = str(spec["task_id"])
        raw = archives[task_id]
        archive_sha256 = (
            ANYIO_ARCHIVE_SHA256
            if task_id == "anyio-interrupt-runner-cleanup"
            else sha256_bytes(raw)
        )
        return raw, {
            "provenance": "consumed-rapid-v6-local-git-object",
            "seed_workspace": spec["seed_workspace"],
            "base_commit": (
                "881cd4e38d31663ae67bdae227ec1ccdfd5e2c77"
                if task_id.startswith("pdm-")
                else "cb245dba9883516f2ed4c23899de157183a1cb50"
            ),
            "archive_format": "git-archive-tar-v1",
            "archive_bytes": len(raw),
            "archive_sha256": archive_sha256,
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
    monkeypatch.setattr(qualification, "_validate_reference_patch_applies", lambda *_a, **_k: None)
    monkeypatch.setattr(qualification, "_apply_reference_patch", lambda *_a, **_k: None)
    candidate = build_candidate(REPOSITORY)
    candidate["_test_archive_provider"] = source_archive
    return candidate


def _without_test_provider(candidate: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in candidate.items() if key != "_test_archive_provider"}


def test_candidate_is_deterministic_two_row_and_retains_exact_anyio(
    offline_candidate: dict[str, object],
) -> None:
    candidate = _without_test_provider(offline_candidate)
    second = build_candidate(REPOSITORY)

    assert candidate == second
    assert json.loads(qualification._json_bytes(candidate)) == candidate
    assert candidate["schema_version"] == "public-behavior-check-qualification-candidate-v6"
    assert candidate["predecessor_execution_hash"] == qualification.PREDECESSOR_EXECUTION_HASH
    assert [row["task_id"] for row in candidate["schedule"]] == [
        "pdm-ignore-active-venv-resolution",
        "pdm-ignore-active-venv-resolution",
    ]
    assert [row["source_state"] for row in candidate["schedule"]] == ["base", "reference"]
    assert {item["task_version"] for item in candidate["task_bindings"]} == {4, 5}
    assert candidate["retained_anyio_qualification"]["status"] == (
        "QUALIFIED_FROM_CONSUMED_V5_ROWS"
    )
    assert candidate["retained_anyio_qualification"]["task_version"] == 4
    assert candidate["docker_contract"] == {
        "image_identity_inspect_calls": 1,
        "container_run_calls": 2,
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
    assert candidate["execution_hash"] in expected_approval_message(candidate)


def test_observer_runs_only_pdm_and_qualifies_composite(
    offline_candidate: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _without_test_provider(offline_candidate)
    provider = offline_candidate["_test_archive_provider"]
    images: list[str] = []
    calls: list[str] = []

    class FakeSandbox:
        def __init__(self, image: str) -> None:
            self.image = image
            images.append(image)

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
    result = observe_candidate(
        REPOSITORY,
        candidate,
        archive_provider=provider,  # type: ignore[arg-type]
    )

    assert result["status"] == "PUBLIC_BEHAVIOR_CHECKS_QUALIFIED"
    assert result["docker_image_inspect_calls"] == 1
    assert result["docker_container_run_attempts"] == 2
    assert result["docker_container_run_completions"] == 2
    assert len(calls) == 2
    assert all("public-ignore-active-venv-resolution" in item for item in calls)
    assert all("pdm-project-pdm" in image for image in images)
    assert result["retained_anyio_qualification"] == candidate["retained_anyio_qualification"]


def test_retained_anyio_rejects_marker_drift(offline_candidate: dict[str, object]) -> None:
    candidate = _without_test_provider(offline_candidate)
    predecessor = json.loads((REPOSITORY / qualification.PREDECESSOR_RESULT_PATH).read_bytes())
    predecessor = copy.deepcopy(predecessor)
    anyio_base = next(
        row
        for row in predecessor["row_observations"]
        if row["task_id"] == "anyio-interrupt-runner-cleanup" and row["source_state"] == "base"
    )
    anyio_base["public_case_markers"] = ["PUBLIC_CASE:anyio:interrupt-timeout"]
    task = next(
        item
        for item in candidate["task_bindings"]
        if item["task_id"] == "anyio-interrupt-runner-cleanup"
    )

    with pytest.raises(
        PublicBehaviorCheckQualificationError, match="retained AnyIO evidence differs"
    ):
        qualification._retained_anyio_qualification(predecessor, task)


def test_pdm_image_failure_stops_before_container(
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
            raise AssertionError("container must not run after identity failure")

    monkeypatch.setattr(qualification, "DockerSandbox", FailingSandbox)
    result = observe_candidate(REPOSITORY, candidate)

    assert result["status"] == "PUBLIC_BEHAVIOR_CHECKS_BLOCKED_IMAGE_IDENTITY"
    assert result["docker_image_inspect_calls"] == 1
    assert result["docker_container_run_attempts"] == 0
    assert result["image_identity_observations"][0]["task_id"] == (
        "pdm-ignore-active-venv-resolution"
    )
    assert result["image_identity_observations"][0]["error_class"] == "OSError"


def test_candidate_rejects_schedule_tampering(offline_candidate: dict[str, object]) -> None:
    candidate = _without_test_provider(offline_candidate)
    candidate["schedule"][0]["source_state"] = "reference"

    with pytest.raises(PublicBehaviorCheckQualificationError, match="identity differs"):
        qualification._validate_candidate(candidate)


def test_consumed_v6_candidate_and_terminal_are_exact_and_cannot_retry() -> None:
    raw = (REPOSITORY / qualification.PREDECESSOR_RESULT_PATH).read_bytes()
    result = json.loads(raw)

    assert sha256_bytes(raw) == qualification.PREDECESSOR_RESULT_FILE_SHA256
    assert result["execution_hash"] == qualification.PREDECESSOR_EXECUTION_HASH
    assert result["status"] == "PUBLIC_BEHAVIOR_CHECKS_NOT_QUALIFIED"

    candidate_raw = (REPOSITORY / qualification.CANDIDATE_PATH).read_bytes()
    candidate = json.loads(candidate_raw)
    assert len(candidate_raw) == 13276
    assert sha256_bytes(candidate_raw) == (
        "sha256:0c6147c3bac5a8fdc82b3f996c6ae640131d7edecb4081eb30f416066ac7b9d4"
    )
    assert candidate["content_hash"] == (
        "sha256:ebcd909b75f23de4e2b00372f2b87c66d6fb9eec159c7ddaf330f2204b622138"
    )
    assert candidate["execution_hash"] == (
        "sha256:1c8dc99447e27d3674e63592adccea8323d74def99b69de0667756c9f5f4e027"
    )
    assert candidate["schedule_hash"] == (
        "sha256:8d5ff9ec8978bf461beda2539264fc3a16391e2334b07d270da1ded3d7de2cc0"
    )
    # This consumed artifact is audited by immutable bytes. Later contract/error
    # source changes intentionally make a current-source rebuild inapplicable.
    qualification._validate_candidate(candidate)
    assert candidate["execution_authorized"] is False

    artifact_hashes = {
        qualification.APPROVAL_PATH: (
            "sha256:f00d99d45928aead79224ce17c98e59d463a64d48077fa9565bae910283116fe"
        ),
        qualification.ATTEMPT_PATH: (
            "sha256:b79bf60088a7140f1de640ec2fb8a4877c0050444ac3792c99be187b83df547c"
        ),
        qualification.RESULT_PATH: (
            "sha256:1d35a3b1defb140118fb5097dd6849d1aafbbe35e7fe5e2721242a39a3bbd7db"
        ),
    }
    for artifact_path, expected_hash in artifact_hashes.items():
        assert sha256_bytes((REPOSITORY / artifact_path).read_bytes()) == expected_hash

    terminal = json.loads((REPOSITORY / qualification.RESULT_PATH).read_bytes())
    assert terminal["content_hash"] == (
        "sha256:804020a7b38de349da1e28821a665ab1e7ce8c7d115b6ee2d7162e5634b40590"
    )
    assert terminal["status"] == "PUBLIC_BEHAVIOR_CHECKS_NOT_QUALIFIED"
    assert terminal["execution_error_class"] is None
    assert terminal["retained_anyio_qualification"]["status"] == ("QUALIFIED_FROM_CONSUMED_V5_ROWS")
    assert terminal["docker_image_inspect_calls"] == 1
    assert terminal["docker_container_run_attempts"] == 2
    assert terminal["docker_container_run_completions"] == 2
    assert terminal["image_identity_observations"][0]["matched"] is True
    assert [row["exit_code"] for row in terminal["row_observations"]] == [1, 1]
    assert [row["expected_observation_matched"] for row in terminal["row_observations"]] == [
        True,
        False,
    ]
    assert [row["public_case_markers"] for row in terminal["row_observations"]] == [
        ["PUBLIC_CASE:pdm:false-zero:no-python"],
        ["PUBLIC_CASE:pdm:conda-false-zero:wrong-path"],
    ]
    assert terminal["image_pull_build_tag_remove_prune_calls"] == 0
    assert terminal["agent_calls"] == terminal["evaluator_calls"] == 0
    assert terminal["provider_calls"] == terminal["network_calls"] == 0
    assert terminal["added_cost_usd"] == 0

    with pytest.raises(PublicBehaviorCheckQualificationError, match="already consumed"):
        qualification.run_once(REPOSITORY)
