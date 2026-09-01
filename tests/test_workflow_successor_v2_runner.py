from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V11,
    LEAN_RUNTIME_POLICY_VERSION_V12,
    LEAN_RUNTIME_POLICY_VERSION_V13,
    LEAN_RUNTIME_POLICY_VERSION_V14,
    LEAN_RUNTIME_POLICY_VERSION_V15,
    LEAN_RUNTIME_POLICY_VERSION_V16,
    LEAN_RUNTIME_POLICY_VERSION_V17,
    LEAN_RUNTIME_POLICY_VERSION_V18,
    LEAN_RUNTIME_POLICY_VERSION_V19,
    LEAN_RUNTIME_POLICY_VERSION_V20,
    LEAN_RUNTIME_POLICY_VERSION_V21,
    build_lean_harness_calibration_manifest,
)
from patchloop.agent.model import ModelTurn, RequestedTool
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import ToolGateway
from patchloop.agent.workflow_causal_alternative_successor import CAUSAL_ALTERNATIVE_POLICY
from patchloop.agent.workflow_successor_v2 import WORK_PLAN_ADMISSION_POLICY
from patchloop.contracts import EventType, MemoryCondition, Phase
from patchloop.sandbox import LocalSandbox, SandboxResult
from patchloop.task_loader import load_task_package

TASK_PATH = "tasks/smoke/config-falsy-override/public.yaml"
TARGET_PATH = "mini_data_utils/config.py"


class _FailFirstVisibleCheckSandbox:
    official = False

    def __init__(self) -> None:
        self.delegate = LocalSandbox()
        self.calls = 0

    def run_check(self, workspace, check):
        self.calls += 1
        if self.calls == 1:
            return SandboxResult(
                command=list(check.command),
                exit_code=1,
                stdout="",
                stderr="injected public failure before semantic correction",
                duration_ms=1,
                timed_out=False,
                truncated=False,
                original_output_bytes=50,
            )
        return self.delegate.run_check(workspace, check)


class _FailFirstTwoVisibleChecksSandbox(_FailFirstVisibleCheckSandbox):
    def run_check(self, workspace, check):
        self.calls += 1
        if self.calls <= 2:
            return SandboxResult(
                command=list(check.command),
                exit_code=1,
                stdout="",
                stderr="same bounded public failure signature",
                duration_ms=1,
                timed_out=False,
                truncated=False,
                original_output_bytes=37,
            )
        return self.delegate.run_check(workspace, check)


class _FailFirstThreeVisibleChecksSandbox(_FailFirstVisibleCheckSandbox):
    def run_check(self, workspace, check):
        self.calls += 1
        if self.calls <= 3:
            return SandboxResult(
                command=list(check.command),
                exit_code=1,
                stdout="",
                stderr="same bounded public failure signature",
                duration_ms=1,
                timed_out=False,
                truncated=False,
                original_output_bytes=37,
            )
        return self.delegate.run_check(workspace, check)


def _manifest(*, run_id: str, version: int):
    package = load_task_package("tasks/smoke/config-falsy-override")
    return build_lean_harness_calibration_manifest(
        package,
        run_id=run_id,
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=(
            LEAN_RUNTIME_POLICY_VERSION_V16
            if version == 16
            else LEAN_RUNTIME_POLICY_VERSION_V15
            if version == 15
            else LEAN_RUNTIME_POLICY_VERSION_V14
            if version == 14
            else LEAN_RUNTIME_POLICY_VERSION_V13
            if version == 13
            else LEAN_RUNTIME_POLICY_VERSION_V12
            if version == 12
            else LEAN_RUNTIME_POLICY_VERSION_V11
        ),
    )


class _ContextOnlyWorkflowAdapter:
    """Choose actions only from the request context and dynamic schema."""

    def __init__(
        self,
        *,
        prefix: str,
        fail_first_mutation: bool = False,
        invalid_plans: bool = False,
        crash_after_first_rejection: bool = False,
        review_correction: bool = False,
        crash_on_active_plan: bool = False,
        duplicate_candidate_bindings: bool = False,
    ) -> None:
        self.prefix = prefix
        self.fail_first_mutation = fail_first_mutation
        self.invalid_plans = invalid_plans
        self.crash_after_first_rejection = crash_after_first_rejection
        self.review_correction = review_correction
        self.crash_on_active_plan = crash_on_active_plan
        self.duplicate_candidate_bindings = duplicate_candidate_bindings
        self.calls = 0
        self.mutations = 0
        self.invalid_plan_calls = 0
        self.review_edit_pending = False
        self.review_correction_done = False

    def _action_id(self, label: str) -> str:
        return f"{self.prefix}-{self.calls}-{label}"

    @staticmethod
    def _catalog(workflow: dict) -> tuple[list[dict], dict]:
        catalog = workflow["eligible_plan_evidence_catalog"]
        items = catalog["items"]
        source = next(item for item in items if item["kind"] == "source_read")
        return items, source

    @staticmethod
    def _plan_arguments(workflow: dict, *, revision: bool) -> dict:
        items, source = _ContextOnlyWorkflowAdapter._catalog(workflow)
        foundation_ids = [item["evidence_id"] for item in items if item["role"] == "foundation"]
        if revision:
            trigger = next(
                item
                for item in items
                if item["evidence_id"] == workflow["required_trigger_evidence_id"]
            )
            status = (
                "review_diff" if trigger["kind"] == "diff_review_result" else "visible_check_failed"
            )
        else:
            targeted = next(
                (item for item in items if item["kind"] == "targeted_check_result"),
                None,
            )
            status = (
                "targeted_check_failed"
                if targeted is not None and targeted["check"]["behavior_status"] == "failed"
                else "targeted_check_passed"
                if targeted is not None
                else "static_source"
            )
        body = {
            "observation_status": status,
            "hypothesis": "Explicit falsey overrides are discarded by the truthiness fallback.",
            "foundation_evidence_ids": foundation_ids,
            "supporting_evidence_ids": [],
            "candidate_files": [
                {
                    "path": source["source"]["path"],
                    "read_evidence_id": source["evidence_id"],
                }
            ],
            "intended_change": "Assign every explicitly supplied override value directly.",
            "expected_behavior": "False, zero, empty strings, and empty lists replace base values.",
            "unknowns": [],
        }
        if revision:
            body["prior_hypothesis_disposition"] = (
                workflow.get("required_prior_hypothesis_disposition") or "refined"
            )
        return body

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        self.calls += 1
        payload = json.loads(context)
        workflow = payload["workflow"]
        names = tuple(item["name"] for item in tools)
        assert workflow["available_tool_names"] == list(names)

        if self.crash_on_active_plan and workflow["active_work_plan"] is not None:
            self.crash_on_active_plan = False
            raise SystemExit(86)

        if (
            self.crash_after_first_rejection
            and self.invalid_plan_calls == 1
            and "record_work_plan" in names
        ):
            raise SystemExit(86)
        if "record_work_plan" in names:
            arguments = self._plan_arguments(workflow, revision=False)
            if self.duplicate_candidate_bindings:
                arguments["candidate_files"] = [
                    arguments["candidate_files"][0],
                    dict(arguments["candidate_files"][0]),
                ]
            if self.invalid_plans:
                arguments["foundation_evidence_ids"] = ["pev:999999"]
                self.invalid_plan_calls += 1
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "record_work_plan",
                        self._action_id("record"),
                        arguments,
                    )
                ]
            )
        if "revise_work_plan" in names:
            arguments = self._plan_arguments(workflow, revision=True)
            if arguments["observation_status"] == "review_diff":
                self.review_edit_pending = True
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "revise_work_plan",
                        self._action_id("revise"),
                        arguments,
                    )
                ]
            )
        if "finish_task" in names and not (
            self.review_correction and not self.review_correction_done
        ):
            return ModelTurn(
                tool_calls=[RequestedTool("finish_task", self._action_id("finish"), {})]
            )
        if "apply_structured_edit" in names:
            self.mutations += 1
            if self.review_edit_pending:
                expected = "result[key] = value"
                replacement = "result[key] = value  # explicit override"
                self.review_edit_pending = False
                self.review_correction_done = True
            else:
                wrong = self.fail_first_mutation and self.mutations == 1
                expected = (
                    "result[key] = value or result.get(key)"
                    if self.mutations == 1
                    else "result[key] = value"
                    if self.mutations >= 3
                    else "result[key] = value or result.get(key)  # inspected"
                )
                replacement = (
                    "result[key] = value or result.get(key)  # inspected"
                    if wrong
                    else "result[key] = value  # semantic reset"
                    if self.mutations >= 3
                    else "result[key] = value"
                )
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "apply_structured_edit",
                        self._action_id("edit"),
                        {
                            "schema_version": "structured-edit-arguments-v2",
                            "files": [
                                {
                                    "path": TARGET_PATH,
                                    "replacements": [
                                        {
                                            "expected_text": expected,
                                            "replacement_text": replacement,
                                        }
                                    ],
                                }
                            ],
                        },
                    )
                ]
            )
        if "read_file" in names:
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "read_file",
                        self._action_id("read"),
                        {"path": TARGET_PATH, "start_line": 1, "end_line": 120},
                    )
                ]
            )
        if "search_files" in names:
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "search_files",
                        self._action_id("search"),
                        {"query": "result[key]", "path_glob": "mini_data_utils/**/*.py"},
                    )
                ]
            )
        if "run_check" in names:
            schema = next(item for item in tools if item["name"] == "run_check")
            check_id = schema["parameters"]["properties"]["check_id"]["enum"][0]
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "run_check",
                        self._action_id("check"),
                        {"check_id": check_id},
                    )
                ]
            )
        if names == ("get_diff",):
            return ModelTurn(tool_calls=[RequestedTool("get_diff", self._action_id("diff"), {})])
        raise AssertionError(f"unexpected V11/V12 tool surface: {names}")


