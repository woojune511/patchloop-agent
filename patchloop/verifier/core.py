"""Private evaluator isolated from the coding-agent context."""

from __future__ import annotations

import json
import math
import re
import shutil
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    RunManifest,
    RunResult,
    SafetyControl,
    SafetyEvidence,
    Usage,
    Verdicts,
    VerdictState,
    VerifierResult,
)
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev.contracts import dev_tool_surface_hash
from patchloop.errors import ContractError, PatchLoopError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import runtime_content_hash
from patchloop.sandbox.runner import Sandbox, SandboxCleanupError, registered_check_execution_policy
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json
from patchloop.verifier.policy import (
    PolicyOutcome,
    verify_dependencies,
    verify_public_api,
    verify_scope,
    verify_test_tampering,
)


@dataclass(frozen=True)
class _CheckEvidence:
    check: Any
    result: VerifierResult
    artifact: Artifact


class EvaluationEngine:
    """Evaluate one exact submitted patch in a separate clean workspace."""

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
        checks: list[Any],
        kind: str,
        results: list[VerifierResult],
        recorded: list[_CheckEvidence],
        deadline: ExecutionDeadline | None = None,
    ) -> None:
        for check in checks:
            if deadline is not None:
                deadline.check()
            started = time.monotonic()
            if getattr(self.sandbox, "supports_execution_deadline", False):
                outcome = self.sandbox.run_check(
                    workspace, check, deadline=deadline,
                    execution_identity={
                        "run_id": run_id, "action_id": f"evaluator:{kind}:{check.id}"
                    },
                )
            else:
                outcome = self.sandbox.run_check(workspace, check)
            execution_policy_hash = (
                sha256_json(outcome.execution_policy)
                if outcome.execution_policy is not None
                else None
            )
            artifact = self.artifact_store.put_json(
                {
                    "command": outcome.command,
                    "exit_code": outcome.exit_code,
                    "stdout": outcome.stdout,
                    "stderr": outcome.stderr,
                    "timed_out": outcome.timed_out,
                    "truncated": outcome.truncated,
                    "original_output_bytes": outcome.original_output_bytes,
                    "execution_policy": outcome.execution_policy,
                    "execution_policy_hash": execution_policy_hash,
                    "deadline_exhausted": outcome.deadline_exhausted,
                    "cleanup_failed": outcome.cleanup_failed,
                }
            )
            passed = not outcome.timed_out and outcome.exit_code in check.expected_exit_codes
            result = VerifierResult(
                verifier_result_id=f"vr_{uuid.uuid4().hex}",
                run_id=run_id,
                check_type=kind,
                check_id=check.id,
                state=(
                    VerdictState.ERROR if outcome.deadline_exhausted or outcome.cleanup_failed
                    else VerdictState.PASS if passed else VerdictState.FAIL
                ),
                duration_ms=int((time.monotonic() - started) * 1_000),
                evidence_artifact_ids=[artifact.artifact_id],
                details={
                    "exit_code": outcome.exit_code,
                    "timed_out": outcome.timed_out,
                    "truncated": outcome.truncated,
                    "execution_policy": outcome.execution_policy,
                    "execution_policy_hash": execution_policy_hash,
                    "deadline_exhausted": outcome.deadline_exhausted,
                    "cleanup_failed": outcome.cleanup_failed,
                    "artifact_path": artifact.path,
                    "evidence_artifacts": [artifact.model_dump(mode="json")],
                },
            )
            results.append(result)
            recorded.append(_CheckEvidence(check, result, artifact))
            if outcome.cleanup_failed:
                raise SandboxCleanupError(
                    "owned evaluator container cleanup could not be confirmed"
                )
            if outcome.deadline_exhausted:
                raise ExecutionDeadlineExceeded("active deadline exhausted during evaluation")

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

    def _safety_evidence(
        self,
        control: SafetyControl,
        state: VerdictState,
        *,
        details: dict[str, Any],
        source_hashes: list[str] | None = None,
    ) -> SafetyEvidence:
        hashes = sorted(set(source_hashes or []))
        artifact = self.artifact_store.put_json(
            {
                "schema_version": "dev-safety-evidence-v1",
                "control": control.value,
                "state": state.value,
                "source_hashes": hashes,
                "details": details,
            }
        )
        return SafetyEvidence(
            control=control,
            state=state,
            evidence_artifact_ids=[artifact.artifact_id],
            evidence_hashes=[*hashes, artifact.content_hash],
            details=details,
        )

    def _sandbox_policy_evidence(
        self,
        manifest: RunManifest,
        expected_checks: list[Any],
        recorded: list[_CheckEvidence],
    ) -> SafetyEvidence:
        if manifest.sandbox_backend == "local":
            return self._safety_evidence(
                SafetyControl.REQUESTED_SANDBOX_POLICY,
                VerdictState.NOT_RUN,
                details={"reason": "local backend has no Docker policy execution"},
            )

        image = getattr(self.sandbox, "image", None)
        integrity_errors: list[str] = []
        violations: list[str] = []
        source_hashes: list[str] = []
        if not isinstance(image, str):
            integrity_errors.append("Docker sandbox image identity is missing")
        if len(recorded) != len(expected_checks):
            integrity_errors.append("one or more Docker check policy records are missing")

        for item in recorded:
            actual = item.result.details.get("execution_policy")
            actual_hash = item.result.details.get("execution_policy_hash")
            source_hashes.append(item.artifact.content_hash)
            if not isinstance(actual, dict) or not isinstance(actual_hash, str):
                integrity_errors.append(f"{item.result.check_id}: execution policy is missing")
                continue
            if sha256_json(actual) != actual_hash:
                integrity_errors.append(f"{item.result.check_id}: execution policy hash mismatch")
                continue
            try:
                raw = self.artifact_store.read_bytes(item.artifact)
                artifact_payload = json.loads(raw.decode("utf-8"))
            except (PatchLoopError, OSError, UnicodeDecodeError, json.JSONDecodeError):
                integrity_errors.append(f"{item.result.check_id}: evidence artifact is invalid")
                continue
            if (
                artifact_payload.get("execution_policy") != actual
                or artifact_payload.get("execution_policy_hash") != actual_hash
            ):
                integrity_errors.append(f"{item.result.check_id}: policy artifact disagrees")
                continue
            source_hashes.append(actual_hash)
            working_directory = "/workspace"
            if item.check.working_directory != ".":
                working_directory += f"/{item.check.working_directory}"
            if isinstance(image, str):
                try:
                    effective = actual.get("effective_timeout_seconds")
                    limited = actual.get("row_deadline_limited")
                    cleanup_status = actual.get("cleanup_status")
                    if (
                        type(effective) not in {int, float}
                        or type(limited) is not bool
                        or limited != (effective < item.check.timeout_seconds)
                        or cleanup_status != "confirmed"
                    ):
                        raise ValueError("invalid deadline or cleanup evidence")
                    expected = registered_check_execution_policy(
                        image=image,
                        working_directory=working_directory,
                        timeout_seconds=item.check.timeout_seconds,
                        output_limit_bytes=item.check.output_limit_bytes,
                        effective_timeout_seconds=effective,
                        row_deadline_limited=limited,
                    )
                except (ValueError, TypeError):
                    integrity_errors.append(
                        f"{item.result.check_id}: timeout or cleanup evidence is invalid"
                    )
                    continue
                if actual != expected:
                    violations.append(f"{item.result.check_id}: requested policy was violated")

        if integrity_errors:
            state = VerdictState.ERROR
        elif violations:
            state = VerdictState.FAIL
        else:
            state = VerdictState.PASS
        return self._safety_evidence(
            SafetyControl.REQUESTED_SANDBOX_POLICY,
            state,
            details={
                "expected_check_count": len(expected_checks),
                "recorded_policy_count": len(recorded),
                "integrity_errors": integrity_errors,
                "violations": violations,
            },
            source_hashes=source_hashes,
        )

    def _probe_policy_evidence(self, manifest: RunManifest) -> SafetyEvidence | None:
        """Validate prior public experiments without granting task-check credit."""

        if manifest.probe_profile_hash is None and not (
            manifest.probe_evidence or manifest.probe_execution_count
        ):
            return None
        from patchloop.sandbox.probes import (
            PROBE_IMAGE_DIGEST,
            PROBE_TIMEOUT_SECONDS,
            probe_execution_policy,
            probe_profile_hash,
        )

        integrity_errors: list[str] = []
        violations: list[str] = []
        source_hashes: list[str] = []
        policy_hashes: list[str] = []
        if (
            manifest.probe_image_digest != PROBE_IMAGE_DIGEST
            or manifest.probe_profile_hash != probe_profile_hash()
        ):
            integrity_errors.append("probe manifest profile or image differs from runtime")
        if len(manifest.probe_evidence) != manifest.probe_execution_count:
            integrity_errors.append("one or more probe execution receipts are missing")
        seen_actions: set[str] = set()
        for index, artifact in enumerate(manifest.probe_evidence):
            label = f"probe receipt {index + 1}"
            source_hashes.append(artifact.content_hash)
            try:
                receipt = json.loads(self.artifact_store.read_bytes(artifact).decode("utf-8"))
            except (PatchLoopError, OSError, UnicodeDecodeError, json.JSONDecodeError):
                integrity_errors.append(f"{label}: artifact is unavailable or invalid")
                continue
            if not isinstance(receipt, dict):
                integrity_errors.append(f"{label}: receipt is not an object")
                continue
            action_id = receipt.get("action_id")
            if (
                not isinstance(action_id, str) or not 1 <= len(action_id) <= 500
                or action_id in seen_actions
                or receipt.get("schema_version") != "dev-probe-receipt-v1"
                or receipt.get("run_id") != manifest.run_id
            ):
                integrity_errors.append(f"{label}: action or run identity is invalid")
                continue
            seen_actions.add(action_id)
            hash_fields = (
                "input_hash", "source_hash", "snapshot_hash", "workspace_diff_hash",
                "diff_hash", "image_digest", "profile_hash", "execution_policy_hash",
            )
            if any(
                not isinstance(receipt.get(key), str)
                or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt[key]) is None
                for key in hash_fields
            ):
                integrity_errors.append(f"{label}: required hash identity is missing or invalid")
                continue
            source_hashes.extend(receipt[key] for key in hash_fields)
            if (
                receipt["image_digest"] != manifest.probe_image_digest
                or receipt["profile_hash"] != manifest.probe_profile_hash
                or receipt["diff_hash"] != receipt["workspace_diff_hash"]
            ):
                integrity_errors.append(f"{label}: image, profile or action diff disagrees")
                continue
            actual = receipt.get("execution_policy")
            if (
                not isinstance(actual, dict)
                or sha256_json(actual) != receipt["execution_policy_hash"]
            ):
                integrity_errors.append(f"{label}: execution policy is missing or hash differs")
                continue
            policy_hashes.append(receipt["execution_policy_hash"])
            effective = actual.get("effective_timeout_seconds")
            limited = actual.get("row_deadline_limited")
            declared = actual.get("requested_timeout_seconds")
            if (
                type(effective) not in {int, float} or not math.isfinite(effective)
                or not 0 < effective <= PROBE_TIMEOUT_SECONDS or type(limited) is not bool
                or limited != (effective < PROBE_TIMEOUT_SECONDS)
                or declared != PROBE_TIMEOUT_SECONDS
                or actual.get("cleanup_status") != "confirmed"
                or receipt.get("cleanup_failed") is not False
            ):
                integrity_errors.append(f"{label}: deadline or cleanup evidence is invalid")
                continue
            expected = probe_execution_policy(
                effective_timeout_seconds=effective,
                row_deadline_limited=limited,
                cleanup_status="confirmed",
            )
            if actual != expected:
                violations.append(f"{label}: requested probe policy was violated")

        state = (
            VerdictState.ERROR if integrity_errors
            else VerdictState.FAIL if violations else VerdictState.PASS
        )
        return self._safety_evidence(
            SafetyControl.REQUESTED_SANDBOX_POLICY,
            state,
            details={
                "kind": "public_probe",
                "expected_probe_count": manifest.probe_execution_count,
                "recorded_probe_count": len(manifest.probe_evidence),
                "probe_image_digest": manifest.probe_image_digest,
                "probe_profile_hash": manifest.probe_profile_hash,
                "integrity_errors": integrity_errors,
                "violations": violations,
                "grants_required_check_credit": False,
                "execution_policy_hashes": sorted(set(policy_hashes)),
            },
            source_hashes=source_hashes,
        )

    @staticmethod
    def _aggregate_safety(evidence: list[SafetyEvidence]) -> VerdictState:
        states = [item.state for item in evidence]
        if any(state == VerdictState.ERROR for state in states):
            return VerdictState.ERROR
        if any(state == VerdictState.FAIL for state in states):
            return VerdictState.FAIL
        if any(state == VerdictState.NOT_RUN for state in states):
            return VerdictState.NOT_RUN
        return VerdictState.PASS

    def _sandbox_identity(self, manifest: RunManifest) -> tuple[str, str | None, str]:
        backend = getattr(self.sandbox, "backend", None)
        if backend not in {"local", "docker"}:
            raise ContractError("evaluator sandbox has no typed backend identity")
        image = getattr(self.sandbox, "image", None) if backend == "docker" else None
        digest = None
        if backend == "docker" and isinstance(image, str) and "@" in image:
            digest = image.rsplit("@", 1)[1]
        identity = {"backend": backend, "evaluator_image": image, "image_digest": digest}
        if manifest.probe_profile_hash is not None:
            from patchloop.sandbox.probes import PROBE_IMAGE_DIGEST, probe_profile_hash

            identity.update(
                probe_image_digest=PROBE_IMAGE_DIGEST, probe_profile_hash=probe_profile_hash(),
            )
        return backend, digest, sha256_json(identity)

    def _validate_manifest_inputs(
        self,
        task_dir: str | Path,
        patch_path: str | Path,
        manifest: RunManifest,
        submitted_patch_artifact: Artifact | None,
    ) -> tuple[Any, bytes]:
        package = load_task_package(task_dir)
        manifest_path = Path(self.artifact_store.root) / "runs" / manifest.run_id / "manifest.json"
        expected_manifest = (
            canonical_json(manifest.model_dump(mode="json")) + "\n"
        ).encode("utf-8")
        if (
            not manifest_path.is_file()
            or manifest_path.is_symlink()
            or manifest_path.read_bytes() != expected_manifest
        ):
            raise ContractError("evaluator manifest is missing or differs from its input")
        if submitted_patch_artifact is None:
            raise ContractError("evaluator requires the accepted submitted patch artifact")
        patch_bytes = self.artifact_store.read_bytes(submitted_patch_artifact)
        try:
            same_path = Path(patch_path).resolve() == Path(submitted_patch_artifact.path).resolve()
        except OSError as exc:
            raise ContractError("evaluator patch path cannot be resolved") from exc
        if not same_path or Path(patch_path).read_bytes() != patch_bytes:
            raise ContractError("evaluator input differs from the accepted patch artifact")

        backend, image_digest, sandbox_identity_hash = self._sandbox_identity(manifest)
        expected_image_digest = (
            package.environment.image_digest
            if backend == "docker" and package.environment is not None
            else None
        )
        patch_hash = sha256_bytes(patch_bytes)
        actual = {
            "task_id": package.public.task_id,
            "task_version": package.public.task_version,
            "base_commit": package.public.repository.base_commit,
            "public_spec_hash": package.public_spec_hash,
            "private_spec_hash": package.private_spec_hash,
            "task_content_hash": package.task_content_hash,
            "runtime_content_hash": runtime_content_hash(),
            "tool_surface_hash": dev_tool_surface_hash(
                planning_policy=manifest.planning_policy, probe_policy=manifest.probe_policy,
            ),
            "sandbox_backend": backend,
            "evaluator_image_digest": image_digest,
            "sandbox_identity_hash": sandbox_identity_hash,
            "submitted_patch_content_hash": patch_hash,
            "visible_check_diff_hash": patch_hash,
            "submitted_changed_files": WorkspaceManager.patch_changed_files(patch_bytes),
        }
        declared = {key: getattr(manifest, key) for key in actual}
        mismatches = sorted(key for key in actual if declared[key] != actual[key])
        if expected_image_digest != image_digest:
            mismatches.append("task_evaluator_image_digest")
        if mismatches:
            raise ContractError(
                "evaluator manifest input mismatch: " + ", ".join(sorted(set(mismatches)))
            )
        return package, patch_bytes

    def evaluate(
        self,
        task_dir: str | Path,
        patch_path: str | Path,
        manifest: RunManifest,
        usage: Usage | None = None,
        submitted_patch_artifact: Artifact | None = None,
        *,
        deadline: ExecutionDeadline | None = None,
    ) -> RunResult:
        run_dir = Path(self.artifact_store.root) / "runs" / manifest.run_id
        manifest_hash = sha256_bytes(
            (canonical_json(manifest.model_dump(mode="json")) + "\n").encode("utf-8")
        )
        evaluation_status = "error"
        failure_class: str | None = None
        deadline_exhausted = False
        applied_patch_hash: str | None = None
        diff_hash: str | None = None
        changed_files: list[str] = []
        results: list[VerifierResult] = []
        recorded_checks: list[_CheckEvidence] = []
        safety_evidence: list[SafetyEvidence] = []
        expected_checks: list[Any] = []
        sandbox_policy_recorded = False
        started = time.monotonic()
        try:
            if deadline is not None:
                deadline.check()
            package, _ = self._validate_manifest_inputs(
                task_dir,
                patch_path,
                manifest,
                submitted_patch_artifact,
            )
            probe_policy = self._probe_policy_evidence(manifest)
            if probe_policy is not None:
                safety_evidence.append(probe_policy)
                if probe_policy.state == VerdictState.ERROR:
                    raise ContractError("probe execution receipts failed integrity validation")
            safety_evidence.extend(
                [
                    self._safety_evidence(
                        SafetyControl.RUNTIME_CONTRACT,
                        VerdictState.PASS,
                        details={
                            "runtime_content_hash": manifest.runtime_content_hash,
                            "task_content_hash": manifest.task_content_hash,
                            "manifest_content_hash": manifest_hash,
                        },
                        source_hashes=[
                            manifest.runtime_content_hash,
                            manifest.task_content_hash,
                            manifest_hash,
                        ],
                    ),
                    self._safety_evidence(
                        SafetyControl.CONSTRAINED_TOOL_SURFACE,
                        VerdictState.PASS,
                        details={"tool_surface_hash": manifest.tool_surface_hash},
                        source_hashes=[manifest.tool_surface_hash],
                    ),
                ]
            )
            if deadline is not None:
                deadline.check()
            workspace = self.workspace_manager.create(
                f"eval_{uuid.uuid4().hex}",
                package.public.repository.url,
                package.public.repository.base_commit,
                deadline=deadline,
            )
            if deadline is not None:
                deadline.check()
            try:
                workspace = self.workspace_manager.validate_managed_workspace(workspace)
            except PatchLoopError as exc:
                safety_evidence.append(
                    self._safety_evidence(
                        SafetyControl.MANAGED_WORKSPACE,
                        VerdictState.FAIL,
                        details={"violation": type(exc).__name__},
                    )
                )
                raise
            safety_evidence.append(
                self._safety_evidence(
                    SafetyControl.MANAGED_WORKSPACE,
                    VerdictState.PASS,
                    details={"workspace_separate": True},
                )
            )
            if deadline is not None:
                deadline.check()
            applied_patch_hash = self.workspace_manager.apply_patch(
                workspace, patch_path, deadline=deadline,
            )
            summary = self.workspace_manager.diff_summary(workspace, deadline=deadline)
            diff_hash = summary.patch_hash
            changed_files = summary.changed_files
            if (
                applied_patch_hash != manifest.submitted_patch_content_hash
                or summary.patch_hash != manifest.submitted_patch_content_hash
                or summary.changed_files != manifest.submitted_changed_files
                or summary.untracked_files
            ):
                raise ContractError("evaluator workspace differs from the submitted artifact")

            hidden_source = Path(package.root) / "hidden"
            hidden_target = workspace / ".patchloop-hidden"
            if hidden_source.exists():
                shutil.copytree(hidden_source, hidden_target)

            expected_checks = [*package.public.visible_checks, *package.private.hidden_checks]
            self._run_checks(
                manifest.run_id,
                workspace,
                package.public.visible_checks,
                "regression",
                results,
                recorded_checks,
                deadline,
            )
            self._run_checks(
                manifest.run_id,
                workspace,
                package.private.hidden_checks,
                "hidden",
                results,
                recorded_checks,
                deadline,
            )
            policies = {
                "scope": verify_scope(summary, package.public.constraints),
                "dependency": verify_dependencies(summary, package.public.constraints),
                "test_tampering": verify_test_tampering(summary),
                "public_api": verify_public_api(
                    summary,
                    package.public.constraints,
                    workspace,
                    deadline=deadline,
                ),
            }
            results.extend(
                self._policy_result(manifest.run_id, check_id, outcome)
                for check_id, outcome in policies.items()
            )

            safety_evidence.append(
                self._sandbox_policy_evidence(manifest, expected_checks, recorded_checks)
            )
            sandbox_policy_recorded = True
            hidden_state = self._aggregate(results, "hidden")
            regression_state = self._aggregate(results, "regression")
            policy_results = [result for result in results if result.check_type == "policy"]
            scope_state = (
                VerdictState.PASS
                if policy_results
                and all(result.state == VerdictState.PASS for result in policy_results)
                else VerdictState.FAIL
            )
            safety_state = self._aggregate_safety(safety_evidence)
            verdicts = Verdicts(
                hidden_tests=hidden_state,
                regression_tests=regression_state,
                scope_policy=scope_state,
                safety_policy=safety_state,
            )
            task_accepted = all(
                state == VerdictState.PASS
                for state in (hidden_state, regression_state, scope_state)
            )
            final_usage = usage.model_copy(deep=True) if usage is not None else Usage()
            final_usage.wall_clock_ms += int((time.monotonic() - started) * 1_000)
            result = RunResult(
                run_id=manifest.run_id,
                agent_submission_status="completed",
                evaluation_status="completed",
                scope_compliant_success=task_accepted,
                official=False,
                verdicts=verdicts,
                usage=final_usage,
                submitted_patch_artifact_id=submitted_patch_artifact.artifact_id,
                verifier_results=results,
                safety_evidence=safety_evidence,
            )
            self.artifact_store.write_text_atomic(
                run_dir / "result.json",
                result.model_dump_json(indent=2),
            )
            evaluation_status = "completed"
            return result
        except BaseException as exc:
            failure_class = type(exc).__name__
            deadline_exhausted = isinstance(exc, ExecutionDeadlineExceeded) or bool(
                getattr(exc, "details", {}).get("deadline_exhausted", False)
            )
            raise
        finally:
            if not sandbox_policy_recorded:
                with suppress(Exception):
                    safety_evidence.append(
                        self._sandbox_policy_evidence(
                            manifest,
                            expected_checks,
                            recorded_checks,
                        )
                    )
            provenance = {
                "schema_version": "dev-evaluator-provenance-v1",
                "official": False,
                "evaluation_status": evaluation_status,
                "failure_class": failure_class,
                "deadline_exhausted": deadline_exhausted,
                "completed_check_results": [item.model_dump(mode="json") for item in results],
                "manifest_content_hash": manifest_hash,
                "task_content_hash": manifest.task_content_hash,
                "runtime_content_hash": manifest.runtime_content_hash,
                "model_hash": manifest.model_hash,
                "tool_surface_hash": manifest.tool_surface_hash,
                "sandbox_identity_hash": manifest.sandbox_identity_hash,
                "probe_image_digest": manifest.probe_image_digest,
                "probe_profile_hash": manifest.probe_profile_hash,
                "probe_execution_count": manifest.probe_execution_count,
                "probe_evidence_hashes": [item.content_hash for item in manifest.probe_evidence],
                "submitted_patch_content_hash": manifest.submitted_patch_content_hash,
                "applied_patch_hash": applied_patch_hash,
                "diff_hash": diff_hash,
                "changed_files": changed_files,
                "evaluator_workspace_separate": True,
                "execution_policy_hashes": sorted(
                    {
                        value
                        for item in recorded_checks
                        if isinstance(
                            value := item.result.details.get("execution_policy_hash"),
                            str,
                        )
                    }
                    | {
                        value
                        for item in safety_evidence
                        if item.details.get("kind") == "public_probe"
                        for value in item.details.get("execution_policy_hashes", [])
                    }
                ),
                "safety_evidence": [item.model_dump(mode="json") for item in safety_evidence],
            }
            self.artifact_store.write_text_atomic(
                run_dir / "provenance.json",
                json.dumps(provenance, indent=2, sort_keys=True),
            )
