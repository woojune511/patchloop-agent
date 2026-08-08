"""Seal the offline-only source qualification for the four-row A/C panel.

D-122 validates the exact development-validation suite, the deterministic
fixed D-110 bundle, its ordered schedule, and the source implementation that
will later support trace qualification.  It deliberately does not create an
execution hash, an execution-authorization candidate, or any provider,
evaluator, Docker, retrieval, or runtime-injection authority.
"""

from __future__ import annotations

import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal

import yaml

from patchloop.contracts import DatasetRole, MemoryCondition
from patchloop.dataset import require_dataset_role, require_frozen_dataset
from patchloop.errors import ContractError
from patchloop.evals.runner import (
    AC_FIXED_BUNDLE_COST_POLICY,
    AC_FIXED_BUNDLE_RUNTIME_CONTRACT_SCHEMA,
    AC_FIXED_BUNDLE_TASKS_ORDERED,
    _ac_fixed_bundle_descriptor,
    _is_ac_fixed_bundle_readiness_profile,
    _make_schedule,
    _suite_hash,
    load_suite,
)
from patchloop.memory.fixed_bundle import (
    D110_INDEX_CONTENT_HASH,
    D110_INDEX_VERSION,
    FIXED_BUNDLE_BYTES,
    FIXED_BUNDLE_POLICY_VERSION,
    FIXED_BUNDLE_SHA256,
    build_fixed_memory_delivery,
)
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-122"
SCHEMA_VERSION = "ac-fixed-bundle-offline-qualification-source-gate-d122-v1"
STATUS = "D122_OFFLINE_SOURCE_QUALIFIED_EXECUTION_CANDIDATE_BLOCKED"

SEALED_HISTORICAL_GATE_ID = (
    "d122_3fb93294d08f1b9a1359e4692dd8aaf9a8df19bef11ea5d66f0857d7eef320cc"
)
SEALED_HISTORICAL_BODY_SHA256 = (
    "sha256:3fb93294d08f1b9a1359e4692dd8aaf9a8df19bef11ea5d66f0857d7eef320cc"
)
SEALED_HISTORICAL_FILE_SHA256 = (
    "sha256:098cc27a457752f21250ecda79bc90061a91396a161cc450a2408e9f73640c24"
)
SEALED_HISTORICAL_FILE_BYTES = 12_699

PLAN_PATH = Path("experiments/ac-structured-pilot.plan.yaml")
SUITE_PATH = Path("experiments/dev-validation-ac-fixed-bundle-readiness-20260808-r1.yaml")
DATASET_PATH = Path("data/dataset-manifest.yaml")
OUTPUT_PATH = Path(
    "reports/live-pilot/artifacts/d122-ac-fixed-bundle-offline-qualification-source-gate.json"
)

IMPLEMENTATION_PATHS = (
    Path("patchloop/contracts.py"),
    Path("patchloop/runtime.py"),
    Path("patchloop/agent/runner.py"),
    Path("patchloop/evals/budget.py"),
    Path("patchloop/evals/runner.py"),
    Path("patchloop/evals/qualification.py"),
    Path("patchloop/evals/d122_ac_fixed_bundle_qualification.py"),
    Path("patchloop/memory/fixed_bundle.py"),
    Path("scripts/build_d122_ac_fixed_bundle_qualification.py"),
    Path("tests/test_fixed_bundle_delivery.py"),
    Path("tests/test_ac_structured_pilot_plan.py"),
    Path("tests/test_ac_fixed_bundle_readiness.py"),
    Path("tests/test_d122_ac_fixed_bundle_qualification.py"),
)

BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "plan_binding",
    "suite_binding",
    "schedule_binding",
    "task_bindings",
    "fixed_bundle_binding",
    "resource_and_cost_boundary",
    "implementation_integrity",
    "offline_qualification",
    "blocked_prerequisites",
    "evidence_boundary",
    "authority",
    "next_gate",
)
ROOT_KEYS = (
    "schema_version",
    "gate_id",
    "semantic_body_hash",
    "semantic_body",
)

