from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from patchloop.contracts import PublicTask, TaskEnvironment
from patchloop.util import sha256_bytes, sha256_json

RECORDED_AT = "2026-08-05T02:24:14Z"
PRICING_VERIFIED_AT = RECORDED_AT
PRICING_SOURCE_URL = "https://developers.openai.com/api/docs/pricing"
DATASET_MANIFEST_HASH = "sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786"
D096_BODY_HASH = "sha256:2e9360d92db5224d181fe8f18254da3850f324b33b24f3833633589085e3b75d"
D094_BODY_HASH = "sha256:ab7be9ad2448d1016b88d451e271330844fc11d8fd4b890f08142618446ff929"
EXPERIMENT_ID = "dev-no-memory-condition-neutral-3000k-20260805-r1"
RESOURCE_PROFILE_ID = "gpt54mini-v2v5-condition-neutral-3000k-v1"
BASELINE_ADMISSION_ID = "memory-development-no-memory-12-row-v1"
RUNTIME_CONTRACT_SCHEMA = "condition-neutral-comparison-runtime-contract-v2"
RUNTIME_EVIDENCE_SCHEMA = "condition-neutral-comparison-runtime-evidence-v2"

SOURCE_FILES: dict[str, dict[str, Any]] = {
    "d096-resource-policy-and-admission": {
        "path": (
            "reports/live-pilot/artifacts/"
            "d096-condition-neutral-resource-policy-baseline-admission.json"
        ),
        "bytes": 19_031,
        "sha256": ("sha256:5c032cff1045a39d1d8d9757205a920b1cd1cfd948c7c4e3e5b526ae6744661d"),
        "semantic_body_hash": D096_BODY_HASH,
    },
    "d087-cost-journal-source": {
        "path": (
            "reports/live-pilot/artifacts/"
            "d087-condition-neutral-comparison-accrued-spend-cap-source-gate.json"
        ),
        "bytes": 9_675,
        "sha256": ("sha256:5f038999b65930a0f155d5eb00a530ac06b6e359de0bdac12fff22398aaa7efe"),
    },
    "d094-pricing-source": {
        "path": ("reports/live-pilot/artifacts/d094-high-headroom-readiness-source-gate.json"),
        "bytes": 13_284,
        "sha256": ("sha256:6887936ec141496e35e3a9d3bd6c34cf04cf02d1849bf80208677151a692c6ed"),
        "semantic_body_hash": D094_BODY_HASH,
    },
    "dataset-manifest": {
        "path": "data/dataset-manifest.yaml",
        "bytes": 47_368,
        "sha256": ("sha256:e8cf14ca9dabebcc03c3522e400dfcb79606541e9b11e59f49510ea5c40bebed"),
    },
    "successor-suite": {
        "path": ("experiments/dev-no-memory-condition-neutral-3000k-20260805-r1.yaml"),
        "bytes": 2_741,
        "sha256": ("sha256:7b3c217388e86a2760694e98031b7ac974c8c450075e3433ee977e35b344abb0"),
    },
}

TASK_PATHS = (
    "tasks/dev-train/loguru-invalid-format-feedback/public.yaml",
    "tasks/dev-train/anyio-interrupt-runner-cleanup/public.yaml",
    "tasks/dev-train/tox-cross-section-empty-substitution/public.yaml",
    "tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml",
    "tasks/dev-train/pdm-ignore-active-venv-resolution/public.yaml",
    "tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml",
)

