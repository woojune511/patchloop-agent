from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals import fresh_harbor_local_image_inventory as inventory
from patchloop.evals.fresh_harbor_local_image_inventory import (
    APPROVAL_TEMPLATE,
    IMAGE_LS_ARGS,
    AttemptIntent,
    Candidate,
    FreshHarborLocalImageInventoryError,
    SourceQualification,
    _parse_inventory,
    _source_checks,
    _target_images,
    build_candidate,
    build_source_qualification,
    expected_approval_message,
    observe,
    run_once,
)
from patchloop.evals.fresh_harbor_partial_preflight import DockerCliBinding
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _attempt(candidate: Candidate) -> AttemptIntent:
    body = {
        "schema_version": "lean-fresh-harbor-local-image-inventory-attempt-v1",
        "attempt_id": "lean-fresh-harbor-local-image-inventory-attempt-20260818-r1",
        "recorded_at": "2026-08-18T00:00:00Z",
        "status": "LOCAL_IMAGE_INVENTORY_ATTEMPT_RECORDED_BEFORE_CALL",
        "approval_binding": {
            "path": "reports/fresh-panel/artifacts/approval.json",
            "file_bytes": 1,
            "file_sha256": f"sha256:{'a' * 64}",
            "content_hash": f"sha256:{'b' * 64}",
            "role": "approval",
        },
        "candidate_binding": {
            "path": "experiments/inventory.json",
            "file_bytes": 1,
            "file_sha256": f"sha256:{'c' * 64}",
            "content_hash": f"sha256:{'d' * 64}",
            "role": "candidate",
        },
        "execution_hash": candidate.execution_hash,
        "docker_cli": DockerCliBinding(
            resolved_path="C:/docker.exe",
            file_bytes=43_095_472,
            file_sha256="sha256:8985cd8ac002c3240b5aa48fe401fcb55dca5d849b537e3c835564e8e8c49a70",
        ).model_dump(mode="json"),
        "command_arguments_hash": sha256_json(list(IMAGE_LS_ARGS)),
        "docker_cli_calls_before_attempt": 0,
    }
    return AttemptIntent(**body, content_hash=sha256_json(body))


def _line(repository: str, tag: str, image_id: str) -> bytes:
    return json.dumps(
        {"Repository": repository, "Tag": tag, "ID": image_id, "Digest": "<none>"}
    ).encode()


def test_source_and_candidate_are_zero_call_and_exact() -> None:
    source = build_source_qualification(REPOSITORY)
    candidate = build_candidate(REPOSITORY)

    assert source.authority.docker_cli_calls == 0
    assert candidate.authority.inventory_preflight_authorized is False
    assert candidate.command_arguments == IMAGE_LS_ARGS
    assert len(candidate.target_images) == 12
    assert candidate.runner_execution_hash.startswith("sha256:92fb35")
    assert candidate.execution_hash in expected_approval_message(candidate)
    assert "{execution_hash}" in APPROVAL_TEMPLATE
    assert _source_checks()["unrelated-image-records-never-persisted"] is True


def test_parser_projects_only_targets_and_marks_missing() -> None:
    targets = _target_images()
    first = targets[0]
    second = targets[1]
    raw = b"\n".join(
        (
            _line("private/unrelated", "latest", "sha256:0"),
            _line(first.normalized_tag.rsplit(":", 1)[0], "v0.1.0", "sha256:1"),
            _line(f"docker.io/{second.normalized_tag.rsplit(':', 1)[0]}", "v0.1.0", "sha256:2"),
        )
    )

    values = _parse_inventory(raw, targets)

    assert len(values) == 12
    assert [item.present for item in values[:3]] == [True, True, False]
    assert "private/unrelated" not in json.dumps([item.model_dump() for item in values])


def test_observer_uses_one_command_and_persists_no_unrelated_rows() -> None:
    candidate = build_candidate(REPOSITORY)
    attempt = _attempt(candidate)
    first = candidate.target_images[0]
    raw = _line(first.normalized_tag.rsplit(":", 1)[0], "v0.1.0", "sha256:1")
    calls: list[tuple[str, ...]] = []

    def runner(arguments: tuple[str, ...], _timeout: int) -> subprocess.CompletedProcess[bytes]:
        calls.append(arguments)
        return subprocess.CompletedProcess([], 0, raw, b"")

    terminal = observe(candidate, attempt, "2026-08-18T00:01:00Z", runner)

    assert calls == [IMAGE_LS_ARGS]
    assert terminal.status == "LOCAL_IMAGE_INVENTORY_COMPLETE_MISSING_IMAGES"
    assert (terminal.present_count, terminal.missing_count) == (1, 11)
    assert terminal.unrelated_local_image_records_persisted == 0
    assert terminal.image_pull_build_tag_remove_prune_calls == 0


