"""Fail-closed paid-boundary contracts for the preregistered held-out A/C panel.

This module is deliberately side-effect free.  It validates an already persisted
approved plan and the append-only journal prefix that must exist before one exact
row may enter the provider runtime.  Plan persistence, journal appends and actual
row dispatch are owned by :mod:`patchloop.evals.heldout_ac_dispatcher`.
"""

from __future__ import annotations

import json
import os
import re
import stat
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from patchloop.contracts import (
    DatasetRole,
    ExperimentPurpose,
    MemoryCondition,
    RunManifest,
)
from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_contracts import HELDOUT_AC_SUITE_ID
from patchloop.evals.heldout_ac_execution import (
    HeldoutACExecutionCandidate,
    heldout_ac_campaign_identity_hash,
)
from patchloop.evals.heldout_ac_persisted_adapter import (
    HeldoutACAuthenticatedPersistedEvidence,
    HeldoutACAuthenticatedPersistedRow,
)
from patchloop.evals.heldout_ac_suite import load_heldout_ac_suite
from patchloop.memory.fixed_bundle import (
    D110_INDEX_CONTENT_HASH,
    D110_INDEX_VERSION,
    FIXED_BUNDLE_POLICY_VERSION,
)
from patchloop.util import safe_relative_path, sha256_bytes, sha256_json

PLAN_SCHEMA_VERSION = "experiment-execution-plan-v1"
PLAN_SCHEMA_VERSION_V2 = "experiment-execution-plan-v2"
PLAN_KIND = "heldout-ac-approved-campaign-v1"
PLAN_KIND_V2 = "heldout-ac-approved-campaign-v2"
RUNTIME_CONTRACT_SCHEMA_VERSION = "heldout-ac-runtime-contract-v1"
RUNTIME_EVIDENCE_SCHEMA_VERSION = "heldout-ac-runtime-evidence-v1"
JOURNAL_SCHEMA_VERSION = "heldout-ac-campaign-journal-event-v1"
JOURNAL_SCHEMA_VERSION_V2 = "heldout-ac-campaign-journal-event-v2"
CALL_GUARD_POLICY_VERSION = "heldout-ac-bounded-call-guard-v1"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RUN_ID_RE = re.compile(r"^run_[A-Za-z0-9_-]+$")
_SUITE_PATH = Path("experiments/heldout-ac-suite-20260814-v1.yaml")


def _exact_typed_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _exact_typed_equal(actual[key], expected[key]) for key in expected
        )
    if isinstance(expected, (list, tuple)):
        return len(actual) == len(expected) and all(
            _exact_typed_equal(left, right) for left, right in zip(actual, expected, strict=True)
        )
    return bool(actual == expected)


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _canonical_utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == UTC.utcoffset(parsed)


def _is_link_or_reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and is_junction():
        return True
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def canonical_heldout_ac_runtime_path(
    path: str | Path,
    *,
    expected_run_root: str | Path,
) -> Path:
    """Return one lexical runtime path after containment and link checks."""

    raw_root = Path(expected_run_root).absolute()
    try:
        if not raw_root.is_dir() or _is_link_or_reparse_point(raw_root):
            raise ContractError("held-out runtime root is not a canonical directory")
        root = raw_root.resolve(strict=True)
    except OSError as exc:
        raise ContractError("held-out runtime root is unavailable") from exc
    candidate = Path(os.path.abspath(Path(path)))
    if not candidate.is_relative_to(root):
        raise ContractError("held-out runtime path escapes the expected root")
    current = root
    for part in candidate.relative_to(root).parts:
        current /= part
        if (current.exists() or current.is_symlink()) and _is_link_or_reparse_point(current):
            raise ContractError("held-out runtime path traverses a link or reparse point")
    if not candidate.resolve(strict=False).is_relative_to(root):
        raise ContractError("held-out runtime path resolves outside the expected root")
    return candidate


def is_heldout_ac_experiment(manifest: RunManifest | None) -> bool:
    """Recognize the reserved identity even when the rest of a manifest is corrupt."""

    return bool(
        manifest is not None
        and manifest.experiment is not None
        and manifest.experiment.experiment_id == HELDOUT_AC_SUITE_ID
    )


