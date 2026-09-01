"""Deterministic zero-call qualification for server-owned causal-plan input."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.workflow_causal_plan_projection_successor import (
    CAUSAL_PLAN_PROJECTION_POLICY,
    normalize_causal_plan_request,
    project_causal_plan_request,
)
from patchloop.agent.workflow_successor_v2 import (
    CheckEvidenceProjection,
    EligiblePlanEvidence,
    EligiblePlanEvidenceCatalog,
    SearchEvidenceProjection,
    SourceEvidenceProjection,
)
from patchloop.contracts import PublicTask
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

SCHEMA_VERSION = "lean-causal-plan-projection-successor-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-causal-plan-projection-public-qualification-20260826-v1.json"
)
RUN_ID = "run_causal_plan_projection_qualification"
EMPTY_DIFF = sha256_text("")
RUNTIME_PATH = "src/package/runtime.py"
HANDLER_PATH = "src/package/handler.py"

SOURCE_FILES = (
    "patchloop/agent/workflow_causal_plan_projection_successor.py",
    "patchloop/agent/workflow_causal_plan_projection_successor_qualification.py",
    "scripts/build_lean_harness_causal_plan_projection_qualification.py",
    "tests/test_workflow_causal_plan_projection_successor.py",
    "tests/test_workflow_causal_plan_projection_successor_qualification.py",
)

IMMUTABLE_PREDECESSORS = {
    (
        "experiments/"
        "lean-harness-causal-alternative-activation-public-qualification-20260826-v1.json"
    ): {
        "bytes": 5_235,
        "file_sha256": ("sha256:72576cdcf05a9337bcee415d3200bfe76f04fd8b13b3231b02140fb6b2cd448e"),
        "content_hash": ("sha256:45f469b256c50b7259b7c1df6a59e3b4fe8f598f67733ef93a96733b72191f85"),
    },
    (
        "reports/rapid-development/"
        "rapid-public-dev-anyio-causal-activation-ab-20260826-r13-4799bfa0afab.jsonl"
    ): {
        "bytes": 9_572,
        "file_sha256": ("sha256:9b74db6c1ad9df37a1838de534af95d28cee1dac4b533330f17527911db1ae72"),
    },
    (
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-causal-activation-ab-20260826-r13-workflow-diagnosis-v1.json"
    ): {
        "bytes": 20_123,
        "file_sha256": ("sha256:6505ecde08fe250972a78024f7c637d3554fadb002e8c1993388f993806429c8"),
        "content_hash": ("sha256:7711031853408178fee6819c7810ec19e73d6ad16c8169acdc09c38d1a148133"),
    },
}


def _identity(root: Path, relative: str, *, canonical_document: bool) -> dict[str, Any]:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise ContractError(f"causal-plan projection input is unavailable: {relative}")
    raw = path.read_bytes()
    identity: dict[str, Any] = {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }
    if canonical_document:
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("causal-plan predecessor is not canonical JSON") from exc
        content_hash = document.get("content_hash")
        if content_hash != sha256_json(
            {key: value for key, value in document.items() if key != "content_hash"}
        ):
            raise ContractError("causal-plan predecessor content hash differs")
        identity["content_hash"] = content_hash
    return identity


def _task() -> PublicTask:
    return PublicTask.model_validate(
        {
            "schema_version": "task-public-v1",
            "task_id": "synthetic-causal-plan-projection",
            "task_version": 1,
            "split": "smoke",
            "repository": {
                "url": "snapshot://synthetic-causal-plan-projection",
                "base_commit": "sha256:" + "0" * 64,
                "language": "python",
            },
            "issue": {
                "title": "Synthetic public behavior",
                "description": "Preserve one public lifecycle behavior through a bounded edit.",
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
            "tags": ["synthetic", "public"],
        }
    )


def _read(sequence: int, path: str, ranges: tuple[tuple[int, int], ...]) -> EligiblePlanEvidence:
    source = SourceEvidenceProjection(
        path=path,
        requested_range=(ranges[0][0], ranges[-1][1]),
        actual_range=(ranges[0][0], ranges[-1][1]),
        visible_ranges=ranges,
        omitted_ranges=(),
        partial_line=False,
        total_lines=400,
        file_content_hash="sha256:" + f"{sequence:064x}",
    )
    return EligiblePlanEvidence.model_validate(
        {
            "evidence_id": f"pev:{sequence}",
            "kind": "source_read",
            "role": "foundation",
            "run_id": RUN_ID,
            "worktree_diff_hash": EMPTY_DIFF,
            "canonical_event_sequence": sequence,
            "model_visible_event_sequences": (sequence,),
            "replay_alias_event_sequences": (),
            "artifact_hash": "sha256:" + f"{sequence + 100:064x}",
            "visible_projection_hash": sha256_json(source.model_dump(mode="json")),
            "source": source.model_dump(mode="python"),
            "check": None,
            "diff_review": None,
            "search": None,
        }
    )


def _failed_check(sequence: int = 13) -> EligiblePlanEvidence:
    check = CheckEvidenceProjection(
        check_id="targeted",
        check_index=0,
        invocation_status="completed",
        behavior_status="failed",
        passed=False,
        timed_out=False,
    )
    return EligiblePlanEvidence.model_validate(
        {
            "evidence_id": f"pev:{sequence}",
            "kind": "targeted_check_result",
            "role": "foundation",
            "run_id": RUN_ID,
            "worktree_diff_hash": EMPTY_DIFF,
            "canonical_event_sequence": sequence,
            "model_visible_event_sequences": (sequence,),
            "replay_alias_event_sequences": (),
            "artifact_hash": "sha256:" + f"{sequence + 100:064x}",
            "visible_projection_hash": sha256_json(check.model_dump(mode="json")),
            "source": None,
            "check": check.model_dump(mode="python"),
            "diff_review": None,
            "search": None,
        }
    )


def _support(sequence: int = 14) -> EligiblePlanEvidence:
    search = SearchEvidenceProjection(
        query_hash="sha256:" + "e" * 64,
        path_glob="src/**/*.py",
        match_count=2,
        truncated=False,
    )
    return EligiblePlanEvidence.model_validate(
        {
            "evidence_id": f"pev:{sequence}",
            "kind": "search_support",
            "role": "support",
            "run_id": RUN_ID,
            "worktree_diff_hash": EMPTY_DIFF,
            "canonical_event_sequence": sequence,
            "model_visible_event_sequences": (sequence,),
            "replay_alias_event_sequences": (),
            "artifact_hash": "sha256:" + f"{sequence + 100:064x}",
            "visible_projection_hash": sha256_json(search.model_dump(mode="json")),
            "source": None,
            "check": None,
            "diff_review": None,
            "search": search.model_dump(mode="python"),
        }
    )


def _catalog(*, include_failed_check: bool) -> EligiblePlanEvidenceCatalog:
    task = _task()
    items = [
        _read(10, RUNTIME_PATH, ((20, 57), (90, 118))),
        _read(11, HANDLER_PATH, ((120, 170),)),
    ]
    if include_failed_check:
        items.append(_failed_check())
    items.append(_support())
    body = {
        "schema_version": "eligible-plan-evidence-catalog-v1",
        "run_id": RUN_ID,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": sha256_json(task.model_dump(mode="json")),
        "worktree_diff_hash": EMPTY_DIFF,
        "model_visible_context_hash": "sha256:" + "c" * 64,
        "model_visible_recent_event_sequences": tuple(
            item.canonical_event_sequence for item in items
        ),
        "items": tuple(item.model_dump(mode="python") for item in items),
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return EligiblePlanEvidenceCatalog.model_validate({**body, "content_hash": sha256_json(body)})


def _linked(span_id: str, name: str) -> dict[str, Any]:
    return {
        "source_span_id": span_id,
        "symbol": name,
        "observation": f"The public source at {name} controls one visible lifecycle step.",
        "relationship_to_next": "This state is forwarded to the next public source boundary.",
    }


def _arguments() -> dict[str, Any]:
    return {
        "hypothesis": "A bounded public source path controls the observed lifecycle behavior.",
        "supporting_evidence_ids": ["pev:14"],
        "candidate_source_span_ids": ["cspan:10:0"],
        "intended_change": "Adjust only the evidence-bound transition.",
        "expected_behavior": "The targeted and upstream checks pass in order.",
        "unknowns": ["Another public boundary may become visible after the edit."],
        "prior_hypothesis_disposition": None,
        "causal_mechanism": {
            "summary": "The entry boundary reaches the handler and returns to the mutation site.",
            "causal_boundary": _linked("cspan:10:0", "entry_boundary"),
            "intermediate_steps": [_linked("cspan:11:0", "handler")],
            "mutation_site": {
                "source_span_id": "cspan:10:0",
                "symbol": "state_transition",
                "observation": "This public source span commits the visible state.",
            },
            "mutation_site_rationale": "The bounded edit changes the observed transition.",
            "expected_observable_effect": "The targeted check observes one completed transition.",
            "falsification_condition": "The same public failure persists after the edit.",
        },
    }


def _reason_code(callable_: Any) -> str:
    try:
        callable_()
    except ContractError as exc:
        codes = exc.details.get("reason_codes", [])
        if len(codes) == 1 and isinstance(codes[0], str):
            return codes[0]
        raise ContractError("causal-plan qualification rejection code differs") from exc
    raise ContractError("causal-plan qualification expected a rejection")


def _scenarios() -> dict[str, Any]:
    task = _task()
    static_catalog = _catalog(include_failed_check=False)
    static_projection = project_causal_plan_request(
        task=task, catalog=static_catalog, trigger="initial"
    )
    arguments = _arguments()
    plan = normalize_causal_plan_request(
        task=task,
        catalog=static_catalog,
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
        raw_arguments=arguments,
    )
    repeated_keys = plan.causal_mechanism.source_coverage_keys

    revision_arguments = _arguments()
    revision_arguments["prior_hypothesis_disposition"] = "rejected"
    revision = normalize_causal_plan_request(
        task=task,
        catalog=_catalog(include_failed_check=True),
        trigger="check_failure",
        revision_index=1,
        parent_plan_hash=plan.content_hash,
        trigger_check_id="targeted",
        trigger_event_sequence=13,
        raw_arguments=revision_arguments,
    )

    old_shape = _arguments()
    old_shape["observation_status"] = "targeted_check_failed"
    old_shape["causal_mechanism"]["mutation_site"]["role"] = "mutation_site"
    old_shape["causal_mechanism"]["mutation_site"]["relationship_to_next"] = "extra"
    forged_span = _arguments()
    forged_span["causal_mechanism"]["mutation_site"]["source_span_id"] = "cspan:84:0"
    nonmechanism_candidate = _arguments()
    nonmechanism_candidate["candidate_source_span_ids"] = ["cspan:10:1"]

    parameter_text = json.dumps(static_projection.parameters, sort_keys=True)
    forbidden_model_fields = (
        "observation_status",
        "foundation_evidence_ids",
        "candidate_files",
        "planned_check_ids",
        "role",
        "path",
        "start_line",
        "end_line",
        "read_evidence_id",
    )
    return {
        "finite_public_source_spans": {
            "span_ids": [
                item.source_span_id for item in static_projection.source_span_catalog.spans
            ],
            "visible_ranges": [
                [item.path, item.start_line, item.end_line]
                for item in static_projection.source_span_catalog.spans
            ],
            "artifact_and_projection_hashes_bound": all(
                item.artifact_hash.startswith("sha256:")
                and item.visible_projection_hash.startswith("sha256:")
                for item in static_projection.source_span_catalog.spans
            ),
            "foreign_span_rejection": _reason_code(
                lambda: normalize_causal_plan_request(
                    task=task,
                    catalog=static_catalog,
                    trigger="initial",
                    revision_index=0,
                    parent_plan_hash=None,
                    trigger_check_id=None,
                    trigger_event_sequence=None,
                    raw_arguments=forged_span,
                )
            ),
        },
        "server_owned_structure": {
            "forbidden_fields_absent": all(
                f'"{field}"' not in parameter_text for field in forbidden_model_fields
            ),
            "roles": [step.role for step in plan.causal_mechanism.causal_path],
            "ordinals": [step.ordinal for step in plan.causal_mechanism.causal_path],
            "final_relationship_to_next": (
                plan.causal_mechanism.causal_path[-1].relationship_to_next
            ),
            "old_shape_rejection": _reason_code(
                lambda: normalize_causal_plan_request(
                    task=task,
                    catalog=static_catalog,
                    trigger="initial",
                    revision_index=0,
                    parent_plan_hash=None,
                    trigger_check_id=None,
                    trigger_event_sequence=None,
                    raw_arguments=old_shape,
                )
            ),
        },
        "repeated_location": {
            "boundary_equals_mutation": repeated_keys[0] == repeated_keys[-1],
            "accepted": True,
            "family_key": plan.causal_mechanism.mechanism_family_key,
            "prose_used_for_distinctness": plan.causal_mechanism.prose_used_for_distinctness,
        },
        "server_owned_observation": {
            "initial_status": plan.observation_status,
            "initial_observation_evidence": plan.observation_evidence,
            "revision_status": revision.observation_status,
            "revision_evidence_id": (
                None
                if revision.observation_evidence is None
                else revision.observation_evidence.evidence_id
            ),
            "revision_evidence_is_foundation": "pev:13"
            in {item.evidence_id for item in revision.foundation_evidence},
        },
        "server_owned_plan_bindings": {
            "foundation_ids": [item.evidence_id for item in plan.foundation_evidence],
            "candidate_files": [item.model_dump(mode="json") for item in plan.candidate_files],
            "planned_check_ids": list(plan.planned_check_ids),
            "candidate_outside_mechanism_rejection": _reason_code(
                lambda: normalize_causal_plan_request(
                    task=task,
                    catalog=static_catalog,
                    trigger="initial",
                    revision_index=0,
                    parent_plan_hash=None,
                    trigger_check_id=None,
                    trigger_event_sequence=None,
                    raw_arguments=nonmechanism_candidate,
                )
            ),
        },
        "round_trip": {
            "request_projection_hash": static_projection.content_hash,
            "plan_hash": plan.content_hash,
            "revision_hash": revision.content_hash,
            "same_input_same_projection": static_projection
            == project_causal_plan_request(task=task, catalog=static_catalog, trigger="initial"),
            "same_input_same_plan": plan
            == normalize_causal_plan_request(
                task=task,
                catalog=static_catalog,
                trigger="initial",
                revision_index=0,
                parent_plan_hash=None,
                trigger_check_id=None,
                trigger_event_sequence=None,
                raw_arguments=_arguments(),
            ),
        },
    }


def build_workflow_causal_plan_projection_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    predecessors: list[dict[str, Any]] = []
    for relative, expected in IMMUTABLE_PREDECESSORS.items():
        observed = _identity(
            root,
            relative,
            canonical_document=relative.endswith(".json"),
        )
        if any(observed.get(key) != value for key, value in expected.items()):
            raise ContractError(f"immutable causal-plan predecessor differs: {relative}")
        predecessors.append(observed)

    activation_path = tuple(IMMUTABLE_PREDECESSORS)[0]
    activation = json.loads((root / activation_path).read_text(encoding="utf-8"))
    diagnosis_path = tuple(IMMUTABLE_PREDECESSORS)[-1]
    diagnosis = json.loads((root / diagnosis_path).read_text(encoding="utf-8"))
    if (
        activation.get("scenarios", {})
        .get("bounded_workflow", {})
        .get("third_plan_dispatch_blocked")
        is not True
        or diagnosis.get("official") is not False
        or diagnosis.get("observed_batch", {}).get("agent_rows_started") != 6
        or diagnosis.get("observed_batch", {}).get("harness_admission_failures") != 0
        or diagnosis.get("source_bundle", {}).get("execution_hash")
        != "sha256:4799bfa0afaba2aeff57ae33d06eb676b4272251847c087515b4a3280fc936b3"
    ):
        raise ContractError("R13 causal-plan diagnosis boundary differs")

    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 26, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "server-owned-generic-public-causal-plan-input-projection",
        "policy_version": CAUSAL_PLAN_PROJECTION_POLICY,
        "runtime_version": None,
        "tool_schema_version": None,
        "context_policy_version": None,
        "runtime_surface_activated": False,
        "runtime_activation_authorized": False,
        "scenarios": _scenarios(),
        "source_files": [
            _identity(root, relative, canonical_document=False) for relative in SOURCE_FILES
        ],
        "immutable_predecessors": predecessors,
        "r13_binding": {
            "execution_hash": diagnosis["source_bundle"]["execution_hash"],
            "official": diagnosis["official"],
            "rows_started": diagnosis["observed_batch"]["agent_rows_started"],
            "v17_rows": next(
                item["rows"]
                for item in diagnosis["variants"]
                if item["variant"] == "lean-harness-v17"
            ),
            "v17_evaluator_reached": next(
                item["evaluator_reached"]
                for item in diagnosis["variants"]
                if item["variant"] == "lean-harness-v17"
            ),
            "r13_retry_allowed": False,
            "coding_quality_inferred": False,
        },
        "preserved_runtime_limits": {
            "existing_one_retry_fail_closed": True,
            "third_plan_dispatch_blocked": True,
            "correction_limit_changed": False,
            "review_correction_limit_changed": False,
            "activation_required_to_claim_runtime_preservation": True,
        },
        "evidence_boundary": {
            "public_synthetic_source_only": True,
            "r13_public_result_and_diagnosis_identity_only": True,
            "task_fixture_files_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "workspace_mutations": 0,
            "added_cost_usd": "0",
        },
        "paid_execution_authorized": False,
        "rapid_candidate_created": False,
        "quality_improvement_established": False,
        "runtime_behavior_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("causal-plan projection qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_causal_plan_projection_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_causal_plan_projection_successor_qualification(root)
    target = (root / QUALIFICATION_PATH).resolve()
    if not target.is_relative_to(root):
        raise ContractError("causal-plan projection qualification output escapes repository")
    raw = qualification_bytes(value)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return value


def load_workflow_causal_plan_projection_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = (root / QUALIFICATION_PATH).resolve()
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("causal-plan projection qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("causal-plan projection qualification bytes differ")
    if value != build_workflow_causal_plan_projection_successor_qualification(root):
        raise ContractError("causal-plan projection qualification source binding differs")
    return value


__all__ = [
    "IMMUTABLE_PREDECESSORS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_causal_plan_projection_successor_qualification",
    "load_workflow_causal_plan_projection_successor_qualification",
    "materialize_workflow_causal_plan_projection_successor_qualification",
    "qualification_bytes",
]
