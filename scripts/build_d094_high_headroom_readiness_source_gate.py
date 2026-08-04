from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from patchloop.util import sha256_bytes, sha256_json

RECORDED_AT = "2026-08-04T14:47:00Z"
EXPERIMENT_ID = "generic-high-headroom-readiness-v2v5-20260804-r1"
SUITE_RELATIVE_PATH = f"experiments/{EXPERIMENT_ID}.yaml"
SUITE_BYTES = 1_666
SUITE_FILE_SHA256 = "sha256:a7d8382a7e46167bf3c439bcb93ed93a28797d83fb276c22180c74a236a39f67"

D093_RELATIVE_PATH = "reports/live-pilot/artifacts/d093-readiness-budget-outcome-correction.json"
D093_BYTES = 9_611
D093_FILE_SHA256 = "sha256:df8a35d7818dba3055ee4bb34519bd39abdc97d4d6add178d3d41b0521273941"
D093_BODY_SHA256 = "sha256:3a5790e57252132387b803681339e00032c62f7026a81d9acbd9f4598fc64ccd"
D093_CORRECTION_ID = "rbocor_3a5790e57252132387b803681339e00032c62f7026a81d9acbd9f4598fc64ccd"
D093_SOURCE_COMMIT = "147263328d678601be86b4cf334f135d840dc98f"

D084_RELATIVE_PATH = (
    "reports/live-pilot/artifacts/d084-condition-neutral-comparison-runtime-gate.json"
)
D084_BYTES = 7_178
D084_FILE_SHA256 = "sha256:e7fb7b7e7e9dad3e6b31fb781f09151b940bf226bdd5876e5e75e472ff24b701"

DATASET_RELATIVE_PATH = "data/dataset-manifest.yaml"
DATASET_BYTES = 47_368
DATASET_FILE_SHA256 = "sha256:e8cf14ca9dabebcc03c3522e400dfcb79606541e9b11e59f49510ea5c40bebed"
DATASET_MANIFEST_HASH = "sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786"

SYSTEM_PROMPT_HASH = "sha256:441c71fdea2defed14f06b32c3fba7a7aaa19f7a3ca749bc994e72708d8a733b"
TOOL_SCHEMA_HASH = "sha256:2ee296c2cf515bf2e0937ec1727dc02046a8560581d39b71246c5b91eccf0827"