class _InvalidSemanticResetAdapter(_ContextOnlyWorkflowAdapter):
    @staticmethod
    def _plan_arguments(workflow: dict, *, revision: bool) -> dict:
        body = _ContextOnlyWorkflowAdapter._plan_arguments(workflow, revision=revision)
        if revision and workflow.get("required_prior_hypothesis_disposition") == "rejected":
            body["prior_hypothesis_disposition"] = "refined"
        return body


class _CrashBeforeSemanticResetRevisionAdapter(_ContextOnlyWorkflowAdapter):
    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        workflow = json.loads(context)["workflow"]
        if workflow.get("required_prior_hypothesis_disposition") == "rejected" and any(
            item["name"] == "revise_work_plan" for item in tools
        ):
            raise SystemExit(86)
        return super().next_turn(context, tools)


class _CausalContextWorkflowAdapter(_ContextOnlyWorkflowAdapter):
    """Exercise V17 using only its public workflow projection and dynamic schema."""

    def __init__(
        self,
        *,
        prefix: str,
        crash_on_cross_reset: bool = False,
        invalid_cross_reset: bool = False,
    ) -> None:
        super().__init__(prefix=prefix, fail_first_mutation=True)
        self.crash_on_cross_reset = crash_on_cross_reset
        self.invalid_cross_reset = invalid_cross_reset
        self.cross_reset_plan_recorded = False

    @staticmethod
    def _mechanism(workflow: dict, *, alternative: bool) -> dict:
        _, source = _ContextOnlyWorkflowAdapter._catalog(workflow)
        source_path = source["source"]["path"]
        evidence_id = source["evidence_id"]

        def location(line: int) -> dict:
            return {
                "path": source_path,
                "start_line": line,
                "end_line": line,
                "read_evidence_id": evidence_id,
                "symbol": None,
            }

        path = (
            [
                {
                    "role": "causal_boundary",
                    "location": location(5),
                    "observation": "Override values enter the merge loop through this boundary.",
                    "relationship_to_next": "The loop assigns each value at the mutation site.",
                },
                {
                    "role": "mutation_site",
                    "location": location(11),
                    "observation": "Truthiness fallback discards explicit falsey values.",
                    "relationship_to_next": None,
                },
            ]
            if alternative
            else [
                {
                    "role": "boundary_and_mutation_site",
                    "location": location(11),
                    "observation": "Truthiness fallback discards explicit falsey values.",
                    "relationship_to_next": None,
                }
            ]
        )
        return {
            "summary": "The merge path replaces explicit falsey values with prior values.",
            "causal_path": path,
            "mutation_site_rationale": (
                "The assignment is the smallest source location that controls the result."
            ),
            "expected_observable_effect": "Explicit falsey values remain present after merge.",
            "falsification_condition": (
                "The targeted check still reports a discarded falsey override."
            ),
        }

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        payload = json.loads(context)
        workflow = payload["workflow"]
        names = tuple(item["name"] for item in tools)
        cross_reset = workflow.get("cross_reset_failure_trigger") is not None
        if cross_reset and self.crash_on_cross_reset:
            self.crash_on_cross_reset = False
            raise SystemExit(86)
        if "record_work_plan" in names or "revise_work_plan" in names:
            self.calls += 1
            revision = "revise_work_plan" in names
            tool_name = "revise_work_plan" if revision else "record_work_plan"
            if cross_reset:
                items, source = self._catalog(workflow)
                arguments = {
                    "observation_status": "visible_check_failed",
                    "hypothesis": "The restored baseline requires a different causal boundary.",
                    "foundation_evidence_ids": [
                        item["evidence_id"] for item in items if item["role"] == "foundation"
                    ],
                    "supporting_evidence_ids": [],
                    "candidate_files": [
                        {
                            "path": source["source"]["path"],
                            "read_evidence_id": source["evidence_id"],
                        }
                    ],
                    "intended_change": "Replace the falsey fallback at the assignment boundary.",
                    "expected_behavior": "Explicit falsey values replace prior values.",
                    "unknowns": [],
                    "prior_causal_mechanism_hash": workflow["causal_mechanism_history"][-1][
                        "mechanism"
                    ]["content_hash"],
                    "alternative_causal_mechanism": self._mechanism(
                        workflow, alternative=not self.invalid_cross_reset
                    ),
                }
                self.cross_reset_plan_recorded = True
            else:
                arguments = self._plan_arguments(workflow, revision=revision)
                arguments["causal_mechanism"] = self._mechanism(workflow, alternative=False)
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        tool_name,
                        self._action_id("causal-plan"),
                        arguments,
                    )
                ]
            )
        if "apply_structured_edit" in names and self.cross_reset_plan_recorded:
            self.calls += 1
            self.mutations += 1
            self.cross_reset_plan_recorded = False
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "apply_structured_edit",
                        self._action_id("alternative-edit"),
                        {
                            "schema_version": "structured-edit-arguments-v2",
                            "files": [
                                {
                                    "path": TARGET_PATH,
                                    "replacements": [
                                        {
                                            "expected_text": (
                                                "result[key] = value or result.get(key)"
                                            ),
                                            "replacement_text": "result[key] = value",
                                        }
                                    ],
                                }
                            ],
                        },
                    )
                ]
            )
        return super().next_turn(context, tools)


