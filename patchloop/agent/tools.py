"""Constrained, evidence-producing tool gateway."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import EventType, PublicTask, ToolResult
from patchloop.errors import ContractError, PolicyViolation, RecoveryError
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.runner import Sandbox
from patchloop.state import StateStore
from patchloop.util import (
    canonical_json,
    ensure_within,
    safe_relative_path,
    sha256_text,
    utc_now,
)
from patchloop.verifier.policy import (
    verify_dependencies,
    verify_public_api,
    verify_scope,
    verify_test_tampering,
)

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "search_files",
        "description": "Search repository text files for a literal query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path_glob": {"type": "string", "default": "**/*"},
            },
            "required": ["query", "path_glob"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read a bounded range from a repository file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
            },
            "required": ["path", "start_line", "end_line"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "apply_patch",
        "description": (
            "Apply a raw Git unified diff to existing tracked text files within "
            "the task's allowed paths. New files, renames, copies, and binary "
            "patches are not supported. "
            "The patch must begin with 'diff --git' and contain ---/+++/@@ lines. "
            "Do not use '*** Begin Patch' or '*** End Patch' markers."
        ),
        "parameters": {
            "type": "object",
            "properties": {"patch": {"type": "string"}},
            "required": ["patch"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "run_check",
        "description": "Run one task-registered public check by ID.",
        "parameters": {
            "type": "object",
            "properties": {"check_id": {"type": "string"}},
            "required": ["check_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_diff",
        "description": "Return the current Git diff and size summary.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "strict": True,
    },
]

_EVENT_ERROR_MESSAGE_LIMIT = 2_000
_UNSUPPORTED_PATCH_METADATA = (
    "new file mode ",
    "rename from ",
    "rename to ",
    "copy from ",
    "copy to ",
)


def _header_path(header: str) -> str:
    path = header[4:].split("\t", 1)[0]
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


def _validate_raw_git_patch(patch: str) -> None:
    if "\x00" in patch or "GIT binary patch" in patch or "Binary files " in patch:
        raise ContractError("apply_patch accepts text patches only; binary patches are forbidden")
    if not patch.lstrip().startswith("diff --git "):
        raise ContractError(
            "apply_patch requires a raw Git unified diff beginning with "
            "'diff --git'; do not use '*** Begin Patch' markers"
        )

    sections: list[list[str]] = []
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            sections.append([line])
        elif sections:
            sections[-1].append(line)
        elif line.strip():
            raise ContractError("apply_patch does not allow content before the first diff header")

    for section in sections:
        if any(
            line.startswith(_UNSUPPORTED_PATCH_METADATA)
            for line in section
        ):
            raise ContractError(
                "apply_patch only supports in-place tracked text changes; "
                "new files, renames, and copies are forbidden"
            )
        old_header = next(
            (index for index, line in enumerate(section) if line.startswith("--- ")),
            None,
        )
        new_header = next(
            (index for index, line in enumerate(section) if line.startswith("+++ ")),
            None,
        )
        hunk_header = next(
            (index for index, line in enumerate(section) if line.startswith("@@ ")),
            None,
        )
        if (
            old_header is None
            or new_header is None
            or hunk_header is None
            or not old_header < new_header < hunk_header
        ):
            raise ContractError(
                "each diff section must contain ordered '---', '+++', and '@@' "
                "headers; binary and metadata-only patches are forbidden"
            )
        old_path = _header_path(section[old_header])
        new_path = _header_path(section[new_header])
        if old_path == "/dev/null":
            raise ContractError(
                "apply_patch only supports tracked files; new-file patches are forbidden"
            )
        if new_path != "/dev/null" and old_path != new_path:
            raise ContractError(
                "apply_patch only supports in-place changes; "
                "rename and copy patches are forbidden"
            )


class ToolGateway:
    def __init__(
        self,
        *,
        run_id: str,
        workspace: Path,
        task: PublicTask,
        state: StateStore,
        artifacts: ArtifactStore,
        sandbox: Sandbox,
    ) -> None:
        self.run_id = run_id
        self.workspace = workspace
        self.task = task
        self.state = state
        self.artifacts = artifacts
        self.sandbox = sandbox

    def execute(self, name: str, action_id: str, arguments: dict[str, Any]) -> ToolResult:
        input_hash = sha256_text(canonical_json({"tool": name, "input": arguments}))
        prior = self.state.get_action_result(self.run_id, action_id, input_hash)
        if prior is not None:
            self.state.append_event(
                self.run_id,
                EventType.TOOL_SUCCEEDED if prior.status == "succeeded" else EventType.TOOL_FAILED,
                actor="idempotency-store",
                correlation_id=action_id,
                payload={
                    "tool": name,
                    "status": prior.status,
                    "artifact_id": prior.output.get("artifact_id"),
                    "artifact_path": prior.output.get("artifact_path"),
                    "replayed": True,
                    "error_code": prior.error_code,
                    "error_message": (
                        prior.error_message[:_EVENT_ERROR_MESSAGE_LIMIT]
                        if prior.error_message
                        else None
                    ),
                    "duration_ms": 0,
                },
            )
            prior.output = {**prior.output, "replayed": True}
            return prior
        started = utc_now()
        self.state.append_event(
            self.run_id,
            EventType.TOOL_CALLED,
            actor="agent",
            correlation_id=action_id,
            payload={"tool": name, "input_hash": input_hash},
        )
        try:
            output = self._dispatch(name, arguments)
            artifact = self.artifacts.put_json(output)
            result = ToolResult(
                action_id=action_id,
                status="succeeded",
                started_at=started,
                finished_at=utc_now(),
                output={
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                    **output,
                },
            )
            event_type = EventType.TOOL_SUCCEEDED
        except (ContractError, PolicyViolation, TypeError, ValueError) as exc:
            error_payload = {
                "tool": name,
                "status": "rejected",
                "error_code": getattr(exc, "code", "INVALID_TOOL_INPUT"),
                "error_message": str(exc),
            }
            artifact = self.artifacts.put_json(error_payload)
            result = ToolResult(
                action_id=action_id,
                status="rejected",
                started_at=started,
                finished_at=utc_now(),
                output={
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                },
                error_code=getattr(exc, "code", "INVALID_TOOL_INPUT"),
                error_message=str(exc),
            )
            event_type = EventType.TOOL_FAILED
        self.state.record_action_result(self.run_id, action_id, input_hash, result)
        self.state.append_event(
            self.run_id,
            event_type,
            actor="tool-gateway",
            correlation_id=action_id,
            payload={
                "tool": name,
                "status": result.status,
                "artifact_id": result.output.get("artifact_id"),
                "artifact_path": result.output.get("artifact_path"),
                "error_code": result.error_code,
                "error_message": (
                    result.error_message[:_EVENT_ERROR_MESSAGE_LIMIT]
                    if result.error_message
                    else None
                ),
                "check_id": result.output.get("check_id"),
                "passed": result.output.get("passed"),
                "timed_out": result.output.get("timed_out"),
                "duration_ms": int((result.finished_at - result.started_at).total_seconds() * 1000),
            },
        )
        if name == "apply_patch" and result.status == "succeeded":
            self.state.append_event(
                self.run_id,
                EventType.PATCH_APPLIED,
                actor="tool-gateway",
                correlation_id=action_id,
                payload={"patch_hash": output["patch_hash"]},
            )
        return result

    def _dispatch(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "read_file":
            return self._read_file(**arguments)
        if name == "search_files":
            return self._search_files(**arguments)
        if name == "apply_patch":
            return self._apply_patch(**arguments)
        if name == "run_check":
            return self._run_check(**arguments)
        if name == "get_diff":
            return self._get_diff()
        raise ContractError(f"unknown tool: {name}")

    def _read_file(self, path: str, start_line: int, end_line: int) -> dict[str, Any]:
        if end_line < start_line or end_line - start_line > 500:
            raise ContractError("read_file range must contain at most 501 ordered lines")
        target = ensure_within(self.workspace, path)
        if not target.is_file():
            raise ContractError(f"file does not exist: {path}")
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        content = "\n".join(lines[start_line - 1 : end_line])
        return {"path": path, "start_line": start_line, "end_line": end_line, "content": content}

    def _search_files(self, query: str, path_glob: str = "**/*") -> dict[str, Any]:
        if not query or len(query) > 500:
            raise ContractError("search query must contain 1-500 characters")
        safe_relative_path(path_glob, field_name="path_glob")
        matches: list[dict[str, Any]] = []
        for path in self.workspace.glob(path_glob):
            if not path.is_file() or ".git" in path.parts:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for line_number, line in enumerate(lines, 1):
                if query in line:
                    matches.append(
                        {
                            "path": path.relative_to(self.workspace).as_posix(),
                            "line": line_number,
                            "text": line[:500],
                        }
                    )
                    if len(matches) >= 100:
                        return {"query": query, "matches": matches, "truncated": True}
        return {"query": query, "matches": matches, "truncated": False}

    def _apply_patch(self, patch: str) -> dict[str, Any]:
        if len(patch.encode("utf-8")) > 500_000:
            raise PolicyViolation("patch exceeds the tool input limit")
        _validate_raw_git_patch(patch)
        baseline = WorkspaceManager.diff_summary(self.workspace)
        baseline_untracked = WorkspaceManager.untracked_files(self.workspace)
        if baseline_untracked:
            raise RecoveryError(
                "agent workspace contains untracked files before patch application"
            )
        completed = subprocess.run(
            ["git", "apply", "--recount", "--whitespace=nowarn", "-"],
            cwd=self.workspace,
            input=patch.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            error = completed.stderr.decode("utf-8", errors="replace").strip()
            raise ContractError(f"patch application failed: {error}")
        try:
            summary = WorkspaceManager.diff_summary(self.workspace)
            outcomes = [
                verify_scope(summary, self.task.constraints),
                verify_dependencies(summary, self.task.constraints),
                verify_test_tampering(summary),
                verify_public_api(summary, self.task.constraints, self.workspace),
            ]
            violations = [
                item for outcome in outcomes for item in outcome.violations
            ]
            untracked = WorkspaceManager.untracked_files(self.workspace)
            if untracked:
                violations.append(
                    "patch produced untracked files: " + ", ".join(untracked)
                )
        except Exception:
            self._rollback_patch(patch, baseline.patch_hash)
            raise
        if violations:
            self._rollback_patch(patch, baseline.patch_hash)
            raise PolicyViolation("; ".join(violations))
        return {
            "patch_hash": sha256_text(patch),
            "worktree_diff_hash": summary.patch_hash,
            "changed_files": summary.changed_files,
            "diff_lines": summary.diff_lines,
        }

    def _rollback_patch(self, patch: str, baseline_diff_hash: str) -> None:
        rollback = subprocess.run(
            [
                "git",
                "apply",
                "--reverse",
                "--recount",
                "--whitespace=nowarn",
                "-",
            ],
            cwd=self.workspace,
            input=patch.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        if rollback.returncode != 0:
            error = rollback.stderr.decode("utf-8", errors="replace").strip()
            raise RecoveryError(f"policy rollback failed: {error}")
        try:
            restored = WorkspaceManager.diff_summary(self.workspace)
            untracked = WorkspaceManager.untracked_files(self.workspace)
        except Exception as exc:
            raise RecoveryError(
                "policy rollback state could not be verified"
            ) from exc
        if restored.patch_hash != baseline_diff_hash or untracked:
            raise RecoveryError(
                "policy rollback did not restore the pre-call workspace state"
            )

    def _run_check(self, check_id: str) -> dict[str, Any]:
        checks = {check.id: check for check in self.task.visible_checks}
        if check_id not in checks:
            raise PolicyViolation(f"unregistered check: {check_id}")
        repeated_timeout = any(
            event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "run_check"
            and event.payload.get("check_id") == check_id
            and event.payload.get("timed_out") is True
            for event in self.state.list_events(self.run_id)
        )
        if repeated_timeout:
            raise PolicyViolation(
                "loop detector rejected an unchanged check after timeout; use a targeted check"
            )
        outcome = self.sandbox.run_check(self.workspace, checks[check_id])
        return {
            "check_id": check_id,
            "exit_code": outcome.exit_code,
            "passed": not outcome.timed_out
            and outcome.exit_code in checks[check_id].expected_exit_codes,
            "timed_out": outcome.timed_out,
            "truncated": outcome.truncated,
            "stdout": outcome.stdout,
            "stderr": outcome.stderr,
        }

    def _get_diff(self) -> dict[str, Any]:
        summary = WorkspaceManager.diff_summary(self.workspace)
        return {
            "patch": summary.patch,
            "patch_hash": summary.patch_hash,
            "changed_files": summary.changed_files,
            "added_lines": summary.added_lines,
            "deleted_lines": summary.deleted_lines,
        }
