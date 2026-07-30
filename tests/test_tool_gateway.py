from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

import pytest

from patchloop.agent.context import build_context, build_context_with_evidence
from patchloop.agent.tools import TOOL_SCHEMAS, ToolGateway
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, Budget, Checkpoint, EventType, FaultSpec, Phase
from patchloop.errors import ActionConflict, ContractError, RecoveryError
from patchloop.evals.qualification import (
    _request_evidence_payload,
    _v4_admission_nested_artifact_evidence,
    _v4_investigation_context_evidence,
    _v4_investigation_lifecycle_evidence,
)
from patchloop.repository import WorkspaceManager
from patchloop.runtime import build_manifest
from patchloop.sandbox import LocalSandbox
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_text, utc_now


def _smoke_gateway(
    tmp_path,
    run_id,
    *,
    tool_schema_version="v2",
    fault: FaultSpec | None = None,
    budget: Budget | None = None,
    max_output_tokens: int = 4096,
    manifest_context_policy_version: str = "phase-evidence-v4",
):
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id=run_id,
        fault=fault,
        budget=budget,
        max_output_tokens=max_output_tokens,
    ).model_copy(update={"context_policy_version": manifest_context_policy_version})
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    workspace = manager.create(
        manifest.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    gateway = ToolGateway(
        run_id=manifest.run_id,
        workspace=workspace,
        task=package.public,
        state=state,
        artifacts=ArtifactStore(tmp_path / "artifacts"),
        sandbox=LocalSandbox(),
        tool_schema_version=tool_schema_version,
        fault=manifest.fault,
    )
    return manager, workspace, gateway


def _r2_style_recount_patch() -> str:
    return (
        "diff --git a/mini_data_utils/csvlite.py "
        "b/mini_data_utils/csvlite.py\n"
        "--- a/mini_data_utils/csvlite.py\n"
        "+++ b/mini_data_utils/csvlite.py\n"
        "@@ -1,7 +1,7 @@\n"
        '-"""A deliberately small CSV reader with one audited defect."""\n'
        '+"""A deliberately small CSV reader with one verified defect."""\n'
        " \n"
        " import csv\n"
        " \n"
        " \n"
        " def parse_rows(text: str) -> list[list[str]]:\n"
    )


def _durable_checkpoint(gateway: ToolGateway) -> Checkpoint:
    gateway.state.append_event(
        gateway.run_id,
        EventType.RUN_STARTED,
        actor="test",
    )
    summary = WorkspaceManager.diff_summary(gateway.workspace)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=gateway.workspace,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    checkpoint = Checkpoint(
        checkpoint_id=f"ckpt_{uuid.uuid4().hex}",
        run_id=gateway.run_id,
        through_sequence=gateway.state.last_sequence(gateway.run_id),
        phase=Phase.REPRODUCE,
        repository_head=head,
        worktree_diff_hash=summary.patch_hash,
        created_at=utc_now(),
    )
    gateway.state.save_checkpoint(checkpoint)
    gateway.state.append_event(
        gateway.run_id,
        EventType.CHECKPOINT_SAVED,
        actor="state-store",
        payload={
            "checkpoint_id": checkpoint.checkpoint_id,
            "through_sequence": checkpoint.through_sequence,
            "worktree_diff_hash": checkpoint.worktree_diff_hash,
        },
    )
    return checkpoint


def _fresh_gateway(gateway: ToolGateway) -> ToolGateway:
    return ToolGateway(
        run_id=gateway.run_id,
        workspace=gateway.workspace,
        task=gateway.task,
        state=gateway.state,
        artifacts=gateway.artifacts,
        sandbox=gateway.sandbox,
        tool_schema_version=gateway.tool_schema_version,
        context_policy_version=gateway.context_policy_version,
        fault=gateway.fault,
    )


def test_mutating_tool_rolls_back_forbidden_path(tmp_path) -> None:
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(package, run_id="run_gateway_policy")
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    workspace = manager.create(
        manifest.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    gateway = ToolGateway(
        run_id=manifest.run_id,
        workspace=workspace,
        task=package.public,
        state=state,
        artifacts=ArtifactStore(tmp_path / "artifacts"),
        sandbox=LocalSandbox(),
    )
    patch = Path("tasks/smoke/csv-quoted-newline/bad/forbidden-path.patch").read_text(
        encoding="utf-8"
    )
    result = gateway.execute("apply_patch", "forbidden-mutation", {"patch": patch})
    assert result.status == "rejected"
    assert "outside allowed_paths" in (result.error_message or "")
    assert manager.diff_summary(workspace).changed_files == []


def test_apply_patch_recounts_incorrect_hunk_line_totals(tmp_path) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recount",
    )
    patch = _r2_style_recount_patch()
    object_root = workspace / ".git" / "objects"
    objects_before = {
        path.relative_to(object_root).as_posix(): path.read_bytes()
        for path in object_root.rglob("*")
        if path.is_file()
    }

    result = gateway.execute(
        "apply_patch",
        "recount-valid-text-patch",
        {"patch": patch},
    )

    assert result.status == "succeeded"
    assert result.output["patch_hash"] == sha256_text(patch)
    assert manager.diff_summary(workspace).changed_files == [
        "mini_data_utils/csvlite.py"
    ]
    assert "one verified defect" in (
        workspace / "mini_data_utils" / "csvlite.py"
    ).read_text(encoding="utf-8")
    objects_after = {
        path.relative_to(object_root).as_posix(): path.read_bytes()
        for path in object_root.rglob("*")
        if path.is_file()
    }
    assert objects_after == objects_before
    assert not (workspace / ".git" / "patchloop-recovery").exists()


def test_controlled_rejection_is_one_shot_and_does_not_mutate_worktree(
    tmp_path,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_controlled_rejection",
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
    )
    patch = _r2_style_recount_patch()
    baseline = manager.diff_summary(workspace)

    rejected = gateway.execute(
        "apply_patch",
        "controlled-first-patch",
        {"patch": patch},
    )

    assert rejected.status == "rejected"
    assert rejected.error_code == "CONTROLLED_DIAGNOSTIC_REJECTION"
    assert (
        rejected.output["error_details"]["schema_version"]
        == "controlled-rejection-v1"
    )
    assert rejected.output["error_details"]["worktree_mutated"] is False
    assert manager.diff_summary(workspace) == baseline
    events = gateway.state.list_events(gateway.run_id)
    assert sum(
        event.type == EventType.PATCH_PREPARED for event in events
    ) == 1
    assert sum(
        event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code")
        == "CONTROLLED_DIAGNOSTIC_REJECTION"
        for event in events
    ) == 1
    assert not any(
        event.type == EventType.PATCH_APPLIED for event in events
    )

    replayed = gateway.execute(
        "apply_patch",
        "controlled-first-patch",
        {"patch": patch},
    )
    assert replayed.status == "rejected"
    assert replayed.output["replayed"] is True
    assert manager.diff_summary(workspace) == baseline

    recovered_gateway = _fresh_gateway(gateway)
    applied = recovered_gateway.execute(
        "apply_patch",
        "controlled-second-patch",
        {"patch": patch},
    )
    assert applied.status == "succeeded"
    assert manager.diff_summary(workspace).changed_files == [
        "mini_data_utils/csvlite.py"
    ]
    events = gateway.state.list_events(gateway.run_id)
    assert sum(
        event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code")
        == "CONTROLLED_DIAGNOSTIC_REJECTION"
        for event in events
    ) == 1
    assert sum(
        event.type == EventType.PATCH_APPLIED for event in events
    ) == 1


def test_controlled_rejection_requires_prepared_intent_to_be_latest(
    tmp_path,
    monkeypatch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_controlled_rejection_interleaved_prepare",
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
    )
    baseline = manager.diff_summary(workspace)
    original_prepare = gateway._prepare_patch_mutation

    def interleaved_prepare(*args, **kwargs):
        intent = original_prepare(*args, **kwargs)
        gateway.state.append_event(
            gateway.run_id,
            EventType.LOOP_DETECTED,
            actor="tamper-test",
            payload={"reason": "interleaved-after-prepare"},
        )
        return intent

    monkeypatch.setattr(
        gateway,
        "_prepare_patch_mutation",
        interleaved_prepare,
    )
    result = gateway.execute(
        "apply_patch",
        "controlled-interleaved-prepare",
        {"patch": _r2_style_recount_patch()},
    )

    assert result.status == "failed"
    assert result.error_code == "RECOVERY_ERROR"
    assert result.output["fatal"] is True
    assert "not the current latest event" in (
        result.error_message or ""
    )
    assert manager.diff_summary(workspace) == baseline
    assert not any(
        event.type == EventType.PATCH_APPLIED
        for event in gateway.state.list_events(gateway.run_id)
    )


def test_controlled_rejection_durable_declaration_rejects_interleaving(
    tmp_path,
    monkeypatch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_controlled_rejection_interleaved_declaration",
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
    )
    baseline = manager.diff_summary(workspace)
    original_rejection = gateway._controlled_rejection

    def interleaved_rejection(**kwargs):
        rejection = original_rejection(**kwargs)
        gateway.state.append_event(
            gateway.run_id,
            EventType.LOOP_DETECTED,
            actor="tamper-test",
            payload={"reason": "interleaved-before-failure"},
        )
        return rejection

    monkeypatch.setattr(
        gateway,
        "_controlled_rejection",
        interleaved_rejection,
    )
    rejected = gateway.execute(
        "apply_patch",
        "controlled-interleaved-declaration",
        {"patch": _r2_style_recount_patch()},
    )
    assert rejected.error_code == "CONTROLLED_DIAGNOSTIC_REJECTION"

    recovered = _fresh_gateway(gateway)
    result = recovered.execute(
        "apply_patch",
        "controlled-after-interleaved-declaration",
        {"patch": _r2_style_recount_patch()},
    )

    assert result.status == "failed"
    assert result.error_code == "RECOVERY_ERROR"
    assert result.output["fatal"] is True
    assert "evidence is malformed" in (result.error_message or "")
    assert manager.diff_summary(workspace) == baseline
    assert not any(
        event.type == EventType.PATCH_APPLIED
        for event in gateway.state.list_events(gateway.run_id)
    )


def test_invalid_patch_does_not_consume_controlled_rejection(
    tmp_path,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_controlled_after_invalid",
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
    )
    baseline = manager.diff_summary(workspace)

    invalid = gateway.execute(
        "apply_patch",
        "invalid-before-controlled",
        {"patch": "*** Begin Patch\n*** End Patch"},
    )
    controlled = gateway.execute(
        "apply_patch",
        "first-prepared-controlled",
        {"patch": _r2_style_recount_patch()},
    )

    assert invalid.status == "rejected"
    assert invalid.error_code == "CONTRACT_ERROR"
    assert controlled.status == "rejected"
    assert controlled.error_code == "CONTROLLED_DIAGNOSTIC_REJECTION"
    assert manager.diff_summary(workspace) == baseline
    controlled_failures = [
        event
        for event in gateway.state.list_events(gateway.run_id)
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code")
        == "CONTROLLED_DIAGNOSTIC_REJECTION"
    ]
    assert len(controlled_failures) == 1


@pytest.mark.parametrize(
    "crash_boundary",
    ["after-tool-called", "after-patch-prepared"],
)
def test_controlled_rejection_recovery_never_applies_interrupted_patch(
    tmp_path,
    monkeypatch,
    crash_boundary,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        f"run_controlled_recovery_{crash_boundary}",
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
    )
    checkpoint = _durable_checkpoint(gateway)
    baseline = manager.diff_summary(workspace)
    if crash_boundary == "after-tool-called":
        monkeypatch.setattr(
            gateway,
            "_prepare_patch_mutation",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                KeyboardInterrupt("synthetic crash after ToolCalled")
            ),
        )
    else:
        monkeypatch.setattr(
            gateway,
            "_controlled_rejection",
            lambda **_kwargs: (_ for _ in ()).throw(
                KeyboardInterrupt("synthetic crash after PatchPrepared")
            ),
        )

    with pytest.raises(KeyboardInterrupt):
        gateway.execute(
            "apply_patch",
            f"controlled-recovery-{crash_boundary}",
            {"patch": _r2_style_recount_patch()},
        )

    assert manager.diff_summary(workspace) == baseline
    recovered = _fresh_gateway(gateway)
    result = recovered.reconcile_interrupted_patch(checkpoint)

    assert result is not None
    assert result.status == "rejected"
    assert result.error_code == "CONTROLLED_DIAGNOSTIC_REJECTION"
    assert manager.diff_summary(workspace) == baseline
    events = gateway.state.list_events(gateway.run_id)
    assert sum(
        event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code")
        == "CONTROLLED_DIAGNOSTIC_REJECTION"
        for event in events
    ) == 1
    assert not any(
        event.type == EventType.PATCH_APPLIED for event in events
    )