class _CausalProjectionWorkflowAdapter(_ContextOnlyWorkflowAdapter):
    """Exercise V18 using only its cspan catalog and semantic input schema."""

    def __init__(
        self,
        *,
        prefix: str,
        invalid_cross_reset: bool = False,
        crash_on_cross_reset: bool = False,
    ) -> None:
        super().__init__(prefix=prefix, fail_first_mutation=True)
        self.invalid_cross_reset = invalid_cross_reset
        self.crash_on_cross_reset = crash_on_cross_reset
        self.cross_reset_plan_recorded = False
        self.plan_arguments: list[dict] = []

    @staticmethod
    def _projection_arguments(workflow: dict, *, revision: bool) -> dict:
        activated = workflow["causal_plan_request_projection"]
        spans = activated["source_projection"]["source_span_catalog"]["spans"]
        history = workflow["causal_mechanism_history"]
        exhausted = {
            item["mechanism"]["causal_path"][0]["source_span"]["coverage_key"] for item in history
        }
        cross_reset = workflow.get("cross_reset_failure_trigger") is not None
        eligible = [item for item in spans if item["coverage_key"] not in exhausted]
        selected = eligible[-1] if cross_reset and eligible else spans[-1]
        span_id = selected["source_span_id"]
        return {
            "hypothesis": ("The evidence-bound merge assignment controls explicit falsey values."),
            "supporting_evidence_ids": [],
            "candidate_source_span_ids": [span_id],
            "intended_change": "Assign the supplied value without a truthiness fallback.",
            "expected_behavior": "Explicit falsey values replace prior values.",
            "unknowns": [],
            "prior_hypothesis_disposition": (
                workflow.get("required_prior_hypothesis_disposition") or "refined"
                if revision
                else None
            ),
            "causal_mechanism": {
                "summary": "The merge assignment directly commits the public result.",
                "causal_boundary": {
                    "source_span_id": span_id,
                    "symbol": None,
                    "observation": "This source span receives and commits the override.",
                    "relationship_to_next": (
                        "The same evidenced assignment is the minimal mutation site."
                    ),
                },
                "intermediate_steps": [],
                "mutation_site": {
                    "source_span_id": span_id,
                    "symbol": None,
                    "observation": "The assignment determines the visible merged value.",
                },
                "mutation_site_rationale": (
                    "Changing this assignment removes the falsey-value fallback."
                ),
                "expected_observable_effect": "The targeted check retains falsey overrides.",
                "falsification_condition": "The targeted check still discards a falsey value.",
            },
        }

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        payload = json.loads(context)
        workflow = payload["workflow"]
        names = tuple(item["name"] for item in tools)
        cross_reset = workflow.get("cross_reset_failure_trigger") is not None
        if cross_reset and self.crash_on_cross_reset:
            self.crash_on_cross_reset = False
            raise SystemExit(86)
        if "record_work_plan" in names or "revise_work_plan" in names:
            self.calls += 1
            revision = "revise_work_plan" in names
            tool_name = "revise_work_plan" if revision else "record_work_plan"
            arguments = self._projection_arguments(workflow, revision=revision)
            if cross_reset:
                self.cross_reset_plan_recorded = True
                if self.invalid_cross_reset:
                    exhausted_span = workflow["causal_mechanism_history"][-1]["mechanism"][
                        "causal_path"
                    ][0]["source_span"]["source_span_id"]
                    arguments["candidate_source_span_ids"] = [exhausted_span]
                    arguments["causal_mechanism"]["causal_boundary"]["source_span_id"] = (
                        exhausted_span
                    )
                    arguments["causal_mechanism"]["mutation_site"]["source_span_id"] = (
                        exhausted_span
                    )
            self.plan_arguments.append(arguments)
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        tool_name,
                        self._action_id("projected-plan"),
                        arguments,
                    )
                ]
            )
        if "apply_structured_edit" in names and self.cross_reset_plan_recorded:
            self.calls += 1
            self.mutations += 1
            self.cross_reset_plan_recorded = False
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "apply_structured_edit",
                        self._action_id("projected-alternative-edit"),
                        {
                            "schema_version": "structured-edit-arguments-v2",
                            "files": [
                                {
                                    "path": TARGET_PATH,
                                    "replacements": [
                                        {
                                            "expected_text": (
                                                "result[key] = value or result.get(key)"
                                            ),
                                            "replacement_text": "result[key] = value",
                                        }
                                    ],
                                }
                            ],
                        },
                    )
                ]
            )
        if "read_file" in names and cross_reset:
            self.calls += 1
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "read_file",
                        self._action_id("narrow-read"),
                        {"path": TARGET_PATH, "start_line": 8, "end_line": 12},
                    )
                ]
            )
        return super().next_turn(context, tools)


class _ExplorationProjectionWorkflowAdapter(_CausalProjectionWorkflowAdapter):
    """Exercise V19 using two distinct request-visible current-source ranges."""

    def __init__(
        self,
        *,
        prefix: str,
        invalid_closure: bool = False,
        fail_first_mutation: bool = False,
    ) -> None:
        super().__init__(prefix=prefix)
        self.fail_first_mutation = fail_first_mutation
        self.invalid_closure = invalid_closure
        self.public_reads = 0

    @staticmethod
    def _exploration_arguments(workflow: dict) -> dict:
        activated = workflow["activated_exploration_plan_request"]
        spans = activated["source_request"]["base_request"]["source_projection"][
            "source_span_catalog"
        ]["spans"]
        distinct: list[dict] = []
        seen: set[str] = set()
        for span in spans:
            if span["coverage_key"] in seen:
                continue
            seen.add(span["coverage_key"])
            distinct.append(span)
        assert len(distinct) >= 2
        boundary, mutation = distinct[0], distinct[-1]
        if workflow.get("cross_reset_failure_trigger") is not None:
            exhausted = {
                item["mechanism"]["causal_path"][0]["source_span"]["coverage_key"]
                for item in workflow["causal_mechanism_history"]
            }
            boundary = next(item for item in distinct if item["coverage_key"] not in exhausted)
            mutation = next(
                item
                for item in reversed(distinct)
                if item["coverage_key"] != boundary["coverage_key"]
            )
        boundary_id = boundary["source_span_id"]
        mutation_id = mutation["source_span_id"]
        return {
            "hypothesis": "The merge assignment controls preservation of explicit falsey values.",
            "supporting_evidence_ids": [],
            "candidate_source_span_ids": [mutation_id],
            "intended_change": "Assign the explicit override without a truthiness fallback.",
            "expected_behavior": "Explicit falsey override values remain present.",
            "unknowns": [],
            "prior_hypothesis_disposition": None,
            "causal_mechanism": {
                "summary": "The merge loop reaches the assignment that commits each override.",
                "causal_boundary": {
                    "source_span_id": boundary_id,
                    "symbol": None,
                    "observation": "The loop owns traversal of supplied override values.",
                    "relationship_to_next": "Each value reaches the merge assignment.",
                },
                "intermediate_steps": [],
                "mutation_site": {
                    "source_span_id": mutation_id,
                    "symbol": None,
                    "observation": "The assignment commits or discards the explicit value.",
                },
                "mutation_site_rationale": "The assignment is the minimal behavioral boundary.",
                "expected_observable_effect": "The targeted check retains falsey overrides.",
                "falsification_condition": "A falsey override is still replaced by the old value.",
            },
            "exploration_state": {
                "boundary_coverage": {
                    "ownership_boundary_span_ids": [boundary_id],
                    "execution_boundary_span_ids": [boundary_id, mutation_id],
                    "mutation_boundary_span_ids": [mutation_id],
                },
                "invariants": [
                    {
                        "subject": "Public merge ownership",
                        "claim": "Traversal and assignment jointly own the visible merge result.",
                        "evidence_source_span_ids": [boundary_id, mutation_id],
                    }
                ],
                "preservation_obligations": [
                    {
                        "public_requirement": "Preserve ordinary override traversal.",
                        "expected_behavior": "Non-falsey and falsey values follow the same loop.",
                        "evidence_source_span_ids": [boundary_id, mutation_id],
                    }
                ],
                "unknown_dispositions": [],
                "open_blocking_unknowns": [],
            },
        }

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        workflow = json.loads(context)["workflow"]
        names = tuple(item["name"] for item in tools)
        if "record_work_plan" in names or "revise_work_plan" in names:
            self.calls += 1
            revision = "revise_work_plan" in names
            tool_name = "revise_work_plan" if revision else "record_work_plan"
            arguments = self._exploration_arguments(workflow)
            if revision:
                arguments["prior_hypothesis_disposition"] = (
                    workflow.get("required_prior_hypothesis_disposition") or "refined"
                )
            if workflow.get("cross_reset_failure_trigger") is not None:
                self.cross_reset_plan_recorded = True
            if self.invalid_closure:
                arguments["exploration_state"]["open_blocking_unknowns"] = [
                    "The mutation owner is still unresolved."
                ]
            self.plan_arguments.append(arguments)
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        tool_name,
                        self._action_id("exploration-plan"),
                        arguments,
                    )
                ]
            )
        if (
            "read_file" in names
            and workflow["target"] in {"pre-mutation-exploration", "correction-investigation"}
            and workflow.get("activated_exploration_plan_request") is None
        ):
            self.calls += 1
            self.public_reads += 1
            start_line, end_line = (1, 8) if self.public_reads % 2 == 1 else (9, 20)
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "read_file",
                        self._action_id("boundary-read"),
                        {
                            "path": TARGET_PATH,
                            "start_line": start_line,
                            "end_line": end_line,
                        },
                    )
                ]
            )
        return super().next_turn(context, tools)


