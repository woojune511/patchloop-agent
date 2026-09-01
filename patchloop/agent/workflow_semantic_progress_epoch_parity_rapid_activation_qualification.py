"""Zero-call Rapid activation qualification for opt-in Lean V20."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.workflow_semantic_progress_epoch_parity_qualification import (
    QUALIFICATION_PATH as V20_QUALIFICATION_PATH,
)
from patchloop.agent.workflow_semantic_progress_epoch_parity_qualification import (
    build_workflow_semantic_progress_epoch_parity_qualification,
)
from patchloop.agent.workflow_semantic_progress_epoch_parity_qualification import (
    qualification_bytes as v20_qualification_bytes,
)
from patchloop.errors import ContractError
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.evals.rapid_public_development_v4 import _runtime_build_binding
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-semantic-progress-epoch-parity-rapid-activation-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-semantic-progress-epoch-parity-"
    "rapid-activation-qualification-20260827-v1.json"
)
EXPERIMENT_ID = "rapid-public-dev-anyio-v5-epoch-parity-ab-20260827-r16"
PLAN_SCHEMA = "experiment-execution-plan-v24"
PLAN_KIND = "rapid-public-development-batch-v1"
VERIFIER_ID = "rapid-r16-candidate-v24-plan-v24"

V20_EXPECTED = {
    "file_bytes": 4_750,
    "file_sha256": ("sha256:88d5e7881cade273e2b9a31652ea4d6ace29e572970a47a0bc04a528cf345ceb"),
    "content_hash": ("sha256:ec05fe5665686deafbdfb16d5d5dd50c7089845cb3c0b99bf4da697b3ecfe5f7"),
}
TASK_SUCCESSOR_QUALIFICATION_PATH = Path(
    "experiments/anyio-ordinary-failure-public-task-successor-source-qualification-20260827-v1.json"
)
TASK_SUCCESSOR_EXPECTED = {
    "file_bytes": 7_838,
    "file_sha256": ("sha256:f0d0c375c37b6c601dcc5364e0294be0fa4b14576194bceb833aa674c59735bf"),
    "content_hash": ("sha256:5e5f1fd0db95cdf1221f11db0222a2b69aa39ddf36ba6755fd4b1f396216d489"),
}
THREE_CHECK_QUALIFICATION_PATH = Path(
    "experiments/anyio-v5-three-visible-check-runtime-compatibility-"
    "source-qualification-20260827-v1.json"
)
THREE_CHECK_EXPECTED = {
    "file_bytes": 7_395,
    "file_sha256": ("sha256:74c1acdf905b417ae9d8d094228d1fd79eda7c95a8f0c354e91a4ffed9a4fef9"),
    "content_hash": ("sha256:068106622659ba325cc789253c76765334a3f58634479f33b385555a03f04080"),
}
V20_PERMITTED_SOURCE_CHANGES = ("patchloop/contracts.py",)
SOURCE_FILES = (
    "patchloop/agent/workflow_semantic_progress_epoch_parity_rapid_activation_qualification.py",
    "patchloop/evals/live_verifier_registry.py",
    "patchloop/evals/rapid_public_development_v19.py",
    "patchloop/contracts.py",
)


def _identity(root: Path, relative: str | Path) -> dict[str, Any]:
    selected = ensure_within(root, Path(relative).as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"semantic epoch Rapid source is unavailable: {relative}")
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
) -> dict[str, Any]:
    prior_rows = stored.get("source_files")
    current_rows = current.get("source_files")
    if not isinstance(prior_rows, list) or not isinstance(current_rows, list):
        raise ContractError("V20 Rapid activation source inventory is unavailable")
    prior = {row.get("path"): row for row in prior_rows if isinstance(row, dict)}
    now = {row.get("path"): row for row in current_rows if isinstance(row, dict)}
    if tuple(prior) != tuple(now):
        raise ContractError("V20 Rapid activation source inventory differs")
    changed = [path for path in prior if prior[path] != now[path]]
    if changed != list(V20_PERMITTED_SOURCE_CHANGES):
        raise ContractError("V20 Rapid activation source changes differ")
    return {
        "qualified_behavior_unchanged": _semantic_projection(stored)
        == _semantic_projection(current),
        "permitted_changed_paths": list(V20_PERMITTED_SOURCE_CHANGES),
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


def build_workflow_semantic_progress_epoch_parity_rapid_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    v20, v20_descriptor = _canonical_artifact(
        root,
        V20_QUALIFICATION_PATH,
        V20_EXPECTED,
        label="Lean V20 predecessor qualification",
    )
    v20_raw = ensure_within(root, V20_QUALIFICATION_PATH.as_posix()).read_bytes()
    if v20_qualification_bytes(v20) != v20_raw:
        raise ContractError("Lean V20 predecessor qualification bytes differ")
    current_v20 = build_workflow_semantic_progress_epoch_parity_qualification(root)
    transition = _source_transition(v20, current_v20)

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
        label="AnyIO-v5 three-check compatibility qualification",
    )
    if not (
        transition["qualified_behavior_unchanged"] is True
        and task.get("status") == "offline-source-qualified"
        and task.get("rapid_candidate_created") is False
        and three.get("status") == "offline-source-qualified"
        and three.get("runtime_source_compatible") is True
        and three.get("rapid_candidate_created") is False
    ):
        raise ContractError("V20 Rapid activation preservation boundary differs")

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
        "scope": "lean-v20-anyio-v5-r16-manifest-and-verifier-activation",
        "experiment_id": EXPERIMENT_ID,
        "plan_schema": PLAN_SCHEMA,
        "plan_kind": PLAN_KIND,
        "verifier_id": VERIFIER_ID,
        "verifier_descriptor_hash": descriptor_hash,
        "runtime_build_hash": runtime_build_hash,
        "runtime_identity": {
            "runtime_policy_version": "lean-harness-v20",
            "tool_schema_version": "v24",
            "context_policy_version": "phase-evidence-v30",
            "request_evidence_schema": "lean-harness-request-evidence-v20",
            "exploration_gate_policy_version": "public-boundary-and-unknown-closure-v1",
            "exploration_gate_activation_policy_version": (
                "gateway-owned-public-exploration-closure-v1"
            ),
            "epoch_parity_policy_version": ("post-restore-semantic-progress-epoch-parity-v1"),
        },
        "v20_predecessor_qualification": v20_descriptor,
        "task_successor_qualification": task_descriptor,
        "three_check_compatibility": three_descriptor,
        "source_preservation": {
            "qualified_behavior_unchanged": True,
            "permitted_admission_source_changes": list(V20_PERMITTED_SOURCE_CHANGES),
            "transition": transition,
        },
        "source_files": [_identity(root, path) for path in SOURCE_FILES],
        "evidence_boundary": {
            "public_source_only": True,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "task_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
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
        raise ContractError("V20 Rapid activation qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_semantic_progress_epoch_parity_rapid_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_semantic_progress_epoch_parity_rapid_activation_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_workflow_semantic_progress_epoch_parity_rapid_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("V20 Rapid activation qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("V20 Rapid activation qualification bytes differ")
    current = build_workflow_semantic_progress_epoch_parity_rapid_activation_qualification(root)
    if value != current:
        raise ContractError("V20 Rapid activation source binding differs")
    return value


__all__ = [
    "EXPERIMENT_ID",
    "PLAN_KIND",
    "PLAN_SCHEMA",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "VERIFIER_ID",
    "build_workflow_semantic_progress_epoch_parity_rapid_activation_qualification",
    "load_workflow_semantic_progress_epoch_parity_rapid_activation_qualification",
    "materialize_workflow_semantic_progress_epoch_parity_rapid_activation_qualification",
    "qualification_bytes",
]
