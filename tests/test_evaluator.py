from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

import patchloop.dev.runner as runner
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ModelConfig, RunManifest, SafetyControl, VerdictState
from patchloop.dev.contracts import dev_tool_surface_hash
from patchloop.errors import ContractError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.sandbox import LocalSandbox, SandboxResult
from patchloop.sandbox.runner import registered_check_execution_policy
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now
from patchloop.verifier import EvaluationEngine


class PolicySandbox:
    backend = "docker"
    official = False

    def __init__(self, image: str, mode: str = "pass") -> None:
        self.image = image
        self.mode = mode
        self.calls = 0
        self.local = LocalSandbox()

    def run_check(self, workspace: Path, check) -> SandboxResult:
        self.calls += 1
        if self.mode == "error_after_one" and self.calls > 1:
            raise RuntimeError("simulated evaluator interruption")
        result = self.local.run_check(workspace, check)
        working_directory = "/workspace"
        if check.working_directory != ".":
            working_directory += f"/{check.working_directory}"
        policy = registered_check_execution_policy(
            image=self.image,
            working_directory=working_directory,
            timeout_seconds=check.timeout_seconds,
            output_limit_bytes=check.output_limit_bytes,
        )
        if self.mode == "violation":
            policy["requested_network"] = "host"
        elif self.mode == "missing":
            policy = None
        return replace(result, execution_policy=policy)


def _copy_smoke_task(tmp_path: Path, *, with_environment: bool) -> tuple[Path, object]:
    source = repository_root() / "tasks" / "smoke" / "csv-quoted-newline"
    task_dir = tmp_path / "task"
    shutil.copytree(source, task_dir)
    if with_environment:
        digest = "sha256:" + "a" * 64
        (task_dir / "environment.yaml").write_text(
            "schema_version: task-environment-v1\n"
            f"evaluator_image: patchloop/test@{digest}\n"
            f"image_digest: {digest}\n",
            encoding="utf-8",
        )
    return task_dir, load_task_package(task_dir)


def _manifest_for(
    package,
    patch_bytes: bytes,
    *,
    backend: str,
    image: str | None,
    run_id: str = "run_dev_evaluator0001",
) -> RunManifest:
    digest = image.rsplit("@", 1)[1] if image is not None else None
    patch_hash = sha256_bytes(patch_bytes)
    return RunManifest(
        run_id=run_id,
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        base_commit=package.public.repository.base_commit,
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
        task_content_hash=package.task_content_hash,
        runtime_content_hash=runtime_content_hash(),
        model_hash=sha256_json({"provider": "mock", "model": "mock-dev"}),
        tool_surface_hash=dev_tool_surface_hash(),
        sandbox_identity_hash=sha256_json(
            {
                "backend": backend,
                "evaluator_image": image,
                "image_digest": digest,
            }
        ),
        submitted_patch_content_hash=patch_hash,
        visible_check_diff_hash=patch_hash,
        submitted_changed_files=WorkspaceManager.patch_changed_files(patch_bytes),
        harness_git_commit=git_commit(),
        model=ModelConfig(provider="mock", model_id="mock-dev"),
        sandbox_backend=backend,
        evaluator_image_digest=digest,
        created_at=utc_now(),
    )


