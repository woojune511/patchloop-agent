from __future__ import annotations

import argparse
import json
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from patchloop.contracts import PublicTask
from patchloop.util import sha256_bytes, sha256_json

RECORDED_AT = "2026-08-05T01:15:57Z"
DATASET_MANIFEST_HASH = (
    "sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786"
)
D095_BODY_HASH = (
    "sha256:79fe3312222896beec28070b5a77e36ffc7854a00c983a70f90cbe37ac2bb99f"
)
D093_BODY_HASH = (
    "sha256:3a5790e57252132387b803681339e00032c62f7026a81d9acbd9f4598fc64ccd"
)
D094_BODY_HASH = (
    "sha256:ab7be9ad2448d1016b88d451e271330844fc11d8fd4b890f08142618446ff929"
)

SOURCE_FILES: dict[str, dict[str, Any]] = {
    "d095-readiness-seal": {
        "path": (
            "reports/live-pilot/"
            "generic-high-headroom-readiness-v2v5-20260804-r1.json"
        ),
        "bytes": 28_269,
        "sha256": (
            "sha256:62ef705c992fcdb3e6e6b648e8376c4d5fdbff2534bd5b0a37158b99b4b3f95e"
        ),
    },
    "d093-readiness-correction": {
        "path": (
            "reports/live-pilot/artifacts/"
            "d093-readiness-budget-outcome-correction.json"
        ),
        "bytes": 9_611,
        "sha256": (
            "sha256:df8a35d7818dba3055ee4bb34519bd39abdc97d4d6add178d3d41b0521273941"
        ),
    },
    "d094-readiness-source-gate": {
        "path": (
            "reports/live-pilot/artifacts/"
            "d094-high-headroom-readiness-source-gate.json"
        ),
        "bytes": 13_284,
        "sha256": (
            "sha256:6887936ec141496e35e3a9d3bd6c34cf04cf02d1849bf80208677151a692c6ed"
        ),
    },
    "d083-historical-budget-freeze": {
        "path": (
            "reports/live-pilot/artifacts/"
            "d083-condition-neutral-comparison-budget-freeze.json"
        ),
        "bytes": 7_395,
        "sha256": (
            "sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88"
        ),
    },
    "d084-historical-runtime-gate": {
        "path": (
            "reports/live-pilot/artifacts/"
            "d084-condition-neutral-comparison-runtime-gate.json"
        ),
        "bytes": 7_178,
        "sha256": (
            "sha256:e7fb7b7e7e9dad3e6b31fb781f09151b940bf226bdd5876e5e75e472ff24b701"
        ),
    },
    "dataset-manifest": {
        "path": "data/dataset-manifest.yaml",
        "bytes": 47_368,
        "sha256": (
            "sha256:e8cf14ca9dabebcc03c3522e400dfcb79606541e9b11e59f49510ea5c40bebed"
        ),
    },
    "historical-baseline-template": {
        "path": "experiments/dev-no-memory-v5.template.yaml",
        "bytes": 1_876,
        "sha256": (
            "sha256:ef7f901a65764832f294e6e5d5706beb9f953523d669b292234d78bd7aa6a1a3"
        ),
    },
}

BASELINE_TASK_PATHS = (
    "tasks/dev-train/loguru-invalid-format-feedback/public.yaml",
    "tasks/dev-train/anyio-interrupt-runner-cleanup/public.yaml",
    "tasks/dev-train/tox-cross-section-empty-substitution/public.yaml",
    "tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml",
    "tasks/dev-train/pdm-ignore-active-venv-resolution/public.yaml",
    "tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml",
)

