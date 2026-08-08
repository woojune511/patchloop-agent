"""Seal the offline D-123 A/C cost-reservation and completion-gate source.

This milestone binds the immutable D-122 predecessor, an append-only R2 suite,
the exact four-row full-schedule cost contract, and the exact complete-matrix
gate implementation.  It performs no live preflight, pricing lookup, Docker,
provider, evaluator, retrieval, memory injection, or agent execution.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml

from patchloop.contracts import (
    AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
    DatasetRole,
)
from patchloop.dataset import require_frozen_dataset
from patchloop.errors import ContractError
from patchloop.evals import d122_ac_fixed_bundle_qualification as d122
from patchloop.evals.runner import (
    AC_FIXED_BUNDLE_COST_POLICY,
    AC_FIXED_BUNDLE_DURABLE_USAGE_EVIDENCE_SCHEMA,
    AC_FIXED_BUNDLE_FIXED_PRICING_SCHEMA,
    AC_FIXED_BUNDLE_FULL_SCHEDULE_COST_CONTROL_SCHEMA,
    _ac_fixed_bundle_descriptor,
    _campaign_cost_control,
    _is_ac_fixed_bundle_readiness_profile,
    _make_schedule,
    _suite_hash,
    load_suite,
)
from patchloop.memory.fixed_bundle import (
    FIXED_BUNDLE_BYTES,
    FIXED_BUNDLE_POLICY_VERSION,
    FIXED_BUNDLE_SHA256,
)
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-123"
SCHEMA_VERSION = "ac-fixed-bundle-cost-completion-offline-source-gate-d123-v1"
STATUS = "D123_AC_COST_COMPLETION_SOURCE_QUALIFIED_EXECUTION_CANDIDATE_BLOCKED"
SEALED_HISTORICAL_GATE_ID = (
    "d123_13fe44a6cc188de29dc38876fb60d114c8a777f8d05ad8b9db833b3d33cf4112"
)
SEALED_HISTORICAL_BODY_SHA256 = (
    "sha256:13fe44a6cc188de29dc38876fb60d114c8a777f8d05ad8b9db833b3d33cf4112"
)
SEALED_HISTORICAL_FILE_SHA256 = (
    "sha256:fab1543644ffefb9e4cda24d73207d3d9f66c07a5a1e006dec27a22699778e17"
)
SEALED_HISTORICAL_FILE_BYTES = 20_953

D122_PATH = Path(
    "reports/live-pilot/artifacts/d122-ac-fixed-bundle-offline-qualification-source-gate.json"
)
D122_GATE_ID = "d122_3fb93294d08f1b9a1359e4692dd8aaf9a8df19bef11ea5d66f0857d7eef320cc"
D122_BODY_SHA256 = "sha256:3fb93294d08f1b9a1359e4692dd8aaf9a8df19bef11ea5d66f0857d7eef320cc"
D122_FILE_SHA256 = "sha256:098cc27a457752f21250ecda79bc90061a91396a161cc450a2408e9f73640c24"
D122_FILE_BYTES = 12_699
D122_STATUS = "D122_OFFLINE_SOURCE_QUALIFIED_EXECUTION_CANDIDATE_BLOCKED"
R1_PLAN_PATH = Path("experiments/ac-structured-pilot.plan.yaml")
R1_PLAN_FILE_BYTES = 6_012
R1_PLAN_FILE_SHA256 = "sha256:11264131d847a64a0cead5b05affe84e35fa7241ca3b187a1361f294ce76643e"
R1_SUITE_PATH = Path("experiments/dev-validation-ac-fixed-bundle-readiness-20260808-r1.yaml")
R1_SUITE_FILE_BYTES = 2_274
R1_SUITE_FILE_SHA256 = "sha256:80358e3795b750d59f66b82da8460ed9c5a2178cbb3e08257c411a94f0f2b8bf"
R1_SUITE_HASH = "sha256:188dac3b6d2b39782554471e9a0c6cab9c2f27c773ae68bfb507175ea8ef87e3"

PLAN_PATH = Path("experiments/ac-structured-pilot-v2.plan.yaml")
PLAN_FILE_BYTES = 3_108
PLAN_FILE_SHA256 = "sha256:6da8e2f9477f3977e7faed3d49afec43def05c39c3316af3aceb555ae8e06963"
SUITE_PATH = Path("experiments/dev-validation-ac-fixed-bundle-readiness-20260808-r2.yaml")
SUITE_FILE_BYTES = 2_925
SUITE_FILE_SHA256 = "sha256:8ed7b07ab86cccab8412168dbcd95f2048ee21ee4d08ad02b0f8a7f68cb73467"
SUITE_HASH = "sha256:4564e57268619174c26ff85f243d2cb95cbb3f7cd7008cdf7391148913c2e9ce"
SCHEDULE_HASH = "sha256:df8c06972308783f6d02364f4e785b4f2ddb2602be0f56b4f487387cf2ea4bcc"
COST_CONTROL_HASH = "sha256:bd0093aeba056185c23991c2b5f5841c81f09fa4513462b40b2a1138871d7dcc"
DATASET_PATH = Path("data/dataset-manifest.yaml")
OUTPUT_PATH = Path(
    "reports/live-pilot/artifacts/d123-ac-cost-completion-offline-source-gate.json"
)

IMPLEMENTATION_PATHS = (
    Path("patchloop/contracts.py"),
    Path("patchloop/agent/runner.py"),
    Path("patchloop/evals/budget.py"),
    Path("patchloop/evals/qualification.py"),
    Path("patchloop/evals/runner.py"),
    Path("patchloop/evals/d122_ac_fixed_bundle_qualification.py"),
    Path("patchloop/evals/d123_ac_cost_completion_qualification.py"),
    Path("patchloop/memory/fixed_bundle.py"),
    Path("patchloop/runtime.py"),
    Path("scripts/build_d122_ac_fixed_bundle_qualification.py"),
    Path("scripts/build_d123_ac_cost_completion_qualification.py"),
    Path("tests/test_ac_fixed_bundle_cost_completion.py"),
    Path("tests/test_d122_ac_fixed_bundle_qualification.py"),
    Path("tests/test_d123_ac_cost_completion_qualification.py"),
)

ROOT_KEYS = (
    "schema_version",
    "gate_id",
    "semantic_body_hash",
    "semantic_body",
)
BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "predecessor_binding",
    "plan_binding",
    "suite_binding",
    "schedule_binding",
    "task_and_bundle_binding",
    "cost_reservation_and_settlement_contract",
    "completion_gate_contract",
    "implementation_integrity",
    "offline_qualification",
    "blocked_prerequisites",
    "evidence_boundary",
    "authority",
    "next_gate",
)

BLOCKED_PREREQUISITES = (
    "atomic-row-start-one-use-consumption-not-yet-qualified",
    "final-result-and-campaign-completed-crash-collision-recovery-not-yet-qualified",
    "clean-committed-source-identity-not-sealed",
    "fresh-official-pricing-within-72-hours-not-verified",
    "separately-authorized-no-call-docker-sdk-and-credential-presence-preflight-not-completed",
    "exact-runner-execution-hash-not-created",
    "one-use-execution-authorization-candidate-not-created",
    "separate-candidate-triple-execution-hash-and-55-dollar-cap-approval-missing",
)

EXPECTED_SCHEDULE_IDS = (
    "sha256:f1790045e63e225fd65c8c6e8b6e596b3bd55a4333aa483b3553d541404c3077",
    "sha256:6cfb4359eaa97ef29e87b16ff4467f8d3c7d165099a1f28fc8d1e6ada6f09be6",
    "sha256:9dce9621b4909280726e03074604e1b496910e7681c868c30ac541f98b2d1547",
    "sha256:336589fb3672961fb65cdff549124728a90a68b7a5d894d3430b960d46b5574b",
)
EXPECTED_TASK_CONDITIONS = (
    ("moto-query-scanned-count", "no_memory"),
    ("moto-query-scanned-count", "structured"),
    ("babel-strict-grouped-decimal-trailing-zeroes", "structured"),
    ("babel-strict-grouped-decimal-trailing-zeroes", "no_memory"),
)


class D123QualificationError(ContractError):
    """Raised when the D-123 source contract or canonical evidence drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D123QualificationError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise D123QualificationError("D-123 repository root is unavailable") from exc
    _require(root.is_dir(), "D-123 repository root is not a directory")
    return root