BLOCKED_PREREQUISITES = (
    "exact-four-row-full-schedule-cost-reservation-not-implemented",
    "exact-four-row-completion-gate-not-implemented",
    "clean-committed-source-identity-not-sealed",
    "fresh-official-pricing-within-72-hours-not-verified",
    "separately-authorized-no-call-docker-and-sdk-preflight-not-completed",
    "exact-runner-execution-hash-not-created",
    "one-use-execution-authorization-candidate-not-created",
    "separate-candidate-triple-execution-hash-and-55-dollar-cap-approval-missing",
)


class D122QualificationError(ContractError):
    """Raised when the D-122 source contract or canonical evidence drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D122QualificationError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise D122QualificationError("D-122 repository root is unavailable") from exc
    _require(root.is_dir(), "D-122 repository root is not a directory")
    return root


def _is_linklike(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    attributes = getattr(metadata, "st_file_attributes", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(reparse and attributes & reparse)


def _canonical_relative(path: Path) -> PurePosixPath:
    parsed = PurePosixPath(path.as_posix())
    _require(
        not parsed.is_absolute()
        and bool(parsed.parts)
        and all(part not in {"", ".", ".."} for part in parsed.parts),
        f"D-122 path is not canonical: {path.as_posix()}",
    )
    for part in parsed.parts:
        _require(
            ":" not in part and part == part.rstrip(" ."),
            f"D-122 path has a platform alias: {path.as_posix()}",
        )
    return parsed


def _logical_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    parsed = _canonical_relative(relative)
    selected = root.joinpath(*parsed.parts)
    current = root
    for index, part in enumerate(parsed.parts):
        current = current / part
        is_final = index == len(parsed.parts) - 1
        if current.exists() or _is_linklike(current):
            _require(
                not _is_linklike(current),
                f"D-122 path traverses a link or reparse point: {relative.as_posix()}",
            )
        elif must_exist or not is_final:
            raise D122QualificationError(f"D-122 path is missing: {relative.as_posix()}")
    try:
        resolved_parent = selected.parent.resolve(strict=True)
    except OSError as exc:
        raise D122QualificationError(
            f"D-122 path parent is unavailable: {relative.as_posix()}"
        ) from exc
    _require(
        resolved_parent.is_relative_to(root),
        f"D-122 path escapes the repository: {relative.as_posix()}",
    )
    if must_exist:
        try:
            resolved = selected.resolve(strict=True)
        except OSError as exc:
            raise D122QualificationError(
                f"D-122 input cannot be resolved: {relative.as_posix()}"
            ) from exc
        _require(
            resolved.is_relative_to(root),
            f"D-122 input escapes the repository: {relative.as_posix()}",
        )
    return selected


def _stable_read(root: Path, relative: Path) -> bytes:
    selected = _logical_path(root, relative, must_exist=True)
    try:
        before_path = selected.stat(follow_symlinks=False)
        _require(
            stat.S_ISREG(before_path.st_mode),
            f"D-122 input is not a regular file: {relative.as_posix()}",
        )
        with selected.open("rb") as stream:
            before_fd = os.fstat(stream.fileno())
            content = stream.read()
            after_fd = os.fstat(stream.fileno())
        after_path = selected.stat(follow_symlinks=False)
    except OSError as exc:
        raise D122QualificationError(f"D-122 input cannot be read: {relative.as_posix()}") from exc
    identities = {
        (before_path.st_dev, before_path.st_ino),
        (before_fd.st_dev, before_fd.st_ino),
        (after_fd.st_dev, after_fd.st_ino),
        (after_path.st_dev, after_path.st_ino),
    }
    _require(
        len(identities) == 1
        and before_path.st_size == after_path.st_size
        and before_path.st_mtime_ns == after_path.st_mtime_ns
        and before_fd.st_size == after_fd.st_size
        and before_fd.st_mtime_ns == after_fd.st_mtime_ns,
        f"D-122 input changed while reading: {relative.as_posix()}",
    )
    return content


def _file_binding(root: Path, relative: Path) -> dict[str, Any]:
    content = _stable_read(root, relative)
    return {
        "path": relative.as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _implementation_state(root: Path) -> dict[str, Any]:
    files = [_file_binding(root, path) for path in IMPLEMENTATION_PATHS]
    return {
        "files": files,
        "file_count": len(files),
        "fingerprint": sha256_text(canonical_json(files)),
    }


def _load_yaml_exact(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(content.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise D122QualificationError(f"D-122 {label} is not valid UTF-8 YAML") from exc
    _require(isinstance(value, dict), f"D-122 {label} root is not an object")
    return value


def _task_rows(root: Path, dataset_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    schedule_rows: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    for task in AC_FIXED_BUNDLE_TASKS_ORDERED:
        task_path = Path(task)
        package = load_task_package(root / task_path.parent)
        entry = require_dataset_role(
            task_id=package.public.task_id,
            task_version=package.public.task_version,
            public_spec_hash=package.public_spec_hash,
            allowed_roles={DatasetRole.DEVELOPMENT_VALIDATION},
            manifest_path=dataset_path,
        )
        _require(
            package.environment is not None,
            f"D-122 task has no pinned evaluator image: {package.public.task_id}",
        )
        _require(
            Path(package.root).resolve(strict=True) == (root / entry.path).resolve(strict=True),
            f"D-122 task path differs from the frozen dataset: {package.public.task_id}",
        )
        _require(
            package.private_spec_hash == entry.private_spec_hash,
            f"D-122 evaluator binding differs: {package.public.task_id}",
        )
        schedule_rows.append(
            {
                "task": task,
                "task_id": package.public.task_id,
                "task_version": package.public.task_version,
                "split": package.public.split,
                "dataset_role": entry.role.value,
                "evaluator_image_digest": package.environment.image_digest,
            }
        )
        bindings.append(
            {
                "order": len(bindings) + 1,
                "task_path": task,
                "task_id": package.public.task_id,
                "task_version": package.public.task_version,
                "dataset_role": entry.role.value,
                "base_commit": package.public.repository.base_commit,
                "public_spec_hash": package.public_spec_hash,
                "private_spec_hash": package.private_spec_hash,
                "evaluator_image_digest": package.environment.image_digest,
            }
        )
    return schedule_rows, bindings


def _source_state(root: Path) -> dict[str, Any]:
    plan_binding = _file_binding(root, PLAN_PATH)
    suite_binding = _file_binding(root, SUITE_PATH)
    dataset_binding = _file_binding(root, DATASET_PATH)
    plan = _load_yaml_exact(_stable_read(root, PLAN_PATH), label="A/C plan")
    suite = load_suite(root / SUITE_PATH)
    _require(
        _is_ac_fixed_bundle_readiness_profile(suite),
        "D-122 suite is not the exact four-row A/C profile",
    )
    dataset, dataset_hash, dataset_path = require_frozen_dataset(root / DATASET_PATH)
    _require(
        suite.dataset_manifest_hash == dataset_hash,
        "D-122 suite dataset hash differs from the frozen registry",
    )
    task_rows, task_bindings = _task_rows(root, dataset_path)
    schedule, schedule_hash = _make_schedule(suite, task_rows)
    _require(
        len(schedule) == 4
        and [row["condition"] for row in schedule]
        == ["no_memory", "structured", "structured", "no_memory"],
        "D-122 schedule is not the exact Moto A/C then Babel C/A order",
    )

    no_memory_delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=suite.memory_token_budget,
        repository=root,
    )
    no_memory_evidence = no_memory_delivery.evidence
    _require(
        no_memory_delivery.text == ""
        and no_memory_evidence.entry_count == 0
        and no_memory_evidence.bundle_bytes == 0
        and no_memory_evidence.bundle_sha256 is None
        and no_memory_evidence.index_version is None
        and no_memory_evidence.index_content_hash is None,
        "D-122 no-memory delivery identity differs",
    )
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.STRUCTURED,
        token_budget=suite.memory_token_budget,
        repository=root,
    )
    evidence = delivery.evidence
    _require(
        evidence.entry_count == 3
        and evidence.bundle_bytes == FIXED_BUNDLE_BYTES
        and evidence.bundle_sha256 == FIXED_BUNDLE_SHA256
        and evidence.index_version == D110_INDEX_VERSION
        and evidence.index_content_hash == D110_INDEX_CONTENT_HASH,
        "D-122 fixed bundle identity differs",
    )
    descriptor = _ac_fixed_bundle_descriptor()
    _require(
        descriptor["bundle_bytes"] == FIXED_BUNDLE_BYTES
        and descriptor["bundle_sha256"] == FIXED_BUNDLE_SHA256
        and descriptor["d110_index_version"] == D110_INDEX_VERSION
        and descriptor["d110_index_content_hash"] == D110_INDEX_CONTENT_HASH,
        "D-122 fixed bundle descriptor differs",
    )

    _require(
        plan.get("schema_version") == "ac-structured-pilot-plan-v1"
        and plan.get("plan_id") == "ac-structured-dev-validation-readiness-20260808-v1",
        "D-122 planning artifact identity differs",
    )
    plan_binding.update(
        {
            "schema_version": plan["schema_version"],
            "plan_id": plan["plan_id"],
            "status": plan.get("status"),
        }
    )
    suite_binding.update(
        {
            "suite_hash": _suite_hash(suite),
            "schema_version": suite.schema_version,
            "experiment_id": suite.experiment_id,
            "purpose": suite.purpose.value,
            "memory_policy_version": suite.memory_policy_version,
            "live_cost_approved": suite.live_cost_approved,
            "approved_execution_hash": suite.approved_execution_hash,
            "pricing_verified_at": (
                suite.pricing_verified_at.isoformat()
                if suite.pricing_verified_at is not None
                else None
            ),
            "dataset": {
                **dataset_binding,
                "dataset_id": dataset.dataset_id,
                "semantic_manifest_hash": dataset_hash,
                "status": dataset.status,
            },
        }
    )
    return {
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
                    "condition": row["condition"],
                    "repetition": row["repetition"],
                }
                for row in schedule
            ],
            "counterbalanced_task_pair_order": True,
            "automatic_retry_or_replacement_allowed": False,
        },
        "task_bindings": task_bindings,
        "fixed_bundle_binding": {
            **descriptor,
            "delivery_policy_version": FIXED_BUNDLE_POLICY_VERSION,
            "delivery_cadence": "every-model-request",
            "no_memory_selected_memory": None,
            "structured_bundle_rebuilt_and_verified": True,
            "retrieval_or_embedding_used": False,
        },
    }


def _body(
    *,
    recorded_at: str,
    source: dict[str, Any],
    implementation: dict[str, Any],
) -> dict[str, Any]:
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "offline-source-qualification",
        "recorded_at": recorded_at,
        "status": STATUS,
        "plan_binding": source["plan_binding"],
        "suite_binding": source["suite_binding"],
        "schedule_binding": source["schedule_binding"],
        "task_bindings": source["task_bindings"],
        "fixed_bundle_binding": source["fixed_bundle_binding"],
        "resource_and_cost_boundary": {
            **AC_FIXED_BUNDLE_COST_POLICY,
            "calculation": "(3000000 + 25000) * 4.5 / 1000000",
            "slack_nanos": 550_000_000,
            "historical_formula_provenance_only": True,
            "historical_d108_bundle_delta_tokens": 702,
            "historical_d108_delta_is_not_per_request_live_evidence": True,
            "fresh_official_pricing_verified": False,
            "full_schedule_reservation_enforced": False,
            "hard_cap_enforced": False,
            "cost_settlement_evidence_present": False,
        },
        "implementation_integrity": implementation,
        "offline_qualification": {
            "exact_suite_profile_validated": True,
            "exact_schedule_bijection_validated": True,
            "frozen_dataset_and_task_bindings_validated": True,
            "fixed_bundle_rebuilt_from_exact_d105_d110_inputs": True,
            "runtime_contract_schema": AC_FIXED_BUNDLE_RUNTIME_CONTRACT_SCHEMA,
            "condition_specific_manifest_binding_implemented": True,
            "condition_specific_trace_qualifier_implemented": True,
            "request_artifact_replay_validator_implemented": True,
            "legacy_selective_retrieval_bypassed": True,
            "live_preflight_has_unconditional_cost_control_blocker": True,
            "focused_test_execution_is_external_to_builder": True,
            "execution_candidate_prepared": False,
            "execution_authorization_candidate_ready": False,
        },
        "blocked_prerequisites": list(BLOCKED_PREREQUISITES),
        "evidence_boundary": {
            "development_validation_only": True,
            "heldout_or_core_tasks_used": False,
            "task_selection_based_on_hidden_or_outcome_evidence": False,
            "live_agent_result_present": False,
            "memory_effect_or_negative_transfer_result_present": False,
            "provider_or_evaluator_result_present": False,
            "clean_committed_source_verified": False,
            "docker_or_sdk_live_preflight_verified": False,
            "network_or_socket_instrumentation_verified": False,
            "source_path_evidence_only_for_zero_call_claims": True,
        },
        "authority": {
            "offline_source_qualification_materialized": True,
            "exact_four_row_suite_materialized": True,
            "fixed_bundle_delivery_implementation_present": True,
            "structured_trace_qualifier_implementation_present": True,
            "execution_candidate_prepared": False,
            "execution_authorization_candidate_ready": False,
            "exact_execution_hash_created": False,
            "approved_execution_hash": None,
            "provider_execution_authorized": False,
            "evaluator_execution_authorized": False,
            "runtime_memory_injection_authorized": False,
            "fixed_bundle_delivery_live_authorized": False,
            "retrieval_authorized": False,
            "docker_preflight_authorized": False,
            "score_policy_mutation_authorized": False,
            "automatic_retry_replacement_or_resume_authorized": False,
            "core_or_heldout_campaign_authorized": False,
            "analysis_or_memory_benefit_claim_authorized": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "docker_calls_made": 0,
            "agent_runs_made": 0,
            "retrieval_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": {
            "action": (
                "implement-exact-four-row-cost-and-completion-gates-then-"
                "prepare-clean-no-call-execution-authorization-candidate"
            ),
            "requires_fresh_official_pricing": True,
            "requires_clean_committed_source": True,
            "requires_separately_authorized_no_call_docker_sdk_preflight": True,
            "requires_separate_exact_candidate_execution_hash_and_cap_approval": True,
            "proposed_hard_cap_usd": 55.0,
            "does_not_authorize_execution": True,
        },
    }
    _require(tuple(body) == BODY_KEYS, "D-122 semantic body fields differ")
    return body


def _envelope(body: dict[str, Any]) -> dict[str, Any]:
    body_hash = sha256_text(canonical_json(body))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "gate_id": f"d122_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }
    _require(tuple(payload) == ROOT_KEYS, "D-122 gate fields differ")
    return payload


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (canonical_json(payload) + "\n").encode("utf-8")


def _parse_recorded_at(value: Any) -> str:
    _require(isinstance(value, str), "D-122 recorded_at is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise D122QualificationError("D-122 recorded_at is invalid") from exc
    _require(
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        "D-122 recorded_at is timezone-naive",
    )
    return value


def _validate_payload(
    *,
    root: Path,
    payload: dict[str, Any],
    raw: bytes,
) -> dict[str, Any]:
    _require(set(payload) == set(ROOT_KEYS), "D-122 gate root fields differ")
    _require(payload.get("schema_version") == SCHEMA_VERSION, "D-122 schema differs")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-122 semantic body is missing")
    _require(set(body) == set(BODY_KEYS), "D-122 semantic body fields differ")
    recorded_at = _parse_recorded_at(body.get("recorded_at"))
    source = _source_state(root)
    implementation = _implementation_state(root)
    expected = _envelope(
        _body(
            recorded_at=recorded_at,
            source=source,
            implementation=implementation,
        )
    )
    expected_bytes = _canonical_bytes(expected)
    _require(raw == expected_bytes, "D-122 full expected payload differs")
    _require(
        payload.get("semantic_body_hash") == sha256_text(canonical_json(body)),
        "D-122 semantic body hash differs",
    )
    _require(
        payload.get("gate_id") == f"d122_{payload['semantic_body_hash'].removeprefix('sha256:')}",
        "D-122 gate ID differs",
    )
    return expected


def _validate_sealed_historical_payload(
    *,
    payload: dict[str, Any],
    raw: bytes,
) -> dict[str, Any]:
    """Validate the immutable D-122 bytes without replaying mutable successors."""

    _require(set(payload) == set(ROOT_KEYS), "D-122 gate root fields differ")
    _require(payload.get("schema_version") == SCHEMA_VERSION, "D-122 schema differs")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-122 semantic body is missing")
    _require(set(body) == set(BODY_KEYS), "D-122 semantic body fields differ")
    _parse_recorded_at(body.get("recorded_at"))
    _require(raw == _canonical_bytes(payload), "D-122 gate bytes are noncanonical")
    body_hash = sha256_text(canonical_json(body))
    _require(body_hash == SEALED_HISTORICAL_BODY_SHA256, "D-122 sealed body differs")
    _require(
        payload.get("semantic_body_hash") == body_hash,
        "D-122 semantic body hash differs",
    )
    _require(
        payload.get("gate_id") == SEALED_HISTORICAL_GATE_ID,
        "D-122 sealed gate ID differs",
    )
    _require(len(raw) == SEALED_HISTORICAL_FILE_BYTES, "D-122 sealed size differs")
    _require(
        sha256_bytes(raw) == SEALED_HISTORICAL_FILE_SHA256,
        "D-122 sealed file hash differs",
    )
    return payload


def validate_d122_source_gate(
    *,
    repository: str | Path | None = None,
    mode: Literal["current-source", "sealed-historical"] = "current-source",
) -> dict[str, Any]:
    """Validate D-122 against current source or its immutable historical seal."""

    root = _repo_root(repository)
    raw = _stable_read(root, OUTPUT_PATH)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D122QualificationError("D-122 gate is not canonical UTF-8 JSON") from exc
    _require(isinstance(payload, dict), "D-122 gate root is not an object")
    if mode == "current-source":
        validated = _validate_payload(root=root, payload=payload, raw=raw)
    elif mode == "sealed-historical":
        validated = _validate_sealed_historical_payload(payload=payload, raw=raw)
    else:
        raise D122QualificationError("D-122 validation mode is unsupported")
    return {
        "status": validated["semantic_body"]["status"],
        "gate_id": validated["gate_id"],
        "semantic_body_hash": validated["semantic_body_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_authorization_candidate_ready": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
    }


def _write_new(root: Path, payload: dict[str, Any]) -> bytes:
    selected = _logical_path(root, OUTPUT_PATH, must_exist=False)
    _require(not selected.exists(), "D-122 source gate already exists")
    content = _canonical_bytes(payload)
    try:
        with selected.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise D122QualificationError("D-122 source gate cannot be created") from exc
    try:
        with selected.open("rb") as stream:
            observed = stream.read()
    except OSError as exc:
        raise D122QualificationError("D-122 source gate cannot be reread") from exc
    _require(observed == content, "D-122 source gate changed after creation")
    return observed


def run_d122_offline_source_gate(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Materialize once, or validate an already complete D-122 source gate."""

    root = _repo_root(repository)
    output = _logical_path(root, OUTPUT_PATH, must_exist=False)
    if output.exists():
        return validate_d122_source_gate(repository=root)
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


__all__ = [
    "D122QualificationError",
    "OUTPUT_PATH",
    "SEALED_HISTORICAL_BODY_SHA256",
    "SEALED_HISTORICAL_FILE_BYTES",
    "SEALED_HISTORICAL_FILE_SHA256",
    "SEALED_HISTORICAL_GATE_ID",
    "run_d122_offline_source_gate",
    "validate_d122_source_gate",
]