def test_command_failure_and_malformed_output_fail_closed() -> None:
    candidate = build_candidate(REPOSITORY)
    attempt = _attempt(candidate)
    failed = observe(
        candidate,
        attempt,
        "2026-08-18T00:01:00Z",
        lambda _args, _timeout: subprocess.CompletedProcess([], 1, b"", b"error"),
    )
    malformed = observe(
        candidate,
        attempt,
        "2026-08-18T00:01:00Z",
        lambda _args, _timeout: subprocess.CompletedProcess([], 0, b"not-json", b""),
    )
    assert failed.status == "LOCAL_IMAGE_INVENTORY_BLOCKED_DOCKER_COMMAND"
    assert malformed.status == "LOCAL_IMAGE_INVENTORY_BLOCKED_INVALID_OUTPUT"
    assert failed.execution_authorized is malformed.execution_authorized is False


def test_rehashed_candidate_command_or_authority_drift_is_rejected() -> None:
    candidate = build_candidate(REPOSITORY)
    body = candidate.model_dump(mode="json")
    body["command_arguments"].append("--quiet")
    projection = {
        key: value
        for key, value in body.items()
        if key
        not in {
            "execution_hash",
            "approval_message_template",
            "authority",
            "next_gate",
            "content_hash",
        }
    }
    body["execution_hash"] = sha256_json(projection)
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError, match="command differs"):
        Candidate.model_validate(body)

    body = candidate.model_dump(mode="json")
    body["authority"]["inventory_preflight_authorized"] = True
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError):
        Candidate.model_validate(body)

    body = candidate.model_dump(mode="json")
    body["runner_candidate_binding"]["file_bytes"] += 1
    projection = {
        key: value
        for key, value in body.items()
        if key
        not in {
            "execution_hash",
            "approval_message_template",
            "authority",
            "next_gate",
            "content_hash",
        }
    }
    body["execution_hash"] = sha256_json(projection)
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError, match="runner binding differs"):
        Candidate.model_validate(body)


def test_rehashed_source_authority_drift_is_rejected() -> None:
    source = build_source_qualification(REPOSITORY)
    body = source.model_dump(mode="json")
    body["authority"]["source_files_read"] = 3
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError, match="source authority differs"):
        SourceQualification.model_validate(body)


def test_duplicate_target_output_is_rejected() -> None:
    target = _target_images()[0]
    row = _line(target.normalized_tag.rsplit(":", 1)[0], "v0.1.0", "sha256:1")
    with pytest.raises(FreshHarborLocalImageInventoryError, match="duplicated"):
        _parse_inventory(row + b"\n" + row, _target_images())


def test_existing_attempt_blocks_reentry_before_any_call(tmp_path: Path) -> None:
    attempt = tmp_path / (
        "reports/fresh-panel/artifacts/lean-fresh-harbor-local-image-inventory-attempt-r1.json"
    )
    attempt.parent.mkdir(parents=True)
    attempt.write_bytes(b"call-claim")

    with pytest.raises(
        FreshHarborLocalImageInventoryError,
        match="already consumed or outcome is uncertain",
    ):
        run_once(tmp_path)


def test_source_and_candidate_materialization_are_idempotent_and_no_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    required = (
        inventory.RUNNER_PATH,
        inventory.PREDECESSOR_TERMINAL_PATH,
        inventory.PREDECESSOR_SOURCE_PATH,
        *inventory.SOURCE_PATHS,
        *inventory.VALIDATION_PATHS,
    )
    for relative in required:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY / relative, target)

    def forbidden_subprocess(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("source and candidate builders must not call Docker")

    monkeypatch.setattr(subprocess, "run", forbidden_subprocess)
    source_first = inventory.materialize_source_qualification(tmp_path)
    source_path = tmp_path / inventory.SOURCE_PATH
    source_mtime = source_path.stat().st_mtime_ns
    source_second = inventory.materialize_source_qualification(tmp_path)
    assert source_second == source_first
    assert source_path.stat().st_mtime_ns == source_mtime

    candidate_first = inventory.materialize_candidate(tmp_path)
    candidate_path = tmp_path / inventory.CANDIDATE_PATH
    candidate_mtime = candidate_path.stat().st_mtime_ns
    candidate_second = inventory.materialize_candidate(tmp_path)
    assert candidate_second == candidate_first
    assert candidate_path.stat().st_mtime_ns == candidate_mtime
    assert not (tmp_path / inventory.APPROVAL_PATH).exists()
    assert not (tmp_path / inventory.ATTEMPT_PATH).exists()
    assert not (tmp_path / inventory.TERMINAL_PATH).exists()