ENVIRONMENT_FILES: dict[str, dict[str, Any]] = {
    "loguru-invalid-format-feedback": {
        "path": "tasks/dev-train/loguru-invalid-format-feedback/environment.yaml",
        "bytes": 340,
        "sha256": ("sha256:ec41316a0a88aed530d67d416a943e6f139c6e99a6580f8fe9c52b5f9184c94f"),
    },
    "anyio-interrupt-runner-cleanup": {
        "path": "tasks/dev-train/anyio-interrupt-runner-cleanup/environment.yaml",
        "bytes": 344,
        "sha256": ("sha256:56ef76aff34338c70c94e5fd60eeda7a3d6aab1e32390b4584a9ef9870495635"),
    },
    "tox-cross-section-empty-substitution": {
        "path": "tasks/dev-train/tox-cross-section-empty-substitution/environment.yaml",
        "bytes": 336,
        "sha256": ("sha256:5ffa4960924e8dda81cc84faf4b3357bcd37e491767f9374300e4d202f5e2208"),
    },
    "hf-hub-xet-endpoint-propagation": {
        "path": "tasks/dev-train/hf-hub-xet-endpoint-propagation/environment.yaml",
        "bytes": 344,
        "sha256": ("sha256:9a6487d24ae7bf6436f3f93d7f4e34fb1a5be5674a342e2f1f2cf53b8f73581a"),
    },
    "pdm-ignore-active-venv-resolution": {
        "path": "tasks/dev-train/pdm-ignore-active-venv-resolution/environment.yaml",
        "bytes": 320,
        "sha256": ("sha256:0059c1afe17a641b71bb992b3bdfa2a53063def6a510bc9ccb8fd085dc72121a"),
    },
    "pyfakefs-makedirs-parent-traversal": {
        "path": "tasks/dev-train/pyfakefs-makedirs-parent-traversal/environment.yaml",
        "bytes": 327,
        "sha256": ("sha256:93b6c006b7528a84054e24871000511642086ef93fd738951ac1e3123ca291d8"),
    },
}

EXPECTED_RANDOMIZED_ROWS = (
    ("pyfakefs-makedirs-parent-traversal", 1),
    ("pyfakefs-makedirs-parent-traversal", 2),
    ("anyio-interrupt-runner-cleanup", 1),
    ("hf-hub-xet-endpoint-propagation", 1),
    ("pdm-ignore-active-venv-resolution", 1),
    ("hf-hub-xet-endpoint-propagation", 2),
    ("anyio-interrupt-runner-cleanup", 2),
    ("loguru-invalid-format-feedback", 1),
    ("loguru-invalid-format-feedback", 2),
    ("tox-cross-section-empty-substitution", 2),
    ("tox-cross-section-empty-substitution", 1),
    ("pdm-ignore-active-venv-resolution", 2),
)

RESOURCE_POLICY = {
    "schema_version": "condition-neutral-comparison-resource-policy-v2",
    "profile_id": RESOURCE_PROFILE_ID,
    "prospective_only": True,
    "provider": "openai",
    "model_id": "gpt-5.4-mini-2026-03-17",
    "reasoning_effort": "medium",
    "reasoning_mode": "standard",
    "service_tier": "default",
    "transport_max_retries": 0,
    "system_prompt_version": "SYSTEM_PROMPT_V3",
    "system_prompt_hash": (
        "sha256:441c71fdea2defed14f06b32c3fba7a7aaa19f7a3ca749bc994e72708d8a733b"
    ),
    "tool_schema_version": "v2",
    "tool_schema_hash": ("sha256:2ee296c2cf515bf2e0937ec1727dc02046a8560581d39b71246c5b91eccf0827"),
    "context_policy_version": "phase-evidence-v5",
    "max_output_tokens": 25_000,
    "memory_max_context_tokens": 2_000,
    "budget": {
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 3_000_000,
        "wall_clock_timeout_seconds": 3_600,
    },
    "call_guard_policy": "model-tool-observability-only-v1",
    "condition_neutral": True,
    "same_budget_for_all_memory_conditions": True,
    "memory_conditions": [
        "no_memory",
        "raw_trace",
        "structured",
        "selective_structured",
    ],
    "retained_guards": [
        "total-token",
        "wall-clock",
        "exact-request",
        "cost",
        "loop",
        "constrained-tool",
        "docker-network",
        "evaluator",
    ],
    "budget_role": "finite-non-target-safety-ceiling",
    "completion_guaranteed": False,
}

COST_POLICY = {
    "schema_version": "campaign-list-price-full-schedule-reserve-v1",
    "accounting_scope": "campaign-local",
    "accounting_basis": "usage-derived-standard-list-price",
    "scheduled_run_count": 12,
    "per_run_worst_rate_reserve_usd": 13.6125,
    "full_schedule_worst_rate_reserve_usd": 163.35,
    "hard_cap_usd": 164.0,
    "hard_cap_slack_usd": 0.65,
    "money_scale": "nano-usd",
    "per_run_reserve_nanos": 13_612_500_000,
    "full_schedule_reserve_nanos": 163_350_000_000,
    "hard_cap_nanos": 164_000_000_000,
    "reservation_mode": "row-bound-full-schedule-up-front",
    "initial_reservation_boundary": "before-first-provider-call",
    "row_reserve_count": 12,
    "cost_censoring_allowed": False,
    "not_started_due_to_cost_allowed": False,
    "settlement_basis": "durable-token-derived-standard-list-price",
    "live_resume_policy": "disabled",
    "completion_guaranteed": False,
    "invoice_or_free_tier_claimed": False,
}


