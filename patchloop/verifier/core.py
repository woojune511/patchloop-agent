"""Private evaluator isolated from the coding-agent context."""

from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    RunManifest,
    RunResult,
    Usage,
    Verdicts,
    VerdictState,
    VerifierResult,
)
from patchloop.errors import ContractError
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.runner import Sandbox
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes
from patchloop.verifier.policy import (
    PolicyOutcome,
    verify_dependencies,
    verify_public_api,
    verify_scope,
    verify_test_tampering,
)


class EvaluationEngine:
    """Evaluate a submitted patch in a separate clean workspace."""

    def __init__(
        self,
        workspace_manager: WorkspaceManager,
        sandbox: Sandbox,
        artifact_store: ArtifactStore,
    ) -> None:
        self.workspace_manager = workspace_manager
        self.sandbox = sandbox
        self.artifact_store = artifact_store

    @staticmethod
    def _policy_result(run_id: str, check_id: str, outcome: PolicyOutcome) -> VerifierResult:
        return VerifierResult(
            verifier_result_id=f"vr_{uuid.uuid4().hex}",
            run_id=run_id,
            check_type="policy",
            check_id=check_id,
            state=VerdictState.PASS if outcome.passed else VerdictState.FAIL,
            duration_ms=0,
            details={"violations": outcome.violations, **outcome.details},
        )

    def _run_checks(
        self,
        run_id: str,
        workspace: Path,
        checks: list,
        kind: str,
    ) -> list[VerifierResult]:
        results: list[VerifierResult] = []
        for check in checks:
            started = time.monotonic()
            outcome = self.sandbox.run_check(workspace, check)
            artifact = self.artifact_store.put_json(
                {
                    "command": outcome.command,
                    "exit_code": outcome.exit_code,
                    "stdout": outcome.stdout,
                    "stderr": outcome.stderr,
                    "timed_out": outcome.timed_out,
                    "truncated": outcome.truncated,
                    "original_output_bytes": outcome.original_output_bytes,
                }
            )
            passed = not outcome.timed_out and outcome.exit_code in check.expected_exit_codes
            results.append(
                VerifierResult(
                    verifier_result_id=f"vr_{uuid.uuid4().hex}",
                    run_id=run_id,
                    check_type=kind,
                    check_id=check.id,
                    state=VerdictState.PASS if passed else VerdictState.FAIL,
                    duration_ms=int((time.monotonic() - started) * 1_000),
                    evidence_artifact_ids=[artifact.artifact_id],
                    details={
                        "exit_code": outcome.exit_code,
                        "timed_out": outcome.timed_out,
                        "truncated": outcome.truncated,
                        "artifact_path": artifact.path,
                        "evidence_artifacts": [artifact.model_dump(mode="json")],
                    },
                )
            )
        return results

    @staticmethod
    def _aggregate(results: list[VerifierResult], check_type: str) -> VerdictState:
        selected = [result for result in results if result.check_type == check_type]
        if not selected:
            return VerdictState.NOT_RUN
        if any(result.state == VerdictState.ERROR for result in selected):
            return VerdictState.ERROR
        if any(result.state != VerdictState.PASS for result in selected):
            return VerdictState.FAIL
        return VerdictState.PASS

    def evaluate(
        self,
        task_dir: str | Path,
        patch_path: str | Path,
        manifest: RunManifest,
        usage: Usage | None = None,
        submitted_patch_artifact: Artifact | None = None,
    ) -> RunResult:
        package = load_task_package(task_dir)
        patch_bytes = Path(patch_path).read_bytes()
        if (
            submitted_patch_artifact is not None
            and sha256_bytes(patch_bytes) != submitted_patch_artifact.content_hash
        ):
            raise ContractError("evaluator input differs from the accepted patch artifact")
        workspace = self.workspace_manager.create(
            f"eval_{uuid.uuid4().hex}",
            package.public.repository.url,
            package.public.repository.base_commit,
        )
        started = time.monotonic()
        patch_hash = self.workspace_manager.apply_patch(workspace, patch_path)

        # Capture the submitted public diff before evaluator-private files are introduced.
        summary = self.workspace_manager.diff_summary(workspace)

        # Evaluator-private files appear only after submission and only in this workspace.
        hidden_source = Path(package.root) / "hidden"
        hidden_target = workspace / ".patchloop-hidden"
        if hidden_source.exists():
            shutil.copytree(hidden_source, hidden_target)

        results = self._run_checks(
            manifest.run_id,
            workspace,
            package.public.visible_checks,
            "regression",
        )
        results.extend(
            self._run_checks(
                manifest.run_id,
                workspace,
                package.private.hidden_checks,
                "hidden",
            )
        )
        policies = {
            "scope": verify_scope(summary, package.public.constraints),
            "dependency": verify_dependencies(summary, package.public.constraints),
            "test_tampering": verify_test_tampering(summary),
            "public_api": verify_public_api(summary, package.public.constraints, workspace),
        }
        results.extend(
            self._policy_result(manifest.run_id, check_id, outcome)
            for check_id, outcome in policies.items()
        )

        hidden_state = self._aggregate(results, "hidden")
        regression_state = self._aggregate(results, "regression")
        policy_results = [result for result in results if result.check_type == "policy"]
        scope_state = (
            VerdictState.PASS
            if policy_results
            and all(result.state == VerdictState.PASS for result in policy_results)
            else VerdictState.FAIL
        )
        verdicts = Verdicts(
            hidden_tests=hidden_state,
            regression_tests=regression_state,
            scope_policy=scope_state,
            safety_policy=VerdictState.PASS,
        )
        success = all(
            state == VerdictState.PASS
            for state in (
                hidden_state,
                regression_state,
                scope_state,
                VerdictState.PASS,
            )
        )
        patch_artifact = submitted_patch_artifact or self.artifact_store.put_text(
            summary.patch,
            "text/x-diff",
        )
        final_usage = usage.model_copy(deep=True) if usage is not None else Usage()
        final_usage.wall_clock_ms += int((time.monotonic() - started) * 1_000)
        result = RunResult(
            run_id=manifest.run_id,
            agent_submission_status="completed",
            evaluation_status="completed",
            scope_compliant_success=success,
            official=False,
            verdicts=verdicts,
            usage=final_usage,
            submitted_patch_artifact_id=patch_artifact.artifact_id,
            verifier_results=results,
        )
        run_dir = Path(self.artifact_store.root) / "runs" / manifest.run_id
        self.artifact_store.write_text_atomic(
            run_dir / "manifest.json",
            manifest.model_dump_json(indent=2),
        )
        self.artifact_store.write_text_atomic(
            run_dir / "result.json",
            result.model_dump_json(indent=2),
        )
        self.artifact_store.write_text_atomic(
            run_dir / "provenance.json",
            json.dumps(
                {
                    "official": False,
                    "patch_hash": patch_hash,
                    "diff_hash": summary.patch_hash,
                    "submitted_patch_content_hash": patch_artifact.content_hash,
                    "evaluator_workspace_separate": True,
                },
                indent=2,
            ),
        )
        return result