class _CrashOnPostRestoreRevisionAdapter(_ExplorationProjectionWorkflowAdapter):
    """Crash after the post-restore third failure exposes its revision gate."""

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        workflow = json.loads(context)["workflow"]
        semantic = workflow.get("semantic_progress_state")
        if (
            not getattr(self, "post_restore_revision_crashed", False)
            and "revise_work_plan" in {item["name"] for item in tools}
            and workflow.get("cross_reset_failure_trigger") is None
            and len(workflow.get("causal_mechanism_history", [])) >= 3
            and semantic is not None
            and semantic.get("same_signature_failed_diff_count") == 1
        ):
            self.post_restore_revision_crashed = True
            raise SystemExit(86)
        return super().next_turn(context, tools)


@pytest.mark.parametrize("version", [11, 12, 13, 14, 15, 16])
def test_v11_v12_v13_v14_context_only_initial_plan_completes(
    tmp_path, monkeypatch, version
) -> None:
    manifest = _manifest(run_id=f"run_v{version}_context_only", version=version)
    runner = AgentRunner(tmp_path / f"runtime-v{version}")
    adapter = _ContextOnlyWorkflowAdapter(prefix=f"v{version}")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    patches = [event for event in events if event.type == EventType.PATCH_APPLIED]
    assert len(plans) == 1
    assert plans[0].payload["revision_index"] == 0
    assert patches[0].payload["plan_hash"] == plans[0].payload["plan_hash"]
    assert not any(
        event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == WORK_PLAN_ADMISSION_POLICY
        for event in events
    )