class D097BuildError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D097BuildError(message)


def _read_exact(root: Path, descriptor: dict[str, Any], *, label: str) -> bytes:
    path = root / descriptor["path"]
    _require(path.is_file(), f"{label} is missing")
    content = path.read_bytes()
    _require(len(content) == descriptor["bytes"], f"{label} byte count drifted")
    _require(sha256_bytes(content) == descriptor["sha256"], f"{label} hash drifted")
    return content


def _load_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D097BuildError(f"{label} is not valid JSON") from exc
    _require(isinstance(payload, dict), f"{label} must be a JSON object")
    return payload


def _load_yaml(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(content)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise D097BuildError(f"{label} is not valid YAML") from exc
    _require(isinstance(payload, dict), f"{label} must be a YAML object")
    return payload


def _content_addressed_body(
    payload: dict[str, Any],
    *,
    expected_hash: str,
    label: str,
) -> dict[str, Any]:
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), f"{label} semantic body is missing")
    _require(
        payload.get("semantic_body_hash") == expected_hash,
        f"{label} semantic hash drifted",
    )
    _require(sha256_json(body) == expected_hash, f"{label} body hash drifted")
    return body


def _validate_d096(payload: dict[str, Any]) -> dict[str, Any]:
    body = _content_addressed_body(
        payload,
        expected_hash=D096_BODY_HASH,
        label="D-096 decision",
    )
    _require(
        payload.get("decision_id") == f"d096_{D096_BODY_HASH.removeprefix('sha256:')}",
        "D-096 decision identity drifted",
    )
    decision = body.get("decision", {})
    _require(
        decision.get("selected")
        == "freeze-high-headroom-policy-and-admit-new-no-memory-source-authoring"
        and decision.get("workflow_readiness_prerequisite_satisfied") is True
        and decision.get("budget_is_target_experimental_factor") is False
        and decision.get("automatic_live_execution_authorized") is False,
        "D-096 policy decision drifted",
    )
    _require(
        body.get("selected_resource_policy") == RESOURCE_POLICY,
        "D-096 selected resource policy drifted",
    )
    supersession = body.get("prospective_supersession_boundary", {})
    _require(
        supersession.get("new_runtime_contract_schema") == RUNTIME_CONTRACT_SCHEMA
        and supersession.get("new_runtime_evidence_schema") == RUNTIME_EVIDENCE_SCHEMA
        and supersession.get("d083_d084_historical_contracts_modified") is False
        and supersession.get("d087_retroactively_admitted") is False
        and supersession.get("d095_retroactively_admitted") is False,
        "D-096 prospective supersession boundary drifted",
    )
    admission = body.get("no_memory_baseline_admission", {})
    schedule = admission.get("schedule_identity", {})
    _require(
        admission.get("admission_id") == BASELINE_ADMISSION_ID
        and admission.get("dataset_manifest_hash") == DATASET_MANIFEST_HASH
        and schedule.get("tasks") == list(TASK_PATHS)
        and schedule.get("condition") == "no_memory"
        and schedule.get("repetitions") == 2
        and schedule.get("seed") == 20260723
        and schedule.get("expected_rows") == 12
        and schedule.get("content_hash")
        == "sha256:e399114a6ea516821a30104a612f7222c0caf3f88def7b5d7472d15f7cc4c27b"
        and admission.get("future_no_memory_source_authoring_unlocked") is True
        and admission.get("live_collection_authorized") is False,
        "D-096 baseline admission drifted",
    )
    completion = admission.get("campaign_completion_requirements", {})
    _require(
        completion.get("expected_rows") == 12
        and completion.get("terminal_rows") == 12
        and completion.get("trace_qualified_rows") == 12
        and completion.get("cost_settled_rows") == 12
        and completion.get("not_started_rows") == 0
        and completion.get("campaign_cost_censoring_allowed") is False
        and completion.get("task_success_required") is False,
        "D-096 completion predicate drifted",
    )
    cost = body.get("cost_authorization_boundary", {})
    _require(
        cost.get("per_run_worst_rate_reserve_usd") == 13.6125
        and cost.get("twelve_run_worst_rate_reserve_usd") == 163.35
        and cost.get("existing_project_cap_usd") == 150.0
        and cost.get("minimum_integer_cap_for_uncensored_twelve_run_worst_case_usd") == 164.0
        and cost.get("campaign_cost_policy_selected") is False
        and cost.get("project_cap_changed") is False,
        "D-096 cost boundary drifted",
    )
    _require(
        body.get("claims_boundary", {}).get("future_no_memory_source_authoring_unlocked") is True
        and body.get("claims_boundary", {}).get("live_execution_authorized") is False,
        "D-096 claims boundary drifted",
    )
    return body