PUBLIC_TASK_FILES: dict[str, dict[str, Any]] = {
    "loguru-invalid-format-feedback": {
        "path": BASELINE_TASK_PATHS[0],
        "bytes": 2_392,
        "sha256": (
            "sha256:efec17dc692c0935553e9e3c67ad5463d977254ea52a536c1dcf4a4c43831f10"
        ),
        "public_spec_hash": (
            "sha256:4839d8e5e1e57efa2a33a458ab0fe839d5ef4200bbe53b0f56683d8b8b98e7ea"
        ),
    },
    "anyio-interrupt-runner-cleanup": {
        "path": BASELINE_TASK_PATHS[1],
        "bytes": 1_864,
        "sha256": (
            "sha256:ea977422306f9ce7203b4fc92aac83a73bc41554813d9ce1d794546767e76ddd"
        ),
        "public_spec_hash": (
            "sha256:b6d5b8d42a003795ed38256fa9a0e07c94578a6e0996179588a15d42604b86bf"
        ),
    },
    "tox-cross-section-empty-substitution": {
        "path": BASELINE_TASK_PATHS[2],
        "bytes": 1_903,
        "sha256": (
            "sha256:cf100f771e799824b2928f28faec4be76f011aa84667b1573b6fa373860b0c82"
        ),
        "public_spec_hash": (
            "sha256:e371eddfbc9e8c73f7b47def95480496d7f88ddccb0348c00a12a9b78c496521"
        ),
    },
    "hf-hub-xet-endpoint-propagation": {
        "path": BASELINE_TASK_PATHS[3],
        "bytes": 1_825,
        "sha256": (
            "sha256:3500452712d3977761f24da95170f073f86ec2a0589b69522321f91f5f473c4f"
        ),
        "public_spec_hash": (
            "sha256:8f7b0ea5f92ec9d843b8053f0739b42570b7407d76fe6f7a7ea6fd08c481a075"
        ),
    },
    "pdm-ignore-active-venv-resolution": {
        "path": BASELINE_TASK_PATHS[4],
        "bytes": 1_986,
        "sha256": (
            "sha256:3d819ce8136e11d0572954f1afcc1918134aeef2e84d8fa365970c45ff671c24"
        ),
        "public_spec_hash": (
            "sha256:6bbb24f06a3dd43956abaee9ca72ecf69f2cfc4e68b2cdc10d877209afe39d27"
        ),
    },
    "pyfakefs-makedirs-parent-traversal": {
        "path": BASELINE_TASK_PATHS[5],
        "bytes": 1_852,
        "sha256": (
            "sha256:5be7e6f6d2ad9722ee90c5a829aa043bf94c70ac317d5ce45254e4f3f9458eb0"
        ),
        "public_spec_hash": (
            "sha256:4d5de049d133ee29adf726733b7ace99b9d55518cc0433c72d2aa7b1576664d8"
        ),
    },
}


class D096BuildError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D096BuildError(message)


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
        raise D096BuildError(f"{label} is not valid JSON") from exc
    _require(isinstance(payload, dict), f"{label} must be a JSON object")
    return payload


def _load_yaml(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(content)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise D096BuildError(f"{label} is not valid YAML") from exc
    _require(isinstance(payload, dict), f"{label} must be a YAML object")
    return payload


def _validate_content_addressed(
    payload: dict[str, Any],
    *,
    expected_body_hash: str,
    label: str,
) -> dict[str, Any]:
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), f"{label} semantic body is missing")
    _require(
        payload.get("semantic_body_hash") == expected_body_hash,
        f"{label} semantic hash drifted",
    )
    _require(sha256_json(body) == expected_body_hash, f"{label} body hash drifted")
    return body


