from __future__ import annotations

import gc
import json
import socket
import subprocess
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from patchloop.agent import batch_image_authority as image_module
from patchloop.agent import runner as runner_module
from patchloop.agent.batch_image_authority import (
    image_authorization_receipt,
    issue_live_batch_image_authorization,
    rehearse_batch_image_authorization,
    validate_row_batch_image,
)
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
from patchloop.errors import HarnessAdmissionError
from patchloop.evals import rapid_public_development_v26 as rapid
from patchloop.evals.batch_image_qualification import run_batch_image_mock
from patchloop.sandbox import DockerSandbox
from patchloop.sandbox.runner import DockerImageIdentityProjection
from patchloop.util import sha256_json
from patchloop.verifier import EvaluationEngine

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_external_work(monkeypatch: pytest.MonkeyPatch) -> None:
    popen = subprocess.Popen

    def blocked(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("batch-image offline test attempted external work")

    def local_git_only(args: Any, *rest: Any, **kwargs: Any) -> Any:
        if args == ["git", "rev-parse", "HEAD"] and kwargs.get("cwd") == ROOT:
            assert not kwargs.get("shell", False)
            return popen(args, *rest, **kwargs)
        return blocked(args, *rest, **kwargs)

    for target, name in (
        (DockerSandbox, "available"),
        (DockerSandbox, "image_identity"),
        (DockerSandbox, "probe_image_identity"),
        (DockerSandbox, "run_check"),
        (OpenAIResponsesAdapter, "next_turn"),
        (OpenAIResponsesAdapter, "execute_request"),
        (EvaluationEngine, "evaluate"),
        (socket, "create_connection"),
        (socket.socket, "connect"),
    ):
        monkeypatch.setattr(target, name, blocked)
    monkeypatch.setattr(subprocess, "Popen", local_git_only)


@pytest.fixture
def candidate() -> dict[str, Any]:
    return rapid.build_rapid_public_development_v26_candidate(repository=ROOT)


def _live(candidate: dict[str, Any], root: Path) -> tuple[Any, Any]:
    rapid._write_or_validate_plan(candidate, root)
    live = issue_live_execution_authorization(candidate["execution_hash"], root=root / ".patchloop")
    batch = rapid._prepare_batch(
        candidate, authority_kind="live", live_authorization=live, repository=ROOT
    )
    return live, batch


def _inspect_stub(
    monkeypatch: pytest.MonkeyPatch, candidate: dict[str, Any], *, valid: bool = True
) -> list[str]:
    calls: list[str] = []
    image = candidate["task_bindings"][0]["evaluator_image"]

    def inspect(sandbox: DockerSandbox) -> DockerImageIdentityProjection:
        calls.append(sandbox.image)
        return DockerImageIdentityProjection(
            requested_repo_digest=image,
            requested_digest=image.rsplit("@", 1)[1],
            config_id="sha256:" + "a" * 64,
            repo_digests=(image,),
            matched_repo_digest=image if valid else None,
        )

    monkeypatch.setattr(DockerSandbox, "image_identity_projection", inspect)
    return calls


def _row(prepared: Any, live: Any, order: int = 1) -> Any:
    manifest = prepared.manifests[order - 1]
    row = runner_module.issue_row_execution_authorization(
        prepared.authorization, manifest, active_schedule_order=order
    )
    runner_module._consume_row_execution_authorization(
        manifest, row, expected_authority_kind="live", live_authorization=live
    )
    return row


def test_real_six_row_start_driver_counts_one_inspect_and_zero_external_calls(
    candidate: dict[str, Any], tmp_path: Path
) -> None:
    first = run_batch_image_mock(candidate, repository=ROOT, state_root=tmp_path / "first")
    second = run_batch_image_mock(candidate, repository=ROOT, state_root=tmp_path / "second")
    assert first == second
    assert first["inspect_adapter_calls"] == 1
    assert first["real_agent_start_count"] == first["provider_gate_count"] == 6
    assert first["per_row_image_inspect_calls"] == 0
    assert first["actual_docker_calls"] == first["provider_calls"] == 0
    assert first["agent_policies_or_task_behavior_exercised"] is False


def test_one_observation_binds_all_manifests_without_config_digest_confusion(
    candidate: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    live, prepared = _live(candidate, tmp_path)
    calls = _inspect_stub(monkeypatch, candidate)
    authority = rapid._admit_prepared_image(candidate, prepared, tmp_path)
    for order in range(1, 7):
        row = _row(prepared, live, order)
        assert (
            validate_row_batch_image(
                authority,
                row,
                prepared.manifests[order - 1],
                expected_kind="live",
                expected_image=authority.image,
                expected_digest=authority.digest,
            )
            == authority.digest
        )
    assert calls == [authority.image]
    receipt = image_authorization_receipt(authority)
    assert receipt["authority_kind"] == "live"
    events = [json.loads(line) for line in authority.receipt_path.read_bytes().splitlines()]
    for event in events:
        assert event["content_hash"] == sha256_json(
            {k: v for k, v in event.items() if k != "content_hash"}
        )
    assert events[0]["type"] == "image-inspection-attempt-started"
    assert len(events[0]["binding"]["manifest_hashes"]) == 6
    assert events[1]["previous_hash"] == events[0]["content_hash"]
    assert events[1]["identity_projection"]["config_id"] != authority.digest
    assert events[1]["identity_projection"]["matched_repo_digest"] == authority.image


@pytest.mark.parametrize("kind", ["missing", "foreign-batch", "copied", "wrong-image", "tampered"])
def test_invalid_image_authority_fails_closed_without_reinspection(
    candidate: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    live, prepared = _live(candidate, tmp_path)
    calls = _inspect_stub(monkeypatch, candidate)
    authority = rapid._admit_prepared_image(candidate, prepared, tmp_path)
    row = _row(prepared, live)
    selected: Any = authority
    expected_image = authority.image
    if kind == "missing":
        selected = None
    elif kind == "foreign-batch":
        other = rapid._prepare_batch(
            candidate, authority_kind="live", live_authorization=live, repository=ROOT
        )
        row = _row(other, live)
    elif kind == "copied":
        selected = replace(authority)
    elif kind == "wrong-image":
        expected_image = "foreign/image@" + authority.digest
    else:
        authority.receipt_path.write_bytes(authority.receipt_path.read_bytes() + b"\n")
    with pytest.raises(HarnessAdmissionError):
        validate_row_batch_image(
            selected,
            row,
            prepared.manifests[0],
            expected_kind="live",
            expected_image=expected_image,
            expected_digest=authority.digest,
        )
    assert len(calls) == 1


def test_missing_required_image_capability_blocks_actual_start_before_workspace_or_provider(
    candidate: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    live, prepared = _live(candidate, tmp_path)
    row = runner_module.issue_row_execution_authorization(
        prepared.authorization, prepared.manifests[0], active_schedule_order=1
    )
    runner = AgentRunner(tmp_path / "runner")
    monkeypatch.setattr(runner.workspaces, "create", lambda *a: pytest.fail("workspace created"))
    with pytest.raises(HarnessAdmissionError, match="batch image authority"):
        runner.start(
            rapid.TASK_PATH,
            model="openai",
            manifest=prepared.manifests[0],
            live_authorization=live,
            row_execution_authorization=row,
        )
    assert runner.state.list_events(prepared.manifests[0].run_id) == []


def test_digest_mismatch_is_receipted_without_any_row_or_retry(
    candidate: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, prepared = _live(candidate, tmp_path)
    calls = _inspect_stub(monkeypatch, candidate, valid=False)
    with pytest.raises(HarnessAdmissionError, match="UNAVAILABLE_OR_MISMATCHED"):
        rapid._admit_prepared_image(candidate, prepared, tmp_path)
    with pytest.raises(HarnessAdmissionError, match="attempt is unavailable"):
        rapid._admit_prepared_image(candidate, prepared, tmp_path)
    assert len(calls) == 1
    events = [
        json.loads(line)
        for line in rapid._image_receipt_path(candidate, tmp_path).read_bytes().splitlines()
    ]
    assert events[-1]["type"] == "image-admission-rejected"
    assert prepared.authorization._state.next_order == 1
    assert prepared.authorization._state.image_authorization is None


@pytest.mark.parametrize("crash_fsync", [1, 2])
def test_crash_marker_forbids_restart_reinspection_even_after_success(
    candidate: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, crash_fsync: int
) -> None:
    live, prepared = _live(candidate, tmp_path)
    calls = _inspect_stub(monkeypatch, candidate)
    original_fsync = image_module.os.fsync
    syncs = 0

    class SimulatedCrash(BaseException):
        pass

    def crash(fd: int) -> None:
        nonlocal syncs
        original_fsync(fd)
        syncs += 1
        if syncs == crash_fsync:
            raise SimulatedCrash()

    with monkeypatch.context() as inner:
        inner.setattr(image_module.os, "fsync", crash)
        with pytest.raises(SimulatedCrash):
            rapid._admit_prepared_image(candidate, prepared, tmp_path)
    restarted = rapid._prepare_batch(
        candidate, authority_kind="live", live_authorization=live, repository=ROOT
    )
    with pytest.raises(HarnessAdmissionError, match="receipt exists"):
        rapid._admit_prepared_image(candidate, restarted, tmp_path)
    assert len(calls) == crash_fsync - 1
    assert restarted.authorization._state.image_authorization is None


def test_rehearsal_receipt_is_deterministic_but_never_live_authority(
    candidate: dict[str, Any], tmp_path: Path
) -> None:
    first = rapid._build_rehearsal_for(candidate, repository=ROOT)
    second = rapid._build_rehearsal_for(candidate, repository=ROOT)
    assert rapid.rehearsal_bytes(first) == rapid.rehearsal_bytes(second)
    assert first["image_gate_count"] == 6
    assert first["image_admission"]["image_identity_observed"] is False
    assert first["docker_calls_made"] == 0
    prepared = rapid._prepare_batch(candidate, authority_kind="rehearsal", repository=ROOT)
    image = candidate["task_bindings"][0]["evaluator_image"]
    authority, _ = rehearse_batch_image_authorization(
        prepared.authorization, prepared.manifests, image=image
    )
    with pytest.raises(HarnessAdmissionError):
        issue_live_batch_image_authorization(
            prepared.authorization,
            prepared.manifests,
            image=image,
            receipt_path=tmp_path / "forbidden.jsonl",
        )
    assert authority.authority_kind == "rehearsal"
    assert not (tmp_path / "forbidden.jsonl").exists()


def test_mixed_image_manifest_binding_rejected_before_inspect_or_receipt(
    candidate: dict[str, Any], tmp_path: Path
) -> None:
    _, prepared = _live(candidate, tmp_path)
    changed = prepared.manifests[0].model_copy(
        update={"evaluator_image_digest": "sha256:" + "0" * 64}
    )
    with pytest.raises(HarnessAdmissionError, match="binding is invalid"):
        issue_live_batch_image_authorization(
            prepared.authorization,
            (changed, *prepared.manifests[1:]),
            image=candidate["task_bindings"][0]["evaluator_image"],
            receipt_path=tmp_path / "forbidden.jsonl",
        )
    assert not (tmp_path / "forbidden.jsonl").exists()


def test_batch_cannot_drop_approved_image_contract(
    candidate: dict[str, Any], tmp_path: Path
) -> None:
    live, prepared = _live(candidate, tmp_path)
    batch = prepared.authorization
    with pytest.raises(HarnessAdmissionError, match="image policy differs"):
        runner_module.issue_batch_execution_authorization(
            authority_kind="live",
            execution_hash=batch.execution_hash,
            plan_hash=batch.plan_hash,
            runtime_build_hash=batch.runtime_build_hash,
            schedule_hash=batch.schedule_hash,
            cost_control_hash=batch.cost_control_hash,
            manifests=prepared.manifests,
            live_authorization=live,
        )


def test_same_digest_foreign_repository_cannot_be_inspected(
    candidate: dict[str, Any], tmp_path: Path
) -> None:
    live, prepared = _live(candidate, tmp_path)
    batch = prepared.authorization
    foreign = "foreign/repository@" + prepared.manifests[0].evaluator_image_digest
    with pytest.raises(HarnessAdmissionError, match="binding is invalid"):
        issue_live_batch_image_authorization(
            batch, prepared.manifests, image=foreign, receipt_path=tmp_path / "forbidden.jsonl"
        )
    assert not (tmp_path / "forbidden.jsonl").exists()
    with pytest.raises(HarnessAdmissionError, match="reference differs"):
        runner_module.issue_batch_execution_authorization(
            authority_kind="live",
            execution_hash=batch.execution_hash,
            plan_hash=batch.plan_hash,
            runtime_build_hash=batch.runtime_build_hash,
            schedule_hash=batch.schedule_hash,
            cost_control_hash=batch.cost_control_hash,
            manifests=prepared.manifests,
            live_authorization=live,
            image_admission_policy=image_module.POLICY_VERSION,
            image_admission_image=foreign,
        )


def test_mock_state_can_be_deleted_without_garbage_collection(
    candidate: dict[str, Any], tmp_path: Path
) -> None:
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        with TemporaryDirectory(prefix="image-cleanup-", dir=tmp_path) as temporary:
            isolated = Path(temporary)
            result = run_batch_image_mock(candidate, repository=ROOT, state_root=isolated / "mock")
            assert result["isolated_mock_sqlite_connections_closed"] is True
        assert not isolated.exists()
    finally:
        if was_enabled:
            gc.enable()