def test_controlled_rejection_recovery_fails_closed_on_malformed_declaration(
    tmp_path,
    monkeypatch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_controlled_recovery_malformed_declaration",
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
    )
    baseline = manager.diff_summary(workspace)
    original_rejection = gateway._controlled_rejection

    def malformed_rejection(**kwargs):
        rejection = original_rejection(**kwargs)
        rejection.details["schema_version"] = "controlled-rejection-corrupt"
        return rejection

    monkeypatch.setattr(
        gateway,
        "_controlled_rejection",
        malformed_rejection,
    )
    malformed = gateway.execute(
        "apply_patch",
        "controlled-malformed-first",
        {"patch": _r2_style_recount_patch()},
    )
    assert malformed.error_code == "CONTROLLED_DIAGNOSTIC_REJECTION"

    recovered = _fresh_gateway(gateway)
    result = recovered.execute(
        "apply_patch",
        "controlled-malformed-retry",
        {"patch": _r2_style_recount_patch()},
    )

    assert result.status == "failed"
    assert result.error_code == "RECOVERY_ERROR"
    assert result.output["fatal"] is True
    assert "evidence is malformed" in (result.error_message or "")
    assert manager.diff_summary(workspace) == baseline
    assert not any(
        event.type == EventType.PATCH_APPLIED
        for event in gateway.state.list_events(gateway.run_id)
    )


def test_controlled_rejection_fails_closed_when_intent_is_not_first_prepared(
    tmp_path,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_controlled_rejection_not_first_prepared",
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
    )
    baseline = manager.diff_summary(workspace)
    gateway.state.append_event(
        gateway.run_id,
        EventType.PATCH_PREPARED,
        actor="tool-gateway",
        correlation_id="corrupt-earlier-intent",
        payload={"schema_version": "patch-mutation-intent-v1"},
    )

    result = gateway.execute(
        "apply_patch",
        "controlled-not-first-prepared",
        {"patch": _r2_style_recount_patch()},
    )

    assert result.status == "failed"
    assert result.error_code == "RECOVERY_ERROR"
    assert result.output["fatal"] is True
    assert "not bound to the first prepared patch" in (
        result.error_message or ""
    )
    assert manager.diff_summary(workspace) == baseline
    assert not any(
        event.type == EventType.PATCH_APPLIED
        for event in gateway.state.list_events(gateway.run_id)
    )


def test_controlled_rejection_recovery_fails_closed_on_duplicate_declaration(
    tmp_path,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_controlled_recovery_duplicate_declaration",
        fault=FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        ),
    )
    baseline = manager.diff_summary(workspace)
    rejected = gateway.execute(
        "apply_patch",
        "controlled-duplicate-first",
        {"patch": _r2_style_recount_patch()},
    )
    assert rejected.error_code == "CONTROLLED_DIAGNOSTIC_REJECTION"
    controlled = next(
        event
        for event in gateway.state.list_events(gateway.run_id)
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("error_code")
        == "CONTROLLED_DIAGNOSTIC_REJECTION"
    )
    gateway.state.append_event(
        gateway.run_id,
        EventType.TOOL_FAILED,
        actor=controlled.actor,
        correlation_id=controlled.correlation_id,
        payload=dict(controlled.payload),
    )

    recovered = _fresh_gateway(gateway)
    result = recovered.execute(
        "apply_patch",
        "controlled-duplicate-retry",
        {"patch": _r2_style_recount_patch()},
    )

    assert result.status == "failed"
    assert result.error_code == "RECOVERY_ERROR"
    assert result.output["fatal"] is True
    assert "duplicate declarations" in (result.error_message or "")
    assert manager.diff_summary(workspace) == baseline
    assert not any(
        event.type == EventType.PATCH_APPLIED
        for event in gateway.state.list_events(gateway.run_id)
    )


def test_interrupted_patch_in_pre_state_is_applied_once_on_recovery(
    tmp_path,
    monkeypatch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recover_pre",
    )
    checkpoint = _durable_checkpoint(gateway)
    patch = _r2_style_recount_patch()

    def crash_before_mutation(*_args, **_kwargs):
        raise SystemExit(86)

    monkeypatch.setattr(gateway, "_apply_patch", crash_before_mutation)
    with pytest.raises(SystemExit, match="86"):
        gateway.execute(
            "apply_patch",
            "recover-pre-action",
            {"patch": patch},
        )

    assert manager.diff_summary(workspace).patch_hash == checkpoint.worktree_diff_hash
    recovered = _fresh_gateway(gateway)
    result = recovered.reconcile_interrupted_patch(checkpoint)

    assert result is not None
    assert result.status == "succeeded"
    assert manager.diff_summary(workspace).patch_hash == result.output[
        "worktree_diff_hash"
    ]
    events = gateway.state.list_events(gateway.run_id)
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 1
    assert sum(event.type == EventType.PATCH_PREPARED for event in events) == 1
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 1


def test_interrupted_read_action_reuses_tool_call_and_closes_outcome(
    tmp_path,
    monkeypatch,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recover_read",
    )
    checkpoint = _durable_checkpoint(gateway)

    def crash_after_call(*_args, **_kwargs):
        raise SystemExit(86)

    monkeypatch.setattr(gateway, "_dispatch", crash_after_call)
    with pytest.raises(SystemExit, match="86"):
        gateway.execute(
            "read_file",
            "recover-read-action",
            {
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 3,
            },
        )

    recovered = _fresh_gateway(gateway)
    reconciled = recovered.reconcile_interrupted_action(checkpoint)

    assert reconciled is not None
    name, result = reconciled
    assert name == "read_file"
    assert result.status == "succeeded"
    events = gateway.state.list_events(gateway.run_id)
    assert (
        sum(
            event.type == EventType.TOOL_CALLED
            and event.correlation_id == "recover-read-action"
            for event in events
        )
        == 1
    )
    assert (
        sum(
            event.type == EventType.TOOL_SUCCEEDED
            and event.correlation_id == "recover-read-action"
            for event in events
        )
        == 1
    )


def test_interrupted_patch_in_post_state_is_not_applied_twice(
    tmp_path,
    monkeypatch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recover_post",
    )
    checkpoint = _durable_checkpoint(gateway)
    patch = _r2_style_recount_patch()

    def crash_before_completion(*_args, **_kwargs):
        raise SystemExit(86)

    monkeypatch.setattr(gateway, "_complete_result", crash_before_completion)
    with pytest.raises(SystemExit, match="86"):
        gateway.execute(
            "apply_patch",
            "recover-post-action",
            {"patch": patch},
        )
    post_crash_hash = manager.diff_summary(workspace).patch_hash
    assert post_crash_hash != checkpoint.worktree_diff_hash

    recovered = _fresh_gateway(gateway)

    def reject_second_forward_apply(*_args, **_kwargs):
        raise AssertionError("recovery attempted to apply the patch twice")

    monkeypatch.setattr(recovered, "_apply_patch", reject_second_forward_apply)
    result = recovered.reconcile_interrupted_patch(checkpoint)

    assert result is not None
    assert result.status == "succeeded"
    assert result.output["worktree_diff_hash"] == post_crash_hash
    assert manager.diff_summary(workspace).patch_hash == post_crash_hash
    events = gateway.state.list_events(gateway.run_id)
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 1
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 1