def _validate_d087(payload: dict[str, Any]) -> dict[str, Any]:
    _require(
        payload.get("schema_version")
        == "condition-neutral-comparison-accrued-spend-cap-source-gate-v1"
        and payload.get("gate_id")
        == "d087-condition-neutral-comparison-accrued-spend-cap-source-gate",
        "D-087 source identity drifted",
    )
    policy = payload.get("campaign_spend_policy", {})
    runtime = payload.get("runtime_binding", {})
    _require(
        policy.get("schema_version") == "campaign-list-price-accrual-cap-v1"
        and policy.get("full_schedule_reserved_up_front") is False
        and policy.get("insufficient_reserve_action")
        == "mark-current-and-remaining-rows-not-started"
        and runtime.get("one_use_paid_boundary_capability") is True
        and runtime.get("atomic_sqlite_reservation_consumption") is True
        and runtime.get("durable_usage_evidence_binds_qualification_source_and_result_hashes")
        is True
        and runtime.get("token_derived_settlement") is True
        and runtime.get("external_or_request_level_billing_ledger_implemented") is False,
        "D-087 cost-journal provenance drifted",
    )
    _require(
        payload.get("authorization_boundary", {}).get("provider_execution_authorized") is False
        and payload.get("claims_boundary", {}).get("historical_artifacts_modified") is False,
        "D-087 historical boundary drifted",
    )
    return payload


def _validate_d094(payload: dict[str, Any]) -> dict[str, Any]:
    body = _content_addressed_body(
        payload,
        expected_hash=D094_BODY_HASH,
        label="D-094 source gate",
    )
    pricing = body.get("pricing", {})
    _require(
        pricing.get("pricing_source_url") == PRICING_SOURCE_URL
        and pricing.get("endpoint_pricing_mode") == "standard-default"
        and pricing.get("input_price_per_million_usd") == 0.75
        and pricing.get("cached_input_price_per_million_usd") == 0.075
        and pricing.get("cache_write_input_price_per_million_usd") is None
        and pricing.get("output_price_per_million_usd") == 4.5
        and pricing.get("per_run_worst_rate_reserve_usd") == 13.6125,
        "D-094 pricing provenance drifted",
    )
    return body