def heldout_ac_candidate_has_current_source_binding(
    candidate: HeldoutACExecutionCandidate,
    *,
    repository: str | Path | None = None,
) -> bool:
    """Revalidate the checked-in current artifact instead of trusting candidate fields."""

    from patchloop.evals.heldout_ac_preflight_source_qualification import (
        load_heldout_ac_preflight_source_binding,
    )

    try:
        expected = load_heldout_ac_preflight_source_binding(repository=repository)
    except ContractError:
        return False
    return candidate.source_qualification == expected


def heldout_ac_candidate_has_bound_source_qualification(
    candidate: HeldoutACExecutionCandidate,
    *,
    repository: str | Path | None = None,
) -> bool:
    """Validate the immutable qualification artifact named by this candidate.

    Historical replay must remain valid after a newer source qualification is
    checked in.  It therefore verifies the candidate-bound bytes and identities,
    while dispatch preparation separately requires the current source binding.
    """

    root = Path(repository).resolve() if repository is not None else Path.cwd().resolve()
    binding = candidate.source_qualification
    try:
        relative = safe_relative_path(
            binding.qualification_file.path,
            field_name="held-out source qualification path",
        )
        selected = (root / relative).resolve(strict=True)
        raw = selected.read_bytes()
        payload = json.loads(raw)
    except (ContractError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    body = (
        {key: value for key, value in payload.items() if key != "content_hash"}
        if isinstance(payload, dict)
        else None
    )
    return bool(
        selected.is_relative_to(root)
        and not selected.is_symlink()
        and isinstance(payload, dict)
        and isinstance(body, dict)
        and len(raw) == binding.qualification_file.file_bytes
        and sha256_bytes(raw) == binding.qualification_file.file_sha256
        and payload.get("content_hash") == binding.qualification_file.content_hash
        and payload.get("content_hash") == binding.source_qualification_hash
        and payload.get("content_hash") == sha256_json(body)
        and payload.get("qualification_id") == binding.qualification_id
        and payload.get("evaluator_source_hash") == binding.evaluator_source_hash
    )


def _expected_memory(candidate_row: Any) -> dict[str, Any]:
    structured = candidate_row.condition == MemoryCondition.STRUCTURED.value
    return {
        "condition": candidate_row.condition,
        "index_version": D110_INDEX_VERSION if structured else None,
        "index_hash": D110_INDEX_CONTENT_HASH if structured else None,
        "max_context_tokens": 2_000,
    }


def heldout_ac_manifest_matches_candidate(
    manifest: RunManifest,
    candidate: HeldoutACExecutionCandidate,
) -> bool:
    """Match every public runtime field that is fixed before secret expansion."""

    experiment = manifest.experiment
    if experiment is None or not 1 <= experiment.schedule_order <= 48:
        return False
    row = candidate.schedule[experiment.schedule_order - 1]
    expected_role = (
        DatasetRole.CORE_SAME_REPO
        if row.role == DatasetRole.CORE_SAME_REPO.value
        else DatasetRole.CORE_CROSS_REPO
    )
    expected_model = {
        "provider": "openai",
        "model_id": "gpt-5.4-mini-2026-03-17",
        "provider_sdk_version": candidate.readiness.openai_sdk.version,
        "replay_hash": None,
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "transport_max_retries": 0,
        "temperature": 0.0,
        "max_output_tokens": 25_000,
        "input_price_per_million_usd": 0.75,
        "cached_input_price_per_million_usd": 0.075,
        "cache_write_input_price_per_million_usd": 0.75,
        "output_price_per_million_usd": 4.5,
    }
    expected_budget = {
        "max_model_calls": 240,
        "max_tool_calls": 400,
        "max_total_tokens": 4_500_000,
        "wall_clock_timeout_seconds": 3_600,
        "token_budget_schema_version": "cumulative-split-v1",
        "max_cumulative_input_tokens": 4_000_000,
        "max_cumulative_output_tokens": 500_000,
    }
    return bool(
        manifest.schema_version == "run-manifest-v2"
        and manifest.task_id == row.task_id
        and manifest.task_version == row.task_version
        and manifest.base_commit == row.base_commit
        and manifest.public_spec_hash == row.public_spec_hash
        and manifest.private_spec_hash == row.private_spec_hash
        and manifest.evaluator_contract is not None
        and manifest.evaluator_contract.task_id == row.task_id
        and manifest.evaluator_contract.evaluator_source_hash
        == candidate.source_qualification.evaluator_source_hash
        and manifest.harness_git_commit == candidate.readiness.git.commit
        and manifest.tool_schema_version == "v2"
        and manifest.context_policy_version == "phase-evidence-v5"
        and manifest.memory_policy_version == FIXED_BUNDLE_POLICY_VERSION
        and manifest.model.model_dump(mode="json") == expected_model
        and manifest.budget.model_dump(mode="json") == expected_budget
        and manifest.sandbox_backend == "docker"
        and manifest.agent_image_digest == row.evaluator_image_digest
        and manifest.evaluator_image_digest == row.evaluator_image_digest
        and manifest.probe_image_digest is None
        and manifest.public_review_contract is None
        and manifest.fault.type == "none"
        and manifest.memory.model_dump(mode="json") == _expected_memory(row)
        and experiment.experiment_id == HELDOUT_AC_SUITE_ID
        and experiment.purpose == ExperimentPurpose.CORE
        and experiment.suite_hash == candidate.suite_content_hash
        and experiment.execution_hash == candidate.execution_hash
        and experiment.campaign_cost_control_hash == candidate.campaign_cost_control.content_hash
        and experiment.dataset_manifest_hash == candidate.dataset_manifest_hash
        and experiment.dataset_role == expected_role
        and experiment.schedule_seed == 20_260_814
        and experiment.schedule_order == row.order
        and experiment.schedule_row_id == row.schedule_row_id
        and experiment.repetition == row.repetition
    )


def heldout_ac_runtime_contract(candidate: HeldoutACExecutionCandidate) -> dict[str, Any]:
    """Build the exact secret-free runtime contract embedded in an approved plan."""

    return {
        "schema_version": RUNTIME_CONTRACT_SCHEMA_VERSION,
        "suite_id": candidate.suite_id,
        "suite_content_hash": candidate.suite_content_hash,
        "execution_hash": candidate.execution_hash,
        "runtime_tuple_hash": candidate.runtime_tuple_hash,
        "schedule_hash": candidate.schedule_hash,
        "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        "evaluator_source_hash": candidate.source_qualification.evaluator_source_hash,
        "source_qualification_hash": (candidate.source_qualification.source_qualification_hash),
        "pricing_binding_hash": candidate.pricing_binding_hash,
        "model_provider": "openai",
        "model_id": "gpt-5.4-mini-2026-03-17",
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "transport_max_retries": 0,
        "max_output_tokens": 25_000,
        "budget": {
            "max_model_calls": 240,
            "max_tool_calls": 400,
            "max_total_tokens": 4_500_000,
            "wall_clock_timeout_seconds": 3_600,
            "token_budget_schema_version": "cumulative-split-v1",
            "max_cumulative_input_tokens": 4_000_000,
            "max_cumulative_output_tokens": 500_000,
        },
        "memory_conditions": ["no_memory", "structured"],
        "memory_policy_version": FIXED_BUNDLE_POLICY_VERSION,
        "memory_max_context_tokens": 2_000,
        "tool_schema_version": "v2",
        "context_policy_version": "phase-evidence-v5",
        "call_guard_policy": CALL_GUARD_POLICY_VERSION,
    }


def heldout_ac_runtime_evidence_document(
    *,
    manifest: RunManifest,
    system_prompt: str,
    tool_schemas: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the CAS document that qualification independently recomputes."""

    if not is_heldout_ac_experiment(manifest) or manifest.experiment is None:
        raise ContractError("held-out runtime evidence requires the reserved experiment identity")
    return {
        "schema_version": RUNTIME_EVIDENCE_SCHEMA_VERSION,
        "experiment_id": manifest.experiment.experiment_id,
        "purpose": "core-ac-heldout",
        "suite_hash": manifest.experiment.suite_hash,
        "execution_hash": manifest.experiment.execution_hash,
        "campaign_cost_control_hash": manifest.experiment.campaign_cost_control_hash,
        "dataset_role": manifest.experiment.dataset_role.value,
        "schedule_seed": manifest.experiment.schedule_seed,
        "schedule_order": manifest.experiment.schedule_order,
        "schedule_row_id": manifest.experiment.schedule_row_id,
        "repetition": manifest.experiment.repetition,
        "model": manifest.model.model_dump(mode="json"),
        "budget": manifest.budget.model_dump(mode="json"),
        "sandbox_backend": manifest.sandbox_backend,
        "agent_image_digest": manifest.agent_image_digest,
        "evaluator_image_digest": manifest.evaluator_image_digest,
        "memory": manifest.memory.model_dump(mode="json"),
        "memory_policy_version": manifest.memory_policy_version,
        "system_prompt": system_prompt,
        "tools": list(tool_schemas),
        "tool_schema_version": manifest.tool_schema_version,
        "context_policy_version": manifest.context_policy_version,
        "call_guard_policy": CALL_GUARD_POLICY_VERSION,
    }


def _parse_plan_candidate(plan: Mapping[str, Any]) -> HeldoutACExecutionCandidate:
    raw = plan.get("candidate")
    if not isinstance(raw, dict):
        raise ContractError("held-out approved plan has no exact candidate")
    try:
        candidate = HeldoutACExecutionCandidate.model_validate_json(json.dumps(raw))
    except ValidationError as exc:
        raise ContractError("held-out approved candidate is invalid") from exc
    if not _exact_typed_equal(raw, candidate.model_dump(mode="json")):
        raise ContractError("held-out approved candidate uses a coercive shape")
    return candidate


def validate_heldout_ac_dispatch_plan(
    *,
    plan: Mapping[str, Any],
    plan_path: str | Path,
    plan_file_sha256: str,
    expected_run_root: str | Path,
    repository: str | Path | None = None,
) -> HeldoutACExecutionCandidate:
    """Validate the complete current plan before any journal path is written."""

    expected_keys = {
        "schema_version",
        "plan_kind",
        "created_at",
        "ready",
        "blockers",
        "suite",
        "candidate",
        "execution_hash",
        "schedule_hash",
        "runtime_contract",
        "campaign_cost_control",
        "approval",
        "journal_path",
        "result_path",
        "campaign_identity_hash",
        "campaign_one_use_ledger_path",
        "campaign_one_use_ledger_file_sha256",
        "campaign_one_use_ledger_content_hash",
    }
    if set(plan) != expected_keys:
        raise ContractError("held-out approved plan fields differ")
    candidate = _parse_plan_candidate(plan)
    try:
        suite = load_heldout_ac_suite(_SUITE_PATH, repository=repository)
    except ContractError:
        raise
    raw_suite = plan.get("suite")
    approval = plan.get("approval")
    approved_root = Path(expected_run_root).absolute()
    plan_file = canonical_heldout_ac_runtime_path(
        plan_path,
        expected_run_root=approved_root,
    )
    expected_plan = canonical_heldout_ac_runtime_path(
        approved_root / "experiments" / "plans" / f"{candidate.execution_hash[7:]}.json",
        expected_run_root=approved_root,
    )
    expected_journal = canonical_heldout_ac_runtime_path(
        approved_root / "experiments" / "journals" / f"{candidate.execution_hash[7:]}.jsonl",
        expected_run_root=approved_root,
    )
    expected_result = canonical_heldout_ac_runtime_path(
        approved_root / "experiments" / "heldout-ac" / f"{candidate.execution_hash[7:]}.json",
        expected_run_root=approved_root,
    )
    campaign_identity = heldout_ac_campaign_identity_hash(candidate)
    expected_ledger = canonical_heldout_ac_runtime_path(
        approved_root / "experiments" / "heldout-ac" / "one-use" / f"{campaign_identity[7:]}.json",
        expected_run_root=approved_root,
    )
    try:
        ledger_path = canonical_heldout_ac_runtime_path(
            str(plan.get("campaign_one_use_ledger_path")),
            expected_run_root=approved_root,
        )
        ledger_bytes = ledger_path.read_bytes()
        ledger = json.loads(ledger_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        ledger_path = expected_ledger
        ledger_bytes = b""
        ledger = None
    ledger_body = (
        {key: value for key, value in ledger.items() if key != "content_hash"}
        if isinstance(ledger, dict)
        else None
    )
    expected_ledger_body = {
        "schema_version": "heldout-ac-paid-campaign-one-use-v1",
        "campaign_identity_hash": campaign_identity,
        "execution_hash": candidate.execution_hash,
        "suite_content_hash": candidate.suite_content_hash,
        "source_qualification_hash": (candidate.source_qualification.source_qualification_hash),
        "base_schedule_hash": candidate.base_schedule_hash,
        "scheduled_run_count": 48,
        "full_schedule_reserve_nanos": 252_000_000_000,
        "hard_cap_nanos": 275_000_000_000,
        "claimed_at": ledger.get("claimed_at") if isinstance(ledger, dict) else None,
    }
    canonical_ledger = (
        (json.dumps(ledger, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        if isinstance(ledger, dict)
        else b""
    )
    valid = bool(
        plan.get("schema_version") == PLAN_SCHEMA_VERSION_V2
        and plan.get("plan_kind") == PLAN_KIND_V2
        and _canonical_utc(plan.get("created_at"))
        and plan.get("ready") is True
        and plan.get("blockers") == []
        and isinstance(raw_suite, dict)
        and _exact_typed_equal(raw_suite, suite.model_dump(mode="json"))
        and plan.get("execution_hash") == candidate.execution_hash
        and heldout_ac_candidate_has_current_source_binding(
            candidate,
            repository=repository,
        )
        and plan.get("schedule_hash") == candidate.schedule_hash
        and _exact_typed_equal(plan.get("runtime_contract"), heldout_ac_runtime_contract(candidate))
        and _exact_typed_equal(
            plan.get("campaign_cost_control"),
            candidate.campaign_cost_control.model_dump(mode="json"),
        )
        and isinstance(approval, dict)
        and set(approval)
        == {
            "invocation_approve_live_cost",
            "invocation_approved_execution_hash",
            "matches_execution_hash",
            "scheduled_run_count",
            "full_schedule_reserve_nanos",
            "hard_cap_nanos",
        }
        and approval.get("invocation_approve_live_cost") is True
        and approval.get("invocation_approved_execution_hash") == candidate.execution_hash
        and approval.get("matches_execution_hash") is True
        and type(approval.get("scheduled_run_count")) is int
        and approval.get("scheduled_run_count") == 48
        and type(approval.get("full_schedule_reserve_nanos")) is int
        and approval.get("full_schedule_reserve_nanos") == 252_000_000_000
        and type(approval.get("hard_cap_nanos")) is int
        and approval.get("hard_cap_nanos") == 275_000_000_000
        and plan.get("journal_path") == str(expected_journal)
        and plan.get("result_path") == str(expected_result)
        and plan.get("campaign_identity_hash") == campaign_identity
        and plan.get("campaign_one_use_ledger_path") == str(expected_ledger)
        and ledger_path == expected_ledger
        and not ledger_path.is_symlink()
        and isinstance(ledger, dict)
        and isinstance(ledger_body, dict)
        and ledger_bytes == canonical_ledger
        and set(ledger) == {*expected_ledger_body, "content_hash"}
        and _canonical_utc(ledger.get("claimed_at"))
        and _exact_typed_equal(ledger_body, expected_ledger_body)
        and ledger.get("content_hash") == sha256_json(ledger_body)
        and plan.get("campaign_one_use_ledger_file_sha256") == sha256_bytes(ledger_bytes)
        and plan.get("campaign_one_use_ledger_content_hash") == ledger.get("content_hash")
        and plan_file == expected_plan
        and _valid_sha256(plan_file_sha256)
        and sha256_bytes(plan_file.read_bytes()) == plan_file_sha256
    )
    if not valid:
        raise ContractError("held-out approved dispatch plan is invalid")
    return candidate


def validate_heldout_ac_live_plan(
    *,
    plan: Mapping[str, Any],
    manifest: RunManifest,
    plan_path: str | Path,
    plan_file_sha256: str,
    expected_run_root: str | Path,
    repository: str | Path | None = None,
) -> HeldoutACExecutionCandidate:
    """Validate the complete persisted plan against one exact manifest."""

    candidate = validate_heldout_ac_dispatch_plan(
        plan=plan,
        plan_path=plan_path,
        plan_file_sha256=plan_file_sha256,
        expected_run_root=expected_run_root,
        repository=repository,
    )
    if not heldout_ac_manifest_matches_candidate(manifest, candidate):
        raise ContractError("held-out approved plan does not match the exact manifest")
    return candidate


def heldout_ac_live_plan_matches_manifest(
    *,
    plan: Mapping[str, Any],
    manifest: RunManifest,
    plan_path: str | Path,
    plan_file_sha256: str,
    expected_run_root: str | Path,
    repository: str | Path | None = None,
) -> bool:
    try:
        validate_heldout_ac_live_plan(
            plan=plan,
            manifest=manifest,
            plan_path=plan_path,
            plan_file_sha256=plan_file_sha256,
            expected_run_root=expected_run_root,
            repository=repository,
        )
        return True
    except (ContractError, OSError, ValueError):
        return False


def _load_journal_events(path: Path) -> tuple[list[dict[str, Any]], bytes]:
    try:
        raw = path.read_bytes()
        if not raw.endswith(b"\n"):
            raise ValueError("journal is not newline terminated")
        events = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContractError("held-out campaign journal is invalid") from exc
    previous_hash: str | None = None
    previous_at: datetime | None = None
    journal_schema: str | None = None
    for sequence, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            raise ContractError("held-out campaign journal event is invalid")
        body = {key: value for key, value in event.items() if key != "event_hash"}
        try:
            recorded_at = datetime.fromisoformat(
                str(event.get("recorded_at")).replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ContractError("held-out campaign journal chronology is invalid") from exc
        event_schema = event.get("schema_version")
        if journal_schema is None and event_schema in {
            JOURNAL_SCHEMA_VERSION,
            JOURNAL_SCHEMA_VERSION_V2,
        }:
            journal_schema = event_schema
        if not (
            set(event)
            == {
                "schema_version",
                "sequence",
                "event_type",
                "recorded_at",
                "previous_event_hash",
                "payload",
                "event_hash",
            }
            and event_schema == journal_schema
            and type(event.get("sequence")) is int
            and event.get("sequence") == sequence
            and _canonical_utc(event.get("recorded_at"))
            and event.get("previous_event_hash") == previous_hash
            and isinstance(event.get("payload"), dict)
            and _valid_sha256(event.get("event_hash"))
            and event.get("event_hash") == sha256_json(body)
            and (previous_at is None or recorded_at >= previous_at)
        ):
            raise ContractError("held-out campaign journal hash chain is invalid")
        previous_hash = event["event_hash"]
        previous_at = recorded_at
    return events, raw


def _row_identity(row: Any) -> dict[str, Any]:
    return {
        "order": row.order,
        "wave": row.wave,
        "schedule_row_id": row.schedule_row_id,
        "task_id": row.task_id,
        "role": row.role,
        "condition": row.condition,
        "repetition": row.repetition,
    }


def heldout_ac_terminal_cost_settled_payload(
    *,
    candidate: HeldoutACExecutionCandidate,
    row: Any,
    authenticated: HeldoutACAuthenticatedPersistedRow,
    run_id: str,
    authenticated_row_path: str,
    authenticated_row_bytes: bytes,
    authenticated_row_content_hash: str,
    actual_run_cost_nanos: int,
    accrued_cost_nanos_before: int,
) -> dict[str, Any]:
    """Project the shared v2 atomic terminal-and-cost journal payload."""

    return {
        **_row_identity(row),
        "run_id": run_id,
        "execution_hash": candidate.execution_hash,
        "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        "authenticated_row_path": authenticated_row_path,
        "authenticated_row_file_sha256": sha256_bytes(authenticated_row_bytes),
        "authenticated_row_content_hash": authenticated_row_content_hash,
        "result_outcome_kind": authenticated.result.outcome_kind.value,
        "evaluation_status": authenticated.result.evaluation_status,
        "qualification_hash": authenticated.qualification_hash,
        "source_evidence_hash": authenticated.source_evidence_hash,
        "actual_run_cost_nanos": actual_run_cost_nanos,
        "accrued_cost_nanos_before": accrued_cost_nanos_before,
        "accrued_cost_nanos_after": accrued_cost_nanos_before + actual_run_cost_nanos,
        "remaining_reserved_rows_after": 48 - row.order,
    }


def validate_heldout_ac_reservation_journal_prefix(
    *,
    plan: Mapping[str, Any],
    manifest: RunManifest,
    plan_path: str | Path,
    plan_file_sha256: str,
    runner_root: str | Path,
    repository: str | Path | None = None,
) -> dict[str, str]:
    """Validate reserve + all prior settlements + the current unique row start."""

    candidate = validate_heldout_ac_live_plan(
        plan=plan,
        manifest=manifest,
        plan_path=plan_path,
        plan_file_sha256=plan_file_sha256,
        expected_run_root=runner_root,
        repository=repository,
    )
    assert manifest.experiment is not None
    root = Path(runner_root).absolute().resolve(strict=True)
    journal = canonical_heldout_ac_runtime_path(
        str(plan["journal_path"]),
        expected_run_root=root,
    )
    events, raw = _load_journal_events(journal)
    order = manifest.experiment.schedule_order
    v2_atomic_settlement = plan.get("schema_version") == PLAN_SCHEMA_VERSION_V2
    prior_event_count = 2 if v2_atomic_settlement else 3
    expected_length = 2 + (order - 1) * prior_event_count + 1
    if len(events) != expected_length:
        raise ContractError("held-out journal prefix does not end at the exact current row start")
    started = events[0]["payload"]
    reserved = events[1]["payload"]
    expected_started = {
        "suite_id": candidate.suite_id,
        "suite_content_hash": candidate.suite_content_hash,
        "execution_hash": candidate.execution_hash,
        "execution_plan_file_sha256": plan_file_sha256,
        "schedule_hash": candidate.schedule_hash,
        "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        "expected_runs": 48,
    }
    expected_reserved = {
        "suite_id": candidate.suite_id,
        "execution_hash": candidate.execution_hash,
        "execution_plan_file_sha256": plan_file_sha256,
        "schedule_hash": candidate.schedule_hash,
        "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        "reserved_runs": 48,
        "per_run_reserve_nanos": 5_250_000_000,
        "full_schedule_reserve_nanos": 252_000_000_000,
        "hard_cap_nanos": 275_000_000_000,
        "cost_censoring_allowed": False,
    }
    if not (
        events[0]["event_type"] == "CampaignStarted"
        and _exact_typed_equal(started, expected_started)
        and events[1]["event_type"] == "FullScheduleCostReserved"
        and _exact_typed_equal(reserved, expected_reserved)
    ):
        raise ContractError("held-out full-schedule reservation differs")

    accrued = 0
    seen_runs: set[str] = set()
    for prior_order in range(1, order):
        offset = 2 + (prior_order - 1) * prior_event_count
        start_event = events[offset]
        terminal_event = events[offset + 1]
        settled_event = None if v2_atomic_settlement else events[offset + 2]
        row = candidate.schedule[prior_order - 1]
        start_payload = start_event["payload"]
        run_id = start_payload.get("run_id")
        expected_start = {
            **_row_identity(row),
            "run_id": run_id,
            "execution_hash": candidate.execution_hash,
            "execution_plan_file_sha256": plan_file_sha256,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        }
        terminal = terminal_event["payload"]
        relative_path = terminal.get("authenticated_row_path")
        if not isinstance(relative_path, str) or not isinstance(run_id, str):
            raise ContractError("held-out prior row has no authenticated evidence path")
        expected_relative_path = (
            Path("experiments")
            / "heldout-ac"
            / "rows"
            / candidate.execution_hash.removeprefix("sha256:")
            / f"{prior_order:02d}-{run_id}-authenticated.json"
        ).as_posix()
        if relative_path != expected_relative_path:
            raise ContractError("held-out prior authenticated evidence path differs")
        evidence_path = canonical_heldout_ac_runtime_path(
            root / expected_relative_path,
            expected_run_root=root,
        )
        try:
            evidence_bytes = evidence_path.read_bytes()
            if v2_atomic_settlement:
                wrapper = HeldoutACAuthenticatedPersistedEvidence.model_validate_json(
                    evidence_bytes
                )
                evidence = wrapper.row
                persisted_content_hash = wrapper.content_hash
                canonical_evidence_bytes = wrapper.model_dump_json(indent=2).encode("utf-8")
            else:
                evidence = HeldoutACAuthenticatedPersistedRow.model_validate_json(evidence_bytes)
                persisted_content_hash = evidence.content_hash
                canonical_evidence_bytes = evidence.model_dump_json(indent=2).encode("utf-8")
        except (OSError, ValidationError) as exc:
            raise ContractError("held-out prior authenticated row is invalid") from exc
        cost = evidence.usage_evidence.token_derived_cost_nanos
        expected_terminal = {
            **_row_identity(row),
            "run_id": run_id,
            "execution_hash": candidate.execution_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "authenticated_row_path": relative_path,
            "authenticated_row_file_sha256": sha256_bytes(evidence_bytes),
            "authenticated_row_content_hash": persisted_content_hash,
            "result_outcome_kind": evidence.result.outcome_kind.value,
            "evaluation_status": evidence.result.evaluation_status,
            "qualification_hash": evidence.qualification_hash,
            "source_evidence_hash": evidence.source_evidence_hash,
            "actual_run_cost_nanos": cost,
        }
        expected_settled = {
            "order": row.order,
            "schedule_row_id": row.schedule_row_id,
            "run_id": run_id,
            "execution_hash": candidate.execution_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "authenticated_row_file_sha256": sha256_bytes(evidence_bytes),
            "authenticated_row_content_hash": persisted_content_hash,
            "actual_run_cost_nanos": cost,
            "accrued_cost_nanos_before": accrued,
            "accrued_cost_nanos_after": accrued + cost,
            "remaining_reserved_rows_after": 48 - prior_order,
        }
        expected_atomic = heldout_ac_terminal_cost_settled_payload(
            candidate=candidate,
            row=row,
            authenticated=evidence,
            run_id=run_id,
            authenticated_row_path=relative_path,
            authenticated_row_bytes=evidence_bytes,
            authenticated_row_content_hash=persisted_content_hash,
            actual_run_cost_nanos=cost,
            accrued_cost_nanos_before=accrued,
        )
        terminal_events_match = (
            terminal_event["event_type"] == "RunTerminalCostSettled"
            and _exact_typed_equal(terminal, expected_atomic)
            if v2_atomic_settlement
            else terminal_event["event_type"] == "RunTerminal"
            and _exact_typed_equal(terminal, expected_terminal)
            and settled_event is not None
            and settled_event["event_type"] == "RunCostSettled"
            and _exact_typed_equal(settled_event["payload"], expected_settled)
        )
        if not (
            isinstance(run_id, str)
            and _RUN_ID_RE.fullmatch(run_id) is not None
            and run_id not in seen_runs
            and start_event["event_type"] == "RunStarted"
            and _exact_typed_equal(start_payload, expected_start)
            and terminal_events_match
            and evidence_bytes == canonical_evidence_bytes
            and evidence.order == prior_order
            and evidence.run_id == run_id
            and evidence.schedule_row_id == row.schedule_row_id
            and evidence.execution_hash == candidate.execution_hash
            and cost <= candidate.campaign_cost_control.per_run_reserve_nanos
            and accrued + cost <= candidate.campaign_cost_control.full_schedule_reserve_nanos
        ):
            raise ContractError("held-out prior row settlement differs")
        seen_runs.add(run_id)
        accrued += cost

    current = events[-1]
    row = candidate.schedule[order - 1]
    expected_current = {
        **_row_identity(row),
        "run_id": manifest.run_id,
        "execution_hash": candidate.execution_hash,
        "execution_plan_file_sha256": plan_file_sha256,
        "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
    }
    if not (
        current["event_type"] == "RunStarted"
        and _exact_typed_equal(current["payload"], expected_current)
        and manifest.run_id not in seen_runs
    ):
        raise ContractError("held-out current row is not uniquely bound to the journal")
    return {
        "journal_path": str(journal),
        "journal_prefix_file_sha256": sha256_bytes(raw),
        "row_started_event_hash": current["event_hash"],
    }


__all__ = [
    "CALL_GUARD_POLICY_VERSION",
    "JOURNAL_SCHEMA_VERSION",
    "JOURNAL_SCHEMA_VERSION_V2",
    "PLAN_KIND",
    "PLAN_KIND_V2",
    "PLAN_SCHEMA_VERSION",
    "PLAN_SCHEMA_VERSION_V2",
    "RUNTIME_CONTRACT_SCHEMA_VERSION",
    "RUNTIME_EVIDENCE_SCHEMA_VERSION",
    "canonical_heldout_ac_runtime_path",
    "heldout_ac_live_plan_matches_manifest",
    "heldout_ac_candidate_has_bound_source_qualification",
    "heldout_ac_candidate_has_current_source_binding",
    "heldout_ac_manifest_matches_candidate",
    "heldout_ac_runtime_contract",
    "heldout_ac_runtime_evidence_document",
    "heldout_ac_terminal_cost_settled_payload",
    "is_heldout_ac_experiment",
    "validate_heldout_ac_dispatch_plan",
    "validate_heldout_ac_live_plan",
    "validate_heldout_ac_reservation_journal_prefix",
]