def _stable_read(root: Path, relative: Path) -> bytes:
    try:
        return d122._stable_read(root, relative)
    except ContractError as exc:
        raise D123QualificationError(f"D-123 cannot stably read {relative.as_posix()}") from exc


def _file_binding(root: Path, relative: Path) -> dict[str, Any]:
    content = _stable_read(root, relative)
    return {
        "path": relative.as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _load_yaml_exact(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(content.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise D123QualificationError(f"D-123 {label} is not valid UTF-8 YAML") from exc
    _require(isinstance(value, dict), f"D-123 {label} root is not an object")
    return value


def _implementation_state(root: Path) -> dict[str, Any]:
    files = [_file_binding(root, path) for path in IMPLEMENTATION_PATHS]
    return {
        "files": files,
        "file_count": len(files),
        "fingerprint": sha256_text(canonical_json(files)),
    }


def _predecessor_binding(root: Path) -> dict[str, Any]:
    _require(
        d122.OUTPUT_PATH == D122_PATH
        and d122.SEALED_HISTORICAL_GATE_ID == D122_GATE_ID
        and d122.SEALED_HISTORICAL_BODY_SHA256 == D122_BODY_SHA256
        and d122.SEALED_HISTORICAL_FILE_SHA256 == D122_FILE_SHA256
        and d122.SEALED_HISTORICAL_FILE_BYTES == D122_FILE_BYTES
        and d122.STATUS == D122_STATUS,
        "D-123 D-122 module constants differ from the independently pinned predecessor",
    )
    result = d122.validate_d122_source_gate(repository=root, mode="sealed-historical")
    _require(
        result
        == {
            "status": D122_STATUS,
            "gate_id": D122_GATE_ID,
            "semantic_body_hash": D122_BODY_SHA256,
            "file_bytes": D122_FILE_BYTES,
            "file_sha256": D122_FILE_SHA256,
            "execution_authorization_candidate_ready": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "docker_calls_made": 0,
        },
        "D-123 predecessor validation differs",
    )
    try:
        predecessor_payload = json.loads(_stable_read(root, D122_PATH).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D123QualificationError("D-123 predecessor body cannot be read") from exc
    predecessor_body = (
        predecessor_payload.get("semantic_body")
        if isinstance(predecessor_payload, dict)
        else None
    )
    predecessor_plan = (
        predecessor_body.get("plan_binding") if isinstance(predecessor_body, dict) else None
    )
    predecessor_suite = (
        predecessor_body.get("suite_binding") if isinstance(predecessor_body, dict) else None
    )
    r1_plan = _file_binding(root, R1_PLAN_PATH)
    r1_suite = _file_binding(root, R1_SUITE_PATH)
    _require(
        isinstance(predecessor_plan, dict)
        and predecessor_plan.get("path") == R1_PLAN_PATH.as_posix()
        and predecessor_plan.get("file_bytes") == R1_PLAN_FILE_BYTES
        and predecessor_plan.get("file_sha256") == R1_PLAN_FILE_SHA256
        and r1_plan
        == {
            "path": R1_PLAN_PATH.as_posix(),
            "file_bytes": R1_PLAN_FILE_BYTES,
            "file_sha256": R1_PLAN_FILE_SHA256,
        },
        "D-123 current R1 plan differs from the D-122 seal",
    )
    _require(
        isinstance(predecessor_suite, dict)
        and predecessor_suite.get("path") == R1_SUITE_PATH.as_posix()
        and predecessor_suite.get("file_bytes") == R1_SUITE_FILE_BYTES
        and predecessor_suite.get("file_sha256") == R1_SUITE_FILE_SHA256
        and predecessor_suite.get("suite_hash") == R1_SUITE_HASH
        and r1_suite
        == {
            "path": R1_SUITE_PATH.as_posix(),
            "file_bytes": R1_SUITE_FILE_BYTES,
            "file_sha256": R1_SUITE_FILE_SHA256,
        },
        "D-123 current R1 suite differs from the D-122 seal",
    )
    return {
        "milestone": "D-122",
        "path": D122_PATH.as_posix(),
        "gate_id": D122_GATE_ID,
        "semantic_body_hash": D122_BODY_SHA256,
        "file_bytes": D122_FILE_BYTES,
        "file_sha256": D122_FILE_SHA256,
        "status": D122_STATUS,
        "validation_mode": "sealed-historical",
        "historical_artifact_mutated": False,
        "r1_source_bytes": {
            "plan": {**r1_plan, "sealed_suite_or_plan_hash": None},
            "suite": {**r1_suite, "sealed_suite_or_plan_hash": R1_SUITE_HASH},
            "match_d122_bindings": True,
        },
    }


def _validate_plan(plan: dict[str, Any]) -> None:
    _require(
        set(plan)
        == {
            "schema_version",
            "plan_id",
            "status",
            "predecessor_plan",
            "suite",
            "matrix",
            "runtime",
            "cost",
            "completion",
            "authority",
            "next_gate",
        },
        "D-123 plan fields differ",
    )
    _require(
        plan.get("schema_version") == "ac-structured-pilot-plan-v2"
        and plan.get("plan_id") == "ac-structured-dev-validation-readiness-20260808-v2"
        and plan.get("status") == "offline-cost-and-completion-source-qualification"
        and plan.get("predecessor_plan") == "experiments/ac-structured-pilot.plan.yaml"
        and plan.get("suite") == SUITE_PATH.as_posix(),
        "D-123 plan identity differs",
    )
    matrix = plan.get("matrix")
    _require(
        isinstance(matrix, dict)
        and matrix.get("conditions") == ["no_memory", "structured"]
        and matrix.get("repetitions") == 1
        and matrix.get("expected_runs") == 4
        and matrix.get("replacement_or_retry_allowed") is False,
        "D-123 matrix contract differs",
    )
    cost = plan.get("cost")
    _require(
        cost
        == {
            "schema_version": "ac-fixed-bundle-full-schedule-reserve-v1",
            "per_run_reserve_nanos": 13_612_500_000,
            "full_schedule_reserve_nanos": 54_450_000_000,
            "hard_cap_nanos": 55_000_000_000,
            "hard_cap_slack_nanos": 550_000_000,
            "reserve_before_first_provider_call": True,
            "row_bound_settlement_required": True,
            "cost_censoring_allowed": False,
            "not_started_due_to_cost_allowed": False,
            "automatic_retry_or_replacement_allowed": False,
            "live_resume_policy": "disabled",
        },
        "D-123 plan cost contract differs",
    )
    completion = plan.get("completion")
    _require(
        completion
        == {
            "schema_version": "ac-fixed-bundle-readiness-complete-matrix-gate-v1",
            "official_evaluator_required_runs": 4,
            "accepted_outcomes": ["resolved", "task_failure"],
            "budget_terminal_allowed": False,
            "infrastructure_error_allowed": False,
            "qualification_error_allowed": False,
            "diagnostic_error_allowed": False,
            "task_success_required": False,
            "readiness_analysis_only": True,
            "memory_benefit_claim_allowed": False,
        },
        "D-123 plan completion contract differs",
    )
    _require(
        plan.get("authority")
        == {
            "offline_implementation_and_tests_authorized": True,
            "source_gate_materialization_authorized": True,
            "fresh_pricing_lookup_authorized": False,
            "docker_or_sdk_preflight_authorized": False,
            "exact_execution_hash_authorized": False,
            "execution_candidate_authorized": False,
            "provider_or_evaluator_execution_authorized": False,
            "runtime_memory_injection_authorized": False,
            "retrieval_or_core_authorized": False,
        },
        "D-123 plan authority differs",
    )
    _require(
        plan.get("next_gate")
        == {
            "action": (
                "separately-authorize-resolve-all-runtime-finalization-and-"
                "clean-no-call-preflight"
            ),
            "required_before_candidate": [
                "atomic-row-start-one-use-consumption-qualified",
                "final-result-and-campaign-completed-crash-collision-recovery-qualified",
                "clean-committed-source-identity-sealed",
                "official-pricing-refreshed-within-72-hours",
                "no-call-docker-sdk-credential-and-endpoint-preflight-completed",
                "exact-runner-execution-hash-created",
            ],
            "execution_candidate_requires_later_exact_approval": True,
        },
        "D-123 plan next gate differs",
    )


def _cost_contract(
    *,
    suite: Any,
    schedule: list[dict[str, Any]],
    schedule_hash: str,
) -> dict[str, Any]:
    row_ids = [row["schedule_row_id"] for row in schedule]
    control = _campaign_cost_control(
        suite,
        {
            "per_run_cost_reserve_usd": 13.6125,
            "budget_upper_bound_usd": 54.45,
        },
        schedule_size=4,
        schedule_hash=schedule_hash,
        schedule_row_ids=row_ids,
    )
    _require(isinstance(control, dict), "D-123 cost control was not derived")
    _require(
        control.get("schema_version") == AC_FIXED_BUNDLE_FULL_SCHEDULE_COST_CONTROL_SCHEMA
        and control.get("content_hash") == COST_CONTROL_HASH,
        "D-123 cost control identity differs",
    )
    usage_contract = {
        "schema_version": "ac-fixed-bundle-usage-settlement-source-contract-d123-v1",
        "durable_usage_schema": AC_FIXED_BUNDLE_DURABLE_USAGE_EVIDENCE_SCHEMA,
        "fixed_pricing_schema": AC_FIXED_BUNDLE_FIXED_PRICING_SCHEMA,
        "displayed_model_cost_usd_is_authoritative": False,
        "usage_tokens_are_repriced_with_integer_nano_usd": True,
        "persisted_result_and_qualification_hashes_required": True,
        "per_row_cost_must_not_exceed_reserve": True,
        "all_four_rows_must_settle": True,
        "invoice_or_free_tier_claimed": False,
    }
    journal_contract = {
        "schema_version": "ac-fixed-bundle-full-schedule-journal-source-contract-d123-v1",
        "required_initial_events": ["CampaignStarted", "FullScheduleCostReserved"],
        "per_row_events": ["RunStarted", "RunTerminal", "RunCostSettled"],
        "failed_settlement_event": "RunCostSettlementUnavailable",
        "required_final_event": "CampaignCompleted",
        "row_order_bound_to_schedule": True,
        "cooperative_append_tail_hash_checked_under_repository_local_lock": True,
        "reserve_fsynced_before_first_run_started": True,
        "automatic_retry_or_replacement_allowed": False,
        "live_resume_policy": "disabled",
        "atomic_row_start_one_use_consumption_verified": False,
        "noncooperative_path_swap_excluded": False,
        "descriptor_and_path_identity_rechecked_under_cooperative_lock": True,
        "agent_runner_root_bound_to_approved_root": True,
        "exact_event_and_usage_descriptor_keysets_and_monotonic_chronology_verified": True,
        "prior_row_durable_usage_reloaded_and_repriced_before_paid_call": True,
        "settlement_unavailable_is_sealed_as_inconclusive": True,
        "final_result_and_campaign_completed_crash_collision_recovery_verified": False,
        "global_or_cross_clone_exclusion_claimed": False,
    }
    return {
        "policy": AC_FIXED_BUNDLE_COST_POLICY,
        "policy_hash": sha256_text(canonical_json(AC_FIXED_BUNDLE_COST_POLICY)),
        "control": control,
        "usage_settlement_contract": usage_contract,
        "usage_settlement_contract_hash": sha256_text(canonical_json(usage_contract)),
        "journal_contract": journal_contract,
        "journal_contract_hash": sha256_text(canonical_json(journal_contract)),
        "reservation_source_implemented": True,
        "reservation_executed": False,
        "usage_settlement_result_present": False,
        "fresh_pricing_authority": False,
    }


def _completion_contract(plan: dict[str, Any]) -> dict[str, Any]:
    contract = {
        **plan["completion"],
        "experiment_id": AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
        "expected_task_condition_order": [list(value) for value in EXPECTED_TASK_CONDITIONS],
        "expected_schedule_row_ids": list(EXPECTED_SCHEDULE_IDS),
        "unique_run_ids_required": True,
        "terminal_qualified_trace_and_leak_pass_required": True,
        "official_evaluator_completed_required": True,
        "durable_cost_settlement_required": True,
        "resolved_scrr_and_four_verdict_conjunction_required": True,
        "not_started_or_budget_terminal_allowed": False,
        "memory_effect_claim_authorized": False,
        "heldout_or_core_claim_authorized": False,
    }
    return {
        "contract": contract,
        "contract_hash": sha256_text(canonical_json(contract)),
        "completion_gate_source_implemented": True,
        "completion_result_present": False,
        "analysis_ready": False,
    }


def _source_state(root: Path) -> dict[str, Any]:
    predecessor = _predecessor_binding(root)
    plan_binding = _file_binding(root, PLAN_PATH)
    suite_binding = _file_binding(root, SUITE_PATH)
    _require(
        plan_binding["file_bytes"] == PLAN_FILE_BYTES
        and plan_binding["file_sha256"] == PLAN_FILE_SHA256,
        "D-123 plan bytes differ",
    )
    _require(
        suite_binding["file_bytes"] == SUITE_FILE_BYTES
        and suite_binding["file_sha256"] == SUITE_FILE_SHA256,
        "D-123 suite bytes differ",
    )
    plan = _load_yaml_exact(_stable_read(root, PLAN_PATH), label="successor plan")
    _validate_plan(plan)
    suite = load_suite(root / SUITE_PATH)
    _require(
        suite.experiment_id == AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID
        and _is_ac_fixed_bundle_readiness_profile(suite),
        "D-123 suite is not the exact R2 A/C cost profile",
    )
    _require(_suite_hash(suite) == SUITE_HASH, "D-123 suite hash differs")
    _require(
        suite.campaign_cost_policy is not None
        and suite.campaign_cost_policy.model_dump(mode="json") == AC_FIXED_BUNDLE_COST_POLICY
        and suite.live_cost_approved is False
        and suite.approved_execution_hash is None
        and suite.pricing_verified_at is None,
        "D-123 suite authority differs",
    )
    dataset, dataset_hash, dataset_path = require_frozen_dataset(root / DATASET_PATH)
    _require(suite.dataset_manifest_hash == dataset_hash, "D-123 dataset hash differs")
    task_rows, task_bindings = d122._task_rows(root, dataset_path)
    schedule, schedule_hash = _make_schedule(suite, task_rows)
    _require(schedule_hash == SCHEDULE_HASH, "D-123 schedule hash differs")
    _require(
        tuple(row["schedule_row_id"] for row in schedule) == EXPECTED_SCHEDULE_IDS
        and tuple((row["task_id"], row["condition"]) for row in schedule)
        == EXPECTED_TASK_CONDITIONS,
        "D-123 schedule order or identity differs",
    )
    descriptor = _ac_fixed_bundle_descriptor()
    _require(
        descriptor.get("policy_version") == FIXED_BUNDLE_POLICY_VERSION
        and descriptor.get("bundle_bytes") == FIXED_BUNDLE_BYTES
        and descriptor.get("bundle_sha256") == FIXED_BUNDLE_SHA256,
        "D-123 fixed bundle descriptor differs",
    )
    plan_binding.update(
        {
            "schema_version": plan["schema_version"],
            "plan_id": plan["plan_id"],
            "status": plan["status"],
        }
    )
    suite_binding.update(
        {
            "schema_version": suite.schema_version,
            "experiment_id": suite.experiment_id,
            "purpose": suite.purpose.value,
            "suite_hash": SUITE_HASH,
            "memory_policy_version": suite.memory_policy_version,
            "live_cost_approved": suite.live_cost_approved,
            "approved_execution_hash": suite.approved_execution_hash,
            "pricing_verified_at": None,
        }
    )
    return {
        "predecessor_binding": predecessor,
        "plan_binding": plan_binding,
        "suite_binding": suite_binding,
        "schedule_binding": {
            "schedule_hash": schedule_hash,
            "expected_run_count": 4,
            "ordered_rows": [
                {
                    "order": row["order"],
                    "schedule_row_id": row["schedule_row_id"],
                    "task_id": row["task_id"],
                    "task_path": row["task"],
                    "condition": row["condition"],
                    "repetition": row["repetition"],
                    "split": row["split"],
                    "dataset_role": row["dataset_role"],
                    "evaluator_image_digest": row["evaluator_image_digest"],
                }
                for row in schedule
            ],
            "counterbalanced_task_pair_order": True,
            "automatic_retry_or_replacement_allowed": False,
        },
        "task_and_bundle_binding": {
            "dataset": {
                **_file_binding(root, DATASET_PATH),
                "dataset_id": dataset.dataset_id,
                "semantic_manifest_hash": dataset_hash,
                "status": dataset.status,
                "role": DatasetRole.DEVELOPMENT_VALIDATION.value,
            },
            "tasks": task_bindings,
            "fixed_bundle_descriptor": descriptor,
            "fixed_bundle_descriptor_hash": sha256_text(canonical_json(descriptor)),
            "delivery_policy_version": FIXED_BUNDLE_POLICY_VERSION,
            "delivery_cadence": "every-model-request",
            "retrieval_or_embedding_used": False,
        },
        "cost_reservation_and_settlement_contract": _cost_contract(
            suite=suite,
            schedule=schedule,
            schedule_hash=schedule_hash,
        ),
        "completion_gate_contract": _completion_contract(plan),
    }


def _body(
    *,
    recorded_at: str,
    source: dict[str, Any],
    implementation: dict[str, Any],
) -> dict[str, Any]:
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "offline-cost-reservation-and-completion-source-qualification",
        "recorded_at": recorded_at,
        "status": STATUS,
        "predecessor_binding": source["predecessor_binding"],
        "plan_binding": source["plan_binding"],
        "suite_binding": source["suite_binding"],
        "schedule_binding": source["schedule_binding"],
        "task_and_bundle_binding": source["task_and_bundle_binding"],
        "cost_reservation_and_settlement_contract": source[
            "cost_reservation_and_settlement_contract"
        ],
        "completion_gate_contract": source["completion_gate_contract"],
        "implementation_integrity": implementation,
        "offline_qualification": {
            "d122_historical_predecessor_validated": True,
            "d122_sealed_artifact_and_r1_source_bytes_preserved": True,
            "versioned_r2_successor_materialized": True,
            "exact_four_row_schedule_bijection_validated": True,
            "full_schedule_reservation_source_implemented": True,
            "durable_usage_settlement_source_implemented": True,
            "complete_matrix_gate_source_implemented": True,
            "d097_regression_tests_external_to_builder": True,
            "live_reservation_executed": False,
            "completion_result_present": False,
            "execution_authorization_candidate_ready": False,
            "focused_test_execution_is_external_to_builder": True,
        },
        "blocked_prerequisites": list(BLOCKED_PREREQUISITES),
        "evidence_boundary": {
            "development_validation_only": True,
            "heldout_or_core_tasks_used": False,
            "fresh_official_pricing_verified": False,
            "clean_committed_source_verified": False,
            "docker_or_sdk_preflight_verified": False,
            "network_or_socket_instrumentation_verified": False,
            "reservation_or_row_claim_executed": False,
            "final_result_and_campaign_completed_recovery_verified": False,
            "live_agent_result_present": False,
            "provider_or_evaluator_result_present": False,
            "memory_effect_or_negative_transfer_result_present": False,
            "source_path_and_guarded_test_evidence_only_for_zero_call_claims": True,
            "cooperative_single_writer_materialization_assumed": True,
            "noncooperative_output_parent_swap_excluded": False,
        },
        "authority": {
            "exact_d122_predecessor_bound": True,
            "d123_offline_source_gate_materialized": True,
            "r2_cost_policy_source_implemented": True,
            "r2_completion_gate_source_implemented": True,
            "reservation_executed": False,
            "completion_result_present": False,
            "atomic_row_start_one_use_consumption_verified": False,
            "final_result_and_campaign_completed_recovery_verified": False,
            "fresh_pricing_lookup_authorized": False,
            "docker_or_sdk_preflight_authorized": False,
            "exact_execution_hash_created": False,
            "approved_execution_hash": None,
            "execution_candidate_prepared": False,
            "execution_authorization_candidate_ready": False,
            "provider_execution_authorized": False,
            "evaluator_execution_authorized": False,
            "runtime_memory_injection_authorized": False,
            "retrieval_authorized": False,
            "agent_execution_authorized": False,
            "analysis_or_memory_benefit_claim_authorized": False,
            "core_or_heldout_campaign_authorized": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "docker_calls_made": 0,
            "agent_runs_made": 0,
            "retrieval_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": {
            "action": (
                "separately-authorize-resolve-all-runtime-finalization-and-"
                "clean-no-call-preflight"
            ),
            "requires_clean_committed_source": True,
            "requires_fresh_official_pricing_within_72_hours": True,
            "requires_atomic_row_start_one_use_qualification": True,
            "requires_final_result_and_campaign_completed_crash_collision_recovery": True,
            "requires_separately_authorized_no_call_docker_sdk_preflight": True,
            "then_prepare_exact_execution_authorization_candidate": True,
            "later_candidate_approval_must_repeat_candidate_triple_execution_hash_and_cap": True,
            "hard_cap_usd": 55.0,
            "does_not_authorize_execution": True,
        },
    }
    _require(tuple(body) == BODY_KEYS, "D-123 semantic body fields differ")
    return body


def _envelope(body: dict[str, Any]) -> dict[str, Any]:
    body_hash = sha256_text(canonical_json(body))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "gate_id": f"d123_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }
    _require(tuple(payload) == ROOT_KEYS, "D-123 gate fields differ")
    return payload


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (canonical_json(payload) + "\n").encode("utf-8")


def _parse_recorded_at(value: Any) -> str:
    _require(isinstance(value, str), "D-123 recorded_at is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise D123QualificationError("D-123 recorded_at is invalid") from exc
    _require(
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        "D-123 recorded_at is timezone-naive",
    )
    return value


def _validate_payload(
    *,
    root: Path,
    payload: dict[str, Any],
    raw: bytes,
) -> dict[str, Any]:
    _require(set(payload) == set(ROOT_KEYS), "D-123 gate root fields differ")
    _require(payload.get("schema_version") == SCHEMA_VERSION, "D-123 schema differs")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-123 semantic body is missing")
    _require(set(body) == set(BODY_KEYS), "D-123 semantic body fields differ")
    recorded_at = _parse_recorded_at(body.get("recorded_at"))
    expected = _envelope(
        _body(
            recorded_at=recorded_at,
            source=_source_state(root),
            implementation=_implementation_state(root),
        )
    )
    _require(raw == _canonical_bytes(expected), "D-123 full expected payload differs")
    return expected


def _result(payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "status": payload["semantic_body"]["status"],
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_authorization_candidate_ready": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
    }


def _validate_sealed_historical_payload(
    *,
    payload: dict[str, Any],
    raw: bytes,
) -> dict[str, Any]:
    _require(set(payload) == set(ROOT_KEYS), "D-123 gate root fields differ")
    _require(payload.get("schema_version") == SCHEMA_VERSION, "D-123 schema differs")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-123 semantic body is missing")
    _require(set(body) == set(BODY_KEYS), "D-123 semantic body fields differ")
    _parse_recorded_at(body.get("recorded_at"))
    _require(raw == _canonical_bytes(payload), "D-123 gate bytes are noncanonical")
    body_hash = sha256_text(canonical_json(body))
    _require(body_hash == SEALED_HISTORICAL_BODY_SHA256, "D-123 sealed body differs")
    _require(
        payload.get("semantic_body_hash") == body_hash,
        "D-123 semantic body hash differs",
    )
    _require(
        payload.get("gate_id") == SEALED_HISTORICAL_GATE_ID,
        "D-123 sealed gate ID differs",
    )
    _require(len(raw) == SEALED_HISTORICAL_FILE_BYTES, "D-123 sealed size differs")
    _require(
        sha256_bytes(raw) == SEALED_HISTORICAL_FILE_SHA256,
        "D-123 sealed file hash differs",
    )
    return payload


def validate_d123_source_gate(
    *,
    repository: str | Path | None = None,
    mode: Literal["current-source", "sealed-historical"] = "current-source",
) -> dict[str, Any]:
    """Validate the checked-in D-123 source gate against current exact inputs."""

    root = _repo_root(repository)
    raw = _stable_read(root, OUTPUT_PATH)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D123QualificationError("D-123 gate is not canonical UTF-8 JSON") from exc
    _require(isinstance(payload, dict), "D-123 gate root is not an object")
    if mode == "current-source":
        validated = _validate_payload(root=root, payload=payload, raw=raw)
    elif mode == "sealed-historical":
        validated = _validate_sealed_historical_payload(payload=payload, raw=raw)
    else:
        raise D123QualificationError("D-123 validation mode is unsupported")
    return _result(validated, raw)


def _write_new(root: Path, payload: dict[str, Any]) -> bytes:
    try:
        selected = d122._logical_path(root, OUTPUT_PATH, must_exist=False)
    except ContractError as exc:
        raise D123QualificationError("D-123 output path is unsafe") from exc
    _require(not selected.exists(), "D-123 source gate already exists")
    content = _canonical_bytes(payload)
    try:
        with selected.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise D123QualificationError("D-123 source gate cannot be created") from exc
    observed = _stable_read(root, OUTPUT_PATH)
    _require(observed == content, "D-123 source gate changed after creation")
    return observed


def run_d123_offline_source_gate(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Materialize once, or validate an already complete D-123 source gate."""

    root = _repo_root(repository)
    try:
        output = d122._logical_path(root, OUTPUT_PATH, must_exist=False)
    except ContractError as exc:
        raise D123QualificationError("D-123 output path is unsafe") from exc
    if output.exists():
        return validate_d123_source_gate(repository=root)
    source = _source_state(root)
    implementation = _implementation_state(root)
    recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload = _envelope(
        _body(
            recorded_at=recorded_at,
            source=source,
            implementation=implementation,
        )
    )
    raw = _write_new(root, payload)
    _validate_payload(root=root, payload=payload, raw=raw)
    return _result(payload, raw)


__all__ = [
    "D123QualificationError",
    "OUTPUT_PATH",
    "SEALED_HISTORICAL_BODY_SHA256",
    "SEALED_HISTORICAL_FILE_BYTES",
    "SEALED_HISTORICAL_FILE_SHA256",
    "SEALED_HISTORICAL_GATE_ID",
    "run_d123_offline_source_gate",
    "validate_d123_source_gate",
]
