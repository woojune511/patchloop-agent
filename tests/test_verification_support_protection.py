"""Explicit task scope protects source-located verification support, end to end."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from test_evaluator import _copy_smoke_task, _manifest_for, _write_manifest

from diagnostics import current_dev20 as panel
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import VerdictState
from patchloop.dev.contracts import RequestedTool
from patchloop.errors import ContractError
from patchloop.git_execution import run_git
from patchloop.repository import DiffSummary, WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox import SandboxResult
from patchloop.task_loader import load_task_package
from patchloop.verifier import EvaluationEngine
from patchloop.verifier.policy import verify_scope

HELPER = "src/sqlfluff/testing/rules.py"
ORIGINAL = "def assert_failure(actual):\n    assert actual\n"
WEAKENED = "def assert_failure(actual):\n    return actual\n"


def current_constraints(index=17):
    return load_task_package(
        repository_root() / panel.PACKAGES / str(index)
    ).public.constraints


@pytest.fixture
def support_workspace(gateway_factory):
    gateway, _, workspace = gateway_factory()
    target = workspace / HELPER
    target.parent.mkdir(parents=True)
    target.write_text(ORIGINAL, encoding="utf-8")
    run_git(workspace, "add", HELPER)
    run_git(workspace, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-m", "public verification helper fixture")
    gateway.public_task.constraints = current_constraints().model_copy(deep=True)
    return gateway, workspace, target


@pytest.mark.parametrize("index", range(16, 21))
def test_current_sqlfluff_tasks_protect_helpers_without_banning_product_source(index):
    constraints = current_constraints(index)
    for path, expected in [
        (HELPER, False),
        ("src/sqlfluff/testing/nested/check.py", False),
        ("src/sqlfluff/rules/L031.py", True),
        ("src/sqlfluff/testing_api.py", True),
    ]:
        diff = DiffSummary([path], 1, 1, "", [])
        assert verify_scope(diff, constraints).passed is expected


def test_gateway_can_read_support_but_rejects_weakening_before_mutation(support_workspace):
    gateway, workspace, target = support_workspace
    read = gateway.execute(RequestedTool(
        name="read_file", action_id="read-helper",
        arguments={"path": HELPER, "start_line": 1, "end_line": 20},
    ))
    assert read.status == "succeeded"
    rejected = gateway.execute(RequestedTool(
        name="replace_text", action_id="weaken-helper",
        arguments={
            "path": HELPER, "old_text": ORIGINAL, "new_text": WEAKENED,
            "occurrence": 1, "hypothesis": "Bypass a contradictory expectation",
            "expected_behavior": "The helper no longer rejects the candidate",
            "causal_revision": None,
        },
    ))
    assert rejected.status == "failed"
    assert rejected.output["mutation_failure"]["class"] == "path_not_allowed"
    assert target.read_text(encoding="utf-8") == ORIGINAL
    assert gateway.accepted_mutations == 0
    assert not WorkspaceManager.diff_summary(workspace).patch


def test_isolated_evaluation_scope_rejects_helper_even_if_checks_pass(
    tmp_path, support_workspace,
):
    gateway, workspace, target = support_workspace
    task_dir, _ = _copy_smoke_task(tmp_path, with_environment=False)
    public_path = task_dir / "public.yaml"
    public = yaml.safe_load(public_path.read_text(encoding="utf-8"))
    public["repository"]["url"] = "https://github.com/sqlfluff/sqlfluff.git"
    public["repository"]["base_commit"] = run_git(
        workspace, "rev-parse", "HEAD"
    ).stdout.strip()
    public["constraints"] = gateway.public_task.constraints.model_dump(mode="json")
    public_path.write_text(yaml.safe_dump(public), encoding="utf-8")
    package = load_task_package(task_dir)
    target.write_text(WEAKENED, encoding="utf-8")
    patch = WorkspaceManager.diff_summary(workspace).patch.encode("utf-8")

    class PassingSandbox:
        backend = "local"
        official = False

        def run_check(self, path, check):
            # Deliberately report success without executing public or private checks.
            assert (path / HELPER).read_text(encoding="utf-8") == WEAKENED
            return SandboxResult(check.command, 0, "", "", 0, False, False, 0)

    store = ArtifactStore(tmp_path / "evaluation-artifacts")
    manager = WorkspaceManager(
        repository_root() / "fixtures/repositories", tmp_path / "isolated-workspaces",
        local_source=workspace,
    )
    engine = EvaluationEngine(manager, PassingSandbox(), store)
    artifact = store.put_bytes(patch, "text/x-diff")
    manifest = _manifest_for(package, patch, backend="local", image=None)
    _write_manifest(store, manifest)
    result = engine.evaluate(task_dir, artifact.path, manifest, submitted_patch_artifact=artifact)
    assert result.verdicts.hidden_tests == VerdictState.PASS
    assert result.verdicts.regression_tests == VerdictState.PASS
    assert result.verdicts.scope_policy == VerdictState.FAIL
    assert not result.scope_compliant_success
    scope = next(item for item in result.verifier_results if item.check_id == "scope")
    assert f"path matches forbidden_paths: {HELPER}" in scope.details["violations"]
    assert Path(artifact.path).read_bytes() == patch


def test_native_assessment_rejects_helper_before_projection_or_execution(
    monkeypatch, tmp_path, support_workspace,
):
    gateway, workspace, target = support_workspace
    target.write_text(WEAKENED, encoding="utf-8")
    diff = WorkspaceManager.diff_summary(workspace)
    run_id = workspace.parent.name
    request = SimpleNamespace(state_root=workspace.parents[2], task=tmp_path / "public.yaml")
    value = {"accounting": {"billing_known": True}, "result": {"runs": [{
        "run_id": run_id, "artifact_hashes": {"submitted_patch": diff.patch_hash},
    }]}}
    monkeypatch.setattr(panel, "load_task_package", lambda _: SimpleNamespace(
        public=gateway.public_task,
    ))

    def no_native_call(*args, **kwargs):
        pytest.fail("forbidden helper edit reached native evaluation")

    monkeypatch.setattr(panel.old, "native_assessment", no_native_call)
    with pytest.raises(ContractError, match="submitted source violates scope"):
        panel.assess(tmp_path, {}, value, request)
    assert target.read_text(encoding="utf-8") == WEAKENED
    assert WorkspaceManager.diff_summary(workspace).patch_hash == diff.patch_hash