def _submitted_patch_bytes(tmp_path: Path, task_dir: Path, package) -> bytes:
    manager = WorkspaceManager(
        repository_root() / "fixtures" / "repositories",
        tmp_path / "submission-workspace",
    )
    workspace = manager.create(
        "submission",
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    manager.apply_patch(workspace, task_dir / package.private.reference_patch.path)
    return manager.diff_summary(workspace).patch.encode("utf-8")


def _write_manifest(store: ArtifactStore, manifest: RunManifest) -> None:
    text = canonical_json(manifest.model_dump(mode="json")) + "\n"
    store.write_text_immutable(store.root / "runs" / manifest.run_id / "manifest.json", text)


def _engine(tmp_path: Path, sandbox) -> tuple[EvaluationEngine, ArtifactStore, Path]:
    store = ArtifactStore(tmp_path / "artifacts")
    workspace_root = tmp_path / "workspaces"
    manager = WorkspaceManager(repository_root() / "fixtures" / "repositories", workspace_root)
    return EvaluationEngine(manager, sandbox, store), store, workspace_root


def test_mock_task_acceptance_passes_while_safety_is_not_run(tmp_path) -> None:
    task_dir, package = _copy_smoke_task(tmp_path, with_environment=False)
    patch_bytes = _submitted_patch_bytes(tmp_path, task_dir, package)
    engine, store, _ = _engine(tmp_path, LocalSandbox())
    artifact = store.put_bytes(patch_bytes, "text/x-diff")
    manifest = _manifest_for(package, patch_bytes, backend="local", image=None)
    _write_manifest(store, manifest)

    result = engine.evaluate(
        task_dir,
        artifact.path,
        manifest,
        submitted_patch_artifact=artifact,
    )
    assert result.scope_compliant_success is True
    assert result.verdicts.safety_policy == VerdictState.NOT_RUN
    controls = {item.control: item.state for item in result.safety_evidence}
    assert controls == {
        SafetyControl.RUNTIME_CONTRACT: VerdictState.PASS,
        SafetyControl.CONSTRAINED_TOOL_SURFACE: VerdictState.PASS,
        SafetyControl.MANAGED_WORKSPACE: VerdictState.PASS,
        SafetyControl.REQUESTED_SANDBOX_POLICY: VerdictState.NOT_RUN,
    }
    check_results = [
        item for item in result.verifier_results if item.check_type in {"hidden", "regression"}
    ]
    assert check_results
    assert all("execution_policy" in item.details for item in check_results)
    assert all(item.details["execution_policy"] is None for item in check_results)


@pytest.mark.parametrize("mismatch", ["task", "patch", "image", "task_content"])
def test_manifest_mismatch_fails_before_workspace_or_check(tmp_path, mismatch) -> None:
    task_dir, package = _copy_smoke_task(
        tmp_path,
        with_environment=mismatch == "image",
    )
    patch_bytes = _submitted_patch_bytes(tmp_path, task_dir, package)
    sandbox = (
        PolicySandbox(package.environment.evaluator_image)
        if mismatch == "image"
        else LocalSandbox()
    )
    engine, store, workspace_root = _engine(tmp_path, sandbox)
    artifact = store.put_bytes(patch_bytes, "text/x-diff")
    manifest = _manifest_for(
        package,
        patch_bytes,
        backend="docker" if mismatch == "image" else "local",
        image=package.environment.evaluator_image if mismatch == "image" else None,
    )
    if mismatch == "task":
        manifest = manifest.model_copy(update={"task_id": "different-task"})
    elif mismatch == "patch":
        other = "sha256:" + "f" * 64
        manifest = manifest.model_copy(
            update={
                "submitted_patch_content_hash": other,
                "visible_check_diff_hash": other,
            }
        )
    elif mismatch == "image":
        digest = "sha256:" + "b" * 64
        image = f"patchloop/other@{digest}"
        manifest = manifest.model_copy(
            update={
                "evaluator_image_digest": digest,
                "sandbox_identity_hash": sha256_json(
                    {
                        "backend": "docker",
                        "evaluator_image": image,
                        "image_digest": digest,
                    }
                ),
            }
        )
    else:
        manifest = manifest.model_copy(update={"task_content_hash": "sha256:" + "e" * 64})
    _write_manifest(store, manifest)

    with pytest.raises(ContractError, match="manifest input mismatch"):
        engine.evaluate(
            task_dir,
            artifact.path,
            manifest,
            submitted_patch_artifact=artifact,
        )
    assert list(workspace_root.iterdir()) == []


@pytest.mark.parametrize(
    ("mode", "expected", "failure_class"),
    [
        ("pass", VerdictState.PASS, None),
        ("violation", VerdictState.FAIL, "SAFETY_POLICY_FAILED"),
        ("missing", VerdictState.ERROR, "SAFETY_EVIDENCE_ERROR"),
    ],
)
def test_docker_policy_evidence_maps_pass_fail_and_error(
    tmp_path,
    mode,
    expected,
    failure_class,
) -> None:
    task_dir, package = _copy_smoke_task(tmp_path, with_environment=True)
    patch_bytes = _submitted_patch_bytes(tmp_path, task_dir, package)
    image = package.environment.evaluator_image
    sandbox = PolicySandbox(image, mode)
    engine, store, _ = _engine(tmp_path, sandbox)
    artifact = store.put_bytes(patch_bytes, "text/x-diff")
    manifest = _manifest_for(package, patch_bytes, backend="docker", image=image)
    _write_manifest(store, manifest)

    result = engine.evaluate(
        task_dir,
        artifact.path,
        manifest,
        submitted_patch_artifact=artifact,
    )
    assert result.scope_compliant_success is True
    assert result.verdicts.safety_policy == expected
    assert runner._evaluator_summary(result) == {
        "task_acceptance": "PASS",
        "safety_state": expected.value.upper(),
        "failure_class": failure_class,
        "claim_eligible": False,
    }
    requested = next(
        item
        for item in result.safety_evidence
        if item.control == SafetyControl.REQUESTED_SANDBOX_POLICY
    )
    assert requested.state == expected
    checks = [
        item for item in result.verifier_results if item.check_type in {"hidden", "regression"}
    ]
    if mode == "missing":
        assert all(item.details["execution_policy"] is None for item in checks)
    else:
        assert all(item.details["execution_policy_hash"].startswith("sha256:") for item in checks)
    provenance = json.loads(
        (store.root / "runs" / manifest.run_id / "provenance.json").read_text(
            encoding="utf-8"
        )
    )
    assert provenance["evaluation_status"] == "completed"
    if mode == "missing":
        assert provenance["execution_policy_hashes"] == []
    else:
        assert provenance["execution_policy_hashes"]


def test_execution_policy_and_failure_provenance_survive_evaluator_error(tmp_path) -> None:
    task_dir, package = _copy_smoke_task(tmp_path, with_environment=True)
    patch_bytes = _submitted_patch_bytes(tmp_path, task_dir, package)
    image = package.environment.evaluator_image
    sandbox = PolicySandbox(image, "error_after_one")
    engine, store, _ = _engine(tmp_path, sandbox)
    artifact = store.put_bytes(patch_bytes, "text/x-diff")
    manifest = _manifest_for(package, patch_bytes, backend="docker", image=image)
    _write_manifest(store, manifest)

    with pytest.raises(RuntimeError, match="simulated evaluator interruption"):
        engine.evaluate(
            task_dir,
            artifact.path,
            manifest,
            submitted_patch_artifact=artifact,
        )
    provenance = json.loads(
        (store.root / "runs" / manifest.run_id / "provenance.json").read_text(
            encoding="utf-8"
        )
    )
    assert provenance["evaluation_status"] == "error"
    assert provenance["failure_class"] == "RuntimeError"
    assert len(provenance["execution_policy_hashes"]) == 1
    requested = next(
        item
        for item in provenance["safety_evidence"]
        if item["control"] == SafetyControl.REQUESTED_SANDBOX_POLICY.value
    )
    assert requested["state"] == VerdictState.ERROR.value
