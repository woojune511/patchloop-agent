"""Evaluator that never trusts the agent's self-reported outcome."""

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
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes
from patchloop.verifier.policy import (
    PolicyOutcome,
    verify_dependencies,
    verify_public_api,
    verify_scope,
    verify_test_tampering,
)
from patchloop.verifier.runtime_evidence import (
    EvaluatorV2RuntimeAuthority,
    EvaluatorV2StoreBoundProduction,
    build_submitted_patch_ref,
    produce_evaluator_v2_result_from_state,
    produce_registered_check_evidence_v2,
    produce_scope_policy_evidence_v2,
)


class EvaluationEngine:
    def __init__(
        self,
        workspace_manager: WorkspaceManager,
        sandbox: Sandbox,
        artifact_store: ArtifactStore,
        state_store: StateStore | None = None,
    ) -> None:
        self.workspace_manager = workspace_manager
        self.sandbox = sandbox
        self.artifact_store = artifact_store
        self.state_store = state_store

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

    def evaluate_v2_candidate(
        self,
        task_dir: str | Path,
        patch_path: str | Path,
        manifest: RunManifest,
        *,
        submitted_patch_artifact: Artifact,
        authority: EvaluatorV2RuntimeAuthority,
        usage: Usage | None = None,
    ) -> EvaluatorV2StoreBoundProduction:
        """Produce one store-bound, unofficial evaluator-v2 candidate.

        This path remains separate from evaluator-v1 and is selected only by
        the authority-gated standard runner. It performs no Docker or provider
        activation on its own; the supplied sandbox owns check execution.
        """

        if self.state_store is None:
            raise ContractError("evaluator-v2 candidate requires durable run state")
        if not self.sandbox.official:
            raise ContractError("evaluator-v2 candidate requires the Docker sandbox")
        persisted_manifest = self.state_store.get_manifest(manifest.run_id)
        if persisted_manifest != manifest:
            raise ContractError("evaluator-v2 candidate manifest differs from durable state")
        package = load_task_package(task_dir)
        patch_bytes = Path(patch_path).read_bytes()
        if (
            self.artifact_store.read_bytes(submitted_patch_artifact) != patch_bytes
            or sha256_bytes(patch_bytes) != submitted_patch_artifact.content_hash
        ):
            raise ContractError("evaluator-v2 candidate patch is not the accepted CAS object")

        workspace = self.workspace_manager.create(
            f"eval_v2_{uuid.uuid4().hex}",
            package.public.repository.url,
            package.public.repository.base_commit,
        )
        started = time.monotonic()
        patch_hash = self.workspace_manager.apply_patch(workspace, patch_path)
        hidden_source = Path(package.root) / "hidden"
        hidden_target = workspace / ".patchloop-hidden"
        if hidden_source.exists():
            shutil.copytree(hidden_source, hidden_target)
        summary = self.workspace_manager.diff_summary(workspace)
        if not (patch_hash == summary.patch_hash == submitted_patch_artifact.content_hash):
            raise ContractError("evaluator-v2 candidate workspace differs from accepted patch")

        patch_ref = build_submitted_patch_ref(
            self.artifact_store,
            submitted_patch_artifact,
        )
        registered = []
        for check_type, checks in (
            ("regression", package.public.visible_checks),
            ("hidden", package.private.hidden_checks),
        ):
            for check in checks:
                outcome = self.sandbox.run_check(workspace, check)
                registered.append(
                    produce_registered_check_evidence_v2(
                        artifact_store=self.artifact_store,
                        manifest=manifest,
                        submitted_patch=patch_ref,
                        check_type=check_type,
                        check=check,
                        outcome=outcome,
                        private_markers=authority.private_markers,
                    )
                )

        policy_outcomes = {
            "scope": verify_scope(summary, package.public.constraints),
            "dependency": verify_dependencies(summary, package.public.constraints),
            "test_tampering": verify_test_tampering(summary),
            "public_api": verify_public_api(
                summary,
                package.public.constraints,
                workspace,
            ),
        }
        policies = [
            produce_scope_policy_evidence_v2(
                artifact_store=self.artifact_store,
                manifest=manifest,
                submitted_patch=patch_ref,
                check_id=check_id,
                outcome=outcome,
            )
            for check_id, outcome in policy_outcomes.items()
        ]
        final_usage = usage.model_copy(deep=True) if usage is not None else Usage()
        final_usage.wall_clock_ms += int((time.monotonic() - started) * 1000)
        return produce_evaluator_v2_result_from_state(
            state_store=self.state_store,
            artifact_store=self.artifact_store,
            run_id=manifest.run_id,
            package=package,
            expected_contract=authority.safety_contract,
            expected_evaluator_source_hash=authority.evaluator_source_hash,
            expected_tool_schemas=authority.tool_schemas,
            private_markers=authority.private_markers,
            submitted_patch=submitted_patch_artifact,
            registered_checks=registered,
            scope_policies=policies,
            usage=final_usage,
        )

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
            raise ContractError("evaluator patch input does not match the accepted artifact")
        workspace = self.workspace_manager.create(
            f"eval_{uuid.uuid4().hex}",
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
        patch_artifact = (
            submitted_patch_artifact
            if submitted_patch_artifact is not None
            else self.artifact_store.put_text(summary.patch, "text/x-diff")
        )
        elapsed = int((time.monotonic() - started) * 1000)
        final_usage = usage.model_copy(deep=True) if usage is not None else Usage()
        final_usage.wall_clock_ms += elapsed
        result = RunResult(
            run_id=manifest.run_id,
            agent_submission_status="completed",
            evaluation_status="completed",
            scope_compliant_success=success,
            official=self.sandbox.official,
            verdicts=verdicts,
            usage=final_usage,
            submitted_patch_artifact_id=patch_artifact.artifact_id,
            verifier_results=results,
        )
        run_dir = Path(self.artifact_store.root) / "runs" / manifest.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
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
                    "patch_hash": patch_hash,
                    "diff_hash": summary.patch_hash,
                    "submitted_patch_artifact_id": patch_artifact.artifact_id,
                    "submitted_patch_content_hash": patch_artifact.content_hash,
                    "verifier_evidence_schema_version": ("verifier-evidence-v1"),
                    "verifier_evidence_artifacts": [
                        raw_artifact
                        for verifier_result in results
                        for raw_artifact in verifier_result.details.get(
                            "evidence_artifacts",
                            [],
                        )
                    ],
                },
                indent=2,
            ),
        )
        return result
