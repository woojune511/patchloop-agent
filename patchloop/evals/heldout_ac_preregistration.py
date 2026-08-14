"""Read-only validation for the frozen held-out A/C preregistration.

This module deliberately is not an experiment runner.  It does not load task
packages, inspect credentials, probe Docker or an SDK, create an execution
hash, or write an artifact.  Its filesystem authority is limited to the
preregistration, the frozen dataset manifest, and four named predecessor
files whose bytes are committed by the preregistration.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from patchloop.contracts import DatasetManifest, DatasetRole
from patchloop.errors import ContractError
from patchloop.util import (
    canonical_json,
    load_unique_yaml,
    require_yaml_scalar_type_identity,
    sha256_bytes,
    sha256_json,
)

SCHEMA_VERSION = "heldout-ac-preregistration-v1"
PREREGISTRATION_ID = "core-ac-fixed-bundle-heldout-20260814-v1"
STATUS = "design-only"
DESIGN_BASE_COMMIT = "895132e04f81b34825d6886be5464ddb808169fc"
CONTENT_HASH = "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
FILE_BYTES = 31_338
FILE_SHA256 = "sha256:f6d9d015329823f3f888aac5f15296b2ddefda9e45b5d5501b8d94587bb11d8f"
PREREGISTRATION_PATH = Path("experiments/heldout-ac-preregistration-20260814-v1.yaml")
DATASET_MANIFEST_PATH = Path("data/dataset-manifest.yaml")

PREDECESSOR_BINDINGS: tuple[dict[str, Any], ...] = (
    {
        "path": "experiments/ac-structured-pilot-v11.plan.yaml",
        "file_bytes": 3_114,
        "file_sha256": "sha256:7df61e67d568f155a535abc61ba08f46650894dbbc2559c34ecd558121084b62",
        "relationship": "executed-r8-runtime-treatment-contract",
    },
    {
        "path": "experiments/dev-validation-ac-fixed-bundle-readiness-20260814-r8.yaml",
        "file_bytes": 3_248,
        "file_sha256": "sha256:cc318e805b0c1b68e440e947f7123fc283616256a5eb0ea749ad5c0b5c2cb699",
        "relationship": "executed-r8-suite-and-cost-predecessor",
    },
    {
        "path": (
            "reports/live-pilot/artifacts/"
            "evaluator-v2-ac-successor-offline-source-qualification-r10.json"
        ),
        "file_bytes": 20_843,
        "file_sha256": "sha256:09b0d96673db714497cc07c9ac5fb5b2ea52e877a6ab69663b566c440cc6d18b",
        "relationship": "executed-r8-source-qualification-predecessor",
    },
    {
        "path": (
            "reports/live-pilot/"
            "dev-validation-ac-fixed-bundle-readiness-20260814-r8-evidence-r4.json"
        ),
        "file_bytes": 19_557,
        "file_sha256": "sha256:5035421a63d58fededab133b77c72e23ee4ad6d380a37c8d1157ce7480b7c62c",
        "relationship": "corrected-r8-development-readiness-evidence",
    },
)

_TOP_LEVEL_KEYS = {
    "schema_version",
    "preregistration_id",
    "status",
    "created_date",
    "provenance",
    "dataset",
    "treatment",
    "schedule_design",
    "schedule",
    "runtime",
    "cost",
    "outcomes",
    "analysis",
    "exclusions",
    "stopping",
    "authority",
    "next_gate",
    "content_hash",
}
_DATASET_TASK_KEYS = {
    "task_id",
    "task_version",
    "path",
    "role",
    "public_spec_hash",
    "private_spec_hash",
    "upstream_repository",
    "environment_image",
    "difficulty_tier",
    "difficulty_total",
    "admission_state",
}
_SCHEDULE_ROW_KEYS = {
    "order",
    "wave",
    "task_id",
    "role",
    "condition",
    "repetition",
}

_SEALED_SECTION_HASHES = {
    "schedule_design": "sha256:52f58401c3626e5d788719ff0932f3f2a2abf1dd1cb092570ad0be461ff68a72",
    "outcomes": "sha256:03ea217e0092c84b02bedd1b896c3e7c5aabd174d6147bf83ab1af6934f54bc5",
    "analysis": "sha256:a044262a830b4615bf0ee9394879a22e46acce184a0894696baff2193b216a3a",
}

_EXPECTED_TREATMENT = {
    "conditions": ["no_memory", "structured"],
    "memory_policy_version": "fixed-d110-bundle-v1",
    "no_memory": {
        "selected_memory": None,
        "entry_count": 0,
        "bundle_bytes": 0,
        "bundle_sha256": None,
    },
    "structured": {
        "delivery": "exact-d110-three-entry-bundle-every-request",
        "entry_count": 3,
        "bundle_bytes": 3_528,
        "bundle_sha256": "sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf",
        "d110_index_version": (
            "idxgrp_563976c4443a725e287225cef1e718daf134fbb96574921cb9e020049ea52064"
        ),
        "d110_index_content_hash": (
            "sha256:3a99e6c190672d1676bc4d13604de989899de9ddac85d282cc90c4d56f426c56"
        ),
    },
    "query_embedding_or_similarity_used": False,
    "threshold_or_reranking_used": False,
    "only_treatment_difference": "selected-memory-content-and-derived-evidence",
}

_A_FIRST_IN_REPETITION_ONE = [
    "dagster-subset-partition-definition-selection",
    "fusesoc-retained-parse-error-diagnostics",
    "hf-hub-custom-tqdm-class-contract",
    "kubeflow-exit-handler-after-dependencies",
    "mtplx-mixed-content-tool-call-stream",
    "pyfakefs-file-wrapper-io-capabilities",
]
_PROJECTION_FIELDS = ["order", "task_id", "role", "condition", "repetition"]

_EXPECTED_RUNTIME = {
    "evaluator_version": "v2",
    "safety_contract_schema": "evaluator-safety-contract-v2",
    "receipt_schema": "evaluator-v2-evaluation-receipt-v1",
    "raw_result_official": False,
    "model": "openai",
    "model_id": "gpt-5.4-mini-2026-03-17",
    "reasoning_effort": "medium",
    "reasoning_mode": "standard",
    "service_tier": "default",
    "transport_max_retries": 0,
    "store": False,
    "system_prompt_version": "SYSTEM_PROMPT_V3",
    "tool_schema_version": "v2",
    "context_policy_version": "phase-evidence-v5",
    "memory_policy_version": "fixed-d110-bundle-v1",
    "sandbox_backend": "docker",
    "marker_profile": "task-private-plus-run-secret-exact-v1",
    "call_guard_policy": "model-tool-bounded-enforcement-v1",
    "max_output_tokens": 25_000,
    "token_budget_schema_version": "cumulative-split-v1",
    "max_cumulative_input_tokens": 4_000_000,
    "max_cumulative_output_tokens": 500_000,
    "max_total_tokens": 4_500_000,
    "max_model_calls": 240,
    "max_tool_calls": 400,
    "wall_clock_timeout_seconds": 3_600,
}

_EXPECTED_COST = {
    "schema_version": "heldout-ac-split-token-full-schedule-reserve-v1",
    "accounting_scope": "campaign-local",
    "accounting_basis": "split-token-ceiling-standard-list-price",
    "scheduled_run_count": 48,
    "input_reserve_rate_per_million_usd": 0.75,
    "output_reserve_rate_per_million_usd": 4.5,
    "cache_discount_assumed": False,
    "per_run_reserve_usd": 5.25,
    "full_schedule_reserve_usd": 252.0,
    "hard_cap_usd": 275.0,
    "hard_cap_slack_usd": 23.0,
    "money_scale": "nano-usd",
    "per_run_reserve_nanos": 5_250_000_000,
    "full_schedule_reserve_nanos": 252_000_000_000,
    "hard_cap_nanos": 275_000_000_000,
    "hard_cap_slack_nanos": 23_000_000_000,
    "reservation_mode": "row-bound-full-schedule-up-front",
    "initial_reservation_boundary": "before-first-provider-call",
    "row_reserve_count": 48,
    "cost_censoring_allowed": False,
    "not_started_due_to_cost_allowed": False,
    "automatic_retry_or_replacement_allowed": False,
    "settlement_basis": "durable-token-derived-standard-list-price",
    "live_resume_policy": "disabled",
    "completion_guaranteed": False,
    "invoice_or_free_tier_claimed": False,
    "pricing_basis_observed_at": "2026-08-13T12:05:26Z",
    "pricing_source_url": "https://developers.openai.com/api/docs/pricing",
    "pricing_refresh_required_before_candidate": True,
    "pricing_drift_disposition": "block-and-create-successor-cost-binding",
}

_EXPECTED_EXCLUSIONS = {
    "task_exclusions_after_preregistration_allowed": False,
    "post_outcome_exclusions_allowed": False,
    "imputation_allowed": False,
    "typed_agent_failures_included_as_zero": True,
    "typed_agent_failure_examples": [
        "token-budget-exhaustion",
        "model-call-limit",
        "tool-call-limit",
        "wall-clock-timeout",
        "submission-failure",
    ],
    "matrix_inconclusive_if": [
        "provider-sdk-docker-or-evaluator-infrastructure-error",
        "qualification-or-completion-contract-mismatch",
        "private-marker-or-leakage-hit",
        "schedule-treatment-runtime-source-or-hash-drift",
        "missing-durable-usage-or-cost-settlement",
        "duplicate-retried-replaced-or-resumed-row",
        "full-schedule-reservation-or-hard-cap-boundary-failure",
    ],
    "partial_rows_disposition": "diagnostic-only-not-headline",
}

_EXPECTED_STOPPING = {
    "fixed_scheduled_rows": 48,
    "interim_outcome_inspection_allowed": False,
    "efficacy_stop_allowed": False,
    "futility_stop_allowed": False,
    "adaptive_budget_allowed": False,
    "row_retry_allowed": False,
    "row_replacement_allowed": False,
    "automatic_resume_allowed": False,
    "infrastructure_or_contract_confound_action": "stop-before-next-provider-call",
    "remaining_rows_after_confound": "not_started",
    "primary_matrix_after_confound": "inconclusive",
    "fresh_campaign_required_after_confound": True,
    "pooling_fresh_campaign_without_prior_preregistration_allowed": False,
    "waves_are_operational_checkpoints_only": True,
}

_EXPECTED_AUTHORITY = {
    "provider_execution_authorized": False,
    "evaluator_execution_authorized": False,
    "agent_execution_authorized": False,
    "docker_observation_authorized": False,
    "sdk_observation_authorized": False,
    "credential_observation_or_provisioning_authorized": False,
    "runtime_memory_injection_authorized": False,
    "heldout_task_spec_content_inspection_authorized": False,
    "heldout_outcome_unblinding_authorized": False,
    "execution_hash_authorized": False,
    "execution_candidate_authorized": False,
    "cost_reservation_authorized": False,
    "spend_authorized": False,
    "automatic_retry_replacement_or_resume_authorized": False,
    "memory_benefit_claim_authorized": False,
    "authorized_provider_calls": 0,
    "authorized_evaluator_calls": 0,
    "authorized_agent_runs": 0,
    "authorized_docker_calls": 0,
    "authorized_sdk_calls": 0,
    "authorized_cost_usd": 0.0,
}

_EXPECTED_NEXT_GATE = {
    "action": "implement-and-offline-validate-heldout-ac-strict-contracts",
    "scope": [
        "standalone-preregistration-validator",
        "dedicated-48-row-suite-schema",
        "dedicated-heldout-source-qualification",
        "typed-agent-failure-aware-completion-adapter",
        "task-cluster-scheduled-row-complete-panel-analysis",
    ],
    "may_open_heldout_task_specs_or_outcomes": False,
    "may_make_provider_evaluator_agent_docker_or_sdk_calls": False,
    "may_reserve_or_spend_cost": False,
    "requires_new_source_qualification": True,
    "requires_exact_execution_candidate": True,
    "requires_separate_explicit_paid_approval": True,
    "grants_execution_authority": False,
}


class HeldoutACPreregistrationError(ContractError):
    """Raised when the design-only preregistration is malformed or drifts."""


def _repository_root(repository: str | Path | None) -> Path:
    root = (
        Path(repository).resolve()
        if repository is not None
        else Path(__file__).resolve().parents[2]
    )
    if not root.is_dir():
        raise HeldoutACPreregistrationError("preregistration repository root is unavailable")
    return root


def _closed_path(root: Path, relative: Path | str, *, label: str) -> Path:
    """Resolve one allow-listed repository file without following path indirection."""

    candidate = root / Path(relative)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise HeldoutACPreregistrationError(f"{label} is unavailable") from exc
    if resolved != candidate.absolute() or not resolved.is_file():
        raise HeldoutACPreregistrationError(f"{label} must be a direct repository file")
    return resolved


def _mapping(value: Any, *, path: str, keys: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HeldoutACPreregistrationError(f"{path} must be a mapping")
    if any(type(key) is not str for key in value):
        raise HeldoutACPreregistrationError(f"{path} keys must be strings")
    if keys is not None and set(value) != keys:
        missing = sorted(keys - set(value))
        extra = sorted(set(value) - keys)
        raise HeldoutACPreregistrationError(
            f"{path} fields differ: missing={missing or []}, extra={extra or []}"
        )
    return value


def _list(value: Any, *, path: str, length: int | None = None) -> list[Any]:
    if type(value) is not list:
        raise HeldoutACPreregistrationError(f"{path} must be a list")
    if length is not None and len(value) != length:
        raise HeldoutACPreregistrationError(f"{path} must contain exactly {length} items")
    return value


def _exact(actual: Any, expected: Any, *, path: str) -> None:
    """Compare a machine contract without bool/int/float equivalence."""

    if type(actual) is not type(expected):
        raise HeldoutACPreregistrationError(
            f"{path} type differs: expected {type(expected).__name__}, got {type(actual).__name__}"
        )
    if isinstance(expected, Mapping):
        if set(actual) != set(expected):
            raise HeldoutACPreregistrationError(f"{path} fields differ")
        for key in expected:
            _exact(actual[key], expected[key], path=f"{path}.{key}")
        return
    if isinstance(expected, Sequence) and not isinstance(expected, (str, bytes, bytearray)):
        if len(actual) != len(expected):
            raise HeldoutACPreregistrationError(f"{path} length differs")
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected, strict=True)):
            _exact(actual_item, expected_item, path=f"{path}[{index}]")
        return
    if actual != expected:
        raise HeldoutACPreregistrationError(f"{path} differs")


def _read_yaml(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw_bytes = path.read_bytes()
        value = load_unique_yaml(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise HeldoutACPreregistrationError(f"{label} is unreadable") from exc
    return _mapping(value, path=label), raw_bytes


def _validate_predecessors(root: Path, provenance: dict[str, Any]) -> None:
    _mapping(
        provenance,
        path="provenance",
        keys={
            "design_base_commit",
            "heldout_task_specs_opened_for_design",
            "heldout_run_outcomes_opened_for_design",
            "predecessors",
        },
    )
    commit = provenance["design_base_commit"]
    _exact(commit, DESIGN_BASE_COMMIT, path="provenance.design_base_commit")
    _exact(
        provenance["heldout_task_specs_opened_for_design"],
        False,
        path="provenance.heldout_task_specs_opened_for_design",
    )
    _exact(
        provenance["heldout_run_outcomes_opened_for_design"],
        False,
        path="provenance.heldout_run_outcomes_opened_for_design",
    )
    rows = _list(provenance["predecessors"], path="provenance.predecessors", length=4)
    observed_paths: list[str] = []
    expected_by_path = {row["path"]: row for row in PREDECESSOR_BINDINGS}
    for index, value in enumerate(rows):
        row = _mapping(
            value,
            path=f"provenance.predecessors[{index}]",
            keys={"path", "file_bytes", "file_sha256", "relationship"},
        )
        path = row["path"]
        if type(path) is not str or path not in expected_by_path:
            raise HeldoutACPreregistrationError(
                "predecessor path is not in the closed four-file set"
            )
        expected = expected_by_path[path]
        _exact(row, expected, path=f"predecessor {path}")
        try:
            content = _closed_path(root, path, label=f"predecessor {path}").read_bytes()
        except OSError as exc:
            raise HeldoutACPreregistrationError(f"predecessor is unreadable: {path}") from exc
        if (
            len(content) != expected["file_bytes"]
            or sha256_bytes(content) != expected["file_sha256"]
        ):
            raise HeldoutACPreregistrationError(f"predecessor bytes drifted: {path}")
        observed_paths.append(path)
    if observed_paths != [row["path"] for row in PREDECESSOR_BINDINGS]:
        raise HeldoutACPreregistrationError("predecessors must use the canonical four-file order")


def _dataset_task_projection(entry: Any) -> dict[str, Any]:
    return {
        "task_id": entry.task_id,
        "task_version": entry.task_version,
        "path": entry.path,
        "role": entry.role.value,
        "public_spec_hash": entry.public_spec_hash,
        "private_spec_hash": entry.private_spec_hash,
        "upstream_repository": entry.source.upstream_repository,
        "environment_image": entry.source.environment_image,
        "difficulty_tier": entry.difficulty.tier.value,
        "difficulty_total": entry.difficulty.total,
        "admission_state": entry.admission_state.value,
    }


def _validate_dataset(root: Path, value: dict[str, Any]) -> dict[str, dict[str, Any]]:
    _mapping(
        value,
        path="dataset",
        keys={"manifest", "required_roles", "task_count", "task_selection_rule", "tasks"},
    )
    manifest_binding = _mapping(
        value["manifest"],
        path="dataset.manifest",
        keys={"path", "file_bytes", "file_sha256", "schema_version", "dataset_id", "status"},
    )
    _exact(manifest_binding["path"], DATASET_MANIFEST_PATH.as_posix(), path="dataset.manifest.path")
    manifest_path = _closed_path(root, DATASET_MANIFEST_PATH, label="dataset manifest")
    manifest_raw, manifest_bytes = _read_yaml(manifest_path, label="dataset manifest")
    if (
        type(manifest_binding["file_bytes"]) is not int
        or type(manifest_binding["file_sha256"]) is not str
    ):
        raise HeldoutACPreregistrationError("dataset manifest byte identity has wrong types")
    if manifest_binding["file_bytes"] != len(manifest_bytes) or manifest_binding[
        "file_sha256"
    ] != sha256_bytes(manifest_bytes):
        raise HeldoutACPreregistrationError("dataset manifest byte identity drifted")
    try:
        manifest = DatasetManifest.model_validate(manifest_raw)
        require_yaml_scalar_type_identity(
            manifest_raw,
            manifest.model_dump(mode="python"),
            source=DATASET_MANIFEST_PATH.name,
        )
    except (ValidationError, ContractError) as exc:
        raise HeldoutACPreregistrationError("dataset manifest contract is invalid") from exc
    _exact(manifest_binding["schema_version"], manifest.schema_version, path="dataset schema")
    _exact(manifest_binding["dataset_id"], manifest.dataset_id, path="dataset id")
    _exact(manifest_binding["status"], "frozen", path="dataset status")
    if manifest.status != "frozen":
        raise HeldoutACPreregistrationError("dataset manifest is not frozen")

    core_entries = [
        entry
        for entry in manifest.tasks
        if entry.role in {DatasetRole.CORE_SAME_REPO, DatasetRole.CORE_CROSS_REPO}
    ]
    if len(core_entries) != 12:
        raise HeldoutACPreregistrationError("frozen core panel must contain exactly 12 tasks")
    expected_roles = {"core-same-repo": 6, "core-cross-repo": 6}
    _exact(value["required_roles"], expected_roles, path="dataset.required_roles")
    _exact(value["task_count"], 12, path="dataset.task_count")
    _exact(
        value["task_selection_rule"],
        "complete-admitted-core-same-repo-and-core-cross-repo-panel",
        path="dataset.task_selection_rule",
    )

    rows = _list(value["tasks"], path="dataset.tasks", length=12)
    expected_by_id = {entry.task_id: _dataset_task_projection(entry) for entry in core_entries}
    observed: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(rows):
        row = _mapping(item, path=f"dataset.tasks[{index}]", keys=_DATASET_TASK_KEYS)
        task_id = row["task_id"]
        if type(task_id) is not str or task_id not in expected_by_id or task_id in observed:
            raise HeldoutACPreregistrationError(
                "dataset task identities are not an exact unique core set"
            )
        _exact(row, expected_by_id[task_id], path=f"dataset task {task_id}")
        observed[task_id] = row
    if set(observed) != set(expected_by_id):
        raise HeldoutACPreregistrationError("dataset task set differs from the frozen core panel")
    return observed


def _validate_schedule(
    value: Any,
    *,
    tasks: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = _list(value, path="schedule", length=48)
    seen_cells: set[tuple[str, int, str]] = set()
    for index, item in enumerate(rows):
        row = _mapping(item, path=f"schedule[{index}]", keys=_SCHEDULE_ROW_KEYS)
        if type(row["order"]) is not int or row["order"] != index + 1:
            raise HeldoutACPreregistrationError("schedule orders must be contiguous from one")
        if type(row["wave"]) is not int or row["wave"] not in {1, 2, 3, 4}:
            raise HeldoutACPreregistrationError("schedule wave must be an integer from one to four")
        task_id = row["task_id"]
        if type(task_id) is not str or task_id not in tasks:
            raise HeldoutACPreregistrationError("schedule references an unknown held-out task")
        _exact(row["role"], tasks[task_id]["role"], path=f"schedule role {task_id}")
        condition = row["condition"]
        repetition = row["repetition"]
        if type(condition) is not str or condition not in {"no_memory", "structured"}:
            raise HeldoutACPreregistrationError(
                "schedule condition must be no_memory or structured"
            )
        if type(repetition) is not int or repetition not in {1, 2}:
            raise HeldoutACPreregistrationError("schedule repetition must be one or two")
        cell = (task_id, repetition, condition)
        if cell in seen_cells:
            raise HeldoutACPreregistrationError(
                "schedule contains a duplicate task/repetition/condition cell"
            )
        seen_cells.add(cell)
    expected_cells = {
        (task_id, repetition, condition)
        for task_id in tasks
        for repetition in (1, 2)
        for condition in ("no_memory", "structured")
    }
    if seen_cells != expected_cells:
        raise HeldoutACPreregistrationError("schedule is not the exact 12 by A/C by two matrix")
    if {row["wave"] for row in rows} != {1, 2, 3, 4} or any(
        sum(row["wave"] == wave for row in rows) != 12 for wave in range(1, 5)
    ):
        raise HeldoutACPreregistrationError("schedule must contain four waves of twelve rows")
    expected_rows = _derived_schedule(tasks)
    _exact(rows, expected_rows, path="schedule deterministic projection")
    return rows


def _derived_schedule(tasks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Reconstruct the preregistered schedule from public registry metadata only."""

    seed = "20260814"
    short_roles = {
        "core-same-repo": "same",
        "core-cross-repo": "cross",
    }
    orientation = sorted(
        tasks,
        key=lambda task_id: sha256_bytes(f"{seed}|orientation|{task_id}".encode()),
    )
    a_first_repetition_one = set(orientation[:6])
    _exact(
        sorted(a_first_repetition_one),
        _A_FIRST_IN_REPETITION_ONE,
        path="schedule A-first orientation set",
    )

    rows: list[dict[str, Any]] = []
    for repetition in (1, 2):
        ranked: dict[str, list[str]] = {}
        for role, short_role in short_roles.items():
            role_tasks = [task_id for task_id, task in tasks.items() if task["role"] == role]
            ranked[role] = sorted(
                role_tasks,
                key=lambda task_id: sha256_bytes(
                    (f"{seed}|round={repetition}|role={short_role}|task={task_id}").encode()
                ),
            )
        role_order = (
            ("core-same-repo", "core-cross-repo")
            if repetition == 1
            else ("core-cross-repo", "core-same-repo")
        )
        blocks = [ranked[role][rank] for rank in range(6) for role in role_order]
        for block_index, task_id in enumerate(blocks):
            wave = (1 if repetition == 1 else 3) + (block_index // 6)
            a_first = task_id in a_first_repetition_one
            if repetition == 2:
                a_first = not a_first
            conditions = ("no_memory", "structured") if a_first else ("structured", "no_memory")
            for condition in conditions:
                rows.append(
                    {
                        "order": len(rows) + 1,
                        "wave": wave,
                        "task_id": task_id,
                        "role": tasks[task_id]["role"],
                        "condition": condition,
                        "repetition": repetition,
                    }
                )
    return rows


def _validate_content_hash(payload: dict[str, Any]) -> None:
    content_hash = payload["content_hash"]
    if type(content_hash) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", content_hash) is None:
        raise HeldoutACPreregistrationError("content_hash is not a SHA-256 identity")
    expected = sha256_json({key: value for key, value in payload.items() if key != "content_hash"})
    if content_hash != expected:
        raise HeldoutACPreregistrationError("preregistration content hash mismatch")


def _validate_sealed_file_identity(payload: dict[str, Any], raw_bytes: bytes) -> None:
    _exact(payload["content_hash"], CONTENT_HASH, path="sealed content_hash")
    _exact(len(raw_bytes), FILE_BYTES, path="sealed file_bytes")
    _exact(sha256_bytes(raw_bytes), FILE_SHA256, path="sealed file_sha256")


def load_heldout_ac_preregistration(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Load and validate the design-only preregistration without execution probes."""

    root = _repository_root(repository)
    payload, raw_bytes = _read_yaml(
        _closed_path(root, PREREGISTRATION_PATH, label="held-out A/C preregistration"),
        label="held-out A/C preregistration",
    )
    _mapping(payload, path="preregistration", keys=_TOP_LEVEL_KEYS)
    _exact(payload["schema_version"], SCHEMA_VERSION, path="schema_version")
    _exact(payload["preregistration_id"], PREREGISTRATION_ID, path="preregistration_id")
    _exact(payload["status"], STATUS, path="status")
    _exact(payload["created_date"], "2026-08-14", path="created_date")
    _validate_content_hash(payload)
    _validate_predecessors(root, _mapping(payload["provenance"], path="provenance"))
    tasks = _validate_dataset(root, _mapping(payload["dataset"], path="dataset"))
    schedule = _validate_schedule(payload["schedule"], tasks=tasks)

    # The remaining sections are strict closed mappings.  Their exact field and
    # semantic checks live below the structural validation so malformed inputs
    # fail before any interpretation can broaden authority.
    _validate_design_sections(payload, schedule=schedule)
    _validate_sealed_file_identity(payload, raw_bytes)
    return {
        "schema_version": payload["schema_version"],
        "preregistration_id": payload["preregistration_id"],
        "status": payload["status"],
        "content_hash": payload["content_hash"],
        "file_bytes": len(raw_bytes),
        "file_sha256": sha256_bytes(raw_bytes),
        "task_count": len(tasks),
        "expected_runs": len(schedule),
        "provider_calls_authorized": False,
        "added_model_cost_usd": 0,
    }


def _validate_design_sections(payload: dict[str, Any], *, schedule: list[dict[str, Any]]) -> None:
    """Validate treatment, runtime, analysis, stopping, and closed authority."""

    expected_sections = {
        "treatment": _EXPECTED_TREATMENT,
        "runtime": _EXPECTED_RUNTIME,
        "cost": _EXPECTED_COST,
        "exclusions": _EXPECTED_EXCLUSIONS,
        "stopping": _EXPECTED_STOPPING,
        "authority": _EXPECTED_AUTHORITY,
        "next_gate": _EXPECTED_NEXT_GATE,
    }
    for key, expected in expected_sections.items():
        section = _mapping(payload[key], path=key, keys=set(expected))
        _exact(section, expected, path=key)

    for key, expected_hash in _SEALED_SECTION_HASHES.items():
        section = _mapping(payload[key], path=key)
        _exact(sha256_json(section), expected_hash, path=f"{key} sealed section hash")

    projection_fields = _PROJECTION_FIELDS
    projection = [{field: row[field] for field in projection_fields} for row in schedule]
    projection_bytes = canonical_json(projection).encode("utf-8")
    _exact(
        len(projection_bytes),
        payload["schedule_design"]["projection_bytes"],
        path="schedule_design.projection_bytes",
    )
    _exact(
        sha256_bytes(projection_bytes),
        payload["schedule_design"]["projection_sha256"],
        path="schedule_design.projection_sha256",
    )

    per_run = (
        payload["runtime"]["max_cumulative_input_tokens"]
        * payload["cost"]["input_reserve_rate_per_million_usd"]
        + payload["runtime"]["max_cumulative_output_tokens"]
        * payload["cost"]["output_reserve_rate_per_million_usd"]
    ) / 1_000_000
    _exact(per_run, payload["cost"]["per_run_reserve_usd"], path="cost per-run arithmetic")
    _exact(
        per_run * len(schedule),
        payload["cost"]["full_schedule_reserve_usd"],
        path="cost full-schedule arithmetic",
    )
    _exact(
        payload["cost"]["hard_cap_usd"] - payload["cost"]["full_schedule_reserve_usd"],
        payload["cost"]["hard_cap_slack_usd"],
        path="cost hard-cap slack arithmetic",
    )


__all__ = [
    "DATASET_MANIFEST_PATH",
    "DESIGN_BASE_COMMIT",
    "CONTENT_HASH",
    "FILE_BYTES",
    "FILE_SHA256",
    "PREDECESSOR_BINDINGS",
    "PREREGISTRATION_ID",
    "PREREGISTRATION_PATH",
    "SCHEMA_VERSION",
    "STATUS",
    "HeldoutACPreregistrationError",
    "load_heldout_ac_preregistration",
]