def test_partial_multi_file_patch_restores_preimages_then_applies_once(
    tmp_path,
    monkeypatch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recover_partial",
    )
    gateway.task = gateway.task.model_copy(
        update={
            "constraints": gateway.task.constraints.model_copy(
                update={"max_changed_files": 2}
            )
        }
    )
    checkpoint = _durable_checkpoint(gateway)
    patch = (
        "diff --git a/mini_data_utils/csvlite.py "
        "b/mini_data_utils/csvlite.py\n"
        "--- a/mini_data_utils/csvlite.py\n"
        "+++ b/mini_data_utils/csvlite.py\n"
        "@@ -1,2 +1,2 @@\n"
        '-"""A deliberately small CSV reader with one audited defect."""\n'
        '+"""A deliberately small CSV reader with one recoverable defect."""\n'
        " \n"
        "diff --git a/mini_data_utils/__init__.py "
        "b/mini_data_utils/__init__.py\n"
        "--- a/mini_data_utils/__init__.py\n"
        "+++ b/mini_data_utils/__init__.py\n"
        "@@ -1,2 +1,2 @@\n"
        '-"""Small data utilities used only as an audited PatchLoop fixture."""\n'
        '+"""Small data utilities used only as a durable PatchLoop fixture."""\n'
        " \n"
    )

    def crash_before_mutation(*_args, **_kwargs):
        raise SystemExit(86)

    monkeypatch.setattr(gateway, "_apply_patch", crash_before_mutation)
    with pytest.raises(SystemExit, match="86"):
        gateway.execute(
            "apply_patch",
            "recover-partial-action",
            {"patch": patch},
        )

    prepared = next(
        event
        for event in gateway.state.list_events(gateway.run_id)
        if event.type == EventType.PATCH_PREPARED
    )
    intent_artifact = Artifact.model_validate(
        prepared.payload["intent_artifact"]
    )
    intent = json.loads(
        gateway.artifacts.read_bytes(intent_artifact).decode("utf-8")
    )
    first = intent["files"][0]
    first_post = Artifact.model_validate(first["postimage_artifact"])
    (workspace / first["path"]).write_bytes(
        gateway.artifacts.read_bytes(first_post)
    )

    recovered = _fresh_gateway(gateway)
    result = recovered.reconcile_interrupted_patch(checkpoint)

    assert result is not None
    assert result.status == "succeeded"
    assert "recoverable defect" in (
        workspace / "mini_data_utils" / "csvlite.py"
    ).read_text(encoding="utf-8")
    assert "durable PatchLoop fixture" in (
        workspace / "mini_data_utils" / "__init__.py"
    ).read_text(encoding="utf-8")
    assert manager.diff_summary(workspace).patch_hash == result.output[
        "worktree_diff_hash"
    ]


def test_preflight_validates_every_postimage_target_before_any_write(
    tmp_path,
) -> None:
    _, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_preflight_all_targets",
    )
    patch = (
        "diff --git a/mini_data_utils/csvlite.py "
        "b/mini_data_utils/csvlite.py\n"
        "--- a/mini_data_utils/csvlite.py\n"
        "+++ b/mini_data_utils/csvlite.py\n"
        "@@ -1,2 +1,2 @@\n"
        '-"""A deliberately small CSV reader with one audited defect."""\n'
        '+"""A deliberately small CSV reader with one recoverable defect."""\n'
        " \n"
        "diff --git a/mini_data_utils/__init__.py "
        "b/mini_data_utils/__init__.py\n"
        "--- a/mini_data_utils/__init__.py\n"
        "+++ b/mini_data_utils/__init__.py\n"
        "@@ -1,2 +1,2 @@\n"
        '-"""Small data utilities used only as an audited PatchLoop fixture."""\n'
        '+"""Small data utilities used only as a durable PatchLoop fixture."""\n'
        " \n"
    )
    action_id = "preflight-all-targets"
    input_hash = sha256_text(
        canonical_json({"tool": "apply_patch", "input": {"patch": patch}})
    )
    patch_artifact = gateway.artifacts.put_text(
        patch,
        media_type="text/x-diff",
    )
    intent = gateway._prepare_patch_mutation(
        action_id,
        input_hash,
        patch,
        patch_artifact,
    )
    first = workspace / "mini_data_utils" / "csvlite.py"
    second = workspace / "mini_data_utils" / "__init__.py"
    first_before = first.read_bytes()
    second_unknown = second.read_bytes().replace(
        b"audited PatchLoop fixture",
        b"unknown external state",
    )
    second.write_bytes(second_unknown)

    with pytest.raises(RecoveryError, match="pre-state"):
        gateway._apply_patch_postimages(intent)

    assert first.read_bytes() == first_before
    assert second.read_bytes() == second_unknown


def test_mixed_recovery_does_not_overwrite_unrelated_tracked_change(
    tmp_path,
    monkeypatch,
) -> None:
    _, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_mixed_unrelated",
    )
    checkpoint = _durable_checkpoint(gateway)
    patch = (
        "diff --git a/mini_data_utils/csvlite.py "
        "b/mini_data_utils/csvlite.py\n"
        "--- a/mini_data_utils/csvlite.py\n"
        "+++ b/mini_data_utils/csvlite.py\n"
        "@@ -1,2 +1,2 @@\n"
        '-"""A deliberately small CSV reader with one audited defect."""\n'
        '+"""A deliberately small CSV reader with one recoverable defect."""\n'
        " \n"
        "diff --git a/mini_data_utils/__init__.py "
        "b/mini_data_utils/__init__.py\n"
        "--- a/mini_data_utils/__init__.py\n"
        "+++ b/mini_data_utils/__init__.py\n"
        "@@ -1,2 +1,2 @@\n"
        '-"""Small data utilities used only as an audited PatchLoop fixture."""\n'
        '+"""Small data utilities used only as a durable PatchLoop fixture."""\n'
        " \n"
    )

    def crash_before_mutation(*_args, **_kwargs):
        raise SystemExit(86)

    monkeypatch.setattr(gateway, "_apply_patch", crash_before_mutation)
    with pytest.raises(SystemExit, match="86"):
        gateway.execute(
            "apply_patch",
            "mixed-unrelated-action",
            {"patch": patch},
        )
    prepared = next(
        event
        for event in gateway.state.list_events(gateway.run_id)
        if event.type == EventType.PATCH_PREPARED
    )
    intent = json.loads(
        gateway.artifacts.read_bytes(
            Artifact.model_validate(prepared.payload["intent_artifact"])
        ).decode("utf-8")
    )
    first_entry = intent["files"][0]
    first = workspace / first_entry["path"]
    first.write_bytes(
        gateway.artifacts.read_bytes(
            Artifact.model_validate(
                first_entry["postimage_artifact"]
            )
        )
    )
    unrelated = workspace / "README.md"
    unrelated.write_text(
        unrelated.read_text(encoding="utf-8")
        + "\nunrelated third state\n",
        encoding="utf-8",
    )
    bytes_before = {
        path: (workspace / path).read_bytes()
        for path in (
            first_entry["path"],
            intent["files"][1]["path"],
            "README.md",
        )
    }

    result = _fresh_gateway(gateway).reconcile_interrupted_patch(checkpoint)

    assert result is not None
    assert result.status == "failed"
    assert result.output["fatal"] is True
    assert "outside the prepared mutation" in (
        result.error_message or ""
    )
    assert {
        path: (workspace / path).read_bytes()
        for path in bytes_before
    } == bytes_before


def test_interrupted_patch_with_tampered_intent_fails_closed(
    tmp_path,
    monkeypatch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recover_tampered",
    )
    checkpoint = _durable_checkpoint(gateway)

    def crash_before_mutation(*_args, **_kwargs):
        raise SystemExit(86)

    monkeypatch.setattr(gateway, "_apply_patch", crash_before_mutation)
    with pytest.raises(SystemExit, match="86"):
        gateway.execute(
            "apply_patch",
            "recover-tampered-action",
            {"patch": _r2_style_recount_patch()},
        )
    prepared = next(
        event
        for event in gateway.state.list_events(gateway.run_id)
        if event.type == EventType.PATCH_PREPARED
    )
    Path(prepared.payload["artifact_path"]).write_bytes(b"tampered")

    result = _fresh_gateway(gateway).reconcile_interrupted_patch(checkpoint)

    assert result is not None
    assert result.status == "failed"
    assert result.output["fatal"] is True
    assert result.error_code == "RECOVERY_ERROR"
    assert manager.diff_summary(workspace).patch_hash == checkpoint.worktree_diff_hash


def test_interrupted_patch_with_unknown_file_state_does_not_overwrite_it(
    tmp_path,
    monkeypatch,
) -> None:
    _, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recover_unknown",
    )
    checkpoint = _durable_checkpoint(gateway)

    def crash_before_mutation(*_args, **_kwargs):
        raise SystemExit(86)

    monkeypatch.setattr(gateway, "_apply_patch", crash_before_mutation)
    with pytest.raises(SystemExit, match="86"):
        gateway.execute(
            "apply_patch",
            "recover-unknown-action",
            {"patch": _r2_style_recount_patch()},
        )
    target = workspace / "mini_data_utils" / "csvlite.py"
    unknown = target.read_text(encoding="utf-8").replace(
        "one audited defect",
        "an unrelated third state",
    )
    target.write_text(unknown, encoding="utf-8")

    result = _fresh_gateway(gateway).reconcile_interrupted_patch(checkpoint)

    assert result is not None
    assert result.status == "failed"
    assert result.output["fatal"] is True
    assert "unknown state" in (result.error_message or "")
    assert target.read_text(encoding="utf-8") == unknown


def test_interrupted_policy_bad_post_state_is_rolled_back_and_rejected(
    tmp_path,
    monkeypatch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recover_policy_bad",
    )
    checkpoint = _durable_checkpoint(gateway)
    patch = Path(
        "tasks/smoke/csv-quoted-newline/bad/forbidden-path.patch"
    ).read_text(encoding="utf-8")

    def crash_before_policy(*_args, **_kwargs):
        raise SystemExit(86)

    monkeypatch.setattr(
        gateway,
        "_finalize_applied_patch",
        crash_before_policy,
    )
    with pytest.raises(SystemExit, match="86"):
        gateway.execute(
            "apply_patch",
            "recover-policy-bad-action",
            {"patch": patch},
        )
    assert manager.diff_summary(workspace).patch_hash != checkpoint.worktree_diff_hash

    result = _fresh_gateway(gateway).reconcile_interrupted_patch(checkpoint)

    assert result is not None
    assert result.status == "rejected"
    assert "outside allowed_paths" in (result.error_message or "")
    assert manager.diff_summary(workspace).patch_hash == checkpoint.worktree_diff_hash
    events = gateway.state.list_events(gateway.run_id)
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 0
    assert sum(event.type == EventType.TOOL_FAILED for event in events) == 1


def test_recounted_patch_replay_is_idempotent(tmp_path) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recount_replay",
    )
    patch = _r2_style_recount_patch()

    first = gateway.execute(
        "apply_patch",
        "recount-replay",
        {"patch": patch},
    )
    first_diff_hash = manager.diff_summary(workspace).patch_hash
    second = gateway.execute(
        "apply_patch",
        "recount-replay",
        {"patch": patch},
    )

    assert first.status == "succeeded"
    assert second.status == "succeeded"
    assert second.output["replayed"] is True
    assert manager.diff_summary(workspace).patch_hash == first_diff_hash
    events = gateway.state.list_events(gateway.run_id)
    assert sum(event.type.value == "ToolCalled" for event in events) == 1
    assert sum(event.type == EventType.TOOL_SUCCEEDED for event in events) == 1
    assert sum(event.type == EventType.TOOL_REPLAYED for event in events) == 1
    assert sum(event.type.value == "PatchApplied" for event in events) == 1
    conflicting_patch = patch.replace("verified defect", "reviewed defect", 1)
    with pytest.raises(ActionConflict):
        gateway.execute(
            "apply_patch",
            "recount-replay",
            {"patch": conflicting_patch},
        )
    assert manager.diff_summary(workspace).patch_hash == first_diff_hash


