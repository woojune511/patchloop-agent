from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from patchloop.evals import public_behavior_check_qualification_v3 as consumed_qualification
from patchloop.evals import public_behavior_check_qualification_v4 as superseded_qualification
from patchloop.evals import public_behavior_check_qualification_v5 as qualification
from patchloop.evals.public_behavior_check_qualification_v5 import (
    PublicBehaviorCheckQualificationError,
    _result_projection,
    build_candidate,
    expected_approval_message,
    observe_candidate,
)
from patchloop.sandbox import SandboxResult
from patchloop.util import sha256_bytes, sha256_json

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
    archives = {spec["task_id"]: _archive(spec["target_path"]) for spec in qualification.TASK_SPECS}

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
    assert candidate["schema_version"] == "public-behavior-check-qualification-candidate-v5"
    assert json.loads(qualification._json_bytes(candidate)) == candidate
    assert candidate["predecessor_execution_hash"] == qualification.PREDECESSOR_EXECUTION_HASH
    assert candidate["predecessor_result"]["path"] == (
        qualification.PREDECESSOR_RESULT_PATH.as_posix()
    )
    assert candidate["superseded_candidate"]["path"] == (
        qualification.SUPERSEDED_CANDIDATE_PATH.as_posix()
    )
    assert candidate["superseded_execution_hash"] == qualification.SUPERSEDED_EXECUTION_HASH
    assert candidate["superseded_status"] == ("CLOSED_BEFORE_APPROVAL_MATERIALIZATION_TYPE_DRIFT")
    assert candidate["superseded_external_effects"] == {
        "docker_calls": 0,
        "provider_calls": 0,
        "network_calls": 0,
        "added_cost_usd": 0,
    }
    assert {item["task_version"] for item in candidate["task_bindings"]} == {4}
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
    assert candidate["public_failure_projection"] == {
        "schema_version": "allowlisted-public-case-id-v1",
        "pattern": qualification.PUBLIC_CASE_PATTERN.pattern,
        "task_allowlists": qualification.PUBLIC_CASE_ALLOWLIST,
        "raw_output_persisted": False,
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
            if check.id == "public-ignore-active-venv-resolution":  # type: ignore[attr-defined]
                marker = "PUBLIC_CASE:pdm:false-unset:no-python"
            else:
                marker = "PUBLIC_CASE:anyio:test-resumed"
            return SandboxResult(
                command=list(check.command),  # type: ignore[attr-defined]
                exit_code=1 if base else 0,
                stdout="",
                stderr=f"Traceback\nAssertionError: {marker}\n" if base else "",
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
    row = {
        "task_id": "pdm-ignore-active-venv-resolution",
        "source_state": "base",
        "expected_observation": "public-assertion-failure",
    }
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


@pytest.mark.parametrize(
    "stderr",
    (
        "Traceback\nAssertionError\n",
        "Traceback\nAssertionError: PUBLIC_CASE:anyio:test-resumed\n",
        "Traceback\nAssertionError: PUBLIC_CASE:pdm:not-allowlisted:wrong-path\n",
    ),
)
def test_base_requires_the_row_specific_allowlisted_public_case(stderr: str) -> None:
    row = {
        "task_id": "pdm-ignore-active-venv-resolution",
        "source_state": "base",
        "expected_observation": "public-assertion-failure",
    }
    result = SandboxResult(
        command=["python", "-c", "raise AssertionError"],
        exit_code=1,
        stdout="",
        stderr=stderr,
        duration_ms=1,
        timed_out=False,
        truncated=False,
        original_output_bytes=len(stderr.encode()),
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


def test_consumed_v2_and_v3_results_are_exact_and_v3_cannot_retry() -> None:
    v2_path = REPOSITORY / (
        "reports/rapid-development/artifacts/"
        "pdm-anyio-public-behavior-check-qualification-result-v2.json"
    )
    v2_raw = v2_path.read_bytes()
    v2 = json.loads(v2_raw)
    assert sha256_bytes(v2_raw) == (
        "sha256:5ffec09c2fd9fc40b5339d516e19a2c720f4e5013495908eb3703394ada3de21"
    )
    assert v2["status"] == "PUBLIC_BEHAVIOR_CHECKS_NOT_QUALIFIED"
    assert v2["docker_image_inspect_calls"] == 2
    assert v2["docker_container_run_attempts"] == 4
    assert v2["docker_container_run_completions"] == 4
    assert v2["provider_calls"] == v2["network_calls"] == v2["added_cost_usd"] == 0
    assert [row["exit_code"] for row in v2["row_observations"]] == [1, 1, 130, 130]
    assert all(row["raw_output_persisted"] is False for row in v2["row_observations"])

    candidate_path = REPOSITORY / consumed_qualification.CANDIDATE_PATH
    candidate_raw = candidate_path.read_bytes()
    candidate = json.loads(candidate_raw)
    assert sha256_bytes(candidate_raw) == (
        "sha256:28ae4633113260664b51b842825dac2ebe5ad79e1cd889fcd2462ab2785bce48"
    )
    assert candidate["execution_hash"] == (
        "sha256:73cc29a0bebbcd5f83e5b402e14ce48a2d705829cdc7aec97af0e832c280bf18"
    )
    assert candidate["schedule_hash"] == (
        "sha256:8db65cb823800bb77e084cb9e9acf212c043ab1bdc11623518ecbab831383f65"
    )
    assert candidate["content_hash"] == sha256_json(
        {key: value for key, value in candidate.items() if key != "content_hash"}
    )
    assert candidate["execution_authorized"] is False
    assert candidate["docker_calls_made"] == candidate["provider_calls_made"] == 0

    for binding in candidate["source_files"]:
        source = REPOSITORY / binding["path"]
        raw = source.read_bytes()
        assert len(raw) == binding["file_bytes"]
        assert sha256_bytes(raw) == binding["file_sha256"]

    artifact_hashes = {
        consumed_qualification.APPROVAL_PATH: (
            "sha256:254c28c2dbc33a1470752b79a3a922c95ac7c5b5eecb39f35c86a8ebbfb63324"
        ),
        consumed_qualification.ATTEMPT_PATH: (
            "sha256:7930590b4103db388144e10d32c2ccc1dc4befb7b9e82cb3e38fe4f9411157e3"
        ),
        consumed_qualification.RESULT_PATH: (
            "sha256:2cd933a8cb45303dae4ac975da8f85021ac8be70ef53c4106e1acc4a7ef463c7"
        ),
    }
    for path, expected_hash in artifact_hashes.items():
        assert sha256_bytes((REPOSITORY / path).read_bytes()) == expected_hash

    result = json.loads((REPOSITORY / consumed_qualification.RESULT_PATH).read_bytes())
    assert result["status"] == "PUBLIC_BEHAVIOR_CHECKS_NOT_QUALIFIED"
    assert result["docker_image_inspect_calls"] == 2
    assert result["docker_container_run_attempts"] == 4
    assert result["docker_container_run_completions"] == 4
    assert result["provider_calls"] == result["network_calls"] == 0
    assert result["added_cost_usd"] == 0
    assert [row["exit_code"] for row in result["row_observations"]] == [1, 1, 0, 0]
    assert [row["expected_observation_matched"] for row in result["row_observations"]] == [
        True,
        False,
        False,
        True,
    ]

    with pytest.raises(
        consumed_qualification.PublicBehaviorCheckQualificationError,
        match="already consumed",
    ):
        consumed_qualification.run_once(REPOSITORY)


def test_v4_materialization_incident_is_exact_and_unactivated() -> None:
    path = REPOSITORY / superseded_qualification.CANDIDATE_PATH
    raw = path.read_bytes()
    candidate = json.loads(raw)

    assert sha256_bytes(raw) == qualification.SUPERSEDED_CANDIDATE_FILE_SHA256
    assert candidate["execution_hash"] == qualification.SUPERSEDED_EXECUTION_HASH
    assert candidate["schema_version"] == "public-behavior-check-qualification-candidate-v4"
    assert candidate["execution_authorized"] is False
    assert candidate["docker_calls_made"] == candidate["provider_calls_made"] == 0
    assert candidate["added_cost_usd"] == 0
    assert all(not (REPOSITORY / item).exists() for item in qualification.SUPERSEDED_CLOSED_PATHS)


def test_consumed_v5_candidate_and_terminal_are_exact_and_cannot_retry() -> None:
    path = REPOSITORY / qualification.CANDIDATE_PATH
    raw = path.read_bytes()
    candidate = json.loads(raw)

    assert len(raw) == 14710
    assert sha256_bytes(raw) == (
        "sha256:d63beb7bd71cb610d351d01eeef27b98dc73d57d5c9aec4cb5e34a48db3be9f9"
    )
    assert candidate["content_hash"] == (
        "sha256:1b1d4c2983abfd986449cc44053ab88d41dc6837ee5177cc666b7b96bb90b72c"
    )
    assert candidate["execution_hash"] == (
        "sha256:f7b0159d622ee6329db6560ab253d117187e6a05a5e7bb630ba325588eb211b3"
    )
    assert candidate["schedule_hash"] == (
        "sha256:c7eb4674aba16a0833c9b6e94d1b73ecacce492df10da2edc9604678feeb6491"
    )
    assert qualification.load_candidate(REPOSITORY) == candidate
    assert candidate["execution_authorized"] is False
    assert candidate["docker_calls_made"] == candidate["provider_calls_made"] == 0
    assert candidate["added_cost_usd"] == 0

    artifact_hashes = {
        qualification.APPROVAL_PATH: (
            "sha256:09953d4e0163f56a5a2082e96a38408ea6df27544fb789770f012df0a95e1ca0"
        ),
        qualification.ATTEMPT_PATH: (
            "sha256:78b52e35d5123e8a1e75c3e7566e55b3b50c791e7df7ec1f044c57fa253d6f39"
        ),
        qualification.RESULT_PATH: (
            "sha256:57ac80b98f26970aba4927157c91eba6964a20b9326cca5470bfa28b4a5b54e4"
        ),
    }
    for artifact_path, expected_hash in artifact_hashes.items():
        assert sha256_bytes((REPOSITORY / artifact_path).read_bytes()) == expected_hash

    result = json.loads((REPOSITORY / qualification.RESULT_PATH).read_bytes())
    assert result["content_hash"] == (
        "sha256:71bb74dfbae3346549a6cc8912aa9c85990db1b2e9ea9cf10f022464150cc1b8"
    )
    assert result["status"] == "PUBLIC_BEHAVIOR_CHECKS_NOT_QUALIFIED"
    assert result["execution_error_class"] is None
    assert result["docker_image_inspect_calls"] == 2
    assert result["docker_container_run_attempts"] == 4
    assert result["docker_container_run_completions"] == 4
    assert all(item["matched"] for item in result["image_identity_observations"])
    assert [row["exit_code"] for row in result["row_observations"]] == [1, 1, 1, 0]
    assert [row["expected_observation_matched"] for row in result["row_observations"]] == [
        True,
        False,
        True,
        True,
    ]
    assert [row["public_case_markers"] for row in result["row_observations"]] == [
        ["PUBLIC_CASE:pdm:false-zero:no-python"],
        ["PUBLIC_CASE:pdm:false-off:wrong-path"],
        ["PUBLIC_CASE:anyio:test-resumed"],
        [],
    ]
    assert result["image_pull_build_tag_remove_prune_calls"] == 0
    assert result["agent_calls"] == result["evaluator_calls"] == 0
    assert result["provider_calls"] == result["network_calls"] == 0
    assert result["added_cost_usd"] == 0

    with pytest.raises(PublicBehaviorCheckQualificationError, match="already consumed"):
        qualification.run_once(REPOSITORY)