TASK_DESCRIPTORS = (
    {
        "task_id": "anyio-interrupt-runner-cleanup",
        "task_version": 1,
        "split": "dev-train",
        "dataset_role": "memory-development",
        "admission_state": "admitted",
        "repository_url": "https://github.com/agronholm/anyio.git",
        "base_commit": "cb245dba9883516f2ed4c23899de157183a1cb50",
        "public_path": ("tasks/dev-train/anyio-interrupt-runner-cleanup/public.yaml"),
        "public_bytes": 1_864,
        "public_file_sha256": (
            "sha256:ea977422306f9ce7203b4fc92aac83a73bc41554813d9ce1d794546767e76ddd"
        ),
        "public_spec_hash": (
            "sha256:b6d5b8d42a003795ed38256fa9a0e07c94578a6e0996179588a15d42604b86bf"
        ),
        "environment_path": ("tasks/dev-train/anyio-interrupt-runner-cleanup/environment.yaml"),
        "environment_bytes": 344,
        "environment_file_sha256": (
            "sha256:56ef76aff34338c70c94e5fd60eeda7a3d6aab1e32390b4584a9ef9870495635"
        ),
        "evaluator_image": (
            "swerebench/sweb.eval.x86_64.agronholm_1776_anyio-1121@"
            "sha256:063bb968109c70a3fe617d9d30287a3a43d549eb1091b27a030a9af2a74c2320"
        ),
        "image_digest": ("sha256:063bb968109c70a3fe617d9d30287a3a43d549eb1091b27a030a9af2a74c2320"),
    },
    {
        "task_id": "pyfakefs-makedirs-parent-traversal",
        "task_version": 1,
        "split": "dev-train",
        "dataset_role": "memory-development",
        "admission_state": "admitted",
        "repository_url": "https://github.com/pytest-dev/pyfakefs.git",
        "base_commit": "7285b671883b8a06fc26466582a8a45baf508bf7",
        "public_path": ("tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml"),
        "public_bytes": 1_852,
        "public_file_sha256": (
            "sha256:5be7e6f6d2ad9722ee90c5a829aa043bf94c70ac317d5ce45254e4f3f9458eb0"
        ),
        "public_spec_hash": (
            "sha256:4d5de049d133ee29adf726733b7ace99b9d55518cc0433c72d2aa7b1576664d8"
        ),
        "environment_path": ("tasks/dev-train/pyfakefs-makedirs-parent-traversal/environment.yaml"),
        "environment_bytes": 327,
        "environment_file_sha256": (
            "sha256:93b6c006b7528a84054e24871000511642086ef93fd738951ac1e3123ca291d8"
        ),
        "evaluator_image": (
            "docker.io/swerebenchv2/pytest-dev-pyfakefs@"
            "sha256:6de3b39018eec22728567f44dfbdc3cbd31322c384f6ee3d7f328ef38165d57c"
        ),
        "image_digest": ("sha256:6de3b39018eec22728567f44dfbdc3cbd31322c384f6ee3d7f328ef38165d57c"),
    },
    {
        "task_id": "hf-hub-xet-endpoint-propagation",
        "task_version": 1,
        "split": "dev-train",
        "dataset_role": "memory-development",
        "admission_state": "admitted",
        "repository_url": "https://github.com/huggingface/huggingface_hub.git",
        "base_commit": "6f9b87ecda5025259c69a1eb0ae6f8ee80d05d33",
        "public_path": ("tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml"),
        "public_bytes": 1_825,
        "public_file_sha256": (
            "sha256:3500452712d3977761f24da95170f073f86ec2a0589b69522321f91f5f473c4f"
        ),
        "public_spec_hash": (
            "sha256:8f7b0ea5f92ec9d843b8053f0739b42570b7407d76fe6f7a7ea6fd08c481a075"
        ),
        "environment_path": ("tasks/dev-train/hf-hub-xet-endpoint-propagation/environment.yaml"),
        "environment_bytes": 344,
        "environment_file_sha256": (
            "sha256:9a6487d24ae7bf6436f3f93d7f4e34fb1a5be5674a342e2f1f2cf53b8f73581a"
        ),
        "evaluator_image": (
            "docker.io/swerebenchv2/huggingface-huggingface-hub@"
            "sha256:c698facf4c9a9e636b8dc114aa9bda6a17ee5f89fe3efd43f39a6543540e891f"
        ),
        "image_digest": ("sha256:c698facf4c9a9e636b8dc114aa9bda6a17ee5f89fe3efd43f39a6543540e891f"),
    },
)

EXPECTED_REQUIRED_TRUE = [
    "all_rows_started_and_terminal",
    "all_rows_trace_qualified",
    "all_rows_submission_accepted",
    "all_rows_evaluator_reached",
    "all_rows_official_evaluator",
    "persisted_qualification_matches_read_only_recomputation",
    "exact_input_telemetry_complete",
    "responses_completed",
    "truncation_disabled",
]
EXPECTED_REQUIRED_ZERO = [
    "infrastructure_errors",
    "qualification_errors",
    "diagnostic_errors",
    "budget_terminal_runs",
    "terminal_loop_failure_runs",
    "model_or_tool_call_budget_blocks",
]


class D094BuildError(RuntimeError):
    pass