def test_v1_cached_result_preserves_legacy_outcome_event(tmp_path) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v1_replay",
        tool_schema_version="v1",
    )
    arguments = {
        "path": "mini_data_utils/csvlite.py",
        "start_line": 1,
        "end_line": 3,
    }

    first = gateway.execute(
        "read_file",
        "legacy-read-replay",
        arguments,
    )
    second = gateway.execute(
        "read_file",
        "legacy-read-replay",
        arguments,
    )

    assert first.status == "succeeded"
    assert second.output["replayed"] is True
    events = gateway.state.list_events(gateway.run_id)
    assert sum(
        event.type == EventType.TOOL_SUCCEEDED for event in events
    ) == 2
    assert not any(
        event.type == EventType.TOOL_REPLAYED for event in events
    )


def test_recounted_policy_violation_is_rolled_back_with_same_patch(tmp_path) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recount_rollback",
    )
    accepted_patch = _r2_style_recount_patch()
    accepted = gateway.execute(
        "apply_patch",
        "recount-before-forbidden",
        {"patch": accepted_patch},
    )
    assert accepted.status == "succeeded"
    pre_rejection_diff_hash = manager.diff_summary(workspace).patch_hash

    patch = Path(
        "tasks/smoke/csv-quoted-newline/bad/forbidden-path.patch"
    ).read_text(encoding="utf-8")
    patch = patch.replace("@@ -1,4 +1,6 @@", "@@ -1,40 +1,60 @@")

    result = gateway.execute(
        "apply_patch",
        "recount-forbidden-text-patch",
        {"patch": patch},
    )

    assert result.status == "rejected"
    assert "outside allowed_paths" in (result.error_message or "")
    summary = manager.diff_summary(workspace)
    assert summary.patch_hash == pre_rejection_diff_hash
    assert summary.changed_files == ["mini_data_utils/csvlite.py"]
    assert "intentionally outside the task scope" not in (
        workspace / "README.md"
    ).read_text(encoding="utf-8")


def test_search_glob_cannot_escape_workspace(tmp_path) -> None:
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(package, run_id="run_gateway_search")
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    workspace = manager.create(
        manifest.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    gateway = ToolGateway(
        run_id=manifest.run_id,
        workspace=workspace,
        task=package.public,
        state=state,
        artifacts=ArtifactStore(tmp_path / "artifacts"),
        sandbox=LocalSandbox(),
    )
    result = gateway.execute(
        "search_files", "escape-search", {"query": "secret", "path_glob": "../**/*"}
    )
    assert result.status == "rejected"
    assert result.error_code == "CONTRACT_ERROR"


def test_rejected_patch_format_is_durable_and_visible_to_next_turn(tmp_path) -> None:
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(package, run_id="run_gateway_patch_format")
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    workspace = manager.create(
        manifest.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    gateway = ToolGateway(
        run_id=manifest.run_id,
        workspace=workspace,
        task=package.public,
        state=state,
        artifacts=artifact_store,
        sandbox=LocalSandbox(),
    )

    result = gateway.execute(
        "apply_patch",
        "invalid-patch-envelope",
        {
            "patch": (
                "*** Begin Patch\n"
                "*** Update File: mini_data_utils/csvlite.py\n"
                "*** End Patch"
            )
        },
    )

    assert result.status == "rejected"
    assert "raw Git unified diff" in (result.error_message or "")
    assert result.output["error_details"]["stage"] == "format"
    assert result.output["error_details"]["reason"] == "invalid_envelope"
    patch_schema = next(schema for schema in TOOL_SCHEMAS if schema["name"] == "apply_patch")
    assert "diff --git" in patch_schema["description"]
    assert "*** Begin Patch" in patch_schema["description"]
    error_artifact = Path(result.output["artifact_path"])
    assert error_artifact.is_file()
    events = state.list_events(manifest.run_id)
    failed = events[-1]
    assert failed.payload["error_message"] == result.error_message
    assert failed.payload["result_artifact"] == result.output["result_artifact"]
    context, _ = build_context(
        package.public,
        events,
        None,
        artifact_store=artifact_store,
    )
    assert "raw Git unified diff" in context
    assert "diff --git" in context


def test_check_and_diff_results_are_bound_to_current_worktree(tmp_path) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_diff_binding",
    )
    patch = Path(
        "tasks/smoke/csv-quoted-newline/reference.patch"
    ).read_text(encoding="utf-8")

    applied = gateway.execute(
        "apply_patch",
        "diff-binding-patch",
        {"patch": patch},
    )
    checked = gateway.execute(
        "run_check",
        "diff-binding-check",
        {"check_id": "existing-unit-tests"},
    )
    reviewed = gateway.execute("get_diff", "diff-binding-review", {})

    diff_hash = manager.diff_summary(workspace).patch_hash
    assert applied.output["worktree_diff_hash"] == diff_hash
    assert checked.output["worktree_diff_hash"] == diff_hash
    assert reviewed.output["worktree_diff_hash"] == diff_hash
    bound_events = [
        event
        for event in gateway.state.list_events(gateway.run_id)
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") in {"run_check", "get_diff"}
    ]
    assert {event.payload["worktree_diff_hash"] for event in bound_events} == {
        diff_hash
    }


def test_repeated_call_is_advisory_and_visible(tmp_path) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_repeat_signal",
    )
    arguments = {"query": "parse_rows", "path_glob": "**/*.py"}

    first = gateway.execute("search_files", "search-first", arguments)
    second = gateway.execute("search_files", "search-second", arguments)

    assert first.status == second.status == "succeeded"
    loop_events = [
        event
        for event in gateway.state.list_events(gateway.run_id)
        if event.type == EventType.LOOP_DETECTED
    ]
    assert len(loop_events) == 1
    assert loop_events[0].payload["tool"] == "search_files"
    assert loop_events[0].payload["enforcement"] == "advisory"


def test_nonconsecutive_repeated_call_is_not_marked_as_loop(tmp_path) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_nonconsecutive_repeat",
    )
    repeated = {"query": "parse_rows", "path_glob": "**/*.py"}

    gateway.execute("search_files", "search-first", repeated)
    gateway.execute(
        "read_file",
        "read-between-searches",
        {
            "path": "mini_data_utils/csvlite.py",
            "start_line": 1,
            "end_line": 2,
        },
    )
    gateway.execute("search_files", "search-after-read", repeated)

    assert not [
        event
        for event in gateway.state.list_events(gateway.run_id)
        if event.type == EventType.LOOP_DETECTED
    ]


