"""Deterministic zero-call qualification for the Lean V16 mechanical successor."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.workflow_candidate_binding_successor import (
    CANDIDATE_BINDING_POLICY_V16,
    normalize_same_path_candidate_bindings,
    validate_work_plan_v16,
)
from patchloop.agent.workflow_successor_v2 import (
    EligiblePlanEvidence,
    EligiblePlanEvidenceCatalogV2,
    SourceEvidenceProjection,
    validate_work_plan_v2,
)
from patchloop.contracts import PublicTask
from patchloop.errors import ContractError
from patchloop.evals.rapid_cli import dispatch_rapid_public_development_cli
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

SCHEMA_VERSION = "lean-candidate-binding-successor-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-candidate-binding-public-qualification-20260825-v1.json"
)
RUN_ID = "run_r12_shaped_candidate_binding_qualification"
DIFF_HASH = sha256_text("")
CANDIDATE_PATH = "src/anyio/pytest_plugin.py"

SOURCE_FILES = (
    "patchloop/agent/workflow_candidate_binding_successor.py",
    "patchloop/agent/workflow_candidate_binding_successor_qualification.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "patchloop/environment.py",
    "patchloop/evals/rapid_cli.py",
    "scripts/build_lean_harness_candidate_binding_qualification.py",
    "tests/test_workflow_candidate_binding_successor.py",
    "tests/test_workflow_successor_v2_runner.py",
    "tests/test_rapid_cli.py",
)

IMMUTABLE_PREDECESSORS = {
    "experiments/lean-harness-semantic-progress-public-qualification-20260825-v1.json": {
        "bytes": 6_703,
        "file_sha256": "sha256:c13b4e6cf4c80b4eaa9c9d1016ab5e3bbdae881341c6a751a611266bb33fe7f0",
        "content_hash": "sha256:d3e578271060144513c2e49978a6e5fc2acf38888a180729bfb93c5b801e8ca1",
    },
    (
        "reports/rapid-development/"
        "rapid-public-dev-anyio-semantic-progress-ab-20260825-r12-4d4fbf5839ed.jsonl"
    ): {
        "bytes": 9_575,
        "file_sha256": "sha256:da653feb1578ffca9234fd6b976f6d62a1518dd73b0a5397bef5f5b820f4ca16",
        "final_content_hash": (
            "sha256:ac45cceea6a27632c03f0674fcf99d3bee1356ce4b207c734d39376b12a9fc26"
        ),
    },
    "scripts/run_rapid_public_development_v18.py": {
        "bytes": 1_134,
        "file_sha256": "sha256:af8a5a5e525be64a169677bbba0adb5b9f99ac23a7df5cf64aaf1f195dc02b75",
    },
}


def _identity(root: Path, relative: str, *, document_kind: str = "raw") -> dict[str, Any]:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise ContractError(f"candidate-binding qualification input is unavailable: {relative}")
    raw = path.read_bytes()
    result: dict[str, Any] = {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }
    if document_kind == "json":
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("candidate-binding predecessor is not canonical JSON") from exc
        content_hash = document.get("content_hash")
        if content_hash != sha256_json(
            {key: value for key, value in document.items() if key != "content_hash"}
        ):
            raise ContractError("candidate-binding predecessor content hash differs")
        result["content_hash"] = content_hash
    elif document_kind == "jsonl":
        try:
            lines = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("candidate-binding predecessor is not canonical JSONL") from exc
        if not lines or not isinstance(lines[-1].get("content_hash"), str):
            raise ContractError("candidate-binding result predecessor lacks its final hash")
        result["final_content_hash"] = lines[-1]["content_hash"]
    return result


def _task() -> PublicTask:
    return PublicTask.model_validate(
        {
            "schema_version": "task-public-v1",
            "task_id": "anyio-interrupt-runner-cleanup",
            "task_version": 4,
            "split": "dev-validation",
            "repository": {
                "url": "snapshot://r12-shaped-public-candidate-binding",
                "base_commit": "sha256:" + "0" * 64,
                "language": "python",
            },
            "issue": {
                "title": "Synthetic R12-shaped public admission",
                "description": "Bind multiple visible reads of one allowed candidate file.",
            },
            "constraints": {
                "allowed_paths": ["src/**/*.py"],
                "forbidden_paths": ["tests/**"],
                "max_changed_files": 2,
                "max_diff_lines": 100,
                "dependency_changes_allowed": False,
                "public_api_changes_allowed": False,
            },
            "visible_checks": [
                {
                    "id": "targeted",
                    "command": ["python", "-m", "synthetic_targeted"],
                    "timeout_seconds": 30,
                },
                {
                    "id": "upstream",
                    "command": ["python", "-m", "synthetic_upstream"],
                    "timeout_seconds": 30,
                },
            ],
            "tags": ["synthetic", "public", "r12-shaped"],
        }
    )


def _read(sequence: int, start: int, end: int) -> EligiblePlanEvidence:
    source = SourceEvidenceProjection(
        path=CANDIDATE_PATH,
        requested_range=(start, end),
        actual_range=(start, end),
        visible_ranges=((start, end),),
        omitted_ranges=(),
        partial_line=False,
        total_lines=1_000,
        file_content_hash="sha256:" + "a" * 64,
    )
    return EligiblePlanEvidence.model_validate(
        {
            "evidence_id": f"pev:{sequence}",
            "kind": "source_read",
            "role": "foundation",
            "run_id": RUN_ID,
            "worktree_diff_hash": DIFF_HASH,
            "canonical_event_sequence": sequence,
            "model_visible_event_sequences": (sequence,),
            "replay_alias_event_sequences": (),
            "artifact_hash": "sha256:" + f"{sequence:064x}",
            "visible_projection_hash": sha256_json(source.model_dump(mode="json")),
            "source": source.model_dump(mode="python"),
            "check": None,
            "diff_review": None,
            "search": None,
        }
    )


def _catalog(task: PublicTask) -> EligiblePlanEvidenceCatalogV2:
    items = (_read(12, 120, 180), _read(17, 300, 360))
    body = {
        "schema_version": "eligible-plan-evidence-catalog-v2",
        "run_id": RUN_ID,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": sha256_json(task.model_dump(mode="json")),
        "worktree_diff_hash": DIFF_HASH,
        "model_visible_context_hash": "sha256:" + "b" * 64,
        "model_visible_recent_event_sequences": (12, 17),
        "items": tuple(item.model_dump(mode="python") for item in items),
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
        "required_trigger_status": "not_required",
        "required_trigger_event_sequence": None,
        "required_trigger_evidence_id": None,
        "model_visible_pinned_event_sequences": (),
        "unavailable_reason": None,
    }
    return EligiblePlanEvidenceCatalogV2.model_validate({**body, "content_hash": sha256_json(body)})


def _arguments(order: tuple[int, int] = (17, 12)) -> dict[str, Any]:
    return {
        "observation_status": "static_source",
        "hypothesis": "Two public ranges support one bounded candidate-file change.",
        "foundation_evidence_ids": ["pev:12", "pev:17"],
        "supporting_evidence_ids": [],
        "candidate_files": [
            {"path": CANDIDATE_PATH, "read_evidence_id": f"pev:{sequence}"} for sequence in order
        ],
        "intended_change": "Adjust only the cited public candidate file.",
        "expected_behavior": "The registered targeted behavior passes before upstream.",
        "unknowns": [],
    }


def _validate(task: PublicTask, catalog: EligiblePlanEvidenceCatalogV2, order=(17, 12)):
    return validate_work_plan_v16(
        task=task,
        catalog=catalog,
        arguments=_arguments(order),
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
    )


def _scenarios(root: Path) -> dict[str, Any]:
    task = _task()
    catalog = _catalog(task)
    legacy_reason_codes: list[str] = []
    try:
        validate_work_plan_v2(
            task=task,
            catalog=catalog,
            arguments=_arguments(),
            trigger="initial",
            revision_index=0,
            parent_plan_hash=None,
            trigger_check_id=None,
            trigger_event_sequence=None,
        )
    except ContractError as exc:
        legacy_reason_codes = list(exc.details.get("reason_codes", []))
    if legacy_reason_codes != ["plan_schema_invalid"]:
        raise ContractError("R12-shaped legacy rejection was not reproduced offline")

    plan, normalization = _validate(task, catalog)
    reversed_plan, reversed_normalization = _validate(task, catalog, (12, 17))
    if plan != reversed_plan or normalization != reversed_normalization:
        raise ContractError("candidate binding normalization is not deterministic")

    invalid = _arguments()
    invalid["candidate_files"][1]["path"] = "src/anyio/_core/_eventloop.py"
    invalid_reason_codes: list[str] = []
    try:
        normalize_same_path_candidate_bindings(
            task=task,
            catalog=catalog,
            arguments=invalid,
        )
    except ContractError as exc:
        invalid_reason_codes = list(exc.details.get("reason_codes", []))
    if invalid_reason_codes != ["candidate_read_binding_invalid"]:
        raise ContractError("invalid candidate binding did not fail closed")

    dispatches = {"rehearse": 0, "execute": 0}
    rehearsal = dispatch_rapid_public_development_cli(
        mode="rehearse",
        repository=root,
        env_file=root / ".env-does-not-need-to-exist-for-rehearsal",
        approve_live_cost=False,
        approved_execution_hash=None,
        rehearse=lambda **_: (
            dispatches.__setitem__("rehearse", dispatches["rehearse"] + 1)
            or {"mode": "rehearse", "external_calls": 0}
        ),
        execute=lambda **_: dispatches.__setitem__("execute", dispatches["execute"] + 1) or {},
    )
    missing_env_failed_closed = False
    try:
        dispatch_rapid_public_development_cli(
            mode="execute",
            repository=root,
            env_file=None,
            approve_live_cost=True,
            approved_execution_hash="sha256:" + "1" * 64,
            rehearse=lambda **_: {},
            execute=lambda **_: dispatches.__setitem__("execute", dispatches["execute"] + 1) or {},
        )
    except ContractError:
        missing_env_failed_closed = True
    if dispatches != {"rehearse": 1, "execute": 0} or not missing_env_failed_closed:
        raise ContractError("credential-safe Rapid entry contract differs")

    return {
        "r12_shaped_legacy_rejection": {
            "candidate_bindings": [
                {"path": CANDIDATE_PATH, "read_evidence_id": "pev:17"},
                {"path": CANDIDATE_PATH, "read_evidence_id": "pev:12"},
            ],
            "legacy_reason_codes": legacy_reason_codes,
            "both_reads_current_public_foundation": True,
        },
        "v16_normalization": {
            "policy_version": CANDIDATE_BINDING_POLICY_V16,
            "plan_hash": plan.content_hash,
            "recorded_candidate_files": [
                item.model_dump(mode="json") for item in plan.candidate_files
            ],
            "retained_foundation_evidence_ids": [
                item.evidence_id for item in plan.foundation_evidence
            ],
            "normalization": normalization.model_dump(mode="json"),
            "reversed_request_exact": True,
        },
        "fail_closed": {
            "mismatched_path_reason_codes": invalid_reason_codes,
            "stale_foreign_private_acceptance_added": False,
        },
        "credential_safe_entry": {
            "rehearsal_result": rehearsal,
            "rehearsal_env_file_read": False,
            "execute_dispatches": dispatches["execute"],
            "missing_explicit_env_file_failed_closed": missing_env_failed_closed,
            "credential_value_recorded": False,
        },
    }


def build_workflow_candidate_binding_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    predecessor_kinds = {
        next(iter(IMMUTABLE_PREDECESSORS)): "json",
        next(iter(tuple(IMMUTABLE_PREDECESSORS)[1:])): "jsonl",
    }
    predecessors = []
    for relative, expected in IMMUTABLE_PREDECESSORS.items():
        observed = _identity(
            root,
            relative,
            document_kind=predecessor_kinds.get(relative, "raw"),
        )
        if any(observed.get(key) != value for key, value in expected.items()):
            raise ContractError(f"immutable candidate-binding predecessor differs: {relative}")
        predecessors.append(observed)
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 25, tzinfo=UTC).isoformat(),
        "successor_runtime": "lean-harness-v16",
        "tool_schema_version": "v20",
        "context_policy_version": "phase-evidence-v26",
        "candidate_binding_policy_version": CANDIDATE_BINDING_POLICY_V16,
        "scenarios": _scenarios(root),
        "source_files": tuple(_identity(root, relative) for relative in SOURCE_FILES),
        "immutable_predecessors": tuple(predecessors),
        "evidence_boundary": {
            "public_only": True,
            "task_fixture_files_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "repository_env_file_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "added_cost_usd": "0",
        },
        "runtime_activation_authorized": False,
        "paid_execution_authorized": False,
        "rapid_candidate_created": False,
        "quality_improvement_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_candidate_binding_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_candidate_binding_successor_qualification(root)
    target = (root / QUALIFICATION_PATH).resolve()
    if not target.is_relative_to(root):
        raise ContractError("candidate-binding qualification output escapes repository")
    target.write_bytes(qualification_bytes(value))
    return value


__all__ = [
    "IMMUTABLE_PREDECESSORS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_candidate_binding_successor_qualification",
    "materialize_workflow_candidate_binding_successor_qualification",
    "qualification_bytes",
]
