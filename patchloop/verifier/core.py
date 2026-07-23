"""Evaluator that never trusts the agent's self-reported outcome."""

from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    RunManifest,
    RunResult,
    Usage,
    Verdicts,
    VerdictState,
    VerifierResult,
)
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.runner import Sandbox
from patchloop.task_loader import load_task_package
from patchloop.verifier.policy import (
    PolicyOutcome,
    verify_dependencies,
    verify_public_api,
    verify_scope,
    verify_test_tampering,
)


class EvaluationEngine:
    def __init__(
        self,
        workspace_manager: WorkspaceManager,
        sandbox: Sandbox,
        artifact_store: ArtifactStore,
    ) -> None:
        self.workspace_manager = workspace_manager
        self.sandbox = sandbox
        self.artifact_store = artifact_store

    def _policy_result(self, run_id: str, check_id: str, outcome: PolicyOutcome) -> VerifierResult:
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
        self, run_id: str, workspace: Path, checks: list, kind: str
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
                    duration_ms=int((time.monotonic() - started) * 1000),
                    evidence_artifact_ids=[artifact.artifact_id],
                    details={
                        "exit_code": outcome.exit_code,
                        "timed_out": outcome.timed_out,
                        "truncated": outcome.truncated,
                        "artifact_path": artifact.path,
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
        self, task_dir: str | Path, patch_path: str | Path, manifest: RunManifest
    ) -> RunResult:
        package = load_task_package(task_dir)
        workspace = self.workspace_manager.create(
            f"{manifest.run_id}_evaluator",
            package.public.repository.url,
            package.public.repository.base_commit,
        )
        started = time.monotonic()
        patch_hash = self.workspace_manager.apply_patch(workspace, patch_path)

        # Hidden files are copied only into the evaluator workspace after agent submission.
        hidden_source = Path(package.root) / "hidden"
        hidden_target = workspace / ".patchloop-hidden"
        if hidden_source.exists():
            shutil.copytree(hidden_source, hidden_target)

        summary = self.workspace_manager.diff_summary(workspace)
        results: list[VerifierResult] = []
        results.extend(
            self._run_checks(
                manifest.run_id, workspace, package.public.visible_checks, "regression"
            )
        )
        results.extend(
            self._run_checks(manifest.run_id, workspace, package.private.hidden_checks, "hidden")
        )

        policy_outcomes = {
            "scope": verify_scope(summary, package.public.constraints),
            "dependency": verify_dependencies(summary, package.public.constraints),
            "test_tampering": verify_test_tampering(summary),
            "public_api": verify_public_api(summary, package.public.constraints, workspace),
        }
        for check_id, outcome in policy_outcomes.items():
            results.append(self._policy_result(manifest.run_id, check_id, outcome))

        hidden_state = self._aggregate(results, "hidden")
        regression_state = self._aggregate(results, "regression")
        policy_results = [result for result in results if result.check_type == "policy"]
        scope_state = (
            VerdictState.PASS
            if policy_results
            and all(result.state == VerdictState.PASS for result in policy_results)
            else VerdictState.FAIL
        )
        safety_state = VerdictState.PASS
        verdicts = Verdicts(
            hidden_tests=hidden_state,
            regression_tests=regression_state,
            scope_policy=scope_state,
            safety_policy=safety_state,
        )
        success = all(
            state == VerdictState.PASS
            for state in (
                hidden_state,
                regression_state,
                scope_state,
                safety_state,
            )
        )
        patch_artifact = self.artifact_store.put_text(summary.patch, "text/x-diff")
        elapsed = int((time.monotonic() - started) * 1000)
        result = RunResult(
            run_id=manifest.run_id,
            agent_submission_status="completed",
            evaluation_status="completed",
            scope_compliant_success=success,
            official=self.sandbox.official,
            verdicts=verdicts,
            usage=Usage(wall_clock_ms=elapsed),
            submitted_patch_artifact_id=patch_artifact.artifact_id,
            verifier_results=results,
        )
        run_dir = Path(self.artifact_store.root) / "runs" / manifest.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        (run_dir / "result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        (run_dir / "provenance.json").write_text(
            json.dumps({"patch_hash": patch_hash, "diff_hash": summary.patch_hash}, indent=2),
            encoding="utf-8",
        )
        return result