def test_v4_nonconsecutive_exact_search_uses_semantic_replay(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_search_replay",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    repeated = {"query": "parse_rows", "path_glob": "**/*.py"}

    first = gateway.execute("search_files", "search-first", repeated)
    gateway.execute(
        "read_file",
        "read-between-searches",
        {
            "path": "mini_data_utils/csvlite.py",
            "start_line": 1,
            "end_line": 2,
        },
    )
    second = gateway.execute(
        "search_files",
        "search-after-read",
        repeated,
    )

    assert first.status == second.status == "succeeded"
    assert second.output["semantic_replay"] is True
    assert "replayed" not in second.output
    assert second.output["novelty"] == {
        "classification": "seen_only",
        "new_evidence_count": 0,
        "reason": "duplicate_search",
    }
    assert second.output["matches"] == first.output["matches"]
    events = gateway.state.list_events(gateway.run_id)
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 3
    assert sum(event.type == EventType.TOOL_SUCCEEDED for event in events) == 2
    assert sum(event.type == EventType.TOOL_REPLAYED for event in events) == 1
    loop = next(
        event
        for event in events
        if event.type == EventType.LOOP_DETECTED
    )
    assert loop.payload["schema_version"] == "investigation-loop-v1"
    assert loop.payload["reason_code"] == "duplicate_search"
    assert loop.payload["enforcement"] == "semantic-cache-replay"


def test_v4_truncated_exact_search_dispatches_again(
    tmp_path,
) -> None:
    _, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_truncated_search",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    generated = workspace / "generated"
    generated.mkdir()
    for index in range(101):
        (generated / f"match_{index:03d}.txt").write_text(
            "replay-boundary-marker\n",
            encoding="utf-8",
        )
    arguments = {
        "query": "replay-boundary-marker",
        "path_glob": "generated/*.txt",
    }

    first = gateway.execute(
        "search_files",
        "truncated-search-first",
        arguments,
    )
    second = gateway.execute(
        "search_files",
        "truncated-search-second",
        arguments,
    )

    assert first.output["truncated"] is True
    assert second.output["truncated"] is True
    assert "semantic_replay" not in second.output
    events = gateway.state.list_events(gateway.run_id)
    assert sum(event.type == EventType.TOOL_SUCCEEDED for event in events) == 2
    assert not any(event.type == EventType.TOOL_REPLAYED for event in events)


def test_v4_fully_covered_read_is_reconstructed_from_result_cas(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_read_replay",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    path = "mini_data_utils/csvlite.py"

    first = gateway.execute(
        "read_file",
        "read-entire-file",
        {"path": path, "start_line": 1, "end_line": 200},
    )
    second = gateway.execute(
        "read_file",
        "read-covered-subset",
        {"path": path, "start_line": 2, "end_line": 4},
    )

    expected = "\n".join(first.output["content"].split("\n")[1:4])
    assert second.status == "succeeded"
    assert second.output["semantic_replay"] is True
    assert second.output["replay_reason"] == "fully_covered_read"
    assert second.output["content"] == expected
    assert second.output["actual_start_line"] == 2
    assert second.output["actual_end_line"] == 4
    events = gateway.state.list_events(gateway.run_id)
    assert sum(event.type == EventType.TOOL_SUCCEEDED for event in events) == 1
    assert sum(event.type == EventType.TOOL_REPLAYED for event in events) == 1

    beyond_eof = gateway.execute(
        "read_file",
        "read-covered-eof",
        {"path": path, "start_line": 100, "end_line": 200},
    )
    assert beyond_eof.output["semantic_replay"] is True
    assert beyond_eof.output["content"] == ""
    assert beyond_eof.output["actual_start_line"] is None
    assert beyond_eof.output["eof_reached"] is True


def test_v4_adjacent_read_ranges_form_replayable_union(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_adjacent_read",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    path = "mini_data_utils/csvlite.py"
    gateway.execute(
        "read_file",
        "read-adjacent-left",
        {"path": path, "start_line": 1, "end_line": 3},
    )
    gateway.execute(
        "read_file",
        "read-adjacent-right",
        {"path": path, "start_line": 4, "end_line": 6},
    )

    result = gateway.execute(
        "read_file",
        "read-across-adjacent-union",
        {"path": path, "start_line": 2, "end_line": 5},
    )

    assert result.output["semantic_replay"] is True
    assert result.output["actual_start_line"] == 2
    assert result.output["actual_end_line"] == 5


def test_v4_partially_overlapping_read_dispatches_new_evidence(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_partial_read",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    path = "mini_data_utils/csvlite.py"

    gateway.execute(
        "read_file",
        "read-first-range",
        {"path": path, "start_line": 1, "end_line": 5},
    )
    result = gateway.execute(
        "read_file",
        "read-overlap-with-new-lines",
        {"path": path, "start_line": 5, "end_line": 10},
    )

    assert result.status == "succeeded"
    assert "semantic_replay" not in result.output
    assert result.output["novelty"]["classification"] == "novel"
    assert result.output["novelty"]["new_evidence_count"] == 5
    events = gateway.state.list_events(gateway.run_id)
    assert sum(event.type == EventType.TOOL_SUCCEEDED for event in events) == 2
    assert not any(event.type == EventType.TOOL_REPLAYED for event in events)


def test_v4_patch_starts_a_new_investigation_epoch(tmp_path) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_epoch",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    arguments = {"query": "parse_rows", "path_glob": "**/*.py"}

    gateway.execute("search_files", "search-before-patch", arguments)
    applied = gateway.execute(
        "apply_patch",
        "epoch-patch",
        {"patch": _r2_style_recount_patch()},
    )
    after = gateway.execute(
        "search_files",
        "search-after-patch",
        arguments,
    )

    assert applied.status == "succeeded"
    assert after.status == "succeeded"
    assert "semantic_replay" not in after.output
    events = gateway.state.list_events(gateway.run_id)
    assert sum(event.type == EventType.TOOL_SUCCEEDED for event in events) == 3
    assert not any(event.type == EventType.TOOL_REPLAYED for event in events)


def test_v4_tail_policy_blocks_inspection_before_tool_admission(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_tail",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    for index in range(16):
        gateway.state.append_event(
            gateway.run_id,
            EventType.MODEL_CALLED,
            actor="test-model",
            payload={"index": index},
        )

    result = gateway.execute(
        "search_files",
        "blocked-tail-search",
        {"query": "parse_rows", "path_glob": "**/*.py"},
    )

    assert result.status == "rejected"
    assert result.error_code == "TOOL_ADMISSION_BLOCKED"
    assert result.output["admission_blocked"] is True
    events = gateway.state.list_events(gateway.run_id)
    assert not any(event.type == EventType.TOOL_CALLED for event in events)
    blocked = next(
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
    )
    assert blocked.payload["reason_codes"] == ["model_tail_reserved"]


def test_v4_tail_policy_blocks_semantic_replay_before_tool_admission(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_tail_semantic_replay",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    arguments = {"query": "parse_rows", "path_glob": "**/*.py"}
    initial = gateway.execute(
        "search_files",
        "tail-source-search",
        arguments,
    )
    assert initial.status == "succeeded"
    for index in range(16):
        gateway.state.append_event(
            gateway.run_id,
            EventType.MODEL_CALLED,
            actor="test-model",
            payload={"index": index},
        )

    blocked = gateway.execute(
        "search_files",
        "tail-duplicate-search",
        arguments,
    )

    assert blocked.status == "rejected"
    assert blocked.error_code == "TOOL_ADMISSION_BLOCKED"
    events = gateway.state.list_events(gateway.run_id)
    assert not any(
        event.type == EventType.TOOL_CALLED
        and event.correlation_id == "tail-duplicate-search"
        for event in events
    )
    assert not any(
        event.type == EventType.TOOL_REPLAYED
        and event.correlation_id == "tail-duplicate-search"
        for event in events
    )


def test_v4_tail_policy_does_not_hide_invalid_inspection_input(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_tail_invalid_path",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    for index in range(16):
        gateway.state.append_event(
            gateway.run_id,
            EventType.MODEL_CALLED,
            actor="test-model",
            payload={"index": index},
        )

    result = gateway.execute(
        "read_file",
        "unsafe-tail-read",
        {
            "path": "../outside.py",
            "start_line": 1,
            "end_line": 2,
        },
    )

    assert result.status == "rejected"
    assert result.error_code == "CONTRACT_ERROR"
    events = gateway.state.list_events(gateway.run_id)
    assert any(event.type == EventType.TOOL_CALLED for event in events)
    assert not any(
        event.type == EventType.TOOL_ADMISSION_BLOCKED
        for event in events
    )


def test_v4_tail_policy_does_not_hide_missing_read_target(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_tail_missing_read",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    for index in range(16):
        gateway.state.append_event(
            gateway.run_id,
            EventType.MODEL_CALLED,
            actor="test-model",
            payload={"index": index},
        )

    result = gateway.execute(
        "read_file",
        "missing-tail-read",
        {
            "path": "mini_data_utils/missing.py",
            "start_line": 1,
            "end_line": 2,
        },
    )

    assert result.status == "rejected"
    assert result.error_code == "CONTRACT_ERROR"
    events = gateway.state.list_events(gateway.run_id)
    assert any(
        event.type == EventType.TOOL_CALLED
        and event.correlation_id == "missing-tail-read"
        for event in events
    )
    assert not any(
        event.type == EventType.TOOL_ADMISSION_BLOCKED
        for event in events
    )


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        (
            "read_file",
            {
                "path": "mini_data_utils/csvlite.py",
                "start_line": True,
                "end_line": 2,
            },
        ),
        (
            "read_file",
            {
                "path": 1,
                "start_line": 1,
                "end_line": 2,
            },
        ),
        (
            "search_files",
            {"query": "parse_rows", "path_glob": 1},
        ),
    ],
)
def test_v4_invalid_inspection_types_close_as_structured_tool_failure(
    tmp_path,
    tool,
    arguments,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        f"run_gateway_v4_invalid_type_{tool}",
    )
    gateway.context_policy_version = "phase-evidence-v4"

    result = gateway.execute(
        tool,
        f"invalid-type-{tool}",
        arguments,
    )

    assert result.status == "rejected"
    assert result.error_code == "CONTRACT_ERROR"
    events = gateway.state.list_events(gateway.run_id)
    assert any(event.type == EventType.TOOL_CALLED for event in events)
    assert any(event.type == EventType.TOOL_FAILED for event in events)


@pytest.mark.parametrize(
    "context_policy_version",
    ["phase-evidence-v4", "phase-evidence-v5"],
)
@pytest.mark.parametrize(
    "invalid_glob",
    [
        "a/**b",
        ".",
        "C:foo",
        "a" * 501,
        "/".join(["a"] * 101),
    ],
)
def test_tail_policy_does_not_hide_invalid_search_glob(
    tmp_path,
    context_policy_version: str,
    invalid_glob: str,
) -> None:
    budget = Budget(
        max_model_calls=21,
        max_tool_calls=50,
        max_total_tokens=180_000,
    )
    _, _, gateway = _smoke_gateway(
        tmp_path,
        f"run_gateway_invalid_glob_{context_policy_version}",
        manifest_context_policy_version=context_policy_version,
        budget=budget,
        max_output_tokens=25_000,
    )
    gateway.context_policy_version = context_policy_version
    if context_policy_version == "phase-evidence-v4":
        for index in range(16):
            gateway.state.append_event(
                gateway.run_id,
                EventType.MODEL_CALLED,
                actor="test-model",
                payload={"index": index},
            )
    else:
        gateway.state.append_event(
            gateway.run_id,
            EventType.MODEL_CALLED,
            actor="test-model",
            payload={
                "requested_input_tokens": 30_000,
                "input_tokens": 30_000,
                "output_tokens": 5_000,
            },
        )

    result = gateway.execute(
        "search_files",
        f"invalid-glob-{context_policy_version}",
        {"query": "parse_rows", "path_glob": invalid_glob},
    )

    assert result.status == "rejected"
    assert result.error_code == "CONTRACT_ERROR"
    events = gateway.state.list_events(gateway.run_id)
    assert any(
        event.type == EventType.TOOL_CALLED
        and event.correlation_id == f"invalid-glob-{context_policy_version}"
        for event in events
    )
    assert any(
        event.type == EventType.TOOL_FAILED
        and event.correlation_id == f"invalid-glob-{context_policy_version}"
        for event in events
    )
    assert not any(
        event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.correlation_id == f"invalid-glob-{context_policy_version}"
        for event in events
    )


def test_v4_tail_policy_does_not_hide_symlink_escape(
    tmp_path,
) -> None:
    _, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_tail_symlink_escape",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    outside = tmp_path / "outside.py"
    outside.write_text("secret = 1\n", encoding="utf-8")
    link = workspace / "mini_data_utils" / "outside-link.py"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    for index in range(16):
        gateway.state.append_event(
            gateway.run_id,
            EventType.MODEL_CALLED,
            actor="test-model",
            payload={"index": index},
        )

    result = gateway.execute(
        "read_file",
        "symlink-escape-tail-read",
        {
            "path": "mini_data_utils/outside-link.py",
            "start_line": 1,
            "end_line": 2,
        },
    )

    assert result.status == "rejected"
    assert result.error_code == "CONTRACT_ERROR"
    events = gateway.state.list_events(gateway.run_id)
    assert any(event.type == EventType.TOOL_CALLED for event in events)
    assert not any(
        event.type == EventType.TOOL_ADMISSION_BLOCKED
        for event in events
    )


@pytest.mark.parametrize(
    ("remaining_model_calls", "exploration_admitted"),
    [
        (6, True),
        (5, False),
        (4, False),
    ],
)
def test_v4_context_projects_the_imminent_model_call_for_tail_policy(
    tmp_path,
    remaining_model_calls: int,
    exploration_admitted: bool,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        f"run_gateway_v4_tail_projection_{remaining_model_calls}",
    )
    checkpoint = Checkpoint(
        checkpoint_id=f"ckpt-v4-tail-{remaining_model_calls}",
        run_id=gateway.run_id,
        through_sequence=0,
        phase=Phase.REPRODUCE,
        repository_head="fixture",
        worktree_diff_hash=sha256_text(""),
        remaining_budget={
            "model_calls": remaining_model_calls,
            "tool_calls": 50,
            "tokens": 10_000,
        },
        created_at=utc_now(),
    )

    context, _ = build_context(
        gateway.task,
        [],
        checkpoint,
        policy_version="phase-evidence-v4",
        artifact_store=gateway.artifacts,
    )
    payload = json.loads(context)
    tail = payload["investigation_ledger"]["tail_policy"]

    assert tail["exploration_admitted"] is exploration_admitted
    assert tail["remaining_budget"][
        "model_calls_after_next_generation"
    ] == max(0, remaining_model_calls - 1)
    allowed = payload["phase_contract"]["allowed_next_actions"]
    assert ("search_files" in allowed) is exploration_admitted
    assert ("read_file" in allowed) is exploration_admitted


def test_v4_context_removes_inspection_from_tail_actions(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_tail_context",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    checkpoint = Checkpoint(
        checkpoint_id="ckpt-v4-tail-context",
        run_id=gateway.run_id,
        through_sequence=0,
        phase=Phase.REPRODUCE,
        repository_head="fixture",
        worktree_diff_hash=sha256_text(""),
        remaining_budget={
            "model_calls": 4,
            "tool_calls": 50,
            "tokens": 10_000,
        },
        created_at=utc_now(),
    )

    context, _ = build_context(
        gateway.task,
        [],
        checkpoint,
        policy_version="phase-evidence-v4",
        artifact_store=gateway.artifacts,
    )

    payload = json.loads(context)
    assert payload["investigation_ledger"]["tail_policy"][
        "exploration_admitted"
    ] is False
    assert "search_files" not in payload["phase_contract"][
        "allowed_next_actions"
    ]
    assert "read_file" not in payload["phase_contract"][
        "allowed_next_actions"
    ]
    assert "apply_patch" in payload["phase_contract"][
        "allowed_next_actions"
    ]


def test_v5_context_projects_exact_input_growth_across_five_tail_turns(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v5_token_projection",
        manifest_context_policy_version="phase-evidence-v5",
        budget=Budget(
            max_model_calls=21,
            max_tool_calls=50,
            max_total_tokens=211_000,
        ),
        max_output_tokens=25_000,
    )
    gateway.context_policy_version = "phase-evidence-v5"
    for requested, output in ((20_000, 1_000), (24_000, 1_000)):
        gateway.state.append_event(
            gateway.run_id,
            EventType.MODEL_CALLED,
            actor="test-model",
            payload={
                "requested_input_tokens": requested,
                "input_tokens": requested,
                "output_tokens": output,
            },
        )
    events = gateway.state.list_events(gateway.run_id)
    built = build_context_with_evidence(
        gateway.task,
        events,
        None,
        policy_version="phase-evidence-v5",
        artifact_store=gateway.artifacts,
        budget=Budget(
            max_model_calls=21,
            max_tool_calls=50,
            max_total_tokens=211_000,
        ),
        max_output_tokens=25_000,
    )
    payload = json.loads(built.rendered)
    tail = payload["investigation_ledger"]["tail_policy"]
    projection = tail["token_projection"]

    assert projection["max_observed_input_tokens"] == 24_000
    assert projection["max_positive_consecutive_growth"] == 4_000
    assert projection["projected_next_input_tokens"] == 28_000
    assert projection["projected_model_turns"] == 5
    assert projection["reserved_tokens"] == 165_000
    assert tail["remaining_budget"]["tokens"] == 165_000
    assert tail["block_reasons"] == ["token_tail_reserved"]
    assert tail["exploration_admitted"] is False
    assert built.evidence["investigation_ledger"]["tail_reserved_tokens"] == 165_000

    open_built = build_context_with_evidence(
        gateway.task,
        events,
        None,
        policy_version="phase-evidence-v5",
        artifact_store=gateway.artifacts,
        budget=Budget(
            max_model_calls=21,
            max_tool_calls=50,
            max_total_tokens=211_001,
        ),
        max_output_tokens=25_000,
    )
    open_tail = json.loads(open_built.rendered)[
        "investigation_ledger"
    ]["tail_policy"]
    assert open_tail["remaining_budget"]["tokens"] == 165_001
    assert open_tail["block_reasons"] == []
    assert open_tail["exploration_admitted"] is True


def test_v5_context_uses_input_fallback_only_when_requested_is_none(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v5_token_fallback",
        manifest_context_policy_version="phase-evidence-v5",
    )
    no_observation = build_context_with_evidence(
        gateway.task,
        [],
        None,
        policy_version="phase-evidence-v5",
        artifact_store=gateway.artifacts,
        budget=Budget(max_total_tokens=1),
        max_output_tokens=25_000,
    )
    no_observation_tail = json.loads(no_observation.rendered)[
        "investigation_ledger"
    ]["tail_policy"]
    assert no_observation_tail["block_reasons"] == []
    assert no_observation_tail["exploration_admitted"] is True

    gateway.state.append_event(
        gateway.run_id,
        EventType.MODEL_CALLED,
        actor="test-model",
        payload={
            "requested_input_tokens": None,
            "input_tokens": 10_000,
            "output_tokens": 1_000,
        },
    )
    events = gateway.state.list_events(gateway.run_id)
    built = build_context_with_evidence(
        gateway.task,
        events,
        None,
        policy_version="phase-evidence-v5",
        artifact_store=gateway.artifacts,
        budget=Budget(max_total_tokens=250_000),
        max_output_tokens=25_000,
    )
    projection = json.loads(built.rendered)["investigation_ledger"]["tail_policy"][
        "token_projection"
    ]

    assert projection["observations"] == [
        {
            "event_sequence": events[-1].sequence,
            "input_tokens": 10_000,
            "source": "input_tokens_fallback",
        }
    ]

    events[-1].payload["requested_input_tokens"] = "invalid"
    with pytest.raises(
        RecoveryError,
        match="invalid requested input tokens",
    ):
        build_context_with_evidence(
            gateway.task,
            events,
            None,
            policy_version="phase-evidence-v5",
            artifact_store=gateway.artifacts,
            budget=Budget(max_total_tokens=250_000),
            max_output_tokens=25_000,
        )


def test_v5_gateway_blocks_token_tail_at_post_generation_boundary(
    tmp_path,
) -> None:
    budget = Budget(
        max_model_calls=21,
        max_tool_calls=50,
        max_total_tokens=180_000,
    )
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v5_token_tail_admission",
        manifest_context_policy_version="phase-evidence-v5",
        budget=budget,
        max_output_tokens=25_000,
    )
    gateway.context_policy_version = "phase-evidence-v5"
    _durable_checkpoint(gateway)
    arguments = {"query": "parse_rows", "path_glob": "**/*.py"}
    gateway.execute(
        "search_files",
        "v5-token-tail-source",
        arguments,
    )
    replay = gateway.execute(
        "search_files",
        "v5-token-tail-replay",
        arguments,
    )
    assert replay.output["semantic_replay"] is True
    gateway.state.append_event(
        gateway.run_id,
        EventType.MODEL_CALLED,
        actor="test-model",
        payload={
            "requested_input_tokens": 30_000,
            "input_tokens": 30_000,
            "output_tokens": 5_000,
        },
    )

    result = gateway.execute(
        "search_files",
        "v5-token-tail-block",
        arguments,
    )

    assert result.status == "rejected"
    assert result.error_code == "TOOL_ADMISSION_BLOCKED"
    events = gateway.state.list_events(gateway.run_id)
    blocked = next(event for event in events if event.type == EventType.TOOL_ADMISSION_BLOCKED)
    tail = blocked.payload["tail_policy"]
    assert blocked.payload["schema_version"] == ("tool-admission-blocked-v2")
    assert blocked.payload["reason_codes"] == ["token_tail_reserved"]
    assert tail["projection_stage"] == "post_generation"
    assert tail["token_projection"]["projected_model_turns"] == 4
    assert tail["token_projection"]["reserved_tokens"] == 145_000
    assert blocked.payload["remaining_tokens"] == 145_000
    assert not any(
        event.type == EventType.TOOL_CALLED and event.correlation_id == "v5-token-tail-block"
        for event in events
    )
    assert not any(
        event.type == EventType.TOOL_REPLAYED
        and event.correlation_id == "v5-token-tail-block"
        for event in events
    )

    manifest = gateway.state.get_manifest(gateway.run_id)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    passed, details = _v4_investigation_lifecycle_evidence(
        root=tmp_path,
        manifest=manifest,
        package=package,
        events=events,
    )
    assert passed is True
    assert details["verified_semantic_replay_count"] == 1
    assert details["verified_admission_block_count"] == 1

    blocked.payload["tail_policy"]["token_projection"]["reserved_tokens"] += 1
    passed, details = _v4_investigation_lifecycle_evidence(
        root=tmp_path,
        manifest=manifest,
        package=package,
        events=events,
    )
    assert passed is False
    assert details["failed_admission_block_sequences"] == [blocked.sequence]


def test_v5_tail_reason_order_is_stable_when_all_reserves_close(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v5_combined_tail",
        manifest_context_policy_version="phase-evidence-v5",
    )
    gateway.state.append_event(
        gateway.run_id,
        EventType.MODEL_CALLED,
        actor="test-model",
        payload={
            "requested_input_tokens": 30_000,
            "input_tokens": 30_000,
            "output_tokens": 5_000,
        },
    )
    built = build_context_with_evidence(
        gateway.task,
        gateway.state.list_events(gateway.run_id),
        None,
        policy_version="phase-evidence-v5",
        artifact_store=gateway.artifacts,
        budget=Budget(
            max_model_calls=6,
            max_tool_calls=1,
            max_total_tokens=180_000,
        ),
        max_output_tokens=25_000,
    )

    assert json.loads(built.rendered)["investigation_ledger"][
        "tail_policy"
    ]["block_reasons"] == [
        "tool_tail_reserved",
        "model_tail_reserved",
        "token_tail_reserved",
    ]


def test_v4_lifecycle_qualification_recomputes_replay_and_admission(
    tmp_path,
    monkeypatch,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_lifecycle_qualification",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    _durable_checkpoint(gateway)
    arguments = {"query": "parse_rows", "path_glob": "**/*.py"}
    gateway.execute("search_files", "lifecycle-source", arguments)
    gateway.execute("search_files", "lifecycle-replay", arguments)
    idempotent_replay = gateway.execute(
        "search_files",
        "lifecycle-replay",
        arguments,
    )
    assert idempotent_replay.output["replayed"] is True
    for index in range(16):
        gateway.state.append_event(
            gateway.run_id,
            EventType.MODEL_CALLED,
            actor="test-model",
            payload={"index": index},
        )
    gateway.execute(
        "search_files",
        "lifecycle-admission",
        {"query": "different", "path_glob": "**/*.py"},
    )
    manifest = gateway.state.get_manifest(gateway.run_id)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    events = gateway.state.list_events(gateway.run_id)

    passed, details = _v4_investigation_lifecycle_evidence(
        root=tmp_path,
        manifest=manifest,
        package=package,
        events=events,
    )

    assert passed is True
    assert details["verified_semantic_replay_count"] == 1
    assert details["verified_admission_block_count"] == 1
    (
        nested_integrity,
        nested_count,
        nested_leaks,
        nested_evidence,
        nested_missing,
    ) = _v4_admission_nested_artifact_evidence(
        root=tmp_path,
        events=events,
        private_tokens={"different"},
    )
    assert nested_integrity is True
    assert nested_count == 2
    assert nested_leaks == 2
    assert {
        item["role"] for item in nested_evidence
    } == {
        "investigation-admission-input",
        "investigation-admission-preflight",
    }
    assert nested_missing == []

    loop = next(
        event
        for event in events
        if event.type == EventType.LOOP_DETECTED
    )
    tampered_loop = loop.model_copy(
        update={
            "payload": {
                **loop.payload,
                "no_progress_streak": 99,
            }
        }
    )
    tampered_events = [
        tampered_loop if event.sequence == loop.sequence else event
        for event in events
    ]
    passed, details = _v4_investigation_lifecycle_evidence(
        root=tmp_path,
        manifest=manifest,
        package=package,
        events=tampered_events,
    )
    assert passed is False
    assert details["failed_semantic_replay_sequences"]

    replay = next(
        event
        for event in events
        if event.type == EventType.TOOL_REPLAYED
        and event.payload.get("semantic_replay") is True
    )
    stripped_payload = dict(replay.payload)
    stripped_payload.pop("schema_version")
    stripped_payload.pop("semantic_replay")
    stripped_replay = replay.model_copy(
        update={"payload": stripped_payload}
    )
    stripped_events = [
        stripped_replay
        if event.sequence == replay.sequence
        else event
        for event in events
    ]
    passed, details = _v4_investigation_lifecycle_evidence(
        root=tmp_path,
        manifest=manifest,
        package=package,
        events=stripped_events,
    )
    assert passed is False
    assert replay.sequence in details[
        "failed_semantic_replay_sequences"
    ]

    def reject_admission_request(*_args, **_kwargs) -> None:
        raise ContractError("synthetic admission validation failure")

    monkeypatch.setattr(
        "patchloop.agent.investigation.validate_inspection_arguments",
        reject_admission_request,
    )
    passed, details = _v4_investigation_lifecycle_evidence(
        root=tmp_path,
        manifest=manifest,
        package=package,
        events=events,
    )
    assert passed is False
    assert details["failed_admission_block_sequences"]


def test_v4_read_admission_uses_frozen_preflight_after_target_deletion(
    tmp_path,
) -> None:
    _, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_read_admission_preflight",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    _durable_checkpoint(gateway)
    for index in range(16):
        gateway.state.append_event(
            gateway.run_id,
            EventType.MODEL_CALLED,
            actor="test-model",
            payload={"index": index},
        )
    result = gateway.execute(
        "read_file",
        "read-admission-preflight",
        {
            "path": "mini_data_utils/csvlite.py",
            "start_line": 1,
            "end_line": 2,
        },
    )
    assert result.error_code == "TOOL_ADMISSION_BLOCKED"
    manifest = gateway.state.get_manifest(gateway.run_id)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    events = gateway.state.list_events(gateway.run_id)

    (workspace / "mini_data_utils" / "csvlite.py").unlink()
    passed, details = _v4_investigation_lifecycle_evidence(
        root=tmp_path,
        manifest=manifest,
        package=package,
        events=events,
    )
    assert passed is True
    assert details["verified_admission_block_count"] == 1

    admission = next(
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
    )
    preflight = json.loads(
        gateway.artifacts.read_bytes(
            Artifact.model_validate(
                admission.payload["preflight_artifact"]
            )
        ).decode("utf-8")
    )
    target = Artifact.model_validate(preflight["target_artifact"])
    Path(target.path).write_bytes(b"tampered target snapshot")
    passed, details = _v4_investigation_lifecycle_evidence(
        root=tmp_path,
        manifest=manifest,
        package=package,
        events=events,
    )
    assert passed is False
    assert details["failed_admission_block_sequences"]


def test_v4_context_retains_evicted_investigation_evidence(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_context_ledger",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    gateway.execute(
        "read_file",
        "ledger-source-read",
        {
            "path": "mini_data_utils/csvlite.py",
            "start_line": 1,
            "end_line": 4,
        },
    )
    for index in range(20):
        gateway.state.append_event(
            gateway.run_id,
            EventType.CHECKPOINT_SAVED,
            actor="test",
            payload={"index": index},
        )
    events = gateway.state.list_events(gateway.run_id)

    first = build_context_with_evidence(
        gateway.task,
        events,
        None,
        policy_version="phase-evidence-v4",
        artifact_store=gateway.artifacts,
    )
    reopened = build_context_with_evidence(
        gateway.task,
        StateStore(gateway.state.path).list_events(gateway.run_id),
        None,
        policy_version="phase-evidence-v4",
        artifact_store=ArtifactStore(gateway.artifacts.root),
    )

    assert first.rendered == reopened.rendered
    assert first.content_hash == reopened.content_hash
    assert first.evidence["events"]["omitted_count"] > 0
    assert (
        first.evidence["investigation_ledger"]["read_file_count"]
        == 1
    )
    payload = json.loads(first.rendered)
    assert payload["investigation_ledger"]["reads"][0]["path"] == (
        "mini_data_utils/csvlite.py"
    )
    assert payload["investigation_ledger"]["reads"][0][
        "covered_ranges"
    ] == [[1, 4]]


def test_v4_context_rehydrates_semantic_replay_result(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_context_replay",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    arguments = {"query": "parse_rows", "path_glob": "**/*.py"}
    gateway.execute("search_files", "context-search-first", arguments)
    gateway.execute("search_files", "context-search-replay", arguments)

    context, _ = build_context(
        gateway.task,
        gateway.state.list_events(gateway.run_id),
        None,
        policy_version="phase-evidence-v4",
        artifact_store=gateway.artifacts,
    )

    payload = json.loads(context)
    replay_event = next(
        event
        for event in payload["recent_events"]
        if event["type"] == EventType.TOOL_REPLAYED.value
    )
    assert replay_event["payload"]["tool_result"][
        "semantic_replay"
    ] is True
    assert replay_event["payload"]["tool_result"]["matches"]


def test_v4_same_action_idempotency_replay_keeps_context_readable(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_idempotent_context",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    arguments = {"query": "parse_rows", "path_glob": "**/*.py"}

    first = gateway.execute(
        "search_files",
        "same-search-action",
        arguments,
    )
    replayed = gateway.execute(
        "search_files",
        "same-search-action",
        arguments,
    )

    assert replayed.output["replayed"] is True
    assert replayed.output["matches"] == first.output["matches"]
    event = gateway.state.list_events(gateway.run_id)[-1]
    assert event.type == EventType.TOOL_REPLAYED
    assert event.actor == "idempotency-store"
    assert event.payload["result_artifact"] == first.output[
        "result_artifact"
    ]

    reopened_state = StateStore(gateway.state.path)
    reopened_artifacts = ArtifactStore(gateway.artifacts.root)
    context, _ = build_context(
        gateway.task,
        reopened_state.list_events(gateway.run_id),
        None,
        policy_version="phase-evidence-v4",
        artifact_store=reopened_artifacts,
    )
    payload = json.loads(context)
    replay_event = next(
        item
        for item in payload["recent_events"]
        if item["sequence"] == event.sequence
    )
    assert replay_event["payload"]["tool_result"]["matches"]


def test_v4_semantic_result_idempotency_and_regular_tool_replay(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_mixed_idempotency",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    arguments = {"query": "parse_rows", "path_glob": "**/*.py"}
    gateway.execute("search_files", "source-search", arguments)
    semantic = gateway.execute(
        "search_files",
        "semantic-action",
        arguments,
    )
    repeated_semantic = gateway.execute(
        "search_files",
        "semantic-action",
        arguments,
    )
    check_id = gateway.task.visible_checks[0].id
    gateway.execute(
        "run_check",
        "regular-action",
        {"check_id": check_id},
    )
    repeated_check = gateway.execute(
        "run_check",
        "regular-action",
        {"check_id": check_id},
    )

    assert semantic.output["semantic_replay"] is True
    assert repeated_semantic.output["replayed"] is True
    assert repeated_semantic.output["semantic_replay"] is True
    assert repeated_check.output["replayed"] is True
    context, _ = build_context(
        gateway.task,
        gateway.state.list_events(gateway.run_id),
        None,
        policy_version="phase-evidence-v4",
        artifact_store=gateway.artifacts,
    )
    assert json.loads(context)["investigation_ledger"][
        "no_progress"
    ]["total_semantic_replays"] == 1


def test_v4_second_semantic_replay_requires_strategy_change(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_strategy_change",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    arguments = {"query": "parse_rows", "path_glob": "**/*.py"}
    gateway.execute("search_files", "strategy-search", arguments)
    gateway.execute("search_files", "strategy-replay-one", arguments)
    gateway.execute("search_files", "strategy-replay-two", arguments)

    built = build_context_with_evidence(
        gateway.task,
        gateway.state.list_events(gateway.run_id),
        None,
        policy_version="phase-evidence-v4",
        artifact_store=gateway.artifacts,
    )

    ledger = json.loads(built.rendered)["investigation_ledger"]
    assert ledger["no_progress"]["streak"] == 2
    assert ledger["no_progress"]["strategy_change_required"] is True
    loops = [
        event
        for event in gateway.state.list_events(gateway.run_id)
        if event.type == EventType.LOOP_DETECTED
    ]
    assert [event.payload["no_progress_streak"] for event in loops] == [
        1,
        2,
    ]


def test_v4_context_fails_closed_on_tampered_result_cas(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_context_tamper",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    result = gateway.execute(
        "search_files",
        "tampered-search",
        {"query": "parse_rows", "path_glob": "**/*.py"},
    )
    Path(result.output["artifact_path"]).write_text(
        '{"tampered": true}',
        encoding="utf-8",
    )

    with pytest.raises(RecoveryError, match="integrity"):
        build_context(
            gateway.task,
            gateway.state.list_events(gateway.run_id),
            None,
            policy_version="phase-evidence-v4",
            artifact_store=gateway.artifacts,
        )


def test_v4_qualification_recomputes_context_ledger(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_v4_qualification",
    )
    gateway.context_policy_version = "phase-evidence-v4"
    gateway.execute(
        "search_files",
        "qualified-search",
        {"query": "parse_rows", "path_glob": "**/*.py"},
    )
    source_events = gateway.state.list_events(gateway.run_id)
    built = build_context_with_evidence(
        gateway.task,
        source_events,
        None,
        policy_version="phase-evidence-v4",
        artifact_store=gateway.artifacts,
    )
    request_body = {"context": built.rendered}
    request_body_hash = sha256_text(canonical_json(request_body))
    request_artifact = gateway.artifacts.put_json(
        {
            "schema_version": "model-request-evidence-v1",
            "provider": "mock",
            "endpoint": None,
            "request_body": request_body,
            "request_body_hash": request_body_hash,
            "context_build": built.evidence,
        }
    )
    ledger_evidence = built.evidence["investigation_ledger"]
    context_event = gateway.state.append_event(
        gateway.run_id,
        EventType.CONTEXT_BUILT,
        actor="context-builder",
        payload={
            "context_hash": built.content_hash,
            "request_body_hash": request_body_hash,
            "artifact_id": request_artifact.artifact_id,
            "artifact_path": request_artifact.path,
            "investigation_ledger_hash": ledger_evidence[
                "content_hash"
            ],
            "investigation_source_through_sequence": (
                ledger_evidence["source_through_sequence"]
            ),
            "investigation_no_progress_streak": ledger_evidence[
                "no_progress_streak"
            ],
            "investigation_exploration_admitted": ledger_evidence[
                "exploration_admitted"
            ],
        },
    )
    package = load_task_package("tasks/smoke/csv-quoted-newline")

    passed, details = _v4_investigation_context_evidence(
        root=tmp_path,
        manifest=gateway.state.get_manifest(gateway.run_id),
        package=package,
        events=gateway.state.list_events(gateway.run_id),
        checkpoints=[],
        context_events=[context_event],
    )
    assert passed is True
    assert details["verified_context_count"] == 1

    tampered = context_event.model_copy(
        update={
            "payload": {
                **context_event.payload,
                "investigation_ledger_hash": "sha256:" + ("0" * 64),
            }
        }
    )
    passed, details = _v4_investigation_context_evidence(
        root=tmp_path,
        manifest=gateway.state.get_manifest(gateway.run_id),
        package=package,
        events=gateway.state.list_events(gateway.run_id),
        checkpoints=[],
        context_events=[tampered],
    )
    assert passed is False
    assert details["failed_context_sequences"] == [
        context_event.sequence
    ]


def test_live_request_evidence_uses_responses_input_not_mock_context(
    tmp_path,
) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_live_request_context",
    )
    actual_context = '{"actual_provider_context": true}'
    request_body = {
        "context": '{"mock_sidecar": true}',
        "input": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": actual_context},
        ],
    }
    request_body_hash = sha256_text(canonical_json(request_body))
    artifact = gateway.artifacts.put_json(
        {
            "schema_version": "model-request-evidence-v1",
            "provider": "openai",
            "endpoint": "/v1/responses",
            "request_body": request_body,
            "request_body_hash": request_body_hash,
            "context_build": {},
        }
    )
    event = gateway.state.append_event(
        gateway.run_id,
        EventType.CONTEXT_BUILT,
        actor="context-builder",
        payload={
            "context_hash": sha256_text(actual_context),
            "request_body_hash": request_body_hash,
            "artifact_id": artifact.artifact_id,
            "artifact_path": artifact.path,
        },
    )

    valid, _ = _request_evidence_payload(
        event,
        artifact_root=gateway.artifacts.root,
        expected_provider="openai",
    )
    wrong_provider, _ = _request_evidence_payload(
        event,
        artifact_root=gateway.artifacts.root,
        expected_provider="mock",
    )

    assert valid is True
    assert wrong_provider is False


@pytest.mark.parametrize(
    ("patch", "expected_error"),
    [
        (
            "diff --git a/mini_data_utils/csvlite.py b/mini_data_utils/csvlite.py\n"
            "old mode 100644\n"
            "new mode 100755\n",
            "mode/symlink changes",
        ),
        (
            "diff --git a/mini_data_utils/blob.bin b/mini_data_utils/blob.bin\n"
            "new file mode 100644\n"
            "index 0000000..1234567\n"
            "GIT binary patch\n"
            "literal 1\n"
            "AcmZQz\n",
            "binary patches",
        ),
    ],
)
def test_apply_patch_rejects_binary_and_metadata_only_changes(
    tmp_path,
    patch,
    expected_error,
) -> None:
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(package, run_id="run_gateway_patch_policy")
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    workspace = manager.create(
        manifest.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    gateway = ToolGateway(
        run_id=manifest.run_id,
        workspace=workspace,
        task=package.public,
        state=state,
        artifacts=ArtifactStore(tmp_path / "artifacts"),
        sandbox=LocalSandbox(),
    )

    result = gateway.execute(
        "apply_patch",
        f"reject-{expected_error}",
        {"patch": patch},
    )

    assert result.status == "rejected"
    assert expected_error in (result.error_message or "")
    assert manager.diff_summary(workspace).changed_files == []


@pytest.mark.parametrize(
    "patch",
    [
        (
            "diff --git a/mini_data_utils/new_module.py "
            "b/mini_data_utils/new_module.py\n"
            "new file mode 100644\n"
            "index 0000000..f11d8a9\n"
            "--- /dev/null\n"
            "+++ b/mini_data_utils/new_module.py\n"
            "@@ -0,0 +1 @@\n"
            "+VALUE = 1\n"
        ),
        (
            "diff --git a/mini_data_utils/csvlite.py "
            "b/mini_data_utils/renamed.py\n"
            "--- a/mini_data_utils/csvlite.py\n"
            "+++ b/mini_data_utils/renamed.py\n"
            "@@ -1 +1 @@\n"
            "-import csv\n"
            "+import csv\n"
        ),
    ],
)
def test_apply_patch_rejects_untracked_or_path_changing_outputs(
    tmp_path,
    patch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_reject_untracked",
    )

    result = gateway.execute(
        "apply_patch",
        "reject-untracked-output",
        {"patch": patch},
    )

    assert result.status == "rejected"
    assert result.error_code == "CONTRACT_ERROR"
    assert not (workspace / "mini_data_utils" / "new_module.py").exists()
    assert not (workspace / "mini_data_utils" / "renamed.py").exists()
    assert manager.diff_summary(workspace).changed_files == []


def test_post_apply_untracked_file_is_rolled_back(
    tmp_path,
    monkeypatch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_post_apply_untracked",
        tool_schema_version="v1",
    )
    patch = (
        "diff --git a/mini_data_utils/new_module.py "
        "b/mini_data_utils/new_module.py\n"
        "new file mode 100644\n"
        "index 0000000..f11d8a9\n"
        "--- /dev/null\n"
        "+++ b/mini_data_utils/new_module.py\n"
        "@@ -0,0 +1 @@\n"
        "+VALUE = 1\n"
    )
    monkeypatch.setattr(
        "patchloop.agent.tools._validate_raw_git_patch",
        lambda _patch: None,
    )

    result = gateway.execute(
        "apply_patch",
        "rollback-post-apply-untracked",
        {"patch": patch},
    )

    assert result.status == "rejected"
    assert "produced untracked files" in (result.error_message or "")
    assert not (workspace / "mini_data_utils" / "new_module.py").exists()
    assert manager.diff_summary(workspace).changed_files == []
    assert manager.untracked_files(workspace) == []


def test_apply_patch_rejects_preexisting_untracked_target(tmp_path) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_preexisting_untracked",
    )
    target = workspace / "scratch.txt"
    target.write_text("before\n", encoding="utf-8")
    patch = (
        "diff --git a/scratch.txt b/scratch.txt\n"
        "--- a/scratch.txt\n"
        "+++ b/scratch.txt\n"
        "@@ -1 +1 @@\n"
        "-before\n"
        "+after\n"
    )

    result = gateway.execute(
        "apply_patch",
        "reject-preexisting-untracked",
        {"patch": patch},
    )

    assert result.status == "failed"
    assert result.error_code == RecoveryError.code
    assert result.output["fatal"] is True
    assert target.read_text(encoding="utf-8") == "before\n"
    assert manager.diff_summary(workspace).changed_files == []
    assert manager.untracked_files(workspace) == ["scratch.txt"]


def test_recount_does_not_relax_hunk_context(tmp_path) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recount_context",
    )
    patch = _r2_style_recount_patch()
    patch = patch.replace("import csv", "import missing_csv")

    result = gateway.execute(
        "apply_patch",
        "reject-invalid-context",
        {"patch": patch},
    )

    assert result.status == "rejected"
    assert "patch application failed" in (result.error_message or "")
    assert manager.diff_summary(workspace).changed_files == []
    assert manager.untracked_files(workspace) == []


def test_post_apply_verifier_error_rolls_back_before_propagating(
    tmp_path,
    monkeypatch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_verifier_error",
    )
    patch = _r2_style_recount_patch()

    def fail_verifier(*_args, **_kwargs):
        raise RuntimeError("synthetic verifier failure")

    monkeypatch.setattr("patchloop.agent.tools.verify_scope", fail_verifier)

    with pytest.raises(RuntimeError, match="synthetic verifier failure"):
        gateway.execute(
            "apply_patch",
            "rollback-verifier-error",
            {"patch": patch},
        )

    assert manager.diff_summary(workspace).changed_files == []
    assert manager.untracked_files(workspace) == []


def test_apply_patch_fails_closed_when_policy_rollback_fails(
    tmp_path,
    monkeypatch,
) -> None:
    _, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_failed_rollback",
    )
    patch = Path(
        "tasks/smoke/csv-quoted-newline/bad/forbidden-path.patch"
    ).read_text(encoding="utf-8")
    def fail_preimage_restore(_intent):
        raise RecoveryError("forced preimage restoration failure")

    monkeypatch.setattr(
        gateway,
        "_restore_patch_preimages",
        fail_preimage_restore,
    )

    result = gateway.execute(
        "apply_patch",
        "force-failed-rollback",
        {"patch": patch},
    )

    assert result.status == "failed"
    assert result.error_code == RecoveryError.code
    assert "forced preimage restoration failure" in (
        result.error_message or ""
    )
    assert result.output["fatal"] is True
    assert "intentionally outside the task scope" in (
        workspace / "README.md"
    ).read_text(encoding="utf-8")