def _validate_suite(payload: dict[str, Any]) -> dict[str, Any]:
    expected_keys = {
        "schema_version",
        "experiment_id",
        "purpose",
        "tasks",
        "conditions",
        "repetitions",
        "model",
        "model_id",
        "reasoning_effort",
        "reasoning_mode",
        "service_tier",
        "transport_max_retries",
        "max_output_tokens",
        "budget",
        "seed",
        "pilot_run_id",
        "live_cost_approved",
        "approved_execution_hash",
        "campaign_cost_policy",
        "estimated_cost_usd",
        "cost_limit_usd",
        "pricing_verified_at",
        "pricing_source_url",
        "input_price_per_million_usd",
        "cached_input_price_per_million_usd",
        "cache_write_input_price_per_million_usd",
        "output_price_per_million_usd",
        "retrieval_threshold",
        "memory_token_budget",
        "embedding_model",
        "embedding_revision",
        "dataset_manifest_hash",
    }
    _require(set(payload) == expected_keys, "D-097 suite fields drifted")
    _require(
        payload.get("schema_version") == "experiment-v2"
        and payload.get("experiment_id") == EXPERIMENT_ID
        and payload.get("purpose") == "memory-development-no-memory"
        and payload.get("tasks") == list(TASK_PATHS)
        and payload.get("conditions") == ["no_memory"]
        and payload.get("repetitions") == 2
        and payload.get("seed") == 20260723,
        "D-097 suite schedule drifted",
    )
    _require(
        payload.get("model") == "openai"
        and payload.get("model_id") == RESOURCE_POLICY["model_id"]
        and payload.get("reasoning_effort") == "medium"
        and payload.get("reasoning_mode") == "standard"
        and payload.get("service_tier") == "default"
        and payload.get("transport_max_retries") == 0
        and payload.get("max_output_tokens") == 25_000
        and payload.get("budget") == RESOURCE_POLICY["budget"]
        and payload.get("memory_token_budget") == 2_000,
        "D-097 suite runtime tuple drifted",
    )
    _require(
        payload.get("pilot_run_id") is None
        and payload.get("live_cost_approved") is False
        and payload.get("approved_execution_hash") is None,
        "D-097 suite embeds live authority",
    )
    _require(
        payload.get("campaign_cost_policy") == COST_POLICY
        and payload.get("estimated_cost_usd") == 163.35
        and payload.get("cost_limit_usd") == 164.0,
        "D-097 full-schedule cost policy drifted",
    )
    _require(
        payload.get("pricing_verified_at") == PRICING_VERIFIED_AT
        and payload.get("pricing_source_url") == PRICING_SOURCE_URL
        and payload.get("input_price_per_million_usd") == 0.75
        and payload.get("cached_input_price_per_million_usd") == 0.075
        and payload.get("cache_write_input_price_per_million_usd") is None
        and payload.get("output_price_per_million_usd") == 4.5,
        "D-097 pricing tuple drifted",
    )
    _require(
        payload.get("retrieval_threshold") == 0.72
        and payload.get("embedding_model") == "sentence-transformers/all-MiniLM-L6-v2"
        and payload.get("embedding_revision") == "PIN_AT_FREEZE"
        and payload.get("dataset_manifest_hash") == DATASET_MANIFEST_HASH,
        "D-097 comparison metadata drifted",
    )
    return payload


def _validate_task_sources(
    root: Path,
    *,
    d096_body: dict[str, Any],
    dataset: dict[str, Any],
) -> list[dict[str, Any]]:
    admission_rows = d096_body["no_memory_baseline_admission"]["task_descriptors"]
    admission_by_id = {row["task_id"]: row for row in admission_rows}
    dataset_rows = dataset.get("tasks")
    _require(isinstance(dataset_rows, list), "dataset task registry is missing")
    dataset_by_id = {
        row.get("task_id"): row
        for row in dataset_rows
        if isinstance(row, dict) and isinstance(row.get("task_id"), str)
    }
    descriptors: list[dict[str, Any]] = []
    for base_order, public_path in enumerate(TASK_PATHS, start=1):
        task_id = Path(public_path).parent.name
        admission = admission_by_id.get(task_id, {})
        public_descriptor = {
            "path": public_path,
            "bytes": admission.get("public_bytes"),
            "sha256": admission.get("public_file_sha256"),
        }
        public_content = _read_exact(
            root,
            public_descriptor,
            label=f"public task {task_id}",
        )
        try:
            public_task = PublicTask.model_validate(
                _load_yaml(public_content, label=f"public task {task_id}")
            )
        except ValidationError as exc:
            raise D097BuildError(f"public task contract drifted for {task_id}") from exc
        public_spec_hash = sha256_json(public_task.model_dump(mode="json"))

        environment_descriptor = ENVIRONMENT_FILES[task_id]
        environment_content = _read_exact(
            root,
            environment_descriptor,
            label=f"task environment {task_id}",
        )
        try:
            environment = TaskEnvironment.model_validate(
                _load_yaml(
                    environment_content,
                    label=f"task environment {task_id}",
                )
            )
        except ValidationError as exc:
            raise D097BuildError(f"task environment contract drifted for {task_id}") from exc

        dataset_row = dataset_by_id.get(task_id, {})
        source = dataset_row.get("source", {})
        _require(
            admission.get("base_order") == base_order
            and admission.get("dataset_role") == "memory-development"
            and admission.get("admission_state") == "admitted"
            and admission.get("public_path") == public_path
            and admission.get("public_spec_hash") == public_spec_hash
            and public_task.task_id == task_id
            and dataset_row.get("path") == str(Path(public_path).parent).replace("\\", "/")
            and dataset_row.get("role") == "memory-development"
            and dataset_row.get("admission_state") == "admitted"
            and dataset_row.get("public_spec_hash") == public_spec_hash
            and source.get("environment_image") == environment.evaluator_image,
            f"frozen task admission drifted for {task_id}",
        )
        descriptors.append(
            {
                "base_order": base_order,
                "task_id": task_id,
                "task_version": public_task.task_version,
                "dataset_role": "memory-development",
                "admission_state": "admitted",
                "public_path": public_path,
                "public_bytes": len(public_content),
                "public_file_sha256": sha256_bytes(public_content),
                "public_spec_hash": public_spec_hash,
                "environment_path": environment_descriptor["path"],
                "environment_bytes": len(environment_content),
                "environment_file_sha256": sha256_bytes(environment_content),
                "evaluator_image": environment.evaluator_image,
                "image_digest": environment.image_digest,
            }
        )
    return descriptors


