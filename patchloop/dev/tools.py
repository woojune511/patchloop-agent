"""Constrained tools for ``dev-head`` with a single mutation contract."""

from __future__ import annotations

import fnmatch
import re
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from patchloop.contracts import PublicTask
from patchloop.dev.contracts import DevLimits, DevToolResult, MutationIntent, RequestedTool
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, PatchLoopError, RecoveryError
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.runner import Sandbox
from patchloop.util import ensure_within, safe_relative_path, sha256_bytes, sha256_json
from patchloop.verifier.policy import verify_scope

READ_TOOLS = frozenset({"search_files", "read_file"})
SINGLE_ACTION_TOOLS = frozenset({"apply_patch", "run_check", "finish_task"})
ALL_DEV_TOOLS = READ_TOOLS | SINGLE_ACTION_TOOLS
_PATCH_PATH = re.compile(r"^diff --git a/(.+) b/(.+)$", re.MULTILINE)


def dev_tool_schemas(*, finish_enabled: bool) -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = [
        {
            "type": "function",
            "name": "search_files",
            "description": (
                "Search tracked public repository text and return bounded evidence spans."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "path_glob": {"type": "string", "default": "**/*"},
                },
                "required": ["query", "path_glob"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "read_file",
            "description": "Read one bounded line range from a tracked public source file.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "start_line": {"type": "integer", "minimum": 1},
                    "end_line": {"type": "integer", "minimum": 1},
                },
                "required": ["path", "start_line", "end_line"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "run_check",
            "description": "Run exactly one public registered check against the current diff.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {"check_id": {"type": "string", "minLength": 1}},
                "required": ["check_id"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "apply_patch",
            "description": (
                "Apply one scoped Git diff. The minimal plan, fresh evidence, and exact current "
                "source anchor are part of this mutation; there is no separate planning tool."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "patch": {"type": "string", "minLength": 1},
                    "hypothesis": {"type": "string", "minLength": 1},
                    "expected_behavior": {"type": "string", "minLength": 1},
                    "evidence_span_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 8,
                    },
                    "edit_anchor": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "minLength": 1},
                            "old_text": {"type": "string", "minLength": 1},
                            "occurrence": {"type": "integer", "minimum": 1},
                        },
                        "required": ["path", "old_text", "occurrence"],
                        "additionalProperties": False,
                    },
                    "falsified_prior_hypothesis": {"type": ["string", "null"]},
                    "alternative_mechanism": {"type": ["string", "null"]},
                },
                "required": [
                    "patch",
                    "hypothesis",
                    "expected_behavior",
                    "evidence_span_ids",
                    "edit_anchor",
                    "falsified_prior_hypothesis",
                    "alternative_mechanism",
                ],
                "additionalProperties": False,
            },
        },
    ]
    if finish_enabled:
        schemas.append(
            {
                "type": "function",
                "name": "finish_task",
                "description": (
                    "Submit the automatically projected current diff after all checks pass."
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
            }
        )
    return schemas


def validate_tool_batch(calls: list[RequestedTool], *, max_parallel_reads: int = 4) -> str:
    """Return ``parallel_read`` or ``single_action``; reject every mixed shape."""

    if not calls:
        raise ContractError("model response must request at least one tool")
    names = [call.name for call in calls]
    action_ids = [call.action_id for call in calls]
    if len(action_ids) != len(set(action_ids)):
        raise ContractError("one model response cannot reuse an action ID")
    if any(name not in ALL_DEV_TOOLS for name in names):
        raise ContractError("model response requested an unknown dev-head tool")
    if all(name in READ_TOOLS for name in names):
        if len(calls) > max_parallel_reads:
            raise ContractError(f"a read batch may contain at most {max_parallel_reads} calls")
        return "parallel_read"
    if len(calls) == 1 and names[0] in SINGLE_ACTION_TOOLS:
        return "single_action"
    raise ContractError(
        "a response must contain only up to four reads/searches or exactly one action"
    )


class DevToolGateway:
    def __init__(
        self,
        *,
        workspace: Path,
        public_task: PublicTask,
        sandbox: Sandbox,
        journal: DevJournal,
        limits: DevLimits,
    ) -> None:
        self.workspace = workspace.resolve()
        self.public_task = public_task
        self.sandbox = sandbox
        self.journal = journal
        self.limits = limits
        self._lock = threading.RLock()
        self.spans: dict[str, dict[str, Any]] = {}
        self.checks_by_diff: dict[str, dict[str, dict[str, Any]]] = {}
        self.failure_diffs: dict[str, set[str]] = {}
        self.requires_alternative = False
        self.accepted_mutations = 0
        self.last_successful_mutation: dict[str, Any] | None = None
        self._hydrate()

    def _hydrate(self) -> None:
        for event in self.journal.events():
            if event["event_type"] != "action_finished":
                continue
            result = DevToolResult.model_validate(event["payload"]["result"])
            if result.status != "succeeded":
                continue
            if result.tool in READ_TOOLS:
                for span in result.output.get("spans", []):
                    if isinstance(span, dict) and isinstance(span.get("span_id"), str):
                        self.spans[span["span_id"]] = span
            elif result.tool == "apply_patch":
                self.accepted_mutations += 1
                self.last_successful_mutation = result.output.get("mutation")
                if result.output.get("alternative_requirement_satisfied") is True:
                    self.requires_alternative = False
            elif result.tool == "run_check":
                self._remember_check(result.output)

    @property
    def current_diff(self):
        return WorkspaceManager.diff_summary(self.workspace)

    @property
    def current_diff_hash(self) -> str:
        return self.current_diff.patch_hash

    def visible_checks_pass(self) -> bool:
        expected = {check.id for check in self.public_task.visible_checks}
        if not expected:
            return bool(self.current_diff.patch)
        rows = self.checks_by_diff.get(self.current_diff_hash, {})
        return expected == {check_id for check_id, row in rows.items() if row.get("passed") is True}

    def execute_batch(self, calls: list[RequestedTool]) -> list[DevToolResult]:
        shape = validate_tool_batch(calls, max_parallel_reads=self.limits.max_parallel_reads)
        if shape == "single_action":
            return [self.execute(calls[0])]
        with ThreadPoolExecutor(max_workers=len(calls), thread_name_prefix="dev-read") as pool:
            futures = [pool.submit(self.execute, call) for call in calls]
            return [future.result() for future in futures]

    def execute(self, call: RequestedTool) -> DevToolResult:
        input_hash = sha256_json({"tool": call.name, "arguments": call.arguments})
        replay = self.journal.action_result(call.action_id, input_hash)
        if replay is not None:
            return replay
        pending = self.journal.pending_action(call.action_id, input_hash)
        baseline = self.current_diff_hash
        preflight_error: Exception | None = None
        mutation_admitted: bool | None = None
        if pending is None:
            if call.name == "apply_patch":
                try:
                    self._validate_intent(call.arguments)
                    mutation_admitted = True
                except (PatchLoopError, ValidationError, ValueError, OSError) as exc:
                    preflight_error = exc
                    mutation_admitted = False
            self.journal.append(
                "action_started",
                {
                    "action_id": call.action_id,
                    "input_hash": input_hash,
                    "tool": call.name,
                    "arguments": call.arguments,
                    "baseline_diff_hash": baseline,
                    "mutation_admitted": mutation_admitted,
                },
            )
        try:
            if preflight_error is not None:
                raise preflight_error
            if pending is not None and call.name == "apply_patch":
                output = self._reconcile_or_apply(call.arguments, pending)
            else:
                output = self._perform(call.name, call.arguments)
            result = DevToolResult(
                action_id=call.action_id,
                input_hash=input_hash,
                tool=call.name,
                status="succeeded",
                output=output,
            )
        except (PatchLoopError, ValidationError, ValueError, OSError, RuntimeError) as exc:
            code = exc.code if isinstance(exc, PatchLoopError) else "TOOL_CONTRACT_ERROR"
            result = DevToolResult(
                action_id=call.action_id,
                input_hash=input_hash,
                tool=call.name,
                status="failed",
                error_code=code,
                message=str(exc)[:1_000],
            )
        self.journal.append(
            "action_finished",
            {
                "action_id": call.action_id,
                "input_hash": input_hash,
                "result": result.model_dump(mode="json"),
            },
        )
        if result.status == "succeeded":
            if result.tool in READ_TOOLS:
                with self._lock:
                    for span in result.output.get("spans", []):
                        self.spans[span["span_id"]] = span
            elif result.tool == "apply_patch":
                self.accepted_mutations += 1
                self.last_successful_mutation = result.output["mutation"]
                if result.output.get("alternative_requirement_satisfied") is True:
                    self.requires_alternative = False
            elif result.tool == "run_check":
                self._remember_check(result.output)
        return result

    def _perform(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "read_file":
            return self._read_file(**arguments)
        if name == "search_files":
            return self._search_files(**arguments)
        if name == "apply_patch":
            return self._apply_patch(arguments)
        if name == "run_check":
            return self._run_check(**arguments)
        if name == "finish_task":
            return self._finish_task(arguments)
        raise ContractError(f"unknown dev-head tool: {name}")

    def _tracked_path(self, relative: str) -> tuple[str, Path]:
        normalized = safe_relative_path(relative)
        if normalized.startswith(".patchloop-hidden/"):
            raise ContractError("private evaluator paths are never agent-readable")
        path = ensure_within(self.workspace, normalized)
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", normalized],
            cwd=self.workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        if tracked.returncode != 0 or not path.is_file() or path.is_symlink():
            raise ContractError(f"path is not a tracked public file: {normalized}")
        return normalized, path

    @staticmethod
    def _span(path: str, start: int, end: int, content: str, file_hash: str) -> dict[str, Any]:
        identity = {
            "path": path,
            "start_line": start,
            "end_line": end,
            "content": content,
            "file_hash": file_hash,
        }
        return {"span_id": f"span_{sha256_json(identity).split(':', 1)[1][:16]}", **identity}

    def _read_file(self, path: str, start_line: int, end_line: int) -> dict[str, Any]:
        if type(start_line) is not int or type(end_line) is not int:
            raise ContractError("read_file line bounds must be integers")
        if start_line < 1 or end_line < start_line or end_line - start_line + 1 > 400:
            raise ContractError("read_file accepts a 1-400 line inclusive range")
        normalized, selected = self._tracked_path(path)
        raw = selected.read_bytes()
        if len(raw) > 2_000_000:
            raise ContractError("read_file refuses files larger than 2 MB")
        text = raw.decode("utf-8")
        lines = text.splitlines()
        actual_end = min(end_line, len(lines))
        content = "\n".join(lines[start_line - 1 : actual_end])
        span = self._span(normalized, start_line, actual_end, content[:24_000], sha256_bytes(raw))
        return {"spans": [span], "line_count": len(lines)}

    def _search_files(self, query: str, path_glob: str = "**/*") -> dict[str, Any]:
        if not isinstance(query, str) or not query or len(query) > 500:
            raise ContractError("search query must contain 1-500 characters")
        pattern = safe_relative_path(path_glob, field_name="search path_glob")
        spans: list[dict[str, Any]] = []
        for selected in sorted(self.workspace.rglob("*")):
            if len(spans) >= 20 or not selected.is_file() or selected.is_symlink():
                continue
            relative = selected.relative_to(self.workspace).as_posix()
            if ".git" in selected.relative_to(self.workspace).parts:
                continue
            if relative.startswith(".patchloop-hidden/") or not fnmatch.fnmatchcase(
                relative, pattern
            ):
                continue
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", "--", relative],
                cwd=self.workspace,
                capture_output=True,
                check=False,
            )
            if tracked.returncode != 0 or selected.stat().st_size > 1_000_000:
                continue
            try:
                raw = selected.read_bytes()
                text = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            lines = text.splitlines()
            for index, line in enumerate(lines, start=1):
                if query not in line:
                    continue
                start = max(1, index - 2)
                end = min(len(lines), index + 2)
                content = "\n".join(lines[start - 1 : end])
                spans.append(self._span(relative, start, end, content, sha256_bytes(raw)))
                if len(spans) >= 20:
                    break
        return {"query": query, "spans": spans, "truncated": len(spans) >= 20}

    def _patch_paths(self, patch: str) -> list[str]:
        if not isinstance(patch, str) or not patch.startswith("diff --git "):
            raise ContractError("apply_patch requires a raw Git unified diff")
        matches = _PATCH_PATH.findall(patch)
        if not matches:
            raise ContractError("apply_patch has no Git diff header")
        paths: list[str] = []
        for before, after in matches:
            if before != after:
                raise ContractError("renames and copies are not allowed")
            paths.append(safe_relative_path(after, field_name="patch path"))
        return sorted(set(paths))

    def _path_allowed(self, path: str) -> bool:
        constraints = self.public_task.constraints
        return any(
            fnmatch.fnmatchcase(path, item) for item in constraints.allowed_paths
        ) and not any(fnmatch.fnmatchcase(path, item) for item in constraints.forbidden_paths)

    def _validate_intent(self, arguments: dict[str, Any]) -> tuple[str, MutationIntent, list[str]]:
        patch = arguments.get("patch")
        if not isinstance(patch, str):
            raise ContractError("apply_patch patch must be a string")
        intent = MutationIntent.model_validate(
            {key: value for key, value in arguments.items() if key != "patch"}
        )
        if self.requires_alternative and (
            intent.falsified_prior_hypothesis is None or intent.alternative_mechanism is None
        ):
            raise ContractError(
                "repeated public failure across two diffs requires falsified_prior_hypothesis "
                "and alternative_mechanism on the next mutation"
            )
        paths = self._patch_paths(patch)
        if any(not self._path_allowed(path) for path in paths):
            raise ContractError("patch changes a path outside the public task allowance")
        anchor_path, anchor_file = self._tracked_path(intent.edit_anchor.path)
        if anchor_path not in paths:
            raise ContractError("exact edit anchor must belong to a patched file")
        anchor_text = anchor_file.read_text(encoding="utf-8")
        positions = [
            match.start()
            for match in re.finditer(re.escape(intent.edit_anchor.old_text), anchor_text)
        ]
        if len(positions) < intent.edit_anchor.occurrence:
            raise ContractError("exact edit anchor is stale or absent from the current source")
        evidence = []
        with self._lock:
            for span_id in intent.evidence_span_ids:
                span = self.spans.get(span_id)
                if span is None:
                    raise ContractError(f"unknown evidence span: {span_id}")
                _, current = self._tracked_path(span["path"])
                if sha256_bytes(current.read_bytes()) != span["file_hash"]:
                    raise ContractError(f"evidence span is stale: {span_id}")
                evidence.append(span)
        if anchor_path not in {span["path"] for span in evidence}:
            raise ContractError(
                "at least one current evidence span must cover the edit-anchor file"
            )
        return patch, intent, paths

    def _run_git_apply(self, patch: str, *extra: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", "apply", "--whitespace=nowarn", *extra, "-"],
            cwd=self.workspace,
            input=patch.encode("utf-8"),
            capture_output=True,
            check=False,
        )

    @staticmethod
    def _git_apply_error(result: subprocess.CompletedProcess[bytes]) -> str:
        return result.stderr.decode("utf-8", errors="replace").strip()[:800]

    def _apply_patch(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.accepted_mutations >= self.limits.max_accepted_mutations:
            raise ContractError("accepted mutation limit reached")
        patch, intent, paths = self._validate_intent(arguments)
        checked = self._run_git_apply(patch, "--check")
        if checked.returncode != 0:
            raise ContractError(f"git apply check failed: {self._git_apply_error(checked)}")
        applied = self._run_git_apply(patch)
        if applied.returncode != 0:
            raise ContractError(f"git apply failed: {self._git_apply_error(applied)}")
        summary = self.current_diff
        scope = verify_scope(summary, self.public_task.constraints)
        if not scope.passed:
            reverted = self._run_git_apply(patch, "--reverse")
            if reverted.returncode != 0:
                raise RecoveryError("out-of-scope mutation could not be rolled back safely")
            raise ContractError("mutation violates allowed paths or diff-size constraints")
        mutation = {
            "hypothesis": intent.hypothesis,
            "expected_behavior": intent.expected_behavior,
            "evidence_span_ids": intent.evidence_span_ids,
            "edit_anchor": intent.edit_anchor.model_dump(mode="json"),
            "falsified_prior_hypothesis": intent.falsified_prior_hypothesis,
            "alternative_mechanism": intent.alternative_mechanism,
            "changed_files": summary.changed_files,
            "diff_hash": summary.patch_hash,
        }
        return {
            "patch_hash": sha256_bytes(patch.encode("utf-8")),
            "worktree_diff_hash": summary.patch_hash,
            "changed_files": paths,
            "mutation": mutation,
            "alternative_requirement_satisfied": self.requires_alternative,
        }

    def _reconcile_or_apply(
        self, arguments: dict[str, Any], pending: dict[str, Any]
    ) -> dict[str, Any]:
        baseline = pending.get("baseline_diff_hash")
        current = self.current_diff_hash
        if current == baseline:
            return self._apply_patch(arguments)
        if pending.get("mutation_admitted") is not True:
            raise RecoveryError("pending mutation was not admitted before the crash")
        patch = arguments.get("patch")
        if not isinstance(patch, str):
            raise RecoveryError("pending mutation patch is invalid")
        intent = MutationIntent.model_validate(
            {key: value for key, value in arguments.items() if key != "patch"}
        )
        paths = self._patch_paths(patch)
        reverse_check = self._run_git_apply(patch, "--reverse", "--check")
        if reverse_check.returncode != 0:
            raise RecoveryError("pending mutation cannot be reconciled with the current workspace")
        summary = self.current_diff
        mutation = {
            "hypothesis": intent.hypothesis,
            "expected_behavior": intent.expected_behavior,
            "evidence_span_ids": intent.evidence_span_ids,
            "edit_anchor": intent.edit_anchor.model_dump(mode="json"),
            "falsified_prior_hypothesis": intent.falsified_prior_hypothesis,
            "alternative_mechanism": intent.alternative_mechanism,
            "changed_files": summary.changed_files,
            "diff_hash": summary.patch_hash,
        }
        return {
            "patch_hash": sha256_bytes(patch.encode("utf-8")),
            "worktree_diff_hash": summary.patch_hash,
            "changed_files": paths,
            "mutation": mutation,
            "recovered_after_crash": True,
            "alternative_requirement_satisfied": self.requires_alternative,
        }

    def _run_check(self, check_id: str) -> dict[str, Any]:
        checks = {check.id: check for check in self.public_task.visible_checks}
        try:
            check = checks[check_id]
        except KeyError as exc:
            raise ContractError(f"unknown public check: {check_id}") from exc
        diff_hash = self.current_diff_hash
        outcome = self.sandbox.run_check(self.workspace, check)
        passed = not outcome.timed_out and outcome.exit_code in check.expected_exit_codes
        signature = sha256_json(
            {
                "check_id": check_id,
                "exit_code": outcome.exit_code,
                "timed_out": outcome.timed_out,
                "stdout": outcome.stdout[-8_000:],
                "stderr": outcome.stderr[-8_000:],
            }
        )
        return {
            "check_id": check_id,
            "diff_hash": diff_hash,
            "passed": passed,
            "failure_signature": None if passed else signature,
            "exit_code": outcome.exit_code,
            "timed_out": outcome.timed_out,
            "truncated": outcome.truncated,
            "stdout": outcome.stdout[-12_000:],
            "stderr": outcome.stderr[-12_000:],
        }

    def _remember_check(self, output: dict[str, Any]) -> None:
        diff_hash = str(output["diff_hash"])
        check_id = str(output["check_id"])
        self.checks_by_diff.setdefault(diff_hash, {})[check_id] = output
        signature = output.get("failure_signature")
        if isinstance(signature, str):
            diffs = self.failure_diffs.setdefault(signature, set())
            diffs.add(diff_hash)
            if len(diffs) >= 2:
                self.requires_alternative = True

    def _finish_task(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if arguments:
            raise ContractError("finish_task accepts no arguments")
        summary = self.current_diff
        if not summary.patch:
            raise ContractError("cannot submit an empty diff")
        if not self.visible_checks_pass():
            raise ContractError("all visible checks must pass against the current diff")
        return {
            "patch": summary.patch,
            "patch_hash": summary.patch_hash,
            "changed_files": summary.changed_files,
            "added_lines": summary.added_lines,
            "deleted_lines": summary.deleted_lines,
        }
