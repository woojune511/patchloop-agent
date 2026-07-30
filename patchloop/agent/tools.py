"""Constrained, evidence-producing tool gateway."""

from __future__ import annotations

import copy
import json
import os
import re
import stat
import subprocess
import tempfile
import uuid
from pathlib import Path, PurePosixPath
from typing import Any

from patchloop.agent.investigation import (
    INSPECTION_ADMISSION_PREFLIGHT_SCHEMA,
    INVESTIGATION_LOOP_SCHEMA,
    INVESTIGATION_POLICY_VERSION,
    TOOL_REPLAY_SCHEMA,
    investigation_policy_version,
    load_inspection_records,
    mutation_epoch,
    nominal_tail_reserve,
    prior_search_match_keys,
    read_coverage,
    reconstruct_covered_read,
    search_match_key,
    tail_policy,
    tool_admission_schema,
    validate_inspection_arguments,
)
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    Checkpoint,
    EventType,
    FaultSpec,
    PublicTask,
    ToolResult,
)
from patchloop.errors import (
    ContractError,
    ControlledDiagnosticRejection,
    PolicyViolation,
    RecoveryError,
)
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

TOOL_SCHEMAS_V1: list[dict[str, Any]] = [
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

TOOL_SCHEMAS_V2: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V1)
next(
    item for item in TOOL_SCHEMAS_V2 if item["name"] == "run_check"
)["description"] = (
    "Run one task-registered public check by ID. A passing result is valid only "
    "for the exact current worktree diff; any later patch requires another check."
)
next(
    item for item in TOOL_SCHEMAS_V2 if item["name"] == "get_diff"
)["description"] = (
    "Return the current Git diff and size summary. Call this after all registered "
    "checks pass for the current diff so the next turn can perform final review."
)
TOOL_SCHEMAS_V2.append(
    {
        "type": "function",
        "name": "finish_task",
        "description": (
            "Submit the current patch for deterministic evaluation. Call only "
            "after every registered check passes for the current diff and the "
            "complete final get_diff result has been reviewed in this turn."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "strict": True,
    }
)
TOOL_SCHEMAS = TOOL_SCHEMAS_V2

_EVENT_ERROR_MESSAGE_LIMIT = 2_000
_INVESTIGATION_CONTEXT_POLICIES = {
    "phase-evidence-v4",
    "phase-evidence-v5",
}
_UNSUPPORTED_PATCH_METADATA = (
    "new file mode ",
    "old mode ",
    "new mode ",
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


def _patch_contract_error(
    message: str,
    *,
    reason: str,
    stage: str = "format",
    line: int | None = None,
) -> ContractError:
    details: dict[str, Any] = {
        "stage": stage,
        "reason": reason,
        "guidance": (
            "Regenerate a raw Git unified diff against the current file content, "
            "then retry with a new action_id."
        ),
    }
    if line is not None:
        details["line"] = line
    return ContractError(message, details=details)


def _validate_raw_git_patch(patch: str) -> None:
    if "\x00" in patch or "GIT binary patch" in patch or "Binary files " in patch:
        raise _patch_contract_error(
            "apply_patch accepts text patches only; binary patches are forbidden",
            reason="binary_patch",
        )
    if not patch.lstrip().startswith("diff --git "):
        raise _patch_contract_error(
            "apply_patch requires a raw Git unified diff beginning with "
            "'diff --git'; do not use '*** Begin Patch' markers",
            reason="invalid_envelope",
        )

    sections: list[list[str]] = []
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            sections.append([line])
        elif sections:
            sections[-1].append(line)
        elif line.strip():
            raise _patch_contract_error(
                "apply_patch does not allow content before the first diff header",
                reason="content_before_header",
            )

    for section in sections:
        if any(
            line.startswith(_UNSUPPORTED_PATCH_METADATA)
            for line in section
        ):
            raise _patch_contract_error(
                "apply_patch only supports in-place tracked text changes; "
                "new files, mode/symlink changes, renames, and copies "
                "are forbidden",
                reason="unsupported_metadata",
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
            raise _patch_contract_error(
                "each diff section must contain ordered '---', '+++', and '@@' "
                "headers; binary and metadata-only patches are forbidden",
                reason="missing_ordered_headers",
            )
        old_path = _header_path(section[old_header])
        new_path = _header_path(section[new_header])
        if old_path == "/dev/null":
            raise _patch_contract_error(
                "apply_patch only supports tracked files; new-file patches are forbidden",
                reason="new_file",
            )
        if new_path != "/dev/null" and old_path != new_path:
            raise _patch_contract_error(
                "apply_patch only supports in-place changes; "
                "rename and copy patches are forbidden",
                reason="path_change",
            )


def _patch_paths(patch: str) -> list[str]:
    paths: list[str] = []
    sections: list[list[str]] = []
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            sections.append([line])
        elif sections:
            sections[-1].append(line)
    for section in sections:
        old_header = next(line for line in section if line.startswith("--- "))
        path = safe_relative_path(
            _header_path(old_header),
            field_name="patch path",
        )
        if path in paths:
            raise _patch_contract_error(
                f"patch contains duplicate file section: {path}",
                reason="duplicate_file_section",
            )
        paths.append(path)
    return paths


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
        tool_schema_version: str = "v2",
        context_policy_version: str = "phase-evidence-v3",
        fault: FaultSpec | None = None,
    ) -> None:
        self.run_id = run_id
        self.workspace = workspace
        self.task = task
        self.state = state
        self.artifacts = artifacts
        self.sandbox = sandbox
        self.tool_schema_version = tool_schema_version
        self.context_policy_version = context_policy_version
        self.fault = fault or FaultSpec()

    def execute(self, name: str, action_id: str, arguments: dict[str, Any]) -> ToolResult:
        input_hash = sha256_text(canonical_json({"tool": name, "input": arguments}))
        prior = self.state.get_action_result(self.run_id, action_id, input_hash)
        if prior is not None:
            self.state.append_event(
                self.run_id,
                (
                    EventType.TOOL_REPLAYED
                    if self.tool_schema_version == "v2"
                    else (
                        EventType.TOOL_SUCCEEDED
                        if prior.status == "succeeded"
                        else EventType.TOOL_FAILED
                    )
                ),
                actor="idempotency-store",
                correlation_id=action_id,
                payload={
                    "tool": name,
                    "status": prior.status,
                    "artifact_id": prior.output.get("artifact_id"),
                    "artifact_path": prior.output.get("artifact_path"),
                    "result_artifact": prior.output.get("result_artifact"),
                    "replayed": True,
                    "error_code": prior.error_code,
                    "error_message": (
                        prior.error_message[:_EVENT_ERROR_MESSAGE_LIMIT]
                        if prior.error_message
                        else None
                    ),
                    "check_id": prior.output.get("check_id"),
                    "passed": prior.output.get("passed"),
                    "timed_out": prior.output.get("timed_out"),
                    "worktree_diff_hash": prior.output.get("worktree_diff_hash"),
                    "duration_ms": 0,
                },
            )
            prior.output = {**prior.output, "replayed": True}
            return prior
        worktree_diff_hash = WorkspaceManager.diff_summary(
            self.workspace
        ).patch_hash
        normalized_call_hash = self._normalized_call_hash(
            name,
            arguments,
            worktree_diff_hash=worktree_diff_hash,
        )
        if (
            self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES
            and name in {"read_file", "search_files"}
            and self._inspection_short_circuit_eligible(
                name,
                arguments,
            )
        ):
            blocked = self._inspection_admission_block(
                name=name,
                action_id=action_id,
                arguments=arguments,
                input_hash=input_hash,
                normalized_call_hash=normalized_call_hash,
                worktree_diff_hash=worktree_diff_hash,
            )
            if blocked is not None:
                return blocked
            semantic_replay = self._semantic_inspection_replay(
                name=name,
                action_id=action_id,
                arguments=arguments,
                input_hash=input_hash,
                normalized_call_hash=normalized_call_hash,
                worktree_diff_hash=worktree_diff_hash,
            )
            if semantic_replay is not None:
                return semantic_replay
        prior_calls = [
            event
            for event in self.state.list_events(self.run_id)
            if event.type == EventType.TOOL_CALLED
        ]
        repeated_calls = 0
        for prior_call in reversed(prior_calls):
            if (
                prior_call.payload.get("normalized_call_hash")
                != normalized_call_hash
            ):
                break
            repeated_calls += 1
        if repeated_calls:
            self.state.append_event(
                self.run_id,
                EventType.LOOP_DETECTED,
                actor="tool-gateway",
                correlation_id=action_id,
                payload={
                    "tool": name,
                    "normalized_call_hash": normalized_call_hash,
                    "prior_call_sequence": prior_calls[-1].sequence,
                    "occurrences": repeated_calls + 1,
                    "enforcement": "advisory",
                },
            )
        started = utc_now()
        patch_artifact: Artifact | None = None
        input_artifact: Artifact | None = None
        if self.tool_schema_version == "v2" and name != "apply_patch":
            input_artifact = self.artifacts.put_json(
                {"tool": name, "input": arguments}
            )
        if (
            self.tool_schema_version == "v2"
            and name == "apply_patch"
            and isinstance(arguments.get("patch"), str)
        ):
            patch_artifact = self.artifacts.put_text(
                str(arguments["patch"]),
                media_type="text/x-diff",
            )
        call_payload: dict[str, Any] = {
            "tool": name,
            "input_hash": input_hash,
            "normalized_call_hash": normalized_call_hash,
        }
        if self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES:
            call_payload["worktree_diff_hash"] = worktree_diff_hash
            call_payload["execution"] = "dispatched"
        if input_artifact is not None:
            call_payload["input_artifact"] = input_artifact.model_dump(
                mode="json"
            )
        if patch_artifact is not None:
            call_payload["patch_artifact"] = patch_artifact.model_dump(mode="json")
            call_payload["artifact_id"] = patch_artifact.artifact_id
            call_payload["artifact_path"] = patch_artifact.path
        elif input_artifact is not None:
            call_payload["artifact_id"] = input_artifact.artifact_id
            call_payload["artifact_path"] = input_artifact.path
        self.state.append_event(
            self.run_id,
            EventType.TOOL_CALLED,
            actor="agent",
            correlation_id=action_id,
            payload=call_payload,
        )
        try:
            if (
                self.tool_schema_version == "v2"
                and name == "apply_patch"
                and patch_artifact is not None
            ):
                intent = self._prepare_patch_mutation(
                    action_id,
                    input_hash,
                    str(arguments["patch"]),
                    patch_artifact,
                )
                if self._controlled_rejection_pending():
                    raise self._controlled_rejection(
                        action_id=action_id,
                        input_hash=input_hash,
                        patch_artifact=patch_artifact,
                        intent=intent,
                    )
                output = self._apply_patch(
                    str(arguments["patch"]),
                    intent=intent,
                )
            else:
                output = self._dispatch(name, arguments)
            if (
                self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES
                and name in {"read_file", "search_files"}
            ):
                output = self._annotate_inspection_result(
                    name=name,
                    output=output,
                    worktree_diff_hash=worktree_diff_hash,
                )
            artifact = self.artifacts.put_json(output)
            result_artifact = (
                artifact.model_dump(mode="json")
                if self.context_policy_version
                in _INVESTIGATION_CONTEXT_POLICIES
                and name in {"read_file", "search_files"}
                else None
            )
            result = ToolResult(
                action_id=action_id,
                status="succeeded",
                started_at=started,
                finished_at=utc_now(),
                output={
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                    **(
                        {"result_artifact": result_artifact}
                        if result_artifact is not None
                        else {}
                    ),
                    **output,
                },
            )
        except (ContractError, PolicyViolation, TypeError, ValueError) as exc:
            result = self._error_result(
                name,
                action_id,
                started,
                exc,
                fatal=False,
            )
        except RecoveryError as exc:
            result = self._error_result(
                name,
                action_id,
                started,
                exc,
                fatal=True,
            )
        self._complete_result(name, input_hash, result)
        return result

    def _inspection_short_circuit_eligible(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> bool:
        """Validate inspection shape and paths before a no-dispatch outcome.

        Invalid requests continue through the ordinary ToolCalled/ToolFailed
        path so tail admission cannot hide a contract or path-policy attempt.
        """

        try:
            validate_inspection_arguments(
                self.workspace,
                name,
                arguments,
            )
            return True
        except ContractError:
            return False

    def _inspection_admission_block(
        self,
        *,
        name: str,
        action_id: str,
        arguments: dict[str, Any],
        input_hash: str,
        normalized_call_hash: str,
        worktree_diff_hash: str,
    ) -> ToolResult | None:
        events = self.state.list_events(self.run_id)
        manifest = self.state.get_manifest(self.run_id)
        reserve = nominal_tail_reserve(self.task)
        policy_version = investigation_policy_version(
            self.context_policy_version
        )
        admission_schema = tool_admission_schema(
            self.context_policy_version
        )
        model_calls_used = sum(
            event.type == EventType.MODEL_CALLED for event in events
        )
        tool_calls_used = sum(
            event.type == EventType.TOOL_CALLED for event in events
        )
        remaining_model_calls = (
            manifest.budget.max_model_calls - model_calls_used
        )
        remaining_tool_calls = (
            manifest.budget.max_tool_calls - tool_calls_used
        )
        calculated_tail_policy = None
        if self.context_policy_version == "phase-evidence-v5":
            calculated_tail_policy = tail_policy(
                self.task,
                None,
                context_policy_version=self.context_policy_version,
                events=events,
                budget=manifest.budget,
                max_output_tokens=manifest.model.max_output_tokens,
                projection_stage="post_generation",
            )
            block_reasons = list(
                calculated_tail_policy["block_reasons"]
            )
        else:
            block_reasons = []
            if remaining_tool_calls <= reserve["tool_calls"]:
                block_reasons.append("tool_tail_reserved")
            if remaining_model_calls <= (
                reserve["model_calls"] + reserve["feedback_model_calls"]
            ):
                block_reasons.append("model_tail_reserved")
        if not block_reasons:
            return None

        started = utc_now()
        input_artifact = self.artifacts.put_json(
            {"tool": name, "input": arguments}
        )
        try:
            preflight_artifact = self._inspection_admission_preflight(
                name=name,
                arguments=arguments,
                worktree_diff_hash=worktree_diff_hash,
            )
        except (ContractError, OSError):
            # The target can disappear between eligibility and snapshot.
            # Ordinary dispatch will then record the structured failure.
            return None
        preflight_descriptor = preflight_artifact.model_dump(mode="json")
        error_message = (
            "inspection was not admitted because the nominal corrective "
            "lifecycle tail is reserved; use apply_patch or another "
            "phase-advancing action"
        )
        error_details = {
            "schema_version": admission_schema,
            "policy_version": policy_version,
            "reason_codes": block_reasons,
            "nominal_reserve": reserve,
            "remaining_model_calls": remaining_model_calls,
            "remaining_tool_calls": remaining_tool_calls,
            "guidance": (
                "Use the durable investigation ledger and move to a scoped "
                "patch, registered validation, diff review, or submission."
            ),
        }
        if calculated_tail_policy is not None:
            error_details["tail_policy"] = calculated_tail_policy
        result_payload = {
            "tool": name,
            "status": "rejected",
            "error_code": "TOOL_ADMISSION_BLOCKED",
            "error_message": error_message,
            "error_details": error_details,
            "admission_blocked": True,
            "worktree_diff_hash": worktree_diff_hash,
            "preflight_artifact": preflight_descriptor,
        }
        result_artifact = self.artifacts.put_json(result_payload)
        result = ToolResult(
            action_id=action_id,
            status="rejected",
            started_at=started,
            finished_at=utc_now(),
            output={
                "artifact_id": result_artifact.artifact_id,
                "artifact_path": result_artifact.path,
                "result_artifact": result_artifact.model_dump(mode="json"),
                **result_payload,
            },
            error_code="TOOL_ADMISSION_BLOCKED",
            error_message=error_message,
        )
        event_payload = {
            "schema_version": admission_schema,
            "policy_version": policy_version,
            "tool": name,
            "status": "rejected",
            "input_hash": input_hash,
            "normalized_call_hash": normalized_call_hash,
            "worktree_diff_hash": worktree_diff_hash,
            "mutation_epoch_sequence": mutation_epoch(events),
            "reason_codes": block_reasons,
            "nominal_reserve": reserve,
            "model_calls_used": model_calls_used,
            "max_model_calls": manifest.budget.max_model_calls,
            "tool_calls_used": tool_calls_used,
            "max_tool_calls": manifest.budget.max_tool_calls,
            "input_artifact": input_artifact.model_dump(mode="json"),
            "preflight_artifact": preflight_descriptor,
            "result_artifact": result_artifact.model_dump(mode="json"),
            "artifact_id": result_artifact.artifact_id,
            "artifact_path": result_artifact.path,
            "error_code": result.error_code,
            "error_message": error_message,
            "error_details": error_details,
        }
        if calculated_tail_policy is not None:
            token_projection = calculated_tail_policy[
                "token_projection"
            ]
            event_payload.update(
                {
                    "tail_policy": calculated_tail_policy,
                    "tokens_used": token_projection[
                        "total_tokens_used"
                    ],
                    "remaining_tokens": token_projection[
                        "remaining_tokens"
                    ],
                    "max_total_tokens": manifest.budget.max_total_tokens,
                    "max_output_tokens": (
                        manifest.model.max_output_tokens
                    ),
                }
            )
        self.state.complete_nonexecuted_action(
            self.run_id,
            action_id,
            input_hash,
            result,
            event_specs=[
                (
                    EventType.TOOL_ADMISSION_BLOCKED,
                    "tool-admission-policy",
                    event_payload,
                )
            ],
        )
        return result

    def _inspection_admission_preflight(
        self,
        *,
        name: str,
        arguments: dict[str, Any],
        worktree_diff_hash: str,
    ) -> Artifact:
        """Freeze stateful validation evidence before a no-dispatch result."""

        payload: dict[str, Any] = {
            "schema_version": INSPECTION_ADMISSION_PREFLIGHT_SCHEMA,
            "policy_version": investigation_policy_version(
                self.context_policy_version
            ),
            "tool": name,
            "worktree_diff_hash": worktree_diff_hash,
        }
        if name == "read_file":
            path = str(arguments["path"])
            workspace = self.workspace.resolve()
            target = ensure_within(workspace, path)
            content = target.read_bytes()
            target_artifact = self.artifacts.put_bytes(content)
            payload.update(
                {
                    "requested_path": path,
                    "resolved_relative_path": target.relative_to(
                        workspace
                    ).as_posix(),
                    "target_artifact": target_artifact.model_dump(
                        mode="json"
                    ),
                }
            )
        else:
            payload.update(
                {
                    "query": arguments["query"],
                    "path_glob": arguments.get("path_glob", "**/*"),
                }
            )
        return self.artifacts.put_json(payload)

    def _investigation_no_progress_streak(
        self,
        events: list,
    ) -> int:
        epoch = mutation_epoch(events)
        streak = 0
        for event in events:
            if epoch is not None and event.sequence <= epoch:
                continue
            if (
                event.type == EventType.LOOP_DETECTED
                and event.payload.get("schema_version")
                == INVESTIGATION_LOOP_SCHEMA
            ):
                streak += 1
            elif (
                event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool")
                in {"read_file", "search_files"}
            ):
                novelty = event.payload.get("novelty")
                if (
                    isinstance(novelty, dict)
                    and novelty.get("classification") == "seen_only"
                ):
                    streak += 1
                else:
                    streak = 0
            elif (
                event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool")
                not in {"read_file", "search_files"}
            ):
                streak = 0
        return streak

    def _semantic_inspection_replay(
        self,
        *,
        name: str,
        action_id: str,
        arguments: dict[str, Any],
        input_hash: str,
        normalized_call_hash: str,
        worktree_diff_hash: str,
        existing_call_payload: dict[str, Any] | None = None,
    ) -> ToolResult | None:
        events = self.state.list_events(self.run_id)
        records = load_inspection_records(
            events,
            self.artifacts,
            worktree_diff_hash=worktree_diff_hash,
        )
        sources = []
        replay_output: dict[str, Any] | None = None
        reason_code: str | None = None
        if name == "search_files":
            exact = [
                record
                for record in records
                if record.tool == name
                and record.normalized_call_hash == normalized_call_hash
                and record.result["truncated"] is False
            ]
            if exact:
                sources = [exact[-1]]
                replay_output = dict(exact[-1].result)
                reason_code = "duplicate_search"
        elif (
            name == "read_file"
            and isinstance(arguments.get("path"), str)
            and type(arguments.get("start_line")) is int
            and type(arguments.get("end_line")) is int
        ):
            reconstructed = reconstruct_covered_read(
                records,
                path=str(arguments["path"]),
                start_line=int(arguments["start_line"]),
                end_line=int(arguments["end_line"]),
                worktree_diff_hash=worktree_diff_hash,
            )
            if reconstructed is not None:
                replay_output, sources = reconstructed
                reason_code = "fully_covered_read"
        if replay_output is None or reason_code is None:
            return None

        started = utc_now()
        input_artifact = (
            Artifact.model_validate(existing_call_payload["input_artifact"])
            if existing_call_payload is not None
            else self.artifacts.put_json({"tool": name, "input": arguments})
        )
        source_call_sequences = [
            source.call_sequence for source in sources
        ]
        source_outcome_sequences = [
            source.outcome_sequence for source in sources
        ]
        replay_payload = {
            **replay_output,
            "novelty": {
                "classification": "seen_only",
                "new_evidence_count": 0,
                "reason": reason_code,
            },
            "semantic_replay": True,
            "replay_kind": "semantic-investigation",
            "replay_reason": reason_code,
            "source_call_sequences": source_call_sequences,
            "source_outcome_sequences": source_outcome_sequences,
        }
        result_artifact = self.artifacts.put_json(replay_payload)
        result = ToolResult(
            action_id=action_id,
            status="succeeded",
            started_at=started,
            finished_at=utc_now(),
            output={
                "artifact_id": result_artifact.artifact_id,
                "artifact_path": result_artifact.path,
                "result_artifact": result_artifact.model_dump(mode="json"),
                **replay_payload,
            },
        )
        new_streak = self._investigation_no_progress_streak(events) + 1
        epoch = mutation_epoch(events)
        call_payload = (
            dict(existing_call_payload)
            if existing_call_payload is not None
            else {
                "tool": name,
                "input_hash": input_hash,
                "normalized_call_hash": normalized_call_hash,
                "worktree_diff_hash": worktree_diff_hash,
                "execution": "semantic-cache-replay",
                "input_artifact": input_artifact.model_dump(mode="json"),
                "artifact_id": input_artifact.artifact_id,
                "artifact_path": input_artifact.path,
            }
        )
        loop_payload = {
            "schema_version": INVESTIGATION_LOOP_SCHEMA,
            "policy_version": INVESTIGATION_POLICY_VERSION,
            "tool": name,
            "reason_code": reason_code,
            "normalized_call_hash": normalized_call_hash,
            "source_call_sequences": source_call_sequences,
            "source_outcome_sequences": source_outcome_sequences,
            "mutation_epoch_sequence": epoch,
            "worktree_diff_hash": worktree_diff_hash,
            "no_progress_streak": new_streak,
            "strategy_change_required": new_streak >= 2,
            "occurrences": new_streak + 1,
            "enforcement": "semantic-cache-replay",
        }
        outcome_payload = {
            "schema_version": TOOL_REPLAY_SCHEMA,
            "tool": name,
            "status": "succeeded",
            "semantic_replay": True,
            "replay_kind": "semantic-investigation",
            "reason_code": reason_code,
            "input_hash": input_hash,
            "normalized_call_hash": normalized_call_hash,
            "source_action_ids": [
                source.action_id for source in sources
            ],
            "source_call_sequences": source_call_sequences,
            "source_outcome_sequences": source_outcome_sequences,
            "mutation_epoch_sequence": epoch,
            "worktree_diff_hash": worktree_diff_hash,
            "artifact_id": result_artifact.artifact_id,
            "artifact_path": result_artifact.path,
            "result_artifact": result_artifact.model_dump(mode="json"),
            "duration_ms": int(
                (result.finished_at - result.started_at).total_seconds()
                * 1000
            ),
        }
        self.state.complete_nonexecuted_action(
            self.run_id,
            action_id,
            input_hash,
            result,
            event_specs=[
                (EventType.TOOL_CALLED, "agent", call_payload),
                (EventType.LOOP_DETECTED, "tool-gateway", loop_payload),
                (EventType.TOOL_REPLAYED, "semantic-cache", outcome_payload),
            ],
        )
        return result

    def _annotate_inspection_result(
        self,
        *,
        name: str,
        output: dict[str, Any],
        worktree_diff_hash: str,
    ) -> dict[str, Any]:
        events = self.state.list_events(self.run_id)
        records = load_inspection_records(
            events,
            self.artifacts,
            worktree_diff_hash=worktree_diff_hash,
        )
        annotated = {**output, "worktree_diff_hash": worktree_diff_hash}
        if name == "read_file":
            prior_lines = {
                line
                for start, end in read_coverage(
                    records,
                    str(output["path"]),
                )
                for line in range(start, end + 1)
            }
            actual_start = output["actual_start_line"]
            actual_end = output["actual_end_line"]
            returned_lines = (
                set(range(actual_start, actual_end + 1))
                if actual_start is not None and actual_end is not None
                else set()
            )
            new_lines = returned_lines - prior_lines
            classification = (
                "novel"
                if new_lines
                else "novel_negative"
            )
            annotated["novelty"] = {
                "schema_version": "inspection-novelty-v1",
                "classification": classification,
                "new_evidence_count": len(new_lines),
                "reused_evidence_count": len(returned_lines & prior_lines),
            }
        else:
            prior_matches = prior_search_match_keys(records)
            current_matches = {
                search_match_key(match)
                for match in output["matches"]
            }
            new_matches = current_matches - prior_matches
            if output["truncated"]:
                classification = "novel_truncated"
            elif not current_matches:
                classification = "novel_negative"
            elif new_matches:
                classification = "novel"
            else:
                classification = "seen_only"
            annotated["novelty"] = {
                "schema_version": "inspection-novelty-v1",
                "classification": classification,
                "new_evidence_count": len(new_matches),
                "reused_evidence_count": len(
                    current_matches & prior_matches
                ),
            }
        return annotated

    def _controlled_rejection_pending(self) -> bool:
        if (
            self.fault.type
            != "controlled-reject-first-prepared-patch"
        ):
            return False
        events = self.state.list_events(self.run_id)
        controlled_failures = [
            event
            for event in events
            if (
                event.type == EventType.TOOL_FAILED
                and event.payload.get("error_code")
                == "CONTROLLED_DIAGNOSTIC_REJECTION"
            )
        ]
        if not controlled_failures:
            return True
        if len(controlled_failures) > 1:
            raise RecoveryError(
                "controlled rejection evidence contains duplicate declarations"
            )

        failure = controlled_failures[0]
        action_id = failure.correlation_id
        calls = [
            event
            for event in events
            if (
                event.type == EventType.TOOL_CALLED
                and event.actor == "agent"
                and event.payload.get("tool") == "apply_patch"
                and event.correlation_id == action_id
                and event.sequence < failure.sequence
            )
        ]
        prepared = [
            event
            for event in events
            if (
                event.type == EventType.PATCH_PREPARED
                and event.actor == "tool-gateway"
                and event.correlation_id == action_id
                and event.sequence < failure.sequence
            )
        ]
        all_prepared = [
            event
            for event in events
            if event.type == EventType.PATCH_PREPARED
        ]
        applied = [
            event
            for event in events
            if (
                event.type == EventType.PATCH_APPLIED
                and event.correlation_id == action_id
            )
        ]
        call = calls[0] if len(calls) == 1 else None
        intent = prepared[0] if len(prepared) == 1 else None
        expected_details = None
        if call is not None and intent is not None:
            patch_artifact = call.payload.get("patch_artifact")
            candidate_hash = (
                patch_artifact.get("content_hash")
                if isinstance(patch_artifact, dict)
                else None
            )
            expected_details = {
                "schema_version": "controlled-rejection-v1",
                "stage": "diagnostic",
                "reason": "controlled_rejection",
                "guidance": (
                    "Review the rehydrated candidate and rejection evidence, "
                    "then retry with a new action_id."
                ),
                "fault_type": "controlled-reject-first-prepared-patch",
                "trigger": "first-preflight-valid-apply-patch",
                "trigger_after": 1,
                "source_call_sequence": call.sequence,
                "source_prepared_sequence": intent.sequence,
                "candidate_content_hash": candidate_hash,
                "input_hash": call.payload.get("input_hash"),
                "prepared_intent_content_hash": intent.payload.get(
                    "content_hash"
                ),
                "baseline_worktree_diff_hash": intent.payload.get(
                    "baseline_worktree_diff_hash"
                ),
                "expected_worktree_diff_hash": intent.payload.get(
                    "expected_worktree_diff_hash"
                ),
                "observed_worktree_diff_hash": intent.payload.get(
                    "baseline_worktree_diff_hash"
                ),
                "worktree_mutated": False,
            }
        details = failure.payload.get("error_details")
        valid = bool(
            failure.actor == "tool-gateway"
            and failure.payload.get("tool") == "apply_patch"
            and failure.payload.get("status") == "rejected"
            and isinstance(action_id, str)
            and action_id
            and call is not None
            and intent is not None
            and call.sequence < intent.sequence < failure.sequence
            and failure.sequence == intent.sequence + 1
            and all_prepared
            and intent.sequence == all_prepared[0].sequence
            and expected_details is not None
            and all(
                isinstance(expected_details.get(field), str)
                and expected_details[field]
                for field in (
                    "candidate_content_hash",
                    "input_hash",
                    "prepared_intent_content_hash",
                    "baseline_worktree_diff_hash",
                    "expected_worktree_diff_hash",
                    "observed_worktree_diff_hash",
                )
            )
            and details == expected_details
            and not applied
        )
        if not valid:
            raise RecoveryError(
                "controlled rejection evidence is malformed"
            )
        return False

    def _controlled_rejection(
        self,
        *,
        action_id: str,
        input_hash: str,
        patch_artifact: Artifact,
        intent: dict[str, Any],
    ) -> ControlledDiagnosticRejection:
        if self._classify_patch_state(intent) != "pre":
            raise RecoveryError(
                "controlled rejection requires the prepared patch pre-state"
            )
        events = self.state.list_events(self.run_id)
        prepared_events = [
            event
            for event in events
            if (
                event.type == EventType.PATCH_PREPARED
                and event.correlation_id == action_id
            )
        ]
        all_prepared = [
            event
            for event in events
            if event.type == EventType.PATCH_PREPARED
        ]
        call_events = [
            event
            for event in events
            if (
                event.type == EventType.TOOL_CALLED
                and event.correlation_id == action_id
                and event.payload.get("tool") == "apply_patch"
            )
        ]
        if len(call_events) != 1 or len(prepared_events) != 1:
            raise RecoveryError(
                "controlled rejection lacks one correlated call and prepared intent"
            )
        call = call_events[0]
        prepared = prepared_events[0]
        if not all_prepared or prepared.sequence != all_prepared[0].sequence:
            raise RecoveryError(
                "controlled rejection is not bound to the first prepared patch"
            )
        if not events or prepared.sequence != events[-1].sequence:
            raise RecoveryError(
                "controlled rejection prepared intent is not the current latest event"
            )
        baseline_hash = str(intent["baseline_worktree_diff_hash"])
        expected_hash = str(intent["expected_worktree_diff_hash"])
        observed = WorkspaceManager.diff_summary(self.workspace)
        if (
            observed.patch_hash != baseline_hash
            or WorkspaceManager.untracked_files(self.workspace)
        ):
            raise RecoveryError(
                "controlled rejection observed a mutated or untracked worktree"
            )
        return ControlledDiagnosticRejection(
            (
                "diagnostic control rejected the first preflight-valid patch "
                "before worktree mutation"
            ),
            details={
                "schema_version": "controlled-rejection-v1",
                "stage": "diagnostic",
                "reason": "controlled_rejection",
                "guidance": (
                    "Review the rehydrated candidate and rejection evidence, "
                    "then retry with a new action_id."
                ),
                "fault_type": self.fault.type,
                "trigger": "first-preflight-valid-apply-patch",
                "trigger_after": self.fault.trigger_after,
                "source_call_sequence": call.sequence,
                "source_prepared_sequence": prepared.sequence,
                "candidate_content_hash": patch_artifact.content_hash,
                "input_hash": input_hash,
                "prepared_intent_content_hash": prepared.payload.get(
                    "content_hash"
                ),
                "baseline_worktree_diff_hash": baseline_hash,
                "expected_worktree_diff_hash": expected_hash,
                "observed_worktree_diff_hash": observed.patch_hash,
                "worktree_mutated": False,
            },
        )

    def _error_result(
        self,
        name: str,
        action_id: str,
        started,
        error: Exception,
        *,
        fatal: bool,
    ) -> ToolResult:
        details = dict(getattr(error, "details", {}))
        if fatal:
            details["fatal"] = True
        status = "failed" if fatal else "rejected"
        error_payload = {
            "tool": name,
            "status": status,
            "error_code": getattr(error, "code", "INVALID_TOOL_INPUT"),
            "error_message": str(error),
            "error_details": details,
        }
        artifact = self.artifacts.put_json(error_payload)
        output: dict[str, Any] = {
            "artifact_id": artifact.artifact_id,
            "artifact_path": artifact.path,
            "result_artifact": artifact.model_dump(mode="json"),
            "error_details": details,
        }
        if fatal:
            output["fatal"] = True
        return ToolResult(
            action_id=action_id,
            status=status,
            started_at=started,
            finished_at=utc_now(),
            output=output,
            error_code=getattr(error, "code", "INVALID_TOOL_INPUT"),
            error_message=str(error),
        )

    @staticmethod
    def _result_event_payload(name: str, result: ToolResult) -> dict[str, Any]:
        return {
            "tool": name,
            "status": result.status,
            "artifact_id": result.output.get("artifact_id"),
            "artifact_path": result.output.get("artifact_path"),
            "result_artifact": result.output.get("result_artifact"),
            "error_code": result.error_code,
            "error_message": (
                result.error_message[:_EVENT_ERROR_MESSAGE_LIMIT]
                if result.error_message
                else None
            ),
            "check_id": result.output.get("check_id"),
            "passed": result.output.get("passed"),
            "timed_out": result.output.get("timed_out"),
            "worktree_diff_hash": result.output.get("worktree_diff_hash"),
            "patch_hash": result.output.get("patch_hash"),
            "error_details": result.output.get("error_details"),
            "novelty": result.output.get("novelty"),
            "duration_ms": int(
                (result.finished_at - result.started_at).total_seconds() * 1000
            ),
        }

    def _complete_result(
        self,
        name: str,
        input_hash: str,
        result: ToolResult,
    ) -> None:
        patch_payload = None
        if name == "apply_patch" and result.status == "succeeded":
            patch_payload = {
                "patch_hash": result.output["patch_hash"],
                "worktree_diff_hash": result.output["worktree_diff_hash"],
            }
        self.state.complete_action(
            self.run_id,
            result.action_id,
            input_hash,
            result,
            outcome_type=(
                EventType.TOOL_SUCCEEDED
                if result.status == "succeeded"
                else EventType.TOOL_FAILED
            ),
            outcome_payload=self._result_event_payload(name, result),
            patch_payload=patch_payload,
        )

    def reconcile_interrupted_patch(
        self,
        checkpoint: Checkpoint,
    ) -> ToolResult | None:
        """Complete one v2 patch action that crossed a hard process boundary."""

        if self.tool_schema_version != "v2":
            return None
        events = self.state.list_events(self.run_id)
        controlled_rejection_pending = self._controlled_rejection_pending()
        calls = [
            event
            for event in events
            if event.sequence > checkpoint.through_sequence
            and event.type == EventType.TOOL_CALLED
            and event.payload.get("tool") == "apply_patch"
        ]
        if not calls:
            return None
        if len(calls) != 1:
            raise RecoveryError(
                "recovery found multiple patch calls after the latest checkpoint"
            )
        call = calls[0]
        if call.correlation_id is None:
            raise RecoveryError("interrupted patch call lacks an action identity")
        action_id = call.correlation_id
        input_hash = call.payload.get("input_hash")
        if not isinstance(input_hash, str):
            raise RecoveryError("interrupted patch call lacks its input hash")
        prior = self.state.get_action_result(
            self.run_id,
            action_id,
            input_hash,
        )
        prepared_events = [
            event
            for event in events
            if event.sequence > call.sequence
            and event.type == EventType.PATCH_PREPARED
            and event.correlation_id == action_id
        ]
        if len(prepared_events) > 1:
            raise RecoveryError("interrupted patch has duplicate prepared intents")

        current = WorkspaceManager.diff_summary(self.workspace)
        if WorkspaceManager.untracked_files(self.workspace):
            raise RecoveryError(
                "agent workspace contains untracked files during patch recovery"
            )
        if prior is not None:
            if prior.status == "succeeded":
                if not prepared_events:
                    raise RecoveryError(
                        "successful interrupted patch lacks a prepared intent"
                    )
                intent, patch = self._load_patch_intent(
                    call,
                    prepared_events[0],
                )
                state = self._classify_patch_state(intent)
                if state != "post":
                    raise RecoveryError(
                        "successful interrupted patch is not in its prepared post-state"
                    )
                if (
                    current.patch_hash
                    != prior.output.get("worktree_diff_hash")
                    or sha256_text(patch) != prior.output.get("patch_hash")
                ):
                    raise RecoveryError(
                        "successful interrupted patch conflicts with its durable result"
                    )
            elif current.patch_hash != checkpoint.worktree_diff_hash:
                raise RecoveryError(
                    "failed interrupted patch did not restore its checkpoint state"
                )
            self._complete_result("apply_patch", input_hash, prior)
            return prior

        started = call.timestamp
        try:
            patch = self._load_call_patch(call)
            if prepared_events:
                intent, prepared_patch = self._load_patch_intent(
                    call,
                    prepared_events[0],
                )
                if prepared_patch != patch:
                    raise RecoveryError(
                        "prepared patch bytes conflict with ToolCalled evidence"
                    )
            else:
                if current.patch_hash != checkpoint.worktree_diff_hash:
                    raise RecoveryError(
                        "workspace changed before a durable patch intent was recorded"
                    )
                patch_artifact = Artifact.model_validate(
                    call.payload.get("patch_artifact")
                )
                intent = self._prepare_patch_mutation(
                    action_id,
                    input_hash,
                    patch,
                    patch_artifact,
                )
            if (
                intent.get("baseline_worktree_diff_hash")
                != checkpoint.worktree_diff_hash
            ):
                raise RecoveryError(
                    "prepared patch baseline does not match the durable checkpoint"
                )
            if controlled_rejection_pending:
                patch_artifact = Artifact.model_validate(
                    call.payload.get("patch_artifact")
                )
                result = self._error_result(
                    "apply_patch",
                    action_id,
                    started,
                    self._controlled_rejection(
                        action_id=action_id,
                        input_hash=input_hash,
                        patch_artifact=patch_artifact,
                        intent=intent,
                    ),
                    fatal=False,
                )
                self._complete_result("apply_patch", input_hash, result)
                return result
            state = self._classify_patch_state(intent)
            if state == "mixed":
                hypothetical = self._hypothetical_preimage_diff_hash(
                    intent
                )
                if (
                    hypothetical
                    != intent["baseline_worktree_diff_hash"]
                ):
                    raise RecoveryError(
                        "mixed patch state includes changes outside "
                        "the prepared mutation"
                    )
                self._restore_patch_preimages(intent)
                state = "pre"
            if state == "pre":
                output = self._apply_patch(patch, intent=intent)
            elif state == "post":
                output = self._finalize_applied_patch(
                    patch,
                    str(intent["baseline_worktree_diff_hash"]),
                    expected_diff_hash=str(
                        intent["expected_worktree_diff_hash"]
                    ),
                    intent=intent,
                )
            else:
                raise RecoveryError(
                    f"unsupported interrupted patch state: {state}"
                )
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
        except (ContractError, PolicyViolation, TypeError, ValueError) as exc:
            result = self._error_result(
                "apply_patch",
                action_id,
                started,
                exc,
                fatal=False,
            )
        except RecoveryError as exc:
            result = self._error_result(
                "apply_patch",
                action_id,
                started,
                exc,
                fatal=True,
            )
        self._complete_result("apply_patch", input_hash, result)
        return result

    def reconcile_interrupted_action(
        self,
        checkpoint: Checkpoint,
    ) -> tuple[str, ToolResult] | None:
        """Complete one non-mutating v2 action without another ToolCalled."""

        if self.tool_schema_version != "v2":
            return None
        events = self.state.list_events(self.run_id)
        calls = [
            event
            for event in events
            if event.sequence > checkpoint.through_sequence
            and event.type == EventType.TOOL_CALLED
            and event.payload.get("tool")
            not in {"apply_patch", "finish_task"}
        ]
        if not calls:
            return None
        if len(calls) != 1:
            raise RecoveryError(
                "recovery found multiple non-patch calls after "
                "the latest checkpoint"
            )
        call = calls[0]
        if call.correlation_id is None:
            raise RecoveryError(
                "interrupted tool call lacks an action identity"
            )
        name, arguments, input_hash = self._load_call_input(call)
        prior = self.state.get_action_result(
            self.run_id,
            call.correlation_id,
            input_hash,
        )
        if (
            self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES
            and name in {"read_file", "search_files"}
            and call.payload.get("execution")
            == "semantic-cache-replay"
        ):
            normalized_call_hash = call.payload.get(
                "normalized_call_hash"
            )
            worktree_diff_hash = call.payload.get("worktree_diff_hash")
            if (
                not isinstance(normalized_call_hash, str)
                or not isinstance(worktree_diff_hash, str)
            ):
                raise RecoveryError(
                    "semantic replay call lacks a valid inspection identity"
                )
            current_diff_hash = WorkspaceManager.diff_summary(
                self.workspace
            ).patch_hash
            expected_normalized_hash = self._normalized_call_hash(
                name,
                arguments,
                worktree_diff_hash=worktree_diff_hash,
            )
            if (
                worktree_diff_hash != current_diff_hash
                or normalized_call_hash != expected_normalized_hash
            ):
                raise RecoveryError(
                    "semantic replay call no longer matches the worktree "
                    "or canonical input"
                )
            if prior is not None:
                semantic_suffix = [
                    event
                    for event in events
                    if event.sequence > call.sequence
                    and event.correlation_id == call.correlation_id
                    and event.type
                    in {EventType.LOOP_DETECTED, EventType.TOOL_REPLAYED}
                ]
                if [event.type for event in semantic_suffix] != [
                    EventType.LOOP_DETECTED,
                    EventType.TOOL_REPLAYED,
                ] or any(
                    event.actor != expected_actor
                    or event.payload.get("tool") != name
                    for event, expected_actor in zip(
                        semantic_suffix,
                        ("tool-gateway", "semantic-cache"),
                        strict=True,
                    )
                ):
                    raise RecoveryError(
                        "semantic replay action has an invalid durable suffix"
                    )
                return name, prior
            replay = self._semantic_inspection_replay(
                name=name,
                action_id=call.correlation_id,
                arguments=arguments,
                input_hash=input_hash,
                normalized_call_hash=normalized_call_hash,
                worktree_diff_hash=worktree_diff_hash,
                existing_call_payload=call.payload,
            )
            if replay is None:
                raise RecoveryError(
                    "interrupted semantic replay can no longer be derived"
                )
            return name, replay
        outcomes = [
            event
            for event in events
            if event.sequence > call.sequence
            and event.correlation_id == call.correlation_id
            and event.type
            in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
        ]
        if len(outcomes) > 1:
            raise RecoveryError(
                "interrupted tool call has duplicate durable outcomes"
            )
        if outcomes and prior is None:
            raise RecoveryError(
                "tool outcome exists without its atomic action result"
            )
        if prior is not None:
            self._complete_result(name, input_hash, prior)
            return name, prior

        started = call.timestamp
        try:
            output = self._dispatch(name, arguments)
            if (
                self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES
                and name in {"read_file", "search_files"}
            ):
                worktree_diff_hash = call.payload.get(
                    "worktree_diff_hash"
                )
                if not isinstance(worktree_diff_hash, str):
                    raise RecoveryError(
                        "v4 inspection call lacks a worktree diff identity"
                    )
                output = self._annotate_inspection_result(
                    name=name,
                    output=output,
                    worktree_diff_hash=worktree_diff_hash,
                )
            artifact = self.artifacts.put_json(output)
            result_artifact = (
                artifact.model_dump(mode="json")
                if self.context_policy_version
                in _INVESTIGATION_CONTEXT_POLICIES
                and name in {"read_file", "search_files"}
                else None
            )
            result = ToolResult(
                action_id=call.correlation_id,
                status="succeeded",
                started_at=started,
                finished_at=utc_now(),
                output={
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                    **(
                        {"result_artifact": result_artifact}
                        if result_artifact is not None
                        else {}
                    ),
                    **output,
                },
            )
        except (ContractError, PolicyViolation, TypeError, ValueError) as exc:
            result = self._error_result(
                name,
                call.correlation_id,
                started,
                exc,
                fatal=False,
            )
        except RecoveryError as exc:
            result = self._error_result(
                name,
                call.correlation_id,
                started,
                exc,
                fatal=True,
            )
        self._complete_result(name, input_hash, result)
        return name, result

    def _load_call_input(self, call) -> tuple[str, dict[str, Any], str]:
        try:
            artifact = Artifact.model_validate(
                call.payload["input_artifact"]
            )
            raw = self.artifacts.read_bytes(artifact)
            value = json.loads(raw.decode("utf-8", errors="strict"))
            name = value["tool"]
            arguments = value["input"]
        except (
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RecoveryError(
                "interrupted tool call lacks valid input evidence"
            ) from exc
        if (
            not isinstance(name, str)
            or name != call.payload.get("tool")
            or name in {"apply_patch", "finish_task"}
            or not isinstance(arguments, dict)
            or call.payload.get("artifact_id") != artifact.artifact_id
            or call.payload.get("artifact_path") != artifact.path
        ):
            raise RecoveryError(
                "interrupted tool input conflicts with ToolCalled evidence"
            )
        input_hash = sha256_text(
            canonical_json({"tool": name, "input": arguments})
        )
        if input_hash != call.payload.get("input_hash"):
            raise RecoveryError(
                "interrupted tool input does not match its call hash"
            )
        return name, arguments, input_hash

    def _load_call_patch(self, call) -> str:
        try:
            artifact = Artifact.model_validate(
                call.payload["patch_artifact"]
            )
            content = self.artifacts.read_bytes(artifact)
            patch = content.decode("utf-8", errors="strict")
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
            raise RecoveryError(
                "interrupted patch lacks valid raw input evidence"
            ) from exc
        expected_input_hash = sha256_text(
            canonical_json({"tool": "apply_patch", "input": {"patch": patch}})
        )
        if expected_input_hash != call.payload.get("input_hash"):
            raise RecoveryError(
                "interrupted patch input does not match its ToolCalled hash"
            )
        return patch

    def _load_patch_intent(
        self,
        call,
        prepared_event,
    ) -> tuple[dict[str, Any], str]:
        try:
            artifact = Artifact.model_validate(
                prepared_event.payload["intent_artifact"]
            )
            raw = self.artifacts.read_bytes(artifact)
            intent = json.loads(raw.decode("utf-8", errors="strict"))
        except (
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RecoveryError(
                "prepared patch intent artifact is invalid"
            ) from exc
        if not isinstance(intent, dict):
            raise RecoveryError("prepared patch intent must be a JSON object")
        if (
            intent.get("schema_version") != "patch-mutation-intent-v1"
            or intent.get("run_id") != self.run_id
            or intent.get("action_id") != call.correlation_id
            or intent.get("input_hash") != call.payload.get("input_hash")
            or prepared_event.payload.get("content_hash")
            != artifact.content_hash
            or prepared_event.payload.get("baseline_worktree_diff_hash")
            != intent.get("baseline_worktree_diff_hash")
            or prepared_event.payload.get("expected_worktree_diff_hash")
            != intent.get("expected_worktree_diff_hash")
        ):
            raise RecoveryError(
                "prepared patch intent conflicts with its event identity"
            )
        patch = self._load_call_patch(call)
        try:
            intent_patch_artifact = Artifact.model_validate(
                intent["patch_artifact"]
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RecoveryError(
                "prepared patch intent lacks its raw patch artifact"
            ) from exc
        if (
            intent_patch_artifact.model_dump(mode="json")
            != call.payload.get("patch_artifact")
            or self.artifacts.read_bytes(intent_patch_artifact)
            != patch.encode("utf-8")
        ):
            raise RecoveryError(
                "prepared patch artifact conflicts with ToolCalled evidence"
            )
        files = intent.get("files")
        if not isinstance(files, list) or not files:
            raise RecoveryError("prepared patch intent has no file images")
        paths: list[str] = []
        try:
            for entry in files:
                if (
                    not isinstance(entry, dict)
                    or set(entry)
                    != {
                        "path",
                        "mode",
                        "git_mode",
                        "preimage_artifact",
                        "postimage_artifact",
                    }
                    or type(entry["mode"]) is not int
                    or not 0 <= entry["mode"] <= 0o7777
                    or entry["git_mode"] not in {"100644", "100755"}
                ):
                    raise ValueError("invalid file image entry")
                path = safe_relative_path(
                    str(entry["path"]),
                    field_name="prepared patch path",
                )
                preimage_artifact = Artifact.model_validate(
                    entry["preimage_artifact"]
                )
                self.artifacts.read_bytes(preimage_artifact)
                postimage_raw = entry["postimage_artifact"]
                if postimage_raw is not None:
                    postimage_artifact = Artifact.model_validate(
                        postimage_raw
                    )
                    self.artifacts.read_bytes(postimage_artifact)
                paths.append(path)
        except (ContractError, KeyError, TypeError, ValueError) as exc:
            raise RecoveryError(
                "prepared patch contains invalid file image evidence"
            ) from exc
        try:
            patch_paths = _patch_paths(patch)
        except ContractError as exc:
            raise RecoveryError(
                "prepared patch raw input no longer satisfies its contract"
            ) from exc
        if paths != patch_paths:
            raise RecoveryError(
                "prepared patch file images do not match the raw patch"
            )
        return intent, patch

    def _classify_patch_state(self, intent: dict[str, Any]) -> str:
        states: list[str] = []
        for entry in intent["files"]:
            try:
                path = safe_relative_path(
                    str(entry["path"]),
                    field_name="prepared patch path",
                )
                pre_artifact = Artifact.model_validate(
                    entry["preimage_artifact"]
                )
                post_raw = entry.get("postimage_artifact")
                post_artifact = (
                    Artifact.model_validate(post_raw)
                    if post_raw is not None
                    else None
                )
                preimage = self.artifacts.read_bytes(pre_artifact)
                postimage = (
                    self.artifacts.read_bytes(post_artifact)
                    if post_artifact is not None
                    else None
                )
                mode = int(entry["mode"])
            except (ContractError, KeyError, TypeError, ValueError) as exc:
                raise RecoveryError(
                    "prepared patch contains invalid file image evidence"
                ) from exc
            target = self._prepared_workspace_target(path, recovery=True)
            if target.exists():
                target_stat = target.lstat()
                if not stat.S_ISREG(target_stat.st_mode):
                    raise RecoveryError(
                        f"prepared patch target is no longer a regular file: {path}"
                    )
                if stat.S_IMODE(target_stat.st_mode) != mode:
                    raise RecoveryError(
                        f"prepared patch target mode changed: {path}"
                    )
                current = target.read_bytes()
                if current == preimage:
                    states.append("pre")
                elif postimage is not None and current == postimage:
                    states.append("post")
                else:
                    raise RecoveryError(
                        f"prepared patch target is in an unknown state: {path}"
                    )
            elif postimage is None:
                states.append("post")
            else:
                raise RecoveryError(
                    f"prepared patch target is unexpectedly missing: {path}"
                )

        summary = WorkspaceManager.diff_summary(self.workspace)
        state_set = set(states)
        if state_set == {"pre"}:
            if summary.patch_hash != intent["baseline_worktree_diff_hash"]:
                raise RecoveryError(
                    "pre-state files do not match the prepared baseline diff"
                )
            return "pre"
        if state_set == {"post"}:
            if summary.patch_hash != intent["expected_worktree_diff_hash"]:
                raise RecoveryError(
                    "post-state files do not match the prepared expected diff"
                )
            return "post"
        if state_set == {"pre", "post"}:
            return "mixed"
        raise RecoveryError("prepared patch has an invalid file-state classification")

    def _restore_patch_preimages(self, intent: dict[str, Any]) -> None:
        recovery_root = self.artifacts.root / "recovery-tmp" / self.run_id
        recovery_root.mkdir(parents=True, exist_ok=True)
        for entry in intent["files"]:
            path = safe_relative_path(
                str(entry["path"]),
                field_name="prepared patch path",
            )
            artifact = Artifact.model_validate(entry["preimage_artifact"])
            preimage = self.artifacts.read_bytes(artifact)
            target = self._prepared_workspace_target(path, recovery=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = recovery_root / f"{uuid.uuid4().hex}.tmp"
            try:
                with temporary.open("xb") as stream:
                    stream.write(preimage)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temporary, int(entry["mode"]))
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        restored = WorkspaceManager.diff_summary(self.workspace)
        if (
            restored.patch_hash != intent["baseline_worktree_diff_hash"]
            or WorkspaceManager.untracked_files(self.workspace)
        ):
            raise RecoveryError(
                "prepared patch preimages did not restore the durable baseline"
            )

    def _prepared_workspace_target(
        self,
        path: str,
        *,
        recovery: bool,
    ) -> Path:
        safe = safe_relative_path(path, field_name="prepared patch path")
        root = self.workspace.resolve()
        parts = PurePosixPath(safe).parts
        target = root.joinpath(*parts)
        cursor = root
        for part in parts:
            cursor = cursor / part
            is_junction = bool(
                getattr(cursor, "is_junction", lambda: False)()
            )
            if cursor.is_symlink() or is_junction:
                message = (
                    "prepared patch path contains a symlink or junction: "
                    f"{safe}"
                )
                if recovery:
                    raise RecoveryError(message)
                raise _patch_contract_error(
                    message,
                    reason="unsupported_target",
                    stage="policy",
                )
        resolved_target = target.resolve(strict=False)
        if (
            os.path.commonpath([str(root), str(resolved_target)])
            != str(root)
        ):
            message = f"prepared patch path escapes workspace: {safe}"
            if recovery:
                raise RecoveryError(message)
            raise _patch_contract_error(
                message,
                reason="unsupported_target",
                stage="policy",
            )
        return target

    def _normalized_call_hash(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        worktree_diff_hash: str | None = None,
    ) -> str:
        summary = (
            None
            if worktree_diff_hash is not None
            else WorkspaceManager.diff_summary(self.workspace)
        )
        current_diff_hash = (
            worktree_diff_hash
            if worktree_diff_hash is not None
            else summary.patch_hash
        )
        state_marker: int | None = None
        if name == "get_diff":
            current_checks = [
                event.sequence
                for event in self.state.list_events(self.run_id)
                if event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "run_check"
                and event.payload.get("worktree_diff_hash") == current_diff_hash
            ]
            state_marker = max(current_checks, default=None)
        return sha256_text(
            canonical_json(
                {
                    "tool": name,
                    "input": arguments,
                    "worktree_diff_hash": current_diff_hash,
                    "state_marker": state_marker,
                }
            )
        )

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
        validate_inspection_arguments(
            self.workspace,
            "read_file",
            {
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
            },
        )
        target = ensure_within(self.workspace, path)
        raw = target.read_text(encoding="utf-8", errors="replace")
        lines = raw.splitlines()
        selected = lines[start_line - 1 : end_line]
        line_count = len(selected)
        actual_start_line = start_line if selected else None
        actual_end_line = (
            start_line + line_count - 1 if selected else None
        )
        result = {
            "path": path,
            "start_line": start_line,
            "end_line": end_line,
            "content": "\n".join(selected),
        }
        if self.context_policy_version not in _INVESTIGATION_CONTEXT_POLICIES:
            return result
        return {
            **result,
            "actual_start_line": actual_start_line,
            "actual_end_line": actual_end_line,
            "line_count": line_count,
            "total_lines": len(lines),
            "eof_reached": end_line >= len(lines),
            "file_content_hash": sha256_text(raw),
        }

    def _search_files(self, query: str, path_glob: str = "**/*") -> dict[str, Any]:
        validate_inspection_arguments(
            self.workspace,
            "search_files",
            {"query": query, "path_glob": path_glob},
        )
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
                        result = {
                            "query": query,
                            "matches": matches,
                            "truncated": True,
                        }
                        if (
                            self.context_policy_version
                            in _INVESTIGATION_CONTEXT_POLICIES
                        ):
                            result.update(
                                {
                                    "path_glob": path_glob,
                                    "match_count": len(matches),
                                }
                            )
                        return result
        result = {
            "query": query,
            "matches": matches,
            "truncated": False,
        }
        if self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES:
            result.update(
                {
                    "path_glob": path_glob,
                    "match_count": len(matches),
                }
            )
        return result

    def _prepare_patch_mutation(
        self,
        action_id: str,
        input_hash: str,
        patch: str,
        patch_artifact: Artifact,
    ) -> dict[str, Any]:
        if len(patch.encode("utf-8")) > 500_000:
            raise PolicyViolation(
                "patch exceeds the tool input limit",
                details={
                    "stage": "policy",
                    "reason": "input_too_large",
                    "guidance": "Reduce the patch to the smallest scoped change.",
                },
            )
        _validate_raw_git_patch(patch)
        baseline = WorkspaceManager.diff_summary(self.workspace)
        baseline_untracked = WorkspaceManager.untracked_files(self.workspace)
        if baseline_untracked:
            raise RecoveryError(
                "agent workspace contains untracked files before patch application"
            )
        paths = _patch_paths(patch)
        expected_diff_hash = self._preview_expected_diff_hash(
            patch,
            baseline.patch_hash,
        )
        if expected_diff_hash == baseline.patch_hash:
            raise PolicyViolation(
                "patch does not change the tracked worktree",
                details={
                    "stage": "policy",
                    "reason": "no_effect",
                    "guidance": "Submit a patch that changes the implicated tracked code.",
                },
            )
        files = self._prepare_file_images(patch, paths)
        intent = {
            "schema_version": "patch-mutation-intent-v1",
            "run_id": self.run_id,
            "action_id": action_id,
            "input_hash": input_hash,
            "patch_artifact": patch_artifact.model_dump(mode="json"),
            "baseline_worktree_diff_hash": baseline.patch_hash,
            "expected_worktree_diff_hash": expected_diff_hash,
            "files": files,
        }
        artifact = self.artifacts.put_json(intent)
        self.state.append_event(
            self.run_id,
            EventType.PATCH_PREPARED,
            actor="tool-gateway",
            correlation_id=action_id,
            payload={
                "schema_version": "patch-mutation-intent-v1",
                "artifact_id": artifact.artifact_id,
                "artifact_path": artifact.path,
                "content_hash": artifact.content_hash,
                "size_bytes": artifact.size_bytes,
                "intent_artifact": artifact.model_dump(mode="json"),
                "baseline_worktree_diff_hash": baseline.patch_hash,
                "expected_worktree_diff_hash": expected_diff_hash,
            },
        )
        return intent

    def _preview_expected_diff_hash(
        self,
        patch: str,
        baseline_diff_hash: str,
    ) -> str:
        with tempfile.TemporaryDirectory(prefix="patchloop-index-") as temporary:
            index_path = Path(temporary) / "index"
            object_path = Path(temporary) / "objects"
            object_path.mkdir()
            git_objects = subprocess.run(
                ["git", "rev-parse", "--git-path", "objects"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if git_objects.returncode != 0:
                raise RecoveryError(
                    "patch preview could not resolve the repository object store"
                )
            alternate_objects = Path(git_objects.stdout.strip())
            if not alternate_objects.is_absolute():
                alternate_objects = (
                    self.workspace / alternate_objects
                ).resolve()
            environment = os.environ.copy()
            environment["GIT_INDEX_FILE"] = str(index_path)
            environment["GIT_OBJECT_DIRECTORY"] = str(object_path)
            environment["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = str(
                alternate_objects
            )

            def run(*args: str, input_bytes: bytes | None = None) -> bytes:
                completed = subprocess.run(
                    ["git", *args],
                    cwd=self.workspace,
                    env=environment,
                    input=input_bytes,
                    capture_output=True,
                    check=False,
                )
                if completed.returncode != 0:
                    message = completed.stderr.decode(
                        "utf-8",
                        errors="replace",
                    ).strip()
                    raise ContractError(
                        f"patch preview failed during git {' '.join(args)}: {message}"
                    )
                return completed.stdout

            run("read-tree", "HEAD")
            run("add", "-u", "--", ".")
            baseline_patch = run(
                "diff",
                "--cached",
                "--no-ext-diff",
                "--binary",
            ).decode("utf-8", errors="strict")
            if sha256_text(baseline_patch) != baseline_diff_hash:
                raise RecoveryError(
                    "temporary patch preview does not match the current worktree"
                )
            try:
                run(
                    "apply",
                    "--cached",
                    "--recount",
                    "--whitespace=nowarn",
                    "-",
                    input_bytes=patch.encode("utf-8"),
                )
            except ContractError as exc:
                raise _patch_contract_error(
                    f"patch application failed during preparation: {exc}",
                    reason="git_apply_failed",
                    stage="context",
                ) from exc
            expected_patch = run(
                "diff",
                "--cached",
                "--no-ext-diff",
                "--binary",
            ).decode("utf-8", errors="strict")
        return sha256_text(expected_patch)

    def _hypothetical_preimage_diff_hash(
        self,
        intent: dict[str, Any],
    ) -> str:
        """Hash current tracked state with touched paths reset in a temp index."""

        with tempfile.TemporaryDirectory(
            prefix="patchloop-reconcile-index-"
        ) as temporary:
            index_path = Path(temporary) / "index"
            object_path = Path(temporary) / "objects"
            object_path.mkdir()
            git_objects = subprocess.run(
                ["git", "rev-parse", "--git-path", "objects"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if git_objects.returncode != 0:
                raise RecoveryError(
                    "mixed-state preview could not resolve the object store"
                )
            alternate_objects = Path(git_objects.stdout.strip())
            if not alternate_objects.is_absolute():
                alternate_objects = (
                    self.workspace / alternate_objects
                ).resolve()
            environment = os.environ.copy()
            environment["GIT_INDEX_FILE"] = str(index_path)
            environment["GIT_OBJECT_DIRECTORY"] = str(object_path)
            environment["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = str(
                alternate_objects
            )

            def run(
                *args: str,
                input_bytes: bytes | None = None,
            ) -> bytes:
                completed = subprocess.run(
                    ["git", *args],
                    cwd=self.workspace,
                    env=environment,
                    input=input_bytes,
                    capture_output=True,
                    check=False,
                )
                if completed.returncode != 0:
                    message = completed.stderr.decode(
                        "utf-8",
                        errors="replace",
                    ).strip()
                    raise RecoveryError(
                        "mixed-state preview failed during "
                        f"git {' '.join(args)}: {message}"
                    )
                return completed.stdout

            run("read-tree", "HEAD")
            run("add", "-u", "--", ".")
            for entry in intent["files"]:
                path = safe_relative_path(
                    str(entry["path"]),
                    field_name="prepared patch path",
                )
                preimage = self.artifacts.read_bytes(
                    Artifact.model_validate(entry["preimage_artifact"])
                )
                object_id = run(
                    "hash-object",
                    "-w",
                    "--stdin",
                    input_bytes=preimage,
                ).decode("ascii").strip()
                run(
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    str(entry["git_mode"]),
                    object_id,
                    path,
                )
            patch = run(
                "diff",
                "--cached",
                "--no-ext-diff",
                "--binary",
            ).decode("utf-8", errors="strict")
        return sha256_text(patch)

    def _prepare_file_images(
        self,
        patch: str,
        paths: list[str],
    ) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix="patchloop-preview-") as temporary:
            scratch = Path(temporary)
            initialize = subprocess.run(
                ["git", "init", "--quiet"],
                cwd=scratch,
                capture_output=True,
                check=False,
            )
            if initialize.returncode != 0:
                raise RecoveryError("patch preview repository initialization failed")
            for path in paths:
                source = self._prepared_workspace_target(
                    path,
                    recovery=False,
                )
                tracked = subprocess.run(
                    ["git", "ls-files", "--stage", "-z", "--", path],
                    cwd=self.workspace,
                    capture_output=True,
                    check=False,
                )
                tracked_entries = [
                    item
                    for item in tracked.stdout.split(b"\0")
                    if item
                ]
                git_mode = None
                if len(tracked_entries) == 1:
                    try:
                        stage, tracked_path = tracked_entries[0].split(
                            b"\t",
                            1,
                        )
                        stage_fields = stage.decode("ascii").split()
                        decoded_path = tracked_path.decode("utf-8")
                        if (
                            len(stage_fields) == 3
                            and stage_fields[2] == "0"
                            and decoded_path.replace("\\", "/") == path
                        ):
                            git_mode = stage_fields[0]
                    except (UnicodeDecodeError, ValueError):
                        git_mode = None
                source_stat = source.lstat() if source.exists() else None
                if (
                    tracked.returncode != 0
                    or git_mode not in {"100644", "100755"}
                    or source_stat is None
                    or not stat.S_ISREG(source_stat.st_mode)
                ):
                    raise _patch_contract_error(
                        f"patch target must be an existing tracked regular file: {path}",
                        reason="unsupported_target",
                        stage="policy",
                    )
                preimage = source.read_bytes()
                pre_artifact = self.artifacts.put_bytes(preimage)
                target = ensure_within(scratch, path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(preimage)
                os.chmod(target, stat.S_IMODE(source_stat.st_mode))
                entries.append(
                    {
                        "path": path,
                        "mode": stat.S_IMODE(source_stat.st_mode),
                        "git_mode": git_mode,
                        "preimage_artifact": pre_artifact.model_dump(mode="json"),
                    }
                )

            completed = subprocess.run(
                ["git", "apply", "--recount", "--whitespace=nowarn", "-"],
                cwd=scratch,
                input=patch.encode("utf-8"),
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                error = completed.stderr.decode(
                    "utf-8",
                    errors="replace",
                ).strip()
                raise _patch_contract_error(
                    f"patch preview application failed: {error}",
                    reason="git_apply_failed",
                    stage="context",
                )
            for entry in entries:
                target = ensure_within(scratch, str(entry["path"]))
                entry["postimage_artifact"] = (
                    self.artifacts.put_bytes(target.read_bytes()).model_dump(
                        mode="json"
                    )
                    if target.exists()
                    else None
                )
        return entries

    def _apply_patch(
        self,
        patch: str,
        *,
        intent: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if len(patch.encode("utf-8")) > 500_000:
            raise PolicyViolation(
                "patch exceeds the tool input limit",
                details={
                    "stage": "policy",
                    "reason": "input_too_large",
                    "guidance": "Reduce the patch to the smallest scoped change.",
                },
            )
        _validate_raw_git_patch(patch)
        baseline = WorkspaceManager.diff_summary(self.workspace)
        baseline_untracked = WorkspaceManager.untracked_files(self.workspace)
        if baseline_untracked:
            raise RecoveryError(
                "agent workspace contains untracked files before patch application"
            )
        expected_diff_hash = None
        if intent is not None:
            if (
                intent.get("baseline_worktree_diff_hash")
                != baseline.patch_hash
            ):
                raise RecoveryError(
                    "prepared patch baseline does not match the current worktree"
                )
            expected_diff_hash = intent.get("expected_worktree_diff_hash")
            self._apply_patch_postimages(intent)
        else:
            completed = subprocess.run(
                ["git", "apply", "--recount", "--whitespace=nowarn", "-"],
                cwd=self.workspace,
                input=patch.encode("utf-8"),
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                error = completed.stderr.decode(
                    "utf-8",
                    errors="replace",
                ).strip()
                line_match = re.search(
                    r"(?:corrupt patch at line|patch at line) (\d+)",
                    error,
                )
                raise _patch_contract_error(
                    f"patch application failed: {error}",
                    reason="git_apply_failed",
                    stage="syntax" if line_match else "context",
                    line=(
                        int(line_match.group(1))
                        if line_match
                        else None
                    ),
                )
        return self._finalize_applied_patch(
            patch,
            baseline.patch_hash,
            expected_diff_hash=expected_diff_hash,
            intent=intent,
        )

    def _apply_patch_postimages(self, intent: dict[str, Any]) -> None:
        recovery_root = self.artifacts.root / "recovery-tmp" / self.run_id
        recovery_root.mkdir(parents=True, exist_ok=True)
        prepared: list[tuple[dict[str, Any], str, Path, bytes | None]] = []
        for entry in intent["files"]:
            try:
                path = safe_relative_path(
                    str(entry["path"]),
                    field_name="prepared patch path",
                )
                target = self._prepared_workspace_target(
                    path,
                    recovery=True,
                )
                preimage = self.artifacts.read_bytes(
                    Artifact.model_validate(entry["preimage_artifact"])
                )
                mode = int(entry["mode"])
                post_raw = entry.get("postimage_artifact")
                postimage = (
                    self.artifacts.read_bytes(
                        Artifact.model_validate(post_raw)
                    )
                    if post_raw is not None
                    else None
                )
                target_stat = (
                    target.lstat() if target.exists() else None
                )
            except (ContractError, KeyError, TypeError, ValueError) as exc:
                raise RecoveryError(
                    "prepared patch contains invalid file image evidence"
                ) from exc
            if target_stat is None or not stat.S_ISREG(target_stat.st_mode):
                raise RecoveryError(
                    f"prepared patch target is not in its pre-state: {path}"
                )
            if (
                target.read_bytes() != preimage
                or stat.S_IMODE(target_stat.st_mode) != mode
            ):
                raise RecoveryError(
                    f"prepared patch target is not in its pre-state: {path}"
                )
            prepared.append((entry, path, target, postimage))

        try:
            for entry, _, target, postimage in prepared:
                if postimage is None:
                    target.unlink()
                    continue
                temporary = recovery_root / f"{uuid.uuid4().hex}.tmp"
                try:
                    with temporary.open("xb") as stream:
                        stream.write(postimage)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.chmod(temporary, int(entry["mode"]))
                    os.replace(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)
        except Exception as exc:
            try:
                self._restore_patch_preimages(intent)
            except Exception as rollback_error:
                raise RecoveryError(
                    "prepared patch write failed and preimage restoration failed"
                ) from rollback_error
            raise RecoveryError(
                "prepared patch write failed; preimages were restored"
            ) from exc

    def _finalize_applied_patch(
        self,
        patch: str,
        baseline_diff_hash: str,
        *,
        expected_diff_hash: str | None = None,
        intent: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            summary = WorkspaceManager.diff_summary(self.workspace)
            if (
                expected_diff_hash is not None
                and summary.patch_hash != expected_diff_hash
            ):
                raise RecoveryError(
                    "applied patch does not match its prepared post-state"
                )
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
            self._rollback_patch(
                patch,
                baseline_diff_hash,
                intent=intent,
            )
            raise
        if violations:
            self._rollback_patch(
                patch,
                baseline_diff_hash,
                intent=intent,
            )
            raise PolicyViolation(
                "; ".join(violations),
                details={
                    "stage": "policy",
                    "reason": "deterministic_policy_violation",
                    "guidance": "Limit the patch to the declared task scope and retry.",
                },
            )
        return {
            "patch_hash": sha256_text(patch),
            "worktree_diff_hash": summary.patch_hash,
            "changed_files": summary.changed_files,
            "diff_lines": summary.diff_lines,
        }

    def _rollback_patch(
        self,
        patch: str,
        baseline_diff_hash: str,
        *,
        intent: dict[str, Any] | None = None,
    ) -> None:
        if intent is not None:
            self._restore_patch_preimages(intent)
            return
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
        before = WorkspaceManager.diff_summary(self.workspace)
        outcome = self.sandbox.run_check(self.workspace, checks[check_id])
        after = WorkspaceManager.diff_summary(self.workspace)
        if before.patch_hash != after.patch_hash:
            raise RecoveryError("registered check modified the tracked worktree")
        return {
            "check_id": check_id,
            "exit_code": outcome.exit_code,
            "passed": not outcome.timed_out
            and outcome.exit_code in checks[check_id].expected_exit_codes,
            "timed_out": outcome.timed_out,
            "truncated": outcome.truncated,
            "stdout": outcome.stdout,
            "stderr": outcome.stderr,
            "worktree_diff_hash": before.patch_hash,
        }

    def _get_diff(self) -> dict[str, Any]:
        summary = WorkspaceManager.diff_summary(self.workspace)
        return {
            "patch": summary.patch,
            "patch_hash": summary.patch_hash,
            "worktree_diff_hash": summary.patch_hash,
            "changed_files": summary.changed_files,
            "added_lines": summary.added_lines,
            "deleted_lines": summary.deleted_lines,
        }