def _expanded_schedule() -> list[dict[str, Any]]:
    rows = [
        {"task_id": Path(path).parent.name, "repetition": repetition}
        for path in TASK_PATHS
        for repetition in (1, 2)
    ]
    random.Random(20260723).shuffle(rows)
    observed = tuple((row["task_id"], row["repetition"]) for row in rows)
    _require(observed == EXPECTED_RANDOMIZED_ROWS, "D-097 randomized schedule drifted")
    return [
        {"order": order, "condition": "no_memory", **row} for order, row in enumerate(rows, start=1)
    ]


def _validate_sources(root: Path) -> dict[str, Any]:
    contents = {
        role: _read_exact(root, descriptor, label=role) for role, descriptor in SOURCE_FILES.items()
    }
    d096 = _validate_d096(
        _load_json(
            contents["d096-resource-policy-and-admission"],
            label="D-096 decision",
        )
    )
    d087 = _validate_d087(
        _load_json(
            contents["d087-cost-journal-source"],
            label="D-087 cost source",
        )
    )
    d094 = _validate_d094(
        _load_json(
            contents["d094-pricing-source"],
            label="D-094 pricing source",
        )
    )
    dataset = _load_yaml(contents["dataset-manifest"], label="dataset manifest")
    _require(
        dataset.get("schema_version") == "dataset-manifest-v1"
        and dataset.get("dataset_id") == "patchloop-benchmark-v1"
        and dataset.get("status") == "frozen"
        and dataset.get("targets", {}).get("memory-development") == 6,
        "frozen dataset identity drifted",
    )
    suite = _validate_suite(_load_yaml(contents["successor-suite"], label="D-097 successor suite"))
    tasks = _validate_task_sources(root, d096_body=d096, dataset=dataset)
    return {
        "d096": d096,
        "d087": d087,
        "d094": d094,
        "dataset": dataset,
        "suite": suite,
        "tasks": tasks,
    }


