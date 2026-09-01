"""Zero-call activation qualification for the AnyIO-v5 Lean V19 Rapid seam."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.three_visible_check_runtime_compatibility_qualification import (
    EXPECTED_CHECK_ORDER,
    build_three_visible_check_runtime_compatibility_qualification,
)
from patchloop.agent.three_visible_check_runtime_compatibility_qualification import (
    QUALIFICATION_PATH as THREE_CHECK_QUALIFICATION_PATH,
)
from patchloop.agent.three_visible_check_runtime_compatibility_qualification import (
    qualification_bytes as three_check_qualification_bytes,
)
from patchloop.agent.workflow_exploration_gate_activation_qualification import (
    QUALIFICATION_PATH as V19_QUALIFICATION_PATH,
)
from patchloop.agent.workflow_exploration_gate_activation_qualification import (
    build_workflow_exploration_gate_activation_qualification,
)
from patchloop.agent.workflow_exploration_gate_activation_qualification import (
    qualification_bytes as v19_qualification_bytes,
)
from patchloop.errors import ContractError
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.evals.rapid_public_development_v4 import _runtime_build_binding
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-exploration-gate-rapid-activation-qualification-v2"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-exploration-gate-rapid-activation-qualification-20260827-v2.json"
)
EXPERIMENT_ID = "rapid-public-dev-anyio-v5-exploration-ab-20260827-r15"
PLAN_SCHEMA = "experiment-execution-plan-v23"
PLAN_KIND = "rapid-public-development-batch-v1"
VERIFIER_ID = "rapid-r15-candidate-v23-plan-v23"

TASK_SUCCESSOR_QUALIFICATION_PATH = Path(
    "experiments/anyio-ordinary-failure-public-task-successor-source-qualification-20260827-v1.json"
)
TASK_SUCCESSOR_EXPECTED = {
    "file_bytes": 7_838,
    "file_sha256": "sha256:f0d0c375c37b6c601dcc5364e0294be0fa4b14576194bceb833aa674c59735bf",
    "content_hash": "sha256:5e5f1fd0db95cdf1221f11db0222a2b69aa39ddf36ba6755fd4b1f396216d489",
}
V19_EXPECTED = {
    "file_bytes": 4_925,
    "file_sha256": "sha256:a25881f54e66a11ef6f3ca9b41d0cf44ce7a37ec1b2fe7fd1efbade0994462c5",
    "content_hash": "sha256:1beb02b77f1b4d9985babe4e64dab4e09cc805bc87fabfa9733dec3f0d2bcb9a",
}
THREE_CHECK_EXPECTED = {
    "file_bytes": 7_395,
    "file_sha256": "sha256:74c1acdf905b417ae9d8d094228d1fd79eda7c95a8f0c354e91a4ffed9a4fef9",
    "content_hash": "sha256:068106622659ba325cc789253c76765334a3f58634479f33b385555a03f04080",
}
CONSUMED_R14_BUILDER = {
    "path": "patchloop/evals/rapid_public_development_v17.py",
    "file_bytes": 82_391,
    "file_sha256": "sha256:30f71d462d6348ff2683a18aec25858f51ba3bfae37ee17b04b460192d7ef399",
}
WORKFLOW_SOURCE_FILES = (
    "patchloop/agent/workflow_exploration_gate_rapid_activation_qualification.py",
    "patchloop/evals/live_verifier_registry.py",
    "patchloop/evals/rapid_public_development_v18.py",
)
V19_PERMITTED_SOURCE_CHANGES = (
    "patchloop/contracts.py",
    "tests/test_workflow_exploration_gate_activation_qualification.py",
)
THREE_CHECK_PERMITTED_SOURCE_CHANGES = (
    "patchloop/contracts.py",
    "tests/test_three_visible_check_runtime_compatibility_qualification.py",
)
PERMITTED_PREDECESSOR_SOURCE_CHANGES = (
    "patchloop/contracts.py",
    "tests/test_workflow_exploration_gate_activation_qualification.py",
    "tests/test_three_visible_check_runtime_compatibility_qualification.py",
)
SUPERSEDED_ACTIVATION_PATH = Path(
    "experiments/lean-harness-exploration-gate-rapid-activation-qualification-20260827-v1.json"
)
SUPERSEDED_ACTIVATION_EXPECTED = {
    "file_bytes": 14_335,
    "file_sha256": "sha256:16dd0ef1726b35697a43fb73cfbedec6c09c3505cf0c774c3fb19fd916dcf9ad",
    "content_hash": "sha256:fc78f5cfb404b98b171bfc210c7e0d1cdbc3fb8bcdfd527bb3ab00e9242a968f",
}


def _identity(root: Path, relative: str | Path) -> dict[str, Any]:
    selected = ensure_within(root, Path(relative).as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"exploration Rapid activation source is unavailable: {relative}")
    raw = selected.read_bytes()
    return {
        "path": selected.relative_to(root).as_posix(),
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }


def _canonical_artifact(
    root: Path,
    path: Path,
    expected: dict[str, Any],
    *,
    label: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    identity = _identity(root, path)
    try:
        raw = ensure_within(root, path.as_posix()).read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError(f"{label} is invalid") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    body = {key: item for key, item in value.items() if key != "content_hash"}
    descriptor = {**identity, "content_hash": value.get("content_hash")}
    if value.get("content_hash") != sha256_json(body) or any(
        descriptor.get(key) != item for key, item in expected.items()
    ):
        raise ContractError(f"{label} identity differs")
    return value, descriptor


def _semantic_projection(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in {"content_hash", "source_files"}}


def _source_transition(
    stored: dict[str, Any],
    current: dict[str, Any],
    permitted_changed_paths: tuple[str, ...],
) -> dict[str, Any]:
    prior_rows = stored.get("source_files")
    current_rows = current.get("source_files")
    if not isinstance(prior_rows, list) or not isinstance(current_rows, list):
        raise ContractError("Rapid activation predecessor source inventory is unavailable")
    prior = {row.get("path"): row for row in prior_rows if isinstance(row, dict)}
    now = {row.get("path"): row for row in current_rows if isinstance(row, dict)}
    if tuple(prior) != tuple(now):
        raise ContractError("Rapid activation predecessor source inventory differs")
    changed = [path for path in prior if prior[path] != now[path]]
    if changed != list(permitted_changed_paths):
        raise ContractError("Rapid activation predecessor source changes differ")
    return {
        "qualified_behavior_unchanged": _semantic_projection(stored)
        == _semantic_projection(current),
        "permitted_changed_paths": list(permitted_changed_paths),
        "observed_changed_paths": changed,
        "source_rows": [
            {
                "path": path,
                "qualified": prior[path],
                "current": now[path],
                "changed": prior[path] != now[path],
            }
            for path in prior
        ],
    }


def build_workflow_exploration_gate_rapid_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    v19, v19_descriptor = _canonical_artifact(
        root,
        V19_QUALIFICATION_PATH,
        V19_EXPECTED,
        label="Lean V19 predecessor qualification",
    )
    v19_raw = ensure_within(root, V19_QUALIFICATION_PATH.as_posix()).read_bytes()
    if v19_qualification_bytes(v19) != v19_raw:
        raise ContractError("Lean V19 predecessor qualification differs")
    current_v19 = build_workflow_exploration_gate_activation_qualification(root)
    v19_transition = _source_transition(v19, current_v19, V19_PERMITTED_SOURCE_CHANGES)

    task, task_descriptor = _canonical_artifact(
        root,
        TASK_SUCCESSOR_QUALIFICATION_PATH,
        TASK_SUCCESSOR_EXPECTED,
        label="AnyIO-v5 task successor qualification",
    )
    three, three_descriptor = _canonical_artifact(
        root,
        THREE_CHECK_QUALIFICATION_PATH,
        THREE_CHECK_EXPECTED,
        label="three-check compatibility qualification",
    )
    three_raw = ensure_within(root, THREE_CHECK_QUALIFICATION_PATH.as_posix()).read_bytes()
    if three_check_qualification_bytes(three) != three_raw:
        raise ContractError("three-check compatibility qualification differs")
    current_three = build_three_visible_check_runtime_compatibility_qualification(root)
    three_transition = _source_transition(
        three,
        current_three,
        THREE_CHECK_PERMITTED_SOURCE_CHANGES,
    )
    superseded_activation, superseded_activation_descriptor = _canonical_artifact(
        root,
        SUPERSEDED_ACTIVATION_PATH,
        SUPERSEDED_ACTIVATION_EXPECTED,
        label="superseded Rapid activation qualification v1",
    )
    if not (
        superseded_activation.get("rapid_candidate_created_by_qualification") is False
        and superseded_activation.get("evidence_boundary", {}).get("provider_calls") == 0
        and superseded_activation.get("evidence_boundary", {}).get("docker_calls") == 0
    ):
        raise ContractError("superseded Rapid activation boundary differs")
    if not (
        task.get("status") == "offline-source-qualified"
        and task.get("rapid_candidate_created") is False
        and tuple(task.get("successor_contract", {}).get("visible_check_ids", ()))
        == EXPECTED_CHECK_ORDER
        and three.get("runtime_source_compatible") is True
        and three.get("runtime_source_modified") is False
        and three.get("rapid_candidate_created") is False
        and v19_transition["qualified_behavior_unchanged"] is True
        and three_transition["qualified_behavior_unchanged"] is True
        and _identity(root, CONSUMED_R14_BUILDER["path"]) == CONSUMED_R14_BUILDER
    ):
        raise ContractError("Rapid activation preservation boundary differs")

    descriptor_hash = live_verifier_registry().descriptor_hash_for(
        experiment_id=EXPERIMENT_ID,
        plan_schema=PLAN_SCHEMA,
        plan_kind=PLAN_KIND,
    )
    runtime_build_hash = _runtime_build_binding(root)[0]
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "lean-v19-anyio-v5-r15-manifest-and-verifier-activation-v2",
        "experiment_id": EXPERIMENT_ID,
        "plan_schema": PLAN_SCHEMA,
        "plan_kind": PLAN_KIND,
        "verifier_id": VERIFIER_ID,
        "verifier_descriptor_hash": descriptor_hash,
        "runtime_build_hash": runtime_build_hash,
        "runtime_identity": {
            "runtime_policy_version": "lean-harness-v19",
            "tool_schema_version": "v23",
            "context_policy_version": "phase-evidence-v29",
            "request_evidence_schema": "lean-harness-request-evidence-v19",
            "exploration_gate_policy_version": "public-boundary-and-unknown-closure-v1",
            "activation_policy_version": "gateway-owned-public-exploration-closure-v1",
        },
        "v19_predecessor_qualification": v19_descriptor,
        "v19_source_transition": v19_transition,
        "task_successor_qualification": task_descriptor,
        "three_check_compatibility": three_descriptor,
        "three_check_source_transition": three_transition,
        "superseded_activation": {
            **superseded_activation_descriptor,
            "superseded_zero_call": True,
        },
        "source_files": [_identity(root, item) for item in WORKFLOW_SOURCE_FILES],
        "source_preservation": {
            "qualified_behavior_unchanged": True,
            "permitted_admission_source_changes": list(PERMITTED_PREDECESSOR_SOURCE_CHANGES),
            "consumed_r14_builder_unchanged": True,
            "lean_v18_behavior_modified": False,
            "anyio_v4_modified": False,
            "anyio_v5_visible_check_order": list(EXPECTED_CHECK_ORDER),
        },
        "evidence_boundary": {
            "public_source_and_qualification_only": True,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "task_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "network_calls": 0,
            "workspace_mutations": 0,
            "added_model_cost_usd": "0",
        },
        "rapid_candidate_created_by_qualification": False,
        "runtime_activation_authorized": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("exploration Rapid activation qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_exploration_gate_rapid_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_exploration_gate_rapid_activation_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_workflow_exploration_gate_rapid_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("exploration Rapid activation qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("exploration Rapid activation qualification bytes differ")
    if value != build_workflow_exploration_gate_rapid_activation_qualification(root):
        raise ContractError("exploration Rapid activation source binding differs")
    return value


__all__ = [
    "EXPERIMENT_ID",
    "PLAN_KIND",
    "PLAN_SCHEMA",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "VERIFIER_ID",
    "WORKFLOW_SOURCE_FILES",
    "build_workflow_exploration_gate_rapid_activation_qualification",
    "load_workflow_exploration_gate_rapid_activation_qualification",
    "materialize_workflow_exploration_gate_rapid_activation_qualification",
    "qualification_bytes",
]