def test_v16_same_path_candidate_binding_is_normalized_and_durable(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _manifest(run_id="run_v16_candidate_binding_e2e", version=16)
    runner = AgentRunner(tmp_path / "runtime-v16-candidate-binding")
    adapter = _ContextOnlyWorkflowAdapter(
        prefix="v16-candidate-binding",
        duplicate_candidate_bindings=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plan = next(event for event in events if event.type == EventType.PLAN_RECORDED)

    assert result["scope_compliant_success"] is True
    assert plan.payload["candidate_files"] == [TARGET_PATH]
    assert plan.payload["candidate_binding_policy_version"] == (
        "same-path-public-read-binding-normalization-v1"
    )
    normalization = plan.payload["candidate_binding_normalization"]
    assert normalization["submitted_binding_count"] == 2
    assert normalization["canonical_candidate_count"] == 1
    assert normalization["path_bindings"][0]["collapsed_same_path_bindings"] is True
    succeeded = next(
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "record_work_plan"
    )
    assert (
        succeeded.payload["candidate_binding_normalization_hash"] == (normalization["content_hash"])
    )


@pytest.mark.parametrize("version", [12, 13, 14, 15, 16])
def test_v12_v13_v14_failed_check_requires_revision_then_rechecks_and_completes(
    tmp_path,
    monkeypatch,
    version,
) -> None:
    manifest = _manifest(run_id=f"run_v{version}_revision_e2e", version=version)
    runner = AgentRunner(tmp_path / f"runtime-v{version}-revision")
    adapter = _ContextOnlyWorkflowAdapter(
        prefix=f"v{version}-revision",
        fail_first_mutation=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    injected_sandbox = _FailFirstVisibleCheckSandbox()
    monkeypatch.setattr(
        "patchloop.agent.runner.LocalSandbox",
        lambda: injected_sandbox,
    )

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    patches = [event for event in events if event.type == EventType.PATCH_APPLIED]
    checks = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "run_check"
    ]

    assert result["scope_compliant_success"] is True
    assert [event.payload["trigger"] for event in plans] == ["initial", "check_failure"]
    assert plans[1].payload["parent_plan_hash"] == plans[0].payload["plan_hash"]
    assert [event.payload["plan_hash"] for event in patches] == [
        plans[0].payload["plan_hash"],
        plans[1].payload["plan_hash"],
    ]
    assert [event.payload["passed"] for event in checks] == [False, True]
    assert events[-1].type in {EventType.RUN_COMPLETED, EventType.CHECKPOINT_SAVED}


@pytest.mark.parametrize("version", [12, 13, 14, 15, 16])
def test_v12_v13_v14_review_correction_requires_revision_and_full_revalidation(
    tmp_path,
    monkeypatch,
    version,
) -> None:
    manifest = _manifest(run_id=f"run_v{version}_review_revision_e2e", version=version)
    runner = AgentRunner(tmp_path / f"runtime-v{version}-review")
    adapter = _ContextOnlyWorkflowAdapter(
        prefix=f"v{version}-review",
        review_correction=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    patches = [event for event in events if event.type == EventType.PATCH_APPLIED]
    checks = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "run_check"
    ]
    reviews = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "get_diff"
    ]

    assert result["scope_compliant_success"] is True
    assert [event.payload["trigger"] for event in plans] == ["initial", "review_correction"]
    assert plans[1].payload["parent_plan_hash"] == plans[0].payload["plan_hash"]
    assert [event.payload["plan_hash"] for event in patches] == [
        plans[0].payload["plan_hash"],
        plans[1].payload["plan_hash"],
    ]
    assert len(checks) == 2
    assert all(event.payload["passed"] is True for event in checks)
    assert len(reviews) == 2
    submission = next(event for event in events if event.type == EventType.SUBMISSION_ACCEPTED)
    assert submission.sequence > reviews[-1].sequence


@pytest.mark.parametrize("version", [12, 13, 14, 15, 16])
def test_v12_v13_v14_initial_plan_and_phase_survive_restart(tmp_path, monkeypatch, version) -> None:
    manifest = _manifest(run_id=f"run_v{version}_plan_restart", version=version)
    runner = AgentRunner(tmp_path / f"runtime-v{version}-plan-restart")
    first = _ContextOnlyWorkflowAdapter(
        prefix=f"v{version}-plan-first",
        crash_on_active_plan=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    checkpoint = runner.state.latest_checkpoint(manifest.run_id)
    assert checkpoint is not None
    assert checkpoint.phase == Phase.PLAN
    assert checkpoint.reproduction_status == "static_evidence"
    assert len(checkpoint.current_plan) == 1
    plan_hash = checkpoint.current_plan[0]

    second = _ContextOnlyWorkflowAdapter(prefix=f"v{version}-plan-second")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    assert sum(event.type == EventType.PLAN_RECORDED for event in events) == 1
    patch = next(event for event in events if event.type == EventType.PATCH_APPLIED)
    assert patch.payload["plan_hash"] == plan_hash


def test_v11_plan_admission_slot_survives_restart_and_stops_after_second_rejection(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _manifest(run_id="run_v11_plan_recovery_restart", version=11)
    runner = AgentRunner(tmp_path / "runtime-v11-recovery")
    first = _ContextOnlyWorkflowAdapter(
        prefix="v11-first",
        invalid_plans=True,
        crash_after_first_rejection=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    checkpoint = runner.state.latest_checkpoint(manifest.run_id)
    assert checkpoint is not None
    assert checkpoint.phase == Phase.REPRODUCE

    second = _ContextOnlyWorkflowAdapter(prefix="v11-second", invalid_plans=True)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)
    rejections = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == WORK_PLAN_ADMISSION_POLICY
    ]

    assert result["terminal_error"]["code"] == "WORK_PLAN_ADMISSION_REPEATED"
    assert len(rejections) == 2
    assert [event.payload["attempt"] for event in rejections] == [1, 2]
    assert not any(event.type == EventType.PATCH_APPLIED for event in events)
    assert second.calls == 1


def test_v15_repeated_public_failure_forces_search_read_and_rejected_revision(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _manifest(run_id="run_v15_semantic_reset_e2e", version=15)
    runner = AgentRunner(tmp_path / "runtime-v15-semantic-reset")
    adapter = _ContextOnlyWorkflowAdapter(
        prefix="v15-semantic-reset",
        fail_first_mutation=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    injected_sandbox = _FailFirstTwoVisibleChecksSandbox()
    monkeypatch.setattr(
        "patchloop.agent.runner.LocalSandbox",
        lambda: injected_sandbox,
    )

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    patches = [event for event in events if event.type == EventType.PATCH_APPLIED]
    checks = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "run_check"
    ]

    assert result["scope_compliant_success"] is True
    assert [event.payload["trigger"] for event in plans] == [
        "initial",
        "check_failure",
        "check_failure",
    ]
    assert [event.payload["plan"]["prior_hypothesis_disposition"] for event in plans] == [
        None,
        "refined",
        "rejected",
    ]
    assert plans[1].payload["semantic_reset_required"] is False
    assert plans[1].payload["same_signature_failed_diff_count"] == 1
    assert plans[2].payload["semantic_reset_required"] is True
    assert plans[2].payload["same_signature_failed_diff_count"] == 2
    assert [event.payload["passed"] for event in checks] == [False, False, True]
    second_failure_sequence = checks[1].sequence
    reset_plan_sequence = plans[2].sequence
    reset_tools = [
        event.payload.get("tool")
        for event in events
        if second_failure_sequence < event.sequence < reset_plan_sequence
        and event.type == EventType.TOOL_SUCCEEDED
    ]
    assert reset_tools == ["read_file", "search_files"]
    assert [event.payload["plan_hash"] for event in patches] == [
        event.payload["plan_hash"] for event in plans
    ]


def test_v15_invalid_semantic_reset_revision_consumes_one_recovery_then_stops(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _manifest(run_id="run_v15_semantic_reset_rejection", version=15)
    runner = AgentRunner(tmp_path / "runtime-v15-semantic-rejection")
    adapter = _InvalidSemanticResetAdapter(
        prefix="v15-semantic-rejection",
        fail_first_mutation=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(
        "patchloop.agent.runner.LocalSandbox",
        lambda: _FailFirstTwoVisibleChecksSandbox(),
    )

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    rejections = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == WORK_PLAN_ADMISSION_POLICY
    ]

    assert result["terminal_error"]["code"] == "WORK_PLAN_ADMISSION_REPEATED"
    assert len(rejections) == 2
    assert [event.payload["attempt"] for event in rejections] == [1, 2]
    assert all(
        "semantic_no_progress_requires_rejected_hypothesis" in event.payload["reason_codes"]
        for event in rejections
    )
    assert not any(
        event.type == EventType.MODEL_CALLED and event.sequence > rejections[-1].sequence
        for event in events
    )
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 2


def test_v15_semantic_reset_search_read_state_survives_restart(tmp_path, monkeypatch) -> None:
    manifest = _manifest(run_id="run_v15_semantic_reset_restart", version=15)
    runner = AgentRunner(tmp_path / "runtime-v15-semantic-restart")
    first = _CrashBeforeSemanticResetRevisionAdapter(
        prefix="v15-semantic-restart-first",
        fail_first_mutation=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)
    injected_sandbox = _FailFirstTwoVisibleChecksSandbox()
    monkeypatch.setattr(
        "patchloop.agent.runner.LocalSandbox",
        lambda: injected_sandbox,
    )

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    before = runner.state.list_events(manifest.run_id)
    second_failure = [
        event
        for event in before
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("passed") is False
    ][-1]
    assert [
        event.payload.get("tool")
        for event in before
        if event.sequence > second_failure.sequence and event.type == EventType.TOOL_SUCCEEDED
    ] == ["read_file", "search_files"]

    second = _ContextOnlyWorkflowAdapter(prefix="v15-semantic-restart-second")
    second.mutations = 2
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]

    assert result["scope_compliant_success"] is True
    assert plans[-1].payload["plan"]["prior_hypothesis_disposition"] == "rejected"
    assert plans[-1].payload["semantic_reset_required"] is True


def _v17_manifest(run_id: str):
    package = load_task_package("tasks/smoke/config-falsy-override")
    return build_lean_harness_calibration_manifest(
        package,
        run_id=run_id,
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V17,
    )


def _v18_manifest(run_id: str):
    package = load_task_package("tasks/smoke/config-falsy-override")
    return build_lean_harness_calibration_manifest(
        package,
        run_id=run_id,
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V18,
    )


def _v19_manifest(run_id: str):
    package = load_task_package("tasks/smoke/config-falsy-override")
    return build_lean_harness_calibration_manifest(
        package,
        run_id=run_id,
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V19,
    )


def _v20_manifest(run_id: str):
    package = load_task_package("tasks/smoke/config-falsy-override")
    return build_lean_harness_calibration_manifest(
        package,
        run_id=run_id,
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V20,
    )


def _v21_manifest(run_id: str):
    package = load_task_package("tasks/smoke/config-falsy-override")
    return build_lean_harness_calibration_manifest(
        package,
        run_id=run_id,
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V21,
    )


class _PinnedPlanGateWorkflowAdapter(_ExplorationProjectionWorkflowAdapter):
    """Use the V21 single-source unknown representation from request context."""

    @staticmethod
    def _exploration_arguments(workflow: dict) -> dict:
        arguments = _ExplorationProjectionWorkflowAdapter._exploration_arguments(workflow)
        arguments.pop("unknowns")
        return arguments


class _CrashBeforePinnedRetryAdapter(_PinnedPlanGateWorkflowAdapter):
    def __init__(self, *, prefix: str) -> None:
        super().__init__(prefix=prefix, invalid_closure=True)

    def next_turn(self, context: str, tools: list[dict]) -> ModelTurn:
        if (
            not getattr(self, "pinned_retry_crashed", False)
            and self.plan_arguments
            and "record_work_plan" in {item["name"] for item in tools}
        ):
            self.pinned_retry_crashed = True
            raise SystemExit(86)
        return super().next_turn(context, tools)


def test_v20_third_same_signature_failure_uses_post_restore_epoch_at_dispatch(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v20_manifest("run_v20_post_restore_epoch_parity")
    runner = AgentRunner(tmp_path / "v20-post-restore-epoch")
    adapter = _ExplorationProjectionWorkflowAdapter(
        prefix="v20-post-restore",
        fail_first_mutation=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    injected_sandbox = _FailFirstThreeVisibleChecksSandbox()
    monkeypatch.setattr("patchloop.agent.runner.LocalSandbox", lambda: injected_sandbox)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    failures = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("passed") is False
    ]
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    restored = [event for event in events if event.type == EventType.MUTATION_BASELINE_RESTORED]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert len(failures) == 3
    assert len(restored) == 1
    assert [event.payload["revision_index"] for event in plans] == [0, 1, 2, 3]
    post_restore_plan = plans[-1]
    domain = post_restore_plan.payload["semantic_progress_event_domain"]
    assert domain["latest_restore_event_sequence"] == restored[0].sequence
    assert failures[-1].sequence in domain["epoch_event_sequences"]
    assert failures[0].sequence not in domain["epoch_event_sequences"]
    assert failures[1].sequence not in domain["epoch_event_sequences"]
    assert post_restore_plan.payload["same_signature_failed_diff_count"] == 1


def test_v20_post_restore_epoch_survives_restart_before_revision_dispatch(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v20_manifest("run_v20_post_restore_epoch_restart")
    runner = AgentRunner(tmp_path / "v20-post-restore-restart")
    first = _CrashOnPostRestoreRevisionAdapter(
        prefix="v20-post-restore-first",
        fail_first_mutation=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)
    injected_sandbox = _FailFirstThreeVisibleChecksSandbox()
    monkeypatch.setattr("patchloop.agent.runner.LocalSandbox", lambda: injected_sandbox)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    before = runner.state.list_events(manifest.run_id)
    assert sum(event.type == EventType.MUTATION_BASELINE_RESTORED for event in before) == 1
    assert sum(event.type == EventType.PLAN_RECORDED for event in before) == 3

    second = _ExplorationProjectionWorkflowAdapter(
        prefix="v20-post-restore-second",
        fail_first_mutation=True,
    )
    second.mutations = 3
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    after = runner.state.list_events(manifest.run_id)
    plans = [event for event in after if event.type == EventType.PLAN_RECORDED]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert [event.payload["revision_index"] for event in plans] == [0, 1, 2, 3]
    assert (
        plans[-1].payload["semantic_progress_event_domain_hash"]
        == (plans[-1].payload["semantic_progress_event_domain"]["content_hash"])
    )


def _v21_model_requests(runner: AgentRunner, run_id: str) -> list[tuple[object, dict]]:
    requests: list[tuple[object, dict]] = []
    for event in runner.state.list_events(run_id):
        if event.type != EventType.MODEL_CALLED:
            continue
        payload = json.loads(
            Path(event.payload["request_artifact_path"]).read_text(encoding="utf-8")
        )
        evidence = payload.get("lean_harness_request")
        if isinstance(evidence, dict) and evidence.get("schema_version") == (
            "lean-harness-request-evidence-v21"
        ):
            requests.append((event, evidence))
    return requests


def test_v21_pins_forced_initial_plan_and_canonicalizes_unknown_once(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v21_manifest("run_v21_pinned_plan_gate_e2e")
    runner = AgentRunner(tmp_path / "v21-pin")
    adapter = _PinnedPlanGateWorkflowAdapter(prefix="v21-pin")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    requests = _v21_model_requests(runner, manifest.run_id)
    plan_requests = [
        (event, evidence)
        for event, evidence in requests
        if evidence["workflow_decision"]["allowed_tool_names"] == ["record_work_plan"]
    ]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert len(plan_requests) == 1
    _, plan_request = plan_requests[0]
    assert plan_request["plan_gate_readiness_source"] == "current_request"
    assert plan_request["plan_gate_readiness_snapshot"] is not None
    plan_schema = next(
        item for item in plan_request["request_body"]["tools"] if item["name"] == "record_work_plan"
    )["parameters"]
    assert "unknowns" not in plan_schema["properties"]
    assert "unknowns" not in adapter.plan_arguments[0]
    assert all(
        event.payload.get("plan_hash") for event in events if event.type == EventType.PATCH_APPLIED
    )


def test_v21_plan_rejection_forces_exactly_one_pinned_retry(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v21_manifest("run_v21_pinned_plan_gate_retry")
    runner = AgentRunner(tmp_path / "v21-retry")
    adapter = _PinnedPlanGateWorkflowAdapter(
        prefix="v21-retry",
        invalid_closure=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    requests = _v21_model_requests(runner, manifest.run_id)
    plan_requests = [
        (event, evidence)
        for event, evidence in requests
        if evidence["workflow_decision"]["allowed_tool_names"] == ["record_work_plan"]
    ]
    rejections = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == WORK_PLAN_ADMISSION_POLICY
    ]

    assert result["terminal_error"]["code"] == "WORK_PLAN_ADMISSION_REPEATED"
    assert len(plan_requests) == 2
    assert [item[1]["plan_gate_readiness_source"] for item in plan_requests] == [
        "current_request",
        "recovered_pin",
    ]
    assert [event.payload["attempt"] for event in rejections] == [1, 2]
    assert not any(
        event.type == EventType.MODEL_CALLED and event.sequence > rejections[-1].sequence
        for event in events
    )
    assert not any(event.type == EventType.PATCH_APPLIED for event in events)


def test_v21_model_visible_pin_survives_restart_without_duplicate_plan(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v21_manifest("run_v21_pinned_plan_gate_restart")
    runner = AgentRunner(tmp_path / "v21-restart")
    first = _CrashBeforePinnedRetryAdapter(prefix="v21-restart-first")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    before = runner.state.list_events(manifest.run_id)
    assert sum(event.type == EventType.PLAN_RECORDED for event in before) == 0
    assert sum(event.type == EventType.TOOL_ADMISSION_BLOCKED for event in before) == 1

    second = _PinnedPlanGateWorkflowAdapter(prefix="v21-restart-second")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    after = runner.state.list_events(manifest.run_id)
    requests = _v21_model_requests(runner, manifest.run_id)

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert sum(event.type == EventType.PLAN_RECORDED for event in after) == 1
    plan_requests = [
        (event, evidence)
        for event, evidence in requests
        if evidence["workflow_decision"]["allowed_tool_names"] == ["record_work_plan"]
    ]
    assert [item[1]["plan_gate_readiness_source"] for item in plan_requests] == [
        "current_request",
        "recovered_pin",
    ]
    assert (
        plan_requests[1][1]["recovered_plan_gate_pin"]["source_model_event_sequence"]
        == plan_requests[0][0].sequence
    )


def test_v19_requires_distinct_source_coverage_and_records_durable_closure(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v19_manifest("run_v19_exploration_gate_e2e")
    runner = AgentRunner(tmp_path / "runtime-v19-exploration-gate")
    adapter = _ExplorationProjectionWorkflowAdapter(prefix="v19-exploration")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    causal = [event for event in events if event.type == EventType.CAUSAL_MECHANISM_RECORDED]
    closures = [event for event in events if event.type == EventType.EXPLORATION_CLOSURE_RECORDED]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert adapter.public_reads == 2
    assert len(plans) == len(causal) == len(closures) == 1
    assert (
        plans[0].payload["exploration_closure_receipt_hash"]
        == (closures[0].payload["binding"]["receipt_hash"])
    )
    assert len(closures[0].payload["binding"]["receipt"]["selected_source_coverage_keys"]) >= 2
    assert not any(
        event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == WORK_PLAN_ADMISSION_POLICY
        for event in events
    )


def test_v19_open_unknown_consumes_one_retry_then_stops_before_third_dispatch(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v19_manifest("run_v19_exploration_gate_admission_limit")
    runner = AgentRunner(tmp_path / "runtime-v19-exploration-admission")
    adapter = _ExplorationProjectionWorkflowAdapter(
        prefix="v19-exploration-invalid",
        invalid_closure=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    rejections = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == WORK_PLAN_ADMISSION_POLICY
    ]

    assert result["terminal_error"]["code"] == "WORK_PLAN_ADMISSION_REPEATED"
    assert len(rejections) == 2
    assert [event.payload["attempt"] for event in rejections] == [1, 2]
    assert all(
        "exploration_blocking_unknowns_open" in event.payload["reason_codes"]
        for event in rejections
    )
    assert not any(
        event.type == EventType.MODEL_CALLED and event.sequence > rejections[-1].sequence
        for event in events
    )
    assert not any(event.type == EventType.PATCH_APPLIED for event in events)


def test_v19_failed_check_requires_a_fresh_revision_closure_before_correction(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v19_manifest("run_v19_exploration_revision_e2e")
    runner = AgentRunner(tmp_path / "v19-revision")
    adapter = _ExplorationProjectionWorkflowAdapter(
        prefix="v19-exploration-revision",
        fail_first_mutation=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    injected_sandbox = _FailFirstVisibleCheckSandbox()
    monkeypatch.setattr("patchloop.agent.runner.LocalSandbox", lambda: injected_sandbox)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    closures = [event for event in events if event.type == EventType.EXPLORATION_CLOSURE_RECORDED]
    patches = [event for event in events if event.type == EventType.PATCH_APPLIED]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert [event.payload["revision_index"] for event in plans] == [0, 1]
    assert len(closures) == len(plans) == len(patches) == 2
    assert [event.payload["plan_hash"] for event in patches] == [
        event.payload["plan_hash"] for event in plans
    ]
    assert all(
        len(event.payload["binding"]["receipt"]["selected_source_coverage_keys"]) >= 2
        for event in closures
    )


def test_v19_repeated_failure_restores_baseline_and_records_alternative_closure(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v19_manifest("run_v19_exploration_cross_reset_e2e")
    runner = AgentRunner(tmp_path / "v19-cross-reset")
    adapter = _ExplorationProjectionWorkflowAdapter(
        prefix="v19-exploration-cross-reset",
        fail_first_mutation=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    injected_sandbox = _FailFirstTwoVisibleChecksSandbox()
    monkeypatch.setattr("patchloop.agent.runner.LocalSandbox", lambda: injected_sandbox)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    closures = [event for event in events if event.type == EventType.EXPLORATION_CLOSURE_RECORDED]
    restored = [event for event in events if event.type == EventType.MUTATION_BASELINE_RESTORED]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert [event.payload["revision_index"] for event in plans] == [0, 1, 2]
    assert len(closures) == len(plans) == 3
    assert len(restored) == 1
    assert closures[-1].payload["binding"]["receipt"]["declared_unknowns_closed"] is True
    assert (
        closures[-1].payload["binding"]["receipt"]["selected_source_coverage_keys"]
        != closures[0].payload["binding"]["receipt"]["selected_source_coverage_keys"]
    )


def test_v19_recorded_closure_survives_restart_without_duplicate_plan(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v19_manifest("run_v19_exploration_restart")
    runner = AgentRunner(tmp_path / "v19-restart")
    first = _ExplorationProjectionWorkflowAdapter(prefix="v19-exploration-first")
    first.crash_on_active_plan = True
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    before = runner.state.list_events(manifest.run_id)
    assert sum(event.type == EventType.PLAN_RECORDED for event in before) == 1
    assert sum(event.type == EventType.EXPLORATION_CLOSURE_RECORDED for event in before) == 1

    second = _ExplorationProjectionWorkflowAdapter(prefix="v19-exploration-second")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    after = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert sum(event.type == EventType.PLAN_RECORDED for event in after) == 1
    assert sum(event.type == EventType.EXPLORATION_CLOSURE_RECORDED for event in after) == 1


def test_v18_server_owned_projection_completes_cross_reset_without_structural_fields(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v18_manifest("run_v18_causal_projection_e2e")
    runner = AgentRunner(tmp_path / "runtime-v18-causal-projection")
    adapter = _CausalProjectionWorkflowAdapter(prefix="v18-projection")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    injected_sandbox = _FailFirstTwoVisibleChecksSandbox()
    monkeypatch.setattr("patchloop.agent.runner.LocalSandbox", lambda: injected_sandbox)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    bindings = [event for event in events if event.type == EventType.CAUSAL_MECHANISM_RECORDED]

    assert result["scope_compliant_success"] is True, result.get("terminal_error")
    assert len(plans) == len(bindings) == 3
    assert all(
        event.payload["schema_version"] == "causal-mechanism-recorded-v2" for event in bindings
    )
    assert (
        bindings[0].payload["binding"]["mechanism"]["source_coverage_keys"][0]
        == (bindings[0].payload["binding"]["mechanism"]["source_coverage_keys"][-1])
    )
    assert bindings[-1].payload["binding"]["stale_check_observation_only"] is True
    assert bindings[-1].payload["binding"]["projected_plan"]["observation_evidence"] is None
    serialized = json.dumps(adapter.plan_arguments[0], sort_keys=True)
    for forbidden in (
        '"observation_status"',
        '"foundation_evidence_ids"',
        '"candidate_files"',
        '"planned_check_ids"',
        '"role"',
        '"path"',
        '"start_line"',
        '"end_line"',
        '"read_evidence_id"',
    ):
        assert forbidden not in serialized


def test_v18_stale_projected_span_consumes_one_retry_then_stops(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v18_manifest("run_v18_causal_projection_admission_limit")
    runner = AgentRunner(tmp_path / "v18a")
    adapter = _CausalProjectionWorkflowAdapter(
        prefix="v18-projection-invalid",
        invalid_cross_reset=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(
        "patchloop.agent.runner.LocalSandbox",
        lambda: _FailFirstTwoVisibleChecksSandbox(),
    )

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    restored = next(event for event in events if event.type == EventType.MUTATION_BASELINE_RESTORED)
    rejections = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == CAUSAL_ALTERNATIVE_POLICY
    ]

    assert result["terminal_error"]["code"] == "WORK_PLAN_ADMISSION_REPEATED"
    assert len(rejections) == 2
    assert [event.payload["attempt"] for event in rejections] == [1, 2]
    assert all(
        "causal_source_span_ineligible" in event.payload["reason_codes"] for event in rejections
    )
    assert not any(
        event.type == EventType.MODEL_CALLED and event.sequence > rejections[-1].sequence
        for event in events
    )
    assert not any(
        event.type == EventType.PATCH_APPLIED and event.sequence > restored.sequence
        for event in events
    )


def test_v18_completed_restore_and_projected_plan_survive_restart(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v18_manifest("run_v18_causal_projection_restart")
    runner = AgentRunner(tmp_path / "v18r")
    first = _CausalProjectionWorkflowAdapter(
        prefix="v18-projection-first",
        crash_on_cross_reset=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)
    injected_sandbox = _FailFirstTwoVisibleChecksSandbox()
    monkeypatch.setattr("patchloop.agent.runner.LocalSandbox", lambda: injected_sandbox)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    before = runner.state.list_events(manifest.run_id)
    restored = [event for event in before if event.type == EventType.MUTATION_BASELINE_RESTORED]
    assert len(restored) == 1

    second = _CausalProjectionWorkflowAdapter(prefix="v18-projection-second")
    second.mutations = 2
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    after = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    assert sum(event.type == EventType.MUTATION_BASELINE_RESTORED for event in after) == 1
    alternatives = [
        event
        for event in after
        if event.type == EventType.CAUSAL_MECHANISM_RECORDED
        and event.payload["binding"].get("cross_reset_failure_trigger_hash") is not None
    ]
    assert len(alternatives) == 1
    assert alternatives[0].payload["schema_version"] == "causal-mechanism-recorded-v2"


def test_v18_partial_reverse_restore_resumes_without_replaying_failures(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v18_manifest("run_v18_causal_projection_partial_restore")
    runner = AgentRunner(tmp_path / "v18p")
    adapter = _CausalProjectionWorkflowAdapter(prefix="v18-projection-partial")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    injected_sandbox = _FailFirstTwoVisibleChecksSandbox()
    monkeypatch.setattr("patchloop.agent.runner.LocalSandbox", lambda: injected_sandbox)
    original_restore = ToolGateway._restore_patch_preimages
    restore_calls = 0

    def crash_after_first_reverse_action(self, intent):
        nonlocal restore_calls
        original_restore(self, intent)
        restore_calls += 1
        if restore_calls == 1:
            raise SystemExit(85)

    monkeypatch.setattr(
        ToolGateway,
        "_restore_patch_preimages",
        crash_after_first_reverse_action,
    )
    with pytest.raises(SystemExit, match="85"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)

    interrupted = runner.state.list_events(manifest.run_id)
    failure_sequences = [
        event.sequence
        for event in interrupted
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("passed") is False
    ]
    assert (
        sum(event.type == EventType.MUTATION_BASELINE_RESTORE_PREPARED for event in interrupted)
        == 1
    )
    assert not any(event.type == EventType.MUTATION_BASELINE_RESTORED for event in interrupted)

    monkeypatch.setattr(ToolGateway, "_restore_patch_preimages", original_restore)
    result = runner.resume(manifest.run_id)
    recovered = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    assert sum(event.type == EventType.MUTATION_BASELINE_RESTORED for event in recovered) == 1
    assert [
        event.sequence
        for event in recovered
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("passed") is False
    ] == failure_sequences


def test_v17_restores_failed_mutation_family_and_records_causal_alternative(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v17_manifest("run_v17_causal_restore_e2e")
    runner = AgentRunner(tmp_path / "runtime-v17-causal")
    adapter = _CausalContextWorkflowAdapter(prefix="v17-causal")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    injected_sandbox = _FailFirstTwoVisibleChecksSandbox()
    monkeypatch.setattr("patchloop.agent.runner.LocalSandbox", lambda: injected_sandbox)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    failures = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("passed") is False
    ]
    prepared = [
        event for event in events if event.type == EventType.MUTATION_BASELINE_RESTORE_PREPARED
    ]
    restored = [event for event in events if event.type == EventType.MUTATION_BASELINE_RESTORED]
    plans = [event for event in events if event.type == EventType.PLAN_RECORDED]
    causal = [event for event in events if event.type == EventType.CAUSAL_MECHANISM_RECORDED]
    patches = [event for event in events if event.type == EventType.PATCH_APPLIED]

    assert result["scope_compliant_success"] is True
    assert len(failures) == 2
    assert len(prepared) == len(restored) == 1
    assert all(event.sequence < restored[0].sequence for event in failures)
    baseline = restored[0].payload["baseline_projection"]
    receipt = restored[0].payload["restore_receipt"]
    assert receipt["restored_action_ids"] == list(reversed(baseline["forward_action_ids"]))
    assert receipt["append_only_events_deleted"] is False
    assert receipt["provider_calls"] == receipt["visible_check_calls"] == 0
    assert len(plans) == len(causal) == len(patches) == 3
    binding = causal[-1].payload["binding"]
    assert binding["causal_alternative_plan"] is not None
    assert binding["cross_reset_failure_trigger_hash"] == restored[0].payload["trigger_hash"]
    assert (
        binding["causal_alternative_plan"]["causal_contrast"][
            "alternative_boundary_is_non_exhausted"
        ]
        is True
    )
    assert [event.payload["plan_hash"] for event in patches] == [
        event.payload["plan_hash"] for event in plans
    ]
    assert all(
        "why_exception_reaches_mutation_site" not in json.dumps(event.payload, sort_keys=True)
        for event in events
        if event.type in {EventType.CONTEXT_BUILT, EventType.CAUSAL_MECHANISM_RECORDED}
    )


def test_v17_completed_restore_and_cross_reset_trigger_survive_restart(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v17_manifest("run_v17_causal_restore_restart")
    runner = AgentRunner(tmp_path / "runtime-v17-causal-restart")
    first = _CausalContextWorkflowAdapter(
        prefix="v17-causal-first",
        crash_on_cross_reset=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: first)
    injected_sandbox = _FailFirstTwoVisibleChecksSandbox()
    monkeypatch.setattr("patchloop.agent.runner.LocalSandbox", lambda: injected_sandbox)

    with pytest.raises(SystemExit, match="86"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)
    before = runner.state.list_events(manifest.run_id)
    restored = [event for event in before if event.type == EventType.MUTATION_BASELINE_RESTORED]
    assert len(restored) == 1
    checkpoint = runner.state.latest_checkpoint(manifest.run_id)
    assert checkpoint is not None
    assert (
        checkpoint.worktree_diff_hash
        == restored[0].payload["trigger"]["restored_baseline_diff_hash"]
    )

    second = _CausalContextWorkflowAdapter(prefix="v17-causal-second")
    second.mutations = 2
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: second)
    result = runner.resume(manifest.run_id)
    after = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    assert sum(event.type == EventType.MUTATION_BASELINE_RESTORED for event in after) == 1
    alternative = [
        event
        for event in after
        if event.type == EventType.CAUSAL_MECHANISM_RECORDED
        and event.payload["binding"].get("cross_reset_failure_trigger_hash") is not None
    ]
    assert len(alternative) == 1


def test_v17_repeated_same_family_alternative_stops_before_third_dispatch(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v17_manifest("run_v17_causal_admission_limit")
    runner = AgentRunner(tmp_path / "runtime-v17-causal-admission")
    adapter = _CausalContextWorkflowAdapter(
        prefix="v17-causal-invalid",
        invalid_cross_reset=True,
    )
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    injected_sandbox = _FailFirstTwoVisibleChecksSandbox()
    monkeypatch.setattr("patchloop.agent.runner.LocalSandbox", lambda: injected_sandbox)

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    restored = next(event for event in events if event.type == EventType.MUTATION_BASELINE_RESTORED)
    rejections = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == CAUSAL_ALTERNATIVE_POLICY
    ]

    assert result["terminal_error"]["code"] == "WORK_PLAN_ADMISSION_REPEATED"
    assert len(rejections) == 2
    assert [event.payload["attempt"] for event in rejections] == [1, 2]
    assert all(
        "causal_boundary_already_exhausted" in event.payload["reason_codes"] for event in rejections
    )
    assert not any(
        event.type == EventType.MODEL_CALLED and event.sequence > rejections[-1].sequence
        for event in events
    )
    assert not any(
        event.type == EventType.PATCH_APPLIED and event.sequence > restored.sequence
        for event in events
    )


def test_v17_partial_reverse_restore_resumes_without_replaying_failure_history(
    tmp_path,
    monkeypatch,
) -> None:
    manifest = _v17_manifest("run_v17_partial_restore_restart")
    runner = AgentRunner(tmp_path / "runtime-v17-partial-restore")
    adapter = _CausalContextWorkflowAdapter(prefix="v17-partial-restore")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    injected_sandbox = _FailFirstTwoVisibleChecksSandbox()
    monkeypatch.setattr("patchloop.agent.runner.LocalSandbox", lambda: injected_sandbox)
    original_restore = ToolGateway._restore_patch_preimages
    restore_calls = 0

    def crash_after_first_reverse_action(self, intent):
        nonlocal restore_calls
        original_restore(self, intent)
        restore_calls += 1
        if restore_calls == 1:
            raise SystemExit(85)

    monkeypatch.setattr(
        ToolGateway,
        "_restore_patch_preimages",
        crash_after_first_reverse_action,
    )
    with pytest.raises(SystemExit, match="85"):
        runner.start(TASK_PATH, model="mock", manifest=manifest)

    interrupted = runner.state.list_events(manifest.run_id)
    assert (
        sum(event.type == EventType.MUTATION_BASELINE_RESTORE_PREPARED for event in interrupted)
        == 1
    )
    assert not any(event.type == EventType.MUTATION_BASELINE_RESTORED for event in interrupted)
    failure_sequences = [
        event.sequence
        for event in interrupted
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("passed") is False
    ]

    monkeypatch.setattr(ToolGateway, "_restore_patch_preimages", original_restore)
    result = runner.resume(manifest.run_id)
    recovered = runner.state.list_events(manifest.run_id)
    restored = [event for event in recovered if event.type == EventType.MUTATION_BASELINE_RESTORED]

    assert result["scope_compliant_success"] is True
    assert len(restored) == 1
    assert (
        sum(event.type == EventType.MUTATION_BASELINE_RESTORE_PREPARED for event in recovered) == 1
    )
    assert restored[0].payload["restore_receipt"]["exact_restore_verified"] is True
    assert [
        event.sequence
        for event in recovered
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("passed") is False
    ] == failure_sequences