def _require_dict(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D094BuildError(f"{label} must be an object")
    return value


def _require_list(value: object, *, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise D094BuildError(f"{label} must be an array")
    return value


def _read_exact_bytes(
    *,
    repo_root: Path,
    relative_path: str,
    expected_bytes: int,
    expected_file_sha256: str,
    label: str,
) -> bytes:
    source = (repo_root / relative_path).read_bytes()
    if len(source) != expected_bytes:
        raise D094BuildError(f"{label} source byte count drifted")
    if sha256_bytes(source) != expected_file_sha256:
        raise D094BuildError(f"{label} source file hash drifted")
    return source


def _load_json(source: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(source)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D094BuildError(f"{label} is not valid UTF-8 JSON") from exc
    return _require_dict(payload, label=label)


def _load_yaml(source: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(source.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise D094BuildError(f"{label} is not valid UTF-8 YAML") from exc
    return _require_dict(payload, label=label)


def _normalize_timestamp(value: object, *, label: str) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise D094BuildError(f"{label} must be an offset-aware timestamp")
    normalized = value.astimezone(UTC).isoformat(timespec="seconds")
    return normalized.replace("+00:00", "Z")


def _assert_exact(value: object, expected: object, *, label: str) -> None:
    if isinstance(expected, dict):
        actual = _require_dict(value, label=label)
        if set(actual) != set(expected):
            raise D094BuildError(f"{label} keys drifted")
        for key, expected_value in expected.items():
            _assert_exact(actual[key], expected_value, label=f"{label}.{key}")
        return
    if isinstance(expected, list):
        actual = _require_list(value, label=label)
        if len(actual) != len(expected):
            raise D094BuildError(f"{label} length drifted")
        for index, (actual_value, expected_value) in enumerate(zip(actual, expected, strict=True)):
            _assert_exact(
                actual_value,
                expected_value,
                label=f"{label}[{index}]",
            )
        return
    if type(value) is not type(expected) or value != expected:
        raise D094BuildError(f"{label} drifted")


def _validate_d093(payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) != {
        "schema_version",
        "correction_id",
        "semantic_body_hash",
        "semantic_body",
    }:
        raise D094BuildError("D-093 wrapper keys drifted")
    if payload.get("schema_version") != ("readiness-budget-outcome-correction-manifest-v1"):
        raise D094BuildError("D-093 wrapper schema drifted")
    if payload.get("correction_id") != D093_CORRECTION_ID:
        raise D094BuildError("D-093 correction ID drifted")
    if payload.get("semantic_body_hash") != D093_BODY_SHA256:
        raise D094BuildError("D-093 semantic body hash drifted")
    body = _require_dict(payload.get("semantic_body"), label="D-093 body")
    if sha256_json(body) != D093_BODY_SHA256:
        raise D094BuildError("D-093 semantic body content drifted")

    next_gate = _require_dict(body.get("next_gate"), label="D-093 next gate")
    if next_gate.get("gate") != "high-headroom-diverse-readiness-source-gate":
        raise D094BuildError("D-093 successor gate drifted")
    expected_tasks = [descriptor["task_id"] for descriptor in TASK_DESCRIPTORS]
    _assert_exact(
        next_gate.get("candidate_tasks"),
        expected_tasks,
        label="D-093 candidate tasks",
    )
    expected_derivation = {
        "source_run_ids": [
            "run_4613c65b2a254349",
            "run_e444de1bb20a4325",
        ],
        "observed_public_maximum_tokens": 1_956_109,
        "token_multiplier_numerator": 3,
        "token_multiplier_denominator": 2,
        "token_unrounded_numerator": 5_868_327,
        "token_unrounded_denominator": 2,
        "token_rounding_quantum": 100_000,
        "candidate_max_total_tokens": 3_000_000,
        "observed_public_maximum_wall_clock_ms": 1_628_695,
        "wall_multiplier_numerator": 2,
        "wall_multiplier_denominator": 1,
        "wall_unrounded_milliseconds": 3_257_390,
        "wall_unit_conversion_milliseconds_per_second": 1_000,
        "wall_rounding_quantum_seconds": 600,
        "candidate_wall_clock_timeout_seconds": 3_600,
        "max_model_calls": None,
        "max_tool_calls": None,
    }
    _assert_exact(
        next_gate.get("candidate_resource_derivation"),
        expected_derivation,
        label="D-093 resource derivation",
    )
    for key in (
        "candidate_values_are_source_frozen",
        "automatic_successor_execution_authorized",
        "provider_execution_authorized",
    ):
        if next_gate.get(key) is not False:
            raise D094BuildError(f"D-093 authority boundary drifted: {key}")
    for key in (
        "clean_source_commit_required",
        "fresh_official_price_check_required",
        "fresh_no_call_preflight_required",
        "new_execution_hash_required",
        "separate_user_cost_approval_required",
    ):
        if next_gate.get(key) is not True:
            raise D094BuildError(f"D-093 successor requirement drifted: {key}")

    readiness = _require_dict(
        body.get("corrected_readiness_stage_contract"),
        label="D-093 readiness contract",
    )
    gate = _require_dict(
        readiness.get("readiness_completion_gate"),
        label="D-093 readiness completion gate",
    )
    expected_gate = {
        "required_true": EXPECTED_REQUIRED_TRUE,
        "required_zero": EXPECTED_REQUIRED_ZERO,
        "task_success_required": False,
        "hidden_acceptance_required": False,
        "scrr_required": False,
    }
    _assert_exact(gate, expected_gate, label="D-093 readiness gate")
    return body


def _validate_d084(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != ("condition-neutral-comparison-runtime-gate-v1"):
        raise D094BuildError("D-084 schema drifted")
    if payload.get("gate_id") != "d084-condition-neutral-comparison-runtime-gate":
        raise D094BuildError("D-084 gate ID drifted")
    profile = _require_dict(payload.get("comparison_profile"), label="D-084 comparison profile")
    expected_stable_profile = {
        "provider": "openai",
        "model_id": "gpt-5.4-mini-2026-03-17",
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "transport_max_retries": 0,
        "system_prompt_version": "SYSTEM_PROMPT_V3",
        "system_prompt_hash": SYSTEM_PROMPT_HASH,
        "tool_schema_version": "v2",
        "tool_schema_hash": TOOL_SCHEMA_HASH,
        "context_policy_version": "phase-evidence-v5",
        "memory_max_context_tokens": 2_000,
        "max_output_tokens": 25_000,
        "call_guard_policy": "model-tool-observability-only-v1",
    }
    for key, expected in expected_stable_profile.items():
        _assert_exact(profile.get(key), expected, label=f"D-084 comparison profile.{key}")
    runtime = _require_dict(payload.get("runtime_contract"), label="D-084 runtime contract")
    if runtime.get("schema_version") != ("condition-neutral-comparison-runtime-contract-v1"):
        raise D094BuildError("D-084 runtime contract schema drifted")
    authorization = _require_dict(
        payload.get("authorization_boundary"), label="D-084 authorization"
    )
    for key in (
        "provider_execution_authorized",
        "approved_execution_hash_created",
        "live_cost_approval_embedded",
        "automatic_execution_authorized",
    ):
        if authorization.get(key) is not False:
            raise D094BuildError(f"D-084 authority boundary drifted: {key}")
    return profile


def _validate_dataset_and_tasks(
    *, repo_root: Path, dataset: dict[str, Any]
) -> list[dict[str, Any]]:
    if dataset.get("schema_version") != "dataset-manifest-v1":
        raise D094BuildError("dataset schema drifted")
    if dataset.get("dataset_id") != "patchloop-benchmark-v1":
        raise D094BuildError("dataset ID drifted")
    if dataset.get("status") != "frozen":
        raise D094BuildError("dataset is not frozen")
    entries = _require_list(dataset.get("tasks"), label="dataset tasks")
    projections: list[dict[str, Any]] = []
    for descriptor in TASK_DESCRIPTORS:
        matches = [
            item
            for item in entries
            if isinstance(item, dict) and item.get("task_id") == descriptor["task_id"]
        ]
        if len(matches) != 1:
            raise D094BuildError(
                f"dataset task exact-one invariant failed: {descriptor['task_id']}"
            )
        entry = matches[0]
        source = _require_dict(entry.get("source"), label=f"{descriptor['task_id']} dataset source")
        expected_entry = {
            "task_version": descriptor["task_version"],
            "path": str(Path(descriptor["public_path"]).parent).replace("\\", "/"),
            "role": descriptor["dataset_role"],
            "admission_state": descriptor["admission_state"],
            "public_spec_hash": descriptor["public_spec_hash"],
        }
        for key, expected in expected_entry.items():
            _assert_exact(
                entry.get(key),
                expected,
                label=f"{descriptor['task_id']} dataset entry.{key}",
            )
        if source.get("environment_image") != descriptor["evaluator_image"]:
            raise D094BuildError(f"{descriptor['task_id']} dataset environment image drifted")

        public_bytes = _read_exact_bytes(
            repo_root=repo_root,
            relative_path=str(descriptor["public_path"]),
            expected_bytes=int(descriptor["public_bytes"]),
            expected_file_sha256=str(descriptor["public_file_sha256"]),
            label=f"{descriptor['task_id']} public descriptor",
        )
        public = _load_yaml(public_bytes, label=f"{descriptor['task_id']} public descriptor")
        repository = _require_dict(
            public.get("repository"),
            label=f"{descriptor['task_id']} public repository",
        )
        public_projection = {
            "schema_version": public.get("schema_version"),
            "task_id": public.get("task_id"),
            "task_version": public.get("task_version"),
            "split": public.get("split"),
            "repository_url": repository.get("url"),
            "base_commit": repository.get("base_commit"),
        }
        expected_public_projection = {
            "schema_version": "task-public-v1",
            "task_id": descriptor["task_id"],
            "task_version": descriptor["task_version"],
            "split": descriptor["split"],
            "repository_url": descriptor["repository_url"],
            "base_commit": descriptor["base_commit"],
        }
        _assert_exact(
            public_projection,
            expected_public_projection,
            label=f"{descriptor['task_id']} public projection",
        )

        environment_bytes = _read_exact_bytes(
            repo_root=repo_root,
            relative_path=str(descriptor["environment_path"]),
            expected_bytes=int(descriptor["environment_bytes"]),
            expected_file_sha256=str(descriptor["environment_file_sha256"]),
            label=f"{descriptor['task_id']} environment descriptor",
        )
        environment = _load_yaml(
            environment_bytes,
            label=f"{descriptor['task_id']} environment descriptor",
        )
        expected_environment = {
            "schema_version": "task-environment-v1",
            "evaluator_image": descriptor["evaluator_image"],
            "image_digest": descriptor["image_digest"],
            "source_image_tag": environment.get("source_image_tag"),
        }
        _assert_exact(
            environment,
            expected_environment,
            label=f"{descriptor['task_id']} environment descriptor",
        )
        if not str(descriptor["evaluator_image"]).endswith(f"@{descriptor['image_digest']}"):
            raise D094BuildError(f"{descriptor['task_id']} evaluator image is not digest pinned")
        projections.append(dict(descriptor))
    return projections


def _validate_suite(payload: dict[str, Any]) -> None:
    normalized = dict(payload)
    normalized["pricing_verified_at"] = _normalize_timestamp(
        payload.get("pricing_verified_at"), label="suite.pricing_verified_at"
    )
    expected = {
        "schema_version": "experiment-v2",
        "experiment_id": EXPERIMENT_ID,
        "purpose": "generic-baseline-readiness",
        "tasks": [descriptor["public_path"] for descriptor in TASK_DESCRIPTORS],
        "conditions": ["no_memory"],
        "repetitions": 1,
        "model": "openai",
        "model_id": "gpt-5.4-mini-2026-03-17",
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "transport_max_retries": 0,
        "max_output_tokens": 25_000,
        "budget": {
            "max_model_calls": None,
            "max_tool_calls": None,
            "max_total_tokens": 3_000_000,
            "wall_clock_timeout_seconds": 3_600,
        },
        "seed": 20_260_723,
        "live_cost_approved": False,
        "approved_execution_hash": None,
        "pilot_run_id": None,
        "estimated_cost_usd": 40.8375,
        "cost_limit_usd": 41,
        "pricing_verified_at": RECORDED_AT,
        "pricing_source_url": "https://developers.openai.com/api/docs/pricing",
        "input_price_per_million_usd": 0.75,
        "cached_input_price_per_million_usd": 0.075,
        "cache_write_input_price_per_million_usd": None,
        "output_price_per_million_usd": 4.5,
        "retrieval_threshold": 0.72,
        "memory_token_budget": 2_000,
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_revision": "PIN_AT_FREEZE",
        "dataset_manifest_hash": DATASET_MANIFEST_HASH,
    }
    _assert_exact(normalized, expected, label="D-094 suite")


def build_source_gate(*, repo_root: Path, recorded_at: str) -> dict[str, object]:
    d093_bytes = _read_exact_bytes(
        repo_root=repo_root,
        relative_path=D093_RELATIVE_PATH,
        expected_bytes=D093_BYTES,
        expected_file_sha256=D093_FILE_SHA256,
        label="D-093",
    )
    d093_body = _validate_d093(_load_json(d093_bytes, label="D-093 source"))
    d084_bytes = _read_exact_bytes(
        repo_root=repo_root,
        relative_path=D084_RELATIVE_PATH,
        expected_bytes=D084_BYTES,
        expected_file_sha256=D084_FILE_SHA256,
        label="D-084",
    )
    d084_profile = _validate_d084(_load_json(d084_bytes, label="D-084 source"))
    suite_bytes = _read_exact_bytes(
        repo_root=repo_root,
        relative_path=SUITE_RELATIVE_PATH,
        expected_bytes=SUITE_BYTES,
        expected_file_sha256=SUITE_FILE_SHA256,
        label="D-094 suite",
    )
    suite = _load_yaml(suite_bytes, label="D-094 suite")
    _validate_suite(suite)
    dataset_bytes = _read_exact_bytes(
        repo_root=repo_root,
        relative_path=DATASET_RELATIVE_PATH,
        expected_bytes=DATASET_BYTES,
        expected_file_sha256=DATASET_FILE_SHA256,
        label="frozen dataset manifest",
    )
    dataset = _load_yaml(dataset_bytes, label="frozen dataset manifest")
    task_descriptors = _validate_dataset_and_tasks(repo_root=repo_root, dataset=dataset)

    d093_next_gate = _require_dict(d093_body["next_gate"], label="D-093 next gate")
    derivation = _require_dict(
        d093_next_gate["candidate_resource_derivation"],
        label="D-093 resource derivation",
    )
    per_run_reserve_decimal = Decimal(3_000_000 + 25_000) * Decimal("4.5") / Decimal(1_000_000)
    suite_reserve_decimal = per_run_reserve_decimal * len(task_descriptors)
    if per_run_reserve_decimal != Decimal("13.6125") or suite_reserve_decimal != Decimal("40.8375"):
        raise D094BuildError("worst-rate reserve calculation drifted")
    per_run_reserve = float(per_run_reserve_decimal)
    suite_reserve = float(suite_reserve_decimal)

    body = {
        "schema_version": "high-headroom-readiness-source-gate-v1",
        "milestone": "D-094 high-headroom diverse readiness source gate",
        "recorded_at": recorded_at,
        "source_binding": {
            "d093_readiness_budget_correction": {
                "path": D093_RELATIVE_PATH,
                "bytes": D093_BYTES,
                "file_sha256": D093_FILE_SHA256,
                "semantic_body_hash": D093_BODY_SHA256,
                "correction_id": D093_CORRECTION_ID,
                "source_git_commit": D093_SOURCE_COMMIT,
                "modified": False,
            },
            "d084_runtime_gate": {
                "path": D084_RELATIVE_PATH,
                "bytes": D084_BYTES,
                "file_sha256": D084_FILE_SHA256,
                "gate_id": "d084-condition-neutral-comparison-runtime-gate",
                "modified": False,
            },
            "experiment_suite": {
                "path": SUITE_RELATIVE_PATH,
                "bytes": SUITE_BYTES,
                "file_sha256": SUITE_FILE_SHA256,
                "experiment_id": EXPERIMENT_ID,
            },
            "frozen_dataset": {
                "path": DATASET_RELATIVE_PATH,
                "bytes": DATASET_BYTES,
                "file_sha256": DATASET_FILE_SHA256,
                "canonical_manifest_hash": DATASET_MANIFEST_HASH,
                "dataset_id": "patchloop-benchmark-v1",
                "status": "frozen",
                "manifest_body_embedded": False,
            },
        },
        "panel_source": {
            "schema_version": "high-headroom-readiness-panel-source-v1",
            "experiment_id": EXPERIMENT_ID,
            "purpose": "generic-baseline-readiness",
            "task_descriptors": task_descriptors,
            "memory_conditions": ["no_memory"],
            "repetitions": 1,
            "model": {
                "provider": d084_profile["provider"],
                "model_id": d084_profile["model_id"],
                "reasoning_effort": d084_profile["reasoning_effort"],
                "reasoning_mode": d084_profile["reasoning_mode"],
                "service_tier": d084_profile["service_tier"],
                "transport_max_retries": d084_profile["transport_max_retries"],
                "max_output_tokens": 25_000,
            },
            "agent_tuple": {
                "system_prompt_version": "SYSTEM_PROMPT_V3",
                "system_prompt_hash": SYSTEM_PROMPT_HASH,
                "tool_schema_version": "v2",
                "tool_schema_hash": TOOL_SCHEMA_HASH,
                "context_policy_version": "phase-evidence-v5",
                "call_guard_policy": "model-tool-observability-only-v1",
                "memory_max_context_tokens": 2_000,
            },
            "budget": {
                "max_model_calls": None,
                "max_tool_calls": None,
                "max_total_tokens": derivation["candidate_max_total_tokens"],
                "wall_clock_timeout_seconds": derivation["candidate_wall_clock_timeout_seconds"],
            },
            "seed": 20_260_723,
        },
        "resource_derivation": {
            "schema_version": "high-headroom-resource-derivation-v1",
            "d093_candidate_resource_derivation": derivation,
            "candidate_values_now_source_frozen_for_exact_experiment": True,
            "budget_role": "non-target-emergency-safety-ceiling",
            "budget_is_target_experimental_factor": False,
            "completion_guaranteed": False,
            "comparison_resource_policy_frozen": False,
        },
        "pricing": {
            "schema_version": "high-headroom-readiness-pricing-v1",
            "verified_at": RECORDED_AT,
            "pricing_source_url": ("https://developers.openai.com/api/docs/pricing"),
            "model_page_url": ("https://developers.openai.com/api/docs/models/gpt-5.4-mini"),
            "current_snapshot": "gpt-5.4-mini-2026-03-17",
            "endpoint_pricing_mode": "standard-default",
            "input_price_per_million_usd": 0.75,
            "cached_input_price_per_million_usd": 0.075,
            "cache_write_input_price_per_million_usd": None,
            "output_price_per_million_usd": 4.5,
            "worst_rate_reserve_formula": (
                "(max_total_tokens + max_output_tokens) * output_price_per_million_usd / 1000000"
            ),
            "per_run_worst_rate_reserve_usd": per_run_reserve,
            "expected_runs": len(task_descriptors),
            "suite_worst_rate_reserve_usd": suite_reserve,
            "source_estimated_cost_usd": 40.8375,
            "source_cost_limit_usd": 41.0,
            "reserve_is_expected_invoice": False,
            "free_tier_or_billed_charge_claimed": False,
        },
        "runtime_binding": {
            "schema_version": "high-headroom-readiness-runtime-binding-v1",
            "runtime_contract_schema": ("generic-high-headroom-readiness-runtime-contract-v1"),
            "runtime_evidence_schema": ("generic-high-headroom-readiness-runtime-evidence-v1"),
            "completion_gate_schema": "generic-high-headroom-readiness-gate-v1",
            "completion_gate_id": "d094-generic-high-headroom-readiness",
            "execution_plan_and_hash_bound": True,
            "run_manifest_exact_selector": True,
            "pre_start_manifest_reconstruction": True,
            "run_started_content_addressed_evidence": True,
            "fresh_start_validation": True,
            "resume_validation": True,
            "disabled_call_guard_qualification": True,
            "persisted_qualification_read_only_recomputation": True,
            "pricing_start_freshness_qualification": True,
        },
        "readiness_predicate": {
            "schema_version": "generic-high-headroom-readiness-gate-v1",
            "gate_id": "d094-generic-high-headroom-readiness",
            "expected_runs": 3,
            "terminal_runs_required": 3,
            "trace_qualified_runs_required": 3,
            "accepted_submission_runs_required": 3,
            "evaluator_reached_runs_required": 3,
            "official_evaluator_runs_required": 3,
            "persisted_qualification_matches_read_only_recomputation_required": (True),
            "exact_input_telemetry_complete_required": True,
            "responses_completed_required": True,
            "truncation_disabled_required": True,
            "infrastructure_errors_allowed": 0,
            "qualification_errors_allowed": 0,
            "diagnostic_errors_allowed": 0,
            "budget_terminal_runs_allowed": 0,
            "terminal_loop_failure_runs_allowed": 0,
            "model_or_tool_call_budget_blocks_allowed": 0,
            "task_success_required": False,
            "hidden_acceptance_required": False,
            "scrr_required": False,
            "calibration_only": True,
        },
        "authorization_boundary": {
            "schema_version": "high-headroom-readiness-source-authorization-v1",
            "source_offline_gate_only": True,
            "clean_no_call_preflight_performed": False,
            "candidate_execution_hash_created": False,
            "candidate_execution_hash": None,
            "approved_execution_hash_created": False,
            "approved_execution_hash": None,
            "execution_hash_consumed": False,
            "provider_execution_authorized": False,
            "evaluator_execution_authorized": False,
            "live_cost_approved": False,
            "maximum_future_approval_cap_usd": 41.0,
            "automatic_execution_authorized": False,
        },
        "claims_boundary": {
            "high_headroom_source_contract_implemented": True,
            "exact_three_task_panel_frozen": True,
            "runtime_contract_implemented_offline": True,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "runtime_rows_executed": 0,
            "run_or_result_state_created": False,
            "added_model_cost_usd": 0.0,
            "workflow_readiness_established": False,
            "budget_sufficiency_established": False,
            "task_success_or_hidden_outcome_observed": False,
            "no_memory_baseline_result_established": False,
            "comparison_denominator_eligible": False,
            "comparison_resource_policy_frozen": False,
            "memory_review_or_admission_or_index_unlocked": False,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "historical_artifacts_modified": False,
            "historical_exact_runs_rerun": False,
        },
        "next_gate": {
            "gate": "clean-no-call-preflight",
            "clean_source_commit_required": True,
            "clean_docker_and_evaluator_identity_required": True,
            "frozen_dataset_revalidation_required": True,
            "openai_sdk_and_fresh_pricing_revalidation_required": True,
            "candidate_execution_hash_required": True,
            "separate_user_approval_required": True,
            "maximum_future_approval_cap_usd": 41.0,
            "provider_call_allowed_during_preflight": False,
            "automatic_execution_authorized": False,
        },
    }
    body_hash = sha256_json(body)
    return {
        "schema_version": "high-headroom-readiness-source-gate-manifest-v1",
        "gate_id": f"d094_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the content-addressed D-094 source-only gate."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--recorded-at", default=RECORDED_AT)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    payload = build_source_gate(repo_root=args.repo_root.resolve(), recorded_at=args.recorded_at)
    if args.compact:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