def _validate_sources(root: Path) -> dict[str, dict[str, Any]]:
    contents = {
        role: _read_exact(root, descriptor, label=role)
        for role, descriptor in SOURCE_FILES.items()
    }
    d095 = _load_json(contents["d095-readiness-seal"], label="D-095 seal")
    d095_body = _validate_content_addressed(
        d095,
        expected_body_hash=D095_BODY_HASH,
        label="D-095 seal",
    )
    _require(d095_body.get("milestone") == "D-095", "D-095 milestone drifted")
    d095_gate = d095_body.get("original_campaign_result", {}).get(
        "completion_gate", {}
    )
    for key in (
        "passed",
        "readiness_evidence_passed",
        "task_identity_passed",
        "row_binding_passed",
        "run_binding_passed",
        "schedule_binding_passed",
        "execution_binding_passed",
        "call_guard_contract_passed",
    ):
        _require(d095_gate.get(key) is True, f"D-095 {key} drifted")
    for key in (
        "expected_runs",
        "terminal_runs",
        "qualified_runs",
        "accepted_submission_runs",
        "official_evaluator_runs",
        "qualification_recomputed_runs",
    ):
        _require(d095_gate.get(key) == 3, f"D-095 {key} drifted")
    for key in (
        "budget_terminal_runs",
        "terminal_loop_failure_runs",
        "model_or_tool_call_budget_block_runs",
    ):
        _require(d095_gate.get(key) == 0, f"D-095 {key} drifted")
    for key in (
        "infrastructure_errors",
        "qualification_errors",
        "diagnostic_errors",
    ):
        _require(
            d095_body.get("original_campaign_result", {}).get(key) == 0,
            f"D-095 {key} drifted",
        )
    d095_claims = d095_body.get("claims_boundary", {})
    _require(
        d095_claims.get("calibration_only") is True
        and d095_claims.get("workflow_readiness_gate_passed") is True
        and d095_claims.get("comparison_resource_policy_frozen") is False
        and d095_claims.get("no_memory_performance_baseline_established") is False,
        "D-095 claims boundary drifted",
    )
    _require(
        d095_body.get("next_gate", {}).get("decision_required")
        == "separate-condition-neutral-resource-policy-and-baseline-admission",
        "D-095 next gate drifted",
    )
    d095_runtime = d095_body.get("environment", {}).get("runtime_contract", {})
    _require(
        d095_runtime.get("budget")
        == {
            "max_model_calls": None,
            "max_tool_calls": None,
            "max_total_tokens": 3_000_000,
            "wall_clock_timeout_seconds": 3_600,
        },
        "D-095 runtime budget drifted",
    )

    d093 = _load_json(
        contents["d093-readiness-correction"],
        label="D-093 correction",
    )
    d093_body = _validate_content_addressed(
        d093,
        expected_body_hash=D093_BODY_HASH,
        label="D-093 correction",
    )
    candidate = d093_body.get("next_gate", {}).get(
        "candidate_resource_derivation", {}
    )
    _require(
        candidate.get("observed_public_maximum_tokens") == 1_956_109
        and candidate.get("candidate_max_total_tokens") == 3_000_000
        and candidate.get("observed_public_maximum_wall_clock_ms") == 1_628_695
        and candidate.get("candidate_wall_clock_timeout_seconds") == 3_600
        and candidate.get("max_model_calls") is None
        and candidate.get("max_tool_calls") is None,
        "D-093 candidate derivation drifted",
    )
    _require(
        d093_body.get("correction_boundary", {}).get(
            "comparison_or_baseline_policy_selected"
        )
        is False,
        "D-093 historical boundary drifted",
    )

    d094 = _load_json(
        contents["d094-readiness-source-gate"],
        label="D-094 source gate",
    )
    d094_body = _validate_content_addressed(
        d094,
        expected_body_hash=D094_BODY_HASH,
        label="D-094 source gate",
    )
    _require(
        d094_body.get("schema_version")
        == "high-headroom-readiness-source-gate-v1"
        and d094_body.get("milestone")
        == "D-094 high-headroom diverse readiness source gate",
        "D-094 identity drifted",
    )
    d094_source = d094_body.get("panel_source", {})
    _require(
        d094_source.get("model")
        == {
            "provider": "openai",
            "model_id": "gpt-5.4-mini-2026-03-17",
            "reasoning_effort": "medium",
            "reasoning_mode": "standard",
            "service_tier": "default",
            "transport_max_retries": 0,
            "max_output_tokens": 25_000,
        }
        and d094_source.get("agent_tuple")
        == {
            "system_prompt_version": "SYSTEM_PROMPT_V3",
            "system_prompt_hash": (
                "sha256:441c71fdea2defed14f06b32c3fba7a7aaa19f7a3ca749bc994e72708d8a733b"
            ),
            "tool_schema_version": "v2",
            "tool_schema_hash": (
                "sha256:2ee296c2cf515bf2e0937ec1727dc02046a8560581d39b71246c5b91eccf0827"
            ),
            "context_policy_version": "phase-evidence-v5",
            "call_guard_policy": "model-tool-observability-only-v1",
            "memory_max_context_tokens": 2_000,
        }
        and d094_source.get("budget")
        == {
            "max_model_calls": None,
            "max_tool_calls": None,
            "max_total_tokens": 3_000_000,
            "wall_clock_timeout_seconds": 3_600,
        },
        "D-094 exact runtime source tuple drifted",
    )
    d094_pricing = d094_body.get("pricing", {})
    _require(
        d094_pricing.get("schema_version")
        == "high-headroom-readiness-pricing-v1"
        and d094_pricing.get("verified_at") == "2026-08-04T14:47:00Z"
        and d094_pricing.get("pricing_source_url")
        == "https://developers.openai.com/api/docs/pricing"
        and d094_pricing.get("endpoint_pricing_mode") == "standard-default"
        and d094_pricing.get("input_price_per_million_usd") == 0.75
        and d094_pricing.get("cached_input_price_per_million_usd") == 0.075
        and d094_pricing.get("output_price_per_million_usd") == 4.5
        and d094_pricing.get("worst_rate_reserve_formula")
        == (
            "(max_total_tokens + max_output_tokens) * "
            "output_price_per_million_usd / 1000000"
        )
        and d094_pricing.get("per_run_worst_rate_reserve_usd") == 13.6125
        and d094_pricing.get("reserve_is_expected_invoice") is False
        and d094_pricing.get("free_tier_or_billed_charge_claimed") is False,
        "D-094 pricing evidence drifted",
    )
    _require(
        d094_body.get("authorization_boundary", {}).get(
            "provider_execution_authorized"
        )
        is False,
        "D-094 historical authorization boundary drifted",
    )

    d083 = _load_json(
        contents["d083-historical-budget-freeze"],
        label="D-083 freeze",
    )
    _require(
        d083.get("freeze_id") == "d083-condition-neutral-comparison-budget-freeze",
        "D-083 identity drifted",
    )
    _require(
        d083.get("frozen_budget", {}).get("profile_id")
        == "gpt54mini-v2v5-condition-neutral-1600k-v1"
        and d083.get("frozen_budget", {}).get("max_total_tokens") == 1_600_000
        and d083.get("frozen_budget", {}).get("wall_clock_timeout_seconds")
        == 1_800,
        "D-083 historical profile drifted",
    )
    _require(
        d083.get("pricing", {}).get("existing_project_cap_usd") == 150.0,
        "D-083 project cap evidence drifted",
    )

    d084 = _load_json(
        contents["d084-historical-runtime-gate"],
        label="D-084 runtime gate",
    )
    _require(
        d084.get("gate_id") == "d084-condition-neutral-comparison-runtime-gate"
        and d084.get("claims_boundary", {}).get("comparison_runtime_gate_implemented")
        is True,
        "D-084 runtime gate drifted",
    )
    _require(
        d084.get("comparison_profile", {}).get("profile_id")
        == "gpt54mini-v2v5-condition-neutral-1600k-v1",
        "D-084 profile drifted",
    )

    dataset = _load_yaml(contents["dataset-manifest"], label="dataset manifest")
    _require(dataset.get("status") == "frozen", "dataset is not frozen")
    _require(
        dataset.get("targets", {}).get("memory-development") == 6,
        "memory-development target drifted",
    )
    task_rows = dataset.get("tasks")
    _require(isinstance(task_rows, list), "dataset task registry is missing")
    by_id = {
        row.get("task_id"): row
        for row in task_rows
        if isinstance(row, dict) and isinstance(row.get("task_id"), str)
    }
    public_tasks: dict[str, dict[str, Any]] = {}
    for task_path in BASELINE_TASK_PATHS:
        task_id = Path(task_path).parent.name
        row = by_id.get(task_id, {})
        descriptor = PUBLIC_TASK_FILES.get(task_id)
        _require(descriptor is not None, f"public CAS is missing for {task_id}")
        _require(
            descriptor.get("path") == task_path,
            f"public path drifted for {task_id}",
        )
        public_content = _read_exact(
            root,
            descriptor,
            label=f"public task {task_id}",
        )
        try:
            public_task = PublicTask.model_validate(
                _load_yaml(public_content, label=f"public task {task_id}")
            )
        except ValidationError as exc:
            raise D096BuildError(
                f"public task contract drifted for {task_id}"
            ) from exc
        public_spec_hash = sha256_json(public_task.model_dump(mode="json"))
        _require(
            row.get("role") == "memory-development"
            and row.get("admission_state") == "admitted"
            and row.get("path") == str(Path(task_path).parent).replace("\\", "/")
            and row.get("task_version") == public_task.task_version
            and row.get("public_spec_hash") == public_spec_hash
            and descriptor.get("public_spec_hash") == public_spec_hash
            and public_task.task_id == task_id,
            f"dataset admission drifted for {task_id}",
        )
        public_tasks[task_id] = {
            "task_version": public_task.task_version,
            "public_path": task_path,
            "public_bytes": descriptor["bytes"],
            "public_file_sha256": descriptor["sha256"],
            "public_spec_hash": public_spec_hash,
        }

    template = _load_yaml(
        contents["historical-baseline-template"],
        label="historical baseline template",
    )
    _require(
        template.get("tasks") == list(BASELINE_TASK_PATHS)
        and template.get("conditions") == ["no_memory"]
        and template.get("repetitions") == 2
        and template.get("seed") == 20260723,
        "baseline schedule carrier drifted",
    )
    _require(
        template.get("dataset_manifest_hash") == DATASET_MANIFEST_HASH,
        "baseline dataset hash drifted",
    )
    _require(
        template.get("budget")
        == {
            "max_model_calls": None,
            "max_tool_calls": None,
            "max_total_tokens": 1_600_000,
            "wall_clock_timeout_seconds": 1_800,
        },
        "historical template budget drifted",
    )
    return {
        "d095": d095_body,
        "d093": d093_body,
        "d094": d094_body,
        "d083": d083,
        "d084": d084,
        "dataset": dataset,
        "template": template,
        "public_tasks": public_tasks,
    }


