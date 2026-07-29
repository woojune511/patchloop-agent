from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

import pytest

from patchloop.agent.context import build_context
from patchloop.agent.tools import TOOL_SCHEMAS, ToolGateway
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, Checkpoint, EventType, FaultSpec, Phase
from patchloop.errors import ActionConflict, RecoveryError
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
):
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id=run_id,
        fault=fault,
    )
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
