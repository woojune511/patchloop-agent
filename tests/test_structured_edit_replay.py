from __future__ import annotations

import inspect
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.structured_edit import (
    AtomicStructuredEditProjection,
    StructuredEditArguments,
    StructuredFileEdit,
    StructuredReplacement,
    project_atomic_structured_edit,
)
from patchloop.agent.structured_edit_replay import (
    StructuredEditDiffCheckReplay,
    StructuredEditGatewayPatch,
    project_structured_edit_diff_check_replay,
    render_structured_edit_gateway_patch,
)
from patchloop.agent.tools import TOOL_SCHEMAS, ToolGateway
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, EventType, TaskConstraints, ToolResult
from patchloop.repository import WorkspaceManager
from patchloop.runtime import build_manifest
from patchloop.sandbox import LocalSandbox
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]
EMPTY_DIFF_HASH = sha256_text("")
TARGET = "mini_data_utils/csvlite.py"


def _disable_git_conversion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    empty_git_config = tmp_path / "empty.gitconfig"
    empty_git_config.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty_git_config.resolve()))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def _gateway(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Any, WorkspaceManager, Path, ToolGateway]:
    _disable_git_conversion(tmp_path, monkeypatch)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_structured_diff_replay",
    ).model_copy(update={"context_policy_version": "phase-evidence-v5"})
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    workspace = manager.create(
        manifest.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    autocrlf = subprocess.run(
        ["git", "config", "--get", "core.autocrlf"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    assert autocrlf.returncode in {0, 1}
    assert autocrlf.stdout.strip().lower() in {"", "false"}
    gateway = ToolGateway(
        run_id=manifest.run_id,
        workspace=workspace,
        task=package.public,
        state=state,
        artifacts=ArtifactStore(tmp_path / "artifacts"),
        sandbox=LocalSandbox(),
        tool_schema_version="v2",
        context_policy_version="phase-evidence-v5",
    )
    return package, manager, workspace, gateway


def _structured(
    workspace: Path,
    constraints: TaskConstraints,
    *,
    expected: bytes = b"audited defect",
    replacement: str = "verified defect",
) -> AtomicStructuredEditProjection:
    raw = (workspace / TARGET).read_bytes()
    start = raw.index(expected)
    arguments = StructuredEditArguments(
        source_worktree_diff_hash=WorkspaceManager.diff_summary(workspace).patch_hash,
        files=(
            StructuredFileEdit(
                path=TARGET,
                preimage_file_sha256=sha256_bytes(raw),
                replacements=(
                    StructuredReplacement(
                        start_byte=start,
                        end_byte=start + len(expected),
                        expected_text=expected.decode("utf-8"),
                        replacement_text=replacement,
                    ),
                ),
            ),
        ),
    )
    return project_atomic_structured_edit(
        action_id="structured-edit-action",
        arguments=arguments,
        preimages={TARGET: raw},
        constraints=constraints,
    )


def _replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    StructuredEditDiffCheckReplay,
    AtomicStructuredEditProjection,
    StructuredEditGatewayPatch,
    ToolGateway,
]:
    package, manager, workspace, gateway = _gateway(tmp_path, monkeypatch)
    baseline = manager.diff_summary(workspace)
    baseline_untracked = tuple(manager.untracked_files(workspace))
    structured = _structured(workspace, package.public.constraints)
    gateway_patch = render_structured_edit_gateway_patch(structured)
    apply_result = gateway.execute(
        "apply_patch",
        "structured-compatibility-apply",
        {"patch": gateway_patch.patch},
    )
    checks = tuple(sorted(package.public.visible_checks, key=lambda item: item.id))
    check_results = tuple(
        gateway.execute(
            "run_check",
            f"structured-check-{check.id}",
            {"check_id": check.id},
        )
        for check in checks
    )
    diff_result = gateway.execute(
        "get_diff",
        "structured-final-diff",
        {},
    )
    replay = project_structured_edit_diff_check_replay(
        gateway_patch=gateway_patch,
        apply_result=apply_result,
        registered_checks=checks,
        check_results=check_results,
        diff_result=diff_result,
        observed_postimages={TARGET: (workspace / TARGET).read_bytes()},
        baseline_worktree_diff_hash=baseline.patch_hash,
        baseline_untracked_files=baseline_untracked,
        final_untracked_files=tuple(manager.untracked_files(workspace)),
        scratch_workspace_attested=True,
        git_core_autocrlf_disabled_attested=True,
        provider_network_docker_calls_attested_zero=True,
    )
    return replay, structured, gateway_patch, gateway


def _rehash(body: dict[str, Any]) -> dict[str, Any]:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def _synthetic_projection(
    *,
    path: str = "src/example.py",
    before: bytes = b"alpha",
    expected: str = "alpha",
    replacement: str = "beta",
) -> AtomicStructuredEditProjection:
    arguments = StructuredEditArguments(
        source_worktree_diff_hash=EMPTY_DIFF_HASH,
        files=(
            StructuredFileEdit(
                path=path,
                preimage_file_sha256=sha256_bytes(before),
                replacements=(
                    StructuredReplacement(
                        start_byte=0,
                        end_byte=len(expected.encode("utf-8")),
                        expected_text=expected,
                        replacement_text=replacement,
                    ),
                ),
            ),
        ),
    )
    return project_atomic_structured_edit(
        action_id="synthetic-structured-edit",
        arguments=arguments,
        preimages={path: before},
        constraints=TaskConstraints(
            allowed_paths=["src/**"],
            max_changed_files=2,
            max_diff_lines=20,
        ),
    )


def test_current_gateway_replays_exact_apply_check_and_diff_offline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay, structured, gateway_patch, gateway = _replay(tmp_path, monkeypatch)

    assert replay.baseline_worktree_diff_hash == EMPTY_DIFF_HASH
    assert replay.gateway_patch == gateway_patch
    assert replay.apply.patch_hash == gateway_patch.patch_hash
    assert replay.diff.worktree_diff_hash == replay.apply.worktree_diff_hash
    assert replay.diff.changed_files == (TARGET,)
    assert replay.check_count == 1
    assert replay.all_checks_passed is True
    assert replay.observed_postimages[0].file_sha256 == (structured.files[0].postimage_file_sha256)
    assert replay.production_workspace_writes_performed == 0
    assert replay.scratch_workspace_mutations_observed == 1
    assert gateway.tool_schema_version == replay.gateway_tool_schema_version
    assert gateway.context_policy_version == replay.gateway_context_policy_version
    assert replay.runtime_activation_authorized is False
    assert replay.provider_calls_authorized is False
    events = gateway.state.list_events(gateway.run_id)
    apply_call = next(
        event
        for event in events
        if event.type == EventType.TOOL_CALLED and event.correlation_id == replay.apply.action_id
    )
    assert apply_call.payload["input_hash"] == replay.legacy_gateway_input_hash
    assert structured.content_hash not in str(apply_call.payload)
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 1
    assert any(
        event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("worktree_diff_hash") == replay.diff.worktree_diff_hash
        for event in events
    )


def test_v7_gateway_projects_structured_edit_into_atomic_patch_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package, _, workspace, gateway = _gateway(tmp_path, monkeypatch)
    gateway.tool_schema_version = "v7"
    gateway.context_policy_version = "phase-evidence-v12"
    structured = _structured(workspace, package.public.constraints)

    result = gateway.execute(
        "apply_structured_edit",
        structured.action_id,
        structured.arguments.model_dump(mode="json"),
    )

    assert result.status == "succeeded", result.output
    assert (
        result.output["patch_hash"] == render_structured_edit_gateway_patch(structured).patch_hash
    )
    assert (workspace / TARGET).read_bytes() == structured.files[0].postimage_text.encode("utf-8")
    call = next(
        event
        for event in gateway.state.list_events(gateway.run_id)
        if event.type == EventType.TOOL_CALLED and event.correlation_id == structured.action_id
    )
    assert call.payload["tool"] == "apply_structured_edit"
    projection_artifact = Artifact.model_validate(
        call.payload["structured_edit_projection_artifact"]
    )
    assert (
        AtomicStructuredEditProjection.model_validate_json(
            gateway.artifacts.read_bytes(projection_artifact)
        )
        == structured
    )
    assert (
        sum(
            event.type == EventType.PATCH_APPLIED
            for event in gateway.state.list_events(gateway.run_id)
        )
        == 1
    )


def test_renderer_is_deterministic_and_handles_missing_final_newline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_git_conversion(tmp_path, monkeypatch)
    structured = _synthetic_projection()
    first = render_structured_edit_gateway_patch(structured)
    second = render_structured_edit_gateway_patch(structured)

    assert first == second
    assert first.patch.startswith("diff --git a/src/example.py b/src/example.py\n")
    assert first.patch.count("\\ No newline at end of file\n") == 2
    assert first.patch_hash == sha256_text(first.patch)
    assert first.model_authored_raw_diff_required is False
    assert first.task_workspace_writes_performed == 0
    workspace = tmp_path / "patch-check"
    target = workspace / "src/example.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"alpha")
    subprocess.run(["git", "init", "--quiet"], cwd=workspace, check=True)
    checked = subprocess.run(
        ["git", "apply", "--check", "--recount", "-"],
        cwd=workspace,
        input=first.patch.encode(),
        capture_output=True,
        check=False,
    )
    assert checked.returncode == 0, checked.stderr.decode(errors="replace")


def test_renderer_orders_multiple_files_and_preserves_utf8_crlf() -> None:
    files = {
        "src/z.py": "name = '한글'\r\n".encode(),
        "src/a.py": b"value = 1\r\n",
    }
    arguments = StructuredEditArguments(
        source_worktree_diff_hash=EMPTY_DIFF_HASH,
        files=tuple(
            StructuredFileEdit(
                path=path,
                preimage_file_sha256=sha256_bytes(raw),
                replacements=(
                    StructuredReplacement(
                        start_byte=raw.index(b"1")
                        if path.endswith("a.py")
                        else raw.index("한글".encode()),
                        end_byte=(raw.index(b"1") + 1)
                        if path.endswith("a.py")
                        else (raw.index("한글".encode()) + len("한글".encode())),
                        expected_text="1" if path.endswith("a.py") else "한글",
                        replacement_text="2" if path.endswith("a.py") else "문자",
                    ),
                ),
            )
            for path, raw in files.items()
        ),
    )
    structured = project_atomic_structured_edit(
        action_id="multi-render",
        arguments=arguments,
        preimages=files,
        constraints=TaskConstraints(
            allowed_paths=["src/**"],
            max_changed_files=2,
            max_diff_lines=20,
        ),
    )
    rendered = render_structured_edit_gateway_patch(structured)

    assert rendered.changed_files == ("src/a.py", "src/z.py")
    assert rendered.patch.index("a/src/a.py") < rendered.patch.index("a/src/z.py")
    assert "한글" in rendered.patch
    assert "문자" in rendered.patch
    assert "\r\n" in rendered.patch


def test_renderer_rejects_paths_that_need_unqualified_git_quoting() -> None:
    structured = _synthetic_projection(path="src/space name.py")

    with pytest.raises(ValueError, match="unquoted Git-safe path"):
        render_structured_edit_gateway_patch(structured)


def test_rehashed_mechanical_patch_drift_is_rejected() -> None:
    rendered = render_structured_edit_gateway_patch(_synthetic_projection())
    body = rendered.model_dump(mode="python")
    body["patch"] = body["patch"].replace("+beta", "+gamma")
    body["patch_hash"] = sha256_text(body["patch"])
    body["patch_bytes"] = len(body["patch"].encode())
    body = _rehash(body)

    with pytest.raises(ValidationError, match="differs from structured images"):
        StructuredEditGatewayPatch.model_validate(body)


def test_replay_rejects_baseline_or_untracked_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay, _, _, _ = _replay(tmp_path, monkeypatch)
    body = replay.model_dump(mode="python")
    body["baseline_worktree_diff_hash"] = "sha256:" + "1" * 64
    body = _rehash(body)
    with pytest.raises(ValidationError, match="baseline differs"):
        StructuredEditDiffCheckReplay.model_validate(body)

    body = replay.model_dump(mode="python")
    body["final_untracked_files"] = ("scratch.txt",)
    body = _rehash(body)
    with pytest.raises(ValidationError, match="no untracked files"):
        StructuredEditDiffCheckReplay.model_validate(body)


def test_replay_rejects_observed_postimage_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay, _, _, _ = _replay(tmp_path, monkeypatch)
    body = replay.model_dump(mode="python")
    observed = body["observed_postimages"][0]
    observed["file_text"] = observed["file_text"].replace("verified", "drifted")
    raw = observed["file_text"].encode()
    observed["file_sha256"] = sha256_bytes(raw)
    observed["file_bytes"] = len(raw)
    observations = list(body["observed_postimages"])
    observations[0] = _rehash(observed)
    body["observed_postimages"] = tuple(observations)
    body = _rehash(body)

    with pytest.raises(ValidationError, match="postimages differ"):
        StructuredEditDiffCheckReplay.model_validate(body)

    authority = replay.model_dump(mode="python")
    authority["runtime_activation_authorized"] = True
    authority = _rehash(authority)
    with pytest.raises(ValidationError):
        StructuredEditDiffCheckReplay.model_validate(authority)


def test_replay_rejects_check_contract_and_diff_hash_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay, _, _, _ = _replay(tmp_path, monkeypatch)
    body = replay.model_dump(mode="python")
    check = body["checks"][0]
    check["check"]["expected_exit_codes"] = [1]
    check["check_contract_hash"] = sha256_json(check["check"])
    checks = list(body["checks"])
    checks[0] = _rehash(check)
    body["checks"] = tuple(checks)
    body = _rehash(body)
    with pytest.raises(ValidationError, match="pass state differs"):
        StructuredEditDiffCheckReplay.model_validate(body)

    body = replay.model_dump(mode="python")
    body["apply"]["worktree_diff_hash"] = "sha256:" + "2" * 64
    body["apply"] = _rehash(body["apply"])
    body = _rehash(body)
    with pytest.raises(ValidationError, match="worktree identities differ"):
        StructuredEditDiffCheckReplay.model_validate(body)


def test_replay_rejects_rehashed_git_blob_identity_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay, _, _, _ = _replay(tmp_path, monkeypatch)
    body = replay.model_dump(mode="python")
    diff = body["diff"]
    diff["patch"] = re_sub_first_index_hash(diff["patch"])
    drifted_hash = sha256_text(diff["patch"])
    diff["patch_hash"] = drifted_hash
    diff["worktree_diff_hash"] = drifted_hash
    body["diff"] = _rehash(diff)
    body["apply"]["worktree_diff_hash"] = drifted_hash
    body["apply"] = _rehash(body["apply"])
    checks = list(body["checks"])
    for index, check in enumerate(checks):
        check["worktree_diff_hash"] = drifted_hash
        checks[index] = _rehash(check)
    body["checks"] = tuple(checks)
    body = _rehash(body)

    with pytest.raises(ValidationError, match="Git blob identity differs"):
        StructuredEditDiffCheckReplay.model_validate(body)


def re_sub_first_index_hash(patch: str) -> str:
    lines = patch.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("index "):
            old, new_and_mode = line.removeprefix("index ").split("..", 1)
            lines[index] = "index " + ("0" * len(old)) + ".." + new_and_mode
            return "".join(lines)
    raise AssertionError("test fixture diff lacks an index line")


def test_projection_requires_exact_types_and_attestations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay, _, gateway_patch, _ = _replay(tmp_path, monkeypatch)
    arguments = {
        "gateway_patch": gateway_patch,
        "apply_result": ToolResult.model_validate(
            {
                "action_id": replay.apply.action_id,
                "status": "succeeded",
                "started_at": "2026-08-16T00:00:00Z",
                "finished_at": "2026-08-16T00:00:01Z",
                "output": {
                    "patch_hash": replay.apply.patch_hash,
                    "worktree_diff_hash": replay.apply.worktree_diff_hash,
                    "changed_files": list(replay.apply.changed_files),
                    "diff_lines": replay.apply.diff_lines,
                },
            }
        ),
        "registered_checks": tuple(item.check for item in replay.checks),
        "check_results": (),
        "diff_result": ToolResult.model_validate(
            {
                "action_id": replay.diff.action_id,
                "status": "succeeded",
                "started_at": "2026-08-16T00:00:00Z",
                "finished_at": "2026-08-16T00:00:01Z",
                "output": {},
            }
        ),
        "observed_postimages": {},
        "baseline_worktree_diff_hash": EMPTY_DIFF_HASH,
        "baseline_untracked_files": (),
        "final_untracked_files": (),
        "scratch_workspace_attested": True,
        "git_core_autocrlf_disabled_attested": True,
        "provider_network_docker_calls_attested_zero": True,
    }
    with pytest.raises(ValueError, match="one exact result"):
        project_structured_edit_diff_check_replay(**arguments)

    arguments["check_results"] = tuple(
        ToolResult.model_validate(
            {
                "action_id": item.action_id,
                "status": "succeeded",
                "started_at": "2026-08-16T00:00:00Z",
                "finished_at": "2026-08-16T00:00:01Z",
                "output": {},
            }
        )
        for item in replay.checks
    )
    arguments["scratch_workspace_attested"] = False
    with pytest.raises(ValueError, match="scratch-workspace attestation"):
        project_structured_edit_diff_check_replay(**arguments)


def test_replay_renderer_is_only_active_through_the_v7_gateway() -> None:
    runner_source = (REPOSITORY / "patchloop/agent/runner.py").read_text(encoding="utf-8")
    tools_source = (REPOSITORY / "patchloop/agent/tools.py").read_text(encoding="utf-8")
    renderer_source = inspect.getsource(render_structured_edit_gateway_patch)
    projector_source = inspect.getsource(project_structured_edit_diff_check_replay)

    assert "apply_structured_edit" not in {item["name"] for item in TOOL_SCHEMAS}
    assert "patchloop.agent.structured_edit_replay" not in runner_source
    assert "render_structured_edit_gateway_patch" in tools_source
    assert "project_structured_edit_diff_check_replay" not in tools_source
    assert "subprocess" not in renderer_source
    assert "ToolGateway" not in projector_source
    assert ".execute(" not in projector_source