def build_decision(
    *,
    repo_root: Path,
    recorded_at: str = RECORDED_AT,
) -> dict[str, Any]:
    sources = _validate_sources(repo_root)
    d095 = sources["d095"]
    d093 = sources["d093"]
    d094 = sources["d094"]
    d095_gate = d095["original_campaign_result"]["completion_gate"]
    candidate = d093["next_gate"]["candidate_resource_derivation"]
    d094_source = d094["panel_source"]
    source_model = d094_source["model"]
    source_agent_tuple = d094_source["agent_tuple"]
    source_budget = d094_source["budget"]
    source_pricing = d094["pricing"]

    per_run_reserve = (
        (
            Decimal(source_budget["max_total_tokens"])
            + Decimal(source_model["max_output_tokens"])
        )
        * Decimal(str(source_pricing["output_price_per_million_usd"]))
        / Decimal(1_000_000)
    )
    _require(
        per_run_reserve
        == Decimal(str(source_pricing["per_run_worst_rate_reserve_usd"])),
        "D-094 per-run reserve does not match its frozen formula inputs",
    )
    baseline_reserve = per_run_reserve * 12
    maximum_dev_reserve = per_run_reserve * 18
    core_reserve = per_run_reserve * 96
    current_project_cap = Decimal(
        str(sources["d083"]["pricing"]["existing_project_cap_usd"])
    )
    minimum_integer_baseline_cap = int(
        baseline_reserve.to_integral_value(rounding=ROUND_CEILING)
    )

    task_descriptors = [
        {
            "base_order": order,
            "task_id": Path(path).parent.name,
            "dataset_role": "memory-development",
            "admission_state": "admitted",
            **sources["public_tasks"][Path(path).parent.name],
        }
        for order, path in enumerate(BASELINE_TASK_PATHS, start=1)
    ]
    baseline_schedule_identity = {
        "tasks": list(BASELINE_TASK_PATHS),
        "condition": "no_memory",
        "repetitions": 2,
        "seed": 20260723,
        "expected_rows": 12,
    }

    body: dict[str, Any] = {
        "milestone": "D-096",
        "evidence_kind": (
            "offline-condition-neutral-resource-policy-and-"
            "no-memory-baseline-admission"
        ),
        "recorded_at": recorded_at,
        "source_bindings": [
            {
                "role": role,
                **descriptor,
                **(
                    {"semantic_body_hash": D095_BODY_HASH}
                    if role == "d095-readiness-seal"
                    else {"semantic_body_hash": D093_BODY_HASH}
                    if role == "d093-readiness-correction"
                    else {"semantic_body_hash": D094_BODY_HASH}
                    if role == "d094-readiness-source-gate"
                    else {}
                ),
            }
            for role, descriptor in SOURCE_FILES.items()
        ],
        "decision": {
            "schema_version": "condition-neutral-resource-baseline-decision-v1",
            "selected": (
                "freeze-high-headroom-policy-and-admit-new-no-memory-source-authoring"
            ),
            "workflow_readiness_prerequisite_satisfied": True,
            "policy_selection_uses_public_process_evidence_only": True,
            "task_success_or_hidden_outcome_used_for_selection": False,
            "budget_is_target_experimental_factor": False,
            "automatic_live_execution_authorized": False,
        },
        "evidence_basis": {
            "schema_version": "condition-neutral-resource-evidence-basis-v1",
            "d093_public_candidate": {
                "observed_public_maximum_tokens": candidate[
                    "observed_public_maximum_tokens"
                ],
                "token_headroom_multiplier": "3/2",
                "candidate_max_total_tokens": candidate[
                    "candidate_max_total_tokens"
                ],
                "observed_public_maximum_wall_clock_ms": candidate[
                    "observed_public_maximum_wall_clock_ms"
                ],
                "wall_headroom_multiplier": "2/1",
                "candidate_wall_clock_timeout_seconds": candidate[
                    "candidate_wall_clock_timeout_seconds"
                ],
            },
            "d095_exact_candidate_observation": {
                "expected_runs": d095_gate["expected_runs"],
                "terminal_runs": d095_gate["terminal_runs"],
                "qualified_runs": d095_gate["qualified_runs"],
                "accepted_submission_runs": d095_gate[
                    "accepted_submission_runs"
                ],
                "official_evaluator_runs": d095_gate["official_evaluator_runs"],
                "budget_terminal_runs": d095_gate["budget_terminal_runs"],
                "terminal_loop_failure_runs": d095_gate[
                    "terminal_loop_failure_runs"
                ],
                "model_or_tool_call_budget_block_runs": d095_gate[
                    "model_or_tool_call_budget_block_runs"
                ],
                "infrastructure_errors": 0,
                "qualification_errors": 0,
                "diagnostic_errors": 0,
                "readiness_gate_passed": True,
            },
            "interpretation": (
                "finite-equal-allocation-selected-before-comparison;"
                "not-a-general-completion-guarantee"
            ),
        },
        "selected_resource_policy": {
            "schema_version": "condition-neutral-comparison-resource-policy-v2",
            "profile_id": "gpt54mini-v2v5-condition-neutral-3000k-v1",
            "prospective_only": True,
            "provider": source_model["provider"],
            "model_id": source_model["model_id"],
            "reasoning_effort": source_model["reasoning_effort"],
            "reasoning_mode": source_model["reasoning_mode"],
            "service_tier": source_model["service_tier"],
            "transport_max_retries": source_model["transport_max_retries"],
            "system_prompt_version": source_agent_tuple["system_prompt_version"],
            "system_prompt_hash": source_agent_tuple["system_prompt_hash"],
            "tool_schema_version": source_agent_tuple["tool_schema_version"],
            "tool_schema_hash": source_agent_tuple["tool_schema_hash"],
            "context_policy_version": source_agent_tuple["context_policy_version"],
            "max_output_tokens": source_model["max_output_tokens"],
            "memory_max_context_tokens": source_agent_tuple[
                "memory_max_context_tokens"
            ],
            "budget": dict(source_budget),
            "call_guard_policy": source_agent_tuple["call_guard_policy"],
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
        },
        "prospective_supersession_boundary": {
            "schema_version": "condition-neutral-policy-supersession-v1",
            "d083_profile_id": "gpt54mini-v2v5-condition-neutral-1600k-v1",
            "d083_d084_historical_contracts_modified": False,
            "d083_profile_valid_for_historical_runs": True,
            "d083_profile_selected_for_new_runs": False,
            "d096_profile_selected_for_new_runs": True,
            "new_runtime_contract_schema": (
                "condition-neutral-comparison-runtime-contract-v2"
            ),
            "new_runtime_evidence_schema": (
                "condition-neutral-comparison-runtime-evidence-v2"
            ),
            "new_runtime_binding_implemented": False,
            "d087_retroactively_admitted": False,
            "d095_retroactively_admitted": False,
            "historical_run_result_or_qualification_modified": False,
        },
        "no_memory_baseline_admission": {
            "schema_version": "no-memory-baseline-admission-contract-v1",
            "admission_id": "memory-development-no-memory-12-row-v1",
            "dataset_manifest_hash": DATASET_MANIFEST_HASH,
            "task_descriptors": task_descriptors,
            "schedule_identity": {
                **baseline_schedule_identity,
                "content_hash": sha256_json(baseline_schedule_identity),
            },
            "historical_1600k_template_is_schedule_carrier_only": True,
            "successor_3000k_suite_required": True,
            "future_no_memory_source_authoring_unlocked": True,
            "live_collection_authorized": False,
            "baseline_result_established": False,
            "allowed_terminal_row_classes": [
                {
                    "class": "official-evaluator-completed",
                    "denominator_included": True,
                    "automatic_rerun_allowed": False,
                    "result_predicate": {
                        "attempt_status": "terminal",
                        "agent_submission_status": "completed",
                        "evaluation_status": "completed",
                        "official": True,
                        "outcome_kind_one_of": ["resolved", "task_failure"],
                        "terminal_error": None,
                    },
                    "trace_predicate": {
                        "submission_accepted_event_count": 1,
                        "model_generation_blocked_event_count": 0,
                        "run_completed_event_count": 1,
                    },
                    "evaluation_receipt_predicate": {
                        "schema_version": "evaluation-receipt-v1",
                        "present": True,
                        "content_hash_verified": True,
                        "run_patch_diff_and_verifier_hashes_bound": True,
                    },
                    "qualification_predicate": {
                        "trace_qualified": True,
                        "evaluation_reached": True,
                        "persisted_matches_read_only_recomputation": True,
                    },
                },
                {
                    "class": "trace-qualified-frozen-policy-budget-terminal",
                    "denominator_included": True,
                    "outcome": "agent_failure",
                    "automatic_rerun_allowed": False,
                    "memory_candidate_eligible": False,
                    "result_predicate": {
                        "attempt_status": "terminal",
                        "agent_submission_status": "failed",
                        "evaluation_status": "not_run",
                        "official": False,
                        "outcome_kind": "agent_failure",
                        "terminal_error_type": "ModelGenerationBudgetError",
                        "terminal_error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
                    },
                    "trace_predicate": {
                        "model_generation_blocked_event_count": 1,
                        "event_actor": "budget-guard",
                        "generation_started": False,
                        "request_artifact_and_body_cas_verified": True,
                        "provider_calls_after_block": 0,
                        "submission_accepted_event_count": 0,
                        "evaluation_receipt_present": False,
                        "allowed_bindings": [
                            {
                                "dimension": "total_tokens",
                                "event_schema": "model-generation-block-v1",
                                "reason_code": "exact_request_budget_exceeded",
                            },
                            {
                                "dimension": "wall_clock",
                                "event_schema": "model-generation-block-v3",
                                "reason_code": "wall_clock_budget_exhausted",
                            },
                        ],
                    },
                    "qualification_predicate": {
                        "trace_qualified": True,
                        "evaluation_reached": False,
                        "persisted_matches_read_only_recomputation": True,
                    },
                },
            ],
            "terminal_branch_partition": {
                "schema_version": "no-memory-terminal-branch-partition-v1",
                "branches": [
                    "official-evaluator-completed",
                    "trace-qualified-frozen-policy-budget-terminal",
                ],
                "mutually_exclusive": True,
                "exhaustive": True,
                "intersection_rows": 0,
                "unclassified_rows": 0,
                "sum_of_branch_counts_required": 12,
            },
            "campaign_completion_requirements": {
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
                "persisted_qualification_matches_read_only_recomputation": True,
                "plan_manifest_runtime_policy_binding_exact": True,
                "no_memory_boundary_passed": True,
                "prompt_usage_telemetry_complete": True,
                "issued_model_calls_equal_completed_responses": True,
                "blocked_generation_is_pre_provider_call": True,
                "store_false_and_truncation_disabled": True,
                "campaign_cost_censoring_allowed": False,
                "task_success_required": False,
            },
            "memory_candidate_rule": {
                "official_evaluator_task_failure_required": True,
                "trace_qualification_required": True,
                "leakage_scan_required": True,
                "budget_or_infrastructure_failure_eligible": False,
                "automatic_rule_admission": False,
                "maintainer_or_agent_review_required_after_collection": True,
            },
        },
        "cost_authorization_boundary": {
            "schema_version": "condition-neutral-high-headroom-cost-boundary-v1",
            "pricing_evidence_source_role": "d094-readiness-source-gate",
            "pricing_verified_at": source_pricing["verified_at"],
            "pricing_source_url": source_pricing["pricing_source_url"],
            "fixed_standard_rates_per_million_usd": {
                "input": source_pricing["input_price_per_million_usd"],
                "cached_input": source_pricing[
                    "cached_input_price_per_million_usd"
                ],
                "output": source_pricing["output_price_per_million_usd"],
            },
            "worst_rate_formula": source_pricing["worst_rate_reserve_formula"],
            "per_run_worst_rate_reserve_usd": float(per_run_reserve),
            "twelve_run_worst_rate_reserve_usd": float(baseline_reserve),
            "eighteen_run_worst_rate_reserve_usd": float(maximum_dev_reserve),
            "ninety_six_run_worst_rate_reserve_usd": float(core_reserve),
            "existing_project_cap_usd": float(current_project_cap),
            "twelve_run_cap_deficit_usd": float(
                baseline_reserve - current_project_cap
            ),
            "ninety_six_run_cap_deficit_usd": float(core_reserve - current_project_cap),
            "minimum_integer_cap_for_uncensored_twelve_run_worst_case_usd": float(
                minimum_integer_baseline_cap
            ),
            "blocker_code": "NO_MEMORY_AUTHORIZATION_CAP_PENDING",
            "campaign_cost_policy_selected": False,
            "project_cap_changed": False,
            "actual_invoice_or_free_tier_treatment_claimed": False,
        },
        "authorization_boundary": {
            "schema_version": "d096-offline-authorization-boundary-v1",
            "offline_decision_only": True,
            "new_suite_created": False,
            "runtime_binding_complete": False,
            "clean_preflight_created": False,
            "execution_hash_created": False,
            "live_cost_approval_embedded": False,
            "provider_execution_authorized": False,
            "evaluator_execution_authorized": False,
            "automatic_successor_execution_authorized": False,
        },
        "claims_boundary": {
            "workflow_readiness_prerequisite_satisfied": True,
            "comparison_resource_policy_frozen": True,
            "baseline_admission_contract_frozen": True,
            "future_no_memory_source_authoring_unlocked": True,
            "live_execution_authorized": False,
            "no_memory_baseline_result_established": False,
            "development_baseline_denominator_complete": False,
            "core_comparison_denominator_eligible": False,
            "memory_review_authorized": False,
            "memory_admission_unlocked": False,
            "memory_index_frozen": False,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "task_success_or_hidden_outcome_used_for_policy_selection": False,
            "prompt_tool_context_or_task_tuning_authorized": False,
            "historical_artifacts_modified": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0.0,
        },
        "next_gate": {
            "gate": "condition-neutral-runtime-v2-and-no-memory-source-gate",
            "required_actions": [
                (
                    "bind the D-096 profile through execution plan, RunManifest, "
                    "start/resume and qualification"
                ),
                "create a new exact 12-row no-memory successor suite",
                "select a non-censoring campaign cost policy and resolve the $150 cap conflict",
                "build a clean no-call preflight before requesting any live approval",
            ],
            "fresh_pricing_required": True,
            "new_experiment_id_required": True,
            "new_execution_hash_required": True,
            "separate_user_cost_approval_required": True,
            "provider_execution_authorized": False,
        },
    }
    body_hash = sha256_json(body)
    return {
        "schema_version": (
            "condition-neutral-resource-policy-baseline-admission-d096-evidence-v1"
        ),
        "decision_id": f"d096_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the content-addressed D-096 offline admission decision."
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
    payload = build_decision(repo_root=repo_root, recorded_at=args.recorded_at)
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