def build_source_gate(
    *,
    repo_root: Path,
    recorded_at: str = RECORDED_AT,
) -> dict[str, Any]:
    sources = _validate_sources(repo_root)
    expanded_schedule = _expanded_schedule()
    source_binding_rows = [
        {"role": role, **descriptor} for role, descriptor in SOURCE_FILES.items()
    ]
    body: dict[str, Any] = {
        "milestone": "D-097",
        "evidence_kind": ("offline-condition-neutral-runtime-v2-no-memory-baseline-source-gate"),
        "recorded_at": recorded_at,
        "source_bindings": source_binding_rows,
        "resource_policy_binding": {
            "schema_version": "d096-resource-policy-binding-v1",
            "path": SOURCE_FILES["d096-resource-policy-and-admission"]["path"],
            "file_sha256": SOURCE_FILES["d096-resource-policy-and-admission"]["sha256"],
            "semantic_body_hash": D096_BODY_HASH,
            "decision_id": f"d096_{D096_BODY_HASH.removeprefix('sha256:')}",
            "profile_id": RESOURCE_PROFILE_ID,
            "baseline_admission_id": BASELINE_ADMISSION_ID,
            "schedule_identity_hash": (
                "sha256:e399114a6ea516821a30104a612f7222c0caf3f88def7b5d7472d15f7cc4c27b"
            ),
            "historical_v1_contracts_modified": False,
            "d087_or_d095_retroactively_admitted": False,
        },
        "successor_suite": {
            "schema_version": "condition-neutral-no-memory-source-v1",
            "experiment_id": EXPERIMENT_ID,
            "purpose": "memory-development-no-memory",
            "suite_path": SOURCE_FILES["successor-suite"]["path"],
            "suite_bytes": SOURCE_FILES["successor-suite"]["bytes"],
            "suite_file_sha256": SOURCE_FILES["successor-suite"]["sha256"],
            "task_descriptors": sources["tasks"],
            "conditions": ["no_memory"],
            "repetitions": 2,
            "seed": 20260723,
            "expected_rows": 12,
            "expanded_schedule": expanded_schedule,
            "expanded_schedule_hash": sha256_json(expanded_schedule),
            "model": {
                "provider": "openai",
                "model_id": RESOURCE_POLICY["model_id"],
                "reasoning_effort": "medium",
                "reasoning_mode": "standard",
                "service_tier": "default",
                "transport_max_retries": 0,
                "max_output_tokens": 25_000,
            },
            "agent_tuple": {
                "system_prompt_version": RESOURCE_POLICY["system_prompt_version"],
                "system_prompt_hash": RESOURCE_POLICY["system_prompt_hash"],
                "tool_schema_version": "v2",
                "tool_schema_hash": RESOURCE_POLICY["tool_schema_hash"],
                "context_policy_version": "phase-evidence-v5",
                "call_guard_policy": "model-tool-observability-only-v1",
                "memory_max_context_tokens": 2_000,
            },
            "budget": dict(RESOURCE_POLICY["budget"]),
            "budget_role": "finite-non-target-safety-ceiling",
            "completion_guaranteed": False,
            "pilot_run_id": None,
            "historical_pilot_reused": False,
            "live_cost_approved": False,
            "approved_execution_hash": None,
        },
        "runtime_binding": {
            "schema_version": "condition-neutral-runtime-v2-source-binding-v1",
            "runtime_contract_schema": RUNTIME_CONTRACT_SCHEMA,
            "runtime_evidence_schema": RUNTIME_EVIDENCE_SCHEMA,
            "campaign_cost_policy_schema": ("campaign-list-price-full-schedule-reserve-v1"),
            "campaign_cost_control_schema": ("campaign-full-schedule-cost-control-evidence-v1"),
            "durable_usage_evidence_schema": (
                "condition-neutral-full-schedule-durable-usage-evidence-v1"
            ),
            "resource_policy_profile_id": RESOURCE_PROFILE_ID,
            "baseline_admission_id": BASELINE_ADMISSION_ID,
            "execution_plan_binding_required": True,
            "execution_hash_binding_required": True,
            "run_manifest_binding_required": True,
            "run_started_cas_binding_required": True,
            "fresh_start_validation_required": True,
            "resume_validation_required": True,
            "qualification_read_only_recomputation_required": True,
            "persisted_qualification_exact_match_required": True,
            "disabled_call_guard_qualification_required": True,
            "source_contract_frozen": True,
            "implementation_verified_by_this_source_builder": False,
        },
        "pricing": {
            "schema_version": "d097-fresh-standard-pricing-v1",
            "verified_at": PRICING_VERIFIED_AT,
            "verification_method": "official-openai-docs-mcp-read-only",
            "pricing_source_url": PRICING_SOURCE_URL,
            "endpoint_pricing_mode": "standard-default",
            "model_id": RESOURCE_POLICY["model_id"],
            "input_price_per_million_usd": 0.75,
            "cached_input_price_per_million_usd": 0.075,
            "cache_write_input_price_per_million_usd": None,
            "output_price_per_million_usd": 4.5,
            "worst_rate_reserve_formula": (
                "(max_total_tokens + max_output_tokens) * output_price_per_million_usd / 1000000"
            ),
            "per_run_worst_rate_reserve_usd": 13.6125,
            "full_schedule_worst_rate_reserve_usd": 163.35,
            "reserve_is_expected_invoice": False,
            "free_tier_or_billed_charge_claimed": False,
            "fresh_revalidation_required_at_clean_preflight": True,
            "maximum_age_hours": 72,
        },
        "campaign_cost_policy": {
            **COST_POLICY,
            "historical_d087_policy_reused": False,
            "d087_journal_safety_properties_carried_forward": [
                "canonical-journal-and-runner-root-binding",
                "append-only-hash-chain",
                "durable-token-derived-settlement",
            ],
            "full_schedule_reserve_recorded_before_first_provider_call": True,
            "initial_reservation_failure_action": "fail-before-any-paid-row",
            "later_row_admission_conditioned_on_earlier_row_settlement": False,
            "per_row_atomic_sqlite_consumption_implemented": False,
            "duplicate_paid_call_prevention_claimed": False,
            "unknown_request_outcome_holds_full_row_reserve": True,
            "whole-local-state-rollback_prevented": False,
            "external_or_request_level_billing_ledger_implemented": False,
        },
        "baseline_completion_predicate": {
            "schema_version": "no-memory-baseline-source-completion-v1",
            "expected_rows": 12,
            "terminal_rows": 12,
            "trace_qualified_rows": 12,
            "cost_settled_rows": 12,
            "not_started_rows": 0,
            "infrastructure_errors": 0,
            "qualification_errors": 0,
            "diagnostic_errors": 0,
            "duplicate_or_replacement_rows": 0,
            "unknown_terminal_rows": 0,
            "model_or_tool_call_budget_blocks": 0,
            "campaign_cost_censored_rows": 0,
            "allowed_terminal_branches": [
                "official-evaluator-completed",
                "trace-qualified-frozen-policy-budget-terminal",
            ],
            "terminal_branches_mutually_exclusive_and_exhaustive": True,
            "persisted_qualification_matches_read_only_recomputation": True,
            "plan_manifest_runtime_policy_admission_cost_binding_exact": True,
            "no_memory_boundary_passed": True,
            "prompt_usage_telemetry_complete": True,
            "issued_model_calls_equal_completed_responses": True,
            "store_false_and_truncation_disabled": True,
            "task_success_required": False,
            "budget_terminal_is_denominator_agent_failure": True,
            "budget_terminal_automatic_rerun_allowed": False,
            "budget_or_infrastructure_failure_memory_candidate_eligible": False,
        },
        "authorization_boundary": {
            "schema_version": "d097-source-authorization-boundary-v1",
            "source_offline_gate_only": True,
            "prospective_suite_cap_selected": True,
            "full_schedule_worst_rate_reserve_usd": 163.35,
            "maximum_future_approval_cap_usd": 164.0,
            "historical_project_cap_usd": 150.0,
            "historical_project_cap_changed": False,
            "campaign_scoped_cap_exception_user_approved": False,
            "clean_source_commit_created": False,
            "clean_no_call_preflight_performed": False,
            "candidate_execution_hash_created": False,
            "candidate_execution_hash": None,
            "approved_execution_hash_created": False,
            "live_cost_approval_embedded": False,
            "provider_execution_authorized": False,
            "evaluator_execution_authorized": False,
            "automatic_execution_authorized": False,
            "separate_exact_hash_and_maximum_cost_approval_required": True,
            "blocker_code": ("NO_MEMORY_CLEAN_PREFLIGHT_AND_164_USD_APPROVAL_PENDING"),
        },
        "claims_boundary": {
            "d097_source_contract_created": True,
            "exact_successor_suite_created": True,
            "resource_policy_v2_bound_at_source": True,
            "full_schedule_non_censoring_cost_policy_selected": True,
            "cost_policy_is_experimental_target": False,
            "runtime_v2_source_contract_frozen": True,
            "runtime_v2_implementation_verified_by_artifact": False,
            "clean_preflight_complete": False,
            "live_execution_authorized": False,
            "no_memory_baseline_result_established": False,
            "development_baseline_denominator_complete": False,
            "memory_review_authorized": False,
            "memory_admission_unlocked": False,
            "memory_index_frozen": False,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "historical_artifacts_modified": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0.0,
        },
        "next_gate": {
            "gate": "clean-no-call-preflight",
            "clean_committed_source_required": True,
            "frozen_dataset_and_task_bytes_revalidation_required": True,
            "docker_and_evaluator_identity_revalidation_required": True,
            "openai_sdk_identity_revalidation_required": True,
            "fresh_official_pricing_revalidation_required": True,
            "candidate_execution_hash_required": True,
            "separate_user_approval_required": True,
            "maximum_future_approval_cap_usd": 164.0,
            "approval_must_acknowledge_campaign_scoped_150_cap_exception": True,
            "provider_or_evaluator_call_allowed_during_preflight": False,
            "automatic_execution_authorized": False,
        },
    }
    body_hash = sha256_json(body)
    return {
        "schema_version": ("condition-neutral-baseline-source-gate-d097-evidence-v1"),
        "gate_id": f"d097_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the content-addressed D-097 offline source gate."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--recorded-at", default=RECORDED_AT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    payload = build_source_gate(repo_root=repo_root, recorded_at=args.recorded_at)
    rendered = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if args.compact
        else json.dumps(payload, ensure_ascii=False, indent=2)
    )
    if args.output is None:
        print(rendered)
    else:
        output = args.output
        if not output.is_absolute():
            output = repo_root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
